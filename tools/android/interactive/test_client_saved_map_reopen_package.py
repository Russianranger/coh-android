"""Actual audited .33 retention and strict .34 saved-map/report/cache packaging.

Light reconstruction runs on real public bytes. Complete asset preparation,
strict SQL, signed assembly and public audit are separate mandatory gates.
"""
import copy
import contextlib
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

import build_client_saved_map_reopen_apk as package
import classify_client_saved_map_reopen_change as owner
import qualify_client_saved_map_reopen as qualification


class SavedMapReopenPackageTests(unittest.TestCase):
    @classmethod
    def actual_inputs(cls):
        recovered = Path('/workspace/scratch/192126a63e48/qualification/public033')
        apk = Path(os.environ.get('COH_SAVED_MAP_REOPEN_TEST_DONOR_APK',
            package.ROOT/'out/donor.apk'))
        report = Path(os.environ.get('COH_SAVED_MAP_REOPEN_TEST_DONOR_REPORT',
            package.ROOT/'out/donor-evidence'/package.DONOR_REPORT_NAME))
        if not apk.is_file(): apk = recovered/package.DONOR_APK_NAME
        if not report.is_file(): report = recovered/package.DONOR_REPORT_NAME
        if not apk.is_file() or not report.is_file():
            raise AssertionError('Authenticated actual public .33 APK and build receipt required; no skips')
        return apk.resolve(), report.resolve()

    @classmethod
    def actual_fixture(cls):
        if not hasattr(cls, '_fixture'):
            apk, report = cls.actual_inputs()
            donor = package.validate_donor(apk, report)
            commit = package.builder().source_commit(os.environ.get('COH_SAVED_MAP_REOPEN_TEST_SOURCE_COMMIT'))
            with tempfile.TemporaryDirectory(prefix='coh-saved-map-light-') as temporary:
                target = Path(temporary)/'candidate'
                runtime, payloads, preflight = package.extract_and_repair(
                    apk, donor, target, commit, execute_preflight=False)
                with zipfile.ZipFile(apk) as archive:
                    original = {name: archive.read(name) for name in
                        set(donor['payloads']) | {'classes.dex'} | set(donor['retained_android_resources'])}
                candidate = {name: (target/name).read_bytes() for name in original}
            cls._fixture = donor, commit, runtime, payloads, preflight, original, candidate
        return cls._fixture

    def test_monotonic_successor_uses_audited_033_donor_and_original_native_identity(self):
        self.assertEqual((package.VERSION_NAME, package.VERSION_CODE), ('0.13.34', 49))
        self.assertEqual(package.DONOR_COMMIT, 'e03943f76b13192680be363dac005d6f23c7a526')
        self.assertEqual(package.DONOR_RUN_ID, 38285895633)
        self.assertEqual(package.DONOR_APK, {'bytes': 42043924,
            'sha256': '482481fd14357f56a0c77069124fdce42712a06180ead8cb4c0cca2a671d4fc2'})
        donor, _, _, _, _, _, _ = self.actual_fixture()
        self.assertEqual(donor['donor']['repository_commit'], '6c4d1d74f34ecdea8fabcf6238368bf72003878f')
        self.assertFalse(donor['native_mapserver_recompiled'])
        self.assertEqual(package.APK_NAME, 'COH-Atlas-Gameplay-0.13.34.apk')
        self.assertEqual(package.DONOR_APK_NAME, 'COH-Atlas-Gameplay-0.13.33.apk')

    def test_historical_032_033_builders_markers_workflows_and_tests_are_exact_source_bytes(self):
        _, report = self.actual_inputs(); donor = json.loads(report.read_bytes())
        for name in ('tools/android/interactive/build_client_map_startup_apk.py',
                'tools/android/interactive/release-client-map-startup-0.13.32.json',
                'tools/android/interactive/build_client_report_loading_apk.py',
                'tools/android/interactive/qualify_client_report_loading.py',
                'tools/android/interactive/release-client-report-loading-0.13.33.json',
                'tools/android/interactive/test_client_report_loading_package.py',
                '.github/workflows/android-client-report-loading.yml'):
            self.assertEqual(package.builder().file_pin(package.ROOT/name),
                donor['qualification']['source_files'][name], name)

    def test_finite_reviewed_source_scope_excludes_native_assets_and_save_relaxation(self):
        self.assertEqual(package.GUEST_SOURCE_CHANGES, {'android/guest/character_zoning.py',
            'android/guest/character_server_data_cache.py'})
        self.assertEqual(len(package.REVIEWED_JAVA_CHANGES), 5)
        self.assertEqual(package.ADDED_PAYLOADS, frozenset())
        for name in ('native_client_recompiled', 'native_mapserver_recompiled', 'native_dbserver_recompiled',
                'graphics_driver_changed', 'wine_or_fex_changed', 'world_assets_changed',
                'asset_reimport_required', 'save_acceptance_relaxed', 'native_runtime_booted',
                'physical_kings_row_reopen_validated', 'physical_map_startup_speedup_validated',
                'sub_30_second_map_startup_validated'):
            self.assertIn(name, package.FALSE_FLAGS)
        self.assertTrue(set(package.REVIEWED_JAVA_CHANGES) <= owner.CLIENT_SAVED_MAP_REOPEN_ALLOWED)
        self.assertTrue(set(package.SOURCE_FILES) <= owner.CLIENT_SAVED_MAP_REOPEN_ALLOWED)

    def test_actual_public_payloads_have_only_two_reviewed_helper_and_manifest_replacements(self):
        donor, _, _, payloads, _, original, candidate = self.actual_fixture()
        changed = {name for name in original if original[name] != candidate[name]}
        expected = {'assets/runtime/'+Path(name).name for name in package.GUEST_SOURCE_CHANGES}
        expected.update(('assets/runtime/client-manifest.json', 'assets/runtime/runtime-manifest.json'))
        self.assertEqual(changed, expected)
        self.assertEqual(package.replacement_payloads(donor), expected)
        package.payload_boundaries(payloads, donor)
        self.assertEqual(candidate['classes.dex'], original['classes.dex'])
        for name in donor['retained_android_resources']:
            self.assertEqual(candidate[name], original[name], name)

    def test_every_native_gpu_wine_fex_asset_descriptor_and_resource_byte_is_retained(self):
        donor, _, _, payloads, preflight, original, candidate = self.actual_fixture()
        changed = package.replacement_payloads(donor)
        for name in set(payloads)-changed:
            self.assertEqual(candidate[name], original[name], name)
            self.assertEqual(package.pin(candidate[name]), donor['payloads'][name], name)
        self.assertTrue(package.typed_equal(preflight['server_archives'], donor['package_preflight']['server_archives']))
        self.assertTrue(package.typed_equal(preflight['map_startup_component'], donor['map_startup_component']))
        self.assertEqual(len(donor['payloads']), 74)
        self.assertFalse(any(name.endswith('.exe') for name in changed))

    def test_ancestry_is_appended_without_relabelling_original_report_or_native_producers(self):
        donor, commit, runtime, _, _, _, _ = self.actual_fixture()
        old = donor['runtime_manifest']
        self.assertEqual(list(runtime), list(old)+['client_saved_map_reopen'])
        for name in old:
            if name not in ('files', 'repository_commit', 'scope'):
                self.assertTrue(package.typed_equal(runtime[name], old[name]), name)
        self.assertTrue(package.typed_equal(runtime['client_report_loading'], old['client_report_loading']))
        self.assertTrue(package.typed_equal(runtime['client_map_startup'], old['client_map_startup']))
        metadata = runtime['client_saved_map_reopen']
        self.assertEqual(metadata['repository_commit'], commit)
        self.assertEqual(metadata['donor_repository_commit'], package.DONOR_COMMIT)
        self.assertFalse(metadata['publication_provenance']['native_producer_relabelled'])
        self.assertFalse(metadata['physical_kings_row_reopen_validated'])
        self.assertFalse(metadata['native_runtime_booted'])

    def test_wrong_donor_receipt_and_wrong_apk_are_rejected_before_reconstruction(self):
        apk, report = self.actual_inputs()
        with tempfile.TemporaryDirectory() as temporary:
            wrong = Path(temporary)/'wrong'
            wrong.write_bytes(b'wrong')
            for a, r in ((wrong, report), (apk, wrong)):
                with self.subTest(apk=a, report=r), self.assertRaises(ValueError):
                    package.validate_donor(a, r)

    def test_payload_retention_rejects_unknown_missing_or_native_byte_change(self):
        donor, _, _, payloads, _, _, _ = self.actual_fixture()
        for mutation in ('unknown', 'missing', 'native'):
            changed = copy.deepcopy(payloads)
            if mutation == 'unknown': changed['assets/runtime/unreviewed.py'] = package.pin(b'unreviewed')
            if mutation == 'missing': changed.pop(next(iter(changed)))
            if mutation == 'native': changed['assets/runtime/game-package.tar.gz'] = package.pin(b'changed native')
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                package.payload_boundaries(changed, donor)

    def test_missing_or_forged_helper_source_pins_cannot_create_runtime_manifest(self):
        donor, commit, _, _, _, _, _ = self.actual_fixture()
        pins = {Path(name).name: package.builder().file_pin(package.ROOT/name)
            for name in package.GUEST_SOURCE_CHANGES}
        for mutation in ('missing', 'forged', 'unknown'):
            changed = copy.deepcopy(pins)
            if mutation == 'missing': changed.pop(next(iter(changed)))
            if mutation == 'forged': changed[next(iter(changed))] = package.pin(b'forged')
            if mutation == 'unknown': changed['unreviewed.py'] = package.pin(b'unknown')
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                package.verification_manifests(donor, changed, commit)

    def test_retained_contracts_keep_exact_original_nested_suite_source_and_donor_attribution(self):
        donor, _, _, _, _, _, _ = self.actual_fixture()
        qualification.validate_suite_inventory()
        self.assertEqual(len(qualification.RETAINED_CONTRACT_MODULES), 6)
        for name in qualification.RETAINED_CONTRACT_MODULES:
            row = qualification.retained_contract_result(name, donor)
            self.assertFalse(row['tests_executed_in_current_run'])
            self.assertEqual(row['source_repository_commit'], package.DONOR_COMMIT)
            self.assertEqual(row['donor_build_report'], package.DONOR_BUILD)
            self.assertFalse(row['native_producer_relabelled'])
            self.assertTrue(package.typed_equal(row['donor_suite_result'], donor['qualification']['test_suites'][name]))
        for name in ('test_saved_map_startup', 'test_saved_map_postgresql',
                'test_client_report_lifecycle_java', 'test_map_startup_native_contract',
                'test_kings_row_runtime_dependencies', 'test_server_worktree_reuse'):
            self.assertIn(name, qualification.TEST_MODULES)
            self.assertNotIn(name, qualification.RETAINED_CONTRACT_MODULES)

    def test_current_suite_cannot_claim_inherited_execution_skips_wrong_scope_or_count(self):
        name = 'test_saved_map_window_java'
        row = {'tests_run': qualification.current_suite_test_count(name), 'status': 'passed',
            'skipped': 0, 'source_scope': 'current_034_candidate_sources', 'tests_executed_in_current_run': True}
        qualification.validate_current_suite_result(name, row)
        for key, value in (('tests_run', row['tests_run']+1), ('skipped', 1),
                ('source_scope', 'current_033_candidate_sources'), ('tests_executed_in_current_run', False),
                ('status', 'failed')):
            changed = dict(row, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                qualification.validate_current_suite_result(name, changed)

    def test_owner_requires_direct_single_parent_push_marker_and_closed_production_scope(self):
        names = sorted(owner.CLIENT_SAVED_MAP_REOPEN_ALLOWED)
        args = ('push', 'a'*40, 'b'*40, 'a'*40)
        self.assertTrue(owner.client_saved_map_reopen_owned(*args, names))
        self.assertFalse(owner.client_saved_map_reopen_owned(*args,
            sorted(owner.CLIENT_SAVED_MAP_REOPEN_ALLOWED-{owner.CLIENT_SAVED_MAP_REOPEN_MARKER})))
        for extra in ('upstream/ouroboros/Game/src/graphics/gfx.c', 'android/native/client-launcher.c',
                'assets/asset-pack-manifest.json', 'android/guest/native_map_startup_contract.py',
                'tools/android/interactive/build_client_report_loading_apk.py',
                'tools/android/interactive/release-client-report-loading-0.13.33.json', 'docs/unreviewed.md'):
            with self.subTest(extra=extra):
                self.assertFalse(owner.client_saved_map_reopen_owned(*args, names+[extra]))
        for context in (('pull_request','a'*40,'b'*40,'a'*40), ('push','c'*40,'b'*40,'a'*40),
                ('push','a'*40,'b'*40,'a'*40+'\n'+'c'*40), ('push','0'*40,'b'*40,'0'*40)):
            self.assertFalse(owner.client_saved_map_reopen_owned(*context, names))

    def test_final_docs_owner_cannot_authorize_production_changes_or_fabricated_evidence(self):
        context = ('push', 'a'*40, 'b'*40, 'a'*40)
        docs = sorted(owner.CLIENT_SAVED_MAP_REOPEN_DOCS)
        self.assertTrue(owner.client_saved_map_reopen_owned(*context, docs))
        for extra in ('android/guest/character_zoning.py', 'docs/android-evidence/unknown.json'):
            self.assertFalse(owner.client_saved_map_reopen_owned(*context, docs+[extra]))
        self.assertFalse(owner.client_saved_map_reopen_owned(*context,
            sorted(owner.CLIENT_SAVED_MAP_REOPEN_DOCS-{owner.CLIENT_SAVED_MAP_REOPEN_PUBLICATION})))

    def test_every_historical_native_dispatcher_defers_only_exact_successor_owner(self):
        import classify_client_animation_repair_change as animation
        import classify_client_profile_recovery_change as profile
        import classify_client_map_startup_change as startup
        names = sorted(owner.CLIENT_SAVED_MAP_REOPEN_ALLOWED)
        self.assertTrue(animation.historical_repair_owned('push','a'*40,'b'*40,'a'*40,names))
        self.assertFalse(animation.historical_repair_owned('push','a'*40,'b'*40,'a'*40,names+['unknown']))
        for module in (animation, profile, startup):
            with tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary)/'output'
                with patch.dict(os.environ, {'GITHUB_EVENT_NAME':'push','COH_PUSH_BEFORE':'a'*40,
                        'GITHUB_OUTPUT':str(output)}), patch.object(module.subprocess,'check_output',
                        side_effect=['a'*40, 'b'*40, ('\0'.join(names)+'\0').encode()]), \
                        contextlib.redirect_stdout(io.StringIO()):
                    module.main()
                self.assertEqual(output.read_text(), 'legacy_native_required=false\n')

    @staticmethod
    def workflow():
        import yaml
        return yaml.safe_load((package.ROOT/package.WORKFLOW).read_text())

    def test_workflow_requires_strict_sql_original_fixtures_and_signed_then_public_audits(self):
        workflow = self.workflow(); jobs = workflow['jobs']
        self.assertEqual(set(jobs), {'changes', 'apk', 'public-audit'})
        self.assertFalse(workflow['concurrency']['cancel-in-progress'])
        self.assertEqual(jobs['apk']['env']['COH_REQUIRE_SAVED_MAP_PG'], '1')
        self.assertEqual(jobs['apk']['env']['COH_REQUIRE_POSTGRESQL'], '1')
        runs = [step.get('run','') for step in jobs['apk']['steps']]
        qualify = next(run for run in runs if 'qualify_client_saved_map_reopen.py ' in run)
        self.assertIn('--dependency-donor-apk out/native-dependency-030.apk', qualify)
        self.assertIn('--animation-donor-apk out/native-animation-029.apk', qualify)
        self.assertIn('--native-contract-donor-apk out/native-contract-031.apk', qualify)
        self.assertTrue(any('build_client_profile_recovery_apk.py download-donor' in run for run in runs))
        self.assertTrue(any('build_client_animation_repair_apk.py download-donor' in run for run in runs))
        audit = next(run for run in runs if 'build_client_saved_map_reopen_apk.py audit ' in run)
        publish = next(run for run in runs if 'build_client_saved_map_reopen_apk.py publish ' in run)
        self.assertLess(runs.index(audit), runs.index(publish))
        audited_path = shlex.split(audit)[shlex.split(audit).index('--audit-receipt')+1]
        published_path = shlex.split(publish)[shlex.split(publish).index('--audit-receipt')+1]
        self.assertEqual(audited_path, published_path)
        self.assertIn("needs.changes.outputs.publish_enabled == 'true'", jobs['public-audit']['if'])
        for job in jobs.values():
            for step in job['steps']:
                run = step.get('run','')
                self.assertNotIn('package_map_startup_native.py', run)
                self.assertNotIn('package_external_assets.py', run)
                self.assertNotIn('build_client_report_loading_apk.py publish', run)
        public_runs = [step.get('run','') for step in jobs['public-audit']['steps']]
        self.assertTrue(any('download-public' in run for run in public_runs))
        self.assertTrue(any('build_client_saved_map_reopen_apk.py audit ' in run for run in public_runs))

    def test_disabled_qualification_gate_never_accesses_network_or_builds_even_when_publish_enabled(self):
        marker = json.loads((package.ROOT/package.MARKER).read_bytes())
        gate = next(step for step in self.workflow()['jobs']['changes']['steps'] if step.get('id')=='gate')
        lines = gate['run'].splitlines()
        code = '\n'.join(lines[1:-1])
        import urllib.request
        for enabled in (True, False):
            changed = dict(marker, qualification_enabled=False, publish_enabled=enabled)
            prior = Path.cwd()
            with tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary); target = directory/package.MARKER
                target.parent.mkdir(parents=True); target.write_text(json.dumps(changed))
                output = directory/'output'
                try:
                    os.chdir(directory)
                    with patch.dict(os.environ, {'GITHUB_OUTPUT':str(output),'GH_TOKEN':'fixture'}), \
                            patch.object(urllib.request,'urlopen',side_effect=AssertionError('disabled gate network')), \
                            contextlib.redirect_stdout(io.StringIO()):
                        with self.assertRaises(SystemExit) as stopped:
                            exec(compile(code, package.WORKFLOW+' gate', 'exec'), {'__name__':'__workflow_test__'})
                        self.assertEqual(stopped.exception.code, 0)
                finally: os.chdir(prior)
                self.assertEqual(output.read_text(), 'publish_enabled='+str(enabled).lower()+'\nrequired=false\n')

    def test_signed_preflight_requires_exact_actual_candidate_proof(self):
        proof = {'package_preflight': {'server_archives': {'native': 'same'}, 'full_startup': {'status':'passed'}}}
        package.require_signed_preflight(copy.deepcopy(proof['package_preflight']), proof)
        wrong = copy.deepcopy(proof['package_preflight']); wrong['full_startup']['status']='failed'
        with self.assertRaises(ValueError): package.require_signed_preflight(wrong, proof)

    def test_audit_receipt_binds_every_independent_signed_byte_authority_and_disallows_claim_inflation(self):
        donor, commit, runtime, payloads, preflight, _, _ = self.actual_fixture()
        report = {'apk':package.APK_NAME, 'version_name':package.VERSION_NAME,'version_code':package.VERSION_CODE,
            'bytes':123,'sha256':'1'*64,'donor':package.donor_link(),'repository_commit':commit,
            'recompiled_dex':package.pin(b'current dex'),'qualification':{'source_files':{'source.py':package.pin(b'current')}},
            'payloads':payloads,'runtime_manifest_sha256':payloads['assets/runtime/runtime-manifest.json']['sha256'],
            'package_preflight':preflight,'map_startup_component':donor['map_startup_component'],
            'external_asset_pack':donor['external_asset_pack']}
        report_pin, q_pin = package.pin(b'current report'), package.pin(b'current q')
        audit = package.audit_record(report, report_pin, q_pin)
        self.assertFalse(audit['physical_execution_validated'])
        self.assertFalse(audit['live_database_and_saved_character_executed'])
        package.validate_audit_record(audit, report, report_pin, q_pin)
        for key, value in (('native_runtime_booted',True), ('physical_execution_validated',True),
                ('repository_tree','0'*40),('build_report',package.pin(b'other')),
                ('qualification_receipt',package.pin(b'other'))):
            changed = copy.deepcopy(audit); changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                package.validate_audit_record(changed, report, report_pin, q_pin)

    def test_source_identity_refuses_untracked_staged_or_changed_inputs(self):
        with tempfile.TemporaryDirectory(prefix='coh-committed-sources-') as temporary:
            root = Path(temporary)
            subprocess.run(['git', 'init', '--quiet', str(root)], check=True)
            source = root/'source.py'; source.write_bytes(b'committed source\n')
            subprocess.run(['git', 'add', 'source.py'], cwd=root, check=True)
            subprocess.run(['git', '-c', 'user.name=Host Fixture', '-c', 'user.email=fixture@example.invalid',
                'commit', '--quiet', '-m', 'Owned disposable source identity fixture'], cwd=root, check=True)
            commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
            with patch.object(package,'ROOT',root):
                package.require_committed_sources(commit, ['source.py'])
                other = root/'untracked.py'; other.write_bytes(b'uncommitted source\n')
                with self.assertRaises(ValueError):
                    package.require_committed_sources(commit, ['source.py','untracked.py'])
                subprocess.run(['git','add','untracked.py'],cwd=root,check=True)
                with self.assertRaises(ValueError):
                    package.require_committed_sources(commit, ['source.py','untracked.py'])
                source.write_bytes(b'changed current bytes\n')
                with self.assertRaises(ValueError):
                    package.require_committed_sources(commit, ['source.py'])

    def test_saved_map_sql_receipt_requires_all_readonly_fixtures_and_truthful_native_boundary(self):
        import test_saved_map_postgresql as sql
        expected = {'format':1, 'status':'passed', 'scope':sql.SCOPE, 'postgresql_major':16,
            'fixtures':sorted(sql.REQUIRED_POSTGRES_FIXTURES),'sql_transaction_mode':'READ ONLY',
            'fixture_schema_isolated':True,'player_database_accessed':False,
            'native_process_booted':False,'native_client_connected':False,
            'native_save_logout_executed':False,'physical_ayn_thor_validated':False,
            'enhancement_no_mutation_scope':'actual_isolated_postgresql_full_34_field_boosts_rows',
            'boost_fields':list(sql.enhancements.BOOST_FIELDS),
            'generated_boost_template_sha256':sql.enhancements.TEMPLATE_SHA256,
            'shipping_enhancement_capture_changed':False}
        sql.validate_qualification_inventory(expected)
        for key, value in (('fixtures',expected['fixtures'][:-1]),('player_database_accessed',True),
                ('native_process_booted',True),('sql_transaction_mode','READ WRITE'),('postgresql_major',15)):
            changed=copy.deepcopy(expected); changed[key]=value
            with self.subTest(key=key), self.assertRaises((ValueError,RuntimeError)):
                sql.validate_qualification_inventory(changed)


if __name__ == '__main__': unittest.main()
