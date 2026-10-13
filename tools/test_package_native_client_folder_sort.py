"""Archive/provenance guards using the actual audited .36 PE donor.

Changed-image and Win32-proof metadata in unit cases are explicitly synthetic;
these tests do not qualify a native Game build or execute a Windows fixture.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

import package_native_client_folder_sort as package
import test_native_client_folder_sort_source as native

DEFAULT_APK = Path('/workspace/scratch/5d16603ca7ff/publication-037-evidence/COH-Atlas-Gameplay-0.13.36.apk')
DONOR_APK = Path(os.environ.get('COH_PUBLIC036_DONOR_APK', str(DEFAULT_APK)))


class NativeClientFolderPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DONOR_APK.is_file():
            raise ValueError('Exact public .36 donor APK required; use --donor-apk or COH_PUBLIC036_DONOR_APK')
        cls.donor = package.donor(DONOR_APK)
        with zipfile.ZipFile(DONOR_APK) as outer:
            with zipfile.ZipFile(io.BytesIO(outer.read('assets/runtime/client-runtime.zip'))) as archive:
                cls.game = archive.read('CityOfHeroes.exe')
        # This metadata fixture checks the verifier's structure only. It must
        # never be exported as actual Win32 execution evidence.
        cls.proof = native.execute(windows=os.name == 'nt')
        cls.proof['native_windows_executed'] = True
        cls.proof['portable_windows_types_are_adapters'] = False

    def image(self, directory, changed=True):
        path = Path(directory) / 'CityOfHeroes.exe'
        path.write_bytes(self.game + (b'\nSYNTHETIC_UNIT_IMAGE\nCOH_CLIENT_FOLDER_METADATA_SORT_V1\n' if changed else b''))
        return path

    def test_actual_public_donor_has_complete_exact_native_closure(self):
        self.assertEqual(self.donor['native_game']['sha256'], package.GAME_SHA)
        self.assertEqual(self.donor['native_game']['size'], package.GAME_BYTES)
        self.assertEqual(self.donor['native_game']['pe_machine'], 332)
        self.assertEqual(len(self.donor['native_member_closure']), 21)
        self.assertFalse(self.donor['native_donor_rebuilt'])
        self.assertFalse(self.donor['original_archive_or_receipts_rewritten'])

    def test_changed_public_apk_bytes_reject_before_archive_reads(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'donor.apk'
            raw = bytearray(DONOR_APK.read_bytes()); raw[-1] ^= 1; path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, 'independently audited public'):
                package.donor(path)

    def test_original_donor_cannot_be_relabelled_changed_game(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, 'Fresh changed Win32'):
                package.validate_game(self.image(temporary, False), self.donor)

    def test_synthetic_changed_image_uses_actual_donor_import_parser(self):
        with tempfile.TemporaryDirectory() as temporary:
            actual = package.validate_game(self.image(temporary), self.donor)
            self.assertEqual(actual['imports'], self.donor['native_game']['imports'])
            self.assertNotEqual(actual['sha256'], package.GAME_SHA)

    def test_native_import_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = self.image(temporary)
            raw = path.read_bytes()
            self.assertIn(b'cg.dll\0', raw)
            path.write_bytes(raw.replace(b'cg.dll\0', b'xx.dll\0', 1))
            with self.assertRaisesRegex(ValueError, 'DLL/ABI closure differs'):
                package.validate_game(path, self.donor)

    def test_pe64_rejects_even_when_constructor_marker_present(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = self.image(temporary); raw = bytearray(path.read_bytes())
            pe = struct.unpack_from('<I', raw, 60)[0]
            struct.pack_into('<H', raw, pe + 4, 0x8664); path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, 'Win32 x86'):
                package.validate_game(path, self.donor)

    def test_constructor_marker_is_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = self.image(temporary); path.write_bytes(self.game + b'unit changed image')
            with self.assertRaisesRegex(ValueError, 'constructor marker'):
                package.validate_game(path, self.donor)

    def test_executed_fixture_hash_rejects_different_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = self.image(temporary)
            with self.assertRaisesRegex(ValueError, 'fixture bytes differ'):
                package.validate_fixture(copy.deepcopy(self.proof), path)

    def test_portable_fixture_cannot_satisfy_actual_windows_gate(self):
        proof = copy.deepcopy(self.proof); proof['native_windows_executed'] = False
        proof['portable_windows_types_are_adapters'] = True
        with self.assertRaisesRegex(ValueError, 'Genuine Win32'):
            package.validate_fixture(proof)

    def test_boolean_schema_version_is_not_integer_version(self):
        proof = copy.deepcopy(self.proof); proof['format'] = True
        with self.assertRaisesRegex(ValueError, 'Exact current'):
            package.validate_fixture(proof)

    def test_float_case_count_is_not_integer_count(self):
        proof = copy.deepcopy(self.proof); proof['cases'] = 398.0
        with self.assertRaisesRegex(ValueError, 'Exact current'):
            package.validate_fixture(proof)

    def test_numeric_true_is_not_native_parity_evidence(self):
        proof = copy.deepcopy(self.proof); proof['provider_metadata_and_all_links_equal'] = 1
        with self.assertRaisesRegex(ValueError, 'Genuine Win32'):
            package.validate_fixture(proof)

    def test_unknown_current_source_change_is_rejected(self):
        proof = copy.deepcopy(self.proof); proof['source']['patched_sha256'][package.source.SOURCE] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'fixture source differs'):
            package.validate_fixture(proof)

    def test_changed_actual_fixture_harness_is_rejected(self):
        proof = copy.deepcopy(self.proof); proof['harness_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'fixture program differs'):
            package.validate_fixture(proof)

    def test_constructor_fixture_cannot_claim_gameplay_or_publication(self):
        for name in ('native_game_executed', 'native_wine_executed', 'physical_device_executed', 'publication_allowed'):
            with self.subTest(name=name):
                proof = copy.deepcopy(self.proof); proof[name] = True
                with self.assertRaisesRegex(ValueError, 'Genuine Win32'):
                    package.validate_fixture(proof)

    def test_native_abi_and_reallocation_bound_are_explicit(self):
        for name in ('observed_row_bytes', 'possible_realloc_payload_overlap_bytes_before_allocator_overhead'):
            with self.subTest(name=name):
                proof = copy.deepcopy(self.proof); proof[name] += 1
                with self.assertRaisesRegex(ValueError, 'ABI/limit differs'):
                    package.validate_fixture(proof)

    def test_previous_provider_comparison_must_retain_stock_work(self):
        proof = copy.deepcopy(self.proof)
        proof['controlled_insertion_comparison_cases'][2]['last_candidate'] = '0'
        with self.assertRaisesRegex(ValueError, 'Populated-provider'):
            package.validate_fixture(proof)

    def test_extra_native_dll_or_server_cannot_enter_game_artifact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in package.MEMBERS | {package.MANIFEST, 'MapServer.exe'}:
                (root / name).write_text('{}')
            with self.assertRaisesRegex(ValueError, 'member closure differs'):
                package.validate_package(root, 'a' * 40, DONOR_APK)

    def test_missing_native_fixture_cannot_be_omitted_from_artifact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in (package.MEMBERS | {package.MANIFEST}) - {package.FIXTURE}:
                (root / name).write_text('{}')
            with self.assertRaisesRegex(ValueError, 'member closure differs'):
                package.validate_package(root, 'a' * 40, DONOR_APK)

    def test_build_cache_requires_regular_win32_normal_game_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'CMakeCache.txt'
            path.write_text('COH_PG_PERSISTENCE_TESTS:BOOL=ON\nCMAKE_GENERATOR_PLATFORM:INTERNAL=x64\n')
            with self.assertRaisesRegex(ValueError, 'normal Win32 Game'):
                package.validate_cache(path)
            path.write_text('COH_PG_PERSISTENCE_TESTS:BOOL=OFF\nCMAKE_GENERATOR_PLATFORM:INTERNAL=Win32\n')
            self.assertEqual(package.validate_cache(path)['bytes'], path.stat().st_size)

    def test_source_and_actions_identity_are_finite_and_exact(self):
        for commit, run in [('a' * 39, 'https://github.com/Russianranger/coh-android/actions/runs/12'),
            ('a' * 40, 'https://github.com/other/repo/actions/runs/12'),
            ('a' * 40, 'https://github.com/Russianranger/coh-android/actions/runs/0')]:
            with self.subTest(commit=commit, run=run):
                with self.assertRaises(ValueError):
                    package.identity(commit, run)

    def test_synthetic_windows_metadata_can_only_pass_structural_gate(self):
        proof = package.validate_fixture(copy.deepcopy(self.proof))
        self.assertEqual(proof['cases'], 398)
        self.assertFalse(proof['native_game_executed'])
        self.assertFalse(proof['publication_allowed'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--donor-apk', type=Path, required=True)
    args, rest = parser.parse_known_args()
    DONOR_APK = args.donor_apk
    unittest.main(argv=[__file__, *rest])
