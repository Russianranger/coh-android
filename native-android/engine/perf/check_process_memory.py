#!/usr/bin/env python3
"""Qualify bounded self-process memory collection without touching APKs or old receipts."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
START = "58caf1d4ab3b39757190f194100ccbc697d57857"


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def run(command, **kwargs):
    p = subprocess.run(list(map(str, command)), capture_output=True, text=True, **kwargs)
    require(p.returncode == 0, f"Command failed ({p.returncode}): {command}\n{p.stdout[-4000:]}{p.stderr[-8000:]}")
    return p.stdout


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def independent_parser(library):
    class Value(ctypes.Structure):
        _fields_ = [("bytes", ctypes.c_uint64), ("status", ctypes.c_int),
                    ("system_error", ctypes.c_int), ("source", ctypes.c_int)]

    class Snapshot(ctypes.Structure):
        _fields_ = [("rss", Value), ("pss", Value), ("rollup_status", ctypes.c_int),
                    ("status_file_status", ctypes.c_int), ("rollup_errno", ctypes.c_int),
                    ("status_file_errno", ctypes.c_int), ("files_opened", ctypes.c_uint32),
                    ("read_calls", ctypes.c_uint32), ("bytes_read", ctypes.c_uint64)]

    api = ctypes.CDLL(str(library))
    api.coh_process_memory_parse.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_size_t,
                                            ctypes.POINTER(Snapshot)]
    api.coh_process_memory_json.argtypes = [ctypes.POINTER(Snapshot), ctypes.c_char_p,
                                           ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    rng = random.Random(43_44_45)
    samples = 2048
    maximum_json = 0
    output = ctypes.create_string_buffer(1024)
    for i in range(samples):
        rss = rng.randrange(1 << 54)
        pss = rng.randrange(rss + 1)
        lines = [f"Rss: {rss} kB", f"Pss: {pss} kB", "Pss_Anon: 777 kB", "SwapPss: 99 kB"]
        rng.shuffle(lines)
        text = ("\n".join(lines) + ("\n" if i % 2 else "")).encode()
        value = Snapshot()
        require(api.coh_process_memory_parse(1, text, len(text), ctypes.byref(value)) == 0,
                "Independent randomized text rejected")
        require(value.rss.bytes == rss * 1024 and value.pss.bytes == pss * 1024,
                "Independent arbitrary-precision kB arithmetic differs")
        needed = ctypes.c_size_t()
        require(api.coh_process_memory_json(ctypes.byref(value), output, 1024,
                                            ctypes.byref(needed)) == 0, "JSON export failed")
        data = json.loads(output.value)
        require(data["rss"]["known"] and data["pss"]["known"] and
                data["rss"]["bytes"] == rss * 1024 and data["pss"]["bytes"] == pss * 1024,
                "JSON precision or presence differs")
        maximum_json = max(maximum_json, needed.value)
    # Legitimate largest supported values, plus the largest diagnostic widths.
    text = b"Rss: 18014398509481983 kB\nPss: 18014398509481983 kB"
    value = Snapshot()
    require(api.coh_process_memory_parse(1, text, len(text), ctypes.byref(value)) == 0,
            "Largest byte count rejected")
    value.files_opened = 2
    value.read_calls = 64
    value.bytes_read = 32770
    value.rollup_errno = value.status_file_errno = 2147483647
    needed = ctypes.c_size_t()
    require(api.coh_process_memory_json(ctypes.byref(value), output, 1024,
                                        ctypes.byref(needed)) == 0, "Largest report overflowed")
    maximum_json = max(maximum_json, needed.value)
    return {"cases": samples, "passed": True, "snapshot_bytes": ctypes.sizeof(Snapshot),
            "largest_tested_json_including_nul": maximum_json,
            "scope": "Independent Python arbitrary-precision parser/export oracle; synthetic proc text, not Android memory"}


def retained_evidence():
    receipts = [
        (REPO / "native-android/engine/audio/lifecycle-host-proof.json", "module_sources"),
        (REPO / "native-android/engine/audio/android-integration/host-proof.json", "sources"),
        (HERE / "evidence/bindings-qualification.json", "module_sha256"),
    ]
    results = []
    for path, key in receipts:
        receipt = json.loads(path.read_text())
        pins = receipt[key]
        for relative, expected in pins.items():
            require(digest(REPO / relative) == expected, f"Retained evidence source changed: {relative}")
        results.append({"receipt": str(path.relative_to(REPO)), "sha256": digest(path),
                        "source_files_verified_unchanged": len(pins)})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ndk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compiler", default="cc")
    args = parser.parse_args()
    sources = [HERE / "coh_process_memory.c", HERE / "coh_perf_bridge.c", HERE / "coh_perf.c"]
    test = HERE / "tests/test_process_memory.c"
    flags = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-I", HERE]
    wraps = ["-Wl,--wrap=malloc,--wrap=calloc,--wrap=realloc,--wrap=free,--wrap=open,--wrap=read,--wrap=close"]
    preserved = retained_evidence()
    with tempfile.TemporaryDirectory(prefix="coh-process-memory-") as directory:
        build = Path(directory)
        binary = build / "memory-test"
        run([args.compiler, *flags, "-O2", test, *sources, *wraps, "-o", binary])
        host = json.loads(run([binary]))
        require(host["direct_allocator_calls"] == 0, "Memory observer called allocator")
        shared = build / "libmemory-host.so"
        run([args.compiler, *flags, "-O2", "-fPIC", "-shared", *sources,
             "-Wl,--no-undefined", "-o", shared])
        independent = independent_parser(shared)
        sanitized = build / "memory-asan"
        run([args.compiler, *flags, "-O1", "-g", "-fno-omit-frame-pointer",
             "-fsanitize=address,undefined", "-fno-sanitize-recover=all", test, *sources,
             *wraps, "-o", sanitized])
        env = dict(os.environ, ASAN_OPTIONS="detect_leaks=1:abort_on_error=1",
                   UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
        attempt = subprocess.run([sanitized], capture_output=True, text=True, env=env)
        leak = attempt.returncode == 0
        if not leak:
            require("Can't open /proc/" in attempt.stderr and "/task for reading" in attempt.stderr
                    and "LeakSanitizer has encountered a fatal error" in attempt.stderr
                    and "ERROR: AddressSanitizer" not in attempt.stderr
                    and "runtime error:" not in attempt.stderr,
                    "Sanitizer failure is not the known process-inspection restriction: " + attempt.stderr)
            env["ASAN_OPTIONS"] = "detect_leaks=0:abort_on_error=1"
            sanitized_result = json.loads(run([sanitized], env=env))
        else:
            sanitized_result = json.loads(attempt.stdout)
        require(host["checks"] == sanitized_result["checks"], "Sanitizer checks differ")
        android = []
        toolchain = args.ndk / "toolchains/llvm/prebuilt/linux-x86_64/bin"
        for abi, compiler, machine in [("arm64-v8a", "aarch64-linux-android26-clang", "AArch64"),
                                       ("x86_64", "x86_64-linux-android26-clang", "Advanced Micro Devices X86-64")]:
            library = build / f"libcoh_process_memory-{abi}.so"
            run([toolchain/compiler, *flags, "-O2", "-fPIC", "-shared", *sources,
                 "-Wl,--no-undefined", "-o", library])
            elf = run([toolchain / "llvm-readelf", "-h", library])
            require(machine in elf, "Unexpected Android architecture")
            android.append({"abi": abi, "api": 26, "status": "built", "elf_machine": machine,
                            "sha256": digest(library), "bytes": library.stat().st_size,
                            "compiler": run([toolchain/compiler, "--version"]).splitlines()[0]})
        report = {
            "schema": 1, "status": "host-qualified-and-android-libraries-built",
            "starting_commit": START,
            "source_revision": run(["git", "rev-parse", "HEAD"], cwd=REPO).strip(),
            "host": host, "independent_parser_oracle": independent,
            "sanitizers": {"address": "passed", "undefined": "passed", "checks": sanitized_result["checks"],
                           "leak_detection": leak,
                           "limitation": None if leak else "Host denies LeakSanitizer /proc/PID/task inspection; linked allocator guard still verifies zero direct allocation calls"},
            "android_libraries": android,
            "retained_audio_listener_perf_evidence": preserved,
            "scope": "New off-hot-path OS telemetry adapter. Original audio/source gain/codec/listener/perf algorithms unchanged; original-game oracle comparison not applicable to proc text parsing.",
            "bounds": {"snapshot_bytes": host["snapshot_bytes"], "fixed_read_buffer_bytes": 16385,
                       "maximum_files_opened": 2, "maximum_read_attempts": 64,
                       "maximum_bytes_read": 32770, "heap_allocations_in_adapter": 0,
                       "syscall_wall_time_bounded": False},
            "module_sha256": {str(p.relative_to(REPO)): digest(p) for p in [*sources, HERE/"coh_process_memory.h", test, Path(__file__)]},
            "emulator_qualified": False, "physical_thor_accepted": False,
            "limitations": [
                "Current process sample is Linux host evidence only; it is not Android/Thor RAM or game-memory endurance evidence.",
                "Android SELinux/kernel policy may make smaps_rollup unavailable; VmRSS fallback stays approximate and never fabricates PSS.",
                "Bounded bytes/syscall count does not bound kernel scan latency. Call only on a low-frequency owner/export worker.",
                "No new audio implementation: exact existing lifecycle, streaming and listener source hashes verified; their valid earlier receipts retained.",
                "Real allocation hooks, GPU timing, physical audio routes/audibility/latency/xruns, thermal sustainability and representative full-game FPS remain unqualified.",
                "Bridge high-water gauges retain old accepted values after failed samples; export latest snapshot + timestamp/age to expose staleness."]
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"status": report["status"], "checks": host["checks"],
                          "independent_cases": independent["cases"], "android_abis": [x["abi"] for x in android],
                          "maximum_tested_json": independent["largest_tested_json_including_nul"],
                          "output": str(args.output)}))


if __name__ == "__main__":
    main()
