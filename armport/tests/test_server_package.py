#!/usr/bin/env python3
"""Host archive/lineage negatives; synthetic PEs never qualify a server build."""
from __future__ import annotations
import copy
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'armport/app'))
import server_package as package


def pe(tag=b'old', *, imports=('KERNEL32.dll',), machine=0x14c):
    """Small PE32 with real bounded import descriptors for the actual reader."""
    data = bytearray(2048)
    data[:2] = b'MZ'; struct.pack_into('<I', data, 60, 64)
    data[64:68] = b'PE\0\0'
    struct.pack_into('<HH', data, 68, machine, 0)
    struct.pack_into('<H', data, 84, 224)
    optional = 88
    struct.pack_into('<H', data, optional, 0x10b)
    struct.pack_into('<I', data, optional + 28, 0x400000)
    struct.pack_into('<I', data, optional + 60, len(data))
    struct.pack_into('<I', data, optional + 92, 16)
    if imports:
        struct.pack_into('<II', data, optional + 104, 512, (len(imports) + 1) * 20)
        for index, name in enumerate(imports):
            offset = 1024 + index * 64
            struct.pack_into('<5I', data, 512 + index * 20, 0, 0, 0, offset, 1)
            raw = name.encode() + b'\0'; data[offset:offset + len(raw)] = raw
    data[-len(tag):] = tag
    return bytes(data)


class ServerArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.variant = 'retained_progress'
        self.baseline = {'test_fixture': 'exact historical baseline'}
        self.source = {'variant': self.variant, 'baseline_receipt': self.baseline,
                       'patched_sha256': {'actual/source.c': 'a' * 64}}
        self.old = pe(); self.new = pe(b'new')
        self.game = {'source_commit': package.SOURCE, 'data_commit': package.DATA,
                     'repository_commit': '1' * 40, 'test_variant': self.variant,
                     'files': {'MapServer.exe': package.executable_record(self.old),
                               'DbServer.exe': package.executable_record(pe(b'db'))},
                     'historical_receipt': {'original': True}}
        self.game['dependency_report'] = package.dependency_report(self.game['files'])
        self.previous_raw = package.canonical(self.game)
        self.report = package.canonical({'shipping_binary_executed': False, 'scope': 'synthetic reader test'})
        self.cache = b'COH_PG_PERSISTENCE_TESTS:BOOL=OFF\n'
        # Contract/source fixtures are isolated seams. Byte, PE, archive, source
        # invocation and exact donor binding below use production functions.
        self.source_mock = mock.patch.object(package, 'validate_source', side_effect=self.check_source).start()
        self.addCleanup(mock.patch.stopall)
        self.predecessor_mock = mock.patch.object(package, 'validate_predecessor', side_effect=self.check_predecessor).start()
        self.prepared = mock.Mock()
        self.prepared.verify_prepared.side_effect = lambda *_args, **_kwargs: copy.deepcopy(self.source)
        self.prepared.validate_test_report.side_effect = self.check_report
        mock.patch.object(package, 'source_module', return_value=self.prepared).start()
        self.manifest = self.work / 'previous.json'; self.manifest.write_bytes(self.previous_raw)
        self.report_path = self.work / 'source-report.json'; self.report_path.write_bytes(self.report)
        self.cache_path = self.work / 'CMakeCache.txt'; self.cache_path.write_bytes(self.cache)
        self.binaries = self.work / 'binaries'; self.binaries.mkdir()
        (self.binaries / 'MapServer.exe').write_bytes(self.new)
        (self.binaries / 'MapServer.pdb').write_bytes(b'separate symbols fixture')
        self.native = self.work / 'server.zip'
        self.game_archive = self.work / 'old.tar.gz'
        self.files = {'game-package.json': self.previous_raw, 'MapServer.exe': self.old,
                      'DbServer.exe': pe(b'db')}
        package.write_game_archive(self.game_archive, self.files)

    def check_source(self, value, *_args, **_kwargs):
        if value != self.source:
            raise ValueError('Source fixture rejects changed recipe')
        return value

    def check_report(self, document, source, **kwargs):
        package.require(package.canonical(document) == self.report and source == self.source,
                        'Source report identity changed')
        return document

    def check_predecessor(self, raw, variant):
        game = package.parse_json(raw)
        package.require(variant in package.VARIANTS and game.get('test_variant') == variant,
                        'Wrong donor variant')
        return game, copy.deepcopy(self.baseline)

    def build(self, output=None):
        return package.package(self.binaries, self.work / 'prepared', self.cache_path,
            self.manifest, self.report_path, output or self.native, variant=self.variant,
            repository_commit='2' * 40, run_id=123, expected_predecessor_pin=package.pin(self.previous_raw))

    def read(self, **kwargs):
        return package.read_package(self.native, **kwargs)

    def rewrite_zip(self, transform, extra=None):
        with zipfile.ZipFile(self.native) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        transform(files)
        with zipfile.ZipFile(self.native, 'w') as archive:
            for name, data in files.items(): archive.writestr(name, data)
            if extra:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    archive.writestr(*extra)

    def edit_build(self, mutate):
        def change(files):
            value = package.parse_json(files[package.BUILD]); mutate(value)
            files[package.BUILD] = package.canonical(value)
        self.rewrite_zip(change)

    def patch(self, target=None, **kwargs):
        return package.patch_game(self.game_archive, self.native, target or self.work / 'new.tar.gz',
            variant=self.variant, repository_commit='2' * 40, run_id=123, **kwargs)

    def test_both_variants_retain_every_other_byte_and_source_lineage(self):
        for variant in sorted(package.VARIANTS):
            with self.subTest(variant=variant):
                self.variant = variant; self.source['variant'] = variant
                self.game['test_variant'] = variant
                self.previous_raw = package.canonical(self.game)
                self.manifest.write_bytes(self.previous_raw)
                self.files['game-package.json'] = self.previous_raw
                package.write_game_archive(self.game_archive, self.files)
                native = self.work / (variant + '.zip'); self.build(native); self.native = native
                target = self.work / (variant + '.tar.gz'); wrapped = self.patch(target)
                result, files = package.read_game_archive(target)
                self.assertEqual(package.previous_package(wrapped), self.game)
                self.assertEqual(result['historical_receipt'], self.game['historical_receipt'])
                self.assertEqual(files['DbServer.exe'], self.files['DbServer.exe'])
                self.assertEqual(files['MapServer.exe'], self.new)
                self.assertFalse(wrapped[package.WRAPPER]['receipt']['physical_device_validated'])
                self.assertEqual(set(files), set(self.files))
                self.prepared.verify_prepared.assert_called()
                self.source_mock.assert_called()
                self.prepared.validate_test_report.assert_called()

    def test_staging_preserves_order_sensitive_historical_receipts(self):
        nested = {'z_last_alphabetically': 1, 'a_first_alphabetically': 2}
        raw = (json.dumps(nested, indent=2) + '\n').encode()
        self.game['order_sensitive_history'] = {'manifest': nested, 'manifest_sha256': package.digest(raw)}
        self.previous_raw = json.dumps(self.game).encode()
        self.manifest.write_bytes(self.previous_raw)
        self.files['game-package.json'] = self.previous_raw
        package.write_game_archive(self.game_archive, self.files)
        self.build(); target = self.work / 'new.tar.gz'; self.patch(target)
        game, _ = package.read_game_archive(target)
        retained = package.previous_package(game)['order_sensitive_history']
        actual_raw = (json.dumps(retained['manifest'], indent=2) + '\n').encode()
        self.assertEqual(package.digest(actual_raw), retained['manifest_sha256'])
        # This is the historical events-progress validator's encoding contract.
        self.assertNotEqual(package.digest((json.dumps(retained['manifest'], sort_keys=True, indent=2) + '\n').encode()),
                            retained['manifest_sha256'])

    def test_zip_and_game_outputs_are_deterministic(self):
        self.build(); second = self.work / 'second.zip'; self.build(second)
        self.assertEqual(self.native.read_bytes(), second.read_bytes())
        one = self.work / 'one.tar.gz'; two = self.work / 'two.tar.gz'
        self.patch(one); self.patch(two)
        self.assertEqual(one.read_bytes(), two.read_bytes())

    def test_wrong_variant_commit_or_run_rejected(self):
        self.build()
        for arguments in ({'variant': 'thor_certified_startup'}, {'repository_commit': '3' * 40}, {'run_id': 124}):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError): self.read(**arguments)

    def test_new_import_and_wrong_machine_rejected_from_actual_pe(self):
        for data in (pe(b'new', imports=('KERNEL32.dll', 'USER32.dll')), pe(b'new', machine=0xaa64)):
            with self.subTest(pin=package.pin(data)), self.assertRaises(ValueError):
                (self.binaries / 'MapServer.exe').write_bytes(data)
                self.build()
            self.assertFalse(self.native.exists())

    def test_changed_binary_or_untrue_import_record_rejected(self):
        self.build()
        self.rewrite_zip(lambda files: files.__setitem__('MapServer.exe', pe(b'tampered')))
        with self.assertRaisesRegex(ValueError, 'bytes or imports'): self.read()

    def test_changed_source_recipe_and_baseline_rejected(self):
        for key in ('patched_sha256', 'baseline_receipt'):
            with self.subTest(key=key):
                self.native.unlink(missing_ok=True); self.build()
                self.edit_build(lambda value: value['build_input'].__setitem__(key, {'changed': True}))
                with self.assertRaisesRegex(ValueError, 'Source fixture'): self.read()

    def test_retained_ancestry_or_non_map_replacement_rejected(self):
        self.build()
        self.edit_build(lambda value: value['files'].__setitem__('DbServer.exe', self.game['files']['DbServer.exe']))
        with self.assertRaisesRegex(ValueError, 'Only MapServer'): self.read()
        self.native.unlink(); self.build()
        self.edit_build(lambda value: value['predecessor'].__setitem__('canonical_sha256', '0' * 64))
        with self.assertRaisesRegex(ValueError, 'predecessor binding'): self.read()

    def test_authenticated_predecessor_pin_is_required(self):
        self.manifest.write_bytes(self.previous_raw + b' ')
        with self.assertRaisesRegex(ValueError, 'Authenticated donor'): self.build()
        self.assertFalse(self.native.exists())

    def test_equivalent_json_with_different_raw_parent_is_rejected_at_staging(self):
        self.build()
        self.files['game-package.json'] += b'\n'
        package.write_game_archive(self.game_archive, self.files)
        with self.assertRaisesRegex(ValueError, 'exact build predecessor'): self.patch()
        self.assertFalse((self.work / 'new.tar.gz').exists())

    def test_wrong_donor_binary_and_unlisted_member_rejected(self):
        self.build()
        for name, data in (('MapServer.exe', pe(b'wrong old')), ('unexpected.dll', pe())):
            with self.subTest(name=name):
                files = dict(self.files); files[name] = data
                package.write_game_archive(self.game_archive, files)
                with self.assertRaises(ValueError): self.patch()
                self.assertFalse((self.work / 'new.tar.gz').exists())

    def test_source_report_does_not_claim_shipping_execution(self):
        self.report_path.write_bytes(b'{"shipping_binary_executed":true}')
        with self.assertRaisesRegex(ValueError, 'shipping binary'): self.build()
        self.assertFalse(self.native.exists())

    def test_source_report_identity_is_checked_after_repinning(self):
        self.build()
        def mutate(files):
            files[package.CHECKS] = package.canonical({'shipping_binary_executed': False, 'wrong_source': True})
            value = package.parse_json(files[package.BUILD])
            value['source_test_report'] = package.pin(files[package.CHECKS])
            files[package.BUILD] = package.canonical(value)
        self.rewrite_zip(mutate)
        with self.assertRaisesRegex(ValueError, 'Source report identity'): self.read()

    def test_missing_duplicate_or_linked_zip_member_rejected(self):
        for failure in ('missing', 'duplicate', 'linked', 'extra'):
            with self.subTest(failure=failure):
                self.native.unlink(missing_ok=True); self.build()
                if failure == 'missing':
                    self.rewrite_zip(lambda files: files.pop(package.CHECKS))
                elif failure == 'duplicate':
                    self.rewrite_zip(lambda files: None, ('MapServer.exe', self.new))
                elif failure == 'extra':
                    self.rewrite_zip(lambda files: None, ('other.dll', self.new))
                else:
                    entry = zipfile.ZipInfo(package.CHECKS); entry.create_system = 3
                    entry.external_attr = 0o120777 << 16
                    self.rewrite_zip(lambda files: files.pop(package.CHECKS), (entry, b'linked'))
                with self.assertRaises(ValueError): self.read()

    def test_tar_links_duplicate_case_and_traversal_rejected(self):
        for name, kind in (('other.dll', tarfile.SYMTYPE), ('mapserver.exe', tarfile.REGTYPE),
                           ('../escape', tarfile.REGTYPE), ('/absolute', tarfile.REGTYPE)):
            with self.subTest(name=name):
                with tarfile.open(self.game_archive, 'w:gz') as archive:
                    for member, raw in self.files.items():
                        info = tarfile.TarInfo(member); info.size = len(raw)
                        archive.addfile(info, io.BytesIO(raw))
                    info = tarfile.TarInfo(name); info.type = kind; info.linkname = 'MapServer.exe'
                    info.size = 1 if kind == tarfile.REGTYPE else 0
                    archive.addfile(info, io.BytesIO(b'x') if info.size else None)
                with self.assertRaises(ValueError): package.read_game_archive(self.game_archive)

    def test_oversized_member_rejected_before_reading(self):
        self.build()
        with mock.patch.object(package, 'MAX_FILE', len(self.new) - 1):
            with self.assertRaisesRegex(ValueError, 'oversized'): self.read()

    def test_duplicate_json_keys_and_nan_rejected(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError): package.parse_json(raw)

    def test_missing_source_verification_and_fixture_off_cannot_publish(self):
        self.prepared.verify_prepared.side_effect = ValueError('source changed')
        with self.assertRaisesRegex(ValueError, 'source changed'): self.build()
        self.assertFalse(self.native.exists())
        self.prepared.verify_prepared.side_effect = lambda *_a, **_kw: self.source
        self.cache_path.write_bytes(b'COH_PG_PERSISTENCE_TESTS:BOOL=ON\n')
        with self.assertRaisesRegex(ValueError, 'fixture mode OFF'): self.build()
        self.assertFalse(self.native.exists())

    def test_output_is_never_replaced_and_failed_stage_leaves_no_output(self):
        self.build()
        with self.assertRaisesRegex(ValueError, 'new path'): self.build()
        target = self.work / 'keep.tar.gz'; target.write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError, 'new path'): self.patch(target)
        self.assertEqual(target.read_bytes(), b'keep')
        self.files['DbServer.exe'] += b'changed'
        package.write_game_archive(self.game_archive, self.files)
        with self.assertRaises(ValueError): self.patch()
        self.assertFalse((self.work / 'new.tar.gz').exists())

    def test_wrapper_projection_rejects_changed_retained_history(self):
        self.build(); wrapped = self.patch()
        wrapped['historical_receipt']['original'] = False
        with self.assertRaisesRegex(ValueError, 'retained package ancestry'): package.previous_package(wrapped)


class HistoricalDonorTests(unittest.TestCase):
    @staticmethod
    def historical_bytes(relative):
        path = ROOT / relative
        return path.read_bytes() if path.is_file() else subprocess.run(
            ['git', 'show', 'HEAD:' + relative], cwd=ROOT, capture_output=True, check=True).stdout

    def test_actual_thor_manifest_uses_existing_startup_contract(self):
        document = json.loads(self.historical_bytes(
            'docs/android-evidence/client-map-startup-0.13.32-publication.json'))
        game = document['complete_preparation']['native_admission']['game_package']
        actual, baseline = package.validate_predecessor(json.dumps(game).encode(), 'thor_certified_startup')
        self.assertEqual(actual, game)
        self.assertEqual(baseline['build_role'], 'map_startup_certified_animation')
        self.assertEqual(baseline['monorail_budget']['contract']['station_preparation_timeout_seconds'], 720)
        with self.assertRaises(ValueError): package.validate_predecessor(json.dumps(game).encode(), 'retained_progress')
        changed = copy.deepcopy(game)
        changed['files']['MapServer.exe']['sha256'] = '0' * 64
        receipt = changed['native_map_startup']['receipt']
        receipt['mapserver']['sha256'] = '0' * 64
        import native_map_startup_contract as contract
        changed['native_map_startup']['receipt_sha256'] = contract.canonical_sha(receipt)
        with self.assertRaisesRegex(ValueError, 'Thor startup native producer'):
            package.validate_predecessor(json.dumps(changed).encode(), 'thor_certified_startup')

    def test_actual_retained_manifest_uses_existing_progress_contract(self):
        relative = 'docs/android-evidence/mapserver-progress-package-36630872719.json'
        path = ROOT / relative
        # The isolated worktree intentionally omits docs; immutable git bytes
        # avoid copying an extra fixture or silently skipping the real donor.
        raw = path.read_bytes() if path.is_file() else subprocess.run(
            ['git', 'show', 'HEAD:' + relative], cwd=ROOT, capture_output=True, check=True).stdout
        game, baseline = package.validate_predecessor(raw, 'retained_progress')
        self.assertEqual(game['files']['MapServer.exe']['sha256'],
                         '52f85c9e2cccfe88eb92f0a2c379a45b14eb997339ce902ed7ba5d470f3690fb')
        self.assertEqual(baseline['build_role'], 'mapserver_progress')
        with self.assertRaises(ValueError): package.validate_predecessor(raw + b' ', 'retained_progress')
        with self.assertRaises(ValueError): package.validate_predecessor(raw, 'thor_certified_startup')


if __name__ == '__main__':
    unittest.main()
