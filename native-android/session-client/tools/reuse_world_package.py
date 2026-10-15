#!/usr/bin/env python3
"""Lease a byte-identical 0.3 package for driver-only qualification changes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

RUNTIME = 'ac840d23026b92455e26a8a50fe4a97d7920f5c2'
ARCHIVE = {'bytes': 7897912, 'sha256': '48cb364da4392af2a782e14fad5ff95e4465a21e6669afe685e61dfb854db36d'}
PACKAGES = {
    'CoH-Native-Session-Client-0.3.0-arm64.apk': {'bytes': 1931361, 'sha256': '75ff158c3e1387671ff2a47f0aa6a126b9c93389fd16685d78a9fcf4ed164639'},
    'CoH-Native-Session-Client-0.3.0-emulator-x86_64.apk': {'bytes': 1951590, 'sha256': '15987156a337bb5c767e49c2fc8e60083c568c6887d39e048cd3222b2b402d05'},
}
ALLOWED = {
    'native-android/session-client/tools/nextbatch_emulator_check.py',
    'native-android/session-client/tools/nextbatch_host_check.py',
    'native-android/session-client/tools/reuse_world_package.py',
    '.github/workflows/native-world-session-client.yml',
}

def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def allowed(path):
    # Only documentation and this batch's result records can accompany the
    # exact driver allowlist. Original evidence used to prepare assets is not
    # exempted: any such change forces a full build.
    return path in ALLOWED or path.startswith('native-android/') and path.endswith('.md') or path.startswith('native-android/evidence/phases22-24/')

def guard(root):
    ancestor = subprocess.run(['git', 'merge-base', '--is-ancestor', RUNTIME, 'HEAD'], cwd=root, capture_output=True)
    if ancestor.returncode:
        return {'eligible': False, 'reason': 'Exact runtime source is not an ancestor'}
    command = ['git', 'diff', '--name-only', RUNTIME, 'HEAD', '--', 'native-android', '.github']
    paths = subprocess.check_output(command, cwd=root, text=True).splitlines()
    rejected = [p for p in paths if not allowed(p)]
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=root, text=True).splitlines()
    return {'eligible': not rejected and not dirty, 'changed_paths': paths, 'rejected_paths': rejected, 'tracked_worktree_dirty': dirty}

def recover(archive, output):
    raw = archive.read_bytes()
    if identity(raw) != ARCHIVE:
        raise ValueError('Original 0.3 build artifact ZIP identity differs')
    output.mkdir(parents=True, exist_ok=True)
    copied = []
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)) or bundle.testzip() is not None or sum(x.file_size for x in bundle.infolist()) > 64*1024*1024:
            raise ValueError('Original artifact closure/integrity differs')
        receipt = json.loads(bundle.read('build-receipt.json'))
        if receipt['passed'] is not True or receipt['source_commit'] != RUNTIME:
            raise ValueError('Original source/build receipt differs')
        for name, pin in PACKAGES.items():
            if identity(bundle.read(name)) != pin:
                raise ValueError('Original package identity differs: ' + name)
            admitted = next(x for x in receipt['artifacts'] if x['file'] == name)
            if {k: admitted[k] for k in ('bytes', 'sha256')} != pin or not all(admitted[k] for k in ('signature_verified', 'manifest_verified', 'packaged_fixtures_verified')):
                raise ValueError('Original package proof differs: ' + name)
        for name in names:
            if name.startswith('emulator-') or name == 'source-validation-stage.json':
                continue  # Never transplant old execution witnesses into a new run.
            target = output / name
            if not target.resolve().is_relative_to(output.resolve()) or target.is_symlink():
                raise ValueError('Unsafe artifact path: ' + name)
            if name.endswith('/'):
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bundle.read(name))
            copied.append(name)
    return copied

def self_test():
    positives = list(ALLOWED) + ['native-android/PHASES22-24.md', 'native-android/evidence/phases22-24/retry.json']
    negatives = ['native-android/session-client/app/src/main/cpp/session_renderer.c', 'native-android/session-client/app/build.gradle', 'native-android/tools/map_fixture/prepare.py', 'native-android/engine/bridge/coh_asset_render.c', 'native-android/evidence/phase9/source-trick-resolution.json', '.github/workflows/native-portable-core.yml', 'native-android/session-client/tools/emulator_check.py']
    assert all(allowed(p) for p in positives) and not any(allowed(p) for p in negatives)
    assert PACKAGES['CoH-Native-Session-Client-0.3.0-arm64.apk']['sha256'] != PACKAGES['CoH-Native-Session-Client-0.3.0-emulator-x86_64.apk']['sha256']
    return {'passed': True, 'admission_cases': len(positives)+len(negatives), 'scope': 'Driver-only path guard; archive and exact package checks execute during recovery'}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root', type=Path, default=Path('.'))
    p.add_argument('--output', type=Path)
    p.add_argument('--guard-only', action='store_true')
    p.add_argument('--github-output', type=Path)
    p.add_argument('--archive', type=Path)
    p.add_argument('--self-test', action='store_true')
    a = p.parse_args()
    if a.self_test:
        print(json.dumps(self_test())); return
    result = guard(a.repo_root.resolve())
    if a.github_output:
        with a.github_output.open('a') as f:
            f.write('eligible=' + str(result['eligible']).lower() + '\n')
    if not a.guard_only:
        if not result['eligible'] or not a.archive or not a.output:
            raise ValueError('Source lease is ineligible or recovery inputs are missing')
        result['copied_files'] = recover(a.archive, a.output)
    result.update({'schema': 1, 'source_runtime_commit': RUNTIME, 'original_run': 38671972824, 'original_artifact': 11945040803, 'archive': ARCHIVE, 'packages': PACKAGES, 'runtime_rebuilt': False, 'old_emulator_witnesses_reused': False})
    if a.output:
        a.output.mkdir(parents=True, exist_ok=True)
        (a.output / 'package-reuse.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))

if __name__ == '__main__':
    main()
