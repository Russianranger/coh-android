#!/usr/bin/env python3
"""Single-read offline preparation contract and retained provenance checks."""
import argparse
from dataclasses import FrozenInstanceError
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import admit

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--capture-zip', type=Path, required=True)
args, rest = parser.parse_known_args()
sys.argv = [sys.argv[0]] + rest

class PreparationTests(unittest.TestCase):
    def test_authentic_binding_and_immutable_payload(self):
        prepared = admit.prepare_archive(args.capture_zip)
        b = prepared.binding
        self.assertEqual(b.inventory_sha256, '5affc1a2f00960732f55f3d88d83af8aa60e8dbc1b5b360cc606cb8095262ba1')
        self.assertEqual(b.source_sha256, prepared.admission.source_identity_sha256)
        self.assertEqual(b.catalog_generation, b.asset_generation)
        self.assertEqual(b.asset_generation, 20261016)
        self.assertEqual(b.map_generation, 0)
        self.assertEqual(b.map_sha256, '0' * 64)
        self.assertEqual(admit.digest(prepared.catalog), b.catalog_sha256)
        self.assertEqual(admit.digest(prepared.snapshot), prepared.admission.snapshot_sha256)
        self.assertIs(type(prepared.catalog), bytes)
        self.assertIs(type(prepared.snapshot), bytes)
        with self.assertRaises(FrozenInstanceError):
            prepared.binding = b
        with self.assertRaises(FrozenInstanceError):
            b.map_generation = 1
        self.assertFalse(prepared.admission.world_authority)

    def test_retained_bytes_survive_archive_replacement_without_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'capture.zip'
            shutil.copyfile(args.capture_zip, path)
            original = admit._bindings
            def replace_after_validation(data):
                result = original(data)
                path.write_bytes(b'changed after successful admission')
                return result
            with patch.object(admit, '_bindings', replace_after_validation):
                prepared = admit.prepare_archive(path)
            self.assertEqual(admit.digest(prepared.catalog), prepared.binding.catalog_sha256)
            self.assertEqual(admit.digest(prepared.snapshot), prepared.admission.snapshot_sha256)
            with self.assertRaises(admit.AdmissionError):
                admit.prepare_archive(path)

    def test_refusal_never_replaces_previous_preparation(self):
        retained = admit.prepare_archive(args.capture_zip)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.zip'
            path.write_bytes(b'bad ZIP')
            with self.assertRaises(admit.AdmissionError):
                retained = admit.prepare_archive(path)
        self.assertEqual(retained.admission.active_roots, 33)
        self.assertEqual(retained.admission.reachable_external, ('_mmayhem_curtain_8_01c',))

if __name__ == '__main__':
    unittest.main()
