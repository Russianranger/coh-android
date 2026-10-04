"""Exercise actual APK/DLL/archive conservation with a small donor fixture.

Native source production and the typed third-layer proof are qualified by the
separate native and contract suites. Here those large source receipts are
substituted while ZIP inventories, manifests, hashes and extraction are real.
"""
import argparse
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

import build_client_loading_apk as package
import build_client_visual_apk as old_package
import test_client_visual_package as baseline

COMMIT = 'a'*40
pin, replace_member = baseline.pin, baseline.replace_member


def fixture(folder):
    apk, old_donor, directory, old_visual = baseline.fixture(folder)
    with mock.patch.object(old_package, 'ROOT', folder), \
            mock.patch.object(old_package, 'current_sources', return_value={}), \
            mock.patch.object(old_package, 'validate_visual_package', return_value=old_visual):
        runtime, payloads, _, _ = old_package.extract_and_repair(apk, old_donor, folder/'previous', 'b'*40, directory)
    # Install the actual typed two-layer receipt chain into the small donor,
    # including its real frozen parser schema. The third-layer contract below
    # executes unchanged; only the Windows native producer is substituted.
    from test_client_loading_contract import client_loading_manifest, loading
    frozen = old_donor['native_responsiveness']
    frozen['retained_cache']['schema_sources_sha256'] = loading.base.baseline.schema_pins()
    old_donor['_client_manifest']['native_responsiveness']['receipt_sha256'] = package.shared.native_contract.canonical_sha(frozen)
    from test_startup_bundle_package import client_fixture
    previous_native = client_fixture()[3]
    previous_native['schema_sources_sha256'] = copy.deepcopy(frozen['retained_cache']['schema_sources_sha256'])
    previous_native['retained_source_inputs'] = copy.deepcopy(frozen['build_inputs'])
    old_package.startup.replace_client_archive(folder/'previous/assets/runtime/client-runtime.zip', old_donor,
        previous_native, folder/'native-client')
    (folder/'previous/assets/runtime/native-responsiveness.json').write_bytes(package.shared.encoded(frozen))
    client = json.loads((folder/'previous/assets/runtime/client-manifest.json').read_text())
    for name in ('client-runtime.zip', 'native-responsiveness.json'):
        member = 'assets/runtime/'+name; record = package.builder().file_pin(folder/'previous'/member)
        payloads[member] = record; client['files'][name] = record; runtime['files'][name] = record
    raw = package.shared.encoded(client); (folder/'previous/assets/runtime/client-manifest.json').write_bytes(raw)
    payloads['assets/runtime/client-manifest.json'] = pin(raw); runtime['files']['client-manifest.json'] = pin(raw)
    raw = package.shared.encoded(runtime); (folder/'previous/assets/runtime/runtime-manifest.json').write_bytes(raw)
    payloads['assets/runtime/runtime-manifest.json'] = pin(raw)
    previous = folder/'previous.apk'
    with zipfile.ZipFile(previous, 'w') as archive:
        for name in payloads: archive.write(folder/'previous'/name, name)
        for name, raw in {'AndroidManifest.xml': b'previous-version-manifest', 'classes.dex': b'exact-memory-DEX',
                'resources.arsc': b'resources', 'res/drawable/ic_coh_client.xml': b'icon'}.items(): archive.writestr(name, raw)
    donor = copy.deepcopy(old_donor); donor['payloads'] = payloads; donor['runtime_manifest'] = runtime
    donor['_client_verification'] = json.loads((folder/'previous/assets/runtime/client-manifest.json').read_text())
    with zipfile.ZipFile(folder/'previous/assets/runtime/client-runtime.zip') as archive:
        donor['_client_manifest'] = json.loads(archive.read('client-package.json'))
        donor['_client_members'] = package.startup.client_member_pins(archive)
    donor['_visual_manifest'] = {'files': {'data/texture_library/previous.texture': pin(b'original-visual')},
        'files_sha256': 'f'*64}
    # The previous payload helper is now retained while the missing-only
    # visual installer is the explicitly reviewed replacement.
    for name in package.HELPERS:
        (folder/'android/guest'/name).write_bytes(('corrected-'+name).encode())
    (directory/'client-visual-assets.zip').write_bytes(b'qualified-superset-archive')
    (directory/'client-visual-manifest.json').write_bytes(b'{"superset":"qualified"}')
    visual = {'format': 1, 'manifest': {'files': dict(donor['_visual_manifest']['files'],
        **{'data/player_library/hostile.geo': pin(b'hostile-model')})},
        'files': {name: package.builder().file_pin(directory/name) for name in package.VISUAL_ASSETS}}
    old_record = donor['_client_manifest']['files']['CityOfHeroes.exe']
    donor['native_client_startup'] = previous_native
    native_directory = folder/'loading-native'; native_directory.mkdir()
    raw = b'bounded-client-loading-Game'; (native_directory/'CityOfHeroes.exe').write_bytes(raw)
    record = dict(old_record, size=len(raw), sha256=pin(raw)['sha256'])
    native = client_loading_manifest(donor['_client_manifest'], record, COMMIT)
    return previous, donor, directory, visual, native_directory, native


@contextlib.contextmanager
def candidate(folder):
    apk, donor, directory, visual, native_directory, native = fixture(folder)
    with mock.patch.object(package, 'ROOT', folder), mock.patch.object(package, 'current_sources', return_value={}), \
            mock.patch.object(package, 'validate_visual_package', return_value=visual), \
            mock.patch.object(package, 'validate_native', return_value=native), \
            mock.patch.object(package, 'visual_builder'):
        runtime, payloads, returned, preflight, _ = package.extract_and_repair(apk, donor,
            folder/'candidate-files', COMMIT, directory, native_directory)
        output = folder/'candidate.apk'; dex = b'corrected-acceptance-DEX'
        with zipfile.ZipFile(output, 'w') as archive:
            for name in payloads: archive.write(folder/'candidate-files'/name, name)
            for name, raw in {'AndroidManifest.xml': b'new-version-manifest', 'classes.dex': dex,
                    'resources.arsc': b'resources', 'res/drawable/ic_coh_client.xml': b'icon'}.items(): archive.writestr(name, raw)
        yield output, apk, donor, directory, visual, payloads, runtime, preflight, pin(dex), native_directory, native


def qualification():
    contract = package.module('client_loading_package_test_contract', package.ROOT/package.QUALIFICATION_SCRIPT)
    return {'format': 1, 'status': 'passed', 'scope': package.QUALIFICATION_SCOPE,
        'repository_commit': COMMIT, 'retained_runtime_repository_commit': package.DONOR_COMMIT,
        'retained_setup_memory_repository_commit': package.RETAINED_SETUP_MEMORY_COMMIT,
        'retained_native_repository_commit': package.RETAINED_NATIVE_COMMIT,
        'donor_apk_sha256': package.DONOR_APK['sha256'],
        **{name: False for name in ('physical_gameplay_validated', 'physical_client_timing_validated',
            'physical_visual_assets_validated', 'native_runtime_booted', 'long_prior_gameplay_milestones_repeated',
            'asset_reimport_required', 'native_dbserver_recompiled', 'native_mapserver_recompiled')},
        **{name: True for name in ('runtime_refresh_required', 'previous_runtime_generation_retained',
            'setup_memory_guards_preserved', 'retained_server_cache_and_save_fix_verified',
            'postgresql_emission_fixture_verified', 'java_or_dex_recompiled', 'native_client_recompiled')},
        'changed_java_sources': sorted(package.JAVA_CHANGES), 'retained_java_sources': 17,
        'retained_world_lod_geometry_verified': True,
        'native_source_commit': package.NATIVE_SOURCE_COMMIT, 'native_source_provenance': package.native_link(),
        'native_client_compiled_in_current_run': False, 'native_client_package_reused': True,
        'postgresql_emission_fixtures': ['cancelled_child_deletion_commits', 'delete_insert_replacement_commits',
            'duplicate_insert_23505_rollback'], 'tests_run': len(contract.TEST_MODULES),
        'checks': {name: True for name in package.CHECKS},
        'source_files': {name: {'bytes': 1, 'sha256': '0'*64} for name in package.SOURCE_FILES},
        'check_suites': copy.deepcopy(contract.CHECK_SUITES),
        'test_suites': {name: {'tests_run': 1, 'status': 'passed', 'skipped': 0} for name in contract.TEST_MODULES}}


class ClientLoadingPackagingTests(unittest.TestCase):
    def verify(self, values):
        output, _, donor, directory, _, payloads, _, _, dex, native_directory, _ = values
        return package.verify_derivative(output, donor, payloads, dex, COMMIT, directory, native_directory)

    def test_actual_derivative_preserves_71_payload_names_and_native_server_archives(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, apk, donor, _, visual, payloads, runtime, preflight, _, _, _ = values
            self.assertEqual(self.verify(values), visual)
            self.assertEqual(len(payloads), 71); self.assertEqual(set(payloads), set(donor['payloads']))
            self.assertEqual({name for name in payloads if payloads[name] != donor['payloads'][name]}, package.REPLACED_PAYLOADS)
            self.assertEqual(preflight, donor['server_payload_extraction_preflight'])
            self.assertEqual(set(runtime['files']), set(donor['runtime_manifest']['files']))
            self.assertEqual(len(runtime['files']), 64)
            self.assertEqual(runtime['client_visual'], donor['runtime_manifest']['client_visual'])
            self.assertTrue(runtime['client_loading']['existing_server_cache_and_save_fix_preserved'])
            with zipfile.ZipFile(output) as current, zipfile.ZipFile(apk) as previous:
                for name in donor['payloads']:
                    if name not in package.REPLACED_PAYLOADS: self.assertEqual(current.read(name), previous.read(name), name)
                self.assertNotEqual(current.read('classes.dex'), previous.read('classes.dex'))

    def test_native_server_animation_import_and_cache_bytes_cannot_be_forged(self):
        for name in ('game-package.tar.gz', 'dbserver-package.tar.gz', 'dbserver-schema.tar.gz',
                'startup-dbserver.exe', 'startup-dbserver-manifest.json', 'server-caches.zip', 'client-caches.zip',
                'server-animations.pigg', 'server-animation-manifest.json', 'atlas-world-supplement.zip',
                'character-avatar-defaults.zip', 'native-responsiveness.json', 'local_character_server.py',
                'character_server_data_cache.py', 'client_animation_package.py'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                output, _, _, _, _, payloads, _, _, _, _, _ = values; member = 'assets/runtime/'+name
                replace_member(output, member, b'foreign'); payloads[member] = pin(b'foreign')
                with self.assertRaisesRegex(ValueError, 'payload boundaries'): self.verify(values)

    def test_foreign_replacement_helper_or_visual_input_is_rejected(self):
        for name in package.HELPERS|package.VISUAL_ASSETS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                output, _, _, _, _, payloads, _, _, _, _, _ = values; member = 'assets/runtime/'+name
                replace_member(output, member, b'foreign'); payloads[member] = pin(b'foreign')
                with self.assertRaisesRegex(ValueError, 'Authored client helper|Verified visual asset'): self.verify(values)

    def test_native_layer_must_preserve_all_20_dlls_and_exact_new_game_bytes(self):
        for mutation in ('retained_dll', 'foreign_game', 'extra_member', 'prior_history'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                output, _, _, _, _, payloads, _, _, _, _, _ = values
                name = 'assets/runtime/client-runtime.zip'
                with zipfile.ZipFile(output) as apk: nested = io.BytesIO(apk.read(name))
                with zipfile.ZipFile(nested) as archive: contents = {entry.filename: archive.read(entry) for entry in archive.infolist()}
                if mutation == 'retained_dll': contents['fixture-0.dll'] = b'foreign-DLL'
                elif mutation == 'foreign_game': contents['CityOfHeroes.exe'] = b'foreign-Game'
                elif mutation == 'extra_member': contents['unreviewed.dll'] = b'foreign-extra-DLL'
                else:
                    manifest = json.loads(contents['client-package.json']); manifest['native_responsiveness']['receipt_sha256'] = 'f'*64
                    contents['client-package.json'] = package.shared.encoded(manifest)
                rewritten = io.BytesIO()
                with zipfile.ZipFile(rewritten, 'w') as archive:
                    for member, raw in contents.items(): archive.writestr(member, raw)
                replace_member(output, name, rewritten.getvalue()); payloads[name] = pin(rewritten.getvalue())
                with self.assertRaisesRegex(ValueError, 'DLL|Game|inventory|drifted'): self.verify(values)

    def test_prior_visual_leaf_removal_or_byte_change_is_rejected(self):
        previous = {'files': {'data/texture_library/previous.texture': pin(b'original')}, 'files_sha256': 'f'*64}
        for current in ({}, {'data/texture_library/previous.texture': pin(b'foreign')}):
            with self.subTest(current=current), self.assertRaisesRegex(ValueError, 'preserve every prior'):
                package.validate_visual_superset({'_visual_manifest': previous}, {'manifest': {'files': current}})

    def test_superset_requires_qualified_new_leaf_and_retains_prior_byte_pin(self):
        previous = {'files': {'data/texture_library/previous.texture': pin(b'original')}, 'files_sha256': 'f'*64}
        with self.assertRaisesRegex(ValueError, 'add qualified'):
            package.validate_visual_superset({'_visual_manifest': previous}, {'manifest': {'files': previous['files']}})
        current = dict(previous['files'], **{'data/player_library/hostile.geo': pin(b'model')})
        self.assertEqual(package.validate_visual_superset({'_visual_manifest': previous}, {'manifest': {'files': current}}),
            {'previous_files_retained': 1, 'new_files': 1, 'previous_files_sha256': 'f'*64})

    def test_wrapper_dex_must_change_and_resources_remain_exact(self):
        for mutation in ('old_dex', 'foreign_dex', 'resource'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                if mutation == 'old_dex':
                    changed = list(values); changed[8] = values[2]['retained_dex']; values = tuple(changed)
                elif mutation == 'foreign_dex': replace_member(values[0], 'classes.dex', b'foreign-dex')
                else: replace_member(values[0], 'resources.arsc', b'foreign-resource')
                with self.assertRaises(ValueError): self.verify(values)

    def test_extra_runtime_payload_is_rejected_even_with_forged_manifest_pin(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            with zipfile.ZipFile(values[0], 'a') as archive: archive.writestr('assets/runtime/unreviewed.py', b'foreign')
            values[5]['assets/runtime/unreviewed.py'] = pin(b'foreign')
            with self.assertRaisesRegex(ValueError, 'payload boundaries'): self.verify(values)

    def test_verification_manifests_cannot_invent_65th_runtime_payload(self):
        donor = {'runtime_manifest': {'files': {str(index): pin(b'fixture') for index in range(64)}}}
        client = {'files': {'known': pin(b'fixture')}}
        with self.assertRaisesRegex(ValueError, 'cannot add'):
            package.verification_manifests(donor, client, {'unknown': pin(b'foreign')}, COMMIT)

    def test_helper_failure_or_retained_provenance_relabelling_fails(self):
        for member, field in (('runtime-manifest.json', 'client_visual'), ('runtime-manifest.json', 'startup_bundle'),
                ('runtime-manifest.json', 'task_gate_required'), ('client-manifest.json', 'unreviewed')):
            with self.subTest(member=member, field=field), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                path = 'assets/runtime/'+member
                with zipfile.ZipFile(values[0]) as archive: data = json.loads(archive.read(path))
                data[field] = 'foreign'; raw = package.shared.encoded(data)
                replace_member(values[0], path, raw); values[5][path] = pin(raw)
                with self.assertRaisesRegex(ValueError, 'Runtime manifest drifted'): self.verify(values)

    def test_source_inventory_permits_only_two_acceptance_classes(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); sources = []
            for index in range(19):
                name = sorted(package.JAVA_CHANGES)[index] if index < 2 else 'android/retained-%02d.java' % index
                path = folder/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'original-java'); sources.append(path)
            donor = {'java_sources': {path.relative_to(folder).as_posix(): pin(path.read_bytes()) for path in sources},
                'preserved_sources': {}, 'source_manifest': pin(b'manifest'), 'payloads': {}}
            manifest = folder/'android/interactive/src/main/AndroidManifest.xml'; manifest.parent.mkdir(parents=True, exist_ok=True); manifest.write_bytes(b'manifest')
            (folder/'android/guest').mkdir(parents=True)
            for name in package.HELPERS:
                (folder/'android/guest'/name).write_bytes(b'corrected-helper')
                donor['payloads']['assets/runtime/'+name] = pin(b'original-helper')
            for path in sources[:2]: path.write_bytes(b'corrected-java')
            with mock.patch.object(package, 'ROOT', folder), mock.patch.object(package, 'validate_retained_native_sources'), \
                    mock.patch.object(package.retained, 'java_sources', return_value=sources):
                _, current, changed = package.current_java_sources(donor, folder/'generated')
                self.assertEqual(changed, sorted(package.JAVA_CHANGES)); self.assertEqual(len(current), 19)
                sources[-1].write_bytes(b'foreign-memory-guard')
                with self.assertRaisesRegex(ValueError, 'Only ClientRuntime'): package.current_java_sources(donor, folder/'generated')

    def test_qualification_rejects_physical_claims_or_java_boundary_mismatch(self):
        for field, value in [('physical_visual_assets_validated', True), ('native_runtime_booted', True),
                ('java_or_dex_recompiled', False), ('changed_java_sources', []), ('retained_java_sources', 16)]:
            with self.subTest(field=field):
                receipt = qualification(); receipt[field] = value
                with self.assertRaisesRegex(ValueError, 'Exact client asset qualification'): package.validate_qualification(receipt, COMMIT)

    def test_successful_qualification_binds_sources_suites_postgresql_and_donor(self):
        receipt = qualification(); base = mock.Mock()
        with mock.patch.object(package, 'builder', return_value=base): self.assertIs(package.validate_qualification(receipt, COMMIT), receipt)
        self.assertEqual(base.checked_file.call_count, len(package.SOURCE_FILES))

    def test_qualification_check_aggregation_covers_only_registered_required_suites(self):
        contract = package.module('client_loading_aggregation_test', package.ROOT/package.QUALIFICATION_SCRIPT)
        results = {name: {'status': 'passed', 'skipped': 0, 'tests_run': 1} for name in contract.TEST_MODULES}
        checks = contract.qualification_checks(results)
        self.assertEqual(set(checks), set(package.CHECKS)); self.assertTrue(all(checks.values()))
        self.assertIn('test_acceptance', contract.TEST_MODULES)
        with mock.patch.dict(contract.CHECK_SUITES, {'android_visual_stage_acceptance_verified': ['unregistered_suite']}):
            with self.assertRaisesRegex(ValueError, 'registered required suites'): contract.qualification_checks(results)
        results.pop('test_acceptance')
        with self.assertRaisesRegex(ValueError, 'complete unique registered'): contract.qualification_checks(results)

    def test_two_fresh_processes_produce_identical_encoded_manifests(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); _, donor, _, _, _, _ = fixture(folder)
            manifest_input = folder/'manifest-input.json'; manifest_input.write_text(json.dumps({
                'donor': {'runtime_manifest': donor['runtime_manifest']}, 'client': donor['_client_verification']}))
            script = '''
import hashlib,json,pathlib,sys
sys.path.insert(0,sys.argv[1])
import build_client_loading_apk as package
value=json.loads(pathlib.Path(sys.argv[2]).read_text())
updates={name:{'bytes':1,'sha256':'f'*64} for name in package.HELPERS|package.VISUAL_ASSETS|package.NATIVE_ASSETS}
client,runtime=package.verification_manifests(value['donor'],value['client'],updates,'a'*40)
print(json.dumps({'client':package.shared.encoded(client).decode(),'runtime':package.shared.encoded(runtime).decode()},sort_keys=True))
'''
            results = [subprocess.run([sys.executable, '-c', script, str(package.ROOT/'tools/android/interactive'), str(manifest_input)],
                env=dict(os.environ, PYTHONHASHSEED=str(seed)), capture_output=True, check=True, timeout=30).stdout for seed in (1, 2)]
            self.assertEqual(results[0], results[1])

    def test_workflow_uses_exact_donor_qualification_and_existing_payload_slots(self):
        text = (package.ROOT/package.WORKFLOW).read_text()
        self.assertIn('run-id: '+str(package.DONOR_RUN_ID), text)
        self.assertIn('name: coh-client-visual-packaging-evidence', text)
        self.assertIn('needs: qualify', text); self.assertIn("COH_REQUIRE_STARTUP_BUNDLE_PG: '1'", text)
        self.assertNotIn('cmake --', text); self.assertNotIn('windows-', text)
        self.assertIn("artifact-ids: '"+str(package.NATIVE_ARTIFACT_ID)+"'", text)
        self.assertIn('run-id: '+str(package.NATIVE_RUN_ID), text)
        self.assertIn('verify-native --client-directory out/client-loading-native', text)
        self.assertIn('assets/client-visual-manifest.json', text)
        self.assertEqual(package.ADDED_PAYLOADS, set()); self.assertEqual(package.ADDED_HELPERS, set())
        self.assertEqual((package.VERSION_NAME, package.VERSION_CODE), ('0.13.8', 23))
        self.assertEqual(package.DONOR_COMMIT, '0da09e771cb472f4ec897c39b90cef675d007edf')

    def test_retained_native_artifact_requires_all_original_source_and_package_byte_pins(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); directory = folder/'native'; directory.mkdir()
            source_pins = {'native-source/patch.diff': pin(b'exact-original-native-source')}
            package_pins = {'native-proof.json': pin(b'exact-original-native-proof')}
            source = folder/'native-source/patch.diff'; source.parent.mkdir(); source.write_bytes(b'exact-original-native-source')
            proof = directory/'native-proof.json'; proof.write_bytes(b'exact-original-native-proof')
            manifest = {'repository_commit': package.NATIVE_SOURCE_COMMIT,
                'run_url': 'https://github.com/'+package.REPOSITORY+'/actions/runs/'+str(package.NATIVE_RUN_ID)}
            producer = mock.Mock(SOURCE_FILES=tuple(source_pins)); producer.validate_package.return_value = manifest
            with mock.patch.object(package, 'ROOT', folder), mock.patch.object(package, 'NATIVE_SOURCE_PINS', source_pins), \
                    mock.patch.object(package, 'NATIVE_PACKAGE_PINS', package_pins), mock.patch.object(package, 'client_builder', return_value=producer):
                self.assertEqual(package.validate_native_package(directory), manifest)
                producer.validate_package.assert_called_with(directory, package.NATIVE_SOURCE_COMMIT)
                for path in (source, proof):
                    previous = path.read_bytes(); path.write_bytes(b'foreign-content')
                    with self.assertRaises(ValueError): package.validate_native_package(directory)
                    path.write_bytes(previous)
                manifest['repository_commit'] = COMMIT
                with self.assertRaisesRegex(ValueError, 'original commit'): package.validate_native_package(directory)


if __name__ == '__main__': unittest.main()
