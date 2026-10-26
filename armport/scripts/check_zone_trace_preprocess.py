#!/usr/bin/env python3
"""Check the trace's stdio binding using actual ARM64 compile commands.

The historical header is reconstructed from patch 0048 in a temporary
include directory; no prepared source or upstream file is modified. The
three original traced translation units must use CRT fprintf. tex.c is the
negative control: the historical header must reproduce x_fprintf there.
The current header must use CRT fprintf in all four translation units.
"""
import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HEADER = 'libs/UtilitiesLib/include/utilitieslib/utils/armport_zone_trace.h'
UNITS = {
    'Game/src/clientcomm/clientcomm.c': 'fprintf',
    'Game/src/group/groupnetrecv.c': 'fprintf',
    'Common/group/groupfileload.c': 'fprintf',
    'Game/src/render/tex.c': 'x_fprintf',
}


def historical_header():
    patch = (ROOT / 'armport/patches/0048-game-zone-load-progress-diagnostics.patch').read_text()
    section = patch.split(f'diff --git a/{HEADER} b/{HEADER}\n', 1)[1]
    section = section.split('\ndiff --git ', 1)[0]
    return '\n'.join(line[1:] for line in section.splitlines()
                     if line.startswith('+') and not line.startswith('+++')) + '\n'


def check(row, include, expected, label):
    args = list(row.get('arguments') or shlex.split(row['command']))
    # CMake emits -o <object> and -c <source> for these clang commands.
    output = args.index('-o')
    del args[output:output + 2]
    args.remove('-c')
    args[1:1] = ['-E'] + ([f'-I{include}'] if include else [])
    result = subprocess.run(args, cwd=row['directory'], capture_output=True,
                            text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f'{label}: preprocessing failed\n{result.stderr}')
    function = re.search(r'static void armportZoneTrace\([^\n]+\)\s*\{(.*?)\n\}',
                         result.stdout, re.S)
    call = re.search(r'\b(x_fprintf|fprintf)\s*\(', function.group(1)) if function else None
    actual = call.group(1) if call else None
    if actual != expected:
        raise RuntimeError(f'{label}: expected {expected}, got {actual}')
    print(f'{label}: preprocess_exit=0 callee={actual}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('compile_commands', type=Path)
    args = parser.parse_args()
    rows = json.loads(args.compile_commands.read_text())
    with tempfile.TemporaryDirectory(prefix='armport-trace-') as tmp:
        include = Path(tmp)
        header = include / 'utilitieslib/utils/armport_zone_trace.h'
        header.parent.mkdir(parents=True)
        header.write_text(historical_header())
        for unit, expected in UNITS.items():
            matches = [r for r in rows if Path(r['file']).as_posix().endswith('/' + unit)]
            if len(matches) != 1:
                raise RuntimeError(f'{unit}: expected one compile command, got {len(matches)}')
            row = matches[0]
            if 'aarch64-w64-mingw32' not in str(row):
                raise RuntimeError(f'{unit}: not the ARM64 Windows compile command')
            check(row, include, expected, f'0048 {unit}')
            check(row, None, 'fprintf', f'current {unit}')


if __name__ == '__main__':
    main()
