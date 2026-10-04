#!/usr/bin/env python3
"""Exercise startup derivative conservation and reject unrelated payload changes."""
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

import build_startup_schedule_apk as package


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def qualification():
    contract = package.module('startup_schedule_test_contract', package.ROOT/package.QUALIFICATION_SCRIPT)
    return {'format': 1, 'status': 'passed', 'scope': package.QUALIFICATION_SCOPE,
        'repository_commit': 'a'*40, 'retained_native_repository_commit': package.RETAINED_NATIVE_COMMIT,
        'donor_apk_sha256': package.DONOR_APK['sha256'], 'physical_gameplay_validated': False,
        'physical_startup_timing_validated': False, 'physical_storage_cleanup_validated': False,
        'physical_fresh_profile_recovery_validated': False, 'native_runtime_booted': False,
        'long_prior_gameplay_milestones_repeated': False, 'native_dbserver_recompiled': True,
        'native_game_or_mapserver_recompiled': False, 'tests_run': len(contract.TEST_MODULES),
        'checks': {name: True for name in package.CHECKS}, 'source_files': {},
        'check_suites': copy.deepcopy(contract.CHECK_SUITES),
        'test_suites': {name: {'tests_run': 1, 'status': 'passed', 'skipped': 0} for name in contract.TEST_MODULES}}


def fixture(folder):
    guest = folder/'android/guest'; guest.mkdir(parents=True)
    assets = {name: ('old-'+name).encode() for name in package.HELPERS}
    for name in package.HELPERS: (guest/name).write_bytes(('new-'+name).encode())
    assets.update({'client-runtime.zip': b'exact-client', 'server-caches.zip': b'exact-93-caches',
        'client-caches.zip': b'exact-texture-caches', 'server-animations.pigg': b'exact-animations',
        'server-animation-manifest.json': package.shared.encoded({'history': 'retained'}),
        'native-responsiveness.json': package.shared.encoded({'history': 'retained'}),
        'atlas-world-supplement.zip': b'exact-world', 'character-avatar-defaults.zip': b'exact-avatar'})
    for name in ('dbserver-package.tar.gz', 'dbserver-schema.tar.gz', 'game-package.tar.gz'):
        source = folder/name; package.shared.write_game_archive(source, {'retained.bin': b'exact-native-bytes'})
        assets[name] = source.read_bytes()
    assets['client-manifest.json'] = package.shared.encoded({'files': {name: pin(raw) for name, raw in assets.items()}})
    runtime = {'repository_commit': package.RETAINED_NATIVE_COMMIT, 'task_gate_required': True,
        'files': {name: pin(raw) for name, raw in assets.items()}, 'scope': 'qualified baseline'}
    assets['runtime-manifest.json'] = package.shared.encoded(runtime)
    payloads = {'assets/runtime/'+name: raw for name, raw in assets.items()}
    payloads.update({name: b'exact-android-native-library' for name in package.builder().NATIVE_MEMBERS})
    donor = {'payloads': {name: pin(raw) for name, raw in payloads.items()},
        'runtime_manifest': runtime, 'native_responsiveness': {'history': 'retained'},
        'server_animation_manifest': {'history': 'retained'}, 'recompiled_dex': pin(b'exact-dex'),
        'retained_android_resources': {'resources.arsc': pin(b'resources'), 'res/drawable/ic_coh_client.xml': pin(b'icon')}}
    apk = folder/'donor.apk'
    with zipfile.ZipFile(apk, 'w') as archive:
        for name, raw in payloads.items(): archive.writestr(name, raw)
        for name, raw in {'AndroidManifest.xml': b'old-manifest', 'classes.dex': b'exact-dex',
                'resources.arsc': b'resources', 'res/drawable/ic_coh_client.xml': b'icon'}.items(): archive.writestr(name, raw)
    donor['server_payload_extraction_preflight'] = package.verify_apk_server_archives(apk)
    native = folder/'native'; native.mkdir()
    document = {'format': 1, 'repository_commit': 'a'*40, 'build_input': {'guarded': True}}
    (native/'DbServer.exe').write_bytes(b'supplemental-native')
    (native/'startup-dbserver-manifest.json').write_bytes(package.shared.encoded(document))
    (native/'CMakeCache.txt').write_bytes(b'exact-build-cache')
    return apk, donor, native, document


@contextlib.contextmanager
def candidate(folder, *, changed=None, extra=None, dex=b'exact-dex'):
    apk, donor, native, document = fixture(folder)
    native_builder = mock.Mock(); native_builder.validate_package.return_value = document
    with mock.patch.object(package, 'ROOT', folder), mock.patch.object(package, 'current_sources', return_value={}), \
         mock.patch.object(package, 'validate_native', return_value=document), mock.patch.object(package, 'native_builder', return_value=native_builder):
        runtime, payloads, _, preflight = package.extract_and_repair(apk, donor, folder/'unpacked', 'a'*40, native)
        output = folder/'candidate.apk'
        with zipfile.ZipFile(output, 'w') as archive:
            for name in payloads:
                raw = (folder/'unpacked'/name).read_bytes()
                archive.writestr(name, changed[1] if changed and name == changed[0] else raw)
            for name, raw in {'AndroidManifest.xml': b'new-manifest', 'classes.dex': dex,
                'resources.arsc': b'resources', 'res/drawable/ic_coh_client.xml': b'icon'}.items(): archive.writestr(name, raw)
            if extra: archive.writestr(extra, b'foreign')
        yield output, apk, donor, native, payloads, runtime, preflight


class StartupSchedulePackagingTests(unittest.TestCase):
    def test_version_only_manifest_keeps_source_unchanged(self):
        source = package.ROOT/'android/interactive/src/main/AndroidManifest.xml'; before = source.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)/'manifest.xml'; package.repair_android_manifest(source, target)
            package.builder(repaired=True).verify_source_manifest(target)
            self.assertIn(b'android:versionName="0.13.3"', target.read_bytes())
            self.assertIn(b'android:versionCode="18"', target.read_bytes())
        self.assertEqual(source.read_bytes(), before)

    def test_exact_baseline_archives_caches_world_avatar_and_dex_retained(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, apk, donor, native, payloads, _, preflight = values
            package.verify_derivative(output, donor, payloads, 'a'*40, native)
            self.assertEqual(preflight, donor['server_payload_extraction_preflight'])
            with zipfile.ZipFile(output) as archive, zipfile.ZipFile(apk) as original:
                for name in donor['payloads']:
                    if name not in package.REPLACED_PAYLOADS: self.assertEqual(archive.read(name), original.read(name))
                self.assertEqual(archive.read('classes.dex'), original.read('classes.dex'))

    def test_four_authored_helpers_and_two_source_bound_native_assets_packaged(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, _, donor, native, payloads, _, _ = values
            self.assertEqual(set(payloads)-set(donor['payloads']), package.ADDED_PAYLOADS)
            self.assertEqual({name for name in donor['payloads'] if payloads[name] != donor['payloads'][name]}, package.REPLACED_PAYLOADS)
            self.assertEqual(len(package.HELPERS), 4)
            package.verify_derivative(output, donor, payloads, 'a'*40, native)

    def test_runtime_sources_identify_new_helpers_without_relabelling_native_history(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, _, donor, native, payloads, runtime, _ = values
            self.assertEqual(runtime['repository_commit'], 'a'*40)
            self.assertEqual(runtime['startup_schedule']['retained_native_repository_commit'], package.RETAINED_NATIVE_COMMIT)
            self.assertEqual(runtime['startup_schedule']['donor_repository_commit'], package.DONOR_COMMIT)
            package.verify_derivative(output, donor, payloads, 'a'*40, native)

    def test_unrelated_payload_replacements_rejected(self):
        for name in ('dbserver-package.tar.gz', 'game-package.tar.gz', 'client-runtime.zip',
                'server-caches.zip', 'client-caches.zip', 'server-animations.pigg',
                'atlas-world-supplement.zip', 'character-avatar-defaults.zip', 'native-responsiveness.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary, \
                 candidate(Path(temporary), changed=('assets/runtime/'+name, b'changed')) as values:
                output, _, donor, native, payloads, _, _ = values
                with self.assertRaises(ValueError): package.verify_derivative(output, donor, payloads, 'a'*40, native)

    def test_recompiled_dex_rejected(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary), dex=b'new-dex') as values:
            output, _, donor, native, payloads, _, _ = values
            with self.assertRaisesRegex(ValueError, 'Android shell'): package.verify_derivative(output, donor, payloads, 'a'*40, native)

    def test_supplemental_native_asset_must_match_checked_package(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, _, donor, native, payloads, _, _ = values
            (native/'DbServer.exe').write_bytes(b'changed-build')
            with self.assertRaisesRegex(ValueError, 'supplemental native asset'): package.verify_derivative(output, donor, payloads, 'a'*40, native)

    def test_current_helper_must_match_packaged_qualified_source(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, _, donor, native, payloads, _, _ = values
            (Path(temporary)/'android/guest/atlas_world_assets.py').write_bytes(b'changed-source')
            with self.assertRaisesRegex(ValueError, 'Authored startup helper'): package.verify_derivative(output, donor, payloads, 'a'*40, native)

    def test_foreign_member_rejected(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary), extra='assets/runtime/foreign.bin') as values:
            output, _, donor, native, payloads, _, _ = values
            with self.assertRaises(ValueError): package.verify_derivative(output, donor, payloads, 'a'*40, native)

    def test_duplicate_member_rejected(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, _, donor, native, payloads, _, _ = values
            with zipfile.ZipFile(output, 'a') as archive, self.assertWarns(UserWarning): archive.writestr('classes.dex', b'exact-dex')
            with self.assertRaisesRegex(ValueError, 'duplicate|Duplicate'): package.verify_derivative(output, donor, payloads, 'a'*40, native)

    def test_manifests_cannot_drift_outside_exact_startup_pins(self):
        with tempfile.TemporaryDirectory() as temporary, candidate(Path(temporary)) as values:
            output, _, donor, native, payloads, _, _ = values
            with zipfile.ZipFile(output) as archive: entries = {name: archive.read(name) for name in archive.namelist()}
            name = 'assets/runtime/client-manifest.json'; manifest = json.loads(entries[name]); manifest['unreviewed'] = True
            entries[name] = package.shared.encoded(manifest); payloads[name] = pin(entries[name])
            with zipfile.ZipFile(output, 'w') as archive:
                for member, raw in entries.items(): archive.writestr(member, raw)
            with self.assertRaisesRegex(ValueError, 'Client manifest drifted'): package.verify_derivative(output, donor, payloads, 'a'*40, native)

    def test_qualification_requires_matching_suite_evidence(self):
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()):
            receipt = qualification()
            self.assertEqual(package.validate_qualification(receipt, 'a'*40)['tests_run'], len(receipt['test_suites']))
            for change in ({'test_suites': {}}, {'tests_run': 2}, {'check_suites': {}},
                    {'test_suites': {'fixture': {'tests_run': 1, 'status': 'passed', 'skipped': 1}}}):
                receipt = qualification(); receipt.update(change)
                with self.subTest(change=change), self.assertRaises(ValueError): package.validate_qualification(receipt, 'a'*40)

    def test_host_qualification_cannot_claim_device_timing_or_native_runtime_acceptance(self):
        for field in ('physical_gameplay_validated', 'physical_startup_timing_validated',
                'physical_fresh_profile_recovery_validated', 'physical_storage_cleanup_validated', 'native_runtime_booted'):
            receipt = qualification(); receipt[field] = True
            with self.subTest(field=field), mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaises(ValueError):
                package.validate_qualification(receipt, 'a'*40)

    def test_qualification_cannot_claim_game_or_mapserver_rebuild(self):
        receipt = qualification(); receipt['native_game_or_mapserver_recompiled'] = True
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaises(ValueError): package.validate_qualification(receipt, 'a'*40)

    def test_mismatched_commit_or_retained_native_source_rejected(self):
        for key, value in (('repository_commit', 'b'*40), ('retained_native_repository_commit', package.DONOR_COMMIT)):
            receipt = qualification(); receipt[key] = value
            with self.subTest(key=key), mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaises(ValueError):
                package.validate_qualification(receipt, 'a'*40)

    def test_unsafe_source_pin_path_rejected(self):
        receipt = qualification(); receipt['source_files'] = {'../outside.py': pin(b'bad')}
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaisesRegex(ValueError, 'Unsafe'):
            package.validate_qualification(receipt, 'a'*40)

    def test_bad_qualification_fails_before_signing(self):
        args = argparse.Namespace(repository_commit='a'*40, donor_apk=Path('donor.apk'),
            donor_build_report=Path('donor.json'), qualification=Path('qualification.json'))
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), mock.patch.object(package, 'validate_donor', return_value={}), \
             mock.patch.object(package, 'read_json', return_value={}), \
             mock.patch.object(package, 'validate_qualification', side_effect=ValueError('qualification failed')), \
             mock.patch.object(base, 'signing_password_spec') as signer:
            with self.assertRaisesRegex(ValueError, 'qualification failed'): package.build(args)
            signer.assert_not_called()

    def test_actual_binary_manifest_permits_only_version_values(self):
        original = 'E: manifest (line=1)\n A: android:versionCode(0x1)=17\n A: android:versionName(0x2)="0.13.2"\n E: application'
        updated = original.replace('line=1', 'line=2').replace('=17', '=18').replace('0.13.2', '0.13.3')
        base = mock.Mock(); base.run.side_effect = (original, updated)
        with mock.patch.object(package.retained, 'builder', return_value=base):
            package.verify_binary_manifest(Path('candidate.apk'), Path('donor.apk'), Path('sdk'))

    def test_actual_binary_manifest_rejects_unrelated_component(self):
        original = 'E: manifest\n A: android:versionCode(0x1)=17\n A: android:versionName(0x2)="0.13.2"\n E: application'
        base = mock.Mock(); base.run.side_effect = (original, original+'\n E: unreviewed-service')
        with mock.patch.object(package.retained, 'builder', return_value=base), self.assertRaisesRegex(ValueError, 'beyond version'):
            package.verify_binary_manifest(Path('candidate.apk'), Path('donor.apk'), Path('sdk'))

    def test_signature_requires_retained_certificate_and_official_v2_v3(self):
        output = 'Verified using v2 scheme (APK Signature Scheme v2): true\nVerified using v3 scheme (APK Signature Scheme v3): true\nSigner #1 certificate SHA-256 digest: '+package.SIGNER
        base = package.retained.builder()
        with mock.patch.object(package.retained, 'builder', return_value=base), mock.patch.object(base, 'run', return_value=output):
            self.assertEqual(package.verify_signature(Path('candidate.apk'), Path('sdk')), package.SIGNER)
        with mock.patch.object(package.retained, 'builder', return_value=base), mock.patch.object(base, 'run', return_value=output.replace(package.SIGNER, '0'*64)), self.assertRaises(ValueError):
            package.verify_signature(Path('candidate.apk'), Path('sdk'))

    def test_existing_release_is_never_replaced(self):
        api = mock.Mock(); api.request.return_value = {'id': 42}
        paths = tuple(Path(name) for name in (package.APK_NAME, package.APK_NAME+'.sha256', package.NOTES_NAME))
        with mock.patch.object(package, 'builder', return_value=mock.Mock()), self.assertRaisesRegex(ValueError, 'never replaced'):
            package.publish_release(api, {'repository_commit': 'a'*40}, paths, 'notes')
        self.assertEqual(api.request.call_count, 1)

    def test_new_pipeline_is_normal_dbserver_only_and_retains_signer(self):
        text = (package.ROOT/package.WORKFLOW).read_text()
        self.assertIn('--config OptDebug --target DbServer --parallel', text)
        self.assertNotIn('--target Game', text); self.assertNotIn('COH_PG_PERSISTENCE_TESTS=ON', text)
        self.assertIn('run-id: 36731428735', text)
        self.assertIn('run-id: 37147463123', text)
        self.assertNotIn('continue-on-error', text)


if __name__ == '__main__': unittest.main()
