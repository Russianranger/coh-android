#!/usr/bin/env python3
"""Use actual converter, layouts and allocation expressions to test grid overlap.

The negative control changes only the triangle offset back to its pre-0071
expression. Both padded and unpadded disk grids must be corrupted by that
control and preserved by the current source, under ASan/UBSan.
"""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile


def harness(root, original=False):
    anim = (root / 'Common/seq/anim.c').read_text()
    poly = (root / 'libs/UtilitiesLib/include/utilitieslib/components/gridpoly.h').read_text()
    tri = (root / 'Common/gridcoll/ctri.h').read_text()
    prefix = '''#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>
typedef uint8_t U8; typedef uint16_t U16; typedef uint32_t U32;
typedef float F32; typedef float Vec2[2]; typedef float Vec3[3];
#define _WIN64 1
#define GEO_FILE_POLYCELL_SIZE 12
'''
    prefix += re.search(r'typedef struct PolyCell\b.*?} PolyCell;', poly, re.S)[0]
    prefix += tri[tri.index('typedef struct BasicTexture'):tri.index('} CTri;') + len('} CTri;')]
    prefix += '''typedef struct { struct { struct { U32 unpacksize; } grid; } pack;
int tri_count; CTri *ctris; } Model;
'''
    start = anim.index('#define GEO_POLYCELL_NATIVE_RESERVE')
    end = anim.index('\n}', anim.index('static PolyCell *polyCellUnpackFile', start)) + 2
    prefix += anim[start:end] + '\n'
    start = anim.index('    uiGridAllocSize = model->pack.grid.unpacksize;')
    end = anim.index('uiTotalAllocSize =', start)
    end = anim.index(';', end) + 1
    sizes = anim[start:end]
    assignments = re.findall(r'^    model->ctris = \(void\*\)\(\(char\*\)pTotalAlloc \+ [^;]+;', anim, re.M)
    assert len(assignments) == 1  # other assignment is the indented shared-heap path
    assignment = assignments[0]
    if original:
        assignment = assignment.replace('uiGridAllocSize', 'model->pack.grid.unpacksize')
    fixture = Path(__file__).with_name('polycell_allocation_fixture.c').read_text()
    return prefix + fixture.replace('    /* ALLOCATION_SIZES */', sizes).replace('    /* TRIANGLE_START */', assignment)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        c = Path(tmp) / 'control.c'
        exe = Path(tmp) / 'control'
        for original in (True, False):
            c.write_text(harness(args.source, original))
            subprocess.run(['cc', '-g', '-O1', '-fsanitize=address,undefined',
                            '-fno-omit-frame-pointer', str(c), '-o', str(exe)], check=True)
            subprocess.run([str(exe), str(int(not original))], check=True)


if __name__ == '__main__':
    main()
