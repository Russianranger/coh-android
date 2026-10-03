"""Startup-cache packaging cannot change accepted native or player-data scope."""
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

import build_startup_caches_apk as package


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
    for name in ('dbserver-package.tar.gz', 'dbserver-schema.tar.gz', 'game-package.tar.gz'):
        archive = folder/name
        package.shared.write_game_archive(archive, {'retained.bin': b'unchanged-native-data'})
        assets[name] = archive.read_bytes()
    assets.update({'client-runtime.zip': b'unchanged-client-container',
        'client-launcher.exe': b'unchanged-launcher', 'client-caches.zip': b'unchanged-client-caches',
        'native-responsiveness.json': b'{"history":"retained"}',
        'atlas-world-supplement.zip': b'unchanged-world', 'character-avatar-defaults.zip': b'unchanged-avatar',
        'stationary_contact_evidence.py': b'unchanged-contact-capture'})
    (guest/'stationary_contact_evidence.py').write_bytes(assets['stationary_contact_evidence.py'])
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
    cache = folder/'cache'; cache.mkdir()
    manifest = {'native_consumption': {'cache_files_unchanged': True},
                'native_generation': {'native_errors': {'status': 'no_native_data_errors'}}}
    (cache/package.CACHE_ARCHIVE).write_bytes(b'verified-cache-fixture')
    (cache/package.CACHE_MANIFEST).write_text(json.dumps(manifest))
    return checkout, apk, donor, cache, manifest


def repaired(folder, checkout, original, donor, caches, manifest):
    with mock.patch.object(package, 'ROOT', checkout), \
         mock.patch.object(package, 'validate_server_caches', return_value=manifest):
        runtime, pins, _, preflight = package.extract_and_repair(
            original, donor, folder/'unpacked', 'a'*40, caches)
    apk = folder/'repaired.apk'; dex = b'new-dex'
    with zipfile.ZipFile(apk, 'w') as archive:
        for name in pins: archive.write(folder/'unpacked'/name, name)
        for name, raw in {'AndroidManifest.xml': b'new-version', 'classes.dex': dex,
                         'resources.arsc': b'resources', 'res/drawable/ic_coh_client.xml': b'icon'}.items():
            archive.writestr(name, raw)
    return apk, runtime, pins, preflight, pin(dex)


class StartupCachesPackagingTests(unittest.TestCase):
    def test_update_preserves_app_identity_and_advances_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = package.ROOT/'android/interactive/src/main/AndroidManifest.xml'
            original = source.read_bytes(); target = Path(temporary)/'manifest.xml'
            package.repair_android_manifest(source, target)
            package.builder(repaired=True).verify_source_manifest(target)
            self.assertIn(b'android:versionName="0.12.1"', target.read_bytes())
            self.assertIn(b'android:versionCode="14"', target.read_bytes())
            self.assertEqual(original, source.read_bytes())

    def test_only_cache_helpers_manifests_and_tar_extractor_are_authorized(self):
        self.assertEqual(package.REQUIRED_PAYLOADS, package.ALLOWED_PAYLOADS)
        self.assertEqual(6, len(package.ALLOWED_PAYLOADS))
        self.assertEqual({'assets/runtime/'+name for name in
            ('server_cache_package.py', 'server_message_cache_format.py', 'server-caches.zip',
             'server-cache-manifest.json')}, package.ADDED_PAYLOADS)
        self.assertEqual({'android/app/src/main/java/io/github/russianranger/cohdiagnostic/TarExtractor.java'},
                         package.JAVA_CHANGES)
        for name in ('game-package.tar.gz', 'client-runtime.zip', 'native-responsiveness.json',
            'client-launcher.exe', 'client-caches.zip', 'dbserver-package.tar.gz',
            'postgresql-runtime.tar.gz', 'character-avatar-defaults.zip', 'atlas-world-supplement.zip',
            'stationary_contact_evidence.py'):
            self.assertNotIn('assets/runtime/'+name, package.ALLOWED_PAYLOADS|package.ADDED_PAYLOADS)

    def test_actual_guest_archive_preflight_and_payload_manifests_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); checkout, original, donor, caches, manifest = fixture(folder)
            apk, runtime, pins, preflight, dex = repaired(folder, checkout, original, donor, caches, manifest)
            package.verify_derivative(apk, donor, pins, dex)
            self.assertEqual(preflight, package.verify_apk_server_archives(apk))
            self.assertEqual(donor['runtime_manifest']['accepted_base_runtime'], runtime['accepted_base_runtime'])
            for name, expected in donor['payloads'].items():
                if name not in package.ALLOWED_PAYLOADS:
                    self.assertEqual(expected, pins[name])
            for name in package.CACHE_PAYLOADS:
                self.assertEqual(package.builder().file_pin(caches/name), pins['assets/runtime/'+name])
            with zipfile.ZipFile(apk) as archive:
                client = json.loads(archive.read('assets/runtime/client-manifest.json'))
                for name in package.HELPERS|package.GUEST_ADDITIONS|package.CACHE_PAYLOADS:
                    self.assertEqual(client['files'][name], runtime['files'][name])

    def test_native_renderer_world_or_contact_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); checkout, original, donor, caches, manifest = fixture(folder)
            apk, _, pins, _, dex = repaired(folder, checkout, original, donor, caches, manifest)
            for name in ('game-package.tar.gz', 'client-runtime.zip', 'native-responsiveness.json',
                         'client-caches.zip', 'atlas-world-supplement.zip', 'stationary_contact_evidence.py'):
                changed = copy.deepcopy(pins); changed['assets/runtime/'+name]['sha256'] = 'f'*64
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'payload boundaries'):
                    package.verify_derivative(apk, donor, changed, dex)

    def test_unknown_packaged_member_cannot_reach_signing(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); checkout, original, donor, caches, manifest = fixture(folder)
            apk, _, pins, _, dex = repaired(folder, checkout, original, donor, caches, manifest)
            with zipfile.ZipFile(apk, 'a') as archive:
                archive.writestr('assets/runtime/unknown.py', b'unqualified')
            with self.assertRaises(ValueError): package.verify_derivative(apk, donor, pins, dex)

    def test_new_helper_cannot_replace_retained_donor_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); checkout, original, donor, caches, manifest = fixture(folder)
            name = 'assets/runtime/server_cache_package.py'; raw = b'collision'
            with zipfile.ZipFile(original, 'a') as archive: archive.writestr(name, raw)
            donor['payloads'][name] = pin(raw)
            with mock.patch.object(package, 'ROOT', checkout), self.assertRaises(ValueError):
                package.extract_and_repair(original, donor, folder/'unpacked', 'a'*40, caches)

    def test_native_generation_and_consumption_proofs_are_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); folder.joinpath(package.CACHE_ARCHIVE).write_bytes(b'cache')
            for missing in ('native_consumption', 'native_generation'):
                manifest = {'native_consumption': {'cache_files_unchanged': True},
                            'native_generation': {'native_errors': {'status': 'no_native_data_errors'}}}
                del manifest[missing]
                (folder/package.CACHE_MANIFEST).write_text(json.dumps(manifest))
                verifier = SimpleNamespace(verify_archive=mock.Mock(return_value=manifest),
                    verify_generated_package=mock.Mock(return_value=manifest))
                with self.subTest(missing=missing), mock.patch.object(package, 'module', return_value=verifier), \
                     self.assertRaisesRegex(ValueError, 'qualification is incomplete'):
                    package.validate_server_caches(folder)

    def test_external_and_embedded_cache_manifest_must_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); (folder/package.CACHE_MANIFEST).write_text('{"changed":true}')
            for native, embedded in (({'changed': False}, {'changed': False}),
                                      ({'changed': False}, {'changed': True})):
                verifier = SimpleNamespace(verify_archive=mock.Mock(return_value=embedded),
                    verify_generated_package=mock.Mock(return_value=native))
                with self.subTest(native=native, embedded=embedded), \
                     mock.patch.object(package, 'module', return_value=verifier), \
                     self.assertRaisesRegex(ValueError, 'manifests differ'):
                    package.validate_server_caches(folder)

    def test_missing_raw_native_proofs_cannot_pass_even_with_a_valid_guest_envelope(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            verifier = SimpleNamespace(verify_archive=mock.Mock(return_value={}),
                verify_generated_package=mock.Mock(side_effect=ValueError('Raw native proof missing')))
            with mock.patch.object(package, 'module', return_value=verifier), \
                 self.assertRaisesRegex(ValueError, 'Raw native proof'):
                package.validate_server_caches(folder)
            verifier.verify_generated_package.assert_called_once_with(folder)
            verifier.verify_archive.assert_not_called()

    def test_host_qualification_cannot_claim_physical_or_native_acceptance(self):
        receipt = qualification()
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()):
            package.validate_qualification(receipt, 'a'*40)
            for name in ('physical_gameplay_validated', 'physical_startup_timing_validated',
                         'native_runtime_booted', 'dialog_semantics_validated',
                         'native_client_or_server_recompiled', 'long_prior_gameplay_milestones_repeated'):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    package.validate_qualification(dict(receipt, **{name: True}), 'a'*40)

    def test_failed_missing_or_cross_commit_checks_cannot_pass(self):
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()):
            for changed in (dict(qualification(), repository_commit='b'*40),
                            dict(qualification(), checks={}), dict(qualification(), status='failed')):
                with self.assertRaises(ValueError): package.validate_qualification(changed, 'a'*40)

    def test_qualification_paths_cannot_escape_checkout(self):
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()):
            for name in ('../external', '/absolute', 'android\\guest\\helper.py'):
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Unsafe'):
                    package.validate_qualification(dict(qualification(), source_files={name: pin(b'x')}), 'a'*40)

    def test_source_changed_after_qualification_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); path = folder/'helper.py'; path.write_bytes(b'qualified')
            receipt = dict(qualification(), source_files={'helper.py': package.builder().file_pin(path)})
            path.write_bytes(b'changed')
            with mock.patch.object(package, 'ROOT', folder), \
                 mock.patch.object(package, 'SOURCE_FILES', frozenset()), self.assertRaises(ValueError):
                package.validate_qualification(receipt, 'a'*40)

    def test_unapproved_java_input_or_rfb_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); java = folder/'android/interactive/src/main/Test.java'
            java.parent.mkdir(parents=True); java.write_text('original')
            base = package.builder(); old = base.file_pin(java); java.write_text('changed')
            with mock.patch.object(package, 'ROOT', folder), \
                 mock.patch.object(base, 'java_sources', return_value=[java]), \
                 mock.patch.object(package, 'builder', return_value=base), self.assertRaisesRegex(ValueError, 'Java changes exceed'):
                package.current_java_sources({'java_sources': {'android/interactive/src/main/Test.java': old}}, folder/'generated')

    def test_invalid_qualification_stops_build_before_extraction_or_signing(self):
        args = argparse.Namespace(repository_commit='a'*40, donor_apk=Path('donor.apk'),
            donor_build_report=Path('donor.json'), qualification=Path('qualification.json'))
        with mock.patch.object(package, 'validate_donor', return_value={}), \
             mock.patch.object(package, 'read_json', return_value={}), \
             mock.patch.object(package, 'extract_and_repair') as extract:
            with self.assertRaises(ValueError): package.build(args)
            extract.assert_not_called()

    def test_unqualified_real_runtime_archives_stop_before_signer_or_extraction(self):
        args = argparse.Namespace(repository_commit='a'*40, donor_apk=Path('donor.apk'),
            donor_build_report=Path('donor.json'), qualification=Path('qualification.json'),
            runtime_timestamps=Path('runtime-timestamps.json'))
        base = package.builder()
        with mock.patch.object(package, 'builder', return_value=base), \
             mock.patch.object(package, 'validate_donor', return_value={}), \
             mock.patch.object(package, 'validate_qualification', return_value=qualification()), \
             mock.patch.object(package, 'read_json', return_value={}), \
             mock.patch.object(package, 'validate_runtime_timestamps',
                               side_effect=ValueError('Real runtime archive extraction proof required')) as timestamp_gate, \
             mock.patch.object(base, 'signing_password_spec') as password, \
             mock.patch.object(base, 'verify_signing_identity') as signer, \
             mock.patch.object(package, 'extract_and_repair') as extract:
            with self.assertRaisesRegex(ValueError, 'Real runtime archive'):
                package.build(args)
            timestamp_gate.assert_called_once_with({}, 'a'*40)
            password.assert_not_called()
            signer.assert_not_called()
            extract.assert_not_called()

    def test_publication_requires_exact_qualified_runtime_archive_receipt_and_pin(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            receipt = {'format': 1, 'status': 'passed', 'repository_commit': 'a'*40,
                       'fixture': 'publication-gate-only'}
            timestamps = folder/'runtime-timestamps.json'
            timestamps.write_text(json.dumps(receipt))
            args = argparse.Namespace(build_report=folder/'build-report.json',
                donor_apk=folder/'donor.apk', donor_build_report=folder/'donor.json',
                qualification=folder/'qualification.json', runtime_timestamps=timestamps,
                server_caches=folder/'server-caches')
            base = package.builder()
            report = {'format': 1, 'apk': package.APK_NAME, 'repository_commit': 'a'*40,
                'application_id': base.APP_ID, 'version_name': package.VERSION_NAME,
                'version_code': package.VERSION_CODE, 'signer_certificate_sha256': package.SIGNER,
                'signing_key_created': False, 'donor': package.donor_link(),
                'runtime_timestamps': receipt, 'runtime_timestamps_receipt': base.file_pin(timestamps)}
            env = {'GITHUB_REPOSITORY': package.REPOSITORY,
                   'GITHUB_REF': 'refs/heads/'+package.BRANCH,
                   'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_SHA': 'a'*40}
            for field, changed in (('runtime_timestamps', dict(receipt, status='failed')),
                                   ('runtime_timestamps_receipt', pin(b'substituted-proof'))):
                value = dict(report, **{field: changed})
                def read(path):
                    return value if path == args.build_report else receipt
                with self.subTest(field=field), mock.patch.dict(package.os.environ, env), \
                     mock.patch.object(package, 'read_json', side_effect=read), \
                     mock.patch.object(package, 'validate_donor', return_value={}), \
                     mock.patch.object(package, 'validate_server_caches', return_value={}), \
                     mock.patch.object(package, 'validate_qualification', return_value={}), \
                     mock.patch.object(package, 'validate_runtime_timestamps', return_value=receipt), \
                     mock.patch.object(package, 'current_java_sources', return_value=([], {}, [])), \
                     mock.patch.object(package, 'verify_derivative') as verify, \
                     mock.patch.object(package, 'publish_release') as publish:
                    with self.assertRaisesRegex(ValueError, 'build receipt differs'):
                        package.publish(args)
                    verify.assert_not_called()
                    publish.assert_not_called()


if __name__ == '__main__':
    unittest.main()
