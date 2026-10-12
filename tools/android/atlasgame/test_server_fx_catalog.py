"""Actual accepted FX BIN conservation and private-install boundary tests.

The test manifest below is deliberately a unit-test fixture. It does not supply
native consumption evidence or qualify publication. Every conversion and install
uses the exact accepted public client FX bytes; the native PE admission alone is
stubbed in private-install tests. A missing real donor is a failure, never a skip.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import server_fx_catalog as fx

DEFAULT_DONOR = ROOT.parent / 'runtime-asset-preflight-cache/payloads/client-caches.zip'
ORIGINAL_PIN = {'bytes': 58505496,
                'sha256': '3b1af6d146db65aa2a00fa9dbe4502776409cdea15f94f717e5455a3cda5fe70'}
PROJECTED_PIN = {'bytes': 3380680,
                 'sha256': 'ab97aa3d9ec2a8edf1ea77d3c807e630e21c3d78555b3650bf80c1025bce8890'}


def digest(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


class ActualFXDonor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        donor = Path(os.environ.get('COH_FX_TEST_CLIENT_CACHES', str(DEFAULT_DONOR)))
        if not donor.is_file():
            raise AssertionError('Exact public client-caches.zip required: ' + str(donor))
        with zipfile.ZipFile(donor) as archive:
            if archive.namelist().count('data/bin/fxinfo.bin') != 1:
                raise AssertionError('Exact single original FX donor member required')
            cls.original = archive.read('data/bin/fxinfo.bin')
        if digest(cls.original) != ORIGINAL_PIN:
            raise AssertionError('Original public FX BIN size/SHA differs')
        cls.full = fx.inspect(cls.original)
        cls.projected, cls.identity = fx.project(cls.original)
        if digest(cls.projected) != PROJECTED_PIN:
            raise AssertionError('Compact public FX projection size/SHA differs')
        cls.compact = fx.inspect(cls.projected)


class StockFXProjectionTests(ActualFXDonor):
    def test_exact_public_donor_and_projection_sha_are_independently_pinned(self):
        self.assertEqual(digest(self.original), ORIGINAL_PIN)
        self.assertEqual(digest(self.projected), PROJECTED_PIN)
        self.assertEqual(len(self.original) - len(self.projected), 55124816)

    def test_all_names_outer_scalars_and_dependencies_conserved_in_order(self):
        self.assertEqual(self.full['identity'], self.compact['identity'])
        self.assertEqual(self.full['names'], self.compact['names'])
        self.assertEqual(len(self.full['rows']), 19607)
        for original, projected in zip(self.full['rows'], self.compact['rows']):
            self.assertEqual(original['prefix'], projected['prefix'])
            self.assertEqual(original['tail'], projected['tail'])
        self.assertEqual(self.full['envelope']['dependencies'], self.compact['envelope']['dependencies'])
        self.assertEqual(self.original[:self.full['root_offset']],
                         self.projected[:self.compact['root_offset']])
        self.assertEqual(self.identity['schema_crc'], '4cb7d9cb')
        self.assertEqual(self.identity['dependency_count'], 19606)
        self.assertEqual(self.identity['dependency_sha256'],
                         '74d70ffdaa69ca89af4e9901b4a62a7d81f6d023887ba3797c572ac8179d68aa')
        self.assertEqual(self.identity['ordered_name_scalar_sha256'],
                         '5aee7bcc70f6c357928209074020f113197fdc0cceb37c7ca3334430341f22f0')

    def test_duplicate_stormkick_is_preserved_and_only_children_are_removed(self):
        duplicates = {name: count for name, count in Counter(
            name.casefold() for name in self.full['names']).items() if count > 1}
        self.assertEqual(duplicates, {'powers/martialarts/stormkick.fx': 2})
        self.assertEqual(self.full['input_records'], 11387)
        self.assertEqual(self.full['condition_records'], 62570)
        self.assertEqual(self.compact['input_records'], 0)
        self.assertEqual(self.compact['condition_records'], 0)
        self.assertEqual(self.compact['identity']['unique_names'], 19606)

    def test_compact_cannot_be_resubmitted_as_original_conversion_input(self):
        with self.assertRaisesRegex(ValueError, 'exact original'):
            fx.project(self.projected)

    def test_changed_scalar_is_structurally_decodable_but_not_qualified(self):
        altered = bytearray(self.projected)
        first_body = self.compact['root_offset'] + 12
        name_bytes = struct.unpack_from('<H', altered, first_body)[0]
        scalar = first_body + ((name_bytes + 2 + 3) & ~3)
        altered[scalar] ^= 1
        raw = bytes(altered)
        self.assertNotEqual(fx.inspect(raw, exact=False)['identity'], self.identity)
        with self.assertRaisesRegex(ValueError, 'Unqualified FX input'):
            fx.inspect(raw)
        with self.assertRaises(ValueError):
            fx.project(raw)

    def test_truncation_and_root_or_outer_bounds_rejected_without_hash_shortcut(self):
        root = self.compact['root_offset']
        changes = [(root, 1), (root + 4, 0), (root + 4, 19608),
                   (root + 8, len(self.projected)), (root + 8, 4)]
        for offset, value in changes:
            altered = bytearray(self.projected)
            struct.pack_into('<I', altered, offset, value)
            with self.subTest(offset=offset, value=value), self.assertRaises(ValueError):
                fx.inspect(bytes(altered), exact=False)
        with self.assertRaises(ValueError):
            fx.inspect(self.projected[:-1], exact=False)

    def test_nonzero_string_padding_and_unsafe_name_rejected(self):
        first_body = self.compact['root_offset'] + 12
        name_bytes = struct.unpack_from('<H', self.projected, first_body)[0]
        padding = (-(name_bytes + 2)) % 4
        self.assertGreater(padding, 0)
        altered = bytearray(self.projected)
        altered[first_body + 2 + name_bytes] = 1
        with self.assertRaisesRegex(ValueError, 'padding'):
            fx.inspect(bytes(altered), exact=False)
        for name in (b'../', b'C:/', b'\\\\/', b'\x00XX'):
            altered = bytearray(self.projected)
            altered[first_body + 2:first_body + 5] = name
            with self.subTest(name=name), self.assertRaises(ValueError):
                fx.inspect(bytes(altered), exact=False)

    def test_child_count_and_nested_extent_rejected_without_exact_hash(self):
        # Locate a real original child rather than inventing a reduced donor.
        cursor = self.full['root_offset'] + 8
        first_child = None
        for row in self.full['rows']:
            length = struct.unpack_from('<I', self.original, cursor)[0]
            body = cursor + 4
            position = body + len(row['prefix'])
            count = struct.unpack_from('<I', self.original, position)[0]
            if count:
                first_child = (position, position + 4)
                break
            position += 4
            count = struct.unpack_from('<I', self.original, position)[0]
            if count:
                first_child = (position, position + 4)
                break
            cursor = body + length
        self.assertIsNotNone(first_child)
        for offset, value in ((first_child[0], 0xffffffff), (first_child[1], 0),
                              (first_child[1], 0xffffffff)):
            altered = bytearray(self.original)
            struct.pack_into('<I', altered, offset, value)
            with self.subTest(offset=offset, value=value), self.assertRaises(ValueError):
                fx.inspect(bytes(altered), exact=False)

    def test_extra_tail_or_file_trailer_rejected_without_exact_hash(self):
        root = self.compact['root_offset']
        altered = bytearray(self.projected + bytes(4))
        struct.pack_into('<I', altered, root, len(altered) - root - 4)
        with self.assertRaisesRegex(ValueError, 'trailing data'):
            fx.inspect(bytes(altered), exact=False)
        altered = bytearray(self.projected)
        first_length = struct.unpack_from('<I', altered, root + 8)[0]
        struct.pack_into('<I', altered, root + 8, first_length + 4)
        with self.assertRaisesRegex(ValueError, 'scalar layout'):
            fx.inspect(bytes(altered), exact=False)


class PrivateFXInstallTests(ActualFXDonor):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.assets = self.root / 'apk-owned-assets'; self.assets.mkdir()
        self.runtime = self.root / ('local-login-server-'+'1'*32); self.runtime.mkdir()
        (self.runtime / 'data/bin').mkdir(parents=True)
        self.target = self.runtime / fx.TARGET
        self.binary = self.runtime / 'MapServer.exe'; self.binary.write_bytes(b'unit-test PE placeholder')
        self.map_package = {'native_monorail': {'receipt_sha256': fx.MONORAIL_RECEIPT}}
        self.manifest = {
            'format': 1, 'role': fx.ROLE, 'repository_commit': 'a' * 40,
            'base': ORIGINAL_PIN, 'projected': PROJECTED_PIN,
            'native_mapserver': fx.MAPSERVER, 'identity': self.identity,
            'native_qualification': {
                'status': fx.QUALIFICATION_STATUS,
                'report': {'bytes': 1, 'sha256': 'b' * 64},
                'indexed_names': 19606, 'native_schema_crc': '4cb7d9cb',
                'all_native_ids_equal': True, 'private_provider_verified': True,
                'shipping_native_changed': False,
                'startup_native_consumer': {'mapserver':{'bytes':42,'sha256':'e'*64},
                    'build_manifest':{'bytes':100,'sha256':'f'*64}, 'preload_processes':2,
                    'normal_full_and_compact_preloads':True,'private_provider_verified':True,
                    'certified_animation_path_observed':True,'physical_timing_validated':False},
            },
            'client_fx_changed': False, 'physical_timing_validated': False,
        }
        (self.assets / fx.PAYLOAD).write_bytes(self.projected)
        self.write_manifest()
        original_file_pin = fx.caches.file_pin
        # All FX payload and target hashes remain real. This fixture substitutes
        # only MapServer PE admission; it is not native qualification evidence.
        def native_only_pin(path):
            return fx.MAPSERVER if Path(path) == self.binary else original_file_pin(path)
        pin_patch = mock.patch.object(fx.caches, 'file_pin', side_effect=native_only_pin)
        self.native_pin = pin_patch.start(); self.addCleanup(pin_patch.stop)
        verifier_patch = mock.patch.object(fx.caches, 'verify_mapserver_compatibility')
        self.native_verifier = verifier_patch.start(); self.addCleanup(verifier_patch.stop)

    def write_manifest(self):
        (self.assets / fx.MANIFEST).write_bytes(fx.canonical(self.manifest))

    def install(self, **arguments):
        return fx.install(self.assets, self.runtime, mapserver_package=self.map_package, **arguments)

    def assert_no_pending(self):
        self.assertEqual(list(self.target.parent.glob('.fx-catalog-*')), [])

    def test_absent_supplement_returns_ordinary_loader_without_touching_runtime(self):
        (self.assets / fx.PAYLOAD).unlink(); (self.assets / fx.MANIFEST).unlink()
        before = sorted(str(path.relative_to(self.runtime)) for path in self.runtime.rglob('*'))
        self.assertEqual(self.install()['status'], 'ordinary_fx_loader')
        self.assertEqual(before, sorted(str(path.relative_to(self.runtime)) for path in self.runtime.rglob('*')))
        self.native_verifier.assert_not_called()

    def test_client_tree_cannot_become_a_projection_target_even_with_native_bytes(self):
        game = self.root/'client-work-fixture'; (game/'data/bin').mkdir(parents=True)
        (game/'data/bin/fxinfo.bin').write_bytes(self.original)
        (game/'MapServer.exe').write_bytes(b'wrong destination admission fixture')
        with self.assertRaisesRegex(ValueError,'server namespace'):
            fx.install(self.assets,game,mapserver_package=self.map_package)
        self.assertEqual(digest((game/'data/bin/fxinfo.bin').read_bytes()),ORIGINAL_PIN)
        self.native_verifier.assert_not_called()

    def test_empty_interrupted_private_bin_is_preserved_for_native_fallback(self):
        self.target.write_bytes(b'')
        before = self.target.stat()
        self.assertEqual(self.install()['status'], 'preserved_existing_fx_native_fallback')
        self.assertEqual(self.target.read_bytes(), b'')
        self.assertEqual((self.target.stat().st_ino, self.target.stat().st_mtime_ns),
                         (before.st_ino, before.st_mtime_ns))
        self.assert_no_pending()

    def test_each_partial_package_is_refused_without_replacing_original(self):
        self.target.write_bytes(self.original)
        for missing in (fx.MANIFEST, fx.PAYLOAD):
            saved = (self.assets / missing).read_bytes(); (self.assets / missing).unlink()
            with self.subTest(missing=missing), self.assertRaises((ValueError, FileNotFoundError)):
                self.install()
            self.assertEqual(digest(self.target.read_bytes()), ORIGINAL_PIN)
            self.assert_no_pending(); (self.assets / missing).write_bytes(saved)

    def test_native_report_is_mandatory_and_cannot_claim_shipping_changes(self):
        proof = self.manifest['native_qualification']
        for key, invalid in (('all_native_ids_equal', False), ('private_provider_verified', False),
                             ('shipping_native_changed', True), ('indexed_names', 19605),
                             ('native_schema_crc', '00000000'), ('status', 'planned')):
            saved = proof[key]; proof[key] = invalid; self.write_manifest()
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'Native FX qualification'):
                self.install()
            self.assertFalse(self.target.exists()); self.assert_no_pending(); proof[key] = saved

    def test_actual_startup_native_pair_and_certificate_use_cannot_be_omitted(self):
        candidate = self.manifest['native_qualification']['startup_native_consumer']
        for key,bad in (('preload_processes',1),('normal_full_and_compact_preloads',False),
                        ('private_provider_verified',False),('certified_animation_path_observed',False),
                        ('physical_timing_validated',True)):
            saved = candidate[key]; candidate[key] = bad; self.write_manifest()
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'startup native'):
                self.install()
            self.assertFalse(self.target.exists());candidate[key] = saved

    def test_typed_candidate_bytes_must_match_the_actual_native_preload_proof(self):
        self.typed_consumer()
        self.manifest['native_qualification']['startup_native_consumer']['mapserver']['sha256'] = 'd'*64
        self.write_manifest()
        with self.assertRaisesRegex(ValueError,'different startup native bytes'): self.install()
        self.assertFalse(self.target.exists())

    def test_unknown_or_duplicate_manifest_fields_fail_closed(self):
        self.manifest['native_freshness_bypass'] = True; self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'identity/scope'):
            self.install()
        del self.manifest['native_freshness_bypass']; self.write_manifest()
        raw = (self.assets / fx.MANIFEST).read_bytes()
        (self.assets / fx.MANIFEST).write_bytes(raw.replace(b'{', b'{"format":1,', 1))
        with self.assertRaisesRegex(ValueError, 'Duplicate manifest key'):
            self.install()
        self.assertFalse(self.target.exists())

    def test_wrong_native_or_mismatched_receipt_cannot_install(self):
        with mock.patch.object(fx.caches, 'file_pin', return_value={'bytes': 1, 'sha256': 'c' * 64}):
            with self.assertRaisesRegex(ValueError, 'exact accepted'):
                self.install()
        self.map_package['native_monorail']['receipt_sha256'] = 'c' * 64
        with self.assertRaisesRegex(ValueError, 'exact accepted'):
            self.install()
        self.assertFalse(self.target.exists()); self.native_verifier.assert_not_called()

    def typed_consumer(self):
        import native_map_startup_contract as startup
        self.map_package['native_map_startup'] = {'receipt': {}, 'receipt_sha256': 'd'*64}
        new_pin = {'bytes':42,'sha256':'e'*64}
        original_pin = fx.caches.file_pin
        def pin_with_new_native(path):
            return new_pin if Path(path) == self.binary else original_pin(path)
        receipt = {'previous_mapserver': dict(fx.MAPSERVER),
                   'build_input': {'retained_sources_sha256':dict(fx.RETAINED_FX_SOURCES)}}
        # These tests isolate FX's additive consumer boundary. The full typed
        # source/PE validator and real native executions have separate gates.
        self.enterContext(mock.patch.object(fx.caches,'file_pin',side_effect=pin_with_new_native))
        self.enterContext(mock.patch.object(startup,'embedded_receipt',return_value=receipt))
        self.enterContext(mock.patch.object(startup,'verify_current_map',return_value={'actual_mapserver_sha256':new_pin['sha256']}))
        return receipt

    def test_typed_startup_consumer_retains_original_fx_control_and_can_install(self):
        self.typed_consumer()
        self.assertEqual(self.install()['status'],'installed_verified_server_fx_projection')
        self.assertEqual(digest(self.target.read_bytes()),PROJECTED_PIN)
        self.assertEqual(self.manifest['native_mapserver'],fx.MAPSERVER)

    def test_typed_startup_cannot_change_original_fx_parser_or_parent_identity(self):
        receipt = self.typed_consumer()
        for field in ('Common/fxinfo.c','libs/UtilitiesLib/src/utils/textparser.c'):
            sources = receipt['build_input']['retained_sources_sha256']; before = sources[field]
            sources[field] = 'f'*64
            with self.subTest(source=field),self.assertRaisesRegex(ValueError,'qualified FX source/parser'):
                self.install()
            self.assertFalse(self.target.exists()); sources[field] = before
        receipt['previous_mapserver']['sha256'] = 'f'*64
        with self.assertRaisesRegex(ValueError,'qualified FX source/parser'):self.install()
        self.assertFalse(self.target.exists())

    def test_payload_corruption_is_refused_before_native_admission(self):
        raw = bytearray(self.projected); raw[-1] ^= 1
        (self.assets / fx.PAYLOAD).write_bytes(raw)
        with self.assertRaisesRegex(ValueError, 'payload differs'):
            self.install()
        self.assertFalse(self.target.exists()); self.native_verifier.assert_not_called()

    def test_missing_private_fx_is_installed_atomically_and_exactly_reused(self):
        result = self.install()
        self.assertEqual(result['status'], 'installed_verified_server_fx_projection')
        self.assertEqual(result['installed_files'], 1)
        self.assertEqual(digest(self.target.read_bytes()), PROJECTED_PIN)
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.target.stat().st_mtime_ns, fx.caches.EPOCH * 10**9)
        before = self.target.stat().st_ino
        reused = self.install()
        self.assertEqual(reused['status'], 'reused_verified_server_fx_projection')
        self.assertEqual(reused['installed_files'], 0)
        self.assertEqual(self.target.stat().st_ino, before); self.assert_no_pending()

    def test_original_private_fx_can_be_replaced_without_prior_hash_read(self):
        self.target.write_bytes(self.original)
        # Force a legitimate first-read atime update: it must not be mistaken for
        # content/inode mutation between admission and the atomic replacement.
        os.utime(self.target, ns=(1, fx.caches.EPOCH * 10**9))
        result = self.install()
        self.assertEqual(result['installed_files'], 1)
        self.assertEqual(digest(self.target.read_bytes()), PROJECTED_PIN)
        self.assert_no_pending()

    def test_unknown_device_generated_bin_is_kept_with_inode_and_mtime(self):
        unknown = b'device-generated ordinary fallback cache'
        self.target.write_bytes(unknown); self.target.chmod(0o600)
        before = self.target.stat()
        result = self.install()
        after = self.target.stat()
        self.assertEqual(result['status'], 'preserved_existing_fx_native_fallback')
        self.assertEqual(result['installed_files'], 0)
        self.assertEqual(self.target.read_bytes(), unknown)
        self.assertEqual((after.st_ino, after.st_mtime_ns, after.st_size, after.st_mode),
                         (before.st_ino, before.st_mtime_ns, before.st_size, before.st_mode))
        self.assert_no_pending()

    def test_larger_unknown_generated_bin_uses_native_fallback_without_projection(self):
        # A valid locally generated cache can grow beyond the accepted original.
        # Its identity is unknown; preserve it instead of silently shrinking it.
        size = ORIGINAL_PIN['bytes'] + 1
        with self.target.open('wb') as stream:
            stream.write(b'unknown native FX cache'); stream.truncate(size)
        before = self.target.stat()
        result = self.install()
        self.assertEqual(result['status'], 'preserved_existing_fx_native_fallback')
        self.assertEqual(result['installed_files'], 0)
        after = self.target.stat()
        self.assertEqual((after.st_ino, after.st_mtime_ns, after.st_size),
                         (before.st_ino, before.st_mtime_ns, size))
        with self.target.open('rb') as stream:
            self.assertEqual(stream.read(23), b'unknown native FX cache')
        self.assert_no_pending()

    def test_target_symlink_and_hardlink_are_refused_without_touching_provider(self):
        provider = self.root / 'original-provider'; provider.write_bytes(self.original)
        self.target.symlink_to(provider)
        with self.assertRaisesRegex(ValueError, 'linked, unowned'):
            self.install()
        self.assertTrue(self.target.is_symlink()); self.target.unlink()
        os.link(provider, self.target); provider.chmod(0o400)
        with self.assertRaisesRegex(ValueError, 'linked, unowned'):
            self.install()
        self.assertEqual(digest(provider.read_bytes()), ORIGINAL_PIN)
        self.assertEqual(provider.stat().st_ino, self.target.stat().st_ino); self.assert_no_pending()

    def test_foreign_owner_is_rejected_using_actual_file_metadata(self):
        self.target.write_bytes(self.original)
        owner = self.target.lstat().st_uid
        with self.assertRaisesRegex(ValueError, 'unowned'):
            fx._regular(self.target, ORIGINAL_PIN['bytes'], owner=owner + 1)
        self.assertEqual(digest(self.target.read_bytes()), ORIGINAL_PIN)

    def test_symlinked_private_directory_or_apk_member_is_refused(self):
        self.target.parent.rmdir(); elsewhere = self.root / 'foreign-bin'; elsewhere.mkdir()
        self.target.parent.symlink_to(elsewhere, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Private FX ancestor'):
            self.install()
        self.assertEqual(list(elsewhere.iterdir()), [])
        self.target.parent.unlink(); self.target.parent.mkdir()
        payload = self.assets / fx.PAYLOAD; payload.unlink()
        original_provider = self.root / 'compact-provider'; original_provider.write_bytes(self.projected)
        payload.symlink_to(original_provider)
        with self.assertRaisesRegex(ValueError, 'linked, unowned'):
            self.install()
        self.assertFalse(self.target.exists())

    def test_interrupted_install_keeps_original_and_removes_temporary_file(self):
        self.target.write_bytes(self.original)
        class Interrupted:
            calls = 0
            def check(self):
                self.calls += 1
                if self.calls == 2:
                    raise RuntimeError('fixture cancellation after staging')
        context = Interrupted()
        with self.assertRaisesRegex(RuntimeError, 'fixture cancellation'):
            self.install(context=context)
        self.assertEqual(context.calls, 2)
        self.assertEqual(digest(self.target.read_bytes()), ORIGINAL_PIN); self.assert_no_pending()

    def test_cancellation_before_staging_does_not_create_target_or_temporary_file(self):
        class Interrupted:
            def check(self):
                raise RuntimeError('fixture cancellation before staging')
        with self.assertRaisesRegex(RuntimeError, 'before staging'):
            self.install(context=Interrupted())
        self.assertFalse(self.target.exists()); self.assert_no_pending()

    def test_target_changed_during_staging_is_preserved_and_not_overwritten(self):
        self.target.write_bytes(self.original)
        target = self.target
        class ConcurrentChange:
            calls = 0
            def check(self):
                self.calls += 1
                if self.calls == 2:
                    target.write_bytes(b'new native generated cache')
        with self.assertRaisesRegex(ValueError, 'changed during'):
            self.install(context=ConcurrentChange())
        self.assertEqual(self.target.read_bytes(), b'new native generated cache'); self.assert_no_pending()

    def test_target_appearing_during_staging_is_preserved_and_not_overwritten(self):
        target = self.target
        class ConcurrentAppearance:
            calls = 0
            def check(self):
                self.calls += 1
                if self.calls == 2:
                    target.write_bytes(b'new native generated cache')
        with self.assertRaisesRegex(ValueError, 'appeared during'):
            self.install(context=ConcurrentAppearance())
        self.assertEqual(self.target.read_bytes(), b'new native generated cache'); self.assert_no_pending()

    def test_game_full_original_and_original_client_cache_archive_are_untouched(self):
        game = self.root / 'private-game/data/bin/fxinfo.bin'; game.parent.mkdir(parents=True)
        game.write_bytes(self.original)
        game_before = game.stat()
        donor = Path(os.environ.get('COH_FX_TEST_CLIENT_CACHES', str(DEFAULT_DONOR)))
        donor_before = donor.stat()
        self.install()
        self.assertEqual(digest(game.read_bytes()), ORIGINAL_PIN)
        self.assertEqual((game.stat().st_ino, game.stat().st_mtime_ns),
                         (game_before.st_ino, game_before.st_mtime_ns))
        self.assertEqual((donor.stat().st_ino, donor.stat().st_mtime_ns, donor.stat().st_size),
                         (donor_before.st_ino, donor_before.st_mtime_ns, donor_before.st_size))
        self.assertEqual(digest(self.target.read_bytes()), PROJECTED_PIN)


if __name__ == '__main__':
    unittest.main()
