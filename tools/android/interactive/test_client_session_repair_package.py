#!/usr/bin/env python3
"""Adversarial boundaries for the host-only .23 session repair publication."""
import copy
import hashlib
import unittest
from unittest import mock

import build_client_session_repair_apk as builder
import build_client_render_pipeline_apk as history


def payloads():
    result = {'assets/runtime/member-%02d.zip'%i: {
        'bytes': i+1, 'sha256': hashlib.sha256(str(i).encode()).hexdigest()}
        for i in range(77-len(builder.REPLACED_PAYLOADS))}
    result.update({name: {'bytes': 100, 'sha256': 'a'*64}
        for name in builder.REPLACED_PAYLOADS})
    return result


def release():
    prefix = 'https://github.com/'+builder.REPOSITORY+'/releases/download/'+builder.RELEASE_TAG+'/'
    return {'id': 10, 'tag_name': builder.RELEASE_TAG, 'draft': False,
        'prerelease': True, 'published_at': '2026-10-09T00:00:00Z',
        'assets': [{'name': name, 'state': 'uploaded',
            'size': 97 if name.endswith('.sha256') else 100,
            'digest': 'sha256:'+'b'*64, 'browser_download_url': prefix+name}
            for name in (builder.APK_NAME, builder.APK_NAME+'.sha256', builder.NOTES_NAME)]}


class SessionRepairPublication(unittest.TestCase):
    def test_private_derivative_does_not_change_historical_builder_globals(self):
        self.assertIsNot(builder._base, history)
        self.assertEqual((history.VERSION_NAME, history.VERSION_CODE), ('0.13.22', 37))
        self.assertEqual(len(history.HELPERS), 4)
        self.assertEqual(len(history.REPLACED_PAYLOADS), 7)
        self.assertEqual(history.REPORT_NAME, 'client-render-pipeline-apk-build-report.json')
        self.assertEqual((builder.VERSION_NAME, builder.VERSION_CODE), ('0.13.23', 38))
        candidate = builder.builder(repaired=True)
        self.assertEqual((candidate.VERSION_NAME, candidate.VERSION_CODE), ('0.13.23', 38))
        self.assertEqual(history.builder(repaired=True).VERSION_NAME, '0.13.22')

    def test_exact_ten_payload_scope_rejects_removed_added_or_changed_retained_bytes(self):
        donor = {'payloads': payloads()}
        candidate = copy.deepcopy(donor['payloads'])
        for name in builder.REPLACED_PAYLOADS:
            candidate[name] = {'bytes': 101, 'sha256': 'b'*64}
        builder.payload_boundaries(candidate, donor)
        self.assertEqual(len(builder.REPLACED_PAYLOADS), 10)
        self.assertEqual(builder.RETAINED_PAYLOAD_COUNT, 67)
        self.assertNotIn('assets/runtime/hardware-renderer.zip', builder.REPLACED_PAYLOADS)
        retained = next(name for name in candidate if name not in builder.REPLACED_PAYLOADS)
        for variant in ('removed', 'added', 'changed', 'unchanged_helper'):
            wrong = copy.deepcopy(candidate)
            if variant == 'removed': wrong.pop(retained)
            elif variant == 'added': wrong['foreign'] = {'bytes': 1, 'sha256': 'c'*64}
            elif variant == 'changed': wrong[retained] = {'bytes': 1, 'sha256': 'c'*64}
            else:
                name = 'assets/runtime/character_session_budget.py'
                wrong[name] = donor['payloads'][name]
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                builder.payload_boundaries(wrong, donor)

    def test_budget_and_reopen_isolation_provenance_retains_successful_gpu_history(self):
        updates = {name: {'bytes': 10, 'sha256': 'd'*64}
            for name in builder.HELPERS|{'client-runtime.zip'}}
        hardware = {'bytes': 500, 'sha256': 'e'*64}
        files = dict(updates, **{'hardware-renderer.zip': hardware,
            'client-manifest.json': {'bytes': 1, 'sha256': 'f'*64}})
        donor = {'_client_verification': {'files': copy.deepcopy(files)},
            'runtime_manifest': {'files': copy.deepcopy(files),
                'client_gpu_profile': {'source': 'accepted'},
                'client_gpu_probe_repair': {'source': 'accepted'},
                'client_renderer_attribution': {'source': 'accepted'}}}
        original = copy.deepcopy(donor)
        client, runtime = builder.verification_manifests(donor, updates, 'a'*40,
            {'role': 'bounded_client_render_pipeline'})
        self.assertEqual(donor, original)
        self.assertEqual(client['files']['hardware-renderer.zip'], hardware)
        for name in ('client_gpu_profile', 'client_gpu_probe_repair', 'client_renderer_attribution'):
            self.assertEqual(runtime[name], donor['runtime_manifest'][name])
        self.assertFalse(runtime['client_render_pipeline']['native_recompiled'])
        repair = runtime['client_session_repair']
        self.assertEqual(repair['changed_guest_helpers'], sorted(builder.NEW_HELPERS))
        self.assertEqual(repair['render_pipeline_isolation_scope'], 'character_reopen_only')
        self.assertTrue(repair['direct_interactive_render_pipeline_instrumentation_retained'])
        self.assertFalse(repair['native_Game_changed_from_public_0_13_22'])
        self.assertFalse(repair['render_pipeline_instrumentation_enabled'])
        self.assertFalse(repair['physical_fps_gain_validated'])
        self.assertEqual(repair['native_Game_sha256'], builder.NATIVE_GAME['sha256'])
        self.assertTrue(repair['legacy_frame_and_renderer_attribution_retained'])
        self.assertTrue(repair['worker_wake_repair_retained'])
        with self.assertRaises(ValueError):
            builder.verification_manifests(donor, dict(updates, foreign={'bytes': 1, 'sha256': 'a'*64}), 'a'*40, {})

    def test_three_helper_exception_cannot_mutate_original_native_source_recipe(self):
        expected = history.REVIEWED_DONOR_SOURCE_CHANGES | {
            'android/guest/'+name for name in builder.NEW_HELPERS} | {
            'tools/android/interactive/test_session_budget_guest.py'}
        self.assertEqual(builder.REVIEWED_DONOR_SOURCE_CHANGES, expected)
        self.assertEqual(builder.RETAINED_NATIVE_SOURCE_FILES, history.RETAINED_NATIVE_SOURCE_FILES)
        self.assertTrue(set('android/guest/'+name for name in builder.NEW_HELPERS).isdisjoint(
            builder.RETAINED_NATIVE_SOURCE_FILES))
        for name, pin in builder.RETAINED_NATIVE_SOURCE_FILES.items():
            with self.subTest(name=name):
                self.assertEqual(builder.builder().file_pin(builder.ROOT/name), pin)

    def test_original_native_producer_and_truthful_no_rebuild_flags_retained(self):
        self.assertEqual(builder.native_build_provenance(), history.native_build_provenance())
        provenance = builder.native_build_provenance()
        self.assertEqual(provenance['repository_commit'], '5af0e27ccf6fbb53d5b3ff5c2c2f3bf5a1d58396')
        self.assertEqual(provenance['run_id'], 37924638566)
        self.assertFalse(provenance['compiled_in_current_publication_run'])
        for name in ('native_client_recompiled', 'java_or_dex_recompiled',
                'native_client_compiled_in_current_publication_run',
                'native_dbserver_recompiled', 'native_mapserver_recompiled',
                'mesa_driver_compiled_in_current_run', 'native_vulkan_probe_compiled_in_current_run',
                'wgl_probe_compiled_in_current_run', 'physical_fps_gain_validated'):
            self.assertIn(name, builder.FALSE_FLAGS)
        self.assertNotIn('native_client_recompiled', builder.TRUE_FLAGS)
        self.assertIn('accepted_Game_bytes_retained', builder.TRUE_FLAGS)

    def test_all_105_retained_suites_and_real_postgresql_guards_are_mandatory(self):
        import qualify_client_session_repair as qualification
        import qualify_client_render_pipeline as previous
        qualification.validate_suite_inventory()
        self.assertEqual(qualification.TEST_MODULES[:105], previous.TEST_MODULES)
        self.assertEqual(len(qualification.TEST_MODULES), 107)
        self.assertIn('test_startup_bundle_save', qualification.TEST_MODULES)
        self.assertIn('test_levelup_ui_repair_dbserver', qualification.TEST_MODULES)
        self.assertIn('test_character_reopen_guest', qualification.CHECK_SUITES[builder.CHECKS[0]])

    def test_partial_existing_release_is_not_silently_skipped_or_replaced(self):
        builder.validate_existing_release(release())
        for variant in ('draft', 'missing', 'duplicate', 'foreign_url', 'missing_digest', 'unfinished'):
            value = release()
            if variant == 'draft': value['draft'] = True
            elif variant == 'missing': value['assets'].pop()
            elif variant == 'duplicate': value['assets'][1] = copy.deepcopy(value['assets'][0])
            elif variant == 'foreign_url': value['assets'][0]['browser_download_url'] = 'https://example.org/foreign.apk'
            elif variant == 'missing_digest': value['assets'][0]['digest'] = None
            else: value['assets'][0]['state'] = 'new'
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                builder.validate_existing_release(value)

    def test_session_contract_rejects_bool_int_collision_and_unreviewed_extra_keys(self):
        exact = {'client_session_repair': builder.session_repair_contract()}
        with mock.patch.object(builder, '_original_validate_qualification', return_value=exact):
            self.assertEqual(builder.validate_qualification(exact, 'a'*40), exact)
            for field, value in (('format', True), ('format', 1.0),
                    ('legacy_frame_and_renderer_attribution_retained', 1),
                    ('render_pipeline_instrumentation_enabled', 0), ('foreign', True)):
                wrong = copy.deepcopy(exact)
                wrong['client_session_repair'][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    builder.validate_qualification(wrong, 'a'*40)

    def test_workflow_has_one_host_owner_no_native_rebuild_and_actual_public_byte_audit(self):
        import yaml
        text = (builder.ROOT/builder.WORKFLOW).read_text()
        workflow = yaml.safe_load(text)
        self.assertEqual(set(workflow['jobs']), {'changes', 'client', 'qualify', 'apk', 'public-audit'})
        self.assertFalse(workflow['concurrency']['cancel-in-progress'])
        for job in workflow['jobs'].values():
            self.assertEqual(job['runs-on'], 'ubuntu-24.04')
            for step in job['steps']:
                if step.get('uses', '').startswith('actions/checkout@'):
                    self.assertEqual(step['with']['fetch-depth'], 2)
        self.assertTrue(any('download-retained-native' in step.get('run', '')
            for step in workflow['jobs']['client']['steps']))
        for forbidden in ('cmake --build', 'vcvars32.bat', '--target Game',
                'gpu-runtime/build.py', 'package_client_gpu_repair.py'):
            self.assertNotIn(forbidden, text)
        self.assertIn('postgres:16', text)
        self.assertIn('COH_REQUIRE_STARTUP_BUNDLE_PG', text)
        self.assertIn('COH_REQUIRE_LEVELUP_UI_REPAIR_PG', text)
        signing = [step for step in workflow['jobs']['apk']['steps']
            if step.get('with', {}).get('name') == 'coh-client-interactive-signing']
        self.assertEqual(len(signing), 1)
        self.assertEqual(signing[0]['with']['run-id'], 36731428735)
        public_steps = workflow['jobs']['public-audit']['steps']
        self.assertTrue(any('download-public' in step.get('run', '') for step in public_steps))
        self.assertTrue(any(' audit' in step.get('run', '') for step in public_steps))


if __name__ == '__main__': unittest.main()
