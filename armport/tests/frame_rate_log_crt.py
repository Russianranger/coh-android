"""Patch 0114 must reach the CRT stdout functions, not UtilitiesLib's wrappers.

Compiles the actual armport_frame_rate_log.h after the game's own stdtypes.h
and file.h (where fflush(f) expands to x_fflush(FileWrapper *)), with
incompatible pointer types as an error. A negative control strips the macro
isolation from the same header and must fail to compile.
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--cc', default='/opt/llvm-mingw/bin/aarch64-w64-mingw32-clang')
args = parser.parse_args()
header = (args.source / 'Game/src/graphics/armport_frame_rate_log.h').read_text()
gfx = (args.source / 'Game/src/graphics/gfx.c').read_text()
assert '#include "graphics/armport_frame_rate_log.h"' in gfx and 'armportFrameRateLogWrite(' in gfx
assert 'armportWorkerLogWrite(elapsed)' in gfx and 'armportWorkerLogStart()' in gfx
assert not re.search(r'ARMPORT_FRAME_RATE_V1[^\n]*\n[^\n]*fflush', gfx), 'gfx.c must not flush directly'
TU = '''#include <stdio.h>
#include "utilitieslib/stdtypes.h"
#include "utilitieslib/utils/file.h"
#include "%s"
volatile long armport_wt_sleeps, armport_wt_spin_hits;
int armport_fps_check(void) { if (armportFrameRateLogEnabled()) { armportWorkerLogStart(); armportFrameRateLogWrite(9.5f, 48, 5.05f, 30, 10); armportWorkerLogWrite(5.05f); } return 0; }
'''
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    negative = re.sub(r'^#(pragma (push|pop)_macro|undef)[^\n]*\n', '', header, flags=re.M)
    assert negative != header
    (root / 'negative.h').write_text(negative)
    (root / 'tu.c').write_text(TU % 'graphics/armport_frame_rate_log.h')
    (root / 'tu_negative.c').write_text(TU % 'negative.h')
    def compile(name):
        return subprocess.run([args.cc, '-fsyntax-only', '-Werror=incompatible-pointer-types',
            '-I' + str(args.source / 'libs/UtilitiesLib/include'), '-I' + str(args.source / 'Game/src'),
            '-I' + str(args.source / 'libs'), '-I' + str(root), str(root / name)], capture_output=True, text=True)
    patched, original = compile('tu.c'), compile('tu_negative.c')
    assert patched.returncode == 0, patched.stderr[-2000:]
    assert original.returncode != 0 and "'FileWrapper *'" in original.stderr, 'negative control unexpectedly compiled'
print('frame-rate log: CRT fputs/fflush(stdout) after file.h compiles; un-isolated header fails (FILE * -> FileWrapper *)')
