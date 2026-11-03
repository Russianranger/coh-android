"""Exercise the actual setup helper, including failed cache/native observations."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import local_login_server as setup

OUTPUT = ('COH_ODBC_DRIVER_V1 NAME PostgreSQL Unicode\n'
          'COH_ODBC_DRIVER_V1 DLL C:\\drivers\\psqlodbc.dll\n'
          'COH_ODBC_DRIVER_V1 PASS bits=32\n')


class LocalOdbcTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.assets = root / 'assets'
        self.prefix = root / 'prefix'
        self.assets.mkdir()
        for name in ('runtime-probe.exe', 'psqlodbc_x86.msi'):
            (self.assets / name).write_bytes(name.encode())
        self.dll = self.prefix / 'drive_c/drivers/psqlodbc.dll'
        self.dll.parent.mkdir(parents=True)
        self.dll.write_bytes(b'qualified-driver')
        self.ctx = SimpleNamespace(report={}, run=Mock(return_value={'exit_code': 0, 'output': OUTPUT}))
        self.owner = SimpleNamespace(wineprefix=self.prefix, args=SimpleNamespace(
            wine='wine', assets=self.assets), wine_env={}, ctx=self.ctx)
        # The native driver remains the production parser, while these host
        # fixture bytes are not Windows executables.
        self.pe = patch.object(setup.base, 'verify_pe32')
        self.pe.start()
        self.addCleanup(self.pe.stop)

    def labels(self):
        return [call.args[0] for call in self.ctx.run.call_args_list]

    def initial_install(self):
        setup.ensure_local_odbc(self.owner)
        self.assertEqual(self.labels(), ['local-install-x86-psqlodbc', 'local-odbc-driver'])
        self.ctx.run.reset_mock()

    def test_first_install_then_exact_reuse_still_executes_native_probe(self):
        self.initial_install()
        setup.ensure_local_odbc(self.owner)
        self.assertEqual(self.labels(), ['local-odbc-driver-reuse'])
        self.assertTrue(self.ctx.report['odbc_setup']['installer_reused'])
        self.assertTrue(self.ctx.report['odbc_setup']['native_driver_probe_executed'])
        self.assertEqual((self.prefix / 'coh-local-odbc-cache.json').stat().st_mode & 0o777, 0o600)

    def test_changed_installer_probe_or_driver_reinstalls(self):
        for target in (self.assets / 'psqlodbc_x86.msi', self.assets / 'runtime-probe.exe', self.dll):
            with self.subTest(target=target.name):
                self.ctx.run.reset_mock()
                setup.ensure_local_odbc(self.owner)
                self.ctx.run.reset_mock()
                target.write_bytes(target.read_bytes() + b'changed')
                setup.ensure_local_odbc(self.owner)
                self.assertEqual(self.labels(), ['local-install-x86-psqlodbc', 'local-odbc-driver'])
                self.assertFalse(self.ctx.report['odbc_setup']['installer_reused'])

    def test_failed_or_malformed_reuse_probe_repairs_and_probes_again(self):
        self.initial_install()
        for result in ({'exit_code': 1, 'output': 'driver missing'},
                       {'exit_code': 0, 'output': OUTPUT.replace('bits=32', 'bits=64')}):
            with self.subTest(result=result):
                self.ctx.run.reset_mock()
                self.ctx.run.side_effect = [result, {'exit_code': 0, 'output': ''},
                                            {'exit_code': 0, 'output': OUTPUT}]
                setup.ensure_local_odbc(self.owner)
                self.assertEqual(self.labels(), ['local-odbc-driver-reuse',
                    'local-install-x86-psqlodbc', 'local-odbc-driver'])

    def test_corrupt_oversized_or_linked_cache_uses_original_path(self):
        self.initial_install()
        cache = self.prefix / 'coh-local-odbc-cache.json'
        for data in ('not json', '[]', '[' * 1800 + ']' * 1800, 'x' * 4097):
            with self.subTest(data=data[:10]):
                cache.write_text(data)
                self.ctx.run.reset_mock()
                setup.ensure_local_odbc(self.owner)
                self.assertEqual(self.labels(), ['local-install-x86-psqlodbc', 'local-odbc-driver'])
        cache.unlink()
        external = Path(self.tmp.name) / 'external'
        external.write_text('preserve')
        cache.symlink_to(external)
        self.ctx.run.reset_mock()
        setup.ensure_local_odbc(self.owner)
        self.assertEqual(self.labels(), ['local-install-x86-psqlodbc', 'local-odbc-driver'])
        self.assertEqual(external.read_text(), 'preserve')
        self.assertEqual(self.ctx.report['odbc_setup']['cache_status'], 'unavailable')

    def test_bad_install_probe_remains_failure(self):
        self.ctx.run.side_effect = [{'exit_code': 0, 'output': ''},
                                    {'exit_code': 0, 'output': OUTPUT.replace('bits=32', 'bits=64')}]
        with self.assertRaises(setup.base.DiagnosticError):
            setup.ensure_local_odbc(self.owner)
        self.assertFalse((self.prefix / 'coh-local-odbc-cache.json').exists())

    def test_cancellation_does_not_install_or_get_hidden(self):
        self.initial_install()
        self.ctx.run.side_effect = setup.base.DiagnosticError('cancelled')
        with self.assertRaisesRegex(setup.base.DiagnosticError, 'cancelled'):
            setup.ensure_local_odbc(self.owner)
        self.assertEqual(self.labels(), ['local-odbc-driver-reuse'])

    def test_driver_cache_refuses_external_or_parent_paths(self):
        for path in (r'Z:\outside.dll', r'C:\..\outside.dll', r'C:\drivers\file:stream.dll'):
            with self.subTest(path=path), self.assertRaises(setup.base.DiagnosticError):
                setup.odbc_dll_path(self.prefix, {'driver_path': path})
        self.dll.unlink()
        self.dll.symlink_to(self.assets / 'runtime-probe.exe')
        with self.assertRaises(setup.base.DiagnosticError):
            setup.odbc_dll_path(self.prefix, {'driver_path': r'C:\drivers\psqlodbc.dll'})

    def test_linked_c_drive_cannot_qualify_reuse_or_overwrite_external_files(self):
        self.initial_install()
        drive = self.prefix / 'drive_c'
        external = Path(self.tmp.name) / 'external-drive-c'
        drive.rename(external)
        drive.symlink_to(external, target_is_directory=True)
        with self.assertRaises(setup.base.DiagnosticError):
            setup.odbc_dll_path(self.prefix, {'driver_path': r'C:\drivers\psqlodbc.dll'})
        setup.ensure_local_odbc(self.owner)
        self.assertEqual(self.labels(), ['local-install-x86-psqlodbc', 'local-odbc-driver'])
        self.assertFalse(self.ctx.report['odbc_setup']['installer_reused'])
        self.assertEqual(self.ctx.report['odbc_setup']['cache_status'], 'unavailable')
        self.assertEqual((external / 'drivers/psqlodbc.dll').read_bytes(), b'qualified-driver')

    def test_looped_driver_cache_remains_optional_and_uses_original_path(self):
        self.initial_install()
        self.dll.unlink()
        self.dll.symlink_to(self.dll.name)
        setup.ensure_local_odbc(self.owner)
        self.assertEqual(self.labels(), ['local-install-x86-psqlodbc', 'local-odbc-driver'])
        self.assertFalse(self.ctx.report['odbc_setup']['installer_reused'])
        self.assertEqual(self.ctx.report['odbc_setup']['cache_status'], 'unavailable')


if __name__ == '__main__':
    unittest.main()
