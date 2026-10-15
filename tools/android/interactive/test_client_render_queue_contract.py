"""Qualify the queue Game extension while preserving every accepted producer."""
import copy
import hashlib
import unittest

import package_client_render_queue_native as native
import test_client_render_queue_native as queue_tests
import test_client_render_pipeline_contract as previous

contract, guest, index = previous.contract, previous.guest, previous.index
WRAPPERS = (*previous.WRAPPERS, 'client_render_pipeline')
foreign_source_variants = previous.foreign_source_variants


def native_manifest(package, record):
    accepted = package['client_render_pipeline']['manifest']
    manifest = copy.deepcopy(accepted)
    build = copy.deepcopy(native.expected_receipt())
    checks = copy.deepcopy(accepted['windows_qualification'])
    checks.update(build_input=build, queue=queue_tests.expected_checks())
    manifest.update(role=native.ROLE, repository_commit='c' * 40, build_input=build,
        files={'CityOfHeroes.exe': copy.deepcopy(record)},
        base_client_executable=copy.deepcopy(package['files']['CityOfHeroes.exe']),
        windows_qualification=checks)
    return manifest


def append_queue(package, raw=b'qualified-render-queue-Game'):
    package = copy.deepcopy(package)
    predecessor = package['files']['CityOfHeroes.exe']
    record = dict(predecessor, size=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    manifest = native_manifest(package, record)
    package['client_render_queue'] = {
        'manifest': manifest, 'manifest_sha256': contract.canonical_sha(manifest),
        'base_client_render_pipeline_manifest_sha256': package['client_render_pipeline']['manifest_sha256'],
        'base_client_executable': copy.deepcopy(predecessor)}
    package['files']['CityOfHeroes.exe'] = record
    return package


def validate_actual_native_ancestry(donor, produced):
    """Qualify actual donor/current native receipts independently of fixtures."""
    import build_client_render_queue_apk as builder
    case = unittest.TestCase()
    before = copy.deepcopy((donor['_native_client_manifest'], produced))
    accepted = donor['immutable_donor_provenance']['native_responsiveness']['build_inputs']
    case.assertTrue(builder.engine.validate_native_source_ancestry(produced['retained_source_inputs'], accepted))
    wrapped = builder.client_manifest(donor, produced)
    case.assertEqual(contract.client_contract(wrapped), produced['files']['CityOfHeroes.exe'])
    for name in WRAPPERS:
        case.assertEqual(wrapped[name], donor['_native_client_manifest'][name])
    case.assertEqual(wrapped['client_render_queue']['base_client_executable'],
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
        'actual_pipeline_Game_predecessor_verified': True, 'raw_source_histories_preserved': True,
        'rejected_foreign_variants': rejected}


class RenderQueueContractTests(unittest.TestCase):
    def setUp(self):
        fixture = previous.RenderPipelineContractTests(
            'test_typed_layer_extends_exact_renderer_Game_and_preserves_every_previous_wrapper')
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        self.donor = fixture.derivative()

    def derivative(self):
        return append_queue(self.donor)

    def test_typed_layer_extends_exact_pipeline_Game_and_preserves_all_eight_previous_wrappers(self):
        expected = self.derivative()
        self.assertEqual(contract.client_contract(expected), expected['files']['CityOfHeroes.exe'])
        for name in WRAPPERS: self.assertEqual(expected[name], self.donor[name])
        self.assertNotEqual(expected['files']['CityOfHeroes.exe'], self.donor['files']['CityOfHeroes.exe'])
        for name in set(expected['files']) - {'CityOfHeroes.exe'}:
            self.assertEqual(expected['files'][name], self.donor['files'][name])

    def test_native_flags_controls_parent_and_Dll_closure_fail_closed(self):
        expected = self.derivative()
        for mutation in ('base_hash', 'old_base', 'format_bool', 'format_float', 'build_format_bool',
                'fidelity', 'cap', 'schema', 'imports', 'target', 'parent_recipe', 'platform', 'proof_header'):
            changed = copy.deepcopy(expected)
            wrapper = changed['client_render_queue']
            manifest, build = wrapper['manifest'], wrapper['manifest']['build_input']
            if mutation == 'base_hash': wrapper['base_client_render_pipeline_manifest_sha256'] = 'e' * 64
            elif mutation == 'old_base': wrapper['base_client_executable'] = changed['client_render_pipeline']['base_client_executable']
            elif mutation == 'format_bool': manifest['format'] = True
            elif mutation == 'format_float': manifest['format'] = 1.0
            elif mutation == 'build_format_bool': build['format'] = True
            elif mutation == 'fidelity': build['graphics_profile_changes'] = True
            elif mutation == 'cap': build['gameplay_frame_cap_changed'] = True
            elif mutation == 'schema': manifest['schema_sources_sha256'] = {}
            elif mutation == 'imports': manifest['files']['CityOfHeroes.exe']['imports'].append('foreign.dll')
            elif mutation == 'target': build['build_targets'] = ['Game', 'MapServer']
            elif mutation == 'parent_recipe': build['base_client_render_pipeline_build_input']['controls']['render_pipeline']['command_sample_interval'] = 32
            elif mutation == 'platform': manifest['windows_qualification']['platform'] = 'linux'
            else: manifest['windows_qualification']['queue']['header_sha256'] = 'f' * 64
            manifest['windows_qualification']['build_input'] = copy.deepcopy(build)
            wrapper['manifest_sha256'] = contract.canonical_sha(manifest)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): contract.client_contract(changed)

    def test_all_new_controls_require_exact_types_and_values(self):
        expected = self.derivative()
        for group, values in expected['client_render_queue']['manifest']['build_input']['controls'].items():
            for field, value in values.items():
                wrong_values = ((1, 1.0, False, None) if value is True else
                    (0, 0.0, True, None) if value is False else
                    (float(value), True, None) if type(value) is int else ('foreign', None))
                for wrong in wrong_values:
                    changed = copy.deepcopy(expected)
                    wrapper = changed['client_render_queue']
                    build = wrapper['manifest']['build_input']
                    build['controls'][group][field] = wrong
                    wrapper['manifest']['windows_qualification']['build_input'] = copy.deepcopy(build)
                    wrapper['manifest_sha256'] = contract.canonical_sha(wrapper['manifest'])
                    with self.subTest(group=group, field=field, value=wrong), self.assertRaises(ValueError):
                        contract.client_contract(changed)

    def test_raw_foreign_source_history_rejected_even_after_rebinding_canonical_hash(self):
        expected = self.derivative()
        for name, inputs in foreign_source_variants(expected['client_render_queue']['manifest']['retained_source_inputs']):
            changed = copy.deepcopy(expected)
            wrapper = changed['client_render_queue']
            wrapper['manifest']['retained_source_inputs'] = inputs
            wrapper['manifest_sha256'] = contract.canonical_sha(wrapper['manifest'])
            with self.subTest(name=name), self.assertRaises(ValueError): contract.client_contract(changed)

    def test_each_real_Win32_proof_flag_requires_true_without_physical_gain_claims(self):
        expected = self.derivative()
        proof = expected['client_render_queue']['manifest']['windows_qualification']['queue']
        for field, value in proof.items():
            if value is not True and value is not False: continue
            for wrong in ((False, 1, 1.0, None) if value is True else (True, 0, 0.0, None)):
                changed = copy.deepcopy(expected)
                wrapper = changed['client_render_queue']
                wrapper['manifest']['windows_qualification']['queue'][field] = wrong
                wrapper['manifest_sha256'] = contract.canonical_sha(wrapper['manifest'])
                with self.subTest(field=field, value=wrong), self.assertRaises(ValueError): contract.client_contract(changed)

    def test_worker_fixture_requires_actual_Win32_source_and_typed_counts_and_lifecycle_proof(self):
        expected = self.derivative()
        proof = expected['client_render_queue']['manifest']['windows_qualification']['queue']['worker_queue_fixture']
        for field, value in proof.items():
            wrong_values = ((False, 1, 1.0, None) if value is True else
                (True, 0, 0.0, None) if value is False else
                (float(value), True, None) if type(value) is int else
                ('f' * 64, None) if field in ('source_sha256', 'header_sha256') else ('foreign', None))
            for wrong in wrong_values:
                changed = copy.deepcopy(expected)
                wrapper = changed['client_render_queue']
                wrapper['manifest']['windows_qualification']['queue']['worker_queue_fixture'][field] = wrong
                wrapper['manifest_sha256'] = contract.canonical_sha(wrapper['manifest'])
                with self.subTest(field=field, value=wrong), self.assertRaises(ValueError): contract.client_contract(changed)


if __name__ == '__main__': unittest.main()
