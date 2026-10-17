#!/usr/bin/env python3
"""Qualify original model-name Trick selection against actual retained root observations."""
import argparse,hashlib,importlib.util,json,os,struct,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
PINS={'cache':'cf9595e54bc65a40d2dddc3a5a13c475d7c2ce07a96420e6001b0e2312926bc1','resources':'8500764939215b576e5ff88056ec85b475785038e09600019846ff5a06eb1cd6','roots':'46df6643795c3d06aa5b52b3c2fadeed1eac00a3693f33ac611bb5d990109e2a'}
ORIGINAL={'Common/seq/tricks.c':'5e91da3f103e9f7ecfe614636ce816fb9dae74a37480f59669d3270d1a2ac4d7','Common/seq/AutoLOD.c':'f34c46abac3e6e95bd5829d1d72a203756a7764872f6a9483c4377a05a546722','Common/seq/anim.c':'adcdfa2ae1a822c4aed10b0f41baeca5e94b8683e10ed78e3bb45d6bac7936bc','libs/UtilitiesLib/src/components/StashTable.c':'d806f2a68c37fd3c9806d4924fb97219adc0401a75afc3523cd2efb4347396f9','libs/UtilitiesLib/include/utilitieslib/components/StashTable.h':'9df42de3e42ae4a721cabbd846c88b478b6c9121c54dde36eec349ba36aaae22'}
LOCAL=['check_trick_model.py','trick_model_oracle.py','coh_wr_trick_model.h','coh_wr_trick_model_internal.inc','tests/test_trick_model.c','tests/test_trick_model_cpp.cpp','tests/trick_model_oracle.h','coh_wr_trick.c','coh_wr_trick.h','coh_wr_trick_types_internal.h','coh_wr_trick_tables_internal.inc','coh_wr_trick_post_source.inc','coh_wr_trick_detached.c','coh_wr_trick_detached.h','coh_wr_trick_detached_core.inc','coh_wr_trick_detached_storage_internal.h','coh_wr_texopt.c','coh_wr_texopt.h','coh_wr_texopt_types_internal.h','coh_wr_texopt_tables_internal.inc','coh_wr_texopt_post_source.inc','coh_wr_surface_states.c','coh_wr_surface_states.h','coh_wr_surface_core.inc','check_texname.py','texopt_cache_contract.py','trick_cache_contract.py','check_trick_cache.py','check_trick_detached.py']
ORIGINAL['libs/UtilitiesLib/src/utils/utils_opt.c']='e86e629114f213a0c13cc101f5690fd47a9f6b48eb21c1f4dc3cff62ab3ec351'
BASE_OWNERS={'coh_wr_trick.c':'355c7b9bf156bc10bac1863742ba0d26efbc3643dd3dd84072b7c01a6317459e','coh_wr_trick_detached.c':'1e811f67ec02ccbedb9e5a30ee12ec0f9f6257b843e5694e88f7d7bc5fcfb56f'}
LEDGER=ROOT/'native-android/engine/scenecatalog/evidence/root-model-texture-partitions-38994607354.json'
OBSERVER=ROOT/'native-android/engine/scenecatalog-server/resource_oracle.py'
DEPS=[HERE/x for x in LOCAL]+[ROOT/'upstream/ouroboros'/x for x in ORIGINAL]+[LEDGER,OBSERVER,HERE.parent/'scenecatalog-server/source_resources.inc',HERE.parent/'assets/coh_asset_loader.c',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c',ROOT/'native-android/src/byte_reader.h',ROOT/'native-android/include/coh_native_core.h']
def sha(b):return hashlib.sha256(b).hexdigest()
START={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS}
def load(name,path):
 b=path.read_bytes()
 if sha(b)!=START[str(path.relative_to(ROOT))]:raise ValueError('helper changed before execution')
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;exec(compile(b,str(path),'exec'),m.__dict__);return m
def run(cmd,**kwargs):
 p=subprocess.run(list(map(str,cmd)),capture_output=True,timeout=180,**kwargs)
 if p.returncode:raise ValueError(p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
 return p.stdout
def exact(path,size,pin):
 with path.open('rb') as f:b=f.read(size+1)
 if len(b)!=size or sha(b)!=pin:raise ValueError('exact bounded input differs '+str(path))
 return b
def text(value,maximum,empty=False):
 if value is None and empty:value=''
 if isinstance(value,bytes):value=value.decode('ascii')
 if not isinstance(value,str) or len(value)>=maximum or not empty and not value or any(ord(c)<32 or ord(c)>126 for c in value):raise ValueError('source name domain')
 return json.dumps(value)
def fixtures(cache,resources,roots,framing,wire,observer):
 s=(ROOT/'upstream/ouroboros/Common/seq/tricks.c').read_text();a=(ROOT/'upstream/ouroboros/Common/seq/AutoLOD.c').read_text()
 schema=wire.schema(s,a,{'tricks':sha(s.encode()),'autolod':sha(a.encode())});framed=framing.frame(cache,PINS['cache'])
 lines=['typedef struct {const char*name,*file;} TrickNameFixture;','static const TrickNameFixture trick_fixtures[]={']
 for i in range(3644):
  row=wire.decode(framed,i,schema);lines.append('{'+text(row.values[0].value,260)+','+text(row.values[1].value,1024)+'},')
 lines+=['};','#ifndef TRICK_MODEL_ORACLE_ONLY','typedef struct {const char*model,*geo,*captured_name,*captured_file;unsigned source_ordinal,info_present;} RootTrickFixture;','static const RootTrickFixture root_fixtures[]={']
 rows=observer.decode(resources);ledger=json.loads(roots);offsets=[];at=0
 while at<len(resources):offsets.append(at);at+=struct.unpack_from('<I',resources,at+16)[0]
 if at!=len(resources) or len(rows)!=len(offsets) or ledger['resources_sha256']!=PINS['resources'] or ledger['model_owner_rows']!=3083 or len(ledger['rows'])!=3083:raise ValueError('root ledger bounds')
 seen=set();generations=set()
 for item in ledger['rows']:
  i=item['source_ordinal']
  if type(i)!=int or i<0 or i>=len(rows) or i in seen:raise ValueError('root ordinal')
  seen.add(i);r=rows[i]
  if not r['model_present'] or r['strings'][1]!=item['model'] or r['strings'][2]!=item['source_geo_name'] or r['textures']!=[tuple(x) for x in item['textures']]:raise ValueError('root model identity')
  present=struct.unpack_from('<I',resources,offsets[i]+104)[0];generations.add(struct.unpack_from('<I',resources,offsets[i]+20)[0])
  if present not in (0,1) or bool(present)!=bool(r['strings'][3]) or bool(present)!=bool(r['strings'][4]):raise ValueError('captured Trick association')
  fields=[text(r['strings'][1],260),text(r['strings'][2],260),text(r['strings'][3],260,True),text(r['strings'][4],1024,True),str(i)+'u',str(present)+'u']
  lines.append('{'+','.join(fields)+'},')
 lines+=['};','#endif'];return '\n'.join(lines)+'\n',sorted(generations)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-cache',type=Path,required=True);p.add_argument('--resources',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('fresh output required')
 for path,pin in ORIGINAL.items():
  if sha((ROOT/'upstream/ouroboros'/path).read_bytes())!=pin:raise ValueError('original source differs '+path)
 for path,pin in BASE_OWNERS.items():
  source=(HERE/path).read_text();added='#include "coh_wr_trick_model.h"\n';marker='\n#define MODEL_SELECT_FUNCTION '
  if source.count(added)!=1 or source.count(marker)!=1 or sha(source.replace(added,'').split(marker)[0].encode())!=pin:raise ValueError('preexisting owner implementation changed '+path)
 cache=exact(a.actual_cache,13537052,PINS['cache']);resources=exact(a.resources,12596422,PINS['resources']);roots=exact(LEDGER,1103262,PINS['roots'])
 old=load('trick_model_commands',HERE/'check_texname.py');framing=load('texopt_cache_contract',HERE/'texopt_cache_contract.py');wire=load('trick_cache_contract',HERE/'trick_cache_contract.py');observer=load('trick_model_resources',OBSERVER);oracle=load('trick_model_oracle',HERE/'trick_model_oracle.py')
 fixture,generations=fixtures(cache,resources,roots,framing,wire,observer);original,functions=oracle.create(ROOT,old.extract)
 common=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',HERE,'-I',HERE/'tests','-I',ROOT/'native-android/include']
 native=[HERE/'coh_wr_texopt.c',HERE/'coh_wr_surface_states.c',HERE/'coh_wr_trick.c',HERE/'coh_wr_trick_detached.c',HERE.parent/'assets/coh_asset_loader.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c',HERE/'tests/test_trick_model.c']
 modes={};binaries={};exports={};mutations=[];stack=[]
 with tempfile.TemporaryDirectory(prefix='coh-trick-model-') as directory:
  d=Path(directory);(d/'trick-model-fixtures.h').write_text(fixture);(d/'original.c').write_text(original)
  for mode,extra in [('release',['-O2']),('address',['-O1','-fsanitize=address','-no-pie']),('undefined',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   objects=[];exports[mode]={}
   for i,path in enumerate(native+[d/'original.c']):
    obj=d/(mode+'-'+str(i)+'.o');run([*common,*extra,'-fstack-usage','-I',d,'-c',path,'-o',obj]);objects.append(obj)
    if i in (2,3):
     names=sorted(x.split()[-1] for x in run(['nm','-g','--defined-only',obj]).decode().splitlines())
     expected=sorted(['coh_wr_trick_'+x for x in ['autolod','find','model_select','numeric_projection','open','release','report','stanim','view']]) if i==2 else sorted(['coh_wr_trick_detach']+['coh_wr_trick_detached_'+x for x in ['autolod','find','model_select','numeric_projection','release','report','source_bytes','stanim','view']])
     if names!=expected:raise ValueError('unexpected public/private exports')
     exports[mode]['whole' if i==2 else 'detached']={'symbols':names,'object_sha256':sha(obj.read_bytes())}
     if mode=='release':stack += [x for x in obj.with_suffix('.su').read_text().splitlines() if 'model_select' in x or 'model_query_string' in x]
   binary=d/mode;run(['cc',*extra,*objects,'-Wl,--wrap=malloc','-Wl,--wrap=calloc','-lcrypto','-lz','-lm','-o',binary]);modes[mode]=json.loads(run([binary,a.actual_cache],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(binary.read_bytes())
  cpp=d/'cpp-link';cpp_source=HERE/'tests/test_trick_model_cpp.cpp';release=[d/('release-'+str(i)+'.o') for i in range(7)]
  run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-pedantic','-I',HERE,cpp_source,*release,'-lcrypto','-lz','-lm','-o',cpp]);run([cpp])
  cpp_proof={'passed':True,'executed':True,'source_sha256':sha(cpp_source.read_bytes()),'actual_whole_C_object_sha256':exports['release']['whole']['object_sha256'],'actual_detached_C_object_sha256':exports['release']['detached']['object_sha256'],'binary_sha256':sha(cpp.read_bytes())}
  production=(HERE/'coh_wr_trick_model_internal.inc').read_text()
  changes=[('whole_name_instead_of_suffix','const char*key=suffix?suffix+2:q->model_name;','const char*key=q->model_name;'),('last_suffix_instead_of_first','const char*suffix=strstr(q->model_name,"__");','const char*suffix=strstr(q->model_name,"__");if(suffix){const char*next;while((next=strstr(suffix+2,"__")))suffix=next;}'),('base_fallback_after_suffix_miss','result.matched=result.source_ordinal!=UINT32_MAX;','result.matched=result.source_ordinal!=UINT32_MAX;if(suffix&&!result.matched){char base[260];size_t n=(size_t)(suffix-q->model_name);memcpy(base,q->model_name,n);base[n]=0;result.source_ordinal=winner(c,(CohBytes){(const uint8_t*)base,n});result.matched=result.source_ordinal!=UINT32_MAX;}'),('source_path_as_lookup_key','winner(c,(CohBytes){(const uint8_t*)key,length})','winner(c,(CohBytes){(const uint8_t*)q->source_geo_path,path_length})'),('diagnostic_on_whole_name_miss','if(suffix&&!result.matched&&q->report_missing_suffix)','if(!result.matched&&q->report_missing_suffix)'),('aggregate_limit_bypass','aggregate>l->aggregate_limit','0')]
  for name,before,after in changes:
   if production.count(before)!=1:raise ValueError('mutation marker differs '+name)
   include=d/(name+'.inc');include.write_text(production.replace(before,after));objects=list(release)+[d/'release-7.o',d/'release-8.o']
   for i in (2,3):
    s=native[i].read_text();marker='#include "coh_wr_trick_model_internal.inc"'
    if s.count(marker)!=1:raise ValueError('private selector include differs')
    source=d/(name+'-'+str(i)+'.c');source.write_text(s.replace(marker,'#include "'+str(include)+'"'));obj=source.with_suffix('.o');run([*common,'-O2','-c',source,'-o',obj]);objects[i]=obj
   binary=d/name;run(['cc','-O2',*objects,'-Wl,--wrap=malloc','-Wl,--wrap=calloc','-lcrypto','-lz','-lm','-o',binary]);result=subprocess.run([binary,a.actual_cache],capture_output=True,timeout=120)
   if not result.returncode:raise ValueError('production mutation escaped '+name)
   mutations.append(name)
 if START!={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS}:raise ValueError('source changed after qualification')
 exact(a.actual_cache,len(cache),PINS['cache']);exact(a.resources,len(resources),PINS['resources']);exact(LEDGER,len(roots),PINS['roots'])
 proof={'passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_sha256':START,'input_sha256':PINS,'original_function_sha256_lf':{k:sha(v.encode()) for k,v in functions.items()},'generated_original_sha256':sha(original.encode()),'generated_independent_dictionary_and_actual_root_fixture_sha256':sha(fixture.encode()),'modes':modes,'binary_sha256':binaries,'standalone_public_exports':exports,'actual_C_object_CPP_link_test':cpp_proof,'host_release_selector_stack_usage':stack,'production_mutations_refused':mutations,'unchanged_original_trickFromObjectName_and_getDirectoryName_executed':True,'dictionary_registration_storage_logging_observers':True,'actual_root_model_name_path_and_captured_Trick_name_file_inputs':True,'captured_SERVER_generation_labels':generations,'historical_CLIENT_cache_label_in_native_fixture':17,'SERVER_CLIENT_generation_equality':False,'whole_and_detached_owners_compared':True,'detached_after_actual_loader_provider_retirement':True,'new_selection_heap_allocations':0,'new_persistent_owner_bytes':0,'unchanged_preexisting_owner_implementation_sha256':BASE_OWNERS,'existing_Trick_reader_getter_bodies_unchanged':True,'full_Trick_animation_postprocess':False,'current_CLIENT_material_selection':False,'material_or_GPU_owner_created':False,'world_authority':False,'android_execution':False,'old_qualifiers_rerun':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes,'mutations':mutations}))
if __name__=='__main__':main()
