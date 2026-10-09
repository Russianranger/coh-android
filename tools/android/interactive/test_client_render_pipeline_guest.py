"""Exercise the typed Game extension, retained cache upgrade and attempt gates.

Fixtures execute the complete guest contract; finite native/WGL execution is
mocked only in selection tests, where the retained probe ownership and bounded
failure behavior remain covered by the unchanged GPU regression suite.
"""
import copy
import functools
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import package_client_render_pipeline_native as native
import test_client_render_pipeline_native as native_tests
import test_client_renderer_attribution_contract as previous
import test_client_gpu_profile as gpu_tests
import character_reopen_diagnostic as reopen

contract, guest, index = previous.contract, previous.guest, previous.index
gpu = gpu_tests.gpu


def native_manifest(package, record):
    accepted = package['client_renderer_attribution']['manifest']
    manifest = copy.deepcopy(accepted)
    build = copy.deepcopy(native.expected_receipt())
    checks = copy.deepcopy(accepted['windows_qualification'])
    checks.update(build_input=build, pipeline=native_tests.expected_checks())
    manifest.update(role=native.ROLE, repository_commit='b' * 40, build_input=build,
        files={'CityOfHeroes.exe': copy.deepcopy(record)},
        base_client_executable=copy.deepcopy(package['files']['CityOfHeroes.exe']),
        windows_qualification=checks)
    return manifest


class RenderPipelineContractTests(previous.RendererContractTests):
    def setUp(self):
        previous.RendererContractTests.setUp(self)
        self.donor = previous.RendererContractTests.derivative(self)
        self.runtime, self.donor_report = self.prepare()
        self.donor_game = copy.deepcopy(self.donor['files']['CityOfHeroes.exe'])

    def derivative(self):
        contents, package = self.read_archive()
        raw = previous.previous.previous.previous.old.fixtures.pe_bytes() + b'focused-render-pipeline-Game'
        record = dict(self.donor_game, size=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        manifest = native_manifest(package, record)
        package['client_render_pipeline'] = {
            'manifest': manifest, 'manifest_sha256': contract.canonical_sha(manifest),
            'base_client_renderer_attribution_manifest_sha256': package['client_renderer_attribution']['manifest_sha256'],
            'base_client_executable': copy.deepcopy(self.donor_game)}
        package['files']['CityOfHeroes.exe'] = record
        contents['CityOfHeroes.exe'] = raw
        self.write_archive(contents, package)
        return package

    def test_upgrade_preserves_generated_cache_private_inputs_and_all_previous_wrappers(self):
        before = self.preserved()
        expected = self.derivative()
        with mock.patch.object(guest.os, 'scandir', side_effect=AssertionError('Input trees recreated')):
            runtime, report = self.prepare()
        self.assertEqual(runtime, self.runtime)
        self.assertEqual(before, self.preserved())
        self.assertTrue(report['native_executable_upgraded'])
        self.assertTrue(report['generated_cache_bytes_preserved'])
        proof = report['native_texture_index_migration']
        self.assertEqual(proof['policy'], 'verified_client_render_pipeline_layer_v1')
        self.assertEqual(proof['previous_executable_sha256'], self.donor_game['sha256'])
        self.assertEqual(proof['layer_manifest_sha256'], expected['client_render_pipeline']['manifest_sha256'])
        self.assertTrue(self.prepare()[1]['reused'])
        self.assertEqual(contract.client_contract(expected), expected['files']['CityOfHeroes.exe'])
        for name in ('native_responsiveness', 'startup_bundle_client', 'client_loading',
                'client_startup_followup', 'client_scene_performance', 'client_gameplay_performance',
                'client_renderer_attribution'):
            self.assertEqual(expected[name], self.donor[name])

    def test_upgrade_rebinds_exact_scene_header_index_without_reading_or_rebuilding_headers(self):
        index.prepare(self.runtime, self.identity, self.donor_game['sha256'],
            previous.previous.textures.Context({'client_worktree': self.donor_report}))
        before = (self.runtime / index.PACK).read_bytes()
        expected = self.derivative()
        _, report = self.prepare()
        with mock.patch.object(index, 'make_pack', side_effect=AssertionError('Prepared headers rebuilt')):
            after, _ = self.upgraded_index(report, expected['files']['CityOfHeroes.exe'])
        self.assertTrue(after['reused'])
        self.assertTrue(after['native_layer_identity_migrated'])
        self.assertEqual(before[64:], (self.runtime / index.PACK).read_bytes()[64:])

    def test_new_wrapper_rejects_forged_controls_receipts_dependencies_and_predecessor(self):
        expected = self.derivative()
        mutations = ('base_hash', 'old_base', 'format_bool', 'format_float', 'sample_float',
            'blocking_gpu', 'fidelity', 'worker_order', 'worker_recheck', 'gameplay_cap', 'schema',
            'imports', 'renderer_recipe', 'windows_platform', 'proof_header')
        for mutation in mutations:
            changed = copy.deepcopy(expected)
            wrapper = changed['client_render_pipeline']
            manifest = wrapper['manifest']
            build = manifest['build_input']
            if mutation == 'base_hash': wrapper['base_client_renderer_attribution_manifest_sha256'] = 'e' * 64
            elif mutation == 'old_base': wrapper['base_client_executable'] = changed['client_renderer_attribution']['base_client_executable']
            elif mutation == 'format_bool': manifest['format'] = True
            elif mutation == 'format_float': manifest['format'] = 1.0
            elif mutation == 'sample_float': build['controls']['render_pipeline']['command_sample_interval'] = 16.0
            elif mutation == 'blocking_gpu': build['controls']['render_pipeline']['blocking_gpu_measurement'] = True
            elif mutation == 'fidelity': build['graphics_profile_changes'] = True
            elif mutation == 'worker_order': build['controls']['worker_wake_repair']['asleep_published_before_event_reset'] = False
            elif mutation == 'worker_recheck': build['controls']['worker_wake_repair']['empty_queue_recheck_preserved'] = 1
            elif mutation == 'gameplay_cap': build['gameplay_frame_cap_changed'] = True
            elif mutation == 'schema': manifest['schema_sources_sha256'] = {}
            elif mutation == 'imports': manifest['files']['CityOfHeroes.exe']['imports'].append('foreign.dll')
            elif mutation == 'renderer_recipe': build['base_client_renderer_attribution_build_input']['controls']['renderer_attribution']['aggregate_only'] = False
            elif mutation == 'windows_platform': manifest['windows_qualification']['platform'] = 'linux'
            else: manifest['windows_qualification']['pipeline']['header_sha256'] = 'f' * 64
            manifest['windows_qualification']['build_input'] = copy.deepcopy(build)
            wrapper['manifest_sha256'] = contract.canonical_sha(manifest)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                contract.client_contract(changed)

    def test_source_bound_win32_proof_flags_are_typed_and_cannot_be_downgraded(self):
        expected = self.derivative()
        proof = expected['client_render_pipeline']['manifest']['windows_qualification']['pipeline']
        for name in (name for name, value in proof.items() if value is True):
            for value in (False, 1, 1.0, None):
                changed = copy.deepcopy(expected)
                wrapper = changed['client_render_pipeline']
                wrapper['manifest']['windows_qualification']['pipeline'][name] = value
                wrapper['manifest_sha256'] = contract.canonical_sha(wrapper['manifest'])
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    contract.client_contract(changed)


@functools.lru_cache(maxsize=1)
def typed_gpu_package():
    """Use the real contract fixture; rebind only its retained public Game pin.

    Archive/cache tests above verify synthetic bytes independently. Selection
    tests need the exact .19/.21 production predecessor enforced by the GPU
    gate, so this in-memory history uses that public executable identity.
    """
    fixture = RenderPipelineContractTests('test_upgrade_preserves_generated_cache_private_inputs_and_all_previous_wrappers')
    try:
        fixture.setUp()
        package = fixture.derivative()
    finally:
        fixture.doCleanups()
    parent = package['client_renderer_attribution']
    parent['manifest']['repository_commit'] = gpu.GAME_SOURCE_COMMIT
    parent['manifest']['files']['CityOfHeroes.exe'].update(sha256=gpu.GAME_SHA256, size=9487872)
    parent['manifest_sha256'] = contract.canonical_sha(parent['manifest'])
    wrapper = package['client_render_pipeline']
    wrapper['base_client_renderer_attribution_manifest_sha256'] = parent['manifest_sha256']
    wrapper['base_client_executable'] = copy.deepcopy(parent['manifest']['files']['CityOfHeroes.exe'])
    wrapper['manifest']['base_client_executable'] = copy.deepcopy(wrapper['base_client_executable'])
    wrapper['manifest_sha256'] = contract.canonical_sha(wrapper['manifest'])
    contract.client_contract(package)
    return package


def install_pipeline(owner):
    package = copy.deepcopy(typed_gpu_package())
    wrapper = package['client_render_pipeline']
    owner.client_executable_sha256 = package['files']['CityOfHeroes.exe']['sha256']
    owner.client_render_pipeline = True
    owner.client_render_pipeline_package = package
    owner.ctx.report['import_identity'] = {'contract_sha256': '4' * 64}
    owner.ctx.report['client_render_pipeline'] = {
        'format': 1, 'verified': True, 'repository_commit': wrapper['manifest']['repository_commit'],
        'manifest_sha256': wrapper['manifest_sha256'],
        'base_client_renderer_attribution_manifest_sha256': wrapper['base_client_renderer_attribution_manifest_sha256'],
        'base_client_executable_sha256': gpu.GAME_SHA256,
        'client_executable_sha256': owner.client_executable_sha256,
        'source_commit': guest.SOURCE, 'data_commit': guest.DATA,
        'native_source_sha256': contract.canonical_sha(wrapper['manifest']['retained_source_inputs']),
        'data_source_sha256': '4' * 64, 'replacement_scope': 'CityOfHeroes.exe_only',
        'source_freshness_preserved': True, 'prepared_cache_schema_changed': False,
        'renderer_changed': False, 'graphics_fidelity_preserved': True,
        'gameplay_frame_cap_changed': False, 'bounded_render_pipeline_diagnostics': True,
        'worker_wakeup_repaired': True, 'physical_fps_improvement_validated': False}
    owner.ctx.report['client_renderer_attribution'].update(repository_commit=gpu.GAME_SOURCE_COMMIT,
        manifest_sha256=package['client_renderer_attribution']['manifest_sha256'],
        client_executable_sha256=gpu.GAME_SHA256)
    return package


class RenderPipelineLaunchTests(unittest.TestCase):
    def setUp(self):
        previous.RendererLaunchTests.setUp(self)
        # Creation retains .22 focused instrumentation. Saved-character reopen
        # has an independently tested .23 isolation policy below.
        creation = reopen.creation.CharacterCreationDiagnostic.__new__(reopen.creation.CharacterCreationDiagnostic)
        creation.__dict__.update(self.diagnostic.__dict__)
        self.diagnostic = creation
        self.package = install_pipeline(self.diagnostic)
        for name in ('client_startup_followup', 'client_scene_performance', 'client_gameplay_performance'):
            self.diagnostic.ctx.report[name]['client_executable_sha256'] = self.diagnostic.client_executable_sha256
        self.diagnostic.wine_env['COH_CLIENT_RENDER_PIPELINE'] = 'untrusted'
        self.original_env = dict(self.diagnostic.wine_env)

    def test_initial_and_retry_bind_current_Game_and_preserve_historical_renderer_producer(self):
        d = self.diagnostic
        before = copy.deepcopy(d.ctx.report['client_renderer_attribution'])
        for label in ('actual-coh-client', 'actual-coh-client-retry'):
            d.launch_client_attempt(label=label)
            env = d.ctx.start.call_args.kwargs['env']
            self.assertEqual(env['COH_CLIENT_RENDER_PIPELINE'], '1')
            self.assertEqual(env['COH_CLIENT_RENDERER_ATTRIBUTION'], '1')
            self.assertEqual(env['COH_CLIENT_GAMEPLAY_FPS'], '30')
            self.assertEqual(d.wine_env, self.original_env)
            self.assertEqual(d.ctx.report['client_renderer_attribution'], before)
            receipt = d.ctx.report['client_render_pipeline_environment']
            self.assertEqual(receipt['client_executable_sha256'], d.client_executable_sha256)
            self.assertEqual(receipt['command_sample_interval'], 16)
            self.assertFalse(receipt['physical_fps_improvement_validated'])
        self.assertEqual(before['client_executable_sha256'], gpu.GAME_SHA256)
        self.assertNotEqual(before['client_executable_sha256'], d.client_executable_sha256)

    def test_disabled_untyped_pipeline_clears_inherited_control_without_mutating_baseline(self):
        d = self.diagnostic
        for flag in (False, None, 1, '1', {}):
            d.client_render_pipeline = flag
            attempt = dict(d.wine_env)
            guest.apply_client_render_pipeline_environment(d, attempt, 'owned-Game')
            self.assertNotIn('COH_CLIENT_RENDER_PIPELINE', attempt)
            self.assertEqual(d.wine_env, self.original_env)
            self.assertFalse(d.ctx.report['client_render_pipeline_environment']['enabled'])

    def test_forged_current_pipeline_producer_cannot_reach_initial_or_retry_Game(self):
        d = self.diagnostic
        accepted = copy.deepcopy(d.ctx.report['client_render_pipeline'])
        for field, wrong in (('verified', 1), ('format', True), ('repository_commit', 'f' * 40),
                ('manifest_sha256', 'e' * 64), ('base_client_executable_sha256', 'e' * 64),
                ('client_executable_sha256', gpu.GAME_SHA256), ('native_source_sha256', 'e' * 64),
                ('data_source_sha256', 'e' * 64), ('graphics_fidelity_preserved', 1),
                ('renderer_changed', True), ('worker_wakeup_repaired', False),
                ('physical_fps_improvement_validated', True)):
            d.ctx.report['client_render_pipeline'] = dict(accepted, **{field: wrong})
            for label in ('actual-coh-client', 'actual-coh-client-retry'):
                with self.subTest(field=field, label=label), self.assertRaises(gpu.GPUProfileError):
                    d.launch_client_attempt(label=label)
                d.ctx.start.assert_not_called()
                self.assertEqual(d.wine_env, self.original_env)


class ReopenRenderPipelineIsolationTests(unittest.TestCase):
    def setUp(self):
        RenderPipelineLaunchTests.setUp(self)

    def select_reopen(self, cls=reopen.StartupOnlyCharacterReopenDiagnostic):
        diagnostic = cls.__new__(cls)
        diagnostic.__dict__.update(self.diagnostic.__dict__)
        self.diagnostic = diagnostic
        return diagnostic

    def test_owned_saved_character_initial_and_retry_isolate_only_new_metrics(self):
        for cls in (reopen.CharacterReopenDiagnostic, reopen.StartupOnlyCharacterReopenDiagnostic):
            d = self.select_reopen(cls)
            before = copy.deepcopy(d.ctx.report['client_renderer_attribution'])
            for label in ('actual-coh-client', 'actual-coh-client-retry'):
                with self.subTest(mode=cls.__name__, label=label):
                    d.launch_client_attempt(label=label)
                    env = d.ctx.start.call_args.kwargs['env']
                    self.assertEqual(env['COH_CLIENT_RENDER_PIPELINE'], '0')
                    self.assertEqual(env['COH_CLIENT_FRAME_TIMING'], '1')
                    self.assertEqual(env['COH_CLIENT_RENDERER_ATTRIBUTION'], '1')
                    self.assertEqual(env['COH_CLIENT_GAMEPLAY_FPS'], '30')
                    self.assertEqual(d.wine_env, self.original_env)
                    self.assertEqual(d.ctx.report['client_renderer_attribution'], before)
                    receipt = d.ctx.report['client_render_pipeline_environment']
                    self.assertEqual(receipt['client_executable_sha256'], d.client_executable_sha256)
                    self.assertEqual(receipt['launch_label'], label)
                    self.assertFalse(receipt['enabled'])
                    self.assertEqual(receipt['render_pipeline'], '0')
                    self.assertIsNone(receipt['record_prefix'])
                    self.assertIsNone(receipt['command_sample_interval'])
                    self.assertTrue(receipt['performance_isolation'])
                    self.assertEqual(receipt['disabled_reason'], 'thor_0_13_22_performance_regression_isolation')
                    self.assertTrue(receipt['frame_timing_retained'])
                    self.assertTrue(receipt['renderer_attribution_retained'])
                    self.assertFalse(receipt['physical_fps_improvement_validated'])

    def test_false_or_untyped_pipeline_never_gains_reopen_override(self):
        # The prior typed renderer has no focused extension. No inherited or
        # truthy value can enable the new extension or create an isolation claim.
        previous.RendererLaunchTests.setUp(self)
        d = self.select_reopen()
        d.wine_env['COH_CLIENT_RENDER_PIPELINE'] = 'inherited-untrusted'
        baseline = dict(d.wine_env)
        for flag in (False, None, 1, '1', {}):
            d.client_render_pipeline = flag
            for label in ('actual-coh-client', 'actual-coh-client-retry'):
                with self.subTest(flag=flag, label=label):
                    d.launch_client_attempt(label=label)
                    env = d.ctx.start.call_args.kwargs['env']
                    self.assertNotIn('COH_CLIENT_RENDER_PIPELINE', env)
                    self.assertEqual(env['COH_CLIENT_FRAME_TIMING'], '1')
                    self.assertEqual(env['COH_CLIENT_RENDERER_ATTRIBUTION'], '1')
                    self.assertFalse(d.ctx.report['client_render_pipeline_environment']['enabled'])
                    self.assertNotIn('performance_isolation', d.ctx.report['client_render_pipeline_environment'])
                    self.assertEqual(d.wine_env, baseline)

    def test_forged_current_game_cannot_reach_reopen_isolation_or_retry_launch(self):
        d = self.select_reopen()
        accepted = copy.deepcopy(d.ctx.report['client_render_pipeline'])
        for field, wrong in (('verified', 1), ('format', True), ('repository_commit', 'f' * 40),
                ('manifest_sha256', 'e' * 64), ('client_executable_sha256', gpu.GAME_SHA256),
                ('native_source_sha256', 'e' * 64), ('physical_fps_improvement_validated', True)):
            d.ctx.report['client_render_pipeline'] = dict(accepted, **{field: wrong})
            for label in ('actual-coh-client', 'actual-coh-client-retry'):
                with self.subTest(field=field, label=label), self.assertRaises(gpu.GPUProfileError):
                    d.launch_client_attempt(label=label)
                d.ctx.start.assert_not_called()
                self.assertEqual(d.wine_env, self.original_env)


class RenderPipelineGPUSelectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.owner, self.baseline = gpu_tests.make_owner(Path(temporary.name))
        self.package = install_pipeline(self.owner)

    def test_new_typed_Game_uses_retained_GPU_payload_with_distinct_producer_receipts(self):
        before = dict(self.baseline)
        with (mock.patch.object(gpu, 'platform_is_arm64', return_value=True),
                mock.patch.object(gpu_tests.base, 'arm64_elf'), mock.patch.object(gpu_tests.base, 'verify_pe32'),
                mock.patch.object(gpu, 'run_probe', return_value=gpu_tests.marker(gpu.NATIVE_PREFIX, gpu_tests.native_result())),
                mock.patch.object(gpu, 'private_wgl_probe', return_value=gpu_tests.wgl_result())):
            for label in ('actual-coh-client', 'actual-coh-client-retry'):
                candidate = gpu.apply_profile(self.owner, self.baseline, label)
                receipt = self.owner.ctx.report['client_gpu_profile']
                self.assertEqual(receipt['selected'], 'turnip')
                self.assertEqual(candidate['MESA_LOADER_DRIVER_OVERRIDE'], 'zink')
                self.assertEqual(receipt['game_producer']['client_executable_sha256'], self.owner.client_executable_sha256)
                self.assertEqual(receipt['game_producer']['retained_renderer_executable_sha256'], gpu.GAME_SHA256)
                self.assertEqual(receipt['gpu_payload_producer']['archive_sha256'], self.owner.ctx.report['asset_sha256'][gpu.ARCHIVE])
                self.assertNotEqual(receipt['game_producer']['repository_commit'], receipt['gpu_payload_producer']['repository_commit'])
                self.assertFalse(receipt['physical_fps_improvement_validated'])
        self.assertEqual(self.baseline, before)

    def test_claimed_replacement_hash_without_typed_extension_stays_Software(self):
        del self.owner.client_render_pipeline_package
        with mock.patch.object(gpu, 'verify_archive', side_effect=AssertionError('Unqualified Game reached payload')):
            self.assertEqual(gpu.apply_profile(self.owner, self.baseline, 'actual-coh-client'), self.baseline)
        self.assertEqual(self.owner.ctx.report['client_gpu_profile']['state'], 'software_fallback')
        self.assertTrue(self.owner.ctx.report['client_gpu_profile']['probe_cleanup_safe'])

    def test_rebound_foreign_wrapper_source_Dll_or_predecessor_is_rejected_before_payload(self):
        accepted = copy.deepcopy(self.package)
        for mutation in ('imports', 'recipe', 'source', 'base', 'dll'):
            package = copy.deepcopy(accepted)
            wrapper = package['client_render_pipeline']
            if mutation == 'imports': wrapper['manifest']['files']['CityOfHeroes.exe']['imports'].append('foreign.dll')
            elif mutation == 'recipe': wrapper['manifest']['build_input']['controls']['render_pipeline']['command_sample_interval'] = 1
            elif mutation == 'source': package['client_renderer_attribution']['manifest']['repository_commit'] = 'f' * 40
            elif mutation == 'base': wrapper['base_client_executable']['sha256'] = 'e' * 64
            else: package['files']['fixture0.dll']['sha256'] = 'e' * 64
            wrapper['manifest_sha256'] = contract.canonical_sha(wrapper['manifest'])
            self.owner.client_render_pipeline_package = package
            self.owner.ctx.report['client_render_pipeline']['manifest_sha256'] = wrapper['manifest_sha256']
            # Use the direct gate: fallback attempt count intentionally remains
            # untouched so every malformed current package reaches validation.
            with self.subTest(mutation=mutation), self.assertRaises((ValueError, gpu.GPUProfileError)):
                gpu.current_game_producer(self.owner)
        self.owner.client_render_pipeline_package = accepted

    def test_exact_old_Game_route_remains_accepted_and_foreign_bytes_stay_rejected(self):
        self.owner.client_render_pipeline = False
        self.owner.client_executable_sha256 = gpu.GAME_SHA256
        proof = gpu.current_game_producer(self.owner)
        self.assertEqual(proof['policy'], 'exact_retained_renderer_Game_v1')
        self.owner.client_executable_sha256 = 'e' * 64
        self.owner.ctx.report['client_renderer_attribution']['client_executable_sha256'] = 'e' * 64
        with self.assertRaises(gpu.GPUProfileError): gpu.current_game_producer(self.owner)


if __name__ == '__main__':
    unittest.main()
