#!/usr/bin/env python3
"""Coverage admission and immutable snapshot ownership: host/source/ASan/ARM64."""
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


def run(command, env=None):
    p = subprocess.run(list(map(str, command)), capture_output=True, text=True, env=env, timeout=180)
    if p.returncode:
        raise RuntimeError(" ".join(map(str, command)) + "\n" + p.stdout + p.stderr)
    return p.stdout


def identity(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--ndk", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--disable-leak-sanitizer", action="store_true")
    args = ap.parse_args()
    pins = json.loads((ROOT / "native-android/walk/source-pins.json").read_text())
    source_ids = {}
    for pin in pins["files"]:
        text = (args.source_root / pin["path"]).read_text().replace("\r\n", "\n").rstrip("\n") + "\n"
        actual = hashlib.sha256(text.encode()).hexdigest()
        if actual != pin["sha256_lf"]:
            raise AssertionError((pin["path"], "pinned source changed", actual))
        source_ids[pin["path"]] = actual
    walk = ROOT / "native-android/walk"
    cc = os.environ.get("CC", "cc")
    flags = ["-std=c11", "-O1", "-g", "-fno-fast-math", "-ffp-contract=off", "-fno-strict-aliasing",
             "-Wall", "-Wextra", "-Werror", "-Wno-unused-variable", "-Wno-unused-parameter",
             "-Wno-unused-but-set-variable", "-Wno-unused-function", "-Wno-misleading-indentation"]
    base = [HERE / "coh_physics_snapshot.c", HERE / "coh_physics.c", walk / "coh_walk.c",
            walk / "source_world.c", ROOT / "native-android/motion/coh_motion.c"]
    kernels = [walk / "source_ctri.c", walk / "source_tritri.c"]
    wrap = ["-Wl,--wrap=malloc,--wrap=calloc,--wrap=realloc,--wrap=free"]
    with tempfile.TemporaryDirectory(prefix="coh-physics-snapshot-") as temp:
        tmp = Path(temp)
        host = tmp / "host"
        run([cc, *flags, HERE / "tests/test_snapshot.c", *base, *kernels, "-pthread", *wrap, "-lm", "-o", host])
        host_result = json.loads(run([host]))
        original = []
        shim = f'#include "{walk / "source_math.h"}"\n#include "{walk / "source_types.h"}"\n#include <stdio.h>\n'
        for filename in ["ctri.c", "tritri_isectline.c"]:
            source = (args.source_root / "upstream/ouroboros/Common/gridcoll" / filename).read_text()
            source = re.sub(r"^\s*#\s*include[^\n]*", "", source, flags=re.M)
            source = re.sub(r"\\[ \t]+\n", lambda _: "\\\n", source)
            path = tmp / filename
            path.write_text(shim + source)
            original.append(path)
        oracle = tmp / "source-oracle"
        run([cc, *flags, HERE / "tests/test_snapshot.c", *base, *original, "-pthread", *wrap, "-lm", "-o", oracle])
        oracle_result = json.loads(run([oracle]))
        for key, value in host_result.items():
            if key != "query_batch_cpu_seconds" and oracle_result[key] != value:
                raise AssertionError(("independent original CTri mismatch", key, value, oracle_result[key]))
        sanitizer = tmp / "sanitizer"
        run([cc, *flags, "-fsanitize=address,undefined", HERE / "tests/test_snapshot.c", *base, *kernels,
             "-pthread", *wrap, "-lm", "-o", sanitizer])
        env = {**os.environ, "ASAN_OPTIONS": "detect_leaks=" + ("0" if args.disable_leak_sanitizer else "1"),
               "UBSAN_OPTIONS": "halt_on_error=1:print_stacktrace=1"}
        sanitizer_result = json.loads(run([sanitizer], env))
        android = {"built": False, "reason": "NDK not provided"}
        if args.ndk:
            binpath = args.ndk / "toolchains/llvm/prebuilt/linux-x86_64/bin"
            output = tmp / "libcoh_physics_snapshot.so"
            run([binpath / "aarch64-linux-android26-clang", *flags, "-shared", "-fPIC", "-Wl,--no-undefined",
                 *base, *kernels, "-lm", "-o", output])
            header = run([binpath / "llvm-readelf", "-h", output])
            symbols = run([binpath / "llvm-nm", "-g", "--defined-only", output])
            exports = [line.split()[-1] for line in symbols.splitlines() if " coh_physics_snapshot_" in line]
            if "AArch64" not in header or len(exports) != 6:
                raise AssertionError(("ARM64 identity/API audit failed", exports))
            android = {"built": True, "abi": "arm64-v8a", "api": 26, "ndk": args.ndk.name,
                       "library": identity(output), "exports": exports,
                       "emulator_qualified": False, "physical_thor_accepted": False}
    receipt = {
        "schema": "coh-native-physics-snapshot-v1", "passed": True,
        "starting_repository_revision": run(["git", "-C", ROOT, "rev-parse", "HEAD"]).strip(),
        "source_revision": pins["upstream_source_revision"], "source_sha256_lf": source_ids,
        "independently_compiled_original_ctri_parity": True,
        "host": host_result, "asan_ubsan": sanitizer_result,
        "leak_sanitizer_enabled": not args.disable_leak_sanitizer,
        "android": android,
        "runtime_source": {str(p.relative_to(ROOT)): identity(p) for p in
                           [*base, *kernels, HERE / "coh_physics_snapshot.h", HERE / "tests/test_snapshot.c"]},
        "limits": ["Coverage is an explicit loader attestation, not proof of completeness from triangle bounds.",
                   "Four connected synthetic source-qualified slope regions; no newly qualified authentic map.",
                   "No jump, dynamic collision, prediction, networking or server changes.",
                   "ARM64 linking does not establish Android runtime, Thor, full-map or performance acceptance."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"passed": True, "host": host_result, "asan_ubsan": sanitizer_result, "android": android}))


if __name__ == "__main__":
    main()
