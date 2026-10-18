"""Optional fixed diagnostics from a precreated private source-observer file.

The admitted orchestrator calls precreate BEFORE launching its owned Map child,
then bind with that actual Popen and its two registered log streams. Collection
follows process/handle closure and cleanup attempts. This helper cannot infer a
Map executable's provenance or process-group absence; those remain orchestrator
inputs. A valid probe grants no source, GROUPS, actor or world authority.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib,io,json,os,stat,subprocess
from pathlib import Path

SCHEMA='coh-fresh-source-profile-probe-v2'
PUBLIC_SCHEMA='coh-fresh-source-profile-diagnostic-v2'
MAXIMUM=8192
SOURCE_COUNTER_MAX=65535
PUBLIC_COUNTER_MAX=255
STAGES=('INSTALL','NORMAL_ENABLE','SEAL','BOUNDARY','QUIET','OWNER','OPEN',
 'CATALOG','RUNTIME','RESOURCES','BOUNDS','ELIGIBILITY','PACKET','QUIET_RELEASE','COMMIT','ABORT')
REFUSALS=('NONE','NOT_CONFIGURED','WRONG_THREAD','SEAL_REFUSED','BOUNDARY_REFUSED',
 'FINISH_REFUSED','ABORTED','PROBE_IO')
FOLDER_FAILURES=('NONE','WRONG_THREAD','REENTRY','BAD_UPDATE_MODE','BAD_MANUAL_MODE',
 'QUEUE_NOT_EMPTY','ACTIVE_UPDATE','ACTIVE_CALLBACK','ACTIVE_SETTER','QUEUE_CHANGED',
 'SETTER_CHANGED','ACTIVITY_CHANGED','COUNTER_LIMIT','RESTORE_FAILED','SYNC_FAILED')
OWNER_FAILURES=('NONE',
 'INPUT_LINK','INPUT_OUTPUT','LIST_ABSENT','LIST_EMPTY',
 'LIST_LIMIT','LIST_STORAGE','LIST_CAPACITY','OUTPUT_LINK_ALIAS',
 'OUTPUT_LIST_ALIAS','OUTPUT_ARRAY_ALIAS','OUTPUT_STORAGE_ALIAS','OUTPUT_WORLD_ALIAS',
 'OUTPUT_ENTITIES_MAX_ALIAS','OUTPUT_ENTITY_TABLE_ALIAS','OUTPUT_ENTITY_STATE_ALIAS','CLIENT_ABSENT',
 'CLIENT_BACKLINK','OUTPUT_CLIENT_ALIAS','ENTITY_ABSENT','OUTPUT_ENTITY_ALIAS',
 'ENTITY_BACKLINK','ENTITY_DBID','ENTITY_ID','ENTITY_SLOT_LOW',
 'ENTITY_SLOT_HIGH','ENTITY_TABLE_SIZE_LOW','ENTITY_TABLE_SIZE_HIGH','ENTITY_NOT_IN_USE',
 'ENTITY_TABLE_MISMATCH','CHARACTER_ABSENT','OUTPUT_CHARACTER_ALIAS','CHARACTER_UNINITIALIZED',
 'CHARACTER_PARENT','LINK_TYPE','LINK_NOT_CONNECTED','LINK_PENDING',
 'LINK_CONNECTING','LINK_DISCONNECTED','LINK_DESTROYED','LINK_REMOVED',
 'LINK_PROTOCOL','CLIENT_STATE_LOW','CLIENT_STATE_HIGH','LIST_ENTRY_ABSENT',
 'OUTPUT_LIST_ENTRY_ALIAS','LINK_INCIDENCE','CLIENT_INCIDENCE',
 'INITIAL_SLOT_OUTSIDE_TABLE','INITIAL_STATE','INITIAL_OUTPUT_ENTINFO_ALIAS',
 'INITIAL_NOT_PLAYER','INITIAL_NOT_OWNED','INITIAL_PLAYER_ABSENT',
 'INITIAL_CLIENT_STATE','INITIAL_ENTITY_READY','INITIAL_RELAY','INITIAL_TRANSFER_LOGIN',
 'INITIAL_TRANSFER_ACTIVE','INITIAL_TRANSFER_WAITING','INITIAL_TRANSFER_STEP')
SOURCE_BOOLS=('complete','loader_released','installer_entered','sink_configured',
 'installation_thread_matched','seal_hook_entered','boundary_entered','boundary_accepted',
 'envelope_committed','seal_attempted','sealed','observation_started','observation_finished',
 'restored','owner_thread_matched','queue_empty','queue_writers_idle','update_idle',
 'callbacks_idle','setters_idle','epoch_unchanged','diagnostic_only',
 'source_generation_admitted','world_authority')
COUNTERS=('queue_count','queue_write_depth','update_depth','callback_depth','setter_depth','activity_epoch')
ENUMS={'stage':STAGES,'refusal':REFUSALS,'folder_failure':FOLDER_FAILURES,'owner_failure':OWNER_FAILURES}
SOURCE_KEYS=frozenset(('schema','loader_status',*ENUMS,*SOURCE_BOOLS,*COUNTERS))
CONTEXT_BOOLS=('process_started','process_closed','handles_closed','cleanup_attempted','probe_validated','counter_saturated')

class ProbeRefused(ValueError):pass
def require(value,code='PROBE_REFUSED'):
 if not value:raise ProbeRefused(code)
def _key(info):return info.st_dev,info.st_ino,info.st_uid
def _fingerprint(info):
 return (*_key(info),info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
def _file(info,key=None):
 require(stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode)==0o600
  and info.st_uid==os.geteuid() and info.st_nlink==1 and (key is None or _key(info)==key))
def _directory(info,key=None):
 require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode)==0o700
  and info.st_uid==os.geteuid() and (key is None or _key(info)==key))
def _parent(path,key=None):
 descriptor=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
 try:_directory(os.fstat(descriptor),key)
 except BaseException:
  os.close(descriptor);raise
 return descriptor
@dataclass(frozen=True,slots=True)
class _Binding:
 child:subprocess.Popen
 pid:int
 streams:tuple
 stream_keys:tuple
 children:object
 handles:object
@dataclass(slots=True)
class ProbeOwner:
 path:Path
 parent_key:tuple
 file_key:tuple
 binding:_Binding|None=None

def _rollback(path,parent_key,file_key):
 """Never remove a replacement, symlink or another owner's file."""
 descriptor=None
 try:
  descriptor=_parent(path.parent,parent_key)
  info=os.stat(path.name,dir_fd=descriptor,follow_symlinks=False)
  require(stat.S_ISREG(info.st_mode) and _key(info)==file_key and info.st_uid==os.geteuid() and info.st_nlink==1)
  os.unlink(path.name,dir_fd=descriptor)
 except Exception:pass
 finally:
  if descriptor is not None:
   try:os.close(descriptor)
   except OSError:pass

def precreate(path):
 """Create a fresh private empty regular file; return only after both FDs close.

 No file descriptor remains open while the original Win32 emitter opens the
 same file with OPEN_EXISTING. The immediate private parent is latched too.
 """
 parent_fd=file_fd=None;parent_key=file_key=None;error=None;result=None
 try:
  path=Path(path).absolute();require(path.name not in ('','.', '..'),'PROBE_PRECREATE_REFUSED')
  parent_fd=_parent(path.parent);parent_key=_key(os.fstat(parent_fd))
  file_fd=os.open(path.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=parent_fd)
  file_key=_key(os.fstat(file_fd));os.fchmod(file_fd,0o600)
  info=os.fstat(file_fd);_file(info,file_key);require(info.st_size==0)
  os.fsync(file_fd);result=ProbeOwner(path,parent_key,file_key)
 except Exception as caught:error=caught
 finally:
  # Attempt every close even when an earlier close fails.
  for descriptor in (file_fd,parent_fd):
   if descriptor is not None:
    try:os.close(descriptor)
    except OSError as caught:
     if error is None:error=caught
 if error is not None:
  if file_key is not None and parent_key is not None:_rollback(path,parent_key,file_key)
  raise ProbeRefused('PROBE_PRECREATE_REFUSED') from None
 return result

def _path_info(owner):
 descriptor=_parent(owner.path.parent,owner.parent_key)
 try:
  info=os.stat(owner.path.name,dir_fd=descriptor,follow_symlinks=False);_file(info,owner.file_key)
  require(0<=info.st_size<MAXIMUM);return info
 finally:os.close(descriptor)
def bind(owner,child,streams,children,handles):
 """Atomically bind the actual registered Popen and its two open log streams.

 The caller admits launch ordering, executable identity and the owned process
 groups separately. Failed bind leaves this owner unbound and the file intact.
 """
 try:
  require(type(owner) is ProbeOwner and owner.binding is None)
  require(isinstance(child,subprocess.Popen) and type(child.pid) is int and child.pid>0
   and any(child is item for item in children))
  streams=tuple(streams);require(len(streams)==2 and streams[0] is not streams[1])
  keys=[]
  for stream in streams:
   require(isinstance(stream,io.IOBase) and not stream.closed and any(stream is item for item in handles))
   info=os.fstat(stream.fileno());_file(info);keys.append(_key(info))
  require(len(set(keys))==2 and owner.file_key not in keys);_path_info(owner)
  owner.binding=_Binding(child,child.pid,streams,tuple(keys),children,handles)
 except Exception:raise ProbeRefused('PROBE_BIND_REFUSED') from None

def _pairs(rows):
 value={}
 for name,item in rows:require(name not in value);value[name]=item
 return value
def parse(raw):
 """Admit exactly the fresh v2 emitter's fixed 36-key typed value."""
 try:
  require(type(raw) is bytes and 0<len(raw)<MAXIMUM)
  value=json.loads(raw.decode('ascii'),object_pairs_hook=_pairs,
   parse_constant=lambda _:require(False))
  require(type(value) is dict and set(value)==SOURCE_KEYS and value['schema']==SCHEMA)
  for name in SOURCE_BOOLS:require(type(value[name]) is bool)
  require(value['diagnostic_only'] is True and value['source_generation_admitted'] is False and value['world_authority'] is False)
  for name,choices in ENUMS.items():require(type(value[name]) is str and value[name] in choices)
  require(type(value['loader_status']) is int and 0<=value['loader_status']<=8)
  for name in COUNTERS:require(type(value[name]) is int and 0<=value[name]<=SOURCE_COUNTER_MAX)
  for flag,count in [('queue_empty','queue_count'),('queue_writers_idle','queue_write_depth'),
    ('update_idle','update_depth'),('callbacks_idle','callback_depth'),('setters_idle','setter_depth')]:
   require(value[flag]==(value[count]==0))
  return {'schema':SCHEMA,**{name:value[name] for name in (*SOURCE_BOOLS,*ENUMS,'loader_status',*COUNTERS)}}
 except Exception:raise ProbeRefused('PROBE_PARSE_REFUSED') from None
def empty():
 return {'schema':PUBLIC_SCHEMA,'probe_state':'UNAVAILABLE',**{name:False for name in CONTEXT_BOOLS},
  **{name:False for name in SOURCE_BOOLS},**{name:'UNAVAILABLE' for name in ENUMS},
  'loader_status':None,**{name:0 for name in COUNTERS},'diagnostic_only':True,
  'source_generation_admitted':False,'world_authority':False}
def public(value):
 """Validate then reconstruct every public field; never serialize input dicts."""
 try:
  require(type(value) is dict and set(value)==set(empty()) and value['schema']==PUBLIC_SCHEMA)
  require(type(value['probe_state']) is str and value['probe_state'] in ('VALID','UNAVAILABLE','REFUSED'))
  for name in (*CONTEXT_BOOLS,*SOURCE_BOOLS):require(type(value[name]) is bool)
  require(value['diagnostic_only'] is True and value['source_generation_admitted'] is False and value['world_authority'] is False)
  for name in COUNTERS:require(type(value[name]) is int and 0<=value[name]<=PUBLIC_COUNTER_MAX)
  if value['probe_state']=='VALID':
   require(all(value[name] for name in ('process_started','process_closed','handles_closed','cleanup_attempted','probe_validated')))
   for name,choices in ENUMS.items():require(type(value[name]) is str and value[name] in choices)
   require(type(value['loader_status']) is int and 0<=value['loader_status']<=8)
  else:
   require(value['probe_validated'] is False and value['counter_saturated'] is False and value['loader_status'] is None)
   for name in ENUMS:require(type(value[name]) is str and value[name]=='UNAVAILABLE')
   for name in COUNTERS:require(value[name]==0)
   for name in SOURCE_BOOLS:require(value[name]==(name=='diagnostic_only'))
  return {'schema':PUBLIC_SCHEMA,'probe_state':value['probe_state'],
   **{name:value[name] for name in CONTEXT_BOOLS},**{name:value[name] for name in SOURCE_BOOLS},
   **{name:value[name] for name in ENUMS},'loader_status':value['loader_status'],**{name:value[name] for name in COUNTERS}}
 except Exception:raise ProbeRefused('PROBE_PUBLIC_REFUSED') from None
def _read_fd(descriptor):
 chunks=[];total=0
 while True:
  block=os.read(descriptor,MAXIMUM-total)
  if not block:break
  total+=len(block);require(total<MAXIMUM);chunks.append(block)
 return b''.join(chunks)
def _read_owned(owner):
 parent_fd=_parent(owner.path.parent,owner.parent_key)
 try:
  before=os.stat(owner.path.name,dir_fd=parent_fd,follow_symlinks=False);_file(before,owner.file_key)
  require(0<=before.st_size<MAXIMUM)
  descriptor=os.open(owner.path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC,dir_fd=parent_fd)
  try:
   opened=os.fstat(descriptor);_file(opened,owner.file_key);require(_fingerprint(opened)==_fingerprint(before))
   raw=_read_fd(descriptor);os.lseek(descriptor,0,os.SEEK_SET);again=_read_fd(descriptor)
   after=os.fstat(descriptor);_file(after,owner.file_key)
   require(raw==again and len(raw)==after.st_size and _fingerprint(after)==_fingerprint(before))
   named=os.stat(owner.path.name,dir_fd=parent_fd,follow_symlinks=False);_file(named,owner.file_key)
   require(_fingerprint(named)==_fingerprint(after))
   require(_fingerprint(_path_info(owner))==_fingerprint(after))
   return raw
  finally:os.close(descriptor)
 finally:os.close(parent_fd)
def _closed(owner,child):
 binding=owner.binding;require(binding is not None and child is binding.child and child.pid==binding.pid
  and any(child is item for item in binding.children) and child.poll() is not None)
 require(all(stream.closed and any(stream is item for item in binding.handles) for stream in binding.streams))

def collect(owner,child,*,cleanup_attempted=False):
 """Optional post-cleanup diagnostic. Returns (fixed public, private or None).

 Unavailable or malformed diagnostics never decide GROUPS/pair/cleanup success.
 The private binding must remain private; only public(result) is exportable.
 """
 result=empty();private=None
 result['cleanup_attempted']=cleanup_attempted is True
 result['process_started']=child is not None
 try:
  if isinstance(child,subprocess.Popen):result['process_closed']=child.poll() is not None
  if owner is None:return public(result),None
  require(type(owner) is ProbeOwner)
  if owner.binding is None and child is None:return public(result),None
  require(owner.binding is not None)
  result['handles_closed']=all(stream.closed for stream in owner.binding.streams)
  require(type(cleanup_attempted) is bool and cleanup_attempted);_closed(owner,child)
  raw=_read_owned(owner)
  if not raw:return public(result),None
  value=parse(raw);_closed(owner,child)
  require(_read_owned(owner)==raw)
  result.update({name:value[name] for name in (*SOURCE_BOOLS,*ENUMS,'loader_status')})
  result.update({name:min(value[name],PUBLIC_COUNTER_MAX) for name in COUNTERS})
  result['counter_saturated']=any(value[name]>PUBLIC_COUNTER_MAX for name in COUNTERS)
  result['probe_state']='VALID';result['probe_validated']=True
  private={'schema':'coh-private-fresh-source-profile-binding-v1','owned_child_pid':owner.binding.pid,
   'file_device':owner.file_key[0],'file_inode':owner.file_key[1],'file_uid':owner.file_key[2],
   'probe_bytes':len(raw),'probe_sha256':hashlib.sha256(raw).hexdigest(),
   'source_counters':{name:value[name] for name in COUNTERS},
   'same_precreated_single_link_file_verified':True,'same_owned_closed_child_and_streams_verified':True,
   'probe_bytes_unchanged':True,'public_upload_permitted':False}
  return public(result),private
 except Exception:
  refused=empty();refused.update({name:result[name] for name in ('process_started','process_closed','handles_closed','cleanup_attempted')})
  refused['probe_state']='REFUSED';return public(refused),None
