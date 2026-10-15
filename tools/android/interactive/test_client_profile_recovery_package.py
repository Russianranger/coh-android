"""Retain .30 native/renderer/assets while qualifying explicit profile recovery and complete preparation."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import build_client_profile_recovery_apk as package


class ProfileRecoveryPackageTests(unittest.TestCase):
    def test_exact_four_payload_boundary_and_monotonic_version(self):
        self.assertEqual((package.VERSION_NAME, package.VERSION_CODE), ('0.13.31', 46))
        self.assertEqual(package.REPLACED_PAYLOADS, {
            'assets/runtime/character_creation_diagnostic.py', 'assets/runtime/local_character_server.py',
            'assets/runtime/client-manifest.json', 'assets/runtime/runtime-manifest.json'})
        self.assertIn('guest_helpers_changed', package.TRUE_FLAGS)
        self.assertIn('java_or_dex_recompiled', package.TRUE_FLAGS)
        for name in ('native_mapserver_recompiled', 'native_client_recompiled',
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
        helpers = {name: package.pin(name.encode()) for name in ('local_character_server.py', 'character_creation_diagnostic.py')}
        client, runtime = package.verification_manifests(donor, helpers, 'e'*40)
        self.assertEqual(runtime['client_bundle'], donor['runtime_manifest']['client_bundle'])
        self.assertEqual(runtime['external_asset_pack'], donor['runtime_manifest']['external_asset_pack'])
        self.assertEqual(runtime['client_receipt_repair'], donor['runtime_manifest']['client_receipt_repair'])
        self.assertEqual(runtime['files']['game-package.tar.gz'], native)
        self.assertEqual(runtime['files']['client-manifest.json'], package.pin(package.shared.encoded(client)))
        self.assertEqual(runtime['client_profile_recovery']['changed_guest_helpers'], helpers)
        self.assertEqual(donor, original)
        with self.assertRaises(ValueError): package.verification_manifests(donor, {'unknown.py': native}, 'e'*40)

    def test_exact_profile_owner_defers_all_historical_publishers(self):
        import classify_client_profile_recovery_change as owner
        import classify_storage_cleanup_change as legacy
        import classify_interactive_change as interactive
        names=sorted(owner.CLIENT_PROFILE_RECOVERY_ALLOWED)
        self.assertTrue(owner.client_profile_recovery_owned('push','a'*40,'b'*40,'a'*40,names))
        self.assertFalse(interactive.runtime_required('push','a'*40,'b'*40,'a'*40,names))
        for name in dir(legacy):
            function=getattr(legacy,name)
            if callable(function) and name.endswith('_required') and name not in ('task_required',):
                # Every gameplay owner's finite push gate has this same signature.
                import inspect
                if len(inspect.signature(function).parameters)==5:
                    with self.subTest(owner=name):
                        self.assertFalse(function('push','a'*40,'b'*40,'a'*40,names))

    def test_profile_owner_rejects_unreviewed_native_guest_java_assets_and_history(self):
        import classify_client_profile_recovery_change as owner
        names=sorted(owner.CLIENT_PROFILE_RECOVERY_ALLOWED)
        for extra in ('android/guest/game_diagnostic.py','android/guest/server_animation_package.py',
                'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientSurface.java',
                'android/native/client-launcher.c','assets/asset-pack-manifest.json',
                'tools/android/interactive/unreviewed.py','docs/unreviewed-status.md'):
            with self.subTest(extra=extra):
                self.assertFalse(owner.client_profile_recovery_owned('push','a'*40,'b'*40,'a'*40,names+[extra]))
        for event,before,head,parent in (('pull_request','a'*40,'b'*40,'a'*40),
                ('workflow_dispatch','a'*40,'b'*40,'a'*40),('push','c'*40,'b'*40,'a'*40),
                ('push','a'*40,'b'*40,'a'*40+'\n'+'c'*40),('push','0'*40,'b'*40,'0'*40)):
            self.assertFalse(owner.client_profile_recovery_owned(event,before,head,parent,names))
        self.assertFalse(owner.client_profile_recovery_owned('push','a'*40,'b'*40,'a'*40,
            sorted(owner.CLIENT_PROFILE_RECOVERY_ALLOWED-{owner.CLIENT_PROFILE_RECOVERY_MARKER})))
        self.assertTrue(owner.client_profile_recovery_owned('push','a'*40,'b'*40,'a'*40,
            sorted(owner.CLIENT_PROFILE_RECOVERY_DOCS)))
        self.assertFalse(owner.client_profile_recovery_owned('push','a'*40,'b'*40,'a'*40,
            sorted(owner.CLIENT_PROFILE_RECOVERY_DOCS-{owner.CLIENT_PROFILE_RECOVERY_PUBLICATION})))

    def test_signed_full_preparation_must_match_qualified_native_assets_and_execution_boundary(self):
        proof={'server_archives': {'mapserver': package.pin(b'qualified original native archive')},
            'runtime_assets': {'animation_count': 5878},
            'full_startup': {'native_runtime_booted': False, 'physical_execution_validated': False,
                'full_prepare_runtime_executed': True, 'original_import': {'files': 173011}}}
        qualification={'package_preflight': copy.deepcopy(proof)}
        package.require_signed_preflight(proof,qualification)
        changes=(('server_archives','mapserver',package.pin(b'wrong signed native archive')),
            ('runtime_assets','animation_count',5877),('full_startup','native_runtime_booted',True),
            ('full_startup','physical_execution_validated',True),
            ('full_startup','full_prepare_runtime_executed',1))
        for section,key,value in changes:
            altered=copy.deepcopy(proof);altered[section][key]=value
            with self.subTest(section=section,key=key), self.assertRaises(ValueError):
                package.require_signed_preflight(altered,qualification)
        altered=copy.deepcopy(proof);altered['full_startup']['original_import']['files']=1
        with self.assertRaises(ValueError):package.require_signed_preflight(altered,qualification)

    def test_actual_authenticated_030_donor_and_candidate_full_orchestration(self):
        import tempfile
        apk=Path(os.environ.get('COH_PROFILE_RECOVERY_TEST_DONOR_APK',package.ROOT/'out/donor.apk')).resolve()
        report=Path(os.environ.get('COH_PROFILE_RECOVERY_TEST_DONOR_REPORT',
            package.ROOT/'out/donor-evidence/client-animation-repair-apk-build-report.json')).resolve()
        self.assertTrue(apk.is_file() and report.is_file(),'Exact .30 public APK/report required; no skips')
        donor=package.validate_donor(apk,report)
        with tempfile.TemporaryDirectory(prefix='coh-profile-test-') as temporary:
            runtime,payloads,preflight=package.extract_and_repair(apk,donor,Path(temporary)/'donor','a'*40)
        package.payload_boundaries(payloads,donor)
        self.assertEqual(preflight['runtime_assets']['animation_count'],5878)
        import qualify_full_startup_preflight as startup
        full=startup.validate_proof(preflight['full_startup'])
        self.assertTrue(full['full_private_worktree_mirror_executed'])
        self.assertTrue(full['full_prepare_runtime_executed'])
        self.assertTrue(full['full_kings_row_cold_and_reuse_preparation_verified'])
        self.assertFalse(full['native_runtime_booted'])
        self.assertFalse(full['physical_execution_validated'])


if __name__ == '__main__': unittest.main()
