#!/usr/bin/env python3
"""One real retained binary comparison; in-memory text changes test differences."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
import zipfile
import compare_bodypart_cache as compare
ROOT = Path(__file__).resolve().parents[3]


class ComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(ROOT / 'native-android/engine/entities/qualification/costume-export-20261017/exact-client-dictionary-bins.zip') as archive:
            cls.cache = archive.read('data/bin/BodyParts.bin')
        cls.source = subprocess.check_output(['git', 'show', 'HEAD:upstream/i24/data/defs/ui/bodyparts.bp'], cwd=ROOT)

    def test_real_retained_bin_matches_original_source(self):
        result = compare.compare(self.cache, self.source, origin='retained-CLIENT')
        self.assertEqual(result['cache_count'], 28)
        self.assertEqual(result['source_count'], 28)
        self.assertTrue(result['ordered_names_match'])
        self.assertTrue(result['all_source_fields_match'])
        self.assertEqual(result['cache']['sha256'], 'b0955c46731ed0cb54ad01d96015b301e583bd0224f8d872f50cfefeb08f6beb')
        self.assertEqual(result['bodyparts_bp']['sha256'], '21aedaa7b4c901a6e6b8a1a7684f343dba675adc0472bdc6053d378ece37558d')

    def test_text_name_change_is_reported(self):
        changed = self.source.replace(b'"Pants"', b'"Other"', 1)
        result = compare.compare(self.cache, changed, origin='retained-CLIENT')
        self.assertFalse(result['ordered_names_match'])
        self.assertIn('0:Name', result['differences'])

    def test_missing_text_row_is_reported(self):
        changed = self.source[:self.source.rfind(b'BodyPart')]
        result = compare.compare(self.cache, changed, origin='retained-CLIENT')
        self.assertEqual(result['source_count'], 27)
        self.assertIn('count', result['differences'])

    def test_original_field_difference_is_reported(self):
        changed = self.source.replace(b'BoneCount\t1', b'BoneCount\t2', 1)
        result = compare.compare(self.cache, changed, origin='retained-CLIENT')
        self.assertIn('0:BoneCount', result['differences'])

    def test_only_dependency_timestamp_is_normalized(self):
        original = compare.dependency_timestamp_identity(self.cache)
        self.assertEqual(original['dependency_timestamps'], [{'path': 'Defs/UI/bodyparts.bp', 'offset': 60, 'bytes': 4, 'raw_timestamp': 1767225600}])
        self.assertEqual(original['timestamp_zeroed_sha256'], '965964f4e58eb24dbb8b85672fb0bdb9631bfc98d938d3d4444aa09a44c67c83')
        changed = bytearray(self.cache); changed[60:64] = bytes([1, 2, 3, 4])
        actual = compare.dependency_timestamp_identity(changed)
        self.assertNotEqual(actual['raw_sha256'], original['raw_sha256'])
        self.assertEqual(actual['timestamp_zeroed_sha256'], original['timestamp_zeroed_sha256'])
        changed = self.cache.replace(b'Pants', b'Other', 1)
        self.assertNotEqual(compare.dependency_timestamp_identity(changed)['timestamp_zeroed_sha256'], original['timestamp_zeroed_sha256'])


if __name__ == '__main__': unittest.main()
