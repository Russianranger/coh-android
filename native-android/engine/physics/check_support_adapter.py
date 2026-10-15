#!/usr/bin/env python3
"""Qualify the separate offline support-client physics adapter."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def run(command, env=None):
    p = subprocess.run(list(map(str, command)), capture_output=True, text=True, env=env, timeout=120)
    if p.returncode:
        raise RuntimeError(" ".join(map(str, command)) + "\n" + p.stdout + p.stderr)
    return p.stdout


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", type=Path, required=True)
    ap.add_argument("--ndk", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--disable-leak-sanitizer", action="store_true")
    args = ap.parse_args()
    support = ROOT / "native-android/support-client/src"
    walk = ROOT / "native-android/walk"
    sources = [support / "support_physics.c", HERE / "coh_physics.c", walk / "coh_walk.c",
               walk / "source_world.c", walk / "source_ctri.c", walk / "source_tritri.c",
               ROOT / "native-android/motion/coh_motion.c"]
    flags = ["-std=c11", "-O1", "-g", "-fno-fast-math", "-ffp-contract=off", "-fno-strict-aliasing", "-Wall", "-Wextra", "-Werror",
             "-Wno-unused-variable", "-Wno-unused-parameter", "-Wno-unused-but-set-variable", "-Wno-unused-function", "-Wno-misleading-indentation"]
    wrap = ["-Wl,--wrap=malloc,--wrap=calloc,--wrap=realloc,--wrap=free"]
    cc = os.environ.get("CC", "cc")
    with tempfile.TemporaryDirectory(prefix="coh-support-physics-") as d:
        tmp = Path(d)
        binary = tmp / "host"
        run([cc, *flags, HERE / "tests/test_support_adapter.c", *sources, *wrap, "-lm", "-o", binary])
        host = json.loads(run([binary, args.fixture]))
        sanitizer = tmp / "sanitizer"
        run([cc, *flags, "-fsanitize=address,undefined", HERE / "tests/test_support_adapter.c", *sources, *wrap, "-lm", "-o", sanitizer])
        env = {**os.environ, "ASAN_OPTIONS": "detect_leaks=" + ("0" if args.disable_leak_sanitizer else "1"),
               "UBSAN_OPTIONS": "halt_on_error=1:print_stacktrace=1"}
        sanitized = json.loads(run([sanitizer, args.fixture], env))
        tc = args.ndk / "toolchains/llvm/prebuilt/linux-x86_64/bin"
        library = tmp / "libsupport_physics.so"
        run([tc / "aarch64-linux-android26-clang", *flags, "-shared", "-fPIC", "-Wl,--no-undefined", *sources, "-lm", "-o", library])
        header = run([tc / "llvm-readelf", "-h", library])
        if "AArch64" not in header:
            raise AssertionError("Not ARM64")
        exports = [line.split()[-1] for line in run([tc / "llvm-nm", "-g", "--defined-only", library]).splitlines()
                   if " coh_support_physics_" in line]
        if len(exports) != 7:
            raise AssertionError(exports)
        receipt = {"schema": "coh-support-physics-adapter-v1", "passed": True, "host": host, "asan_ubsan": sanitized,
                   "leak_sanitizer_enabled": not args.disable_leak_sanitizer,
                   "leak_sanitizer_note": "Explicitly disabled: sandbox /proc task access was unavailable during preceding module qualification" if args.disable_leak_sanitizer else "enabled",
                   "fixture_sha256": sha(args.fixture), "android": {"built": True, "abi": "arm64-v8a", "api": 26,
                   "library_sha256": sha(library), "exports": exports, "emulator_qualified": False, "physical_thor_accepted": False},
                   "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in [*sources, support / "support_physics.h"]}}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps({"passed": True, "host": host, "asan_ubsan_passed": True, "android_built": True}))


if __name__ == "__main__":
    main()
