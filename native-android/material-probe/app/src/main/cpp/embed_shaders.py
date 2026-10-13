#!/usr/bin/env python3
"""Embed the reviewed, source-owned GLSL files without rewriting their contents."""
import pathlib
import sys

root, output = map(pathlib.Path, sys.argv[1:])
entries = [('kSkinVertex', 'skinned_dual.vert'), ('kQuadVertex', 'material_quad.vert'),
           ('kMaterialFragment', 'dual_tint.frag')]
lines = ['/* Generated from reviewed shader files; do not edit. */']
for symbol, name in entries:
    raw = (root / name).read_bytes()
    # Octal byte escapes are unambiguous across following hexadecimal digits.
    lines.append('static const char ' + symbol + '[] =')
    for offset in range(0, len(raw), 64):
        lines.append('    "' + ''.join('\\%03o' % b for b in raw[offset:offset+64]) + '"')
    lines.append('    ;')
output.write_text('\n'.join(lines) + '\n')
