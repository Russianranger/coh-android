"""Fresh native Linux kernel controls; no Wine/Android/device authority."""
from __future__ import annotations
import ctypes as C
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import time
import unittest

HERE=Path(__file__).resolve().parent
class Root(C.Structure):
    _fields_=[("guest",C.c_char_p),("host",C.c_char_p),("device",C.c_uint64),("inode",C.c_uint64),("uid",C.c_uint32)]
class Error(C.Structure):
    _fields_=[("number",C.c_int),("rows",C.c_uint64),("fallback",C.c_int)]
class Stats(C.Structure):
    _fields_=[("metadata",C.c_uint64),("names",C.c_uint64),("batches",C.c_uint64),("missing",C.c_uint64),("heap",C.c_size_t),("peak",C.c_size_t)]

def bind_library(path):
    lib=C.CDLL(str(path))
    lib.coh_live_namespace_open.argtypes=[C.POINTER(C.c_void_p),C.POINTER(Root),C.c_size_t,C.c_uint32,C.c_uint32,C.c_int,C.c_int,C.POINTER(Error)]
    lib.coh_live_namespace_open.restype=C.c_int
    lib.coh_live_directory_open.argtypes=[C.c_void_p,C.POINTER(C.c_void_p),C.c_char_p,C.c_void_p,C.c_void_p,C.POINTER(Error)]
    lib.coh_live_directory_open.restype=C.c_int
    lib.coh_live_directory_next.argtypes=[C.c_void_p,C.POINTER(C.c_void_p),C.POINTER(C.c_size_t),C.POINTER(Error)]
    lib.coh_live_directory_next.restype=C.c_int
    lib.coh_live_namespace_close.argtypes=[C.c_void_p]
    lib.coh_live_directory_close.argtypes=[C.c_void_p]
    lib.coh_live_namespace_stats.argtypes=[C.c_void_p,C.POINTER(Stats)]
    lib.coh_live_directory_identity.argtypes=[C.c_void_p,C.POINTER(C.c_uint64),C.POINTER(C.c_uint64),C.POINTER(C.c_uint32),C.POINTER(Error)]
    lib.coh_live_directory_identity.restype=C.c_int
    lib.coh_live_directory_guest_path.argtypes=[C.c_void_p]
    lib.coh_live_directory_guest_path.restype=C.c_char_p
    lib.coh_live_test_fault.argtypes=[C.c_int,C.c_int]
    return lib

def decode(blob,sequence,first):
    assert len(blob)<=27944 and blob[:8]==b"COHLIVE1"
    assert blob[8:24]==bytes(range(16)) and blob[24:40]==bytes(range(16,32))
    seq,start,count,final,reserved,size=struct.unpack_from("<6I",blob,40)
    assert (seq,start,reserved,size)==(sequence,first,0,len(blob))
    assert count<=85 and size==64+328*count and final in (0,1)
    rows=[];used=0
    for index in range(count):
        offset=64+index*328
        ordinal,status=struct.unpack_from("<II",blob,offset)
        assert (ordinal,status)==(first+index,0)
        wfd=blob[offset+8:offset+328]
        attributes,=struct.unpack_from("<I",wfd)
        write,=struct.unpack_from("<Q",wfd,20)
        high,low=struct.unpack_from("<II",wfd,28)
        name=wfd[44:304].split(b"\0",1)[0].decode("ascii")
        assert wfd[4:20]==bytes(16) and wfd[36:44]==bytes(8) and wfd[304:]==bytes(16)
        used=((used+7)&~7)+94+2*len(name)
        assert used<=8192
        rows.append({"name":name,"attrs":attributes,"time":write,"size":high*2**32+low})
    return rows,bool(final)

class NativeFixture:
    def __init__(self,lib,bindings,show=False,case=False,pin_changes=None):
        self.lib=lib;self.handle=C.c_void_p();self.cursors=[];self.error=Error()
        values=[]
        for guest,path in bindings:
            st=path.stat()
            values.append(Root(guest.encode(),os.fsencode(path),st.st_dev,st.st_ino,st.st_uid))
        if pin_changes:
            for field,value in pin_changes.items():setattr(values[0],field,value)
        roots=(Root*len(values))(*values)
        self.opened=bool(lib.coh_live_namespace_open(C.byref(self.handle),roots,len(roots),os.getuid(),1000,int(show),int(case),C.byref(self.error)))
    def open(self,path="/data/items"):
        cursor=C.c_void_p();error=Error()
        good=self.lib.coh_live_directory_open(self.handle,C.byref(cursor),path.encode(),bytes(range(16)),bytes(range(16,32)),C.byref(error))
        if good:self.cursors.append(cursor)
        return bool(good),cursor,error
    def next(self,cursor):
        out=C.c_void_p();size=C.c_size_t();error=Error()
        good=self.lib.coh_live_directory_next(cursor,C.byref(out),C.byref(size),C.byref(error))
        return bool(good),C.string_at(out,size.value) if good else None,error
    def all(self,cursor):
        sequence=first=0;rows=[]
        while True:
            good,blob,error=self.next(cursor)
            if not good:raise RuntimeError((error.number,error.rows,error.fallback))
            batch,final=decode(blob,sequence,first);rows+=batch
            sequence+=1;first+=len(batch)
            if final:return rows
    def stats(self):
        out=Stats();self.lib.coh_live_namespace_stats(self.handle,C.byref(out));return out
    def close_cursor(self,cursor):
        self.lib.coh_live_directory_close(cursor)
        self.cursors=[c for c in self.cursors if c.value!=cursor.value]
    def close(self):
        if self.handle.value:self.lib.coh_live_namespace_close(self.handle);self.handle=C.c_void_p();self.cursors=[]


def _permission_capability_drop():
    """Drop authority in the child only; no UID remapping or privileged DAC test."""
    class CapHeader(C.Structure):
        _fields_=[("version",C.c_uint32),("pid",C.c_int)]
    class CapData(C.Structure):
        _fields_=[("effective",C.c_uint32),("permitted",C.c_uint32),("inheritable",C.c_uint32)]
    libc=C.CDLL(None,use_errno=True)
    libc.prctl.argtypes=[C.c_int,C.c_ulong,C.c_ulong,C.c_ulong,C.c_ulong]
    libc.prctl.restype=C.c_int
    libc.capset.argtypes=[C.POINTER(CapHeader),C.POINTER(CapData)]
    libc.capset.restype=C.c_int
    # No-new-privileges prevents a root UID exec from regaining dropped authority.
    if libc.prctl(38,1,0,0,0)!=0:os._exit(117)
    header=CapHeader(0x20080522,0);data=(CapData*2)()
    if libc.capset(C.byref(header),data)!=0:os._exit(118)

def _permission_child(library,root_name,parent_name,scenario,pins_json):
    """Actual ordinary Linux DAC operations and exact native API, not a mock."""
    import fcntl
    root,parent=Path(root_name),Path(parent_name);pins=json.loads(pins_json)
    status={line.split(":",1)[0]:line.split(":",1)[1].strip()
            for line in Path("/proc/self/status").read_text().splitlines() if ":" in line}
    assert os.getuid()==pins["uid"] and os.geteuid()==pins["uid"]
    assert all(int(status[name],16)==0 for name in ("CapEff","CapPrm","CapInh"))
    assert status["NoNewPrivs"]=="1"
    lib=bind_library(library)
    lib.coh_live_namespace_validate.argtypes=[C.c_void_p,C.POINTER(Error)]
    lib.coh_live_namespace_validate.restype=C.c_int
    # Build from the parent's known ordinary inode, even when search is denied.
    spec=Root(b"/data",os.fsencode(root),pins["device"],pins["inode"],pins["uid"])
    f=NativeFixture.__new__(NativeFixture)
    f.lib=lib;f.handle=C.c_void_p();f.cursors=[];f.error=Error()
    before=len(os.listdir("/proc/self/fd"))
    try:
        parent_fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    except OSError as error:
        parent_read_errno=error.errno
    else:
        os.close(parent_fd);parent_read_errno=0
    if scenario!="no_search":assert parent_read_errno in (errno.EACCES,errno.ENOTDIR)
    f.opened=bool(lib.coh_live_namespace_open(C.byref(f.handle),C.byref(spec),1,
        os.getuid(),1000,0,0,C.byref(f.error)))
    observations={"uid":os.getuid(),"euid":os.geteuid(),
        "CapEff":status["CapEff"],"CapPrm":status["CapPrm"],"CapInh":status["CapInh"],
        "NoNewPrivs":status["NoNewPrivs"],"parent_mode":oct(parent.lstat().st_mode&0o777),
        "parent_O_RDONLY_errno":parent_read_errno,"namespace_opened":f.opened,"scenario":scenario}
    def replace_parent(as_link=False):
        moved=parent.with_name(parent.name+"-known-old")
        parent.rename(moved)
        if as_link:
            parent.symlink_to(moved.name,target_is_directory=True)
        else:
            parent.mkdir(mode=0o700);replacement=parent/root.name;replacement.mkdir(mode=0o700)
            (replacement/"items").mkdir();(replacement/"items"/"foreign").write_bytes(b"other")
            parent.chmod(0o111)
    try:
        if scenario in ("final_unreadable","no_search","ancestor_alias"):
            assert not f.opened and not f.handle.value
            expected=(errno.ENOTDIR,errno.ELOOP) if scenario=="ancestor_alias" else (errno.EACCES,)
            assert f.error.number in expected and (f.error.rows,f.error.fallback)==(0,1)
            observations["refusal"]={"errno":f.error.number,"rows":f.error.rows,"fallback":bool(f.error.fallback)}
        else:
            assert f.opened,(f.error.number,f.error.rows)
            held=[]
            for name in os.listdir("/proc/self/fd"):
                try:
                    if os.readlink("/proc/self/fd/"+name)==str(root):held.append(int(name))
                except FileNotFoundError:pass
            assert len(held)==1
            flags=fcntl.fcntl(held[0],fcntl.F_GETFL)
            assert flags&os.O_PATH==0 and flags&os.O_ACCMODE==os.O_RDONLY
            assert flags&os.O_DIRECTORY and fcntl.fcntl(held[0],fcntl.F_GETFD)&fcntl.FD_CLOEXEC
            observations["final_held_root_is_readonly_directory_not_O_PATH"]=True
            if scenario=="readable":
                # Linux authorizes known-name app-root reads through the execute-only parent.
                fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC);os.close(fd)
                error=Error();assert lib.coh_live_namespace_validate(f.handle,C.byref(error))
                good,c,error=f.open();assert good,(error.number,error.rows)
                rows=f.all(c);assert [r["name"] for r in rows]==[".","..","payload"]
                observations["actual_directory_rows"]=[r["name"] for r in rows]
            elif scenario=="late_unreadable":
                root.chmod(0o100);error=Error()
                assert not lib.coh_live_namespace_validate(f.handle,C.byref(error))
                assert (error.number,error.rows,error.fallback)==(errno.EACCES,0,1)
                observations["refusal"]={"errno":error.number,"rows":error.rows,"fallback":bool(error.fallback)}
            elif scenario in ("retarget_initial","retarget_alias_initial"):
                replace_parent(scenario=="retarget_alias_initial");error=Error()
                assert not lib.coh_live_namespace_validate(f.handle,C.byref(error))
                expected=(errno.ENOTDIR,errno.ELOOP) if scenario=="retarget_alias_initial" else (errno.ESTALE,)
                assert error.number in expected and (error.rows,error.fallback)==(0,1)
                observations["refusal"]={"errno":error.number,"rows":error.rows,"fallback":bool(error.fallback)}
            elif scenario in ("retarget_late","retarget_alias_late"):
                good,c,error=f.open();assert good
                good,raw,error=f.next(c);assert good
                rows,final=decode(raw,0,0);assert rows and not final
                replace_parent(scenario=="retarget_alias_late")
                good,_,error=f.next(c);assert not good
                expected=(errno.ENOTDIR,errno.ELOOP) if scenario=="retarget_alias_late" else (errno.ESTALE,)
                assert error.number in expected and error.rows==len(rows) and error.fallback==0
                observations["refusal"]={"errno":error.number,"rows":error.rows,"fallback":bool(error.fallback)}
            else:raise AssertionError("Unknown permission fixture")
    finally:f.close()
    after=len(os.listdir("/proc/self/fd"));assert before==after
    observations["held_descriptor_counts_before_after"]=[before,after]
    print(json.dumps(observations,sort_keys=True))

class KernelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build=tempfile.TemporaryDirectory(prefix="coh-native-live-core-build-")
        cls.binary=Path(cls.build.name)/"libnative-live-test.so"
        command=["gcc","-std=c11","-O2","-Wall","-Wextra","-Werror","-Wpedantic","-fPIC","-shared",
                 str(HERE/"coh_live_directory_core.c"),str(HERE/"native_core_faults.c"),"-o",str(cls.binary)]
        for symbol in ("malloc","calloc","openat","fdopendir","readdir","fstat","readlinkat","getxattr","closedir"):
            command += [f"-Wl,--wrap={symbol}"]
        subprocess.run(command,check=True,capture_output=True)
        cls.lib=bind_library(cls.binary)
    @classmethod
    def tearDownClass(cls):cls.build.cleanup()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="coh-native-live-kernel-")
        self.root=Path(self.temp.name);self.items=self.root/"items";self.items.mkdir()
        self.fixtures=[];self.lib.coh_live_test_fault(0,0)
    def tearDown(self):
        self.lib.coh_live_test_fault(0,0)
        for f in self.fixtures:f.close()
        self.temp.cleanup()
    def fixture(self,bindings=None,**kw):
        f=NativeFixture(self.lib,bindings or [("/data",self.root)],**kw);self.fixtures.append(f);return f
    def many(self,n=180):
        for i in range(n):(self.items/f"f{i:05d}").write_bytes(b"old")
    def cursor(self,f=None,path="/data/items"):
        f=f or self.fixture();self.assertTrue(f.opened,(f.error.number,f.error.rows))
        good,c,error=f.open(path);self.assertTrue(good,(error.number,error.rows));return f,c
    def first(self,f,c):
        good,blob,error=f.next(c);self.assertTrue(good,(error.number,error.rows));return decode(blob,0,0)[0],blob
    def rest(self,f,c,first):
        all_rows=list(first);sequence=1
        while True:
            good,blob,error=f.next(c);self.assertTrue(good,(error.number,error.rows));batch,final=decode(blob,sequence,len(all_rows));all_rows+=batch;sequence+=1
            if final:return all_rows

    def execute_permission_control(self,scenario):
        parent=self.root/"execute-only-parent";parent.mkdir(mode=0o700)
        app=parent/"app-owned";app.mkdir(mode=0o700);items=app/"items";items.mkdir()
        if scenario.endswith("late") and scenario.startswith("retarget"):
            for i in range(180):(items/f"f{i:05d}").write_bytes(b"owned")
        else:(items/"payload").write_bytes(b"owned")
        st=app.stat();pins={"device":st.st_dev,"inode":st.st_ino,"uid":st.st_uid}
        parent.chmod(0o444 if scenario=="no_search" else 0o111)
        requested=app
        if scenario=="final_unreadable":app.chmod(0o100)
        if scenario=="ancestor_alias":
            alias=self.root/"known-ancestor-alias";alias.symlink_to(parent.name,target_is_directory=True)
            requested=alias/app.name;parent=alias
        run=subprocess.run([os.sys.executable,str(Path(__file__).resolve()),"--permission-child",
            str(self.binary),str(requested),str(parent),scenario,json.dumps(pins)],
            preexec_fn=_permission_capability_drop,capture_output=True,text=True,timeout=15)
        self.assertEqual(run.returncode,0,run.stderr)
        result=json.loads(run.stdout);self.assertEqual(result["scenario"],scenario)
        self.assertEqual(result["NoNewPrivs"],"1")
        for name in ("CapEff","CapPrm","CapInh"):self.assertEqual(int(result[name],16),0)
        self.assertEqual(result["held_descriptor_counts_before_after"][0],
                         result["held_descriptor_counts_before_after"][1])
        return result

    def test_execute_only_ancestor_readable_final_real_DAC(self):
        result=self.execute_permission_control("readable")
        self.assertEqual(result["parent_O_RDONLY_errno"],errno.EACCES)
        self.assertTrue(result["final_held_root_is_readonly_directory_not_O_PATH"])
        self.assertEqual(result["actual_directory_rows"],[".","..","payload"])
    def test_execute_only_final_root_real_DAC_refused(self):
        self.assertEqual(self.execute_permission_control("final_unreadable")["refusal"]["errno"],errno.EACCES)
    def test_ancestor_missing_search_permission_real_DAC_refused(self):
        self.assertEqual(self.execute_permission_control("no_search")["refusal"]["errno"],errno.EACCES)
    def test_execute_only_symlink_ancestor_real_kernel_refused(self):
        self.assertFalse(self.execute_permission_control("ancestor_alias")["namespace_opened"])
    def test_execute_only_final_read_permission_removed_refused(self):
        self.assertEqual(self.execute_permission_control("late_unreadable")["refusal"]["errno"],errno.EACCES)
    def test_execute_only_ancestor_retarget_initial_refused(self):
        self.assertEqual(self.execute_permission_control("retarget_initial")["refusal"]["errno"],errno.ESTALE)
    def test_execute_only_ancestor_retarget_after_rows_no_fallback(self):
        self.assertFalse(self.execute_permission_control("retarget_late")["refusal"]["fallback"])
    def test_execute_only_ancestor_same_inode_alias_initial_refused(self):
        self.assertFalse(self.execute_permission_control("retarget_alias_initial")["refusal"]["rows"])
    def test_execute_only_ancestor_same_inode_alias_after_rows_no_fallback(self):
        self.assertFalse(self.execute_permission_control("retarget_alias_late")["refusal"]["fallback"])

    def test_native_current_fields_and_uppercase_order(self):
        names=["z","Z","a","A","_under","[bracket]","long filename.txt",".hidden"]
        for i,name in enumerate(names):
            p=self.items/name;p.write_bytes(bytes(i+1));os.utime(p,ns=(1700000000123456789,1700000000234567891))
        (self.items/"Dir").mkdir()
        f,c=self.cursor();self.assertEqual(f.stats().metadata,0)
        rows=f.all(c);self.assertEqual([r["name"] for r in rows],[".",".."]+sorted(names+["Dir"],key=lambda n:(n.upper(),n)))
        for r in rows:
            p=self.items/r["name"];st=p.stat();self.assertEqual(r["size"],0 if p.is_dir() else st.st_size)
            self.assertEqual(r["time"],st.st_mtime_ns//100+116444736000000000)
            self.assertEqual(bool(r["attrs"]&16),p.is_dir())
    def test_metadata_mutates_between_native_batches(self):
        self.many();f,c=self.cursor();first,_=self.first(f,c)
        target=self.items/"f00170";target.write_bytes(b"new-current-long-payload")
        os.utime(target,ns=(1700000000000000000,1700000000567890123))
        rows=self.rest(f,c,first);row=next(r for r in rows if r["name"]==target.name)
        self.assertEqual(row["size"],len(b"new-current-long-payload"));self.assertEqual(row["time"],17000000005678901+116444736000000000)
    def test_membership_snapshot_excludes_later_new_name(self):
        self.many();f,c=self.cursor();first,_=self.first(f,c);(self.items/"new_file").write_bytes(b"new")
        self.assertNotIn("new_file",[r["name"] for r in self.rest(f,c,first)])
    def test_deleted_name_is_current_proven_absence(self):
        self.many();f,c=self.cursor();first,_=self.first(f,c);(self.items/"f00170").unlink()
        self.assertNotIn("f00170",[r["name"] for r in self.rest(f,c,first)]);self.assertEqual(f.stats().missing,1)
    def test_directory_path_replacement_is_terminal_binding_refusal(self):
        self.many();f,c=self.cursor();first,_=self.first(f,c)
        self.items.rename(self.root/"olditems");self.items.mkdir();(self.items/"f00170").write_bytes(b"unrelated replacement")
        good,_,error=f.next(c);self.assertFalse(good);self.assertEqual((error.number,error.rows,error.fallback),(errno.ESTALE,len(first),0))
    def test_relative_link_after_directory_rename_is_binding_refusal(self):
        self.many();(self.items/"zlink").symlink_to("f00170");f,c=self.cursor();first,_=self.first(f,c)
        self.items.rename(self.root/"olditems");self.items.mkdir();(self.items/"f00170").write_bytes(b"different")
        good,_,error=f.next(c);self.assertFalse(good);self.assertEqual((error.number,error.rows,error.fallback),(errno.ESTALE,len(first),0))
    def test_absolute_guest_link_uses_bound_root(self):
        target=self.root/"second";target.mkdir();(target/"payload").write_bytes(b"actual target")
        (self.items/"link").symlink_to("/other/payload")
        f,c=self.cursor(self.fixture(bindings=[("/data",self.root),("/other",target)]))
        self.assertEqual(next(r["size"] for r in f.all(c) if r["name"]=="link"),13)
    def test_relative_parent_and_directory_link(self):
        (self.root/"payload").write_bytes(b"parent");(self.items/"link").symlink_to("../payload");(self.items/"dirlink").symlink_to("../items")
        f,c=self.cursor();rows=f.all(c);self.assertEqual(next(r["size"] for r in rows if r["name"]=="link"),6)
        row=next(r for r in rows if r["name"]=="dirlink");self.assertEqual(row["size"],0);self.assertTrue(row["attrs"]&16)
    def test_link_unknown_root_is_refusal_not_absence(self):
        (self.items/"link").symlink_to("/foreign/no-file");f,c=self.cursor()
        good,_,error=f.next(c);self.assertFalse(good);self.assertEqual(error.number,errno.EXDEV);self.assertEqual((error.rows,error.fallback),(0,1))
    def test_late_unknown_link_is_terminal_no_restart(self):
        self.many();(self.items/"zlink").symlink_to("/foreign/no-file");f,c=self.cursor();first,_=self.first(f,c)
        while True:
            good,_,error=f.next(c)
            if not good:break
        self.assertEqual(error.number,errno.EXDEV);self.assertGreater(error.rows,0);self.assertEqual(error.fallback,0)
        (self.items/"zlink").unlink();good,_,error2=f.next(c);self.assertFalse(good);self.assertEqual(error2.number,errno.EPIPE);self.assertEqual(error2.rows,error.rows)
    def test_legacy_name_refuses_before_metadata(self):
        (self.items/"old.l2s.0001").write_bytes(b"unknown");f=self.fixture();good,_,error=f.open();self.assertFalse(good);self.assertEqual(error.number,errno.EOPNOTSUPP);self.assertEqual(f.stats().metadata,0)
    def test_legacy_link_target_refuses_not_missing(self):
        (self.items/"link").symlink_to(".l2s0001");f,c=self.cursor();good,_,error=f.next(c);self.assertFalse(good);self.assertEqual(error.number,errno.EOPNOTSUPP)
    def test_link_loop_is_bounded(self):
        (self.items/"loop").symlink_to("loop");f,c=self.cursor();good,_,error=f.next(c);self.assertFalse(good);self.assertEqual(error.number,errno.ELOOP)
    def test_proven_broken_supported_link_is_skipped(self):
        (self.items/"broken").symlink_to("absent");f,c=self.cursor();self.assertEqual([r["name"] for r in f.all(c)],[".",".."])
    def test_nonascii_membership_refuses_before_rows(self):
        (self.items/"caf\u00e9").write_bytes(b"unknown");f=self.fixture();good,_,error=f.open();self.assertFalse(good);self.assertEqual(error.number,errno.EOPNOTSUPP)
    def test_windows_invalid_name_refuses_before_rows(self):
        (self.items/"bad:name").write_bytes(b"unknown");f=self.fixture();good,_,error=f.open();self.assertFalse(good);self.assertEqual(error.number,errno.EOPNOTSUPP)
    def test_native_root_wrong_inode_refuses(self):
        f=self.fixture(pin_changes={"inode":self.root.stat().st_ino+1});self.assertFalse(f.opened);self.assertEqual(f.error.number,errno.ESTALE)
    def test_native_root_wrong_uid_refuses(self):
        f=self.fixture(pin_changes={"uid":os.getuid()+1});self.assertFalse(f.opened)
    def test_host_symlink_ancestor_refuses(self):
        alias=self.root/"alias";alias.symlink_to(self.items,target_is_directory=True)
        f=self.fixture(bindings=[("/data",alias)]);self.assertFalse(f.opened)
    def test_unknown_guest_root_and_prefix_collision(self):
        f=self.fixture()
        for path in ("/foreign","/datax/items"):
            good,_,error=f.open(path);self.assertFalse(good);self.assertEqual(error.number,errno.EXDEV)
    def test_nested_bind_longest_component_boundary(self):
        alternate=self.root/"alternate";alternate.mkdir();(alternate/"payload").write_bytes(b"bound")
        (self.items/"payload").write_bytes(b"unrelated")
        f,c=self.cursor(self.fixture(bindings=[("/data",self.root),("/data/items",alternate)]));self.assertEqual(next(r["size"] for r in f.all(c) if r["name"]=="payload"),5)
    def test_cross_device_bind_is_initial_refusal(self):
        if not Path("/dev/shm").is_dir():self.skipTest("No separate shared-memory filesystem")
        with tempfile.TemporaryDirectory(prefix="coh-live-owned-cross-device-",dir="/dev/shm") as other:
            p=Path(other)
            if p.stat().st_dev==self.root.stat().st_dev:self.skipTest("Fixture filesystems have same device")
            f=self.fixture(bindings=[("/data",self.root),("/other",p)])
            self.assertFalse(f.opened);self.assertEqual(f.error.number,errno.EXDEV)
    def test_exact_held_identity_and_resolved_guest_target(self):
        target=self.root/"target";target.mkdir();(target/"file").write_bytes(b"payload")
        (self.root/"alias").symlink_to("/data/target",target_is_directory=True)
        f,c=self.cursor(path="/data/alias");dev=C.c_uint64();ino=C.c_uint64();uid=C.c_uint32();error=Error()
        self.assertTrue(self.lib.coh_live_directory_identity(c,C.byref(dev),C.byref(ino),C.byref(uid),C.byref(error)))
        self.assertEqual((dev.value,ino.value,uid.value),(target.stat().st_dev,target.stat().st_ino,target.stat().st_uid))
        self.assertEqual(self.lib.coh_live_directory_guest_path(c),b"/data/target")
    def test_alias_target_change_is_initial_binding_refusal(self):
        (self.root/"first").mkdir();(self.root/"second").mkdir();alias=self.root/"alias";alias.symlink_to("first",target_is_directory=True)
        f,c=self.cursor(path="/data/alias");alias.unlink();alias.symlink_to("second",target_is_directory=True)
        good,_,error=f.next(c);self.assertFalse(good);self.assertEqual((error.number,error.rows,error.fallback),(errno.ESTALE,0,1))
    def test_duplicate_binding_refuses(self):
        f=self.fixture(bindings=[("/data",self.root),("/data",self.items)]);self.assertFalse(f.opened)
    def test_root_replacement_late_fails_and_preserves_prior_rows(self):
        self.many();f,c=self.cursor();first,_=self.first(f,c)
        moved=self.root.with_name(self.root.name+"-owned-moved");self.root.rename(moved);self.root.mkdir()
        try:
            good,_,error=f.next(c);self.assertFalse(good);self.assertEqual((error.number,error.rows,error.fallback),(errno.ESTALE,len(first),0))
        finally:
            self.root.rmdir();moved.rename(self.root)
    def test_special_file_refuses_without_body_read(self):
        os.mkfifo(self.items/"pipe");f,c=self.cursor();good,_,error=f.next(c);self.assertFalse(good);self.assertEqual(error.number,errno.EOPNOTSUPP)
    def test_current_dos_xattr_hidden_system_projection(self):
        target=self.items/"file";target.write_bytes(b"x");os.setxattr(target,"user.DOSATTRIB",b"0x6")
        f,c=self.cursor();row=next(r for r in f.all(c) if r["name"]=="file");self.assertEqual(row["attrs"]&6,6)
    def test_unknown_xattr_is_refusal(self):
        target=self.items/"file";target.write_bytes(b"x");os.setxattr(target,"user.DOSATTRIB",b"unsupported")
        f,c=self.cursor();good,_,error=f.next(c);self.assertFalse(good);self.assertEqual(error.number,errno.EOPNOTSUPP)
    def test_signed_xattr_overflow_matches_reviewed_Wine_flags(self):
        target=self.items/"file";target.write_bytes(b"x")
        for text,flags in ((b"0x7fffffffffffffff",6),(b"0x8000000000000000",6),(b"0xffffffffffffffff",6),(b"0x10000000000000000",6),(b"0x80000000",0)):
            os.setxattr(target,"user.DOSATTRIB",text);f,c=self.cursor()
            self.assertEqual(next(r["attrs"]&6 for r in f.all(c) if r["name"]=="file"),flags,text)
            f.close_cursor(c)
    def test_readonly_any_permission_bit_and_hidden_option(self):
        names=[("none",0o444),("group",0o464),("other",0o446),(".dot",0o444)]
        for name,mode in names:p=self.items/name;p.write_bytes(b"x");p.chmod(mode)
        f,c=self.cursor();rows={r["name"]:r for r in f.all(c)}
        self.assertTrue(rows["none"]["attrs"]&1);self.assertFalse(rows["group"]["attrs"]&1);self.assertFalse(rows["other"]["attrs"]&1);self.assertTrue(rows[".dot"]["attrs"]&2)
        f,c=self.cursor(self.fixture(show=True));self.assertFalse(next(r for r in f.all(c) if r["name"]==".dot")["attrs"]&2)
    def test_cursor_bound_and_namespace_owns_all_descriptors(self):
        f=self.fixture();baseline=len(os.listdir("/proc/self/fd"))
        for _ in range(16):self.cursor(f)
        good,_,error=f.open();self.assertFalse(good);self.assertEqual(error.number,errno.EMFILE)
        f.close();self.assertLessEqual(len(os.listdir("/proc/self/fd")),baseline)
    def test_exact_directory_name_bound_including_dot_entries(self):
        self.many(8190);f,c=self.cursor();self.assertEqual(len(f.all(c)),8192);f.close_cursor(c)
        (self.items/"extra").write_bytes(b"x");good,_,error=f.open();self.assertFalse(good);self.assertEqual(error.number,errno.EOVERFLOW)
    def test_memory_reclaimed_when_cursor_closes(self):
        self.many(500);f=self.fixture();baseline=f.stats().heap;f,c=self.cursor(f);self.assertGreater(f.stats().heap,baseline)
        f.all(c);f.close_cursor(c);self.assertEqual(f.stats().heap,baseline);self.assertLessEqual(f.stats().peak,32*1024*1024)
    def test_owned_fd_cleanup_on_open_listing_allocation_failures(self):
        self.many(20);f=self.fixture();baseline=len(os.listdir("/proc/self/fd"));heap=f.stats().heap
        for kind in (1,3,4,5,6,9):
            for after in (0,1,2):
                self.lib.coh_live_test_fault(kind,after);good,c,error=f.open()
                self.lib.coh_live_test_fault(0,0)
                if good:f.close_cursor(c)
                else:self.assertEqual(error.rows,0)
                self.assertEqual(len(os.listdir("/proc/self/fd")),baseline,(kind,after));self.assertEqual(f.stats().heap,heap,(kind,after))
    def test_owned_fd_cleanup_on_namespace_allocation_failure(self):
        baseline=len(os.listdir("/proc/self/fd"));self.lib.coh_live_test_fault(2,0);f=self.fixture();self.assertFalse(f.opened);self.assertEqual(len(os.listdir("/proc/self/fd")),baseline)
    def test_owned_fd_cleanup_on_readlink_and_xattr_failure(self):
        (self.items/"file").write_bytes(b"x");(self.items/"link").symlink_to("file")
        for kind in (7,8):
            f,c=self.cursor();baseline=len(os.listdir("/proc/self/fd"));self.lib.coh_live_test_fault(kind,0)
            good,_,error=f.next(c);self.assertFalse(good);self.assertEqual(error.number,errno.EIO)
            self.lib.coh_live_test_fault(0,0);self.assertEqual(len(os.listdir("/proc/self/fd")),baseline);f.close_cursor(c)
    def test_readonly_service_preserves_control_profile_bytes(self):
        profile=self.items/"profile.dat";profile.write_bytes(b"synthetic identity powers costume map position")
        before=hashlib.sha256(profile.read_bytes()).hexdigest();st=profile.stat();f,c=self.cursor();f.all(c)
        self.assertEqual(hashlib.sha256(profile.read_bytes()).hexdigest(),before);self.assertEqual(profile.stat().st_mtime_ns,st.st_mtime_ns)
    def test_overflow_entry_is_reobserved_not_cached(self):
        self.many(180);f,c=self.cursor();first,_=self.first(f,c)
        self.assertGreater(f.stats().metadata,len(first))
        next_index=len(first)-2;target=self.items/f"f{next_index:05d}";target.write_bytes(b"overflow was updated")
        rows=self.rest(f,c,first);self.assertEqual(next(r["size"] for r in rows if r["name"]==target.name),20)
    def test_85_row_cap_still_observes_nonfitting_86th_candidate(self):
        names=[chr(c) for c in range(32,127) if chr(c) not in '/\\:*?"<>|.']
        self.assertEqual(len(names),85)
        for name in names:(self.items/name).write_bytes(b"old")
        f,c=self.cursor();first,blob=self.first(f,c)
        self.assertEqual(len(first),85);self.assertEqual(len(blob),27944);self.assertEqual(f.stats().metadata,86)
        pending=sorted(names,key=lambda n:(n.upper(),n))[83];(self.items/pending).write_bytes(b"changed after overflow lookup")
        rows=self.rest(f,c,first)
        self.assertEqual(next(r["size"] for r in rows if r["name"]==pending),29)
    def test_late_xattr_error_retains_terminal_failure(self):
        self.many();f,c=self.cursor();first,_=self.first(f,c);os.setxattr(self.items/"f00170","user.DOSATTRIB",b"unknown")
        while True:
            good,_,error=f.next(c)
            if not good:break
        self.assertEqual(error.number,errno.EOPNOTSUPP);self.assertGreaterEqual(error.rows,len(first));self.assertEqual(error.fallback,0)
    def test_final_cursor_cannot_restart(self):
        f,c=self.cursor();f.all(c);good,_,error=f.next(c);self.assertFalse(good);self.assertEqual(error.number,errno.EPIPE);self.assertEqual(error.fallback,0)

if __name__=="__main__":
    if len(os.sys.argv)>1 and os.sys.argv[1]=="--permission-child":
        _permission_child(*os.sys.argv[2:])
    else:unittest.main(verbosity=2)
