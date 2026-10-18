#!/usr/bin/env python3
"""Qualify only the new fresh pre-entry owner fallback; no old suites/runtime."""
import argparse,ast,hashlib,json,os,re,subprocess,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
MODES={'release':['-O2'],'address':['-O1','-fsanitize=address','-no-pie'],
 'undefined':['-O1','-fsanitize=undefined','-fno-sanitize-recover=all']}
ORIGINALS=('libs/UtilitiesLib/include/utilitieslib/components/ArrayOld.h',
 'MapServer/src/svr/svr_base.h','libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h',
 'Common/entity/gametypes.h','Common/entity/entity.h','Common/entity/entity.c',
 'Common/entity/character_base.h','Common/entity/entity_enum.h',
 'MapServer/src/entity/entIncludeServer.h','MapServer/src/container/containercallbacks.c',
 'MapServer/src/svr/svr_tick.c','MapServer/src/svr/svr_player.c',
 'MapServer/src/player/parseClientInput.c','MapServer/src/entity/entsend.c',
 'MapServer/src/dbcomm/dbmapxfer.c')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def require(value,code):
 if not value:raise ValueError('COH_FRESH_INITIAL_OWNER_QUAL_'+code)
def c_function(text,name):
 match=re.search(r'^[\w \t*]+\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text,re.M)
 require(match is not None,'FUNCTION_'+name);at=text.index('{',match.start())+1;depth=1
 while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[match.start():at]+'\n'
def declaration(text,start,end):
 at=text.index(start);return text[at:text.index(end,at)+len(end)]+'\n'
def function(raw,name):
 text=raw.decode();nodes=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==name]
 require(len(nodes)==1,'PY_FUNCTION_'+name);node=nodes[0]
 return ''.join(text.splitlines(keepends=True)[node.lineno-1:node.end_lineno])
def unchanged(admitted):require(all(p.read_bytes()==raw for p,raw in admitted.items()),'SOURCE_CHANGED')
def tracked(root,name):return subprocess.run(['git','show','HEAD:'+name],cwd=root,check=True,capture_output=True).stdout
def production(admitted):
 base=types.SimpleNamespace();scope={'hashlib':hashlib}
 for name in ('require','sha','lf'):
  exec(compile(function(admitted[HERE.parent/'stage_export.py'],name),'admitted-base','exec'),scope)
  setattr(base,name,scope[name])
 raw=admitted[HERE/'stage.py'];scope={'base':base,'HERE':HERE,'re':re}
 for node in ast.parse(raw.decode()).body:
  if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
   try:scope[node.targets[0].id]=ast.literal_eval(node.value)
   except (ValueError,TypeError):pass
 for name in ('once','owner_predicates','instrument_owner','specialize_initial_owner'):
  exec(compile(function(raw,name),'admitted-stage','exec'),scope)
 unchanged(admitted);return scope
def lifecycle(sources):
 # These are exact original source facts, NOT execution of complete lifecycle
 # functions. Only entInUse/character_IsInitialized execute in the host fixture.
 checks={
 'new_entity_zero_initialized':('Common/entity/entity.c',b'memset(e, 0, sizeof(Entity));'),
 'loaded_player_sleeping':('MapServer/src/container/containercallbacks.c',b'entity_state[ e->owner ] = ENTITY_SLEEPING;'),
 'loaded_owned':('MapServer/src/container/containercallbacks.c',b'playerEntAdd(PLAYER_ENTS_OWNED,e);'),
 'relay_provenance':('MapServer/src/container/containercallbacks.c',b'e->demand_loaded    = ci->demand_loaded;'),
 'transfer_provenance':('MapServer/src/container/containercallbacks.c',b'e->is_map_xfer        = ci->is_map_xfer;'),
 'new_client_not_ready':('MapServer/src/svr/svr_player.c',b'client->ready = CLIENTSTATE_NOT_READY;'),
 'created_player_type':('MapServer/src/svr/svr_player.c',b'SET_ENTTYPE(e) = ENTTYPE_PLAYER;'),
 'owned_flag':('MapServer/src/svr/svr_player.c',b'e->owned = 1;'),
 'released_owned_flag':('MapServer/src/svr/svr_player.c',b'e->owned = 0;'),
 'ready_wakes_player':('MapServer/src/player/parseClientInput.c',b'entity_state[i] = ENTITY_IN_USE;'),
 'sleeping_initial_update':('MapServer/src/entity/entsend.c',b'When the server initially starts sending a game client their entity,'),
 'outgoing_transfer_drops_ownership':('MapServer/src/dbcomm/dbmapxfer.c',b'playerEntDelete(PLAYER_ENTS_OWNED,e,0);')}
 for name,(path,token) in checks.items():require(token in sources[path],'LIFECYCLE_'+name)
 tick=sources['MapServer/src/svr/svr_tick.c'];scene=tick[tick.index(b'xcase CLIENT_REQSCENE:'):tick.index(b'xcase CLIENT_REQALLENTS:')]
 require(scene.index(b'worldSendUpdate(client->link,1);')<scene.index(b'client->ready = CLIENTSTATE_NOT_READY;'),'REQSCENE_ORDER')
 connect=c_function(tick.decode(),'svrHandleClientConnect')
 require('playerEntAdd(PLAYER_ENTS_ACTIVE,client->entity);' in connect and 'entity_state[' not in connect,'CONNECT_NO_WAKE')
 return {name:{'source':path,'exact_token_sha256':sha(token)} for name,(path,token) in checks.items()}
def header(admitted,sources,specialized):
 texts={name:raw.decode() for name,raw in sources.items()}
 types_used=[declaration(texts[path],start,end) for path,start,end in (
  (ORIGINALS[0],'typedef struct Array{','} Array;'),
  (ORIGINALS[2],'typedef enum NetLinkType','} NetLinkType;'),
  (ORIGINALS[2],'typedef enum NetLinkOperationType','} NetLinkOperationType;'),
  (ORIGINALS[3],'typedef enum DbFlag','} DbFlag;'),
  (ORIGINALS[7],'typedef enum EntType','} EntType;'),
  (ORIGINALS[8],'typedef enum MapXferStep','} MapXferStep;'),
  (ORIGINALS[8],'typedef struct DbCommState','} DbCommState;'))]
 types_used.insert(0,'typedef int MapTransferType;\n')
 for name,path in [('MAX_ENTITIES_PRIVATE',ORIGINALS[3]),('ENTITY_IN_USE',ORIGINALS[4]),
                   ('ENTITY_SLEEPING',ORIGINALS[4]),('ENTITY_BEING_FREED',ORIGINALS[4])]:
  types_used.append(re.search(r'^#define '+name+r'\s+[^\n]+',texts[path],re.M)[0]+'\n')
 client=declaration(texts[ORIGINALS[1]],'typedef enum ClientReadyState','} ClientReadyState;')+declaration(texts[ORIGINALS[1]],'typedef struct ClientLink','} ClientLink;')
 shim=admitted[HERE.parent/'groups_owner_oracle_shim.h'].decode();shim=shim[:shim.index('static unsigned checks,position_calls')]
 start=shim.index('struct Entity {');end=shim.index('};',start)+2
 shim=shim[:start]+'''typedef struct Player {unsigned host_opaque;} Player;
struct Entity {int owner;U32 id;int db_id;U32 auth_id;int map_id,static_map_id;ClientLink*client;Character*pchar;DbFlag db_flags;U8 ready:1;U8 owned:1,demand_loaded:1,is_map_xfer:1;Player*pl;DbCommState dbcomm_state;};'''+shim[end:]
 shim=shim[:shim.index('static NetLinkList net_links;')]+'''
typedef struct EntityInfo {EntType type;} EntityInfo;
static struct OwnerGlobals {
 union {NetLinkList value;unsigned char padding[512];} links;
 union {int value;unsigned char padding[512];} world,maximum;
 union {Entity *value[MAX_ENTITIES_PRIVATE];unsigned char padding[sizeof(Entity*)*MAX_ENTITIES_PRIVATE+512];} table;
 union {U8 value[MAX_ENTITIES_PRIVATE];unsigned char padding[MAX_ENTITIES_PRIVATE+512];} state;
 union {EntityInfo value[MAX_ENTITIES_PRIVATE];unsigned char padding[sizeof(EntityInfo)*MAX_ENTITIES_PRIVATE+512];} info;
} owner_globals;
#define net_links owner_globals.links.value
#define world_id owner_globals.world.value
#define entities_max owner_globals.maximum.value
#define entities owner_globals.table.value
#define entity_state owner_globals.state.value
#define entinfo owner_globals.info.value
static unsigned checks,type_reads;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"initial owner control line%d: %s\\n",__LINE__,#x);abort();}}while(0)
/* Type access is instrumented only in HOST storage: same value/identity plus
 * a checked access counter, so bounds/alias refusal precedes a type read. */
static const EntityInfo *observed_entinfo(int index){CHECK(index>=1&&index<entities_max);type_reads++;return &entinfo[index];}
#define ENTINFO_BY_ID(id) (*observed_entinfo(id))
#define ENTINFO(e) ENTINFO_BY_ID((e)->owner)
#define ENTTYPE(e) (ENTINFO(e).type)
#define INLINEDBG inline
'''
 shim=shim.replace('/* ORIGINAL_TYPES */','\n'.join(types_used)).replace('/* ORIGINAL_CLIENT_LINK */',client)
 shim+=c_function(texts[ORIGINALS[6]],'character_IsInitialized')+c_function(texts[ORIGINALS[5]],'entInUse')
 group=admitted[HERE/'source_group_profile.inc'].decode()
 shim+='''
#include "coh_fresh_source_profile_api.h"
typedef int32_t LONG;typedef uint32_t DWORD;
static LONG coh_fp_thread;static DWORD current_thread;
static unsigned coh_fp_entered,coh_fp_complete;
static CohFreshOwnerFailure coh_fp_owner_failure;
static LONG InterlockedCompareExchange(volatile LONG*p,LONG value,LONG expected){LONG old=*p;if(old==expected)*p=value;return old;}
static DWORD GetCurrentThreadId(void){return current_thread;}
'''
 shim+=c_function(group,'coh_fp_owner')
 shim+='#define coh_fresh_source_owner_failed original_latch\n'+c_function(group,'coh_fresh_source_owner_failed')+'#undef coh_fresh_source_owner_failed\n'
 shim+='''static unsigned trace_count,trace_ids[128];
int coh_fresh_source_owner_failed(int value,CohFreshOwnerFailure reason){CHECK(trace_count<128);trace_ids[trace_count++]=(unsigned)reason;return original_latch(value,reason);}
'''
 shim+=declaration(group,'static const char*coh_fp_owner_failures[]','};')
 shim+='#define coh_source_groups_prepare_owner original_prepare\n'+admitted[HERE.parent/'source_groups_owner.inc'].decode()+'\n#undef coh_source_groups_prepare_owner\n'
 shim+=c_function(specialized.decode(),'coh_fresh_source_initial_owner')
 shim+='#define coh_source_groups_prepare_owner fresh_prepare\n'+c_function(specialized.decode(),'coh_source_groups_prepare_owner')+'#undef coh_source_groups_prepare_owner\n'
 return shim.encode()
def process(command,admitted,timeout=120):
 unchanged(admitted);result=subprocess.run(list(map(str,command)),capture_output=True,timeout=timeout,
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
 unchanged(admitted);return result
def compile_run(args,work,admitted,generated,flags,refuse=False):
 work.mkdir(mode=0o700);(work/'initial_owner_fixture.h').write_bytes(generated)
 for target,name in [('test.c','test_initial_owner.c'),('coh_fresh_source_profile_api.h','source_group_profile_api.h'),('coh_fresh_folder_profile_api.h','source_folder_profile_api.h')]:
  (work/target).write_bytes(admitted[HERE/name])
 binary=work/'test-initial-owner';command=[args.cc,'-std=c11','-g','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I',work,work/'test.c','-o',binary]
 built=process(command,admitted);(work/'build.stdout').write_bytes(built.stdout);(work/'build.stderr').write_bytes(built.stderr)
 require(built.returncode==0,'BUILD_'+work.name);raw=binary.read_bytes();tested=process([binary],admitted,30)
 (work/'stdout.json').write_bytes(tested.stdout);(work/'stderr.txt').write_bytes(tested.stderr)
 require(binary.read_bytes()==raw,'BINARY_CHANGED')
 if refuse:require(tested.returncode!=0,'MUTATION_SURVIVED_'+work.name);return {'refused':True,'header_sha256':sha(generated)}
 require(tested.returncode==0 and not tested.stderr,'RUN_'+work.name);value=json.loads(tested.stdout)
 require(value['passed'] is True and value['fallback_guard_refusals']==13 and value['sleeping_successes']==1 and value['unchanged_active_successes']==30,'COUNTS')
 return {'controls':value,'flags':flags,'binary':{'bytes':len(raw),'sha256':sha(raw)},'command':list(map(str,command))}
def parser_controls(admitted,reasons):
 # Execute only the small admitted pure parser dependencies, not its process/
 # file collection methods or any historical test suite.
 raw=admitted[HERE/'probe.py'];scope={'json':json}
 for node in ast.parse(raw.decode()).body:
  if isinstance(node,ast.Assign):
   try:
    code=ast.Module(body=[node],type_ignores=[]);exec(compile(code,'admitted-probe-constants','exec'),scope)
   except NameError:pass
 scope['ProbeRefused']=type('ProbeRefused',(ValueError,),{})
 for name in ('require','_pairs','parse','empty','public'):
  exec(compile(function(raw,name),'admitted-probe-parser','exec'),scope)
 value={'schema':scope['SCHEMA'],'loader_status':0,**{name:values[0] for name,values in scope['ENUMS'].items()},
  **{name:False for name in scope['SOURCE_BOOLS']},**{name:0 for name in scope['COUNTERS']}}
 value['diagnostic_only']=True
 for name in ('queue_empty','queue_writers_idle','update_idle','callbacks_idle','setters_idle'):value[name]=True
 checks=0
 for reason in reasons:
  value['owner_failure']=reason;encoded=(json.dumps(value,separators=(',',':'))+'\n').encode()
  require(scope['parse'](encoded)==value,'PARSE_REASON');checks+=1
  projected={**scope['empty'](),**value,'schema':scope['PUBLIC_SCHEMA'],'probe_state':'VALID',
   **{name:True for name in ('process_started','process_closed','handles_closed','cleanup_attempted','probe_validated')}}
  result=scope['public'](projected)
  require(set(result)==set(scope['empty']()) and len(result)==43 and result['owner_failure']==reason
   and result['source_generation_admitted'] is False and result['world_authority'] is False,'PUBLIC_REASON');checks+=1
 for reason in (True,7,None,'PRIVATE_POINTER_OR_STATE_CANARY','INITIAL_STATE:2'):
  value['owner_failure']=reason
  try:scope['parse'](json.dumps(value).encode())
  except scope['ProbeRefused']:checks+=1
  else:require(False,'PARSE_PRIVATE_VALUE')
 require(tuple(reasons)==scope['OWNER_FAILURES'][-13:],'PARSE_ENUM_ORDER')
 return {'checks':checks,'fixed_additional_reasons':list(reasons),'file_or_child_collection_replayed':False}
def run(args):
 root=args.source_root.resolve(strict=True);require(HERE==root/'native-android/engine/scenecatalog-server/fresh_callback_observer','OWN_ROOT')
 revision=subprocess.run(['git','rev-parse','HEAD'],cwd=root,check=True,capture_output=True,text=True).stdout.strip()
 output=args.output.absolute();require(not output.exists() and not output.is_symlink(),'OUTPUT_EXISTS')
 paths=[Path(__file__).resolve(),HERE/'test_initial_owner.c',HERE/'stage.py',HERE/'source_group_profile_api.h',
  HERE/'source_group_profile.inc',HERE/'source_folder_profile_api.h',HERE/'probe.py',HERE/'test_stage.py',
  HERE/'INITIAL_OWNER_ELIGIBILITY.md',HERE/'README.md',HERE.parent/'source_groups_owner.inc',
  HERE.parent/'groups_owner_oracle_shim.h',HERE.parent/'stage_export.py']
 admitted={p:p.read_bytes() for p in paths}
 for p,raw in admitted.items():require(tracked(root,p.relative_to(root).as_posix())==raw,'UNCOMMITTED_SOURCE')
 sources={};original_raw={}
 for name in ORIGINALS:
  raw=tracked(root,'upstream/ouroboros/'+name);require((root/'upstream/ouroboros'/name).read_bytes()==raw,'ORIGINAL_CHANGED')
  original_raw[name]=raw;sources[name]=raw.replace(b'\r\n',b'\n')
 facts=lifecycle(sources);stage=production(admitted);old=admitted[HERE.parent/'source_groups_owner.inc']
 instrumented=stage['instrument_owner'](old);specialized=stage['specialize_initial_owner'](instrumented)
 # Independently reverse ONLY the added eligibility helper and the one replaced
 # atom; the retained47-atom instrumentation is not requalified/replayed here.
 restored=specialized.replace(stage['INITIAL_OWNER_SOURCE'],b'',1)
 new=b'!coh_fresh_source_initial_owner(entity,client,out,sizeof(*out))'
 require(restored.count(new)==1,'ONE_REPLACED_ATOM');restored=restored.replace(new,b'!entInUse(entity->owner)',1)
 require(restored==instrumented,'UNCHANGED_REMAINING_OWNER')
 refusals=0
 for bad in (instrumented+b'\n',old,specialized):
  try:stage['specialize_initial_owner'](bad)
  except ValueError:refusals+=1
  else:require(False,'SPECIALIZER_REFUSAL')
 generated=header(admitted,sources,specialized);output.mkdir(mode=0o700,parents=True)
 compiler=process([args.cc,'--version'],admitted);require(compiler.returncode==0,'COMPILER')
 modes={mode:compile_run(args,output/mode,admitted,generated,flags) for mode,flags in MODES.items()}
 require(all(row['controls']==modes['release']['controls'] for row in modes.values()),'MODE_RESULT')
 mutations={
 'missing_live_range':(b'entity->owner>=entities_max',b'0'),
 'mixed_sleeping_bits':(b'entity_state[entity->owner]!=ENTITY_SLEEPING',b'!(entity_state[entity->owner]&ENTITY_SLEEPING)'),
 'missing_entinfo_alias':(b'!coh_source_owner_disjoint(out,output_bytes,entinfo,(size_t)MAX_ENTITIES_PRIVATE*sizeof(*entinfo))',b'(!out||output_bytes==0)'),
 'missing_owned':(b'!entity->owned',b'0'),
 'missing_client_phase':(b'client->ready!=CLIENTSTATE_NOT_READY',b'(!client)'),
 'missing_transfer_step':(b'entity->dbcomm_state.map_xfer_step!=MAPXFER_NO_XFER',b'0')}
 killed={}
 for name,(before,after) in mutations.items():
  require(generated.count(before)==1,'MUTATION_ANCHOR');mutated=generated.replace(before,after,1)
  killed[name]=compile_run(args,output/('mutation-'+name),admitted,mutated,['-O2'],True)
 parser=parser_controls(admitted,modes['release']['controls']['reason_names']);unchanged(admitted)
 for name,raw in sources.items():require(tracked(root,'upstream/ouroboros/'+name).replace(b'\r\n',b'\n')==raw,'LATE_ORIGINAL_CHANGED')
 require(subprocess.run(['git','rev-parse','HEAD'],cwd=root,check=True,capture_output=True,text=True).stdout.strip()==revision,'REVISION_CHANGED')
 receipt={'schema':'coh-fresh-initial-owner-host-v1','passed':True,'source_revision':revision,
  'source_sha256':{p.relative_to(root).as_posix():sha(raw) for p,raw in admitted.items()},
  'original_sha256_lf':{name:sha(raw) for name,raw in sources.items()},'lifecycle_source_facts':facts,
  'original_sha256_raw':{name:sha(raw) for name,raw in original_raw.items()},
  'original_owner_sha256':sha(old),'instrumented_owner_sha256':sha(instrumented),'specialized_owner_sha256':sha(specialized),
  'generated_host_header_sha256':sha(generated),'one_gate_exact_reverse':True,'specializer_refusal_controls':refusals,
  'modes':modes,'mutations':killed,'parser':parser,'compiler':compiler.stdout.decode().splitlines()[0],
  'old_47_atom_oracle_replayed':False,'old_folder_or_83_qualification_replayed':False,'native_qualification_replayed':False,
  'whole_lifecycle_executed':False,'host_member_subset_storage_only':True,'host_type_access_counter':True,
  'original_win32_layout_qualified':False,'leak_sanitizer_qualified':False,'runtime_executed':False,
  'actual_sleeping_state_established':False,'source_generation_admitted':False,'world_authority':False}
 target=output/'initial-owner.json'
 try:
  with target.open('xb') as stream:
   stream.write((json.dumps(receipt,indent=2,sort_keys=True)+'\n').encode());stream.flush();os.fsync(stream.fileno())
  unchanged(admitted)
  require(subprocess.run(['git','rev-parse','HEAD'],cwd=root,check=True,capture_output=True,text=True).stdout.strip()==revision,'LATE_REVISION_CHANGED')
 except BaseException:
  try:target.unlink()
  except OSError:pass
  raise
 return receipt
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--cc',default='cc')
 result=run(parser.parse_args());print(json.dumps({'passed':True,'schema':result['schema'],'controls':result['modes']['release']['controls']}))
