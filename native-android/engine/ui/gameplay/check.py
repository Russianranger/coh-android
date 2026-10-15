#!/usr/bin/env python3
"""Opt-in Gates 34-36 HUD qualification. No accepted UI/Session files are changed."""
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

HERE=Path(__file__).resolve().parent
UI=HERE.parent
SOURCES=[UI/"coh_ui.c",UI/"coh_hud.c",HERE/"coh_hud_android.c",HERE/"coh_hud_atlas.c",HERE/"coh_hud_quad.c"]
STRICT=["-std=c99","-Wall","-Wextra","-Werror","-Wpedantic"]

def run(command,**kwargs):
    p=subprocess.run([str(x) for x in command],capture_output=True,text=True,**kwargs)
    if p.returncode:
        raise RuntimeError(f"Command failed ({p.returncode}): {command}\n{p.stdout}\n{p.stderr}")
    return p.stdout

def extract(text,signature):
    start=text.index(signature);brace=text.index("{",start);depth=0
    for pos in range(brace,len(text)):
        depth+=(text[pos]=="{")-(text[pos]=="}")
        if not depth:return text[start:pos+1]
    raise ValueError(f"Unclosed source function {signature}")

def source_root(path):
    for root in (path,path/"upstream/ouroboros",path.parent/"upstream/ouroboros"):
        if (root/"Game/src/UI/uiStatus.c").is_file():return root
    raise FileNotFoundError("Pass the full repository with upstream/ouroboros, or that source root")

def source_oracle(root,temp,cc):
    root=source_root(root)
    status=(root/"Game/src/UI/uiStatus.c").read_text()
    sprite=(root/"Game/src/UI/sprite/sprite_base.c").read_text()
    provenance=json.loads((HERE/"docs/source-hashes.json").read_text())
    observed={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in provenance["files"]}
    assert observed==provenance["files"],"Original bytes changed; audit before requalification"
    # Compile original threshold functions and byte interpolation, not handwritten expected tables.
    prefix="""#include <stdint.h>\n#include <stdbool.h>\ntypedef uint32_t U32;\n"""
    defines="\n".join(line for line in status.splitlines() if re.match(r"#define (OUT_OF_PHASE_COLOR|FULL_HEALTH_COLOR|MED_HEALTH_COLOR|LOW_HEALTH_COLOR|FULL_HEALTH_THRESHOLD|MED_HEALTH_THRESHOLD|LOW_HEALTH_THRESHOLD|FULL_ENDURANCE_COLOR|LOW_ENDURANCE_COLOR|FULL_ENDURANCE_THRESHOLD|LOW_ENDURANCE_THRESHOLD)\s",line))
    oracle=prefix+defines+"\n"+extract(sprite,"static int interp(")+"\n"+extract(sprite,"void interp_rgba(")+"\n"
    oracle+=extract(status,"int getHealthColor(")+"\n"+extract(status,"static int getEnduranceColor(")+"\n"
    oracle+="uint32_t original_health(int phase,float p){return (uint32_t)getHealthColor(phase,p);}\n"
    oracle+="uint32_t original_endurance(float p){return (uint32_t)getEnduranceColor(p);}\n"
    source=temp/"original_hud_oracle.c";source.write_text(oracle)
    shared=temp/"hud-oracle.so"
    run([cc,"-std=c99","-O2","-shared","-fPIC",source,*SOURCES,"-lm","-o",shared])
    lib=C.CDLL(str(shared))
    for name in ("original_health","coh_hud_health_color"):
        getattr(lib,name).argtypes=[C.c_int,C.c_float];getattr(lib,name).restype=C.c_uint32
    for name in ("original_endurance","coh_hud_endurance_color"):
        getattr(lib,name).argtypes=[C.c_float];getattr(lib,name).restype=C.c_uint32
    rng=random.Random(3436);values=[-1,0,.2,.3,.4,.6,.7,1,2,float("nan"),float("inf"),-float("inf")]
    values+=[i/8192 for i in range(8193)]+[rng.uniform(-2,2) for _ in range(2048)]
    checks=0
    for p in values:
        for phase in (0,1):
            assert lib.original_health(phase,p)==lib.coh_hud_health_color(phase,p),(phase,p)
            checks+=1
        assert lib.original_endurance(p)==lib.coh_hud_endurance_color(p),p;checks+=1
    tray=(root/"Common/gameComm/trayCommon.h").read_text()
    assert re.search(r"#define TRAY_WD\s+\( 10 \)",tray)
    assert re.search(r"#define TRAY_HT\s+\( 1 \)",tray)
    fonts=(root/"Game/src/UI/sprite/sprite_font.c").read_text()
    assert re.search(r'ttMontBold\s*=\s*ttFontLoadCached\("mont_hvbold.ttf", 1\)',fonts)
    assert re.search(r'ttMontBold->glyphGenMode\s*=\s*TTGGM_NOHINT',fonts)
    core=(root/"Game/src/graphics/truetype/ttFontCore.c").read_text()
    assert re.search(r'case TTGGM_NOHINT:\s*flag = FT_LOAD_NO_HINTING;',core)
    return {"status":"passed","color_reference_comparisons":checks,"primary_tray_slots":10,
            "original_font_load_policy":"mont_hvbold.ttf, NOHINT/FT_LOAD_NO_HINTING, normal grayscale",
            "files":observed,"scope":"Original health/endurance color/interp bodies and ten-slot primary tray. Layout mock, no font/GPU parity."}

def font_check(font,temp,cc):
    from fontTools.ttLib import TTFont
    from make_atlas import build,render
    hashes=json.loads((HERE/"docs/font-provenance.json").read_text())
    expected={r["name"].split("/")[-1]:r["sha256"] for r in hashes["records"]}
    assert hashlib.sha256(font.read_bytes()).hexdigest()==expected[font.name],"Original asset font identity differs"
    directory=temp/"authentic-font-atlas";manifest=build(font,directory)
    table=TTFont(font);cmap=table.getBestCmap();upem=table["head"].unitsPerEm;deltas=[]
    for g in manifest["glyphs"]:
        advance=table["hmtx"][cmap[g["codepoint"]]][0]*16/upem
        delta=abs(g["advance"]-advance);assert delta<=1/64;deltas.append(delta)
    table.close()
    original,_=render(font);packed=(directory/"atlas.alpha").read_bytes();occupied=set()
    for glyph,source in zip(manifest["glyphs"],original):
        for y in range(glyph["height"]):
            offset=(glyph["y"]+y)*manifest["width"]+glyph["x"]
            assert packed[offset:offset+glyph["width"]]==source["alpha"][y*glyph["width"]:(y+1)*glyph["width"]]
            occupied.update(range(offset,offset+glyph["width"]))
    assert not any(v for i,v in enumerate(packed) if i not in occupied)
    source=temp/"authentic_atlas_test.c"
    source.write_text('''#include <assert.h>
#include "atlas.h"
int main(void){CohUiGlyph glyph;unsigned c;
assert(coh_hud_atlas_validate(&coh_hud_font)==COH_OK);
for(c=32;c<127;c++)assert(coh_hud_atlas_glyph(&coh_hud_font,1,c,16,&glyph)==COH_OK);
assert(coh_hud_atlas_glyph(&coh_hud_font,1,0x1f3ae,16,&glyph)==COH_OK);
assert(sizeof(coh_hud_font_alpha)==COH_HUD_FONT_WIDTH*COH_HUD_FONT_HEIGHT);return 0;}
''')
    binary=temp/"authentic_atlas_test"
    run([cc,*STRICT,"-O2","-I",HERE,"-I",directory,source,HERE/"coh_hud_atlas.c","-lm","-o",binary]);run([binary])
    failures=0
    for kwargs in ({"size":0},{"codepoints":range(513)},{"codepoints":[65,65]},{"codepoints":[0xd800]}):
        try:render(font,**kwargs)
        except ValueError:failures+=1
        else:raise AssertionError("Malformed atlas input accepted")
    malformed=temp/"malformed.ttf";malformed.write_bytes(b"bad original font")
    try:render(malformed)
    except ValueError:failures+=1
    else:raise AssertionError("Malformed font accepted")
    return {"status":"passed","font":font.name,"font_sha256":manifest["font_sha256"],"glyphs":len(manifest["glyphs"]),
            "negative_inputs":failures,"fonttools_advance_max_delta_px":max(deltas),"advance_tolerance_px":1/64,
            "alpha_bytes":manifest["alpha_bytes"],"alpha_sha256":manifest["alpha_sha256"],"rasterization":manifest["rasterization"],
            "scope":"Original font, source NOHINT flag, independent fontTools hmtx advances, exact packed host FreeType masks; legacy/GPU rendering pending"}

def android_build(ndk,temp,output):
    toolchain=ndk/"toolchains/llvm/prebuilt/linux-x86_64/bin"
    cc=toolchain/"aarch64-linux-android26-clang"
    library=output.parent/"libcoh_hud.so"
    command=[cc,*STRICT,"-O2","-fPIC","-shared",*SOURCES,HERE/"coh_hud_gles.c","-lm","-lGLESv3","-Wl,--no-undefined","-o",library]
    run(command)
    # Compile proof that portable numeric boundary mappings match actual Android headers.
    static=temp/"android_constants.c"
    static.write_text('''#include <android/input.h>
#include <android/keycodes.h>
#define CHECK(name,value) typedef char check_##name[(name==(value))?1:-1]
CHECK(AKEY_EVENT_ACTION_DOWN,0);CHECK(AKEY_EVENT_ACTION_UP,1);
CHECK(AKEYCODE_DPAD_UP,19);CHECK(AKEYCODE_DPAD_DOWN,20);CHECK(AKEYCODE_DPAD_LEFT,21);
CHECK(AKEYCODE_DPAD_RIGHT,22);CHECK(AKEYCODE_DPAD_CENTER,23);CHECK(AKEYCODE_TAB,61);
CHECK(AKEYCODE_ENTER,66);CHECK(AKEYCODE_DEL,67);CHECK(AKEYCODE_BACK,4);
CHECK(AKEYCODE_BUTTON_A,96);CHECK(AKEYCODE_BUTTON_B,97);CHECK(AKEYCODE_BUTTON_L1,102);
CHECK(AKEYCODE_BUTTON_R1,103);CHECK(AKEYCODE_ESCAPE,111);
CHECK(AMOTION_EVENT_ACTION_DOWN,0);CHECK(AMOTION_EVENT_ACTION_UP,1);
CHECK(AMOTION_EVENT_ACTION_MOVE,2);CHECK(AMOTION_EVENT_ACTION_CANCEL,3);
CHECK(AMOTION_EVENT_ACTION_POINTER_DOWN,5);CHECK(AMOTION_EVENT_ACTION_POINTER_UP,6);
''')
    run([cc,*STRICT,"-c",static,"-o",temp/"android_constants.o"])
    elf=run([toolchain/"llvm-readelf","-h",library])
    assert "AArch64" in elf and "ELF64" in elf
    imports=run([toolchain/"llvm-nm","-u",library])
    assert not re.search(r"\b(malloc|calloc|realloc|free)(?:@|$)",imports,re.M)
    return {"status":"ARM64 built","api":26,"compiler":str(cc),"artifact":library.name,
            "sha256":hashlib.sha256(library.read_bytes()).hexdigest(),"bytes":library.stat().st_size,
            "android_header_constant_checks":22,"no_allocator_imports":True,"command":[str(x) for x in command],
            "execution":"not run; compilation does not qualify Android rendering/input"}

def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--source-root",type=Path)
    p.add_argument("--sanitize",action="store_true")
    p.add_argument("--font",type=Path,help="Recovered original mont_hvbold.ttf")
    p.add_argument("--ndk",type=Path,default=Path(os.environ["ANDROID_NDK_HOME"]) if os.environ.get("ANDROID_NDK_HOME") else None)
    p.add_argument("--cc",default=os.environ.get("CC","gcc"))
    args=p.parse_args();output=args.output if args.output.suffix==".json" else args.output/"qualification.json"
    output.parent.mkdir(parents=True,exist_ok=True)
    report={"gates":[34,35,36],"module":"opt-in native gameplay HUD","host":"running",
            "emulator":"not run","physical_thor":"not run","accepted_baseline":"not modified"}
    with tempfile.TemporaryDirectory(prefix="coh-hud-") as directory:
        temp=Path(directory);binary=temp/"hud-tests"
        command=[args.cc,*STRICT,"-O2",*SOURCES,HERE/"tests/hud_test.c","-lm","-o",binary]
        run(command);report["tests"]=json.loads(run([binary]));report["host_command"]=[str(x) for x in command]
        imports=run(["nm","-u",binary]);assert not re.search(r"\b(malloc|calloc|realloc|free)(?:@|$)",imports,re.M)
        report["no_allocator_imports"]=True
        report["allocation_scope"]="Fixed caller arena; verifies direct imports, not libc internals of snprintf or process-wide allocation profiling"
        if args.sanitize:
            sanitized=temp/"hud-tests-sanitized"
            run([args.cc,*STRICT,"-O1","-g","-fno-omit-frame-pointer","-fsanitize=address,undefined",*SOURCES,HERE/"tests/hud_test.c","-lm","-o",sanitized])
            env=dict(os.environ,ASAN_OPTIONS="detect_leaks=0:abort_on_error=1",UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
            report["sanitizer_tests"]=json.loads(run([sanitized],env=env))
            report["sanitizers"]="ASan + UBSan passed; LSan disabled; module has no owned heap"
        else:report["sanitizers"]="not run"
        report["source_oracle"]=source_oracle(args.source_root,temp,args.cc) if args.source_root else {"status":"not run"}
        report["authentic_font"]=font_check(args.font,temp,args.cc) if args.font else {"status":"not run; pass --font"}
        report["android"]=android_build(args.ndk,temp,output) if args.ndk else {"status":"not run; pass --ndk"}
        report["host"]="qualified within documented mock HUD/source-color scope" if args.source_root and args.sanitize else "tests passed; qualification incomplete"
        files=[*SOURCES[1:],UI/"coh_hud.h",HERE/"coh_hud_android.h",HERE/"coh_hud_atlas.h",HERE/"coh_hud_gles.h",HERE/"coh_hud_gles.c",HERE/"make_atlas.py",HERE/"tests/hud_test.c"]
        report["source_files"]={str(f.relative_to(UI)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
        report["reused_kernel_hashes"]={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (UI/"coh_ui.c",UI/"coh_ui.h")}
        report["performance_scope"]="Host CPU clock snapshot+drawlist only; no device/GPU or 30 FPS claim"
        output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"output":str(output),"host":report["host"],"android":report["android"]["status"]}))

if __name__=="__main__":main()
