"""Actual .30 native bytes retain Atlas-only DbServer replacement ownership."""
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'android/guest'), str(Path(__file__).parent)]
import local_character_server as server
import build_client_profile_recovery_apk as release

STOCK = {'bytes': 1661440, 'sha256': '535bfd6df77ce09bc3d1048accd95d7910552f8861c3a9c4e356d522786d585c'}
MANUAL = {'bytes': 1664512, 'sha256': 'ea1d43d7a1ed61559376563bd8bad68987fbf47a4ec41f0d6fe8fe16cfe933ba'}


def pin(path):
    return {'bytes': path.stat().st_size, 'sha256': server.base.file_hash(path)}


class KingsNativeDependencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        apk = Path(os.environ.get('COH_PROFILE_RECOVERY_TEST_DONOR_APK', ROOT/'out/donor.apk'))
        if not apk.is_file() or pin(apk) != release.DONOR_APK:
            raise AssertionError('Actual authenticated public .30 APK required; native dependency tests never skip')
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-kings-dependency-donor-')
        cls.root = Path(cls.temporary.name)
        with zipfile.ZipFile(apk) as archive:
            for name in ('game-package.tar.gz', 'dbserver-package.tar.gz',
                         'startup-dbserver.exe', 'startup-dbserver-manifest.json'):
                (cls.root/name).write_bytes(archive.read('assets/runtime/'+name))
        server.login.extract_regular(cls.root/'game-package.tar.gz', cls.root/'game')
        server.login.extract_regular(cls.root/'dbserver-package.tar.gz', cls.root/'dbserver')
        cls.game = json.loads((cls.root/'game/game-package.json').read_text())
        cls.package = json.loads((cls.root/'dbserver/package-manifest.json').read_text())
        if pin(cls.root/'game/DbServer.exe') != STOCK or pin(cls.root/'startup-dbserver.exe') != MANUAL:
            raise AssertionError('Published stock/manual native DbServer identity differs')

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def instance(self, *, manual=True):
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='coh-kings-dependencies-')))
        atlas, original, assets, kings = (root/name for name in ('atlas', 'original', 'assets', 'kings'))
        for path in (atlas, original, assets, kings): path.mkdir()
        for name in self.game['files']:
            shutil.copyfile(self.root/'game'/name, atlas/name)
            shutil.copyfile(self.root/'game'/name, original/name)
        for name in ('startup-dbserver.exe', 'startup-dbserver-manifest.json'):
            shutil.copyfile(self.root/name, assets/name)
        value = object.__new__(server.LocalCharacterServer)
        value.runtime, value.map_package_dir = atlas, original
        value.map_package, value.package = copy.deepcopy(self.game), copy.deepcopy(self.package)
        value.owner = SimpleNamespace(args=SimpleNamespace(assets=assets))
        value.manual_atlas_startup = server.install_manual_atlas_dbserver(assets, atlas, value.package) if manual else None
        return value, kings

    def mutate(self, path):
        raw = bytearray(path.read_bytes()); raw[-1] ^= 1; path.write_bytes(raw)

    def rewritten_manifest(self, value, transform):
        path = value.owner.args.assets/'startup-dbserver-manifest.json'
        document = json.loads(path.read_text()); transform(document)
        path.write_text(json.dumps(document))
        value.manual_atlas_startup['manifest_sha256'] = server.base.file_hash(path)

    def test_actual_manual_atlas_and_stock_kings_closures_both_preserved(self):
        value, kings = self.instance()
        before = {name: pin(value.runtime/name) for name in self.game['files']}
        self.assertEqual(before['DbServer.exe'], MANUAL)
        self.assertNotEqual(before['DbServer.exe']['sha256'], value.map_package['files']['DbServer.exe']['sha256'])
        proof = value.copy_kings_native_dependencies(kings)
        self.assertEqual(pin(kings/'DbServer.exe'), STOCK)
        self.assertEqual(proof['DbServer.exe'], dict(STOCK, source='verified_original_game_package'))
        self.assertEqual(before, {name: pin(value.runtime/name) for name in self.game['files']})
        for name, expected in self.game['files'].items():
            self.assertEqual(pin(kings/name), {key: expected[key] for key in ('bytes', 'sha256')})
            self.assertEqual((kings/name).stat().st_mode & 0o777, 0o400)
            if name != 'DbServer.exe': self.assertEqual(proof[name]['source'], 'owned_atlas_runtime')

    def test_original_runtime_without_supplement_keeps_original_source_policy(self):
        value, kings = self.instance(manual=False)
        proof = value.copy_kings_native_dependencies(kings)
        self.assertEqual(pin(kings/'DbServer.exe'), STOCK)
        self.assertEqual(proof['DbServer.exe']['source'], 'owned_atlas_runtime')

    def test_tampered_installed_atlas_manual_executable_refused(self):
        value, kings = self.instance(); self.mutate(value.runtime/'DbServer.exe')
        with self.assertRaisesRegex(server.base.DiagnosticError, 'Installed Atlas manual DbServer'):
            value.copy_kings_native_dependencies(kings)

    def test_tampered_original_game_package_dbserver_refused(self):
        value, kings = self.instance(); self.mutate(value.map_package_dir/'DbServer.exe')
        with self.assertRaisesRegex(server.base.DiagnosticError, 'qualified source: DbServer.exe'):
            value.copy_kings_native_dependencies(kings)
        self.assertEqual(pin(value.runtime/'DbServer.exe'), MANUAL)

    def test_other_dependency_and_mapserver_mutants_still_refused(self):
        for name in ('CrashRpt.dll', 'MapServer.exe'):
            value, kings = self.instance(); self.mutate(value.runtime/name)
            with self.subTest(name=name), self.assertRaisesRegex(server.base.DiagnosticError, 'qualified source: '+name):
                value.copy_kings_native_dependencies(kings)

    def test_unqualified_manual_report_never_enables_fallback(self):
        for field, changed in (('enabled', False), ('other_native_targets_changed', True),
                               ('executable_sha256', 'f'*64), ('manifest_sha256', 'f'*64)):
            value, kings = self.instance(); value.manual_atlas_startup[field] = changed
            with self.subTest(field=field), self.assertRaises(server.base.DiagnosticError):
                value.copy_kings_native_dependencies(kings)

    def test_changed_supplement_scope_refused_even_with_updated_report_digest(self):
        value, kings = self.instance()
        self.rewritten_manifest(value, lambda document: document.update(replacement_scope='all_native_targets'))
        with self.assertRaisesRegex(server.base.DiagnosticError, 'Installed Atlas manual DbServer'):
            value.copy_kings_native_dependencies(kings)

    def test_changed_original_donor_pin_refused_even_with_updated_report_digest(self):
        value, kings = self.instance()
        self.rewritten_manifest(value, lambda document: document['base_normal_executable'].update(sha256='f'*64))
        with self.assertRaisesRegex(server.base.DiagnosticError, 'Installed Atlas manual DbServer'):
            value.copy_kings_native_dependencies(kings)

    def test_linked_original_or_manual_atlas_dependency_refused(self):
        for directory in ('runtime', 'map_package_dir'):
            value, kings = self.instance(); path = getattr(value, directory)/'DbServer.exe'
            retained = path.with_name('retained-DbServer.exe'); path.rename(retained); path.symlink_to(retained)
            with self.subTest(directory=directory), self.assertRaises(server.base.DiagnosticError):
                value.copy_kings_native_dependencies(kings)

    def test_missing_supplement_receipt_cannot_accept_manual_atlas_bytes(self):
        value, kings = self.instance(); value.manual_atlas_startup = None
        with self.assertRaisesRegex(server.base.DiagnosticError, 'qualified source: DbServer.exe'):
            value.copy_kings_native_dependencies(kings)

    def test_existing_destination_is_never_replaced(self):
        value, kings = self.instance(); path = kings/'CrashRpt.dll'; path.write_bytes(b'preserve')
        with self.assertRaisesRegex(server.base.DiagnosticError, 'already exists'):
            value.copy_kings_native_dependencies(kings)
        self.assertEqual(path.read_bytes(), b'preserve')


if __name__ == '__main__': unittest.main()
