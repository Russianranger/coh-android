#!/usr/bin/env python3
"""Execute exact continuation ELFs on Android; do not touch an installed app."""
from pathlib import Path
import argparse
import json
import re
import subprocess

from common import ABIS, CLAIMS, FIXTURES, MODULES, child, digest, elf_identity, git_state, json_equal, native_result, read, write

HERE = Path(__file__).resolve().parent


def validate(root, manifest, abi):
    if (manifest.get("schema") != "coh-primary-continuation-android-v1"
            or manifest.get("passed") is not True or set(manifest.get("suites", {})) != set(MODULES)):
        raise ValueError("All required successful continuation suites are required")
    if any(manifest.get(key) is not False for key in CLAIMS):
        raise ValueError("Contract artifact has an invalid acceptance claim")
    if not re.fullmatch(r"[a-f0-9]{40}", manifest.get("source_revision", "")):
        raise ValueError("Manifest must identify an exact Git source revision")
    entries = {}
    for name, suite in manifest["suites"].items():
        if set(suite.get("abis", {})) != set(ABIS):
            raise ValueError("Both Android ABI artifacts are required")
        item = suite["abis"][abi]
        binary, receipt_path = child(root, item["binary"]), child(root, item["receipt"])
        host_path = child(root, suite["host_receipt"])
        if (item.get("abi") != abi or digest(binary) != item["sha256"]
                or digest(receipt_path) != item["receipt_sha256"]
                or digest(host_path) != suite["host_receipt_sha256"]):
            raise ValueError("Artifact, build receipt or host oracle receipt identity differs: " + name)
        if (type(item["bytes"]) is not int or not 0 < item["bytes"] <= 128 * 1024 * 1024
                or item["bytes"] != binary.stat().st_size):
            raise ValueError("Invalid executable byte count")
        elf_identity(binary, abi)
        receipt, host = read(receipt_path), read(host_path)
        costume = suite.get("costume_fixture")
        if name == "entities":
            if not isinstance(costume, dict):
                raise ValueError("Original costume fixture is required")
            costume_path = child(root, costume["path"])
            if (costume_path.name != "costume_fixtures.h"
                    or digest(costume_path) != costume["sha256"]
                    or host.get("costume_fixtures_sha256") != costume["sha256"]):
                raise ValueError("Costume fixture differs from original host oracle")
        elif costume is not None:
            raise ValueError("Unexpected costume fixture")
        lookup = suite.get("lookup_fixture")
        if name == "scenegraph":
            if not isinstance(lookup, dict):
                raise ValueError("Original lookup fixture is required")
            lookup_path = child(root, lookup["path"])
            if (lookup_path.name != "lookup_fixtures.h"
                    or digest(lookup_path) != lookup["sha256"]
                    or host.get("lookup_fixtures_sha256") != lookup["sha256"]):
                raise ValueError("Lookup fixture differs from original host oracle")
        elif lookup is not None:
            raise ValueError("Unexpected lookup fixture")
        fixture = suite.get("fixture")
        if name in FIXTURES:
            if not isinstance(fixture, dict):
                raise ValueError("Generated source fixture artifact is required: " + name)
            fixture_path = child(root, fixture["path"])
            if (fixture_path.name != FIXTURES[name] or digest(fixture_path) != fixture["sha256"]
                    or host.get("fixtures_sha256") != fixture["sha256"]):
                raise ValueError("Preserved fixture differs from its host source oracle: " + name)
            # Bind both build ABIs even when this run executes only x86_64.
            for built_abi, built_item in suite["abis"].items():
                built_receipt_path = child(root, built_item["receipt"])
                built_receipt = read(built_receipt_path)
                if (digest(built_receipt_path) != built_item["receipt_sha256"]
                        or built_receipt.get("passed") is not True
                        or built_receipt.get("abi") != built_abi
                        or built_receipt.get("fixtures_sha256") != fixture["sha256"]):
                    raise ValueError("Both Android ABI fixtures must match the host oracle: " + name)
                if costume and built_receipt.get("costume_fixtures_sha256") != costume["sha256"]:
                    raise ValueError("Both ABI costume fixtures must match original oracle")
                if lookup and built_receipt.get("lookup_fixtures_sha256") != lookup["sha256"]:
                    raise ValueError("Both ABI lookup fixtures must match original oracle")
        elif fixture is not None:
            raise ValueError("Unexpected external fixture for the standalone auth policy suite")
        if (receipt.get("passed") is not True or receipt.get("abi") != abi
                or receipt.get("binary") != binary.name
                or receipt.get("binary_sha256") != item["sha256"]):
            raise ValueError("Build receipt does not identify the executable: " + name)
        expected = native_result(suite["expected"])
        if host.get("passed") is not True or not json_equal(host.get("checks", {}).get("release"), expected):
            raise ValueError("Expected Android result differs from the successful host oracle: " + name)
        entries[name] = {"binary": binary, "expected": expected, "descriptor": item}
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", type=Path, required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=HERE.parents[2])
    parser.add_argument("--abi", choices=ABIS, default="x86_64")
    parser.add_argument("--device-kind", choices=("emulator", "physical"), default="emulator")
    parser.add_argument("--android-sdk", type=int, default=33)
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Refusing to overwrite an existing execution receipt")
    root = args.artifacts.resolve()
    proof = {"schema": "coh-primary-continuation-android-execution-v1", "passed": False,
             **{key: False for key in CLAIMS}, "suites": {}, "errors": {}, "abi": args.abi,
             "android_executed": False, "emulator_qualified": False,
             "physical_android_executed": False,
             "scope": "Standalone source-oracle contracts; no Combined APK, server, accounts or live world"}
    adb = [args.adb.resolve(), "-s", args.serial]
    command_number = 0

    def run(command, timeout=60):
        nonlocal command_number
        command_number += 1
        log = args.output.parent / "logs" / (str(command_number).zfill(3) + ".log")
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("wb") as stream:
            try:
                process = subprocess.run([str(value) for value in command], stdout=stream,
                                         stderr=subprocess.STDOUT, timeout=timeout)
            except subprocess.TimeoutExpired:
                raise RuntimeError("Android command timed out; retained " + str(log.name)) from None
        if process.returncode:
            raise RuntimeError("Android command failed; retained " + str(log.name))
        return log.read_text().strip()

    remote = None
    try:
        manifest_path = child(root, "android-execution-manifest.json")
        manifest = read(manifest_path)
        entries = validate(root, manifest, args.abi)
        proof["manifest_sha256"] = digest(manifest_path)
        proof["source_revision"] = manifest["source_revision"]
        state = git_state(args.source_root.resolve())
        if state["source_revision"] != manifest["source_revision"]:
            raise ValueError("Runner checkout differs from the qualified source revision")
        if args.require_clean and (state["source_git_status_porcelain"] or manifest["source_worktree_dirty"]):
            raise ValueError("Hosted execution requires clean qualified and runner source trees")
        run([*adb, "wait-for-device"])
        prop = lambda name: run([*adb, "shell", "getprop", name])
        if args.abi not in prop("ro.product.cpu.abilist").split(","):
            raise ValueError("Selected Android does not support the requested ABI")
        if prop("ro.build.version.sdk") != str(args.android_sdk):
            raise ValueError("Selected Android does not match the required SDK")
        emulator = prop("ro.kernel.qemu") == "1"
        if emulator != (args.device_kind == "emulator"):
            raise ValueError("Selected Android does not match --device-kind")
        proof.update(android_sdk=args.android_sdk, device_is_emulator=emulator,
                     android_release=prop("ro.build.version.release"), device_model=prop("ro.product.model"))
        remote = run([*adb, "shell", "mktemp", "-d", "/data/local/tmp/coh-primary.XXXXXX"])
        if not re.fullmatch(r"/data/local/tmp/coh-primary\.[A-Za-z0-9]+", remote):
            remote = None
            raise ValueError("Unexpected Android temporary directory")
        for name, entry in sorted(entries.items()):
            try:
                destination = remote + "/" + name
                run([*adb, "push", entry["binary"], destination])
                transferred_sha = run([*adb, "shell", "sha256sum", destination]).split()[0]
                if transferred_sha != entry["descriptor"]["sha256"]:
                    raise ValueError("Transferred executable identity differs")
                run([*adb, "shell", "chmod", "700", destination])
                stdout = run([*adb, "shell", destination], timeout=180)
                actual = native_result(json.loads(stdout))
                if not json_equal(actual, entry["expected"]):
                    write(args.output.parent / (name + "-unexpected.json"), actual)
                    raise ValueError("Android output differs from the exact source-qualified host result")
                proof["suites"][name] = {"passed": True, "android_executed": True,
                    "binary_sha256": transferred_sha, "result": actual,
                    "build_receipt_sha256": entry["descriptor"]["receipt_sha256"]}
            except Exception as error:
                proof["errors"][name] = str(error)
            write(args.output, proof)
        proof["passed"] = not proof["errors"] and set(proof["suites"]) == set(MODULES)
        proof["emulator_qualified"] = proof["passed"] and emulator
        proof["physical_android_executed"] = proof["passed"] and not emulator
    except Exception as error:
        proof["errors"]["execution"] = str(error)
    finally:
        if remote is not None:
            try:
                run([*adb, "shell", "rm", "-rf", remote])
                proof["temporary_files_removed"] = True
            except Exception as error:
                proof["errors"]["cleanup"] = str(error)
                proof["passed"] = False
                proof["emulator_qualified"] = False
                proof["physical_android_executed"] = False
    proof["android_executed"] = bool(proof["suites"])
    write(args.output, proof)
    print(json.dumps(proof, indent=2, sort_keys=True))
    return 0 if proof["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
