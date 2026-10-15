#!/usr/bin/env python3
import argparse,hashlib,json,os,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
NATIVE=HERE.parents[2]
def run(cmd,env=None):
    r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,env=env)
    if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    return r.stdout
def main():
    p=argparse.ArgumentParser();p.add_argument('--rig-directory',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--android-clang',type=Path)
    a=p.parse_args();out=a.output.resolve();out.parent.mkdir(parents=True,exist_ok=True);build=out.parent/'adapter-build';build.mkdir(exist_ok=True)
    cc=os.environ.get('CC') or shutil.which('cc');sources=[NATIVE/'support-client/src/support_animation.c',HERE.parent/'coh_seq_playback.c',HERE.parent/'coh_sequencer.c',NATIVE/'animation/coh_animation.c']
    clips=[a.rig_directory/('huge-'+name+'.bin') for name in ['1_2punch','jump_n_smash','fallout']];results={}
    for name,flags in [('host',['-O2']),('asan-ubsan',['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie'])]:
        exe=build/(name+'-adapter-test');run([cc,'-std=c11','-Wall','-Wextra','-Werror',*flags,'-I',NATIVE/'support-client/src',HERE/'tests/adapter_test.c',*sources,'-lm','-o',exe])
        env=os.environ.copy();env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1';results[name]=json.loads(run([exe,*clips],env))
    clang=a.android_clang or Path('/workspace/scratch/cd30b2fc1c9e/toolchains/android-ndk-r28c/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang')
    android={'status':'not run'}
    if clang.exists():
        obj=build/'support_animation-arm64.o';run([clang,'-std=c11','-O2','-Wall','-Wextra','-Werror','-c',sources[0],'-o',obj]);android={'status':'ARM64 API26 object built; no Android execution','sha256':hashlib.sha256(obj.read_bytes()).hexdigest(),'bytes':obj.stat().st_size}
    result={'schema':'coh-support-animation-adapter-v1','host':results,'android':android,'physical_thor':'not run','module_sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in [sources[0],sources[0].with_suffix('.h')]},'clips':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in clips},'scope':'isolated neutral Huge raw clip mock playback; accepted grounded code unchanged','limitations':['No morph hierarchy composition, gameplay graph side effects, live session or Android execution proof.','ASan and UBSan active; LeakSanitizer disabled for executor /proc limitation.']}
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
