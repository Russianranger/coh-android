"""Retain .29 native/renderer/assets while replacing two reviewed guest helpers."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import build_client_animation_repair_apk as package


class AnimationRepairPackageTests(unittest.TestCase):
    def test_exact_four_payload_boundary_and_monotonic_version(self):
        self.assertEqual((package.VERSION_NAME, package.VERSION_CODE), ('0.13.30', 45))
        self.assertEqual(package.REPLACED_PAYLOADS, {
            'assets/runtime/server_animation_package.py', 'assets/runtime/local_character_server.py',
            'assets/runtime/client-manifest.json', 'assets/runtime/runtime-manifest.json'})
        self.assertIn('guest_helpers_changed', package.TRUE_FLAGS)
        for name in ('java_or_dex_recompiled', 'native_mapserver_recompiled', 'native_client_recompiled',
                     'world_assets_changed', 'asset_reimport_required', 'save_acceptance_relaxed'):
            self.assertIn(name, package.FALSE_FLAGS)

    def test_boundary_rejects_native_renderer_guest_and_asset_mutation_or_loss(self):
        retained = {'assets/runtime/'+name for name in ('game-package.tar.gz', 'client-runtime.zip',
            'hardware-renderer.zip', 'dbserver-package.tar.gz', 'dbserver-schema.tar.gz',
            'game_diagnostic.py', 'character_reopen_diagnostic.py', 'asset-pack-manifest.json',
            'kings-row-beacon-lock.json', 'native-responsiveness.json')}
        names = package.REPLACED_PAYLOADS | retained
        names |= {'assets/runtime/retained-%02d' % index for index in range(69-len(names))}
        donor = {'payloads': {name: package.pin(name.encode()) for name in names}}
        candidate = copy.deepcopy(donor['payloads'])
        candidate.update({name: package.pin(b'approved repair') for name in package.REPLACED_PAYLOADS})
        package.payload_boundaries(candidate, donor)
        for name in retained:
            with self.subTest(name=name):
                bad = dict(candidate, **{name: package.pin(b'unknown change')})
                with self.assertRaises(ValueError): package.payload_boundaries(bad, donor)
                del bad[name]
                with self.assertRaises(ValueError): package.payload_boundaries(bad, donor)
        for name in package.REPLACED_PAYLOADS:
            bad = dict(candidate); bad[name] = donor['payloads'][name]
            with self.subTest(unrepaired=name), self.assertRaises(ValueError): package.payload_boundaries(bad, donor)

    def test_manifest_repair_keeps_native_and_external_asset_ownership_exact(self):
        native = package.pin(b'unchanged game archive')
        donor = {'_client_verification': {'files': {'game-package.tar.gz': native}},
            'runtime_manifest': {'files': {'game-package.tar.gz': native},
                'client_bundle': {'local_server': {'mapserver': {'archive_pin': native,
                    'package_repository_commit': 'c'*40, 'monorail_native_repository_commit': 'd'*40}}},
                'external_asset_pack': {'version': '1.0.0', 'manifest_sha256': 'a'*64},
                'client_receipt_repair': {'repository_commit': package.DONOR_COMMIT}}}
        original = copy.deepcopy(donor)
        helpers = {name: package.pin(name.encode()) for name in ('local_character_server.py', 'server_animation_package.py')}
        client, runtime = package.verification_manifests(donor, helpers, 'e'*40)
        self.assertEqual(runtime['client_bundle'], donor['runtime_manifest']['client_bundle'])
        self.assertEqual(runtime['external_asset_pack'], donor['runtime_manifest']['external_asset_pack'])
        self.assertEqual(runtime['client_receipt_repair'], donor['runtime_manifest']['client_receipt_repair'])
        self.assertEqual(runtime['files']['game-package.tar.gz'], native)
        self.assertEqual(runtime['files']['client-manifest.json'], package.pin(package.shared.encoded(client)))
        self.assertEqual(runtime['client_animation_repair']['changed_guest_helpers'], helpers)
        self.assertEqual(donor, original)
        with self.assertRaises(ValueError): package.verification_manifests(donor, {'unknown.py': native}, 'e'*40)

    def test_actual_029_donor_and_installer_preflight_are_process_deterministic(self):
        apk = Path(os.environ.get('COH_ANIMATION_TEST_DONOR_APK', package.ROOT/'out/donor.apk')).resolve()
        report = Path(os.environ.get('COH_ANIMATION_TEST_DONOR_REPORT',
            package.ROOT/'out/donor-evidence/client-receipt-repair-apk-build-report.json')).resolve()
        self.assertTrue(apk.is_file() and report.is_file(), 'Exact public .29 APK and report required; no fixture skip')
        script = '''import json,sys,tempfile
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import build_client_animation_repair_apk as p
d=p.validate_donor(Path(sys.argv[2]),Path(sys.argv[3]))
with tempfile.TemporaryDirectory() as td:
    runtime,payloads,preflight=p.extract_and_repair(Path(sys.argv[2]),d,Path(td)/'donor','a'*40)
    print(json.dumps({'payloads':payloads,'preflight':preflight},sort_keys=True))
'''
        results = []
        for seed in ('1', '73422'):
            result = subprocess.run([sys.executable, '-c', script, str(Path(package.__file__).parent),
                str(apk), str(report)], env=dict(os.environ, PYTHONHASHSEED=seed),
                capture_output=True, text=True, timeout=600)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            results.append(json.loads(result.stdout))
        self.assertEqual(results[0], results[1])
        proof = results[0]['preflight']['runtime_assets']
        self.assertEqual(proof['status'], 'passed')
        self.assertEqual(proof['animation_count'], 5878)
        for name in ('fresh_create_payload_verified', 'saved_reopen_payload_verified',
                     'atlas_cold_and_reuse_verified', 'kings_cold_and_reuse_verified', 'prepared_caches_verified'):
            self.assertIs(proof[name], True)
        self.assertIs(proof['native_runtime_booted'], False)
        self.assertIs(proof['physical_execution_validated'], False)


if __name__ == '__main__': unittest.main()
