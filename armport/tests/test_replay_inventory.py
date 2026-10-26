#!/usr/bin/env python3
"""Framing failures must not become successful receive-code evidence."""
import hashlib
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import replay_inventory as replay


def put(data, offset, value, width=4):
    struct.pack_into('<I' if width == 4 else '<Q', data, offset, value)


def initial():
    data = bytearray(89)
    data[:8] = b'COHIRP01'
    for offset, value in ((8, 88), (12, 1), (16, 8), (40, 1), (48, 28), (52, 3)):
        put(data, offset, value)
    data[56:88] = hashlib.sha256(data[88:]).digest()
    return data


def post():
    data = bytearray(64 + 112 + 1 + 96)
    data[:8] = b'COHPRP01'
    for offset, value in ((8, 64), (12, 112), (16, 96), (20, 128),
                          (24, 8 * 1024 * 1024), (32, 30000),
                          (40, 4 * 1024 * 1024), (44, 4096)):
        put(data, offset, value)
    data[64:72] = b'COHMSG01'
    for offset, value in ((8, 112), (12, 1), (16, 8), (24, 3),
                          (32, 500), (40, 1), (48, 32), (56, 2), (64, 1), (68, 2)):
        put(data, 64 + offset, value)
    data[136:168] = hashlib.sha256(data[176:177]).digest()
    data[177:185] = b'COHPEND1'
    for offset, value in ((8, 96), (12, 1), (16, 1), (28, 1),
                          (32, 1), (40, 8), (48, 500), (56, 500)):
        put(data, 177 + offset, value)
    data[241:273] = hashlib.sha256(data[:177]).digest()
    return data


class EnvelopeTests(unittest.TestCase):
    def test_valid_envelopes_preserve_unknown_initial_id_and_post_cursor(self):
        self.assertIsNone(replay.initial(initial())['packet_id'])
        record = replay.post_ready(post())['records'][0]
        self.assertEqual((record['packet_id'], record['post_command_cursor']), (32, 3))

    def test_payload_corruption(self):
        for decoder, data, offset in ((replay.initial, initial(), 88), (replay.post_ready, post(), 176)):
            data[offset] ^= 1
            with self.assertRaisesRegex(ValueError, 'payload SHA-256'):
                decoder(data)

    def test_truncated_or_appended_records(self):
        data = post()
        for malformed in (data[:-1], data + b'\0', data[:64] + data[177:]):
            with self.assertRaises(ValueError):
                replay.post_ready(malformed)

    def test_partial_capture(self):
        for offset, value in ((16, 2), (20, 1), (24, 1), (28, 0)):
            data = post()
            put(data, 177 + offset, value)
            with self.assertRaisesRegex(ValueError, 'incomplete observation'):
                replay.post_ready(data)

    def test_bad_cursor_and_length(self):
        for offset, value in ((12, 0xffffffff), (16, 9), (24, 9), (40, 2)):
            data = initial()
            put(data, offset, value)
            with self.assertRaises(ValueError):
                replay.initial(data)

    def test_metadata_corruption_is_covered_by_prefix_hash(self):
        data = post()
        put(data, 64 + 48, 33)
        with self.assertRaisesRegex(ValueError, 'prefix SHA-256'):
            replay.post_ready(data)


if __name__ == '__main__':
    unittest.main()
