#!/usr/bin/env python3
"""Build COH Atlas Gameplay 0.13.41: the public 0.13.36 app with the ARM64 client option.

User approval (2026-10-26, Claude lead session): build and sign this APK for the
M5 Thor play test. It is an in-place update of the installed 0.13.36 app: same
application ID and the same retained development signer, so the app's saved
character, private database, imported assets and Wine prefix are kept.

Inputs are pinned:
- the public 0.13.36 donor APK;
- the M4-qualified ARM64 client package (armport-app-client-package from M4
  run 40417983694; client/data from M3 run 40407492746);
- the retained signing identity (run 36731428735).

Changes against the donor:
- classes.dex is recompiled from this repository's app sources (0.13.36
  sources plus the reviewed M4 ARM64-option diff);
- version metadata becomes 0.13.41 / 56, and the binary manifest is checked
  to differ only in its version fields;
- stage_app_assets adds the ARM64 client, its guest helpers and the manifest
  entries, and replaces character_creation_diagnostic.py.

Every other APK member must stay byte-identical to the donor. x86 remains the
default client.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

import stage_app_assets

ROOT = Path(__file__).resolve().parents[2]
APP_ID = 'io.github.russianranger.cohclientinteractive'
ANDROID = '{http://schemas.android.com/apk/res/android}'
VERSION_NAME, VERSION_CODE = '0.13.41', 56
APK_NAME = 'COH-Atlas-Gameplay-0.13.41.apk'
DONOR_NAME = 'COH-Atlas-Gameplay-0.13.36.apk'
DONOR_RELEASE = 'coh-atlas-gameplay-v0.13.36'
DONOR_ASSET_ID = 635975286
DONOR_APK = {'bytes': 42076692, 'sha256': '14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f'}
DONOR_COMMIT = '3570430cefdb'  # release target prefix, informational
SIGNER = '92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282'
ALIAS = 'coh-client-interactive'
# The donor DEX's exact 24-source set (class list of the 0.13.36 classes.dex).
HELPERS = ('TarExtractor', 'DeviceHosts', 'DiagnosticOutcome', 'DiagnosticReports', 'CleanupGuard',
           'DiagnosticRuntime', 'DbServerAcceptance', 'AssetPackArchive', 'AssetPackStore', 'SetupMemoryGuard')
EXTRA_SOURCES = ('android/zoning/src/main/java/io/github/russianranger/cohclientinteractive/ClientZoning.java',
                 'android/recovery/src/main/java/io/github/russianranger/cohclientinteractive/ClientReports.java',
                 'android/recovery/src/main/java/io/github/russianranger/cohclientinteractive/ClientSocketRecovery.java')
# Runtime payloads the ARM64 option may add or change. Everything else is retained.
ADDED_RUNTIME = frozenset({'armport-client.zip', 'armport_client_package.py', 'armport_interactive.py',
                           'client_stdio.py'})
CHANGED_RUNTIME = frozenset({'character_creation_diagnostic.py', 'local_character_server.py', 'character_zoning.py',
                             'runtime-manifest.json', 'client-manifest.json'})
REVIEWED_JAVA_CHANGES = frozenset({
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientAcceptance.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientActivity.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientRuntime.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientService.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientSurface.java',
    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/InteractiveRfbClient.java'})


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest_bytes(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def pin(path):
    require(path.is_file() and not path.is_symlink(), 'Regular file required: ' + str(path))
    with path.open('rb') as stream:
        return {'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def run(*command, env=None):
    result = subprocess.run([str(part) for part in command], capture_output=True, text=True, env=env)
    require(result.returncode == 0, 'Command failed: ' + ' '.join(map(str, command[:3])) + '\n'
            + result.stdout[-2000:] + result.stderr[-2000:])
    return result.stdout


def java_sources(main_dir, generated):
    sources = sorted((main_dir / 'java').rglob('*.java'))
    for path in sources:
        packages = re.findall(r'^package\s+([A-Za-z0-9_.]+)\s*;', path.read_text(), re.M)
        require(len(packages) == 1 and (packages[0] == APP_ID or packages[0].startswith(APP_ID + '.')),
                'Unexpected Java package: ' + path.name)
    sources += sorted(generated.rglob('*.java'))
    sources.append(ROOT / 'android/atlas/src/main/java/io/github/russianranger/cohatlas/AtlasAssetImporter.java')
    diagnostic = ROOT / 'android/app/src/main/java/io/github/russianranger/cohdiagnostic'
    sources += [diagnostic / (name + '.java') for name in HELPERS]
    sources += [ROOT / name for name in EXTRA_SOURCES]
    require(len([p for p in sources if not p.is_relative_to(generated)]) == 24, 'Donor 24-source set differs')
    require(len(sources) == len(set(sources)) and all(p.is_file() and not p.is_symlink() for p in sources),
            'Missing, linked or duplicated Java source')
    return sources


def versioned_manifest(source, destination):
    tree = ET.parse(source)
    root = tree.getroot()
    require(root.tag == 'manifest' and root.get('package') == APP_ID, 'Source manifest identity differs')
    root.set(ANDROID + 'versionName', VERSION_NAME)
    root.set(ANDROID + 'versionCode', str(VERSION_CODE))
    ET.register_namespace('android', ANDROID[1:-1])
    tree.write(destination, encoding='utf-8', xml_declaration=True)


def normalized_manifest(apk, build_tools):
    output = run(build_tools / 'aapt2', 'dump', 'xmltree', apk, '--file', 'AndroidManifest.xml')
    lines = output.splitlines()
    require(sum(':versionCode(' in l for l in lines) == 1 and sum(':versionName(' in l for l in lines) == 1,
            'Binary manifest version metadata missing or duplicated')
    result = []
    for line in lines:
        line = re.sub(r' \(line=\d+\)', '', line)
        if ':versionCode(' in line or ':versionName(' in line:
            line = line.split('=')[0] + '=VERSION'
        result.append(line)
    return result


def verify_signature(apk, build_tools):
    output = run('java', '-jar', build_tools / 'lib/apksigner.jar', 'verify', '--verbose', '--print-certs', apk)
    require('Verified using v2 scheme (APK Signature Scheme v2): true' in output
            and 'Verified using v3 scheme (APK Signature Scheme v3): true' in output, 'v2/v3 signature required')
    certs = re.findall(r'Signer #1 certificate SHA-256 digest: ([0-9a-f]{64})', output)
    require(certs == [SIGNER], 'Signer certificate differs from the installed app lineage')
    return certs[0]


def members(apk):
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), 'Duplicate APK member')
        return {name: digest_bytes(archive.read(name)) for name in names if not name.endswith('/')}


def build(args):
    require(re.fullmatch('[0-9a-f]{40}', args.repository_commit), 'Exact repository commit required')
    require(pin(args.donor_apk) == DONOR_APK, 'Donor 0.13.36 APK bytes differ from the public release')
    require(args.output.name == APK_NAME and not args.output.exists(), 'Fresh output required')
    for tool in (args.android_jar, args.build_tools / 'aapt2', args.build_tools / 'zipalign',
                 args.build_tools / 'lib/d8.jar', args.build_tools / 'lib/apksigner.jar'):
        require(tool.is_file(), 'Missing Android SDK tool: ' + str(tool))
    donor_signer = verify_signature(args.donor_apk, args.build_tools)
    password = 'env:' + args.password_env
    require(os.environ.get(args.password_env), 'Signing password environment variable is empty')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    donor_members = members(args.donor_apk)
    with tempfile.TemporaryDirectory(prefix='coh-thor-apk-', dir=args.output.parent) as temporary:
        work = Path(temporary)
        # 1. Donor runtime assets, then the reviewed ARM64 staging.
        donor_runtime = work / 'donor-runtime'
        donor_runtime.mkdir()
        with zipfile.ZipFile(args.donor_apk) as archive:
            for name in donor_members:
                path = PurePosixPath(name)
                if name.startswith('assets/runtime/'):
                    require(len(path.parts) == 3 and '\\' not in name, 'Unsafe donor runtime member')
                    (donor_runtime / path.name).write_bytes(archive.read(name))
        pack = json.loads((donor_runtime / 'asset-pack-manifest.json').read_text())
        external = {name.split('/', 1)[1]: record for name, record in pack['files'].items()
                    if name.startswith('runtime/')}
        runtime_files = json.loads((donor_runtime / 'runtime-manifest.json').read_text())['files']
        require({n for n in runtime_files if not (donor_runtime / n).exists()} == set(external),
                'Unpackaged runtime payloads must be exactly the external asset-pack runtime files')
        staged = work / 'staged-runtime'
        armport = stage_app_assets.stage(donor_runtime, args.armport, staged, args.repository_commit, external)
        staged_names = {p.name for p in staged.iterdir()}
        donor_names = {p.name for p in donor_runtime.iterdir()}
        require(staged_names - donor_names == ADDED_RUNTIME and donor_names <= staged_names,
                'Unexpected runtime additions or removals: ' + repr(sorted(staged_names ^ donor_names)))
        changed = sorted(name for name in donor_names if pin(staged / name) != pin(donor_runtime / name))
        require(set(changed) <= CHANGED_RUNTIME, 'Unreviewed runtime payload changed: ' + repr(changed))
        # 2. Shell: versioned manifest, retained resources, recompiled DEX.
        manifest = work / 'AndroidManifest.xml'
        main_dir = ROOT / 'android/interactive/src/main'
        versioned_manifest(main_dir / 'AndroidManifest.xml', manifest)
        resources, unsigned = work / 'resources.zip', work / 'unsigned.apk'
        classes, generated, dex = work / 'classes', work / 'generated', work / 'dex'
        for folder in (classes, generated, dex):
            folder.mkdir()
        run(args.build_tools / 'aapt2', 'compile', '--dir', main_dir / 'res', '-o', resources)
        run(args.build_tools / 'aapt2', 'link', '-I', args.android_jar, '--manifest', manifest,
            '--min-sdk-version', '26', '--target-sdk-version', '35', '--java', generated, resources, '-o', unsigned)
        shell = members(unsigned)
        for name, record in shell.items():
            if name != 'AndroidManifest.xml':
                require(donor_members.get(name) == record, 'Android resource differs from donor: ' + name)
        sources = java_sources(main_dir, generated)
        source_pins = {p.relative_to(ROOT).as_posix(): pin(p) for p in sources if p.is_relative_to(ROOT)}
        run('java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8', '-cp', args.android_jar,
            '-d', classes, *sources)
        jar = work / 'classes.jar'
        with zipfile.ZipFile(jar, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(classes.rglob('*.class')):
                archive.write(path, path.relative_to(classes).as_posix())
        run('java', '-cp', args.build_tools / 'lib/d8.jar', 'com.android.tools.r8.D8', '--min-api', '26',
            '--lib', args.android_jar, '--output', dex, jar)
        require({p.name for p in dex.iterdir()} == {'classes.dex'}, 'Unexpected DEX output')
        # 3. Assemble: donor non-shell members (runtime from staging), new DEX.
        with zipfile.ZipFile(args.donor_apk) as donor, zipfile.ZipFile(unsigned, 'a') as archive:
            for info in donor.infolist():
                name = info.filename
                if (name in shell or name == 'classes.dex' or name.startswith('META-INF/')
                        or name.startswith('assets/runtime/') or name.endswith('/')):
                    continue
                archive.writestr(info, donor.read(name), compress_type=info.compress_type)
            runtime_compression = {i.filename: i.compress_type for i in donor.infolist()}
            for path in sorted(staged.iterdir()):
                name = 'assets/runtime/' + path.name
                compress = runtime_compression.get(name, zipfile.ZIP_STORED if path.suffix == '.zip'
                                                   else zipfile.ZIP_DEFLATED)
                archive.write(path, name, compress_type=compress)
            archive.write(dex / 'classes.dex', 'classes.dex', compress_type=zipfile.ZIP_DEFLATED)
        aligned, signed = work / 'aligned.apk', work / 'signed.apk'
        run(args.build_tools / 'zipalign', '-f', '-p', '4', unsigned, aligned)
        run('java', '-jar', args.build_tools / 'lib/apksigner.jar', 'sign', '--ks', args.keystore,
            '--ks-key-alias', ALIAS, '--ks-pass', password, '--key-pass', password, '--out', signed, aligned)
        certificate = verify_signature(signed, args.build_tools)
        run(args.build_tools / 'zipalign', '-c', '-p', '4', signed)
        badging = run(args.build_tools / 'aapt2', 'dump', 'badging', signed)
        require(re.search(r"^package: name='%s' versionCode='%d' versionName='%s'" % (
            re.escape(APP_ID), VERSION_CODE, re.escape(VERSION_NAME)), badging, re.M), 'Badging identity differs')
        require(normalized_manifest(signed, args.build_tools) == normalized_manifest(args.donor_apk, args.build_tools),
                'Binary manifest changed beyond version metadata')
        # 4. Exact member accounting against the donor.
        final = members(signed)
        retained, replaced, added = [], [], []
        for name, record in final.items():
            if name.startswith('META-INF/'):
                continue
            if name not in donor_members:
                added.append(name)
            elif donor_members[name] == record:
                retained.append(name)
            else:
                replaced.append(name)
        removed = sorted(n for n in donor_members if n not in final and not n.startswith('META-INF/'))
        require(not removed, 'Donor members removed: ' + repr(removed))
        require(set(added) == {'assets/runtime/' + n for n in ADDED_RUNTIME}, 'Unexpected added members: ' + repr(added))
        require(set(replaced) <= {'classes.dex', 'AndroidManifest.xml'} | {'assets/runtime/' + n for n in CHANGED_RUNTIME},
                'Unreviewed replaced members: ' + repr(replaced))
        for name in ADDED_RUNTIME | CHANGED_RUNTIME:
            if (staged / name).exists():
                require(final['assets/runtime/' + name] == pin(staged / name), 'Staged payload differs: ' + name)
        shutil.copyfile(signed, args.output)
    report = {
        'format': 1, 'apk': APK_NAME, **pin(args.output), 'application_id': APP_ID,
        'version_name': VERSION_NAME, 'version_code': VERSION_CODE, 'repository_commit': args.repository_commit,
        'donor': {'apk': DONOR_NAME, 'release': DONOR_RELEASE, 'release_asset_id': DONOR_ASSET_ID, **DONOR_APK,
                  'signer_certificate_sha256': donor_signer},
        'armport_client': armport, 'armport_package': pin(args.armport),
        'signer_certificate_sha256': certificate, 'signing_key_created': False,
        'signature_verified': True, 'binary_manifest_version_only_verified': True,
        'retained_members': len(retained), 'replaced_members': sorted(replaced), 'added_members': sorted(added),
        'changed_runtime_payloads': changed, 'java_sources': source_pins,
        'default_client_architecture': 'x86', 'arm64_client_selectable': True,
        'installation': 'In-place update of COH Atlas Gameplay 0.13.36 (same application ID and signer). '
                        'Keeps the saved character, private database, imported assets and Wine prefix.',
        'device_validated': False, 'gameplay_validated': False, 'm5_complete': False,
    }
    report_path = args.output.with_name('thor-apk-build-report.json')
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    args.output.with_suffix('.apk.sha256').write_text(report['sha256'] + '  ' + APK_NAME + '\n')
    print(json.dumps({k: report[k] for k in ('apk', 'bytes', 'sha256', 'version_name', 'version_code',
                                              'signer_certificate_sha256', 'replaced_members', 'added_members')}))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('donor-apk', 'armport', 'android-jar', 'build-tools', 'keystore', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--password-env', default='COH_INTERACTIVE_KEYSTORE_PASSWORD')
    args = parser.parse_args()
    for key in ('donor_apk', 'armport', 'android_jar', 'build_tools', 'keystore', 'output'):
        setattr(args, key, getattr(args, key).absolute())
    build(args)


if __name__ == '__main__':
    main()
