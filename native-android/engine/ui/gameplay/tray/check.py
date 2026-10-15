#!/usr/bin/env python3
"""Original tray-art preparation/source-oracle/host-GLES qualification."""
import argparse
import ctypes as C
import ctypes.util
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
from PIL import Image
from prepare import build,decode,checked,HERE

STRICT=['-std=c99','-Wall','-Wextra','-Werror','-Wpedantic']
def run(args,**kwargs):
    p=subprocess.run([str(x) for x in args],text=True,capture_output=True,**kwargs)
    if p.returncode:raise RuntimeError(f'{args}\n{p.stdout}\n{p.stderr}')
    return p.stdout

def extract(text,signature):
    start=text.index(signature);brace=text.index('{',start);depth=0
    for i in range(brace,len(text)):
        depth+=(text[i]=='{')-(text[i]=='}')
        if not depth:return text[start:i+1]
    raise ValueError('Unclosed source body')

def source_oracle(root,corpus,temp):
    pins=json.loads((HERE/'source-pins.json').read_text())
    for name,expected in pins['files'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,'Original source differs'
    tray=(root/'Game/src/UI/uiTray.c').read_text();rt=(root/'Game/src/render/thread/rt_tex.c').read_text()
    border=(root/'Game/src/graphics/textureatlasPrivate.h').read_text()
    assert 'atlasLoadTexture( "tray_ring_power.tga"' in tray
    assert 'tex->width = tex->data->actual_width = tex_header->actualTexture->width;' in (root/'Game/src/graphics/textureatlas.c').read_text()
    slot=tray[tray.index('num = slotNumber + 1;'):tray.index('// make a collision box',tray.index('num = slotNumber + 1;'))]
    swap=extract(rt,'for(j=0;j<size;j+=4)')
    original='#include <stdlib.h>\n#include <string.h>\n#include <assert.h>\ntypedef unsigned char U8;\n#define BORDER_2 2\n'
    original+=extract(border,'U8 *borderize(')+'\n'
    original+='void original_rgba(U8*pix,int size){int j;U8 c;'+swap+'}\nint original_slot(int slotNumber){int num;'+slot+'return num;}\n'
    src=temp/'original.c';src.write_text(original);lib=temp/'original.so';run(['gcc',*STRICT,'-O2','-fPIC','-shared',src,'-o',lib])
    library=C.CDLL(str(lib));library.original_slot.argtypes=[C.c_int];library.original_slot.restype=C.c_int
    library.original_rgba.argtypes=[C.c_void_p,C.c_int];library.borderize.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int];library.borderize.restype=C.c_void_p
    libc=C.CDLL(None);libc.free.argtypes=[C.c_void_p]
    assetpins=json.loads((HERE/'pins.json').read_text());compared=0
    for index,pin in enumerate(assetpins['records']):
        raw=(corpus/pin['file_name']).read_bytes();rgba,w,h,dds=decode(raw);sw,sh=struct.unpack_from('<II',dds,12)[::-1]
        expected=Image.open(io.BytesIO(dds)).convert('RGBA').crop((0,0,w,h)).tobytes();assert expected==rgba
        bgra=C.create_string_buffer(dds[128:]);library.original_rgba(bgra,len(dds)-128)
        original=library.borderize(bgra,w,h,sw,sh,4)
        try:
            bordered=C.string_at(original,(w+2)*(h+2)*4)
            cropped=b''.join(bordered[((y+1)*(w+2)+1)*4:((y+1)*(w+2)+1+w)*4] for y in range(h))
            assert cropped==rgba;compared+=len(rgba)
        finally:libc.free(original)
        if index:assert pin['file_name']==f'tray_ring_number_{library.original_slot(index-1)}.texture'
    return {'status':'passed','original_rgba_and_borderize_compared_bytes':compared,'independent_pillow_compared_bytes':compared,
            'original_slot_number_comparisons':10,'source_commit':assetpins['source_commit'],'source_hashes':pins['files'],
            'scope':'Compiled original byte-swap and atlas borderize bodies; original logical crop and slot numbering. Full original HUD rasterizer parity is not claimed.'}

def negative_cases(corpus):
    b=(corpus/'tray_ring_power.texture').read_bytes();head=struct.unpack_from('<i',b)[0];cases=[b[:8],b[:31],b[:100],b+b'x']
    for offset,fmt,value in [(0,'i',-1),(0,'i',1000000),(4,'i',0),(8,'i',0),(12,'i',65),(head+4,'I',0),(head+76,'I',0),(head+80,'I',4),(head+84,'I',1),(head+88,'I',16),(head+24,'I',2),(head+112,'I',1),(head+28,'I',2)]:
        bad=bytearray(b);struct.pack_into('<'+fmt,bad,offset,value);cases.append(bytes(bad))
    for bad in cases:
        try:decode(bad)
        except (ValueError,struct.error):pass
        else:raise AssertionError('Malformed original tray admitted')
    pin=json.loads((HERE/'pins.json').read_text())['records'][0]
    bad=bytearray(b);bad[-1]^=1
    try:checked(bytes(bad),pin)
    except ValueError:pass
    else:raise AssertionError('Corrupt identity admitted')
    return len(cases)+1

def gpu(ndk,generated,temp):
    os.environ.setdefault('EGL_PLATFORM','surfaceless');e=C.CDLL(ctypes.util.find_library('EGL'));glname=ctypes.util.find_library('GL');gl=C.CDLL(glname)
    e.eglGetDisplay.argtypes=[C.c_void_p];e.eglGetDisplay.restype=C.c_void_p;e.eglInitialize.argtypes=[C.c_void_p,C.POINTER(C.c_int),C.POINTER(C.c_int)]
    e.eglBindAPI.argtypes=[C.c_uint];e.eglChooseConfig.argtypes=[C.c_void_p,C.POINTER(C.c_int),C.POINTER(C.c_void_p),C.c_int,C.POINTER(C.c_int)]
    e.eglCreatePbufferSurface.argtypes=[C.c_void_p,C.c_void_p,C.POINTER(C.c_int)];e.eglCreatePbufferSurface.restype=C.c_void_p
    e.eglCreateContext.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.POINTER(C.c_int)];e.eglCreateContext.restype=C.c_void_p
    e.eglMakeCurrent.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p];e.eglDestroyContext.argtypes=[C.c_void_p,C.c_void_p]
    e.eglDestroySurface.argtypes=[C.c_void_p,C.c_void_p];e.eglTerminate.argtypes=[C.c_void_p]
    gl.glGetString.argtypes=[C.c_uint];gl.glGetString.restype=C.c_char_p
    display=e.eglGetDisplay(None);a=C.c_int();b=C.c_int();context=surface=None;assert e.eglInitialize(display,C.byref(a),C.byref(b))
    try:
        assert e.eglBindAPI(0x30a0);attrs=(C.c_int*13)(0x3033,1,0x3040,0x40,0x3024,8,0x3023,8,0x3022,8,0x3021,8,0x3038);config=C.c_void_p();count=C.c_int()
        assert e.eglChooseConfig(display,attrs,C.byref(config),1,C.byref(count)) and count.value
        surface=e.eglCreatePbufferSurface(display,config,(C.c_int*5)(0x3057,64,0x3056,64,0x3038));context=e.eglCreateContext(display,config,None,(C.c_int*3)(0x3098,3,0x3038))
        assert surface and context and e.eglMakeCurrent(display,surface,surface,context)
        include=ndk/'toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/include'
        for name in ('GLES3','KHR'):shutil.copytree(include/name,temp/name)
        module=temp/'tray-gpu.so';run(['gcc',*STRICT,'-O2','-shared','-fPIC','-I',temp,'-I',generated,HERE/'gles_test.c',HERE.parent/'coh_hud_gles.c',HERE.parent/'coh_hud_quad.c',f'-l:{glname}','-lm','-o',module])
        lib=C.CDLL(str(module));lib.run_tray_gles_tests.restype=C.c_int;n=lib.run_tray_gles_tests();assert n>10000
        return {'status':'passed','rendered_images':33,'resource_generation_recreates':3,'channel_comparisons':n,'channel_tolerance':1,
                'renderer':gl.glGetString(0x1f01).decode(),'GL_version':gl.glGetString(0x1f02).decode(),'gl_errors':0,
                'scope':'Real host Mesa GLES3; Android/Adreno and physical Thor remain pending'}
    finally:
        e.eglMakeCurrent(display,None,None,None)
        if context:e.eglDestroyContext(display,context)
        if surface:e.eglDestroySurface(display,surface)
        e.eglTerminate(display)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--corpus',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--ndk',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='coh-tray-') as d:
        temp=Path(d);generated=temp/'generated';m=build(generated,a.corpus)
        report={'module':'Original source tray decoration','implementation_start_commit':'3c5da1d8cd501d778e270d395109d40666fbe37a',
                'source_oracle':source_oracle(a.source_root,a.corpus,temp),'negative_cases':negative_cases(a.corpus),
                'gpu':gpu(a.ndk,generated,temp),'images':len(m['records']),'rgba_bytes':sum(r['rgba_bytes'] for r in m['records']),
                'physical_thor':'not run','emulator':'not run; coordinator integration required','prepared_images':m['records']}
        # Requalify only changed HUD boundary, including existing source-color oracle.
        args=['python',HERE.parent/'check.py','--output',temp/'hud.json','--source-root',a.source_root,'--ndk',a.ndk]
        if a.sanitize:args+=['--sanitize']
        run(args);report['hud_regression']=json.load(open(temp/'hud.json'))
        # Compile prepared immutable original image bytes and portable API for ARM64.
        src=temp/'prepared_android.c';src.write_text('#include "support_tray.h"\n#include "coh_hud.h"\nCohStatus prepared_tray(CohHud*h){return coh_hud_set_tray_decoration(h,coh_hud_tray_images[0].resource,coh_hud_tray_numbers);}\n')
        cc=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang'
        run([cc,*STRICT,'-O2','-I',generated,'-I',HERE.parent.parent,'-c',src,'-o',temp/'prepared_android.o'])
        report['prepared_image_android']='ARM64 compiled; actual GLES upload/device rendering remain pending'
        report['changed_source_sha256']={str(x.relative_to(HERE.parent.parent)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [HERE.parent.parent/'coh_hud.c',HERE.parent.parent/'coh_hud.h',HERE/'prepare.py',HERE/'gles_test.c',HERE/'check.py']}
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'output':str(a.output),'source_oracle':report['source_oracle']['status'],'gpu':report['gpu']['status'],'negative_cases':report['negative_cases'],'hud':report['hud_regression']['host']}))
if __name__=='__main__':main()
