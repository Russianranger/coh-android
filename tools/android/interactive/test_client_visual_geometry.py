"""Native legacy GEO zero-texture tables and material index bounds."""
import struct
import unittest
import zlib

import client_visual_geometry as geometry


def legacy_cached_header(texture_block, texture_id=0):
    names = b'OriginalLegacyModel\0'
    ids = struct.pack('<HH', texture_id, 0)
    model_header = bytearray(140)
    struct.pack_into('<I', model_header, 136, 1)
    model = bytearray(216)
    struct.pack_into('<I', model, 12, 1)  # texture count
    header = (struct.pack('<IIII', 0, len(texture_block), len(names), len(ids))
        + texture_block + names + ids + model_header + model)
    packed = zlib.compress(header)
    return struct.pack('<II', len(packed) + 4, len(header)) + packed


class ClientVisualGeometryTest(unittest.TestCase):
    def test_native_legacy_empty_table_supplies_white_texid_zero(self):
        raw = legacy_cached_header(struct.pack('<II', 0, 0))
        self.assertEqual(geometry.tables(raw), (0,
            [{'name': 'OriginalLegacyModel', 'direct_texture_names': ['white']}]))
        proof = geometry.requested_model_proof(raw, [{'model': 'OriginalLegacyModel'}])
        self.assertEqual(proof['absent_requested_models'], [])
        self.assertFalse(proof['mesh_or_skinning_execution_validated'])

    def test_empty_table_requires_native_count_and_first_slot_space(self):
        with self.assertRaisesRegex(ValueError, 'native white slot'):
            geometry.tables(legacy_cached_header(struct.pack('<I', 0)))

    def test_native_white_fallback_does_not_accept_other_texture_ids(self):
        with self.assertRaisesRegex(ValueError, 'invalid texture ID'):
            geometry.tables(legacy_cached_header(struct.pack('<II', 0, 0), 1))


if __name__ == '__main__':
    unittest.main()
