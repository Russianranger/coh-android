"""Missing-only installer rejection/recovery tests and frozen donor model proofs.

Synthetic small installer fixtures make no graphics or Android execution claim.
The separate manifest checks bind the actual reviewed donor/model inventories.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'android/guest'), str(Path(__file__).resolve().parent)]
import client_visual_assets as visual
import client_startup_diagnostic as client
from diagnostic import DiagnosticError
import prepare_client_visual_assets as producer
import client_visual_geometry as geometry


class Context:
    def check(self):
        pass


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.assets, self.work = self.root / 'assets', self.root / 'client-work-fixture'
        self.assets.mkdir(); (self.work / 'data/Player_Library').mkdir(parents=True)
        (self.work / 'data/texture_library').mkdir()
        (self.work / 'data/bin').mkdir(); (self.work / 'data/bin/preserved.bin').write_bytes(b'accepted-cache')
        (self.work / 'client-work.json').write_text('{}')
        self.members = {'data/player_library/fem_boot.geo': b'original-donor-geometry',
            'data/texture_library/gui/tray_ring_power.texture': b'original-donor-texture'}
        self.files = {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            for name, raw in self.members.items()}
        self.document = {'format': 1, 'scope': visual.SCOPE, 'source_commit': client.SOURCE,
            'data_commit': client.DATA, 'file_count': 2, 'payload_bytes': sum(len(v) for v in self.members.values()),
            'files': self.files, 'files_sha256': hashlib.sha256(visual.canonical(self.files)).hexdigest(),
            'installation': 'private_client_worktree_missing_files_only',
            'imported_assets_modified': False, 'prepared_caches_modified': False,
            'existing_supplements_modified': False, 'runtime_visual_validated': False, 'gameplay_validated': False,
            'closure': {'unresolved_dependencies': [], 'absent_requested_models': []}}
        first, second = list(self.files)
        self.baseline = {first: self.files[first]}; self.additions = {second: self.files[second]}
        self.document['visual_extension'] = {'files': {second: [{'scope': 'fixture'}]},
            'file_count': 1, 'payload_bytes': self.files[second]['bytes'], 'missing_only': True,
            'baseline_payloads_preserved': True, 'baseline_file_count': 1,
            'baseline_payload_bytes': self.files[first]['bytes'],
            'baseline_files_sha256': hashlib.sha256(visual.canonical(self.baseline)).hexdigest()}
        self.write_archive(self.members)
        self.document['archive'] = {'filename': visual.ARCHIVE, **producer.pin(self.assets / visual.ARCHIVE)}
        self.repin()
        self.patches = mock.patch.multiple(visual, ARCHIVE_SHA256=self.document['archive']['sha256'],
            ARCHIVE_BYTES=self.document['archive']['bytes'], MANIFEST_SHA256=self.manifest_sha,
            FILE_COUNT=2, PAYLOAD_BYTES=self.document['payload_bytes'], FILES_SHA256=self.document['files_sha256'],
            BASE_FILE_COUNT=1, BASE_PAYLOAD_BYTES=self.files[first]['bytes'],
            BASE_FILES_SHA256=self.document['visual_extension']['baseline_files_sha256'],
            EXTENSION_FILE_COUNT=1, EXTENSION_PAYLOAD_BYTES=self.files[second]['bytes'],
            EXTENSION_FILES_SHA256=hashlib.sha256(visual.canonical(self.additions)).hexdigest())
        self.patches.start(); self.addCleanup(self.patches.stop); self.addCleanup(self.temporary.cleanup)

    def write_archive(self, members, *, bad_mode=False, duplicate=False):
        with zipfile.ZipFile(self.assets / visual.ARCHIVE, 'w') as archive:
            for name, raw in members.items():
                entry = zipfile.ZipInfo(name)
                entry.create_system = 3; entry.external_attr = ((stat.S_IFLNK if bad_mode else stat.S_IFREG) | 0o444) << 16
                archive.writestr(entry, raw)
            if duplicate:
                name = next(iter(members)); archive.writestr(name, members[name])

    def repin(self):
        raw = visual.canonical(self.document)
        (self.assets / visual.MANIFEST).write_bytes(raw)
        self.manifest_sha = hashlib.sha256(raw).hexdigest()

    def run_install(self):
        return visual.install(self.work, self.assets, Context())

    def target(self, name):
        return self.work / name.replace('player_library', 'Player_Library')

    def test_first_install_and_exact_warm_reuse_preserve_cache_and_directory_case(self):
        directory = (self.work / 'data/Player_Library').stat().st_ino
        first = self.run_install()
        self.assertEqual(first['installed_files'], 2)
        self.assertFalse(first['fingerprint_reused'])
        with mock.patch.object(visual.zipfile, 'ZipFile', side_effect=AssertionError('Warm decode forbidden')):
            warm = self.run_install()
        self.assertTrue(warm['fingerprint_reused'])
        self.assertEqual((warm['archive_read_bytes'], warm['decoded_files']), (0, 0))
        self.assertEqual((self.work / 'data/Player_Library').stat().st_ino, directory)
        self.assertFalse((self.work / 'data/player_library').exists())
        self.assertEqual((self.work / 'data/bin/preserved.bin').read_bytes(), b'accepted-cache')
        for name, raw in self.members.items():
            self.assertEqual(self.target(name).read_bytes(), raw)
            self.assertEqual(stat.S_IMODE(self.target(name).stat().st_mode), 0o444)

    def test_conflicting_existing_leaf_is_preserved(self):
        name = next(iter(self.members)); target = self.target(name)
        target.write_bytes(b'x' * self.files[name]['bytes']); target.chmod(0o444)
        os.utime(target, (client.CACHE_EPOCH, client.CACHE_EPOCH))
        with self.assertRaisesRegex((ValueError, DiagnosticError), 'conflicts'):
            self.run_install()
        self.assertEqual(target.read_bytes(), b'x' * self.files[name]['bytes'])
        self.assertFalse((self.work / visual.MARKER).exists())
        self.assertFalse(self.target(list(self.members)[1]).exists())

    def test_existing_import_symlink_is_never_replaced_even_if_bytes_match(self):
        name = next(iter(self.members)); original = self.root / 'imported.geo'
        original.write_bytes(self.members[name]); original.chmod(0o444)
        self.target(name).symlink_to(original)
        with self.assertRaises((ValueError, DiagnosticError, OSError)):
            self.run_install()
        self.assertTrue(self.target(name).is_symlink())
        self.assertEqual(original.read_bytes(), self.members[name])

    def test_linked_destination_directory_is_refused(self):
        (self.work / 'data/Player_Library').rmdir()
        original = self.root / 'original'; original.mkdir()
        (self.work / 'data/Player_Library').symlink_to(original, target_is_directory=True)
        with self.assertRaisesRegex((ValueError, DiagnosticError), 'Linked|non-directory'):
            self.run_install()
        self.assertEqual(list(original.iterdir()), [])

    def test_linked_receipt_is_refused_before_install(self):
        other = self.root / 'other'; other.write_text('{}')
        (self.work / visual.MARKER).symlink_to(other)
        with self.assertRaises((ValueError, DiagnosticError, OSError)):
            self.run_install()
        self.assertFalse(self.target(next(iter(self.members))).exists())

    def test_case_conflicting_leaf_is_refused(self):
        (self.work / 'data/Player_Library/FEM_BOOT.geo').write_bytes(b'existing')
        with self.assertRaisesRegex((ValueError, DiagnosticError), 'Case-conflicting'):
            self.run_install()
        self.assertEqual((self.work / 'data/Player_Library/FEM_BOOT.geo').read_bytes(), b'existing')

    def test_content_rewrite_with_restored_mtime_breaks_reuse(self):
        self.run_install(); name = next(iter(self.members)); target = self.target(name)
        target.chmod(0o644); target.write_bytes(b'x' * target.stat().st_size); target.chmod(0o444)
        os.utime(target, (client.CACHE_EPOCH, client.CACHE_EPOCH))
        with self.assertRaisesRegex((ValueError, DiagnosticError), 'conflicts'):
            self.run_install()

    def test_writable_installed_leaf_is_refused(self):
        self.run_install(); target = self.target(next(iter(self.members))); target.chmod(0o644)
        with self.assertRaisesRegex((ValueError, DiagnosticError), 'permissions'):
            self.run_install()

    def test_changed_archive_is_rejected(self):
        path = self.assets / visual.ARCHIVE
        raw = bytearray(path.read_bytes()); raw[35] ^= 1; path.write_bytes(raw)
        with self.assertRaisesRegex((ValueError, DiagnosticError), 'archive differs'):
            self.run_install()
        self.assertFalse((self.work / visual.MARKER).exists())

    def test_changed_manifest_is_rejected(self):
        (self.assets / visual.MANIFEST).write_bytes(b'{}')
        with self.assertRaisesRegex((ValueError, DiagnosticError), 'manifest differs'):
            self.run_install()

    def test_malformed_owned_derived_receipt_recovers_after_full_verification(self):
        self.run_install(); path = self.work / visual.MARKER
        path.chmod(0o644); path.write_text('{'); path.chmod(0o444)
        os.utime(path, (client.CACHE_EPOCH, client.CACHE_EPOCH))
        report = self.run_install()
        self.assertFalse(report['fingerprint_reused'])
        self.assertEqual(report['installed_files'], 0)
        self.assertTrue(self.run_install()['fingerprint_reused'])

    def test_missing_selected_file_recovers_without_touching_other_assets(self):
        self.run_install(); name = next(iter(self.members)); self.target(name).unlink()
        report = self.run_install()
        self.assertEqual(report['installed_files'], 1)
        self.assertEqual(self.target(name).read_bytes(), self.members[name])
        self.assertEqual((self.work / 'data/bin/preserved.bin').read_bytes(), b'accepted-cache')

    def test_cancelled_partial_decode_publishes_no_file_or_receipt(self):
        def cancelled(archive, name, pin, output, context):
            output.write(b'x'); raise ValueError('Stop requested')
        with mock.patch.object(visual.world, 'extract_payload', side_effect=cancelled):
            with self.assertRaisesRegex((ValueError, DiagnosticError), 'Stop requested'):
                self.run_install()
        self.assertFalse((self.work / visual.MARKER).exists())
        self.assertFalse(self.target(next(iter(self.members))).exists())
        self.assertEqual(list((self.work / 'data/Player_Library').iterdir()), [])

    def test_nonregular_zip_member_is_rejected_even_with_matching_outer_pin(self):
        self.write_archive(self.members, bad_mode=True)
        pin = producer.pin(self.assets / visual.ARCHIVE)
        self.document['archive'].update(pin); self.repin()
        with mock.patch.multiple(visual, ARCHIVE_SHA256=pin['sha256'], ARCHIVE_BYTES=pin['bytes'], MANIFEST_SHA256=self.manifest_sha):
            with self.assertRaisesRegex((ValueError, DiagnosticError), 'Invalid.*ZIP'):
                self.run_install()

    def test_racing_destination_publication_never_overwrites_an_existing_file(self):
        original = client.publish_new_regular_file
        def raced(temporary, target):
            if target.suffix == '.geo':
                target.write_bytes(b'racing-owner-file')
            return original(temporary, target)
        with mock.patch.object(client, 'publish_new_regular_file', side_effect=raced):
            with self.assertRaises((ValueError, DiagnosticError, FileExistsError)):
                self.run_install()
        self.assertEqual(self.target(next(iter(self.members))).read_bytes(), b'racing-owner-file')
        self.assertFalse((self.work / visual.MARKER).exists())

    def test_upgrade_adds_only_delta_and_preserves_previous_installed_leaf_identity(self):
        name = next(iter(self.baseline)); target = self.target(name)
        target.write_bytes(self.members[name]); target.chmod(0o444)
        os.utime(target, (client.CACHE_EPOCH, client.CACHE_EPOCH))
        before = target.stat()
        report = self.run_install()
        self.assertEqual((report['installed_files'], report['reused_files']), (1, 1))
        self.assertEqual((target.stat().st_dev, target.stat().st_ino, target.stat().st_mtime_ns),
            (before.st_dev, before.st_ino, before.st_mtime_ns))
        self.assertEqual(target.read_bytes(), self.members[name])

    def test_changed_baseline_pin_is_rejected_even_if_whole_manifest_is_repinned(self):
        self.document['visual_extension']['baseline_files_sha256'] = '0' * 64; self.repin()
        with mock.patch.object(visual, 'MANIFEST_SHA256', self.manifest_sha):
            with self.assertRaisesRegex((ValueError, DiagnosticError), 'baseline policy'):
                self.run_install()
        self.assertFalse(self.target(next(iter(self.members))).exists())


class SourceProofTests(unittest.TestCase):
    def test_extension_preserves_290_leaves_and_binds_exact_hostile_family(self):
        value = producer.read_manifest(ROOT / 'assets' / producer.MANIFEST)
        selected = producer.extension_files(value)
        self.assertEqual(len(selected), 33)
        self.assertEqual(sum(name.endswith('.geo') for name in selected), 8)
        self.assertEqual(sum(name.endswith('.texture') for name in selected), 25)
        self.assertEqual(value['visual_extension']['unresolved_dependencies'], [])
        proofs = value['visual_extension']['requested_model_proof']
        self.assertEqual(sum(len(row['requested_models']) for row in proofs.values()), 19)
        self.assertTrue(all(not row['absent_requested_models'] for row in proofs.values()))
        names = value['visual_extension']['hostile_identity']['costumes']
        self.assertEqual(set(names), {f'Thug_Hellion_{i:02}' for i in range(1, 7)})
        self.assertIn('NPC "Thug_Hellion_01"', (ROOT / 'upstream/i24/data/defs/villaincostume/thugs.nd').read_text())
        self.assertIn('"P222712670" "Blood Brother Chopper"',
            (ROOT / 'upstream/i24/data/texts/english/villains/villains.xls.ms').read_text())

    def test_low_detail_bush_material_both_primary_and_fallback_are_selected(self):
        value = producer.read_manifest(ROOT / 'assets' / producer.MANIFEST)
        selected = value['visual_extension']['files']
        for stem in ('praet_bushlods_d', 'praet_bushlods_fb'):
            name = 'data/texture_library/world/city_zones/praetoria/nature/' + stem + '.texture'
            self.assertIn(name, selected)
            self.assertTrue(any(row.get('alias') == 'X_P_BushLODs' for row in selected[name]))
        proof = value['visual_extension']['preserved_world_geometry_proof'][
            'data/object_library/city_zones/praetoria/nature/bushes/praet_bushes_urban01.geo']
        self.assertTrue(any('LOD' in row['name'] and 'X_P_BushLODs' in row['direct_texture_names']
            for row in proof['models']))

    def test_extension_rejects_a_changed_retained_leaf(self):
        value = producer.read_manifest(ROOT / 'assets' / producer.MANIFEST)
        value = copy.deepcopy(value)
        name = next(n for n in value['files'] if n not in value['visual_extension']['files'])
        value['files'][name]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'preserved 0.13.7 payload'):
            producer.extension_files(value)

    def test_actual_frozen_manifest_has_no_baseline_replacements_and_discloses_known_gaps(self):
        value = producer.read_manifest(ROOT / 'assets' / producer.MANIFEST)
        self.assertEqual(value['file_count'], producer.FILE_COUNT)
        self.assertEqual(value['closure']['absent_requested_models'], [
            {'geometry': 'data/player_library/male_collar.geo', 'model': 'GEO_Collar_MAGIC'}])
        self.assertFalse(value['closure']['full_global_asset_closure'])

    def test_payload_paths_exclude_imports_caches_and_other_runtime_files(self):
        for name in ['../data/player_library/a.geo', 'data/player_library/../a.geo',
            'data/texture_library/../../bin/powers.bin', 'data/texture_library/a.geo',
            'data/player_library/a.texture', 'data/server/bin/a.bin', 'data/Texture_Library/a.texture',
            'C:/data/texture_library/a.texture', 'data//texture_library/a.texture']:
            self.assertFalse(visual.safe_payload(name), name)
            self.assertFalse(producer.safe_payload(name), name)

    def test_actual_gui_requests_are_in_the_selected_texture_inventory(self):
        value = producer.read_manifest(ROOT / 'assets' / producer.MANIFEST)
        wanted = {'tray_ring_power', 'tray_ring_inspiration', 'enhnctray_ringhole', 'insp_ring', 'insp_ring_back'}
        supplied = {Path(name).stem for name, rows in value['requests'].items()
            if any(row['scope'] == 'current_atlas_gui' for row in rows)}
        self.assertTrue(wanted <= supplied)

    def test_actual_liberty_geometry_and_genders_are_explicit(self):
        value = producer.read_manifest(ROOT / 'assets' / producer.MANIFEST)
        files = set(value['files']) | {'data/' + row['path'].casefold() for row in
            json.loads((ROOT / 'assets/reference-inputs-manifest.json').read_text())['files']}
        for name in ['fem_pants', 'fem_shirt', 'fem_head', 'fem_glove', 'fem_boot', 'fem_belt', 'fem_hair', 'fem_spadr']:
            self.assertTrue('data/player_library/' + name + '.geo' in files, name)
        self.assertTrue(any(Path(name).stem == 'sf_hips_skin_tights' for name in files))
        self.assertTrue(any(Path(name).stem == 'sf_face_skin_head_08' for name in files))

    def test_reviewed_model_indices_bind135_matches_and_report_one_exact_missing_model(self):
        value = producer.read_manifest(ROOT / 'assets' / producer.MANIFEST)
        proofs = value['closure']['requested_model_proof'].values()
        self.assertEqual(sum(row['indexed_model_count'] for row in proofs), 6576)
        self.assertEqual(sum(len(row['requested_models']) for row in proofs), 135)
        self.assertEqual(sum(len(row['absent_requested_models']) for row in proofs), 1)
        self.assertEqual(len({row['target'] for row in value['closure']['unresolved_dependencies']}), 5)

    def test_missing_Larm_suppression_and_source_folded_gloves_are_bound(self):
        value = producer.read_manifest(ROOT / 'assets' / producer.MANIFEST)
        source = ROOT / 'upstream/ouroboros/Game/src/entity/entclient.c'
        self.assertEqual(producer.pin(source), value['source_files'][source.relative_to(ROOT).as_posix()])
        self.assertIn('E3 hack', source.read_text())
        proof = value['closure']['requested_model_proof']['data/player_library/fem_glove.geo']
        self.assertEqual({row['requested'] for row in proof['requested_models']},
            {'GEO_LARMR_Folded', 'GEO_LARML_Folded'})
        self.assertEqual(proof['absent_requested_models'], [])

    def test_geometry_reader_rejects_corrupt_sizes_offsets_and_versions(self):
        for raw in [b'', bytes(16), (123).to_bytes(4, 'little') + bytes(4) + (9).to_bytes(4, 'little') + bytes(20)]:
            with self.assertRaises((ValueError, struct.error)):
                geometry.tables(raw)


if __name__ == '__main__':
    unittest.main()
