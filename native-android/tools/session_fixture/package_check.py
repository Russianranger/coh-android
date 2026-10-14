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

RUNTIME_ASSETS = {'world.bin', 'character.bin', 'rig.bin', 'morph.bin', 'locomotion.bin'}
VERSION = '0.1.0-gates16-18'
PACKAGE = 'org.coh.sessionclient'
LIBRARY = 'libcoh_session_client.so'


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('native-android/results/session-client'))
    parser.add_argument('--assets', type=Path, default=Path('native-android/session-client/app/src/main/assets'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    expected = {p.name for p in args.assets.iterdir() if p.is_file()}
    manifest = json.loads((args.assets / 'asset-manifest.json').read_text())
    assert manifest['schema'] == 1 and set(manifest['assets']) == RUNTIME_ASSETS
    for name, pin in manifest['assets'].items():
        assert identity((args.assets / name).read_bytes()) == pin, name
    combined = json.loads((args.assets / 'session-fixture.json').read_text())
    assert combined['passed'] is True and combined['gates'] == [16, 17, 18]
    assert combined['reference_data_drive_rendering'] is False
    assert set(combined['assets']) | {'asset-manifest.json', 'session-fixture.json'} == expected
    for name, pin in combined['assets'].items():
        assert identity((args.assets / name).read_bytes()) == pin, name
    for filename in ('character-fixture.json', 'world-fixture.json', 'locomotion-fixture.json'):
        for name, pin in json.loads((args.assets / filename).read_text())['assets'].items():
            assert identity((args.assets / name).read_bytes()) == {k: pin[k] for k in ('bytes', 'sha256')}, name
    signer = Path(os.environ['ANDROID_HOME']) / 'build-tools/35.0.0/apksigner'
    artifacts = []
    for label, abi, machine in [('arm64', 'arm64-v8a', 183), ('emulator-x86_64', 'x86_64', 62)]:
        path = args.output / ('CoH-Native-Session-Client-0.1.0-' + label + '.apk')
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
        assert match and match.groups() == (PACKAGE, '1', VERSION)
        assert "sdkVersion:'26'" in badging and "targetSdkVersion:'35'" in badging
        assert re.findall(r"^uses-permission: name='([^']+)'", badging, re.M) == [], 'Offline session client must not request network permission'
        assert "native-code: '" + abi + "'" in badging
        certificate = re.search(r'^Signer #1 certificate SHA-256 digest: ([0-9a-f]+)$', signature, re.M)
        assert certificate
        (args.output / ('apk-signature-' + label + '.txt')).write_text(signature)
        (args.output / ('apk-badging-' + label + '.txt')).write_text(badging)
        artifacts.append({'file': path.name, **identity(path.read_bytes()), 'abi': abi, 'elf_machine': machine,
                          'native_library': {'file': native[0], **identity(elf)},
                          'signature_verified': True, 'manifest_verified': True,
                          'packaged_fixtures_verified': True,
                          'signer_certificate_sha256': certificate.group(1)})
    assert len({a['signer_certificate_sha256'] for a in artifacts}) == 1
    receipt = {'schema': 1, 'gates': [16, 17, 18], 'source_commit': os.environ.get('GITHUB_SHA', 'local-uncommitted'),
               'workflow_run_id': os.environ.get('GITHUB_RUN_ID', 'local'), 'application_id': PACKAGE,
               'version_name': VERSION, 'version_code': 1, 'min_sdk': 26, 'target_sdk': 35,
               'gradle': '8.9', 'android_gradle_plugin': '8.7.3', 'ndk': '28.2.13676358', 'cmake': '3.22.1',
               'signing': 'Isolated CI debug key; separate from production launcher',
               'artifacts': artifacts, 'assets': [{'file': name, **identity((args.assets / name).read_bytes())} for name in sorted(expected)],
               'native_session_execution': True, 'original_game_execution': False,
               'full_atlas_loaded': False, 'collision_and_gravity_qualified': False,
               'full_sequencer_execution': False, 'server_interoperability_verified': False,
               'thor_device_execution_verified': False, 'physical_controller_verified': False}
    (args.output / 'build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (args.output / 'SHA256SUMS').write_text(''.join(a['sha256'] + '  ' + a['file'] + '\n' for a in artifacts))
    print(json.dumps({'passed': True, 'artifacts': artifacts}))


if __name__ == '__main__':
    main()
