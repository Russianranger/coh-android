"""Exercise real retained APK conservation using the typed 0.13.8 chain.

Small fixture assets replace only external visual/native producers. Actual ZIP
inventories, retained Game/DLL/DEX bytes, runtime histories, helper source pins,
server archive extraction and forgery rejection execute without substitution.
"""
import contextlib
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import build_client_streaming_apk as package
import test_client_loading_package as previous

COMMIT = 'a'*40
pin, replace_member = previous.pin, previous.replace_member


def qualification():
    contract = package.module('client_streaming_test_qualification', package.ROOT/package.QUALIFICATION_SCRIPT)
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
        'changed_java_sources': [], 'retained_java_sources': 19, 'authored_java_sources_verified': 19,
        'retained_baseline_payloads_verified': 71,
        'postgresql_emission_fixtures': ['cancelled_child_deletion_commits', 'delete_insert_replacement_commits',
            'duplicate_insert_23505_rollback'], 'tests_run': len(contract.TEST_MODULES),
        'checks': {name: True for name in package.CHECKS},
        'source_files': {name: {'bytes': 1, 'sha256': '0'*64} for name in package.SOURCE_FILES},
        'check_suites': copy.deepcopy(contract.CHECK_SUITES),
        'test_suites': {name: {'tests_run': 1, 'status': 'passed', 'skipped': 0} for name in contract.TEST_MODULES}}


def fixture(folder):
    with previous.candidate(folder) as values:
        output, _, old_donor, directory, old_visual, payloads, runtime, preflight, dex, _, native = values
        apk = folder/'immediate-donor.apk'; output.rename(apk)
        donor = copy.deepcopy(old_donor)
        donor.update(payloads=payloads, runtime_manifest=runtime, recompiled_dex=dex,
            server_payload_extraction_preflight=preflight, native_client_loading=native)
        with zipfile.ZipFile(apk) as archive:
            donor['_client_verification'] = json.loads(archive.read('assets/runtime/client-manifest.json'))
        donor['_visual_manifest'] = copy.deepcopy(old_visual['manifest'])
        donor['_visual_manifest']['files_sha256'] = 'f'*64
    # All prior native, visuals and history are now the immediate donor.
    for name in package.HELPERS:
        (folder/'android/guest'/name).write_bytes(('bounded-streaming-'+name).encode())
    (directory/'client-visual-assets.zip').write_bytes(b'original-leaves-and-exact-new-encounter')
    (directory/'client-visual-manifest.json').write_bytes(b'{"encounter":"bounded"}')
    visual = {'format': 1, 'manifest': {'files': dict(donor['_visual_manifest']['files'],
        **{'data/texture_library/encounter.texture': pin(b'exact-new-encounter')})},
        'files': {name: package.builder().file_pin(directory/name) for name in package.VISUAL_ASSETS}}
    return apk, donor, directory, visual


@contextlib.contextmanager
def candidate(folder):
    apk, donor, directory, visual = fixture(folder)
    with mock.patch.object(package, 'ROOT', folder), mock.patch.object(package, 'current_sources', return_value={}), \
            mock.patch.object(package, 'validate_visual_package', return_value=visual), \
            mock.patch.object(package, 'visual_builder'):
        runtime, payloads, returned, preflight = package.extract_and_repair(apk, donor,
            folder/'streaming-files', COMMIT, directory)
        output = folder/'streaming.apk'
        with zipfile.ZipFile(output, 'w') as archive, zipfile.ZipFile(apk) as original:
            for name in payloads: archive.write(folder/'streaming-files'/name, name)
            for name in ('classes.dex', 'resources.arsc', 'res/drawable/ic_coh_client.xml'):
                archive.writestr(name, original.read(name))
            archive.writestr('AndroidManifest.xml', b'version-only-update')
        yield output, apk, donor, directory, visual, payloads, runtime, preflight


class ClientStreamingPackagingTests(unittest.TestCase):
    def verify(self, values):
        output, _, donor, directory, _, payloads, _, _ = values
        return package.verify_derivative(output, donor, payloads, COMMIT, directory)

    def test_immediate_donor_game_dlls_dex_animation_server_cache_and_history_are_exact(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, apk, donor, _, visual, payloads, runtime, preflight = values
            self.assertEqual(self.verify(values), visual)
            self.assertEqual(len(payloads), 71); self.assertEqual(set(payloads), set(donor['payloads']))
            self.assertEqual(len(package.REPLACED_PAYLOADS), 7)
            self.assertEqual({n for n in payloads if payloads[n] != donor['payloads'][n]}, package.REPLACED_PAYLOADS)
            self.assertEqual(preflight, donor['server_payload_extraction_preflight'])
            self.assertEqual(set(runtime['files']), set(donor['runtime_manifest']['files']))
            self.assertEqual(len(runtime['files']), 64)
            for name in ('client_visual', 'client_loading'):
                self.assertEqual(runtime[name], donor['runtime_manifest'][name])
            self.assertFalse(runtime['client_streaming']['native_client_recompiled'])
            with zipfile.ZipFile(output) as current, zipfile.ZipFile(apk) as original:
                for name in set(payloads)-package.REPLACED_PAYLOADS:
                    self.assertEqual(current.read(name), original.read(name), name)
                self.assertEqual(current.read('classes.dex'), original.read('classes.dex'))

    def test_every_native_server_cache_animation_import_save_or_previous_helper_forgery_is_rejected(self):
        for name in ('client-runtime.zip', 'game-package.tar.gz', 'dbserver-package.tar.gz', 'dbserver-schema.tar.gz',
                'startup-dbserver.exe', 'startup-dbserver-manifest.json', 'server-caches.zip', 'client-caches.zip',
                'server-animations.pigg', 'server-animation-manifest.json', 'atlas-world-supplement.zip',
                'character-avatar-defaults.zip', 'native-responsiveness.json', 'local_character_server.py',
                'character_server_data_cache.py', 'client_animation_package.py', 'character_creation_diagnostic.py'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                output, _, _, _, _, payloads, _, _ = values; member = 'assets/runtime/'+name
                if member in payloads:
                    replace_member(output, member, b'forged'); payloads[member] = pin(b'forged')
                else:
                    with zipfile.ZipFile(output, 'a') as archive: archive.writestr(member, b'forged')
                    payloads[member] = pin(b'forged')
                with self.assertRaisesRegex(ValueError, 'payload boundaries'): self.verify(values)

    def test_dex_resources_and_android_native_bytes_cannot_change(self):
        for name in ('classes.dex', 'resources.arsc', next(iter(package.builder().NATIVE_MEMBERS))):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                output, _, _, _, _, payloads, _, _ = values
                replace_member(output, name, b'forged')
                if name in payloads: payloads[name] = pin(b'forged')
                with self.assertRaises(ValueError): self.verify(values)

    def test_foreign_helper_or_visual_producer_bytes_are_rejected(self):
        for name in package.HELPERS|package.VISUAL_ASSETS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                output, _, _, _, _, payloads, _, _ = values; member = 'assets/runtime/'+name
                replace_member(output, member, b'forged'); payloads[member] = pin(b'forged')
                with self.assertRaisesRegex(ValueError, 'Authored client helper|Verified visual asset'): self.verify(values)

    def test_runtime_history_relabelling_rejected_even_with_forged_outer_pin(self):
        for key in ('client_visual', 'client_loading', 'startup_only_reopen', 'task_gate_required'):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
                output, _, _, _, _, payloads, runtime, _ = values
                changed = copy.deepcopy(runtime); changed[key] = 'forged'
                raw = package.shared.encoded(changed); member = 'assets/runtime/runtime-manifest.json'
                replace_member(output, member, raw); payloads[member] = pin(raw)
                with self.assertRaisesRegex(ValueError, 'manifest drifted'): self.verify(values)

    def test_visual_old_leaf_removal_replacement_and_empty_followup_are_rejected(self):
        old = {'files': {'data/texture_library/old.texture': pin(b'old')}, 'files_sha256': 'f'*64}
        for current in ({}, old['files'], {'data/texture_library/old.texture': pin(b'forged'),
                'data/texture_library/new.texture': pin(b'new')}):
            with self.subTest(current=current), self.assertRaisesRegex(ValueError, 'Every immediate'):
                package.validate_visual_superset({'_visual_manifest': old}, {'manifest': {'files': current}})

    def test_reviewed_addition_retains_previous_visual_bytes_and_counts(self):
        old = {'files': {'data/texture_library/old.texture': pin(b'old')}, 'files_sha256': 'f'*64}
        current = {'files': dict(old['files'], **{'data/texture_library/new.texture': pin(b'new')})}
        self.assertEqual(package.validate_visual_superset({'_visual_manifest': old}, {'manifest': current}),
            {'retained_files': 1, 'added_files': 1, 'added_bytes': 3, 'previous_files_sha256': 'f'*64})

    def test_new_verification_inventory_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); _, donor, _, _ = fixture(folder)
            with self.assertRaisesRegex(ValueError, 'cannot add'):
                package.verification_manifests(donor, donor['_client_verification'],
                    {'unreviewed.py': pin(b'unreviewed')}, COMMIT)

    def test_existing_release_cannot_be_replaced(self):
        api = mock.Mock(); api.request.return_value = {'object': {'type': 'commit', 'sha': COMMIT}}
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk = folder/package.APK_NAME; apk.write_bytes(b'apk')
            with self.assertRaisesRegex(ValueError, 'never replaced'):
                package.publish_release(api, {'repository_commit': COMMIT, **pin(b'apk')},
                    (apk, folder/(package.APK_NAME+'.sha256'), folder/package.NOTES_NAME), 'reviewed')

    def test_qualification_requires_complete_passed_suites_counts_and_exact_retained_flags(self):
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), mock.patch.object(base, 'checked_file'):
            self.assertEqual(package.validate_qualification(qualification(), COMMIT)['status'], 'passed')
            for mutation in ('missing_suite', 'skipped', 'failed', 'bad_count', 'native_recompiled', 'java_changed'):
                with self.subTest(mutation=mutation):
                    receipt = qualification(); name = next(iter(receipt['test_suites']))
                    if mutation == 'missing_suite': receipt['test_suites'].pop(name)
                    elif mutation == 'skipped': receipt['test_suites'][name]['skipped'] = 1
                    elif mutation == 'failed': receipt['test_suites'][name]['status'] = 'failed'
                    elif mutation == 'bad_count': receipt['tests_run'] += 1
                    elif mutation == 'native_recompiled': receipt['native_client_recompiled'] = True
                    else: receipt['changed_java_sources'] = ['unreviewed.java']
                    with self.assertRaises(ValueError): package.validate_qualification(receipt, COMMIT)

    def test_qualification_source_pins_fail_closed_after_reviewed_file_changes(self):
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), \
                mock.patch.object(base, 'checked_file', side_effect=ValueError('source changed')):
            with self.assertRaisesRegex(ValueError, 'source changed'):
                package.validate_qualification(qualification(), COMMIT)


if __name__ == '__main__': unittest.main()
