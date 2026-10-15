#!/usr/bin/env python3
"""Offline SupportUi adapter runtime, threading and ARM64 build qualification."""
import argparse
import ctypes.util
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from make_atlas import build

HERE=Path(__file__).resolve().parent
NATIVE=HERE.parents[2]
SUPPORT=NATIVE/"support-client/src"
SOURCES=[SUPPORT/"support_ui.c",HERE.parent/"coh_ui.c",HERE.parent/"coh_hud.c",HERE/"coh_hud_android.c",
         HERE/"coh_hud_atlas.c",HERE/"coh_hud_quad.c",HERE/"coh_hud_gles.c"]
STRICT=["-std=c99","-Wall","-Wextra","-Werror","-Wpedantic"]

def run(command,**kwargs):
    p=subprocess.run([str(x) for x in command],capture_output=True,text=True,**kwargs)
    if p.returncode:raise RuntimeError(f"Command failed {p.returncode}: {command}\n{p.stdout}\n{p.stderr}")
    return p.stdout

def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument("--ndk",type=Path,required=True);p.add_argument("--font",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True);p.add_argument("--sanitize",action="store_true");p.add_argument("--cc",default="gcc")
    a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="coh-support-ui-") as directory:
        temp=Path(directory);font=temp/"generated";manifest=build(a.font,font)
        shutil.copyfile(font/"atlas.h",font/"support_font.h")
        include=a.ndk/"toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/include"
        for name in ("GLES3","KHR"):shutil.copytree(include/name,temp/name)
        gl=ctypes.util.find_library("GL");egl=ctypes.util.find_library("EGL")
        if not gl or not egl:raise RuntimeError("Host EGL/GL unavailable")
        command=[a.cc,*STRICT,"-DSUPPORT_UI_TEST_MAIN","-I",font,"-I",HERE,"-I",temp,*SOURCES,HERE/"tests/support_ui_test.c",
                 f"-l:{gl}",f"-l:{egl}","-lm","-lpthread"]
        binary=temp/"support-ui-tests";run([*command,"-O2","-o",binary]);tests=json.loads(run([binary]))
        report={"module":"offline SupportUi mutex adapter","host":"passed","tests":tests,"font_sha256":manifest["font_sha256"],
                "allocation":"One initialization calloc; fixed arena thereafter. Mutex serializes all public update/render/snapshot methods. Caller owns lifetime shutdown.",
                "emulator":"not run","physical_thor":"not run","thread_scope":"Observed mutex stress; TSan not run"}
        if a.sanitize:
            sanitized=temp/"support-ui-tests-sanitized"
            run([*command,"-O1","-g","-fno-omit-frame-pointer","-fsanitize=address,undefined","-o",sanitized])
            env=dict(os.environ,ASAN_OPTIONS="detect_leaks=0:abort_on_error=1",UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
            report["sanitizer_tests"]=json.loads(run([sanitized],env=env));report["sanitizers"]="ASan + UBSan passed; LSan disabled"
        else:report["sanitizers"]="not run"
        compiler=a.ndk/"toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang"
        artifact=temp/"libcoh_support_ui.so"
        android=[compiler,*STRICT,"-O2","-fPIC","-shared","-I",font,"-I",HERE,*SOURCES,"-lm","-lGLESv3","-Wl,--no-undefined","-o",artifact]
        run(android);report["android"]={"status":"ARM64 built","api":26,"bytes":artifact.stat().st_size,"sha256":hashlib.sha256(artifact.read_bytes()).hexdigest(),
                                         "execution":"not run; host EGL execution is separate"}
        report["source_hashes"]={str(f.relative_to(NATIVE)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [*SOURCES,SUPPORT/"support_ui.h",HERE/"tests/support_ui_test.c"]}
        a.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"output":str(a.output),"host":"passed","android":"ARM64 built"}))

if __name__=="__main__":main()
