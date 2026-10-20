#!/usr/bin/env python3
"""Actual Mesa full-default-framebuffer downsample/state restoration, not Thor."""
import argparse,ctypes as C,hashlib,json,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;NATIVE=HERE.parents[1];CPP=HERE.parent/'app/src/main/cpp'
sys.path.insert(0,str(NATIVE/'engine/renderer/tests'));from gpu_check import EGL
p=argparse.ArgumentParser();p.add_argument('--gles-headers',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--fullscreen',action='store_true');a=p.parse_args();a.work.mkdir(parents=True,exist_ok=False)
# Host libc remains authoritative: import only graphics declarations from NDK.
includes=a.work/'include';includes.mkdir()
for sub in ('GLES3','KHR'):
 (includes/sub).symlink_to((a.gles_headers/sub).resolve(),target_is_directory=True)
sources=[CPP/'session_frame_capture_gl.c',CPP/'session_frame_capture_gl.h',CPP/'session_frame_capture.h'];pins={str(s):hashlib.sha256(s.read_bytes()).hexdigest()for s in sources}
libpath=a.work/'capture-gl.so';r=subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic',*(['-DCOH_FULLSCREEN_DIAGNOSTIC=1']if a.fullscreen else []),'-O2','-fstack-usage','-shared','-fPIC','-I',str(includes),str(sources[0]),'-l:libGL.so.1','-o',str(libpath)],capture_output=True,text=True,timeout=180)
if r.returncode:raise RuntimeError(r.stderr)
lib=C.CDLL(str(libpath));lib.coh_frame_capture_readback.argtypes=[C.c_uint]*4+[C.c_void_p]
e=EGL();g=e.g;U=C.c_uint
for n,res,args in [('glScissor',None,[C.c_int]*4),('glPixelStorei',None,[U,C.c_int]),('glGetIntegerv',None,[U,C.POINTER(C.c_int)]),('glIsEnabled',C.c_ubyte,[U])]:e.gf(n,res,args)
e.ef('eglCreatePbufferSurface',C.c_void_p,[C.c_void_p,C.c_void_p,C.POINTER(C.c_int)]);e.ef('eglDestroySurface',U,[C.c_void_p,C.c_void_p]);checks=0
vw,vh,tw,th=(1280,720,640,360)if a.fullscreen else(400,200,192,96)
for cycle in range(2):
 surface=e.e.eglCreatePbufferSurface(e.display,e.config,(C.c_int*5)(0x3057,vw,0x3056,vh,0x3038));assert surface
 assert e.e.eglMakeCurrent(e.display,surface,surface,e.context)
 g.glBindFramebuffer(0x8d40,0);g.glViewport(0,0,vw,vh);g.glEnable(0x0c11)
 for x,y,color in [(0,0,(1,0,0,1)),(vw//2,0,(0,1,0,1)),(0,vh//2,(0,0,1,1)),(vw//2,vh//2,(1,1,0,1))]:g.glScissor(x,y,vw//2,vh//2);g.glClearColor(*color);g.glClear(0x4000)
 # Nondefault pack/scissor state must not crop or overrun the bounded buffer.
 g.glScissor(7,9,11,13)
 for key,val in [(0x0d05,8),(0x0d02,211),(0x0d04,3),(0x0d03,2)]:g.glPixelStorei(key,val)
 size=tw*th*4;out=(C.c_ubyte*(size+32))(*([173]*(size+32)))
 assert lib.coh_frame_capture_readback(vw,vh,tw,th,C.byref(out,16));checks+=1
 raw=bytes(out)[16:-16];assert bytes(out)[:16]==bytes([173]*16)==bytes(out)[-16:];checks+=1
 for x,y,color in [(0,0,(255,0,0,255)),(tw-1,0,(0,255,0,255)),(0,th-1,(0,0,255,255)),(tw-1,th-1,(255,255,0,255))]:assert tuple(raw[(y*tw+x)*4:(y*tw+x+1)*4])==color;checks+=1
 for key,val in [(0x0d05,8),(0x0d02,211),(0x0d04,3),(0x0d03,2)]:v=C.c_int();g.glGetIntegerv(key,C.byref(v));assert v.value==val;checks+=1
 assert g.glIsEnabled(0x0c11) and g.glGetError()==0;checks+=1
 assert not lib.coh_frame_capture_readback(vw,vh,641 if a.fullscreen else 193,th,C.byref(out,16));checks+=1
 assert e.e.eglMakeCurrent(e.display,None,None,e.context);assert e.e.eglDestroySurface(e.display,surface)
 if not cycle:e.recreate_context()
e.close();assert pins=={str(s):hashlib.sha256(s.read_bytes()).hexdigest()for s in sources}
result={'passed':True,'checks':checks,'identity':e.identity,'source_sha256':pins,'whole_framebuffer_four_corners':True,'context_recreation':True,'source_viewport':[vw,vh],'capture_dimensions':[tw,th],'RGBA_bytes':size,'gl_errors':0,'physical_Thor':False,'driver_memory_measured':False}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
