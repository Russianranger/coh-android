#!/usr/bin/env python3
"""Conservation and fail-closed packaging tests for the Android storage recovery shell."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import build_storage_recovery_apk as package


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def qualification():
    return {'format': 1, 'status': 'passed', 'scope': package.QUALIFICATION_SCOPE,
        'repository_commit': 'a'*40, 'runtime_repository_commit': package.RUNTIME_COMMIT,
        'donor_apk_sha256': package.DONOR_APK['sha256'], 'physical_gameplay_validated': False,
        'physical_startup_timing_validated': False, 'physical_storage_cleanup_validated': False,
        'physical_fresh_profile_recovery_validated': False,
        'native_runtime_booted': False, 'native_client_or_server_recompiled': False,
        'long_prior_gameplay_milestones_repeated': False, 'tests_run': 489,
        'checks': {name: True for name in package.CHECKS}, 'source_files': {}}


def fixture(folder):
    assets = {'client-runtime.zip': b'client', 'server-caches.zip': b'exact-93-caches',
        'server-animations.pigg': b'qualified-native-animation-pack',
        'server-animation-manifest.json': b'{"history":"retained"}',
        'native-responsiveness.json': b'{"history":"retained"}',
        'task_gate_evidence.py': b'unchanged task observer', 'task-gate.json': b'{"required":true}',
        'atlas-world-supplement.zip': b'world', 'character-avatar-defaults.zip': b'avatar'}
    for name in ('dbserver-package.tar.gz', 'dbserver-schema.tar.gz', 'game-package.tar.gz'):
        source = folder/name
        package.shared.write_game_archive(source, {'retained.bin': b'exact-native-bytes'})
        assets[name] = source.read_bytes()
    assets['client-manifest.json'] = package.shared.encoded({'files': {name: pin(raw) for name, raw in assets.items()}})
    runtime = {'repository_commit': package.RUNTIME_COMMIT, 'task_gate_required': True,
               'files': {name: pin(raw) for name, raw in assets.items()}}
    assets['runtime-manifest.json'] = package.shared.encoded(runtime)
    payloads = {'assets/runtime/'+name: raw for name, raw in assets.items()}
    payloads.update({name: b'exact-native-library' for name in package.builder().NATIVE_MEMBERS})
    donor = {'payloads': {name: pin(raw) for name, raw in payloads.items()},
        'runtime_manifest': runtime, 'native_responsiveness': {'history': 'retained'},
        'server_animation_manifest': {'history': 'retained'}, 'recompiled_dex': pin(b'old-dex'),
        'retained_android_resources': {'resources.arsc': pin(b'resources'), 'res/drawable/ic_coh_client.xml': pin(b'icon')}}
    apk = folder/'donor.apk'
    with zipfile.ZipFile(apk, 'w') as archive:
        for name, raw in payloads.items(): archive.writestr(name, raw)
        for name, raw in {'AndroidManifest.xml': b'old-manifest', 'classes.dex': b'old-dex',
                         'resources.arsc': b'resources', 'res/drawable/ic_coh_client.xml': b'icon'}.items():
            archive.writestr(name, raw)
    donor['server_payload_extraction_preflight'] = package.verify_apk_server_archives(apk)
    return apk, donor


def repaired(folder, apk, donor, *, changed=None, extra=None, dex=b'new-dex'):
    runtime, payloads, _, preflight = package.extract_retained(apk, donor, folder/'unpacked')
    candidate = folder/'candidate.apk'
    with zipfile.ZipFile(candidate, 'w') as archive:
        for name in payloads:
            raw = (folder/'unpacked'/name).read_bytes()
            archive.writestr(name, changed[1] if changed and name == changed[0] else raw)
        for name, raw in {'AndroidManifest.xml': b'new-manifest', 'classes.dex': dex,
                         'resources.arsc': b'resources', 'res/drawable/ic_coh_client.xml': b'icon'}.items():
            archive.writestr(name, raw)
        if extra: archive.writestr(extra, b'foreign')
    return candidate, runtime, payloads, preflight, pin(dex)


class StorageRecoveryPackagingTests(unittest.TestCase):
    def test_version_only_manifest_repair_preserves_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = package.ROOT/'android/interactive/src/main/AndroidManifest.xml'
            before = source.read_bytes(); output = Path(temporary)/'manifest.xml'
            package.repair_android_manifest(source, output)
            package.builder(repaired=True).verify_source_manifest(output)
            self.assertIn(b'android:versionName="0.13.2"', output.read_bytes())
            self.assertIn(b'android:versionCode="17"', output.read_bytes())
            self.assertEqual(source.read_bytes(), before)

    def test_extraction_conserves_runtime_and_client_manifest_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk, donor = fixture(folder)
            candidate, runtime, payloads, preflight, dex = repaired(folder, apk, donor)
            self.assertEqual(payloads, donor['payloads'])
            self.assertEqual(runtime['repository_commit'], package.RUNTIME_COMMIT)
            self.assertEqual(preflight, donor['server_payload_extraction_preflight'])
            package.verify_derivative(candidate, donor, payloads, dex)

    def test_exact_server_caches_and_animation_provenance_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk, donor = fixture(folder)
            candidate, _, payloads, _, dex = repaired(folder, apk, donor)
            package.verify_derivative(candidate, donor, payloads, dex)
            with zipfile.ZipFile(candidate) as archive, zipfile.ZipFile(apk) as original:
                for name in ('server-caches.zip', 'server-animations.pigg', 'server-animation-manifest.json'):
                    self.assertEqual(archive.read('assets/runtime/'+name), original.read('assets/runtime/'+name))

    def test_runtime_relabel_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk, donor = fixture(folder)
            candidate, _, payloads, _, dex = repaired(folder, apk, donor,
                changed=('assets/runtime/runtime-manifest.json', b'{"repository_commit":"new"}'))
            with self.assertRaises(ValueError): package.verify_derivative(candidate, donor, payloads, dex)

    def test_animation_payload_replacement_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk, donor = fixture(folder)
            candidate, _, payloads, _, dex = repaired(folder, apk, donor,
                changed=('assets/runtime/server-animations.pigg', b'regenerated'))
            with self.assertRaises(ValueError): package.verify_derivative(candidate, donor, payloads, dex)

    def test_native_binary_replacement_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk, donor = fixture(folder)
            candidate, _, payloads, _, dex = repaired(folder, apk, donor,
                changed=(next(iter(package.builder().NATIVE_MEMBERS)), b'changed'))
            with self.assertRaises(ValueError): package.verify_derivative(candidate, donor, payloads, dex)

    def test_supplied_runtime_pin_change_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk, donor = fixture(folder)
            candidate, _, payloads, _, dex = repaired(folder, apk, donor)
            payloads['assets/runtime/client-runtime.zip'] = pin(b'changed')
            with self.assertRaisesRegex(ValueError, 'retained runtime payloads'):
                package.verify_derivative(candidate, donor, payloads, dex)

    def test_unchanged_dex_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk, donor = fixture(folder)
            candidate, _, payloads, _, dex = repaired(folder, apk, donor, dex=b'old-dex')
            with self.assertRaisesRegex(ValueError, 'recompile Java'):
                package.verify_derivative(candidate, donor, payloads, dex)

    def test_foreign_candidate_file_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk, donor = fixture(folder)
            candidate, _, payloads, _, dex = repaired(folder, apk, donor, extra='assets/runtime/foreign.bin')
            with self.assertRaises(ValueError):
                package.verify_derivative(candidate, donor, payloads, dex)

    def test_duplicate_member_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk, donor = fixture(folder)
            candidate, _, payloads, _, dex = repaired(folder, apk, donor)
            with zipfile.ZipFile(candidate, 'a') as archive:
                with self.assertWarns(UserWarning): archive.writestr('classes.dex', b'new-dex')
            with self.assertRaises(ValueError):
                package.verify_derivative(candidate, donor, payloads, dex)

    def test_retained_android_resources_change_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk, donor = fixture(folder)
            candidate, _, payloads, _, dex = repaired(folder, apk, donor)
            donor['retained_android_resources']['resources.arsc'] = pin(b'changed')
            with self.assertRaisesRegex(ValueError, 'resources or recompiled DEX'):
                package.verify_derivative(candidate, donor, payloads, dex)

    def test_qualification_accepts_exact_current_and_retained_source_split(self):
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()):
            self.assertEqual(package.validate_qualification(qualification(), 'a'*40)['runtime_repository_commit'], package.RUNTIME_COMMIT)

    def test_false_physical_cleanup_claim_rejected(self):
        receipt = qualification(); receipt['physical_storage_cleanup_validated'] = True
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaises(ValueError):
            package.validate_qualification(receipt, 'a'*40)

    def test_changed_retained_runtime_source_rejected(self):
        receipt = qualification(); receipt['runtime_repository_commit'] = 'a'*40
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaises(ValueError):
            package.validate_qualification(receipt, 'a'*40)

    def test_insufficient_or_incomplete_qualification_rejected(self):
        for change in ({'tests_run': 488}, {'checks': {name: False for name in package.CHECKS}}, {'repository_commit': 'b'*40}):
            receipt = qualification(); receipt.update(change)
            with self.subTest(change=change), mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaises(ValueError):
                package.validate_qualification(receipt, 'a'*40)

    def test_unrelated_java_change_or_missing_recovery_source_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); source = folder/'old.java'; source.write_text('changed')
            base = package.builder(); donor = {'java_sources': {'old.java': pin(b'old')}, 'preserved_sources': {}}
            with mock.patch.object(package, 'ROOT', folder), mock.patch.object(package, 'builder', return_value=base), \
                 mock.patch.object(base, 'java_sources', return_value=[source]), self.assertRaisesRegex(ValueError, '18 authored Java'):
                package.current_java_sources(donor, folder/'generated')

    def test_bad_qualification_stops_before_signing(self):
        args = argparse.Namespace(repository_commit='a'*40, donor_apk=Path('donor.apk'),
            donor_build_report=Path('donor.json'), qualification=Path('qualification.json'))
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), \
             mock.patch.object(package, 'validate_donor', return_value={}), \
             mock.patch.object(package, 'read_json', return_value={}), \
             mock.patch.object(package, 'validate_qualification', side_effect=ValueError('qualification failed')), \
             mock.patch.object(base, 'signing_password_spec') as signer:
            with self.assertRaisesRegex(ValueError, 'qualification failed'): package.build(args)
            signer.assert_not_called()

    def test_actual_binary_manifest_allows_only_version_values(self):
        original = 'E: manifest (line=1)\n  A: android:versionCode(0x0101021b)=16\n  A: android:versionName(0x0101021c)="0.13.1"\n  E: application\n    A: android:allowBackup(0x1)=false'
        updated = original.replace('line=1', 'line=2').replace('=16', '=17').replace('0.13.1', '0.13.2')
        base = mock.Mock(); base.run.side_effect = (original, updated)
        with mock.patch.object(package, 'builder', return_value=base):
            package.verify_binary_manifest(Path('candidate.apk'), Path('donor.apk'), Path('sdk'))

    def test_actual_binary_manifest_rejects_permission_or_activity_drift(self):
        original = 'E: manifest\n A: android:versionCode(0x1)=15\n A: android:versionName(0x2)="0.13.0"\n E: application'
        base = mock.Mock(); base.run.side_effect = (original, original+'\n E: extra-activity')
        with mock.patch.object(package, 'builder', return_value=base), self.assertRaisesRegex(ValueError, 'beyond version'):
            package.verify_binary_manifest(Path('candidate.apk'), Path('donor.apk'), Path('sdk'))

    def test_official_signature_requires_v2_and_v3(self):
        output = 'Verified using v2 scheme (APK Signature Scheme v2): true\nVerified using v3 scheme (APK Signature Scheme v3): true\nSigner #1 certificate SHA-256 digest: '+package.SIGNER
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), mock.patch.object(base, 'run', return_value=output):
            self.assertEqual(package.verify_signature(Path('candidate.apk'), Path('sdk')), package.SIGNER)

    def test_v1_only_or_wrong_signer_cannot_publish(self):
        base = package.builder()
        for output in ('Signer #1 certificate SHA-256 digest: '+package.SIGNER,
            'Verified using v2 scheme (APK Signature Scheme v2): true\nVerified using v3 scheme (APK Signature Scheme v3): true\nSigner #1 certificate SHA-256 digest: '+'0'*64):
            with self.subTest(output=output), mock.patch.object(package, 'builder', return_value=base), \
                 mock.patch.object(base, 'run', return_value=output), self.assertRaises(ValueError):
                package.verify_signature(Path('candidate.apk'), Path('sdk'))

    def test_existing_release_never_replaced(self):
        api = mock.Mock(); api.request.return_value = {'id': 42}
        paths = tuple(Path(name) for name in (package.APK_NAME, package.APK_NAME+'.sha256', package.NOTES_NAME))
        base = mock.Mock()
        with mock.patch.object(package, 'builder', return_value=base), self.assertRaisesRegex(ValueError, 'never replaced'):
            package.publish_release(api, {'repository_commit': 'a'*40}, paths, 'notes')
        self.assertEqual(api.request.call_count, 1)
        self.assertEqual(api.request.call_args.args, ('/releases/tags/'+package.RELEASE_TAG,))

    def test_physical_fresh_profile_recovery_is_not_claimed_by_host_tests(self):
        receipt = qualification(); receipt['physical_fresh_profile_recovery_validated'] = True
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaises(ValueError):
            package.validate_qualification(receipt, 'a'*40)

    def test_wrapper_donor_and_retained_runtime_sources_are_distinct(self):
        self.assertNotEqual(package.DONOR_COMMIT, package.RUNTIME_COMMIT)
        self.assertEqual(package.VERSION_NAME, '0.13.2')
        self.assertEqual(package.VERSION_CODE, 17)
        self.assertEqual(package.DONOR_APK_NAME, 'COH-Atlas-Gameplay-0.13.1.apk')
        self.assertEqual(package.donor_link()['repository_commit'], package.DONOR_COMMIT)

    def test_no_new_java_or_runtime_payload_is_allowed(self):
        self.assertFalse(package.JAVA_ADDITIONS)
        self.assertEqual(len(package.JAVA_CHANGES), 6)
        self.assertIn('android/app/src/main/java/io/github/russianranger/cohdiagnostic/DiagnosticRuntime.java', package.JAVA_CHANGES)
        self.assertIn(package.JAVA_ROOT+'StorageAudit.java', package.JAVA_CHANGES)
        self.assertIn(package.JAVA_ROOT+'StorageFiles.java', package.JAVA_CHANGES)

    def test_setup_source_change_is_pinned_with_its_runtime_reuse_guards(self):
        self.assertIn('tools/android/interactive/test_runtime_setup_reuse.py', package.SOURCE_FILES)
        self.assertIn('tools/android/interactive/test_fresh_profile_recovery.py', package.SOURCE_FILES)
        self.assertIn('tools/android/interactive/test_storage_recovery_ui.py', package.SOURCE_FILES)
        self.assertTrue(package.JAVA_CHANGES <= package.SOURCE_FILES)

    def test_candidate_with_changed_component_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk, donor = fixture(folder)
            candidate, _, payloads, _, dex = repaired(folder, apk, donor,
                changed=('assets/runtime/client-manifest.json', b'{"files":{}}'))
            with self.assertRaises(ValueError): package.verify_derivative(candidate, donor, payloads, dex)

    def test_retained_runtime_cannot_be_relabelled_as_wrapper_donor_commit(self):
        receipt = qualification(); receipt['runtime_repository_commit'] = package.DONOR_COMMIT
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaises(ValueError):
            package.validate_qualification(receipt, 'a'*40)


if __name__ == '__main__': unittest.main()
