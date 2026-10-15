"""Exercise the native-only derivative's real extraction and closed boundaries."""
import contextlib
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import build_reopen_startup_repair_apk as package
import test_levelup_ui_repair_package as previous

COMMIT = 'a'*40
pin, replace_member = previous.pin, previous.replace_member


@contextlib.contextmanager
def candidate(folder):
    with previous.candidate(folder) as values:
        apk = values[0]; donor = copy.deepcopy(values[2])
        donor.update(payloads=copy.deepcopy(values[5]), runtime_manifest=copy.deepcopy(values[6]),
            server_payload_extraction_preflight=copy.deepcopy(values[7]), native_dbserver=copy.deepcopy(values[9]))
        with zipfile.ZipFile(apk) as archive:
            donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
        (folder/'android/guest'/package.GUEST).write_bytes(b'new-typed-native-witness')
        native_dir = folder/'startup-repair-native'; native_dir.mkdir()
        (native_dir/'DbServer.exe').write_bytes(b'new-thread-name-formatter-and-retained-sql-fixes')
        native = {'format': 1, 'repository_commit': COMMIT, 'files': {'DbServer.exe': {'size': 48, 'sha256': pin((native_dir/'DbServer.exe').read_bytes())['sha256']}}}
        (native_dir/'startup-dbserver-manifest.json').write_bytes(package.shared.encoded(native))
        with mock.patch.object(package, 'ROOT', folder), mock.patch.object(package, 'current_sources', return_value={}), \
                mock.patch.object(package, 'validate_native', return_value=native):
            runtime, payloads, preflight = package.extract_and_repair(apk, donor, folder/'native-repair-files', COMMIT, native_dir)
            output = folder/'native-repair.apk'
            with zipfile.ZipFile(output, 'w') as archive, zipfile.ZipFile(apk) as original:
                for name in payloads: archive.write(folder/'native-repair-files'/name, name)
                for name in ('classes.dex', 'resources.arsc', 'res/drawable/ic_coh_client.xml'): archive.writestr(name, original.read(name))
                archive.writestr('AndroidManifest.xml', b'version-only-update')
            yield output, apk, donor, payloads, runtime, preflight, native_dir, native


def qualification():
    contract = package.module('reopen_test_qualification', package.ROOT/package.QUALIFICATION_SCRIPT)
    return {'format': 1, 'status': 'passed', 'scope': package.QUALIFICATION_SCOPE, 'repository_commit': COMMIT,
        'donor': package.donor_link(), 'checks': {name: True for name in package.CHECKS},
        'native_dbserver_compiled_in_current_run': True, 'native_dbserver_package_reused': False,
        **{name: False for name in ('physical_reopen_validated', 'physical_gameplay_validated', 'physical_client_timing_validated',
            'physical_visual_assets_validated', 'native_client_recompiled', 'native_mapserver_recompiled', 'java_or_dex_recompiled', 'asset_reimport_required')},
        'test_suites': {name: {'status': 'passed', 'skipped': 0, 'tests_run': 1} for name in contract.TEST_MODULES},
        'tests_run': len(contract.TEST_MODULES), 'check_suites': copy.deepcopy(contract.CHECK_SUITES),
        'source_files': {name: pin(b'source') for name in package.SOURCE_FILES},
        'startup_thread_name_fixtures': sorted(package.module('startup_test_fixture', package.ROOT/'tools/android/interactive/test_reopen_dbserver_thread_name.py').REQUIRED_THREAD_NAME_FIXTURES),
        'postgresql_emission_fixtures': ['cancelled_child_deletion_commits', 'delete_insert_replacement_commits', 'duplicate_insert_23505_rollback'],
        'postgresql_levelup_fixtures': sorted(package.prior.levelup_postgresql_fixtures())}


class ReopenStartupPackagingTests(unittest.TestCase):
    def verify(self, values):
        return package.verify_derivative(values[0], values[2], values[3], COMMIT, values[6])

    def test_version_28_and_exact_public_donor_identity(self):
        self.assertEqual((package.VERSION_NAME, package.VERSION_CODE), ('0.13.13', 28))
        self.assertEqual(package.donor_link()['run_id'], 37315299321)
        self.assertEqual(package.DONOR_APK['sha256'], 'ca692d986d7f8bf50d11be03348f07c436e7f3f1b6c5fab83e8ebe2bc932e749')
        self.assertEqual((len(package.REPLACED_PAYLOADS), len(package.UPDATES)), (5, 3))

    def test_real_extraction_conserves_all72_payloads_except5_owned_native_binding_payloads(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            self.assertEqual(self.verify(values), values[4])
            self.assertEqual(len(values[3]), 72)
            self.assertEqual(values[5], values[2]['server_payload_extraction_preflight'])
            with zipfile.ZipFile(values[0]) as current, zipfile.ZipFile(values[1]) as donor:
                for name in set(values[3])-package.REPLACED_PAYLOADS:
                    self.assertEqual(current.read(name), donor.read(name), name)
                for name in ('classes.dex', 'resources.arsc', 'res/drawable/ic_coh_client.xml'):
                    self.assertEqual(current.read(name), donor.read(name))
            self.assertEqual(values[4]['levelup_ui_repair'], values[2]['runtime_manifest']['levelup_ui_repair'])
            self.assertTrue(values[4]['reopen_startup_repair']['all_published_ui_resources_retained'])

    def test_ui_game_mapserver_dlls_caches_training_helper_and_graphics_cannot_change(self):
        names = ('client-visual-assets.zip', 'client-visual-manifest.json', 'client-runtime.zip', 'game-package.tar.gz',
            'dbserver-package.tar.gz', 'dbserver-schema.tar.gz', 'server-caches.zip', 'client-caches.zip',
            'atlas-world-supplement.zip', 'character-avatar-defaults.zip', 'native_training_save.py',
            'client_interactive_diagnostic.py', 'client_visual_assets.py', 'texture_header_index.py')
        for name in names:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                member = 'assets/runtime/'+name; replace_member(values[0], member, b'foreign'); values[3][member] = pin(b'foreign')
                with self.assertRaisesRegex(ValueError, 'payload boundaries'): self.verify(values)

    def test_native_bytes_and_authored_witness_must_match_actual_qualified_inputs(self):
        for name in package.UPDATES:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                member = 'assets/runtime/'+name; replace_member(values[0], member, b'foreign'); values[3][member] = pin(b'foreign')
                with self.assertRaisesRegex(ValueError, 'Authored guest|Source-bound native'): self.verify(values)

    def test_android_shell_unknown_members_and_manifest_history_mutations_are_refused(self):
        for name in ('classes.dex', 'resources.arsc', 'res/drawable/ic_coh_client.xml', 'assets/runtime/foreign.py'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                if name.endswith('foreign.py'):
                    with zipfile.ZipFile(values[0], 'a') as archive: archive.writestr(name, b'foreign')
                else: replace_member(values[0], name, b'foreign')
                with self.assertRaises(ValueError): self.verify(values)
        for key in ('levelup_ui_repair', 'task_gate_required', 'startup_only_reopen', 'client_asset_closure'):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                runtime = copy.deepcopy(values[4]); runtime[key] = 'foreign'; raw = package.shared.encoded(runtime)
                member = 'assets/runtime/runtime-manifest.json'; replace_member(values[0], member, raw); values[3][member] = pin(raw)
                with self.assertRaisesRegex(ValueError, 'verification manifests'): self.verify(values)

    def test_no_added_deleted_or_unchanged_dbserver_payload_is_permitted(self):
        for mutation in ('add', 'delete', 'unchanged'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                if mutation == 'add': values[3]['assets/runtime/foreign.py'] = pin(b'foreign')
                elif mutation == 'delete': values[3].pop('assets/runtime/native_training_save.py')
                else: values[3]['assets/runtime/startup-dbserver.exe'] = values[2]['payloads']['assets/runtime/startup-dbserver.exe']
                with self.assertRaisesRegex(ValueError, 'payload boundaries'): self.verify(values)

    def test_native_ancestry_cannot_be_relabelled_or_failing_binary_reused(self):
        fields = ('role', 'build_input', 'startup_bundle_build_input', 'retained_normal_files',
            'base_package_manifest_sha256', 'base_normal_executable', 'base_startup_executable',
            'base_startup_bundle_executable', 'base_normal_cmake_cache_sha256')
        old = {name: {'frozen': name} for name in fields}; old['files'] = {'DbServer.exe': pin(b'old')}
        native = copy.deepcopy(old); native['files'] = {'DbServer.exe': pin(b'new')}
        producer = mock.Mock(); producer.validate_package.return_value = native
        with mock.patch.object(package.prior, 'native_builder', return_value=producer):
            self.assertEqual(package.validate_native(Path('native'), COMMIT, {'native_dbserver': old}), native)
            for field in fields+('files',):
                producer.validate_package.return_value = copy.deepcopy(native)
                producer.validate_package.return_value[field] = old[field] if field == 'files' else {'foreign': 1}
                with self.subTest(field=field), self.assertRaises(ValueError): package.validate_native(Path('native'), COMMIT, {'native_dbserver': old})

    def test_guest_witness_allows_only_existing_function_and_rejects_other_ast_edits(self):
        old = b'import json\nVERSION=1\ndef levelup_ui_repair_build_input(a,b):\n return {"hash":"old"}\ndef unchanged():\n return 1\n'
        new = old.replace(b'"old"', b'"new"')
        self.assertEqual(package.validate_guest_delta(old, new)['changed_functions'], ['levelup_ui_repair_build_input'])
        for bad in (old, new+b'\nimport foreign\n', new.replace(b'VERSION=1', b'VERSION=2'), new.replace(b'return 1', b'return 2')):
            with self.assertRaises(ValueError): package.validate_guest_delta(old, bad)

    def test_actual_public_saved_character_helper_delta_is_only_the_native_witness(self):
        candidates = (package.ROOT/'out/reopen-donor'/package.DONOR_APK_NAME,
            package.ROOT/'out/ci01312/public'/package.DONOR_APK_NAME)
        donor = next((path for path in candidates if path.is_file()), candidates[0])
        self.assertTrue(donor.is_file(), 'Exact public0.13.12 donor must be available')
        with zipfile.ZipFile(donor) as archive: old = archive.read('assets/runtime/'+package.GUEST)
        self.assertTrue(package.validate_guest_delta(old, (package.ROOT/'android/guest'/package.GUEST).read_bytes())['all_other_ast_nodes_retained'])

    def test_qualification_requires_complete_suites_source_pins_current_native_and_all_realpg_fixtures(self):
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), mock.patch.object(base, 'checked_file'):
            self.assertEqual(package.validate_qualification(qualification(), COMMIT)['status'], 'passed')
            for mutation in ('missing', 'skip', 'fail', 'count', 'reused', 'not_current', 'physical', 'java', 'pg', 'source', 'formatter'):
                value = qualification(); first = next(iter(value['test_suites']))
                if mutation == 'missing': value['test_suites'].pop(first)
                elif mutation == 'skip': value['test_suites'][first]['skipped'] = 1
                elif mutation == 'fail': value['test_suites'][first]['status'] = 'failed'
                elif mutation == 'count': value['tests_run'] += 1
                elif mutation == 'reused': value['native_dbserver_package_reused'] = True
                elif mutation == 'not_current': value['native_dbserver_compiled_in_current_run'] = False
                elif mutation == 'physical': value['physical_reopen_validated'] = True
                elif mutation == 'java': value['java_or_dex_recompiled'] = True
                elif mutation == 'pg': value['postgresql_levelup_fixtures'] = []
                elif mutation == 'formatter': value['startup_thread_name_fixtures'] = []
                else: value['source_files'].pop(next(iter(value['source_files'])))
                with self.subTest(mutation=mutation), self.assertRaises(ValueError): package.validate_qualification(value, COMMIT)

    def test_previous_release_is_never_replaced(self):
        api = mock.Mock(); api.request.return_value = {'id': 1}
        assets = tuple(Path(name) for name in (package.APK_NAME, package.APK_NAME+'.sha256', package.NOTES_NAME))
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), mock.patch.object(base, 'checked_file'):
            with self.assertRaisesRegex(ValueError, 'Existing release'): package.publish_release(api, {'repository_commit': COMMIT}, assets, 'notes')
        self.assertFalse(any(call.kwargs.get('method') in ('POST', 'PATCH') for call in api.request.call_args_list))

    def test_workflow_compiles_win32_fixture_and_never_rediscovers_or_materializes_ui(self):
        source = (package.ROOT/package.WORKFLOW).read_text()
        self.assertIn('vcvars32.bat', source)
        self.assertIn('test_reopen_dbserver_thread_name.py --require-windows', source)
        self.assertIn('coh-levelup-ui-repair-packaging-evidence', source)
        self.assertIn('run-id: 37315299321', source)
        self.assertIn('--target DbServer', source)
        self.assertIn('--output out/reopen-startup-repair/'+package.APK_NAME, source)
        for forbidden in ('discover_client_ui_repair_assets.py', 'prepare_client_ui_repair_assets.py', 'coh-levelup-ui-repair-assets'):
            self.assertNotIn(forbidden, source)
        for sdk in ('35.0.0', 'android-35/android.jar', 'coh-client-interactive.jks'):
            self.assertIn(sdk, source)


if __name__ == '__main__': unittest.main(verbosity=2)
