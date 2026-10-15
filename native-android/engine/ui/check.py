#!/usr/bin/env python3
"""Standalone Gate 34 checks. Source comparisons execute extracted original C bodies."""
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent

def run(args, **kwargs):
    result=subprocess.run([str(x) for x in args], capture_output=True, text=True, **kwargs)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {args}\n{result.stdout}\n{result.stderr}")
    return result.stdout

def body(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for pos in range(brace, len(text)):
        depth += (text[pos] == "{") - (text[pos] == "}")
        if not depth:
            return text[start:pos+1]
    raise ValueError("Unclosed original function")

def source_checks(root, temp, cc):
    if (root / "upstream/ouroboros").is_dir():
        root = root / "upstream/ouroboros"
    expected = json.loads((HERE / "docs/source-hashes.json").read_text())["files"]
    observed = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in expected}
    if observed != expected:
        raise AssertionError("Original source hashes changed; audit before requalification")
    sprite = (root / "Game/src/UI/sprite/sprite_base.c").read_text()
    focus = (root / "Game/src/UI/uiFocus.c").read_text()
    # The shipping runtime predicate is explicitly shell=true, loading=false.
    oracle = r'''
#include <assert.h>
#include <stdbool.h>
#include <string.h>
#define devassert assert
#define FALSE 0
#define DEFAULT_SCRN_WD 1024
#define DEFAULT_SCRN_HT 768
#define SPRITE_XY_NO_SCALE 1
typedef float F32;
static int wd_,ht_,letter_,sSpriteScalingMode;
static void windowClientSize(int *w,int *h){*w=wd_;*h=ht_;}
static int isLetterBoxMenu(void){return letter_;}
static int loadingScreenVisible(void){return 0;}
static int shell_menu(void){return 1;}
'''
    oracle += body(sprite, "void calc_scrn_scaling_with_offset(")
    oracle += r'''
void original_scale(int mode,int width,int height,float *o){
    wd_=width;ht_=height;letter_=mode==2;sSpriteScalingMode=mode;
    calc_scrn_scaling_with_offset(o,o+1,o+2,o+3);
}
typedef int (*LostFocusFunction)(void*,void*);
int uiGetFocusExDbg(void*,bool,LostFocusFunction,char*,char*,int);
'''
    oracle += re.sub(r"^#include[^\n]*", "", focus, flags=re.M)
    oracle += r'''
void original_focus_init(void){uiReturnAllFocus();}
int original_focus_set(int id){
    if(!id){uiReturnAllFocus();return 0;}
    return uiGetFocusDbg((void*)(long)id,id==3,0,0,0)?0:1;
}
int original_focus_id(void){return (int)(long)activeRequest.obj;}
int original_focus_editable(void){return uiFocusIsEditable();}
'''
    source = temp / "original_ui_oracle.c"
    source.write_text(oracle)
    shared = temp / "ui-oracle.so"
    run([cc,"-std=c99","-O2","-fPIC","-shared",source,HERE/"coh_ui.c",HERE/"tests/oracle_bridge.c","-lm","-o",shared])
    lib = C.CDLL(str(shared))
    for name in ("original_scale", "native_scale"):
        getattr(lib,name).argtypes = [C.c_int,C.c_int,C.c_int,C.POINTER(C.c_float)]
    rng = random.Random(34)
    resolutions = [(1024,768),(1280,720),(1920,1080),(720,1280),(1,1),(32768,32768)]
    resolutions += [(rng.randint(1,32768),rng.randint(1,32768)) for _ in range(250)]
    count = 0
    for mode in range(3):
        for width,height in resolutions:
            expected_,actual = (C.c_float*4)(),(C.c_float*4)()
            lib.original_scale(mode,width,height,expected_)
            assert lib.native_scale(mode,width,height,actual)==0
            for x,y in zip(expected_,actual):
                assert abs(x-y)<=0.002, (mode,width,height,list(expected_),list(actual))
            count += 1
    lib.original_focus_init();lib.native_focus_init()
    trace=[0,1,1,2,3,3,0,2,0]
    trace += [rng.randrange(4) for _ in range(250)]
    for id_ in trace:
        assert lib.original_focus_set(id_)==lib.native_focus_set(id_)==0
        assert lib.original_focus_id()==lib.native_focus_id()
        assert lib.original_focus_editable()==lib.native_focus_editable()
    lib.coh_ui_utf8.argtypes=[C.c_char_p,C.c_int,C.POINTER(C.c_size_t)]
    unicode_cases=0
    corpus=[b"",b"hello",b"\n",b"\t",b"\x7f",b"\xed\xa0\x80",b"\xf4\x90\x80\x80"]
    corpus += [bytes(rng.randint(1,255) for _ in range(rng.randrange(1,24))) for _ in range(4096)]
    for _ in range(256):
        cp=rng.randrange(0x110000)
        if cp and not 0xd800<=cp<=0xdfff:corpus.append(chr(cp).encode("utf8"))
    for single in (0,1):
        for raw in corpus:
            try:
                decoded=raw.decode("utf8")
                valid=all(ord(c)!=127 and (ord(c)>=32 or (not single and c in "\n\t")) for c in decoded)
            except UnicodeDecodeError:valid=False
            n=C.c_size_t(999)
            status=lib.coh_ui_utf8(raw,single,C.byref(n))
            assert (status==0)==valid,(raw,single,status)
            assert n.value==(len(raw) if valid else 999)
            unicode_cases+=1
    return {"status":"passed","source_files":len(observed),"hashes":observed,
            "original_scaling_cases":count,"original_focus_trace_steps":len(trace),
            "python_utf8_reference_cases":unicode_cases,
            "scope":"Exact original shell scaling/letterbox and single-owner editable focus bodies; no font raster/GPU parity claim"}

def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--source-root",type=Path)
    p.add_argument("--sanitize",action="store_true")
    p.add_argument("--cc",default=os.environ.get("CC","gcc"))
    args=p.parse_args()
    output=args.output if args.output.suffix==".json" else args.output/"qualification.json"
    output.parent.mkdir(parents=True,exist_ok=True)
    report={"gate":34,"module":"native game UI framework","host":"running","android":"not run","emulator":"not run","physical_thor":"not run"}
    with tempfile.TemporaryDirectory(prefix="coh-ui-") as temp_:
        temp=Path(temp_)
        binary=temp/"ui-test"
        command=[args.cc,"-std=c99","-Wall","-Wextra","-Werror","-Wpedantic","-O2",HERE/"coh_ui.c",HERE/"tests/ui_test.c","-lm","-o",binary]
        run(command);report["host_tests"]=json.loads(run([binary]))
        report["host_command"]=[str(x) for x in command]
        undefined=run(["nm","-u",binary])
        assert not re.search(r"\b(malloc|calloc|realloc|free)(?:@|$)",undefined,re.M)
        report["no_heap_imports"]=True
        if args.sanitize:
            sanitized=temp/"ui-test-sanitized"
            san=[args.cc,"-std=c99","-Wall","-Wextra","-Werror","-Wpedantic","-O1","-g","-fno-omit-frame-pointer","-fsanitize=address,undefined",HERE/"coh_ui.c",HERE/"tests/ui_test.c","-lm","-o",sanitized]
            run(san)
            # This execution environment prevents LSan's /proc task inspection.
            # This module owns no heap; malloc-family imports are checked above.
            env=dict(os.environ,ASAN_OPTIONS="detect_leaks=0:abort_on_error=1",UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
            report["sanitizer_tests"]=json.loads(run([sanitized],env=env))
            report["sanitizers"]="ASan + UBSan passed; LSan disabled (/proc task/ptrace environment limitation)"
        else:report["sanitizers"]="not run"
        if args.source_root:
            report["source_oracle"]=source_checks(args.source_root,temp,args.cc)
        else:report["source_oracle"]={"status":"not run; pass --source-root"}
        report["host"]="passed"
        report["source_files"]={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ("coh_ui.h","coh_ui.c","tests/ui_test.c","tests/oracle_bridge.c")}
        report["qualification"]="host qualified framework only" if args.source_root and args.sanitize else "host implementation checks passed; incomplete qualification"
        output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"output":str(output),"host":report["host"],"qualification":report["qualification"]}))

if __name__=="__main__":main()
