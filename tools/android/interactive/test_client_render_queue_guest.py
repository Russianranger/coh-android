"""Exercise current queue Game launch gates, retained samplers and exact caches."""
import copy
import functools
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import test_client_render_queue_contract as contracts
import test_client_render_pipeline_guest as previous

contract, guest, index, gpu = previous.contract, previous.guest, previous.index, previous.gpu
reopen = previous.reopen


class RenderQueueCacheTests(unittest.TestCase):
    def setUp(self):
        fixture = previous.RenderPipelineContractTests(
            'test_upgrade_preserves_generated_cache_private_inputs_and_all_previous_wrappers')
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        self.fixture = fixture
        self.donor = fixture.derivative()
        self.runtime, self.donor_report = fixture.prepare()
        self.donor_game = copy.deepcopy(self.donor['files']['CityOfHeroes.exe'])

    def derivative(self):
        contents, package = self.fixture.read_archive()
        raw = previous.previous.previous.previous.previous.old.fixtures.pe_bytes() + b'sparse-coalesced-render-queue-Game'
        produced = contracts.append_queue(package, raw)
        contents['CityOfHeroes.exe'] = raw
        self.fixture.write_archive(contents, produced)
        return produced

    def test_only_Game_upgrades_and_all_cached_private_inputs_and_wrappers_survive(self):
        before = self.fixture.preserved()
        produced = self.derivative()
        with mock.patch.object(guest.os, 'scandir', side_effect=AssertionError('Input trees recreated')):
            runtime, report = self.fixture.prepare()
        self.assertEqual(runtime, self.runtime)
        self.assertEqual(before, self.fixture.preserved())
        self.assertTrue(report['native_executable_upgraded'])
        self.assertTrue(report['generated_cache_bytes_preserved'])
        proof = report['native_texture_index_migration']
        self.assertEqual(proof['policy'], 'verified_client_render_queue_layer_v1')
        self.assertEqual(proof['previous_executable_sha256'], self.donor_game['sha256'])
        self.assertEqual(proof['layer_manifest_sha256'], produced['client_render_queue']['manifest_sha256'])
        for name in contracts.WRAPPERS: self.assertEqual(produced[name], self.donor[name])
        self.assertTrue(self.fixture.prepare()[1]['reused'])

    def test_exact_header_index_rebind_preserves_generated_pack_bytes(self):
        index.prepare(self.runtime, self.fixture.identity, self.donor_game['sha256'],
            previous.previous.previous.textures.Context({'client_worktree': self.donor_report}))
        before = (self.runtime / index.PACK).read_bytes()
        produced = self.derivative()
        _, report = self.fixture.prepare()
        with mock.patch.object(index, 'make_pack', side_effect=AssertionError('Prepared headers rebuilt')):
            result, _ = self.fixture.upgraded_index(report, produced['files']['CityOfHeroes.exe'])
        self.assertTrue(result['reused'])
        self.assertTrue(result['native_layer_identity_migrated'])
        self.assertEqual(before[64:], (self.runtime / index.PACK).read_bytes()[64:])


@functools.lru_cache(maxsize=1)
def typed_queue_package():
    # Selection tests use the real typed history and the independently pinned
    # production predecessor identity. Cache tests separately qualify bytes.
    package = copy.deepcopy(previous.typed_gpu_package())
    parent = package['client_render_pipeline']
    parent['manifest']['repository_commit'] = gpu.PIPELINE_SOURCE_COMMIT
    parent['manifest']['files']['CityOfHeroes.exe'].update(sha256=gpu.PIPELINE_GAME_SHA256, size=9494016)
    parent['manifest_sha256'] = contract.canonical_sha(parent['manifest'])
    package['files']['CityOfHeroes.exe'] = copy.deepcopy(parent['manifest']['files']['CityOfHeroes.exe'])
    produced = contracts.append_queue(package)
    contract.client_contract(produced)
    return produced


def install_queue(owner):
    package = copy.deepcopy(typed_queue_package())
    wrapper = package['client_render_queue']
    parent = package['client_render_pipeline']
    owner.client_render_queue = True
    owner.client_render_queue_package = package
    owner.client_render_pipeline_package = package
    owner.client_executable_sha256 = package['files']['CityOfHeroes.exe']['sha256']
    owner.ctx.report['client_render_pipeline'].update(
        repository_commit=gpu.PIPELINE_SOURCE_COMMIT, manifest_sha256=parent['manifest_sha256'],
        client_executable_sha256=gpu.PIPELINE_GAME_SHA256,
        producer_scope='retained_historical_render_pipeline_Game')
    owner.ctx.report['client_render_queue'] = {
        'format': 1, 'verified': True, 'repository_commit': wrapper['manifest']['repository_commit'],
        'manifest_sha256': wrapper['manifest_sha256'],
        'base_client_render_pipeline_manifest_sha256': parent['manifest_sha256'],
        'base_client_executable_sha256': gpu.PIPELINE_GAME_SHA256,
        'client_executable_sha256': owner.client_executable_sha256,
        'source_commit': guest.SOURCE, 'data_commit': guest.DATA,
        'native_source_sha256': contract.canonical_sha(wrapper['manifest']['retained_source_inputs']),
        'data_source_sha256': owner.ctx.report['import_identity']['contract_sha256'],
        'replacement_scope': 'CityOfHeroes.exe_only', 'source_freshness_preserved': True,
        'prepared_cache_schema_changed': False, 'renderer_changed': False,
        'graphics_fidelity_preserved': True, 'gameplay_frame_cap_changed': False,
        'bounded_render_queue_diagnostics': True, 'render_worker_wake_coalesced': True,
        'physical_fps_improvement_validated': False}
    return package


class RenderQueueLaunchTests(unittest.TestCase):
    def setUp(self):
        previous.RenderPipelineLaunchTests.setUp(self)
        self.package = install_queue(self.diagnostic)
        for name in ('client_startup_followup', 'client_scene_performance', 'client_gameplay_performance'):
            self.diagnostic.ctx.report[name]['client_executable_sha256'] = self.diagnostic.client_executable_sha256
        self.diagnostic.wine_env['COH_CLIENT_RENDER_QUEUE'] = 'untrusted'
        self.original_env = dict(self.diagnostic.wine_env)

    def test_creation_and_saved_character_retries_bind_new_Game_and_preserve_RP0_policy(self):
        creation = self.diagnostic
        for cls in (type(creation), reopen.CharacterReopenDiagnostic, reopen.StartupOnlyCharacterReopenDiagnostic):
            d = cls.__new__(cls)
            d.__dict__.update(creation.__dict__)
            before = copy.deepcopy({name: d.ctx.report[name] for name in ('client_renderer_attribution', 'client_render_pipeline')})
            for label in ('actual-coh-client', 'actual-coh-client-retry'):
                d.launch_client_attempt(label=label)
                env = d.ctx.start.call_args.kwargs['env']
                self.assertEqual(env['COH_CLIENT_RENDER_QUEUE'], '1')
                self.assertEqual(env['COH_CLIENT_RENDER_PIPELINE'], '1' if cls is type(creation) else '0')
                self.assertEqual(env['COH_CLIENT_RENDERER_ATTRIBUTION'], '1')
                self.assertEqual(env['COH_CLIENT_FRAME_TIMING'], '1')
                self.assertEqual(env['COH_CLIENT_GAMEPLAY_FPS'], '30')
                self.assertEqual(d.wine_env, self.original_env)
                self.assertEqual({name: d.ctx.report[name] for name in before}, before)
                receipt = d.ctx.report['client_render_queue_environment']
                self.assertEqual(receipt['launch_label'], label)
                self.assertEqual(receipt['client_executable_sha256'], d.client_executable_sha256)
                self.assertEqual(receipt['frame_sample_interval'], 32)
                self.assertFalse(receipt['physical_fps_improvement_validated'])
                if cls is not type(creation):
                    self.assertTrue(d.ctx.report['client_render_pipeline_environment']['performance_isolation'])
        self.assertEqual(before['client_render_pipeline']['repository_commit'], gpu.PIPELINE_SOURCE_COMMIT)
        self.assertEqual(before['client_render_pipeline']['client_executable_sha256'], gpu.PIPELINE_GAME_SHA256)
        self.assertNotEqual(gpu.PIPELINE_GAME_SHA256, creation.client_executable_sha256)

    def test_untyped_or_disabled_queue_clears_inherited_control_without_mutating_shared_environment(self):
        d = self.diagnostic
        for value in (False, None, 1, '1', {}):
            d.client_render_queue = value
            attempt = dict(d.wine_env)
            guest.apply_client_render_queue_environment(d, attempt, 'owned-Game')
            self.assertNotIn('COH_CLIENT_RENDER_QUEUE', attempt)
            self.assertEqual(d.wine_env, self.original_env)
            self.assertFalse(d.ctx.report['client_render_queue_environment']['enabled'])

    def test_forged_queue_producer_fails_before_owned_initial_or_retry_launch(self):
        d = self.diagnostic
        accepted = copy.deepcopy(d.ctx.report['client_render_queue'])
        for field, wrong in (('verified', 1), ('format', True), ('repository_commit', 'f' * 40),
                ('manifest_sha256', 'e' * 64), ('base_client_executable_sha256', 'e' * 64),
                ('client_executable_sha256', gpu.PIPELINE_GAME_SHA256), ('native_source_sha256', 'e' * 64),
                ('data_source_sha256', 'e' * 64), ('graphics_fidelity_preserved', 1),
                ('renderer_changed', True), ('render_worker_wake_coalesced', False),
                ('physical_fps_improvement_validated', True)):
            d.ctx.report['client_render_queue'] = dict(accepted, **{field: wrong})
            for label in ('actual-coh-client', 'actual-coh-client-retry'):
                with self.subTest(field=field, label=label), self.assertRaises(gpu.GPUProfileError):
                    d.launch_client_attempt(label=label)
                d.ctx.start.assert_not_called()
                self.assertEqual(d.wine_env, self.original_env)

    def test_pipeline_and_queue_cannot_claim_different_current_packages(self):
        self.diagnostic.client_render_pipeline_package = copy.deepcopy(previous.typed_gpu_package())
        with self.assertRaises(gpu.GPUProfileError):
            self.diagnostic.launch_client_attempt()
        self.diagnostic.ctx.start.assert_not_called()


class RenderQueueGPUSelectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.owner, self.baseline = previous.gpu_tests.make_owner(Path(temporary.name))
        previous.install_pipeline(self.owner)
        self.package = install_queue(self.owner)

    def test_current_Game_receipt_is_distinct_from_retained_Game_and_GPU_producers(self):
        before = dict(self.baseline)
        with (mock.patch.object(gpu, 'platform_is_arm64', return_value=True),
                mock.patch.object(previous.gpu_tests.base, 'arm64_elf'), mock.patch.object(previous.gpu_tests.base, 'verify_pe32'),
                mock.patch.object(gpu, 'run_probe', return_value=previous.gpu_tests.marker(gpu.NATIVE_PREFIX, previous.gpu_tests.native_result())),
                mock.patch.object(gpu, 'private_wgl_probe', return_value=previous.gpu_tests.wgl_result())):
            selected = gpu.apply_profile(self.owner, self.baseline, 'actual-coh-client')
        receipt = self.owner.ctx.report['client_gpu_profile']
        self.assertEqual(receipt['selected'], 'turnip')
        self.assertEqual(selected['MESA_LOADER_DRIVER_OVERRIDE'], 'zink')
        self.assertEqual(receipt['game_producer']['client_executable_sha256'], self.owner.client_executable_sha256)
        self.assertEqual(receipt['game_producer']['retained_pipeline_executable_sha256'], gpu.PIPELINE_GAME_SHA256)
        self.assertEqual(receipt['game_producer']['retained_pipeline_repository_commit'], gpu.PIPELINE_SOURCE_COMMIT)
        self.assertEqual(receipt['game_producer']['retained_renderer_executable_sha256'], gpu.GAME_SHA256)
        self.assertNotEqual(receipt['game_producer']['repository_commit'], receipt['gpu_payload_producer']['repository_commit'])
        self.assertFalse(receipt['physical_fps_improvement_validated'])
        self.assertEqual(self.baseline, before)

    def test_claimed_queue_without_typed_extension_stays_Software_before_payload(self):
        del self.owner.client_render_queue_package
        with mock.patch.object(gpu, 'verify_archive', side_effect=AssertionError('Unqualified Game reached payload')):
            self.assertEqual(gpu.apply_profile(self.owner, self.baseline, 'actual-coh-client'), self.baseline)
        self.assertEqual(self.owner.ctx.report['client_gpu_profile']['state'], 'software_fallback')
        self.assertTrue(self.owner.ctx.report['client_gpu_profile']['probe_cleanup_safe'])

    def test_canonical_rebinding_does_not_authorize_foreign_frozen_pipeline_source(self):
        parent = self.package['client_render_pipeline']
        parent['manifest']['repository_commit'] = 'f' * 40
        parent['manifest_sha256'] = contract.canonical_sha(parent['manifest'])
        queue = self.package['client_render_queue']
        queue['base_client_render_pipeline_manifest_sha256'] = parent['manifest_sha256']
        self.owner.ctx.report['client_render_pipeline'].update(
            repository_commit='f' * 40, manifest_sha256=parent['manifest_sha256'])
        self.owner.ctx.report['client_render_queue']['base_client_render_pipeline_manifest_sha256'] = parent['manifest_sha256']
        # Structurally sound fabricated producer history still cannot replace
        # the independently fixed .22 source identity used by actual selection.
        contract.client_contract(self.package)
        with self.assertRaises(gpu.GPUProfileError): gpu.current_game_producer(self.owner)

    def test_Software_fallback_does_not_modify_accepted_environment_or_cleanup_bounds(self):
        with mock.patch.object(gpu, 'platform_is_arm64', return_value=False):
            returned = gpu.apply_profile(self.owner, self.baseline, 'actual-coh-client')
        self.assertEqual(returned, self.baseline)
        self.assertIsNot(returned, self.baseline)
        receipt = self.owner.ctx.report['client_gpu_profile']
        self.assertEqual(receipt['state'], 'software_fallback')
        self.assertTrue(receipt['probe_cleanup_safe'])
        self.assertFalse(receipt['automatic_mid_game_fallback'])
        self.owner.ctx.start.assert_not_called()


if __name__ == '__main__': unittest.main()
