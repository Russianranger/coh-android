#!/usr/bin/env python3
"""Reuse pinned gates19–21 package bytes after driver-only changes.

This retains successful package/source receipts exactly and excludes the failed
original emulator outputs. Fresh emulator execution is required separately.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import subprocess
import zipfile

SOURCE_COMMIT = '8629d6a7c4863f492ee50bc030c21c2b2d2f0c3d'
WORKFLOW_RUN = '38656997946'
ARTIFACT_ID = 11936304916
ARCHIVE_BYTES = 7291533
ARCHIVE_SHA256 = '662b679f33854c704b831a061ba03a5d142b8f987686f783293f51ef84503151'
BUILD_RECEIPT_PIN = {'bytes': 5143, 'sha256': 'fdf108fa56d45419e867a453ef28a0728348f8f0c4dd9fbfa32c2235e6fb1ae1'}
HOST_RECEIPT_PIN = {'bytes': 1490, 'sha256': '1b4700f07c4e843efdeac138bebfc77078f4fd81eb9c3e6f91ac7d5ffe99794b'}
CERTIFICATE_SHA256 = '9aec9a8635d33dabd676748c3287e035e00d676546b4da18469dd48eecf5c522'
KEYSTORE_PIN = {'bytes': 2738, 'sha256': '2c5a771d7a3989726d475a64471a1cf8bffafb62193a3a98a49ed7070ab2ee05'}
APK_PINS = {
    'CoH-Native-Session-Client-0.2.0-arm64.apk': {
        'bytes': 2344055, 'sha256': '2d59e2b39af99facc6f3ac26b310aeba85802542efabb1e71d90e2d33a00de92',
        'abi': 'arm64-v8a', 'elf_machine': 183},
    'CoH-Native-Session-Client-0.2.0-emulator-x86_64.apk': {
        'bytes': 2361364, 'sha256': '45752990736305bc1520d81e9c6507bb4b53a8322970bed8535085ff0f44af4e',
        'abi': 'x86_64', 'elf_machine': 62},
}
ALLOWED_FILES = frozenset({
    'native-android/session-client/tools/emulator_check.py',
    'native-android/session-client/tools/tap_host_check.py',
    'native-android/session-client/tools/reuse_walkable_package.py',
    'native-android/session-client/tools/reuse_walkable_host_check.py',
    '.github/workflows/native-session-client.yml',
})
PROOF_FILES = frozenset({
    'host-walkable-proof.json', 'host-walk-proof.json', 'host-directional-proof.json',
    'host-directional-sampler-proof.json', 'lifecycle/lifecycle-host-checks.json',
    'depth-codec-host.json', 'snapshot-host.json',
})
EXTRA_JSON = frozenset({'accepted-assets-recovery.json', 'source-floor-resolution.json',
                        'legacy-locomotion-abi-proof.json', 'session-fixture.json',
                        'walkable-fixture.json', 'asset-manifest.json'})
MAX_EXTRACTED = 64 << 20


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(root, *arguments):
    return subprocess.run(['git', *arguments], cwd=root, capture_output=True,
                          check=True, timeout=30).stdout


def safe_name(name):
    path = PurePosixPath(name)
    return (bool(name) and not path.is_absolute() and '..' not in path.parts
            and '\\' not in name and not re.match(r'^[A-Za-z]:', name)
            and str(path) == name.rstrip('/'))


def allowed_path(name):
    if not safe_name(name):
        return False
    if name in ALLOWED_FILES:
        return True
    if name.startswith('native-android/evidence/phases19-21/'):
        return True
    # Only documentation outside application/asset/source dependency directories.
    if name == 'README.md':
        return True
    if name.startswith('native-android/') and name.endswith('.md'):
        forbidden = ('/app/', '/shaders/', '/src/', '/include/', '/source/', '/corpus/')
        return not any(part in name for part in forbidden)
    return False


def guard(root, base, head, branch_ref=None):
    """Actual Git ancestry and working-tree gate; no artifact checks or builds."""
    changes = []
    try:
        require(bool(re.fullmatch('[0-9a-f]{40}', head)), 'Head must be an exact commit SHA')
        require(git(root, 'rev-parse', 'HEAD').decode().strip() == head, 'Head differs from checkout')
        require(git(root, 'rev-parse', base).decode().strip() == base, 'Base must be an exact commit SHA')
        branch = git(root, 'branch', '--show-current').decode().strip()
        require(branch in ('native-android', ''), 'Checkout is not native-android')
        require((branch_ref == 'refs/heads/native-android') if branch_ref is not None
                else branch == 'native-android', 'Branch provenance is not native-android')
        require(not git(root, 'status', '--porcelain', '--untracked-files=no').strip(),
                'Tracked working tree or index changed')
        untracked = git(root, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0')
        require(all(not name or name.decode().startswith('native-android/results/') for name in untracked),
                'Untracked files outside generated results')
        git(root, 'merge-base', '--is-ancestor', base, head)
        raw = git(root, 'diff', '--raw', '-z', '--no-renames', base, head).split(b'\0')
        require(raw[-1] == b'' and (len(raw)-1) % 2 == 0, 'Malformed Git raw diff')
        for index in range(0, len(raw)-1, 2):
            fields = raw[index].decode('ascii').split()
            name = raw[index+1].decode('utf8')
            require(len(fields) == 5 and fields[0].startswith(':'), 'Malformed Git diff record')
            before, after = fields[0][1:], fields[1]
            changes.append({'path': name, 'old_mode': before, 'new_mode': after, 'status': fields[4]})
            require(before in {'000000', '100644', '100755'} and after in {'000000', '100644', '100755'},
                    'Symlink, gitlink or non-regular Git mode changed')
            require(fields[4] in {'A', 'M', 'D'} and allowed_path(name),
                    'Runtime, app, adapter, shader, asset, source or unapproved dependency changed')
        return {'eligible': True, 'reason': 'Only allowlisted driver, workflow, documentation or evidence changes',
                'changes': changes}
    except (subprocess.CalledProcessError, UnicodeError, ValueError) as error:
        return {'eligible': False, 'reason': str(error) if isinstance(error, ValueError)
                else 'Git ancestry or diff inspection failed closed', 'changes': changes}


def archive_entries(bundle):
    entries = bundle.infolist()
    require(len(entries) <= 20000 and sum(item.file_size for item in entries) <= MAX_EXTRACTED,
            'Archive extraction exceeds bounded limits')
    names = set()
    for item in entries:
        kind = stat.S_IFMT(item.external_attr >> 16)
        require(safe_name(item.filename) and item.filename not in names
                and kind in {0, stat.S_IFREG, stat.S_IFDIR} and not item.flag_bits & 1,
                'Unsafe, duplicate, encrypted or non-regular ZIP entry')
        names.add(item.filename)
    require(bundle.testzip() is None, 'Artifact ZIP CRC integrity failed')
    return names


def verify_archive(archive, repo_root):
    raw = archive.read_bytes()
    require(identity(raw) == {'bytes': ARCHIVE_BYTES, 'sha256': ARCHIVE_SHA256},
            'Original artifact archive size or SHA256 changed')
    selected = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
        names = archive_entries(bundle)
        receipt_raw = bundle.read('build-receipt.json')
        host_raw = bundle.read('source-validation-stage.json')
        require(identity(receipt_raw) == BUILD_RECEIPT_PIN, 'Original build receipt changed')
        require(identity(host_raw) == HOST_RECEIPT_PIN, 'Original host-stage receipt changed')
        receipt, host = json.loads(receipt_raw), json.loads(host_raw)
        for document in (receipt, host):
            require(document['source_commit'] == SOURCE_COMMIT and str(document['workflow_run_id']) == WORKFLOW_RUN
                    and document['gates'] == [19, 20, 21], 'Original source/run/gates differ')
        require(host['status'] == 'completed' and host['passed'] is True, 'Original host stage is not complete')
        require(receipt['application_id'] == 'org.coh.sessionclient.walk'
                and receipt['version_code'] == 2 and receipt['version_name'] == '0.2.0-gates19-21',
                'Original package identity changed')
        require(receipt['test_signer']['certificate_sha256'] == CERTIFICATE_SHA256
                and {key: receipt['test_signer'][key] for key in KEYSTORE_PIN} == KEYSTORE_PIN,
                'Original public test signer identity changed')
        key = repo_root / 'native-android/session-client/app/test-signing/session-test.p12'
        require(identity(key.read_bytes()) == KEYSTORE_PIN, 'Current public test signing key changed')
        require({proof['file'] for proof in host['proofs']} == PROOF_FILES, 'Original proof closure differs')
        for proof in host['proofs']:
            payload = bundle.read(proof['file'])
            require(identity(payload) == {key: proof[key] for key in ('bytes', 'sha256')},
                    'Original proof bytes changed: ' + proof['file'])
            require(json.loads(payload)['passed'] is True, 'Original source proof did not pass')
            selected[proof['file']] = payload
        artifacts = {item['file']: item for item in receipt['artifacts']}
        require(set(artifacts) == set(APK_PINS), 'Original APK closure changed')
        assets = {item['file']: item for item in receipt['assets']}
        for name, expected in APK_PINS.items():
            item = artifacts[name]
            payload = bundle.read(name)
            require(identity(payload) == {key: expected[key] for key in ('bytes', 'sha256')}
                    == {key: item[key] for key in ('bytes', 'sha256')}, 'Pinned APK bytes changed')
            require(item['abi'] == expected['abi'] and item['elf_machine'] == expected['elf_machine']
                    and item['signature_verified'] is True and item['manifest_verified'] is True
                    and item['packaged_fixtures_verified'] is True
                    and item['signer_certificate_sha256'] == CERTIFICATE_SHA256, 'Pinned APK package qualification differs')
            with zipfile.ZipFile(io.BytesIO(payload)) as apk:
                apk_names = archive_entries(apk)
                native = item['native_library']; elf = apk.read(native['file'])
                require(identity(elf) == {key: native[key] for key in ('bytes', 'sha256')}
                        and elf[:6] == b'\x7fELF\x02\x01'
                        and struct.unpack_from('<H', elf, 18)[0] == expected['elf_machine'],
                        'Pinned native library identity changed')
                require({entry[7:] for entry in apk_names if entry.startswith('assets/') and not entry.endswith('/')}
                        == set(assets), 'Packaged asset closure changed')
                for asset, pin in assets.items():
                    require(identity(apk.read('assets/' + asset)) == {key: pin[key] for key in ('bytes', 'sha256')},
                            'Packaged source asset identity changed: ' + asset)
            selected[name] = payload
        selected['build-receipt.json'] = receipt_raw
        selected['source-validation-stage.json'] = host_raw
        selected['SHA256SUMS'] = bundle.read('SHA256SUMS')
        for name in EXTRA_JSON:
            payload = bundle.read(name); document = json.loads(payload)
            if name in assets:
                require(identity(payload) == {key: assets[name][key] for key in ('bytes', 'sha256')},
                        'Retained asset metadata differs from package: ' + name)
            if name in {'accepted-assets-recovery.json', 'source-floor-resolution.json', 'legacy-locomotion-abi-proof.json'}:
                require(document['passed'] is True, 'Retained source metadata did not pass: ' + name)
            selected[name] = payload
        for label in ('arm64', 'emulator-x86_64'):
            signature = 'apk-signature-' + label + '.txt'
            badging = 'apk-badging-' + label + '.txt'
            require(('Signer #1 certificate SHA-256 digest: ' + CERTIFICATE_SHA256)
                    in bundle.read(signature).decode(), 'Retained signer receipt differs')
            require("package: name='org.coh.sessionclient.walk' versionCode='2' versionName='0.2.0-gates19-21'"
                    in bundle.read(badging).decode(), 'Retained manifest receipt differs')
            selected[signature] = bundle.read(signature); selected[badging] = bundle.read(badging)
    return selected, receipt, host


def github_output(path, **values):
    if path:
        with Path(path).open('a') as output:
            for key, value in values.items():
                output.write(key + '=' + ('true' if value else 'false') + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=Path('.'))
    parser.add_argument('--output', type=Path, default=Path('native-android/results/session-client'))
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--guard-only', '--preflight', action='store_true')
    parser.add_argument('--github-output', type=Path)
    args = parser.parse_args()
    output_path = args.github_output or os.environ.get('GITHUB_OUTPUT')
    head = git(args.repo_root, 'rev-parse', 'HEAD').decode().strip()
    decision = guard(args.repo_root, SOURCE_COMMIT, head, os.environ.get('GITHUB_REF'))
    if os.environ.get('GITHUB_SHA') and os.environ['GITHUB_SHA'] != head:
        decision.update(eligible=False, reason='GITHUB_SHA differs from checkout')
    if os.environ.get('GITHUB_REPOSITORY') and os.environ['GITHUB_REPOSITORY'] != 'Russianranger/coh-android':
        decision.update(eligible=False, reason='Workflow belongs to another repository')
    decision.update(schema=1, original_runtime_source_commit=SOURCE_COMMIT, validation_head=head)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'walkable-reuse-guard.json').write_text(json.dumps(decision, indent=2) + '\n')
    github_output(output_path, eligible=decision['eligible'], reused=False)
    if args.guard_only:
        print(json.dumps(decision)); return
    require(decision['eligible'], 'Pinned runtime reuse is forbidden: ' + decision['reason'])
    require(args.archive is not None, '--archive is required for package reuse')
    selected, receipt, host = verify_archive(args.archive, args.repo_root)
    require(all(not (args.output / name).exists() for name in selected),
            'Reuse would overwrite existing source or package evidence')
    for name, raw in selected.items():
        destination = args.output / name
        require(not destination.parent.is_symlink(), 'Reuse destination parent is a symlink')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as output:
            output.write(raw)
    driver = args.repo_root / 'native-android/session-client/tools/emulator_check.py'
    reuse = {
        'schema': 1, 'package_bytes_reused': True,
        'original_runtime_source_commit': SOURCE_COMMIT, 'validation_head': head,
        'validation_workflow_run_id': os.environ.get('GITHUB_RUN_ID'),
        'validation_driver_sha256': hashlib.sha256(driver.read_bytes()).hexdigest(),
        'original_workflow_run_id': WORKFLOW_RUN, 'original_artifact_id': ARTIFACT_ID,
        'original_archive_bytes': ARCHIVE_BYTES, 'original_archive_sha256': ARCHIVE_SHA256,
        'original_build_receipt_sha256': BUILD_RECEIPT_PIN['sha256'],
        'original_host_stage_sha256': HOST_RECEIPT_PIN['sha256'],
        'artifacts': receipt['artifacts'], 'retained_files': sorted(selected),
        'original_source_host_proofs_retained_unchanged': True, 'source_host_tests_rerun': False,
        'original_emulator_results_reused': False, 'new_emulator_acceptance': False,
        'thor_device_execution_verified': False,
        'scope': 'Pinned source/package qualifications only; current driver executes the exact unchanged APK separately',
    }
    (args.output / 'package-reuse-receipt.json').write_text(json.dumps(reuse, indent=2) + '\n')
    github_output(output_path, reused=True)
    print(json.dumps({'reused': True, 'runtime_source_commit': SOURCE_COMMIT, 'retained_files': sorted(selected)}))


if __name__ == '__main__':
    main()
