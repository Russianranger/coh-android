#!/usr/bin/env python3
"""Conservation and fail-closed guards for the retained-runtime setup wrapper."""
import argparse
import copy
import hashlib
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock
import zipfile

import build_setup_memory_apk as package


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def qualification():
    contract = package.module('setup_memory_test_contract', package.ROOT/package.QUALIFICATION_SCRIPT)
    return {'format': 1, 'status': 'passed', 'scope': package.QUALIFICATION_SCOPE,
        'repository_commit': 'a'*40, 'runtime_repository_commit': package.DONOR_COMMIT,
        'retained_native_repository_commit': package.RETAINED_NATIVE_COMMIT,
        'donor_apk_sha256': package.DONOR_APK['sha256'],
        **{name: False for name in ('physical_gameplay_validated', 'physical_startup_timing_validated',
            'physical_storage_cleanup_validated', 'physical_fresh_profile_recovery_validated',
            'physical_setup_memory_validated', 'native_runtime_booted', 'native_client_or_server_recompiled',
            'long_prior_gameplay_milestones_repeated', 'runtime_refresh_required', 'asset_reimport_required')},
        'installed_runtime_identity_preserved': True,
        'tests_run': len(contract.TEST_MODULES), 'checks': {name: True for name in package.CHECKS},
        'source_files': {}, 'check_suites': copy.deepcopy(contract.CHECK_SUITES),
        'test_suites': {name: {'tests_run': 1, 'status': 'passed', 'skipped': 0} for name in contract.TEST_MODULES}}


def fixture(folder):
    assets = {'character_reopen_diagnostic.py': b'exact-startup-only-helper',
        'client-runtime.zip': b'exact-client', 'client-caches.zip': b'exact-client-cache',
        'server-caches.zip': b'exact-server-caches', 'server-animations.pigg': b'exact-animation-pack',
        'startup-dbserver.exe': b'exact-supplemental-DbServer',
        'startup-dbserver-manifest.json': package.shared.encoded({'repository_commit': 'd'*40}),
        'native-responsiveness.json': package.shared.encoded({'history': 'retained'}),
        'server-animation-manifest.json': package.shared.encoded({'history': 'retained'}),
        'task_gate_evidence.py': b'exact-task-observer', 'task-gate.json': b'{"required":true}',
        'atlas-world-supplement.zip': b'exact-world', 'character-avatar-defaults.zip': b'exact-avatar'}
    for name in ('dbserver-package.tar.gz', 'dbserver-schema.tar.gz', 'game-package.tar.gz'):
        source = folder/name; package.shared.write_game_archive(source, {'retained.bin': b'exact-native'})
        assets[name] = source.read_bytes()
    native = package.builder().NATIVE_MEMBERS
    while len(assets)+2+len(native) < 67:
        assets['retained-'+str(len(assets))+'.bin'] = b'exact-retained-member'
    assets['client-manifest.json'] = package.shared.encoded({'files': {name: pin(raw) for name, raw in assets.items()}})
    runtime = {'repository_commit': package.DONOR_COMMIT, 'startup_only_reopen': True,
        'task_gate_required': True, 'startup_schedule': {'repository_commit': 'd'*40},
        'files': {name: pin(raw) for name, raw in assets.items()}}
    assets['runtime-manifest.json'] = package.shared.encoded(runtime)
    payloads = {'assets/runtime/'+name: raw for name, raw in assets.items()}
    payloads.update({name: b'exact-Android-native' for name in native})
    donor = {'payloads': {name: pin(raw) for name, raw in payloads.items()}, 'runtime_manifest': runtime,
        'native_responsiveness': {'history': 'retained'}, 'server_animation_manifest': {'history': 'retained'},
        'recompiled_dex': pin(b'old-dex'),
        'retained_android_resources': {'resources.arsc': pin(b'resources'), 'res/drawable/ic_coh_client.xml': pin(b'icon')}}
    apk = folder/'donor.apk'
    with zipfile.ZipFile(apk, 'w') as archive:
        for name, raw in payloads.items(): archive.writestr(name, raw)
        for name, raw in {'AndroidManifest.xml': b'old-manifest', 'classes.dex': b'old-dex',
            'resources.arsc': b'resources', 'res/drawable/ic_coh_client.xml': b'icon'}.items(): archive.writestr(name, raw)
    donor['server_payload_extraction_preflight'] = package.verify_apk_server_archives(apk)
    return apk, donor


def candidate(folder, apk, donor, *, changed=None, extra=None, dex=b'setup-wrapper-dex'):
    runtime, payloads, retained, preflight = package.extract_retained(apk, donor, folder/'unpacked')
    output = folder/'candidate.apk'
    with zipfile.ZipFile(output, 'w') as archive:
        for name in payloads:
            raw = (folder/'unpacked'/name).read_bytes()
            archive.writestr(name, changed[1] if changed and name == changed[0] else raw)
        for name, raw in {'AndroidManifest.xml': b'new-manifest', 'classes.dex': dex,
            'resources.arsc': b'resources', 'res/drawable/ic_coh_client.xml': b'icon'}.items(): archive.writestr(name, raw)
        if extra: archive.writestr(extra, b'foreign')
    return output, runtime, payloads, retained, preflight, pin(dex)


class SetupMemoryPackagingTests(unittest.TestCase):
    def test_version_only_manifest_update_preserves_authored_source(self):
        source = package.ROOT/'android/interactive/src/main/AndroidManifest.xml'; before = source.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)/'manifest.xml'; package.repair_android_manifest(source, target)
            package.builder(repaired=True).verify_source_manifest(target)
            self.assertIn(b'android:versionName="0.13.5"', target.read_bytes())
            self.assertIn(b'android:versionCode="20"', target.read_bytes())
        self.assertEqual(before, source.read_bytes())

    def test_all_67_payloads_and_runtime_identity_are_retained_byte_exact(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk, donor = fixture(folder)
            output, runtime, payloads, _, preflight, dex = candidate(folder, apk, donor)
            self.assertEqual(67, len(payloads)); self.assertEqual(payloads, donor['payloads'])
            self.assertEqual(runtime, donor['runtime_manifest']); self.assertEqual(preflight, donor['server_payload_extraction_preflight'])
            with zipfile.ZipFile(output) as updated, zipfile.ZipFile(apk) as original:
                for name in payloads: self.assertEqual(updated.read(name), original.read(name), name)
            package.verify_derivative(output, donor, payloads, dex)

    def test_native_cache_world_avatar_helper_and_verification_manifest_changes_fail(self):
        names = ('startup-dbserver.exe', 'startup-dbserver-manifest.json', 'dbserver-package.tar.gz',
            'game-package.tar.gz', 'server-caches.zip', 'client-caches.zip', 'client-runtime.zip',
            'server-animations.pigg', 'atlas-world-supplement.zip', 'character-avatar-defaults.zip',
            'character_reopen_diagnostic.py', 'client-manifest.json', 'runtime-manifest.json')
        for name in names:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary); apk, donor = fixture(folder)
                output, _, payloads, _, _, dex = candidate(folder, apk, donor, changed=('assets/runtime/'+name, b'changed'))
                with self.assertRaises(ValueError): package.verify_derivative(output, donor, payloads, dex)

    def test_android_native_library_replacement_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk, donor = fixture(folder)
            output, _, payloads, _, _, dex = candidate(folder, apk, donor,
                changed=(next(iter(package.builder().NATIVE_MEMBERS)), b'changed'))
            with self.assertRaises(ValueError): package.verify_derivative(output, donor, payloads, dex)

    def test_supplied_updated_payload_pin_cannot_hide_changed_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk, donor = fixture(folder)
            output, _, payloads, _, _, dex = candidate(folder, apk, donor,
                changed=('assets/runtime/client-manifest.json', b'changed'))
            payloads['assets/runtime/client-manifest.json'] = pin(b'changed')
            with self.assertRaisesRegex(ValueError, 'retained runtime payloads'):
                package.verify_derivative(output, donor, payloads, dex)

    def test_unchanged_dex_cannot_mask_missing_wrapper_rebuild(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk, donor = fixture(folder)
            output, _, payloads, _, _, dex = candidate(folder, apk, donor, dex=b'old-dex')
            with self.assertRaisesRegex(ValueError, 'recompile Java'): package.verify_derivative(output, donor, payloads, dex)

    def test_foreign_duplicate_or_linked_archive_entries_fail(self):
        for kind in ('foreign', 'duplicate', 'symlink'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary); apk, donor = fixture(folder)
                output, _, payloads, _, _, dex = candidate(folder, apk, donor,
                    extra='foreign.bin' if kind == 'foreign' else None)
                if kind == 'duplicate':
                    with zipfile.ZipFile(output, 'a') as archive, self.assertWarns(UserWarning): archive.writestr('classes.dex', b'other')
                if kind == 'symlink':
                    with zipfile.ZipFile(output, 'a') as archive:
                        entry = zipfile.ZipInfo('linked'); entry.create_system = 3; entry.external_attr = (stat.S_IFLNK|0o777) << 16
                        archive.writestr(entry, b'target')
                with self.assertRaises(ValueError): package.verify_derivative(output, donor, payloads, dex)

    def test_retained_android_resources_cannot_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); apk, donor = fixture(folder)
            output, _, payloads, _, _, dex = candidate(folder, apk, donor)
            donor['retained_android_resources']['resources.arsc'] = pin(b'changed')
            with self.assertRaisesRegex(ValueError, 'resources or recompiled DEX'):
                package.verify_derivative(output, donor, payloads, dex)

    def test_current_collector_appends_one_guard_without_mutating_frozen_builder(self):
        base = package.builder(); generated = package.ROOT/'out/nonexistent-generated-java'
        baseline = base.java_sources(package.ROOT/'android/interactive/src/main', generated)
        sources = package.java_sources(base, generated)
        self.assertEqual(18, len(baseline)); self.assertEqual(19, len(sources))
        self.assertEqual(set(sources)-set(baseline), {package.ROOT/name for name in package.JAVA_ADDITIONS})
        self.assertEqual(baseline, base.java_sources(package.ROOT/'android/interactive/src/main', generated))

    def test_guard_package_links_and_duplicate_collection_fail(self):
        base = package.builder()
        for kind in ('wrong-package', 'symlink', 'already-collected'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary); source = folder/next(iter(package.JAVA_ADDITIONS)); source.parent.mkdir(parents=True)
                source.write_text('package io.github.russianranger.cohdiagnostic;\nfinal class SetupMemoryGuard {}\n')
                if kind == 'wrong-package': source.write_text('package unreviewed;\nfinal class SetupMemoryGuard {}\n')
                if kind == 'symlink': source.rename(source.with_suffix('.real')); source.symlink_to(source.with_suffix('.real'))
                with mock.patch.object(package, 'ROOT', folder), mock.patch.object(base, 'java_sources',
                        return_value=[source] if kind == 'already-collected' else []), self.assertRaises(ValueError):
                    package.java_sources(base, folder/'generated')

    def test_exact_six_java_changes_and_one_guard_addition_are_accepted(self):
        base = package.builder(); generated = package.ROOT/'out/nonexistent-generated-java'
        sources = package.java_sources(base, generated)
        previous = {source.relative_to(package.ROOT).as_posix(): base.file_pin(source) for source in sources
            if source.relative_to(package.ROOT).as_posix() not in package.JAVA_ADDITIONS}
        for name in package.JAVA_CHANGES: previous[name] = pin(b'qualified-old-source')
        donor = {'java_sources': previous, 'preserved_sources': {}, 'payloads': {},
            'source_manifest': base.file_pin(package.ROOT/'android/interactive/src/main/AndroidManifest.xml')}
        _, pins, changed = package.current_java_sources(donor, generated)
        self.assertEqual(19, len(pins)); self.assertEqual(set(changed), package.JAVA_CHANGES)
        unchanged = next(name for name in previous if name not in package.JAVA_CHANGES)
        previous[unchanged] = pin(b'other-change')
        with self.assertRaisesRegex(ValueError, 'six setup'): package.current_java_sources(donor, generated)

    def test_qualification_requires_exact_suite_contract_and_accounted_test_results(self):
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()):
            package.validate_qualification(qualification(), 'a'*40)
            for changes in ({'test_suites': {}}, {'check_suites': {}}, {'tests_run': 0},
                    {'tests_run': 999}, {'repository_commit': 'b'*40}, {'checks': {name: False for name in package.CHECKS}}):
                receipt = qualification(); receipt.update(changes)
                with self.subTest(changes=changes), self.assertRaises(ValueError): package.validate_qualification(receipt, 'a'*40)

    def test_skipped_failed_or_empty_guard_suites_are_rejected(self):
        for evidence in ({'skipped': 1}, {'status': 'failed'}, {'tests_run': 0}):
            receipt = qualification(); receipt['test_suites']['test_setup_memory_guard'].update(evidence)
            with self.subTest(evidence=evidence), mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaises(ValueError):
                package.validate_qualification(receipt, 'a'*40)

    def test_host_qualification_cannot_claim_device_memory_validation_or_new_runtime_identity(self):
        for name, value in (('physical_setup_memory_validated', True), ('physical_startup_timing_validated', True),
                ('native_client_or_server_recompiled', True), ('runtime_refresh_required', True),
                ('installed_runtime_identity_preserved', False), ('asset_reimport_required', True),
                ('runtime_repository_commit', 'a'*40), ('retained_native_repository_commit', 'a'*40)):
            receipt = qualification(); receipt[name] = value
            with self.subTest(name=name), mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaises(ValueError):
                package.validate_qualification(receipt, 'a'*40)

    def test_qualification_rejects_unsafe_and_changed_source_pins(self):
        for name in ('../foreign.py', '/foreign.py', 'dir\\foreign.py'):
            receipt = qualification(); receipt['source_files'] = {name: pin(b'foreign')}
            with self.subTest(name=name), mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaisesRegex(ValueError, 'Unsafe'):
                package.validate_qualification(receipt, 'a'*40)
        name = 'tools/android/interactive/test_setup_memory_package.py'
        receipt = qualification(); receipt['source_files'] = {name: pin(b'stale')}
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaisesRegex(ValueError, 'changed after verification'):
            package.validate_qualification(receipt, 'a'*40)

    def test_incomplete_source_closure_and_wrong_donor_receipt_fail(self):
        with self.assertRaisesRegex(ValueError, 'source closure'): package.validate_qualification(qualification(), 'a'*40)
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary)/'donor.json'; receipt.write_text('{}')
            with self.assertRaises(ValueError): package.validate_donor_receipt(receipt)

    def test_bad_qualification_prevents_access_to_signing(self):
        args = argparse.Namespace(repository_commit='a'*40, donor_apk=Path('donor.apk'),
            donor_build_report=Path('donor.json'), qualification=Path('qualification.json'))
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), mock.patch.object(package, 'validate_donor', return_value={}), \
                mock.patch.object(package, 'read_json', return_value={}), \
                mock.patch.object(package, 'validate_qualification', side_effect=ValueError('qualification failed')), \
                mock.patch.object(base, 'signing_password_spec') as signer:
            with self.assertRaisesRegex(ValueError, 'qualification failed'): package.build(args)
            signer.assert_not_called()

    def test_actual_binary_manifest_allows_only_two_version_values(self):
        original = 'E: manifest (line=1)\n A: android:versionCode(0x1)=19\n A: android:versionName(0x2)="0.13.4"\n E: application'
        updated = original.replace('line=1', 'line=2').replace('=19', '=20').replace('0.13.4', '0.13.5')
        base = mock.Mock(); base.run.side_effect = (original, updated)
        with mock.patch.object(package, 'builder', return_value=base):
            package.verify_binary_manifest(Path('candidate.apk'), Path('donor.apk'), Path('sdk'))
        base.run.side_effect = (original, updated+'\n E: foreign-activity')
        with mock.patch.object(package, 'builder', return_value=base), self.assertRaisesRegex(ValueError, 'beyond version'):
            package.verify_binary_manifest(Path('candidate.apk'), Path('donor.apk'), Path('sdk'))

    def test_official_signature_requires_retained_signer_and_both_v2_v3(self):
        output = 'Verified using v2 scheme (APK Signature Scheme v2): true\nVerified using v3 scheme (APK Signature Scheme v3): true\nSigner #1 certificate SHA-256 digest: '+package.SIGNER
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), mock.patch.object(base, 'run', return_value=output):
            self.assertEqual(package.SIGNER, package.verify_signature(Path('candidate.apk'), Path('sdk')))
        for invalid in (output.replace(package.SIGNER, '0'*64), output.replace('v2): true', 'v2): false'),
                output.replace('v3): true', 'v3): false')):
            with self.subTest(invalid=invalid), mock.patch.object(package, 'builder', return_value=base), \
                    mock.patch.object(base, 'run', return_value=invalid), self.assertRaises(ValueError):
                package.verify_signature(Path('candidate.apk'), Path('sdk'))

    def test_existing_release_is_never_replaced(self):
        api = mock.Mock(); api.request.return_value = {'id': 42}
        assets = tuple(Path(name) for name in (package.APK_NAME, package.APK_NAME+'.sha256', package.NOTES_NAME))
        with mock.patch.object(package, 'builder', return_value=mock.Mock()), self.assertRaisesRegex(ValueError, 'never replaced'):
            package.publish_release(api, {'repository_commit': 'a'*40}, assets, 'notes')
        self.assertEqual(1, api.request.call_count)

    def test_workflow_qualifies_then_builds_without_any_native_job(self):
        text = (package.ROOT/package.WORKFLOW).read_text()
        self.assertNotIn('windows-', text); self.assertNotIn('cmake ', text); self.assertNotIn('continue-on-error', text)
        self.assertIn('run-id: 37171443387', text); self.assertIn('run-id: 36731428735', text)
        self.assertIn('needs: [qualify]', text); self.assertIn('0.13.5 release', text)
        self.assertEqual(6, len(package.JAVA_CHANGES)); self.assertEqual(1, len(package.JAVA_ADDITIONS))

    def test_qualification_source_closure_binds_java_tests_and_routing(self):
        for name in ('tools/android/test_setup_memory_guard.py', 'tools/android/interactive/test_setup_service.py',
                'tools/android/test_archive.py', '.github/workflows/android-task-receipt-cleanup.yml',
                'docs/android-evidence/setup-memory-0.13.4-user-report.json'):
            self.assertIn(name, package.SOURCE_FILES)
        self.assertTrue(package.JAVA_CHANGES|package.JAVA_ADDITIONS <= package.SOURCE_FILES)


if __name__ == '__main__': unittest.main()
