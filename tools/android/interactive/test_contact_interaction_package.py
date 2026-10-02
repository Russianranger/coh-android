"""Prove source-only contact packaging keeps native/history/data boundaries."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import urllib.error
import zipfile

import build_contact_interaction_apk as package


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def fixture(folder):
    checkout = folder/'source'; guest = checkout/'android/guest'; guest.mkdir(parents=True)
    assets = {}
    for name in package.HELPERS:
        assets[name] = ('old '+name).encode(); (guest/name).write_bytes(('new '+name).encode())
    for name in package.GUEST_ADDITIONS: (guest/name).write_bytes(('new '+name).encode())
    for name in ('dbserver-package.tar.gz', 'dbserver-schema.tar.gz', 'game-package.tar.gz'):
        archive = folder/name; package.shared.write_game_archive(archive, {'retained.bin': b'native-data'})
        assets[name] = archive.read_bytes()
    assets.update({'client-runtime.zip': b'retained-client-container', 'client-launcher.exe': b'retained-launcher',
                   'client-caches.zip': b'retained-caches', 'native-responsiveness.json': b'{"history":"retained"}'})
    client = {'files': {name: pin(raw) for name, raw in assets.items()}}
    assets['client-manifest.json'] = package.shared.encoded(client)
    runtime = {'files': {name: pin(raw) for name, raw in assets.items()}, 'accepted_base_runtime': {'history': 'retained'}}
    assets['runtime-manifest.json'] = package.shared.encoded(runtime)
    payloads = {'assets/runtime/'+name: raw for name, raw in assets.items()}
    payloads.update({name: b'retained-arm64-library' for name in package.builder().NATIVE_MEMBERS})
    donor = {'payloads': {name: pin(raw) for name, raw in payloads.items()}, 'runtime_manifest': runtime,
             'native_responsiveness': {'history': 'retained'},
             'retained_android_resources': {'resources.arsc': pin(b'resources'), 'res/drawable/ic_coh_client.xml': pin(b'icon')}}
    apk = folder/'donor.apk'
    with zipfile.ZipFile(apk, 'w') as archive:
        for name, raw in payloads.items(): archive.writestr(name, raw)
        for name, raw in {'AndroidManifest.xml': b'original', 'classes.dex': b'old-dex',
                          'resources.arsc': b'resources', 'res/drawable/ic_coh_client.xml': b'icon'}.items():
            archive.writestr(name, raw)
    return checkout, apk, donor


def repaired_apk(folder, checkout, original, donor):
    with mock.patch.object(package, 'ROOT', checkout):
        runtime, pins, retained, preflight = package.extract_and_repair(original, donor, folder/'unpacked', 'a'*40)
    apk = folder/'repaired.apk'; dex = b'new-dex'
    with zipfile.ZipFile(apk, 'w') as archive:
        for name in pins: archive.write(folder/'unpacked'/name, name)
        for name, raw in {'AndroidManifest.xml': b'version-update', 'classes.dex': dex,
                          'resources.arsc': b'resources', 'res/drawable/ic_coh_client.xml': b'icon'}.items():
            archive.writestr(name, raw)
    return apk, runtime, pins, preflight, pin(dex)


class ContactPackagingTests(unittest.TestCase):
    def test_manifest_advances_version_without_changing_app_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = package.ROOT/'android/interactive/src/main/AndroidManifest.xml'
            original = source.read_bytes(); target = Path(temporary)/'manifest.xml'
            package.repair_android_manifest(source, target)
            package.builder(repaired=True).verify_source_manifest(target)
            self.assertIn(b'android:versionName="0.12.0"', target.read_bytes())
            self.assertIn(b'android:versionCode="13"', target.read_bytes())
            self.assertEqual(original, source.read_bytes())

    def test_mutation_scope_has_only_three_guests_manifests_and_one_export_helper(self):
        self.assertEqual(package.REQUIRED_PAYLOADS, package.ALLOWED_PAYLOADS)
        self.assertEqual(5, len(package.ALLOWED_PAYLOADS))
        self.assertEqual({'assets/runtime/stationary_contact_evidence.py'}, package.ADDED_PAYLOADS)
        for name in ('game-package.tar.gz', 'client-runtime.zip', 'native-responsiveness.json', 'client-launcher.exe',
                     'client-caches.zip', 'dbserver-package.tar.gz', 'postgresql-runtime.tar.gz',
                     'character-avatar-defaults.zip', 'atlas-world-supplement.zip'):
            self.assertNotIn('assets/runtime/'+name, package.ALLOWED_PAYLOADS|package.ADDED_PAYLOADS)
        self.assertEqual(5, len(package.JAVA_CHANGES))
        for name in ('InteractiveRfbClient.java', 'TarExtractor.java', 'ClientInput.java'):
            self.assertFalse(any(path.endswith('/'+name) for path in package.JAVA_CHANGES))

    def test_real_guest_preflight_preserves_canonical_native_archives_and_cache_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); checkout, original, donor = fixture(folder)
            apk, runtime, pins, preflight, dex = repaired_apk(folder, checkout, original, donor)
            package.verify_derivative(apk, donor, pins, dex)
            self.assertEqual(preflight, package.verify_apk_server_archives(apk))
            self.assertEqual(set(donor['payloads'])|package.ADDED_PAYLOADS, set(pins))
            for name, expected in donor['payloads'].items():
                if name not in package.ALLOWED_PAYLOADS: self.assertEqual(expected, pins[name])
            self.assertEqual(donor['runtime_manifest']['accepted_base_runtime'], runtime['accepted_base_runtime'])

    def test_changed_native_cache_driver_or_world_pin_cannot_be_authorized(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); checkout, original, donor = fixture(folder)
            apk, runtime, pins, preflight, dex = repaired_apk(folder, checkout, original, donor)
            for name in ('game-package.tar.gz', 'client-runtime.zip', 'native-responsiveness.json', 'client-caches.zip'):
                changed = copy.deepcopy(pins); changed['assets/runtime/'+name]['sha256'] = 'f'*64
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'source-only payload boundaries'):
                    package.verify_derivative(apk, donor, changed, dex)

    def test_packaged_extra_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); checkout, original, donor = fixture(folder)
            apk, runtime, pins, preflight, dex = repaired_apk(folder, checkout, original, donor)
            with zipfile.ZipFile(apk, 'a') as archive: archive.writestr('assets/runtime/unknown.py', b'unknown')
            with self.assertRaises(ValueError): package.verify_derivative(apk, donor, pins, dex)

    def test_new_helper_cannot_overwrite_a_donor_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); checkout, original, donor = fixture(folder)
            name = 'assets/runtime/stationary_contact_evidence.py'; raw = b'collision'
            with zipfile.ZipFile(original, 'a') as archive: archive.writestr(name, raw)
            donor['payloads'][name] = pin(raw)
            with mock.patch.object(package, 'ROOT', checkout), self.assertRaises(ValueError):
                package.extract_and_repair(original, donor, folder/'unpacked', 'a'*40)

    def test_a_server_archive_metadata_regression_stops_packaging(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); checkout, original, donor = fixture(folder)
            broken = folder/'broken.tar.gz'
            import tarfile, io
            with tarfile.open(broken, 'w:gz') as archive:
                entry = tarfile.TarInfo('file'); entry.mode = 0o644; entry.mtime = 1767225600; entry.size = 1
                archive.addfile(entry, io.BytesIO(b'x'))
            name = 'assets/runtime/game-package.tar.gz'; raw = broken.read_bytes()
            replacement = folder/'broken.apk'
            with zipfile.ZipFile(original) as source, zipfile.ZipFile(replacement, 'w') as destination:
                for entry in source.infolist(): destination.writestr(entry.filename, raw if entry.filename == name else source.read(entry))
            donor['payloads'][name] = pin(raw)
            with mock.patch.object(package, 'ROOT', checkout), self.assertRaisesRegex(Exception, 'archive metadata differs'):
                package.extract_and_repair(replacement, donor, folder/'unpacked', 'a'*40)

    def test_qualification_cannot_claim_dialog_semantics_or_new_native_execution(self):
        receipt = {'format': 1, 'status': 'passed', 'scope': package.QUALIFICATION_SCOPE, 'repository_commit': 'a'*40,
            'donor_apk_sha256': package.DONOR_APK['sha256'], 'physical_gameplay_validated': False,
            'native_runtime_booted': False, 'dialog_semantics_validated': False, 'native_client_or_server_recompiled': False,
            'tests_run': 50, 'checks': {name: True for name in package.CHECKS}, 'source_files': {}}
        with mock.patch.object(package, 'SOURCE_FILES', frozenset()):
            package.validate_qualification(receipt, 'a'*40)
            for name in ('physical_gameplay_validated', 'native_runtime_booted', 'dialog_semantics_validated', 'native_client_or_server_recompiled'):
                changed = dict(receipt, **{name: True})
                with self.subTest(name=name), self.assertRaises(ValueError): package.validate_qualification(changed, 'a'*40)

    def test_unqualified_or_wrong_donor_receipt_cannot_reach_build_signing(self):
        args = argparse.Namespace(repository_commit='a'*40, donor_apk=Path('donor.apk'), donor_build_report=Path('donor.json'), qualification=Path('qualification.json'))
        with mock.patch.object(package, 'validate_donor', return_value={}), \
             mock.patch.object(package, 'read_json', return_value={}), \
             mock.patch.object(package, 'extract_and_repair') as extract:
            with self.assertRaises(ValueError): package.build(args)
            extract.assert_not_called()

    def test_java_inventory_refuses_unapproved_rfb_or_extractor_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); java = folder/'android/interactive/src/main/Test.java'; java.parent.mkdir(parents=True); java.write_text('original')
            base = package.builder(); original = base.file_pin(java); java.write_text('unexpected change')
            with mock.patch.object(package, 'ROOT', folder), mock.patch.object(package, 'JAVA_CHANGES', frozenset()), \
                 mock.patch.object(base, 'java_sources', return_value=[java]), mock.patch.object(package, 'builder', return_value=base):
                with self.assertRaisesRegex(ValueError, 'Java changes exceed'):
                    package.current_java_sources({'java_sources': {'android/interactive/src/main/Test.java': original}}, folder/'generated')

    def test_release_upload_mismatch_is_never_published_and_body_has_no_new_native_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            assets = tuple(folder/name for name in (package.APK_NAME, package.APK_NAME+'.sha256', package.NOTES_NAME))
            for path in assets: path.write_bytes(b'test')
            report = dict(package.builder().file_pin(assets[0]), repository_commit='a'*40)
            api = mock.Mock()
            def request(path, data=None, **kwargs):
                if path.startswith(('/releases/tags/', '/git/ref/tags/')):
                    raise urllib.error.HTTPError('https://api.github.com', 404, 'Not Found', {}, None)
                if path == '/releases':
                    self.assertIn('optional-recovery and contact evidence qualification', data['body'])
                    self.assertNotIn('native build', data['body'])
                    return {'id': 1, 'draft': True, 'prerelease': True, 'tag_name': package.RELEASE_TAG}
                return {'state': 'uploaded', 'name': data.name, 'size': data.stat().st_size, 'digest': 'sha256:'+'f'*64}
            api.request.side_effect = request
            with self.assertRaises(ValueError): package.publish_release(api, report, assets, 'notes')
            self.assertFalse(any(call.kwargs.get('method') == 'PATCH' for call in api.request.call_args_list))


if __name__ == '__main__': unittest.main()
