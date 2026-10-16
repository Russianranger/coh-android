#!/usr/bin/env python3
"""Storage-only boundaries: no synthetic record is called an authentic capture."""
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
import delivery as d


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='coh-catalog-delivery-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.catalog = self.root / 'input.cohcat'
        self.manifest = self.root / 'input.json'
        self.output = self.root / 'generation-1'
        # A source-neutral EMPTY envelope; nonempty malformed records deliberately
        # remain a native decoder gate even if transport digest/header match.
        self.raw = b'COHCAT01' + struct.pack('<10I', 1, 48, 48, 7, 0, 0, 10, 20, 0, 0)
        self.catalog.write_bytes(self.raw)
        self.item = {'schema': d.BINDING_SCHEMA,
                     'catalog': {'bytes': len(self.raw), 'sha256': d.digest(self.raw)},
                     'generation': 7,
                     'groups': {'files': 0, 'definitions_crc': 10, 'references_crc': 20,
                                'active_roots': 0, 'receipt_sha256': 'a' * 64},
                     'provenance': {'source_revision': d.SOURCE_REVISION,
                                    'exporter_sha256': d.EXPORTER_SHA256,
                                    'asset_inventory_sha256': 'b' * 64,
                                    'profile_snapshot_sha256': 'c' * 64,
                                    'map_identity_sha256': 'd' * 64,
                                    'capture_receipt_sha256': 'e' * 64}}
        self.write_binding()

    def write_binding(self):
        raw = json.dumps(self.item, sort_keys=True).encode()
        self.manifest.write_bytes(raw)
        self.pin = d.digest(raw)

    def admit(self):
        return d.admit(self.catalog, self.manifest, self.pin, self.output)

    def refused(self):
        with self.assertRaises(d.Refused):
            self.admit()
        self.assertFalse(self.output.exists())

    def test_storage_receipt_never_promotes_authority(self):
        result = self.admit()
        self.assertTrue(result['storage_admitted'])
        for field in ('native_decode_completed', 'provenance_independently_verified',
                      'authentic_capture_established', 'graph_published',
                      'renderer_authorized', 'apk_changed'):
            self.assertIs(result[field], False)
        self.assertEqual((self.output / 'catalog.cohcat').read_bytes(), self.raw)
        self.assertEqual((self.output / 'binding.json').read_bytes(), self.manifest.read_bytes())
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)

    def test_untrusted_pin_refused(self):
        self.pin = 'f' * 64
        self.refused()

    def test_payload_corruption_refused(self):
        self.catalog.write_bytes(self.raw[:-1] + b'\1')
        self.refused()

    def test_corruption_after_inspection_rolls_back(self):
        original = d.inspect_catalog
        def mutate(*args):
            result = original(*args)
            self.catalog.write_bytes(self.raw[:-1] + b'\1')
            return result
        with mock.patch.object(d, 'inspect_catalog', mutate):
            self.refused()

    def test_output_existing_unchanged(self):
        self.output.mkdir()
        marker = self.output / 'keep'
        marker.write_bytes(b'existing')
        with self.assertRaises(d.Refused):
            self.admit()
        self.assertEqual(marker.read_bytes(), b'existing')
        self.assertEqual(list(self.output.iterdir()), [marker])

    def test_write_failure_rolls_back_only_new_directory(self):
        before = {p.name: p.read_bytes() for p in (self.catalog, self.manifest)}
        with mock.patch.object(d, 'emit_json', side_effect=OSError('private detail')):
            with self.assertRaises(OSError):
                self.admit()
        self.assertFalse(self.output.exists())
        self.assertEqual(before, {p.name: p.read_bytes() for p in (self.catalog, self.manifest)})

    def test_catalog_symlink(self):
        other = self.root / 'link'
        other.symlink_to(self.catalog)
        self.catalog = other
        self.refused()

    def test_catalog_hardlink(self):
        os.link(self.catalog, self.root / 'alias')
        self.refused()

    def test_binding_symlink(self):
        other = self.root / 'link'
        other.symlink_to(self.manifest)
        self.manifest = other
        self.refused()

    def test_output_parent_symlink(self):
        other = self.root / 'link'
        other.symlink_to(self.root, target_is_directory=True)
        self.output = other / 'output'
        self.refused()

    def test_header_fields_refused_even_with_new_payload_hash(self):
        # All other header fields are bound or range checked independently of SHA.
        for offset, value in ((8, 2), (12, 49), (16, 49), (20, 0), (20, 8),
                              (24, 1), (28, 65537), (32, 11), (36, 21),
                              (40, 1), (44, 1)):
            with self.subTest(offset=offset, value=value):
                raw = bytearray(self.raw); struct.pack_into('<I', raw, offset, value)
                self.catalog.write_bytes(raw)
                self.item['catalog']['sha256'] = d.digest(raw)
                self.write_binding(); self.refused()

    def test_not_a_native_decoder(self):
        raw = self.raw + b'bad-record'
        raw = raw[:16] + struct.pack('<I', len(raw)) + raw[20:]
        self.catalog.write_bytes(raw)
        self.item['catalog'] = {'bytes': len(raw), 'sha256': d.digest(raw)}
        self.write_binding()
        self.assertFalse(self.admit()['native_decode_completed'])

    def test_binding_missing_extra_and_wrong_type(self):
        cases = []
        for field in self.item:
            altered = copy.deepcopy(self.item); del altered[field]; cases.append(altered)
        altered = copy.deepcopy(self.item); altered['live'] = True; cases.append(altered)
        for bad in (True, 0, -1, 2 ** 32, 1.0, '7', None):
            altered = copy.deepcopy(self.item); altered['generation'] = bad; cases.append(altered)
        for altered in cases:
            with self.subTest(item=altered):
                self.item = altered; self.write_binding(); self.refused()

    def test_provenance_mismatch_and_invalid_digests(self):
        original = copy.deepcopy(self.item)
        for field in original['provenance']:
            self.item = copy.deepcopy(original)
            self.item['provenance'][field] = 'different'
            self.write_binding(); self.refused()

    def test_groups_mutations(self):
        original = copy.deepcopy(self.item)
        for field in ('files', 'definitions_crc', 'references_crc', 'active_roots'):
            self.item = copy.deepcopy(original)
            self.item['groups'][field] += 1
            self.write_binding(); self.refused()

    def test_size_limits(self):
        for size in (0, 47, d.CATALOG_MAX + 1, True, '48'):
            self.item['catalog']['bytes'] = size
            self.write_binding(); self.refused()

    def test_oversized_input_bounded(self):
        with self.catalog.open('wb') as stream:
            stream.truncate(d.CATALOG_MAX + 1)
        self.refused()

    def test_oversized_json_bounded(self):
        self.manifest.write_bytes(b' ' * (d.JSON_MAX + 1))
        self.refused()

    def test_duplicate_json(self):
        raw = self.manifest.read_bytes().replace(b'{', b'{"generation":7,', 1)
        self.manifest.write_bytes(raw); self.pin = d.digest(raw)
        self.refused()

    def test_nonfinite_json(self):
        raw = self.manifest.read_bytes().replace(b'"generation": 7', b'"generation": NaN')
        self.manifest.write_bytes(raw); self.pin = d.digest(raw)
        self.refused()

    def test_refuse_unqualified_binary(self):
        archive = self.root / 'candidate.zip'; archive.write_bytes(b'not a qualified binary')
        with self.assertRaises(d.Refused):
            d.candidate(archive, d.ROOT, self.output)
        self.assertFalse(self.output.exists())

    def test_candidate_commit_rollback(self):
        # This is I/O rollback only. Real archived PE admission runs separately.
        with mock.patch.object(d, 'inspect_candidate', return_value=(b'{}', b'candidate')):
            with mock.patch.object(d, 'emit_json', side_effect=OSError()):
                with self.assertRaises(OSError):
                    d.candidate(self.catalog, d.ROOT, self.output)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
