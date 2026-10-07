"""Typed Game wrapper and real existing-worktree/header-pack upgrade scenarios."""
import copy
import hashlib
import unittest
from unittest.mock import patch

import package_client_scene_performance_native as native
import test_client_startup_followup_contract as previous

contract, guest, index, textures = previous.contract, previous.guest, previous.index, previous.textures


def native_manifest(package, record):
    manifest = copy.deepcopy(package['client_startup_followup']['manifest'])
    manifest.pop('preload_source_sha256')
    build = copy.deepcopy(native.expected_receipt())
    import test_client_scene_performance_native as scene_tests
    import test_client_frame_timing_native as frame_tests
    scene = scene_tests.expected_checks()
    frame = frame_tests.expected_receipt()
    checks = {'format': 1, 'status': 'passed', 'platform': 'windows', 'architecture': 'Win32',
        'configuration': 'OptDebug', 'build_input': build, 'scene': scene, 'frame': frame}
    manifest.update(role=native.ROLE, repository_commit='f'*40, build_input=build,
        files={'CityOfHeroes.exe': copy.deepcopy(record)}, base_client_executable=copy.deepcopy(package['files']['CityOfHeroes.exe']),
        windows_qualification=checks)
    return manifest


class ClientScenePerformanceContractTests(unittest.TestCase):
    read_archive = previous.ClientStartupFollowupContractTests.read_archive
    write_archive = previous.ClientStartupFollowupContractTests.write_archive
    prepare = previous.ClientStartupFollowupContractTests.prepare
    preserved = previous.ClientStartupFollowupContractTests.preserved
    loading_derivative = previous.ClientStartupFollowupContractTests.loading_derivative
    upgraded_index = previous.ClientStartupFollowupContractTests.upgraded_index

    def setUp(self):
        previous.ClientStartupFollowupContractTests.setUp(self)
        self.donor = previous.ClientStartupFollowupContractTests.derivative(self)
        self.runtime, self.donor_report = self.prepare()
        self.donor_game = copy.deepcopy(self.donor['files']['CityOfHeroes.exe'])

    def derivative(self):
        contents, package = self.read_archive()
        raw = previous.old.fixtures.pe_bytes()+b'bounded-native-scene-and-frame-Game'
        record = dict(self.donor_game, size=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        manifest = native_manifest(package, record)
        package['client_scene_performance'] = {'manifest': manifest, 'manifest_sha256': contract.canonical_sha(manifest),
            'base_client_startup_followup_manifest_sha256': package['client_startup_followup']['manifest_sha256'],
            'base_client_executable': copy.deepcopy(self.donor_game)}
        package['files']['CityOfHeroes.exe'] = record; contents['CityOfHeroes.exe'] = raw
        self.write_archive(contents, package)
        return package

    def test_upgrade_preserves_private_input_roots_generated_caches_and_server_links(self):
        before = self.preserved(); expected = self.derivative()
        with patch.object(guest.os, 'scandir', side_effect=AssertionError('Accepted input tree recreated')):
            runtime, report = self.prepare()
        self.assertEqual(runtime, self.runtime); self.assertEqual(before, self.preserved())
        self.assertTrue(report['native_executable_upgraded']); self.assertTrue(report['generated_cache_bytes_preserved'])
        proof = report['native_texture_index_migration']
        self.assertEqual(proof['policy'], 'verified_client_scene_performance_layer_v1')
        self.assertEqual(proof['previous_executable_sha256'], self.donor_game['sha256'])
        self.assertEqual(proof['layer_manifest_sha256'], expected['client_scene_performance']['manifest_sha256'])
        self.assertEqual(self.server_leaf.resolve(strict=True), self.supplement)
        self.assertTrue(self.prepare()[1]['reused'])

    def test_header_index_rebind_keeps_every_prepared_header_byte(self):
        index.prepare(self.runtime, self.identity, self.donor_game['sha256'], textures.Context({'client_worktree': self.donor_report}))
        raw = (self.runtime/index.PACK).read_bytes(); expected = self.derivative(); _, report = self.prepare()
        with patch.object(index, 'make_pack', side_effect=AssertionError('Prepared texture headers rebuilt')):
            after, _ = self.upgraded_index(report, expected['files']['CityOfHeroes.exe'])
        rebound = (self.runtime/index.PACK).read_bytes()
        self.assertTrue(after['reused']); self.assertTrue(after['native_layer_identity_migrated'])
        self.assertEqual(raw[64:], rebound[64:])

    def test_typed_wrapper_keeps_all_accepted_native_history(self):
        expected = self.derivative()
        self.assertEqual(contract.client_contract(expected), expected['files']['CityOfHeroes.exe'])
        for name in ('native_responsiveness', 'startup_bundle_client', 'client_loading', 'client_startup_followup'):
            self.assertEqual(expected[name], self.donor[name])

    def test_forged_native_targets_cache_renderer_ancestry_imports_and_proofs_rejected(self):
        expected = self.derivative()
        for mutation in ('base', 'schema', 'target', 'renderer', 'freshness', 'full_asset', 'scope',
                'same_game', 'imports', 'platform', 'harness', 'sources', 'fallback'):
            changed = copy.deepcopy(expected); wrapper = changed['client_scene_performance']; manifest = wrapper['manifest']; build = manifest['build_input']
            if mutation == 'base': wrapper['base_client_startup_followup_manifest_sha256'] = 'e'*64
            elif mutation == 'schema': manifest['schema_sources_sha256'] = {}
            elif mutation == 'target': build['build_targets'] = ['Game', 'MapServer']
            elif mutation == 'renderer': build['renderer_changed'] = True
            elif mutation == 'freshness': build['source_freshness_changed'] = True
            elif mutation == 'full_asset': build['controls']['frame_profile']['aggregate_only'] = False
            elif mutation == 'scope': manifest['replacement_scope'] = 'all_native'
            elif mutation == 'same_game': manifest['files']['CityOfHeroes.exe'] = self.donor_game
            elif mutation == 'imports': manifest['files']['CityOfHeroes.exe']['imports'].append('foreign.dll')
            elif mutation == 'platform': manifest['windows_qualification']['platform'] = 'linux'
            elif mutation == 'harness': manifest['windows_qualification']['scene']['harness_sha256'] = 'missing'
            elif mutation == 'sources': build['patched_sha256'] = {}
            else: build['controls']['discarded_fx_preload']['stock_fallback_preserved'] = False
            wrapper['manifest_sha256'] = contract.canonical_sha(manifest)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): contract.client_contract(changed)


if __name__ == '__main__': unittest.main()
