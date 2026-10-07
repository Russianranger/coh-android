"""Typed Game wrapper and real existing-worktree/header-pack upgrade scenarios."""
import copy
import hashlib
import itertools
import json
import unittest
from unittest.mock import patch

import package_client_scene_performance_native as native
import test_client_startup_followup_contract as previous

contract, guest, index, textures = previous.contract, previous.guest, previous.index, previous.textures


def bind_source_digests(inputs):
    """Recompute source-recipe bindings independently of the guest validator."""
    def digest(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    events = inputs['character_events']; progress = events['progress_build_input']; game = progress['game_build_input']
    game['postgresql_build_input_canonical_sha256'] = digest(game['postgresql_build_input'])
    progress['game_build_input_canonical_sha256'] = digest(game)
    events['progress_build_input_canonical_sha256'] = digest(progress)
    return inputs


def foreign_source_variants(inputs):
    """Include invented leaves with correctly recomputed enclosing bindings."""
    for name in ('pg_header', 'pg_fixture', 'pg_extra', 'pg_patch', 'event_source', 'texture',
            'pg_digest', 'game_digest', 'progress_digest'):
        changed = copy.deepcopy(inputs)
        events = changed['character_events']; progress = events['progress_build_input']; game = progress['game_build_input']
        pg = game['postgresql_build_input']
        if name == 'pg_header': pg['overlay_sha256']['Common/sql/pg_compat.h'] = 'f'*64
        elif name == 'pg_fixture': pg['overlay_sha256']['DBServer/src/pg_persistence_test.c'] = 'f'*64
        elif name == 'pg_extra': pg['overlay_sha256']['DBServer/src/foreign.c'] = 'f'*64
        elif name == 'pg_patch': pg['patch_sha256'] = 'f'*64
        elif name == 'event_source': events['source_sha256'][next(iter(events['source_sha256']))] = 'f'*64
        elif name == 'texture': changed['client_texture']['parse6_schema_changes'] = True
        bind_source_digests(changed)
        if name == 'pg_digest': game['postgresql_build_input_canonical_sha256'] = 'f'*64
        elif name == 'game_digest': progress['game_build_input_canonical_sha256'] = 'f'*64
        elif name == 'progress_digest': events['progress_build_input_canonical_sha256'] = 'f'*64
        yield name, changed


def validate_actual_native_ancestry(donor, produced):
    """Qualification exercises the actual external donor and Win32 build receipts."""
    import build_client_scene_performance_apk as builder
    case = unittest.TestCase()
    before = copy.deepcopy((donor['_native_client_manifest'], produced))
    accepted = donor['immutable_donor_provenance']['native_responsiveness']['build_inputs']
    case.assertTrue(builder.validate_native_source_ancestry(produced['retained_source_inputs'], accepted))
    wrapped = builder.client_manifest(donor, produced)
    case.assertEqual(contract.client_contract(wrapped), produced['files']['CityOfHeroes.exe'])
    for name in ('native_responsiveness', 'startup_bundle_client', 'client_loading', 'client_startup_followup'):
        case.assertEqual(wrapped[name], donor['_native_client_manifest'][name])
    rejected = []
    for name, inputs in foreign_source_variants(produced['retained_source_inputs']):
        with case.assertRaises(ValueError): builder.validate_native_source_ancestry(inputs, accepted)
        changed = copy.deepcopy(produced); changed['retained_source_inputs'] = inputs
        with case.assertRaises(ValueError): builder.client_manifest(donor, changed)
        rejected.append(name)
    case.assertEqual((donor['_native_client_manifest'], produced), before)
    return {'status': 'passed', 'actual_external_donor_and_win32_receipts_verified': True,
        'full_guest_typed_client_wrapper_verified': True, 'older_native_history_unchanged': True,
        'raw_source_histories_preserved': True, 'rejected_foreign_variants': rejected}


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
        # Bind the real PG->game->progress->events recipe before older fixture
        # layers create their wrappers or worktrees. Earlier suites stay intact.
        import prepare_character_events_source as events_source
        import test_native_client_upgrade as initial
        initial_candidate = initial.NativeClientUpgradeTests.candidate

        def full_ancestry_candidate(fixture):
            initial_candidate(fixture)
            contents, package = fixture.read_archive()
            frozen = package['native_responsiveness']['receipt']
            frozen['build_inputs']['character_events'] = events_source.expected_events_receipt()
            package['native_responsiveness']['receipt_sha256'] = contract.canonical_sha(frozen)
            fixture.write_archive(contents, package)
            (fixture.assets/'native-responsiveness.json').write_text(json.dumps(frozen))
            return frozen

        with patch.object(initial.NativeClientUpgradeTests, 'candidate', full_ancestry_candidate):
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

    def test_only_two_independently_hashed_pg_checkout_encodings_and_bound_digests_can_vary(self):
        expected = self.derivative(); wrapper = expected['client_scene_performance']
        accepted = expected['native_responsiveness']['receipt']['build_inputs']
        paths = ('Common/sql/pg_compat.h', 'DBServer/src/pg_persistence_test.c')
        variants = []
        for name in paths:
            raw = (native.ROOT/'database/postgresql/overlay'/name).read_bytes().replace(b'\r\n', b'\n')
            variants.append(tuple(hashlib.sha256(value).hexdigest() for value in (raw, raw.replace(b'\n', b'\r\n'))))
        original = copy.deepcopy(accepted)
        for selected in itertools.product(*variants):
            changed = copy.deepcopy(expected); current = changed['client_scene_performance']
            inputs = current['manifest']['retained_source_inputs']
            pg = inputs['character_events']['progress_build_input']['game_build_input']['postgresql_build_input']
            for name, digest in zip(paths, selected): pg['overlay_sha256'][name] = digest
            bind_source_digests(inputs)
            current['manifest_sha256'] = contract.canonical_sha(current['manifest'])
            self.assertTrue(contract.scene_source_inputs_equivalent(inputs, accepted))
            self.assertTrue(contract.scene_source_inputs_equivalent(accepted, inputs))
            self.assertEqual(contract.client_contract(changed), changed['files']['CityOfHeroes.exe'])
        self.assertEqual(accepted, original)
        self.assertEqual(wrapper['manifest_sha256'], contract.canonical_sha(wrapper['manifest']))

    def test_invented_source_leaves_or_digests_rejected_even_with_rebound_scene_wrapper(self):
        expected = self.derivative(); accepted = expected['native_responsiveness']['receipt']['build_inputs']
        for name, inputs in foreign_source_variants(expected['client_scene_performance']['manifest']['retained_source_inputs']):
            changed = copy.deepcopy(expected); wrapper = changed['client_scene_performance']
            wrapper['manifest']['retained_source_inputs'] = inputs
            wrapper['manifest_sha256'] = contract.canonical_sha(wrapper['manifest'])
            with self.subTest(mutation=name), self.assertRaises(ValueError): contract.client_contract(changed)
            with self.subTest(accepted_mutation=name), self.assertRaises(ValueError):
                contract.scene_source_inputs_equivalent(accepted, inputs)

    def test_previous_native_layers_still_require_exact_raw_source_history(self):
        expected = self.derivative(); changed = copy.deepcopy(expected)
        wrapper = changed['startup_bundle_client']; inputs = wrapper['manifest']['retained_source_inputs']
        overlay = inputs['character_events']['progress_build_input']['game_build_input']['postgresql_build_input']['overlay_sha256']
        name = 'Common/sql/pg_compat.h'
        raw = (native.ROOT/'database/postgresql/overlay'/name).read_bytes().replace(b'\r\n', b'\n')
        hashes = [hashlib.sha256(value).hexdigest() for value in (raw, raw.replace(b'\n', b'\r\n'))]
        overlay[name] = next(value for value in hashes if value != overlay[name])
        bind_source_digests(inputs); wrapper['manifest_sha256'] = contract.canonical_sha(wrapper['manifest'])
        with self.assertRaises(ValueError): contract.startup_bundle_client_contract(changed)

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
