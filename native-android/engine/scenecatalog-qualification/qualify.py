#!/usr/bin/env python3
"""Run source oracles and standalone catalog/scene/entity contracts, never APKs."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
import json
import subprocess
import sys

from common import (ABIS, CLAIMS, FIXTURES, MODULES, SCHEMA, child, digest, elf_identity,
                    execute, git_state, json_equal, native_result, read, reject_compile_claims,
                    suite_sources, verify_sources, write)

HERE = Path(__file__).resolve().parent


def inventory(repo):
    """Bind native implementation, oracle adapters, original inputs and runner bytes."""
    directories = [*("native-android/engine/" + name for name in (*MODULES, "replication", "scenecatalog-server", "scenecatalog-qualification")),
                   "native-android/tools/protocol_fixture", "native-android/include"]
    names = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z", "--", *directories], text=True).split("\0")
    paths = {name for name in names if name and (Path(name).suffix in (".c", ".h", ".inc", ".py")
              or Path(name).name == "CMakeLists.txt" or Path(name).name.endswith("pins.json"))}
    paths.add("native-android/engine/coh_contracts.h")
    paths.add("upstream/ouroboros/MapServer/src/svr/svr_init.c")
    paths.add(".github/workflows/native-scene-catalog.yml")
    # Expand the pin sets actually used by these three source oracles. Other
    # retained replication/crypto pin sets refer to optional original inputs
    # that these suites do not read and that a minimal clone need not contain.
    for name in sorted(paths.copy()):
        if (name.startswith(("native-android/engine/entities/", "native-android/engine/scenecatalog/"))
                and name.endswith("pins.json")) or name == "native-android/engine/replication/groups-source-pins.json":
            pins = read(child(repo, name))
            for original in pins.get("sha256_lf", {}):
                paths.add("upstream/ouroboros/" + original)
            for item in pins.get("sources", {}).values():
                if isinstance(item, dict) and "path" in item:
                    paths.add(item["path"])
    return {name: digest(child(repo, name)) for name in sorted(paths)}


def host_suite(out, module, value, sanitize):
    if value.get("passed") is not True:
        raise ValueError("Host source oracle did not pass: " + module)
    reject_compile_claims(value)
    expected = native_result(value.get("checks", {}).get("release"))
    for mode in (("release", "asan", "ubsan") if sanitize else ("release",)):
        if not json_equal(native_result(value.get("checks", {}).get(mode)), expected):
            raise ValueError("Host sanitizer result differs from release: " + module + "/" + mode)
    if type(value.get("fixtures")) is not int or value["fixtures"] <= 0:
        raise ValueError("Original-source fixture count must be a positive integer")
    fixture = child(out, "fixtures/" + module + "/" + FIXTURES[module])
    if digest(fixture) != value.get("fixtures_sha256"):
        raise ValueError("Preserved fixture differs from host oracle: " + module)
    suite_sources(module, value.get("source_sha256"))
    costume = None
    if module == "entities":
        path = child(out, "fixtures/entities/costume_fixtures.h")
        if digest(path) != value.get("costume_fixtures_sha256"):
            raise ValueError("Preserved costume fixture differs from original oracle")
        costume = {"path": path.relative_to(out).as_posix(), "sha256": digest(path)}
    host = out / "host" / (module + ".json")
    return {"expected": expected, "source_sha256": value["source_sha256"],
            "fixture": {"path": fixture.relative_to(out).as_posix(), "sha256": digest(fixture)},
            "costume_fixture": costume,
            "host_receipt": host.relative_to(out).as_posix(), "host_receipt_sha256": digest(host)}


def manifest_suite(out, module, host, sanitize):
    suite = host_suite(out, module, host, sanitize)
    suite["abis"] = {}
    for abi in ABIS:
        receipt_path = out / "android" / module / abi / "receipt.json"
        receipt = read(receipt_path)
        reject_compile_claims(receipt)
        if suite["costume_fixture"] and receipt.get("costume_fixtures_sha256") != suite["costume_fixture"]["sha256"]:
            raise ValueError("Android costume fixture differs from original oracle")
        if (receipt.get("passed") is not True or receipt.get("abi") != abi
                or receipt.get("fixtures_sha256") != suite["fixture"]["sha256"]
                or not json_equal(receipt.get("source_sha256"), suite["source_sha256"])):
            raise ValueError("Android receipt differs from source oracle: " + module + "/" + abi)
        name = receipt.get("binary")
        if not isinstance(name, str) or Path(name).name != name:
            raise ValueError("Android executable name must be a basename")
        binary = child(receipt_path.parent, name)
        if digest(binary) != receipt.get("binary_sha256"):
            raise ValueError("Build receipt does not identify executable bytes")
        elf_identity(binary, abi)
        suite["abis"][abi] = {"abi": abi, "binary": binary.relative_to(out).as_posix(),
            "sha256": digest(binary), "bytes": binary.stat().st_size,
            "receipt": receipt_path.relative_to(out).as_posix(), "receipt_sha256": digest(receipt_path)}
    return suite


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=HERE.parents[2])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ndk", type=Path)
    parser.add_argument("--sanitize", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error("--workers must be between 1 and 8")
    repo, out = args.source_root.resolve(), args.output.resolve()
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        parser.error("--output must be empty; retain prior qualification artifacts")
    ndk = args.ndk.resolve() if args.ndk else None
    if ndk and not args.sanitize:
        parser.error("Android artifacts require --sanitize host qualification")
    if ndk and not (ndk / "source.properties").is_file():
        parser.error("--ndk must name an extracted public Android NDK")
    out.mkdir(parents=True, exist_ok=True)
    proof = {"schema": "coh-scenecatalog-qualification-v1", "passed": False,
        **{key: False for key in CLAIMS}, "android_executed": False, "android_built": False,
        "emulator_qualified": False, "results": {}, "errors": {},
        "scope": "Standalone original-source scene catalog, scenegraph regression and staged entity transactions",
        "driver_sha256": digest(Path(__file__)), "sanitizers_requested": args.sanitize,
        "clean_source_required": args.require_clean}
    try:
        proof.update(git_state(repo))
        proof["source_worktree_dirty"] = bool(proof["source_git_status_porcelain"])
        if args.require_clean and proof["source_worktree_dirty"]:
            raise ValueError("Qualification requires a clean source tree")
        proof["source_sha256"] = inventory(repo)
        if ndk:
            proof["ndk_source_properties"] = (ndk / "source.properties").read_text()
            proof["ndk_source_properties_sha256"] = digest(ndk / "source.properties")
        write(out / "qualification.json", proof)

        def check(module):
            result = out / "host" / (module + ".json")
            command = [sys.executable, repo / "native-android/engine" / module / "check.py",
                "--source-root", repo, "--output", result,
                "--fixtures-output", (out / "fixtures" / module / FIXTURES[module]
                                      if module == "entities" else out / "fixtures" / module)]
            if ndk:
                command += ["--ndk", ndk, "--android-output", out / "android" / module]
            if args.sanitize:
                command.append("--sanitize")
            execute(command, out / "logs" / (module + ".log"))
            value = read(result)
            host_suite(out, module, value, args.sanitize)
            verify_sources(repo, value["source_sha256"])
            if not all(proof["source_sha256"].get(name) == sha for name, sha in value["source_sha256"].items()):
                raise ValueError("Module source bytes are missing from aggregate inventory: " + module)
            return value

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(check, module): module for module in MODULES}
            for future in as_completed(futures):
                module = futures[future]
                try:
                    proof["results"][module] = future.result()
                except Exception as error:
                    proof["errors"][module] = str(error)
                write(out / "qualification.json", proof)
        state_end = git_state(repo)
        proof["source_revision_end"] = state_end["source_revision"]
        proof["source_git_status_porcelain_end"] = state_end["source_git_status_porcelain"]
        if (state_end["source_revision"] != proof["source_revision"]
                or (args.require_clean and state_end["source_git_status_porcelain"])):
            raise ValueError("Source state changed during qualification")
        verify_sources(repo, proof["source_sha256"])
        if not proof["errors"]:
            if ndk:
                manifest = {"schema": SCHEMA, "passed": True,
                    "source_revision": proof["source_revision"], "source_sha256": proof["source_sha256"],
                    "source_worktree_dirty": proof["source_worktree_dirty"],
                    "sanitizers_passed": args.sanitize,
                    "suites": {module: manifest_suite(out, module, proof["results"][module], args.sanitize) for module in MODULES},
                    "android_executed": False, **{key: False for key in CLAIMS}, "scope": proof["scope"]}
                # The runner rechecks every ABI, not just the one selected for execution.
                from run_android import validate
                validate(out, manifest, "x86_64")
                write(out / "android-execution-manifest.json", manifest)
                proof["android_manifest_sha256"] = digest(out / "android-execution-manifest.json")
                proof["android_built"] = True
            proof["passed"] = True
    except Exception as error:
        proof["errors"]["qualification"] = str(error)
    write(out / "qualification.json", proof)
    print(json.dumps({"passed": proof["passed"], "results": sorted(proof["results"]),
        "errors": proof["errors"], "android_built": proof["android_built"], "accepted_apks_rebuilt": False}, indent=2))
    return 0 if proof["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
