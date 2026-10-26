#!/usr/bin/env python3
"""Exercise the actual texture-name helper under ASan/UBSan.

The original strncpyt body is used with a host strncpy_s adapter for its valid
positive-capacity contract. This does not test the Windows CRT or GPU rendering.
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
from receiver_tray_state import function


def fixture(source, texture):
    helper = function((source / 'libs/UtilitiesLib/src/utils/utils.c').read_text(),
                      'char *strncpyt(')
    native = function(texture, 'static int texFixName(')
    return r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define TEX_TGA 1
#define TEX_JPEG 2
#define TEX_DDS 4
static int strncpy_s(char *dst, size_t cap, const char *src, size_t count) {
    size_t n = strlen(src); assert(cap > 0 && count < cap);
    if (n > count) n = count;
    memcpy(dst, src, n); dst[n] = 0; return 0;
}
''' + helper + native + r'''
int main(int argc, char **argv) {
    char out[128], alias[256], before[256];
    const char *input = argv[2];
    int cap = atoi(argv[3]), inplace = atoi(argv[1]);
    assert(strlen(input) < sizeof(alias) && cap > 0 && cap <= sizeof(out));
    strcpy(alias, input); strcpy(before, input);
    int type = texFixName(inplace ? alias : input, inplace ? alias : out,
                          inplace ? -1 : cap);
    if (!inplace) assert(!strcmp(input, before));
    printf("%d:%s", type, inplace ? alias : out); return 0;
}
'''


def expected(name, cap, inplace):
    name = name if inplace else name[:cap - 1]
    kind = 0
    if len(name) < 4:
        return '1:' + name
    if name[-4] == '.':
        kind = {'tga': 1, 'jpg': 2, 'dds': 4}.get(name[-3:], 0)
        name = name[:-4]
    elif len(name) >= 8 and name[-8] == '.':
        kind = 4 if name[-7:] == 'texture' else 0
        name = name[:-8]
    return str(kind) + ':' + name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--original', type=Path)
    args = parser.parse_args()
    native = (args.source / 'Game/src/render/tex.c').read_text()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        def build(text, label):
            src = root / (label + '.c'); exe = root / label
            src.write_text(fixture(args.source, text))
            subprocess.run([os.environ.get('CC', 'cc'), '-std=c99', '-O1', '-g',
                            '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer',
                            str(src), '-o', str(exe)], check=True)
            return exe
        fixed = build(native, 'fixed')
        original = build(args.original.read_text(), 'original') if args.original else None
        names = ['', 'x', 'abc', 'blue', 'white', 'yellow', 'missing', 'abcdefgh',
                 '.tga', 'a.tga', 'abc.jpg', 'abc.dds', 'abc.TGA', 'abc.xyz',
                 '.texture', 'white.texture', 'name.unknown', 'Statue_Stone_Detail.tga',
                 'AP_Asphalt_01_NS', 'Male_Statue_Atlas_N',
                 'x' * 127, 'x' * 128, 'x' * 200 + '.dds']
        count = equivalent = 0
        for name in names:
            for inplace, cap in [(0, n) for n in (1, 4, 5, 8, 16, 128)] + [(1, 128)]:
                command = [str(inplace), name, str(cap)]
                result = subprocess.run([str(fixed), *command], capture_output=True, text=True, timeout=10)
                assert result.returncode == 0 and not result.stderr, (command, result.stderr)
                assert result.stdout == expected(name, cap, inplace), (command, result.stdout)
                count += 1
                # Compare only inputs where the original's pointer reads are defined.
                safe = (inplace or len(name) < cap) and (
                    len(name) < 4 or len(name) >= 8 or name[-4] == '.')
                if original and safe:
                    old = subprocess.run([str(original), *command], capture_output=True, text=True, timeout=10)
                    assert old.returncode == 0 and not old.stderr and old.stdout == result.stdout
                    equivalent += 1
        if original:
            for name in ('blue', 'white', 'yellow', 'missing', 'x' * 200):
                old = subprocess.run([str(original), '0', name, '128'], capture_output=True, text=True, timeout=10)
                diagnostic = ('AddressSanitizer: stack-buffer-' if len(name) < 8
                              else 'runtime error: store to address')
                assert old.returncode != 0 and diagnostic in old.stderr, old.stderr
            print(f'Original: four buffer under-reads and one out-of-bounds store reproduced; {equivalent} defined cases identical.')
        print(f'Patched actual texFixName/strncpyt: {count} ASan/UBSan cases pass; copied/in-place, short names, extensions, truncation, source nonmutation.')


if __name__ == '__main__':
    main()
