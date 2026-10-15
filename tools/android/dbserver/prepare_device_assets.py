#!/usr/bin/env python3
"""Assemble a receipted Android DbServer candidate from exact accepted inputs."""
import argparse
import copy
import gzip
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile

import host_dbserver_smoke as host

ROOT = host.ROOT
RUNTIME_RUN_ID = 36364550345
PACKAGE_RUN_ID = 36460867428
PACKAGE_COMMIT = "eed2ce1f5388195f65a07853919761a93657aca6"
PACKAGE_MANIFEST_SHA256 = "95f62cc81b0743c13652e55aee01aed6871fc96d70a84b8dfd62fb8a0d9fe0d6"
SCHEMA_MANIFEST_SHA256 = "b89136892e69ceb39db640613d3f8a34abf2ef8e75e947f4034728b935938b92"
BASE_MANIFEST = "accepted-runtime-manifest.json"
EXTRA_FILES = {BASE_MANIFEST, "dbserver_diagnostic.py", "dbserver-package.tar.gz", "dbserver-schema.tar.gz"}
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
require = host.require
digest = host.digest


def accepted_evidence():
    """Cross-check the pins against the independently preserved qualification."""
    root = ROOT / "docs/android-evidence"
    accepted = host.read_manifest(root / f"accepted-dbserver-hosted-{PACKAGE_RUN_ID}.json")
    inputs_path = root / f"dbserver-host-inputs-{PACKAGE_RUN_ID}.json"
    inputs = host.read_manifest(inputs_path)
    require(accepted.get("status") == "accepted_hosted_dbserver_fixture_and_normal_schema"
            and accepted.get("run_id") == PACKAGE_RUN_ID
            and accepted.get("workflow_conclusion") == "success"
            and accepted.get("repository_commit") == PACKAGE_COMMIT
            and accepted.get("android_execution_validated") is False
            and accepted.get("android_listener_binding_validated") is False
            and accepted.get("gameplay_validated") is False,
            "Accepted hosted DbServer evidence differs")
    require(host.exact_contract(inputs, accepted.get("inputs")), "Preserved hosted inputs differ")
    record = accepted["preserved_files"][inputs_path.name]
    require(record["sha256"] == digest(inputs_path) and record["bytes"] == inputs_path.stat().st_size,
            "Preserved hosted inputs hash/size differs")
    for key, value in (("runtime_manifest_sha256", host.ACCEPTED_RUNTIME_MANIFEST),
                       ("runtime_commit", host.ACCEPTED_RUNTIME_COMMIT),
                       ("package_manifest_sha256", PACKAGE_MANIFEST_SHA256),
                       ("package_commit", PACKAGE_COMMIT),
                       ("schema_manifest_sha256", SCHEMA_MANIFEST_SHA256),
                       ("schema_acceptance_run_id", 36088012666)):
        require(inputs.get(key) == value, "Accepted input pin differs: " + key)
    return inputs


def bundle_contract():
    return {"format": 1, "package_run_id": PACKAGE_RUN_ID,
            "package_manifest_sha256": PACKAGE_MANIFEST_SHA256,
            "package_repository_commit": PACKAGE_COMMIT,
            "schema_manifest_sha256": SCHEMA_MANIFEST_SHA256,
            "schema_acceptance_run_id": 36088012666,
            "guest_script": "dbserver_diagnostic.py",
            "package_archive": "dbserver-package.tar.gz",
            "schema_archive": "dbserver-schema.tar.gz", "listener_policy": "device",
            "android_execution_validated": False, "gameplay_validated": False}


def base_contract(manifest):
    return {"run_id": RUNTIME_RUN_ID, "repository_commit": host.ACCEPTED_RUNTIME_COMMIT,
            "manifest_file": BASE_MANIFEST, "manifest_sha256": host.ACCEPTED_RUNTIME_MANIFEST,
            "manifest": manifest}


def regular_directory(path):
    path = Path(path)
    require(path.is_dir() and not path.is_symlink(), "Missing or symlinked input directory: " + str(path))
    return path.resolve()


def fresh_output(output, inputs):
    output = Path(output)
    require(not output.exists() and not output.is_symlink(), "Use a fresh output path: " + str(output))
    output = output.resolve()
    require(all(not output.is_relative_to(path) and not path.is_relative_to(output) for path in inputs),
            "Output must not overlap an input tree")
    return output


def safe_name(name):
    relative = PurePosixPath(name)
    require(type(name) is str and bool(relative.parts) and not relative.is_absolute()
            and relative.as_posix() == name and ".." not in relative.parts
            and "\\" not in name and "\x00" not in name, "Unsafe archive path")
    return relative


def write_archive(source, output):
    """Archive only regular files, with stable byte ordering and metadata."""
    paths = sorted(source.rglob("*"), key=lambda path: path.relative_to(source).as_posix())
    for path in paths:
        require(not path.is_symlink() and (path.is_file() or path.is_dir()),
                "Archive input contains a symlink or special file")
    with output.open("xb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for path in paths:
                if path.is_dir():
                    continue
                name = path.relative_to(source).as_posix()
                safe_name(name)
                member = tarfile.TarInfo(name)
                member.size = path.stat().st_size
                member.mode = 0o644
                member.uid = member.gid = member.mtime = 0
                member.uname = member.gname = ""
                with path.open("rb") as stream:
                    archive.addfile(member, stream)


def extract_archive(archive_path, output):
    """Extract our bounded, regular-file-only archive format without tar path writes."""
    output.mkdir(mode=0o700)
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        require(0 < len(members) <= 4096 and sum(member.size for member in members) <= 256 * 1024 * 1024,
                "Archive exceeds the device input bound")
        names = [member.name for member in members]
        require(names == sorted(set(names)), "Archive members are duplicate or unordered")
        for member in members:
            safe_name(member.name)
            require(member.isfile() and member.size >= 0 and member.mode == 0o644
                    and member.uid == member.gid == member.mtime == 0
                    and member.uname == member.gname == "" and not member.linkname
                    and not member.pax_headers, "Archive member metadata is not canonical")
            path = output / member.name
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            with archive.extractfile(member) as source, path.open("xb") as target:
                shutil.copyfileobj(source, target)
            path.chmod(0o644)


def verify_input_payloads(package, schema):
    require(digest(package / "package-manifest.json") == PACKAGE_MANIFEST_SHA256,
            "Device diagnostic requires the qualified loopback package")
    require(digest(schema / "schema-manifest.json") == SCHEMA_MANIFEST_SHA256,
            "Device diagnostic requires the accepted generated schema")
    package_manifest = host.verify_package(package)
    schema_manifest = host.verify_schema(schema)
    require(package_manifest.get("repository_commit") == PACKAGE_COMMIT,
            "Qualified package repository commit differs")
    return package_manifest, schema_manifest


def verify_device_metadata(assets):
    """Verify the inventory and preserve the accepted base as an independent anchor."""
    assets = regular_directory(assets)
    accepted_evidence()
    manifest = host.read_manifest(assets / "runtime-manifest.json")
    base = host.read_manifest(assets / BASE_MANIFEST)
    require(digest(assets / BASE_MANIFEST) == host.ACCEPTED_RUNTIME_MANIFEST
            and base.get("repository_commit") == host.ACCEPTED_RUNTIME_COMMIT
            and len(base.get("files", {})) == 12, "Accepted base runtime differs")
    require(isinstance(manifest.get("repository_commit"), str)
            and COMMIT.fullmatch(manifest["repository_commit"]), "Invalid candidate repository commit")
    require(host.exact_contract(manifest.get("accepted_base_runtime"), base_contract(base)),
            "Accepted base runtime metadata differs")
    require(host.exact_contract(manifest.get("dbserver_device_bundle"), bundle_contract()),
            "Device bundle contract differs")
    require(set(manifest) == set(base) | {"accepted_base_runtime", "dbserver_device_bundle"},
            "Candidate runtime manifest fields differ")
    preserved_keys = set(base) - {"files", "repository_commit", "scope"}
    require(all(host.exact_contract(manifest.get(key), base[key]) for key in preserved_keys),
            "Accepted runtime contract was modified")
    require(set(manifest.get("files", {})) == set(base["files"]) | EXTRA_FILES
            and all(host.exact_contract(manifest["files"][name], record) for name, record in base["files"].items()),
            "Accepted runtime inventory was modified")
    host.verify_inventory(assets, manifest["files"], excluded=("runtime-manifest.json",))
    require(digest(assets / "dbserver_diagnostic.py") == digest(ROOT / "android/guest/dbserver_diagnostic.py"),
            "Candidate guest script differs from the current checkout")
    return manifest


def verify_device_assets(assets):
    """Verify metadata and archived inventories before signing or hosted execution."""
    assets = regular_directory(assets)
    manifest = verify_device_metadata(assets)
    with tempfile.TemporaryDirectory(prefix="coh-device-verify-") as temporary:
        root = Path(temporary)
        extract_archive(assets / "dbserver-package.tar.gz", root / "package")
        extract_archive(assets / "dbserver-schema.tar.gz", root / "schema")
        verify_input_payloads(root / "package", root / "schema")
    return manifest


def extract_device_inputs(assets, output):
    """Materialize the exact packaged inputs for an independent hosted exercise."""
    assets = regular_directory(assets)
    verify_device_metadata(assets)
    output = fresh_output(output, (assets,))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".device-extract-", dir=output.parent) as temporary:
        staging = Path(temporary) / "inputs"
        staging.mkdir(mode=0o700)
        extract_archive(assets / "dbserver-package.tar.gz", staging / "package")
        extract_archive(assets / "dbserver-schema.tar.gz", staging / "schema")
        verify_input_payloads(staging / "package", staging / "schema")
        require(not output.exists(), "Output appeared during extraction")
        staging.rename(output)
    return {"package": output / "package", "schema": output / "schema"}


def prepare_device_assets(*, assets, package, schema, output, repository_commit, receipt=None):
    require(type(repository_commit) is str and COMMIT.fullmatch(repository_commit),
            "Repository commit must be a full lowercase Git commit")
    assets, package, schema = (regular_directory(path) for path in (assets, package, schema))
    inputs = (assets, package, schema)
    output = fresh_output(output, inputs)
    if receipt is not None:
        receipt = fresh_output(receipt, (*inputs, output))
    accepted_evidence()
    base = host.verify_runtime_assets(assets)
    verify_input_payloads(package, schema)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".device-assets-", dir=output.parent) as temporary:
        staging = Path(temporary) / "runtime"
        staging.mkdir(mode=0o755)
        for name in base["files"]:
            destination = staging / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(assets / name, destination)
        shutil.copyfile(assets / "runtime-manifest.json", staging / BASE_MANIFEST)
        shutil.copyfile(ROOT / "android/guest/dbserver_diagnostic.py", staging / "dbserver_diagnostic.py")
        write_archive(package, staging / "dbserver-package.tar.gz")
        write_archive(schema, staging / "dbserver-schema.tar.gz")
        manifest = copy.deepcopy(base)
        manifest["repository_commit"] = repository_commit
        manifest["accepted_base_runtime"] = base_contract(base)
        manifest["dbserver_device_bundle"] = bundle_contract()
        manifest["scope"] = "Android DbServer diagnostic candidate build inputs; Android execution and gameplay unvalidated"
        manifest["files"].update({name: {"bytes": (staging / name).stat().st_size,
                                        "sha256": digest(staging / name)} for name in sorted(EXTRA_FILES)})
        (staging / "runtime-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        # Round-trip the exact archives before publishing the candidate directory.
        extracted = Path(temporary) / "roundtrip"
        extract_device_inputs(staging, extracted)
        result = {"format": 1, "scope": "android_dbserver_device_assets_preparation",
                  "repository_commit": repository_commit,
                  "runtime_manifest_sha256": digest(staging / "runtime-manifest.json"),
                  "accepted_base_runtime": {key: value for key, value in base_contract(base).items() if key != "manifest"},
                  "dbserver_device_bundle": bundle_contract(),
                  "additional_files": {name: manifest["files"][name] for name in sorted(EXTRA_FILES)},
                  "base_file_bytes_preserved": True, "archive_roundtrip_verified": True,
                  "android_execution_validated": False, "gameplay_validated": False}
        require(not output.exists(), "Output appeared during preparation")
        staging.rename(output)
        if receipt is not None:
            receipt_created = False
            try:
                receipt.parent.mkdir(parents=True, exist_ok=True)
                with receipt.open("x") as stream:
                    receipt_created = True
                    stream.write(json.dumps(result, indent=2) + "\n")
            except Exception:
                # Do not leave a published candidate when receipt publication failed.
                shutil.rmtree(output)
                if receipt_created:
                    receipt.unlink(missing_ok=True)
                raise
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "out/android/assets/runtime")
    parser.add_argument("--repository-commit", required=True)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--extract-output", type=Path)
    args = parser.parse_args()
    result = prepare_device_assets(assets=args.assets, package=args.package, schema=args.schema,
                                   output=args.output, repository_commit=args.repository_commit, receipt=args.receipt)
    if args.extract_output:
        extract_device_inputs(args.output, args.extract_output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
