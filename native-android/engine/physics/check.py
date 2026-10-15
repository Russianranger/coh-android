#!/usr/bin/env python3
"""Gate 32 static-world continuation: source/BVH/WALK/sanitizer/ARM64 evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def run(command, env=None, timeout=180):
    proc = subprocess.run(list(map(str, command)), text=True, capture_output=True, env=env, timeout=timeout)
    if proc.returncode:
        raise RuntimeError(" ".join(map(str, command)) + "\n" + proc.stdout + proc.stderr)
    return proc.stdout


def identity(path):
    b = path.read_bytes()
    return {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}


def source_tokens(text):
    """Qualify unchanged CTri arithmetic, excluding the unused #if 0 colltest."""
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    text = re.sub(r"^\s*#\s*include[^\n]*", "", text, flags=re.M)
    if "static colltest()" in text:
        start = text.index("static colltest()")
        brace = text.index("{", start)
        depth, end = 1, brace + 1
        while depth:
            depth += (text[end] == "{") - (text[end] == "}")
            end += 1
        text = text[:start] + text[end:]
    text = re.sub(r"#if\s+0\s*#endif", "", text)
    return re.sub(r"\s", "", text)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--source-root", required=True, type=Path)
    ap.add_argument("--fixture", type=Path, help="Qualified authentic COHWALK1 corpus, or set COH_WALK_FIXTURE")
    ap.add_argument("--ndk", type=Path, default=os.environ.get("ANDROID_NDK_HOME"))
    ap.add_argument("--disable-leak-sanitizer", action="store_true")
    args = ap.parse_args()
    fixture = args.fixture or (Path(os.environ["COH_WALK_FIXTURE"]) if os.environ.get("COH_WALK_FIXTURE") else None)
    if not fixture or not fixture.is_file():
        ap.error("Provide --fixture /path/to/qualified/walkable.bin (authentic corpus is not duplicated in this module)")
    pins = json.loads((ROOT / "native-android/walk/source-pins.json").read_text())
    original_ids = {}
    for pin in pins["files"]:
        path = args.source_root / pin["path"]
        normalized = path.read_text().replace("\r\n", "\n").rstrip("\n") + "\n"
        actual = hashlib.sha256(normalized.encode()).hexdigest()
        if actual != pin["sha256_lf"]:
            raise AssertionError((pin["path"], "original source identity differs", actual))
        original_ids[pin["path"]] = actual
    walk = ROOT / "native-android/walk"
    upstream_ctri = args.source_root / "upstream/ouroboros/Common/gridcoll/ctri.c"
    upstream_tri = args.source_root / "upstream/ouroboros/Common/gridcoll/tritri_isectline.c"
    if source_tokens(upstream_ctri.read_text()) != source_tokens((walk / "source_ctri.c").read_text()):
        raise AssertionError("accepted CTri implementation no longer has original source tokens")
    cc = os.environ.get("CC", "cc")
    common = ["-std=c11", "-O1", "-g", "-fno-fast-math", "-ffp-contract=off", "-fno-strict-aliasing",
              "-Wall", "-Wextra", "-Werror", "-Wno-unused-variable", "-Wno-unused-parameter",
              "-Wno-unused-but-set-variable", "-Wno-unused-function", "-Wno-misleading-indentation"]
    base = [HERE / "coh_physics.c", walk / "coh_walk.c", walk / "coh_walk_selftest.c",
            walk / "source_world.c", ROOT / "native-android/motion/coh_motion.c"]
    ctri = [walk / "source_ctri.c", walk / "source_tritri.c"]
    wrap = ["-Wl,--wrap=malloc,--wrap=calloc,--wrap=realloc,--wrap=free"]
    with tempfile.TemporaryDirectory(prefix="coh-physics-") as temp:
        tmp = Path(temp)
        native = tmp / "host"
        run([cc, *common, HERE / "tests/test_physics.c", *base, *ctri, *wrap, "-lm", "-o", native])
        host = json.loads(run([native, fixture]))
        # Compile independently from the pinned original files. Platform headers
        # are replaced by the qualified portable type/math shim. All active
        # original CTri and triangle-intersection statements remain unchanged.
        original_ctri, original_tri = tmp / "original_ctri.c", tmp / "original_tritri.c"
        shim = f'#include "{walk / "source_math.h"}"\n#include "{walk / "source_types.h"}"\n#include <stdio.h>\n'
        original_ctri.write_text(shim + re.sub(r"^\s*#\s*include[^\n]*", "", upstream_ctri.read_text(), flags=re.M))
        tri_text = re.sub(r"^\s*#\s*include[^\n]*", "", upstream_tri.read_text(), flags=re.M)
        # Original macro has whitespace after a continuation backslash. Strip
        # that whitespace only, retaining the exact original macro statements.
        tri_text = re.sub(r"\\[ \t]+\n", lambda _: "\\\n", tri_text)
        original_tri.write_text(shim + tri_text)
        oracle_bin = tmp / "original-source"
        run([cc, *common, HERE / "tests/test_physics.c", *base, original_ctri, original_tri, *wrap, "-lm", "-o", oracle_bin])
        oracle = json.loads(run([oracle_bin, fixture]))
        for key, value in host.items():
            if key != "synthetic_oracle_batch_cpu_seconds" and oracle[key] != value:
                raise AssertionError(("independently compiled original source mismatch", key, value, oracle[key]))
        sanitizer_bin = tmp / "sanitizer"
        run([cc, *common, "-fsanitize=address,undefined", HERE / "tests/test_physics.c", *base, *ctri, *wrap, "-lm", "-o", sanitizer_bin])
        env = {**os.environ, "ASAN_OPTIONS": "detect_leaks=" + ("0" if args.disable_leak_sanitizer else "1"),
               "UBSAN_OPTIONS": "halt_on_error=1:print_stacktrace=1"}
        sanitizer = json.loads(run([sanitizer_bin, fixture], env))
        android = {"built": False, "reason": "NDK was not supplied; host qualification alone"}
        if args.ndk:
            toolchain = args.ndk / "toolchains/llvm/prebuilt/linux-x86_64/bin"
            compiler = toolchain / "aarch64-linux-android26-clang"
            output = tmp / "libcoh_physics.so"
            run([compiler, *common, "-shared", "-fPIC", "-Wl,--no-undefined", *base, *ctri, "-lm", "-o", output])
            header = run([toolchain / "llvm-readelf", "-h", output])
            symbols = run([toolchain / "llvm-nm", "-g", "--defined-only", output])
            if "AArch64" not in header:
                raise AssertionError("Android library is not ARM64")
            exports = [line.split()[-1] for line in symbols.splitlines() if " coh_physics_" in line]
            if len(exports) != 8:
                raise AssertionError(("unexpected physics API symbols", exports))
            android = {"built": True, "abi": "arm64-v8a", "api": 26,
                       "ndk": args.ndk.name, "library": identity(output), "exports": exports,
                       "emulator_qualified": False, "physical_thor_accepted": False}
        receipt = {
            "schema": "coh-native-physics-continuation-v1", "passed": True,
            "source_revision": pins["upstream_source_revision"], "original_source_sha256_lf": original_ids,
            "ctri_active_tokens_identical": True, "independently_compiled_original_ctri_parity": True,
            "host": host, "asan_ubsan": sanitizer, "sanitizers_passed": True,
            "leak_sanitizer_enabled": not args.disable_leak_sanitizer,
            "authentic_fixture": {"name": fixture.name, **identity(fixture)}, "android": android,
            "scope": "Immutable static-world segments, bounded BVH source CTri queries, off-tick neighborhoods around unchanged accepted WALK. Synthetic elevation/slope oracle witnesses and authentic floor/bench collision regression. No jump implementation, full-map qualification, network prediction or Thor acceptance.",
            "runtime_source": {str(p.relative_to(ROOT)): identity(p) for p in [*base, *ctri, HERE / "coh_physics.h"]},
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps({"passed": True, "host": host, "sanitizers_passed": True, "android_built": android["built"]}))


if __name__ == "__main__":
    main()
