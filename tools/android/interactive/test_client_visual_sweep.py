"""Safety checks for finite original leaves, model evidence and donor retention."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib

import client_visual_tricks as tricks
import discover_client_visual_sweep as sweep


def original_texture(name='texture_library/test/exact.texture'):
    original = name.removesuffix('.texture') + '.tga'
    header = 32 + len(original) + 1
    raw = struct.pack('<IIII', header, 4, 1, 1) + bytes(16) + original.encode() + b'\0DATA'
    stored = zlib.compress(raw)
    selected = {'path': name, 'offset': 500, 'bytes': len(raw), 'stored_bytes': len(stored),
        'compressed': True, 'md5_table': hashlib.md5(raw).hexdigest(),
        'cached_header_id': 0, 'cached_header': raw[:header],
        'identity': {'archive': 'textures.pigg', 'source_archive_bytes': 10000,
            'source_etag': '"fixed"', 'source_last_modified': 'Sun, 28 Sep 2025 02:23:40 GMT',
            'source_metadata_sha256': '1' * 64}}
    return selected, raw, stored


def encoded_member(path, name):
    with zipfile.ZipFile(path) as archive, Path(path).open('rb') as stream:
        info = archive.getinfo(name)
        stream.seek(info.header_offset)
        header = stream.read(30)
        fields = struct.unpack('<IHHHHHIIIHH', header)
        stream.seek(fields[-2] + fields[-1], 1)
        return stream.read(info.compress_size)


class ClientVisualSweepTest(unittest.TestCase):
    def test_payload_name_rejects_unreviewed_or_traversal_inputs(self):
        for value in ('data/object_library/fx/exact.geo', 'data/player_library/bf_glove.geo',
                'data/texture_library/npcs/exact.texture'):
            self.assertTrue(sweep.safe_payload(value))
        for value in ('data/object_library/../bad.geo', 'data/defs/foo.geo',
                'data/player_library/UPPER.geo', 'data/player_library/a\\b.geo',
                'data/object_library/a.texture', '/data/player_library/a.geo'):
            self.assertFalse(sweep.safe_payload(value))

    def test_original_payload_requires_size_md5_and_cached_header(self):
        selected, raw, stored = original_texture()
        record = sweep.verified_payload(selected, stored)
        self.assertEqual(record['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertTrue(record['cached_header_verified'])
        changed = dict(selected, md5_table='0' * 32)
        with self.assertRaises(ValueError):
            sweep.verified_payload(changed, stored)
        changed = dict(selected, cached_header=b'wrong')
        with self.assertRaises(ValueError):
            sweep.verified_payload(changed, stored)

    def test_original_compressed_stream_rejects_trailing_data(self):
        selected, _, stored = original_texture()
        changed = dict(selected, stored_bytes=len(stored) + 1)
        with self.assertRaises(ValueError):
            sweep.verified_payload(changed, stored + b'!')

    def test_bounded_neighbor_range_keeps_actual_download_and_member_receipts(self):
        first, _, one = original_texture('texture_library/test/one.texture')
        second, _, two = original_texture('texture_library/test/two.texture')
        second['offset'] = first['offset'] + len(one) + 10
        names = ('data/texture_library/test/one.texture', 'data/texture_library/test/two.texture')
        groups, gaps = sweep.payload_groups(dict(zip(names, (first, second))))
        self.assertEqual((len(groups), gaps), (1, 10))
        downloaded = one + bytes(10) + two
        receipt = f"bytes {first['offset']}-{second['offset'] + len(two) - 1}/10000"
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(sweep.ranges, 'partial', return_value=(downloaded, receipt)) as transfer:
                records = dict(sweep.materialize_group(groups[0], directory))
            transfer.assert_called_once()
            self.assertEqual(records[names[0]]['source_content_range'],
                f"bytes {first['offset']}-{first['offset'] + len(one) - 1}/10000")
            self.assertEqual(records[names[1]]['source_download_content_range'], receipt)
            self.assertEqual(records[names[0]]['source_download_sha256'],
                hashlib.sha256(downloaded).hexdigest())
            with patch.object(sweep.ranges, 'partial', side_effect=AssertionError('unexpected fresh transfer')):
                self.assertEqual(dict(sweep.materialize_group(groups[0], directory)), records)

    def test_neighbor_group_does_not_cross_gap_range_or_archive_bounds(self):
        first, _, _ = original_texture('texture_library/test/one.texture')
        second, _, _ = original_texture('texture_library/test/two.texture')
        second['offset'] = first['offset'] + first['stored_bytes'] + sweep.MAX_RANGE_GAP + 1
        groups, gaps = sweep.payload_groups({'first': first, 'second': second})
        self.assertEqual((len(groups), gaps), (2, 0))
        second['offset'] = first['offset'] + first['stored_bytes']
        second['identity'] = dict(second['identity'], archive='other.pigg')
        groups, gaps = sweep.payload_groups({'first': first, 'second': second})
        self.assertEqual((len(groups), gaps), (2, 0))

    def test_native_all_slot_closure_preserves_existing_leaves(self):
        parsed = tricks.parse_texture_tricks_text('''Texture X_Ground
Base1 ground
Mask mask
BumpMap1 bump
Fallback
UseFallback 1
Base fallback
End
End
''', 'upstream/i24/data/tricks/exact.txt')
        index = {'x_ground': parsed}
        files = {f'texture_library/{name}.texture': {'bytes': 10, 'stored_bytes': 8}
            for name in ('ground', 'mask', 'bump', 'fallback')}
        requests = {'textures': {'x_ground': [{'scope': 'observed', 'target': 'X_Ground'}]}}
        result = sweep.plan(files, requests, {'data/texture_library/ground.texture'}, index)
        self.assertEqual(set(result['selected']), {f'data/texture_library/{name}.texture'
            for name in ('mask', 'bump', 'fallback')})
        self.assertEqual(result['unresolved_dependencies'], [])
        self.assertIn('x_ground', result['stock_composite_aliases'])

    def test_absent_native_leaf_and_ambiguous_stem_are_not_substituted(self):
        result = sweep.plan({}, {'textures': {'missing': [{'scope': 'observed', 'target': 'missing'}]}}, set(), {})
        self.assertEqual(result['selected'], {})
        self.assertEqual(result['unresolved_dependencies'][0]['target'], 'missing')
        files = {f'texture_library/{sub}/same.texture': {'bytes': 10, 'stored_bytes': 8}
            for sub in ('a', 'b')}
        with self.assertRaises(ValueError):
            sweep.plan(files, {'textures': {'same': [{'scope': 'observed', 'target': 'same'}]}}, set(), {})

    def test_missing_filename_does_not_invent_model_requests(self):
        proof = {'requested_models': [], 'absent_requested_models': [], 'model_table_sha256': '1' * 64}
        row = {'cached_header': b'header', 'bytes': 100, 'stored_bytes': 50}
        request = {'geometry': {'data/object_library/fx/test.geo': [{'scope': 'observed_startup_missing_geometry'}]}}
        with patch.object(sweep.geometry, 'requested_model_proof', return_value=proof), \
                patch.object(sweep.geometry, 'tables', return_value=(8, [{'name': 'OriginalModel',
                    'direct_texture_names': ['direct']}])):
            result = sweep.plan({'object_library/fx/test.geo': row}, request, set(), {})
        self.assertEqual(result['requested_model_proof']['data/object_library/fx/test.geo']['requested_models'], [])
        self.assertEqual(result['unresolved_dependencies'][0]['target'], 'direct')

    def test_rejected_original_geo_header_is_an_explicit_unselected_gap(self):
        request = {'geometry': {'data/object_library/fx/test.geo': [{'scope': 'observed_startup_missing_geometry'}]}}
        with patch.object(sweep.geometry, 'requested_model_proof', side_effect=ValueError('invalid original table')):
            result = sweep.plan({'object_library/fx/test.geo': {'cached_header': b'bad'}}, request, set(), {})
        self.assertEqual(result['selected'], {})
        self.assertEqual(result['unresolved_dependencies'][0]['kind'], 'geometry_header')

    def test_composition_keeps_accepted_encoded_stream_and_adds_original_stream(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            old_name, new_name = 'data/player_library/old.geo', 'data/texture_library/test/exact.texture'
            old_raw = b'accepted original payload' * 50
            baseline = directory / 'baseline.zip'
            with zipfile.ZipFile(baseline, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
                archive.writestr(old_name, old_raw)
            selected, raw, stored = original_texture()
            record = sweep.verified_payload(selected, stored)
            (directory / hashlib.sha256(new_name.encode()).hexdigest()).write_bytes(stored)
            output = directory / 'output.zip'
            sweep.write_extended_zip(output, baseline, {'files': {old_name: sweep.pin_bytes(old_raw)}},
                {new_name: record}, directory)
            self.assertEqual(encoded_member(output, old_name), encoded_member(baseline, old_name))
            self.assertEqual(encoded_member(output, new_name), stored[2:-4])
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.read(old_name), old_raw)
                self.assertEqual(archive.read(new_name), raw)


if __name__ == '__main__':
    unittest.main()
