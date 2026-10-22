#!/usr/bin/env python3
"""Edit the ArmPort patch series as git commits.

  patchwork.py init <dir>    copy upstream/ouroboros to <dir>/src, commit it as
                             "base", then apply each patch in armport/patches/series
                             as one commit named after the patch file.
  patchwork.py export <dir>  write each commit after "base" back to
                             armport/patches/<commit subject> and rewrite series.

Edit with ordinary git in <dir>/src: new commits become new patches (the commit
subject is the patch file name); to change an existing patch, commit a fixup and
run `GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash base` before export.
upstream/ is never modified. <dir> must be outside any other git checkout.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPSTREAM = os.path.join(ROOT, 'upstream', 'ouroboros')
PATCHES = os.path.join(ROOT, 'armport', 'patches')
GIT = ['git', '-c', 'user.name=armport', '-c', 'user.email=armport@localhost',
       '-c', 'core.autocrlf=false']


def git(src, *args, capture=False):
    r = subprocess.run(GIT + list(args), cwd=src, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"git {' '.join(args)} failed:\n{r.stderr}")
    return r.stdout


def series():
    path = os.path.join(PATCHES, 'series')
    if not os.path.exists(path):
        return []
    return [l.strip() for l in open(path) if l.strip() and not l.startswith('#')]


def init(work):
    src = os.path.join(work, 'src')
    if os.path.exists(src):
        sys.exit(f'{src} exists')
    shutil.copytree(UPSTREAM, src, symlinks=True,
                    ignore=shutil.ignore_patterns('data', 'Assets', '.git'))
    git(src, 'init', '-q')
    with open(os.path.join(src, '.git', 'info', 'exclude'), 'a') as f:
        f.write('AutoGen/\n*.StructParser.sources\n')
    git(src, 'add', '-A')
    git(src, 'commit', '-q', '-m', 'base')
    git(src, 'tag', 'base')
    for name in series():
        git(src, 'apply', '--whitespace=nowarn', os.path.join(PATCHES, name))
        git(src, 'add', '-A')
        git(src, 'commit', '-q', '-m', name)
        print('applied', name)


def export(work):
    src = os.path.join(work, 'src')
    commits = git(src, 'rev-list', '--reverse', 'base..HEAD').split()
    names = []
    for c in commits:
        name = git(src, 'log', '-1', '--format=%s', c).strip()
        if not name.endswith('.patch'):
            sys.exit(f'commit {c[:9]} subject must be a patch file name, got {name!r}')
        diff = git(src, 'diff', '--binary', c + '~1', c)
        with open(os.path.join(PATCHES, name), 'w', newline='') as f:
            f.write(diff)
        names.append(name)
    for old in set(series()) - set(names):
        os.remove(os.path.join(PATCHES, old))
        print('removed', old)
    with open(os.path.join(PATCHES, 'series'), 'w') as f:
        f.write(''.join(n + '\n' for n in names))
    print(f'exported {len(names)} patches')


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] not in ('init', 'export'):
        sys.exit(__doc__)
    {'init': init, 'export': export}[sys.argv[1]](sys.argv[2])
