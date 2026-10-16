#!/usr/bin/env python3
"""Validate the retained authentic catalog with standalone native executables."""
from pathlib import Path
import argparse
import importlib.util
import re
import sys
import zipfile

from common import (ABIS, CLAIMS, child, digest, elf_identity, execute, git_state,
                    json_equal, read, reject_claims, write)

HERE = Path(__file__).resolve().parent
ENGINE = "native-android/engine/"
MANIFEST = ENGINE + "scenecatalog-server/evidence/capture-38948147691/external-capture.json"
WORKFLOW = ".github/workflows/native-catalog-capture-validation.yml"
SOURCES = tuple(ENGINE + name for name in (
    "scenecatalog/validate_file.c", "scenecatalog/coh_scenecatalog.c",
    "scenegraph/coh_scenegraph.c", "replication/coh_replication.c", "replication/coh_groups.c"))
SCHEMA = "coh-authentic-catalog-android-build-v1"


def inventory(repo):
    names = {MANIFEST, WORKFLOW, ENGINE + "coh_contracts.h",
             "native-android/tools/protocol_fixture/prepare.py",
             ENGINE + "scenegraph/coh_scenegraph.h", *SOURCES,
             str(HERE.relative_to(repo) / "capture_android.py"),
             str(HERE.relative_to(repo) / "common.py")}
    for directory in ("scenecatalog", "replication"):
        for path in (repo / ENGINE / directory).rglob("*"):
            if "evidence" not in path.parts and path.suffix in (".c", ".h", ".inc", ".py"):
                names.add(path.relative_to(repo).as_posix())
    pin = ENGINE + "replication/groups-source-pins.json"
    names.add(pin)
    names.update("upstream/ouroboros/" + name for name in read(repo / pin)["sha256_lf"])
    names.update(path.relative_to(repo).as_posix() for path in (repo / "native-android/include").rglob("*.h"))
    return {name: digest(child(repo, name)) for name in sorted(names)}


def catalog_module(repo):
    path = repo / ENGINE / "scenecatalog"
    sys.path.insert(0, str(path))
    spec = importlib.util.spec_from_file_location("capture_check_file", path / "check_file.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extract_capture(archive, out, manifest):
    expected = manifest["artifact"]
    if archive.stat().st_size != expected["bytes"] or digest(archive) != expected["sha256"]:
        raise ValueError("Retained artifact ZIP identity differs")
    wanted = {manifest["catalog"]["path"]: manifest["catalog"]["bytes"],
              "capture/capture-receipt.json": 32 * 1024}
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)) or len(names) > 512:
            raise ValueError("Duplicate or excessive artifact members")
        for name, limit in wanted.items():
            info = bundle.getinfo(name)
            if info.file_size > limit or info.is_dir() or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Capture member is not bounded regular data")
            path = out / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info) as source, path.open("xb") as target:
                data = source.read(limit + 1)
                if len(data) != info.file_size:
                    raise ValueError("Capture member size differs")
                target.write(data)


def validate(repo, out, proof):
    """Validate exact capture, host results, source closure and both ABI files."""
    reject_claims(proof, required=True)
    if (proof.get("schema") != SCHEMA or proof.get("passed") is not True
            or proof.get("android_executed") is not False
            or proof.get("source_worktree_dirty") is not False
            or not re.fullmatch(r"[a-f0-9]{40}", proof.get("source_revision", ""))
            or set(proof.get("abis", {})) != set(ABIS)):
        raise ValueError("Complete clean build receipt required")
    sources = inventory(repo)
    if not json_equal(sources, proof.get("source_sha256")):
        raise ValueError("Build source closure differs from current checkout")
    if git_state(repo)["source_revision"] != proof["source_revision"]:
        raise ValueError("Build revision differs from runner checkout")
    capture, manifest = catalog_module(repo).admit_capture(out / "input")
    if not json_equal(manifest, proof.get("capture_provenance")):
        raise ValueError("Capture provenance differs")
    host_path = child(out, "host.json")
    if digest(host_path) != proof.get("host_receipt_sha256"):
        raise ValueError("Host receipt identity differs")
    host = read(host_path)
    if (host.get("passed") is not True or host.get("authentic_capture_validated") is not True
            or not json_equal(host.get("authentic_capture_provenance"), manifest)
            or any(sources.get(name) != sha for name, sha in host.get("source_sha256", {}).items())
            or not set(SOURCES).issubset(host.get("source_sha256", {}))):
        raise ValueError("Source-bound authentic host qualification required")
    expected = proof.get("expected")
    if not isinstance(expected, dict):
        raise ValueError("Missing native expected result")
    for key, value in manifest["observations"].items():
        if type(expected.get(key)) is not int or expected[key] != value:
            raise ValueError("Authentic catalog counts/checksums differ")
    if (expected.get("native_decode_completed") is not True or not json_equal(expected.get("status"), 0)
            or expected.get("validation_mode") != "stream"
            or expected.get("catalog_materialized") is not False
            or expected.get("graph_published") is not False
            or expected.get("renderer_authorized") is not False
            or expected.get("failed_record_peak_unknown") is not False
            or expected.get("records_validated") != manifest["observations"]["definitions"]
            or expected.get("input_bytes") != manifest["catalog"]["bytes"]
            or expected.get("generation") != manifest["catalog"]["generation"]
            or not json_equal(expected.get("owned_bytes"), 0)
            or not json_equal(expected.get("stage"), 6)
            or expected.get("offset") != manifest["catalog"]["bytes"]
            or not 0 < expected.get("peak_working_bytes", 0) <= 32 * 1024**2
            or not 0 < expected.get("peak_aggregate_bytes", 0) <= 96 * 1024**2
            or expected.get("working_upper_bound") != 32 * 1024**2
            or expected.get("aggregate_upper_bound") != 32 * 1024**2):
        raise ValueError("Complete bounded stream validation required")
    for mode in ("release", "asan", "ubsan"):
        result = host.get("checks", {}).get(mode, {})
        if (not json_equal(result.get("authentic_capture_stream"), expected)
                or result.get("malformed_rejections") != 24
                or result.get("unchanged_materializer_refusal", {}).get("status") != 4):
            raise ValueError("Sanitized host result or refusal control differs")
    for abi, item in proof["abis"].items():
        binary = child(out, item["path"])
        if binary.stat().st_size != item["bytes"] or digest(binary) != item["sha256"]:
            raise ValueError("Android executable bytes differ")
        elf_identity(binary, abi)
    return capture


def build(args):
    repo, out = args.source_root.resolve(), args.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError("Build output must be empty")
    state = git_state(repo)
    if state["source_git_status_porcelain"]:
        raise ValueError("Clean committed build source required")
    proof = dict(schema=SCHEMA, passed=False, android_executed=False,
                 source_revision=state["source_revision"], source_worktree_dirty=False,
                 source_sha256=inventory(repo), abis={}, **{key: False for key in CLAIMS})
    proof["scope"] = "Standalone validation of retained authentic saved catalog; no live GROUPS, actors, renderer, APK or server execution"
    try:
        manifest = read(repo / MANIFEST)
        extract_capture(args.archive.resolve(), out / "input", manifest)
        execute([sys.executable, repo / ENGINE / "scenecatalog/check_file.py",
                 "--source-root", repo, "--capture-directory", out / "input",
                 "--output", out / "host.json", "--sanitize"], out / "logs/host.log")
        host = read(out / "host.json")
        proof.update(host_receipt_sha256=digest(out / "host.json"), capture_provenance=manifest,
                     expected=host["checks"]["release"]["authentic_capture_stream"])
        ndk = args.ndk.resolve()
        properties = (ndk / "source.properties").read_text()
        if "Pkg.Revision = 28.2.13676358" not in properties:
            raise ValueError("Pinned Android NDK r28c required")
        proof["ndk_source_properties"] = properties
        for abi, triple in (("arm64-v8a", "aarch64-linux-android26"), ("x86_64", "x86_64-linux-android26")):
            binary = out / abi / "catalog-validator"
            binary.parent.mkdir(parents=True)
            cc = ndk / "toolchains/llvm/prebuilt/linux-x86_64/bin" / (triple + "-clang")
            command = [cc, "-std=c99", "-Wall", "-Wextra", "-Werror", "-pedantic", "-O2",
                       *(repo / path for path in SOURCES), "-lm", "-o", binary]
            execute(command, out / "logs" / (abi + ".log"))
            proof["abis"][abi] = dict(path=binary.relative_to(out).as_posix(), bytes=binary.stat().st_size,
                                      sha256=digest(binary), command=list(map(str, command)))
        proof["passed"] = True
        validate(repo, out, proof)
        if git_state(repo) != state:
            raise ValueError("Source state changed during build")
    except Exception as error:
        proof.update(passed=False, error=str(error))
    write(out / "build.json", proof)
    return 0 if proof["passed"] else 1


def run_android(args):
    repo, out = args.source_root.resolve(), args.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError("Execution output must be empty")
    artifacts = args.artifacts.resolve()
    proof = dict(schema="coh-authentic-catalog-android-execution-v1", passed=False,
                 execution_attempted=False, android_executed=False, emulator_qualified=False,
                 **{key: False for key in CLAIMS})
    remote, number = None, 0
    adb = [args.adb.resolve(), "-s", args.serial]

    def run(command, timeout=60):
        nonlocal number
        number += 1
        return execute([*adb, *command], out / "logs" / (f"{number:03d}.log"), timeout=timeout).strip()

    try:
        manifest = read(child(artifacts, "build.json"))
        capture = validate(repo, artifacts, manifest)
        state = git_state(repo)
        if state["source_git_status_porcelain"]:
            raise ValueError("Clean committed execution source required")
        proof.update(source_revision=manifest["source_revision"], source_sha256=manifest["source_sha256"],
                     build_receipt_sha256=digest(artifacts / "build.json"),
                     capture_provenance=manifest["capture_provenance"], abi="x86_64")
        run(["wait-for-device"])
        prop = lambda name: run(["shell", "getprop", name])
        if (prop("ro.kernel.qemu") != "1" or prop("ro.build.version.sdk") != "33"
                or "x86_64" not in prop("ro.product.cpu.abilist").split(",")):
            raise ValueError("Android 13 x86_64 emulator required")
        proof["android_build_fingerprint"] = prop("ro.build.fingerprint")
        remote = run(["shell", "mktemp", "-d", "/data/local/tmp/coh-captured-catalog.XXXXXX"])
        if not re.fullmatch(r"/data/local/tmp/coh-captured-catalog\.[A-Za-z0-9]+", remote):
            remote = None
            raise ValueError("Unexpected temporary directory")
        item = manifest["abis"]["x86_64"]
        for path, name, sha in ((child(artifacts, item["path"]), "validator", item["sha256"]),
                                (capture, "catalog.cohcat", manifest["capture_provenance"]["catalog"]["sha256"])):
            run(["push", path, remote + "/" + name])
            if run(["shell", "sha256sum", remote + "/" + name]).split()[0] != sha:
                raise ValueError("Transferred input/executable identity differs")
        run(["shell", "chmod", "700", remote + "/validator"])
        from common import loads
        proof["execution_attempted"] = True
        write(out / "receipt.json", proof)
        result = loads(run(["shell", remote + "/validator", remote + "/catalog.cohcat",
                            str(manifest["capture_provenance"]["catalog"]["generation"]), "--stream"], timeout=180))
        proof.update(android_executed=True, result=result, binary_sha256=item["sha256"])
        if not json_equal(result, manifest["expected"]):
            raise ValueError("Android result differs from all three host modes")
        validate(repo, artifacts, manifest)
        if git_state(repo) != state:
            raise ValueError("Source state changed during execution")
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
