#!/usr/bin/env python3
"""Verify the source pin, copy it, then apply the PostgreSQL patch and overlay."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or output == ROOT or ROOT/'upstream' in output.parents:
        parser.error('Use a new output directory outside the immutable snapshots')
    subprocess.run([sys.executable, str(ROOT/'tools/verify_source.py')], check=True)
    lock = json.loads((ROOT/'upstream-lock.json').read_text())
    shutil.copytree(ROOT/lock['destination'], output)
    patch = ROOT/'patches/postgresql/0001-dbserver-postgresql.patch'
    # git apply works without creating a checkout and rejects mismatched contexts.
    env = os.environ.copy()
    # Do not let git discover the enclosing project checkout and silently skip
    # patches when output is a subdirectory such as out/pg-source.
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
        env.pop(name, None)
    env['GIT_CEILING_DIRECTORIES'] = str(output.parent)
    subprocess.run(['git', 'apply', '--check', str(patch)], cwd=output, env=env, check=True)
    subprocess.run(['git', 'apply', str(patch)], cwd=output, env=env, check=True)
    modified = {}
    for line in patch.read_text().splitlines():
        if not line.startswith('+++ b/'):
            continue
        name = line[6:]
        actual = (output/name).read_bytes()
        if actual == (ROOT/lock['destination']/name).read_bytes():
            raise ValueError('Patch did not change expected file: ' + name)
        modified[name] = hashlib.sha256(actual).hexdigest()
    overlay = ROOT/'database/postgresql/overlay'
    receipts = {}
    for path in sorted(overlay.rglob('*')):
        if not path.is_file():
            continue
        target = output/path.relative_to(overlay)
        if target.exists():
            raise ValueError('Overlay must not overwrite an upstream file: ' + str(target))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        receipts[path.relative_to(overlay).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    (output/'postgresql-build-input.json').write_text(json.dumps({
        'source_commit': lock['commit'], 'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(),
        'overlay_sha256': receipts, 'patched_sha256': modified}, indent=2)+'\n')
    print('Prepared PostgreSQL source:', output)

if __name__ == '__main__':
    main()
