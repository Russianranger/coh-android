#!/usr/bin/env python3
"""Conservation and fail-closed tests for the startup-only wrapper derivative."""
import argparse
import contextlib
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import build_task_receipt_cleanup_apk as package


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def qualification():
    contract = package.module('cleanup_test_contract', package.ROOT/package.QUALIFICATION_SCRIPT)
    return {'format': 1, 'status': 'passed', 'scope': package.QUALIFICATION_SCOPE,
        'repository_commit': 'a'*40, 'retained_runtime_repository_commit': package.DONOR_COMMIT,
        'retained_native_repository_commit': package.RETAINED_NATIVE_COMMIT,
        'donor_apk_sha256': package.DONOR_APK['sha256'], 'physical_gameplay_validated': False,
        'physical_startup_timing_validated': False, 'physical_storage_cleanup_validated': False,
        'physical_fresh_profile_recovery_validated': False, 'native_runtime_booted': False,
        'native_client_or_server_recompiled': False, 'long_prior_gameplay_milestones_repeated': False,
        'runtime_refresh_required': True, 'previous_runtime_generation_retained': True, 'asset_reimport_required': False,
        'tests_run': len(contract.TEST_MODULES), 'checks': {name: True for name in package.CHECKS},
        'source_files': {}, 'check_suites': copy.deepcopy(contract.CHECK_SUITES),
        'test_suites': {name: {'tests_run': 1, 'status': 'passed', 'skipped': 0} for name in contract.TEST_MODULES}}


def fixture(folder):
    guest = folder/'android/guest'; guest.mkdir(parents=True)
    (guest/'character_reopen_diagnostic.py').write_bytes(b'new explicit startup-only helper')
    assets = {'character_reopen_diagnostic.py': b'old helper', 'client-runtime.zip': b'exact-client',
        'client-caches.zip': b'exact-client-cache', 'server-caches.zip': b'exact-93-cache',
        'server-animations.pigg': b'exact-animations', 'startup-dbserver.exe': b'exact-supplemental-dbserver',
        'startup-dbserver-manifest.json': package.shared.encoded({'repository_commit': package.DONOR_COMMIT}),
        'native-responsiveness.json': package.shared.encoded({'history': 'retained'}),
        'server-animation-manifest.json': package.shared.encoded({'history': 'retained'}),
        'atlas-world-supplement.zip': b'exact-world', 'character-avatar-defaults.zip': b'exact-avatar'}
    for name in ('dbserver-package.tar.gz', 'dbserver-schema.tar.gz', 'game-package.tar.gz'):
        source = folder/name; package.shared.write_game_archive(source, {'retained.bin': b'exact-native'})
        assets[name] = source.read_bytes()
    assets['client-manifest.json'] = package.shared.encoded({'files': {name: pin(raw) for name, raw in assets.items()}})
    runtime = {'repository_commit': package.DONOR_COMMIT, 'task_gate_required': True,
        'startup_schedule': {'repository_commit': package.DONOR_COMMIT, 'native_dbserver_manifest': pin(assets['startup-dbserver-manifest.json'])},
        'files': {name: pin(raw) for name, raw in assets.items()}, 'scope': 'qualified startup'}
    assets['runtime-manifest.json'] = package.shared.encoded(runtime)
    payloads = {'assets/runtime/'+name: raw for name, raw in assets.items()}
    payloads.update({name: b'exact-Android-native' for name in package.builder().NATIVE_MEMBERS})
    donor = {'payloads': {name: pin(raw) for name, raw in payloads.items()}, 'runtime_manifest': runtime,
        'retained_dex': pin(b'old-dex'), 'native_responsiveness': {'history': 'retained'},
        'server_animation_manifest': {'history': 'retained'}, 'native_dbserver': {'repository_commit': package.DONOR_COMMIT},
        'retained_android_resources': {'resources.arsc': pin(b'resources'), 'res/drawable/ic_coh_client.xml': pin(b'icon')}}
    apk = folder/'donor.apk'
    with zipfile.ZipFile(apk, 'w') as archive:
        for name, raw in payloads.items(): archive.writestr(name, raw)
        for name, raw in {'AndroidManifest.xml': b'old-manifest', 'classes.dex': b'old-dex',
            'resources.arsc': b'resources', 'res/drawable/ic_coh_client.xml': b'icon'}.items(): archive.writestr(name, raw)
    donor['server_payload_extraction_preflight'] = package.verify_apk_server_archives(apk)
    return apk, donor


@contextlib.contextmanager
def candidate(folder, *, changed=None, extra=None, dex=b'corrected-dex'):
    apk, donor = fixture(folder)
    with mock.patch.object(package, 'ROOT', folder):
        runtime, payloads, _, preflight = package.extract_retained(apk, donor, folder/'unpacked', 'a'*40)
        output = folder/'candidate.apk'
        with zipfile.ZipFile(output, 'w') as archive:
            for name in payloads:
                raw = (folder/'unpacked'/name).read_bytes()
                archive.writestr(name, changed[1] if changed and name == changed[0] else raw)
            for name, raw in {'AndroidManifest.xml': b'new-manifest', 'classes.dex': dex,
                'resources.arsc': b'resources', 'res/drawable/ic_coh_client.xml': b'icon'}.items(): archive.writestr(name, raw)
            if extra: archive.writestr(extra, b'foreign')
        yield output, apk, donor, payloads, runtime, preflight, pin(dex)


class TaskReceiptCleanupPackagingTests(unittest.TestCase):
    def test_manifest_updates_only_version_and_retains_source(self):
        source = package.ROOT/'android/interactive/src/main/AndroidManifest.xml'; before = source.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)/'manifest.xml'; package.repair_android_manifest(source, target)
            package.builder(repaired=True).verify_source_manifest(target)
            self.assertIn(b'android:versionName="0.13.4"', target.read_bytes())
            self.assertIn(b'android:versionCode="19"', target.read_bytes())
        self.assertEqual(source.read_bytes(), before)

    def test_only_one_helper_and_its_two_manifests_are_replaced(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, _, donor, payloads, _, _, dex = values
            self.assertEqual(set(payloads), set(donor['payloads']))
            self.assertEqual({n for n in payloads if payloads[n] != donor['payloads'][n]}, package.REPLACED_PAYLOADS)
            package.verify_derivative(output, donor, payloads, dex, 'a'*40)

    def test_all_native_cache_world_avatar_and_prior_startup_bytes_are_exact(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, apk, donor, payloads, _, preflight, dex = values
            self.assertEqual(preflight, donor['server_payload_extraction_preflight'])
            with zipfile.ZipFile(output) as archive, zipfile.ZipFile(apk) as original:
                for name in donor['payloads']:
                    if name not in package.REPLACED_PAYLOADS: self.assertEqual(archive.read(name), original.read(name))
            package.verify_derivative(output, donor, payloads, dex, 'a'*40)

    def test_explicit_startup_flag_preserves_task_contract_and_native_provenance(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, _, donor, payloads, runtime, _, dex = values
            self.assertIs(runtime['startup_only_reopen'], True); self.assertIs(runtime['task_gate_required'], True)
            self.assertEqual(runtime['startup_schedule'], donor['runtime_manifest']['startup_schedule'])
            self.assertEqual(runtime['repository_commit'], 'a'*40)
            package.verify_derivative(output, donor, payloads, dex, 'a'*40)

    def test_unrelated_payload_or_supplemental_native_replacement_rejected(self):
        for name in ('startup-dbserver.exe', 'startup-dbserver-manifest.json', 'dbserver-package.tar.gz',
                'game-package.tar.gz', 'server-caches.zip', 'client-caches.zip', 'client-runtime.zip',
                'server-animations.pigg', 'atlas-world-supplement.zip', 'character-avatar-defaults.zip'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, \
                 candidate(Path(temporary), changed=('assets/runtime/'+name, b'changed')) as values:
                output, _, donor, payloads, _, _, dex = values
                with self.assertRaises(ValueError): package.verify_derivative(output, donor, payloads, dex, 'a'*40)

    def test_old_dex_cannot_mask_missing_wrapper_rebuild(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary), dex=b'old-dex') as values:
            output, _, donor, payloads, _, _, dex = values
            with self.assertRaisesRegex(ValueError, 'recompile'): package.verify_derivative(output, donor, payloads, dex, 'a'*40)

    def test_helper_must_match_current_qualified_source(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, _, donor, payloads, _, _, dex = values
            (Path(temporary)/'android/guest/character_reopen_diagnostic.py').write_bytes(b'mutated')
            with self.assertRaisesRegex(ValueError, 'Qualified reopen helper'): package.verify_derivative(output, donor, payloads, dex, 'a'*40)

    def test_foreign_or_duplicate_apk_members_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary), extra='assets/runtime/foreign.py') as values:
            output, _, donor, payloads, _, _, dex = values
            with self.assertRaises(ValueError): package.verify_derivative(output, donor, payloads, dex, 'a'*40)
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, _, donor, payloads, _, _, dex = values
            with zipfile.ZipFile(output, 'a') as archive, self.assertWarns(UserWarning): archive.writestr('classes.dex', b'corrected-dex')
            with self.assertRaises(ValueError): package.verify_derivative(output, donor, payloads, dex, 'a'*40)

    def test_unrelated_client_manifest_value_cannot_be_relabelled(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, _, donor, payloads, _, _, dex = values
            with zipfile.ZipFile(output) as archive: entries = {name: archive.read(name) for name in archive.namelist()}
            name = 'assets/runtime/client-manifest.json'; document = json.loads(entries[name]); document['unreviewed'] = True
            entries[name] = package.shared.encoded(document); payloads[name] = pin(entries[name])
            with zipfile.ZipFile(output, 'w') as archive:
                for name, raw in entries.items(): archive.writestr(name, raw)
            with self.assertRaisesRegex(ValueError, 'one helper pin'): package.verify_derivative(output, donor, payloads, dex, 'a'*40)

    def test_qualification_requires_exact_source_suite_and_real_evidence(self):
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()):
            package.validate_qualification(qualification(), 'a'*40)
            for change in ({'test_suites': {}}, {'check_suites': {}}, {'tests_run': 0}, {'repository_commit': 'b'*40}):
                receipt = qualification(); receipt.update(change)
                with self.subTest(change=change), self.assertRaises(ValueError): package.validate_qualification(receipt, 'a'*40)

    def test_host_receipt_cannot_claim_device_timing_native_rebuild_or_no_setup(self):
        for name, value in (('physical_startup_timing_validated', True), ('native_client_or_server_recompiled', True),
                ('runtime_refresh_required', False), ('asset_reimport_required', True)):
            receipt = qualification(); receipt[name] = value
            with self.subTest(name=name), mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaises(ValueError):
                package.validate_qualification(receipt, 'a'*40)

    def test_unsafe_source_path_is_rejected(self):
        receipt = qualification(); receipt['source_files'] = {'../untrusted.py': pin(b'bad')}
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaisesRegex(ValueError, 'Unsafe'):
            package.validate_qualification(receipt, 'a'*40)

    def test_bad_qualification_prevents_signing(self):
        args = argparse.Namespace(repository_commit='a'*40, donor_apk=Path('donor.apk'),
            donor_build_report=Path('donor.json'), qualification=Path('qualification.json'))
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), mock.patch.object(package, 'validate_donor', return_value={}), \
             mock.patch.object(package, 'read_json', return_value={}), \
             mock.patch.object(package, 'validate_qualification', side_effect=ValueError('qualification failed')), \
             mock.patch.object(base, 'signing_password_spec') as signer:
            with self.assertRaisesRegex(ValueError, 'qualification failed'): package.build(args)
            signer.assert_not_called()

    def test_official_signature_requires_same_signer_and_v2_v3(self):
        output = 'Verified using v2 scheme (APK Signature Scheme v2): true\nVerified using v3 scheme (APK Signature Scheme v3): true\nSigner #1 certificate SHA-256 digest: '+package.SIGNER
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), mock.patch.object(base, 'run', return_value=output):
            self.assertEqual(package.verify_signature(Path('candidate.apk'), Path('sdk')), package.SIGNER)
        with mock.patch.object(package, 'builder', return_value=base), mock.patch.object(base, 'run', return_value=output.replace(package.SIGNER, '0'*64)), self.assertRaises(ValueError):
            package.verify_signature(Path('candidate.apk'), Path('sdk'))

    def test_existing_release_is_never_replaced(self):
        api = mock.Mock(); api.request.return_value = {'id': 42}
        assets = tuple(Path(name) for name in (package.APK_NAME, package.APK_NAME+'.sha256', package.NOTES_NAME))
        with mock.patch.object(package, 'builder', return_value=mock.Mock()), self.assertRaisesRegex(ValueError, 'never replaced'):
            package.publish_release(api, {'repository_commit': 'a'*40}, assets, 'notes')
        self.assertEqual(api.request.call_count, 1)

    def test_pipeline_has_no_native_job_and_uses_exact_previous_release_and_signer(self):
        text = (package.ROOT/package.WORKFLOW).read_text()
        self.assertNotIn('windows-', text); self.assertNotIn('cmake ', text); self.assertNotIn('--native-directory', text)
        self.assertIn('run-id: 37167835800', text); self.assertIn('run-id: 36731428735', text)
        self.assertNotIn('continue-on-error', text)
        self.assertEqual(package.JAVA_CHANGES, {package.JAVA_ROOT+'ClientRuntime.java'})


if __name__ == '__main__': unittest.main()
