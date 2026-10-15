from pathlib import Path
import ctypes as C,json,os,errno
class Root(C.Structure):
 _fields_=[('guest',C.c_char_p),('host',C.c_char_p),('device',C.c_uint64),('inode',C.c_uint64),('uid',C.c_uint32)]
class Error(C.Structure):
 _fields_=[('number',C.c_int),('rows',C.c_uint64),('fallback',C.c_int)]
library,root_name,parent_name,pins_json=os.sys.argv[1:];pins=json.loads(pins_json)
status={a:b.strip() for a,b in [line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line]}
assert os.getuid()==os.geteuid()==pins['uid']
assert all(int(status[k],16)==0 for k in ('CapEff','CapPrm','CapInh'))
assert status['NoNewPrivs']=='1'
before=len(os.listdir('/proc/self/fd'))
try: fd=os.open(parent_name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
except OSError as e: parent_errno=e.errno
else: os.close(fd);raise AssertionError('DAC bypass: parent was readable')
assert parent_errno==errno.EACCES
fd=os.open(root_name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC);os.close(fd)
lib=C.CDLL(library);lib.coh_live_namespace_open.argtypes=[C.POINTER(C.c_void_p),C.POINTER(Root),C.c_size_t,C.c_uint32,C.c_uint32,C.c_int,C.c_int,C.POINTER(Error)]
root=Root(b'/data',os.fsencode(root_name),pins['device'],pins['inode'],pins['uid']);handle=C.c_void_p();error=Error()
opened=bool(lib.coh_live_namespace_open(C.byref(handle),C.byref(root),1,os.getuid(),1000,0,0,C.byref(error)))
assert not opened and not handle.value and (error.number,error.rows,error.fallback)==(errno.EACCES,0,1)
after=len(os.listdir('/proc/self/fd'));assert before==after
print(json.dumps({'namespace_opened':opened,'native_errno':error.number,'rows':error.rows,'fallback':bool(error.fallback),'uid':os.getuid(),'euid':os.geteuid(),'CapEff':status['CapEff'],'CapPrm':status['CapPrm'],'CapInh':status['CapInh'],'NoNewPrivs':status['NoNewPrivs'],'parent_O_RDONLY_errno':parent_errno,'final_known_name_direct_open_succeeded':True,'fd_counts_before_after':[before,after]},sort_keys=True))
