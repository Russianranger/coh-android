#!/usr/bin/env python3
"""Execute the existing crypto/auth suite on an explicitly selected Android.

This test does not attempt a network login and never reads user credentials.
It verifies the executable against its build receipt before transfer.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess


def run(command, timeout=60):
    result = subprocess.run([str(value) for value in command], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"Command failed: {command!r}\n{result.stdout}")
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", type=Path, required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device-kind", choices=("emulator", "physical"), default="emulator")
    args = parser.parse_args()
    receipt_path = args.artifacts / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    executable = args.artifacts / "test_auth_android"
    executable_sha = hashlib.sha256(executable.read_bytes()).hexdigest()
    if receipt["status"] != "PASS" or executable_sha != receipt["artifacts_sha256"][executable.name]:
        raise ValueError("Auth executable does not match a successful build receipt")
    adb = [args.adb, "-s", args.serial]
    run([*adb, "wait-for-device"])
    prop = lambda name: run([*adb, "shell", "getprop", name])
    abis = prop("ro.product.cpu.abilist").split(",")
    if receipt["abi"] not in abis:
        raise ValueError("Selected Android does not support the qualified ABI")
    is_emulator = prop("ro.kernel.qemu") == "1"
    if is_emulator != (args.device_kind == "emulator"):
        raise ValueError("Selected Android does not match --device-kind")
    remote = run([*adb, "shell", "mktemp", "-d", "/data/local/tmp/coh-auth.XXXXXX"])
    if not re.fullmatch(r"/data/local/tmp/coh-auth\.[A-Za-z0-9]+", remote):
        raise ValueError("Unexpected Android temporary directory")
    try:
        run([*adb, "push", executable, remote + "/test_auth_android"])
        run([*adb, "shell", "chmod", "700", remote + "/test_auth_android"])
        output = run([*adb, "shell", remote + "/test_auth_android"], timeout=90)
        tests = json.loads(output)
        if tests["checks"] != 1920 or tests["malformed_inputs"] != 10000 or tests["authenticated_server_session"]:
            raise ValueError("Unexpected auth-suite contract result")
    finally:
        run([*adb, "shell", "rm", "-rf", remote])
    result = {
        "status": "PASS", "scope": "Existing native auth and cryptographic contract tests",
        "abi": receipt["abi"], "android_release": prop("ro.build.version.release"),
        "android_sdk": prop("ro.build.version.sdk"), "device_model": prop("ro.product.model"),
        "openssl_version": receipt["openssl_version"],
        "openssl_archive_sha256": receipt["openssl_archive_sha256"],
        "build_receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "test_executable_sha256": executable_sha, "native_tests": tests,
        "android_test_executed": True, "emulator_qualified": is_emulator,
        "physical_android_executed": not is_emulator,
        "physical_thor_accepted": False,
        "actual_server_interoperability_verified": False,
        "authenticated_server_session": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
