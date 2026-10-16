#!/usr/bin/env python3
"""Render actual panel/HUD composition with prepared authentic source-font bytes."""
import argparse
from collections import Counter
import ctypes as C
import ctypes.util
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from PIL import Image
from check import HERE,SOURCES,STRICT,run

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ndk',type=Path,required=True);p.add_argument('--font-dir',type=Path,required=True)
 p.add_argument('--font-manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 manifest=json.loads(a.font_manifest.read_text());assert manifest['font_sha256']=='714351827092d0ed290a8625a75780636b66c66fcc91d575bb80a633ae0c4329'
 header=(a.font_dir/'support_font.h').read_text();body=header.split('coh_hud_font_alpha[32768]={',1)[1].split('};',1)[0]
 alpha=bytes(int(v) for v in re.findall(r'\d+',body));assert hashlib.sha256(alpha).hexdigest()==manifest['alpha_sha256']
 os.environ.setdefault('EGL_PLATFORM','surfaceless');e=C.CDLL(ctypes.util.find_library('EGL'));glname=ctypes.util.find_library('GL');gl=C.CDLL(glname)
 e.eglGetDisplay.argtypes=[C.c_void_p];e.eglGetDisplay.restype=C.c_void_p;e.eglInitialize.argtypes=[C.c_void_p,C.POINTER(C.c_int),C.POINTER(C.c_int)]
 e.eglBindAPI.argtypes=[C.c_uint];e.eglChooseConfig.argtypes=[C.c_void_p,C.POINTER(C.c_int),C.POINTER(C.c_void_p),C.c_int,C.POINTER(C.c_int)]
 e.eglCreatePbufferSurface.argtypes=[C.c_void_p,C.c_void_p,C.POINTER(C.c_int)];e.eglCreatePbufferSurface.restype=C.c_void_p
 e.eglCreateContext.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.POINTER(C.c_int)];e.eglCreateContext.restype=C.c_void_p
 e.eglMakeCurrent.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p];e.eglDestroyContext.argtypes=[C.c_void_p,C.c_void_p]
 e.eglDestroySurface.argtypes=[C.c_void_p,C.c_void_p];e.eglTerminate.argtypes=[C.c_void_p];gl.glGetString.argtypes=[C.c_uint];gl.glGetString.restype=C.c_char_p
 display=e.eglGetDisplay(None);major=C.c_int();minor=C.c_int();surface=context=None;assert e.eglInitialize(display,C.byref(major),C.byref(minor))
 a.output.mkdir(parents=True,exist_ok=True)
 try:
  assert e.eglBindAPI(0x30a0);attrs=(C.c_int*13)(0x3033,1,0x3040,0x40,0x3024,8,0x3023,8,0x3022,8,0x3021,8,0x3038)
  config=C.c_void_p();count=C.c_int();assert e.eglChooseConfig(display,attrs,C.byref(config),1,C.byref(count)) and count.value
  surface=e.eglCreatePbufferSurface(display,config,(C.c_int*5)(0x3057,1280,0x3056,720,0x3038));context=e.eglCreateContext(display,config,None,(C.c_int*3)(0x3098,3,0x3038))
  assert surface and context and e.eglMakeCurrent(display,surface,surface,context)
  with tempfile.TemporaryDirectory(prefix='coh-panel-gles-') as d:
   tmp=Path(d);include=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/include'
   for name in ('GLES3','KHR'):shutil.copytree(include/name,tmp/name)
   lib=tmp/'demo.so';run(['gcc',*STRICT,'-O2','-shared','-fPIC','-I',tmp,'-I',a.font_dir,'-I',HERE.parent,
       *SOURCES,HERE/'gles_demo.c',HERE.parent/'coh_hud_gles.c',HERE.parent/'coh_hud_quad.c',HERE.parent/'coh_hud_atlas.c',
       f'-l:{glname}','-lm','-Wl,--no-undefined','-o',lib])
   native=C.CDLL(str(lib));native.presentation_demo.argtypes=[C.c_uint,C.c_void_p];native.presentation_demo.restype=C.c_int;outputs=[]
   for tab,name in enumerate(['details','inventory','enhancements','missions','contacts']):
    pixels=(C.c_ubyte*(1280*720*4))();draws=native.presentation_demo(tab,pixels);assert draws>100
    image=Image.frombytes('RGBA',(1280,720),bytes(pixels)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    png=a.output/(name+'.png');image.save(png)
    colors=Counter(image.get_flattened_data());checks={'source_health_green':colors[(80,235,52,255)]}
    if name=='missions':checks.update(source_mission_cyan=colors[(0,222,255,255)],source_completed_mission_green=colors[(0,255,68,255)])
    if name=='contacts':checks.update(source_completed_contact_green=colors[(0,255,51,255)])
    assert all(value>100 for value in checks.values()),'Expected source-color pixels missing from rendered panel'
    outputs.append({'tab':name,'panel_draws':draws,'source_color_pixels':checks,'png_sha256':hashlib.sha256(png.read_bytes()).hexdigest(),'png_bytes':png.stat().st_size})
  report={'status':'passed','scope':'Actual host software GLES3, existing authentic Montreal Heavy atlas, all five panels and bounded target/damage text; no real scene or Android/Adreno acceptance.',
      'renderer':gl.glGetString(0x1f01).decode(),'GL_version':gl.glGetString(0x1f02).decode(),'frames':5,'gl_errors':0,
      'font_sha256':manifest['font_sha256'],'alpha_sha256':manifest['alpha_sha256'],'font_header_sha256':hashlib.sha256(header.encode()).hexdigest(),
      'images':outputs,'source_hashes':{str(f.relative_to(HERE.parent.parent)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [*SOURCES,HERE/'gles_demo.c',HERE/'gles_check.py']}}
  (a.output/'qualification-gles.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
 finally:
  e.eglMakeCurrent(display,None,None,None)
  if context:e.eglDestroyContext(display,context)
  if surface:e.eglDestroySurface(display,surface)
  e.eglTerminate(display)
if __name__=='__main__':main()
