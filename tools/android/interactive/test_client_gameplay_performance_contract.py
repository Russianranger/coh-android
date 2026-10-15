"""Qualify the new Game wrapper, exact predecessor upgrade and owned launches."""
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

import package_client_gameplay_performance_native as native
import test_client_scene_performance_contract as previous
import test_client_preload_launch as launches

contract, guest, index, textures = previous.contract, previous.guest, previous.index, previous.textures


def native_manifest(package, record):
    manifest = copy.deepcopy(package['client_scene_performance']['manifest'])
    build = copy.deepcopy(native.expected_receipt())
    import test_client_gameplay_performance_native as gameplay_tests
    checks = copy.deepcopy(manifest['windows_qualification'])
    checks.update(build_input=build, gameplay=gameplay_tests.expected_checks())
    manifest.update(role=native.ROLE, repository_commit='a'*40, build_input=build,
        files={'CityOfHeroes.exe': copy.deepcopy(record)},
        base_client_executable=copy.deepcopy(package['files']['CityOfHeroes.exe']),
        windows_qualification=checks)
    return manifest


def validate_actual_native_ancestry(donor, produced):
    """Hosted qualification uses the real donor and actual Win32 source proofs."""
    import build_client_gameplay_performance_apk as builder
    case = unittest.TestCase()
    before = copy.deepcopy((donor['_native_client_manifest'], produced))
    accepted = donor['immutable_donor_provenance']['native_responsiveness']['build_inputs']
    case.assertTrue(builder.validate_native_source_ancestry(produced['retained_source_inputs'], accepted))
    wrapped = builder.client_manifest(donor, produced)
    case.assertEqual(contract.client_contract(wrapped), produced['files']['CityOfHeroes.exe'])
    for name in ('native_responsiveness', 'startup_bundle_client', 'client_loading',
            'client_startup_followup', 'client_scene_performance'):
        case.assertEqual(wrapped[name], donor['_native_client_manifest'][name])
    case.assertEqual(wrapped['client_gameplay_performance']['base_client_executable'],
        donor['_native_client_manifest']['files']['CityOfHeroes.exe'])
    rejected = []
    for name, inputs in previous.foreign_source_variants(produced['retained_source_inputs']):
        with case.assertRaises(ValueError): builder.validate_native_source_ancestry(inputs, accepted)
        changed = copy.deepcopy(produced); changed['retained_source_inputs'] = inputs
        with case.assertRaises(ValueError): builder.client_manifest(donor, changed)
        rejected.append(name)
    case.assertEqual((donor['_native_client_manifest'], produced), before)
    return {'status': 'passed', 'actual_external_donor_and_win32_receipts_verified': True,
        'full_guest_typed_client_wrapper_verified': True, 'older_native_history_unchanged': True,
        'actual_scene_Game_predecessor_verified': True, 'raw_source_histories_preserved': True,
        'rejected_foreign_variants': rejected}


class ClientGameplayPerformanceContractTests(unittest.TestCase):
    read_archive = previous.ClientScenePerformanceContractTests.read_archive
    write_archive = previous.ClientScenePerformanceContractTests.write_archive
    prepare = previous.ClientScenePerformanceContractTests.prepare
    preserved = previous.ClientScenePerformanceContractTests.preserved
    loading_derivative = previous.ClientScenePerformanceContractTests.loading_derivative
    upgraded_index = previous.ClientScenePerformanceContractTests.upgraded_index

    def setUp(self):
        previous.ClientScenePerformanceContractTests.setUp(self)
        self.donor = previous.ClientScenePerformanceContractTests.derivative(self)
        self.runtime, self.donor_report = self.prepare()
        self.donor_game = copy.deepcopy(self.donor['files']['CityOfHeroes.exe'])

    def derivative(self):
        contents, package = self.read_archive()
        raw = previous.previous.old.fixtures.pe_bytes()+b'bounded-native-gameplay-30fps-Game'
        record = dict(self.donor_game, size=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        manifest = native_manifest(package, record)
        package['client_gameplay_performance'] = {
            'manifest': manifest, 'manifest_sha256': contract.canonical_sha(manifest),
            'base_client_scene_performance_manifest_sha256': package['client_scene_performance']['manifest_sha256'],
            'base_client_executable': copy.deepcopy(self.donor_game)}
        package['files']['CityOfHeroes.exe'] = record; contents['CityOfHeroes.exe'] = raw
        self.write_archive(contents, package)
        return package

    def test_upgrade_preserves_generated_cache_private_inputs_and_all_previous_wrappers(self):
        before = self.preserved(); expected = self.derivative()
        with patch.object(guest.os, 'scandir', side_effect=AssertionError('Input trees recreated')):
            runtime, report = self.prepare()
        self.assertEqual(runtime, self.runtime); self.assertEqual(before, self.preserved())
        self.assertTrue(report['native_executable_upgraded']); self.assertTrue(report['generated_cache_bytes_preserved'])
        proof = report['native_texture_index_migration']
        self.assertEqual(proof['policy'], 'verified_client_gameplay_performance_layer_v1')
        self.assertEqual(proof['previous_executable_sha256'], self.donor_game['sha256'])
        self.assertNotEqual(proof['previous_executable_sha256'],
            expected['client_scene_performance']['base_client_executable']['sha256'])
        self.assertEqual(proof['layer_manifest_sha256'], expected['client_gameplay_performance']['manifest_sha256'])
        self.assertEqual(self.server_leaf.resolve(strict=True), self.supplement)
        self.assertTrue(self.prepare()[1]['reused'])
        self.assertEqual(contract.client_contract(expected), expected['files']['CityOfHeroes.exe'])
        for name in ('native_responsiveness', 'startup_bundle_client', 'client_loading',
                'client_startup_followup', 'client_scene_performance'):
            self.assertEqual(expected[name], self.donor[name])

    def test_upgrade_rebinds_exact_scene_header_index_without_reading_or_rebuilding_headers(self):
        index.prepare(self.runtime, self.identity, self.donor_game['sha256'],
            textures.Context({'client_worktree': self.donor_report}))
        before = (self.runtime/index.PACK).read_bytes()
        expected = self.derivative(); _, report = self.prepare()
        with patch.object(index, 'make_pack', side_effect=AssertionError('Prepared headers rebuilt')):
            after, _ = self.upgraded_index(report, expected['files']['CityOfHeroes.exe'])
        self.assertTrue(after['reused']); self.assertTrue(after['native_layer_identity_migrated'])
        self.assertEqual(before[64:], (self.runtime/index.PACK).read_bytes()[64:])

    def test_new_wrapper_rejects_forged_controls_receipts_dependencies_and_predecessor(self):
        expected = self.derivative()
        for mutation in ('base_hash', 'old_base', 'format_bool', 'format_float', 'build_format_bool',
                'control_float', 'control_bool', 'menu_cap', 'fallback', 'maxfps_command',
                'renderer', 'schema', 'imports', 'target', 'scene_recipe', 'platform', 'proof_header'):
            changed = copy.deepcopy(expected); wrapper = changed['client_gameplay_performance']
            manifest = wrapper['manifest']; build = manifest['build_input']
            if mutation == 'base_hash': wrapper['base_client_scene_performance_manifest_sha256'] = 'e'*64
            elif mutation == 'old_base': wrapper['base_client_executable'] = changed['client_scene_performance']['base_client_executable']
            elif mutation == 'format_bool': manifest['format'] = True
            elif mutation == 'format_float': manifest['format'] = 1.0
            elif mutation == 'build_format_bool': build['format'] = True
            elif mutation == 'control_float': build['controls']['bounded_texture_errors']['retained_key_limit'] = 64.0
            elif mutation == 'control_bool': build['controls']['gameplay_frame_cap']['create_bins_excluded'] = 1
            elif mutation == 'menu_cap': build['controls']['gameplay_frame_cap']['menus_and_background_cap_retained'] = False
            elif mutation == 'fallback': build['controls']['bounded_texture_errors']['texture_load_fallback_and_assignments_preserved'] = False
            elif mutation == 'maxfps_command': build['controls']['gameplay_frame_cap']['runtime_maxfps_command_preserved'] = False
            elif mutation == 'renderer': build['renderer_changed'] = True
            elif mutation == 'schema': manifest['schema_sources_sha256'] = {}
            elif mutation == 'imports': manifest['files']['CityOfHeroes.exe']['imports'].append('foreign.dll')
            elif mutation == 'target': build['build_targets'] = ['Game', 'MapServer']
            elif mutation == 'scene_recipe': build['base_client_scene_performance_build_input']['controls']['frame_profile']['bounded'] = False
            elif mutation == 'platform': manifest['windows_qualification']['platform'] = 'linux'
            else: manifest['windows_qualification']['gameplay']['header_sha256'] = 'f'*64
            manifest['windows_qualification']['build_input'] = copy.deepcopy(build)
            wrapper['manifest_sha256'] = contract.canonical_sha(manifest)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): contract.client_contract(changed)

    def test_new_wrapper_rejects_correctly_rebound_foreign_source_ancestry(self):
        expected = self.derivative()
        for name, inputs in previous.foreign_source_variants(
                expected['client_gameplay_performance']['manifest']['retained_source_inputs']):
            changed = copy.deepcopy(expected); wrapper = changed['client_gameplay_performance']
            wrapper['manifest']['retained_source_inputs'] = inputs
            wrapper['manifest_sha256'] = contract.canonical_sha(wrapper['manifest'])
            with self.subTest(mutation=name), self.assertRaises(ValueError): contract.client_contract(changed)

    def test_source_bound_win32_proof_flags_are_typed_and_cannot_be_downgraded(self):
        expected = self.derivative()
        proof = expected['client_gameplay_performance']['manifest']['windows_qualification']['gameplay']
        flags = [name for name, value in proof.items() if value is True]
        for name in flags:
            for value in (False, 1, 1.0, None):
                changed = copy.deepcopy(expected); wrapper = changed['client_gameplay_performance']
                wrapper['manifest']['windows_qualification']['gameplay'][name] = value
                wrapper['manifest_sha256'] = contract.canonical_sha(wrapper['manifest'])
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    contract.client_contract(changed)


class ClientGameplayLaunchTests(unittest.TestCase):
    def setUp(self):
        launches.ClientSceneLaunchTests.setUp(self)
        d = self.diagnostic
        d.client_gameplay_performance = True
        self.gameplay = {
            'repository_commit': '9'*40, 'manifest_sha256': '8'*64,
            'client_executable_sha256': launches.GAME_SHA, 'replacement_scope': 'CityOfHeroes.exe_only',
            'source_freshness_preserved': True, 'prepared_cache_schema_changed': False,
            'renderer_changed': False, 'menus_and_background_cap_retained': True,
            'runtime_maxfps_command_preserved': True, 'bounded_texture_errors': True,
            'texture_load_fallback_and_assignments_preserved': True}
        d.ctx.report['client_gameplay_performance'] = copy.deepcopy(self.gameplay)
        d.wine_env.update(COH_CLIENT_GRAPHICS_PROFILE='performance', COH_CLIENT_GAMEPLAY_FPS='untrusted-240',
            COH_CLIENT_BOUNDED_TEXTURE_ERRORS='untrusted')
        self.original_env = dict(d.wine_env)

    def test_initial_and_retry_use_qualified_30fps_or_10fps_and_keep_scene_profiles(self):
        d = self.diagnostic
        for profile, cap in (('performance', '30'), ('standard', '10')):
            d.wine_env['COH_CLIENT_GRAPHICS_PROFILE'] = profile; baseline = dict(d.wine_env)
            for label in ('actual-coh-client', 'actual-coh-client-retry'):
                d.launch_client_attempt(label=label)
                env = d.ctx.start.call_args.kwargs['env']
                self.assertEqual(env['COH_CLIENT_GAMEPLAY_FPS'], cap)
                self.assertEqual(env['COH_CLIENT_BOUNDED_TEXTURE_ERRORS'], '1')
                self.assertEqual(env['COH_CLIENT_SCENE_PROFILE'], '1')
                self.assertEqual(env['COH_CLIENT_FRAME_TIMING'], '1')
                self.assertEqual(env['COH_CLIENT_BIN_PROFILE'], '0')
                report = d.ctx.report['client_gameplay_performance_environment']
                self.assertEqual(report['launch_label'], label); self.assertEqual(report['gameplay_fps_requested'], cap)
                self.assertFalse(report['shared_wine_environment_modified'])
                self.assertEqual(d.wine_env, baseline)
                self.assertEqual(d.ctx.report['client_gameplay_performance'], self.gameplay)

    def test_plain_startup_effective_standard_profile_cannot_inherit_requested_performance_cap(self):
        d = self.diagnostic; environment = dict(d.wine_env)
        guest.apply_client_gameplay_environment(d, environment, 'actual-coh-client', 'standard')
        self.assertEqual(environment['COH_CLIENT_GAMEPLAY_FPS'], '10')
        self.assertEqual(environment['COH_CLIENT_BOUNDED_TEXTURE_ERRORS'], '1')
        self.assertEqual(d.wine_env, self.original_env)

    def test_unknown_or_truthy_producer_strips_only_new_controls_on_both_attempts(self):
        d = self.diagnostic
        for enabled in (False, None, 1, '1', {'verified': True}):
            d.client_gameplay_performance = enabled
            for label in ('actual-coh-client', 'actual-coh-client-retry'):
                d.launch_client_attempt(label=label)
                env = d.ctx.start.call_args.kwargs['env']
                self.assertNotIn('COH_CLIENT_GAMEPLAY_FPS', env)
                self.assertNotIn('COH_CLIENT_BOUNDED_TEXTURE_ERRORS', env)
                self.assertEqual(env['COH_CLIENT_SCENE_PROFILE'], '1')
                self.assertFalse(d.ctx.report['client_gameplay_performance_environment']['enabled'])
                self.assertEqual(d.wine_env, self.original_env)

    def test_forged_current_producer_never_reaches_initial_or_retry_launch(self):
        d = self.diagnostic
        for field, value in (('client_executable_sha256', 'b'*64), ('manifest_sha256', ''),
                ('repository_commit', 'foreign'), ('replacement_scope', 'all_native'),
                ('menus_and_background_cap_retained', 1), ('runtime_maxfps_command_preserved', False),
                ('bounded_texture_errors', 1), ('texture_load_fallback_and_assignments_preserved', False),
                ('prepared_cache_schema_changed', True), ('renderer_changed', True)):
            producer = copy.deepcopy(self.gameplay); producer[field] = value
            d.ctx.report['client_gameplay_performance'] = producer
            for label in ('actual-coh-client', 'actual-coh-client-retry'):
                with self.subTest(field=field, label=label), self.assertRaisesRegex(
                        guest.base.DiagnosticError, 'current verified Game producer'):
                    d.launch_client_attempt(label=label)
                d.ctx.start.assert_not_called(); self.assertEqual(d.wine_env, self.original_env)


if __name__ == '__main__': unittest.main()
