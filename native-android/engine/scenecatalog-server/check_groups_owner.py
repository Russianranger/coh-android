#!/usr/bin/env python3
"""Read-only original producer owner chain preparation, no source hook or server."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,tempfile,types,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
FILES=['MapServer/src/player/clientEntityLink.c','MapServer/src/svr/svr_tick.c','MapServer/src/svr/svr_base.h','MapServer/src/svr/svr_base.c','MapServer/src/group/groupnetsend.c','MapServer/src/entity/entIncludeServer.h','MapServer/src/entity/entserver.c','Common/entity/entity.h','Common/entity/entity.c','Common/entity/character_base.h','Common/entity/gametypes.h','libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h','libs/UtilitiesLib/src/network/net_version.c','libs/UtilitiesLib/include/utilitieslib/components/ArrayOld.h']
def sha(b):return hashlib.sha256(b).hexdigest()
def original(path):return subprocess.run(['git','show','HEAD:upstream/ouroboros/'+path],cwd=ROOT,capture_output=True,check=True).stdout.decode().replace('\r\n','\n')
def run(args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=180,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
def admit(paths):
 return {path:path.read_bytes() for path in paths}
def unchanged(admitted):
 if any(path.read_bytes()!=data for path,data in admitted.items()):raise RuntimeError('qualification source changed')
def execute_admitted(path,admitted):
 unchanged(admitted)
 module=types.ModuleType('owner_original_extract');module.__file__=str(path)
 try:exec(compile(admitted[path],str(path),'exec'),module.__dict__)
 finally:unchanged(admitted)
 return module
def source_guard_controls(directory):
 # Only owned temporary files are mutated; the real admitted project is untouched.
 path=directory/'helper.py';other=directory/'dependency.h';other.write_bytes(b'first')
 path.write_bytes(b'value=17\n');admitted=admit([path,other])
 assert execute_admitted(path,admitted).value==17
 other.write_bytes(b'changed')
 try:execute_admitted(path,admitted)
 except RuntimeError:pass
 else:raise AssertionError('pre-execution dependency mutation accepted')
 other.write_bytes(b'first');path.write_bytes(b'value=99\n')
 try:execute_admitted(path,admitted)
 except RuntimeError:pass
 else:raise AssertionError('pre-execution helper mutation accepted')
 # Mutation made by admitted code itself must refuse after execution.
 path.write_bytes(b'from pathlib import Path\nPath(__file__).write_bytes(b"changed")\n')
 admitted=admit([path,other])
 try:execute_admitted(path,admitted)
 except RuntimeError:pass
 else:raise AssertionError('during-execution mutation accepted')
 path.write_bytes(b'value=17\n');admitted=admit([path,other]);execute_admitted(path,admitted)
 other.write_bytes(b'late')
 try:unchanged(admitted)
 except RuntimeError:pass
 else:raise AssertionError('final dependency mutation accepted')
 return 5
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
helperpath=HERE.parent/'replication/groups_oracle.py';pinfile=HERE/'groups-owner-source-pins.json'
paths=[Path(__file__),pinfile,helperpath,HERE/'groups_owner_oracle_shim.h',HERE/'test_groups_owner.c',HERE/'source_groups_owner.inc',HERE/'GROUPS_OWNER.md']
# Admit the complete local closure before executing any project helper.
admitted=admit(paths);frozen={str(path.relative_to(ROOT)):sha(data) for path,data in admitted.items()}
sources={n:original(n) for n in FILES}
assert json.loads(admitted[pinfile])['original_sha256_lf']=={n:sha(data.encode()) for n,data in sources.items()}
helper=execute_admitted(helperpath,admitted)
functions={}
for name,path in [('clientSetEntity',FILES[0]),('svrHandleClientMsg',FILES[1]),('worldSendUpdate',FILES[4]),('character_IsInitialized','Common/entity/character_base.h'),('entInUse','Common/entity/entity.c'),('applyNetworkVersionToLink','libs/UtilitiesLib/src/network/net_version.c')]:functions[name]={'source':path,'sha256_lf':sha(helper.extract(sources[path],name).encode())}
# Extract complete original declarations by their exact source terminator.
def decl(path,start,end):
 s=sources[path];at=s.index(start);finish=s.index(end,at)+len(end);return s[at:finish]+'\n'
types_used={'Array':decl(FILES[-1],'typedef struct Array{','} Array;'),'ClientReadyState':decl(FILES[2],'typedef enum ClientReadyState','} ClientReadyState;'),'ClientLink':decl(FILES[2],'typedef struct ClientLink','} ClientLink;'),'NetLinkType':decl(FILES[11],'typedef enum NetLinkType','} NetLinkType;'),'NetLinkOperationType':decl(FILES[11],'typedef enum NetLinkOperationType','} NetLinkOperationType;'),'DbFlag':decl('Common/entity/gametypes.h','typedef enum DbFlag','} DbFlag;')}
for path,patterns in {'Common/entity/entity.h':[r'\bint\s+owner\s*;',r'\bU32\s+id\s*;',r'\bint\s+db_id\s*;',r'\bU32\s+auth_id\s*;',r'\bCharacter\s*\*\s*pchar\s*;',r'extern Entity\*\s+entities\[\]\s*;',r'extern U8\s+entity_state\[\]\s*;'],'MapServer/src/entity/entIncludeServer.h':[r'ClientLink\*\s+client\s*;',r'U8\s+ready\s*:\s*1\s*;'],'Common/entity/character_base.h':[r'Entity\s*\*entParent\s*;',r'const CharacterClass\s*\*pclass\s*;']}.items():
 for pattern in patterns:assert re.search(pattern,sources[path]),(path,pattern)
net=sources['libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h']
for name in ['UID','protocolVersion','connection_id','connect_id','last_update_time','last_processed_id','last_recv_id','last_ordered_recv_id']:
 assert re.search(r'\bU32\s+'+name+r'\s*;',net),name
for name in ['connected','pending','connecting','disconnected','destroyed','removedFromMasterList','compressionAllowed','compressionDefault','orderedAllowed','orderedDefault','controlCommandsSeparate','cookieSend','cookieEcho']:
 assert re.search(r'\bU32\s+'+name+r'\s*:\s*1\s*;',net),name
for pattern in [r'NetLinkType\s+type\s*;',r'NetLinkOperationType\s+opType\s*;',r'void\s*\*\s*userData\s*;',r'int\s+last_world_id\s*;',r'Array\s*\*\s*links\s*;']:
 assert re.search(pattern,net),pattern
maxdef=re.search(r'^#define MAX_ENTITIES_PRIVATE\s+\d+[^\n]*',sources['Common/entity/gametypes.h'],re.M).group(0)
entityinuse=re.search(r'^#define ENTITY_IN_USE\s+\([^\n]+',sources['Common/entity/entity.h'],re.M).group(0)
beingfreed=re.search(r'^#define ENTITY_BEING_FREED\s+\([^\n]+',sources['Common/entity/entity.h'],re.M).group(0)
positions='\n'.join(re.search(r'^\s*#define '+name+r'\([^\n]+',sources['MapServer/src/entity/entIncludeServer.h'],re.M).group(0) for name in ['ENTPOS_BY_ID','ENTPOS'])+'\n'
handler=helper.extract(sources[FILES[1]],'svrHandleClientMsg');scene=handler[handler.index('        xcase CLIENT_REQSCENE:'):handler.index('        xcase CLIENT_REQALLENTS:')]
ms=scene.index('                for(i = 0;');me=scene.index('                if (!pktEnd(pak))');membership=scene[ms:me]
gs=scene.index('                if (!client->entity ||');ge=scene.index('                if( failed )',gs);guard=scene[gs:ge]
assert 'worldSendUpdate(client->link,1);' in scene and scene.index('worldSendUpdate(client->link,1);')>ge
pins={'schema':'coh-source-owner-pins-v1','original_sha256_lf':{k:sha(v.encode()) for k,v in sources.items()},'original_functions':functions,'original_types_sha256_lf':{k:sha(v.encode()) for k,v in types_used.items()},'reqscene_membership_sha256_lf':sha(membership.encode()),'reqscene_character_guard_sha256_lf':sha(guard.encode()),'source_max_entities_macro':maxdef}
assert json.loads(admitted[pinfile])==pins
modes={};binaries={};stack={}
with tempfile.TemporaryDirectory(prefix='coh-source-owner-') as directory:
 d=Path(directory);sys.pycache_prefix=str(d/'pycache');sys.dont_write_bytecode=True;guard_checks=source_guard_controls(d);unchanged(admitted)
 code=admitted[HERE/'groups_owner_oracle_shim.h'].decode().replace('/* ORIGINAL_TYPES */','\n'.join(types_used[k] for k in ['Array','NetLinkType','NetLinkOperationType','DbFlag'])+'\n'+maxdef+'\n'+entityinuse+'\n'+beingfreed).replace('/* ORIGINAL_CLIENT_LINK */',types_used['ClientReadyState']+types_used['ClientLink']).replace('/* ORIGINAL_POSITION_MACROS */',positions)
 code+='\n'+helper.extract(sources['Common/entity/character_base.h'],'character_IsInitialized')+'\n'+helper.extract(sources['Common/entity/entity.c'],'entInUse')+'\n'+helper.extract(sources[FILES[0]],'clientSetEntity')+'\n'+helper.extract(sources['libs/UtilitiesLib/src/network/net_version.c'],'applyNetworkVersionToLink')
 code+='\nstatic void original_reqscene_membership(ClientLink*client){int i;\n'+membership+'\n}\nstatic int original_reqscene_character(ClientLink*client){int failed=false;\n'+guard+'\nreturn !failed;}\n'+admitted[HERE/'test_groups_owner.c'].decode();(d/'test.c').write_text(code)
 for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  binary=d/mode;run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-fstack-usage',*flags,'-I'+str(HERE),d/'test.c','-o',binary]);modes[mode]=json.loads(run([binary]));binaries[mode]=sha(binary.read_bytes());su=binary.with_name(mode+'-test.su');frames={}
  for line in su.read_text().splitlines():
   loc,size,kind=line.split('\t');name=loc.rsplit(':',1)[-1]
   if 'unbounded' in kind:raise ValueError('unbounded stack frame '+name)
   if name.startswith('coh_source_'):frames[name]=int(size)
  stack[mode]={'frames':frames,'conservative_bytes':sum(frames.values())+4096}
assert pins['original_sha256_lf']=={n:sha(original(n).encode()) for n in FILES};unchanged(admitted);assert all(x==modes['release'] for x in modes.values())
r={'schema':'coh-source-groups-owner-v1','passed':True,'local_sources_admitted_before_project_execution':True,'helper_executed_from_admitted_bytes':True,'source_guard_controls':guard_checks,'source_sha256':frozen,'original':pins,'modes':modes,'binary_sha256':binaries,'stack':stack,'host_member_subset_storage_only':True,'original_win32_layout_qualified':False,'observer_read_only':True,'zero_alloc_observer':True,'hook_installed':False,'live_groups_captured':False,'source_generation_admitted':False,'native_entity_decode_verified':False,'crypto_auth_verified':False,'world_authority':False,'android_executed':False,'real_server_executed':False,'leak_sanitizer':False}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes}))
