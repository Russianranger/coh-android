#!/usr/bin/env python3
"""Fresh read-only audit of original compiled/executed native ARM evidence.

It never compiles or executes C, JNI, Java, QEMU, Wine, Game or a database. The
original overall FAILED report remains byte-for-byte failed. Passed components
retain their original run/command owner; only this inspection is fresh.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import urllib.request
import base64
import zipfile

HERE=Path(__file__).resolve().parent
MANIFEST=HERE/"retained-ARM-artifact-11878700818.json"
EXPORTED=("nativeCreate","nativeOpen","nativeNext","nativeCloseCursor","nativeCloseNamespace","nativeStats","nativeIdentity","nativeCanonicalGuestPath")
PREFIX="Java_io_github_russianranger_cohclientinteractive_NativeLiveDirectory_"
EXPECTED_COMMANDS=("host-native-kernel-tests","compile-host-fixture","execute-host-fixture","compile-host-JNI","compile-Java-facade-fixture","execute-host-JNI","NDK-compiler-version","compile-Bionic-ARM64-fixture","inspect-Bionic-ARM64-fixture","execute-Bionic-ARM64-fixture","compile-Bionic-ARM64-JNI","inspect-Bionic-ARM64-JNI")
class AuditFailure(ValueError):pass
def require(condition,message):
    if not condition:raise AuditFailure(message)
def digest(data):return {"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}
def pin(path):return digest(Path(path).read_bytes())
def authenticate_zip(path,manifest):
    expected=manifest["origin"]["bytes"]
    require(Path(path).stat().st_size==expected,"Original artifact ZIP size mismatch before intake")
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    with os.fdopen(fd,"rb") as stream:
        held=os.fstat(stream.fileno())
        require(stat.S_ISREG(held.st_mode) and held.st_size==expected,"Artifact changed/type mismatch before payload read")
        data=stream.read(expected+1)
    require(digest(data)=={k:manifest["origin"][k] for k in ("bytes","sha256")},"Original artifact ZIP bytes mismatch")
    out={}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos=z.infolist();require(len(infos)==43 and len({i.filename for i in infos})==43,"Exact member inventory required")
        require(sum(i.file_size for i in infos)<=32*1024*1024 and z.testzip() is None,"ZIP bound/CRC failed")
        require(set(i.filename for i in infos)==set(manifest["members"]),"ZIP membership changed")
        for i in infos:
            p=Path(i.filename)
            require(not p.is_absolute() and ".." not in p.parts and not i.is_dir() and stat.S_IFMT(i.external_attr>>16)!=stat.S_IFLNK,"Unsafe artifact member")
            data=z.read(i);require(digest(data)==manifest["members"][i.filename],"Member bytes changed: "+i.filename);out[i.filename]=data
    return out
def inspect_elf(text):
    require("ELF64" in text and "AArch64" in text,"JNI architecture mismatch")
    needed=re.findall(r"\(NEEDED\).*?\[([^]]+)\]",text)
    require(needed==["libdl.so","libc.so"],"Unknown or changed exact JNI dependency set")
    soname=re.findall(r"\(SONAME\).*?\[([^]]+)\]",text)
    require(not soname,"Unexpected SONAME; original uniquely named library has none")
    stacks=[line for line in text.splitlines() if "GNU_STACK" in line]
    require(len(stacks)==1 and re.search(r"\bRW\s+\d+\s*$",stacks[0]) is not None,"Executable/unknown stack policy")
    imported=re.findall(r"\bUND[ \t]+([^ \t\n]+)",text)
    imported=[x for x in imported if x!="0"]
    require(len(imported)==35 and all(x.endswith("@LIBC") for x in imported),"Unknown versioned import; LIBDL must remain unused")
    exports=re.findall(re.escape(PREFIX)+r"(\w+)",text)
    require(len(exports)==8 and set(exports)==set(EXPORTED),"Exact eight JNI exports required")
    return {"needed":needed,"SONAME":None,"GNU_STACK":"RW nonexecutable","JNI_exports":sorted(exports),"undefined_imports":imported,"LIBDL_undefined_imports":0}
def original_execution(members):
    root="out/native-live-directory-037/"
    report=json.loads(members[root+"qualification.json"])
    require(report["status"]=="failed" and report["failure"]=={"type":"ValueError","message":"JNI dependency boundary changed"},"Original failed outcome must be retained")
    commands=report["commands"]
    require(tuple(x["label"] for x in commands)==EXPECTED_COMMANDS and all(x["exit_code"]==0 for x in commands),"Original finite successful command ownership mismatch")
    for item in commands:
        for suffix in ("stdout","stderr"):
            require(digest(members[root+item["label"]+"."+suffix])==item[suffix],"Original raw command provenance mismatch")
    kernel=members[root+"host-native-kernel-tests.stderr"].decode()
    require("Ran 42 tests" in kernel and kernel.rstrip().endswith("OK"),"Original42 native kernel tests unqualified")
    host=json.loads(members[root+"execute-host-fixture.stdout"])
    jni=json.loads(members[root+"execute-host-JNI.stdout"])
    arm=json.loads(members[root+"execute-Bionic-ARM64-fixture.stdout"])
    require(host["controls_passed"]==26 and host["failures"]==0,"Original host C fixture failed")
    require(jni["controls_passed"]==28 and jni["failures"]==0 and not members[root+"execute-host-JNI.stderr"],"Original checked-JNI failed/warned")
    require(arm["controls_passed"]==26 and arm["failures"]==0 and arm["libc"]=="Bionic" and arm["pointer_bytes"]==8 and arm["stat_bytes"]==128,"Original actual Bionic fixture failed/ABI mismatch")
    for flag in ("Android_OS_Wine_FEX_PRoot_parity","registered_Game_consumer","shipping_admission","physical_Thor_performance","native_SQL_or_player_data_touched"):
        require(report[flag] is False,"Original closed gate changed")
    return report,{"host_kernel_tests":42,"host_C_controls":26,"checked_host_JNI_controls":28,"static_Bionic_ARM64_controls":26,"original_command_count":12,"original_overall_status":"failed","raw_Bionic_observation":arm,"execution_and_build_owner":"43ac851 / run38531585318 / job115744482237"}
def current_source(members,repository):
    old_report=json.loads(members["out/native-live-directory-037/qualification.json"])
    relevant=("coh_live_directory_core.h","coh_live_directory_core.c","coh_live_directory_jni.c","native_core_faults.c","test_native_live_directory_core.py","native_live_fixture.c","NativeLiveDirectory.java","NativeLiveDirectoryFixture.java","qualify_native_live_directory.py")
    out={}
    for name in relevant:
        data=members["tools/native_live_directory/"+name]
        require(digest(data)==old_report["source_files"][name],"Original backend source report pin drift")
        require((repository/"tools/native_live_directory"/name).read_bytes()==data,"Current compiled/tested source changed: "+name)
        out[name]=digest(data)
    return out
def run_readonly(command,out,label):
    result=subprocess.run([str(x) for x in command],capture_output=True,timeout=60,check=False)
    require(len(result.stdout)<=256*1024 and len(result.stderr)<=256*1024,"Read-only command output bound")
    (out/(label+".stdout")).write_bytes(result.stdout);(out/(label+".stderr")).write_bytes(result.stderr)
    require(result.returncode==0,label+" failed")
    return result.stdout.decode()+result.stderr.decode()
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--artifact",type=Path,required=True);parser.add_argument("--out",type=Path,required=True);parser.add_argument("--ndk",type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    manifest=json.loads(MANIFEST.read_text());result={"schema":"coh-live-native-retained-inspection-v1","started_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"fresh_action":"read-only artifact/ELF/compiler-driver inspection only","status":"incomplete","shipping_admission":False,"Android_Wine_FEX_PRoot_qualified":False,"native_Game_registered":False,"physical_Thor_improvement_demonstrated":False,"compilation_or_fixture_reexecution":False}
    try:
        members=authenticate_zip(args.artifact,manifest);old,execution=original_execution(members)
        result["source_files"]=current_source(members,HERE.parents[1]);result["original_execution"]=execution;result["original_origin"]=manifest["origin"]
        so=out/"libcoh_live_directory.so";so.write_bytes(members["out/native-live-directory-037/libcoh_live_directory.so"])
        result["JNI"]={**pin(so),**inspect_elf(run_readonly(["readelf","--wide","--file-header","--program-headers","--dynamic","--dyn-syms",so],out,"fresh-ELF-inspection"))}
        require(pin(args.ndk/"source.properties")==old["NDK"]["source_properties"],"NDK source-properties identity changed")
        compiler=args.ndk/"toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android29-clang"
        require(pin(compiler.resolve())==old["NDK"]["compiler"],"NDK compiler wrapper identity changed")
        version=run_readonly([compiler,"--version"],out,"fresh-compiler-version")
        require(version==old["NDK"]["compiler_version"],"Exact original compiler version/source identity required")
        command=next(x["command"] for x in old["commands"] if x["label"]=="compile-Bionic-ARM64-JNI")
        require(command[0]==str(compiler),"Original linker driver route changed")
        dry=run_readonly([compiler,"-###",*command[1:]],out,"fresh-driver-dry-run")
        require("ld.lld" in dry and '"-ldl"' in dry and '"-lc"' in dry,"Original Android default linker libraries not witnessed")
        result["compiler_driver_only_dry_run"]={"executed_linker":False,"compiler":old["NDK"]["compiler"],"source_properties":old["NDK"]["source_properties"]}
        primary=manifest["primary_NDK_driver"]
        with urllib.request.urlopen(primary["url"],timeout=30) as stream:encoded=stream.read(2*1024*1024+1)
        require(len(encoded)<=2*1024*1024,"Primary driver source bound")
        source=base64.b64decode(encoded,validate=True);require(digest(source)=={k:primary[k] for k in ("bytes","sha256")},"Exact pinned primary NDK driver source mismatch")
        text=source.decode();require('if (TC.getTriple().isAndroid() && !Args.hasArg(options::OPT_static) &&' in text and '    CmdArgs.push_back("-ldl");' in text,"Primary Android driver insertion rule changed")
        (out/"Android-clang-d8003-CommonArgs.cpp").write_bytes(source);result["primary_NDK_driver"]=primary
        result["status"]="passed-retained-component-inspection"
    except Exception as exc:
        result["status"]="failed";result["failure"]={"type":type(exc).__name__,"message":str(exc)};raise
    finally:
        result["finished_utc"]=dt.datetime.now(dt.timezone.utc).isoformat();result["manifest"]=pin(MANIFEST)
        result["artifacts"]={p.name:pin(p) for p in sorted(out.iterdir()) if p.is_file()}
        (out/"retained-inspection.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
if __name__=="__main__":main()
