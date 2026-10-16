#!/usr/bin/env python3
"""Attempt independent protocol and adapter suites; preserve each result."""
from pathlib import Path
import argparse
import json
import subprocess
import sys


def run_suites(adb, serial, artifacts):
    here = Path(__file__).resolve().parent
    output = Path(artifacts) / "android-execution"
    output.mkdir(parents=True, exist_ok=True)
    specs = (
        ("protocol", "run_android.py", Path(artifacts), output / "receipt.json", ["--require-clean"]),
        ("world-adapter", "run_adapter_android.py", Path(artifacts) / "world-adapter",
         output / "world-adapter/receipt.json", []),
    )
    results = {}
    for name, driver, inputs, receipt, extra in specs:
        command = [sys.executable, str(here / driver), "--adb", str(adb), "--serial", serial,
                   "--artifacts", str(inputs), "--output", str(receipt), *extra]
        completed = subprocess.run(command, check=False)
        # This records driver exit, not native execution or device acceptance.
        results[name] = {"driver_attempted": True, "driver_exit_code": completed.returncode,
                         "receipt": str(receipt.relative_to(output))}
    value = {"scope": "independent_standalone_driver_outcomes",
             "passed": all(item["driver_exit_code"] == 0 for item in results.values()),
             "suites": results, "physical_thor_accepted": False,
             "actual_server_interoperability_verified": False}
    (output / "batch.json").write_text(json.dumps(value, indent=2) + "\n")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", type=Path, required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    return 0 if run_suites(args.adb, args.serial, args.artifacts)["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
