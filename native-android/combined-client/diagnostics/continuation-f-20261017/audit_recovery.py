#!/usr/bin/env python3
"""Read-only byte audit of preserved worktrees against pinned Git trees.

This classifies bytes, never qualification or semantic equivalence. Historical
commit IDs can differ after publication; actual Git blob bytes remain decisive.
No checkout, fetch, index update, command execution from old files or mutation of
the old directory occurs. Missing Git trees refuse instead of fetching.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

PREFIXES = ('native-android', '.github/workflows', 'tools')
TREES = ('worker-a', 'worker-b', 'worker-c', 'worker-d', 'worker-e', 'worker-f',
         'integration', 'published')
MAX_FILES = 8192
MAX_FILE_BYTES = 128 * 1024 * 1024


def git(root, *args):
    return subprocess.check_output(['git', '--no-replace-objects', '-C', str(root), *args],
                                   env=dict(os.environ, GIT_NO_LAZY_FETCH='1'), timeout=30)


def tree(root, revision):
    result = {}
    for row in git(root, 'ls-tree', '-rz', revision, '--', *PREFIXES).split(b'\0'):
        if row:
            metadata, path = row.split(b'\t', 1)
            mode, kind, digest = metadata.split()
            if kind == b'blob':
                result[path.decode()] = digest.decode()
    return result


def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def classify(path, digest, current, historical):
    if current.get(path) == digest:
        return 'identical_at_pin'
    if (path, digest) in historical:
        return 'remote_history_superseded'
    return 'different_unclassified' if path in current else 'not_at_pin'


def read_regular(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
            raise ValueError('nonregular or oversized audit input')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            data = stream.read(MAX_FILE_BYTES + 1)
        after = os.fstat(descriptor)
        if len(data) != before.st_size or (before.st_dev, before.st_ino, before.st_size,
                before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino,
                after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('audit input changed')
        return data
    finally:
        os.close(descriptor)


def audit(root, old, revision, history_count=100):
    if not 1 <= history_count <= 256:
        raise ValueError('history count bound')
    pinned = git(root, 'rev-parse', '--verify', revision + '^{commit}').decode().strip()
    current = tree(root, pinned)
    revisions = git(root, 'log', '--first-parent', '--format=%H',
                    '--max-count=' + str(history_count), pinned).decode().splitlines()
    historical = {}
    for commit in revisions:
        for path, digest in tree(root, commit).items():
            historical.setdefault((path, digest), commit)
    result = {'schema': 'coh-preserved-worktree-byte-audit-v1', 'source_pin': pinned,
              'scope': list(PREFIXES), 'history_commits_examined': len(revisions),
              'classification_does_not_establish_qualification': True,
              'old_files_executed': False, 'old_files_modified': False,
              'publication_manifests': [], 'trees': {}}
    manifests = sorted([*old.glob('*manifest.json'), *old.glob('publication7/manifest.json')])
    for path in manifests:
        raw = read_regular(path)
        record = json.loads(raw)
        entries = record['entries']
        result['publication_manifests'].append({
            'file': str(path.relative_to(old)), 'sha256': hashlib.sha256(raw).hexdigest(),
            'base': record.get('base'), 'head': record.get('head'), 'entries': len(entries),
            'same_at_current_pin': sum(current.get(r['path']) == r.get('sha') for r in entries),
            'entry_blob_history_classification': dict(Counter(
                classify(r['path'], r['sha'], current, historical) for r in entries))})
    for name in TREES:
        counts, differences, ignored, count = Counter(), [], [], 0
        base = old / name
        for prefix in PREFIXES:
            directory = base / prefix
            if directory.is_symlink():
                raise ValueError('symlink audit directory')
            if not directory.is_dir():
                continue
            for parent, dirs, files in os.walk(directory, followlinks=False):
                dirs[:] = sorted(d for d in dirs if d != '__pycache__' and
                                 not (Path(parent) / d).is_symlink())
                for filename in sorted(files):
                    path = Path(parent) / filename
                    relative = str(path.relative_to(base))
                    if path.is_symlink():
                        ignored.append(relative)
                        continue
                    count += 1
                    if count > MAX_FILES:
                        raise ValueError('worktree audit file bound')
                    data = read_regular(path)
                    digest = blob(data)
                    kind = classify(relative, digest, current, historical)
                    counts[kind] += 1
                    if kind != 'identical_at_pin':
                        row = {'path': relative, 'bytes': len(data), 'blob': digest,
                               'pin_blob': current.get(relative), 'classification': kind}
                        if (relative, digest) in historical:
                            row['historical_commit'] = historical[relative, digest]
                        differences.append(row)
        gitdir = base / '.git'
        raw_gitdir = read_regular(gitdir).decode().strip() if gitdir.is_file() else None
        result['trees'][name] = {'files': count, 'counts': dict(counts),
                                'ignored_symlinks': ignored, 'gitdir_record': raw_gitdir,
                                'different': differences}
    result['files_audited'] = sum(r['files'] for r in result['trees'].values())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True, type=Path)
    parser.add_argument('--preserved-root', required=True, type=Path)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('fresh output required')
    result = audit(args.source_root.resolve(), args.preserved_root.resolve(), args.revision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'source_pin': result['source_pin'],
                      'files_audited': result['files_audited']}))


if __name__ == '__main__':
    main()
