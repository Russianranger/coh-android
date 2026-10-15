#!/usr/bin/env python3
"""Real software-host GLES3 backend checks; never Android/Adreno qualification."""
import ctypes as C
import ctypes.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import json
import hashlib

HERE=Path(__file__).resolve().parent

def run_gles(ndk,cc="gcc",font=None):
    os.environ.setdefault("EGL_PLATFORM","surfaceless")
    library=ctypes.util.find_library("EGL");gl_library=ctypes.util.find_library("GL")
    if not library or not gl_library:raise RuntimeError("Host EGL/GL loader unavailable")
    e=C.CDLL(library);gl=C.CDLL(gl_library)
    e.eglGetDisplay.argtypes=[C.c_void_p];e.eglGetDisplay.restype=C.c_void_p
    e.eglInitialize.argtypes=[C.c_void_p,C.POINTER(C.c_int),C.POINTER(C.c_int)]
    e.eglBindAPI.argtypes=[C.c_uint]
    e.eglChooseConfig.argtypes=[C.c_void_p,C.POINTER(C.c_int),C.POINTER(C.c_void_p),C.c_int,C.POINTER(C.c_int)]
    e.eglCreatePbufferSurface.argtypes=[C.c_void_p,C.c_void_p,C.POINTER(C.c_int)];e.eglCreatePbufferSurface.restype=C.c_void_p
    e.eglCreateContext.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.POINTER(C.c_int)];e.eglCreateContext.restype=C.c_void_p
    e.eglMakeCurrent.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p]
    e.eglDestroyContext.argtypes=[C.c_void_p,C.c_void_p];e.eglDestroySurface.argtypes=[C.c_void_p,C.c_void_p]
    e.eglTerminate.argtypes=[C.c_void_p]
    gl.glGetString.argtypes=[C.c_uint];gl.glGetString.restype=C.c_char_p
    display=e.eglGetDisplay(None);major=C.c_int();minor=C.c_int();surface=context=None
    if not e.eglInitialize(display,C.byref(major),C.byref(minor)):raise RuntimeError("Host EGL initialize failed")
    try:
        assert e.eglBindAPI(0x30a0) # EGL_OPENGL_ES_API
        attributes=(C.c_int*13)(0x3033,1,0x3040,0x40,0x3024,8,0x3023,8,0x3022,8,0x3021,8,0x3038)
        config=C.c_void_p();count=C.c_int()
        assert e.eglChooseConfig(display,attributes,C.byref(config),1,C.byref(count)) and count.value
        surface=e.eglCreatePbufferSurface(display,config,(C.c_int*5)(0x3057,64,0x3056,64,0x3038))
        context=e.eglCreateContext(display,config,None,(C.c_int*3)(0x3098,3,0x3038))
        assert surface and context and e.eglMakeCurrent(display,surface,surface,context)
        version=gl.glGetString(0x1f02).decode();renderer=gl.glGetString(0x1f01).decode()
        with tempfile.TemporaryDirectory(prefix="coh-hud-gles-") as directory:
            temp=Path(directory)
            # Only portable Khronos headers are copied; host libc headers remain native.
            include=ndk/"toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/include"
            for name in ("GLES3","KHR"):shutil.copytree(include/name,temp/name)
            output=temp/"hud-gles.so"
            command=[cc,"-std=c99","-Wall","-Wextra","-Werror","-Wpedantic","-O2","-fPIC","-shared","-I",str(temp),
                     str(HERE/"coh_hud_gles.c"),str(HERE/"coh_hud_quad.c"),str(HERE/"tests/gles_test.c"),
                     "-Wl,--no-undefined",f"-l:{gl_library}","-lm","-o",str(output)]
            if font:
                from make_atlas import build
                atlas=temp/"font";manifest=build(font,atlas)
                command+=["-DCOH_HUD_REAL_FONT","-I",str(atlas),"-I",str(HERE),str(HERE/"coh_hud_atlas.c")]
            p=subprocess.run(command,capture_output=True,text=True)
            if p.returncode:raise RuntimeError(p.stderr)
            module=C.CDLL(str(output));module.run_hud_gles_tests.restype=C.c_int
            assert module.run_hud_gles_tests()==0
            font_report={"status":"not run; pass --font"}
            if font:
                module.run_hud_original_font_tests.restype=C.c_int
                comparisons=module.run_hud_original_font_tests();assert comparisons>1000
                font_report={"status":"passed","font_sha256":manifest["font_sha256"],"glyphs":len(manifest["glyphs"]),
                             "pixel_comparisons":comparisons,"channel_tolerance":1,"alpha_sha256":manifest["alpha_sha256"]}
        return {"status":"passed","EGL":f"{major.value}.{minor.value}","GL_version":version,"renderer":renderer,
                "pixel_comparisons":4,"channel_tolerance":1,"negative_cases":5,"bounded_batch_quads":128,
                "batch_draw_calls":2,"gl_errors":0,"authentic_font_gpu":font_report,
                "source_hashes":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (HERE/"coh_hud_gles.c",HERE/"coh_hud_gles.h",HERE/"coh_hud_quad.c",HERE/"tests/gles_test.c")},
                "scope":"Actual GLES3 shaders/batching/R8 alpha/blending/scissor on host software GPU; Android/Adreno pending"}
    finally:
        e.eglMakeCurrent(display,None,None,None)
        if context:e.eglDestroyContext(display,context)
        if surface:e.eglDestroySurface(display,surface)
        e.eglTerminate(display)

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(__doc__);p.add_argument("--ndk",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--font",type=Path)
    a=p.parse_args();report=run_gles(a.ndk,font=a.font);a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report))
