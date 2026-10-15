#!/usr/bin/env python3
"""Qualify additive live-session contracts without rebuilding accepted APKs.

Real TCP/UDP fixture exchanges, original-function oracles and cross-built test
executables are distinct from authentication against a complete source shard.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ABIS = ("arm64-v8a", "x86_64")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def execute(command, log, result=None):
    command = [str(value) for value in command]
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, timeout=1200)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(process.stdout)
    if process.returncode:
        raise RuntimeError(f"Exit {process.returncode}; see {log.name}: " + process.stdout[-2000:])
    if result:
        proof = read(result)
        if proof.get("passed") is not True and proof.get("status") != "PASS":
            raise ValueError(f"Qualification result did not pass: {result}")
        return proof
    return {"passed": True}


def verify_crypto(root, native):
    pin = read(native / "engine/auth/android/openssl-source.json")
    for abi in ABIS:
        output = root / abi
        receipt = read(output / "receipt.json")
        if (receipt.get("status") != "PASS" or receipt.get("abi") != abi
                or receipt.get("openssl_archive_sha256") != pin["sha256"]
                or receipt.get("source_pin_sha256") != digest(native / "engine/auth/android/openssl-source.json")):
            raise ValueError("Public Android crypto pin or ABI receipt differs")
        for relative, expected in receipt["artifacts_sha256"].items():
            if digest(output / relative) != expected:
                raise ValueError("Public Android crypto artifact hash differs: " + relative)
        for relative, expected in receipt["native_source_sha256"].items():
            if digest(native / relative) != expected:
                raise ValueError("Reusable crypto was built from different native source: " + relative)
    return {"passed": True, "abis": list(ABIS), "verified_source_and_artifact_hashes": True}


def binary_descriptor(out, binary, receipt, abi):
    if not binary.is_file() or not receipt.is_file():
        raise ValueError("Android executable or receipt missing: " + str(binary))
    return {
        "abi": abi, "binary": binary.relative_to(out).as_posix(),
        "sha256": digest(binary), "bytes": binary.stat().st_size,
        "receipt": receipt.relative_to(out).as_posix(), "receipt_sha256": digest(receipt),
    }


def manifest(out, results):
    crypto = {abi: binary_descriptor(out, out / "crypto" / abi / "test_auth_android",
                                     out / "crypto" / abi / "receipt.json", abi) for abi in ABIS}
    login = {}
    maps = {}
    for abi in ABIS:
        for module, destination in (("login", login), ("mapclient", maps)):
            receipt = out / "android" / module / abi / "receipt.json"
            proof = read(receipt)
            if proof.get("passed") is not True or proof.get("abi") != abi:
                raise ValueError("Android build receipt did not pass: " + str(receipt))
            binary = receipt.parent / proof["binary"]
            if binary.name != proof["binary"] or digest(binary) != proof["binary_sha256"]:
                raise ValueError("Android module executable identity differs")
            destination[abi] = binary_descriptor(out, binary, receipt, abi)
    dbreceipt = out / "android/dbclient/android-build.json"
    dbproof = read(dbreceipt)
    db = {"wire": {}, "session": {}}
    for item in dbproof["artifacts"]:
        if item["abi"] not in ABIS or item["kind"] not in db or item.get("built") is not True:
            raise ValueError("Unexpected DB Android artifact contract")
        binary = dbreceipt.parent / item["file"]
        if binary.name != item["file"] or digest(binary) != item["sha256"]:
            raise ValueError("DB Android executable identity differs")
        if item["abi"] in db[item["kind"]]:
            raise ValueError("Duplicate DB Android artifact")
        db[item["kind"]][item["abi"]] = binary_descriptor(out, binary, dbreceipt, item["abi"])
    if any(set(values) != set(ABIS) for values in db.values()):
        raise ValueError("DB Android build omitted a required ABI")
    dbhost = results["dbclient"]["checks"]["release"]
    maphost = results["mapclient"]["checks"]["release"]
    return {
        "schema": "coh-native-live-contracts-android-v1", "passed": True,
        "scope": "Five independent native crypto/TCP/UDP contracts with scripted peers; no full-shard authentication",
        "actual_server_interoperability_verified": False, "real_account_login_verified": False,
        "physical_thor_accepted": False, "android_executed": False,
        "suites": {
            "crypto": {"receipt_kind": "crypto", "abis": crypto,
                       "required": {"checks": 1920, "malformed_inputs": 10000,
                                    "authenticated_server_session": False}},
            "login": {"receipt_kind": "module", "abis": login,
                      "required": {"passed": True, "socket_scenarios": 11,
                                   "actual_os_tcp": True, "synthetic_authserver": True,
                                   "real_account_login_verified": False, "passwords_logged": False,
                                   "descriptor_cleanup": True}},
            "db_wire": {"receipt_kind": "db", "artifact_kind": "wire", "abis": db["wire"],
                        "required": {"passed": True, "malformed_inputs": dbhost["malformed_inputs"],
                                     "real_server_login": False}},
            "db_session": {"receipt_kind": "db", "artifact_kind": "session", "abis": db["session"],
                           "required": {"passed": True, "socket_scenarios": dbhost["session"]["socket_scenarios"],
                                        "actual_os_udp": True, "source_layout_peer": True,
                                        "real_authenticated_server": False, "socket_leak_check": True}},
            "mapclient": {"receipt_kind": "module", "abis": maps,
                          "required": {"negative_cases": maphost["negative_cases"],
                                       "scenarios": maphost["scenarios"], "actual_os_udp": True,
                                       "scripted_peer_only": True, "socket_leak_check": True,
                                       "actual_authentication": False, "live_world": False}},
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=HERE.parents[2])
    parser.add_argument("--ndk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--crypto-root", type=Path, help="Existing parent of both ABI public crypto outputs; verify and reuse")
    parser.add_argument("--sanitize", action="store_true")
    parser.add_argument("--jobs", type=int, default=3, help="Parallel OpenSSL make jobs")
    parser.add_argument("--workers", type=int, default=4, help="Independent host-check workers")
    parser.add_argument("--require-clean", action="store_true", help="Reject a dirty source tree, as required in hosted qualification")
    args = parser.parse_args()
    if args.jobs < 1 or args.workers < 1:
        parser.error("Build jobs and workers must be positive")
    repo = args.source_root.resolve()
    native = repo / "native-android"
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    ndk = args.ndk.resolve()
    if not (ndk / "source.properties").is_file():
        parser.error("--ndk must name an extracted public Android NDK")
    python = sys.executable
    sanitize = ["--sanitize"] if args.sanitize else []
    status = subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain=v1", "--untracked-files=normal"], text=True)
    if args.require_clean and status:
        parser.error("Hosted qualification requires a clean source working tree")
    proof = {"schema": "coh-native-live-contract-qualification-v1", "passed": False,
             "source_revision": subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip(),
             "source_git_status_porcelain": status.splitlines(), "source_worktree_dirty": bool(status),
             "clean_source_required": args.require_clean,
             "driver_sha256": digest(Path(__file__)), "parallel_host_workers": args.workers,
             "sanitizers_requested": args.sanitize, "results": {}, "errors": {},
             "android_executed": False, "emulator_qualified": False,
             "physical_thor_accepted": False, "actual_server_interoperability_verified": False,
             "real_account_login_verified": False, "full_live_world_verified": False,
             "accepted_apks_rebuilt": False, "gates25_27_complete": False}

    def crypto():
        if args.crypto_root:
            root = args.crypto_root.resolve()
            result = verify_crypto(root, native)
            for abi in ABIS:
                destination = out / "crypto" / abi
                if destination.resolve() != (root / abi).resolve():
                    if destination.exists():
                        raise ValueError("Refusing to overwrite reusable crypto output")
                    shutil.copytree(root / abi, destination)
            return {**result, "reused_existing_binaries": True}
        execute([python, native / "engine/auth/android/build.py", "--ndk", ndk,
                 "--output", out / "crypto", "--jobs", args.jobs], out / "logs/crypto-build.log")
        return {**verify_crypto(out / "crypto", native), "reused_existing_binaries": False}

    tasks = {"crypto_build": crypto}
    for name, relative, android in (
            ("crypto_host", "auth", False), ("dbclient", "dbclient", True),
            ("mapclient", "mapclient", True), ("server_oracle", "session/server-oracle", False)):
        command = [python, native / "engine" / relative / "check.py", "--source-root", repo,
                   "--output", out / "host" / (name + ".json"), *sanitize]
        if android:
            command += ["--ndk", ndk, "--android-output", out / "android" / name]
        tasks[name] = lambda command=command, name=name: execute(command, out / "logs" / (name + ".log"),
                                                                out / "host" / (name + ".json"))
    live_owner = native / "engine/live/check.py"
    proof["live_owner_host_contract_present"] = live_owner.is_file()
    if live_owner.is_file():
        tasks["live_owner"] = lambda: execute(
            [python, live_owner, "--source-root", repo, "--ndk", ndk,
             "--output", out / "host/live_owner.json", *sanitize],
            out / "logs/live_owner.log", out / "host/live_owner.json")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(action): name for name, action in tasks.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                proof["results"][name] = future.result()
            except Exception as error:
                proof["errors"][name] = str(error)
            write(out / "qualification.json", proof)
    if not proof["errors"]:
        try:
            login_output = out / "host/login.json"
            proof["results"]["login"] = execute(
                [python, native / "engine/login/check.py", "--source-root", repo, "--output", login_output,
                 "--ndk", ndk, "--crypto-root", out / "crypto", "--android-output", out / "android/login", *sanitize],
                out / "logs/login.log", login_output)
            proof["results"]["combined_arm64"] = execute(
                [python, native / "engine/build.py", "--ndk", ndk,
                 "--crypto-root", out / "crypto/arm64-v8a", "--output", out / "engine-arm64"],
                out / "logs/engine-arm64.log", out / "engine-arm64/build-receipt.json")
            proof["results"]["combined_host"] = execute(
                [python, native / "engine/build.py", "--output", out / "engine-host", *sanitize],
                out / "logs/engine-host.log", out / "engine-host/build-receipt.json")
            android_manifest = manifest(out, proof["results"])
            write(out / "android-execution-manifest.json", android_manifest)
            proof["android_manifest_sha256"] = digest(out / "android-execution-manifest.json")
            proof["passed"] = True
        except Exception as error:
            proof["errors"]["dependent_integration"] = str(error)
    proof["source_revision_end"] = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    status_end = subprocess.check_output(
        ["git", "-C", str(repo), "status", "--porcelain=v1", "--untracked-files=normal"], text=True)
    proof["source_git_status_porcelain_end"] = status_end.splitlines()
    proof["source_revision_changed_during_qualification"] = proof["source_revision_end"] != proof["source_revision"]
    if args.require_clean and (status_end or proof["source_revision_changed_during_qualification"]):
        proof["passed"] = False
        proof["errors"]["clean_source"] = "Hosted source changed during qualification"
    write(out / "qualification.json", proof)
    print(json.dumps({"passed": proof["passed"], "completed_checks": sorted(proof["results"]),
                      "errors": proof["errors"], "android_executed": False,
                      "real_account_login_verified": False}, indent=2))
    if not proof["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
