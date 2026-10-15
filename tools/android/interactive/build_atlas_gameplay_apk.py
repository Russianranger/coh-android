#!/usr/bin/env python3
"""Build initial Atlas gameplay around the qualified 0.10.0 backend.

Two Android input/UI sources change, and 27 missing material textures extend
the pinned world inventory. Only immutable world-pin constants and their
verification metadata change in guest payloads; all other guest, native,
client, server, avatar and import bytes stay identical to the donor.
A completed ARM64 reopening qualification and reviewed world frames are
required before building or publishing the next device candidate.
"""
from __future__ import annotations

import argparse
import ast
import copy
import importlib.util
import json
import os
import re
import shutil
import stat
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPOSITORY = "Russianranger/coh-android"
REPOSITORY_ID = 1368730125
BRANCH = "codex/character-persistence-continuation"
DONOR_RUN_ID = 36920583713
DONOR_COMMIT = "204615c6c4a809d6b814c7174b81448cffea3f7a"
DONOR_WORKFLOW = ".github/workflows/android-client-interactive.yml"
QUALIFICATION_WORKFLOW = ".github/workflows/android-character-reopen-qualified-apk.yml"
DONOR_APK_NAME = "COH-Character-Reopen-0.10.0.apk"
DONOR_BUILD_NAME = "interactive-apk-build-report.json"
DONOR_ARTIFACT_NAME = "coh-client-interaction-apk"
HOST_REPORT_NAME = "client-evidence/host-client-report.json"
DRIVER_NAME = "client-evidence/qualification-driver.json"
EVIDENCE_NAME = "coh-client-interaction-arm64-evidence"
SIGNER = "92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282"
VERSION_NAME = "0.11.0"
VERSION_CODE = 6
APK_NAME = "COH-Atlas-Gameplay-0.11.0.apk"
REPORT_NAME = "atlas-gameplay-apk-build-report.json"
NOTES_NAME = "COH-Atlas-Gameplay-0.11.0-testing.txt"
RELEASE_TAG = "coh-atlas-gameplay-v0.11.0"
VISUAL_REVIEW = ROOT / "docs/android-evidence/atlas-world-reopen-reviewed.json"
NOTES = ROOT / "docs" / NOTES_NAME
INPUT_SOURCES = frozenset("android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/" + name
                          for name in ("ClientActivity.java", "ClientInput.java"))
WORLD_PIN_NAMES = frozenset(("MANIFEST_SHA256", "ARCHIVE_SHA256", "ARCHIVE_BYTES", "PAYLOAD_BYTES", "FILE_COUNT", "FILES_SHA256"))
WORLD_MEMBERS = frozenset("assets/runtime/" + name for name in (
    "atlas_world_assets.py", "atlas-world-supplement.zip", "atlas-world-supplement-manifest.json",
    "client-manifest.json", "runtime-manifest.json"))


def require(value, message):
    if not value:
        raise ValueError(message)


def builder(*, gameplay=False):
    # An isolated module instance leaves the original builder and its 0.10.0
    # constants unchanged, even when both builders are used in one process.
    spec = importlib.util.spec_from_file_location("coh_gameplay_base_builder", Path(__file__).with_name("build_apk.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if gameplay:
        module.VERSION_NAME, module.VERSION_CODE, module.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return module


def read_json(path, *, limit=8 * 1024 * 1024):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= limit,
            "Missing, linked or oversized metadata: " + path.name)
    return json.loads(path.read_text())


def repository_identity(record):
    return record.get("id") == REPOSITORY_ID and record.get("full_name") == REPOSITORY


def reviewed_donor_pins(review):
    base = builder()
    apk, build, artifact = (review.get(name) for name in ("donor_apk", "donor_build_report", "apk_artifact"))
    for pin, name in ((apk, DONOR_APK_NAME), (build, DONOR_BUILD_NAME), (artifact, DONOR_ARTIFACT_NAME)):
        base.checked_pin(pin)
        require(pin.get("name") == name and pin["bytes"] > 0 and pin["sha256"] != "0" * 64,
                "Reviewed exact donor file/artifact pins are missing")
    require(type(artifact.get("id")) is int and artifact["id"] > 0, "Reviewed APK artifact identity is missing")
    return apk, build, artifact


def validate_run(metadata, *, run_id, commit, workflow, jobs_required, successful):
    run, jobs = metadata.get("run", {}), metadata.get("jobs", {})
    require(run.get("id") == run_id and run.get("run_attempt") == 1 and run.get("status") == "completed"
            and (run.get("conclusion") == "success" if successful else run.get("conclusion") in ("success", "failure"))
            and run.get("head_sha") == commit and run.get("head_branch") == BRANCH
            and run.get("event") in ("push", "workflow_dispatch") and run.get("path") == workflow
            and repository_identity(run.get("repository", {})) and repository_identity(run.get("head_repository", {})),
            "Source run identity, completion or success requirement differs")
    require(jobs.get("total_count") == len(jobs.get("jobs", [])), "Incomplete source jobs pagination")
    for name in jobs_required:
        found = [job for job in jobs.get("jobs", []) if job.get("name") == name]
        require(len(found) == 1 and found[0].get("run_id") == run_id
                and found[0].get("status") == "completed" and found[0].get("conclusion") == "success",
                "Required source job did not pass: " + name)
        if name == "runtime":
            require("ubuntu-24.04-arm" in found[0].get("labels", []), "Qualification runtime was not ARM64")
    return run


def validate_qualification(metadata, review):
    apk_pin, _, apk_artifact = reviewed_donor_pins(review)
    qualification_id, qualification_commit = review.get("qualification_run_id"), review.get("qualification_head_sha")
    require(type(qualification_id) is int and qualification_id > 0 and qualification_id != DONOR_RUN_ID,
            "A separate completed exact-APK runtime qualification is required")
    builder().source_commit(qualification_commit)
    donor, qualification = metadata.get("donor", {}), metadata.get("qualification", {})
    # The donor build jobs passed, but its old graphical driver failed during
    # reopening. Only the separate corrected-driver success qualifies runtime.
    validate_run(donor, run_id=DONOR_RUN_ID, commit=DONOR_COMMIT, workflow=DONOR_WORKFLOW,
                 jobs_required=("tooling", "client-caches", "apk"), successful=False)
    run = validate_run(qualification, run_id=qualification_id, commit=qualification_commit, workflow=QUALIFICATION_WORKFLOW,
                       jobs_required=("tooling", "runtime"), successful=True)
    require(review.get("format") == 1 and review.get("status") == "passed"
            and review.get("apk_sha256") == apk_pin["sha256"]
            and review.get("atlas_world_visible") is True and review.get("avatar_visible") is True,
            "A reviewed visible Atlas world and avatar are required")
    evidence = review.get("qualification_artifact", {})
    pins = builder()
    pins.checked_pin(evidence)
    require(type(evidence.get("id")) is int and evidence["id"] > 0,
            "Reviewed qualification artifact identity is missing")
    for name, expected, source_run, source_commit, source_metadata in (
            (DONOR_ARTIFACT_NAME, apk_artifact, DONOR_RUN_ID, DONOR_COMMIT, donor),
            (EVIDENCE_NAME, evidence, qualification_id, qualification_commit, qualification)):
        actual = source_metadata.get("artifacts", {}).get(name, {})
        source = actual.get("workflow_run", {})
        require(actual.get("id") == expected["id"] and actual.get("name") == name
                and actual.get("expired") is False and actual.get("size_in_bytes") == expected["bytes"]
                and actual.get("digest") == "sha256:" + expected["sha256"]
                and source.get("id") == source_run and source.get("head_sha") == source_commit
                and source.get("repository_id") == REPOSITORY_ID
                and source.get("head_repository_id") == REPOSITORY_ID,
                "Exact qualified donor artifact identity or bytes differ: " + name)
    host_pin = review.get("host_report", {})
    pins.checked_pin(host_pin)
    require(host_pin.get("name") == HOST_REPORT_NAME, "Unexpected reviewed host report member")
    driver_pin = review.get("qualification_driver", {})
    pins.checked_pin(driver_pin)
    require(driver_pin.get("name") == DRIVER_NAME, "Unexpected reviewed qualification driver member")
    frames = review.get("visual_evidence_frames", [])
    require(isinstance(frames, list) and 0 < len(frames) <= 20, "Reviewed world screenshot pins are missing")
    names = set()
    for frame in frames:
        name = frame.get("name", "")
        require(isinstance(name, str) and name.startswith("client-evidence/") and name.endswith(".png")
                and Path(name).as_posix() == name and ".." not in Path(name).parts
                and "\\" not in name and name not in names, "Unsafe or duplicated reviewed screenshot path")
        pins.checked_pin(frame)
        names.add(name)
    return run


def validate_driver(driver, review):
    apk, build, artifact = reviewed_donor_pins(review)
    require(driver.get("format") == 1 and driver.get("scope") == "exact_donor_apk_current_host_harness_native_arm64"
            and driver.get("host_harness_repository_commit") == review["qualification_head_sha"]
            and isinstance(driver.get("host_harness_repository_tree"), str)
            and re.fullmatch("[0-9a-f]{40}", driver["host_harness_repository_tree"])
            and driver.get("workflow_path") == QUALIFICATION_WORKFLOW
            and driver.get("workflow_run_id") == review["qualification_run_id"] and driver.get("workflow_run_attempt") == 1
            and driver.get("repository") == REPOSITORY and driver.get("ref") == "refs/heads/" + BRANCH
            and driver.get("apk_rebuilt") is False and driver.get("client_or_server_recompiled") is False
            and driver.get("fresh_postgresql_profile") is True and driver.get("synthetic_character_rows") is False
            and driver.get("qualification_scope") == "two_real_graphical_sessions_with_owned_stack_restart_and_normal_logout"
            and driver.get("apk_donor") == {"run_id": DONOR_RUN_ID, "repository_commit": DONOR_COMMIT,
                "apk": apk, "build_report": build, "artifact": artifact},
            "Corrected host driver provenance differs from the qualified unchanged APK")
    files = driver.get("source_manifest", {}).get("files", {})
    import hashlib
    require(driver.get("source_manifest", {}).get("format") == 1 and
            driver["source_manifest"].get("files_sha256") == hashlib.sha256(
                json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "Qualified host source manifest digest differs")
    required = {QUALIFICATION_WORKFLOW, "tools/android/interactive/character_reopen_host_smoke.py",
                "tools/android/interactive/character_host_smoke.py", "tools/android/interactive/host_smoke.py",
                "tools/android/interactive/login_host_smoke.py"}
    require(isinstance(files, dict) and required <= set(files), "Qualified host harness source manifest is incomplete")
    for name in required:
        builder().checked_file(ROOT / name, files[name])
    return {name: files[name] for name in sorted(required)}


def validate_donor_receipts(build, host, review):
    apk_pin, _, _ = reviewed_donor_pins(review)
    require(build.get("format") == 1 and build.get("apk") == DONOR_APK_NAME
            and build.get("repository_commit") == DONOR_COMMIT
            and {key: build.get(key) for key in ("bytes", "sha256")} == builder().checked_pin(apk_pin)
            and build.get("application_id") == builder().APP_ID and build.get("version_name") == "0.10.0"
            and build.get("version_code") == 5 and build.get("abi") == "arm64-v8a"
            and all(build.get(key) is True for key in ("signature_verified", "payload_bytes_verified", "package_badging_verified"))
            and build.get("signing_key_created") is False
            and build.get("signer_certificate_sha256") == SIGNER
            and build.get("expected_signer_certificate_sha256") == SIGNER,
            "Exact retained-signer donor build receipt differs")
    require(host.get("format") == 1 and host.get("status") == "passed" and host.get("failure") is None
            and host.get("scope") == "exact_apk_graphical_character_reopen_native_arm64"
            and host.get("repository_commit") == DONOR_COMMIT
            and host.get("apk_sha256") == apk_pin["sha256"]
            and host.get("runtime_manifest_sha256") == build.get("runtime_manifest_sha256"),
            "Exact APK ARM64 reopening receipt differs")
    sessions = host.get("sessions", [])
    require(len(sessions) == 2 and all(session.get("status") == "passed" and session.get("failure") is None
                                     for session in sessions), "Both donor character sessions must have passed")
    continuity = host.get("persistent_reopen_continuity", {})
    require(all(continuity.get(key) is True for key in (
                "same_persistent_profile", "fully_stopped_between_sessions", "existing_powers_and_costume_preserved"))
            and continuity.get("synthetic_character_rows") is False
            and continuity.get("new_creation_requested_during_reopen") is False,
            "Qualified persistent character reopening continuity is incomplete")


def verify_backend_sources(report):
    base = builder()
    expected_sources = report.get("java_sources", {})
    require(isinstance(expected_sources, dict) and INPUT_SOURCES <= set(expected_sources),
            "Donor Java source closure is missing")
    current = {path.relative_to(ROOT).as_posix() for path in base.java_sources(ROOT / "android/interactive/src/main", ROOT / "out/no-generated-java")}
    require(current == set(expected_sources), "Java source inventory changed outside the two input/UI files")
    unchanged = {}
    for name in sorted(current - INPUT_SOURCES):
        unchanged[name] = base.checked_file(ROOT / name, expected_sources[name])
    native_sources = report.get("native_launcher_source", {})
    require(set(native_sources) == {"android/native/client-launcher.c"}, "Missing donor native launcher source")
    unchanged.update({name: base.checked_file(ROOT / name, pin) for name, pin in native_sources.items()})
    return unchanged


def world_helper_pins(raw):
    tree = ast.parse(raw)
    pins = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        names = [node.id for target in statement.targets for node in ast.walk(target) if isinstance(node, ast.Name)]
        if not WORLD_PIN_NAMES.intersection(names):
            continue
        require(len(statement.targets) == 1 and set(names) <= WORLD_PIN_NAMES,
                "World helper changed a non-pin assignment")
        value = ast.literal_eval(statement.value)
        values = value if isinstance(statement.targets[0], (ast.Tuple, ast.List)) else [value]
        require(isinstance(values, (tuple, list)) and len(values) == len(names), "Malformed world immutable pin assignment")
        for name, item in zip(names, values):
            require(name not in pins and (type(item) is int and item > 0 if name in ("ARCHIVE_BYTES", "PAYLOAD_BYTES", "FILE_COUNT")
                    else isinstance(item, str) and re.fullmatch("[0-9a-f]{64}", item)), "Invalid or duplicated world helper pin")
            pins[name] = item
        statement.value = ast.Constant(value="__immutable_world_pin__")
    require(set(pins) == WORLD_PIN_NAMES, "World helper immutable pin inventory differs")
    return pins, ast.dump(tree, include_attributes=False)


def validate_world_helper(donor_source, current_source):
    old, normalized_old = world_helper_pins(donor_source)
    new, normalized_new = world_helper_pins(current_source)
    require(normalized_old == normalized_new, "World helper changed beyond immutable supplement pins")
    return {"donor": old, "current": new}


def validate_world_extension(old, new):
    original, revised = old.get("files", {}), new.get("files", {})
    require(isinstance(original, dict) and original and isinstance(revised, dict)
            and all(revised.get(name) == pin for name, pin in original.items()),
            "Revised world changed an existing qualified geometry or texture payload")
    added = {name: pin for name, pin in revised.items() if name not in original}
    require(len(added) == 27 and sum(pin["bytes"] for pin in added.values()) == 8955931
            and all(name.startswith("data/texture_library/") and name.endswith(".texture") for name in added),
            "Expected only the 27 missing Atlas material and shader texture targets")
    require(old.get("source_commit") == new.get("source_commit") and old.get("data_commit") == new.get("data_commit")
            and new.get("runtime_visual_validated") is False and new.get("gameplay_validated") is False,
            "World extension provenance or validation claims differ")
    return added


def apply_world_derivative(destination, donor, commit):
    """Retain qualified backend bytes and regenerate only world-bound metadata."""
    base, destination = builder(), Path(destination)
    assets = destination / "assets/runtime"
    old = read_json(assets / "atlas-world-supplement-manifest.json")
    spec = importlib.util.spec_from_file_location("coh_gameplay_world_derivative", Path(__file__).with_name("prepare_atlas_world_assets.py"))
    world = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(world)
    manifest_path, archive_path = ROOT / "assets" / world.MANIFEST, ROOT / "assets" / world.ARCHIVE
    new = world.read_manifest(manifest_path)
    added = validate_world_extension(old, new)
    helper = ROOT / "android/guest/atlas_world_assets.py"
    helper_delta = validate_world_helper((assets / helper.name).read_bytes(), helper.read_bytes())
    expected = {"MANIFEST_SHA256": world.MANIFEST_PIN["sha256"], "ARCHIVE_SHA256": world.ARCHIVE_PIN["sha256"],
                "ARCHIVE_BYTES": world.ARCHIVE_PIN["bytes"], "PAYLOAD_BYTES": world.PAYLOAD_BYTES,
                "FILE_COUNT": world.FILE_COUNT, "FILES_SHA256": world.FILES_SHA256}
    require(helper_delta["current"] == expected, "Current world helper constants differ from the reviewed derivative")
    materialization = world.materialize(archive_path, manifest_path, base_archive=assets / world.ARCHIVE)
    world.verify(archive_path, manifest_path)
    for source in (archive_path, manifest_path, helper):
        shutil.copyfile(source, assets / source.name)
    payloads = copy.deepcopy(donor["payloads"])
    for name in (world.ARCHIVE, world.MANIFEST, helper.name):
        payloads["assets/runtime/" + name] = base.file_pin(assets / name)
    client = read_json(assets / "client-manifest.json")
    for name in (world.ARCHIVE, world.MANIFEST, helper.name):
        require(name in client["files"], "World derivative input missing from client verification manifest")
        client["files"][name] = payloads["assets/runtime/" + name]
    (assets / "client-manifest.json").write_text(json.dumps(client, indent=2) + "\n")
    payloads["assets/runtime/client-manifest.json"] = base.file_pin(assets / "client-manifest.json")
    runtime = copy.deepcopy(donor["runtime_manifest"])
    for name in (world.ARCHIVE, world.MANIFEST, helper.name, "client-manifest.json"):
        runtime["files"][name] = payloads["assets/runtime/" + name]
    runtime["client_bundle"]["world_supplement"] = world.bundle_contract()
    runtime["repository_commit"] = commit
    runtime["scope"] = "Qualified reopening backend with a revised missing-only Atlas material supplement; gameplay and revised world remain device-unvalidated"
    (assets / "runtime-manifest.json").write_text(json.dumps(runtime, indent=2) + "\n")
    payloads["assets/runtime/runtime-manifest.json"] = base.file_pin(assets / "runtime-manifest.json")
    changed = {name for name in payloads if payloads[name] != donor["payloads"][name]}
    require(changed == WORLD_MEMBERS, "Gameplay resource derivative changed inputs outside the five world-bound members")
    members = [(destination / name, name) for name in sorted(payloads)]
    for path, name in members:
        base.checked_file(path, payloads[name])
    derivative = {"format": 1, "scope": "missing_only_material_shader_texture_resources",
                  "retained_original_files": len(old["files"]),
                  "original_world_manifest": donor["payloads"]["assets/runtime/atlas-world-supplement-manifest.json"],
                  "added_files": added, "added_file_count": len(added), "added_payload_bytes": 8955931,
                  "changed_apk_payloads": sorted(changed), "helper_immutable_pin_delta": helper_delta,
                  "source_manifest": base.file_pin(manifest_path), "archive": base.file_pin(archive_path),
                  "materialization": materialization, "qualified_backend_preserved": True,
                  "revised_world_host_tested": False, "full_apk_host_tested": False,
                  "runtime_visual_validated": False, "gameplay_validated": False}
    # The original world inventory itself binds the retained geometry/textures.
    import hashlib
    derivative["retained_original_files_sha256"] = hashlib.sha256(json.dumps(old["files"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return runtime, members, payloads, derivative


def extract_donor(apk, report, destination):
    """Extract only the exact pinned payload inventory into a fresh directory."""
    base, destination = builder(), Path(destination)
    base.checked_file(Path(apk), report)
    require(not destination.exists() and not destination.is_symlink(), "Fresh donor extraction directory required")
    expected = report.get("payloads", {})
    base.verify_packaged_payloads(apk, expected)
    destination.mkdir(parents=True)
    members = []
    with zipfile.ZipFile(apk) as archive:
        for name in sorted(expected):
            require((name.startswith("assets/runtime/") or name.startswith("assets/atlas/") or name in base.NATIVE_MEMBERS)
                    and ".." not in Path(name).parts and "\\" not in name
                    and not stat.S_ISLNK(archive.getinfo(name).external_attr >> 16), "Unsafe donor APK payload path")
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output, 1024 * 1024)
            base.checked_file(target, expected[name])
            if name.startswith("assets/runtime/") and name.endswith(".py"):
                if Path(name).name == "atlas_world_assets.py":
                    validate_world_helper(target.read_bytes(), (ROOT / "android/guest/atlas_world_assets.py").read_bytes())
                else:
                    base.checked_file(ROOT / "android/guest" / Path(name).name, expected[name])
            members.append((target, name))
    manifest = read_json(destination / "assets/runtime/runtime-manifest.json")
    require(manifest.get("repository_commit") == DONOR_COMMIT
            and base.file_pin(destination / "assets/runtime/runtime-manifest.json")["sha256"] == report.get("runtime_manifest_sha256")
            and manifest == report.get("runtime_manifest"), "Retained runtime manifest provenance differs")
    # The complete payload map is pinned by the reviewed donor build receipt
    # and qualified APK. Current world constants intentionally differ; retain
    # the old client archive's donor provenance rather than relabeling it.
    require(manifest.get("files", {}).get("client-manifest.json") == expected.get("assets/runtime/client-manifest.json"),
            "Donor runtime/client verification inventory differs")
    client = read_json(destination / "assets/runtime/client-manifest.json")
    require(all(expected.get("assets/runtime/" + name) == pin for name, pin in manifest.get("files", {}).items())
            and all(manifest["files"].get(name) == pin for name, pin in client.get("files", {}).items()),
            "Donor verification manifests are inconsistent")
    base.verify_import_package(destination / "assets/atlas")
    for name in base.NATIVE_MEMBERS:
        path = destination / name
        with path.open("rb") as stream:
            header = stream.read(20)
        require(header[:6] == b"\x7fELF\x02\x01" and int.from_bytes(header[18:20], "little") == 183,
                "Retained native payload is not ARM64 ELF")
    return manifest, members, copy.deepcopy(expected)


def gameplay_manifest(source, destination):
    base = builder()
    base.verify_source_manifest(source)
    tree = ET.parse(source)
    manifest = tree.getroot()
    manifest.set(base.ANDROID + "versionName", VERSION_NAME)
    manifest.set(base.ANDROID + "versionCode", str(VERSION_CODE))
    manifest.find("application").set(base.ANDROID + "label", "COH Atlas Gameplay")
    ET.register_namespace("android", base.ANDROID[1:-1])
    tree.write(destination, encoding="utf-8", xml_declaration=True)
    builder(gameplay=True).verify_source_manifest(destination)


class GitHub:
    def __init__(self, token):
        require(bool(token), "GitHub token is required")
        self.token = token

    def request(self, path, data=None, *, method=None, upload=False):
        host = "uploads.github.com" if upload else "api.github.com"
        url = "https://" + host + "/repos/" + REPOSITORY + path
        headers = {"Authorization": "Bearer " + self.token, "Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28"}
        if upload:
            file = Path(data)
            headers.update({"Content-Type": "application/octet-stream", "Content-Length": str(file.stat().st_size)})
            with file.open("rb") as body:
                with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers, method=method), timeout=240) as response:
                    return json.load(response)
        if data is not None:
            data = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method=method), timeout=90) as response:
            return json.load(response)


def qualify(args):
    review = read_json(args.visual_review)
    api = GitHub(os.environ.get("GH_TOKEN"))
    qualification_id = review.get("qualification_run_id")
    require(type(qualification_id) is int and qualification_id > 0, "Reviewed runtime qualification run is missing")
    metadata = {"format": 1}
    for key, identifier, name in (("donor", DONOR_RUN_ID, DONOR_ARTIFACT_NAME), ("qualification", qualification_id, EVIDENCE_NAME)):
        artifacts = api.request(f"/actions/runs/{identifier}/artifacts?per_page=100")
        require(artifacts.get("total_count") == len(artifacts.get("artifacts", [])), "Incomplete source artifact pagination")
        found = [item for item in artifacts.get("artifacts", []) if item.get("name") == name]
        require(len(found) == 1, "Missing or duplicated source artifact: " + name)
        metadata[key] = {"run": api.request(f"/actions/runs/{identifier}"),
                         "jobs": api.request(f"/actions/runs/{identifier}/jobs?filter=latest&per_page=100"),
                         "artifacts": {name: found[0]}}
    validate_qualification(metadata, review)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    require(not args.output.exists() and not args.output.is_symlink(), "Fresh qualification metadata output required")
    args.output.write_text(json.dumps(metadata, indent=2) + "\n")
    print("Exact completed ARM64 reopening and reviewed Atlas world qualification verified.")


def build(args):
    base, current = builder(), builder(gameplay=True)
    commit = base.source_commit(args.repository_commit)
    metadata, review = read_json(args.qualification), read_json(args.visual_review)
    validate_qualification(metadata, review)
    apk_pin, build_pin, apk_artifact = reviewed_donor_pins(review)
    base.checked_file(args.donor_build_report, build_pin)
    donor = read_json(args.donor_build_report)
    base.checked_file(args.evidence / HOST_REPORT_NAME, review["host_report"])
    validate_donor_receipts(donor, read_json(args.evidence / HOST_REPORT_NAME), review)
    base.checked_file(args.evidence / DRIVER_NAME, review["qualification_driver"])
    harness_sources = validate_driver(read_json(args.evidence / DRIVER_NAME), review)
    for frame in review["visual_evidence_frames"]:
        base.checked_file(args.evidence / frame["name"], frame)
    preserved_sources = verify_backend_sources(donor)
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, "coh-client-interactive", SIGNER, password)
    base.checked_file(args.testing_notes)
    require(args.testing_notes.stat().st_size <= 65536 and args.testing_notes.read_text().strip(), "Bounded gameplay testing notes required")
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), "Fresh gameplay APK output required")
    for tool in (args.android_jar, args.build_tools / "aapt2", args.build_tools / "zipalign",
                 args.build_tools / "lib/d8.jar", args.build_tools / "lib/apksigner.jar"):
        require(tool.is_file() and not tool.is_symlink(), "Missing Android build tool: " + str(tool))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="coh-atlas-gameplay-", dir=args.output.parent) as temporary:
        work = Path(temporary)
        runtime, members, payloads = extract_donor(args.donor_apk, donor, work / "donor")
        runtime, members, payloads, world_derivative = apply_world_derivative(work / "donor", donor, commit)
        classes, generated, dex = (work / name for name in ("classes", "generated", "dex"))
        for folder in (classes, generated, dex):
            folder.mkdir()
        manifest = work / "AndroidManifest.xml"
        source_manifest = ROOT / "android/interactive/src/main/AndroidManifest.xml"
        gameplay_manifest(source_manifest, manifest)
        resources, unsigned, aligned, signed = (work / name for name in ("resources.zip", "unsigned.apk", "aligned.apk", "signed.apk"))
        main = ROOT / "android/interactive/src/main"
        base.run(args.build_tools / "aapt2", "compile", "--dir", main / "res", "-o", resources)
        base.run(args.build_tools / "aapt2", "link", "-I", args.android_jar, "--manifest", manifest,
                 "--min-sdk-version", "26", "--target-sdk-version", "35", "--java", generated, resources, "-o", unsigned)
        sources = base.java_sources(main, generated)
        source_pins = {path.relative_to(ROOT).as_posix(): base.file_pin(path) for path in sources
                       if path.is_relative_to(ROOT) and not path.is_relative_to(work)}
        base.run("java", "-m", "jdk.compiler/com.sun.tools.javac.Main", "--release", "8", "-cp", args.android_jar,
                 "-d", classes, *sources)
        class_jar = work / "classes.jar"
        with zipfile.ZipFile(class_jar, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(classes.rglob("*.class")):
                archive.write(path, path.relative_to(classes).as_posix())
        base.run("java", "-cp", args.build_tools / "lib/d8.jar", "com.android.tools.r8.D8", "--min-api", "26",
                 "--lib", args.android_jar, "--output", dex, class_jar)
        with zipfile.ZipFile(unsigned, "a", zipfile.ZIP_DEFLATED) as archive:
            base.append_payloads(archive, members)
            for path in sorted(dex.glob("*.dex")):
                archive.write(path, path.name)
        base.run(args.build_tools / "zipalign", "-f", "4", unsigned, aligned)
        base.run("java", "-jar", args.build_tools / "lib/apksigner.jar", "sign", "--ks", args.keystore,
                 "--ks-key-alias", "coh-client-interactive", "--ks-pass", password, "--key-pass", password, "--out", signed, aligned)
        certificate = base.verify_signer_output(base.run("java", "-jar", args.build_tools / "lib/apksigner.jar",
                                                       "verify", "--verbose", "--print-certs", signed), SIGNER)
        base.run(args.build_tools / "zipalign", "-c", "4", signed)
        badging = base.run(args.build_tools / "aapt2", "dump", "badging", signed)
        current.verify_badging(badging)
        base.verify_packaged_payloads(signed, payloads)
        shutil.copyfile(signed, args.output)
        report = {"format": 1, "apk": APK_NAME, **base.file_pin(args.output), "repository_commit": commit,
                  "application_id": base.APP_ID, "version_name": VERSION_NAME, "version_code": VERSION_CODE,
                  "abi": "arm64-v8a", "signer_certificate_sha256": certificate, "signing_key_created": False,
                  "signature_verified": True, "package_badging_verified": True, "payload_bytes_verified": True,
                  "qualified_backend_reused": True, "guest_files_changed": True, "native_libraries_changed": False,
                  "client_or_server_recompiled": False, "world_supplement_reconstructed": True,
                  "runtime_manifest_sha256": payloads["assets/runtime/runtime-manifest.json"]["sha256"], "runtime_manifest": runtime,
                  "world_derivative": world_derivative,
                  "payloads": payloads, "java_sources": source_pins, "preserved_sources": preserved_sources,
                  "source_manifest": base.file_pin(source_manifest), "generated_manifest": base.file_pin(manifest),
                  "testing_notes": {"name": NOTES_NAME, **base.file_pin(args.testing_notes)},
                  "qualification_donor": {"run_id": DONOR_RUN_ID, "repository_commit": DONOR_COMMIT,
                      "apk": apk_pin, "build_report": build_pin,
                      "artifact": apk_artifact, "evidence_artifact": review["qualification_artifact"],
                      "qualification_run_id": review["qualification_run_id"],
                      "qualification_head_sha": review["qualification_head_sha"],
                      "qualification_driver": review["qualification_driver"], "host_harness_sources": harness_sources,
                      "host_report": review["host_report"], "visual_review": base.file_pin(args.visual_review),
                      "visual_evidence_frames": review["visual_evidence_frames"]},
                  "scope": "Android Atlas gameplay input and missing material-texture candidate retaining the qualified reopening backend; revised world inputs and complete APK await device validation",
                  "device_validated": False, "gameplay_validated": False,
                  "installation": "In-place retained-signer update from accepted Character Creation 0.9.0. Refresh runtime; preserve THORHERO, private database, Wine profile and imported assets."}
        (args.output.parent / REPORT_NAME).write_text(json.dumps(report, indent=2) + "\n")
        args.output.with_suffix(".apk.sha256").write_text(report["sha256"] + "  " + APK_NAME + "\n")
        shutil.copyfile(args.testing_notes, args.output.parent / NOTES_NAME)
        print("Built retained-signer Atlas gameplay candidate", report["sha256"], "with the qualified backend and verified material inputs.")


def publish_release(api, report, assets, notes):
    base = builder()
    require(tuple(path.name for path in assets) == (APK_NAME, APK_NAME + ".sha256", NOTES_NAME), "Unexpected gameplay release assets")
    base.checked_file(assets[0], report)
    for path in ("/releases/tags/" + RELEASE_TAG, "/git/ref/tags/" + RELEASE_TAG):
        try:
            existing = api.request(path)
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
        else:
            if path.startswith("/releases/"):
                raise ValueError("Existing gameplay release is never replaced")
            require(existing.get("object", {}).get("type") == "commit"
                    and existing["object"].get("sha") == report["repository_commit"], "Existing gameplay tag points elsewhere")
    body = notes + "\n\nAPK SHA-256: `" + report["sha256"] + "`.\n"
    body += "[Retained backend's completed ARM64 qualification](https://github.com/" + REPOSITORY + "/actions/runs/" + str(report["qualification_donor"]["qualification_run_id"]) + ").\n"
    body += "The 27 missing material textures and Android gameplay controls are new; the revised world and complete APK require the focused AYN Thor device test.\n"
    release = api.request("/releases", {"tag_name": RELEASE_TAG, "target_commitish": report["repository_commit"],
                          "name": "COH Atlas Gameplay 0.11.0", "body": body, "draft": True, "prerelease": True,
                          "generate_release_notes": False, "make_latest": "false"}, method="POST")
    require(type(release.get("id")) is int and release.get("draft") is True
            and release.get("prerelease") is True and release.get("tag_name") == RELEASE_TAG, "Unexpected created draft release")
    for path in assets:
        result = api.request("/releases/" + str(release["id"]) + "/assets?" + urllib.parse.urlencode({"name": path.name}),
                             path, method="POST", upload=True)
        pin = base.file_pin(path)
        require(result.get("state") == "uploaded" and result.get("name") == path.name
                and result.get("size") == pin["bytes"] and result.get("digest") == "sha256:" + pin["sha256"],
                "Gameplay release upload bytes were not verified")
    published = api.request("/releases/" + str(release["id"]), {"draft": False, "prerelease": True, "make_latest": "false"}, method="PATCH")
    require(published.get("id") == release["id"] and published.get("draft") is False
            and published.get("prerelease") is True and published.get("tag_name") == RELEASE_TAG,
            "Gameplay prerelease publication did not complete")
    return published.get("html_url")


def publish(args):
    base, current = builder(), builder(gameplay=True)
    require(os.environ.get("GITHUB_REPOSITORY") == REPOSITORY and os.environ.get("GITHUB_REF") == "refs/heads/" + BRANCH
            and os.environ.get("GITHUB_EVENT_NAME") in ("push", "workflow_dispatch"), "Gameplay publication requires the authorized continuation branch")
    report = read_json(args.build_report)
    require(report.get("format") == 1 and report.get("apk") == APK_NAME and report.get("application_id") == base.APP_ID
            and report.get("version_name") == VERSION_NAME and report.get("version_code") == VERSION_CODE
            and report.get("repository_commit") == os.environ.get("GITHUB_SHA")
            and report.get("signer_certificate_sha256") == SIGNER and report.get("signing_key_created") is False
            and all(report.get(key) is True for key in ("signature_verified", "package_badging_verified", "payload_bytes_verified", "qualified_backend_reused",
                                                      "guest_files_changed", "world_supplement_reconstructed"))
            and all(report.get(key) is False for key in ("native_libraries_changed", "client_or_server_recompiled", "device_validated", "gameplay_validated")),
            "Gameplay APK receipt differs from the intended qualified-backend resource derivative")
    review = read_json(args.visual_review)
    validate_qualification(read_json(args.qualification), review)
    apk_pin, build_pin, artifact = reviewed_donor_pins(review)
    donor = report.get("qualification_donor", {})
    require(donor.get("run_id") == DONOR_RUN_ID and donor.get("repository_commit") == DONOR_COMMIT
            and donor.get("apk") == apk_pin and donor.get("build_report") == build_pin and donor.get("artifact") == artifact
            and donor.get("qualification_run_id") == review["qualification_run_id"]
            and donor.get("qualification_head_sha") == review["qualification_head_sha"]
            and donor.get("qualification_driver") == review["qualification_driver"]
            and donor.get("visual_review") == base.file_pin(args.visual_review), "Gameplay donor provenance differs")
    derivative = report.get("world_derivative", {})
    require(derivative.get("qualified_backend_preserved") is True and derivative.get("added_file_count") == 27
            and derivative.get("added_payload_bytes") == 8955931 and set(derivative.get("changed_apk_payloads", [])) == WORLD_MEMBERS
            and all(derivative.get(key) is False for key in ("revised_world_host_tested", "full_apk_host_tested", "runtime_visual_validated", "gameplay_validated")),
            "Gameplay resource derivative provenance or testing claims differ")
    base.checked_file(args.apk, report)
    base.verify_packaged_payloads(args.apk, report["payloads"])
    base.verify_signer_output(base.run("java", "-jar", args.build_tools / "lib/apksigner.jar", "verify", "--verbose", "--print-certs", args.apk), SIGNER)
    current.verify_badging(base.run(args.build_tools / "aapt2", "dump", "badging", args.apk))
    base.checked_file(args.testing_notes, report["testing_notes"])
    checksum = args.apk.with_suffix(".apk.sha256")
    require(checksum.read_text() == report["sha256"] + "  " + APK_NAME + "\n", "Gameplay APK checksum differs")
    public_notes = args.apk.parent / NOTES_NAME
    base.checked_file(public_notes, report["testing_notes"])
    url = publish_release(GitHub(os.environ.get("GH_TOKEN")), report, (args.apk, checksum, public_notes), public_notes.read_text())
    print("Published gameplay prerelease:", url)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    gate = commands.add_parser("qualify")
    gate.add_argument("--visual-review", type=Path, default=VISUAL_REVIEW)
    gate.add_argument("--output", type=Path, required=True)
    create = commands.add_parser("build")
    for name in ("donor-apk", "donor-build-report", "evidence", "qualification", "android-jar", "build-tools", "keystore", "output"):
        create.add_argument("--" + name, type=Path, required=True)
    create.add_argument("--visual-review", type=Path, default=VISUAL_REVIEW)
    create.add_argument("--testing-notes", type=Path, default=NOTES)
    create.add_argument("--repository-commit")
    create.add_argument("--password-env", default="COH_INTERACTIVE_KEYSTORE_PASSWORD")
    release = commands.add_parser("publish")
    for name in ("apk", "build-report", "build-tools", "qualification"):
        release.add_argument("--" + name, type=Path, required=True)
    release.add_argument("--visual-review", type=Path, default=VISUAL_REVIEW)
    release.add_argument("--testing-notes", type=Path, default=NOTES)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.absolute())
    {"qualify": qualify, "build": build, "publish": publish}[args.command](args)


if __name__ == "__main__":
    main()
