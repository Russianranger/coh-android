#!/usr/bin/env python3
"""Integrity and boundary checks for the external all-zone original pack."""
import hashlib
import struct
import tempfile
import unittest
from pathlib import Path
import zipfile
import zlib

import prepare_zones_world_assets as zones


class ZonesPackTests(unittest.TestCase):
    def row(self, raw, compressed=False):
        encoded = zlib.compress(raw) if compressed else raw
        return {'path': 'sound/ogg/city/kingsamb1_loop.ogg', 'bytes': len(raw),
                'stored_bytes': len(encoded), 'compressed': compressed,
                'md5_table': hashlib.md5(raw).hexdigest(), 'offset': 1000,
                'cached_header_id': -1, 'cached_header': b'',
                'identity': {'archive': 'stage1.pigg', 'source_archive_bytes': 999999,
                    'source_etag': '"fixed"', 'source_last_modified': 'fixed',
                    'source_metadata_sha256': 'a' * 64}}, encoded

    def page(self, payload=b'original audio'):
        header = b'OggS\x00' + bytes(21) + b'\x01'
        return header + bytes([len(payload)]) + payload

    def test_original_ogg_container_and_zlib_integrity(self):
        raw = self.page() + self.page(b'next page')
        for compressed in (False, True):
            row, encoded = self.row(raw, compressed)
            receipt = zones.verify_payload(row, encoded)
            self.assertEqual(receipt['ogg_container']['pages'], 2)
            self.assertFalse(receipt['ogg_container']['codec_playback_verified'])
            self.assertEqual(receipt['sha256'], hashlib.sha256(raw).hexdigest())
            with self.assertRaises(ValueError):
                zones.verify_payload(row, encoded[:-1])

    def test_malformed_ogg_cannot_be_hidden_by_valid_md5(self):
        for raw in (b'OggS\x00', self.page()[:-1], self.page() + b'trailing'):
            row, encoded = self.row(raw)
            with self.assertRaises(ValueError):
                zones.verify_payload(row, encoded)

    def test_member_path_boundary(self):
        for path in ('data/object_library/city/world.geo', 'data/player_library/model.geo',
                     'data/texture_library/zone/tile.texture', 'data/sound/ogg/5th column/a.ogg'):
            self.assertTrue(zones.safe_payload(path), path)
        for path in ('../data/x.geo', '/data/object_library/x.geo',
                     'data/object_library/../x.geo', 'data\\object_library\\x.geo',
                     'data/object_library/X.geo', 'data/geobin/maps/city.bin',
                     'data/server/db/maps.db', 'data/sound/ogg/x.ogg/../y.ogg'):
            self.assertFalse(zones.safe_payload(path), path)

    def test_zero_model_original_is_not_qualified_geometry(self):
        def original(count):
            model_header = bytearray(140)
            struct.pack_into('<I', model_header, 136, count)
            header = struct.pack('<4I', 0, 8, 0, 0) + bytes(8) + model_header
            packed = zlib.compress(header)
            raw = struct.pack('<4I', len(packed) + 12, 0, 8, len(header)) + packed
            row, encoded = self.row(raw)
            row.update(path='player_library/original_empty_fx.geo', cached_header=raw)
            return row, encoded
        receipt = zones.verify_payload(*original(0))
        self.assertEqual(receipt['original_model_count'], 0)
        self.assertFalse(receipt['model_table_verified'])
        with self.assertRaisesRegex(ValueError, 'Nonzero unsupported'):
            zones.verify_payload(*original(65537))

    def test_zip_duplicate_and_content_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'zone.zip'
            name = 'data/sound/ogg/city/a.ogg'; raw = self.page()
            zones.donor.write_zip_members(path, [(name, raw, raw, zipfile.ZIP_STORED)])
            document = {'archive': zones.pin(path), 'payload_bytes': len(raw),
                'files': {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}}}
            self.assertEqual(zones.verify_archive(path, document)['files_verified'], 1)
            document['files'][name]['sha256'] = '0' * 64
            with self.assertRaises(ValueError):
                zones.verify_archive(path, document)
            duplicate = Path(temporary) / 'duplicate.zip'
            zones.donor.write_zip_members(duplicate, [(name, raw, raw, 0), (name, raw, raw, 0)])
            document['archive'] = zones.pin(duplicate)
            with self.assertRaises(ValueError):
                zones.verify_archive(duplicate, document)


if __name__ == '__main__':
    unittest.main()
