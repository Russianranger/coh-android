#!/usr/bin/env python3
"""Replay exact hosted protocol evidence admission; never execute a binary."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tempfile
import zipfile

PIN = '6005bbf34376cb71bb5b3fc71058af629b19ce86'
ARTIFACTS = {
    '12090071990': (24754479, 'cfdf66d77f3a11ffc5c814583d27540e51266fa8c2c3fd742c9b90fc6f3aecdf'),
    '12089827111': (3288, '0b1e4dcfdc22b38b84a723baab590174a1fd6119368e21418873a8c52afc6ea6'),
    '12088939718': (1639924, '7b914001140588ddec6a991b660cb6745c907b7ab3390c2b82b63f16421841ee'),
    '12090290394': (74638, '4fb09153c11acfdb12954a64cb04aaf2c6f18f1e1b17a06d7c42a0507db8adea'),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(test, message):
    if not test:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text())


def module(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--artifacts', type=Path, required=True,
                   help='Directory containing ID/artifact.zip for all four pinned artifacts')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    require(not a.output.exists(), 'Fresh output required')
    repo = a.repo.resolve()
    # Execute only the two small evidence validators from the exact qualified
    # revision, never an unpinned working-tree replacement or downloaded code.
    source = lambda name: subprocess.check_output(['git', '-C', str(repo), 'show', PIN + ':' + name])
    source_hashes = {}
    def sources(mapping, prefix='native-android/', lf=False):
        for path, expected in mapping.items():
            rel = prefix + path
            raw = source(rel)
            require(sha(raw.replace(b'\r\n', b'\n') if lf else raw) == expected,
                    'Qualified Git source differs: ' + rel)
            source_hashes[rel] = sha(raw)
    with tempfile.TemporaryDirectory(prefix='coh-ci-admit-') as temp:
        temp = Path(temp)
        roots = {}
        for identity, (size, digest) in ARTIFACTS.items():
            raw = (a.artifacts / identity / 'artifact.zip').read_bytes()
            require(len(raw) == size and sha(raw) == digest, 'Artifact identity differs: ' + identity)
            root = temp / identity
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                infos = z.infolist()
                require(len(infos) <= 1024 and len({x.filename for x in infos}) == len(infos), 'ZIP member count/duplicates')
                require(sum(x.file_size for x in infos) <= 256 * 1024 * 1024, 'ZIP aggregate bound')
                for item in infos:
                    path = PurePosixPath(item.filename)
                    require(not path.is_absolute() and '..' not in path.parts and '\\' not in item.filename
                            and not stat.S_ISLNK(item.external_attr >> 16)
                            and item.file_size <= 64 * 1024 * 1024, 'Unsafe ZIP member')
                require(z.testzip() is None, 'ZIP CRC differs')
                z.extractall(root)
            roots[identity] = root
        host = roots['12090071990']
        run = roots['12089827111']
        session = roots['12088939718']
        boundary = roots['12090290394']
        qualification = read_json(host / 'qualification.json')
        require(qualification['passed'] is True and qualification['source_revision'] == PIN
                and qualification['source_revision_end'] == PIN
                and qualification['source_worktree_dirty'] is False
                and qualification['source_git_status_porcelain'] == []
                and qualification['source_git_status_porcelain_end'] == []
                and qualification['errors'] == {}, 'Host source/qualification admission')
        driver = temp / 'run_live_android.py'
        driver.write_bytes(source('native-android/engine/session/run_live_android.py'))
        live = module(driver)
        manifest = read_json(host / 'android-execution-manifest.json')
        require(qualification['android_manifest_sha256'] == sha((host / 'android-execution-manifest.json').read_bytes())
                and qualification['driver_sha256'] == sha(source('native-android/engine/session/qualify_live.py')),
                'Host manifest/qualification driver differs')
        abis = {abi: live.validate(host, manifest, abi) for abi in ('arm64-v8a', 'x86_64')}
        for abi, entries in abis.items():
            for name, entry in entries.items():
                raw = entry['binary'].read_bytes()
                require(raw[:6] == b'\x7fELF\x02\x01' and int.from_bytes(raw[18:20], 'little') ==
                        (183 if abi == 'arm64-v8a' else 62), 'ELF ABI differs: ' + name)
                descriptor = manifest['suites'][name]['abis'][abi]
                build_receipt = read_json(host / descriptor['receipt'])
                if name in ('crypto', 'login'):
                    sources(build_receipt['native_source_sha256' if name == 'crypto' else 'source_sha256'])
        proof = read_json(run / 'receipt.json')
        require(proof['passed'] is True and proof['android_executed'] is True
                and proof['emulator_qualified'] is True and proof['device_is_emulator'] is True
                and proof['android_sdk'] == '33' and proof['android_release'] == '13'
                and proof['abi'] == 'x86_64' and set(proof['suites']) == live.SUITES
                and proof['manifest_sha256'] == sha((host / 'android-execution-manifest.json').read_bytes()),
                'Android execution identity differs')
        for name, entry in abis['x86_64'].items():
            actual = proof['suites'][name]
            require(actual == read_json(run / (name + '.json'))
                    and actual['passed'] is True and actual['android_executed'] is True
                    and actual['binary_sha256'] == entry['descriptor']['sha256']
                    and actual['build_receipt_sha256'] == entry['descriptor']['receipt_sha256'],
                    'Transferred binary receipt differs: ' + name)
            live.check_result(name, actual['result'], entry['expected'])
        for key in ('accepted_apks_rebuilt', 'actual_server_interoperability_verified', 'full_live_world_verified',
                    'gates25_27_complete', 'physical_android_executed', 'physical_thor_accepted', 'real_account_login_verified'):
            require(proof[key] is False, 'Unexpected acceptance: ' + key)
        summary = read_json(session / 'summary.json')
        require(summary['passed'] is True and summary['accepted_apk_rebuilt'] is False, 'Session host summary')
        sources(summary['source_sha256'])
        combined = [(session / 'combined-arm64', read_json(session / 'combined-arm64/build-receipt.json'), 183),
                    (session / 'combined-host', read_json(session / 'combined-host/build-receipt.json'), 62),
                    (host / 'engine-arm64', qualification['results']['combined_arm64'], 183),
                    (host / 'engine-host', qualification['results']['combined_host'], 62)]
        for root, receipt, machine in combined:
            require(receipt['passed'] is True, 'Combined library build failed')
            sources({x['path']: x['sha256'] for x in receipt['sources']})
            item = receipt['library']
            require(item['name'] == 'libcoh_native_engine.so', 'Unexpected library path')
            raw = (root / item['name']).read_bytes()
            require(len(raw) == item['bytes'] and sha(raw) == item['sha256']
                    and raw[:6] == b'\x7fELF\x02\x01'
                    and int.from_bytes(raw[18:20], 'little') == machine, 'Combined library differs')
        for group, key in [('live_owner', 'source_sha256'), ('mapclient', 'implementation_sha256'),
                           ('server_oracle', 'native_sources_sha256')]:
            sources(qualification['results'][group][key])
        build = read_json(boundary / 'boundary-build.json')
        require(build == read_json(session / 'boundary/boundary-build.json') and build['passed'] is True,
                'Boundary host receipt identity')
        sources(build['source_sha256'])
        for abi, item in build['binaries'].items():
            binary = boundary / ('coh-net-udp-' + abi)
            require(sha(binary.read_bytes()) == item['sha256'] and binary.stat().st_size == item['bytes']
                    and binary.read_bytes() == (session / 'boundary' / binary.name).read_bytes(), 'Boundary binary differs')
        boundary_driver = temp / 'android_boundary.py'
        boundary_driver.write_bytes(source('native-android/engine/session/android_boundary.py'))
        boundary_check = module(boundary_driver)
        udp = read_json(boundary / 'android-udp-proof.json')
        require(udp['passed'] is True and udp['android_api'] == '33' and udp['abi'] == 'x86_64'
                and udp['binary_sha256'] == build['binaries']['x86_64']['sha256']
                and boundary_check.valid_socket_report(udp['native'])
                and udp['native'] == read_json(boundary / 'android-udp-stdout.txt')
                and udp['arm64_executed'] is False and udp['physical_thor_accepted'] is False
                and udp['actual_server_interoperability_verified'] is False, 'UDP Android boundary admission')
        result = {'passed': True, 'source_revision': PIN, 'artifact_identities_verified': list(ARTIFACTS),
                  'git_source_files_verified': len(source_hashes), 'source_sha256': source_hashes,
                  'android13_x86_64_suites': {k: v['result'] for k, v in proof['suites'].items()},
                  'android13_udp_boundary': udp['native'], 'arm64_built_suites': sorted(live.SUITES),
                  'boundary_device_cleanup_verified': False,
                  'live_suites_device_cleanup_receipt_verified': True,
                  'arm64_executed': False, 'physical_thor_accepted': False, 'live_world': False,
                  'accepted_apks_rebuilt': False, 'independent_artifact_replay_only': True}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}))


if __name__ == '__main__':
    main()
