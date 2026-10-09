#!/usr/bin/env python3
"""Build the standalone, import-only Atlas Setup APK with JDK 17 and SDK 35.

This application carries reviewed data and its import contract. It deliberately
contains no game/server runtime, native libraries, or network permission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP_ID = "io.github.russianranger.cohatlas"
LAUNCHER = APP_ID + ".AtlasActivity"
VERSION_NAME = "0.3.0"
VERSION_CODE = 1
APK_NAME = f"COH-Atlas-Setup-{VERSION_NAME}.apk"
ANDROID = "{http://schemas.android.com/apk/res/android}"
PAYLOAD_NAMES = frozenset({"atlas-import.properties", "atlas-text.zip",
                           "atlas-text-index.tsv", "atlas-assets-index.tsv"})
STREAM_BLOCK = 1024 * 1024
PERMISSIONS = frozenset("android.permission." + name for name in (
    "FOREGROUND_SERVICE", "FOREGROUND_SERVICE_SPECIAL_USE", "POST_NOTIFICATIONS", "WAKE_LOCK"))


def stream_digest(stream):
    result = hashlib.sha256()
    count = 0
    while True:
        block = stream.read(STREAM_BLOCK)
        if not block:
            return count, result.hexdigest()
        count += len(block)
        result.update(block)


def file_pin(path):
    with Path(path).open("rb") as stream:
        size, sha256 = stream_digest(stream)
    return {"bytes": size, "sha256": sha256}


def run(*command):
    result = subprocess.run([str(item) for item in command], cwd=ROOT, check=True,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    return result.stdout


def source_commit(value=None):
    if value is None:
        value = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                               text=True, stdout=subprocess.PIPE).stdout.strip()
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValueError("Expected exact lowercase repository commit")
    return value


def verify_source_manifest(path):
    document = ET.parse(path).getroot()
    if (document.tag != "manifest" or document.get("package") != APP_ID
            or document.get(ANDROID + "versionName") != VERSION_NAME
            or document.get(ANDROID + "versionCode") != str(VERSION_CODE)
            or document.get(ANDROID + "sharedUserId") is not None):
        raise ValueError("Source manifest identity mismatch")
    sdk = document.findall("uses-sdk")
    if (len(sdk) != 1 or sdk[0].get(ANDROID + "minSdkVersion") != "26"
            or sdk[0].get(ANDROID + "targetSdkVersion") != "35"):
        raise ValueError("Source manifest SDK mismatch")
    permissions = [element.get(ANDROID + "name") for element in document
                   if element.tag.startswith("uses-permission")]
    if len(permissions) != len(PERMISSIONS) or set(permissions) != PERMISSIONS:
        raise ValueError("Import-only application permissions differ from the offline import contract")
    applications = document.findall("application")
    if len(applications) != 1:
        raise ValueError("Source manifest application missing")
    application = applications[0]
    if application.get(ANDROID + "hasCode") == "false":
        raise ValueError("Source application must contain Java code")
    launchers = []
    for activity in application.findall("activity"):
        for intent in activity.findall("intent-filter"):
            actions = {element.get(ANDROID + "name") for element in intent.findall("action")}
            categories = {element.get(ANDROID + "name") for element in intent.findall("category")}
            if ("android.intent.action.MAIN" in actions
                    and "android.intent.category.LAUNCHER" in categories):
                name = activity.get(ANDROID + "name", "")
                if name.startswith("."):
                    name = APP_ID + name
                launchers.append((name, activity.get(ANDROID + "exported")))
    if launchers != [(LAUNCHER, "true")]:
        raise ValueError("Source manifest launcher mismatch")


def verify_badging(text):
    packages = re.findall(r"^package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", text, re.M)
    if packages != [(APP_ID, str(VERSION_CODE), VERSION_NAME)]:
        raise ValueError("APK package/version mismatch")
    minimum = re.findall(r"^(?:minSdkVersion|sdkVersion):'([^']+)'$", text, re.M)
    target = re.findall(r"^targetSdkVersion:'([^']+)'$", text, re.M)
    if not minimum or set(minimum) != {"26"} or target != ["35"]:
        raise ValueError("APK SDK mismatch")
    if re.search(r"^native-code:", text, re.M):
        raise ValueError("Import-only APK must not contain native code")
    permissions = re.findall(r"^uses-permission(?:-[^:]*)?: name='([^']+)'", text, re.M)
    if len(permissions) != len(PERMISSIONS) or set(permissions) != PERMISSIONS:
        raise ValueError("Import-only APK permissions differ from the offline import contract")
    launchers = re.findall(r"^launchable-activity: name='([^']+)'", text, re.M)
    if launchers != [LAUNCHER]:
        raise ValueError("APK launcher mismatch")


def payloads(assets, commit):
    from package_game_import import verify_package

    assets = Path(assets)
    contract = verify_package(assets, repository_commit=source_commit(commit))
    members = []
    pins = {}
    property_prefixes = {"atlas-text.zip": "text.archive", "atlas-text-index.tsv": "text.index",
                         "atlas-assets-index.tsv": "asset.index"}
    for name in sorted(PAYLOAD_NAMES):
        path = assets / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Missing or linked APK payload: " + name)
        pin = file_pin(path)
        prefix = property_prefixes.get(name)
        if prefix and (str(pin["bytes"]) != str(contract[prefix + ".bytes"])
                       or pin["sha256"] != contract[prefix + ".sha256"]):
            raise ValueError("APK payload changed after verification: " + name)
        member = "assets/atlas/" + name
        members.append((path, member))
        pins[member] = pin
    return contract, members, pins


def append_payloads(archive, members):
    for path, member in members:
        # atlas-text.zip is already compressed and may be hundreds of MB.
        # ZipFile.write streams it; do not read the complete payload into RAM.
        compression = zipfile.ZIP_STORED if path.name == "atlas-text.zip" else zipfile.ZIP_DEFLATED
        archive.write(path, member, compress_type=compression)


def verify_packaged_payloads(apk, expected):
    if set(expected) != {"assets/atlas/" + name for name in PAYLOAD_NAMES}:
        raise ValueError("Expected payload set mismatch")
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("APK contains duplicate members")
        if "classes.dex" not in names:
            raise ValueError("APK DEX missing")
        if any(name.startswith("lib/") for name in names):
            raise ValueError("Import-only APK must not contain native libraries")
        actual_assets = {name for name in names if name.startswith("assets/")}
        if actual_assets != set(expected):
            raise ValueError("APK payload set mismatch")
        if archive.getinfo("assets/atlas/atlas-text.zip").compress_type != zipfile.ZIP_STORED:
            raise ValueError("Text ZIP must be stored without APK recompression")
        for member, pin in expected.items():
            # Reading to EOF also checks the archive member CRC.
            with archive.open(member) as stream:
                size, sha256 = stream_digest(stream)
            if {"bytes": size, "sha256": sha256} != pin:
                raise ValueError("Packaged payload changed: " + member)
        if archive.testzip() is not None:
            raise ValueError("APK ZIP verification failed")
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--android-jar", type=Path, required=True)
    parser.add_argument("--build-tools", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--repository-commit")
    parser.add_argument("--keystore", type=Path, required=True)
    parser.add_argument("--alias", default="coh-atlas-setup")
    parser.add_argument("--output", type=Path, default=ROOT / "out/android-atlas" / APK_NAME)
    args = parser.parse_args()
    for key in ("android_jar", "build_tools", "assets", "keystore", "output"):
        setattr(args, key, getattr(args, key).resolve())
    commit = source_commit(args.repository_commit)
    contract, members, payload_pins = payloads(args.assets, commit)
    main_dir = ROOT / "android/atlas/src/main"
    verify_source_manifest(main_dir / "AndroidManifest.xml")
    for path in [args.android_jar, args.build_tools / "aapt2", args.build_tools / "zipalign",
                 args.build_tools / "lib/d8.jar", args.build_tools / "lib/apksigner.jar"]:
        if not path.is_file():
            raise FileNotFoundError("Missing Android build tool: " + str(path))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="coh-atlas-apk-", dir=args.output.parent) as temp:
        work = Path(temp)
        classes, generated, dex = work / "classes", work / "generated", work / "dex"
        for folder in (classes, generated, dex):
            folder.mkdir()
        resources, unsigned, aligned, signed = (work / name for name in (
            "resources.zip", "unsigned.apk", "aligned.apk", "signed.apk"))
        run(args.build_tools / "aapt2", "compile", "--dir", main_dir / "res", "-o", resources)
        run(args.build_tools / "aapt2", "link", "-I", args.android_jar, "--manifest", main_dir / "AndroidManifest.xml",
            "--min-sdk-version", "26", "--target-sdk-version", "35", "--java", generated, resources, "-o", unsigned)
        sources = sorted((main_dir / "java").rglob("*.java")) + sorted(generated.rglob("*.java"))
        run("java", "-m", "jdk.compiler/com.sun.tools.javac.Main", "--release", "8", "-cp", args.android_jar, "-d", classes, *sources)
        class_jar = work / "classes.jar"
        with zipfile.ZipFile(class_jar, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(classes.rglob("*.class")):
                archive.write(path, path.relative_to(classes).as_posix())
        run("java", "-cp", args.build_tools / "lib/d8.jar", "com.android.tools.r8.D8", "--min-api", "26",
            "--lib", args.android_jar, "--output", dex, class_jar)
        with zipfile.ZipFile(unsigned, "a", zipfile.ZIP_DEFLATED) as archive:
            append_payloads(archive, members)
            for path in sorted(dex.glob("*.dex")):
                archive.write(path, path.name)
        run(args.build_tools / "zipalign", "-f", "4", unsigned, aligned)
        generated_key = not args.keystore.exists()
        if generated_key:
            args.keystore.parent.mkdir(parents=True, exist_ok=True)
            run("keytool", "-genkeypair", "-keystore", args.keystore, "-storepass", "android", "-keypass", "android",
                "-alias", args.alias, "-keyalg", "RSA", "-keysize", "3072", "-validity", "3650",
                "-dname", "CN=COH Atlas Setup Ephemeral CI, O=Russianranger")
        run("java", "-jar", args.build_tools / "lib/apksigner.jar", "sign", "--ks", args.keystore,
            "--ks-key-alias", args.alias, "--ks-pass", "pass:android", "--key-pass", "pass:android", "--out", signed, aligned)
        verification = run("java", "-jar", args.build_tools / "lib/apksigner.jar", "verify", "--verbose", "--print-certs", signed)
        certificate = re.search(r"^Signer #1 certificate SHA-256 digest:\s*([0-9a-fA-F]{64})$", verification, re.M)
        if not certificate:
            raise ValueError("No verified signer certificate")
        run(args.build_tools / "zipalign", "-c", "4", signed)
        badging = run(args.build_tools / "aapt2", "dump", "badging", signed)
        verify_badging(badging)
        verify_packaged_payloads(signed, payload_pins)
        shutil.copyfile(signed, args.output)
        report = {
            "format": 1, "apk": args.output.name, **file_pin(args.output),
            "application_id": APP_ID, "version_name": VERSION_NAME, "version_code": VERSION_CODE,
            "min_sdk": 26, "target_sdk": 35, "abi": "java_only", "permissions": sorted(PERMISSIONS),
            "repository_commit": commit, "bundle_contract": contract,
            "payloads": payload_pins, "signature_verified": True,
            "signer_certificate_sha256": certificate.group(1).lower(),
            "signing_key_created": generated_key,
            "signing": "Development/ephemeral CI certificate; not a stable release/update signing identity",
            "package_badging_verified": True, "badging": badging,
            "payload_bytes_verified": True, "device_validated": False, "gameplay_validated": False,
            "candidate_role": "physical_thor_verified_asset_import_only",
            "scope": "Imports and verifies reviewed data only; no server, game client, or runtime launch",
            "installation": "Separate application ID preserves the accepted diagnostics and their private data",
        }
        (args.output.parent / "atlas-apk-build-report.json").write_text(json.dumps(report, indent=2) + "\n")
        args.output.with_suffix(".apk.sha256").write_text(report["sha256"] + "  " + args.output.name + "\n")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as failure:
        if failure.stdout:
            print(failure.stdout)
        raise
