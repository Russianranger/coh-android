#!/usr/bin/env python3
"""Offline SupportUi adapter runtime, threading and ARM64 build qualification."""
import argparse
import ctypes.util
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from make_atlas import build

HERE=Path(__file__).resolve().parent
NATIVE=HERE.parents[2]
STRICT=["-std=c11","-Wall","-Wextra","-Werror","-Wpedantic"]

def run(command,**kwargs):
    p=subprocess.run([str(x) for x in command],capture_output=True,text=True,**kwargs)
    if p.returncode:raise RuntimeError(f"Command failed {p.returncode}: {command}\n{p.stdout}\n{p.stderr}")
    return p.stdout

def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument("--ndk",type=Path,required=True)
    fonts=p.add_mutually_exclusive_group(required=True);fonts.add_argument("--font",type=Path)
    fonts.add_argument("--font-header",type=Path,help="Previously admitted authentic generated support_font.h")
    p.add_argument("--font-preparation",type=Path,help="Original prepare_assets.py evidence admitting --font-header")
    p.add_argument("--source-root",type=Path,default=NATIVE.parent,help="Read-only coordinator source checkout to qualify")
    p.add_argument("--tray-corpus",type=Path,help="Optional pinned original tray texture cache")
    p.add_argument("--axis-checks",action="store_true",help="Also exercise coordinator atomic analog mailbox and repeat through public SupportUi")
    p.add_argument("--output",type=Path,required=True);p.add_argument("--sanitize",action="store_true");p.add_argument("--cc",default="gcc")
    a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="coh-support-ui-") as directory:
        temp=Path(directory);font=temp/"generated";native=a.source_root.resolve()/"native-android"
        gameplay=native/"engine/ui/gameplay";support=native/"support-client/src"
        sources=[support/"support_ui.c",gameplay.parent/"coh_ui.c",gameplay.parent/"coh_hud.c",gameplay/"coh_hud_android.c",
                 gameplay/"coh_hud_atlas.c",gameplay/"coh_hud_quad.c",gameplay/"coh_hud_gles.c",gameplay/"coh_hud_axis_navigation.c"]
        if a.font:
            manifest=build(a.font,font);shutil.copyfile(font/"atlas.h",font/"support_font.h")
        else:
            if not a.font_preparation:raise ValueError("--font-header requires original --font-preparation evidence")
            preparation=json.loads(a.font_preparation.read_text());raw=a.font_header.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=preparation["font_header_sha256"]:raise ValueError("Prepared font-header SHA256 differs")
            manifest=preparation["font"]
            if manifest["font_sha256"]!="714351827092d0ed290a8625a75780636b66c66fcc91d575bb80a633ae0c4329":raise ValueError("Prepared original font identity differs")
            font.mkdir();(font/"support_font.h").write_bytes(raw)
        spec=importlib.util.spec_from_file_location("support_tray_prepare",HERE/"tray/prepare.py")
        tray=importlib.util.module_from_spec(spec);spec.loader.exec_module(tray);tray_manifest=tray.build(font,a.tray_corpus)
        include=a.ndk/"toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr/include"
        for name in ("GLES3","KHR"):shutil.copytree(include/name,temp/name)
        gl=ctypes.util.find_library("GL");egl=ctypes.util.find_library("EGL")
        if not gl or not egl:raise RuntimeError("Host EGL/GL unavailable")
        test=gameplay/"tests/support_ui_test.c";tests_sources=[test]
        if a.axis_checks:
            text=test.read_text().replace('#include "../../../../support-client/src/support_ui.h"','#include "support_ui.h"\nextern void root_axis_adapter_checks(void);')
            text=text.replace('result=run_support_ui_tests();','root_axis_adapter_checks();result=run_support_ui_tests();')
            test=temp/"support_ui_axis_test.c";test.write_text(text);tests_sources=[test,HERE/"tests/root_axis_adapter_test.c"]
        command=[a.cc,*STRICT,"-DSUPPORT_UI_TEST_MAIN","-I",font,"-I",gameplay,"-I",support,"-I",temp,*sources,*tests_sources,
                 f"-l:{gl}",f"-l:{egl}","-lm","-lpthread"]
        binary=temp/"support-ui-tests";run([*command,"-O2","-o",binary]);rows=[json.loads(line) for line in run([binary]).splitlines()];tests=rows[-1]
        report={"module":"offline SupportUi mutex adapter","host":"passed","tests":tests,"font_sha256":manifest["font_sha256"],
                "allocation":"One initialization calloc; fixed arena thereafter. Mutex serializes all public update/render/snapshot methods. Caller owns lifetime shutdown.",
                "emulator":"not run","physical_thor":"not run","thread_scope":"Observed mutex stress; TSan not run",
                "source_root":str(a.source_root.resolve()),"source_commit":run(["git","rev-parse","HEAD"],cwd=a.source_root).strip(),
                "generated_tray_images":len(tray_manifest["records"]),"generated_tray_rgba_bytes":sum(r["rgba_bytes"] for r in tray_manifest["records"])}
        if a.axis_checks:report["axis_tests"]=rows[0]
        if a.sanitize:
            sanitized=temp/"support-ui-tests-sanitized"
            run([*command,"-O1","-g","-fno-omit-frame-pointer","-fsanitize=address,undefined","-o",sanitized])
            env=dict(os.environ,ASAN_OPTIONS="detect_leaks=0:abort_on_error=1",UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
            rows=[json.loads(line) for line in run([sanitized],env=env).splitlines()]
            report["sanitizer_tests"]=rows[-1];report["sanitizers"]="ASan + UBSan passed; LSan disabled"
            if a.axis_checks:report["sanitizer_axis_tests"]=rows[0]
        else:report["sanitizers"]="not run"
        compiler=a.ndk/"toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang"
        artifact=temp/"libcoh_support_ui.so"
        android=[compiler,*STRICT,"-O2","-fPIC","-shared","-I",font,"-I",gameplay,*sources,"-lm","-lGLESv3","-Wl,--no-undefined","-o",artifact]
        run(android);report["android"]={"status":"ARM64 built","api":26,"bytes":artifact.stat().st_size,"sha256":hashlib.sha256(artifact.read_bytes()).hexdigest(),
                                         "execution":"not run; host EGL execution is separate"}
        report["source_hashes"]={str(f.relative_to(native)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [*sources,support/"support_ui.h",gameplay/"tests/support_ui_test.c"]}
        report["generated_font_header_sha256"]=hashlib.sha256((font/"support_font.h").read_bytes()).hexdigest()
        report["generated_tray_header_sha256"]=hashlib.sha256((font/"support_tray.h").read_bytes()).hexdigest()
        report["qualification_test_hashes"]={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in tests_sources}
        a.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"output":str(a.output),"host":"passed","android":"ARM64 built"}))

if __name__=="__main__":main()
