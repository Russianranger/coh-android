"""Certified MapServer candidate retention, strict proof and actual preparation."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

import build_client_map_startup_apk as package


class MapStartupPackageTests(unittest.TestCase):
    def actual_inputs(self):
        apk = Path(os.environ.get('COH_MAP_STARTUP_TEST_DONOR_APK', package.ROOT/'out/donor.apk')).resolve()
        report = Path(os.environ.get('COH_MAP_STARTUP_TEST_DONOR_REPORT',
            package.ROOT/'out/donor-evidence/client-profile-recovery-apk-build-report.json')).resolve()
        inputs = Path(os.environ.get('COH_MAP_STARTUP_TEST_INPUTS', package.ROOT/'out/map-startup-inputs')).resolve()
        self.assertTrue(apk.is_file() and report.is_file() and inputs.is_dir(),
            'Actual authenticated .31 APK, receipt and certified native component are mandatory; no skips')
        donor = package.validate_donor(apk, report)
        commit = package.builder().source_commit(os.environ.get('COH_MAP_STARTUP_TEST_SOURCE_COMMIT'))
        return apk, donor, inputs, commit

    def test_actual_component_serialization_preserves_every_historical_reader_before_preparation(self):
        import game_diagnostic as guest
        import package_map_startup_native as native
        apk, donor, inputs, commit = self.actual_inputs()
        with tempfile.TemporaryDirectory(prefix='coh-map-startup-receipts-') as temporary:
            destination = Path(temporary)/'candidate'
            runtime, _, preflight = package.extract_and_repair(
                apk, donor, destination, commit, inputs, execute_preflight=False)
            path = destination/'assets/runtime/game-package.tar.gz'
            members = package.game_archive_members(path)
            raw = members['game-package.json']; game = json.loads(raw)
            self.assertEqual(guest.game_listener_contract(game), guest.evidence.GAME_LOOPBACK_METADATA)
            self.assertTrue(guest.game_loopback_contract(game)['endpoints'])
            receipt = native.contract.embedded_receipt(game)
            self.assertEqual(native.contract.monorail.embedded_receipt(game)['mapserver']['sha256'],
                             native.contract.PREVIOUS_SHA256)
            progress = guest.mapserver_progress_contract(game)
            self.assertEqual(progress['producer']['mapserver_sha256'], receipt['mapserver']['sha256'])
            self.assertEqual(package.pin(members['MapServer.exe']),
                             native.contract.pin_record(receipt['mapserver']))
            mapped = runtime['client_bundle']['local_server']['mapserver']
            self.assertEqual(mapped['package_manifest_sha256'], package.pin(raw)['sha256'])
            self.assertNotEqual(mapped['package_manifest_sha256'], package.pin(native.canonical(game))['sha256'])
            self.assertEqual(mapped['archive_pin'], package.builder().file_pin(path))
            self.assertEqual(preflight['server_archives']['archives']['dbserver-package.tar.gz'],
                             donor['package_preflight']['server_archives']['archives']['dbserver-package.tar.gz'])
            original = Path(temporary)/'original.tar.gz'
            with zipfile.ZipFile(apk) as archive:
                original.write_bytes(archive.read('assets/runtime/game-package.tar.gz'))
            old_members = package.game_archive_members(original)
            old = json.loads(old_members['game-package.json'])
            self.assertEqual(native.contract.previous_package(game), old)
            self.assertEqual(json.dumps(game['inputs'], indent=2), json.dumps(old['inputs'], indent=2))
            for name in ('loopback_game', 'mapserver_progress'):
                current_manifest = json.dumps(game['inputs'][name]['manifest'], indent=2)+'\n'
                old_manifest = json.dumps(old['inputs'][name]['manifest'], indent=2)+'\n'
                hashes = {hashlib.sha256(raw.encode()).hexdigest() for raw in
                          (current_manifest, current_manifest.replace('\n', '\r\n'))}
                self.assertEqual(hashes, {hashlib.sha256(raw.encode()).hexdigest() for raw in
                                 (old_manifest, old_manifest.replace('\n', '\r\n'))})
                self.assertIn(game['inputs'][name]['manifest_sha256'], hashes)
            for name in set(members)-{'MapServer.exe', 'game-package.json'}:
                self.assertEqual(members[name], old_members[name], name)
            # Reproduce the rejected canonical intermediate using actual
            # qualified bytes. Both old byte guards must remain strict.
            sorted_game = json.loads(native.canonical(game))
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'Game listener donor receipt bytes differ'):
                guest.game_listener_contract(sorted_game)
            with self.assertRaisesRegex(ValueError, 'Candidate MapServer producer manifest differs'):
                guest.mapserver_progress_contract(sorted_game)
            good_pin = package.builder().file_pin(path)
            members['game-package.json'] = native.canonical(game)
            native.write_game_archive(path, members)
            restored, restored_pin = package.restore_retained_game_receipt_order(path, old_members)
            self.assertEqual(restored, game)
            self.assertEqual(restored_pin, package.pin(raw))
            self.assertEqual(package.builder().file_pin(path), good_pin)

    def test_actual_component_serialization_refuses_changed_retained_metadata_and_native_members(self):
        import package_map_startup_native as native
        apk, donor, inputs, commit = self.actual_inputs()
        with tempfile.TemporaryDirectory(prefix='coh-map-startup-receipt-negatives-') as temporary:
            destination = Path(temporary)/'candidate'
            package.extract_and_repair(apk, donor, destination, commit, inputs, execute_preflight=False)
            path = destination/'assets/runtime/game-package.tar.gz'
            good = package.game_archive_members(path)
            original = Path(temporary)/'original.tar.gz'
            with zipfile.ZipFile(apk) as archive:
                original.write_bytes(archive.read('assets/runtime/game-package.tar.gz'))
            old_members = package.game_archive_members(original)
            bad_metadata = copy.deepcopy(good)
            game = json.loads(good['game-package.json'])
            game['inputs']['loopback_game']['manifest']['runtime_execution_validated'] = True
            bad_metadata['game-package.json'] = native.canonical(game)
            for name, members in (
                ('retained_metadata', bad_metadata),
                ('retained_dbserver', dict(good, **{'DbServer.exe': b'changed retained DbServer'})),
                ('current_mapserver', dict(good, **{'MapServer.exe': b'changed certified MapServer'})),
                ('unknown_member', dict(good, **{'unreviewed.dll': b'unknown dependency'}))):
                native.write_game_archive(path, members)
                with self.subTest(mutation=name), self.assertRaises(ValueError):
                    package.restore_retained_game_receipt_order(path, old_members)

    def test_atlas_legacy_workflow_always_runs_host_checks_then_uses_the_bounded_native_owner(self):
        import yaml
        workflow = yaml.safe_load((package.ROOT/'.github/workflows/android-atlas-game.yml').read_text())
        tooling = workflow['jobs']['tooling']
        self.assertEqual(tooling['outputs']['legacy_native_required'],
                         '${{ steps.owner.outputs.legacy_native_required }}')
        checkout = next(step for step in tooling['steps'] if step.get('uses', '').startswith('actions/checkout@'))
        self.assertEqual(checkout['with']['fetch-depth'], 2)
        owner = next(step for step in tooling['steps'] if step.get('id') == 'owner')
        self.assertEqual(owner['run'], 'python3 tools/android/interactive/classify_client_assets_change.py')
        self.assertEqual(owner['env']['COH_PUSH_BEFORE'], '${{ github.event.before }}')
        checks = next(step for step in tooling['steps'] if step.get('name') ==
            'Check combined app, device policy and exact accepted inputs')
        self.assertNotIn('if', checks)
        self.assertEqual(checks['run'].splitlines(), [
            'python3 tools/android/run_retained_host_contracts.py --group atlasgame',
            "python3 -m unittest discover -s tools/android/atlas -p 'test_*.py' -v",
            'python3 tools/android/run_retained_host_contracts.py --group game'])
        self.assertEqual(workflow['jobs']['apk']['needs'], 'tooling')
        self.assertEqual(workflow['jobs']['apk']['if'],
            "github.event_name != 'pull_request' && needs.tooling.outputs.legacy_native_required != 'false'")
        self.assertEqual(workflow['jobs']['runtime']['needs'], 'apk')

    def test_inherited_legacy_owner_delegates_current_scope_without_changing_historical_specializations(self):
        import classify_client_map_startup_change as owner
        import classify_client_assets_change as legacy
        import classify_client_profile_recovery_change as historical
        names = sorted(owner.CLIENT_MAP_STARTUP_ALLOWED)
        context = ('push', 'a'*40, 'b'*40, 'a'*40, names)
        self.assertTrue(legacy.client_animation_repair_owned(*context))
        self.assertFalse(legacy.client_assets_owned(*context))
        self.assertFalse(historical.client_profile_recovery_owned(*context))

    def test_inherited_legacy_owner_keeps_unknown_paths_dispatch_pull_request_and_ambiguous_history_closed(self):
        import classify_client_map_startup_change as owner
        import classify_client_assets_change as legacy
        names = sorted(owner.CLIENT_MAP_STARTUP_ALLOWED)
        for context in (
            ('push', 'a'*40, 'b'*40, 'a'*40, names+['android/guest/client_gpu_profile.py']),
            ('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names),
            ('pull_request', 'a'*40, 'b'*40, 'a'*40, names),
            ('push', 'c'*40, 'b'*40, 'a'*40, names),
            ('push', 'a'*40, 'b'*40, 'a'*40+'\n'+'c'*40, names),
            ('push', '0'*40, 'b'*40, '0'*40, names)):
            with self.subTest(context=context[:4]):
                self.assertFalse(legacy.client_animation_repair_owned(*context))

    def test_legacy_linux_groups_keep_every_historical_module_and_name_only_separate_fixture_owners(self):
        import run_retained_host_contracts as retained
        import qualify_client_map_startup as qualification
        for group in ('game', 'atlasgame'):
            directory, selected, excluded = retained.inventory(group)
            self.assertEqual(set(selected), set(retained.HISTORICAL_MODULES[group])
                | set(retained.REQUIRED_ADDITIONS[group]))
            self.assertTrue(all(path.parent == directory for path in selected.values()))
            self.assertEqual(set(selected) | set(excluded),
                {path.name for path in directory.glob('test_*.py')})
            self.assertTrue(all(excluded.values()))
        self.assertEqual(retained.EXCLUDED_MODULES['game'].keys(), {'test_map_startup_monorail_budget.py'})
        self.assertEqual(retained.EXCLUDED_MODULES['atlasgame'].keys(), {
            'test_server_fx_catalog.py', 'test_server_fx_catalog_native_proof.py'})
        self.assertTrue({'test_server_fx_catalog', 'test_server_fx_catalog_native_proof',
            'test_map_startup_monorail_budget'} <= set(qualification.TEST_MODULES))
        import package_map_startup_native as native
        self.assertIn('tools/android/game/test_map_startup_monorail_budget.py', native.SOURCE_FILES)

    def test_legacy_linux_inventory_cannot_drop_retained_modules_or_silently_ignore_new_host_files(self):
        import run_retained_host_contracts as retained
        with tempfile.TemporaryDirectory(prefix='coh-retained-inventory-') as temporary:
            root = Path(temporary); directory = root/'tools/android/game'; directory.mkdir(parents=True)
            for name in set(retained.HISTORICAL_MODULES['game']) | set(retained.EXCLUDED_MODULES['game']):
                (directory/name).write_text('# isolated source inventory fixture\n')
            extra = directory/'test_additional_host_contract.py'; extra.write_text('# new host suite\n')
            _, selected, excluded = retained.inventory('game', root=root)
            self.assertIn(extra.name, selected)
            self.assertEqual(set(excluded), {'test_map_startup_monorail_budget.py'})
            (directory/retained.HISTORICAL_MODULES['game'][0]).unlink()
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                retained.inventory('game', root=root)

    def test_legacy_linux_loader_selects_actual_source_even_when_basename_is_shadowed(self):
        import run_retained_host_contracts as retained
        import sys
        from types import ModuleType
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(prefix='coh-retained-loader-') as temporary:
            path = Path(temporary)/'test_shadowed.py'
            path.write_text('import unittest\nclass ActualPath(unittest.TestCase):\n'
                ' def test_actual_selected_source(self): self.assertEqual(2 + 2, 4)\n')
            wrong = ModuleType('test_shadowed'); wrong.__file__ = str(path.with_name('wrong.py'))
            with patch.dict(sys.modules, {'test_shadowed': wrong}):
                suite, search = retained.load_suite('game', path)
                self.assertEqual(suite.countTestCases(), 1)
                self.assertEqual(search[0], str(path.parent))
                result = unittest.TestResult(); suite.run(result)
                self.assertTrue(result.wasSuccessful())
                self.assertIs(sys.modules['test_shadowed'], wrong)

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
        apk, donor, inputs, commit = self.actual_inputs()
        import package_map_startup_native as native
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
