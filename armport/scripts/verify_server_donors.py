#!/usr/bin/env python3
"""Verify the existing retained M3 server donors after artifact/cache restore."""
import argparse
import hashlib
import json
from pathlib import Path
import stat


MANIFEST = Path(__file__).resolve().parents[1] / 'server/donor-inventory.json'


def verify(root, manifest):
    expected = {row['path']: row for row in manifest['files']}
    actual = {}
    if not root.is_dir() or root.is_symlink():
        raise ValueError('donor root is not an ordinary directory')
    for path in root.rglob('*'):
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            continue
        relative = path.relative_to(root).as_posix()
        if not stat.S_ISREG(mode):
            raise ValueError('non-regular donor: ' + relative)
        if relative not in expected or path.stat().st_size != expected[relative]['bytes']:
            raise ValueError('unexpected donor name/size: ' + relative)
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        if digest.hexdigest() != expected[relative]['sha256']:
            raise ValueError('donor digest mismatch: ' + relative)
        actual[relative] = path.stat().st_size
    if actual.keys() != expected.keys():
        raise ValueError('missing donors: ' + ', '.join(sorted(expected.keys() - actual.keys())))
    return dict(files=len(actual), bytes=sum(actual.values()), source_run=manifest['source_run'],
                source_artifact=manifest['source_artifact'], verified=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.root, json.loads(MANIFEST.read_text())), sort_keys=True))
