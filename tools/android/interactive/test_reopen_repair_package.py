"""Exercise canonical extraction and bind the repair to reused native history."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'android/guest')]
import build_reopen_repair_apk as repair
import build_responsiveness_apk as original
import local_login_server as guest


def archive(path, entries):
    with tarfile.open(path, 'w:gz') as output:
        for name, raw, attributes in entries:
            info = tarfile.TarInfo(name); info.size = len(raw); info.mode = 0o644
            for key, value in attributes.items(): setattr(info, key, value)
            output.addfile(info, io.BytesIO(raw) if info.isfile() else None)


class RepairPackageTests(unittest.TestCase):
    def test_repair_configuration_preserves_historical_builder_defaults(self):
        self.assertEqual(('0.11.6', 12), (repair.CORE.VERSION_NAME, repair.CORE.VERSION_CODE))
        self.assertEqual(('0.11.5', 11), (original.VERSION_NAME, original.VERSION_CODE))
        self.assertFalse(repair.CORE.CLIENT_OR_SERVER_RECOMPILED)
        self.assertTrue(original.CLIENT_OR_SERVER_RECOMPILED)
        self.assertEqual(repair.JAVA_CHANGES - original.JAVA_CHANGES,
                         {'android/app/src/main/java/io/github/russianranger/cohdiagnostic/TarExtractor.java'})
        for path in ('assets/runtime/client-caches.zip', 'assets/runtime/character-avatar-defaults.zip',
                     'assets/runtime/dbserver-package.tar.gz', 'assets/runtime/dbserver-schema.tar.gz'):
            self.assertNotIn(path, repair.ALLOWED_PAYLOADS)

    def test_repair_manifest_keeps_identity_and_advances_installable_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = ROOT/'android/interactive/src/main/AndroidManifest.xml'
            previous = source.read_bytes(); target = Path(temporary)/'manifest.xml'
            repair.repair_android_manifest(source, target)
            repair.builder(repaired=True).verify_source_manifest(target)
            self.assertIn(b'android:versionName="0.11.6"', target.read_bytes())
            self.assertIn(b'android:versionCode="12"', target.read_bytes())
            self.assertEqual(previous, source.read_bytes())

    def test_canonical_writer_passes_the_actual_guest_extractor(self):
        members = {'MapServer.exe': b'MZtest', 'game-package.json': b'{}'}
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); source = folder/'game.tar.gz'; destination = folder/'unpacked'
            repair.write_game_archive(source, members)
            guest.extract_regular(source, destination)
            self.assertEqual(members, {path.name: path.read_bytes() for path in destination.iterdir()})
            with tarfile.open(source, 'r:gz') as packed:
                self.assertEqual(sorted(members), [entry.name for entry in packed.getmembers()])
                for entry in packed.getmembers():
                    self.assertEqual((0, 0, 0, 0o644, '', '', {}),
                        (entry.uid, entry.gid, entry.mtime, entry.mode, entry.uname, entry.gname, entry.pax_headers))

    def test_all_three_server_archives_are_consumed_and_counted(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            names = ('dbserver-package.tar.gz', 'dbserver-schema.tar.gz', 'game-package.tar.gz')
            for name in names: repair.write_game_archive(folder/name, {'file': b'payload'})
            proof = repair.verify_server_archives(folder)
            self.assertEqual('passed', proof['status'])
            self.assertEqual(set(names), set(proof['archives']))
            for name in names:
                pin = repair.builder().file_pin(folder/name)
                self.assertEqual(dict(pin, file_count=1, extracted_bytes=7), proof['archives'][name])

    def test_the_reported_prior_timestamp_is_rejected_before_any_file_is_written(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); source = folder/'game.tar.gz'; destination = folder/'unpacked'
            archive(source, [('MapServer.exe', b'MZtest', {'mtime': 1767225600})])
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'Server payload archive metadata differs'):
                guest.extract_regular(source, destination)
            self.assertFalse(any(destination.iterdir()))

    def test_canonical_fix_does_not_relax_metadata_or_path_guards(self):
        cases = [
            [('file', b'x', {'uid': 1})], [('file', b'x', {'gid': 1})],
            [('file', b'x', {'mode': 0o755})], [('file', b'x', {'uname': 'owner'})],
            [('file', b'x', {'pax_headers': {'comment': 'unexpected'}})],
            [('../escape', b'x', {})], [('/escape', b'x', {})],
            [('file', b'', {'type': tarfile.SYMTYPE, 'linkname': '../escape'})],
            [('A', b'x', {}), ('a', b'y', {})],
            [('file', b'x', {}), ('file', b'y', {})],
            [('z', b'x', {}), ('a', b'y', {})],
        ]
        for entries in cases:
            with self.subTest(entries=entries), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary); source = folder/'game.tar.gz'
                archive(source, entries)
                with self.assertRaises(guest.base.DiagnosticError):
                    guest.extract_regular(source, folder/'unpacked')
                self.assertFalse((folder.parent/'escape').exists())

    def test_three_archive_preflight_rejects_a_bad_game_even_when_the_other_two_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            for name in ('dbserver-package.tar.gz', 'dbserver-schema.tar.gz'):
                repair.write_game_archive(folder/name, {'file': b'payload'})
            archive(folder/'game-package.tar.gz', [('file', b'x', {'mtime': 1767225600})])
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'Server payload archive metadata differs'):
                repair.verify_server_archives(folder)

    def test_build_refuses_an_unbound_prior_failure_before_build_or_signing(self):
        args = argparse.Namespace(native_commit=repair.NATIVE_COMMIT,
                                  prior_apk=Path('prior.apk'), qualification=Path('qualification.json'))
        with mock.patch.object(repair, 'reproduce_prior_archive_failure', return_value={'status': 'reproduced'}), \
             mock.patch.object(repair.CORE, 'read_json', return_value={'prior_archive_failure': {'status': 'different'}}), \
             mock.patch.object(repair.CORE, 'build') as build:
            with self.assertRaisesRegex(ValueError, 'exact public 0.11.5 archive rejection'): repair.build(args)
            build.assert_not_called()

    def test_build_refuses_replacing_the_retained_native_run(self):
        args = argparse.Namespace(native_commit='f'*40)
        with mock.patch.object(repair.CORE, 'build') as build, \
             mock.patch.object(repair, 'reproduce_prior_archive_failure') as reproduction:
            with self.assertRaisesRegex(ValueError, 'already published 0.11.5 native build'): repair.build(args)
            build.assert_not_called(); reproduction.assert_not_called()

    def test_native_reuse_rejects_changed_actual_executable_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary); prior = folder/'prior.apk'; prior.write_bytes(b'prior')
            pins = {name: {'bytes': 8, 'sha256': hashlib.sha256(b'retained').hexdigest()}
                    for name in ('CityOfHeroes.exe', 'MapServer.exe')}
            for name in pins: (folder/name).write_bytes(b'retained')
            base = repair.builder()
            checked = base.checked_file
            def check(path, pin=None):
                if path == prior: return checked(path)
                return checked(path, pin)
            base.checked_file = check
            run = {'run_url': 'https://github.com/Russianranger/coh-android/actions/runs/'+str(repair.NATIVE_RUN_ID)}
            with mock.patch.object(repair.CORE, 'builder', return_value=base), \
                 mock.patch.object(repair, 'native_bytes', return_value=pins), \
                 mock.patch.object(repair.CORE.native_package, 'validate_package', return_value=run):
                for changed in pins:
                    with self.subTest(changed=changed):
                        (folder/changed).write_bytes(b'changed!')
                        with self.assertRaises(ValueError):
                            repair.verify_native_reuse(prior, native_directory=folder)
                        (folder/changed).write_bytes(b'retained')

    def test_publish_rechecks_actual_archive_and_native_proof_before_delegating(self):
        args = argparse.Namespace(build_report=Path('report.json'), prior_apk=Path('prior.apk'), apk=Path('repair.apk'))
        expected = {'prior_archive_failure': {'status': 'reproduced'},
                    'native_build_reused': {'files': 'retained'},
                    'actual_guest_archive_extraction': {'status': 'passed'}}
        with mock.patch.object(repair, 'reproduce_prior_archive_failure', return_value=expected['prior_archive_failure']), \
             mock.patch.object(repair, 'verify_native_reuse', return_value=expected['native_build_reused']), \
             mock.patch.object(repair, 'verify_apk_server_archives', return_value=expected['actual_guest_archive_extraction']), \
             mock.patch.object(repair.CORE, 'publish') as publish:
            for mutate in ('actual_guest_archive_extraction', 'native_build_reused'):
                evidence = copy.deepcopy(expected); evidence[mutate] = {'status': 'changed'}
                with mock.patch.object(repair.CORE, 'read_json', return_value={
                        'reopen_repair': evidence, 'client_or_server_recompiled_this_build': False}):
                    with self.assertRaisesRegex(ValueError, 'independently verified'): repair.publish(args)
            publish.assert_not_called()


if __name__ == '__main__': unittest.main()
