#!/usr/bin/env python3
"""ASan/UBSan source controls; allocator balance is checked by the C fixture."""
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
GROUPS = ("basic", "malformed", "acknowledgements", "io", "declines", "bounds", "allocation", "paths", "empty-full")

def main():
    env = dict(os.environ)
    # LeakSanitizer cannot inspect /proc under this execution environment's
    # ptrace. This is explicitly not a passing LeakSanitizer qualification.
    env["ASAN_OPTIONS"] = "detect_leaks=0:halt_on_error=1"
    env["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"
    results = []
    with tempfile.TemporaryDirectory(prefix="coh-live-transport-asan-") as folder:
        executable = pathlib.Path(folder) / "controls"
        command = ["cc", "-std=c99", "-O1", "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                   "-Wall", "-Wextra", "-Werror", "-Wno-misleading-indentation", "-I", str(ROOT),
                   str(ROOT / "coh_live_transport.c"), str(ROOT / "transport_fixture.c"), "-o", str(executable)]
        subprocess.run(command, check=True, capture_output=True, text=True)
        for group in GROUPS:
            result = subprocess.run([str(executable), group], env=env, capture_output=True, text=True, timeout=10)
            results.append({"group": group, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    pins = []
    for name in ("coh_live_directory_batch.h", "coh_live_transport.h", "coh_live_transport.c", "transport_fixture.c", "qualify_transport_sanitizers.py"):
        data = (ROOT / name).read_bytes()
        pins.append({"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    passed = all(r["returncode"] == 0 for r in results)
    report = {"schema": "coh-live-transport-asan-ubsan-controls-v1", "source_only": True,
              "asan_ubsan_passed": passed, "leak_sanitizer_qualified": False,
              "leak_sanitizer_limitation": "ptrace/proc visibility prevents LeakSanitizer in this executor; explicit balanced allocator checks run instead",
              "source_pins": pins, "results": results, "production_authority": False}
    (ROOT / "sanitizer-control-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"asan_ubsan_passed": passed, "groups": len(results), "leak_sanitizer_qualified": False}))
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())
