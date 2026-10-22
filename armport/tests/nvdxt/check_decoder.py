#!/usr/bin/env python3
"""Check the nvDXT stand-in's DDS decoder (armport/standins/nvdxt) natively,
under ASan/UBSan: Pillow parity for DXT1/3/5, RGBA and RGB with partial edge
blocks, and row-pitch handling (padded rows, and the stale top-level pitch
render/tex.c leaves after skipping mip levels). Needs a host C++ compiler and
Pillow. Prints ::error lines for GitHub and exits 1 on any failure."""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
STANDIN = os.path.join(HERE, '..', '..', 'standins', 'nvdxt', 'nvdxt_standin.cpp')


def dds_rgb(w, h, bpp, pitch, pitch_flag, rows, masks):
    flags = 0x1 | 0x2 | 0x4 | 0x1000 | (0x8 if pitch_flag else 0)
    pf = struct.pack('<8I', 32, 0x40 | (0x1 if masks[3] else 0), 0, bpp, *masks)
    hdr = struct.pack('<7I', 124, flags, h, w, pitch, 0, 0) + b'\0' * 44 + pf + \
        struct.pack('<4I', 0x1000, 0, 0, 0) + b'\0' * 4
    assert len(hdr) == 124
    return b'DDS ' + hdr + b''.join(rows)


def main():
    from PIL import Image
    tmp = tempfile.mkdtemp(prefix='nvdxt-test-')
    exe = os.path.join(tmp, 'decode')
    cxx = os.environ.get('CXX', 'c++')
    subprocess.run([cxx, '-O1', '-g', '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-w',
                    '-I', os.path.join(HERE, 'include'), os.path.join(HERE, 'decode_main.cpp'), STANDIN,
                    '-o', exe], check=True)

    def decode(path):
        r = subprocess.run([exe, path, path + '.raw'], capture_output=True, text=True)
        if r.returncode or r.stderr.strip():
            return None, (r.stdout + r.stderr)[-800:]
        return open(path + '.raw', 'rb').read(), ''

    results = []
    w, h = 37, 22
    img = Image.new('RGBA', (w, h))
    img.putdata([(x * 7 % 256, y * 11 % 256, (x * y) % 256, (x + y) * 5 % 256) for y in range(h) for x in range(w)])
    for fmt in ('DXT1', 'DXT3', 'DXT5', 'RGBA', 'RGB'):
        p = os.path.join(tmp, fmt + '.dds')
        src = img.convert('RGB') if fmt == 'RGB' else img
        src.save(p, **({} if fmt in ('RGBA', 'RGB') else {'pixel_format': fmt}))
        ref = Image.open(p).convert('RGBA')
        ref.load()
        got, err = decode(p)
        same = got is not None and Image.frombytes('RGBA', (w, h), got, 'raw', 'BGRA').tobytes() == ref.tobytes()
        results.append((f'Pillow parity {fmt} {w}x{h}', same, err))

    m24 = (0xff0000, 0xff00, 0xff, 0)
    rows = [bytes([10, 20, 30]), bytes([60, 50, 40])]
    want = bytes([10, 20, 30, 255, 60, 50, 40, 255])
    pitch_cases = {
        'RGB24 1x2, pitch 4 (padded rows)': dds_rgb(1, 2, 24, 4, True, [rows[0] + b'\x63', rows[1]], m24),
        'RGB24 1x2, pitch 3 (unpadded)': dds_rgb(1, 2, 24, 3, True, rows, m24),
        'RGB24 1x2, no pitch flag': dds_rgb(1, 2, 24, 0, False, rows, m24),
        'RGB24 1x2, stale pitch 8 after mip skip': dds_rgb(1, 2, 24, 8, True, rows, m24),
    }
    for name, data in pitch_cases.items():
        p = os.path.join(tmp, 'pitch.dds')
        open(p, 'wb').write(data)
        got, err = decode(p)
        results.append((name, got == want, err or (f'got {list(got)}' if got else '')))

    failed = [r for r in results if not r[1]]
    for name, ok, err in results:
        print(('ok   ' if ok else 'FAIL ') + name + ('' if ok else ': ' + err))
    if failed:
        print('::error title=ArmPort nvDXT decoder::' + '; '.join(n for n, _, _ in failed))
        return 1
    print(f'::notice title=ArmPort nvDXT decoder::{len(results)} checks passed (ASan/UBSan)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
