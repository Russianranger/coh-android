#!/usr/bin/env python3
"""Isolated analog-focus hysteresis/repeat policy; no device acceptance inferred."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
SOURCES=[HERE.parent/'coh_ui.c',HERE.parent/'coh_hud.c',HERE/'coh_hud_axis_navigation.c']
STRICT=['-std=c99','-Wall','-Wextra','-Werror','-Wpedantic']
def run(command,**kwargs):
    p=subprocess.run([str(x) for x in command],capture_output=True,text=True,**kwargs)
    if p.returncode:raise RuntimeError(f'{command}\n{p.stdout}\n{p.stderr}')
    return p.stdout

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ndk',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='coh-hud-axis-') as d:
        temp=Path(d);binary=temp/'axis-test';run(['gcc',*STRICT,'-O2',*SOURCES,HERE/'tests/axis_navigation_test.c','-lm','-o',binary])
        report={'module':'Additive mobile analog HUD-focus policy','host':'passed','tests':json.loads(run([binary])),
                'source_policy':'New mobile focus hysteresis/repeat contract; original desktop stick timing parity is not claimed. Calls existing source-qualified coh_hud_action only.',
                'source_baseline':'0b75ade0c801735e10c5798f641948a45cc50488','implementation_start_commit':'e6f5d4b190d60480e178b9bf6ce33859e457ef46',
                'emulator':'not run; coordinator must wire selected stick and frame ticks','physical_thor':'not run','sanitizers':'not run'}
        assert not re.search(r'\b(malloc|calloc|realloc|free)(?:@|$)',run(['nm','-u',binary]),re.M)
        if a.sanitize:
            sanitized=temp/'axis-sanitized';run(['gcc',*STRICT,'-O1','-g','-fno-omit-frame-pointer','-fsanitize=address,undefined',*SOURCES,HERE/'tests/axis_navigation_test.c','-lm','-o',sanitized])
            report['sanitizer_tests']=json.loads(run([sanitized],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')))
            report['sanitizers']='ASan + UBSan passed; LSan disabled; caller-owned fixed storage'
        toolchain=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin';lib=temp/'libcoh_hud_axis.so'
        run([toolchain/'aarch64-linux-android26-clang',*STRICT,'-O2','-fPIC','-shared',*SOURCES,'-lm','-Wl,--no-undefined','-o',lib])
        assert 'AArch64' in run([toolchain/'llvm-readelf','-h',lib]);assert not re.search(r'\b(malloc|calloc|realloc|free)(?:@|$)',run([toolchain/'llvm-nm','-u',lib]),re.M)
        report['android']={'status':'ARM64 built','api':26,'bytes':lib.stat().st_size,'sha256':hashlib.sha256(lib.read_bytes()).hexdigest(),'execution':'not run'}
        report['no_direct_allocator_imports']=True
        report['source_hashes']={str(f.relative_to(HERE.parent)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [*SOURCES,HERE/'coh_hud_axis_navigation.h',HERE/'tests/axis_navigation_test.c']}
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'output':str(a.output),'host':report['host'],'sanitizers':report['sanitizers'],'android':report['android']['status']}))
if __name__=='__main__':main()
