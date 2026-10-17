#!/usr/bin/env python3
"""Offline mutation controls. Pass the retained evidence.zip as sole argument."""
import argparse
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import warnings
import zipfile
import admit

parser = argparse.ArgumentParser()
parser.add_argument('--capture-zip', type=Path, required=True)
args, remaining = parser.parse_known_args()
ARCHIVE = args.capture_zip
sys.argv = [sys.argv[0]] + remaining

class AdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(ARCHIVE) as z:
            cls.original = {i.filename: z.read(i) for i in z.infolist()}

    def assert_archive_refused(self, data, duplicate=None, symlink=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'mutated.zip'
            with warnings.catch_warnings(), zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
                warnings.simplefilter('ignore', UserWarning)
                for name, payload in data.items():
                    if name == symlink:
                        info = zipfile.ZipInfo(name)
                        info.external_attr = (stat.S_IFLNK | 0o777) << 16
                        z.writestr(info, payload)
                    else:
                        z.writestr(name, payload)
                if duplicate:
                    z.writestr(duplicate, data[duplicate])
            with self.assertRaises(admit.AdmissionError):
                admit.validate_archive(path)

    def test_actual_capture_and_frozen_scope(self):
        result = admit.validate_archive(ARCHIVE)
        self.assertEqual(result.active_roots, 33)
        self.assertEqual(result.external_objects, 7)
        self.assertEqual(result.reachable_external, ('_mmayhem_curtain_8_01c',))
        self.assertTrue(result.offline_analysis_only)
        for name in ('live_groups_transaction', 'physical_generation_verified', 'graph_publication_authorized',
                     'actor_publication_authorized', 'renderer_authorized', 'world_authority'):
            self.assertIs(getattr(result, name), False)
        with self.assertRaises(FrozenInstanceError):
            result.world_authority = True

    def test_every_member_byte_mutation_rejected(self):
        for name, original in self.original.items():
            with self.subTest(name=name):
                mutated = dict(self.original)
                mutated[name] = bytes([original[0] ^ 1]) + original[1:] if original else b'x'
                self.assert_archive_refused(mutated)

    def test_every_missing_member_rejected(self):
        for name in self.original:
            with self.subTest(name=name):
                mutated = dict(self.original)
                del mutated[name]
                self.assert_archive_refused(mutated)

    def test_container_ambiguity_and_escape(self):
        self.assert_archive_refused(self.original, duplicate='capture/runtime.cohrts')
        self.assert_archive_refused(self.original, symlink='capture/runtime.cohrts')
        for name in ('../escape', '/absolute', 'capture/../escape', 'capture\\runtime.cohrts'):
            mutated = dict(self.original)
            mutated[name] = b'x'
            self.assert_archive_refused(mutated)

    def test_semantic_bindings_independent_of_hash_seal(self):
        cases = [
            ('capture/snapshot-binding.json', ('cleanup_verified',), False),
            ('capture/snapshot-binding.json', ('asset_generation',), 20261017),
            ('capture/snapshot-binding.json', ('live_groups_transaction',), True),
            ('capture/snapshot-binding.json', ('run_identity', 'file'), '../run-identity.json'),
            ('capture/capture-receipt.json', ('owned_process_groups_absent',), False),
            ('capture/capture-receipt.json', ('renderer_authorized',), True),
            ('capture/capture-receipt.json', ('catalog_exact_equality',), False),
            ('capture/source-identity.json', ('retained_catalog_sha256',), '0' * 64),
            ('capture/run-identity.json', ('orchestration_source_revision',), '0' * 40),
            ('runtime-graph-diagnostic.json', ('capture_pins', 'snapshot_sha256'), '0' * 64),
            ('runtime-graph-diagnostic.json', ('world_authority',), True),
            ('runtime-graph-diagnostic.json', ('captured', 'asan', 'active_roots'), 32),
            ('scope.json', ('native_ready_or_character_ack',), True),
        ]
        for name, keys, value in cases:
            with self.subTest(name=name, keys=keys):
                data = dict(self.original)
                obj = json.loads(data[name])
                target = obj
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = value
                data[name] = json.dumps(obj).encode()
                with self.assertRaises(admit.AdmissionError):
                    admit._bindings(data)

    def test_duplicate_json_and_nonfinite_rejected(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}'):
            with self.assertRaises(admit.AdmissionError):
                admit.decode(raw)

    def test_invalid_zip_and_compressed_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.zip'
            for payload in (b'not a zip', b'\0' * (admit.MAX_ARCHIVE + 1)):
                path.write_bytes(payload)
                with self.assertRaises(admit.AdmissionError):
                    admit.validate_archive(path)

if __name__ == '__main__':
    unittest.main()
