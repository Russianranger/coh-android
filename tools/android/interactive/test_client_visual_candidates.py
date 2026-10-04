"""Bounded exact-leaf discovery checks; no donor or graphics execution claims."""
import hashlib
from pathlib import Path
import struct
import sys
import unittest
from unittest import mock
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent))
import discover_client_visual_candidates as discovery


def pool(flag, rows):
    block = b''.join(struct.pack('<I', len(row)) + row for row in rows)
    return struct.pack('<III', flag, len(rows), len(block)) + block


def fixture(stem='chest_bm_labcoat_01a', *, duplicate=False):
    name = ('texture_library/characters/' + stem + '.texture').encode() + b'\0'
    original = ('texture_library/characters/' + stem + '.dds').encode() + b'\0'
    header_size = 32 + len(original)
    header = struct.pack('<IIII', header_size, 3, 16, 16) + bytes(16) + original
    raw = header + b'dds'
    names = [name, name] if duplicate else [name]
    count = len(names)
    tables_size = 16 + count * 48 + len(pool(0x6789, names)) + len(pool(0x9ABC, [header]))
    rows = b''.join(discovery.inspect_piggs.ENTRY.pack(0x3456, index, len(raw), 0,
        tables_size + index * len(raw), 0, 0, hashlib.md5(raw).digest(), 0) for index in range(count))
    metadata = discovery.inspect_piggs.HEADER.pack(0x123, 2, 2, 16, 48, count) + rows + pool(0x6789, names) + pool(0x9ABC, [header])
    identity = {'archive': 'stage2.pigg', 'source_metadata_bytes': len(metadata),
        'source_metadata_sha256': hashlib.sha256(metadata).hexdigest(),
        'source_archive_bytes': tables_size + count * len(raw),
        'source_etag': '"frozen"', 'source_last_modified': 'frozen-date'}
    return metadata, identity, raw


class CandidateTests(unittest.TestCase):
    def test_exact_native_stem_selects_one_original_and_verifies_its_cached_header(self):
        meta, identity, raw = fixture()
        with mock.patch.object(discovery, 'partial', return_value=(meta, 'metadata-range')):
            archive, selected = discovery.metadata(identity)
        self.assertEqual(set(selected), {'chest_bm_labcoat_01a'})
        with mock.patch.object(discovery, 'partial', return_value=(raw, 'payload-range')):
            name, record, stored = discovery.texture(selected['chest_bm_labcoat_01a'])
        self.assertEqual(record['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertTrue(record['cached_header_verified'])
        self.assertEqual(stored, raw)
        self.assertEqual(name, 'data/texture_library/characters/chest_bm_labcoat_01a.texture')

    def test_neighboring_name_is_not_speculatively_selected(self):
        meta, identity, _ = fixture('chest_bm_labcoat_01a_other')
        with mock.patch.object(discovery, 'partial', return_value=(meta, 'metadata-range')):
            self.assertEqual(discovery.metadata(identity)[1], {})

    def test_changed_metadata_and_case_collisions_are_refused(self):
        meta, identity, _ = fixture()
        with mock.patch.object(discovery, 'partial', return_value=(meta + b'x', 'metadata-range')):
            with self.assertRaisesRegex(ValueError, 'metadata differs'):
                discovery.metadata(identity)
        meta, identity, _ = fixture(duplicate=True)
        with mock.patch.object(discovery, 'partial', return_value=(meta, 'metadata-range')):
            with self.assertRaisesRegex(ValueError, 'case-colliding'):
                discovery.metadata(identity)

    def test_changed_selected_payload_and_oversized_ranges_are_refused(self):
        meta, identity, raw = fixture()
        with mock.patch.object(discovery, 'partial', return_value=(meta, 'metadata-range')):
            row = discovery.metadata(identity)[1]['chest_bm_labcoat_01a']
        with mock.patch.object(discovery, 'partial', return_value=(raw[:-1] + b'x', 'payload-range')):
            with self.assertRaisesRegex(ValueError, 'size/MD5/cached header'):
                discovery.texture(row)
        with self.assertRaisesRegex(ValueError, 'unbounded or unreviewed'):
            discovery.partial(discovery.BASE_URL + identity['archive'], 0,
                discovery.MAX_METADATA_BYTES + 1, identity)

    def test_compressed_original_stream_retains_zlib_integrity(self):
        meta, identity, raw = fixture()
        with mock.patch.object(discovery, 'partial', return_value=(meta, 'metadata-range')):
            row = discovery.metadata(identity)[1]['chest_bm_labcoat_01a']
        stored = zlib.compress(raw)
        row.update(compressed=True, stored_bytes=len(stored))
        with mock.patch.object(discovery, 'partial', return_value=(stored, 'payload-range')):
            self.assertEqual(discovery.texture(row)[2], stored)
        with mock.patch.object(discovery, 'partial', return_value=(stored + b'trailing', 'payload-range')):
            with self.assertRaisesRegex(ValueError, 'zlib stream differs'):
                discovery.texture(row)


if __name__ == '__main__':
    unittest.main()
