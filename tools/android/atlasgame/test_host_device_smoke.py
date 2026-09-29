"""Boundary and provenance checks for the combined APK import/runtime gate."""
import copy
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

import host_device_smoke as host


class ApkExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def apk(self, *, extra=None, duplicate=None, symlink=None, manifest=None):
        manifest = manifest or {'format': 1, 'files': {'diagnostic.py': {'bytes': 1, 'sha256': 'a' * 64}}}
        members = {'assets/runtime/runtime-manifest.json': json.dumps(manifest),
                   'assets/runtime/diagnostic.py': b'x', 'classes.dex': b'dex'}
        members.update({'assets/atlas/' + name: b'import' for name in host.package.PACKAGE_FILES})
        members.update(extra or {})
        path = self.root / 'candidate.apk'
        with zipfile.ZipFile(path, 'w') as archive:
            for name, content in members.items():
                if name == symlink:
                    entry = zipfile.ZipInfo(name)
                    entry.create_system = 3
                    entry.external_attr = (stat.S_IFLNK | 0o777) << 16
                    archive.writestr(entry, content)
                else:
                    archive.writestr(name, content)
            if duplicate:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    archive.writestr(duplicate, members[duplicate])
        return path

    def test_extracts_exact_both_asset_sets_without_extracting_code(self):
        paths = host.extract_apk_assets(self.apk(), self.root / 'assets')
        self.assertEqual(set(paths), {'runtime', 'atlas'})
        self.assertEqual({p.name for p in paths['atlas'].iterdir()}, set(host.package.PACKAGE_FILES))
        self.assertEqual((paths['runtime'] / 'diagnostic.py').read_bytes(), b'x')
        self.assertFalse((self.root / 'assets/classes.dex').exists())

    def test_extra_or_escape_asset_is_rejected_before_any_write(self):
        for name in ('assets/unreviewed.dat', 'assets/atlas/../escape', 'assets/runtime/extra.py'):
            with self.subTest(name=name):
                destination = self.root / 'assets'
                with self.assertRaisesRegex(RuntimeError, 'asset set'):
                    host.extract_apk_assets(self.apk(extra={name: b'bad'}), destination)
                self.assertFalse(destination.exists())

    def test_duplicate_apk_member_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'Duplicate APK'):
            host.extract_apk_assets(self.apk(duplicate='classes.dex'), self.root / 'assets')

    def test_linked_import_and_runtime_payloads_are_rejected(self):
        for name in ('assets/runtime/diagnostic.py', 'assets/atlas/' + host.package.TEXT_ARCHIVE):
            with self.subTest(name=name), self.assertRaisesRegex(RuntimeError, 'Linked'):
                host.extract_apk_assets(self.apk(symlink=name), self.root / 'assets')
            self.assertFalse((self.root / 'assets').exists())

    def test_nonflat_runtime_and_aggregate_budget_are_rejected(self):
        manifest = {'format': 1, 'files': {'../escape': {'bytes': 1, 'sha256': 'a' * 64}}}
        with self.assertRaisesRegex(RuntimeError, 'Unsafe'):
            host.extract_apk_assets(self.apk(manifest=manifest), self.root / 'assets')
        with mock.patch.object(host, 'MAX_APK_ASSETS', 32):
            with self.assertRaisesRegex(RuntimeError, 'extraction budget'):
                host.extract_apk_assets(self.apk(), self.root / 'assets')

    def test_existing_output_cannot_be_overwritten(self):
        output = self.root / 'assets'
        output.mkdir()
        (output / 'preserved').write_bytes(b'keep')
        with self.assertRaisesRegex(RuntimeError, 'must be new'):
            host.extract_apk_assets(self.apk(), output)
        self.assertEqual((output / 'preserved').read_bytes(), b'keep')


class AdapterTests(unittest.TestCase):
    def sample(self):
        imported = {'generation': 'generation-' + 'a' * 32, 'contract_sha256': 'b' * 64,
                    'receipt_sha256': 'c' * 64, 'file_count': 173011, 'total_bytes': 2977730517}
        runtime = {'files': {name: {'sha256': str(number) * 64}
                            for number, name in enumerate(host.assets_builder.GUEST_SCRIPTS)}}
        report = {'listener_policy': 'device', 'android_listener_binding_validated': False,
                  'imported_content': {**imported, 'private_copy_verified': True,
                                       'source_generation_unchanged': True},
                  'device_adapter': {'candidate_repository_commit': 'd' * 40,
                                     'accepted_runtime_manifest_sha256': host.dbhost.ACCEPTED_RUNTIME_MANIFEST,
                                     'accepted_game_repository_commit': host.assets_builder.PACKAGE_COMMIT,
                                     'guest_source_sha256': {name: value['sha256']
                                                              for name, value in runtime['files'].items()}}}
        return report, {'candidate_commit': 'd' * 40, 'runtime': runtime, 'import_report': imported}

    def test_complete_provenance_passes(self):
        report, expected = self.sample()
        host.validate_adapter_report(report, **expected)

    def test_host_cannot_claim_android_or_skip_device_listener_policy(self):
        for key, value in (('listener_policy', 'host-default'), ('android_listener_binding_validated', True)):
            with self.subTest(key=key), self.assertRaisesRegex(RuntimeError, 'device-proof scope'):
                report, expected = self.sample()
                report[key] = value
                host.validate_adapter_report(report, **expected)

    def test_wrong_generation_changed_source_or_relaxed_boolean_is_rejected(self):
        mutations = [('generation', 'generation-' + 'e' * 32), ('contract_sha256', 'e' * 64),
                     ('receipt_sha256', 'e' * 64), ('file_count', 1), ('private_copy_verified', 1),
                     ('source_generation_unchanged', False)]
        for key, value in mutations:
            with self.subTest(key=key), self.assertRaisesRegex(RuntimeError, 'generation'):
                report, expected = self.sample()
                report['imported_content'][key] = value
                host.validate_adapter_report(report, **expected)

    def test_new_candidate_cannot_relabel_the_accepted_donor_or_guest(self):
        report, expected = self.sample()
        for key in ('candidate_repository_commit', 'accepted_game_repository_commit',
                    'accepted_runtime_manifest_sha256', 'guest_source_sha256'):
            with self.subTest(key=key), self.assertRaisesRegex(RuntimeError, 'provenance'):
                changed = copy.deepcopy(report)
                changed['device_adapter'][key] = 'substituted'
                host.validate_adapter_report(changed, **expected)

    def test_command_uses_exact_adapter_receipt_manifest_and_device_policy(self):
        root = Path('/fixture')
        generation = root / 'installed' / ('generation-' + 'a' * 32)
        command = host.make_command(work=root / 'work', assets=root / 'runtime', package=root / 'package',
                                    generation=generation, schema=root / 'schema', data_manifest=root / 'manifest.json',
                                    import_contract=root / 'atlas-import.properties', proot=root / 'native',
                                    timeout_seconds=5400)
        self.assertIn('/opt/coh-m3/game_device_diagnostic.py', command)
        self.assertNotIn('/opt/coh-m3/game_diagnostic.py', command)
        self.assertEqual(command[command.index('--execution-platform') + 1], 'host')
        self.assertEqual(command[command.index('--listener-policy') + 1], 'device')
        self.assertEqual(command[command.index('--timeout-seconds') + 1], '5400')
        self.assertEqual(command[command.index('--game-data') + 1], '/opt/coh-game-data/' + generation.name)
        self.assertIn(str(generation) + ':/opt/coh-game-data/' + generation.name, command)
        self.assertIn(str(root / 'manifest.json') + ':/opt/coh-game-data-manifest.json', command)
        self.assertIn(str(root / 'atlas-import.properties') + ':/opt/coh-import-contract.properties', command)

    def test_host_namespace_wrapper_remains_mandatory_and_drops_credentials(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            with mock.patch.object(host.dbhost.os, 'getuid', return_value=1001), \
                    mock.patch.object(host.dbhost.os, 'geteuid', return_value=1001), \
                    mock.patch.object(host.dbhost.os, 'getgid', return_value=1001), \
                    mock.patch.object(host.dbhost.os, 'readlink', return_value='net:[123]'):
                command, environment, expected = host.dbhost.isolate_command(
                    ['proot', '--game-device'], evidence=path, proot=path, work=path)
            self.assertEqual(command[:5], ['sudo', '-n', 'unshare', '--net', '--'])
            self.assertNotIn('GH_TOKEN', environment)
            self.assertNotIn('GITHUB_TOKEN', environment)
            with self.assertRaisesRegex(RuntimeError, 'isolation receipt'):
                host.dbhost.validate_network_receipt({}, expected)


if __name__ == '__main__':
    unittest.main()
