#!/usr/bin/env python3
"""Build the separate interactive graphical client test from accepted donors.

JDK 17 and SDK 35 build the small Java shell. The accepted ARM64 runtime and
qualified client are streamed into the APK and checked again after signing.
This is a development candidate; Android execution and gameplay are not inferred
from successful packaging.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP_ID = "io.github.russianranger.cohclientinteractive"
LAUNCHER = APP_ID + ".ClientActivity"
VERSION_NAME = "0.9.0"
VERSION_CODE = 4
APK_NAME = f"COH-Character-Creation-{VERSION_NAME}.apk"
ANDROID = "{http://schemas.android.com/apk/res/android}"
NATIVE_NAMES = frozenset({"libproot.so", "libproot-loader.so"})
NATIVE_MEMBERS = frozenset("lib/arm64-v8a/" + name for name in NATIVE_NAMES)
HELPERS = ("TarExtractor", "DeviceHosts", "DiagnosticOutcome", "DiagnosticReports", "CleanupGuard", "DiagnosticRuntime", "DbServerAcceptance")
STREAM_BLOCK = 1024 * 1024
PERMISSIONS = frozenset("android.permission." + name for name in (
    "INTERNET", "FOREGROUND_SERVICE", "FOREGROUND_SERVICE_DATA_SYNC", "POST_NOTIFICATIONS", "WAKE_LOCK"))


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


def verify_runtime_assets(assets, repository_commit=None):
    module = load_tool("interactive_device_assets", ROOT / "tools/android/interactive/prepare_assets.py")
    return module.verify_device_assets(assets, repository_commit=repository_commit)


IMPORT_NAMES = frozenset({'atlas-import.properties','atlas-text.zip','atlas-text-index.tsv','atlas-assets-index.tsv'})
IMPORT_COMMIT = 'e30c0b58b0e53534f92e77cdb7b8b93fe3ddc5ce'
IMPORT_RECEIPT = ROOT/'docs/android-evidence/atlas-test-apk-build-36638344040.json'
IMPORT_RECEIPT_SHA256 = '39f4e75aa947d5519e42d176d756c317adae21ed18ea03fcdeb155b6bb7535ea'


def accepted_import_receipt():
    if file_pin(IMPORT_RECEIPT)['sha256'] != IMPORT_RECEIPT_SHA256:
        raise ValueError('Accepted Atlas import receipt changed')
    document=json.loads(IMPORT_RECEIPT.read_text())
    if document['repository_commit'] != IMPORT_COMMIT: raise ValueError('Wrong Atlas donor commit')
    return document


def accepted_import_pins():
    return {name:pin for name,pin in accepted_import_receipt()['payloads'].items() if name.startswith('assets/atlas/')}


def import_donor():
    receipt=accepted_import_receipt()
    return {'run_id':36638344040,'repository_commit':IMPORT_COMMIT,
            'apk_sha256':receipt['sha256'],'apk_bytes':receipt['bytes'],
            'build_receipt_sha256':IMPORT_RECEIPT_SHA256,'payloads':accepted_import_pins()}


def verify_import_package(directory):
    directory=Path(directory)
    if directory.is_symlink() or not directory.is_dir() or {p.name for p in directory.iterdir()} != IMPORT_NAMES:
        raise ValueError('Expected exact four-file accepted import bundle')
    for member,pin in accepted_import_pins().items(): checked_file(directory/Path(member).name,pin)
    properties={}
    for line in (directory/'atlas-import.properties').read_text().splitlines():
        if line.count('=') != 1: raise ValueError('Malformed import contract')
        key,value=line.split('=',1)
        if key in properties: raise ValueError('Duplicate import contract key')
        properties[key]=value
    expected=accepted_import_receipt()['bundle_contract']
    if properties != {key:str(value) for key,value in expected.items()}:
        raise ValueError('Exact accepted import contract differs')
    return expected


def extract_import_donor(apk, output):
    apk,output=Path(apk),Path(output); expected=accepted_import_receipt()
    if checked_file(apk) != {'bytes':expected['bytes'],'sha256':expected['sha256']}:
        raise ValueError('Accepted Atlas APK bytes differ')
    if output.exists(): raise ValueError('Fresh import extraction required')
    output.mkdir(parents=True)
    with zipfile.ZipFile(apk) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())): raise ValueError('Duplicate APK member')
        for member in accepted_import_pins():
            with archive.open(member) as source,(output/Path(member).name).open('xb') as target:
                shutil.copyfileobj(source,target,1024*1024)
    return verify_import_package(output)


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
        raise ValueError("Interactive client test permissions differ from the contract")
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
            or services[0].get(ANDROID + "foregroundServiceType") != "dataSync"
            or services[0].get(ANDROID + "name") != APP_ID + ".ClientService"):
        raise ValueError("Expected one private data-sync foreground service")
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
        raise ValueError("Interactive client test APK permissions differ from the contract")
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


def payloads(runtime_assets, native, commit, import_assets):
    commit = source_commit(commit)
    runtime_assets, native = Path(runtime_assets), Path(native)
    for directory in (runtime_assets, native, native / "arm64-v8a"):
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("Missing or linked APK payload directory")
    manifest_pin = checked_file(runtime_assets / "runtime-manifest.json")
    runtime = verify_runtime_assets(runtime_assets, repository_commit=commit)
    if (runtime.get("format") != 1 or runtime.get("repository_commit") != commit
            or not isinstance(runtime.get("files"), dict) or not runtime["files"]):
        raise ValueError("Runtime manifest lacks the exact candidate commit/files")
    members, pins = [], {}

    def add(path, member, expected=None):
        pins[member] = checked_file(path, expected)
        members.append((path, member))

    import_contract = verify_import_package(import_assets)
    for name in sorted(IMPORT_NAMES):
        add(Path(import_assets)/name, "assets/atlas/"+name, accepted_import_pins()["assets/atlas/"+name])
    for name, pin in sorted(runtime["files"].items()):
        if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", name)
                or name in (".", "..", "runtime-manifest.json")):
            raise ValueError("Unsafe runtime member")
        add(runtime_assets / name, "assets/runtime/" + name, pin)
    add(runtime_assets / "runtime-manifest.json", "assets/runtime/runtime-manifest.json",
        manifest_pin)
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
    return runtime, members, pins


def is_precompressed(member):
    return member.startswith("assets/") and member.endswith((".zip", ".gz", ".xz", ".bz2", ".zst"))


def append_payloads(archive, members):
    for path, member in members:
        # ZipFile.write streams. Do not load the hundreds of MB of data/runtime
        # into memory or recompress an archive that is already compressed.
        compression = zipfile.ZIP_STORED if is_precompressed(member) else zipfile.ZIP_DEFLATED
        archive.write(path, member, compress_type=compression)


def verify_packaged_payloads(apk, expected):
    if ({name for name in expected if name.startswith("lib/")} != NATIVE_MEMBERS
            or "assets/runtime/runtime-manifest.json" not in expected
            or any(not name.startswith(("assets/runtime/", "assets/atlas/", "lib/arm64-v8a/")) for name in expected)):
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
    application_sources = sorted((main_dir / "java").rglob("*.java"))
    if not any(path.name == "InteractiveRfbClient.java" for path in application_sources):
        raise ValueError("Interactive RFB client source missing")
    for path in application_sources:
        declarations = re.findall(r"^package\s+([A-Za-z0-9_.]+)\s*;", path.read_text(), re.M)
        if len(declarations) != 1 or not (declarations[0] == APP_ID or declarations[0].startswith(APP_ID + ".")):
            raise ValueError("Interactive Java source package differs: " + path.name)
    sources = application_sources + sorted(generated.rglob("*.java"))
    sources.append(ROOT / "android/atlas/src/main/java/io/github/russianranger/cohatlas/AtlasAssetImporter.java")
    diagnostic = ROOT / "android/app/src/main/java/io/github/russianranger/cohdiagnostic"
    sources.extend(diagnostic / (name + ".java") for name in HELPERS)
    if len(sources) != len(set(sources)) or any(not path.is_file() or path.is_symlink() for path in sources):
        raise ValueError("Missing, linked or duplicated Java source")
    return sources


def signing_password_spec(environment_name=None, password_file=None):
    if environment_name is not None and password_file is not None:
        raise ValueError("Use one signing password source")
    if password_file is not None:
        path = Path(password_file).absolute()
        if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 4096:
            raise ValueError("Missing, linked or oversized signing password file")
        return "file:" + str(path)
    name = environment_name or "COH_INTERACTIVE_KEYSTORE_PASSWORD"
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) or not os.environ.get(name):
        raise ValueError("Signing password environment variable is missing or invalid")
    return "env:" + name


def verify_signing_identity(keystore, alias, expected_certificate, password_spec):
    """Require the retained key; this builder never creates or replaces one."""
    keystore = Path(keystore)
    if keystore.is_symlink() or not keystore.is_file() or not 0 < keystore.stat().st_size <= 1024*1024:
        raise ValueError("Existing regular retained signing keystore required")
    if alias != "coh-client-interactive" or not re.fullmatch(r"[0-9a-f]{64}", expected_certificate):
        raise ValueError("Expected retained signing alias and lowercase certificate SHA-256")
    kind, value = password_spec.split(":", 1)
    if kind not in ("env", "file") or not value:
        raise ValueError("Signing password must use an environment variable or file")
    with tempfile.TemporaryDirectory(prefix="coh-interactive-certificate-") as temporary:
        certificate = Path(temporary)/"certificate.der"
        run("keytool", "-exportcert", "-keystore", keystore, "-alias", alias,
            "-storepass:" + kind, value, "-file", certificate)
        actual = file_pin(certificate)["sha256"]
    if actual != expected_certificate:
        raise ValueError("Retained signing certificate differs from expected identity")
    return actual


def verify_signer_output(verification, expected_certificate):
    signers = re.findall(r"^Signer #(\d+) certificate SHA-256 digest:\s*([0-9a-fA-F]{64})$", verification, re.M)
    signers = [(number, digest.lower()) for number, digest in signers]
    if signers != [("1", expected_certificate)]:
        raise ValueError("APK signer differs from the retained certificate identity")
    return expected_certificate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--android-jar", type=Path, required=True)
    parser.add_argument("--build-tools", type=Path, required=True)
    parser.add_argument("--runtime-assets", type=Path, required=True)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--import-assets", type=Path, required=True)
    parser.add_argument("--repository-commit")
    parser.add_argument("--keystore", type=Path, required=True)
    parser.add_argument("--alias", choices=("coh-client-interactive",), default="coh-client-interactive")
    parser.add_argument("--expected-cert-sha256", required=True)
    password = parser.add_mutually_exclusive_group()
    password.add_argument("--password-env", default=None)
    password.add_argument("--password-file", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "out/android-interactive" / APK_NAME)
    args = parser.parse_args()
    for key in ("android_jar", "build_tools", "runtime_assets", "import_assets", "native", "keystore", "output"):
        setattr(args, key, getattr(args, key).absolute())
    commit = source_commit(args.repository_commit)
    password_spec = signing_password_spec(args.password_env, args.password_file)
    verify_signing_identity(args.keystore, args.alias, args.expected_cert_sha256, password_spec)
    runtime, members, payload_pins = payloads(args.runtime_assets, args.native, commit, args.import_assets)
    main_dir = ROOT / "android/interactive/src/main"
    verify_source_manifest(main_dir / "AndroidManifest.xml")
    for path in [args.android_jar, args.build_tools / "aapt2", args.build_tools / "zipalign",
                 args.build_tools / "lib/d8.jar", args.build_tools / "lib/apksigner.jar"]:
        if not path.is_file():
            raise FileNotFoundError("Missing Android build tool: " + str(path))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="coh-interactive-apk-", dir=args.output.parent) as temp:
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
        run("java", "-jar", args.build_tools / "lib/apksigner.jar", "sign", "--ks", args.keystore,
            "--ks-key-alias", args.alias, "--ks-pass", password_spec, "--key-pass", password_spec, "--out", signed, aligned)
        verification = run("java", "-jar", args.build_tools / "lib/apksigner.jar", "verify", "--verbose", "--print-certs", signed)
        certificate = verify_signer_output(verification, args.expected_cert_sha256)
        run(args.build_tools / "zipalign", "-c", "4", signed)
        badging = run(args.build_tools / "aapt2", "dump", "badging", signed)
        verify_badging(badging)
        verify_packaged_payloads(signed, payload_pins)
        shutil.copyfile(signed, args.output)
        report = {
            "format": 1, "apk": args.output.name, **file_pin(args.output),
            "application_id": APP_ID, "version_name": VERSION_NAME, "version_code": VERSION_CODE,
            "min_sdk": 26, "target_sdk": 35, "abi": "arm64-v8a", "permissions": sorted(PERMISSIONS),
            "repository_commit": commit, "bundle_contract": runtime["client_bundle"],
            "import_donor": import_donor(), "import_contract": verify_import_package(args.import_assets),
            "runtime_manifest_sha256": payload_pins["assets/runtime/runtime-manifest.json"]["sha256"],
            "runtime_manifest": runtime, "payloads": payload_pins, "java_sources": source_pins,
            "native_launcher_source": {"android/native/client-launcher.c": file_pin(ROOT/"android/native/client-launcher.c")},
            "signature_verified": True, "signer_certificate_sha256": certificate,
            "signing_key_created": False,
            "signing": "Retained CI development identity; certificate pinned before and after signing",
            "signing_alias": args.alias, "expected_signer_certificate_sha256": args.expected_cert_sha256,
            "package_badging_verified": True, "badging": badging,
            "payload_bytes_verified": True, "device_validated": False, "gameplay_validated": False,
            "candidate_role": "physical_thor_actual_character_creation_test",
            "scope": "Pinned CityOfHeroes graphical character creation with persistent DbServer profile and accepted MapServer; device character creation and gameplay remain unvalidated",
            "installation": "In-place update to Client Interaction with the retained signing identity. Reuses imported assets, Wine prefix, and client caches; starts persistent local PostgreSQL and DbServer.",
        }
        (args.output.parent / "interactive-apk-build-report.json").write_text(json.dumps(report, indent=2) + "\n")
        args.output.with_suffix(".apk.sha256").write_text(report["sha256"] + "  " + args.output.name + "\n")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as failure:
        if failure.stdout:
            print(failure.stdout)
        raise
