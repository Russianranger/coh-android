#!/usr/bin/env python3
"""Compare native fresh-initial model-level material policy with original CLIENT functions."""
import argparse,hashlib,importlib.util,json,os,re,struct,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
RESOURCE_SHA='8500764939215b576e5ff88056ec85b475785038e09600019846ff5a06eb1cd6'
LEDGER_SHA='46df6643795c3d06aa5b52b3c2fadeed1eac00a3693f33ac611bb5d990109e2a'
CACHE_SHA='cf9595e54bc65a40d2dddc3a5a13c475d7c2ce07a96420e6001b0e2312926bc1'
STATES_SHA='9c4a5aab4c2bffb99eb2416e76a692449ee26927beed3cdd86dece02af2b2aac'
ORIGINAL_PINS={'upstream/ouroboros/Common/seq/anim.c': 'adcdfa2ae1a822c4aed10b0f41baeca5e94b8683e10ed78e3bb45d6bac7936bc', 'upstream/ouroboros/Common/seq/anim.h': 'b5e6149d6222a74e1d3741b902c0a08fec45ad08ac63665be1d214ba54d2fbbe', 'upstream/ouroboros/Common/seq/tricks.h': '4e6a46939e5b61848e73b34eaab34eca506a2665259e8ebd36171aa802159a49', 'upstream/ouroboros/Common/seq/AutoLOD.h': '22fcff5c7eb9887057a8d6fa2b64dcb8a72c69cf585e208995205be5912865e5', 'upstream/ouroboros/Common/seq/animtrackanimate.h': '1c3292e5938562e6d4c093cd52d5ef0d92f58cabf0e18048f926df5e7d71e273', 'upstream/ouroboros/Game/src/render/model.c': '5a5fb0d03c94450b108436c4d67e1503246e72627cc6155d23ddc1e557755072', 'upstream/ouroboros/Game/src/render/tex.h': '56e56aea12a4126250f5f6f4d2211f62814b7eae4ad2598271f5423b60680552', 'upstream/ouroboros/Game/src/render/texEnums.h': '6e96499b08adcfdf2a788286da086aead8e17d2b05ae8c31ee50752b7de778de', 'upstream/ouroboros/Game/src/render/thread/rt_state.c': '6d80cb17585e40a3e1dea7f51d2d9d1129af2569ed6b9fe770dc7aaea734ea0d', 'upstream/ouroboros/Game/src/render/thread/rt_state.h': '688e3b33339c7a658c0887f770ecb0a45228bd8d0d146db8e3ba5e0caed471f0', 'upstream/ouroboros/Game/src/render/thread/rt_init.h': '789e74ff2f86ad1a01f6bdfac095c81a68b820ad5c8c478c2cabdacdc897f85d', 'upstream/ouroboros/Game/src/graphics/gfxSettings.h': 'd2b1a2cb220061f659f714bc85dccb0ca64b9105410068e5c5042c812097de17'}
LEDGER=ROOT/'native-android/engine/scenecatalog/evidence/root-model-texture-partitions-38994607354.json'
OBSERVER=ROOT/'native-android/engine/scenecatalog-server/resource_oracle.py'
LOCAL=['check_model_material.py','coh_wr_model_material.c','coh_wr_model_material.h','model_material_oracle.py','tests/test_model_material.c','tests/test_model_material_cpp.cpp','check_texname.py','coh_wr_texopt.c','coh_wr_texopt.h','coh_wr_texopt_types_internal.h','coh_wr_texopt_tables_internal.inc','coh_wr_texopt_post_source.inc','coh_wr_trick.c','coh_wr_trick.h','coh_wr_trick_types_internal.h','coh_wr_trick_tables_internal.inc','coh_wr_trick_post_source.inc','coh_wr_surface_states.c','coh_wr_surface_states.h','coh_wr_surface_core.inc','coh_wr_rigid.c','coh_wr_rigid.h']
DEPS=[HERE/x for x in LOCAL]+[ROOT/x for x in ORIGINAL_PINS]+[LEDGER,OBSERVER,HERE.parent/'scenecatalog-server/source_resources.inc',HERE.parent/'assets/coh_asset_loader.c',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c',ROOT/'native-android/src/byte_reader.h',ROOT/'native-android/include/coh_native_core.h']
def sha(b):return hashlib.sha256(b).hexdigest()
START={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS}
def load(name,path):
 b=path.read_bytes()
 if sha(b)!=START[str(path.relative_to(ROOT))]:raise ValueError('helper changed before execution')
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;exec(compile(b,str(path),'exec'),m.__dict__);return m

def run(cmd,**kw):
 p=subprocess.run(list(map(str,cmd)),capture_output=True,timeout=180,**kw)
 if p.returncode:raise ValueError(p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
 return p.stdout

def exact(path,size,digest):
 with path.open('rb') as stream:b=stream.read(size+1)
 if len(b)!=size or sha(b)!=digest:raise ValueError('exact bounded input differs '+str(path))
 return b

def roots(resources,observer):
 if sha(LEDGER.read_bytes())!=LEDGER_SHA:raise ValueError('exact root ledger differs')
 ledger=json.loads(LEDGER.read_bytes());rows=observer.decode(resources);offsets=[];at=0
 while at<len(resources):offsets.append(at);at+=struct.unpack_from('<I',resources,at+16)[0]
 if at!=len(resources) or len(rows)!=len(offsets) or ledger['resources_sha256']!=RESOURCE_SHA or ledger['model_owner_rows']!=3083 or len(ledger['rows'])!=3083:raise ValueError('root record bounds')
 fixture=['typedef struct{const char*name;unsigned ordinal,parts,trick,f1,f2,flags;}RootFixture;','static const RootFixture root_fixtures[]={'];seen=set()
 for item in ledger['rows']:
  i=item['source_ordinal']
  if type(i)!=int or i<0 or i>=len(rows) or i in seen:raise ValueError('root ordinal')
  seen.add(i);row=rows[i]
  if not row['model_present'] or row['strings'][1]!=item['model'] or row['strings'][2]!=item['source_geo_name'] or row['textures']!=[tuple(x) for x in item['textures']]:raise ValueError('root exact model/partition identity')
  parts=len(row['textures']);trick,f1,f2,flags=struct.unpack_from('<4I',resources,offsets[i]+104)
  if not 1<=parts<=256 or trick>1 or not trick and (f1 or f2 or flags):raise ValueError('fresh-initial projection source domain')
  fixture.append('{'+json.dumps(item['model'])+','+','.join(str(x)+'u' for x in [i,parts,trick,f1,f2,flags])+'},')
 return '\n'.join(fixture+['};'])+'\n'

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-cache',type=Path,required=True);p.add_argument('--actual-states',type=Path,required=True);p.add_argument('--resources',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('fresh output required')
 for path,pin in ORIGINAL_PINS.items():
  if sha((ROOT/path).read_bytes())!=pin:raise ValueError('original source pin differs '+path)
 cache=exact(a.actual_cache,13537052,CACHE_SHA);states=exact(a.actual_states,15380,STATES_SHA);resources=exact(a.resources,12596422,RESOURCE_SHA)
 old=load('model_policy_commands',HERE/'check_texname.py');observer=load('model_policy_resources',OBSERVER);producer=load('model_material_oracle',HERE/'model_material_oracle.py')
 fixture=roots(resources,observer);production=(HERE/'coh_wr_model_material.c').read_text();constants=re.findall(r'^#define ((?:OBJ|TRICK|TEXOPT)\w+) ',production,re.M)
 if len(constants)!=25 or len(set(constants))!=25:raise ValueError('explicit numeric source facts drift')
 generated,functions=producer.create(ROOT,old.extract,constants)
 facts=''.join('CHECK('+x+'==original_model_constant("'+x+'"));\n' for x in constants)
 common=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-I',HERE,'-I',ROOT/'native-android/include']
 source_extra=['-Wno-unused-variable','-Wno-parentheses','-Wno-error=pedantic']
 modes={};binaries={};exports={};mutations=[];stack=[]
 with tempfile.TemporaryDirectory(prefix='coh-model-policy-') as directory:
  temp=Path(directory);(temp/'original.c').write_text(generated);(temp/'model-policy-fixtures.h').write_text(fixture);(temp/'model-policy-constant-checks.h').write_text(facts)
  sources=[HERE/'tests/test_model_material.c',HERE/'coh_wr_texopt.c',HERE/'coh_wr_trick.c',HERE/'coh_wr_surface_states.c',HERE.parent/'assets/coh_asset_loader.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
  for mode,extra in [('release',['-O2']),('address',['-O1','-fsanitize=address','-no-pie']),('undefined',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   obj=temp/(mode+'-standalone.o');run([*common,*extra,'-fstack-usage','-c',HERE/'coh_wr_model_material.c','-o',obj]);names=sorted(x.split()[-1] for x in run(['nm','-g','--defined-only',obj]).decode().splitlines())
   if names!=['coh_wr_model_material_project']:raise ValueError('private source symbol leaked')
   exports[mode]={'symbols':names,'object_sha256':sha(obj.read_bytes())}
   if mode=='release':stack=obj.with_suffix('.su').read_text().splitlines()
   objects=[]
   for i,path in enumerate(sources):
    obj=temp/(mode+'-'+str(i)+'.o');run([*common,*extra,'-I',temp,'-c',path,'-o',obj]);objects.append(obj)
   obj=temp/(mode+'-original.o');run([*common,*extra,*source_extra,'-c',temp/'original.c','-o',obj]);objects.append(obj)
   binary=temp/mode;run(['cc',*extra,*objects,'-Wl,--wrap=malloc','-Wl,--wrap=calloc','-lz','-lcrypto','-lm','-o',binary]);modes[mode]=json.loads(run([binary,a.actual_cache,a.actual_states],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(binary.read_bytes())
  cxx_binary=temp/'cpp-link';cxx_source=HERE/'tests/test_model_material_cpp.cpp'
  run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-pedantic','-I',HERE,cxx_source,temp/'release-standalone.o','-o',cxx_binary]);run([cxx_binary])
  cxx_proof={'passed':True,'source_sha256':sha(cxx_source.read_bytes()),'actual_C_object_sha256':exports['release']['object_sha256'],'binary_sha256':sha(cxx_binary.read_bytes()),'executed':True}
  changes=[('global_ADDGLOW_promotion','if(p->blend.shader==3)minimum=p->blend;','if(0)minimum=p->blend;'),('common_bits_retained','result.common_blend.shader!=chosen.shader','result.common_blend.shader!=chosen.shader||result.common_blend.bits!=chosen.bits'),('merged_first_partition','result.parts[0]=merged','result.parts[q->part_count-1]=merged'),('white_mask_early_return','if(p->mask_is_exact_white)return 0;','if(0)return 0;'),('fallback_force_opaque_only','if(p->is_fallback&&p->texopt_present','if(!p->is_fallback&&p->texopt_present'),('MULTI_variant_intersection','next.bits&old.bits','next.bits|old.bits')]
  for name,before,after in changes:
   if production.count(before)!=1:raise ValueError('mutation marker drift '+name)
   mutated=temp/(name+'.c');mutated.write_text(production.replace(before,after));test=(HERE/'tests/test_model_material.c').read_text();marker='#include "../coh_wr_model_material.c"'
   if test.count(marker)!=1:raise ValueError('private production include drift')
   wrapper=temp/(name+'-test.c');wrapper.write_text(test.replace(marker,'#include "'+str(mutated)+'"').replace('#include "../coh_wr_texopt.h"','#include "coh_wr_texopt.h"').replace('#include "../coh_wr_trick.h"','#include "coh_wr_trick.h"'));binary=temp/name
   run([*common,'-O2','-I',temp,wrapper,*[temp/('release-'+str(i)+'.o') for i in range(1,7)],temp/'release-original.o','-Wl,--wrap=malloc','-Wl,--wrap=calloc','-lz','-lcrypto','-lm','-o',binary]);result=subprocess.run([binary,a.actual_cache,a.actual_states],capture_output=True,timeout=120)
   if not result.returncode:raise ValueError('production mutation escaped '+name)
   mutations.append(name)
 if START!={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS}:raise ValueError('source readmission differs')
 exact(a.actual_cache,len(cache),CACHE_SHA);exact(a.actual_states,len(states),STATES_SHA);exact(a.resources,len(resources),RESOURCE_SHA)
 proof={'passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_sha256':START,'input_sha256':{'historical_tricks':CACHE_SHA,'historical_states':STATES_SHA,'resources':RESOURCE_SHA,'root_ledger':LEDGER_SHA},'original_function_sha256_lf':{k:sha(v.encode()) for k,v in functions.items()},'generated_original_sha256':sha(generated.encode()),'generated_root_fields_sha256':sha(fixture.encode()),'source_numeric_constants_compared':constants,'modes':modes,'binary_sha256':binaries,'standalone_public_exports':exports,'actual_C_object_CPP_link_test':cxx_proof,'host_release_stack_usage':stack,'production_mutations_refused':mutations,'unchanged_original_policy_functions_executed':True,'fresh_initial_state_only':True,'fixture_input_layout_storage_allocator_model_selection_and_capability_observers':True,'root_SERVER_fields_with_derived_TexBind_and_normal_inputs':True,'historical_dictionary_controls_independent_not_model_associated':True,'native_policy_heap_allocations':0,'existing_rigid_material_validator_unchanged':True,'original_only_compiler_warning_allowances':source_extra,'current_TexBind_selection_proven':False,'current_CLIENT_generation':False,'effective_material_or_GPU_owner_created':False,'world_authority':False,'android_execution':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes,'mutations':mutations}))
if __name__=='__main__':main()
