#!/usr/bin/env python3
"""Build and verify the dependency-free diagnostic APK with JDK 17 and SDK 35."""
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
ROOT = Path(__file__).resolve().parents[2]
APP_ID = "io.github.russianranger.cohdiagnostic.m3"
JAVA_PACKAGE = "io.github.russianranger.cohdiagnostic"
VERSION_NAME = "0.2.0"
VERSION_CODE = 7
APK_NAME = f"COH-Server-Test-{VERSION_NAME}.apk"
ANDROID = "{http://schemas.android.com/apk/res/android}"

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def run(*command):
    result = subprocess.run([str(x) for x in command], cwd=ROOT, check=True,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    return result.stdout

def verify_badging(text):
    package = re.search(r"^package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", text, re.M)
    if not package or package.groups() != (APP_ID, str(VERSION_CODE), VERSION_NAME):
        raise ValueError("APK package/version mismatch")
    # SDK 35 aapt2 uses minSdkVersion; older aapt2 called it sdkVersion.
    minimum = re.findall(r"^(?:minSdkVersion|sdkVersion):'([^']+)'$", text, re.M)
    target = re.findall(r"^targetSdkVersion:'([^']+)'$", text, re.M)
    if not minimum or set(minimum) != {"26"} or target != ["35"]:
        raise ValueError("APK SDK mismatch")
    native = re.search(r"^native-code:\s*(.*)$", text, re.M)
    if not native or native.group(1).strip() != "'arm64-v8a'":
        raise ValueError("APK must contain only ARM64 libraries")
    if not re.search(r"^launchable-activity: name='" + re.escape(JAVA_PACKAGE) + r"\.MainActivity'", text, re.M):
        raise ValueError("APK launcher missing")

def payloads(assets, native):
    # The candidate packages the qualified real DbServer in addition to the
    # byte-identical accepted M2 runtime. Validate both before signing the APK.
    import sys
    sys.path.insert(0, str(ROOT / "tools/android/dbserver"))
    from prepare_device_assets import verify_device_assets
    verify_device_assets(assets / "runtime")
    manifest = json.loads((assets / "runtime/runtime-manifest.json").read_text())
    if manifest.get("format") != 1 or not re.fullmatch(r"[0-9a-f]{40}", manifest.get("repository_commit", "")):
        raise ValueError("Runtime manifest lacks exact source commit")
    for name, pin in manifest["files"].items():
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            raise ValueError("Unsafe runtime member")
        path = assets / "runtime" / name
        if not path.is_file() or path.stat().st_size != pin["bytes"] or digest(path) != pin["sha256"]:
            raise ValueError("Runtime asset differs from manifest: " + name)
    members = [(assets / "runtime" / name, "assets/runtime/" + name)
               for name in sorted([*manifest["files"], "runtime-manifest.json"])]
    # Build receipts, corresponding sources and licenses remain separate CI artifacts.
    libraries = [native / "arm64-v8a" / name for name in ("libproot.so", "libproot-loader.so")]
    if any(not p.is_file() for p in libraries):
        raise ValueError("Expected ARM64 PRoot and its loader")
    native_receipt = json.loads((assets / "runtime/proot-build.json").read_text())
    if native_receipt.get("target") != "android-arm64":
        raise ValueError("Expected accepted Android PRoot provenance")
    for path in libraries:
        pin = native_receipt["files"][path.name]
        if path.is_symlink() or path.stat().st_size != pin["bytes"] or digest(path) != pin["sha256"]:
            raise ValueError("Native payload differs from accepted provenance: " + path.name)
        with path.open("rb") as stream:
            header = stream.read(20)
        if len(header) != 20 or header[:6] != b"\x7fELF\x02\x01" or int.from_bytes(header[18:20], "little") != 183:
            raise ValueError("Native payload is not an ARM64 ELF: " + path.name)
        members.append((path, "lib/" + path.relative_to(native).as_posix()))
    return manifest, members

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--android-jar", type=Path, required=True)
    parser.add_argument("--build-tools", type=Path, required=True)
    parser.add_argument("--keystore", type=Path, required=True)
    parser.add_argument("--alias", default="coh-diagnostic")
    parser.add_argument("--output", type=Path, default=ROOT / "out/android" / APK_NAME)
    args = parser.parse_args()
    for key in ("android_jar", "build_tools", "keystore", "output"):
        setattr(args, key, getattr(args, key).resolve())
    main_dir = ROOT / "android/app/src/main"
    assets, native = ROOT / "out/android/assets", ROOT / "out/android/native"
    manifest, members = payloads(assets, native)
    xml = ET.parse(main_dir / "AndroidManifest.xml").getroot()
    if (xml.get("package") != APP_ID or xml.get(ANDROID + "versionName") != VERSION_NAME
            or xml.get(ANDROID + "versionCode") != str(VERSION_CODE)):
        raise ValueError("Source manifest identity mismatch")
    if xml.find("application").get(ANDROID + "extractNativeLibs") != "true":
        raise ValueError("PRoot requires native extraction")
    for path in [args.android_jar, args.build_tools / "aapt2", args.build_tools / "zipalign",
                 args.build_tools / "lib/d8.jar", args.build_tools / "lib/apksigner.jar"]:
        if not path.is_file():
            raise FileNotFoundError("Missing Android build tool: " + str(path))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="coh-apk-", dir=args.output.parent) as temp:
        work = Path(temp)
        classes, generated, dex = work / "classes", work / "generated", work / "dex"
        for folder in (classes, generated, dex):
            folder.mkdir()
        resources, unsigned, aligned, signed = (work / x for x in ("resources.zip", "unsigned.apk", "aligned.apk", "signed.apk"))
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
            for path, member in members:
                archive.write(path, member)
            for path in sorted(dex.glob("*.dex")):
                archive.write(path, path.name)
        run(args.build_tools / "zipalign", "-f", "4", unsigned, aligned)
        if not args.keystore.exists():
            args.keystore.parent.mkdir(parents=True, exist_ok=True)
            run("keytool", "-genkeypair", "-keystore", args.keystore, "-storepass", "android", "-keypass", "android",
                "-alias", args.alias, "-keyalg", "RSA", "-keysize", "3072", "-validity", "3650",
                "-dname", "CN=COH Diagnostic Ephemeral CI, O=Russianranger")
        run("java", "-jar", args.build_tools / "lib/apksigner.jar", "sign", "--ks", args.keystore,
            "--ks-key-alias", args.alias, "--ks-pass", "pass:android", "--key-pass", "pass:android", "--out", signed, aligned)
        verification = run("java", "-jar", args.build_tools / "lib/apksigner.jar", "verify", "--verbose", "--print-certs", signed)
        certificate = re.search(r"^Signer #1 certificate SHA-256 digest:\s*([0-9a-fA-F]{64})$", verification, re.M)
        if not certificate:
            raise ValueError("No verified signer certificate")
        run(args.build_tools / "zipalign", "-c", "4", signed)
        verify_badging(run(args.build_tools / "aapt2", "dump", "badging", signed))
        with zipfile.ZipFile(signed) as archive:
            if archive.testzip() is not None or "classes.dex" not in archive.namelist():
                raise ValueError("APK ZIP or DEX verification failed")
            for path, member in members:
                if hashlib.sha256(archive.read(member)).hexdigest() != digest(path):
                    raise ValueError("Packaged payload changed: " + member)
        shutil.copyfile(signed, args.output)
        report = {
            "format": 1, "apk": args.output.name, "bytes": args.output.stat().st_size, "sha256": digest(args.output),
            "application_id": APP_ID, "version_name": VERSION_NAME, "version_code": VERSION_CODE,
            "min_sdk": 26, "target_sdk": 35, "abi": "arm64-v8a",
            "repository_commit": manifest["repository_commit"], "runtime_manifest_sha256": digest(assets / "runtime/runtime-manifest.json"),
            "signature_verified": True, "signer_certificate_sha256": certificate.group(1).lower(),
            "signing": "Ephemeral CI certificate; not a stable release/update signing identity",
            "package_badging_verified": True, "payload_bytes_verified": True,
            "device_validated": False, "gameplay_validated": False,
            "candidate_role": "physical_thor_real_dbserver_test",
            "installation": "Side-by-side application ID preserves the accepted 0.1.5 diagnostic and its private runtime",
            "device_dbserver": manifest["dbserver_device_bundle"],
        }
        (args.output.parent / "apk-build-report.json").write_text(json.dumps(report, indent=2) + "\n")
        args.output.with_suffix(".apk.sha256").write_text(report["sha256"] + "  " + args.output.name + "\n")
        print(json.dumps(report, indent=2))

if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as failure:
        if failure.stdout:
            print(failure.stdout)
        raise
