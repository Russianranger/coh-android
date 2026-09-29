#!/usr/bin/env python3
"""Package the exact hosted Atlas donor inside a separately identified device bundle."""
from __future__ import annotations

import argparse
import copy
import gzip
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/android/dbserver"))
sys.path.insert(0, str(ROOT / "tools/android/game"))
import host_game_smoke as game
import host_dbserver_smoke as host
import stack_probe_receipt

# Import by file identity: both the older DbServer builder and this module have
# the public name prepare_device_assets, and may coexist in a test process.
_spec = importlib.util.spec_from_file_location(
    "coh_dbserver_device_assets", ROOT / "tools/android/dbserver/prepare_device_assets.py")
common = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(common)
require, digest = host.require, host.digest
regular_directory, fresh_output = common.regular_directory, common.fresh_output
write_archive, extract_archive = common.write_archive, common.extract_archive

RUNTIME_RUN_ID = 36364550345
PACKAGE_RUN_ID = 36510836956
PACKAGE_COMMIT = "ac4c1f7978be444a893f65f5177641191861d42f"
PACKAGE_MANIFEST_SHA256 = "ebfdbbab3984627f7c39220f42a9c3e67b78ffe555aa742621a7a1450731fb2a"
SCHEMA_MANIFEST_SHA256 = "b89136892e69ceb39db640613d3f8a34abf2ef8e75e947f4034728b935938b92"
DATA_MANIFEST_SHA256 = "b367cc35d3f3826d9988ffa5dadb0a240ffc0967f0d248586e54d8ac545615f4"
DATA_MANIFEST_BYTES = 32184737
OBSERVER_MANIFEST_SHA256 = "7e8ea3b34917160222e56cec0012860eec2b1d684907723365222d369a399185"
BASE_MANIFEST = "accepted-runtime-manifest.json"
GUEST_SCRIPTS = ("game_device_diagnostic.py", "game_diagnostic.py", "game_evidence.py",
                 "game_hang_evidence.py", "dbserver_diagnostic.py")
EXTRA_FILES = {BASE_MANIFEST, *GUEST_SCRIPTS, "game-package.tar.gz", "dbserver-schema.tar.gz",
               "game-data-manifest.json.gz", "GameStackProbe.exe", "stack-probe-build.json"}
COMMIT = re.compile(r"[0-9a-f]{40}\Z")


def accepted_evidence():
    evidence = ROOT / "docs/android-evidence"
    accepted = game.read_json(evidence / f"accepted-game-listeners-hosted-{PACKAGE_RUN_ID}.json")
    require(accepted.get("status") == "accepted_hosted_game_listeners"
            and accepted.get("workflow_conclusion") == "success"
            and accepted.get("run_id") == PACKAGE_RUN_ID
            and accepted.get("repository_commit") == PACKAGE_COMMIT
            and accepted.get("android_execution_validated") is False
            and accepted.get("gameplay_validated") is False,
            "Accepted Atlas qualification differs")
    inputs_path = evidence / f"game-listeners-host-inputs-{PACKAGE_RUN_ID}.json"
    inputs = game.read_json(inputs_path)
    require(isinstance(accepted.get("inputs"), dict)
            and all(host.exact_contract(inputs.get(key), value) for key, value in accepted["inputs"].items()),
            "Accepted Atlas inputs differ")
    for key, expected in (("runtime_manifest_sha256", host.ACCEPTED_RUNTIME_MANIFEST),
                          ("game_package_sha256", PACKAGE_MANIFEST_SHA256),
                          ("schema_manifest_sha256", SCHEMA_MANIFEST_SHA256),
                          ("game_data_manifest_sha256", DATA_MANIFEST_SHA256),
                          ("repository_commit", PACKAGE_COMMIT),
                          ("runtime_commit", host.ACCEPTED_RUNTIME_COMMIT)):
        require(inputs.get(key) == expected, "Accepted Atlas input pin differs: " + key)
    for filename in (inputs_path.name, f"game-listeners-package-{PACKAGE_RUN_ID}.json"):
        path = evidence / filename
        record = accepted["preserved_files"][filename]
        require(path.stat().st_size == record["bytes"] and digest(path) == record["sha256"],
                "Preserved Atlas evidence differs: " + filename)
    require(digest(evidence / f"game-listeners-package-{PACKAGE_RUN_ID}.json") == PACKAGE_MANIFEST_SHA256,
            "Preserved composite manifest differs")
    return inputs


def bundle_contract():
    return {"format": 1, "package_run_id": PACKAGE_RUN_ID,
            "package_repository_commit": PACKAGE_COMMIT,
            "package_manifest_sha256": PACKAGE_MANIFEST_SHA256,
            "package_archive": "game-package.tar.gz",
            "schema_manifest_sha256": SCHEMA_MANIFEST_SHA256,
            "schema_acceptance_run_id": 36088012666,
            "schema_archive": "dbserver-schema.tar.gz",
            "data_manifest_archive": "game-data-manifest.json.gz",
            "data_manifest_sha256": DATA_MANIFEST_SHA256,
            "data_manifest_bytes": DATA_MANIFEST_BYTES,
            "data_file_count": game.DATA_FILE_COUNT, "data_total_bytes": game.DATA_TOTAL_BYTES,
            "guest_script": "game_device_diagnostic.py", "guest_scripts": list(GUEST_SCRIPTS),
            "observer_manifest_sha256": OBSERVER_MANIFEST_SHA256,
            "listener_policy": "device", "dbserver_profile": "loopback",
            "game_listener_profile": "loopback", "android_execution_validated": False,
            "gameplay_validated": False}


def base_contract(manifest):
    return {"run_id": RUNTIME_RUN_ID, "repository_commit": host.ACCEPTED_RUNTIME_COMMIT,
            "manifest_file": BASE_MANIFEST, "manifest_sha256": host.ACCEPTED_RUNTIME_MANIFEST,
            "manifest": manifest}


def verify_data_manifest(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size == DATA_MANIFEST_BYTES
            and digest(path) == DATA_MANIFEST_SHA256, "Accepted full game data manifest differs")
    value = game.read_json(path)
    require(value.get("scope") == "reviewed_game_data"
            and value.get("source_commit") == host.SOURCE_COMMIT
            and value.get("data_commit") == host.DATA_COMMIT
            and value.get("android_execution_validated") is False
            and value.get("gameplay_validated") is False,
            "Accepted full game data identity differs")
    files = value.get("files")
    total = game.inventory_bounds(files, maximum_files=game.MAX_DATA_FILES, maximum_bytes=game.MAX_DATA_BYTES)
    require(value.get("file_count") == len(files) == game.DATA_FILE_COUNT
            and value.get("total_bytes") == total == game.DATA_TOTAL_BYTES
            and value.get("asset_manifest_sha256") == game.ASSET_MANIFEST_SHA256
            and value.get("asset_archive_sha256") == game.ASSET_ARCHIVE_SHA256
            and all(name.startswith("data/") for name in files), "Accepted game data inventory differs")
    return value


def write_data_manifest(source, destination):
    verify_data_manifest(source)
    with destination.open("xb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as target:
        with source.open("rb") as stream:
            shutil.copyfileobj(stream, target)


def extract_data_manifest(source, destination):
    """Bound decompression before JSON parsing or writing an oversized file."""
    count = 0
    created = False
    try:
        with gzip.open(source, "rb") as stream, destination.open("xb") as target:
            created = True
            while block := stream.read(min(1024 * 1024, DATA_MANIFEST_BYTES - count + 1)):
                count += len(block)
                require(count <= DATA_MANIFEST_BYTES, "Game data manifest decompression exceeds bound")
                target.write(block)
        verify_data_manifest(destination)
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)
        raise


def verify_input_payloads(package, schema, data_manifest, stack_probe):
    require(digest(package / "game-package.json") == PACKAGE_MANIFEST_SHA256,
            "Device test requires the exact qualified Atlas package")
    require(digest(schema / "schema-manifest.json") == SCHEMA_MANIFEST_SHA256,
            "Device test requires the accepted generated schema")
    package_manifest = game.verify_package(package, dbserver_profile="loopback", game_listener_profile="loopback")
    require(package_manifest.get("repository_commit") == PACKAGE_COMMIT, "Accepted Atlas package commit differs")
    host.verify_schema(schema)
    verify_data_manifest(data_manifest)
    require(digest(stack_probe / "stack-probe-build.json") == OBSERVER_MANIFEST_SHA256,
            "Device test requires the accepted observer")
    stack_probe_receipt.verify(stack_probe, PACKAGE_COMMIT)


def verify_device_metadata(assets):
    assets = regular_directory(assets)
    accepted_evidence()
    manifest = game.read_json(assets / "runtime-manifest.json")
    base = game.read_json(assets / BASE_MANIFEST)
    require(digest(assets / BASE_MANIFEST) == host.ACCEPTED_RUNTIME_MANIFEST
            and base.get("repository_commit") == host.ACCEPTED_RUNTIME_COMMIT
            and len(base.get("files", {})) == 12, "Accepted base runtime differs")
    require(type(manifest.get("repository_commit")) is str and COMMIT.fullmatch(manifest["repository_commit"]),
            "Invalid candidate repository commit")
    require(host.exact_contract(manifest.get("accepted_base_runtime"), base_contract(base)),
            "Accepted base runtime metadata differs")
    require(host.exact_contract(manifest.get("atlas_device_bundle"), bundle_contract()),
            "Atlas device bundle contract differs")
    require(set(manifest) == set(base) | {"accepted_base_runtime", "atlas_device_bundle"},
            "Candidate runtime manifest fields differ")
    require(all(host.exact_contract(manifest.get(key), base[key])
                for key in set(base) - {"files", "repository_commit", "scope"}),
            "Accepted runtime contract was modified")
    require(set(manifest.get("files", {})) == set(base["files"]) | EXTRA_FILES
            and all(host.exact_contract(manifest["files"][name], record) for name, record in base["files"].items()),
            "Accepted runtime inventory was modified")
    host.verify_inventory(assets, manifest["files"], excluded=("runtime-manifest.json",))
    for name in GUEST_SCRIPTS:
        require(digest(assets / name) == digest(ROOT / "android/guest" / name),
                "Candidate guest script differs from the checkout: " + name)
    return manifest


def extract_device_inputs(assets, output):
    assets = regular_directory(assets)
    verify_device_metadata(assets)
    output = fresh_output(output, (assets,))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".atlas-unpack-", dir=output.parent) as temporary:
        staging = Path(temporary) / "inputs"
        staging.mkdir(mode=0o700)
        extract_archive(assets / "game-package.tar.gz", staging / "package")
        extract_archive(assets / "dbserver-schema.tar.gz", staging / "schema")
        extract_data_manifest(assets / "game-data-manifest.json.gz", staging / "game-data-manifest.json")
        verify_input_payloads(staging / "package", staging / "schema", staging / "game-data-manifest.json", assets)
        require(not output.exists(), "Output appeared during extraction")
        staging.rename(output)
    return {"package": output / "package", "schema": output / "schema",
            "data_manifest": output / "game-data-manifest.json"}


def verify_device_assets(assets):
    manifest = verify_device_metadata(assets)
    with tempfile.TemporaryDirectory(prefix="coh-atlas-verify-") as temporary:
        extract_device_inputs(assets, Path(temporary) / "inputs")
    return manifest


def prepare_device_assets(*, assets, package, schema, game_data_manifest, stack_probe,
                          output, repository_commit, receipt=None):
    require(type(repository_commit) is str and COMMIT.fullmatch(repository_commit),
            "Repository commit must be a full lowercase Git commit")
    assets, package, schema, stack_probe = map(regular_directory, (assets, package, schema, stack_probe))
    game_data_manifest = Path(game_data_manifest)
    require(game_data_manifest.is_file() and not game_data_manifest.is_symlink(), "Missing game data manifest")
    game_data_manifest = game_data_manifest.resolve()
    inputs = (assets, package, schema, stack_probe, game_data_manifest)
    output = fresh_output(output, inputs)
    if receipt is not None:
        receipt = fresh_output(receipt, (*inputs, output))
    accepted_evidence()
    base = host.verify_runtime_assets(assets)
    verify_input_payloads(package, schema, game_data_manifest, stack_probe)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".atlas-assets-", dir=output.parent) as temporary:
        staging = Path(temporary) / "runtime"
        staging.mkdir(mode=0o755)
        for name in base["files"]:
            shutil.copyfile(assets / name, staging / name)
        shutil.copyfile(assets / "runtime-manifest.json", staging / BASE_MANIFEST)
        for name in GUEST_SCRIPTS:
            shutil.copyfile(ROOT / "android/guest" / name, staging / name)
        for name in ("GameStackProbe.exe", "stack-probe-build.json"):
            shutil.copyfile(stack_probe / name, staging / name)
        write_archive(package, staging / "game-package.tar.gz")
        write_archive(schema, staging / "dbserver-schema.tar.gz")
        write_data_manifest(game_data_manifest, staging / "game-data-manifest.json.gz")
        manifest = copy.deepcopy(base)
        manifest["repository_commit"] = repository_commit
        manifest["accepted_base_runtime"] = base_contract(base)
        manifest["atlas_device_bundle"] = bundle_contract()
        manifest["scope"] = "Android Atlas candidate build inputs; physical Android and gameplay unvalidated"
        manifest["files"].update({name: {"bytes": (staging / name).stat().st_size,
                                        "sha256": digest(staging / name)} for name in sorted(EXTRA_FILES)})
        (staging / "runtime-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        extract_device_inputs(staging, Path(temporary) / "roundtrip")
        result = {"format": 1, "scope": "android_atlas_device_assets_preparation",
                  "repository_commit": repository_commit,
                  "runtime_manifest_sha256": digest(staging / "runtime-manifest.json"),
                  "accepted_base_runtime": {key: value for key, value in base_contract(base).items() if key != "manifest"},
                  "atlas_device_bundle": bundle_contract(),
                  "additional_files": {name: manifest["files"][name] for name in sorted(EXTRA_FILES)},
                  "base_file_bytes_preserved": True, "archive_roundtrip_verified": True,
                  "android_execution_validated": False, "gameplay_validated": False}
        require(not output.exists(), "Output appeared during preparation")
        staging.rename(output)
        if receipt is not None:
            created = False
            try:
                receipt.parent.mkdir(parents=True, exist_ok=True)
                with receipt.open("x") as stream:
                    created = True
                    stream.write(json.dumps(result, indent=2) + "\n")
            except BaseException:
                shutil.rmtree(output)
                if created:
                    receipt.unlink(missing_ok=True)
                raise
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("assets", "package", "schema", "game-data-manifest", "stack-probe", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--repository-commit", required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare_device_assets(**vars(args)), indent=2))


if __name__ == "__main__":
    main()
