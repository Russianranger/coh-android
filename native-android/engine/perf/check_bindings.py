#!/usr/bin/env python3
"""Opt-in moving-listener/cumulative-perf qualification, no Android execution."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parents[1]
REPO = NATIVE.parent
BASE = "3c5da1d8cd501d778e270d395109d40666fbe37a"

def require(ok, message):
    if not ok:
        raise ValueError(message)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run(args, **kwargs):
    r = subprocess.run([str(x) for x in args], capture_output=True, text=True, **kwargs)
    require(r.returncode == 0, "command failed: " + " ".join(map(str, args)) + "\n" + r.stdout[-4000:] + r.stderr[-8000:])
    return r.stdout

def oracle(root, build):
    spec = importlib.util.spec_from_file_location("audio_check", NATIVE / "engine/audio/check.py")
    audio = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audio)
    generated, sound_pins = audio.source_oracle(root, build)
    math = root / "upstream/ouroboros/libs/UtilitiesLib/src/utils/mathutil.c"
    text = math.read_text(encoding="latin1").replace("\r\n", "\n")
    expected = "77f4468858066f854d060338dae41c31e44a7318fad363baae9b28b98b36cb1f"
    require(hashlib.sha256(text.encode()).hexdigest() == expected, "Original mathutil.c pin differs")
    body = audio.function(text, "createMat3YPR")
    body_pin = "20ec80bc614452b9ab22a836ea9c4db022cca7daa6652583a3735333c5ccf688"
    require(hashlib.sha256(body.encode()).hexdigest() == body_pin, "Original createMat3YPR body differs")
    shim = '''
typedef float Mat3[3][3];
static void mathutil_sincosf(float a,float*s,float*c){*s=sinf(a);*c=cosf(a);}
'''
    suffix = '''
#include "coh_audio_listener.h"
void oracle_right(const float degrees[3],float right[3]) {
    float pyr[3];Mat3 m;
    for(unsigned i=0;i<3;i++)pyr[i]=(float)(((double)degrees[i]*3.14159265358979323846)*(1.0f/180.0f));
    createMat3YPR(m,pyr);for(unsigned i=0;i<3;i++)right[i]=m[0][i];
}
float oracle_moving_spatial(const CohAudioEvent *e,CohVec3 pos,CohVec3 right,float *pan) {
    head_mat[0][0]=right.x;head_mat[0][1]=right.y;head_mat[0][2]=right.z;
    head_mat[3][0]=pos.x;head_mat[3][1]=pos.y;head_mat[3][2]=pos.z;
    game_state.ignoreSoundRamp=e->ignore_ramp;SoundSphere s={0};
    s.inner_radius=e->inner_radius;s.outer_radius=e->outer_radius;s.max_volume=1;s.volRatio=e->gain;
    s.pos[0]=e->position.x;s.pos[1]=e->position.y;s.pos[2]=e->position.z;
    *pan=0;return sphereGroupGetVolume(&s,1,pan);
}
'''
    generated.write_text(generated.read_text() + shim + body + suffix)
    return generated, {"original_revision": sound_pins["revision"], "sound": sound_pins,
                       "mathutil_lf_sha256": expected, "createMat3YPR_unchanged_body_sha256": body_pin,
                       "shim": "Original createMat3YPR unchanged; sin/cos shim matches portable _WIN64 source branch. Source gain/group functions unchanged; controlled one-sphere nonfading world listener."}

def independent_trace(report):
    perf = report["perf"]; bindings = report["bindings"]
    expected = sum(i % 7 for i in range(1, 1001) if i % 13 and i % 17) + 12
    require(perf["counters"]["draw_calls"] == expected, "Independent cumulative delta arithmetic differs")
    draw = bindings["counters"]["draw_calls"]
    require(draw == {"known": True, "mode": "total", "generation": 2, "owner_total": 507,
                     "observations": 2004, "rebases": 1, "rejected": 2}, "Cumulative baseline/reset accounting differs")
    require(bindings["counters"]["readbacks"]["known"] and perf["counters"]["readbacks"] == 0,
            "Measured zero not distinguishable")
    require(not bindings["counters"]["allocations"]["known"], "Unobserved zero reported known")
    require(perf["counters"]["upload_bytes"] == (1 << 64) - 1, "Counter saturation differs")
    require(bindings["memory"]["module_accounted"] == {"known": True, "current_bytes": 400, "peak_bytes": 600, "observations": 2}, "Memory kind or high-water accounting differs")
    require(bindings["memory"]["process_rss"]["known"] and not bindings["memory"]["process_pss"]["known"],
            "Unknown process memory mislabeled")
    require(report["hot_path_allocator_calls"] == 0, "Sampling/listener/mixer allocated or freed")
    return {"passed": True, "draw_calls_expected": expected,
            "scope": "Independent Python arithmetic over explicit 1000-step trace, paused/disabled exclusion, repeated totals, reset and source-mode rejection; no game FPS claim"}

def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--source-root", type=Path, required=True)
    a.add_argument("--ndk", type=Path, required=True)
    a.add_argument("--output", type=Path, required=True)
    a.add_argument("--compiler", default="cc")
    args = a.parse_args()
    sources = [HERE/"coh_perf.c", HERE/"coh_perf_bridge.c", NATIVE/"engine/audio/coh_audio_listener.c",
               NATIVE/"engine/audio/coh_mixer.c", NATIVE/"audio/coh_audio.c", NATIVE/"world/coh_world.c"]
    headers = [HERE/"coh_perf_bridge.h", NATIVE/"engine/audio/coh_audio_listener.h"]
    common = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-ffp-contract=off", "-I", HERE, "-I", NATIVE/"engine/audio"]
    wraps = ["-Wl,--wrap=malloc,--wrap=calloc,--wrap=realloc,--wrap=free"]
    with tempfile.TemporaryDirectory(prefix="coh-bindings-") as td:
        build = Path(td); original, provenance = oracle(args.source_root, build)
        host = build/"bindings-test"
        run([args.compiler, *common, "-O2", HERE/"tests/test_bindings.c", *sources, original, *wraps, "-lm", "-o", host])
        tested = json.loads(run([host])); arithmetic = independent_trace(tested)
        sanitized = build/"bindings-asan"
        run([args.compiler, *common, "-O1", "-g", "-fno-omit-frame-pointer", "-fsanitize=address,undefined", "-fno-sanitize-recover=all", HERE/"tests/test_bindings.c", *sources, original, *wraps, "-lm", "-o", sanitized])
        env = dict(os.environ); env["ASAN_OPTIONS"] = "detect_leaks=1:abort_on_error=1"; env["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"
        attempt = subprocess.run([sanitized], capture_output=True, text=True, env=env)
        leak = attempt.returncode == 0
        if not leak:
            spec = importlib.util.spec_from_file_location("audio_check_retry", NATIVE/"engine/audio/check.py")
            check = importlib.util.module_from_spec(spec); spec.loader.exec_module(check)
            require(check.lsan_task_inspection_blocked(attempt.stderr), "Sanitizer failed: " + attempt.stderr[-8000:])
            env["ASAN_OPTIONS"] = "detect_leaks=0:abort_on_error=1"
            sanitized_result = json.loads(run([sanitized], env=env))
        else:
            sanitized_result = json.loads(attempt.stdout)
        independent_trace(sanitized_result)
        clang = args.ndk/"toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang"
        library = build/"libcoh_gameplay_bindings.so"
        command = [clang,*common,"-O2","-fPIC","-shared",*sources,"-Wl,--no-undefined","-lm","-o",library]
        run(command);elf = run([clang.parent/"llvm-readelf","-h",library]);require("AArch64" in elf,"Wrong Android architecture")
        report = {"schema": 1, "status": "host-qualified-and-arm64-built", "starting_commit": BASE,
                  "features": ["source-reflected-view camera listener binding", "generation-safe total/delta counter observations", "unknown-vs-measured-zero diagnostics", "memory gauges typed accounted/RSS/PSS"],
                  "host": tested, "independent_trace": arithmetic, "source_provenance": provenance,
                  "sanitizers": {"address": "passed", "undefined": "passed", "leak_detection": leak,
                                 "leak_limitation": None if leak else "LeakSanitizer process inspection denied; explicit allocator-call guard covers all added hot paths; inherited mixer lifetime accounting unchanged",
                                 "checks": sanitized_result["checks"]},
                  "android_arm64": {"status": "built", "api":26, "elf_machine":"AArch64", "library_sha256":digest(library), "library_bytes":library.stat().st_size,
                                    "compiler":run([clang,"--version"]).splitlines()[0], "sources":[str(p.relative_to(REPO)) for p in sources],
                                    "scope":"Linked additive adapters and unchanged mixer/perf/source-world kernels only, no AAudio driver/APK execution"},
                  "emulator_qualified": False, "physical_thor_accepted": False,
                  "memory": {"fixed_bridge_bytes":tested["bridge_bytes"], "listener_pose_bytes":tested["listener_pose_bytes"], "sampling_allocator_calls":tested["hot_path_allocator_calls"],
                             "device_rss_pss_thermal": "unknown; unit-test memory gauge values are explicit synthetic fixtures"},
                  "module_sha256": {str(p.relative_to(REPO)):digest(p) for p in [*sources,*headers,HERE/"tests/test_bindings.c",Path(__file__)]},
                  "limitations":["Audio focus/route/platform lifecycle belongs to Android owner; no new Android lifecycle claims.",
                                 "Counter totals require stable serialized owner generation; first observation rebases without reconstructing earlier operations.",
                                 "Source camera inverse uses accepted float view; world position roundtrip tolerance 0.025 source units within +/-32500.",
                                 "No synchronous GPU operation or inferred GPU timing added; GPU/thermal remain unknown until measured.",
                                 "No physical audibility, latency, sustained xrun/FPS acceptance, full-game performance or gate acceptance."]}
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+"\n")
        print(json.dumps({"status":report["status"],"checks":tested["checks"],"source_spatial_comparisons":tested["spatial_source_comparisons"],"source_cameras":tested["cameras"],"sampler_allocator_calls":tested["hot_path_allocator_calls"],"output":str(args.output)}))

if __name__ == "__main__":
    main()
