#!/usr/bin/env python3
"""Verify heap snapshot formatting uses CRT bounds, with a failing old-macro control."""
import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import tempfile


def check(row, source, expected, label):
    args = list(row.get('arguments') or shlex.split(row['command']))
    at = args.index('-o')
    del args[at:at + 2]
    args.remove('-c')
    original = Path(row['file'])
    args[args.index(str(original))] = str(source)
    args[1:1] = ['-E', '-P', '-I' + str(original.parent)]
    result = subprocess.run(args, cwd=row['directory'], capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(label + ': preprocessing failed\n' + result.stderr)
    body = result.stdout.split('static void check_at(', 1)[1]
    # check() stringifies its condition; those diagnostic literals are not calls.
    body = re.sub(r'"(?:\\.|[^"\\])*"', '""', body)
    calls = set(re.findall(r'\b((?:quick_)?(?:vsnprintf|snprintf|sprintf))\s*\(', body))
    if calls != expected:
        raise RuntimeError(f'{label}: expected {sorted(expected)}, got {sorted(calls)}')
    print(f'{label}: preprocess_exit=0 formatting_callees={sorted(calls)}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('compile_commands', type=Path)
    args = parser.parse_args()
    rows = [r for r in json.loads(args.compile_commands.read_text())
            if Path(r['file']).as_posix().endswith('/armport/replay/state.c')]
    if len(rows) != 1:
        raise ValueError('Expected one actual replay state compile command')
    row = rows[0]
    source = Path(row['file'])
    check(row, source, {'vsnprintf', 'snprintf', 'sprintf'}, 'current heap snapshot writer')
    with tempfile.TemporaryDirectory(prefix='armport-state-macro-') as temporary:
        control = Path(temporary) / 'state-control.c'
        text = source.read_text()
        for name in ('vsnprintf', 'snprintf', 'sprintf'):
            text = text.replace('#undef ' + name + '\n', '')
        control.write_text(text)
        check(row, control, {'quick_vsnprintf', 'quick_snprintf', 'quick_sprintf'},
              'negative control without CRT unbinding')


if __name__ == '__main__':
    main()
