#!/usr/bin/env python3
"""Adversarial publication boundaries for the Game-only .22 continuation."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import build_client_render_pipeline_apk as builder


def payloads():
    result = {'assets/runtime/member-%02d.zip'%i: {'bytes': i+1, 'sha256': hashlib.sha256(str(i).encode()).hexdigest()} for i in range(77-len(builder.REPLACED_PAYLOADS))}
    result.update({name: {'bytes': 100, 'sha256': 'a'*64} for name in builder.REPLACED_PAYLOADS})
    return result


def release():
    base = 'https://github.com/'+builder.REPOSITORY+'/releases/download/'+builder.RELEASE_TAG+'/'
    return {'id': 10, 'tag_name': builder.RELEASE_TAG, 'draft': False, 'prerelease': True, 'published_at': '2026-10-09T00:00:00Z',
        'assets': [{'name': name, 'state': 'uploaded', 'size': 97 if name.endswith('.sha256') else 100, 'digest': 'sha256:'+'b'*64, 'browser_download_url': base+name}
            for name in (builder.APK_NAME, builder.APK_NAME+'.sha256', builder.NOTES_NAME)]}


class RenderPipelinePublication(unittest.TestCase):
    def test_exact_seven_payloads_and_seventy_retained_bytes(self):
        donor = {'payloads': payloads()}; candidate = copy.deepcopy(donor['payloads'])
        for name in builder.REPLACED_PAYLOADS: candidate[name] = {'bytes': 101, 'sha256': 'b'*64}
        builder.payload_boundaries(candidate, donor)
        self.assertEqual(len(builder.REPLACED_PAYLOADS), 7)
        self.assertNotIn('assets/runtime/hardware-renderer.zip', builder.REPLACED_PAYLOADS)
        for name in (next(name for name in candidate if name not in builder.REPLACED_PAYLOADS), 'foreign'):
            wrong = copy.deepcopy(candidate); wrong[name] = {'bytes': 1, 'sha256': 'c'*64}
            with self.subTest(name=name), self.assertRaises(ValueError): builder.payload_boundaries(wrong, donor)
        for name in builder.REPLACED_PAYLOADS:
            wrong = copy.deepcopy(candidate); wrong[name] = donor['payloads'][name]
            with self.subTest(name=name), self.assertRaises(ValueError): builder.payload_boundaries(wrong, donor)

    def test_successful_gpu_and_historical_renderer_metadata_retained(self):
        updates = {name: {'bytes': 10, 'sha256': 'd'*64} for name in builder.HELPERS|{'client-runtime.zip'}}
        hardware = {'bytes': 500, 'sha256': 'e'*64}
        files = dict(updates, **{'hardware-renderer.zip': hardware, 'client-manifest.json': {'bytes': 1, 'sha256': 'f'*64}})
        donor = {'_client_verification': {'files': copy.deepcopy(files)}, 'runtime_manifest': {'files': copy.deepcopy(files),
            'client_gpu_profile': {'source': 'accepted'}, 'client_gpu_probe_repair': {'source': 'accepted'}, 'client_renderer_attribution': {'source': 'accepted'}}}
        original = copy.deepcopy(donor)
        client, runtime = builder.verification_manifests(donor, updates, 'a'*40, {'role': 'bounded_client_render_pipeline'})
        self.assertEqual(donor, original)
        self.assertEqual(client['files']['hardware-renderer.zip'], hardware)
        for name in ('client_gpu_profile', 'client_gpu_probe_repair', 'client_renderer_attribution'):
            self.assertEqual(runtime[name], donor['runtime_manifest'][name])
        self.assertFalse(runtime['client_render_pipeline']['physical_performance_validated'])
        self.assertTrue(runtime['client_render_pipeline']['successful_gpu_driver_and_both_probes_retained'])
        with self.assertRaises(ValueError): builder.verification_manifests(donor, dict(updates, foreign={'bytes': 1, 'sha256': 'a'*64}), 'a'*40, {})

    def test_original_artifact_zip_external_pin_precedes_report_trust(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/builder.DONOR_EVIDENCE_ARCHIVE
            with zipfile.ZipFile(path, 'w') as archive:
                for name in sorted(builder.DONOR_EVIDENCE_NAMES): archive.writestr(name, json.dumps({'foreign': True}))
            with self.assertRaises(ValueError): builder.donor_evidence_members(path)
            with mock.patch.object(builder, 'DONOR_EVIDENCE', builder.pin(path.read_bytes())):
                result = builder.donor_evidence_members(path)
                self.assertEqual(set(result), builder.DONOR_EVIDENCE_NAMES)
                with zipfile.ZipFile(path, 'a') as archive: archive.writestr('../foreign.json', '{}')
                with self.assertRaises(ValueError): builder.donor_evidence_members(path)

    def test_authenticated_zip_rejects_duplicate_and_foreign_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            for variant in ('foreign', 'duplicate', 'empty'):
                path = Path(temporary)/(variant+'.zip')
                with zipfile.ZipFile(path, 'w') as archive:
                    for name in sorted(builder.DONOR_EVIDENCE_NAMES): archive.writestr(name, 'proof' if variant != 'empty' else '')
                    if variant == 'foreign': archive.writestr('other.txt', 'foreign')
                    if variant == 'duplicate':
                        import warnings
                        with warnings.catch_warnings():
                            warnings.simplefilter('ignore', UserWarning); archive.writestr(builder.DONOR_REPORT_NAME, 'duplicate')
                with self.subTest(variant=variant), mock.patch.object(builder, 'DONOR_EVIDENCE', builder.pin(path.read_bytes())), self.assertRaises(ValueError):
                    builder.donor_evidence_members(path)

    def test_skip_only_complete_public_release(self):
        builder.validate_existing_release(release())
        for variant in ('draft', 'missing', 'duplicate', 'url', 'digest', 'unfinished'):
            value = release()
            if variant == 'draft': value['draft'] = True
            if variant == 'missing': value['assets'].pop()
            if variant == 'duplicate': value['assets'][1] = copy.deepcopy(value['assets'][0])
            if variant == 'url': value['assets'][0]['browser_download_url'] = 'https://example.org/foreign.apk'
            if variant == 'digest': value['assets'][0]['digest'] = 'a'*64
            if variant == 'unfinished': value['assets'][0]['state'] = 'new'
            with self.subTest(variant=variant), self.assertRaises(ValueError): builder.validate_existing_release(value)

    def test_physical_gain_false_and_native_only_flags_true(self):
        self.assertIn('physical_fps_gain_validated', builder.FALSE_FLAGS)
        for name in ('java_or_dex_recompiled', 'mesa_driver_compiled_in_current_run', 'native_vulkan_probe_compiled_in_current_run', 'wgl_probe_compiled_in_current_run'):
            self.assertIn(name, builder.FALSE_FLAGS)
        self.assertIn('native_client_recompiled', builder.TRUE_FLAGS)
        self.assertEqual(builder.DONOR_GAME['sha256'], 'adcabb11135fe44b2c1f997a088ec58e4ea0d90e9defaa9f88efea34538caa44')

    def test_retained_suite_inventory_and_original_public_evidence_pin(self):
        import qualify_client_render_pipeline as qualification
        qualification.validate_suite_inventory()
        self.assertEqual(qualification.TEST_MODULES[:99], qualification.previous.TEST_MODULES)
        self.assertEqual(len(qualification.TEST_MODULES), 105)
        publication = json.loads((builder.ROOT/'docs/android-evidence/gpu-repair-0.13.21-publication.json').read_text())
        evidence = next(value for value in publication['actions_artifact_zip_metadata'] if value['id'] == builder.DONOR_EVIDENCE_ID)
        self.assertEqual(builder.DONOR_EVIDENCE, {'bytes': evidence['zip_bytes'], 'sha256': evidence['zip_sha256']})
        self.assertEqual(builder.DONOR_COMMIT, publication['repository_commit'])
        apk = next(value for value in publication['release']['assets'] if value['name'] == builder.DONOR_APK_NAME)
        self.assertEqual(builder.DONOR_APK, {name: apk[name] for name in ('bytes', 'sha256')})

    def test_workflow_compiles_only_game_and_reuses_signer(self):
        import yaml
        workflow = yaml.safe_load((builder.ROOT/builder.WORKFLOW).read_text())
        self.assertEqual(set(workflow['jobs']), {'changes', 'client', 'qualify', 'apk', 'public-audit'})
        self.assertFalse(workflow['concurrency']['cancel-in-progress'])
        self.assertEqual(workflow['jobs']['client']['runs-on'], 'windows-2025-vs2026')
        client_steps = workflow['jobs']['client']['steps']
        command = next(step['run'] for step in client_steps if 'Build only Game' in step.get('name', ''))
        self.assertIn('--target Game', command)
        all_text = (builder.ROOT/builder.WORKFLOW).read_text()
        for forbidden in ('package_client_gpu_repair.py', 'gpu-runtime/build.py', 'coh-gpu-probe.c /Fo', 'coh-vulkan-gpu-probe.c'):
            self.assertNotIn(forbidden, all_text)
        signing = [step for step in workflow['jobs']['apk']['steps'] if step.get('with', {}).get('name') == 'coh-client-interactive-signing']
        self.assertEqual(len(signing), 1); self.assertEqual(signing[0]['with']['run-id'], 36731428735)
        public_steps = workflow['jobs']['public-audit']['steps']
        self.assertTrue(any('download-public' in step.get('run', '') for step in public_steps))
        self.assertTrue(any(' audit' in step.get('run', '') for step in public_steps))


if __name__ == '__main__': unittest.main()
