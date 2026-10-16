#!/usr/bin/env python3
"""Qualify isolated scene/entity/auth-policy contracts without rebuilding an APK."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
import json
import sys

from common import ABIS, CLAIMS, FIXTURES, MODULES, child, digest, elf_identity, execute, git_state, native_result, read, write

HERE = Path(__file__).resolve().parent


def manifest_suite(out, module, host):
    host_path = out / "host" / (module + ".json")
    expected = native_result(host["checks"]["release"])
    fixture = None
    if module in FIXTURES:
        fixture_path = child(out, Path("android") / module / FIXTURES[module])
        fixture_sha = digest(fixture_path)
        if host.get("fixtures_sha256") != fixture_sha:
            raise ValueError("Preserved fixture differs from the host oracle: " + module)
        fixture = {"path": fixture_path.relative_to(out).as_posix(), "sha256": fixture_sha}
    entries = {}
    for abi in ABIS:
        receipt_path = out / "android" / module / abi / "receipt.json"
        receipt = read(receipt_path)
        if receipt.get("passed") is not True or receipt.get("abi") != abi:
            raise ValueError("Android build receipt did not pass: " + module + "/" + abi)
        if fixture and receipt.get("fixtures_sha256") != fixture["sha256"]:
            raise ValueError("Android fixture differs from the host oracle: " + module + "/" + abi)
        name = receipt["binary"]
        if Path(name).name != name:
            raise ValueError("Android executable name must be a basename")
        binary = child(receipt_path.parent, name)
        if digest(binary) != receipt["binary_sha256"]:
            raise ValueError("Build receipt does not identify executable bytes")
        elf_identity(binary, abi)
        entries[abi] = {"abi": abi, "binary": binary.relative_to(out).as_posix(),
                        "sha256": digest(binary), "bytes": binary.stat().st_size,
                        "receipt": receipt_path.relative_to(out).as_posix(),
                        "receipt_sha256": digest(receipt_path)}
    return {"expected": expected, "abis": entries, "fixture": fixture,
            "host_receipt": host_path.relative_to(out).as_posix(),
            "host_receipt_sha256": digest(host_path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=HERE.parents[2])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ndk", type=Path, required=True)
    parser.add_argument("--sanitize", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error("--workers must be between 1 and 8")
    repo, out, ndk = args.source_root.resolve(), args.output.resolve(), args.ndk.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error("--output must be empty; retain prior qualification artifacts")
    if not (ndk / "source.properties").is_file():
        parser.error("--ndk must name an extracted public Android NDK")
    out.mkdir(parents=True, exist_ok=True)
    proof = {"schema": "coh-primary-continuation-qualification-v1", "passed": False,
             **{key: False for key in CLAIMS}, "android_executed": False,
             "emulator_qualified": False, "results": {}, "errors": {},
             "scope": "Additive bounded scene graph, entity records and authentication admission contracts",
             "driver_sha256": digest(Path(__file__)), "sanitizers_requested": args.sanitize,
             "clean_source_required": args.require_clean,
             "ndk_source_properties_sha256": digest(ndk / "source.properties")}
    try:
        proof.update(git_state(repo))
        proof["source_worktree_dirty"] = bool(proof["source_git_status_porcelain"])
        if args.require_clean and proof["source_worktree_dirty"]:
            raise ValueError("Hosted qualification requires a clean source tree")
        write(out / "qualification.json", proof)
        tasks = {}
        for module in MODULES:
            result = out / "host" / (module + ".json")
            command = [sys.executable, repo / "native-android/engine" / module / "check.py",
                       "--source-root", repo, "--output", result, "--ndk", ndk,
                       "--android-output", out / "android" / module]
            if args.sanitize:
                command.append("--sanitize")
            if module == "auth-interop":
                command += ["--probe-output", out / "host/coh_auth_interop_probe"]
            tasks[module] = (command, result)
        # Public crypto oracle is independent of deployment admission tests.
        result = out / "host/public-crypto-oracle.json"
        tasks["public-crypto-oracle"] = ([sys.executable, repo / "native-android/engine/auth/check.py",
            "--source-root", repo, "--output", result, *(["--sanitize"] if args.sanitize else [])], result)

        def check(name):
            command, result_path = tasks[name]
            execute(command, out / "logs" / (name + ".log"))
            value = read(result_path)
            if value.get("passed") is not True and value.get("status") != "PASS":
                raise ValueError("Host oracle/contract did not pass: " + name)
            if name == "auth-interop":
                lifecycle = native_result(value.get("probe_lifecycle"))
                probe = value.get("host_probe", {})
                if (lifecycle.get("auth_success_replies_sent") != 0
                        or lifecycle.get("real_account_login_verified") is not False
                        or probe.get("built") is not True or probe.get("executed") is not True
                        or probe.get("sha256") != digest(out / "host/coh_auth_interop_probe")):
                    raise ValueError("Missing exact host auth no-success lifecycle qualification")
            return value

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(check, name): name for name in tasks}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    proof["results"][name] = future.result()
                except Exception as error:
                    proof["errors"][name] = str(error)
                write(out / "qualification.json", proof)
        state_end = git_state(repo)
        proof["source_revision_end"] = state_end["source_revision"]
        proof["source_git_status_porcelain_end"] = state_end["source_git_status_porcelain"]
        if (state_end["source_revision"] != proof["source_revision"]
                or (args.require_clean and state_end["source_git_status_porcelain"])):
            raise ValueError("Source state changed during qualification")
        if not proof["errors"]:
            suites = {module: manifest_suite(out, module, proof["results"][module]) for module in MODULES}
            manifest = {"schema": "coh-primary-continuation-android-v1", "passed": True,
                        "source_revision": proof["source_revision"],
                        "source_worktree_dirty": proof["source_worktree_dirty"],
                        "suites": suites, "android_executed": False,
                        **{key: False for key in CLAIMS}, "scope": proof["scope"]}
            write(out / "android-execution-manifest.json", manifest)
            proof["android_manifest_sha256"] = digest(out / "android-execution-manifest.json")
            proof["passed"] = True
    except Exception as error:
        proof["errors"]["qualification"] = str(error)
    write(out / "qualification.json", proof)
    print(json.dumps({"passed": proof["passed"], "results": sorted(proof["results"]),
                      "errors": proof["errors"], "accepted_apks_rebuilt": False}, indent=2))
    return 0 if proof["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
