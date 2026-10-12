"""Certified MapServer candidate retention, strict proof and actual preparation."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

import build_client_map_startup_apk as package


class MapStartupPackageTests(unittest.TestCase):
    def test_exact_derivative_owner_routes_reviewed_native_sources_and_final_evidence(self):
        import classify_client_map_startup_change as owner
        names = sorted(owner.CLIENT_MAP_STARTUP_ALLOWED)
        self.assertTrue(owner.client_map_startup_owned('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertTrue(owner.client_map_startup_owned('push', 'a'*40, 'b'*40, 'a'*40,
            sorted(owner.CLIENT_MAP_STARTUP_DOCS)))
        self.assertFalse(owner.client_map_startup_owned('push', 'a'*40, 'b'*40, 'a'*40,
            sorted(owner.CLIENT_MAP_STARTUP_DOCS-{owner.CLIENT_MAP_STARTUP_PUBLICATION})))
        self.assertFalse(owner.client_map_startup_owned('push', 'a'*40, 'b'*40, 'a'*40,
            sorted(owner.CLIENT_MAP_STARTUP_ALLOWED-{owner.CLIENT_MAP_STARTUP_MARKER})))

    def test_derivative_owner_refuses_unreviewed_game_renderer_database_assets_java_and_ancestry(self):
        import classify_client_map_startup_change as owner
        names = sorted(owner.CLIENT_MAP_STARTUP_ALLOWED)
        for extra in ('upstream/ouroboros/Game/src/graphics/gfx.c',
            'upstream/ouroboros/DbServer/dbdispatch.c', 'android/guest/client_gpu_profile.py',
            'assets/asset-pack-manifest.json', 'android/native/client-launcher.c',
            'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientSurface.java',
            'database/map-startup/unreviewed.c', 'docs/unreviewed-status.md'):
            with self.subTest(extra=extra):
                self.assertFalse(owner.client_map_startup_owned('push', 'a'*40, 'b'*40, 'a'*40, names+[extra]))
        for event, before, head, parent in (
            ('pull_request', 'a'*40, 'b'*40, 'a'*40),
            ('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40),
            ('push', 'c'*40, 'b'*40, 'a'*40),
            ('push', 'a'*40, 'b'*40, 'a'*40+'\n'+'c'*40),
            ('push', '0'*40, 'b'*40, '0'*40),
            ('push', 'a'*40, 'a'*40, 'a'*40)):
            with self.subTest(event=event, before=before, parent=parent):
                self.assertFalse(owner.client_map_startup_owned(event, before, head, parent, names))

    def test_release_identity_retains_exact_published_031_donor(self):
        self.assertEqual((package.VERSION_NAME, package.VERSION_CODE), ('0.13.32', 47))
        self.assertEqual(package.DONOR_COMMIT, '74fe247be85173e618f1af2c8af71b1316de4cd8')
        self.assertEqual(package.DONOR_APK, {'bytes': 41203812,
            'sha256': 'e56df1bcf2210aff131ba80189b1b2dee760f27066e3ee26e09c5fea1654ad80'})
        self.assertEqual(package.ADDED_PAYLOADS, {'assets/runtime/'+name for name in (
            'server_fx_catalog.py', 'native_map_startup_contract.py', 'server-fx-catalog.bin',
            'server-fx-catalog-manifest.json', 'map-startup-manifest.json')})
        self.assertIn('native_mapserver_recompiled', package.TRUE_FLAGS)
        for name in ('native_client_recompiled', 'native_dbserver_recompiled',
            'graphics_driver_changed', 'wine_or_fex_changed', 'world_assets_changed',
            'asset_reimport_required', 'save_acceptance_relaxed',
            'physical_map_startup_speedup_validated', 'sub_30_second_map_startup_validated'):
            self.assertIn(name, package.FALSE_FLAGS)
        self.assertEqual(package.REVIEWED_JAVA_CHANGES, {
            'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/'+name+'.java'
            for name in ('ClientAcceptance', 'ClientRuntime')} | {
            'android/recovery/src/main/java/io/github/russianranger/cohclientinteractive/ClientReports.java'})

    def test_retention_rejects_mutated_native_gpu_database_assets_missing_inputs_and_unknown_payloads(self):
        retained = {'assets/runtime/'+name for name in (
            'client-runtime.zip', 'hardware-renderer.zip', 'dbserver-package.tar.gz',
            'dbserver-schema.tar.gz', 'native-responsiveness.json', 'asset-pack-manifest.json',
            'startup-dbserver.exe', 'postgresql-runtime.tar.gz', 'client_gpu_profile.py',
            'character_reopen_diagnostic.py', 'character_creation_diagnostic.py')}
        names = package.REPLACED_PAYLOADS | retained
        names |= {'assets/runtime/retained-%02d' % index for index in range(69-len(names))}
        donor = {'payloads': {name: package.pin(name.encode()) for name in names}}
        expected = package.replacement_payloads(donor)
        candidate = copy.deepcopy(donor['payloads'])
        candidate.update({name: package.pin(('approved:'+name).encode()) for name in expected})
        candidate.update({name: package.pin(('added:'+name).encode()) for name in package.ADDED_PAYLOADS})
        package.payload_boundaries(candidate, donor)
        for name in retained:
            bad = dict(candidate, **{name: package.pin(b'unapproved bytes')})
            with self.subTest(mutation=name), self.assertRaises(ValueError):
                package.payload_boundaries(bad, donor)
        for name in expected | package.ADDED_PAYLOADS:
            bad = dict(candidate); del bad[name]
            with self.subTest(missing=name), self.assertRaises(ValueError):
                package.payload_boundaries(bad, donor)
        for name in expected:
            bad = dict(candidate); bad[name] = donor['payloads'][name]
            with self.subTest(unrepaired=name), self.assertRaises(ValueError):
                package.payload_boundaries(bad, donor)
        candidate['assets/runtime/observer-MapServer.exe'] = package.pin(b'host-only observer')
        with self.assertRaises(ValueError): package.payload_boundaries(candidate, donor)

    def test_signed_preparation_refuses_native_proof_changes_fabricated_device_claims_or_typed_scope_changes(self):
        proof = {'map_startup_component': {'status': 'passed', 'shipping_mapserver': package.pin(b'qualified PE'),
            'native_fixture': package.pin(b'actual native fixture report'),
            'physical_timing_validated': False}, 'runtime_assets': {'animation_count': 5878},
            'full_startup': {'native_runtime_booted': False, 'physical_execution_validated': False,
                'original_import': {'files': 173011}, 'full_prepare_runtime_executed': True}}
        qualification = {'package_preflight': copy.deepcopy(proof)}
        package.require_signed_preflight(proof, qualification)
        for section, key, value in (
            ('map_startup_component', 'shipping_mapserver', package.pin(b'other PE')),
            ('map_startup_component', 'native_fixture', package.pin(b'unexecuted fixture')),
            ('map_startup_component', 'physical_timing_validated', True),
            ('runtime_assets', 'animation_count', 5877),
            ('full_startup', 'native_runtime_booted', True),
            ('full_startup', 'physical_execution_validated', True),
            ('full_startup', 'full_prepare_runtime_executed', 1)):
            altered = copy.deepcopy(proof); altered[section][key] = value
            with self.subTest(section=section, key=key), self.assertRaises(ValueError):
                package.require_signed_preflight(altered, qualification)

    def test_actual_public_031_and_certified_native_component_complete_cold_warm_kings_preparation(self):
        apk = Path(os.environ.get('COH_MAP_STARTUP_TEST_DONOR_APK', package.ROOT/'out/donor.apk')).resolve()
        report = Path(os.environ.get('COH_MAP_STARTUP_TEST_DONOR_REPORT',
            package.ROOT/'out/donor-evidence/client-profile-recovery-apk-build-report.json')).resolve()
        inputs = Path(os.environ.get('COH_MAP_STARTUP_TEST_INPUTS', package.ROOT/'out/map-startup-inputs')).resolve()
        self.assertTrue(apk.is_file() and report.is_file() and inputs.is_dir(),
            'Actual authenticated .31 APK, receipt and certified native component are mandatory; no skips')
        donor = package.validate_donor(apk, report)
        import package_map_startup_native as native
        commit = package.builder().source_commit(os.environ.get('COH_MAP_STARTUP_TEST_SOURCE_COMMIT'))
        component = native.validate_component_inputs(inputs, commit)
        with tempfile.TemporaryDirectory(prefix='coh-map-startup-test-') as temporary:
            runtime, payloads, preflight = package.extract_and_repair(
                apk, donor, Path(temporary)/'candidate', commit, inputs)
        package.payload_boundaries(payloads, donor)
        self.assertEqual(preflight['map_startup_component'], component)
        self.assertEqual(preflight['runtime_assets']['animation_count'], 5878)
        import qualify_full_startup_preflight as startup
        full = startup.validate_proof(preflight['full_startup'])
        for name in ('full_private_worktree_mirror_executed', 'full_prepare_runtime_executed',
            'fresh_create_cold_preparation_verified', 'saved_reopen_warm_preparation_verified',
            'full_kings_row_cold_and_reuse_preparation_verified'):
            self.assertIs(full[name], True)
        self.assertIs(full['native_runtime_booted'], False)
        self.assertIs(full['physical_execution_validated'], False)
        self.assertEqual(runtime['external_asset_pack'], donor['runtime_manifest']['external_asset_pack'])


if __name__ == '__main__': unittest.main()
