#!/usr/bin/env python3
"""Package a focused avatar worktree repair around the exact published 0.11.0 APK.

The accepted DEX, native libraries, world, client and server are copied from the
signed donor. Only the avatar helper and its two verification manifests change.
Publication requires the separate native ARM64 PRoot upgrade qualification.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[3]
REPOSITORY = "Russianranger/coh-android"
BRANCH = "codex/character-persistence-continuation"
DONOR_COMMIT = "1649e807d2b2310170e775c53bafa24cd932638a"
DONOR_RUN_ID = 36937373454
DONOR_APK_NAME = "COH-Atlas-Gameplay-0.11.0.apk"
DONOR_APK = {"bytes": 595099993, "sha256": "e3a0760d23ef57747343ee8fd0c76e68a92194df040062266f3dc282cd15a924"}
DONOR_BUILD = {"bytes": 45992, "sha256": "cc0ad0f09bf06f598e6f65e706260fa9bb1a90e699ad1794d9df9ff1625d1d00"}
DONOR_URL = "https://github.com/" + REPOSITORY + "/releases/download/coh-atlas-gameplay-v0.11.0/" + DONOR_APK_NAME
SIGNER = "92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282"
VERSION_NAME, VERSION_CODE = "0.11.1", 7
APK_NAME = "COH-Atlas-Gameplay-0.11.1.apk"
REPORT_NAME = "avatar-repair-apk-build-report.json"
NOTES_NAME = "COH-Atlas-Gameplay-0.11.1-testing.txt"
RELEASE_TAG = "coh-atlas-gameplay-v0.11.1"
NOTES = ROOT / "docs" / NOTES_NAME
HELPER = "character_avatar_assets.py"
CHANGED_PAYLOADS = frozenset("assets/runtime/" + name for name in (HELPER, "client-manifest.json", "runtime-manifest.json"))
QUALIFICATION_SCOPE = "legacy_avatar_hardlink_repair_native_proot"
QUALIFICATION_SCRIPT = "tools/android/interactive/qualify_avatar_repair.py"
WORKFLOW = ".github/workflows/android-avatar-repair.yml"


def require(value, message):
    if not value:
        raise ValueError(message)


def builder(*, repaired=False):
    spec = importlib.util.spec_from_file_location("coh_avatar_repair_base", Path(__file__).with_name("build_apk.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if repaired:
        module.VERSION_NAME, module.VERSION_CODE, module.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return module


def read_json(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= 8 * 1024 * 1024,
            "Missing, linked or oversized metadata: " + path.name)
    return json.loads(path.read_text())


def validate_donor_receipt(report):
    require(report.get("format") == 1 and report.get("apk") == DONOR_APK_NAME
            and report.get("repository_commit") == DONOR_COMMIT
            and {key: report.get(key) for key in DONOR_APK} == DONOR_APK
            and report.get("application_id") == builder().APP_ID
            and report.get("version_name") == "0.11.0" and report.get("version_code") == 6
            and report.get("abi") == "arm64-v8a" and report.get("signer_certificate_sha256") == SIGNER
            and report.get("signing_key_created") is False
            and all(report.get(key) is True for key in ("signature_verified", "package_badging_verified", "payload_bytes_verified")),
            "Exact published retained-signer 0.11.0 donor receipt differs")


def validate_donor(apk, report_path):
    base = builder()
    base.checked_file(apk, DONOR_APK)
    base.checked_file(report_path, DONOR_BUILD)
    report = read_json(report_path)
    validate_donor_receipt(report)
    base.verify_packaged_payloads(apk, report["payloads"])
    return report


def validate_qualification(receipt, commit):
    base = builder()
    require(receipt.get("format") == 1 and receipt.get("status") == "passed"
            and receipt.get("scope") == QUALIFICATION_SCOPE and receipt.get("machine") == "aarch64"
            and receipt.get("guest_uid") == 1000 and receipt.get("execution_platform") == "native_proot"
            and receipt.get("repository_commit") == commit and receipt.get("donor_apk_sha256") == DONOR_APK["sha256"],
            "A focused native ARM64 PRoot repair qualification for this exact commit is required")
    files = receipt.get("source_files", {})
    for name in ("android/guest/" + HELPER, QUALIFICATION_SCRIPT, WORKFLOW,
                 "tools/android/interactive/build_avatar_repair_apk.py"):
        require(name in files, "Repair qualification source closure is incomplete")
        base.checked_file(ROOT / name, files[name])
    require(receipt.get("helper_sha256") == files["android/guest/" + HELPER]["sha256"]
            and receipt.get("qualifier_sha256") == files[QUALIFICATION_SCRIPT]["sha256"], "Qualified helper or driver pin differs")
    fixture = receipt.get("fixture", {})
    require(fixture.get("old_read_nofollow_errno") == 40 and fixture.get("repaired_files") == 21
            and fixture.get("repeated_reused_files") == 21
            and all(fixture.get(name) is True for name in ("exact_bytes_metadata_preserved", "hidden_backing_entries_removed",
                                                         "sentinels_preserved", "negative_cases_passed")),
            "Avatar reuse repair checks are incomplete")
    require(all(fixture.get("interruption_cases", {}).get(name, {}).get("retry_passed") is True
                and fixture["interruption_cases"][name].get("all_payloads_preserved") is True
                and fixture["interruption_cases"][name].get("hidden_backing_entries_removed") is True
                for name in ("after_leaf_replacement", "after_intermediate_removal")),
            "Interrupted repair retries must preserve all payloads and remove old backing entries")
    require(fixture.get("healthy_links_refused_unchanged", {}).get("refused") is True
            and fixture["healthy_links_refused_unchanged"].get("all_entries_preserved") is True,
            "Healthy or foreign links must not be silently repaired")
    proot = receipt.get("native_proot_build", {})
    require(proot.get("target") == "linux-arm64" and proot.get("source_commit") == "7266fb3e8516535682f5a9c8f3a7e70f6506eddb"
            and proot.get("source_tree") == "8fcee3911b8e0848a1fc75c2e9827316ba658a5a"
            and proot.get("sysvipc_memfd_patch") is True and proot.get("optional_acceleration_patch") is False,
            "Focused qualification must use the accepted PRoot source and patch family")
    return receipt


def repair_manifests(runtime, client, helper_pin, client_pin, commit):
    """Return the exact narrow derivative without relabeling immutable packages."""
    revised_client = copy.deepcopy(client)
    require(HELPER in revised_client.get("files", {}), "Donor client helper pin is missing")
    revised_client["files"][HELPER] = helper_pin
    revised_runtime = copy.deepcopy(runtime)
    require(HELPER in revised_runtime.get("files", {}) and "client-manifest.json" in revised_runtime["files"],
            "Donor runtime verification pins are incomplete")
    revised_runtime["files"][HELPER] = helper_pin
    revised_runtime["files"]["client-manifest.json"] = client_pin
    revised_runtime["repository_commit"] = commit
    revised_runtime["scope"] = "Published 0.11.0 gameplay candidate with focused native PRoot avatar reuse repair; physical reopening and gameplay remain pending"
    return revised_runtime, revised_client


def extract_and_repair(apk, donor, destination, commit):
    base = builder()
    require(not destination.exists() and not destination.is_symlink(), "Fresh donor extraction tree required")
    destination.mkdir(parents=True)
    retained = {}
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), "Duplicate donor APK entries")
        for entry in archive.infolist():
            name = entry.filename
            if name == "AndroidManifest.xml" or name.startswith("META-INF/"):
                continue
            require(name in donor["payloads"] or name in ("classes.dex", "resources.arsc", "res/drawable/ic_coh_client.xml"),
                    "Unexpected donor APK member")
            require(not stat.S_ISLNK(entry.external_attr >> 16), "Linked donor APK member")
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output, 1024 * 1024)
            retained[name] = base.file_pin(target)
    require(all(retained.get(name) == pin for name, pin in donor["payloads"].items()), "Donor payload bytes differ")
    assets = destination / "assets/runtime"
    runtime = read_json(assets / "runtime-manifest.json")
    client = read_json(assets / "client-manifest.json")
    require(runtime == donor["runtime_manifest"] and runtime["repository_commit"] == DONOR_COMMIT,
            "Donor runtime manifest identity differs")
    require(all(runtime["files"].get(name) == pin for name, pin in client["files"].items()),
            "Donor client/runtime verification manifests differ")
    for name, pin in donor.get("java_sources", {}).items():
        base.checked_file(ROOT / name, pin)
    for name, pin in donor.get("native_launcher_source", {}).items():
        base.checked_file(ROOT / name, pin)
    for name, pin in donor["payloads"].items():
        if name.startswith("assets/runtime/") and name.endswith(".py") and Path(name).name != HELPER:
            base.checked_file(ROOT / "android/guest" / Path(name).name, pin)
    helper = ROOT / "android/guest" / HELPER
    shutil.copyfile(helper, assets / HELPER)
    helper_pin = base.file_pin(helper)
    updated_client = copy.deepcopy(client)
    updated_client["files"][HELPER] = helper_pin
    (assets / "client-manifest.json").write_text(json.dumps(updated_client, indent=2) + "\n")
    runtime, expected_client = repair_manifests(runtime, client, helper_pin,
        base.file_pin(assets / "client-manifest.json"), commit)
    require(updated_client == expected_client, "Client metadata changed beyond its helper pin")
    (assets / "runtime-manifest.json").write_text(json.dumps(runtime, indent=2) + "\n")
    revised = {name: base.file_pin(destination / name) for name in retained}
    require({name for name in revised if revised[name] != retained[name]} == CHANGED_PAYLOADS,
            "Avatar repair changed members outside its helper and two verification manifests")
    return runtime, {name: revised[name] for name in donor["payloads"]}, revised


def repair_android_manifest(source, destination):
    base = builder()
    base.verify_source_manifest(source)
    tree = ET.parse(source)
    manifest = tree.getroot()
    manifest.set(base.ANDROID + "versionName", VERSION_NAME)
    manifest.set(base.ANDROID + "versionCode", str(VERSION_CODE))
    manifest.find("application").set(base.ANDROID + "label", "COH Atlas Gameplay")
    ET.register_namespace("android", base.ANDROID[1:-1])
    tree.write(destination, encoding="utf-8", xml_declaration=True)
    builder(repaired=True).verify_source_manifest(destination)


def download(args):
    require(not args.output.exists() and not args.output.is_symlink(), "Fresh donor APK output required")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(DONOR_URL, timeout=120) as source, args.output.open("xb") as target:
        total = 0
        while chunk := source.read(1024 * 1024):
            total += len(chunk)
            require(total <= DONOR_APK["bytes"], "Donor download exceeds the pinned size")
            target.write(chunk)
    builder().checked_file(args.output, DONOR_APK)
    print("Exact published 0.11.0 donor APK downloaded and pinned.")


def prepare(args):
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    require(not args.output.exists() and not args.output.is_symlink(), "Fresh qualification inputs directory required")
    args.output.mkdir(parents=True)
    # Recover only the accepted source receipts; no Wine/rootfs rebuild or
    # another graphical session is needed for this pre-game file operation.
    with zipfile.ZipFile(args.donor_apk) as archive:
        for source, target in (("accepted-runtime-manifest.json", "runtime-manifest.json"),
                               ("proot-build.json", "proot-build.json")):
            data = archive.read("assets/runtime/" + source)
            require({"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} ==
                    donor["payloads"]["assets/runtime/" + source], "Accepted qualification input differs")
            (args.output / target).write_bytes(data)


def build(args):
    base, current = builder(), builder(repaired=True)
    commit = base.source_commit(args.repository_commit)
    donor = validate_donor(args.donor_apk, args.donor_build_report)
    qualification = validate_qualification(read_json(args.qualification), commit)
    base.checked_file(ROOT / "android/interactive/src/main/AndroidManifest.xml", donor["source_manifest"])
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, "coh-client-interactive", SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), "Fresh repair APK required")
    base.checked_file(args.testing_notes)
    require(0 < args.testing_notes.stat().st_size <= 65536, "Bounded testing notes required")
    for tool in (args.android_jar, args.build_tools / "aapt2", args.build_tools / "zipalign", args.build_tools / "lib/apksigner.jar"):
        require(tool.is_file() and not tool.is_symlink(), "Required Android tool missing")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="coh-avatar-repair-", dir=args.output.parent) as temporary:
        work = Path(temporary)
        runtime, payloads, members = extract_and_repair(args.donor_apk, donor, work / "donor", commit)
        manifest = work / "AndroidManifest.xml"
        repair_android_manifest(ROOT / "android/interactive/src/main/AndroidManifest.xml", manifest)
        resources, unsigned, aligned, signed = (work / name for name in ("resources.zip", "unsigned.apk", "aligned.apk", "signed.apk"))
        base.run(args.build_tools / "aapt2", "compile", "--dir", ROOT / "android/interactive/src/main/res", "-o", resources)
        base.run(args.build_tools / "aapt2", "link", "-I", args.android_jar, "--manifest", manifest,
                 "--min-sdk-version", "26", "--target-sdk-version", "35", resources, "-o", unsigned)
        with zipfile.ZipFile(unsigned) as archive:
            require(set(archive.namelist()) == {"AndroidManifest.xml", "resources.arsc", "res/drawable/ic_coh_client.xml"},
                    "Generated Android resource inventory differs")
            for name in ("resources.arsc", "res/drawable/ic_coh_client.xml"):
                data = archive.read(name)
                require({"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} == members[name],
                        "Android resources changed beyond package version metadata")
        with zipfile.ZipFile(unsigned, "a", zipfile.ZIP_DEFLATED) as archive:
            base.append_payloads(archive, [(work / "donor" / name, name) for name in sorted(payloads)])
            archive.write(work / "donor/classes.dex", "classes.dex")
        base.run(args.build_tools / "zipalign", "-f", "4", unsigned, aligned)
        base.run("java", "-jar", args.build_tools / "lib/apksigner.jar", "sign", "--ks", args.keystore,
                 "--ks-key-alias", "coh-client-interactive", "--ks-pass", password, "--key-pass", password, "--out", signed, aligned)
        certificate = base.verify_signer_output(base.run("java", "-jar", args.build_tools / "lib/apksigner.jar",
                                                       "verify", "--verbose", "--print-certs", signed), SIGNER)
        base.run(args.build_tools / "zipalign", "-c", "4", signed)
        current.verify_badging(base.run(args.build_tools / "aapt2", "dump", "badging", signed))
        base.verify_packaged_payloads(signed, payloads)
        with zipfile.ZipFile(signed) as archive:
            for name in ("classes.dex", "resources.arsc", "res/drawable/ic_coh_client.xml"):
                data = archive.read(name)
                require({"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} == members[name], "Retained Android shell bytes changed")
        shutil.copyfile(signed, args.output)
        report = {"format": 1, "apk": APK_NAME, **base.file_pin(args.output), "repository_commit": commit,
                  "application_id": base.APP_ID, "version_name": VERSION_NAME, "version_code": VERSION_CODE,
                  "abi": "arm64-v8a", "signer_certificate_sha256": certificate, "signing_key_created": False,
                  "signature_verified": True, "package_badging_verified": True, "payload_bytes_verified": True,
                  "runtime_manifest": runtime, "runtime_manifest_sha256": payloads["assets/runtime/runtime-manifest.json"]["sha256"],
                  "payloads": payloads, "changed_apk_payloads": sorted(CHANGED_PAYLOADS),
                  "retained_dex": members["classes.dex"], "retained_android_resources": {name: members[name] for name in ("resources.arsc", "res/drawable/ic_coh_client.xml")},
                  "donor": {"run_id": DONOR_RUN_ID, "repository_commit": DONOR_COMMIT, "apk": DONOR_APK, "build_report": DONOR_BUILD},
                  "qualification": qualification, "qualification_receipt": base.file_pin(args.qualification),
                  "testing_notes": base.file_pin(args.testing_notes), "native_libraries_changed": False,
                  "client_or_server_recompiled": False, "java_or_dex_recompiled": False, "world_assets_changed": False,
                  "physical_gameplay_validated": False,
                  "scope": "Focused avatar reuse repair retaining the complete published 0.11.0 gameplay shell and world; physical reopening, Atlas rendering and ground recovery pending"}
        (args.output.parent / REPORT_NAME).write_text(json.dumps(report, indent=2) + "\n")
        args.output.with_suffix(".apk.sha256").write_text(report["sha256"] + "  " + APK_NAME + "\n")
        shutil.copyfile(args.testing_notes, args.output.parent / NOTES_NAME)
        print("Built focused retained-signer avatar repair", report["sha256"])


def publish_release(api, report, assets, notes):
    base = builder()
    require(tuple(path.name for path in assets) == (APK_NAME, APK_NAME + ".sha256", NOTES_NAME), "Unexpected repair release assets")
    base.checked_file(assets[0], report)
    for path in ("/releases/tags/" + RELEASE_TAG, "/git/ref/tags/" + RELEASE_TAG):
        try:
            existing = api.request(path)
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
        else:
            require(not path.startswith("/releases/"), "Existing repair release is never replaced")
            require(existing.get("object", {}).get("type") == "commit" and existing["object"].get("sha") == report["repository_commit"],
                    "Existing repair tag points elsewhere")
    body = notes + "\n\nAPK SHA-256: `" + report["sha256"] + "`.\n"
    body += "[Focused native ARM64 PRoot qualification](https://github.com/" + REPOSITORY + "/actions/runs/" + os.environ.get("GITHUB_RUN_ID", "") + ").\n"
    release = api.request("/releases", {"tag_name": RELEASE_TAG, "target_commitish": report["repository_commit"],
        "name": "COH Atlas Gameplay 0.11.1 — saved-character asset repair", "body": body, "draft": True,
        "prerelease": True, "generate_release_notes": False, "make_latest": "false"}, method="POST")
    require(type(release.get("id")) is int and release.get("draft") is True and release.get("prerelease") is True
            and release.get("tag_name") == RELEASE_TAG, "Unexpected created repair release")
    for path in assets:
        result = api.request("/releases/" + str(release["id"]) + "/assets?" + urllib.parse.urlencode({"name": path.name}),
                             path, method="POST", upload=True)
        pin = base.file_pin(path)
        require(result.get("state") == "uploaded" and result.get("name") == path.name and result.get("size") == pin["bytes"]
                and result.get("digest") == "sha256:" + pin["sha256"], "Repair release upload bytes differ")
    published = api.request("/releases/" + str(release["id"]), {"draft": False, "prerelease": True, "make_latest": "false"}, method="PATCH")
    require(published.get("id") == release["id"] and published.get("draft") is False and published.get("prerelease") is True
            and published.get("tag_name") == RELEASE_TAG, "Repair publication did not complete")
    return published.get("html_url")


def publish(args):
    base, current = builder(), builder(repaired=True)
    require(os.environ.get("GITHUB_REPOSITORY") == REPOSITORY and os.environ.get("GITHUB_REF") == "refs/heads/" + BRANCH
            and os.environ.get("GITHUB_EVENT_NAME") in ("push", "workflow_dispatch"), "Repair publication requires the authorized continuation branch")
    report = read_json(args.build_report)
    require(report.get("format") == 1 and report.get("apk") == APK_NAME and report.get("application_id") == base.APP_ID
            and report.get("version_name") == VERSION_NAME and report.get("version_code") == VERSION_CODE
            and report.get("repository_commit") == os.environ.get("GITHUB_SHA") and report.get("signer_certificate_sha256") == SIGNER
            and report.get("signing_key_created") is False
            and all(report.get(key) is True for key in ("signature_verified", "package_badging_verified", "payload_bytes_verified"))
            and all(report.get(key) is False for key in ("native_libraries_changed", "client_or_server_recompiled", "java_or_dex_recompiled", "world_assets_changed", "physical_gameplay_validated"))
            and set(report.get("changed_apk_payloads", [])) == CHANGED_PAYLOADS
            and report.get("donor") == {"run_id": DONOR_RUN_ID, "repository_commit": DONOR_COMMIT, "apk": DONOR_APK, "build_report": DONOR_BUILD},
            "Repair build receipt or derivative boundaries differ")
    receipt = read_json(args.qualification)
    validate_qualification(receipt, report["repository_commit"])
    require(receipt == report.get("qualification") and base.file_pin(args.qualification) == report.get("qualification_receipt"), "Qualified repair evidence changed")
    base.checked_file(args.apk, report)
    base.verify_packaged_payloads(args.apk, report["payloads"])
    base.verify_signer_output(base.run("java", "-jar", args.build_tools / "lib/apksigner.jar", "verify", "--verbose", "--print-certs", args.apk), SIGNER)
    current.verify_badging(base.run(args.build_tools / "aapt2", "dump", "badging", args.apk))
    base.checked_file(args.testing_notes, report["testing_notes"])
    checksum = args.apk.with_suffix(".apk.sha256")
    require(checksum.read_text() == report["sha256"] + "  " + APK_NAME + "\n", "Repair checksum differs")
    public_notes = args.apk.parent / NOTES_NAME
    base.checked_file(public_notes, report["testing_notes"])
    spec = importlib.util.spec_from_file_location("coh_repair_github", Path(__file__).with_name("build_atlas_gameplay_apk.py"))
    api_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api_module)
    print("Published avatar repair prerelease:", publish_release(api_module.GitHub(os.environ.get("GH_TOKEN")), report,
          (args.apk, checksum, public_notes), public_notes.read_text()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    get = commands.add_parser("download-donor")
    get.add_argument("--output", type=Path, required=True)
    inputs = commands.add_parser("prepare-qualification")
    for name in ("donor-apk", "donor-build-report", "output"):
        inputs.add_argument("--" + name, type=Path, required=True)
    create = commands.add_parser("build")
    for name in ("donor-apk", "donor-build-report", "qualification", "android-jar", "build-tools", "keystore", "output"):
        create.add_argument("--" + name, type=Path, required=True)
    create.add_argument("--repository-commit")
    create.add_argument("--password-env", default="COH_INTERACTIVE_KEYSTORE_PASSWORD")
    create.add_argument("--testing-notes", type=Path, default=NOTES)
    release = commands.add_parser("publish")
    for name in ("apk", "build-report", "build-tools", "qualification"):
        release.add_argument("--" + name, type=Path, required=True)
    release.add_argument("--testing-notes", type=Path, default=NOTES)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.absolute())
    {"download-donor": download, "prepare-qualification": prepare, "build": build, "publish": publish}[args.command](args)


if __name__ == "__main__":
    main()
