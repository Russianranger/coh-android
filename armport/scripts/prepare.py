#!/usr/bin/env python3
"""Make a patched copy of the original source for the ARM64 build.

Copies upstream/ouroboros (without game data) to <out>/src and applies the
patches listed in armport/patches/series, in order, with `git apply`.
upstream/ itself is never modified.

  python3 armport/scripts/prepare.py --out /tmp/armport-build
"""
import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPSTREAM = os.path.join(ROOT, 'upstream', 'ouroboros')
PATCHES = os.path.join(ROOT, 'armport', 'patches')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--force', action='store_true', help='replace an existing copy')
    a = ap.parse_args()
    src = os.path.join(a.out, 'src')
    if os.path.exists(src):
        if not a.force:
            sys.exit(f'{src} exists; use --force to replace it')
        shutil.rmtree(src)
    shutil.copytree(UPSTREAM, src, symlinks=True,
                    ignore=shutil.ignore_patterns('data', 'Assets', '.git'))
    series = os.path.join(PATCHES, 'series')
    names = []
    if os.path.exists(series):
        names = [l.strip() for l in open(series) if l.strip() and not l.startswith('#')]
    for name in names:
        path = os.path.join(PATCHES, name)
        r = subprocess.run(['git', 'apply', '--whitespace=nowarn', '-p1',
                            path], cwd=src, capture_output=True, text=True)
        if r.returncode:
            sys.exit(f'patch {name} failed:\n{r.stderr}')
        print('applied', name)
    print(f'prepared {src} with {len(names)} patches')


if __name__ == '__main__':
    main()
