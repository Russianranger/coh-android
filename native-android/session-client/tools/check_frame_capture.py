#!/usr/bin/env python3
"""Bounded current-frame owner: source bytes, overflow, atomic replacement and cleanup."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;CPP=HERE.parent/'app/src/main/cpp'
p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.work.mkdir(parents=True,exist_ok=False)
sources=[CPP/'session_frame_capture.c',CPP/'session_frame_capture.h',HERE/'test_frame_capture.c'];pins={str(s):hashlib.sha256(s.read_bytes()).hexdigest()for s in sources};modes={}
for mode,flags in [('release',['-O2','-fstack-usage']),('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
 binary=a.work/mode;command=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I',str(CPP),str(sources[0]),str(sources[2]),'-Wl,--wrap=calloc,--wrap=free','-lm','-o',str(binary)]
 r=subprocess.run(command,capture_output=True,text=True,timeout=180)
 if r.returncode:raise RuntimeError(r.stderr)
 r=subprocess.run([str(binary)],capture_output=True,text=True,timeout=60,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 modes[mode]=json.loads(r.stdout)
assert pins=={str(s):hashlib.sha256(s.read_bytes()).hexdigest()for s in sources}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'passed':True,'source_sha256':pins,'modes':modes,'actual_framebuffer_readback':False,'leak_sanitizer_executed':False,'scope':'Portable capture owner only; GL, JNI and Android export qualification separate.'},indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes}))
