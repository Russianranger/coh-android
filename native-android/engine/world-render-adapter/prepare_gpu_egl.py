#!/usr/bin/env python3
"""Source-bound standalone EGL host execution and optional two-ABI NDK packaging."""
import argparse,hashlib,importlib.util,json,os,shutil,subprocess
from pathlib import Path
import gpu_egl_contract as contract
HERE=Path(__file__).resolve().parent

def call(command,output,label,env=None):
 p=subprocess.run(list(map(str,command)),capture_output=True,timeout=180,env=env)
 (output/(label+'.stdout')).write_bytes(p.stdout);(output/(label+'.stderr')).write_bytes(p.stderr)
 if p.returncode:raise ValueError('Command failed; preserved '+label+' logs')
 return p.stdout

def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],text=True,timeout=30).strip()
def packet(path):
 raw=path.read_bytes()
 if len(raw)!=3*349524 or hashlib.sha256(raw).hexdigest()!=contract.WHOLE_PACKET_SHA or any(hashlib.sha256(raw[i*349524:(i+1)*349524]).hexdigest()!=contract.PACKET_SHA for i in range(3)):raise ValueError('Exact all-stage GPU readback packet differs')
 return contract.WHOLE_PACKET_SHA

def prepare(args):
 root=args.source_root.resolve();output=args.output.resolve()
 if Path(__file__).resolve()!=root/'native-android/engine/world-render-adapter/prepare_gpu_egl.py':raise ValueError('Executing preparer must belong to source root')
 if output.exists():raise ValueError('New output directory required')
 if git(root,'status','--porcelain','--untracked-files=no'):raise ValueError('Clean committed tracked source required')
 source=contract.source_hashes(root)
 if set(git(root,'ls-files','--error-unmatch','--',*source).splitlines())!=set(source):raise ValueError('Every consumed source/helper must be committed')
 commit=git(root,'rev-parse','HEAD');tree=git(root,'rev-parse','HEAD^{tree}')
 prior=root/'native-android/engine/world-render-adapter/qualification/gpu-texture-model-20261017/host.json'
 if contract.sha(prior)!=contract.PRIOR_SHA:raise ValueError('Exact prior GPU source-model proof changed')
 old=json.loads(prior.read_text())
 for path,want in old['source_sha256'].items():
  if contract.sha(root/path)!=want:raise ValueError('Prior source qualification no longer matches '+path)
 raw=args.actual_texture.read_bytes();header=contract.fixture_header(raw)
 pins=json.loads((HERE/'egl-host-header-pins.json').read_text())
 for name,pin in pins.items():
  p=args.host_headers/name
  if p.stat().st_size!=pin['bytes'] or contract.sha(p)!=pin['sha256']:raise ValueError('Exact primary host header mismatch')
 output.mkdir(parents=True);(output/'box-1.texture').write_bytes(raw);(output/'egl_fixture_digest.h').write_bytes(header)
 source_list=[(root/'native-android/engine/world-render-adapter'/name).resolve() for name in contract.SOURCES]
 common=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-fno-fast-math','-ffp-contract=off','-I'+str(root/'native-android/include')]
 link=[args.host_egl.resolve(),args.host_gles.resolve(),'-lcrypto','-lz','-lm','-lpthread']
 env=dict(os.environ,EGL_PLATFORM='surfaceless',ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
 results={};library_before={str(p.resolve()):contract.sha(p.resolve()) for p in (args.host_egl,args.host_gles)}
 for mode,flags in {'release':['-O2'],'address':['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie'],'undefined':['-O1','-g','-fsanitize=undefined','-fno-omit-frame-pointer'],'finite-fixture':['-O2','-DCOH_EGL_FIXTURE_DIGEST','-I'+str(output)]}.items():
  exe=output/('host-'+mode);readback=output/(mode+'.rgba')
  call(['cc',*common,*flags,'-I'+str(args.host_headers),*source_list,*link,'-o',exe],output,'compile-'+mode)
  native=contract.native(json.loads(call([exe,output/'box-1.texture',readback],output,'execute-'+mode,env=env)),'host-linux')
  results[mode]={'native':native,'binary_sha256':contract.sha(exe),'packet_sha256':packet(readback)}
 # Independent per-mip DDS/Pillow oracle, beyond equal upload/readback callbacks.
 helper=root/'native-android/engine/world-render-adapter/check_sampler.py';spec=importlib.util.spec_from_file_location('qualified_cpu_texture_oracle',helper);oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
 first=output/'independent-first-chain.rgba';first.write_bytes((output/'release.rgba').read_bytes()[:349524]);pillow=oracle.texture_oracle(output/'box-1.texture',first)
 android={};ndk_identity=None
 if args.ndk:
  ndk=args.ndk.resolve();properties=(ndk/'source.properties').read_text()
  if 'Pkg.Revision = 28.2.13676358' not in properties:raise ValueError('Exact NDKr28c required')
  toolchain=ndk/'toolchains/llvm/prebuilt/linux-x86_64';ndk_identity={'revision':'28.2.13676358','source_properties_sha256':contract.sha(ndk/'source.properties'),'clang_sha256':contract.sha(toolchain/'bin/clang'),'headers_sha256':{p:contract.sha(toolchain/'sysroot/usr/include'/p) for p in pins}}
  for abi,(compiler,machine) in contract.ABI.items():
   directory=output/abi;directory.mkdir();exe=directory/'coh_gpu_egl_test'
   command=[toolchain/'bin'/compiler,*common,'-O2','-fPIE','-pie','-DCOH_EGL_FIXTURE_DIGEST','-I'+str(output),*source_list,'-lEGL','-lGLESv3','-lz','-lm','-o',exe]
   call(command,output,'compile-'+abi);contract.elf(exe,machine)
   android[abi]={'binary':str(exe.relative_to(output)),'binary_sha256':contract.sha(exe),'bytes':exe.stat().st_size,'elf_machine':machine,'compiler_sha256':contract.sha(toolchain/'bin'/compiler),'built':True,'executed':False}
 library_after={str(p.resolve()):contract.sha(p.resolve()) for p in (args.host_egl,args.host_gles)}
 if library_before!=library_after:raise ValueError('Declared host library files changed')
 if source!=contract.source_hashes(root) or git(root,'rev-parse','HEAD')!=commit or git(root,'status','--porcelain','--untracked-files=no'):raise ValueError('Source changed during qualification')
 proof={'schema':'coh-standalone-egl-v1','passed':True,'source_commit':commit,'source_tree':tree,'source_sha256':source,'prior_gpu_model_sha256':contract.PRIOR_SHA,'fixture_sha256':contract.FIXTURE_SHA,'fixture_bytes':43990,'fixture_header_sha256':contract.sha(output/'egl_fixture_digest.h'),'readback_sha256':contract.WHOLE_PACKET_SHA,'host':results,'pillow':pillow,'host_headers':pins,'host_library_files_before':library_before,'host_library_files_after':library_after,'host_loaded_mapping_verified':False,'system_driver_sanitized':False,'ndk':ndk_identity,'android':android,'android_executed':False,'host_actual_gles':True,'asan_leak_detection':False,'material_authority':False,'world_authority':False,'shipping_renderer_modified':False}
 (output/'qualification.json').write_text(json.dumps(proof,indent=2)+'\n');return proof

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('source-root','actual-texture','host-headers','host-egl','host-gles','output'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--ndk',type=Path);a=p.parse_args();r=prepare(a);print(json.dumps({'passed':True,'host_actual_gles':True,'android_built':list(r['android']),'android_executed':False}))
if __name__=='__main__':main()
