"""Run real APK conservation checks; asset-format tests qualify the producer.

Only the visual producer and live-source check are substituted in small ZIP
fixtures. Payload boundaries, manifests, all original native/server archives,
DEX/resources, SHA256 and extraction checks run unchanged.
"""
import argparse
import contextlib
import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import build_client_visual_apk as package
import test_startup_bundle_package as baseline

COMMIT = 'a'*40
pin = baseline.pin
replace_member = baseline.replace_member


def fixture(folder):
    apk, donor, _, _, _, _ = baseline.fixture(folder)
    donor['retained_dex'] = donor.pop('recompiled_dex')
    with zipfile.ZipFile(apk) as archive:
        donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
        donor['native_dbserver'] = json.loads(archive.read('assets/runtime/startup-dbserver-manifest.json'))
    # Match the actual donor's 59 client pins and 60 runtime pins. Four of
    # the older fixture filler assets become retained Atlas importer resources.
    with zipfile.ZipFile(apk) as archive:
        contents = {entry.filename: archive.read(entry) for entry in archive.infolist()}
    names = sorted(name for name in donor['payloads'] if name.startswith('assets/runtime/retained-'))[:4]
    for index, name in enumerate(names):
        raw = contents.pop(name); donor['payloads'].pop(name)
        replacement = 'assets/atlas/retained-fixture-%s.bin' % index
        contents[replacement] = raw; donor['payloads'][replacement] = pin(raw)
        donor['_client_verification']['files'].pop(Path(name).name)
        donor['runtime_manifest']['files'].pop(Path(name).name)
    raw = package.shared.encoded(donor['_client_verification'])
    contents['assets/runtime/client-manifest.json'] = raw
    donor['payloads']['assets/runtime/client-manifest.json'] = pin(raw)
    donor['runtime_manifest']['files']['client-manifest.json'] = pin(raw)
    raw = package.shared.encoded(donor['runtime_manifest'])
    contents['assets/runtime/runtime-manifest.json'] = raw
    donor['payloads']['assets/runtime/runtime-manifest.json'] = pin(raw)
    with zipfile.ZipFile(apk, 'w') as archive:
        for name, raw in contents.items(): archive.writestr(name, raw)
    for name in package.ADDED_HELPERS:
        (folder/'android/guest'/name).write_bytes(('authored-new-'+name).encode())
    directory = folder/'visual'; directory.mkdir()
    (directory/'client-visual-assets.zip').write_bytes(b'exact-selected-visual-archive')
    (directory/'client-visual-manifest.json').write_bytes(b'{"selected":"exact-fixture"}')
    visual = {'format': 1, 'manifest': {'selected': 'exact-fixture'},
        'files': {name: package.builder().file_pin(directory/name) for name in package.VISUAL_ASSETS}}
    return apk, donor, directory, visual


@contextlib.contextmanager
def candidate(folder):
    apk, donor, directory, visual = fixture(folder)
    with mock.patch.object(package, 'ROOT', folder), \
            mock.patch.object(package, 'current_sources', return_value={}), \
            mock.patch.object(package, 'validate_visual_package', return_value=visual):
        runtime, payloads, returned, preflight = package.extract_and_repair(apk, donor,
            folder/'unpacked', COMMIT, directory)
        output = folder/'candidate.apk'
        with zipfile.ZipFile(output, 'w') as archive:
            for name in payloads: archive.write(folder/'unpacked'/name, name)
            for name, raw in {'AndroidManifest.xml': b'new-version-manifest', 'classes.dex': b'exact-memory-DEX',
                    'resources.arsc': b'resources', 'res/drawable/ic_coh_client.xml': b'icon'}.items():
                archive.writestr(name, raw)
        yield output, apk, donor, directory, visual, payloads, runtime, preflight


def qualification():
    contract = package.module('client_visual_package_qualification_fixture', package.ROOT/package.QUALIFICATION_SCRIPT)
    return {'format': 1, 'status': 'passed', 'scope': package.QUALIFICATION_SCOPE,
        'repository_commit': COMMIT, 'retained_runtime_repository_commit': package.DONOR_COMMIT,
        'retained_setup_memory_repository_commit': package.RETAINED_SETUP_MEMORY_COMMIT,
        'retained_native_repository_commit': package.RETAINED_NATIVE_COMMIT,
        'donor_apk_sha256': package.DONOR_APK['sha256'],
        **{name: False for name in ('physical_gameplay_validated', 'physical_client_timing_validated',
            'physical_visual_assets_validated', 'native_runtime_booted', 'long_prior_gameplay_milestones_repeated',
            'asset_reimport_required', 'java_or_dex_recompiled', 'native_dbserver_recompiled',
            'native_client_recompiled', 'native_mapserver_recompiled')},
        **{name: True for name in ('runtime_refresh_required', 'previous_runtime_generation_retained',
            'setup_memory_guards_preserved', 'retained_server_cache_and_save_fix_verified',
            'postgresql_emission_fixture_verified')},
        'postgresql_emission_fixtures': ['cancelled_child_deletion_commits', 'delete_insert_replacement_commits',
            'duplicate_insert_23505_rollback'], 'tests_run': len(contract.TEST_MODULES),
        'checks': {name: True for name in package.CHECKS},
        'source_files': {name: {'bytes': 1, 'sha256': '0'*64} for name in package.SOURCE_FILES},
        'check_suites': copy.deepcopy(contract.CHECK_SUITES),
        'test_suites': {name: {'tests_run': 1, 'status': 'passed', 'skipped': 0} for name in contract.TEST_MODULES}}


class ClientVisualPackagingTests(unittest.TestCase):
    def verify(self, values):
        output, _, donor, directory, _, payloads, _, _ = values
        return package.verify_derivative(output, donor, payloads, COMMIT, directory)

    def test_real_derivative_retains_all_67_native_server_payloads_and_memory_shell(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, apk, donor, _, visual, payloads, runtime, preflight = values
            self.assertEqual(self.verify(values), visual)
            self.assertEqual(len(payloads), 71)
            self.assertEqual(set(payloads)-set(donor['payloads']), package.ADDED_PAYLOADS)
            self.assertEqual({name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]},
                package.REPLACED_PAYLOADS)
            self.assertEqual(preflight, donor['server_payload_extraction_preflight'])
            self.assertEqual(runtime['repository_commit'], COMMIT)
            self.assertTrue(runtime['startup_only_reopen']); self.assertTrue(runtime['task_gate_required'])
            self.assertTrue(runtime['client_visual']['existing_server_cache_and_save_fix_preserved'])
            self.assertFalse(runtime['client_visual']['native_client_recompiled'])
            with zipfile.ZipFile(output) as current, zipfile.ZipFile(apk) as original:
                for name in donor['payloads']:
                    if name not in package.REPLACED_PAYLOADS: self.assertEqual(current.read(name), original.read(name), name)
                self.assertEqual(current.read('classes.dex'), original.read('classes.dex'))

    def test_nested_client_game_dlls_source_receipt_are_byte_exact(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, apk, _, _, _, _, _, _ = values
            self.verify(values)
            with zipfile.ZipFile(output) as current, zipfile.ZipFile(apk) as original:
                self.assertEqual(current.read('assets/runtime/client-runtime.zip'), original.read('assets/runtime/client-runtime.zip'))

    def test_server_cache_save_import_world_animation_driver_changes_cannot_be_hidden_by_forged_pin(self):
        for name in ('game-package.tar.gz', 'dbserver-package.tar.gz', 'dbserver-schema.tar.gz',
                'startup-dbserver.exe', 'startup-dbserver-manifest.json', 'server-caches.zip',
                'client-caches.zip', 'server-animations.pigg', 'server-animation-manifest.json',
                'client-runtime.zip', 'atlas-world-supplement.zip', 'character-avatar-defaults.zip',
                'native-responsiveness.json', 'character_server_data_cache.py', 'local_character_server.py',
                'texture_header_index.py', 'client_startup_diagnostic.py', 'task_gate_evidence.py'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                output, _, _, _, _, payloads, _, _ = values
                member = 'assets/runtime/'+name
                # Real candidate fixture includes retained helpers selected by the
                # preceding pass. Missing retained production names are added as
                # unexpected inventory, which must also fail closed.
                if member in payloads:
                    replace_member(output, member, b'foreign'); payloads[member] = pin(b'foreign')
                else:
                    with zipfile.ZipFile(output, 'a') as archive: archive.writestr(member, b'foreign')
                    payloads[member] = pin(b'foreign')
                with self.assertRaisesRegex(ValueError, 'payload boundaries'): self.verify(values)

    def test_memory_dex_resources_and_android_native_code_remain_exact(self):
        for name in ('classes.dex', 'resources.arsc', next(iter(package.builder().NATIVE_MEMBERS))):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                output, _, _, _, _, payloads, _, _ = values
                replace_member(output, name, b'foreign')
                if name in payloads: payloads[name] = pin(b'foreign')
                with self.assertRaises(ValueError): self.verify(values)

    def test_added_helpers_and_changed_integration_require_authored_source_bytes(self):
        for name in package.HELPERS|package.ADDED_HELPERS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                output, _, _, _, _, payloads, _, _ = values
                member = 'assets/runtime/'+name
                replace_member(output, member, b'foreign helper'); payloads[member] = pin(b'foreign helper')
                with self.assertRaisesRegex(ValueError, 'Authored client helper'): self.verify(values)

    def test_visual_archive_and_manifest_require_same_verified_asset_directory(self):
        for name in package.VISUAL_ASSETS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                output, _, _, _, _, payloads, _, _ = values
                member = 'assets/runtime/'+name
                replace_member(output, member, b'foreign asset'); payloads[member] = pin(b'foreign asset')
                with self.assertRaisesRegex(ValueError, 'Verified visual asset'): self.verify(values)

    def test_asset_source_files_cannot_change_after_packaging(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            _, _, _, directory, _, _, _, _ = values
            (directory/'client-visual-assets.zip').write_bytes(b'changed-after-packaging')
            with self.assertRaisesRegex(ValueError, 'Verified visual asset'): self.verify(values)

    def test_verification_manifest_cannot_relabel_native_server_cache_or_save_history(self):
        for member, field in (('runtime-manifest.json', 'startup_bundle'), ('runtime-manifest.json', 'startup_schedule'),
                ('runtime-manifest.json', 'task_gate_required'), ('client-manifest.json', 'unreviewed')):
            with self.subTest(member=member, field=field), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                output, _, _, _, _, payloads, _, _ = values
                path = 'assets/runtime/'+member
                with zipfile.ZipFile(output) as archive: value = json.loads(archive.read(path))
                value[field] = 'foreign'
                raw = package.shared.encoded(value); replace_member(output, path, raw); payloads[path] = pin(raw)
                with self.assertRaisesRegex(ValueError, 'Runtime manifest drifted'): self.verify(values)

    def test_manifest_must_include_all_four_new_payload_pins(self):
        for member in ('runtime-manifest.json', 'client-manifest.json'):
            with self.subTest(member=member), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                output, _, _, _, _, payloads, _, _ = values
                path = 'assets/runtime/'+member
                with zipfile.ZipFile(output) as archive: value = json.loads(archive.read(path))
                value['files'].pop('client_animation_package.py')
                raw = package.shared.encoded(value); replace_member(output, path, raw); payloads[path] = pin(raw)
                with self.assertRaisesRegex(ValueError, 'Runtime manifest drifted'): self.verify(values)

    def test_incomplete_added_payload_inventory_fails(self):
        for name in package.ADDED_PAYLOADS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                values[5].pop(name)
                with self.assertRaisesRegex(ValueError, 'payload boundaries'): self.verify(values)

    def test_unexpected_apk_member_cannot_be_hidden(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            with zipfile.ZipFile(values[0], 'a') as archive: archive.writestr('unreviewed.bin', b'foreign')
            with self.assertRaisesRegex(ValueError, 'APK (inventory|payload set mismatch)'): self.verify(values)

    def test_donor_extraction_rejects_unexpected_member_before_writing_outside_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk, donor, directory, visual = fixture(folder)
            with zipfile.ZipFile(apk, 'a') as archive: archive.writestr('../unreviewed.bin', b'foreign')
            with mock.patch.object(package, 'ROOT', folder), \
                    mock.patch.object(package, 'current_sources', return_value={}), \
                    mock.patch.object(package, 'validate_visual_package', return_value=visual):
                with self.assertRaises(ValueError): package.extract_and_repair(apk, donor, folder/'unpacked', COMMIT, directory)
            self.assertFalse((folder/'unreviewed.bin').exists())

    def test_visual_package_validator_binds_tracked_manifest_and_regular_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); assets = folder/'assets'; assets.mkdir(); directory = folder/'visual'; directory.mkdir()
            for target in (assets, directory):
                (target/'client-visual-manifest.json').write_text('{"source":"verified"}')
                (target/'client-visual-assets.zip').write_bytes(b'verified archive')
            producer = mock.Mock(); producer.verify.return_value = {'source': 'verified'}
            guest = mock.Mock(); guest.package.return_value = {'source': 'verified'}
            with mock.patch.object(package, 'ROOT', folder), mock.patch.object(package, 'visual_builder', return_value=producer), \
                    mock.patch.object(package, 'visual_guest', return_value=guest):
                result = package.validate_visual_package(directory)
                self.assertEqual(result['manifest'], {'source': 'verified'})
                producer.verify.assert_called_once_with(directory/'client-visual-assets.zip', directory/'client-visual-manifest.json', root=folder)
                (directory/'client-visual-manifest.json').write_text('{"source":"foreign"}')
                with self.assertRaisesRegex(ValueError, 'source manifest differs'): package.validate_visual_package(directory)

    def test_visual_guest_constant_or_manifest_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); assets = folder/'assets'; assets.mkdir(); directory = folder/'visual'; directory.mkdir()
            for target in (assets, directory):
                (target/'client-visual-manifest.json').write_text('{"source":"verified"}')
                (target/'client-visual-assets.zip').write_bytes(b'verified archive')
            producer, guest = mock.Mock(), mock.Mock(); guest.package.return_value = {'source': 'foreign'}
            with mock.patch.object(package, 'ROOT', folder), mock.patch.object(package, 'visual_builder', return_value=producer), \
                    mock.patch.object(package, 'visual_guest', return_value=guest):
                with self.assertRaisesRegex(ValueError, 'Guest visual constants'): package.validate_visual_package(directory)

    def test_visual_package_validator_rejects_linked_inputs(self):
        for name in package.VISUAL_ASSETS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary); directory = folder/'visual'; directory.mkdir()
                original = folder/'linked-input'; original.write_bytes(b'foreign')
                for member in package.VISUAL_ASSETS:
                    if member == name: (directory/member).symlink_to(original)
                    else: (directory/member).write_bytes(b'fixture')
                with self.assertRaises(ValueError): package.validate_visual_package(directory)

    def test_qualification_cannot_claim_physical_results_or_native_rebuild(self):
        for name in ('physical_gameplay_validated', 'physical_client_timing_validated', 'physical_visual_assets_validated',
                'native_runtime_booted', 'long_prior_gameplay_milestones_repeated', 'asset_reimport_required',
                'java_or_dex_recompiled', 'native_dbserver_recompiled', 'native_client_recompiled', 'native_mapserver_recompiled'):
            with self.subTest(name=name):
                receipt = qualification(); receipt[name] = True
                with self.assertRaisesRegex(ValueError, 'Exact client asset qualification'): package.validate_qualification(receipt, COMMIT)

    def test_qualification_requires_exact_retained_memory_cache_save_and_donor_identity(self):
        for name in ('runtime_refresh_required', 'previous_runtime_generation_retained', 'setup_memory_guards_preserved',
                'retained_server_cache_and_save_fix_verified', 'postgresql_emission_fixture_verified'):
            with self.subTest(name=name):
                receipt = qualification(); receipt[name] = False
                with self.assertRaisesRegex(ValueError, 'Exact client asset qualification'): package.validate_qualification(receipt, COMMIT)
        receipt = qualification(); receipt['donor_apk_sha256'] = 'f'*64
        with self.assertRaises(ValueError): package.validate_qualification(receipt, COMMIT)
        receipt = qualification(); receipt['postgresql_emission_fixtures'] = []
        with self.assertRaises(ValueError): package.validate_qualification(receipt, COMMIT)

    def test_qualification_requires_exact_suite_and_source_closure(self):
        for mutation in ('missing_suite', 'skipped_suite', 'missing_source', 'test_total', 'foreign_check_suite'):
            with self.subTest(mutation=mutation):
                receipt = qualification()
                if mutation == 'missing_suite': receipt['test_suites'].pop('test_client_animation_package')
                elif mutation == 'skipped_suite': receipt['test_suites']['test_client_animation_package']['skipped'] = 1
                elif mutation == 'missing_source': receipt['source_files'].pop('android/guest/client_animation_package.py')
                elif mutation == 'test_total': receipt['tests_run'] += 1
                else: receipt['check_suites']['client_animation_mount_and_failure_guards_verified'] = []
                with self.assertRaises(ValueError): package.validate_qualification(receipt, COMMIT)

    def test_source_change_after_qualification_is_rejected(self):
        receipt = qualification()
        with self.assertRaises(ValueError): package.validate_qualification(receipt, COMMIT)

    def test_successful_qualification_binds_exact_all_source_pins(self):
        receipt = qualification(); reader = mock.Mock(); reader.checked_file.return_value = None
        with mock.patch.object(package, 'builder', return_value=reader):
            self.assertIs(package.validate_qualification(receipt, COMMIT), receipt)
        self.assertEqual(reader.checked_file.call_count, len(package.SOURCE_FILES))

    def test_visual_package_change_after_qualification_is_rejected_before_signing(self):
        receipt = qualification(); receipt['visual_package'] = {'old': True}
        args = argparse.Namespace(repository_commit=COMMIT, donor_apk=Path('donor.apk'),
            donor_build_report=Path('receipt.json'), qualification=Path('qualification.json'),
            visual_directory=Path('visual'))
        with mock.patch.object(package, 'validate_donor', return_value={}), \
                mock.patch.object(package, 'read_json', return_value=receipt), \
                mock.patch.object(package, 'validate_qualification', return_value=receipt), \
                mock.patch.object(package, 'validate_visual_package', return_value={'new': True}):
            with self.assertRaisesRegex(ValueError, 'changed after host qualification'): package.build(args)

    def test_fresh_publication_process_reproduces_exact_client_and_runtime_manifest_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); _, donor, _, _ = fixture(folder)
            manifest_input = folder/'manifest-input.json'
            manifest_input.write_text(json.dumps({'donor': {'runtime_manifest': donor['runtime_manifest']},
                'client': donor['_client_verification']}))
            # Production build and publication execute in different interpreters.
            # These exact helper sets previously inserted new JSON keys in
            # process-dependent order, changing the client SHA inside runtime.
            script = """
import hashlib, json, pathlib, sys
sys.path.insert(0, sys.argv[1])
import build_client_visual_apk as package
value = json.loads(pathlib.Path(sys.argv[2]).read_text())
updates = {name: {'bytes': 1, 'sha256': 'f'*64}
    for name in package.HELPERS|package.ADDED_HELPERS|package.VISUAL_ASSETS}
client, runtime = package.verification_manifests(value['donor'], value['client'], updates, 'a'*40)
encoded_client, encoded_runtime = map(package.shared.encoded, (client, runtime))
assert runtime['files']['client-manifest.json'] == {'bytes': len(encoded_client),
    'sha256': hashlib.sha256(encoded_client).hexdigest()}
print(json.dumps({'client': encoded_client.decode(), 'runtime': encoded_runtime.decode()}, sort_keys=True))
"""
            results = [subprocess.run([sys.executable, '-c', script, str(package.ROOT/'tools/android/interactive'),
                str(manifest_input)], env=dict(os.environ, PYTHONHASHSEED=str(seed)),
                capture_output=True, check=True, timeout=30).stdout for seed in (1, 2)]
            self.assertEqual(results[0], results[1], 'Fresh build/publication processes changed client/runtime manifest bytes')

    def test_workflow_has_no_native_or_java_compile_and_uses_exact_qualified_asset(self):
        text = (package.ROOT/package.WORKFLOW).read_text()
        self.assertEqual(text.count('    runs-on:'), 2)
        self.assertNotIn('cmake --', text); self.assertNotIn('windows-', text); self.assertNotIn('javac', text)
        self.assertIn('needs: qualify', text)
        self.assertIn('run-id: '+str(package.DONOR_RUN_ID), text)
        self.assertIn('name: coh-client-visual-assets', text)
        self.assertIn('--qualification out/client-visual-qualification.json', text)
        self.assertIn("COH_REQUIRE_STARTUP_BUNDLE_PG: '1'", text)
        self.assertIn("--materialize", text)

    def test_exact_reviewed_replacement_and_addition_contract(self):
        self.assertEqual(package.HELPERS, {'character_creation_diagnostic.py'})
        self.assertEqual(package.ADDED_HELPERS, {'client_animation_package.py', 'client_visual_assets.py'})
        self.assertEqual(len(package.REPLACED_PAYLOADS), 3)
        self.assertEqual(len(package.ADDED_PAYLOADS), 4)
        self.assertEqual((package.VERSION_NAME, package.VERSION_CODE), ('0.13.7', 22))
        self.assertEqual(package.DONOR_COMMIT, '7b48762de0748e443a2df60c6e4b59e22b365e35')


if __name__ == '__main__': unittest.main()
