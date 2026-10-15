#!/usr/bin/env python3
"""Execute hash-verified native crypto/TCP/UDP contracts on one Android.

No APK, app data, user account or external server is touched. Scripted peers
inside the test executables are not evidence of full-shard interoperability.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

SUITES = {"crypto", "login", "db_wire", "db_session", "mapclient"}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(command, timeout=60):
    process = subprocess.run([str(value) for value in command], text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    if process.returncode:
        raise RuntimeError(f"Command failed ({process.returncode}): {command!r}\n" + process.stdout[-3000:])
    return process.stdout.strip()


def child(root, relative):
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Artifact path must remain inside the downloaded artifact")
    result = (root / path).resolve()
    if not result.is_relative_to(root) or not result.is_file():
        raise ValueError("Artifact file is absent or outside the downloaded artifact")
    return result


def validate(root, manifest, abi):
    if manifest.get("schema") != "coh-native-live-contracts-android-v1" or manifest.get("passed") is not True:
        raise ValueError("A successful live-contract build manifest is required")
    if set(manifest["suites"]) != SUITES:
        raise ValueError("Android execution requires all five native contract suites")
    entries = {}
    for name, suite in manifest["suites"].items():
        item = suite["abis"][abi]
        binary = child(root, item["binary"])
        receipt_path = child(root, item["receipt"])
        if item.get("abi") != abi or digest(binary) != item["sha256"] or digest(receipt_path) != item["receipt_sha256"]:
            raise ValueError("Android artifact or receipt identity differs: " + name)
        if not 0 < binary.stat().st_size <= 128 * 1024 * 1024 or binary.stat().st_size != item["bytes"]:
            raise ValueError("Android executable size differs: " + name)
        receipt = json.loads(receipt_path.read_text())
        kind = suite["receipt_kind"]
        if kind == "crypto":
            relative = binary.relative_to(receipt_path.parent).as_posix()
            expected = receipt["artifacts_sha256"].get(relative)
            valid = receipt.get("status") == "PASS" and receipt.get("abi") == abi
        elif kind == "module":
            expected = receipt.get("binary_sha256")
            valid = (receipt.get("passed") is True and receipt.get("abi") == abi
                     and receipt.get("binary") == binary.name)
        elif kind == "db":
            candidates = [value for value in receipt["artifacts"] if value.get("abi") == abi
                          and value.get("kind") == suite["artifact_kind"] and value.get("file") == binary.name]
            expected = candidates[0]["sha256"] if len(candidates) == 1 else None
            valid = len(candidates) == 1 and candidates[0].get("built") is True
        else:
            raise ValueError("Unknown Android build-receipt contract")
        if not valid or expected != item["sha256"]:
            raise ValueError("Build receipt does not identify the executable: " + name)
        entries[name] = {"binary": binary, "expected": suite["required"], "descriptor": item}
    return entries


def check_result(name, actual, expected):
    if not isinstance(actual, dict) or type(actual.get("checks")) is not int or actual["checks"] <= 0:
        raise ValueError("Native suite did not report positive check counts: " + name)
    for key, value in expected.items():
        if type(actual.get(key)) is not type(value) or actual[key] != value:
            raise ValueError("Native suite contract differs: " + name + "." + key)
    # Authentication/world flags must remain false even if a fixture gains an
    # unexpected new diagnostics field. No fixture may promote itself to login.
    for key in ("authenticated_server_session", "real_account_login_verified", "real_server_login",
                "real_authenticated_server", "actual_authentication", "live_world"):
        if key in actual and actual[key] is not False:
            raise ValueError("Scripted native suite made a full-session acceptance claim")


def write(path, result):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", type=Path, required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--abi", choices=("x86_64", "arm64-v8a"), default="x86_64")
    parser.add_argument("--device-kind", choices=("emulator", "physical"), default="emulator")
    parser.add_argument("--android-sdk", type=int, default=33)
    args = parser.parse_args()
    root = args.artifacts.resolve()
    proof = {"schema": "coh-native-live-contracts-android-execution-v1", "passed": False,
             "abi": args.abi, "suites": {}, "android_executed": False, "emulator_qualified": False,
             "physical_android_executed": False, "physical_thor_accepted": False,
             "actual_server_interoperability_verified": False, "real_account_login_verified": False,
             "full_live_world_verified": False, "gates25_27_complete": False,
             "accepted_apks_rebuilt": False, "scope": "Five native crypto/scripted-peer TCP/UDP contract suites"}
    adb = [args.adb.resolve(), "-s", args.serial]
    try:
        manifest_path = child(root, "android-execution-manifest.json")
        manifest = json.loads(manifest_path.read_text())
        entries = validate(root, manifest, args.abi)
        proof["manifest_sha256"] = digest(manifest_path)
        run([*adb, "wait-for-device"])
        prop = lambda name: run([*adb, "shell", "getprop", name])
        if args.abi not in prop("ro.product.cpu.abilist").split(","):
            raise ValueError("Selected Android does not support the requested executable ABI")
        sdk = prop("ro.build.version.sdk")
        if sdk != str(args.android_sdk):
            raise ValueError("Selected Android SDK differs from the required qualification profile")
        emulator = prop("ro.kernel.qemu") == "1"
        if emulator != (args.device_kind == "emulator"):
            raise ValueError("Selected Android does not match --device-kind")
        proof["android_sdk"] = sdk
        proof["android_release"] = prop("ro.build.version.release")
        proof["device_model"] = prop("ro.product.model")
        proof["device_is_emulator"] = emulator
        remote = run([*adb, "shell", "mktemp", "-d", "/data/local/tmp/coh-live.XXXXXX"])
        if not re.fullmatch(r"/data/local/tmp/coh-live\.[A-Za-z0-9]+", remote):
            raise ValueError("Unexpected Android temporary directory")
        try:
            for name in sorted(entries):
                entry = entries[name]
                destination = remote + "/" + name
                run([*adb, "push", entry["binary"], destination])
                remote_sha = run([*adb, "shell", "sha256sum", destination]).split()[0]
                if remote_sha != entry["descriptor"]["sha256"]:
                    raise ValueError("Transferred Android executable identity differs: " + name)
                run([*adb, "shell", "chmod", "700", destination])
                stdout = run([*adb, "shell", destination], timeout=120)
                result = json.loads(stdout)
                check_result(name, result, entry["expected"])
                proof["suites"][name] = {"passed": True, "android_executed": True,
                                        "binary_sha256": remote_sha,
                                        "build_receipt_sha256": entry["descriptor"]["receipt_sha256"],
                                        "result": result}
                write(args.output.parent / (name + ".json"), proof["suites"][name])
                write(args.output, proof)
        finally:
            run([*adb, "shell", "rm", "-rf", remote])
        proof["passed"] = set(proof["suites"]) == SUITES
        proof["android_executed"] = proof["passed"]
        proof["emulator_qualified"] = proof["passed"] and emulator
        proof["physical_android_executed"] = proof["passed"] and not emulator
    except Exception as error:
        proof["error"] = str(error)
        proof["android_executed"] = bool(proof["suites"])
    write(args.output, proof)
    print(json.dumps(proof, indent=2, sort_keys=True))
    if not proof["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
