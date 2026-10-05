"""Exercise real derivative extraction and strict nested retention boundaries."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import build_levelup_ui_repair_apk as package
import test_client_asset_closure_package as previous

COMMIT = 'a'*40
pin, replace_member = previous.pin, previous.replace_member


def qualification():
    contract = package.module('levelup_test_qualification', package.ROOT/package.QUALIFICATION_SCRIPT)
    value = previous.qualification()
    value.update(scope=package.QUALIFICATION_SCOPE, retained_runtime_repository_commit=package.DONOR_COMMIT,
        donor_apk_sha256=package.DONOR_APK['sha256'], native_client_recompiled=False,
        native_dbserver_recompiled=True, native_dbserver_compiled_in_current_run=True,
        native_dbserver_package_reused=False, tests_run=len(contract.TEST_MODULES),
        checks={name: True for name in package.CHECKS},
        source_files={name: pin(b'source') for name in package.SOURCE_FILES},
        postgresql_levelup_fixtures=sorted(package.levelup_postgresql_fixtures()),
        check_suites=copy.deepcopy(contract.CHECK_SUITES),
        test_suites={name: {'tests_run': 1, 'status': 'passed', 'skipped': 0} for name in contract.TEST_MODULES})
    return value


@contextlib.contextmanager
def candidate(folder):
    with previous.candidate(folder) as values:
        output, _, old, directory, old_visual, payloads, runtime, preflight = values
        apk = folder/'accepted.apk'; output.rename(apk)
        donor = copy.deepcopy(old)
        donor.update(payloads=payloads, runtime_manifest=runtime, server_payload_extraction_preflight=preflight)
        with zipfile.ZipFile(apk) as archive:
            donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
            with zipfile.ZipFile(io.BytesIO(archive.read('assets/runtime/client-runtime.zip'))) as client:
                donor['_native_client_manifest'] = json.loads(client.read('client-package.json'))
                donor['_client_members'] = package.startup.client_member_pins(client)
        donor['_visual_manifest'] = copy.deepcopy(old_visual['manifest'])
    for name in package.HELPERS|package.ADDED_HELPERS:
        (folder/'android/guest'/name).write_bytes(('authored-repair-'+name).encode())
    (directory/'client-visual-assets.zip').write_bytes(b'old-compressed-streams-plus-ui')
    (directory/'client-visual-manifest.json').write_bytes(b'{"ui":"qualified"}')
    visual = {'format': 1, 'manifest': {'files': dict(donor['_visual_manifest']['files'],
        **{'data/texture_library/ui/new.texture': pin(b'new-ui')}),
        'visual_extension': {'preserved_world_geometry_proof': {}}},
        'files': {name: package.builder().file_pin(directory/name) for name in package.VISUAL_ASSETS}}
    native_directory = folder/'repair-dbserver'; native_directory.mkdir()
    raw = b'physical-empty-child-row-read-witness'; (native_directory/'DbServer.exe').write_bytes(raw)
    native = {'format': 1, 'repository_commit': COMMIT, 'files': {'DbServer.exe': {'size': len(raw), 'sha256': pin(raw)['sha256']}}}
    (native_directory/'startup-dbserver-manifest.json').write_bytes(package.shared.encoded(native))
    original_module = package.module
    def fixture_module(name, path):
        return mock.Mock() if name == 'followup_world_geometry_verifier' else original_module(name, path)
    with mock.patch.object(package, 'ROOT', folder), mock.patch.object(package, 'current_sources', return_value={}), \
            mock.patch.object(package, 'validate_visual_package', return_value=visual), \
            mock.patch.object(package, 'validate_visual_superset'), \
            mock.patch.object(package, 'verify_visual_streams'), \
            mock.patch.object(package, 'validate_native', return_value=native), \
            mock.patch.object(package, 'module', side_effect=fixture_module):
        runtime, payloads, _, preflight = package.extract_and_repair(apk, donor,
            folder/'repair-files', COMMIT, directory, native_directory)
        output = folder/'repair.apk'
        with zipfile.ZipFile(output, 'w') as archive, zipfile.ZipFile(apk) as original:
            for name in payloads: archive.write(folder/'repair-files'/name, name)
            for name in ('classes.dex', 'resources.arsc', 'res/drawable/ic_coh_client.xml'):
                archive.writestr(name, original.read(name))
            archive.writestr('AndroidManifest.xml', b'version-only-update')
        yield output, apk, donor, directory, visual, payloads, runtime, preflight, native_directory, native


class LevelupUiRepairPackagingTests(unittest.TestCase):
    def verify(self, values):
        output, _, donor, directory, _, payloads, _, _, native_directory, _ = values
        return package.verify_derivative(output, donor, payloads, COMMIT, directory, native_directory)

    def test_only_nine_owned_payloads_change_and_the_entire_client_android_and_server_history_survives(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, apk, donor, _, visual, payloads, runtime, preflight, _, _ = values
            self.assertEqual(self.verify(values), visual)
            self.assertEqual((len(payloads), len(package.REPLACED_PAYLOADS)), (72, 9))
            self.assertEqual({name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]}, package.REPLACED_PAYLOADS)
            self.assertEqual(set(payloads)-set(donor['payloads']), package.ADDED_PAYLOADS)
            self.assertEqual(preflight, donor['server_payload_extraction_preflight'])
            self.assertEqual(set(runtime['files']), set(donor['runtime_manifest']['files'])|package.ADDED_HELPERS)
            self.assertEqual(len(runtime['files']), 65)
            self.assertTrue(runtime['levelup_ui_repair']['native_dbserver_recompiled'])
            self.assertFalse(runtime['levelup_ui_repair']['native_client_recompiled'])
            for name in ('client_visual', 'client_loading', 'client_streaming', 'client_asset_closure'):
                self.assertEqual(runtime[name], donor['runtime_manifest'][name])
            with zipfile.ZipFile(output) as current, zipfile.ZipFile(apk) as original:
                for name in set(payloads)-package.REPLACED_PAYLOADS-package.ADDED_PAYLOADS:
                    self.assertEqual(current.read(name), original.read(name), name)
                self.assertEqual(current.read('classes.dex'), original.read('classes.dex'))
                self.assertEqual(current.read('assets/runtime/client-runtime.zip'), original.read('assets/runtime/client-runtime.zip'))

    def test_no_other_server_cache_schema_world_avatar_graphics_or_helper_can_change(self):
        for name in ('game-package.tar.gz', 'dbserver-package.tar.gz', 'dbserver-schema.tar.gz',
                'client-runtime.zip', 'server-caches.zip', 'client-caches.zip', 'server-animations.pigg',
                'atlas-world-supplement.zip', 'character-avatar-defaults.zip', 'native-responsiveness.json',
                'native_responsiveness_contract.py', 'texture_header_index.py', 'client_startup_diagnostic.py',
                'character_server_data_cache.py', 'client_animation_package.py'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                member = 'assets/runtime/'+name; replace_member(values[0], member, b'forged'); values[5][member] = pin(b'forged')
                with self.assertRaisesRegex(ValueError, 'payload boundaries'): self.verify(values)

    def test_retained_android_shell_native_libraries_and_unknown_members_are_rejected(self):
        for name in ('classes.dex', 'resources.arsc', next(iter(package.builder().NATIVE_MEMBERS)), 'assets/runtime/foreign.py'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                if name == 'assets/runtime/foreign.py':
                    with zipfile.ZipFile(values[0], 'a') as archive: archive.writestr(name, b'forged')
                else: replace_member(values[0], name, b'forged')
                if name in values[5]: values[5][name] = pin(b'forged')
                with self.assertRaises(ValueError): self.verify(values)

    def test_authored_helpers_ui_and_dbserver_bytes_must_match_the_qualified_producers(self):
        for name in package.HELPERS|package.ADDED_HELPERS|package.VISUAL_ASSETS|package.NATIVE_ASSETS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                member = 'assets/runtime/'+name; replace_member(values[0], member, b'forged'); values[5][member] = pin(b'forged')
                with self.assertRaisesRegex(ValueError, 'Authored repair helper|Verified UI asset|DbServer supplement'): self.verify(values)

    def test_all_retained_runtime_history_and_save_requirement_flags_are_conserved(self):
        for key in ('client_visual', 'client_loading', 'client_streaming', 'client_asset_closure', 'startup_only_reopen', 'task_gate_required'):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                changed = copy.deepcopy(values[6]); changed[key] = 'forged'; raw = package.shared.encoded(changed)
                member = 'assets/runtime/runtime-manifest.json'; replace_member(values[0], member, raw); values[5][member] = pin(raw)
                with self.assertRaisesRegex(ValueError, 'manifest changed'): self.verify(values)

    def test_ui_superset_requires_every_9490_leaf_and_an_actual_addition(self):
        leaves = {'data/texture_library/'+str(index)+'.texture': pin(b'old') for index in range(9490)}
        old = {'_visual_manifest': {'files': leaves, 'files_sha256': 'f'*64}}
        current = dict(leaves, **{'data/texture_library/ui/new.texture': pin(b'ui')})
        self.assertEqual(package.validate_visual_superset(old, {'manifest': {'files': current}}),
            {'retained_files': 9490, 'added_files': 1, 'added_bytes': 2, 'previous_files_sha256': 'f'*64})
        for changed in (leaves, dict(current, **{next(iter(leaves)): pin(b'foreign')}), dict(list(current.items())[1:])):
            with self.assertRaisesRegex(ValueError, 'Every immediate'): package.validate_visual_superset(old, {'manifest': {'files': changed}})

    def test_all_9490_original_compressed_streams_and_metadata_survive_append_but_recompression_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); target = folder/'client-visual-assets.zip'
            with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
                for index in range(9490): archive.writestr('data/texture_library/'+str(index)+'.texture', b'retained-'*64)
            with zipfile.ZipFile(target) as archive:
                pins = {row.filename: package.visual_stream_pin(archive, row) for row in archive.infolist()}
            donor = {'_visual_stream_pins': pins, '_visual_manifest': {'files': dict.fromkeys(pins)}}
            with zipfile.ZipFile(target, 'a') as archive: archive.writestr('data/texture_library/ui/new.texture', b'new')
            self.assertEqual(package.verify_visual_streams(None, folder, donor),
                {'retained_compressed_streams': 9490, 'all_streams_byte_identical': True})
            with zipfile.ZipFile(target) as archive: raw = {row.filename: archive.read(row) for row in archive.infolist()}
            with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
                for name, content in raw.items(): archive.writestr(name, content)
            with self.assertRaisesRegex(ValueError, 'compressed visual stream changed'):
                package.verify_visual_streams(None, folder, donor)

    def test_nested_client_rejects_game_dll_and_provenance_changes(self):
        for name in ('CityOfHeroes.exe', 'fixture-0.dll', 'client-package.json', 'extra.dll'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                with zipfile.ZipFile(values[1]) as apk:
                    source = io.BytesIO(apk.read('assets/runtime/client-runtime.zip'))
                if name == 'extra.dll':
                    with zipfile.ZipFile(source, 'a') as archive: archive.writestr(name, b'forged')
                else: replace_member(source, name, b'forged')
                with self.assertRaisesRegex(ValueError, 'Retained Game'): package.verify_client_archive(source, values[2])

    def test_new_native_producer_retains_both_previous_save_layers_and_dependency_ancestry(self):
        previous_native = {'build_input': {'retained': 1}, 'startup_bundle_build_input': {'retained': 2},
            **{name: 'retained' for name in ('base_package_manifest_sha256', 'base_normal_executable',
                'retained_normal_files', 'base_normal_cmake_cache_sha256', 'base_startup_executable')}}
        donor = {'native_dbserver': previous_native, 'payloads': {'assets/runtime/startup-dbserver.exe': pin(b'old')}}
        native = dict(previous_native, repository_commit=COMMIT, base_startup_bundle_executable=pin(b'old'),
            files={'DbServer.exe': {'sha256': pin(b'new')['sha256']}})
        producer = mock.Mock(); producer.validate_package.return_value = native
        with mock.patch.object(package, 'native_builder', return_value=producer):
            self.assertEqual(package.validate_native(Path('native'), COMMIT, donor), native)
            for field in set(previous_native)|{'base_startup_bundle_executable'}:
                changed = copy.deepcopy(native); changed[field] = {}; producer.validate_package.return_value = changed
                with self.subTest(field=field), self.assertRaises(ValueError): package.validate_native(Path('native'), COMMIT, donor)

    def test_qualification_requires_complete_current_dbserver_pg_fixtures_and_every_suite(self):
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), mock.patch.object(base, 'checked_file'):
            self.assertEqual(package.validate_qualification(qualification(), COMMIT)['status'], 'passed')
            for mutation in ('missing', 'skip', 'fail', 'count', 'reused', 'not_current', 'server', 'game', 'java', 'pg'):
                receipt = qualification(); name = next(iter(receipt['test_suites']))
                if mutation == 'missing': receipt['test_suites'].pop(name)
                elif mutation == 'skip': receipt['test_suites'][name]['skipped'] = 1
                elif mutation == 'fail': receipt['test_suites'][name]['status'] = 'failed'
                elif mutation == 'count': receipt['tests_run'] += 1
                elif mutation == 'reused': receipt['native_dbserver_package_reused'] = True
                elif mutation == 'not_current': receipt['native_dbserver_compiled_in_current_run'] = False
                elif mutation == 'server': receipt['native_mapserver_recompiled'] = True
                elif mutation == 'game': receipt['native_client_recompiled'] = True
                elif mutation == 'pg': receipt['postgresql_levelup_fixtures'] = []
                else: receipt['changed_java_sources'] = ['foreign.java']
                with self.subTest(mutation=mutation), self.assertRaises(ValueError): package.validate_qualification(receipt, COMMIT)

    def test_guest_ast_delta_retains_all_other_code_and_exact_ancestry_constants(self):
        path = next((p for p in (package.ROOT/'out/donor01311'/package.DONOR_APK_NAME,
            package.ROOT/'out/donor'/package.DONOR_APK_NAME) if p.is_file()), package.ROOT/'out/donor'/package.DONOR_APK_NAME)
        self.assertTrue(path.is_file(), 'Exact public donor must be available for qualification')
        with zipfile.ZipFile(path) as donor:
            for name in package.HELPERS-{'client_visual_assets.py'}:
                old = donor.read('assets/runtime/'+name); new = (package.ROOT/'android/guest'/name).read_bytes()
                self.assertTrue(package.validate_guest_delta(name, old, new)['all_other_ast_nodes_retained'])
                for forged in (new+b'\nimport foreign\n', new.replace(b'import json', b'import foreign', 1)):
                    with self.subTest(name=name), self.assertRaises(ValueError): package.validate_guest_delta(name, old, forged)

    def test_training_evidence_cannot_use_modified_native_or_power_definition_producers(self):
        pins = package.RETAINED_REWARD_SOURCE_FILES | package.RETAINED_TRAINING_SOURCE_FILES
        first = next(iter(pins))
        donor = {'qualification': {'source_files': {first: pins[first]}}}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in pins:
                target = root/name; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((package.ROOT/name).read_bytes())
            with mock.patch.object(package, 'ROOT', root):
                self.assertEqual(set(package.validate_retained_native_sources(donor)), set(pins))
                for name in package.RETAINED_TRAINING_SOURCE_FILES:
                    target = root/name; original = target.read_bytes()
                    target.write_bytes(original+b'\n')
                    with self.subTest(name=name), self.assertRaises(ValueError):
                        package.validate_retained_native_sources(donor)
                    target.write_bytes(original)

    def test_existing_release_is_never_overwritten(self):
        api = mock.Mock(); api.request.return_value = {'object': {'type': 'commit', 'sha': COMMIT}}
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk = folder/package.APK_NAME; apk.write_bytes(b'apk')
            with self.assertRaisesRegex(ValueError, 'never replaced'):
                package.publish_release(api, {'repository_commit': COMMIT, **pin(b'apk')},
                    (apk, folder/(package.APK_NAME+'.sha256'), folder/package.NOTES_NAME), 'reviewed')

    def test_workflow_uses_current_dbserver_only_retains_exact_donor_and_requires_real_pg_qualification(self):
        text = (package.ROOT/package.WORKFLOW).read_text()
        self.assertEqual((package.VERSION_NAME, package.VERSION_CODE), ('0.13.12', 27))
        self.assertEqual(package.DONOR_COMMIT, 'a5ff474674393e898f9a5d4b3ad29ae51dd25a2a')
        self.assertIn('run-id: '+str(package.DONOR_RUN_ID), text)
        self.assertIn('name: coh-client-startup-followup-packaging-evidence', text)
        self.assertIn('--target DbServer', text)
        self.assertNotIn('--target Game', text); self.assertNotIn('--target MapServer', text)
        self.assertIn('needs: [changes, dbserver, assets, qualify]', text)
        self.assertIn("COH_REQUIRE_STARTUP_BUNDLE_PG: '1'", text)
        self.assertIn("COH_REQUIRE_LEVELUP_UI_REPAIR_PG: '1'", text)
        self.assertNotIn('d8.jar', text); self.assertNotIn('javac', text)
        self.assertIn('out/levelup-ui-repair/'+package.APK_NAME, text)
