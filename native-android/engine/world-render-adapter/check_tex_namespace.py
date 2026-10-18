#!/usr/bin/env python3
"""Qualify declared immutable provider selection; no original/current namespace grant."""
import argparse,hashlib,importlib.util,json,os,subprocess,sys,tempfile,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
ORIGINAL={
 'upstream/ouroboros/libs/UtilitiesLib/src/utils/FolderCacheNode.c':'36faafa73afd83361fb8e4f25e340961fae5fb9d33c298b1200be9a4b2a48524',
 'upstream/ouroboros/libs/UtilitiesLib/src/utils/FolderCache.c':'93aac8a9e1a59ca47ab5a067580c36f7ed884db51038577b0453756f55af1d4c',
 'upstream/ouroboros/libs/UtilitiesLib/src/utils/fileutil.c':'6d3991db4e8c1a1b7f55280c7ea69711d765e01009022172a2c90eccd759fdd7',
 'upstream/ouroboros/libs/UtilitiesLib/src/utils/file.c':'8ad08c34d2fed652578e26f0ec1fab79419b40414644c6b8e1ccbc58694733e1',
 'upstream/ouroboros/libs/UtilitiesLib/src/utils/piglib.c':'786ea2c5e9b8cf14fe4dfd4880b9cfe85a138afbccd56759e59b30b7663ed528',
 'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/FolderCache.h':'42f1b9c5555abdc93afe7029cdf02bb551d572c18557fed00d7610d6c58e177c',
 'upstream/ouroboros/Game/src/render/tex.c':'4507ee6fa752ed9452e78c4c989a9de0bdf93d81dd3597f1b1db063d73f1ca5c',
 'upstream/ouroboros/Game/src/render/tex.h':'56e56aea12a4126250f5f6f4d2211f62814b7eae4ad2598271f5423b60680552',
 'upstream/ouroboros/Game/src/render/texEnums.h':'6e96499b08adcfdf2a788286da086aead8e17d2b05ae8c31ee50752b7de778de'}
LOCAL=['coh_wr_tex_namespace.c','coh_wr_tex_namespace.h','tex_namespace_oracle.py','check_tex_namespace.py','tests/test_tex_namespace.c','tests/test_tex_namespace_cpp.cpp','tests/tex_namespace_fixture.h','check_texname.py','qualification/texture-seed-eligibility-20261017/required-default-inputs.json']
NATIVE=[HERE.parent/'assets/coh_asset_loader.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
DEPS=[HERE/x for x in LOCAL]+[ROOT/x for x in ORIGINAL]+NATIVE+[HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/src/byte_reader.h',ROOT/'assets/character-avatar-defaults-manifest.json',ROOT/'assets/character-avatar-defaults.zip',ROOT/'assets/reference-inputs-manifest.json']
def sha(body):return hashlib.sha256(body).hexdigest()
def run(command,**kwargs):
 result=subprocess.run(list(map(str,command)),capture_output=True,timeout=180,**kwargs)
 if result.returncode:raise ValueError(result.stdout.decode(errors='replace')+result.stderr.decode(errors='replace'))
 return result.stdout
def load(name,path,pins):
 body=path.read_bytes()
 if sha(body)!=pins[str(path.relative_to(ROOT))]:raise ValueError('source helper changed')
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;exec(compile(body,str(path),'exec'),module.__dict__);return module
def exact(path,size,pin):
 with path.open('rb') as stream:body=stream.read(size+1)
 if len(body)!=size or sha(body)!=pin:raise ValueError('exact authentic source differs')
 return body
def prepare_bodies(default_zip,directory):
 archive=exact(default_zip,12308,'87a999e6c1c003b96a9fa169ce11637b61eb696766517e063fafce73fdc39c24')
 allow=json.loads((HERE/'qualification/texture-seed-eligibility-20261017/required-default-inputs.json').read_bytes())['required_defaults'];rows=[]
 with zipfile.ZipFile(default_zip) as z:
  report=z.read('default-headers.json');manifest=z.read('fresh-default-headers/manifest.json')
  if sha(report)!='ab1cf2773b540061c62fd9b42e3ca5f6d58e191805b8a35c8dbf0a06646789a5' or sha(manifest)!='1fe575013883344e4ce9f04d83739356e5605f9d6caf7e8190385f420ea5e2c5' or z.testzip() is not None:raise ValueError('exact actual staged admission receipt differs')
  files=json.loads(manifest)['files'];expected={'default-headers.json','fresh-default-headers/manifest.json'}|{'fresh-default-headers/'+x['filename'] for x in files}
  if len(z.namelist())!=9 or set(z.namelist())!=expected or len(files)!=7:raise ValueError('fixed source artifact inventory differs')
  for item,pin in zip(files,allow):
   body=z.read('fresh-default-headers/'+item['filename'])
   if len(body)!=pin['whole_body_bytes'] or sha(body)!=pin['whole_body_sha256'] or item['virtual_asset_path']!=pin['required_virtual_asset_path']:raise ValueError('exact actual default body differs')
   rows.append((item['virtual_asset_path'][5:],body))
 avatar=ROOT/'assets/character-avatar-defaults.zip';exact(avatar,1842488,'03f980c983702c2c9d21b0f674903e151129d0554b25d800b8724036f2cb4a29')
 raw=(ROOT/'assets/character-avatar-defaults-manifest.json').read_bytes()
 if sha(raw)!='2a96ff8fb24b686502d62e1e1ed25453681d4c15389c59b1f35ce3fbf1a5feb7':raise ValueError('exact avatar manifest differs')
 manifest=json.loads(raw)
 with zipfile.ZipFile(avatar) as z:
  if len(z.namelist())!=manifest['file_count'] or set(z.namelist())!=set(manifest['files']):raise ValueError('avatar source inventory differs')
  for path,pin in sorted(manifest['files'].items()):
   if not path.endswith('.texture'):continue
   body=z.read(path)
   if not path.startswith('data/texture_library/') or len(body)!=pin['bytes'] or sha(body)!=pin['sha256']:raise ValueError('actual avatar cached header differs')
   rows.append((path[5:],body))
 if len(rows)!=22:raise ValueError('exact seven defaults plus fifteen avatar bodies required')
 fixture=['static const Authentic authentic[]={'];pins=[]
 for i,(path,body) in enumerate(rows):
  name='auth-%03d.texture'%i;(directory/name).write_bytes(body);digest=sha(body);fixture.append('{'+json.dumps(path)+','+json.dumps(name)+','+str(len(body))+',{'+','.join('0x'+digest[k:k+2] for k in range(0,64,2))+'}},');pins.append({'path':path,'bytes':len(body),'sha256':digest})
 return '\n'.join(fixture+['};'])+'\n',pins,sha(archive)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-defaults-zip',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 if args.output.exists():raise ValueError('fresh output required')
 before={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS}
 if any(before[k]!=v for k,v in ORIGINAL.items()):raise ValueError('original source pin differs')
 old=load('namespace_source_extract',HERE/'check_texname.py',before);producer=load('namespace_original',HERE/'tex_namespace_oracle.py',before);oracle,functions,flags,wire=producer.create(ROOT,old.extract)
 reference=(ROOT/'assets/reference-inputs-manifest.json').read_bytes()
 if sha(reference)!='cf96742b1b65306356df69d065fcfb5bda0986ec8700d47ae1422452a1c0db7f':raise ValueError('exact retained path corpus differs')
 paths=[x['path'] for x in json.loads(reference)['files'] if x['path'].endswith('.texture')]
 if len(paths)!=8936 or len(set(x.lower() for x in paths))!=8936:raise ValueError('reference path-only corpus differs')
 projected='static const char*projected_paths[]={\n'+',\n'.join(map(json.dumps,paths))+'\n};\n';modes={};binaries={};objects={};stack=[];mutations=[]
 common=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',HERE,'-I',ROOT/'native-android/include']
 with tempfile.TemporaryDirectory(prefix='coh-source-namespace-') as raw:
  d=Path(raw);bodies=d/'bodies';bodies.mkdir();fixture,body_pins,artifact_sha=prepare_bodies(args.actual_defaults_zip,bodies);(d/'tex-namespace-authentic.h').write_text(fixture);(d/'tex-namespace-projected-paths.h').write_text(projected);(d/'original.c').write_text(oracle)
  for mode,extra in [('release',['-O2']),('address',['-O1','-fsanitize=address','-no-pie']),('undefined',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   standalone=d/(mode+'-native.o');run([*common,*extra,'-fstack-usage','-c',HERE/'coh_wr_tex_namespace.c','-o',standalone]);objects[mode]=sha(standalone.read_bytes())
   if mode=='release':stack=standalone.with_suffix('.su').read_text().splitlines()
   oracle_object=d/(mode+'-oracle.o');run([*common,*extra,'-Wno-pedantic','-Wno-unused-variable','-Wno-unused-parameter','-Wno-unused-but-set-variable','-Wno-sign-compare','-Wno-type-limits','-c',d/'original.c','-o',oracle_object]);binary=d/mode
   run([*common,*extra,'-I',d,HERE/'tests/test_tex_namespace.c',*NATIVE,oracle_object,'-Wl,--wrap=calloc','-lcrypto','-lz','-lm','-o',binary]);modes[mode]=json.loads(run([binary,bodies],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(binary.read_bytes())
  cpp=d/'cpp';core_objects=[]
  for i,path in enumerate(NATIVE):
   target=d/('core-'+str(i)+'.o');run([*common,'-O2','-c',path,'-o',target]);core_objects.append(target)
  run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-pedantic',HERE/'tests/test_tex_namespace_cpp.cpp',d/'release-native.o',*core_objects,'-lz','-lm','-o',cpp]);run([cpp]);cpp_sha=sha(cpp.read_bytes())
  native=(HERE/'coh_wr_tex_namespace.c').read_text();test=(HERE/'tests/test_tex_namespace.c').read_text();include='#include "../coh_wr_tex_namespace.c"'
  changes=[('reverse_directional_pig_DST','(int64_t)next->timestamp-old->timestamp==3600','(int64_t)old->timestamp-next->timestamp==3600'),('reverse_PIG_priority','next->location<=old->location','next->location>=old->location'),('drop_duplicate_rows','else{strcpy(b->key,r->basics[b->first].key);r->report.duplicates_retained++;}','else{continue;}'),('disable_LWC_skip','r->policy.lwc_active&&r->policy.lwc_last_completed_stage>1','0&&r->policy.lwc_active&&r->policy.lwc_last_completed_stage>1'),('bypass_aggregate_limit','n<=r->limits.aggregate_limit','1'),('omit_provider_retirement','if(r->held)r->policy.provider_drop(r->policy.provider_context);','if(0)r->policy.provider_drop(r->policy.provider_context);'),('bypass_reacquired_body_hash','status==COH_OK&&memcmp(digest,b->hash,32)','0')]
  if test.count(include)!=1:raise ValueError('private source include differs')
  for label,before_text,after_text in changes:
   expected=2 if label=='reverse_directional_pig_DST' else 1
   if native.count(before_text)!=expected:raise ValueError('mutation preimage differs '+label)
   source=d/(label+'.c');source.write_text(native.replace(before_text,after_text));wrapper=d/(label+'-test.c');wrapper.write_text(test.replace(include,'#include "'+str(source)+'"'));binary=d/label
   run([*common,'-O2','-I',d,'-I',HERE/'tests',wrapper,*NATIVE,d/'release-oracle.o','-Wl,--wrap=calloc','-lcrypto','-lz','-lm','-o',binary]);result=subprocess.run([binary,bodies],capture_output=True,timeout=180)
   if result.returncode==0:raise ValueError('production mutation escaped '+label)
   mutations.append(label)
 frames=[]
 for row in stack:
  columns=row.split('\t')
  if len(columns)!=3 or ('dynamic' in columns[2] and 'bounded' not in columns[2]):raise ValueError('unbounded module stack report')
  frames.append(int(columns[1]))
 module_stack_bound=sum(frames)
 if module_stack_bound>65536 or 'Frame frames[130]' not in native or native.count('scan_node(')!=2:raise ValueError('iterative module stack reserve differs')
 if before!={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in DEPS}:raise ValueError('source readmission differs')
 exact(args.actual_defaults_zip,12308,artifact_sha)
 proof={'passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_sha256':before,'actual_default_artifact':{'run':39078874753,'artifact':12118720382,'bytes':12308,'sha256':artifact_sha},'authentic_header_bodies':body_pins,'authentic_body_count':22,'authentic_bodies_are_not_a_complete_provider_namespace':True,'reference_paths':8936,'reference_path_headers_are_controlled_projections_not_authentic_bodies':True,'original_function_sha256_lf':{k:sha(v.encode()) for k,v in functions.items()},'original_functions_unchanged':True,'original_wire_type_sha256_lf':sha(wire.encode()),'original_flags_sha256_lf':sha(flags.encode()),'generated_oracle_sha256':sha(oracle.encode()),'generated_authentic_fixture_sha256':sha(fixture.encode()),'generated_path_projection_sha256':sha(projected.encode()),'modes':modes,'binary_sha256':binaries,'standalone_C_object_sha256':objects,'actual_C_object_CPP_call_link':{'passed':True,'binary_sha256':cpp_sha},'release_host_stack_usage':stack,'release_module_frame_sum_conservative_bytes':module_stack_bound,'module_own_preparation_reserve_bytes':65536,'native_scanner_iterative_fixed_frames':130,'maximum_258_byte_path_control_executed':True,'module_stack_claim_excludes_loader_provider_callbacks_libc_and_Android':True,'production_mutations_refused':mutations,'provider_fixture_is_declared_immutable_native_snapshot':True,'historical_original_mount_order_or_timestamp_reconstructed':False,'original_directory_OS_enumerator_or_watcher_executed':False,'original_full_provider_outer_functions_not_executed':['fileLoadDataDirs','FolderCacheAddFolderToNode','FolderCacheAddPig','fileScanAllDataDirs'],'original_TexOpt_lookup_observed_as_NULL':True,'original_file_stash_storage_and_pool_observers':True,'existing_loader_actual_PIGG_uncompressed_and_zlib_body_pins':True,'old_qualifiers_rerun':False,'current_provider_generation':False,'namespace_complete':False,'default_identity':False,'material_authority':False,'GPU':False,'world_authority':False,'Android_execution':False,'RSS_or_global_budget_claim':False}
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes}))
if __name__=='__main__':main()
