#!/usr/bin/env python3
"""Qualify historical initial material-trick creation eligibility; no TexBind creation."""
import argparse,hashlib,importlib.util,json,os,subprocess,sys,tempfile,zipfile
from pathlib import Path,PurePosixPath
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
PINS={'cache':'cf9595e54bc65a40d2dddc3a5a13c475d7c2ce07a96420e6001b0e2312926bc1','states':'9c4a5aab4c2bffb99eb2416e76a692449ee26927beed3cdd86dece02af2b2aac','avatar':'03f980c983702c2c9d21b0f674903e151129d0554b25d800b8724036f2cb4a29'}
ORIGINAL={'upstream/ouroboros/Common/seq/tricks.c':'5e91da3f103e9f7ecfe614636ce816fb9dae74a37480f59669d3270d1a2ac4d7','upstream/ouroboros/Game/src/render/tex.c':'4507ee6fa752ed9452e78c4c989a9de0bdf93d81dd3597f1b1db063d73f1ca5c','upstream/ouroboros/Game/src/render/tex.h':'56e56aea12a4126250f5f6f4d2211f62814b7eae4ad2598271f5423b60680552','upstream/ouroboros/Common/seq/tricks.h':'4e6a46939e5b61848e73b34eaab34eca506a2665259e8ebd36171aa802159a49','upstream/ouroboros/Game/src/render/texEnums.h':'6e96499b08adcfdf2a788286da086aead8e17d2b05ae8c31ee50752b7de778de'}
LOCAL=['coh_wr_tex_seed.c','coh_wr_tex_seed.h','tex_seed_oracle.py','check_tex_seed.py','tests/test_tex_seed.c','tests/test_tex_seed_cpp.cpp','coh_wr_tex_inputs.c','coh_wr_tex_inputs.h','coh_wr_tex_basic_lookup.c','coh_wr_tex_basic_lookup.h','coh_wr_texopt.c','coh_wr_texopt.h','coh_wr_texopt_types_internal.h','coh_wr_texopt_tables_internal.inc','coh_wr_texopt_post_source.inc','coh_wr_surface_states.c','coh_wr_surface_states.h','coh_wr_surface_core.inc','check_texname.py','texname_guard_candidate.py']
DEPS=[HERE/x for x in LOCAL]+[ROOT/x for x in ORIGINAL]+[ROOT/'assets/character-avatar-defaults-manifest.json',ROOT/'assets/character-avatar-defaults.zip',ROOT/'assets/reference-inputs-manifest.json',HERE/'qualification/texture-seed-eligibility-20261017/required-default-inputs.json',HERE.parent/'assets/coh_asset_loader.c',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c',ROOT/'native-android/src/byte_reader.h',ROOT/'native-android/include/coh_native_core.h']
def sha(b):return hashlib.sha256(b).hexdigest()
START={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS}
def run(cmd,**kw):
 p=subprocess.run(list(map(str,cmd)),capture_output=True,timeout=180,**kw)
 if p.returncode:raise ValueError(p.stdout.decode(errors='replace')+p.stderr.decode(errors='replace'))
 return p.stdout
def load(name,path):
 b=path.read_bytes()
 if sha(b)!=START[str(path.relative_to(ROOT))]:raise ValueError('helper changed before execution')
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;exec(compile(b,str(path),'exec'),m.__dict__);return m
def exact(path,size,pin):
 with path.open('rb') as stream:b=stream.read(size+1)
 if len(b)!=size or sha(b)!=pin:raise ValueError('exact bounded input differs '+str(path))
 return b
def avatars(archive,destination):
 manifest=json.loads((ROOT/'assets/character-avatar-defaults-manifest.json').read_bytes())
 if START['assets/character-avatar-defaults-manifest.json']!='2a96ff8fb24b686502d62e1e1ed25453681d4c15389c59b1f35ce3fbf1a5feb7':raise ValueError('avatar manifest pin differs')
 rows=sorted((path,pin) for path,pin in manifest['files'].items() if path.endswith('.texture'))
 if len(rows)!=15:raise ValueError('exact fifteen avatar texture entries required')
 fixture=['typedef struct{const char*path;size_t bytes;uint8_t sha256[32];}AvatarFixture;','static const AvatarFixture avatar[]={']
 with zipfile.ZipFile(archive) as z:
  if len(z.namelist())!=manifest['file_count'] or set(z.namelist())!=set(manifest['files']):raise ValueError('avatar archive inventory differs')
  for path,pin in rows:
   parts=PurePosixPath(path).parts
   if not parts or any(x in ('','.','..') for x in parts) or path.startswith('/') or '\\' in path:raise ValueError('safe exact avatar member required')
   info=z.getinfo(path)
   if info.file_size!=pin['bytes'] or not 0<info.file_size<=1<<20:raise ValueError('bounded avatar texture differs')
   body=z.read(path)
   if len(body)!=pin['bytes'] or sha(body)!=pin['sha256']:raise ValueError('avatar texture pin differs')
   target=destination/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
   fixture.append('{'+json.dumps(path)+','+str(len(body))+'u,{'+','.join('0x'+pin['sha256'][i:i+2] for i in range(0,64,2))+'}},')
 return '\n'.join(fixture+['};'])+'\n',{path:pin for path,pin in rows}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-cache',type=Path,required=True);p.add_argument('--actual-states',type=Path,required=True);p.add_argument('--avatar-zip',type=Path,default=ROOT/'assets/character-avatar-defaults.zip');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('fresh output required')
 for path,pin in ORIGINAL.items():
  if sha((ROOT/path).read_bytes())!=pin:raise ValueError('original source pin differs '+path)
 cache=exact(a.actual_cache,13537052,PINS['cache']);states=exact(a.actual_states,15380,PINS['states']);avatar=exact(a.avatar_zip,1842488,PINS['avatar'])
 old=load('tex_seed_commands',HERE/'check_texname.py');guard=load('tex_seed_guard',HERE/'texname_guard_candidate.py');producer=load('tex_seed_oracle',HERE/'tex_seed_oracle.py');original,functions,repair=producer.create(ROOT,old.extract,guard.patch)
 common=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',HERE,'-I',ROOT/'native-android/include']
 native=[HERE/'tests/test_tex_seed.c',HERE/'coh_wr_tex_inputs.c',HERE/'coh_wr_tex_basic_lookup.c',HERE/'coh_wr_texopt.c',HERE/'coh_wr_surface_states.c',HERE.parent/'assets/coh_asset_loader.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
 modes={};binaries={};exports={};mutations=[];stack=[]
 with tempfile.TemporaryDirectory(prefix='coh-tex-seed-') as raw:
  d=Path(raw);bodydir=d/'avatar';fixture,payloads=avatars(a.avatar_zip,bodydir);(d/'tex-seed-fixtures.h').write_text(fixture);(d/'original.c').write_text(original)
  for mode,flags in [('release',['-O2']),('address',['-O1','-fsanitize=address','-no-pie']),('undefined',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   standalone=d/(mode+'-standalone.o');run([*common,*flags,'-fstack-usage','-c',HERE/'coh_wr_tex_seed.c','-o',standalone]);symbols=sorted(x.split()[-1] for x in run(['nm','-g','--defined-only',standalone]).decode().splitlines())
   if symbols!=['coh_wr_tex_seed']:raise ValueError('unexpected public/private export')
   exports[mode]={'symbols':symbols,'actual_C_object_sha256':sha(standalone.read_bytes())}
   if mode=='release':stack=standalone.with_suffix('.su').read_text().splitlines()
   objects=[]
   for i,path in enumerate(native+[d/'original.c']):
    obj=d/(mode+'-'+str(i)+'.o');run([*common,*flags,'-I',d,'-c',path,'-o',obj]);objects.append(obj)
   binary=d/mode;run(['cc',*flags,*objects,'-Wl,--wrap=malloc','-Wl,--wrap=calloc','-lcrypto','-lz','-lm','-o',binary]);modes[mode]=json.loads(run([binary,a.actual_cache,a.actual_states,bodydir],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(binary.read_bytes())
  cpp=d/'cpp-link';cpp_source=HERE/'tests/test_tex_seed_cpp.cpp';run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-pedantic','-I',HERE,cpp_source,d/'release-standalone.o',*[d/('release-'+str(i)+'.o') for i in range(1,8)],'-lcrypto','-lz','-lm','-o',cpp]);run([cpp]);cpp_proof={'passed':True,'executed':True,'source_sha256':sha(cpp_source.read_bytes()),'actual_C_object_sha256':exports['release']['actual_C_object_sha256'],'binary_sha256':sha(cpp.read_bytes())}
  production=(HERE/'coh_wr_tex_seed.c').read_text()
  changes=[('exact_equal_instead_of_prefix','else if(prefix(base,v->name))','else if(equal(base,v->name))'),('omit_enabled_fallback','uint32_t slots=v->fallback.use_fallback?16u:13u;','uint32_t slots=13u;'),('unknown_means_present','if(found.branch!=COH_WR_BASIC_OBSERVED_HEADER)return COH_NOT_FOUND;','if(0)return COH_NOT_FOUND;'),('swappable_is_required','&&!equal(s,"swappable")','&&1'),('wrong_source_slot','d->source_slot=i;','d->source_slot=15u-i;'),('aggregate_limit_bypass','total>l->aggregate_limit','0')]
  for name,before,after in changes:
   if production.count(before)!=1:raise ValueError('mutation preimage differs '+name)
   mutated=d/(name+'.c');mutated.write_text(production.replace(before,after));test=(HERE/'tests/test_tex_seed.c').read_text();marker='#include "../coh_wr_tex_seed.c"'
   if test.count(marker)!=1:raise ValueError('private production include differs')
   wrapper=d/(name+'-test.c');wrapper.write_text(test.replace(marker,'#include "'+str(mutated)+'"'));obj=d/(name+'.o');extra=['-Wno-unused-function'] if name=='exact_equal_instead_of_prefix' else []
   run([*common,'-O2',*extra,'-I',d,'-c',wrapper,'-o',obj]);binary=d/name;run(['cc','-O2',obj,*[d/('release-'+str(i)+'.o') for i in range(1,9)],'-Wl,--wrap=malloc','-Wl,--wrap=calloc','-lcrypto','-lz','-lm','-o',binary]);result=subprocess.run([binary,a.actual_cache,a.actual_states,bodydir],capture_output=True,timeout=180)
   if not result.returncode:raise ValueError('production mutation escaped '+name)
   mutations.append(name)
 if START!={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS}:raise ValueError('source readmission differs')
 exact(a.actual_cache,len(cache),PINS['cache']);exact(a.actual_states,len(states),PINS['states']);exact(a.avatar_zip,len(avatar),PINS['avatar'])
 proof={'passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_sha256':START,'input_sha256':PINS,'authentic_avatar_texture_members':payloads,'original_function_sha256_lf':{k:sha(v.encode()) for k,v in functions.items()},'generated_original_sha256':sha(original.encode()),'generated_authentic_headers_fixture_sha256':sha(fixture.encode()),'modes':modes,'binary_sha256':binaries,'standalone_public_exports':exports,'actual_C_object_CPP_call_link':cpp_proof,'host_release_stack_usage':stack,'production_mutations_refused':mutations,'unchanged_original_IsValidTexName_trickFindAllTextures_trickCreateTextures_executed':True,'original_Basic_lookup_and_explicit_short_key_repair':repair,'original_release_debug_poison_assertions_disabled':True,'native_actual_postprocessed_cache_record_inputs':True,'original_gate_compared_over_native_record_fields_not_independent_postprocess_requalification':True,'controlled_TexOpt_views_are_not_actual_cache_rows':True,'subset_unknown_stops_before_original_miss_branch':True,'actual_retired_cache_owner_loader_provider_and_Surface':True,'seed_heap_allocations':0,'new_persistent_owner_bytes':0,'historical_fixture_input_label':17,'current_CLIENT_generation':False,'original_table_absence_proven':False,'delayed_load_or_LWC_state_established':False,'default_or_TexBind_created':False,'current_material_selection':False,'world_authority':False,'android_execution':False,'old_qualifiers_rerun':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes,'mutations':mutations}))
if __name__=='__main__':main()
