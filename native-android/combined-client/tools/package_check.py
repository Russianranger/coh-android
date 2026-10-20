#!/usr/bin/env python3
"""Audit the actual APK, keeping large runtime/game payloads external."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import zipfile
from prepare import DONOR_SHA, DONOR_BYTES, SCENE_SHA, SCENE_ASSETS, safe_zip, pin

PACKAGE = 'org.coh.nativecombined'
BUILD_PROFILES = {
    'original-fragment': ('10', '0.1.9-gates25-27-test'),
    'memory-diagnostic': ('11', '0.1.10-memory-diagnostic-test'),
    'report-diagnostic': ('12', '0.1.11-report-diagnostic-test'),
    'catalog-diagnostic': ('13', '0.1.12-catalog-diagnostic-test'),
    'entity-diagnostic': ('14', '0.1.13-entity-diagnostic-test'),
}


def check_build_identity(version_code, version_name, profile):
    assert (version_code, version_name) == BUILD_PROFILES[profile], 'APK version differs from the selected build profile'


def process_memory_jni(raw, readelf):
    """Require the additive memory sampler on the production network DSO."""
    if readelf is None or not readelf.is_file():
        raise ValueError('Memory diagnostic profile requires pinned --readelf')
    with tempfile.TemporaryDirectory(prefix='combined-memory-jni-') as directory:
        library = Path(directory) / 'libcoh_combined_network.so'
        library.write_bytes(raw)
        symbols = run([readelf, '--dyn-syms', '--wide', library])
    exported = set()
    for line in symbols.splitlines():
        fields = line.split()
        if len(fields) >= 8 and fields[0].rstrip(':').isdigit() and fields[6] != 'UND' and fields[4] in ('GLOBAL', 'WEAK') and fields[5] in ('DEFAULT', 'PROTECTED'):
            exported.add(fields[7].split('@', 1)[0])
    entrypoint = 'Java_org_coh_nativecombined_LocalNative_processMemory'
    assert entrypoint in exported, 'Production process-memory JNI entrypoint absent'
    assert not any(name.startswith('Java_org_coh_nativecombined_InteropNative_') for name in exported), 'Diagnostic interop JNI leaked into the production network DSO'
    return entrypoint


def run(command):
    return subprocess.run([str(x) for x in command], check=True, capture_output=True, text=True, timeout=60).stdout


def tool(args, name):
    if args.build_tools:
        path = args.build_tools / name
        if not path.is_file():
            raise ValueError('Missing pinned Android build tool ' + str(path))
        return path
    sdk = os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT')
    if sdk and (Path(sdk) / 'build-tools/35.0.0' / name).is_file():
        return Path(sdk) / 'build-tools/35.0.0' / name
    raise ValueError('Use --build-tools for Android build-tools/35.0.0')


def audit(args):
    if args.build_profile in ('memory-diagnostic', 'report-diagnostic', 'catalog-diagnostic', 'entity-diagnostic') and not args.require_interop:
        raise ValueError('Memory diagnostic build must retain the independent interop library audit')
    if args.apk.stat().st_size > 25 << 20:
        raise ValueError('Combined APK exceeds bounded 25MiB small-core policy')
    with zipfile.ZipFile(args.apk) as z:
        safe_zip(z)
        receipt = json.loads(z.read('assets/combined/build-inputs.json'))
        contract = json.loads(z.read('assets/combined/import-contract.json'))
        assert receipt['donor_apk']['sha256'] == DONOR_SHA
        assert receipt['donor_apk']['bytes'] == DONOR_BYTES
        assert receipt['scene_apk']['sha256'] == SCENE_SHA
        assert receipt['large_runtime_payloads_bundled'] is False
        assert receipt['actual_server_interoperability_verified'] is False
        assert contract['donor_apk'] == receipt['donor_apk']
        assert pin(z.read('assets/combined/import-contract.json')) == receipt['import_contract']
        expected_assets = {'assets/combined/import-contract.json', 'assets/combined/build-inputs.json', 'assets/atlas/atlas-import.properties'}
        assert pin(z.read('assets/combined/OPENSSL-LICENSE.txt')) == receipt['public_crypto']['license']
        assert receipt['public_crypto']['license']['sha256'] == '7d5450cb2d142651b8afa315b5f238efc805dad827d91ba367d8516bc9d49e7a'
        expected_assets.add('assets/combined/OPENSSL-LICENSE.txt')
        for name, value in contract['bundled_files'].items():
            assert name.startswith('runtime/') and name.count('/') == 1
            data = z.read('assets/' + name)
            assert pin(data) == value, 'Bundled donor metadata changed: ' + name
            assert contract['donor_files']['assets/' + name] == value, 'Donor closure overridden'
            assert name.endswith(('.json', '.py', '.sql', '.md'))
            expected_assets.add('assets/' + name)
        for name, value in receipt['scene_files'].items():
            assert name in SCENE_ASSETS and pin(z.read('assets/' + name)) == value
            expected_assets.add('assets/' + name)
        assert set(receipt['scene_files']) == set(SCENE_ASSETS)
        for name, value in receipt['combined_helpers'].items():
            assert '/' not in name and name.endswith('.py')
            assert pin(z.read('assets/combined/' + name)) == value
            expected_assets.add('assets/combined/' + name)
        actual_assets = {i.filename for i in z.infolist() if i.filename.startswith('assets/') and not i.is_dir()}
        assert actual_assets == expected_assets, 'Unexpected or missing embedded asset payloads'
        asset_bytes = sum(z.getinfo(n).file_size for n in actual_assets)
        assert asset_bytes < 12 << 20, 'Uncompressed embedded assets exceed bounded scene/metadata scope'
        libraries = {}
        memory_entrypoint = None
        native_abis = set()
        for i in z.infolist():
            if not i.filename.startswith('lib/') or i.is_dir():
                continue
            _, abi, filename = i.filename.split('/')
            assert abi in ('arm64-v8a', 'x86_64')
            allowed = ('libproot.so', 'libproot-loader.so', 'libcoh_combined_network.so', 'libcoh_session_client.so', 'libc++_shared.so')
            if args.require_interop:
                allowed += ('libcoh_combined_interop.so',)
            assert filename in allowed
            data = z.read(i)
            assert data[:5] == b'\x7fELF\x02', 'Native library is not ELF64'
            machine = int.from_bytes(data[18:20], 'little')
            assert machine == (183 if abi == 'arm64-v8a' else 62)
            if filename.startswith('libproot'):
                assert abi == 'arm64-v8a' and pin(data) == receipt['proot_cores'][filename], 'PRoot core changed'
            if filename == 'libcoh_combined_network.so':
                native_abis.add(abi)
                if args.build_profile in ('memory-diagnostic', 'report-diagnostic', 'catalog-diagnostic', 'entity-diagnostic'):
                    memory_entrypoint = process_memory_jni(data, args.readelf)
            libraries[i.filename] = pin(data)
        assert native_abis == {args.abi}
        assert 'lib/' + args.abi + '/libcoh_session_client.so' in libraries
        if args.require_interop:
            assert 'lib/' + args.abi + '/libcoh_combined_interop.so' in libraries
        if args.abi == 'arm64-v8a':
            assert all('lib/arm64-v8a/' + n in libraries for n in receipt['proot_cores'])
        # PE binaries, archives, PostgreSQL, rootfs and full game assets are never
        # admitted as embedded package inputs. The external donor retains them.
        for i in z.infolist():
            assert not i.filename.lower().endswith(('.exe', '.dll', '.msi', '.zip', '.tar.gz', '.pigg'))
    metadata = run([tool(args, 'aapt'), 'dump', 'badging', args.apk])
    identity = re.search(r"^package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", metadata, re.M)
    assert identity and identity.group(1) == PACKAGE
    if args.require_interop:
        check_build_identity(identity.group(2), identity.group(3), args.build_profile)
    assert "launchable-activity: name='org.coh.nativecombined.MainActivity'" in metadata
    signer = run([tool(args, 'apksigner'), 'verify', '--print-certs', args.apk])
    certificates = re.findall(r'Signer #\d+ certificate SHA-256 digest: (\S+)', signer)
    assert len(certificates) == 1
    if args.require_interop:
        assert certificates[0] == '9aec9a8635d33dabd676748c3287e035e00d676546b4da18469dd48eecf5c522', 'Test upgrade signer differs from accepted Combined builds'
    source = run(['git', '-C', args.source_root, 'rev-parse', 'HEAD']).strip()
    if os.environ.get('GITHUB_SHA'):
        assert source == os.environ['GITHUB_SHA'], 'APK qualification is not checking the workflow source revision'
    dirty = run(['git', '-C', args.source_root, 'status', '--porcelain', '--untracked-files=no'])
    if args.require_clean and dirty.strip():
        raise ValueError('Qualification source has tracked modifications')
    return {'format': 1, 'status': 'passed', 'apk': {'name': args.apk.name, **pin(args.apk.read_bytes())}, 'package': PACKAGE, 'version_code': identity.group(2), 'version_name': identity.group(3), 'build_profile': args.build_profile if args.require_interop else None, 'process_memory_jni_entrypoint': memory_entrypoint, 'abi': args.abi, 'source_commit': source, 'tracked_source_clean': not bool(dirty.strip()), 'signer_certificate_sha256': certificates[0], 'embedded_asset_bytes': asset_bytes, 'embedded_asset_files': len(actual_assets), 'native_libraries': libraries, 'large_runtime_game_payloads_embedded': False, 'donor_apk_sha256': DONOR_SHA, 'accepted_scene_apk_sha256': SCENE_SHA, 'actual_server_interoperability_verified': False, 'scope': 'Package identity, exact bounded scene and donor metadata, native ELF architecture, signer and absence of embedded large runtime/game payloads.'}


def main():
    if not __debug__ or os.environ.get('PYTHONOPTIMIZE'):
        raise ValueError('OPTIMIZED_PACKAGE_AUDIT_REFUSED')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apk', type=Path, required=True)
    p.add_argument('--abi', choices=['arm64-v8a', 'x86_64'], required=True)
    p.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[3])
    p.add_argument('--build-tools', type=Path)
    p.add_argument('--require-clean', action='store_true')
    p.add_argument('--require-interop', action='store_true', help='Require the separate Gates 25-27 diagnostic library and test version')
    p.add_argument('--build-profile', choices=BUILD_PROFILES, default='original-fragment', help='Exact admitted version pair; historical default remains unchanged')
    p.add_argument('--readelf', type=Path, help='Pinned NDK llvm-readelf, required for the memory diagnostic production JNI audit')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    value = audit(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': value['status'], 'apk': value['apk'], 'abi': args.abi, 'embedded_asset_bytes': value['embedded_asset_bytes']}))


if __name__ == '__main__':
    main()
