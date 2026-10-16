#!/usr/bin/env python3
"""Run exact standalone catalog/scene/entity ELFs on Android without an APK."""
from pathlib import Path
import argparse
import json
import re

from common import (ABIS, CLAIMS, FIXTURES, MODULES, SCHEMA, child, digest, elf_identity,
                    execute, git_state, hash_value, json_equal, loads, mapping, native_result,
                    read, reject_claims, reject_compile_claims, source_hashes, suite_sources, verify_sources, write)

HERE = Path(__file__).resolve().parent


def validate(root, manifest, abi):
    """Admit every artifact and both ABI receipts before any Android command."""
    mapping(manifest, "Manifest")
    if (manifest.get("schema") != SCHEMA or manifest.get("passed") is not True
            or set(mapping(manifest.get("suites"), "Suites")) != set(MODULES)):
        raise ValueError("All three successful scene catalog qualification suites are required")
    reject_claims(manifest, required=True)
    if (manifest.get("android_executed") is not False
            or type(manifest.get("source_worktree_dirty")) is not bool
            or manifest.get("sanitizers_passed") is not True):
        raise ValueError("Build manifest must identify unexecuted Android and sanitized host results")
    if not isinstance(manifest.get("source_revision"), str) or not re.fullmatch(r"[a-f0-9]{40}", manifest["source_revision"]):
        raise ValueError("Manifest must identify an exact Git source revision")
    aggregate_sources = source_hashes(manifest.get("source_sha256"))
    if abi not in ABIS:
        raise ValueError("Unsupported Android ABI")
    entries = {}
    for name in MODULES:
        suite = mapping(manifest["suites"][name], "Suite")
        if set(mapping(suite.get("abis"), "ABI artifacts")) != set(ABIS):
            raise ValueError("Both Android ABI artifacts are required: " + name)
        expected = native_result(suite.get("expected"))
        sources = suite_sources(name, suite.get("source_sha256"))
        if not all(aggregate_sources.get(path) == sha for path, sha in sources.items()):
            raise ValueError("Module sources differ from aggregate inventory: " + name)
        host_path = child(root, suite.get("host_receipt"))
        if digest(host_path) != hash_value(suite.get("host_receipt_sha256")):
            raise ValueError("Host oracle receipt identity differs: " + name)
        host = mapping(read(host_path), "Host receipt")
        reject_compile_claims(host)
        checks = mapping(host.get("checks"), "Host checks")
        if (host.get("passed") is not True or not json_equal(host.get("source_sha256"), sources)
                or type(host.get("fixtures")) is not int or host["fixtures"] <= 0):
            raise ValueError("Host receipt must identify successful original-source fixtures: " + name)
        for mode in ("release", "asan", "ubsan"):
            if not json_equal(native_result(checks.get(mode)), expected):
                raise ValueError("Expected Android result differs from sanitized host oracle: " + name)
        fixture = mapping(suite.get("fixture"), "Preserved fixture")
        fixture_path = child(root, fixture.get("path"))
        if (fixture_path.name != FIXTURES[name] or digest(fixture_path) != hash_value(fixture.get("sha256"))
                or host.get("fixtures_sha256") != fixture["sha256"]):
            raise ValueError("Preserved fixture differs from its source oracle: " + name)
        costume = suite.get("costume_fixture")
        if name == "entities":
            mapping(costume, "Original costume fixture")
            path = child(root, costume.get("path"))
            if (path.name != "costume_fixtures.h" or digest(path) != hash_value(costume.get("sha256"))
                    or host.get("costume_fixtures_sha256") != costume["sha256"]):
                raise ValueError("Costume fixture differs from original host oracle")
        elif costume is not None:
            raise ValueError("Unexpected costume fixture")
        lookup = suite.get("lookup_fixture")
        if name == "scenegraph":
            mapping(lookup, "Original lookup fixture")
            path = child(root, lookup.get("path"))
            if (path.name != "lookup_fixtures.h" or digest(path) != hash_value(lookup.get("sha256"))
                    or host.get("lookup_fixtures_sha256") != lookup["sha256"]):
                raise ValueError("Lookup fixture differs from original host oracle")
        elif lookup is not None:
            raise ValueError("Unexpected lookup fixture")
        for built_abi in ABIS:
            item = mapping(suite["abis"][built_abi], "ABI artifact")
            binary, receipt_path = child(root, item.get("binary")), child(root, item.get("receipt"))
            if (item.get("abi") != built_abi or digest(binary) != hash_value(item.get("sha256"))
                    or digest(receipt_path) != hash_value(item.get("receipt_sha256"))):
                raise ValueError("Android artifact or build receipt identity differs: " + name + "/" + built_abi)
            if (type(item.get("bytes")) is not int or not 0 < item["bytes"] <= 128 * 1024 * 1024
                    or item["bytes"] != binary.stat().st_size):
                raise ValueError("Invalid executable byte count")
            elf_identity(binary, built_abi)
            receipt = mapping(read(receipt_path), "Build receipt")
            reject_compile_claims(receipt)
            if costume and receipt.get("costume_fixtures_sha256") != costume["sha256"]:
                raise ValueError("Both ABI costume fixtures must match original oracle")
            if lookup and receipt.get("lookup_fixtures_sha256") != lookup["sha256"]:
                raise ValueError("Both ABI lookup fixtures must match original oracle")
            if (receipt.get("passed") is not True or receipt.get("abi") != built_abi
                    or receipt.get("binary") != binary.name
                    or receipt.get("binary_sha256") != item["sha256"]
                    or receipt.get("fixtures_sha256") != fixture["sha256"]
                    or not json_equal(receipt.get("source_sha256"), sources)):
                raise ValueError("Build receipt differs from exact host source/fixture/executable: " + name + "/" + built_abi)
        entries[name] = {"binary": child(root, suite["abis"][abi]["binary"]), "expected": expected,
                         "descriptor": suite["abis"][abi]}
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
    if args.output.parent.exists() and (not args.output.parent.is_dir() or any(args.output.parent.iterdir())):
        parser.error("Execution output directory must be empty; retain prior command evidence")
    root, repo = args.artifacts.resolve(), args.source_root.resolve()
    proof = {"schema": "coh-scenecatalog-android-execution-v1", "passed": False,
        **{key: False for key in CLAIMS}, "suites": {}, "errors": {}, "abi": args.abi,
        "android_executed": False, "emulator_qualified": False, "physical_android_executed": False,
        "scope": "Standalone source-oracle catalog/scene/entity contracts; no APK, account, server or live world"}
    adb = [args.adb.resolve(), "-s", args.serial]
    command_number = 0

    def run(command, timeout=60):
        nonlocal command_number
        command_number += 1
        log = args.output.parent / "logs" / (str(command_number).zfill(3) + ".log")
        return execute(command, log, timeout=timeout).strip()

    remote = None
    try:
        manifest_path = child(root, "android-execution-manifest.json")
        manifest = read(manifest_path)
        entries = validate(root, manifest, args.abi)
        qualification_path = child(root, "qualification.json")
        qualified = mapping(read(qualification_path), "Aggregate qualification")
        if (qualified.get("passed") is not True or qualified.get("android_built") is not True
                or qualified.get("android_manifest_sha256") != digest(manifest_path)
                or qualified.get("source_revision") != manifest["source_revision"]
                or not json_equal(qualified.get("source_sha256"), manifest["source_sha256"])):
            raise ValueError("Manifest differs from completed aggregate qualification")
        reject_claims(qualified, required=True)
        reject_compile_claims(qualified)
        proof.update(manifest_sha256=digest(manifest_path), qualification_sha256=digest(qualification_path),
                     source_revision=manifest["source_revision"], source_sha256=manifest["source_sha256"])
        state = git_state(repo)
        if state["source_revision"] != manifest["source_revision"]:
            raise ValueError("Runner checkout differs from qualified source revision")
        if args.require_clean and (state["source_git_status_porcelain"] or manifest["source_worktree_dirty"]):
            raise ValueError("Execution requires clean qualified and runner source trees")
        verify_sources(repo, manifest["source_sha256"])
        run([*adb, "wait-for-device"])
        prop = lambda name: run([*adb, "shell", "getprop", name])
        if args.abi not in prop("ro.product.cpu.abilist").split(","):
            raise ValueError("Selected Android does not support requested ABI")
        if prop("ro.build.version.sdk") != str(args.android_sdk):
            raise ValueError("Selected Android does not match required SDK")
        emulator = prop("ro.kernel.qemu") == "1"
        if emulator != (args.device_kind == "emulator"):
            raise ValueError("Selected Android does not match --device-kind")
        proof.update(android_sdk=args.android_sdk, device_is_emulator=emulator,
                     android_release=prop("ro.build.version.release"), device_model=prop("ro.product.model"),
                     android_build_fingerprint=prop("ro.build.fingerprint"))
        remote = run([*adb, "shell", "mktemp", "-d", "/data/local/tmp/coh-catalog.XXXXXX"])
        if not re.fullmatch(r"/data/local/tmp/coh-catalog\.[A-Za-z0-9]+", remote):
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
                actual = native_result(loads(run([*adb, "shell", destination], timeout=180)))
                if not json_equal(actual, entry["expected"]):
                    write(args.output.parent / (name + "-unexpected.json"), actual)
                    raise ValueError("Android output differs from exact sanitized host oracle result")
                proof["suites"][name] = {"passed": True, "android_executed": True,
                    "binary_sha256": transferred_sha, "result": actual,
                    "build_receipt_sha256": entry["descriptor"]["receipt_sha256"]}
            except Exception as error:
                proof["errors"][name] = str(error)
            write(args.output, proof)
        verify_sources(repo, manifest["source_sha256"])
        state_end = git_state(repo)
        if (state_end["source_revision"] != manifest["source_revision"]
                or (args.require_clean and state_end["source_git_status_porcelain"])):
            raise ValueError("Runner source state changed during Android execution")
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
                proof["passed"] = proof["emulator_qualified"] = proof["physical_android_executed"] = False
    proof["android_executed"] = bool(proof["suites"])
    write(args.output, proof)
    print(json.dumps(proof, indent=2, sort_keys=True))
    return 0 if proof["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
