"""Fixed native child diagnostics, never a packet/owner/authority receipt."""
from __future__ import annotations
import os,re,stat
import delivery as d
STDOUT_MAX=16*1024
SCHEMA='coh-local-initial-capture-status-v2'
LEGACY_SCHEMA='coh-local-initial-capture-status-v1'
PUBLIC_SCHEMA='coh-native-source-diagnostic-v2'
FAILURES=('NONE','INPUT','OWNER','PROTOCOL','GROUPS','REQUEST','COMMAND','HEADER',
 'OBSERVER','RELEASE','TIMEOUT','CANCELLED','MEMORY')
ENUMS={
 'CohStatus':('native-android/engine/coh_contracts.h',('COH_OK','COH_INVALID','COH_UNSUPPORTED','COH_NOT_FOUND','COH_LIMIT','COH_CANCELLED','COH_IO','COH_STATE')),
 'CohLocalPhase':('native-android/engine/local/coh_local.h',('COH_LOCAL_IDLE','COH_LOCAL_DB_CONNECTING','COH_LOCAL_CHARACTERS_READY','COH_LOCAL_MAP_CONNECTING','COH_LOCAL_SCENE_INCOMPLETE','COH_LOCAL_CLOSED','COH_LOCAL_SUSPENDED','COH_LOCAL_CANCELLED','COH_LOCAL_FAILED','COH_LOCAL_TIMED_OUT','COH_LOCAL_UNSUPPORTED')),
 'CohDbSessionPhase':('native-android/engine/dbclient/coh_db_session.h',('COH_DB_IDLE','COH_DB_CONNECTING','COH_DB_WAIT_PLAYERS','COH_DB_QUEUED','COH_DB_CHARACTERS','COH_DB_WAIT_MAP','COH_DB_HANDOFF_READY','COH_DB_DISCONNECTING','COH_DB_SUSPENDED','COH_DB_CLOSED','COH_DB_FAILED','COH_DB_CANCELLED','COH_DB_TIMED_OUT')),
 'CohMapPhase':('native-android/engine/mapclient/coh_mapclient.h',('COH_MAP_IDLE','COH_MAP_NET_CONNECTING','COH_MAP_WAIT_CONNECT','COH_MAP_WAIT_SHORTCUTS','COH_MAP_WAIT_SCENE','COH_MAP_SCENE_INCOMPLETE','COH_MAP_DISCONNECTING','COH_MAP_CLOSED','COH_MAP_SUSPENDED','COH_MAP_TIMED_OUT','COH_MAP_FAILED'))}
COMMAND_SOURCE_LF_SHA256={
 'Common/comm_game.h':'ee8af9fbe23a1e83f4fcf8e1289c29751befbb544178cb9a34bd84b97f3d9a12',
 'libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h':'116b3c4a4d4319893ddc0cd75a60722ec58c96a3dc066a74b1b92e12d925aea9'}
COMMAND_MAP='native-android/engine/initial-capture/coh_initial_command_kinds.inc'
COMMAND_PINS='native-android/engine/initial-capture/command-source-pins.json'
COMMAND_SOURCE_PATHS=tuple(sorted((COMMAND_MAP,COMMAND_PINS,
 *('upstream/ouroboros/'+name for name in COMMAND_SOURCE_LF_SHA256))))
ENUM_SOURCE_PATHS=tuple(sorted({value[0] for value in ENUMS.values()}|set(COMMAND_SOURCE_PATHS)))
FALSE=('source_generation_admitted','complete_initial_character','actor_publication','ack_permitted','world_authority')
BOOLS=('passed','initial_packet_observed','groups_observed','terminal_failure')
KEYS=frozenset(('schema','status','opened_sockets','closed_sockets','diagnostic_failure_code',
 'reqallents_sent','local_phase','terminal_db_phase','terminal_map_phase',
 'refused_command_valid','refused_command_kind',*FALSE,*BOOLS))
PUBLIC_BOOLS=('process_started','stdout_validated','groups_observed','initial_packet_observed',
 'native_groups_result_passed','terminal_failure','native_sockets_closed',
 'source_capture_checked','source_capture_present','source_partial_present')
def require(value):d.require(value,'NATIVE_STATUS_REFUSED')
def command_names(root):
    texts={}
    for name,expected in COMMAND_SOURCE_LF_SHA256.items():
        raw=d.read(root/('upstream/ouroboros/'+name),1024**2).replace(b'\r\n',b'\n')
        require(d.digest(raw)==expected);texts[name]=re.sub(r'/\*.*?\*/|//[^\n]*','',raw.decode('ascii'),flags=re.S)
    require(len(re.findall(r'\bCOMM_MAX_CMD\s*=\s*2\s*,',texts['libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h']))==1)
    matches=re.findall(r'typedef\s+enum\s+ServerCommCmd\s*\{([^}]+)\}\s*ServerCommCmd\s*;',texts['Common/comm_game.h'])
    require(len(matches)==1 and re.fullmatch(r'\s*SERVER_UPDATE\s*=\s*COMM_MAX_CMD\s*,(?:\s*SERVER_[A-Z0-9_]+\s*,)+\s*',matches[0]))
    names=re.findall(r'\bSERVER_[A-Z0-9_]+\b',matches[0]);require(len(names)==232 and names[-1]=='SERVER_CMD_COUNT' and len(set(names))==len(names))
    return tuple(names[:-1])
# Names originate only in this exact pinned source enum, never a runtime name.
COMMAND_NAMES=command_names(d.ROOT)
def verify_commands(root):
    frozen={name:d.read(root/name,1024**2) for name in COMMAND_SOURCE_PATHS}
    names=command_names(root);require(names==COMMAND_NAMES)
    manifest=d.json_object(frozen[COMMAND_PINS])
    require(set(manifest)=={'schema','sha256_lf'} and type(manifest['schema']) is int and manifest['schema']==1
        and manifest['sha256_lf']==COMMAND_SOURCE_LF_SHA256)
    raw=frozen[COMMAND_MAP];clean=re.sub(r'/\*.*?\*/|//[^\n]*','',raw.decode('ascii'),flags=re.S)
    rows=[]
    for line in clean.splitlines():
        if not line.strip():continue
        match=re.fullmatch(r'\s*COH_INITIAL_CAPTURE_COMMAND\((SERVER_[A-Z0-9_]+),\s*([0-9]+)\)\s*',line)
        require(match is not None);rows.append((match[1],int(match[2])))
    require(rows==list(zip(names,range(2,2+len(names)))))
    require(all(d.read(root/name,1024**2)==raw for name,raw in frozen.items()))
    return {name:d.digest(raw) for name,raw in frozen.items()}
def verify_enums(root):
    pins={}
    for typename,(name,expected) in ENUMS.items():
        raw=d.read(root/name,1024**2);text=raw.decode('ascii')
        text=re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)
        matches=re.findall(r'typedef\s+enum\s*\{([^}]+)\}\s*'+re.escape(typename)+r'\s*;',text)
        require(len(matches)==1);actual=[];value=-1
        for field in matches[0].split(','):
            item=re.fullmatch(r'\s*([A-Za-z_][A-Za-z_0-9]*)\s*(?:=\s*([0-9]+))?\s*',field)
            require(item is not None);value=int(item[2]) if item[2] is not None else value+1
            actual.append((item[1],value))
        require(actual==list(zip(expected,range(len(expected)))));pins[name]=d.digest(raw)
    pins.update(verify_commands(root));return pins
def empty():
    return {'schema':PUBLIC_SCHEMA,**{name:False for name in PUBLIC_BOOLS},
        'exit_code':'UNEXPECTED','stdout_state':'UNAVAILABLE','diagnostic_failure_code':'UNAVAILABLE',
        'coh_status':None,'local_phase':None,'terminal_db_phase':None,'terminal_map_phase':None,
        'reqallents_sent':0,'refused_command_valid':False,'refused_command_kind':'NONE',
        'source_generation_admitted':False,'actor_publication':False,
        'ack_permitted':False,'world_authority':False}
def public(value):
    # Validate then reconstruct the ENTIRE allowlist; never copy raw dictionaries.
    require(type(value) is dict)
    legacy=value.get('schema')=='coh-native-source-diagnostic-v1'
    require(set(value)==set(empty())-({'refused_command_valid','refused_command_kind'} if legacy else set())
        and value.get('schema')==('coh-native-source-diagnostic-v1' if legacy else PUBLIC_SCHEMA))
    for name in PUBLIC_BOOLS:require(type(value.get(name)) is bool)
    require((type(value['exit_code']) is int and value['exit_code'] in (0,1,2)) or value['exit_code']=='UNEXPECTED')
    require(value['stdout_state'] in ('UNAVAILABLE','REFUSED','VALID'))
    d.uint(value['reqallents_sent'],1)
    for name in ('source_generation_admitted','actor_publication','ack_permitted','world_authority'):require(value.get(name) is False)
    if value['stdout_state']=='VALID':
        require(value['process_started'] and value['stdout_validated']
            and type(value['diagnostic_failure_code']) is str and value['diagnostic_failure_code'] in FAILURES)
        for name,maximum in (('coh_status',7),('local_phase',10),('terminal_db_phase',12),('terminal_map_phase',10)):d.uint(value[name],maximum)
    else:
        require(value['stdout_validated'] is False and value['diagnostic_failure_code']=='UNAVAILABLE'
            and all(value[name] is None for name in ('coh_status','local_phase','terminal_db_phase','terminal_map_phase'))
            and value['reqallents_sent']==0 and all(value[name] is False for name in
            ('groups_observed','initial_packet_observed','native_groups_result_passed','terminal_failure','native_sockets_closed')))
    if value['process_started'] is False:require(value['exit_code']=='UNEXPECTED' and value['stdout_state']=='UNAVAILABLE')
    if value['source_capture_checked'] is False:require(value['source_capture_present'] is False and value['source_partial_present'] is False)
    if legacy:
        result=empty()
        for name in ('process_started','exit_code','source_capture_checked','source_capture_present','source_partial_present'):result[name]=value[name]
        return result
    require(type(value['refused_command_valid']) is bool and type(value['refused_command_kind']) is str
        and ((value['refused_command_valid'] is False and value['refused_command_kind']=='NONE')
        or (value['refused_command_valid'] is True and value['refused_command_kind'] in ('UNKNOWN',*COMMAND_NAMES))))
    if value['stdout_state']!='VALID':require(value['refused_command_valid'] is False)
    return {'schema':PUBLIC_SCHEMA,
        **{name:value[name] for name in PUBLIC_BOOLS},'exit_code':value['exit_code'],
        'stdout_state':value['stdout_state'],'diagnostic_failure_code':value['diagnostic_failure_code'],
        'coh_status':value['coh_status'],'local_phase':value['local_phase'],
        'terminal_db_phase':value['terminal_db_phase'],'terminal_map_phase':value['terminal_map_phase'],
        'reqallents_sent':value['reqallents_sent'],'refused_command_valid':value['refused_command_valid'],
        'refused_command_kind':value['refused_command_kind'],'source_generation_admitted':False,
        'actor_publication':False,'ack_permitted':False,'world_authority':False}
def parse(raw):
    require(type(raw) is bytes and 0<len(raw)<=STDOUT_MAX);value=d.json_object(raw)
    legacy=value.get('schema')==LEGACY_SCHEMA
    require(set(value)==KEYS-({'refused_command_valid','refused_command_kind'} if legacy else set()) and value.get('schema')==(LEGACY_SCHEMA if legacy else SCHEMA))
    for name in BOOLS:require(type(value.get(name)) is bool)
    for name in FALSE:require(value.get(name) is False)
    require(type(value['diagnostic_failure_code']) is str and value['diagnostic_failure_code'] in FAILURES)
    for name,maximum in (('status',7),('local_phase',10),('terminal_db_phase',12),('terminal_map_phase',10),
        ('reqallents_sent',1),('opened_sockets',2),('closed_sockets',2)):d.uint(value[name],maximum)
    if legacy:return None
    result=empty();result.update(process_started=True,stdout_validated=True,stdout_state='VALID',
        groups_observed=value['groups_observed'],initial_packet_observed=value['initial_packet_observed'],
        native_groups_result_passed=value['passed'],terminal_failure=value['terminal_failure'],
        native_sockets_closed=value['opened_sockets']==value['closed_sockets'],
        diagnostic_failure_code=value['diagnostic_failure_code'],coh_status=value['status'],
        local_phase=value['local_phase'],terminal_db_phase=value['terminal_db_phase'],
        terminal_map_phase=value['terminal_map_phase'],reqallents_sent=value['reqallents_sent'],
        refused_command_valid=value['refused_command_valid'],refused_command_kind=value['refused_command_kind'])
    return public(result)
def file_key(info):return info.st_dev,info.st_ino,info.st_uid
def owned_file(path,expected=None):
    path=d.regular(path);info=path.stat()
    require(info.st_uid==os.geteuid() and not info.st_mode&0o077 and stat.S_ISREG(info.st_mode)
        and info.st_nlink==1 and (expected is None or file_key(info)==expected))
    return path,info
def latch(child,path,stream,children,handles):
    require(any(child is item for item in children) and any(stream is item for item in handles)
        and type(child.pid) is int and child.pid>0 and not stream.closed)
    info=os.fstat(stream.fileno());path,_=owned_file(path,file_key(info))
    return {'child':child,'pid':child.pid,'path':path,'stream':stream,'key':file_key(info)}
def source_presence(path):
    if path is None:return False,False,False
    def present(value):
        try:value.lstat();return True
        except FileNotFoundError:return False
    try:return True,present(path),present(path.with_name(path.name+'.partial'))
    except OSError:return False,False,False
def collect(child,owner,children,source_capture,initial_role,root):
    result=empty();result['process_started']=child is not None
    if child is not None:
        try:code=child.poll()
        except Exception:code=None
        result['exit_code']=code if type(code) is int and code in (0,1,2) else 'UNEXPECTED'
    result['source_capture_checked'],result['source_capture_present'],result['source_partial_present']=source_presence(source_capture)
    if not initial_role or child is None:return public(result),None
    private=None;base=dict(result)
    try:
        require(owner is not None and owner['child'] is child and owner['pid']==child.pid
            and any(child is item for item in children) and child.poll() is not None and owner['stream'].closed)
        path,info=owned_file(owner['path'],owner['key'])
        require(0<info.st_size<=STDOUT_MAX);before=d.hash_file(path,STDOUT_MAX)
        raw=d.read(path,STDOUT_MAX);parsed=parse(raw)
        path,after=owned_file(path,owner['key']);require(d.hash_file(path,STDOUT_MAX)==before
            and (len(raw),d.digest(raw))==before and after.st_size==info.st_size)
        owned_file(path,owner['key'])
        if parsed is None:return public(base),None
        enum_pins=verify_enums(root)
        owned_file(path,owner['key']);require(d.hash_file(path,STDOUT_MAX)==before)
        owned_file(path,owner['key'])
        parsed.update(exit_code=result['exit_code'],source_capture_checked=result['source_capture_checked'],
            source_capture_present=result['source_capture_present'],source_partial_present=result['source_partial_present'])
        result=public(parsed)
        private={'schema':'coh-private-native-stdout-binding-v1','owned_child_pid':owner['pid'],
            'file_device':owner['key'][0],'file_inode':owner['key'][1],'file_uid':owner['key'][2],
            'stdout_bytes':before[0],'stdout_sha256':before[1],'enum_source_sha256':enum_pins,
            'same_owned_closed_child_and_stdout_verified':True,'stdout_bytes_unchanged':True,
            'public_upload_permitted':False}
    except Exception:result=base;result['stdout_state']='REFUSED';private=None
    return public(result),private
def record(report,child,owner,children,source_capture,initial_role,root):
    # Diagnostics remain optional to the unchanged GROUPS admission. Even a
    # diagnostic filesystem/dependency failure cannot discard an accepted pair.
    try:result,private=collect(child,owner,children,source_capture,initial_role,root)
    except Exception:
        result=empty();result['process_started']=child is not None
        if child is not None:
            result['stdout_state']='REFUSED' if initial_role else 'UNAVAILABLE'
            try:
                code=child.poll();result['exit_code']=code if type(code) is int and code in (0,1,2) else 'UNEXPECTED'
            except Exception:pass
        private=None
    report['native_diagnostic']=public(result)
    if private is not None:report['private_native_stdout']=private
    else:report.pop('private_native_stdout',None)
