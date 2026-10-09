"""Execute the new typed Game layer without relaxing any earlier ancestry."""
from __future__ import annotations
import copy
import hashlib
import unittest

import package_client_render_pipeline_native as native
import test_client_renderer_attribution_contract as previous
import test_client_render_pipeline_native as pipeline_tests

contract, guest, index = previous.contract, previous.guest, previous.index
foreign_source_variants = previous.previous.previous.foreign_source_variants
WRAPPERS = ('native_responsiveness', 'startup_bundle_client', 'client_loading',
    'client_startup_followup', 'client_scene_performance', 'client_gameplay_performance',
    'client_renderer_attribution')


def native_manifest(package, record):
    accepted = package['client_renderer_attribution']['manifest']
    manifest = copy.deepcopy(accepted)
    build = copy.deepcopy(native.expected_receipt())
    checks = copy.deepcopy(accepted['windows_qualification'])
    checks.update(build_input=build, pipeline=pipeline_tests.expected_checks())
    manifest.update(role=native.ROLE, repository_commit='a'*40, build_input=build,
        files={'CityOfHeroes.exe': copy.deepcopy(record)},
        base_client_executable=copy.deepcopy(package['files']['CityOfHeroes.exe']),
        windows_qualification=checks)
    return manifest


def append_pipeline(package, raw=b'qualified-render-pipeline-Game'):
    package = copy.deepcopy(package)
    previous_game = package['files']['CityOfHeroes.exe']
    record = dict(previous_game, size=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    manifest = native_manifest(package, record)
    package['client_render_pipeline'] = {
        'manifest': manifest, 'manifest_sha256': contract.canonical_sha(manifest),
        'base_client_renderer_attribution_manifest_sha256': package['client_renderer_attribution']['manifest_sha256'],
        'base_client_executable': copy.deepcopy(previous_game)}
    package['files']['CityOfHeroes.exe'] = record
    return package


def validate_actual_native_ancestry(donor, produced):
    """Hosted checks use the actual immutable .21 donor and current Win32 proof."""
    import build_client_render_pipeline_apk as builder
    case = unittest.TestCase()
    before = copy.deepcopy((donor['_native_client_manifest'], produced))
    accepted = donor['immutable_donor_provenance']['native_responsiveness']['build_inputs']
    case.assertTrue(builder.engine.validate_native_source_ancestry(produced['retained_source_inputs'], accepted))
    wrapped = builder.client_manifest(donor, produced)
    case.assertEqual(contract.client_contract(wrapped), produced['files']['CityOfHeroes.exe'])
    for name in WRAPPERS:
        case.assertEqual(wrapped[name], donor['_native_client_manifest'][name])
    case.assertEqual(wrapped['client_render_pipeline']['base_client_executable'],
        donor['_native_client_manifest']['files']['CityOfHeroes.exe'])
    rejected = []
    for name, inputs in foreign_source_variants(produced['retained_source_inputs']):
        with case.assertRaises(ValueError): builder.engine.validate_native_source_ancestry(inputs, accepted)
        changed = copy.deepcopy(produced)
        changed['retained_source_inputs'] = inputs
        with case.assertRaises(ValueError): builder.client_manifest(donor, changed)
        rejected.append(name)
    case.assertEqual((donor['_native_client_manifest'], produced), before)
    return {'status': 'passed', 'actual_external_donor_and_win32_receipts_verified': True,
        'full_guest_typed_client_wrapper_verified': True, 'older_native_history_unchanged': True,
        'actual_renderer_Game_predecessor_verified': True, 'raw_source_histories_preserved': True,
        'rejected_foreign_variants': rejected}


class RenderPipelineContractTests(unittest.TestCase):
    def setUp(self):
        self.fixture = previous.RendererContractTests(
            'test_upgrade_preserves_generated_cache_private_inputs_and_all_previous_wrappers')
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.donor = self.fixture.derivative()

    def derivative(self):
        return append_pipeline(self.donor)

    def test_typed_layer_extends_exact_renderer_Game_and_preserves_every_previous_wrapper(self):
        expected = self.derivative()
        self.assertEqual(contract.client_contract(expected), expected['files']['CityOfHeroes.exe'])
        for name in WRAPPERS:
            self.assertEqual(expected[name], self.donor[name])
        self.assertNotEqual(expected['files']['CityOfHeroes.exe'], self.donor['files']['CityOfHeroes.exe'])
        self.assertEqual(set(expected['files']), set(self.donor['files']))
        for name in set(expected['files']) - {'CityOfHeroes.exe'}:
            self.assertEqual(expected['files'][name], self.donor['files'][name])

    def test_forged_controls_dependencies_source_parent_and_proof_rejected(self):
        expected = self.derivative()
        for mutation in ('old_base', 'base_hash', 'format_bool', 'format_float', 'build_format_bool',
                'sample_float', 'sample_bool', 'wake_disabled', 'wake_producer', 'wake_source', 'queue_source',
                'cap', 'fps', 'renderer', 'schema', 'imports', 'target', 'parent_recipe',
                'platform', 'proof_header', 'main_scope', 'renderer_scope'):
            changed = copy.deepcopy(expected)
            wrapper = changed['client_render_pipeline']
            manifest = wrapper['manifest']; build = manifest['build_input']
            if mutation == 'old_base': wrapper['base_client_executable'] = changed['client_renderer_attribution']['base_client_executable']
            elif mutation == 'base_hash': wrapper['base_client_renderer_attribution_manifest_sha256'] = 'e'*64
            elif mutation == 'format_bool': manifest['format'] = True
            elif mutation == 'format_float': manifest['format'] = 1.0
            elif mutation == 'build_format_bool': build['format'] = True
            elif mutation == 'sample_float': build['controls']['render_pipeline']['command_sample_interval'] = 16.0
            elif mutation == 'sample_bool': build['controls']['render_pipeline']['aggregate_only'] = 1
            elif mutation == 'wake_disabled': build['worker_wakeup_changed'] = False
            elif mutation == 'wake_producer': build['controls']['worker_wake_repair']['producer_signals_unchanged'] = False
            elif mutation == 'wake_source': build['source_sha256']['libs/UtilitiesLib/src/components/WorkerThread.c'] = 'e'*64
            elif mutation == 'queue_source': build['source_sha256']['Game/src/render/thread/rt_queue.h'] = 'e'*64
            elif mutation == 'cap': build['gameplay_frame_cap_changed'] = True
            elif mutation == 'fps': build['native_fps_display_changed'] = True
            elif mutation == 'renderer': build['renderer_changed'] = True
            elif mutation == 'schema': manifest['schema_sources_sha256'] = {}
            elif mutation == 'imports': manifest['files']['CityOfHeroes.exe']['imports'].append('foreign.dll')
            elif mutation == 'target': build['build_targets'] = ['Game', 'MapServer']
            elif mutation == 'parent_recipe': build['base_client_renderer_attribution_build_input']['controls']['renderer_attribution']['aggregate_only'] = False
            elif mutation == 'platform': manifest['windows_qualification']['platform'] = 'linux'
            elif mutation == 'main_scope': build['controls']['render_pipeline']['main_scope'] = 'all_states'
            elif mutation == 'renderer_scope': build['controls']['render_pipeline']['renderer_scope'] = 'gameplay'
            else: manifest['windows_qualification']['pipeline']['header_sha256'] = 'f'*64
            manifest['windows_qualification']['build_input'] = copy.deepcopy(build)
            wrapper['manifest_sha256'] = contract.canonical_sha(manifest)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                contract.client_contract(changed)

    def test_correctly_rebound_foreign_ancestry_is_rejected(self):
        expected = self.derivative()
        for name, inputs in foreign_source_variants(expected['client_render_pipeline']['manifest']['retained_source_inputs']):
            changed = copy.deepcopy(expected)
            wrapper = changed['client_render_pipeline']
            wrapper['manifest']['retained_source_inputs'] = inputs
            wrapper['manifest_sha256'] = contract.canonical_sha(wrapper['manifest'])
            with self.subTest(mutation=name), self.assertRaises(ValueError):
                contract.client_contract(changed)

    def test_every_native_proof_flag_and_retained_qualification_remains_typed(self):
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
        for name in ('scene', 'frame', 'gameplay', 'renderer'):
            changed = copy.deepcopy(expected)
            wrapper = changed['client_render_pipeline']
            wrapper['manifest']['windows_qualification'][name]['platform'] = 'foreign'
            wrapper['manifest_sha256'] = contract.canonical_sha(wrapper['manifest'])
            with self.subTest(retained=name), self.assertRaises(ValueError):
                contract.client_contract(changed)


if __name__ == '__main__':
    unittest.main()
