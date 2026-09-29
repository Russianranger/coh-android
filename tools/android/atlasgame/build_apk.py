#!/usr/bin/env python3
"""Build the separate Atlas Park server test APK from verified data and runtime.

JDK 17 and SDK 35 build the small Java shell. Reviewed import payloads and the
accepted ARM64 runtime are streamed into the APK and checked again after signing.
This is a development candidate; Android execution and gameplay are not inferred
from successful packaging.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP_ID = "io.github.russianranger.cohatlastest"
LAUNCHER = APP_ID + ".AtlasActivity"
VERSION_NAME = "0.4.0"
VERSION_CODE = 1
APK_NAME = f"COH-Atlas-Test-{VERSION_NAME}.apk"
ANDROID = "{http://schemas.android.com/apk/res/android}"
IMPORT_NAMES = frozenset({"atlas-import.properties", "atlas-text.zip",
                          "atlas-text-index.tsv", "atlas-assets-index.tsv"})
NATIVE_NAMES = frozenset({"libproot.so", "libproot-loader.so"})
NATIVE_MEMBERS = frozenset("lib/arm64-v8a/" + name for name in NATIVE_NAMES)
HELPERS = ("TarExtractor", "DeviceHosts", "DiagnosticOutcome", "DiagnosticReports", "CleanupGuard")
STREAM_BLOCK = 1024 * 1024
PERMISSIONS = frozenset("android.permission." + name for name in (
    "INTERNET", "FOREGROUND_SERVICE", "FOREGROUND_SERVICE_SPECIAL_USE", "POST_NOTIFICATIONS", "WAKE_LOCK"))


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


def load_tool(name, path):
    """Avoid name collisions with the accepted DbServer packaging tools."""
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            del sys.modules[name]
            raise
    return sys.modules[name]


def verify_import_package(assets, commit):
    module = load_tool("atlas_game_import_package", ROOT / "tools/android/atlas/package_game_import.py")
    return module.verify_package(assets, repository_commit=commit)


def verify_runtime_assets(assets):
    module = load_tool("atlas_game_device_assets", ROOT / "tools/android/atlasgame/prepare_device_assets.py")
    return module.verify_device_assets(assets)


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
        raise ValueError("Atlas server test permissions differ from the contract")
    applications = document.findall("application")
    if len(applications) != 1:
        raise ValueError("Source manifest application missing")
    application = applications[0]
    if application.get(ANDROID + "hasCode") == "false":
        raise ValueError("Source application must contain Java code")
    if application.get(ANDROID + "extractNativeLibs") != "true":
        raise ValueError("PRoot requires native extraction")
    if application.get(ANDROID + "allowBackup") != "false":
        raise ValueError("Private test state must disable automatic backup")
    services = application.findall("service")
    if (len(services) != 1 or services[0].get(ANDROID + "exported") != "false"
            or services[0].get(ANDROID + "foregroundServiceType") != "specialUse"):
        raise ValueError("Expected one private special-use foreground service")
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
    native = re.findall(r"^native-code:\s*(.*)$", text, re.M)
    if native != ["'arm64-v8a'"]:
        raise ValueError("APK must contain only ARM64 libraries")
    permissions = re.findall(r"^uses-permission(?:-[^:]*)?: name='([^']+)'", text, re.M)
    if len(permissions) != len(PERMISSIONS) or set(permissions) != PERMISSIONS:
        raise ValueError("Atlas server test APK permissions differ from the contract")
    launchers = re.findall(r"^launchable-activity: name='([^']+)'", text, re.M)
    if launchers != [LAUNCHER]:
        raise ValueError("APK launcher mismatch")


def checked_pin(record):
    if (not isinstance(record, dict) or type(record.get("bytes")) is not int or record["bytes"] < 0
            or not isinstance(record.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])):
        raise ValueError("Invalid payload provenance")
    return {"bytes": record["bytes"], "sha256": record["sha256"]}


def checked_file(path, pin=None):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing or linked APK payload: " + path.name)
    actual = file_pin(path)
    if pin is not None and actual != checked_pin(pin):
        raise ValueError("APK payload changed after verification: " + path.name)
    return actual


def payloads(assets, runtime_assets, native, commit):
    commit = source_commit(commit)
    assets, runtime_assets, native = Path(assets), Path(runtime_assets), Path(native)
    for directory in (assets, runtime_assets, native, native / "arm64-v8a"):
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("Missing or linked APK payload directory")
    metadata_pins = {"assets/atlas/atlas-import.properties": checked_file(assets / "atlas-import.properties"),
                     "assets/runtime/runtime-manifest.json": checked_file(runtime_assets / "runtime-manifest.json")}
    contract = verify_import_package(assets, commit)
    runtime = verify_runtime_assets(runtime_assets)
    if contract.get("repository.commit") != commit:
        raise ValueError("Import contract lacks the exact candidate commit")
    if (runtime.get("format") != 1 or runtime.get("repository_commit") != commit
            or not isinstance(runtime.get("files"), dict) or not runtime["files"]):
        raise ValueError("Runtime manifest lacks the exact candidate commit/files")
    members, pins = [], {}

    def add(path, member, expected=None):
        pins[member] = checked_file(path, expected)
        members.append((path, member))

    for name in sorted(IMPORT_NAMES):
        prefix = {"atlas-text.zip": "text.archive", "atlas-text-index.tsv": "text.index",
                  "atlas-assets-index.tsv": "asset.index"}.get(name)
        expected = metadata_pins["assets/atlas/" + name] if prefix is None else {
            "bytes": int(contract[prefix + ".bytes"]), "sha256": contract[prefix + ".sha256"]}
        add(assets / name, "assets/atlas/" + name, expected)
    for name, pin in sorted(runtime["files"].items()):
        if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", name)
                or name in (".", "..", "runtime-manifest.json")):
            raise ValueError("Unsafe runtime member")
        add(runtime_assets / name, "assets/runtime/" + name, pin)
    add(runtime_assets / "runtime-manifest.json", "assets/runtime/runtime-manifest.json",
        metadata_pins["assets/runtime/runtime-manifest.json"])
    receipt_path = runtime_assets / "proot-build.json"
    if ("proot-build.json" not in runtime["files"] or receipt_path.is_symlink()
            or not receipt_path.is_file() or receipt_path.stat().st_size > 1024 * 1024):
        raise ValueError("Missing accepted Android PRoot provenance")
    receipt_bytes = receipt_path.read_bytes()
    if {"bytes": len(receipt_bytes), "sha256": hashlib.sha256(receipt_bytes).hexdigest()} != pins["assets/runtime/proot-build.json"]:
        raise ValueError("Android PRoot provenance changed after verification")
    receipt = json.loads(receipt_bytes)
    if receipt.get("target") != "android-arm64":
        raise ValueError("Expected accepted Android PRoot provenance")
    for name in sorted(NATIVE_NAMES):
        path = native / "arm64-v8a" / name
        add(path, "lib/arm64-v8a/" + name, receipt["files"][name])
        with path.open("rb") as stream:
            header = stream.read(20)
        if len(header) != 20 or header[:6] != b"\x7fELF\x02\x01" or int.from_bytes(header[18:20], "little") != 183:
            raise ValueError("Native payload is not an ARM64 ELF: " + name)
    return contract, runtime, members, pins


def is_precompressed(member):
    return member.startswith("assets/") and member.endswith((".zip", ".gz", ".xz", ".bz2", ".zst"))


def append_payloads(archive, members):
    for path, member in members:
        # ZipFile.write streams. Do not load the hundreds of MB of data/runtime
        # into memory or recompress an archive that is already compressed.
        compression = zipfile.ZIP_STORED if is_precompressed(member) else zipfile.ZIP_DEFLATED
        archive.write(path, member, compress_type=compression)


def verify_packaged_payloads(apk, expected):
    import_members = {"assets/atlas/" + name for name in IMPORT_NAMES}
    if ({name for name in expected if name.startswith("assets/atlas/")} != import_members
            or {name for name in expected if name.startswith("lib/")} != NATIVE_MEMBERS
            or "assets/runtime/runtime-manifest.json" not in expected
            or any(not name.startswith(("assets/atlas/", "assets/runtime/", "lib/arm64-v8a/"))
                   for name in expected)):
        raise ValueError("Expected payload set mismatch")
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("APK contains duplicate members")
        if "classes.dex" not in names:
            raise ValueError("APK DEX missing")
        actual = {name for name in names if name.startswith(("assets/", "lib/"))}
        if actual != set(expected):
            raise ValueError("APK payload set mismatch")
        for member, pin in expected.items():
            if is_precompressed(member) and archive.getinfo(member).compress_type != zipfile.ZIP_STORED:
                raise ValueError("Compressed archives must be stored without APK recompression")
            # Reading to EOF validates CRC and the digest without unbounded reads.
            with archive.open(member) as stream:
                size, sha256 = stream_digest(stream)
            if {"bytes": size, "sha256": sha256} != pin:
                raise ValueError("Packaged payload changed: " + member)
        if archive.testzip() is not None:
            raise ValueError("APK ZIP verification failed")
    return expected


def java_sources(main_dir, generated):
    sources = sorted((main_dir / "java").rglob("*.java")) + sorted(generated.rglob("*.java"))
    sources.append(ROOT / "android/atlas/src/main/java/io/github/russianranger/cohatlas/AtlasAssetImporter.java")
    diagnostic = ROOT / "android/app/src/main/java/io/github/russianranger/cohdiagnostic"
    sources.extend(diagnostic / (name + ".java") for name in HELPERS)
    if len(sources) != len(set(sources)) or any(not path.is_file() or path.is_symlink() for path in sources):
        raise ValueError("Missing, linked or duplicated Java source")
    return sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--android-jar", type=Path, required=True)
    parser.add_argument("--build-tools", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--runtime-assets", type=Path, required=True)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--repository-commit")
    parser.add_argument("--keystore", type=Path, required=True)
    parser.add_argument("--alias", default="coh-atlas-test")
    parser.add_argument("--output", type=Path, default=ROOT / "out/android-atlas-game" / APK_NAME)
    args = parser.parse_args()
    for key in ("android_jar", "build_tools", "assets", "runtime_assets", "native", "keystore", "output"):
        setattr(args, key, getattr(args, key).absolute())
    commit = source_commit(args.repository_commit)
    contract, runtime, members, payload_pins = payloads(args.assets, args.runtime_assets, args.native, commit)
    main_dir = ROOT / "android/atlasgame/src/main"
    verify_source_manifest(main_dir / "AndroidManifest.xml")
    for path in [args.android_jar, args.build_tools / "aapt2", args.build_tools / "zipalign",
                 args.build_tools / "lib/d8.jar", args.build_tools / "lib/apksigner.jar"]:
        if not path.is_file():
            raise FileNotFoundError("Missing Android build tool: " + str(path))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="coh-atlas-game-apk-", dir=args.output.parent) as temp:
        work = Path(temp)
        classes, generated, dex = work / "classes", work / "generated", work / "dex"
        for folder in (classes, generated, dex):
            folder.mkdir()
        resources, unsigned, aligned, signed = (work / name for name in (
            "resources.zip", "unsigned.apk", "aligned.apk", "signed.apk"))
        run(args.build_tools / "aapt2", "compile", "--dir", main_dir / "res", "-o", resources)
        run(args.build_tools / "aapt2", "link", "-I", args.android_jar, "--manifest", main_dir / "AndroidManifest.xml",
            "--min-sdk-version", "26", "--target-sdk-version", "35", "--java", generated, resources, "-o", unsigned)
        sources = java_sources(main_dir, generated)
        source_pins = {path.relative_to(ROOT).as_posix(): file_pin(path)
                       for path in sources if path.is_relative_to(ROOT) and not path.is_relative_to(work)}
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
                "-dname", "CN=COH Atlas Test Ephemeral CI, O=Russianranger")
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
            "min_sdk": 26, "target_sdk": 35, "abi": "arm64-v8a", "permissions": sorted(PERMISSIONS),
            "repository_commit": commit, "bundle_contract": contract,
            "runtime_manifest_sha256": payload_pins["assets/runtime/runtime-manifest.json"]["sha256"],
            "runtime_manifest": runtime, "payloads": payload_pins, "java_sources": source_pins,
            "signature_verified": True, "signer_certificate_sha256": certificate.group(1).lower(),
            "signing_key_created": generated_key,
            "signing": "Development/ephemeral CI certificate; not a stable release/update signing identity",
            "package_badging_verified": True, "badging": badging,
            "payload_bytes_verified": True, "device_validated": False, "gameplay_validated": False,
            "candidate_role": "physical_thor_atlas_park_server_test",
            "scope": "Reviewed asset import and local Atlas Park server persistence test; no graphical game client",
            "installation": "Separate application ID preserves accepted apps; import the reviewed asset ZIP into this app before running",
        }
        (args.output.parent / "atlas-game-apk-build-report.json").write_text(json.dumps(report, indent=2) + "\n")
        args.output.with_suffix(".apk.sha256").write_text(report["sha256"] + "  " + args.output.name + "\n")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as failure:
        if failure.stdout:
            print(failure.stdout)
        raise
