#!/usr/bin/env python3
"""Prepare bounded, pinned build inputs; large server/game data stays external.

A launcher APK is an input donor, never executed or installed by this tool. Only
its tiny PRoot core, immutable metadata and reviewed Python helpers enter the new
APK. PostgreSQL, Wine/FEX, rootfs, PE game/server binaries and asset packs do not.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import shutil
import stat
import subprocess
import urllib.request
import zipfile
from client_slots_input import prepare_client_slots

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
ROOT = PROJECT.parents[1]
DONOR_URL = 'https://github.com/Russianranger/coh-android/releases/download/coh-atlas-gameplay-v0.13.36/COH-Atlas-Gameplay-0.13.36.apk'
DONOR_NAME = 'COH-Atlas-Gameplay-0.13.36.apk'
DONOR_BYTES = 42076692
DONOR_SHA = '14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f'
SCENE_ARTIFACT = '11945445541'
SCENE_NAME = 'CoH-Native-Session-Client-0.3.0-arm64.apk'
SCENE_SHA = '75ff158c3e1387671ff2a47f0aa6a126b9c93389fd16685d78a9fcf4ed164639'
SCENE_ASSETS = ('asset-manifest.json', 'character.bin', 'locomotion.bin', 'map-fixture.json', 'map.bin', 'morph.bin', 'rig.bin', 'session-fixture.json', 'walkable-fixture.json', 'walkable.bin', 'world.bin')
METADATA_SUFFIXES = ('.json', '.py', '.sql', '.md')


def pin(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def verify(path, sha, length=None):
    if not path.is_file() or (length is not None and path.stat().st_size != length):
        raise ValueError('Missing or unexpected byte length: ' + str(path))
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != sha:
        raise ValueError('Input SHA256 mismatch: ' + str(path))


def safe_zip(z):
    names = set()
    for info in z.infolist():
        p = PurePosixPath(info.filename)
        if info.filename in names or p.is_absolute() or '..' in p.parts or '\\' in info.filename:
            raise ValueError('Unsafe/duplicate APK archive path')
        names.add(info.filename)
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise ValueError('Symlink APK archive entry')


def download(url, path, sha, size):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        verify(path, sha, size)
        return
    temporary = path.with_suffix(path.suffix + '.download')
    try:
        with urllib.request.urlopen(url, timeout=60) as source, temporary.open('wb') as out:
            total = 0
            while chunk := source.read(1 << 20):
                total += len(chunk)
                if total > size:
                    raise ValueError('Pinned input exceeds expected length')
                out.write(chunk)
        verify(temporary, sha, size)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def scene_input(args):
    if args.scene_apk:
        path = args.scene_apk.resolve()
    else:
        path = args.cache / SCENE_NAME
        if not path.exists():
            archive = args.cache / ('artifact-' + SCENE_ARTIFACT + '.zip')
            args.cache.mkdir(parents=True, exist_ok=True)
            with archive.open('wb') as out:
                subprocess.run(['gh', 'api', 'repos/Russianranger/coh-android/actions/artifacts/' + SCENE_ARTIFACT + '/zip'], stdout=out, check=True, timeout=180)
            with zipfile.ZipFile(archive) as z:
                safe_zip(z)
                matches = [i for i in z.infolist() if PurePosixPath(i.filename).name == SCENE_NAME]
                if len(matches) != 1 or matches[0].file_size > 8 << 20:
                    raise ValueError('Qualified artifact contains no unique bounded accepted scene APK')
                path.write_bytes(z.read(matches[0]))
    verify(path, SCENE_SHA)
    return path


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def prepare(args):
    donor = args.donor_apk.resolve() if args.donor_apk else args.cache / DONOR_NAME
    if not args.donor_apk:
        download(DONOR_URL, donor, DONOR_SHA, DONOR_BYTES)
    verify(donor, DONOR_SHA, DONOR_BYTES)
    scene = scene_input(args)
    assets = args.output / 'assets'
    jni = args.output / 'jniLibs'
    # These generated directories are exclusively owned by this preparer.
    for name in ('runtime', 'combined', 'atlas'):
        shutil.rmtree(assets / name, ignore_errors=True)
    for name in ('neighborhood-map.bin','live-world.bin'):
        (assets / name).unlink(missing_ok=True)
    bundled = {}
    donor_files = {}
    receipt = {'format': 1, 'donor_apk': {'name': DONOR_NAME, **pin(donor.read_bytes())}, 'scene_apk': {'name': SCENE_NAME, **pin(scene.read_bytes())}, 'large_runtime_payloads_bundled': False, 'actual_server_interoperability_verified': False}
    with zipfile.ZipFile(donor) as z:
        safe_zip(z)
        for info in z.infolist():
            if not info.filename.startswith('assets/runtime/') or info.is_dir():
                continue
            name = info.filename.removeprefix('assets/runtime/')
            if '/' in name or info.file_size > 16 << 20:
                raise ValueError('Unexpected donor runtime inventory shape')
            data = z.read(info)
            donor_files[info.filename] = pin(data)
            if name.endswith(METADATA_SUFFIXES):
                write(assets / 'runtime' / name, data)
                bundled['runtime/' + name] = pin(data)
        data = z.read('assets/atlas/atlas-import.properties')
        write(assets / 'atlas/atlas-import.properties', data)
        # This executable is the established Android PRoot core, not a PE server.
        cores = {}
        for name in ('libproot.so', 'libproot-loader.so'):
            data = z.read('lib/arm64-v8a/' + name)
            if not (data[:5] == b'\x7fELF\x02' and int.from_bytes(data[18:20], 'little') == 183 and len(data) < 1 << 20):
                raise ValueError('Unexpected PRoot native core')
            write(jni / 'arm64-v8a' / name, data)
            cores[name] = pin(data)
        receipt['proot_cores'] = cores
    # Preserve the complete donor helper/manifest closure byte-for-byte. Its
    # client-manifest independently verifies the original runtime scripts.
    # New server-only orchestration is a separate, reviewed combined helper.
    helper_paths = sorted((PROJECT / 'runtime').glob('*.py')) + args.guest_override
    combined_helpers = {}
    for path in helper_paths:
        if path.name in combined_helpers or path.suffix != '.py' or not path.is_file() or path.stat().st_size > 1 << 20:
            raise ValueError('Invalid or duplicate combined Python helper')
        data = path.read_bytes()
        write(assets / 'combined' / path.name, data)
        combined_helpers[path.name] = pin(data)
    receipt['combined_helpers'] = combined_helpers
    # The public static crypto dependency is redistributed with its exact
    # reviewed license and source coordinates; no private Android crypto is used.
    crypto_pin = json.loads((ROOT / 'native-android/engine/auth/android/openssl-source.json').read_text())
    crypto_license = (ROOT / 'native-android/engine/auth/android/OPENSSL-LICENSE.txt').read_bytes()
    if hashlib.sha256(crypto_license).hexdigest() != crypto_pin['license_sha256']:
        raise ValueError('Public crypto license differs from source pin')
    write(assets / 'combined/OPENSSL-LICENSE.txt', crypto_license)
    receipt['public_crypto'] = {'version': crypto_pin['version'], 'source_url': crypto_pin['url'],
                               'source_sha256': crypto_pin['sha256'], 'license': pin(crypto_license)}
    if getattr(args, 'client_slots', False):
        receipt['client_slots'] = prepare_client_slots(assets)
    contract = {'format': 1, 'donor_apk': receipt['donor_apk'], 'donor_files': donor_files, 'bundled_files': bundled}
    write(assets / 'combined/import-contract.json', (json.dumps(contract, sort_keys=True, indent=2) + '\n').encode())
    with zipfile.ZipFile(scene) as z:
        safe_zip(z)
        asset_names = {n.removeprefix('assets/') for n in z.namelist() if n.startswith('assets/') and not n.endswith('/')}
        if asset_names != set(SCENE_ASSETS):
            raise ValueError('Accepted scene APK asset inventory changed')
        scene_files = {}
        for name in SCENE_ASSETS:
            data = z.read('assets/' + name)
            if len(data) > 8 << 20:
                raise ValueError('Accepted bounded scene asset exceeds limit')
            write(assets / name, data)
            scene_files[name] = pin(data)
        receipt['scene_files'] = scene_files
    receipt['runtime_helpers'] = {p: v for p, v in bundled.items() if p.endswith('.py')}
    receipt['import_contract'] = pin((assets / 'combined/import-contract.json').read_bytes())
    write(assets / 'combined/build-inputs.json', (json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode())
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'status': 'prepared', 'scene_files': len(scene_files), 'donor_files': len(donor_files), 'guest_helpers': len(receipt['runtime_helpers']), 'large_payloads_bundled': False}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--donor-apk', type=Path)
    p.add_argument('--scene-apk', type=Path)
    p.add_argument('--cache', type=Path, default=PROJECT / '.inputs')
    p.add_argument('--output', type=Path, default=PROJECT / 'app/src/main')
    p.add_argument('--guest-override', type=Path, action='append', default=[])
    p.add_argument('--client-slots', action='store_true', help='Bundle the exact retained CLIENT slot image for the next diagnostic')
    p.add_argument('--evidence', type=Path, default=ROOT / 'native-android/results/combined-client/build-inputs.json')
    prepare(p.parse_args())


if __name__ == '__main__':
    main()
