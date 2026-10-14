"""Bounded x86 GEO PolyCell offset decoder; never relocate disk pointers.

Source: Common/seq/anim.c polyCellUnpack and gridpoly.h at the pinned
Ouroboros commit. Output is acquisition metadata, not runtime collision.
"""
import struct

MAX_BYTES = 4 << 20
MAX_CELLS = 65536
MAX_DEPTH = 64
MAX_REFERENCES = 1 << 20


def decode(raw, triangle_count):
    if not isinstance(raw, bytes) or not 12 <= len(raw) <= MAX_BYTES:
        raise ValueError('grid byte bound')
    if not isinstance(triangle_count, int) or not 1 <= triangle_count <= 65536:
        raise ValueError('triangle count bound')
    cells, active = {}, set()
    references = 0

    def span(offset, size):
        if offset < 0 or size < 0 or offset > len(raw) - size:
            raise ValueError('grid offset span')
        return raw[offset:offset + size]

    def visit(offset, depth):
        nonlocal references
        if offset in active:
            raise ValueError('cyclic grid')
        if depth > MAX_DEPTH:
            raise ValueError('grid depth bound')
        if offset in cells:
            return
        if len(cells) >= MAX_CELLS or offset % 4:
            raise ValueError('grid cell bound/alignment')
        children, indices, count = struct.unpack('<IIi', span(offset, 12))
        if not 0 <= count <= triangle_count or (count and not indices):
            raise ValueError('cell triangle count/pointer')
        if indices % 2 or children % 4:
            raise ValueError('grid array alignment')
        references += count
        if references > MAX_REFERENCES:
            raise ValueError('grid reference bound')
        triangles = list(struct.unpack('<' + 'H' * count, span(indices, count * 2))) if count else []
        if any(i >= triangle_count for i in triangles):
            raise ValueError('absent triangle')
        offsets = list(struct.unpack('<8I', span(children, 32))) if children else [0] * 8
        cells[offset] = {'offset': offset, 'triangles': triangles, 'children': offsets}
        active.add(offset)
        for child in offsets:
            if child:
                visit(child, depth + 1)
        active.remove(offset)

    visit(0, 0)  # Source root is base; zero child offsets are null.
    return {'schema': 1, 'source_layout': 'x86 little-endian PolyCell: 12 bytes',
            'bytes': len(raw), 'cell_count': len(cells),
            'triangle_references': references, 'cells': list(cells.values()),
            'collision_flags_reconstructed': False, 'runtime_collision_qualified': False}
