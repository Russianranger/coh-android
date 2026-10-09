"""Execute the typed renderer layer, exact cache migration and owned launch gate."""
import copy
import hashlib
import unittest
from unittest.mock import patch

import package_client_renderer_attribution_native as native
import test_client_gameplay_performance_contract as previous
import test_client_renderer_attribution_native as renderer_tests

contract, guest, index = previous.contract, previous.guest, previous.index


def native_manifest(package, record):
    accepted = package['client_gameplay_performance']['manifest']
    manifest = copy.deepcopy(accepted)
    build = copy.deepcopy(native.expected_receipt())
    checks = copy.deepcopy(accepted['windows_qualification'])
    checks.update(build_input=build, renderer=renderer_tests.expected_checks())
    manifest.update(role=native.ROLE, repository_commit='a'*40, build_input=build,
        files={'CityOfHeroes.exe': copy.deepcopy(record)},
        base_client_executable=copy.deepcopy(package['files']['CityOfHeroes.exe']),
        windows_qualification=checks)
    return manifest


def validate_actual_native_ancestry(donor, produced):
    """Run hosted checks against the actual immutable donor and genuine Win32 proof."""
    import build_client_renderer_attribution_apk as builder
    case = unittest.TestCase()
    before = copy.deepcopy((donor['_native_client_manifest'], produced))
    accepted = donor['immutable_donor_provenance']['native_responsiveness']['build_inputs']
    case.assertTrue(builder.engine.validate_native_source_ancestry(produced['retained_source_inputs'], accepted))
    wrapped = builder.client_manifest(donor, produced)
    case.assertEqual(contract.client_contract(wrapped), produced['files']['CityOfHeroes.exe'])
    for name in ('native_responsiveness', 'startup_bundle_client', 'client_loading',
            'client_startup_followup', 'client_scene_performance', 'client_gameplay_performance'):
        case.assertEqual(wrapped[name], donor['_native_client_manifest'][name])
    case.assertEqual(wrapped['client_renderer_attribution']['base_client_executable'],
        donor['_native_client_manifest']['files']['CityOfHeroes.exe'])
    rejected = []
    for name, inputs in previous.previous.foreign_source_variants(produced['retained_source_inputs']):
        with case.assertRaises(ValueError): builder.engine.validate_native_source_ancestry(inputs, accepted)
        changed = copy.deepcopy(produced); changed['retained_source_inputs'] = inputs
        with case.assertRaises(ValueError): builder.client_manifest(donor, changed)
        rejected.append(name)
    case.assertEqual((donor['_native_client_manifest'], produced), before)
    return {'status': 'passed', 'actual_external_donor_and_win32_receipts_verified': True,
        'full_guest_typed_client_wrapper_verified': True, 'older_native_history_unchanged': True,
        'actual_gameplay_Game_predecessor_verified': True, 'raw_source_histories_preserved': True,
        'rejected_foreign_variants': rejected}


class RendererContractTests(previous.ClientGameplayPerformanceContractTests):
    def setUp(self):
        previous.ClientGameplayPerformanceContractTests.setUp(self)
        self.donor = previous.ClientGameplayPerformanceContractTests.derivative(self)
        self.runtime, self.donor_report = self.prepare()
        self.donor_game = copy.deepcopy(self.donor['files']['CityOfHeroes.exe'])

    def derivative(self):
        contents, package = self.read_archive()
        raw = previous.previous.previous.old.fixtures.pe_bytes()+b'bounded-native-renderer-attribution-Game'
        record = dict(self.donor_game, size=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        manifest = native_manifest(package, record)
        package['client_renderer_attribution'] = {
            'manifest': manifest, 'manifest_sha256': contract.canonical_sha(manifest),
            'base_client_gameplay_performance_manifest_sha256': package['client_gameplay_performance']['manifest_sha256'],
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
        self.assertEqual(proof['policy'], 'verified_client_renderer_attribution_layer_v1')
        self.assertEqual(proof['previous_executable_sha256'], self.donor_game['sha256'])
        self.assertEqual(proof['layer_manifest_sha256'], expected['client_renderer_attribution']['manifest_sha256'])
        self.assertTrue(self.prepare()[1]['reused'])
        self.assertEqual(contract.client_contract(expected), expected['files']['CityOfHeroes.exe'])
        for name in ('native_responsiveness', 'startup_bundle_client', 'client_loading',
                'client_startup_followup', 'client_scene_performance', 'client_gameplay_performance'):
            self.assertEqual(expected[name], self.donor[name])

    def test_upgrade_rebinds_exact_scene_header_index_without_reading_or_rebuilding_headers(self):
        index.prepare(self.runtime, self.identity, self.donor_game['sha256'],
            previous.textures.Context({'client_worktree': self.donor_report}))
        before = (self.runtime/index.PACK).read_bytes(); expected = self.derivative(); _, report = self.prepare()
        with patch.object(index, 'make_pack', side_effect=AssertionError('Prepared headers rebuilt')):
            after, _ = self.upgraded_index(report, expected['files']['CityOfHeroes.exe'])
        self.assertTrue(after['reused']); self.assertTrue(after['native_layer_identity_migrated'])
        self.assertEqual(before[64:], (self.runtime/index.PACK).read_bytes()[64:])

    def test_new_wrapper_rejects_forged_controls_receipts_dependencies_and_predecessor(self):
        expected = self.derivative()
        for mutation in ('old_base', 'base_hash', 'format_bool', 'format_float', 'build_format_bool',
                'control_float', 'control_bool', 'worker', 'cap', 'fps_sampling', 'fps_location',
                'renderer', 'schema', 'imports', 'target', 'parent_recipe', 'platform', 'proof_header'):
            changed = copy.deepcopy(expected); wrapper = changed['client_renderer_attribution']; manifest = wrapper['manifest']; build = manifest['build_input']
            if mutation == 'old_base': wrapper['base_client_executable'] = changed['client_gameplay_performance']['base_client_executable']
            elif mutation == 'base_hash': wrapper['base_client_gameplay_performance_manifest_sha256'] = 'e'*64
            elif mutation == 'format_bool': manifest['format'] = True
            elif mutation == 'format_float': manifest['format'] = 1.0
            elif mutation == 'build_format_bool': build['format'] = True
            elif mutation == 'control_float': build['controls']['renderer_attribution']['window_report_limit_per_thread'] = 120.0
            elif mutation == 'control_bool': build['controls']['renderer_attribution']['aggregate_only'] = 1
            elif mutation == 'worker': build['controls']['renderer_attribution']['worker_configuration_unchanged'] = False
            elif mutation == 'cap': build['gameplay_frame_cap_changed'] = True
            elif mutation == 'fps_sampling': build['controls']['visible_native_fps']['sampling_unchanged'] = False
            elif mutation == 'fps_location': build['controls']['visible_native_fps']['font_grid_row'] = 0
            elif mutation == 'renderer': build['renderer_changed'] = True
            elif mutation == 'schema': manifest['schema_sources_sha256'] = {}
            elif mutation == 'imports': manifest['files']['CityOfHeroes.exe']['imports'].append('foreign.dll')
            elif mutation == 'target': build['build_targets'] = ['Game', 'MapServer']
            elif mutation == 'parent_recipe': build['base_client_gameplay_performance_build_input']['controls']['gameplay_frame_cap']['allowed_values'] = ['60']
            elif mutation == 'platform': manifest['windows_qualification']['platform'] = 'linux'
            else: manifest['windows_qualification']['renderer']['header_sha256'] = 'f'*64
            manifest['windows_qualification']['build_input'] = copy.deepcopy(build)
            wrapper['manifest_sha256'] = contract.canonical_sha(manifest)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): contract.client_contract(changed)

    def test_new_wrapper_rejects_correctly_rebound_foreign_source_ancestry(self):
        expected = self.derivative()
        for name, inputs in previous.previous.foreign_source_variants(expected['client_renderer_attribution']['manifest']['retained_source_inputs']):
            changed = copy.deepcopy(expected); wrapper = changed['client_renderer_attribution']
            wrapper['manifest']['retained_source_inputs'] = inputs; wrapper['manifest_sha256'] = contract.canonical_sha(wrapper['manifest'])
            with self.subTest(mutation=name), self.assertRaises(ValueError): contract.client_contract(changed)

    def test_source_bound_win32_proof_flags_are_typed_and_cannot_be_downgraded(self):
        expected = self.derivative(); proof = expected['client_renderer_attribution']['manifest']['windows_qualification']['renderer']
        for name in (name for name,value in proof.items() if value is True):
            for value in (False,1,1.0,None):
                changed = copy.deepcopy(expected); wrapper = changed['client_renderer_attribution']
                wrapper['manifest']['windows_qualification']['renderer'][name] = value
                wrapper['manifest_sha256'] = contract.canonical_sha(wrapper['manifest'])
                with self.subTest(name=name,value=value), self.assertRaises(ValueError): contract.client_contract(changed)


class RendererLaunchTests(unittest.TestCase):
    def setUp(self):
        previous.ClientGameplayLaunchTests.setUp(self)
        d = self.diagnostic; d.client_renderer_attribution = True
        self.renderer = {'format':1,'verified':True,'repository_commit':'7'*40,'manifest_sha256':'6'*64,
            'client_executable_sha256':d.client_executable_sha256,'source_commit':guest.SOURCE,'data_commit':guest.DATA,
            'native_source_sha256':'5'*64,'data_source_sha256':'4'*64,
            'replacement_scope':'CityOfHeroes.exe_only','source_freshness_preserved':True,
            'prepared_cache_schema_changed':False,'renderer_changed':False,'bounded_renderer_diagnostics':True,
            'queue_pacing_rendering_loading_unchanged':True,'worker_configuration_unchanged':True,
            'native_showfps_command_preserved':True}
        d.ctx.report['client_renderer_attribution'] = copy.deepcopy(self.renderer)
        d.wine_env['COH_CLIENT_RENDERER_ATTRIBUTION'] = 'untrusted'
        self.original_env = dict(d.wine_env)

    def test_verified_renderer_attempts_clear_stale_control_and_preserve_10_30_scene_pacing(self):
        d = self.diagnostic
        for profile,cap in (('performance','30'),('standard','10')):
            d.wine_env['COH_CLIENT_GRAPHICS_PROFILE'] = profile; baseline = dict(d.wine_env)
            for label in ('actual-coh-client','actual-coh-client-retry'):
                d.launch_client_attempt(label=label); env = d.ctx.start.call_args.kwargs['env']
                self.assertEqual(env['COH_CLIENT_RENDERER_ATTRIBUTION'],'1')
                self.assertEqual(env['COH_CLIENT_GAMEPLAY_FPS'],cap); self.assertEqual(env['COH_CLIENT_FRAME_TIMING'],'1')
                self.assertEqual(env['COH_CLIENT_BOUNDED_TEXTURE_ERRORS'],'1'); self.assertEqual(env['COH_CLIENT_BIN_PROFILE'],'0')
                self.assertEqual(d.wine_env,baseline); self.assertEqual(d.ctx.report['client_renderer_attribution'],self.renderer)
                self.assertFalse(d.ctx.report['client_renderer_attribution_environment']['shared_wine_environment_modified'])

    def test_unknown_or_truthy_renderer_cannot_enable_diagnostics(self):
        d = self.diagnostic
        for enabled in (False,None,1,'1',{'verified':True}):
            d.client_renderer_attribution = enabled
            for label in ('actual-coh-client','actual-coh-client-retry'):
                d.launch_client_attempt(label=label); env = d.ctx.start.call_args.kwargs['env']
                self.assertNotIn('COH_CLIENT_RENDERER_ATTRIBUTION',env)
                self.assertEqual(env['COH_CLIENT_BOUNDED_TEXTURE_ERRORS'],'1'); self.assertEqual(d.wine_env,self.original_env)

    def test_forged_renderer_producer_never_reaches_initial_or_retry_launch(self):
        d = self.diagnostic
        for field,value in (('verified',1),('format',True),('client_executable_sha256','b'*64),
                ('manifest_sha256',''),('repository_commit','foreign'),('source_commit','f'*40),
                ('native_source_sha256',''),('data_source_sha256',''),('replacement_scope','all_native'),
                ('source_freshness_preserved',1),('prepared_cache_schema_changed',True),('renderer_changed',True),
                ('bounded_renderer_diagnostics',1),('queue_pacing_rendering_loading_unchanged',False),
                ('worker_configuration_unchanged',False),('native_showfps_command_preserved',False)):
            producer = copy.deepcopy(self.renderer); producer[field] = value; d.ctx.report['client_renderer_attribution'] = producer
            for label in ('actual-coh-client','actual-coh-client-retry'):
                with self.subTest(field=field,label=label),self.assertRaisesRegex(guest.base.DiagnosticError,'current verified Game producer'):
                    d.launch_client_attempt(label=label)
                d.ctx.start.assert_not_called(); self.assertEqual(d.wine_env,self.original_env)


if __name__ == '__main__': unittest.main()
