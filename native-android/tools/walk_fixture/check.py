#!/usr/bin/env python3
"""Qualify bounded WALK against an independently compiled original-source oracle."""
import argparse
import ctypes as C
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('walk_original_oracle',HERE/'oracle.py')
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)

def run(command,env=None):
    p=subprocess.run(list(map(str,command)),text=True,capture_output=True,timeout=120,env=env)
    if p.returncode:raise RuntimeError(' '.join(map(str,command))+'\n'+p.stdout+p.stderr)
    return p.stdout

def identity(path):
    b=path.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root',type=Path,default=ROOT)
    ap.add_argument('--world-source',type=Path)
    ap.add_argument('--grid-header',type=Path)
    ap.add_argument('--fixture',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--disable-leak-sanitizer',action='store_true',
        help='Use only when local container procfs/ptrace prevents LeakSanitizer; hosted CI keeps leak detection enabled.')
    args=ap.parse_args()
    source_files=['coh_walk.c','coh_walk_selftest.c','source_world.c','source_ctri.c','source_tritri.c']
    sources=[ROOT/'native-android/walk'/x for x in source_files]+[ROOT/'native-android/motion/coh_motion.c']
    common=[os.environ.get('CC','cc'),'-std=c11','-O1','-fno-fast-math','-ffp-contract=off','-fno-strict-aliasing','-Wall','-Wextra','-Werror',
        '-Wno-unused-variable','-Wno-unused-parameter','-Wno-unused-but-set-variable','-Wno-unused-function','-Wno-misleading-indentation']
    with tempfile.TemporaryDirectory(prefix='coh-walk-check-') as directory:
        tmp=Path(directory);original=tmp/'original.json';velocity=tmp/'velocity.json';slide=tmp/'slide.json';lib=tmp/'adapter.so'
        command=[os.environ.get('PYTHON','python3'),HERE/'oracle.py','--source-root',args.source_root,'--output',original,
            '--goldens-json',velocity,'--slide-goldens-json',slide]
        if args.world_source:command+=['--world-source',args.world_source]
        if args.grid_header:command+=['--grid-header',args.grid_header]
        run(command)
        run(common+['-shared','-fPIC',*sources,'-lm','-o',lib])
        native=C.CDLL(str(lib));native.coh_walk_velocity_probe.argtypes=[C.c_float,C.c_uint,C.c_uint,*[C.POINTER(C.c_float)]*4]
        velocity_rows=json.loads(velocity.read_text());max_error=0.0
        for dt,flags,state,inp,vel,norm,expected in velocity_rows:
            out=(C.c_float*3)();native.coh_walk_velocity_probe(dt,flags,state,*[(C.c_float*3)(*v)for v in(inp,vel,norm)],out)
            error=max(abs(a-b)for a,b in zip(out,expected));max_error=max(max_error,error)
            if not all(abs(a-b)<=.00001 for a,b in zip(out,expected)):raise AssertionError(('original velocity mismatch',dt,flags,state,list(out),expected))
        native.coh_walk_slide_probe.argtypes=[*[C.POINTER(C.c_float)]*3,C.c_uint,C.POINTER(C.c_float),C.c_int,C.POINTER(C.c_float),C.POINTER(C.c_uint)]
        slide_rows=json.loads(slide.read_text());max_slide_error=0.0
        for top,bot,vel,count,contacts,fallback,expected,status in slide_rows:
            out=(C.c_float*9)();st=(C.c_uint*4)()
            native.coh_walk_slide_probe(*[(C.c_float*3)(*v)for v in(top,bot,vel)],count,(C.c_float*9)(*contacts),fallback,out,st)
            error=max(abs(a-b)for a,b in zip(out,expected));max_slide_error=max(max_slide_error,error)
            if error>.00001 or list(st)!=status:raise AssertionError(('original SlideWall mismatch',list(out),expected,list(st),status))
        env={**os.environ,'ASAN_OPTIONS':'detect_leaks='+('0' if args.disable_leak_sanitizer else '1'),
            'UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'}
        sanitizer=tmp/'sanitizer';run(common+['-g','-fsanitize=address,undefined',HERE/'sanitizer.c',*sources,'-lm','-o',sanitizer])
        adapter_checks=json.loads(run([sanitizer],env))
        scene_driver=tmp/'scene';run(common+['-g','-fsanitize=address,undefined',HERE/'scene_driver.c',*sources,'-lm','-o',scene_driver])
        authored_checks=json.loads(run([scene_driver,args.fixture],env))
        receipt={'schema':'coh-native-bounded-walk-qualification-v1','passed':True,
            'original_source':json.loads(original.read_text()),'source_velocity_cases':len(velocity_rows),
            'source_slide_transcripts':len(slide_rows),'max_velocity_error':max_error,'max_slide_error':max_slide_error,
            'authored_fixture':{'filename':args.fixture.name,**identity(args.fixture)},'adapter_sanitizer':adapter_checks,
            'authored_scene_sanitizer':authored_checks,'asan_ubsan_passed':True,
            'leak_sanitizer_enabled':not args.disable_leak_sanitizer,
            'leak_detection':'disabled by explicit local-container option; allocations explicitly destroyed' if args.disable_leak_sanitizer else 'enabled; no allocator leaks detected',
            'scope':'Original active WALK velocity/feet/head/wall and CTri query kernels in bounded authored static geometry; neutral source modifiers, fixed 30Hz, source max five substeps; no entity collision, jumping/powers/full tracker streaming/server prediction.',
            'physical_gates19_21_accepted':False,
            'runtime_sources':{x:identity(ROOT/'native-android/walk'/x)for x in source_files}}
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps({k:receipt[k]for k in ['passed','source_velocity_cases','source_slide_transcripts','max_velocity_error','max_slide_error','asan_ubsan_passed']}))
if __name__=='__main__':main()
