"""Missing-only installer rejection/recovery tests and frozen donor model proofs.

Synthetic small installer fixtures make no graphics or Android execution claim.
The separate manifest checks bind the actual reviewed donor/model inventories.
"""
import copy
import base64
import gzip
import hashlib
import io
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


class SourceManifestEncodingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / producer.MANIFEST
        self.raw = b'{"files":{"original-leaf":{"bytes":64}},"format":1}\n'
        self.pin = {'bytes': len(self.raw), 'sha256': hashlib.sha256(self.raw).hexdigest()}
        patch = mock.patch.object(producer, 'MANIFEST_PIN', self.pin)
        patch.start(); self.addCleanup(patch.stop)

    def envelope(self, packed=None):
        packed = packed if packed is not None else gzip.compress(self.raw, mtime=0)
        return {'format': 1, 'scope': producer.SOURCE_MANIFEST_SCOPE,
            'encoding': 'gzip+base64', 'decoded': dict(self.pin),
            'gzip': {'bytes': len(packed), 'sha256': hashlib.sha256(packed).hexdigest()},
            'data': base64.b64encode(packed).decode('ascii')}

    def write(self, value):
        self.path.write_bytes(producer.canonical(value) + b'\n')

    def test_plaintext_and_envelope_return_identical_original_bytes(self):
        self.path.write_bytes(self.raw)
        self.assertEqual(producer.manifest_bytes(self.path), self.raw)
        self.write(self.envelope())
        self.assertEqual(producer.manifest_bytes(self.path), self.raw)

    def test_linked_source_is_rejected_even_if_original_bytes_match(self):
        target = self.root / 'original.json'
        for raw in (self.raw, producer.canonical(self.envelope()) + b'\n'):
            target.write_bytes(raw)
            self.path.symlink_to(target)
            with self.assertRaisesRegex(ValueError, 'linked client visual manifest input'):
                producer.manifest_bytes(self.path)
            self.path.unlink()
            self.assertEqual(target.read_bytes(), raw)

    def test_source_encoding_never_reaches_prepared_runtime_manifest(self):
        assets, output = self.root / 'assets', self.root / 'output'
        assets.mkdir(); output.mkdir()
        self.path = assets / producer.MANIFEST
        self.write(self.envelope())
        archive_raw = b'exact-original-archive-streams'
        (assets / producer.ARCHIVE).write_bytes(archive_raw)
        with mock.patch.object(producer, 'verify') as verify:
            producer.prepare(output, root=self.root)
        self.assertEqual(verify.call_count, 2)
        self.assertEqual((output / producer.MANIFEST).read_bytes(), self.raw)
        self.assertEqual((output / producer.ARCHIVE).read_bytes(), archive_raw)

    def test_changed_packed_stream_is_rejected_before_decompression(self):
        value = self.envelope(); value['gzip']['sha256'] = '0' * 64; self.write(value)
        with mock.patch.object(producer.zlib, 'decompressobj', side_effect=AssertionError('decode forbidden')):
            with self.assertRaisesRegex(ValueError, 'gzip stream differs'):
                producer.manifest_bytes(self.path)

    def test_wrong_decoded_pin_or_extra_envelope_fields_are_rejected(self):
        for change in ('bytes', 'sha256', 'extra', 'encoding'):
            value = self.envelope()
            if change == 'bytes': value['decoded']['bytes'] += 1
            elif change == 'sha256': value['decoded']['sha256'] = '0' * 64
            elif change == 'encoding': value['encoding'] = 'unbounded-zip'
            else: value['extra'] = True
            self.write(value)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'envelope differs'):
                producer.manifest_bytes(self.path)

    def test_duplicate_envelope_fields_are_rejected(self):
        raw = producer.canonical(self.envelope())
        self.path.write_bytes(b'{"format":1,' + raw[1:])
        with self.assertRaisesRegex(ValueError, 'duplicate fields'):
            producer.manifest_bytes(self.path)

    def test_invalid_base64_and_gzip_crc_are_rejected(self):
        value = self.envelope(); value['data'] = '!' + value['data'][1:]; self.write(value)
        with self.assertRaises(ValueError): producer.manifest_bytes(self.path)
        packed = bytearray(gzip.compress(self.raw, mtime=0)); packed[-8] ^= 1
        self.write(self.envelope(bytes(packed)))
        with self.assertRaisesRegex(ValueError, 'gzip stream is invalid'):
            producer.manifest_bytes(self.path)

    def test_concatenated_or_trailing_gzip_bytes_are_rejected(self):
        packed = gzip.compress(self.raw, mtime=0)
        for tail in (b'trailing', gzip.compress(b'another-manifest', mtime=0)):
            self.write(self.envelope(packed + tail))
            with self.subTest(tail=tail), self.assertRaisesRegex(ValueError, 'decoded bytes differ'):
                producer.manifest_bytes(self.path)

    def test_expansion_is_limited_by_exact_reviewed_decoded_size(self):
        self.write(self.envelope(gzip.compress(b'x' * 1000000, mtime=0)))
        with self.assertRaisesRegex(ValueError, 'decoded bytes differ or exceed bound'):
            producer.manifest_bytes(self.path)

    def test_source_and_packed_sizes_are_bounded_before_decode(self):
        self.write(self.envelope())
        with mock.patch.object(producer, 'MAX_SOURCE_MANIFEST_BYTES', 32):
            with self.assertRaisesRegex(ValueError, 'envelope exceeds bound'):
                producer.manifest_bytes(self.path)
        value = self.envelope(); value['gzip']['bytes'] = producer.MAX_SOURCE_GZIP_BYTES + 1
        self.write(value)
        with self.assertRaisesRegex(ValueError, 'encoded stream exceeds bound'):
            producer.manifest_bytes(self.path)

    def test_plaintext_over_bound_is_rejected(self):
        self.path.write_bytes(self.raw)
        with mock.patch.object(producer, 'MAX_MANIFEST_BYTES', len(self.raw) - 1):
            with self.assertRaisesRegex(ValueError, 'manifest differs from reviewed metadata'):
                producer.manifest_bytes(self.path)


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
            ENCOUNTER_FILE_COUNT=0, SWEEP_FILE_COUNT=0,
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


class PartialResponseTests(unittest.TestCase):
    def fixture(self):
        body = b'ignored-gap-original-leaf-neighbor'
        raw = b'original-leaf'
        start = 100
        offset = start + body.index(raw)
        row = {'source_archive': 'fixture.pigg', 'offset': offset, 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest(), 'md5_table': hashlib.md5(raw).hexdigest(),
            'compressed': False, 'stored_bytes': len(raw), 'stored_sha256': hashlib.sha256(raw).hexdigest(),
            'source_download_content_range': f'bytes {start}-{start+len(body)-1}/1000',
            'source_download_bytes': len(body), 'source_download_sha256': hashlib.sha256(body).hexdigest(),
            'source_download_member_bytes': len(raw),
            'source_member_range': f'bytes {offset}-{offset+len(raw)-1}/1000',
            'source_content_range': f'bytes {offset}-{offset+len(raw)-1}/1000'}
        url = 'https://dists.thunderspy.org/piggs/fixture.pigg'
        key = (url, 'original-etag', 'original-last-modified', 1000, row['source_download_content_range'])
        response = io.BytesIO(body)
        response.status = 206
        response.geturl = lambda: url
        response.headers = {'ETag': key[1], 'Last-Modified': key[2], 'Content-Range': key[4],
            'Content-Length': str(len(body))}
        return body, raw, row, key, response

    def test_exact_response_with_gap_preserves_selected_original_stream(self):
        body, raw, row, key, response = self.fixture()
        with mock.patch.object(producer.urllib.request, 'urlopen', return_value=response) as transfer:
            result = producer.download_selected_range((key, [('fixture', row)]))
        self.assertEqual(result, [('fixture', row, raw)])
        self.assertEqual(transfer.call_args.args[0].get_header('Range'), 'bytes=100-'+str(99+len(body)))

    def test_changed_neighbor_is_rejected_even_when_selected_leaf_matches(self):
        _, _, row, key, response = self.fixture()
        response.getbuffer()[0] ^= 1
        with mock.patch.object(producer.urllib.request, 'urlopen', return_value=response):
            with self.assertRaisesRegex(ValueError, 'response bytes differ'):
                producer.download_selected_range((key, [('fixture', row)]))

    def test_partial_response_cannot_be_replaced_with_full_download(self):
        _, _, row, key, response = self.fixture()
        response.status = 200
        with mock.patch.object(producer.urllib.request, 'urlopen', return_value=response):
            with self.assertRaisesRegex(ValueError, 'partial transfer was refused'):
                producer.download_selected_range((key, [('fixture', row)]))

    def test_shared_receipt_cannot_bind_another_archive(self):
        value = {'provenance': {'sweep_downloads': {'r0000': {'source_archive': 'foreign.pigg'}}}}
        with self.assertRaisesRegex(ValueError, 'missing or foreign'):
            producer.selected_download_record(value, {'source_download_receipt': 'r0000',
                'source_archive': 'fixture.pigg', 'stored_bytes': 1})

    def test_shared_receipt_expansion_preserves_original_evidence(self):
        original = {'source_download_receipt': 'r0000', 'source_archive': 'fixture.pigg', 'stored_bytes': 7}
        value = {'provenance': {'sweep_downloads': {'r0000': {'source_archive': 'fixture.pigg',
            'content_range': 'bytes 1-9/100', 'bytes': 9, 'sha256': 'a'*64}}}}
        actual = producer.selected_download_record(value, original)
        self.assertEqual(actual['source_download_content_range'], 'bytes 1-9/100')
        self.assertNotIn('source_download_content_range', original)


class SourceProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.swept = producer.read_manifest(ROOT / 'assets' / producer.MANIFEST)

    def test_sweep_preserves_all_immediate329_file_identities(self):
        value = self.swept
        additions = producer.sweep_files(value)
        self.assertEqual(additions, visual.sweep_files(value))
        retained = {name: row for name, row in value['files'].items() if name not in additions}
        self.assertEqual(len(retained), 329)
        self.assertEqual(sum(row['bytes'] for row in retained.values()), 39521237)
        self.assertEqual(hashlib.sha256(producer.canonical(retained)).hexdigest(),
            '07b61f301355f2bb0174db2b41f1254b3f2b80cfd660d5f467415c7f33707c09')

    def test_sweep_rejects_changed_immediate_leaf_even_with_new_inventory_digest(self):
        value = copy.deepcopy(self.swept)
        old = next(name for name in value['files'] if name not in value['sweep_extension']['files'])
        value['files'][old]['sha256'] = '0'*64
        value['files_sha256'] = hashlib.sha256(producer.canonical(value['files'])).hexdigest()
        for check in (producer.sweep_files, visual.sweep_files):
            with self.assertRaisesRegex((ValueError, DiagnosticError), 'preserved 0.13.9 payload'):
                check(value)

    def test_sweep_rejects_changed_source_witness_and_false_physical_or_preload_claims(self):
        changed = copy.deepcopy(self.swept)
        name = next(iter(changed['sweep_extension']['files']))
        changed['requests'][name][0]['target'] = 'unrelated_texture'
        with self.assertRaisesRegex(ValueError, 'source evidence differ'):
            producer.sweep_files(changed)
        for flag in ('runtime_visual_validated', 'full_global_asset_closure', 'preloading'):
            changed = copy.deepcopy(self.swept); changed['sweep_extension'][flag] = True
            with self.assertRaisesRegex(ValueError, 'source evidence differ'):
                producer.sweep_files(changed)

    def test_all390_recorded_missing_geometries_have_native_model_inventory_proof(self):
        requests = json.loads((ROOT/'assets/client-visual-sweep-requests.json').read_text())
        observed = {name for name, rows in requests['geometry'].items()
            if any(row.get('scope') == 'observed_startup_missing_geometry' for row in rows)}
        self.assertEqual(len(observed), 390)
        proofs = self.swept['sweep_extension']['requested_model_proof']
        self.assertTrue(observed <= set(proofs))
        self.assertTrue(all(row['absent_requested_models'] == [] for row in proofs.values()))
        for name in observed:
            self.assertGreater(proofs[name]['indexed_model_count'], 0, name)

    def test_silent_civilian_and_vanguard_hands_have_exact_original_models(self):
        proofs = self.swept['sweep_extension']['requested_model_proof']
        for stem in ('bm_glove','bf_glove','v_new_rikti_glove','v_male_glove','v_fem_glove'):
            proof = proofs['data/player_library/'+stem+'.geo']
            self.assertTrue(proof['requested_models'], stem)
            self.assertFalse(proof['absent_requested_models'], stem)
            self.assertTrue(any('larm' in row['requested'].casefold() for row in proof['requested_models']), stem)

    def test_loaded_atlas_ground_and_bench_missing_layers_are_explicit(self):
        stems = {Path(name).stem for name in self.swept['sweep_extension']['files']}
        self.assertTrue({'plaza_grass_freshcut_01_z','plaza_grass_freshcut_01_ns',
            'plaza_grass_freshcut_01a_ns','p_planter_soil_ns','bench_gold_fb','bench_gold_ns'} <= stems)

    def test_encounter_extension_keeps_323_prior_leaves_and_only_six_observed_npc_textures(self):
        value = producer.read_manifest(ROOT / 'assets' / producer.MANIFEST)
        names = producer.encounter_files(value)
        self.assertEqual(len(names), 6)
        self.assertEqual(sum(value['files'][name]['bytes'] for name in names), 291538)
        self.assertEqual({Path(name).stem for name in names}, {'chest_bm_labcoat_01a',
            'chest_bm_labcoat_01b', 'chest_bm_flannel_01a', 'chest_bm_flannel_01b',
            'face_skin_bf_25asian3', 'face_skin_bf_45black1'})
        # The retained producer still verifies this historical recipe. The
        # candidate guest requires its new exact appearance manifest identity.
        with tempfile.TemporaryDirectory() as temporary:
            assets = Path(temporary)
            (assets / producer.MANIFEST).write_bytes(
                producer.manifest_bytes(ROOT / 'assets' / producer.MANIFEST))
            with self.assertRaisesRegex(DiagnosticError, 'manifest differs'):
                visual.package(assets)
        receipt = json.loads((ROOT / value['encounter_extension']['source_device_receipt']).read_text())
        console = next(row for row in receipt['source_files'] if row['path'].endswith('client-console.log'))
        self.assertEqual({key: console[key] for key in ('bytes', 'sha256')},
            value['encounter_extension']['source_console'])
        self.assertFalse(value['encounter_extension']['runtime_visual_validated'])
        self.assertTrue(all(value['provenance']['entries'][name]['source_archive'] == 'stage1c.pigg' for name in names))

    def test_encounter_append_rejects_modified_prior_payloads_and_speculative_target_names(self):
        value = producer.read_manifest(ROOT / 'assets' / producer.MANIFEST)
        changed = copy.deepcopy(value)
        name = next(n for n in changed['files'] if n not in changed['encounter_extension']['files']
            and n not in changed.get('sweep_extension', {}).get('files', {}))
        changed['files'][name]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'preserved 0.13.8 payload'):
            producer.encounter_files(changed)
        changed = copy.deepcopy(value)
        name = next(iter(changed['encounter_extension']['files']))
        rows = changed['encounter_extension']['files'].pop(name)
        changed['encounter_extension']['files']['data/texture_library/npcs/other.texture'] = rows
        with self.assertRaisesRegex(ValueError, 'encounter extension bounds'):
            producer.encounter_files(changed)

    def test_encounter_evidence_does_not_allow_native_renderer_or_physical_success_claims(self):
        value = producer.read_manifest(ROOT / 'assets' / producer.MANIFEST)
        for key in ('runtime_visual_validated', 'npc_identity_claimed', 'native_renderer_changed',
                    'global_lod_distances_changed', 'full_global_asset_closure'):
            changed = copy.deepcopy(value)
            changed['encounter_extension'][key] = True
            with self.assertRaisesRegex(ValueError, 'encounter extension bounds'):
                producer.encounter_files(changed)

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
        name = next(n for n in value['files'] if n not in value['visual_extension']['files']
            and n not in value.get('sweep_extension', {}).get('files', {}))
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
