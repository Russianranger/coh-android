"""Explicit synthetic ALLENTS bodies with source-compatible streaming envelopes.

This does not execute an original character/world serializer. The generated
header is build input, so Android sends the exact host-admitted bytes.
"""
from pathlib import Path
import hashlib
import struct
import zlib


def produce(directory):
    cases = {}
    arrays = []
    for name, prefix in (('single', 966), ('multi', 6000)):
        body = bytearray(65536)
        struct.pack_into('<II', body, 0, 3, 7)  # ALLENTS, full-update ID
        body[8] = 1
        struct.pack_into('<III', body, 9, 0, 123, 456)
        body[21] = 1
        state = 25028
        for at in range(22, 22 + prefix):
            state ^= (state << 13) & 0xffffffff
            state ^= state >> 17
            state ^= (state << 5) & 0xffffffff
            state &= 0xffffffff
            body[at] = state & 255
        compressor = zlib.compressobj(9)
        encoded = body[:4] + struct.pack('<I', len(body) - 4)
        encoded += compressor.compress(body[4:]) + compressor.flush(zlib.Z_SYNC_FLUSH)
        if (name == 'single' and len(encoded) != 1200) or not 1200 <= len(encoded) <= 16384:
            raise ValueError('FRAGMENT_FIXTURE_COMPRESSED_BOUND')
        decoder = zlib.decompressobj()
        if body[:4] + decoder.decompress(encoded[8:]) != body or decoder.unconsumed_tail or decoder.unused_data:
            raise ValueError('FRAGMENT_FIXTURE_ROUNDTRIP')
        if not encoded.endswith(b'\x00\x00\xff\xff'):
            raise ValueError('FRAGMENT_FIXTURE_STREAM_SUFFIX')
        arrays.append('static const uint8_t fragment_initial_' + name + '[]={' + ','.join(map(str, encoded)) + '};')
        cases['fragment-' + name] = {'decoded_bytes': len(body), 'decoded_sha256': hashlib.sha256(body).hexdigest(),
            'compressed_bytes': len(encoded), 'compressed_sha256': hashlib.sha256(encoded).hexdigest(),
            'sibling_count': (len(encoded) + 1199) // 1200, 'first_ordered_id': 1,
            'later_ordered_id': 0, 'part_zero_sent_last': name == 'multi'}
    path = Path(directory) / 'fragment-fixtures.h'
    path.write_text('/* Synthetic bytes only; original-compatible ordered sibling envelopes. */\n' + '\n'.join(arrays) + '\n')
    return {'schema': 'coh-initial-fragment-fixture-v1', 'cases': cases,
            'header_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'zlib_version': zlib.ZLIB_VERSION, 'whole_original_allents_producer': False, 'world_authority': False}
