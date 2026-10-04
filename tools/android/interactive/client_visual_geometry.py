"""Bounded reader for the x86 GEO model/name/TexID tables used by geoLoadStubs.

This verifies header records and direct material-name edges. It never claims
mesh/skinning/graphics execution or that every costume in a GEO is qualified.
"""
from __future__ import annotations
import hashlib
import json
import struct
import zlib


def require(value, message):
    if not value:
        raise ValueError(message)


def region(data, offset, size):
    require(0 <= offset <= len(data) and 0 <= size <= len(data) - offset,
        'Client visual geometry table exceeds original header bounds')
    return data[offset:offset + size]


def u32(data, offset):
    return struct.unpack('<I', region(data, offset, 4))[0]


def name_at(block, offset):
    require(0 <= offset < len(block), 'Client visual geometry name offset is invalid')
    end = block.find(b'\0', offset)
    require(offset < end <= offset + 1024, 'Client visual geometry name lacks a bounded terminator')
    raw = block[offset:end]
    require(all(32 <= value < 127 for value in raw), 'Client visual geometry name is not printable ASCII')
    return raw.decode('ascii')


def names_table(block):
    count = u32(block, 0)
    require(count <= 65536 and 4 + count * 4 <= len(block), 'Client visual packed texture name count differs')
    base = 4 + 4 * count
    return [name_at(block, base + u32(block, 4 + 4 * index)) for index in range(count)]


def tables(raw):
    biased, unpacked = struct.unpack('<II', region(raw, 0, 8))
    if unpacked == 0:
        version, unpacked = struct.unpack('<II', region(raw, 8, 8))
        start, packed = 16, biased - 12
        require(2 <= version <= 8 and version != 6, 'Client visual GEO version is rejected by geoLoadStubs')
    else:
        version, start, packed = 0, 8, biased - 4
    require(0 < unpacked <= 128 * 1024**2 and packed > 0, 'Client visual geometry header exceeds bound')
    decoder = zlib.decompressobj()
    header = decoder.decompress(region(raw, start, packed), unpacked + 1)
    require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
        and len(header) == unpacked, 'Client visual geometry compressed header differs')
    block_count = 5 if 2 <= version <= 6 else 4
    sizes = [u32(header, 4 * index) for index in range(block_count)]
    pos = block_count * 4
    texture_names = names_table(region(header, pos, sizes[1])); pos += sizes[1]
    object_names = region(header, pos, sizes[2]); pos += sizes[2]
    texidx = region(header, pos, sizes[3]); pos += sizes[3]
    if block_count == 5:
        region(header, pos, sizes[4]); pos += sizes[4]
    # ModelHeader has fixed x86 pointer fields:124-byte name,3 four-byte
    # pointer/float fields and the model_count at136; it is read verbatim.
    count = u32(header, pos + 136)
    require(0 < count <= 65536, 'Client visual geometry model count differs')
    region(header, pos, 140); pos += 140
    models = []
    for _ in range(count):
        size = 216 if version < 3 else u32(header, pos)
        name_offset = 80 if version < 3 else 64 if version >= 8 else 60
        require(name_offset + 4 <= size <= 4096, 'Client visual geometry model record size differs')
        record = region(header, pos, size)
        name = name_at(object_names, u32(record, name_offset))
        texture_count = u32(record, 12 if version < 3 else 8)
        texture_offset = u32(record, 36 if version < 3 else 28 if version >= 8 else 24)
        require(texture_count <= 65536, 'Client visual geometry model texture count exceeds bound')
        ids = region(texidx, texture_offset, texture_count * 4)
        selected = []
        for index in range(texture_count):
            texture_id, triangle_count = struct.unpack_from('<HH', ids, index * 4)
            require(texture_id < len(texture_names), 'Client visual geometry model references an invalid texture ID')
            selected.append(texture_names[texture_id])
        models.append({'name': name, 'direct_texture_names': selected})
        pos += size
    require(pos <= len(header), 'Client visual geometry records exceed header')
    return version, models


def requested_model_proof(raw, requests):
    version, models = tables(raw)
    indexed = {}
    for model in models:
        indexed.setdefault(model['name'].split('__', 1)[0].casefold(), []).append(model)
    requested = sorted(set(row['model'] for row in requests if 'model' in row))
    matched, missing = [], []
    for name in requested:
        candidates = indexed.get(name.casefold(), [])
        if not candidates:
            missing.append(name)
        else:
            matched.append({'requested': name, 'matches': candidates})
    canonical = json.dumps(models, sort_keys=True, separators=(',', ':')).encode()
    return {'version': version, 'indexed_model_count': len(models),
        'model_table_sha256': hashlib.sha256(canonical).hexdigest(), 'requested_models': matched,
        'absent_requested_models': missing, 'mesh_or_skinning_execution_validated': False}
