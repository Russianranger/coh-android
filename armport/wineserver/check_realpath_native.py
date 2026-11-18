#!/usr/bin/env python3
"""Native check of the wineserver realpath cache (armport/wineserver/build.sh).

Usage: check_realpath_native.py LIBRARY CHECK_BINARY

Builds a folder tree with links, then resolves the same list of paths with a
process named "wineserver" three ways: glibc alone, the library switched on,
and the library loaded but not switched on. All three must print the same
answers; a process of another name must not use the table at all. Prints one
JSON line with the library's own counters.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

REPORT = 'ARMPORT_REALPATH_CACHE_V1 '


def run(binary, paths, environment, repeat=1):
    result = subprocess.run([str(binary), '--repeat', str(repeat), *paths], env=environment,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    if result.returncode != 0:
        raise SystemExit('check binary failed: %r %r' % (result.returncode, result.stdout[-400:]))
    if result.stderr:
        raise SystemExit('check binary wrote to stderr: %r' % result.stderr[-400:])
    return result.stdout.decode()


def counters(prefix):
    """The one report file "<prefix>.<pid>" of the run that just ended."""
    found = sorted(prefix.parent.glob(prefix.name + '.*'))
    if len(found) != 1 or not found[0].name[len(prefix.name) + 1:].isdigit():
        raise SystemExit('expected one report file: %r' % [path.name for path in found])
    text = found[0].read_text()
    found[0].unlink()
    if not text.startswith(REPORT) or not text.endswith('\n') or text.count('\n') != 1:
        raise SystemExit('unexpected report: %r' % text[:200])
    return {key: int(value) for key, value in (item.split('=') for item in text[len(REPORT):].split())}


def main(argv):
    library, binary = Path(argv[1]).resolve(), Path(argv[2]).resolve()
    work = Path(tempfile.mkdtemp(prefix='realpath-check-'))
    try:
        server, other = work / 'bin/wineserver', work / 'bin/other-program'
        server.parent.mkdir()
        shutil.copy2(binary, server)
        shutil.copy2(binary, other)
        tree = work / 'tree'
        deep = tree / 'a/b/c/d/e/f/g/h'
        deep.mkdir(parents=True)
        files = []
        for index in range(40):
            path = deep / ('file-%02d.bin' % index)
            path.write_bytes(b'x')
            files.append(str(path))
        (tree / 'plain.txt').write_text('x')
        os.symlink('a/b', tree / 'folder-link')                 # a link in the middle of a path
        os.symlink('plain.txt', tree / 'file-link')             # the last component is a link
        os.symlink('missing', tree / 'dangling')
        os.symlink(str(tree), work / 'drive')                   # like dosdevices/z:
        paths = files + [
            str(tree / 'plain.txt'), str(tree / 'file-link'), str(tree / 'dangling'),
            str(tree / 'missing.txt'), str(tree / 'missing-folder/x.txt'),
            str(tree / 'folder-link/c/d/e/f/g/h/file-00.bin'), str(tree / 'folder-link/c'),
            str(work / 'drive/a/b/c/d/e/f/g/h/file-01.bin'), str(work / 'drive/plain.txt'),
            str(tree / 'a/b/../b/c'), str(tree / 'a/./b'), str(tree / 'a/b/'), str(tree / 'a/b/.'),
            str(tree / 'a/b/..'), str(tree) + '//a//b/c', '/', '/proc', 'relative/path',
            '', str(tree / 'plain.txt/x'), str(deep), str(tree / ('n' * 300)),
        ]
        clean = {key: value for key, value in os.environ.items()
                 if key not in ('LD_PRELOAD', 'ARMPORT_REALPATH_CACHE', 'ARMPORT_REALPATH_CACHE_REPORT')}
        report = work / 'report.txt'
        loaded = dict(clean, LD_PRELOAD=str(library))
        cached = dict(loaded, ARMPORT_REALPATH_CACHE='1', ARMPORT_REALPATH_CACHE_REPORT=str(report))
        expected = run(server, paths, clean, repeat=3)
        if 'mismatch' in expected or expected.count('\n') != 2 * len(paths):
            raise SystemExit('unexpected control output')
        if run(server, paths, loaded, repeat=3) != expected:
            raise SystemExit('loaded but not switched on: answers differ')
        written = lambda: sorted(path.name for path in work.glob('report.txt*'))
        if written():
            raise SystemExit('a report was written without the switch')
        if run(other, paths, cached, repeat=3) != expected or written():
            raise SystemExit('another program used the table')
        if run(server, paths, cached, repeat=3) != expected:
            raise SystemExit('switched on: answers differ from glibc')
        found = counters(report)
        # Both forms (allocated and caller's buffer), three rounds.
        if found['calls'] != 6 * len(paths) or found['fast'] + found['passed'] != found['calls']:
            raise SystemExit('counters do not add up: %r' % found)
        if found['fast'] < 6 * len(files) or found['folders'] > len(paths):
            raise SystemExit('the table was not used as expected: %r' % found)
        # A folder that is replaced by a link is noticed once its entry is older than the limit;
        # within it, a file that has gone is still answered by glibc (the last component is probed).
        gone = deep / 'file-39.bin'
        both = run(server, [str(gone)], cached)
        gone.unlink()
        if not both.startswith('ok ') or run(server, [str(gone), str(gone)], cached) != run(server, [str(gone), str(gone)], clean):
            raise SystemExit('a removed file was answered from the table')
        print(json.dumps({'format': 1, 'paths': len(paths), 'rounds': 3, **found}, sort_keys=True))
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main(sys.argv)
