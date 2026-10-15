#!/usr/bin/env python3
"""Bind the new 0.3 packages to seven runtime assets and the stable test signer.

This receipt qualifies package integrity only. Emulator and physical execution
remain separately reported, and no accepted APK is rebuilt by this checker.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('accepted_session_signer_checks', HERE / 'package_check.py')
signer_checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(signer_checks)
PREP_SPEC = importlib.util.spec_from_file_location('preserved_session_input_pins', HERE / 'prepare_world_session.py')
preparer = importlib.util.module_from_spec(PREP_SPEC)
PREP_SPEC.loader.exec_module(preparer)
PACKAGE = 'org.coh.sessionclient.walk'
VERSION = '0.3.0-gates22-24'
VERSION_CODE = 3
RUNTIME = preparer.RUNTIME
EXPECTED = RUNTIME | preparer.METADATA


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def prepared_assets(directory):
    entries = list(directory.iterdir())
    assert all(p.is_file() and not p.is_symlink() for p in entries)
    assert {p.name for p in entries} == EXPECTED, 'Prepared package asset closure differs'
    manifest = json.loads((directory / 'asset-manifest.json').read_text())
    assert manifest['schema'] == 1 and set(manifest['assets']) == RUNTIME
    fixture = json.loads((directory / 'session-fixture.json').read_text())
    assert fixture['passed'] is True and fixture['gates'] == [22, 23, 24]
    assert fixture['reference_data_drive_rendering'] is False
    assert fixture['runtime_motion_scripted_by_fixture'] is False
    assert fixture['accepted_qualification_repeated'] is False
    assert set(fixture['assets']) | {'asset-manifest.json', 'session-fixture.json'} == EXPECTED
    assert fixture['accepted_apk'] == preparer.ACCEPTED_APK
    assert fixture['accepted_runtime_assets_preserved'] == preparer.ACCEPTED_RUNTIME
    for name, pin in fixture['assets'].items():
        assert identity((directory / name).read_bytes()) == pin, name
    for name, pin in manifest['assets'].items():
        assert identity((directory / name).read_bytes()) == pin, name
    for name, pin in preparer.ACCEPTED_RUNTIME.items():
        assert manifest['assets'][name] == pin, 'Accepted runtime bytes changed: ' + name
    scene = json.loads((directory / 'map-fixture.json').read_text())
    walk = json.loads((directory / 'walkable-fixture.json').read_text())
    assert scene['passed'] is True and walk['passed'] is True
    assert scene['expanded_walkable'] == walk
    assert scene['catalog'] == fixture['catalog'] == {'nodes': 25, 'endpoints': 3, 'assets': 8, 'instances': 11}
    assert set(scene['radius_queries']) == {'24', '96'}
    assert len(scene['radius_queries']['24']) < len(scene['radius_queries']['96'])
    assert manifest['assets']['map.bin'] == {k: scene['bundle'][k] for k in ('bytes', 'sha256')}
    assert walk['assets'] == {'walkable.bin': manifest['assets']['walkable.bin']}
    assert (directory / 'map.bin').read_bytes()[:8] == b'COHWB001'
    assert (directory / 'walkable.bin').read_bytes()[:8] == b'COHWALK1'
    assert walk['scene']['triangle_count'] == 2304
    assert walk['render_collision_source_positions_shared'] is True
    return manifest, fixture, scene, walk


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('native-android/results/world-session-client'))
    parser.add_argument('--assets', type=Path, default=Path('native-android/session-client/app/src/main/assets'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    stable_signer = signer_checks.test_signer_identity()
    manifest, fixture, scene, walk = prepared_assets(args.assets)
    signer = Path(os.environ['ANDROID_HOME']) / 'build-tools/35.0.0/apksigner'
    artifacts = []
    for label, abi, machine in [('arm64', 'arm64-v8a', 183), ('emulator-x86_64', 'x86_64', 62)]:
        path = args.output / ('CoH-Native-Session-Client-0.3.0-' + label + '.apk')
        with zipfile.ZipFile(path) as apk:
            names = apk.namelist()
            assert len(names) == len(set(names)) and apk.testzip() is None
            libraries = [n for n in names if n.startswith('lib/') and n.endswith('.so')]
            assert libraries == ['lib/' + abi + '/' + signer_checks.LIBRARY], libraries
            elf = apk.read(libraries[0])
            assert elf[:6] == b'\x7fELF\x02\x01' and struct.unpack_from('<H', elf, 18)[0] == machine
            assets = {n.removeprefix('assets/') for n in names if n.startswith('assets/') and not n.endswith('/')}
            assert assets == EXPECTED, 'APK asset closure differs'
            for name in sorted(EXPECTED):
                assert apk.read('assets/' + name) == (args.assets / name).read_bytes(), name
        signature = subprocess.check_output([str(signer), 'verify', '--verbose', '--print-certs', str(path)], text=True)
        badging = subprocess.check_output([str(signer.with_name('aapt')), 'dump', 'badging', str(path)], text=True)
        match = re.search(r"^package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", badging, re.M)
        assert match and match.groups() == (PACKAGE, str(VERSION_CODE), VERSION)
        assert "sdkVersion:'26'" in badging and "targetSdkVersion:'35'" in badging
        assert re.findall(r"^uses-permission: name='([^']+)'", badging, re.M) == [], 'Offline source-world client must not request network permission'
        assert "native-code: '" + abi + "'" in badging
        launchable = re.search(r"^launchable-activity: name='([^']+)'", badging, re.M)
        assert launchable and launchable.group(1) == 'org.coh.sessionclient.MainActivity'
        certificates = re.findall(r'^Signer #[0-9]+ certificate SHA-256 digest: ([0-9a-f]+)$', signature, re.M)
        assert certificates == [signer_checks.TEST_SIGNER['certificate_sha256']], 'APK signer differs from the stable accepted public test key'
        (args.output / ('apk-signature-' + label + '.txt')).write_text(signature)
        (args.output / ('apk-badging-' + label + '.txt')).write_text(badging)
        artifacts.append({'file': path.name, **identity(path.read_bytes()), 'abi': abi, 'elf_machine': machine,
                          'native_library': {'file': libraries[0], **identity(elf)},
                          'signature_verified': True, 'manifest_verified': True,
                          'packaged_fixtures_verified': True, 'signer_certificate_sha256': certificates[0]})
    receipt = {'schema': 1, 'gates': [22, 23, 24], 'passed': True,
               'source_commit': os.environ.get('GITHUB_SHA', 'local-uncommitted'),
               'workflow_run_id': os.environ.get('GITHUB_RUN_ID', 'local'),
               'application_id': PACKAGE, 'version_name': VERSION, 'version_code': VERSION_CODE,
               'min_sdk': 26, 'target_sdk': 35, 'gradle': '8.9', 'android_gradle_plugin': '8.7.3',
               'ndk': '28.2.13676358', 'cmake': '3.22.1', 'test_signer': stable_signer,
               'signing': 'Stable intentionally public debug-only PKCS12 key; upgrade of accepted 0.2 without data clearing',
               'artifacts': artifacts,
               'assets': [{'file': name, **identity((args.assets / name).read_bytes())} for name in sorted(EXPECTED)],
               'runtime_asset_count': len(RUNTIME), 'total_packaged_assets': len(EXPECTED),
               'source_catalog': scene['catalog'], 'source_collision_triangles': walk['scene']['triangle_count'],
               'accepted_runtime_assets_preserved': preparer.ACCEPTED_RUNTIME,
               'accepted_qualification_repeated': False, 'native_session_execution_verified': False,
               'qualification_scope': 'Exact source/input/package/ELF/signature integrity; emulator and Thor execution are separate receipts',
               'full_atlas_loaded': False, 'server_interoperability_verified': False,
               'thor_device_execution_verified': False, 'physical_controller_verified': False}
    (args.output / 'build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (args.output / 'SHA256SUMS').write_text(''.join(a['sha256'] + '  ' + a['file'] + '\n' for a in artifacts))
    print(json.dumps({'passed': True, 'artifacts': artifacts}))


if __name__ == '__main__':
    main()
