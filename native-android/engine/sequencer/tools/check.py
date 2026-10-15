#!/usr/bin/env python3
"""Standalone opt-in qualification; never edits root builds or accepted gates."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent.parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE/"tools"))
import source_fixture
import original_oracle

def run(cmd,**kwargs):
    r=subprocess.run([str(x) for x in cmd],text=True,capture_output=True,**kwargs)
    if r.returncode:
        raise RuntimeError("command failed: "+" ".join(map(str,cmd))+"\n"+r.stdout+r.stderr)
    return r.stdout

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    p.add_argument("--source-root",help="Full repo/upstream directory or original ouroboros tree")
    p.add_argument("--asset-root",help="Original i24 tree (defaults to source-root sibling i24)")
    p.add_argument("--sanitize",action="store_true")
    p.add_argument("--android-clang")
    a=p.parse_args()
    target=Path(a.output).resolve()
    report_path=target if target.suffix==".json" else target/"report.json"
    build=report_path.parent/"sequencer-build";build.mkdir(parents=True,exist_ok=True)
    fixture=json.loads((HERE/"fixtures/source_graph.json").read_text())
    oracle=False
    if a.source_root:
        root=Path(a.source_root).resolve()
        if not (root/"Common/seq/seqsequence.c").exists():
            for candidate in (root/"upstream/ouroboros",root/"ouroboros"):
                if (candidate/"Common/seq/seqsequence.c").exists(): root=candidate;break
        assets=Path(a.asset_root).resolve() if a.asset_root else root.parent/"i24"
        actual=source_fixture.export(root,assets)
        if actual!=fixture: raise RuntimeError("Pinned original source/data fixture mismatch; inspect before admission")
        original_oracle.write(root,build/"original_oracle.c")
        oracle=True
    source_fixture.write_header(fixture,build/"source_graph.h")
    cc=os.environ.get("CC") or shutil.which("cc")
    if not cc: raise RuntimeError("C compiler unavailable")
    base=[cc,"-std=c11","-Wall","-Wextra","-I",HERE,"-I",build]
    outputs={}
    commands=[]
    for name,flags in [("host",["-O2"])] + ([("asan-ubsan",["-O1","-g","-fsanitize=address,undefined","-fno-omit-frame-pointer","-fno-pie","-no-pie"])] if a.sanitize else []):
        obj=build/(name+"-module.o")
        cmd=base+flags+["-Werror","-c",HERE/"coh_sequencer.c","-o",obj]
        run(cmd);commands.append(list(map(str,cmd)))
        undefined=run(["nm","-u",obj])
        forbidden=[s for s in ("malloc","calloc","realloc","free","pthread_mutex","fopen","open") if any(line.split()[-1]==s for line in undefined.splitlines() if line.split())]
        if forbidden: raise RuntimeError("unexpected hot path dependency: "+str(forbidden))
        exe=build/(name+"-test")
        cmd=base+flags+[HERE/"tests/test_sequencer.c",obj,HERE/"../../animation/coh_animation.c","-lm","-o",exe]
        if oracle: cmd += ["-DCOH_SEQ_ORACLE",build/"original_oracle.c","-Wno-unused-function","-Wno-unused-variable","-Wno-unused-but-set-variable"]
        run(cmd);commands.append(list(map(str,cmd)))
        # This executor's /proc task view prevents LeakSanitizer process scans.
        # ASan bounds/use-after-free and UBSan remain enabled; module has no heap
        # dependencies (checked independently above).
        env=os.environ.copy();env["ASAN_OPTIONS"]="detect_leaks=0:halt_on_error=1";env["UBSAN_OPTIONS"]="halt_on_error=1:print_stacktrace=1"
        outputs[name]=json.loads(run([exe],env=env));commands.append([str(exe)])
    android={"status":"not run; coordinator ARM64 build/device admission pending"}
    if a.android_clang:
        obj=build/"coh_sequencer-arm64.o"
        cmd=[a.android_clang,"-std=c11","-O2","-Wall","-Wextra","-Werror","-c",HERE/"coh_sequencer.c","-o",obj]
        run(cmd);commands.append(list(map(str,cmd)))
        android={"status":"ARM64 API26 object compiled; not emulator/device execution","object_sha256":hashlib.sha256(obj.read_bytes()).hexdigest(),"bytes":obj.stat().st_size}
    report={"gate":33,"status":"host-qualified bounded selection/timing module; full gate pending", "original_source_kernel_oracle":oracle,"source_moves":len(fixture["moves"]),"source_families":["jump","fall","combat kick","emote","knockdown cycle"],"host":outputs,"android":android,"physical_thor":"not run","emulator":"not run","leak_sanitizer":"not run: executor /proc task restrictions; ASan+UBSan enabled and module imports no heap allocator", "fixture_sha256":hashlib.sha256((HERE/"fixtures/source_graph.json").read_bytes()).hexdigest(),"module_sha256":{str(path.relative_to(HERE)):hashlib.sha256(path.read_bytes()).hexdigest() for path in [HERE/"coh_sequencer.c",HERE/"coh_sequencer.h",HERE/"tests/test_sequencer.c"]},"commands":commands,"limitations":["New non-ground encoded clips are not decoded/visually qualified; explicit authored source ranges are selection/timing evidence only.","Unresolved animation end frames remain ready=0; missing next-moves remain COH_SEQ_NONE and fail atomically.","Attachments, root motion, FX, per-bone transition blending, ragdolls and authoritative server reconciliation remain external/unqualified.","Performance is a host microbenchmark; no device gameplay FPS claim."]}
    report_path.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"report":str(report_path),"host":outputs,"android":android,"original_source_kernel_oracle":oracle},indent=2))

if __name__=="__main__":
    main()
