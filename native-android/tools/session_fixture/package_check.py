#!/usr/bin/env python3
"""Bind session APK bytes to exact fixtures, architecture, manifest and signature."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import zipfile

RUNTIME_ASSETS = {'world.bin', 'character.bin', 'rig.bin', 'morph.bin', 'locomotion.bin', 'walkable.bin'}
VERSION = '0.2.0-gates19-21'
PACKAGE = 'org.coh.sessionclient.walk'
LIBRARY = 'libcoh_session_client.so'
TEST_SIGNER = {
    'schema': 1, 'keystore': 'session-test.p12', 'bytes': 2738,
    'sha256': '2c5a771d7a3989726d475a64471a1cf8bffafb62193a3a98a49ed7070ab2ee05',
    'certificate_sha256': '9aec9a8635d33dabd676748c3287e035e00d676546b4da18469dd48eecf5c522',
    'alias': 'coh-native-test', 'store_type': 'PKCS12',
    'password': 'coh-native-public-test',
}


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def test_signer_identity():
    directory = Path(__file__).resolve().parents[2] / 'session-client/app/test-signing'
    metadata = json.loads((directory / 'signer.json').read_text())
    assert {key: metadata[key] for key in TEST_SIGNER} == TEST_SIGNER, 'Public test signer metadata changed'
    assert identity((directory / TEST_SIGNER['keystore']).read_bytes()) == {
        key: TEST_SIGNER[key] for key in ('bytes', 'sha256')
    }, 'Public test signer keystore bytes changed'
    return {key: TEST_SIGNER[key] for key in ('keystore', 'bytes', 'sha256', 'certificate_sha256', 'alias', 'store_type')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('native-android/results/session-client'))
    parser.add_argument('--assets', type=Path, default=Path('native-android/session-client/app/src/main/assets'))
    args = parser.parse_args()
    stable_signer = test_signer_identity()
    args.output.mkdir(parents=True, exist_ok=True)
    expected = {p.name for p in args.assets.iterdir() if p.is_file()}
    manifest = json.loads((args.assets / 'asset-manifest.json').read_text())
    assert manifest['schema'] == 1 and set(manifest['assets']) == RUNTIME_ASSETS
    for name, pin in manifest['assets'].items():
        assert identity((args.assets / name).read_bytes()) == pin, name
    combined = json.loads((args.assets / 'session-fixture.json').read_text())
    assert combined['passed'] is True and combined['gates'] == [19, 20, 21]
    assert combined['reference_data_drive_rendering'] is False
    assert set(combined['assets']) | {'asset-manifest.json', 'session-fixture.json'} == expected
    for name, pin in combined['assets'].items():
        assert identity((args.assets / name).read_bytes()) == pin, name
    for filename in ('character-fixture.json', 'world-fixture.json', 'directional-fixture.json', 'walkable-fixture.json'):
        for name, pin in json.loads((args.assets / filename).read_text())['assets'].items():
            assert identity((args.assets / name).read_bytes()) == {k: pin[k] for k in ('bytes', 'sha256')}, name
    signer = Path(os.environ['ANDROID_HOME']) / 'build-tools/35.0.0/apksigner'
    artifacts = []
    for label, abi, machine in [('arm64', 'arm64-v8a', 183), ('emulator-x86_64', 'x86_64', 62)]:
        path = args.output / ('CoH-Native-Session-Client-0.2.0-' + label + '.apk')
        with zipfile.ZipFile(path) as apk:
            assert apk.testzip() is None
            native = [n for n in apk.namelist() if n.startswith('lib/') and n.endswith('.so')]
            assert native == ['lib/' + abi + '/' + LIBRARY], native
            elf = apk.read(native[0])
            assert elf[:6] == b'\x7fELF\x02\x01' and struct.unpack_from('<H', elf, 18)[0] == machine
            assert {n.removeprefix('assets/') for n in apk.namelist() if n.startswith('assets/') and not n.endswith('/')} == expected
            for name in expected:
                assert apk.read('assets/' + name) == (args.assets / name).read_bytes(), name
        signature = subprocess.check_output([str(signer), 'verify', '--verbose', '--print-certs', str(path)], text=True)
        badging = subprocess.check_output([str(signer.with_name('aapt')), 'dump', 'badging', str(path)], text=True)
        match = re.search(r"^package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", badging, re.M)
        assert match and match.groups() == (PACKAGE, '2', VERSION)
        assert "sdkVersion:'26'" in badging and "targetSdkVersion:'35'" in badging
        assert re.findall(r"^uses-permission: name='([^']+)'", badging, re.M) == [], 'Offline session client must not request network permission'
        assert "native-code: '" + abi + "'" in badging
        certificate = re.search(r'^Signer #1 certificate SHA-256 digest: ([0-9a-f]+)$', signature, re.M)
        assert certificate and certificate.group(1) == TEST_SIGNER['certificate_sha256'], 'APK certificate differs from stable public test signer'
        (args.output / ('apk-signature-' + label + '.txt')).write_text(signature)
        (args.output / ('apk-badging-' + label + '.txt')).write_text(badging)
        artifacts.append({'file': path.name, **identity(path.read_bytes()), 'abi': abi, 'elf_machine': machine,
                          'native_library': {'file': native[0], **identity(elf)},
                          'signature_verified': True, 'manifest_verified': True,
                          'packaged_fixtures_verified': True,
                          'signer_certificate_sha256': certificate.group(1)})
    assert len({a['signer_certificate_sha256'] for a in artifacts}) == 1
    receipt = {'schema': 1, 'gates': [19, 20, 21], 'source_commit': os.environ.get('GITHUB_SHA', 'local-uncommitted'),
               'workflow_run_id': os.environ.get('GITHUB_RUN_ID', 'local'), 'application_id': PACKAGE,
               'version_name': VERSION, 'version_code': 2, 'min_sdk': 26, 'target_sdk': 35,
               'gradle': '8.9', 'android_gradle_plugin': '8.7.3', 'ndk': '28.2.13676358', 'cmake': '3.22.1',
               'signing': 'Stable intentionally public PKCS12 test-only signer; separate application ID and signing from accepted 0.1.0 and production launcher',
               'test_signer': stable_signer,
               'artifacts': artifacts, 'assets': [{'file': name, **identity((args.assets / name).read_bytes())} for name in sorted(expected)],
               'native_session_implementation': True, 'native_session_execution_verified': False,
               'qualification_scope': 'Package integrity only; execution is reported separately by emulator/device receipts',
               'original_game_execution': False,
               'full_atlas_loaded': False, 'collision_and_gravity_qualified': False,
               'full_sequencer_execution': False, 'server_interoperability_verified': False,
               'thor_device_execution_verified': False, 'physical_controller_verified': False}
    (args.output / 'build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (args.output / 'SHA256SUMS').write_text(''.join(a['sha256'] + '  ' + a['file'] + '\n' for a in artifacts))
    print(json.dumps({'passed': True, 'artifacts': artifacts}))


if __name__ == '__main__':
    main()
