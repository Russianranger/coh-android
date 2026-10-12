"""Host receipt-reader negatives using the actual .31 historical package.

The replacement leaf below is deliberately a parser fixture. These tests never
qualify a native build or substitute for the mandatory actual Windows receipts.
"""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'android/guest')]
import native_map_startup_contract as contract
import prepare_map_startup_source as source
import map_startup_animation_certificate as certificate
import package_map_startup_native as package


class MapStartupContractReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        apk = Path(os.environ.get('COH_MAP_STARTUP_TEST_DONOR_APK',
            '/workspace/scratch/52beb2ce66cd/profile-recovery-031-evidence/accepted/COH-Atlas-Gameplay-0.13.31.apk'))
        if contract.file_pin(apk) != {'bytes': 41203812, 'sha256': 'e56df1bcf2210aff131ba80189b1b2dee760f27066e3ee26e09c5fea1654ad80'}:
            raise AssertionError('Actual accepted .31 donor required; no skips')
        with zipfile.ZipFile(apk) as archive: raw = archive.read('assets/runtime/game-package.tar.gz')
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
            cls.old = json.load(archive.extractfile('game-package.json'))
        pigg = Path(os.environ.get('COH_MAP_STARTUP_TEST_ANIMATIONS',
            '/workspace/scratch/52beb2ce66cd/runtime-asset-preflight-cache/payloads/server-animations.pigg'))
        manifest = Path(os.environ.get('COH_MAP_STARTUP_TEST_ANIMATION_MANIFEST',
            '/workspace/scratch/52beb2ce66cd/runtime-asset-preflight-cache/payloads/server-animation-manifest.json'))
        _, cert = certificate.generate(pigg, manifest)
        cls.build = source.expected_receipt(cert)
        cls.raw = b'host receipt-reader fixture; not a native PE'

    def candidate(self):
        game = copy.deepcopy(self.old)
        old = game['files']['MapServer.exe']; current = copy.deepcopy(old)
        current.update(bytes=len(self.raw), sha256=hashlib.sha256(self.raw).hexdigest())
        opaque = {'bytes': 1, 'sha256': '1'*64}
        receipt = {'format': 1, 'role': contract.ROLE, 'repository_commit': '2'*40,
            'source_commit': game['source_commit'], 'data_commit': game['data_commit'],
            'build_input': copy.deepcopy(self.build), 'mapserver': current, 'previous_mapserver': copy.deepcopy(old),
            'retained_native_files': {name: row for name,row in game['files'].items() if name != 'MapServer.exe'},
            'schema_sources_sha256': game['native_monorail']['receipt']['schema_sources_sha256'],
            'native_build_repository_commit': '3'*40, 'native_build_manifest': opaque,
            'native_fixture': opaque, 'native_monorail_fixture': opaque, 'fx_qualification': opaque,
            'physical_timing_validated': False, 'native_gameplay_validated': False}
        game['files']['MapServer.exe'] = current
        game['native_map_startup'] = {'receipt': receipt, 'receipt_sha256': contract.canonical_sha(receipt)}
        return game

    def reseal(self, game):
        game['native_map_startup']['receipt_sha256'] = contract.canonical_sha(game['native_map_startup']['receipt'])
        return game

    def test_additive_reader_preserves_exact_three_generations_and_native_closure(self):
        game = self.candidate(); receipt = contract.embedded_receipt(game)
        self.assertEqual(contract.previous_package(game), self.old)
        self.assertEqual(game['native_monorail'], self.old['native_monorail'])
        self.assertEqual(game['native_responsiveness'], self.old['native_responsiveness'])
        self.assertEqual(len(receipt['retained_native_files']), 24)
        self.assertEqual(receipt['previous_mapserver']['sha256'], contract.PREVIOUS_SHA256)
        self.assertEqual(receipt['build_input']['monorail_budget']['contract']['station_preparation_timeout_seconds'], 720)
        self.assertEqual(game['native_monorail']['receipt']['build_input']['contract']['station_preparation_timeout_seconds'], 600)
        self.assertEqual(contract.monorail.progress_contract(game)['producer']['mapserver_sha256'], receipt['mapserver']['sha256'])

    def test_actual_current_leaf_is_required_and_unknown_or_changed_bytes_fail(self):
        game = self.candidate()
        with tempfile.TemporaryDirectory(prefix='map-startup-reader-') as tmp:
            path = Path(tmp)/'MapServer.exe'; path.write_bytes(self.raw)
            proof = contract.verify_current_map(path, game)
            self.assertTrue(proof['cache_donor_identity_preserved'])
            self.assertTrue(proof['native_animation_reader_changed'])
            self.assertFalse(proof['physical_loading_gain_validated'])
            import server_cache_package as caches
            import server_animation_package as animations
            compatibility = caches.verify_mapserver_compatibility(path, game)
            self.assertEqual(compatibility['original_cache_donor_mapserver_sha256'], caches.MAPSERVER_SHA256)
            manifest = {'identity': animations.identity(), 'pigg': certificate.PACK_PIN}
            compatible = animations.verify_runtime(Path(tmp), manifest, mapserver_package=game)
            self.assertTrue(compatible['animation_identity_preserved'])
            self.assertTrue(compatible['native_animation_reader_changed'])
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError): contract.verify_current_map(path, game)
        bad = self.candidate(); bad['native_map_startup']['receipt']['mapserver']['imports'] = ['unknown.dll']
        with self.assertRaises(ValueError): contract.embedded_receipt(self.reseal(bad))

    def test_changed_retained_dependency_or_original_history_is_refused(self):
        for target in ('native_responsiveness', 'native_monorail'):
            bad = self.candidate(); bad[target]['receipt_sha256'] = '0'*64
            with self.assertRaises(ValueError): contract.embedded_receipt(bad)
        bad = self.candidate(); name = next(n for n in bad['files'] if n != 'MapServer.exe')
        bad['files'][name]['sha256'] = '0'*64
        bad['native_map_startup']['receipt']['retained_native_files'][name]['sha256'] = '0'*64
        with self.assertRaises(ValueError): contract.embedded_receipt(self.reseal(bad))

    def test_forged_certificate_parser_or_station_clock_scope_is_refused(self):
        for path, value in ((('format',), True), (('build_input','schema_version'), True),
            (('build_input','retained_sources_sha256','Common/fxinfo.c'), '0'*64),
            (('build_input','animation_certificate','generated_table','sha256'), '0'*64),
            (('build_input','animation_certificate','original_animation_identity','mapserver_sha256'), '0'*64),
            (('build_input','animation_certificate','original_animation_identity','loader'), 'unproved-loader'),
            (('build_input','monorail_budget','contract','station_preparation_timeout_seconds'), 721),
            (('physical_timing_validated',), True), (('native_gameplay_validated',), True)):
            bad = self.candidate(); cursor = bad['native_map_startup']['receipt']
            for key in path[:-1]: cursor = cursor[key]
            cursor[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(ValueError): contract.embedded_receipt(self.reseal(bad))

    def test_runtime_binding_updates_current_producer_and_manifest_without_relabeling_old_history(self):
        game = self.candidate()
        component = {'repository_commit': '2'*40, 'native_repository_commit': '3'*40,
            'native_build': {'run_id': 123}, 'physical_timing_validated': False}
        binding = package.runtime_binding(component, game, '2'*40)
        self.assertEqual(binding['monorail_contract']['station_preparation_timeout_seconds'], 720)
        self.assertEqual(binding['mapserver_progress_producer']['repository_commit'], '3'*40)
        self.assertEqual(binding['package_manifest_sha256'], hashlib.sha256(package.canonical(game)).hexdigest())
        self.assertNotIn('archive_pin', binding)
        self.assertEqual(contract.previous_package(game), self.old)

    def test_unready_component_marker_cannot_start_download_or_publication(self):
        with tempfile.TemporaryDirectory(prefix='map-startup-marker-') as tmp:
            marker = Path(tmp)/'release.json'; marker.write_text('{"publish_enabled":false}')
            args = type('Args', (), {'marker': marker, 'output': Path(tmp)/'inputs', 'repository_commit': '2'*40})()
            with self.assertRaisesRegex(ValueError, 'not ready'): package.stage_inputs(args)
            self.assertFalse(args.output.exists())

    def test_extracted_artifact_is_rechecked_against_all_actual_zip_bytes(self):
        with tempfile.TemporaryDirectory(prefix='map-startup-zip-') as tmp:
            archive = Path(tmp)/'accepted.zip'; output = Path(tmp)/'native'
            with zipfile.ZipFile(archive, 'w') as destination:
                destination.writestr('evidence/actual.txt', b'proof bytes')
            package.extract_artifact(archive, output); package.verify_extracted_archive(archive, output)
            (output/'evidence/actual.txt').write_bytes(b'forged local proof')
            with self.assertRaises(ValueError): package.verify_extracted_archive(archive, output)


if __name__ == '__main__': unittest.main()
