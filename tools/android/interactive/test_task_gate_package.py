#!/usr/bin/env python3
"""Packaging boundary and fail-closed proof regressions for the 0.13.0 gate."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import zipfile

import build_task_gate_apk as package


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def qualification():
    return {'format': 1, 'status': 'passed', 'scope': package.QUALIFICATION_SCOPE,
        'repository_commit': 'a'*40, 'donor_apk_sha256': package.DONOR_APK['sha256'],
        'physical_gameplay_validated': False, 'physical_startup_timing_validated': False,
        'native_runtime_booted': False, 'dialog_semantics_validated': False,
        'native_client_or_server_recompiled': False, 'long_prior_gameplay_milestones_repeated': False,
        'tests_run': 250, 'checks': {name: True for name in package.CHECKS}, 'source_files': {}}


def fixture(folder):
    checkout = folder/'source'
    guest = checkout/'android/guest'; guest.mkdir(parents=True)
    assets = {}
    for name in package.HELPERS:
        assets[name] = ('old '+name).encode()
        (guest/name).write_bytes(('new '+name).encode())
    for name in package.GUEST_ADDITIONS:
        (guest/name).write_bytes(('new '+name).encode())
    for name in package.GUEST_DATA_ADDITIONS:
        (guest/name).write_text('{"format":1,"bounded_task_gate":true}')
    for name in ('dbserver-package.tar.gz', 'dbserver-schema.tar.gz', 'game-package.tar.gz'):
        archive = folder/name
        package.shared.write_game_archive(archive, {'retained.bin': b'unchanged-native-data'})
        assets[name] = archive.read_bytes()
    assets.update({'client-runtime.zip': b'unchanged-client-container',
        'client-launcher.exe': b'unchanged-launcher', 'client-caches.zip': b'unchanged-client-caches',
        'server-caches.zip': b'unchanged-exact-93-server-caches',
        'server-cache-manifest.json': b'{"files":93,"native_mapserver":"retained"}',
        'native-responsiveness.json': b'{"history":"retained"}',
        'atlas-world-supplement.zip': b'unchanged-world',
        'character-avatar-defaults.zip': b'unchanged-avatar',
        'server_cache_package.py': b'unchanged-existing-cache-helper'})
    (guest/'server_cache_package.py').write_bytes(assets['server_cache_package.py'])
    client = {'files': {name: pin(raw) for name, raw in assets.items()}}
    assets['client-manifest.json'] = package.shared.encoded(client)
    runtime = {'files': {name: pin(raw) for name, raw in assets.items()},
               'accepted_base_runtime': {'history': 'retained'}}
    assets['runtime-manifest.json'] = package.shared.encoded(runtime)
    payloads = {'assets/runtime/'+name: raw for name, raw in assets.items()}
    payloads.update({name: b'unchanged-arm64-library' for name in package.builder().NATIVE_MEMBERS})
    donor = {'payloads': {name: pin(raw) for name, raw in payloads.items()},
        'runtime_manifest': runtime, 'native_responsiveness': {'history': 'retained'},
        'retained_android_resources': {'resources.arsc': pin(b'resources'),
                                     'res/drawable/ic_coh_client.xml': pin(b'icon')}}
    apk = folder/'donor.apk'
    with zipfile.ZipFile(apk, 'w') as archive:
        for name, raw in payloads.items(): archive.writestr(name, raw)
        for name, raw in {'AndroidManifest.xml': b'old-version', 'classes.dex': b'old-dex',
                         'resources.arsc': b'resources', 'res/drawable/ic_coh_client.xml': b'icon'}.items():
            archive.writestr(name, raw)
    animations = folder/'animations'; animations.mkdir()
    manifest = {'format': 1, 'fixture': 'only native proof verifier is mocked'}
    (animations/package.ANIMATION_ARCHIVE).write_bytes(b'qualified-pigg-fixture')
    (animations/package.ANIMATION_MANIFEST).write_text(json.dumps(manifest))
    return checkout, apk, donor, animations, manifest


def repaired(folder, checkout, original, donor, animations, manifest):
    with mock.patch.object(package, 'ROOT', checkout), \
         mock.patch.object(package, 'validate_animation_pack', return_value=manifest):
        runtime, pins, _, preflight = package.extract_and_repair(
            original, donor, folder/'unpacked', 'a'*40, animations)
    apk = folder/'repaired.apk'; dex = b'new-dex'
    with zipfile.ZipFile(apk, 'w') as archive:
        for name in pins: archive.write(folder/'unpacked'/name, name)
        for name, raw in {'AndroidManifest.xml': b'new-version', 'classes.dex': dex,
                         'resources.arsc': b'resources', 'res/drawable/ic_coh_client.xml': b'icon'}.items():
            archive.writestr(name, raw)
    return apk, runtime, pins, preflight, pin(dex)


class TaskGatePackagingTests(unittest.TestCase):
    def test_update_advances_version_without_source_manifest_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = package.ROOT/'android/interactive/src/main/AndroidManifest.xml'
            original = source.read_bytes(); target = Path(temporary)/'manifest.xml'
            package.repair_android_manifest(source, target)
            package.builder(repaired=True).verify_source_manifest(target)
            self.assertIn(b'android:versionName="0.13.0"', target.read_bytes())
            self.assertIn(b'android:versionCode="15"', target.read_bytes())
            self.assertEqual(original, source.read_bytes())

    def test_immutable_public_donor_and_exact_cache_inputs(self):
        self.assertEqual(package.DONOR_APK, {'bytes': 625055087,
            'sha256': 'fee8880a53916e4ff746d67c8a6ab22f3f0cf2ab7779198cef59035ef4d6bf29'})
        self.assertEqual(package.DONOR_RUN_ID, 37116009802)
        self.assertEqual(package.DONOR_COMMIT, '1fcabfa28f1f32a8c78de2cac496d6647fd376a9')
        self.assertEqual(package.DONOR_BUILD, {'bytes': 182804,
            'sha256': '39c6cf242b3ebcb69ca1e0ed6ab538dc8c5b7c43ac5871c555d158c4a1486340'})
        for name in ('server-caches.zip', 'server-cache-manifest.json', 'server_cache_package.py',
                     'game-package.tar.gz', 'client-runtime.zip', 'client-caches.zip',
                     'native-responsiveness.json', 'atlas-world-supplement.zip',
                     'character-avatar-defaults.zip'):
            self.assertNotIn('assets/runtime/'+name, package.ALLOWED_PAYLOADS|package.ADDED_PAYLOADS)

    def test_only_task_and_animation_additions_are_authorized(self):
        self.assertEqual({'assets/runtime/'+name for name in
            ('task_gate_evidence.py', 'task-gate.json', 'server_animation_package.py',
             'server-animations.pigg', 'server-animation-manifest.json')}, package.ADDED_PAYLOADS)
        self.assertEqual({package.JAVA_ROOT+name+'.java' for name in
            ('ClientActivity', 'ClientRuntime', 'ClientService', 'ClientAcceptance',
             'InteractiveRfbClient')}, package.JAVA_CHANGES)
        self.assertTrue(package.REQUIRED_PAYLOADS < package.ALLOWED_PAYLOADS)
        self.assertEqual({'assets/runtime/client_startup_diagnostic.py'},
                         package.ALLOWED_PAYLOADS-package.REQUIRED_PAYLOADS)

    def test_actual_extraction_manifest_binding_and_all_prior_payloads_retained(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); checkout, original, donor, animations, manifest = fixture(folder)
            apk, runtime, pins, preflight, dex = repaired(folder, checkout, original, donor, animations, manifest)
            package.verify_derivative(apk, donor, pins, dex)
            self.assertEqual(preflight, package.verify_apk_server_archives(apk))
            self.assertIs(runtime['task_gate_required'], True)
            self.assertEqual(donor['runtime_manifest']['accepted_base_runtime'], runtime['accepted_base_runtime'])
            for name, expected in donor['payloads'].items():
                if name not in package.ALLOWED_PAYLOADS:
                    self.assertEqual(expected, pins[name])
            with zipfile.ZipFile(apk) as archive:
                client = json.loads(archive.read('assets/runtime/client-manifest.json'))
                for name in package.HELPERS|package.GUEST_ADDITIONS|package.GUEST_DATA_ADDITIONS|package.ANIMATION_PAYLOADS:
                    self.assertEqual(client['files'][name], runtime['files'][name])

    def test_native_archive_renderer_world_and_existing_cache_mutations_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); checkout, original, donor, animations, manifest = fixture(folder)
            apk, _, pins, _, dex = repaired(folder, checkout, original, donor, animations, manifest)
            for name in ('game-package.tar.gz', 'client-runtime.zip', 'native-responsiveness.json',
                         'client-caches.zip', 'atlas-world-supplement.zip', 'server-caches.zip',
                         'server-cache-manifest.json', 'character-avatar-defaults.zip'):
                changed = copy.deepcopy(pins); changed['assets/runtime/'+name]['sha256'] = 'f'*64
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'payload boundaries'):
                    package.verify_derivative(apk, donor, changed, dex)

    def test_optional_startup_helper_can_remain_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); checkout, original, donor, animations, manifest = fixture(folder)
            name = 'assets/runtime/client_startup_diagnostic.py'
            with zipfile.ZipFile(original) as archive:
                (checkout/'android/guest/client_startup_diagnostic.py').write_bytes(archive.read(name))
            apk, _, pins, _, dex = repaired(folder, checkout, original, donor, animations, manifest)
            self.assertEqual(donor['payloads'][name], pins[name])
            package.verify_derivative(apk, donor, pins, dex)

    def test_unknown_member_cannot_reach_signing(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); checkout, original, donor, animations, manifest = fixture(folder)
            apk, _, pins, _, dex = repaired(folder, checkout, original, donor, animations, manifest)
            with zipfile.ZipFile(apk, 'a') as archive: archive.writestr('assets/runtime/unqualified.py', b'x')
            with self.assertRaises(ValueError): package.verify_derivative(apk, donor, pins, dex)

    def test_added_helper_or_config_cannot_replace_donor_content(self):
        for name in package.GUEST_ADDITIONS|package.GUEST_DATA_ADDITIONS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary); checkout, original, donor, animations, manifest = fixture(folder)
                member = 'assets/runtime/'+name; raw = b'collision'
                with zipfile.ZipFile(original, 'a') as archive: archive.writestr(member, raw)
                donor['payloads'][member] = pin(raw)
                with mock.patch.object(package, 'ROOT', checkout), self.assertRaises(ValueError):
                    package.extract_and_repair(original, donor, folder/'unpacked', 'a'*40, animations)

    def test_raw_native_consumption_proof_required_not_envelope_flags(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            verifier = SimpleNamespace(verify_generated_package=mock.Mock(
                side_effect=ValueError('Actual cold/warm native consumption proof required')))
            with mock.patch.object(package, 'module', return_value=verifier), \
                 self.assertRaisesRegex(ValueError, 'Actual cold/warm native'):
                package.validate_animation_pack(folder)
            verifier.verify_generated_package.assert_called_once_with(folder)

    def test_native_manifest_and_packaged_manifest_must_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); (folder/package.ANIMATION_MANIFEST).write_text('{"changed":true}')
            verifier = SimpleNamespace(verify_generated_package=mock.Mock(return_value={'changed': False}))
            with mock.patch.object(package, 'module', return_value=verifier), \
                 self.assertRaisesRegex(ValueError, 'manifest differ'):
                package.validate_animation_pack(folder)

    def test_native_animation_proof_must_match_candidate_commit(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            manifest = {'repository_commit': 'b'*40}
            (folder/package.ANIMATION_MANIFEST).write_text(json.dumps(manifest))
            verifier = SimpleNamespace(verify_generated_package=mock.Mock(return_value=manifest))
            with mock.patch.object(package, 'module', return_value=verifier), \
                 self.assertRaisesRegex(ValueError, 'source commit differs'):
                package.validate_animation_pack(folder, 'a'*40)

    def test_host_qualification_cannot_claim_physical_native_or_timing_acceptance(self):
        receipt = qualification()
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()):
            package.validate_qualification(receipt, 'a'*40)
            for name in ('physical_gameplay_validated', 'physical_startup_timing_validated',
                         'native_runtime_booted', 'dialog_semantics_validated',
                         'native_client_or_server_recompiled', 'long_prior_gameplay_milestones_repeated'):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    package.validate_qualification(dict(receipt, **{name: True}), 'a'*40)

    def test_failed_missing_or_cross_commit_qualification_rejected(self):
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()):
            for changed in (dict(qualification(), repository_commit='b'*40),
                            dict(qualification(), checks={}), dict(qualification(), status='failed')):
                with self.assertRaises(ValueError): package.validate_qualification(changed, 'a'*40)

    def test_qualification_source_paths_are_bounded(self):
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()):
            for name in ('../external', '/absolute', 'android\\guest\\helper.py'):
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Unsafe'):
                    package.validate_qualification(dict(qualification(), source_files={name: pin(b'x')}), 'a'*40)

    def test_changed_qualified_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); source = folder/'helper.py'; source.write_bytes(b'qualified')
            receipt = dict(qualification(), source_files={'helper.py': package.builder().file_pin(source)})
            source.write_bytes(b'changed')
            with mock.patch.object(package, 'ROOT', folder), \
                 mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaises(ValueError):
                package.validate_qualification(receipt, 'a'*40)

    def test_unapproved_java_input_or_installer_change_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); java = folder/'android/interactive/src/main/Unexpected.java'
            java.parent.mkdir(parents=True); java.write_text('original')
            base = package.builder(); old = base.file_pin(java); java.write_text('changed')
            with mock.patch.object(package, 'ROOT', folder), \
                 mock.patch.object(base, 'java_sources', return_value=[java]), \
                 mock.patch.object(package, 'builder', return_value=base), \
                 self.assertRaisesRegex(ValueError, 'Java changes exceed'):
                package.current_java_sources({'java_sources': {'android/interactive/src/main/Unexpected.java': old}}, folder/'generated')

    def test_publication_binds_animation_proof_to_validated_current_commit(self):
        args = argparse.Namespace(build_report=Path('build-report.json'), donor_apk=Path('donor.apk'),
            donor_build_report=Path('donor.json'), server_animations=Path('animations'))
        env = {'GITHUB_REPOSITORY': package.REPOSITORY,
            'GITHUB_REF': 'refs/heads/'+package.BRANCH, 'GITHUB_EVENT_NAME': 'push', 'GITHUB_SHA': 'a'*40}
        base = package.builder()
        with mock.patch.dict(package.os.environ, env), \
             mock.patch.object(package, 'builder', return_value=base), \
             mock.patch.object(base, 'source_commit', return_value='a'*40) as commit, \
             mock.patch.object(package, 'read_json', return_value={}), \
             mock.patch.object(package, 'validate_donor', return_value={}), \
             mock.patch.object(package, 'validate_animation_pack',
                side_effect=ValueError('Actual native proof is required')) as native, \
             mock.patch.object(package, 'publish_release') as publish:
            with self.assertRaisesRegex(ValueError, 'Actual native proof'):
                package.publish(args)
            commit.assert_called_once_with('a'*40)
            native.assert_called_once_with(args.server_animations, 'a'*40)
            publish.assert_not_called()

    def test_failed_native_proof_stops_before_signer_or_extraction(self):
        args = argparse.Namespace(repository_commit='a'*40, donor_apk=Path('donor.apk'),
            donor_build_report=Path('donor.json'), qualification=Path('qualification.json'),
            server_animations=Path('animations'))
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), \
             mock.patch.object(package, 'validate_donor', return_value={}), \
             mock.patch.object(package, 'validate_qualification', return_value=qualification()), \
             mock.patch.object(package, 'read_json', return_value={}), \
             mock.patch.object(package, 'validate_animation_pack', side_effect=ValueError('Native consumption required')), \
             mock.patch.object(base, 'signing_password_spec') as password, \
             mock.patch.object(base, 'verify_signing_identity') as signer, \
             mock.patch.object(package, 'extract_and_repair') as extract:
            with self.assertRaisesRegex(ValueError, 'Native consumption required'): package.build(args)
            password.assert_not_called(); signer.assert_not_called(); extract.assert_not_called()


if __name__ == '__main__':
    unittest.main()
