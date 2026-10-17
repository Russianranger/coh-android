#!/usr/bin/env python3
"""Qualify only the new entity suffix; no APK or previously accepted module rebuild."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("tail_evidence_common", HERE.parent / "scenecatalog-qualification/common.py")
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
ABIS, CLAIMS = common.ABIS, common.CLAIMS
ENGINE = "native-android/engine/"
SCHEMA = "coh-very-rare-tail-android-build-v1"
REQUIRED = {ENGINE + name for name in (
    "entities/coh_very_rare_tail.c", "entities/coh_very_rare_tail.h",
    "entities/test_very_rare_tail.c", "entities/tail_oracle_shim.h",
    "entities/tail_fixture.c.inc", "entities/tail_observation.h",
    "entities/very-rare-tail-source-pins.json", "entities/check_very_rare_tail.py",
    "replication/coh_replication.c", "replication/coh_replication.h", "coh_contracts.h")}
REQUIRED.update({"native-android/include/coh_native_core.h", "native-android/tools/protocol_fixture/prepare.py"})
DRIVERS = {ENGINE + "continuation/very_rare_tail_android.py",
           ENGINE + "continuation/test_very_rare_tail_android.py",
           ENGINE + "scenecatalog-qualification/common.py",
           ".github/workflows/native-entity-tail.yml"}
FALSE_CLAIMS = ("full_update_complete", "stale_state_application_qualified", "dictionary_authority",
                "actor_publication", "acknowledgments_enabled", "real_server_interoperability", "thor_accepted")
FUNCTIONS = {"entSendOtherSupergroupInfo", "entReceiveOtherSupergroupInfo",
             "entSendLevelingpactInfo", "entReceiveLevelingpactInfo",
             "entSendLogoutUpdate", "entReceiveLogoutUpdate", "TaskStatusSend", "TaskStatusReceive"}


def original_sources(repo, host):
    pins = common.read(common.child(repo, ENGINE + "entities/very-rare-tail-source-pins.json"))["sha256_lf"]
    if len(pins) != 13 or not common.json_equal(pins, host.get("original", {}).get("source_sha256_lf")):
        raise ValueError("Complete original-source pins required")
    for name, expected in common.source_hashes(pins).items():
        relative = "upstream/ouroboros/" + name
        path = repo / relative
        raw = path.read_bytes() if path.is_file() else subprocess.check_output(["git", "-C", str(repo), "show", "HEAD:" + relative])
        if hashlib.sha256(raw.decode().replace("\r\n", "\n").encode()).hexdigest() != expected:
            raise ValueError("Original producer/consumer source differs: " + name)
    original = host["original"]
    if (set(original.get("whole_functions_executed", [])) != FUNCTIONS
            or original.get("oracle_sanitized") is not False):
        raise ValueError("Exact original function scope required")


def validate(repo, root, proof):
    common.reject_claims(proof, required=True)
    if (proof.get("schema") != SCHEMA or proof.get("passed") is not True
            or proof.get("android_executed") is not False or proof.get("source_worktree_dirty") is not False
            or set(proof.get("abis", {})) != set(ABIS)
            or not re.fullmatch(r"[a-f0-9]{40}", proof.get("source_revision", ""))):
        raise ValueError("Complete clean entity-tail build receipt required")
    if common.git_state(repo)["source_revision"] != proof["source_revision"]:
        raise ValueError("Build revision differs from runner checkout")
    common.verify_sources(repo, proof["source_sha256"])
    if set(proof["source_sha256"]) != REQUIRED | DRIVERS:
        raise ValueError("Exact entity-tail source closure required")
    host_path = common.child(root, "host.json")
    if common.digest(host_path) != proof.get("host_receipt_sha256"):
        raise ValueError("Host receipt identity differs")
    host = common.read(host_path)
    if (host.get("schema") != "coh-very-rare-tail-qualification-v1" or host.get("passed") is not True
            or host.get("prepare_only") is not False or host.get("source_worktree_clean") is not True
            or host.get("source_unchanged_before_after") is not True or host.get("cpp_link_passed") is not True
            or host.get("source_revision") != proof["source_revision"]
            or set(host.get("source_sha256", {})) != REQUIRED
            or any(proof["source_sha256"].get(k) != v for k, v in host["source_sha256"].items())):
        raise ValueError("Complete exact-source host qualification required")
    common.reject_claims(host)
    for key in FALSE_CLAIMS:
        if host.get(key) is not False:
            raise ValueError("Unsupported host authority: " + key)
    original_sources(repo, host)
    expected = common.native_result(proof.get("expected"))
    if any(expected.get(key) is not False for key in ("full_update_complete", "actor_publication")):
        raise ValueError("Native suffix must remain uncommitted outer-message staging")
    for key in ("truncations", "mutations", "randomized", "fixtures", "output_bytes", "workspace_bytes"):
        if type(expected.get(key)) is not int or expected[key] <= 0:
            raise ValueError("Missing native negative/resource evidence: " + key)
    if type(expected.get("aggregate_limit")) is not int or expected["aggregate_limit"] != 4 * 1024**2:
        raise ValueError("Exact bounded native aggregate required")
    if set(host.get("checks", {})) != {"release", "asan", "ubsan"}:
        raise ValueError("Release and both sanitizer modes required")
    for result in host["checks"].values():
        if not common.json_equal(result, expected):
            raise ValueError("Native host modes differ")
    fixture_hash = host.get("fixtures", {}).get("sha256")
    if common.digest(common.child(root, "android/tail_fixtures.h")) != fixture_hash:
        raise ValueError("Original-source fixture identity differs")
    if set(host.get("android", {})) != set(ABIS):
        raise ValueError("Host receipt lacks both ABI builds")
    for abi, item in proof["abis"].items():
        binary, receipt_path = common.child(root, item["path"]), common.child(root, item["receipt"])
        if (type(item.get("bytes")) is not int or not 64 <= item["bytes"] <= 128 * 1024**2
                or binary.stat().st_size != item["bytes"] or common.digest(binary) != item["sha256"]
                or common.digest(receipt_path) != item["receipt_sha256"]):
            raise ValueError("ABI artifact identity differs")
        common.elf_identity(binary, abi)
        receipt = common.read(receipt_path)
        if (receipt.get("built") is not True or receipt.get("executed") is not False
                or receipt.get("binary") != binary.name or receipt.get("binary_sha256") != item["sha256"]
                or receipt.get("fixtures_sha256") != fixture_hash
                or not common.json_equal(receipt.get("source_sha256"), host["source_sha256"])
                or not common.json_equal(host["android"][abi], receipt)):
            raise ValueError("ABI source/fixture receipt differs")
        common.reject_compile_claims(receipt)
    return expected


def build(args):
    repo, out = args.source_root.resolve(), args.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError("Refusing to overwrite qualification")
    state = common.git_state(repo)
    if state["source_git_status_porcelain"]:
        raise ValueError("Clean committed entity-tail source required")
    proof = dict(schema=SCHEMA, passed=False, android_executed=False,
                 source_revision=state["source_revision"], source_worktree_dirty=False,
                 **{key: False for key in CLAIMS})
    try:
        common.execute([sys.executable, repo / ENGINE / "entities/check_very_rare_tail.py",
                        "--source-root", repo, "--sanitize", "--ndk", args.ndk.resolve(),
                        "--android-output", out / "android", "--output", out / "host.json"], out / "logs/host.log")
        host = common.read(out / "host.json")
        sources = dict(host["source_sha256"])
        sources.update({name: common.digest(common.child(repo, name)) for name in DRIVERS})
        proof.update(source_sha256=sources, host_receipt_sha256=common.digest(out / "host.json"),
                     expected=host["checks"]["release"], abis={})
        for abi in ABIS:
            receipt_path = common.child(out, "android/" + abi + "/receipt.json")
            receipt = common.read(receipt_path)
            binary = common.child(receipt_path.parent, receipt["binary"])
            proof["abis"][abi] = dict(path=binary.relative_to(out).as_posix(), bytes=binary.stat().st_size,
                sha256=common.digest(binary), receipt=receipt_path.relative_to(out).as_posix(),
                receipt_sha256=common.digest(receipt_path))
        proof["passed"] = True
        validate(repo, out, proof)
        if common.git_state(repo) != state:
            raise ValueError("Source changed during qualification")
    except Exception as error:
        proof.update(passed=False, error=str(error))
    common.write(out / "build.json", proof)
    print({"passed": proof["passed"], "error": proof.get("error"), "apk_rebuilt": False})
    return 0 if proof["passed"] else 1


def run_android(args):
    repo, root, out = args.source_root.resolve(), args.artifacts.resolve(), args.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError("Refusing to overwrite Android execution")
    proof = dict(schema="coh-very-rare-tail-android-execution-v1", passed=False,
                 execution_attempted=False, android_executed=False, emulator_qualified=False,
                 **{key: False for key in CLAIMS})
    remote, number = None, 0
    adb = [args.adb.resolve(), "-s", args.serial]
    def run(command, timeout=60):
        nonlocal number
        number += 1
        return common.execute([*adb, *command], out / "logs" / (f"{number:03d}.log"), timeout=timeout).strip()
    try:
        manifest = common.read(common.child(root, "build.json"))
        expected = validate(repo, root, manifest)
        state = common.git_state(repo)
        if state["source_git_status_porcelain"]:
            raise ValueError("Clean entity-tail execution source required")
        proof.update(source_revision=manifest["source_revision"], source_sha256=manifest["source_sha256"],
                     build_receipt_sha256=common.digest(root / "build.json"), abi="x86_64")
        run(["wait-for-device"])
        prop = lambda name: run(["shell", "getprop", name])
        if (prop("ro.kernel.qemu") != "1" or prop("ro.build.version.sdk") != "33"
                or "x86_64" not in prop("ro.product.cpu.abilist").split(",")):
            raise ValueError("Android 13 x86_64 emulator required")
        proof["android_build_fingerprint"] = prop("ro.build.fingerprint")
        remote = run(["shell", "mktemp", "-d", "/data/local/tmp/coh-entity-tail.XXXXXX"])
        if not re.fullmatch(r"/data/local/tmp/coh-entity-tail\.[A-Za-z0-9]+", remote):
            remote = None
            raise ValueError("Unexpected temporary directory")
        item = manifest["abis"]["x86_64"]
        run(["push", common.child(root, item["path"]), remote + "/tail-test"])
        if run(["shell", "sha256sum", remote + "/tail-test"]).split()[0] != item["sha256"]:
            raise ValueError("Transferred binary identity differs")
        run(["shell", "chmod", "700", remote + "/tail-test"])
        proof["execution_attempted"] = True
        common.write(out / "receipt.json", proof)
        result = common.loads(run(["shell", "timeout", "180", remote + "/tail-test"], timeout=240))
        proof.update(android_executed=True, result=result, binary_sha256=item["sha256"])
        if not common.json_equal(result, expected):
            raise ValueError("Android result differs from all host modes")
        validate(repo, root, manifest)
        if common.git_state(repo) != state:
            raise ValueError("Execution source changed")
        proof.update(passed=True, emulator_qualified=True)
    except Exception as error:
        proof.update(passed=False, emulator_qualified=False, error=str(error))
    finally:
        if remote is not None:
            try:
                run(["shell", "rm", "-rf", remote])
                run(["shell", "test", "!", "-e", remote])
                proof["temporary_files_removed"] = True
            except Exception as error:
                proof.update(passed=False, emulator_qualified=False, cleanup_error=str(error))
    common.write(out / "receipt.json", proof)
    return 0 if proof["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "run"))
    parser.add_argument("--source-root", type=Path, default=HERE.parents[2])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ndk", type=Path)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--adb", type=Path)
    parser.add_argument("--serial", default="emulator-5554")
    args = parser.parse_args()
    if args.mode == "build" and not args.ndk:
        parser.error("build requires --ndk")
    if args.mode == "run" and (not args.artifacts or not args.adb):
        parser.error("run requires --artifacts and --adb")
    return build(args) if args.mode == "build" else run_android(args)


if __name__ == "__main__":
    raise SystemExit(main())
