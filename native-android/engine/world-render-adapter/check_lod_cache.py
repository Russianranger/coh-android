#!/usr/bin/env python3
"""Qualify exact historical native LOD cache and original initial path/hash precedence."""
import argparse,hashlib,importlib.util,json,os,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
CACHE_SHA='13800255781138248226340be316cd628e98800d9ba889fe1aecc902e483b66a'
RESOURCE_SHA='8500764939215b576e5ff88056ec85b475785038e09600019846ff5a06eb1cd6'
LEDGER_SHA='46df6643795c3d06aa5b52b3c2fadeed1eac00a3693f33ac611bb5d990109e2a'
LEDGER=ROOT/'native-android/engine/scenecatalog/evidence/root-model-texture-partitions-38994607354.json'
OBSERVER=ROOT/'native-android/engine/scenecatalog-server/resource_oracle.py'
AUTO_SHA='f34c46abac3e6e95bd5829d1d72a203756a7764872f6a9483c4377a05a546722'
LOCAL=['check_lod_cache.py','coh_wr_lod_cache.c','coh_wr_lod_cache.h','coh_wr_texopt.h','lod_cache_oracle.py','tests/test_lod_cache.c','texopt_setup_oracle.py','texopt_full_oracle.py','check_surface_states.py','check_texname.py','texopt_cache_contract.py','CLIENT_SURFACE_STATES.md','coh_wr_surface_states.c','coh_wr_surface_states.h','coh_wr_surface_core.inc','tests/test_surface_states.c']
UPSTREAM=['Common/seq/AutoLOD.c','Common/seq/AutoLOD.h','Common/seq/tricks.c','Common/seq/tricks.h','Common/seq/seqstate.c','Common/seq/seqstate.h','Common/seq/TriggeredMove.h','Game/src/render/texEnums.h','Game/src/render/thread/rt_state.h','libs/UtilitiesLib/src/utils/utils.c','libs/UtilitiesLib/src/utils/textparser.c','libs/UtilitiesLib/src/utils/serialize.c','libs/UtilitiesLib/include/utilitieslib/utils/textparser.h']
DEPS=[LEDGER,OBSERVER,ROOT/'native-android/engine/scenecatalog-server/source_resources.inc']+[HERE/x for x in LOCAL]+[ROOT/'upstream/ouroboros'/x for x in UPSTREAM]+[HERE.parent/'assets/coh_asset_loader.c',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c',ROOT/'native-android/src/byte_reader.h',ROOT/'native-android/include/coh_native_core.h']
def sha(b):return hashlib.sha256(b).hexdigest()
def run(cmd,**kw):
 p=subprocess.run(list(map(str,cmd)),capture_output=True,timeout=180,**kw)
 if p.returncode:raise ValueError(p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
 return p.stdout
START={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS}
def load(name,path):
 body=path.read_bytes()
 if sha(body)!=START[str(path.relative_to(ROOT))]:raise ValueError('helper changed before execution')
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;exec(compile(body,str(path),'exec'),module.__dict__);return module

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-cache',type=Path,required=True);p.add_argument('--resources',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('fresh output required')
 with a.actual_cache.open('rb') as f:body=f.read(1059017)
 if len(body)!=1059016 or sha(body)!=CACHE_SHA:raise ValueError('exact retained cache differs')
 if sha((ROOT/'upstream/ouroboros/Common/seq/AutoLOD.c').read_bytes())!=AUTO_SHA:raise ValueError('original AutoLOD source differs')
 with a.resources.open('rb') as f:resources=f.read(12596423)
 if len(resources)!=12596422 or sha(resources)!=RESOURCE_SHA or sha(LEDGER.read_bytes())!=LEDGER_SHA:raise ValueError('exact retained root/resource inputs differ')
 observer=load('lod_root_resource_observer',OBSERVER);observed=observer.decode(resources);ledger=json.loads(LEDGER.read_bytes())
 if ledger['resources_sha256']!=RESOURCE_SHA or ledger['model_owner_rows']!=3083 or len(ledger['rows'])!=3083:raise ValueError('root ledger identity')
 fixture=['typedef struct{unsigned ordinal;const char*geo,*model;}RootQuery;','static const RootQuery root_queries[]={']
 seen=set()
 for row in ledger['rows']:
  i=row['source_ordinal']
  if type(i)!=int or i<0 or i>=len(observed) or i in seen:raise ValueError('root source ordinal')
  seen.add(i);actual=observed[i]
  if not actual['model_present'] or actual['strings'][1]!=row['model'] or actual['strings'][2]!=row['source_geo_name'] or actual['textures']!=[tuple(x) for x in row['textures']]:raise ValueError('root source observation differs')
  fixture.append('{'+str(i)+','+json.dumps(row['source_geo_name'])+','+json.dumps(row['model'])+'},')
 fixture='\n'.join(fixture+['};'])+'\n'

 old=load('check_texname',HERE/'check_texname.py');load('texopt_full_oracle',HERE/'texopt_full_oracle.py');load('check_surface_states',HERE/'check_surface_states.py');load('texopt_setup_oracle',HERE/'texopt_setup_oracle.py');oracle=load('lod_cache_oracle',HERE/'lod_cache_oracle.py')
 generated=oracle.create(ROOT,old.extract)
 header=(ROOT/'upstream/ouroboros/Common/seq/AutoLOD.h').read_text()
 def decl(start,end):at=header.index(start);return header[at:header.index(end,at)+len(end)]
 types='#include <stdint.h>\n#include <stdbool.h>\ntypedef float F32;typedef uint32_t U32;\n'+decl('typedef struct AutoLOD\n','} AutoLOD;')+'\n'+decl('typedef struct ModelLODInfo\n','} ModelLODInfo;')
 common=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-I',HERE,'-I',ROOT/'native-android/include']
 original_flags=['-Wno-missing-field-initializers','-Wno-unused-parameter','-Wno-unused-variable','-Wno-unused-but-set-variable','-Wno-unused-value']
 modes={};binaries={};exports={};mutations=[];stack=[]
 with tempfile.TemporaryDirectory(prefix='coh-lod-cache-') as directory:
  temp=Path(directory);source=temp/'original.c';source.write_text(generated);(temp/'lod-original-types.h').write_text(types);(temp/'lod-root-fixtures.h').write_text(fixture)
  for mode,extra in [('release',['-O2']),('address',['-O1','-fsanitize=address','-no-pie']),('undefined',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   standalone=temp/(mode+'-standalone.o');run([*common,*extra,'-fstack-usage','-c',HERE/'coh_wr_lod_cache.c','-o',standalone]);symbols=run(['nm','-g','--defined-only',standalone]).decode();names=sorted(x.split()[-1] for x in symbols.splitlines());expected=sorted(['coh_wr_lod_cache_'+x for x in ['open','release','report','row','child']]+['coh_wr_lod_dictionary_'+x for x in ['stage','release','report','row','child','lookup']]+['coh_wr_lod_source_filename'])
   if names!=expected:raise ValueError('private source symbol leaked')
   exports[mode]={'symbols':names,'object_sha256':sha(standalone.read_bytes())}
   if mode=='release':stack=standalone.with_suffix('.su').read_text().splitlines()
   sources=[HERE/'tests/test_lod_cache.c',HERE.parent/'assets/coh_asset_loader.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c'];objects=[]
   for i,path in enumerate(sources):
    obj=temp/(mode+'-'+str(i)+'.o');run([*common,*extra,'-I',temp,'-c',path,'-o',obj]);objects.append(obj)
   obj=temp/(mode+'-original.o');run([*common,*extra,*original_flags,'-c',source,'-o',obj]);objects.append(obj)
   binary=temp/mode;run(['cc',*extra,*objects,'-Wl,--wrap=calloc','-lz','-lcrypto','-lm','-o',binary]);modes[mode]=json.loads(run([binary,a.actual_cache],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(binary.read_bytes())
  changes=[('near_fade_field_order','!scalar(&q,&v.lod_nearfade)||!scalar(&q,&v.lod_near)','!scalar(&q,&v.lod_near)||!scalar(&q,&v.lod_nearfade)'),('duplicate_last_wins','d->index[end]<first','d->index[end]>first'),('force_auto_with_existing_rows','r.force&&!r.count','r.force||!r.count'),('data_root_component','start=start?start+6:geo','start=geo'),('digest_identity','if(memcmp(hash,expected,32))','if(0)')]
  production=(HERE/'coh_wr_lod_cache.c').read_text()
  for name,before,after in changes:
   if production.count(before)!=1:raise ValueError('mutation marker drift '+name)
   mutated=temp/(name+'.c');mutated.write_text(production.replace(before,after));test=(HERE/'tests/test_lod_cache.c').read_text();include='#include "../coh_wr_lod_cache.c"'
   if test.count(include)!=1:raise ValueError('private source test drift')
   wrapper=temp/(name+'-test.c');wrapper.write_text(test.replace(include,'#include "'+str(mutated)+'"'))
   binary=temp/name;run([*common,'-Wno-unused-const-variable','-Wno-unused-variable','-O2','-I',temp,wrapper,temp/'release-1.o',temp/'release-2.o',temp/'release-3.o',temp/'release-original.o','-Wl,--wrap=calloc','-lz','-lcrypto','-lm','-o',binary]);result=subprocess.run([binary,a.actual_cache],capture_output=True,timeout=60)
   if result.returncode==0:raise ValueError('production mutation escaped '+name)
   mutations.append(name)
 if START!={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS} or sha(a.actual_cache.read_bytes())!=CACHE_SHA or sha(a.resources.read_bytes())!=RESOURCE_SHA:raise ValueError('source/body readmission differs')
 auto=(ROOT/'upstream/ouroboros/Common/seq/AutoLOD.c').read_text();reader=(ROOT/'upstream/ouroboros/libs/UtilitiesLib/src/utils/textparser.c').read_text();functions={name:sha(old.extract(auto,signature).encode()) for name,signature in [('getLODFileName','char *getLODFileName('),('fillInLODFilenames','static void fillInLODFilenames('),('lodinfoLoadPostProcess','void lodinfoLoadPostProcess(')]};functions['original_earray_readbin']=sha(old.extract(reader,'int earray_readbin(').encode())
 proof={'passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_sha256':START,'cache_sha256':CACHE_SHA,'cache_bytes':len(body),'resources_sha256':RESOURCE_SHA,'root_ledger_sha256':LEDGER_SHA,'generated_root_queries_sha256':sha(fixture.encode()),'root_query_scope':'Historical source lookup under explicit fixture writable path; no current CLIENT generation','observed_schema_word':'e8361497','compiled_schema_crc_recomputed':False,'original_functions_sha256_lf':functions,'generated_original_sha256':sha(generated.encode()),'original_types_sha256':sha(types.encode()),'modes':modes,'binary_sha256':binaries,'standalone_public_exports':exports,'host_release_stack_usage':stack,'production_mutations_refused':mutations,'unchanged_original_typed_readers_executed':True,'unchanged_original_initial_postprocess_executed':True,'unchanged_original_lookup_early_return_prefix_executed':True,'fixture_writable_path_and_stash_and_runtime_storage_observers':True,'actual_writable_path_mapping_proven':False,'object_library_models_resolved':False,'runtime_removed_reload_state_implemented':False,'current_CLIENT_generation':False,'material_authority':False,'world_authority':False,'android_execution':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes,'mutations':mutations}))
if __name__=='__main__':main()
