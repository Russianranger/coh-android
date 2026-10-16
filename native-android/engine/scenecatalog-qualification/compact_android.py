#!/usr/bin/env python3
"""Qualify compact topology against retained capture without a server or APK."""
from pathlib import Path
import argparse
import re
import sys

from common import (ABIS, CLAIMS, child, digest, elf_identity, execute, git_state,
                    json_equal, native_result, read, reject_claims, verify_sources, write)
from capture_android import MANIFEST, catalog_module, extract_capture

HERE = Path(__file__).resolve().parent
ENGINE = "native-android/engine/"
SCHEMA = "coh-authentic-compact-android-build-v1"
REQUIRED = {ENGINE + p for p in (
    "scenegraph/coh_scene_compact.c", "scenegraph/coh_scene_compact.h",
    "scenegraph/tests/test_scene_compact.c", "scenegraph/check_compact.py",
    "scenegraph/tests/compact_missing_audit.c", "scenegraph/coh_scenegraph.c", "scenegraph/coh_scenegraph.h",
    "scenecatalog/coh_scenecatalog.c", "scenecatalog/coh_scenecatalog.h", "scenecatalog/check.py",
    "scenecatalog/source_export.inc", "scenecatalog/tests/source_catalog_harness.c",
    "scenecatalog/check_file.py", "replication/coh_replication.c", "replication/coh_replication.h",
    "replication/coh_groups.c", "replication/coh_groups.h", "replication/groups_oracle.py",
    "replication/groups-source-pins.json", "coh_contracts.h")}.union({MANIFEST})
DRIVERS = (ENGINE + "scenecatalog-qualification/compact_android.py",
           ENGINE + "scenecatalog-qualification/common.py",
           ENGINE + "scenecatalog-qualification/capture_android.py",
           ".github/workflows/native-scene-catalog.yml",
           ".github/workflows/native-compact-recovery.yml")
MISSING_NAMES = ["_cot_warpgate_base", "_cot_warpgate_glow", "_mmayhem_curtain_8_01c",
                 "_mmayhem_curtain_8_02c", "_mmayhem_curtain_8_03c",
                 "_mmayhem_curtain_16_01c", "_mmayhem_curtain_16_02c"]


def validate(repo, root, proof):
    reject_claims(proof, required=True)
    if (proof.get("schema") != SCHEMA or proof.get("passed") is not True
            or proof.get("android_executed") is not False
            or proof.get("source_worktree_dirty") is not False
            or set(proof.get("abis", {})) != set(ABIS)
            or not re.fullmatch(r"[a-f0-9]{40}", proof.get("source_revision", ""))):
        raise ValueError("Complete clean compact build receipt required")
    if git_state(repo)["source_revision"] != proof["source_revision"]:
        raise ValueError("Build revision differs from runner checkout")
    verify_sources(repo, proof["source_sha256"])
    if not REQUIRED.union(DRIVERS).issubset(proof["source_sha256"]):
        raise ValueError("Compact source closure missing required input")
    capture, provenance = catalog_module(repo).admit_capture(root / "input")
    if not json_equal(proof.get("capture_provenance"), provenance):
        raise ValueError("Capture provenance differs")
    host_path = child(root, "host.json")
    if digest(host_path) != proof.get("host_receipt_sha256"):
        raise ValueError("Compact host receipt differs")
    host = read(host_path)
    if (host.get("passed") is not True or host.get("authentic_capture_refusal_tested") is not True
            or not json_equal(host.get("capture_provenance"), provenance)
            or not REQUIRED.issubset(host.get("source_sha256", {}))
            or any(proof["source_sha256"].get(k) != v for k, v in host["source_sha256"].items())):
        raise ValueError("Exact captured compact host qualification required")
    for key in ("graph_published_from_authentic_capture", "roots_bound", "assets_bound",
                "renderer_authorized", "android_executed", "physical_thor_accepted"):
        if host.get(key) is not False:
            raise ValueError("Compact host receipt claims unsupported authority: " + key)
    expected = native_result(proof.get("expected"))
    if (expected.get("actual_capture_expected_missing_ref") is not True
            or expected.get("world_ready") is not False
            or not json_equal(expected.get("live_allocations"), 0)):
        raise ValueError("Authentic missing-reference refusal and cleanup required")
    for key, value in (("actual_references_checked", 130314), ("actual_missing_count", 7),
                       ("actual_missing_stored", 7), ("actual_diagnostics_truncated", 0),
                       ("actual_missing_names", MISSING_NAMES)):
        if not json_equal(expected.get(key), value):
            raise ValueError("Exact captured missing-dependency diagnostics required")
    for key in ("actual_candidate_reserved_bytes", "actual_peak_live_payload_bytes", "actual_audit_named_peak_bytes"):
        if type(expected.get(key)) is not int or not 0 < expected[key] <= 96 * 1024**2:
            raise ValueError("Bounded actual-capture memory evidence required")
    for mode in ("release", "asan", "ubsan"):
        if not json_equal(host.get("checks", {}).get(mode), expected):
            raise ValueError("Compact host modes differ")
    fixture = child(root, "android/catalog_fixtures.h")
    if digest(fixture) != host.get("fixtures_sha256"):
        raise ValueError("Compact original-source fixture differs")
    for abi, item in proof["abis"].items():
        binary, receipt_path = child(root, item["path"]), child(root, item["receipt"])
        if (type(item.get("bytes")) is not int or not 0 < item["bytes"] <= 128 * 1024**2
                or binary.stat().st_size != item["bytes"] or digest(binary) != item["sha256"]
                or digest(receipt_path) != item["receipt_sha256"]):
            raise ValueError("Compact ABI file identity differs")
        elf_identity(binary, abi)
        receipt = read(receipt_path)
        if (receipt.get("passed") is not True or receipt.get("abi") != abi
                or receipt.get("binary") != binary.name or receipt.get("binary_sha256") != item["sha256"]
                or receipt.get("fixtures_sha256") != host["fixtures_sha256"]
                or not json_equal(receipt.get("source_sha256"), host["source_sha256"])
                or receipt.get("execution_qualified") is not False):
            raise ValueError("Compact ABI source or fixture receipt differs")
    return capture


def build(args):
    repo, out = args.source_root.resolve(), args.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError("Refusing to overwrite compact qualification")
    state = git_state(repo)
    if state["source_git_status_porcelain"]:
        raise ValueError("Clean committed compact source required")
    proof = dict(schema=SCHEMA, passed=False, android_executed=False,
                 source_revision=state["source_revision"], source_worktree_dirty=False,
                 **{key: False for key in CLAIMS})
    try:
        provenance = read(repo / MANIFEST)
        extract_capture(args.archive.resolve(), out / "input", provenance)
        execute([sys.executable, repo / ENGINE / "scenegraph/check_compact.py",
                 "--source-root", repo, "--capture-directory", out / "input",
                 "--sanitize", "--ndk", args.ndk.resolve(),
                 "--android-output", out / "android", "--output", out / "host.json"],
                out / "logs/host.log")
        host = read(out / "host.json")
        source = dict(host["source_sha256"])
        source.update({name: digest(child(repo, name)) for name in DRIVERS})
        proof.update(source_sha256=source, capture_provenance=provenance,
                     host_receipt_sha256=digest(out / "host.json"),
                     expected=host["checks"]["release"], abis={})
        for abi in ABIS:
            receipt_path = child(out, "android/" + abi + "/receipt.json")
            receipt = read(receipt_path)
            binary = child(receipt_path.parent, receipt["binary"])
            proof["abis"][abi] = dict(path=binary.relative_to(out).as_posix(),
                bytes=binary.stat().st_size, sha256=digest(binary),
                receipt=receipt_path.relative_to(out).as_posix(), receipt_sha256=digest(receipt_path))
        proof["passed"] = True
        validate(repo, out, proof)
        if git_state(repo) != state:
            raise ValueError("Compact source changed during qualification")
    except Exception as error:
        proof.update(passed=False, error=str(error))
    write(out / "build.json", proof)
    print({"passed": proof["passed"], "error": proof.get("error"), "apk_rebuilt": False})
    return 0 if proof["passed"] else 1


def run_android(args):
    repo, root, out = args.source_root.resolve(), args.artifacts.resolve(), args.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError("Refusing to overwrite compact Android execution")
    proof = dict(schema="coh-authentic-compact-android-execution-v1", passed=False,
                 execution_attempted=False, android_executed=False, emulator_qualified=False,
                 **{key: False for key in CLAIMS})
    remote, number = None, 0
    adb = [args.adb.resolve(), "-s", args.serial]
    def run(command, timeout=60):
        nonlocal number
        number += 1
        return execute([*adb, *command], out / "logs" / (f"{number:03d}.log"), timeout=timeout).strip()
    try:
        manifest = read(child(root, "build.json"))
        capture = validate(repo, root, manifest)
        state = git_state(repo)
        if state["source_git_status_porcelain"]:
            raise ValueError("Clean compact execution source required")
        proof.update(source_revision=manifest["source_revision"], source_sha256=manifest["source_sha256"],
                     build_receipt_sha256=digest(root / "build.json"),
                     capture_provenance=manifest["capture_provenance"], abi="x86_64")
        run(["wait-for-device"])
        prop = lambda name: run(["shell", "getprop", name])
        if (prop("ro.kernel.qemu") != "1" or prop("ro.build.version.sdk") != "33"
                or "x86_64" not in prop("ro.product.cpu.abilist").split(",")):
            raise ValueError("Android 13 x86_64 emulator required")
        proof["android_build_fingerprint"] = prop("ro.build.fingerprint")
        remote = run(["shell", "mktemp", "-d", "/data/local/tmp/coh-compact-capture.XXXXXX"])
        if not re.fullmatch(r"/data/local/tmp/coh-compact-capture\.[A-Za-z0-9]+", remote):
            remote = None
            raise ValueError("Unexpected temporary directory")
        item = manifest["abis"]["x86_64"]
        for path, name, sha in ((child(root, item["path"]), "compact-test", item["sha256"]),
                (capture, "catalog.cohcat", manifest["capture_provenance"]["catalog"]["sha256"])):
            run(["push", path, remote + "/" + name])
            if run(["shell", "sha256sum", remote + "/" + name]).split()[0] != sha:
                raise ValueError("Transferred compact file differs")
        run(["shell", "chmod", "700", remote + "/compact-test"])
        proof["execution_attempted"] = True
        write(out / "receipt.json", proof)
        from common import loads
        result = loads(run(["shell", "timeout", "120", remote + "/compact-test",
                            remote + "/catalog.cohcat"], timeout=180))
        proof.update(android_executed=True, result=result, binary_sha256=item["sha256"])
        if not json_equal(result, manifest["expected"]):
            raise ValueError("Compact Android result differs from host modes")
        validate(repo, root, manifest)
        if git_state(repo) != state:
            raise ValueError("Compact execution source changed")
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
    write(out / "receipt.json", proof)
    return 0 if proof["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "run"))
    parser.add_argument("--source-root", type=Path, default=HERE.parents[2])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--ndk", type=Path)
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--adb", type=Path)
    parser.add_argument("--serial", default="emulator-5554")
    args = parser.parse_args()
    if args.mode == "build" and (not args.archive or not args.ndk):
        parser.error("build requires --archive and --ndk")
    if args.mode == "run" and (not args.artifacts or not args.adb):
        parser.error("run requires --artifacts and --adb")
    return build(args) if args.mode == "build" else run_android(args)


if __name__ == "__main__":
    raise SystemExit(main())
