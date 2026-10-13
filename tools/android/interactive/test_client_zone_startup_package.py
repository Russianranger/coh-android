"""Real public donor authentication and finite successor source/assembly gates."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import build_client_zone_startup_apk as package
import classify_client_zone_startup_change as owner


class ClientZoneStartupPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        recovery = Path('/workspace/scratch/5d16603ca7ff/publication-037-evidence')
        cls.apk = Path(os.environ.get('COH_ZONE_STARTUP_TEST_DONOR_APK', recovery/package.DONOR_APK_NAME))
        cls.report = Path(os.environ.get('COH_ZONE_STARTUP_TEST_DONOR_REPORT', recovery/package.DONOR_REPORT_NAME))
        if not cls.apk.is_file() or not cls.report.is_file():
            raise AssertionError('Authenticated actual public .36 APK and receipt required; no skips')
        cls.donor = package.validate_donor(cls.apk, cls.report, check_sources=False)

    def marker(self):
        value = package.read_json(package.ROOT/package.MARKER)
        value.update(qualification_enabled=False, publish_enabled=False, reviewed_source_integrated=False)
        value['native_promotions'] = {'game': {'enabled': False}, 'mapserver': {'enabled': False}}
        return value

    def test_exact_monotonic_public_donor_and_signer(self):
        self.assertEqual((package.VERSION_NAME, package.VERSION_CODE), ('0.13.37', 52))
        self.assertEqual(package.DONOR_COMMIT, '3570430cefdb15d9b239563e85cccf4d8fe6f32e')
        self.assertEqual(package.DONOR_RUN_ID, 38346809297)
        self.assertEqual(self.donor['sha256'], package.DONOR_APK['sha256'])
        self.assertEqual(self.donor['signer_certificate_sha256'], package.SIGNER)
        self.assertTrue(self.donor['all_native_member_bytes_retained'])

    def test_donor_mutation_rejected_before_source_admission(self):
        with tempfile.TemporaryDirectory() as temporary:
            changed = Path(temporary)/'report.json'
            raw = self.report.read_bytes(); changed.write_bytes(raw+b' ')
            with self.assertRaises(ValueError): package.validate_donor(self.apk, changed, check_sources=False)

    def test_scaffold_and_unqualified_promotions_are_disabled(self):
        value = self.marker(); package.validate_release_marker(value)
        self.assertFalse(value['qualification_enabled'])
        self.assertFalse(value['publish_enabled'])
        with self.assertRaises(ValueError): package.validate_release_marker(value, qualification=True)
        for name in ('game', 'mapserver'):
            changed = copy.deepcopy(value); changed['native_promotions'][name]['enabled'] = True
            with self.subTest(name=name), self.assertRaises(ValueError): package.validate_release_marker(changed)

    def test_publication_requires_reviewed_current_qualification(self):
        value = self.marker(); value.update(publish_enabled=True, qualification_enabled=True)
        with self.assertRaises(ValueError): package.validate_release_marker(value, publication=True)
        value['reviewed_source_integrated'] = True
        package.validate_release_marker(value, publication=True)
        value['version_code'] = True
        with self.assertRaises(ValueError): package.validate_release_marker(value)

    def test_exact_reviewed_java_census_and_changed_guest(self):
        java = package.current_sources(self.donor)
        self.assertEqual(len(java), 24)
        self.assertEqual(package.changed_java_sources(self.donor), sorted(package.REVIEWED_JAVA_CHANGES))
        self.assertEqual(package.added_java_sources(self.donor), [])
        self.assertEqual(package.replacement_payloads(self.donor), frozenset({
            'assets/runtime/client-manifest.json', 'assets/runtime/runtime-manifest.json',
            'assets/runtime/game_device_diagnostic.py'}))

    def test_unreviewed_existing_java_change_rejected(self):
        native = package.builder()
        target = next(name for name in self.donor['java_sources'] if name not in package.REVIEWED_JAVA_CHANGES)
        original = native.file_pin
        def changed(path):
            value = original(path)
            return {'bytes': value['bytes']+1, 'sha256': value['sha256']} if Path(path)==package.ROOT/target else value
        with patch.object(native, 'file_pin', side_effect=changed), patch.object(package, 'builder', return_value=native):
            with self.assertRaises(ValueError): package.current_sources(self.donor)

    def test_actual_archive_reconstruction_preserves_all_native_bytes_and_ancestry(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            native_dir = work/'native'
            native = package.extract_retained_launcher(self.apk, self.donor, native_dir)
            candidate = work/'candidate'
            runtime, payloads, proof = package.extract_and_repair(self.apk, self.donor,
                candidate, package.DONOR_COMMIT, native_dir, native, execute_preflight=False)
            self.assertEqual(proof['server_archives'], self.donor['package_preflight']['server_archives'])
            self.assertFalse(proof['native_metadata_admission']['new_native_consumer_admitted'])
            self.assertEqual(runtime['client_startup_latency'], self.donor['runtime_manifest']['client_startup_latency'])
            self.assertEqual(runtime['client_bundle'], self.donor['runtime_manifest']['client_bundle'])
            with zipfile.ZipFile(self.apk) as old:
                for name in self.donor['payloads']:
                    if name not in package.replacement_payloads(self.donor):
                        self.assertEqual((candidate/name).read_bytes(), old.read(name), name)
            self.assertEqual({name for name in payloads if payloads[name] != self.donor['payloads'][name]},
                set(package.replacement_payloads(self.donor)))

    def test_finite_owner_rejects_unknown_paths_and_ambiguous_ancestry(self):
        before, head = '1'*40, '2'*40
        paths = [package.MARKER, 'android/guest/game_device_diagnostic.py']
        self.assertTrue(owner.client_zone_startup_owned('push', before, head, before, paths))
        for changed in (paths+['Client.exe'], paths+['android/guest/unknown.py'], [None], ['../escape']):
            with self.subTest(paths=changed): self.assertFalse(owner.client_zone_startup_owned('push', before, head, before, changed))
        self.assertFalse(owner.client_zone_startup_owned('pull_request', before, head, before, paths))
        self.assertFalse(owner.client_zone_startup_owned('push', before, head, '3'*40, paths))

    def test_documentation_owner_requires_successor_publication_receipt(self):
        args = ('push', '1'*40, '2'*40, '1'*40)
        self.assertFalse(owner.client_zone_startup_owned(*args, ['docs/HANDOFF.md']))
        self.assertTrue(owner.client_zone_startup_owned(*args,
            ['docs/HANDOFF.md', owner.CLIENT_ZONE_STARTUP_PUBLICATION]))


if __name__ == '__main__': unittest.main()
