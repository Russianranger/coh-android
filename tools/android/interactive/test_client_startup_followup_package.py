"""Real APK and nested client conservation after the immediate .10 donor.

Only external asset/native production is substituted in the small APK fixture;
all extraction, payload pins, history, twenty DLLs, DEX and server checks run.
Separate producer/contract suites bind the real staged source and Game receipt.
"""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import build_client_startup_followup_apk as package
import test_client_asset_closure_package as previous

COMMIT = 'a'*40
pin, replace_member = previous.pin, previous.replace_member


def qualification():
    contract = package.module('followup_test_qualification', package.ROOT/package.QUALIFICATION_SCRIPT)
    value = previous.qualification()
    value.update(scope=package.QUALIFICATION_SCOPE, retained_runtime_repository_commit=package.DONOR_COMMIT,
        donor_apk_sha256=package.DONOR_APK['sha256'], native_client_recompiled=True,
        native_client_compiled_in_current_run=True, native_client_package_reused=False,
        tests_run=len(contract.TEST_MODULES), checks={name: True for name in package.CHECKS},
        source_files={name: pin(b'source') for name in package.SOURCE_FILES},
        check_suites=copy.deepcopy(contract.CHECK_SUITES),
        test_suites={name: {'tests_run': 1, 'status': 'passed', 'skipped': 0} for name in contract.TEST_MODULES})
    return value


@contextlib.contextmanager
def candidate(folder):
    with previous.candidate(folder) as values:
        output, _, old, directory, old_visual, payloads, runtime, preflight = values
        apk = folder/'accepted-asset-closure.apk'; output.rename(apk)
        donor = copy.deepcopy(old)
        donor.update(payloads=payloads, runtime_manifest=runtime,
            server_payload_extraction_preflight=preflight)
        with zipfile.ZipFile(apk) as archive:
            donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
            with zipfile.ZipFile(io.BytesIO(archive.read('assets/runtime/client-runtime.zip'))) as client:
                donor['_native_client_manifest'] = json.loads(client.read('client-package.json'))
                donor['_client_members'] = package.startup.client_member_pins(client)
        donor['_visual_manifest'] = copy.deepcopy(old_visual['manifest'])
    for name in package.HELPERS:
        (folder/'android/guest'/name).write_bytes(('authored-followup-'+name).encode())
    (directory/'client-visual-assets.zip').write_bytes(b'exact-prior-streams-plus-appearance')
    (directory/'client-visual-manifest.json').write_bytes(b'{"appearance":"qualified"}')
    visual = {'format': 1, 'manifest': {'files': dict(donor['_visual_manifest']['files'],
        **{'data/player_library/new_head.geo': pin(b'new-head')}),
        'visual_extension': {'preserved_world_geometry_proof': {}}},
        'files': {name: package.builder().file_pin(directory/name) for name in package.VISUAL_ASSETS}}
    native_directory = folder/'followup-native'; native_directory.mkdir()
    raw = b'opt-in-metadata-preload-Game'; (native_directory/'CityOfHeroes.exe').write_bytes(raw)
    record = dict(donor['_native_client_manifest']['files']['CityOfHeroes.exe'],
        size=len(raw), sha256=pin(raw)['sha256'])
    native = {'format': 1, 'repository_commit': COMMIT, 'files': {'CityOfHeroes.exe': record},
        'base_client_executable': donor['native_client_loading']['files']['CityOfHeroes.exe'],
        'retained_source_inputs': donor['native_responsiveness']['build_inputs'],
        'schema_sources_sha256': donor['native_responsiveness']['retained_cache']['schema_sources_sha256'],
        'build_targets': ['Game'], 'replacement_scope': 'CityOfHeroes.exe_only',
        'retained_native_dependencies_changed': False}
    # Production typed source receipt validation is covered by the real native
    # contract suite. This fixture still executes every nested byte/inventory check.
    original_module = package.module
    def fixture_module(name, path):
        return mock.Mock() if name == 'followup_world_geometry_verifier' else original_module(name, path)
    with mock.patch.object(package, 'ROOT', folder), mock.patch.object(package, 'current_sources', return_value={}), \
            mock.patch.object(package, 'validate_visual_package', return_value=visual), \
            mock.patch.object(package, 'validate_visual_superset'), \
            mock.patch.object(package, 'verify_visual_streams'), \
            mock.patch.object(package, 'validate_native', return_value=native), \
            mock.patch.object(package, 'module', side_effect=fixture_module), \
            mock.patch.object(package.shared.native_contract, 'client_contract'):
        runtime, payloads, _, preflight = package.extract_and_repair(apk, donor,
            folder/'followup-files', COMMIT, directory, native_directory)
        output = folder/'followup.apk'
        with zipfile.ZipFile(output, 'w') as archive, zipfile.ZipFile(apk) as original:
            for name in payloads: archive.write(folder/'followup-files'/name, name)
            for name in ('classes.dex', 'resources.arsc', 'res/drawable/ic_coh_client.xml'):
                archive.writestr(name, original.read(name))
            archive.writestr('AndroidManifest.xml', b'version-only-update')
        yield output, apk, donor, directory, visual, payloads, runtime, preflight, native_directory, native


class ClientStartupFollowupPackagingTests(unittest.TestCase):
    def verify(self, values):
        output, _, donor, directory, _, payloads, _, _, native_directory, _ = values
        return package.verify_derivative(output, donor, payloads, COMMIT, directory, native_directory)

    def test_71_payloads_and_all_server_dex_cache_avatar_and_history_bytes_are_exact(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, apk, donor, _, visual, payloads, runtime, preflight, _, _ = values
            self.assertEqual(self.verify(values), visual)
            self.assertEqual(len(payloads), 71); self.assertEqual(len(package.REPLACED_PAYLOADS), 9)
            self.assertEqual({name for name in payloads if payloads[name] != donor['payloads'][name]}, package.REPLACED_PAYLOADS)
            self.assertEqual(preflight, donor['server_payload_extraction_preflight'])
            self.assertEqual(set(runtime['files']), set(donor['runtime_manifest']['files']))
            self.assertEqual(len(runtime['files']), 64)
            for name in ('client_visual', 'client_loading', 'client_streaming', 'client_asset_closure'):
                self.assertEqual(runtime[name], donor['runtime_manifest'][name])
            self.assertTrue(runtime['client_startup_followup']['native_client_recompiled'])
            with zipfile.ZipFile(output) as current, zipfile.ZipFile(apk) as original:
                for name in set(payloads)-package.REPLACED_PAYLOADS:
                    self.assertEqual(current.read(name), original.read(name), name)
                self.assertEqual(current.read('classes.dex'), original.read('classes.dex'))
                with zipfile.ZipFile(io.BytesIO(current.read('assets/runtime/client-runtime.zip'))) as client:
                    self.assertEqual(len(client.infolist()), 22)
                    for name, expected in donor['_client_members'].items():
                        if name not in ('CityOfHeroes.exe', 'client-package.json'):
                            self.assertEqual(pin(client.read(name)), expected)

    def test_server_cache_import_save_and_unreviewed_helper_forgeries_are_rejected(self):
        for name in ('game-package.tar.gz', 'dbserver-package.tar.gz', 'dbserver-schema.tar.gz',
                'startup-dbserver.exe', 'server-caches.zip', 'client-caches.zip', 'server-animations.pigg',
                'atlas-world-supplement.zip', 'character-avatar-defaults.zip', 'native-responsiveness.json',
                'local_character_server.py', 'character_server_data_cache.py', 'client_animation_package.py'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                member = 'assets/runtime/'+name; replace_member(values[0], member, b'forged'); values[5][member] = pin(b'forged')
                with self.assertRaisesRegex(ValueError, 'payload boundaries'): self.verify(values)

    def test_retained_android_shell_and_native_android_bytes_are_exact(self):
        for name in ('classes.dex', 'resources.arsc', next(iter(package.builder().NATIVE_MEMBERS))):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                replace_member(values[0], name, b'forged')
                if name in values[5]: values[5][name] = pin(b'forged')
                with self.assertRaises(ValueError): self.verify(values)

    def test_foreign_helper_and_appearance_archive_bytes_are_rejected(self):
        for name in package.HELPERS|package.VISUAL_ASSETS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                member = 'assets/runtime/'+name; replace_member(values[0], member, b'forged'); values[5][member] = pin(b'forged')
                with self.assertRaisesRegex(ValueError, 'Authored client helper|Verified appearance asset'): self.verify(values)

    def test_nested_client_rejects_dll_game_extra_member_and_prior_history_forgeries(self):
        for mutation in ('dll', 'game', 'extra', 'history'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                member = 'assets/runtime/client-runtime.zip'
                with zipfile.ZipFile(values[0]) as apk, zipfile.ZipFile(io.BytesIO(apk.read(member))) as client:
                    contents = {row.filename: client.read(row) for row in client.infolist()}
                if mutation == 'dll': contents['fixture-0.dll'] = b'foreign'
                elif mutation == 'game': contents['CityOfHeroes.exe'] = b'foreign'
                elif mutation == 'extra': contents['foreign.dll'] = b'foreign'
                else:
                    history = json.loads(contents['client-package.json']); history['client_loading']['manifest_sha256'] = 'f'*64
                    contents['client-package.json'] = package.shared.encoded(history)
                rewritten = io.BytesIO()
                with zipfile.ZipFile(rewritten, 'w') as client:
                    for name, raw in contents.items(): client.writestr(name, raw)
                replace_member(values[0], member, rewritten.getvalue()); values[5][member] = pin(rewritten.getvalue())
                with self.assertRaisesRegex(ValueError, 'DLL|Game|inventory|drifted'):
                    package.verify_client_archive(io.BytesIO(rewritten.getvalue()), values[2], values[9])
                with self.assertRaises(ValueError): self.verify(values)

    def test_all_runtime_history_flags_are_preserved(self):
        for key in ('client_visual', 'client_loading', 'client_streaming', 'client_asset_closure', 'startup_only_reopen', 'task_gate_required'):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                changed = copy.deepcopy(values[6]); changed[key] = 'forged'; raw = package.shared.encoded(changed)
                member = 'assets/runtime/runtime-manifest.json'; replace_member(values[0], member, raw); values[5][member] = pin(raw)
                with self.assertRaisesRegex(ValueError, 'manifest changed'): self.verify(values)

    def test_superset_requires_every_5476_leaf_and_an_actual_addition(self):
        leaves = {'data/texture_library/'+str(index)+'.texture': pin(b'old') for index in range(5476)}
        old = {'_visual_manifest': {'files': leaves, 'files_sha256': 'f'*64}}
        current = dict(leaves, **{'data/player_library/new.geo': pin(b'model')})
        self.assertEqual(package.validate_visual_superset(old, {'manifest': {'files': current}}),
            {'retained_files': 5476, 'added_files': 1, 'added_bytes': 5, 'previous_files_sha256': 'f'*64})
        for changed in (leaves, dict(current, **{next(iter(leaves)): pin(b'foreign')}), dict(list(current.items())[1:])):
            with self.assertRaisesRegex(ValueError, 'Every immediate'): package.validate_visual_superset(old, {'manifest': {'files': changed}})

    def test_original_5476_compressed_streams_and_metadata_survive_append_but_not_recompression(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); target = folder/'client-visual-assets.zip'
            with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
                for index in range(5476): archive.writestr('data/texture_library/'+str(index)+'.texture', b'retained-'*64)
            with zipfile.ZipFile(target) as archive:
                pins = {row.filename: package.visual_stream_pin(archive, row) for row in archive.infolist()}
            donor = {'_visual_stream_pins': pins, '_visual_manifest': {'files': dict.fromkeys(pins)}}
            with zipfile.ZipFile(target, 'a') as archive: archive.writestr('data/texture_library/new.texture', b'new')
            self.assertEqual(package.verify_visual_streams(None, folder, donor),
                {'retained_compressed_streams': 5476, 'all_streams_byte_identical': True})
            with zipfile.ZipFile(target) as archive: raw = {row.filename: archive.read(row) for row in archive.infolist()}
            with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
                for name, content in raw.items(): archive.writestr(name, content)
            with self.assertRaisesRegex(ValueError, 'compressed visual stream changed'):
                package.verify_visual_streams(None, folder, donor)

    def test_native_producer_cannot_change_donor_ancestry_or_compile_servers(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            native, donor = values[9], values[2]
        producer = mock.Mock(); producer.validate_package.return_value = native
        with mock.patch.object(package, 'native_builder', return_value=producer):
            self.assertEqual(package.validate_native(Path('native'), COMMIT, donor), native)
            for field, foreign in (('base_client_executable', {}), ('retained_source_inputs', {}),
                    ('schema_sources_sha256', {}), ('build_targets', ['Game', 'MapServer']),
                    ('replacement_scope', 'all'), ('retained_native_dependencies_changed', True)):
                changed = copy.deepcopy(native); changed[field] = foreign; producer.validate_package.return_value = changed
                with self.assertRaises(ValueError): package.validate_native(Path('native'), COMMIT, donor)

    def test_existing_release_is_never_overwritten(self):
        api = mock.Mock(); api.request.return_value = {'object': {'type': 'commit', 'sha': COMMIT}}
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk = folder/package.APK_NAME; apk.write_bytes(b'apk')
            with self.assertRaisesRegex(ValueError, 'never replaced'):
                package.publish_release(api, {'repository_commit': COMMIT, **pin(b'apk')},
                    (apk, folder/(package.APK_NAME+'.sha256'), folder/package.NOTES_NAME), 'reviewed')

    def test_qualification_requires_complete_current_game_and_all_retained_suites(self):
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), mock.patch.object(base, 'checked_file'):
            self.assertEqual(package.validate_qualification(qualification(), COMMIT)['status'], 'passed')
            for mutation in ('missing', 'skip', 'fail', 'count', 'reused_game', 'game_not_current', 'server', 'java'):
                receipt = qualification(); name = next(iter(receipt['test_suites']))
                if mutation == 'missing': receipt['test_suites'].pop(name)
                elif mutation == 'skip': receipt['test_suites'][name]['skipped'] = 1
                elif mutation == 'fail': receipt['test_suites'][name]['status'] = 'failed'
                elif mutation == 'count': receipt['tests_run'] += 1
                elif mutation == 'reused_game': receipt['native_client_package_reused'] = True
                elif mutation == 'game_not_current': receipt['native_client_compiled_in_current_run'] = False
                elif mutation == 'server': receipt['native_mapserver_recompiled'] = True
                else: receipt['changed_java_sources'] = ['foreign.java']
                with self.subTest(mutation=mutation), self.assertRaises(ValueError): package.validate_qualification(receipt, COMMIT)

    def test_qualification_rejects_source_changes_after_qualification(self):
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), mock.patch.object(base, 'checked_file', side_effect=ValueError('source changed')):
            with self.assertRaisesRegex(ValueError, 'source changed'): package.validate_qualification(qualification(), COMMIT)

    def test_verification_inventory_cannot_add_a_payload(self):
        donor = {'runtime_manifest': {'files': {str(index): pin(b'fixture') for index in range(64)}}}
        with self.assertRaisesRegex(ValueError, 'cannot add'):
            package.verification_manifests(donor, {'files': {'known': pin(b'fixture')}}, {'foreign.py': pin(b'foreign')}, COMMIT)

    def test_workflow_binds_new_release_exact_donor_game_only_and_parallel_assets(self):
        text = (package.ROOT/package.WORKFLOW).read_text()
        self.assertEqual((package.VERSION_NAME, package.VERSION_CODE), ('0.13.11', 26))
        self.assertEqual(package.DONOR_COMMIT, '9c36a5f411290400cb4aa4b2711a4bdcd39ca8cb')
        self.assertIn('run-id: '+str(package.DONOR_RUN_ID), text)
        self.assertIn('name: coh-client-asset-closure-packaging-evidence', text)
        self.assertIn('--target Game', text); self.assertNotIn('--target MapServer', text)
        self.assertIn('needs: [changes, client, assets]', text)
        self.assertIn("COH_REQUIRE_STARTUP_BUNDLE_PG: '1'", text)
        self.assertNotIn('d8.jar', text); self.assertNotIn('javac', text)
        self.assertIn('out/client-startup-followup/'+package.APK_NAME, text)

    def test_guest_ast_delta_cannot_change_imports_unrelated_functions_or_verifier_hash_checks(self):
        import zipfile
        path = next(path for path in (package.ROOT/'out/public'/package.DONOR_APK_NAME,
            package.ROOT/'out/donor'/package.DONOR_APK_NAME) if path.is_file())
        with zipfile.ZipFile(path) as donor:
            for name in package.HELPERS-{'client_visual_assets.py'}:
                old = donor.read('assets/runtime/'+name); new = (package.ROOT/'android/guest'/name).read_bytes()
                self.assertTrue(package.validate_guest_delta(name, old, new)['all_other_ast_nodes_retained'])
                for forged in (new+b'\nimport foreign\n', new.replace(b'import json', b'import foreign', 1)):
                    with self.subTest(name=name), self.assertRaises(ValueError): package.validate_guest_delta(name, old, forged)


class ProductionAppearanceBindingTests(unittest.TestCase):
    def test_frozen_appearance_guest_acceptance_preserves_5476_leaves_and_refuses_stale_donor(self):
        producer = package.visual_builder()
        guest = package.visual_guest()
        value = producer.read_manifest(package.ROOT/'assets/client-appearance-manifest.json', root=package.ROOT)
        baseline = package.read_json(package.ROOT/'assets/client-visual-manifest.json')
        self.assertGreater(guest.APPEARANCE_FILE_COUNT, 0)
        self.assertEqual(len(baseline['files']), 5476)
        self.assertTrue(set(baseline['files']) < set(value['files']))
        self.assertTrue(all(value['files'][name] == expected for name, expected in baseline['files'].items()))
        self.assertEqual(value['appearance_extension']['baseline_files_sha256'], baseline['files_sha256'])
        self.assertEqual(len(value['files']), 5476+guest.APPEARANCE_FILE_COUNT)
        self.assertEqual(guest.ARCHIVE_BYTES, producer.ARCHIVE_PIN['bytes'])
        self.assertLessEqual(guest.ARCHIVE_BYTES, 1024**3)
        self.assertLessEqual(producer.MANIFEST_PIN['bytes'], 64*1024**2)
        self.assertLessEqual(guest.PAYLOAD_BYTES, 2*1024**3)
        with tempfile.TemporaryDirectory() as temporary:
            assets = Path(temporary)
            (assets/'client-visual-manifest.json').write_bytes(
                producer.manifest_bytes(package.ROOT/'assets/client-appearance-manifest.json'))
            self.assertEqual(guest.package(assets), value)
            appearances = guest.appearance_files(value)
            sweeps = guest.sweep_files(value)
            encounters = guest.encounter_files(value)
            historical_extension = set(value['visual_extension']['files'])
            self.assertEqual((len(appearances), len(sweeps), len(encounters), len(historical_extension)),
                (guest.APPEARANCE_FILE_COUNT, 5147, 6, 33))
            partitions = (appearances, sweeps, encounters, historical_extension)
            self.assertEqual(sum(map(len, partitions)), len(set().union(*partitions)))
            self.assertEqual(len(set(value['files'])-set().union(*partitions)), 290)
            old = package.module('historical_visual_bytes', Path(package.__file__).with_name('prepare_client_visual_assets.py'))
            (assets/'client-visual-manifest.json').write_bytes(
                old.manifest_bytes(package.ROOT/'assets/client-visual-manifest.json'))
            with self.assertRaisesRegex(guest.client.base.DiagnosticError, 'manifest differs'):
                guest.package(assets)
