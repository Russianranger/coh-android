#!/usr/bin/env python3
"""Qualify the isolated canonical BGRA32 namespace-body adapter, host only."""
import argparse,hashlib,importlib.util,io,json,os,subprocess,tempfile,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
ORIGINAL={
 'upstream/ouroboros/Game/src/render/tex.c':'4507ee6fa752ed9452e78c4c989a9de0bdf93d81dd3597f1b1db063d73f1ca5c',
 'upstream/ouroboros/Game/src/render/tex.h':'56e56aea12a4126250f5f6f4d2211f62814b7eae4ad2598271f5423b60680552',
 'upstream/ouroboros/Game/src/render/thread/rt_tex.c':'5ce562b7184fa594eb0d678f7981fb5fb0f899b44a1e70c984949f68646fdaf5',
 'upstream/ouroboros/Game/src/render/thread/rt_tex.h':'c72efa76b355a4be9c77fcaa2ccc121cdec6c8dedbe3126271ddf43c7e7adcf2',
 'upstream/ouroboros/Game/src/render/dd.h':'6ad47ecd21afd291ac418b5cf84e1e810fe1c6cb98be0c50d7f3e62a98a25a5e'}
LOCAL=['coh_wr_tex_rgba32.c','coh_wr_tex_rgba32.h','check_tex_rgba32.py','tex_rgba32_oracle.py','tests/test_tex_rgba32.c','tests/test_tex_rgba32_cpp.cpp','tests/tex_rgba32_fixture.h','coh_wr_tex_namespace.c','coh_wr_tex_namespace.h']
NATIVE=[HERE/'coh_wr_tex_namespace.c',HERE.parent/'assets/coh_asset_loader.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
DEPS=list(dict.fromkeys([HERE/x for x in LOCAL]+[ROOT/x for x in ORIGINAL]+NATIVE+[HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'coh_contracts.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/src/byte_reader.h']))
def sha(b):return hashlib.sha256(b).hexdigest()
def run(command,**kwargs):
 result=subprocess.run(list(map(str,command)),capture_output=True,timeout=180,**kwargs)
 if result.returncode:raise ValueError(result.stdout.decode(errors='replace')+result.stderr.decode(errors='replace'))
 return result.stdout
def grey_body(path):
 with path.open('rb') as stream:archive=stream.read(12309)
 if len(archive)!=12308 or sha(archive)!='87a999e6c1c003b96a9fa169ce11637b61eb696766517e063fafce73fdc39c24':raise ValueError('exact retained default artifact differs')
 with zipfile.ZipFile(io.BytesIO(archive)) as z:
  if z.testzip() is not None:raise ValueError('artifact CRC differs')
  manifest=z.read('fresh-default-headers/manifest.json');report=z.read('default-headers.json')
  if sha(manifest)!='1fe575013883344e4ce9f04d83739356e5605f9d6caf7e8190385f420ea5e2c5' or sha(report)!='ab1cf2773b540061c62fd9b42e3ca5f6d58e191805b8a35c8dbf0a06646789a5':raise ValueError('actual admission receipts differ')
  files=json.loads(manifest)['files'];expected={'default-headers.json','fresh-default-headers/manifest.json'}|{'fresh-default-headers/'+x['filename'] for x in files}
  if len(files)!=7 or len(z.namelist())!=9 or set(z.namelist())!=expected:raise ValueError('fixed artifact inventory differs')
  rows=[x for x in files if x['virtual_asset_path']=='data/texture_library/world/filler/grey.texture']
  if len(rows)!=1:raise ValueError('exact grey identity missing')
  body=z.read('fresh-default-headers/'+rows[0]['filename'])
  if len(body)!=894 or sha(body)!='b628966e91a864f9edcb0634605823a7ef3d8e2305f36d1a9f6e9834b018a013':raise ValueError('exact authentic grey bytes differ')
  return body
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--actual-defaults-zip',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 if args.output.exists():raise ValueError('fresh output required')
 pins={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in DEPS}
 if any(pins[k]!=v for k,v in ORIGINAL.items()):raise ValueError('original source differs')
 helper=HERE/'tex_rgba32_oracle.py';raw=helper.read_bytes()
 if sha(raw)!=pins[str(helper.relative_to(ROOT))]:raise ValueError('source helper differs')
 spec=importlib.util.spec_from_file_location('rgba32_original',helper);module=importlib.util.module_from_spec(spec);exec(compile(raw,str(helper),'exec'),module.__dict__);oracle,functions,observers=module.create(ROOT)
 body=grey_body(args.actual_defaults_zip);modes={};binaries={};objects={};stack=[];mutations=[]
 common=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',HERE,'-I',ROOT/'native-android/include']
 with tempfile.TemporaryDirectory(prefix='coh-rgba32-') as raw_directory:
  d=Path(raw_directory);grey=d/'grey.texture';grey.write_bytes(body);original=d/'original.c';original.write_text(oracle)
  for mode,extra in [('release',['-O2']),('address',['-O1','-fsanitize=address','-no-pie']),('undefined',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   obj=d/(mode+'-native.o');run([*common,*extra,'-fstack-usage','-c',HERE/'coh_wr_tex_rgba32.c','-o',obj]);objects[mode]=sha(obj.read_bytes())
   if mode=='release':stack=obj.with_suffix('.su').read_text().splitlines()
   old=d/(mode+'-oracle.o');run([*common,*extra,'-Wno-sign-compare','-Wno-unused-parameter','-Wno-unused-variable','-Wno-unused-result','-Wno-pedantic','-Wno-pointer-sign','-c',original,'-o',old]);binary=d/mode
   run([*common,*extra,HERE/'tests/test_tex_rgba32.c',*NATIVE,old,'-Wl,--wrap=calloc','-Wl,--wrap=free','-lcrypto','-lz','-lm','-o',binary]);modes[mode]=json.loads(run([binary,grey],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(binary.read_bytes())
  core=[]
  for i,path in enumerate(NATIVE):
   obj=d/('core-'+str(i)+'.o');run([*common,'-O2','-c',path,'-o',obj]);core.append(obj)
  cpp=d/'cpp';run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-pedantic',HERE/'tests/test_tex_rgba32_cpp.cpp',d/'release-native.o',*core,'-lz','-lm','-o',cpp]);run([cpp]);cpp_sha=sha(cpp.read_bytes())
  source=(HERE/'coh_wr_tex_rgba32.c').read_text();test=(HERE/'tests/test_tex_rgba32.c').read_text();include='#include "../coh_wr_tex_rgba32.c"'
  changes=[('omit_red_blue_swap','target[at]=input[at+2]','target[at]=input[at]'),('force_opaque_alpha','target[at+3]=input[at+3]','target[at+3]=255'),('ignore_skip','plan.offset;uint8_t*target','128;uint8_t*target'),('admit_trailing_or_truncated_payload','if(total!=b->file_bytes)','if(0)'),('drop_lower_mips','i<plan.count;i++','i<1;i++'),('leak_source_lease','CohStatus released=coh_wr_tex_namespace_release(source,&lease)','CohStatus released=COH_OK'),('bypass_owned_limit','owned>bound.owned_limit','0'),('ignore_final_cancellation','if(stopped(cancel))status=COH_CANCELLED;','if(0)status=COH_CANCELLED;')]
  for label,before,after in changes:
   if source.count(before)!=1 or test.count(include)!=1:raise ValueError('mutation preimage differs '+label)
   changed=d/(label+'.c');changed.write_text(source.replace(before,after));wrapper=d/(label+'-test.c');wrapper.write_text(test.replace(include,'#include "'+str(changed)+'"'));binary=d/label
   run([*common,'-O2','-I',HERE/'tests',wrapper,*NATIVE,d/'release-oracle.o','-Wl,--wrap=calloc','-Wl,--wrap=free','-lcrypto','-lz','-lm','-o',binary]);result=subprocess.run([binary,grey],capture_output=True,timeout=180)
   if result.returncode==0:raise ValueError('semantic mutation escaped '+label)
   mutations.append(label)
 frames=[]
 for line in stack:
  parts=line.split('\t')
  if len(parts)!=3 or ('dynamic' in parts[2] and 'bounded' not in parts[2]):raise ValueError('unbounded native frame')
  frames.append(int(parts[1]))
 if sum(frames)>16384:raise ValueError('own module stack reserve too small')
 if pins!={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in DEPS} or body!=grey_body(args.actual_defaults_zip):raise ValueError('final readmission differs')
 proof={'passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_sha256':pins,'actual_source':{'run':39078874753,'artifact':12118720382,'archive_bytes':12308,'archive_sha256':'87a999e6c1c003b96a9fa169ce11637b61eb696766517e063fafce73fdc39c24','asset':'data/texture_library/world/filler/grey.texture','whole_body_bytes':894,'whole_body_sha256':sha(body),'wrapper_bytes':426,'DDS_bytes':468,'base_width':8,'base_height':8,'source_mip_count':4,'RGBA_mip_bytes':[256,64,16,4]},'original_functions_unchanged':True,'original_function_sha256_lf':{k:sha(v.encode()) for k,v in functions.items()},'original_observers':observers,'generated_oracle_sha256':sha(oracle.encode()),'modes':modes,'binary_sha256':binaries,'standalone_C_object_sha256':objects,'actual_C_object_CPP_call_link':{'passed':True,'binary_sha256':cpp_sha},'release_host_stack_usage':stack,'own_module_frame_sum_conservative_bytes':sum(frames),'own_preparation_reserve_bytes':16384,'stack_excludes_namespace_loader_callback_libc_Android':True,'mutations_refused':mutations,'source_selected_namespace_body_acquired_and_hash_rechecked':True,'source_pin_released_after_immutable_copy':True,'LeakSanitizer_executed':False,'LeakSanitizer_host_limitation':'ptrace/proc task enumeration unavailable; calloc/free and provider lease balance checked separately','protected_DXT_loader_modified':False,'old_qualifiers_rerun':False,'current_namespace':False,'default_identity':False,'effective_material_sampler':False,'GPU':False,'world':False,'Android_execution':False,'RSS_or_global_budget':False}
 proof['controlled_fixture_provider_external_bytes']='known body bytes + sizeof Memory + declared256KiB allowance; not a measured complete runtime/global budget'
 proof['late_cancellation_after_final_actual_pixel_store']=True
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes}))
if __name__=='__main__':main()
