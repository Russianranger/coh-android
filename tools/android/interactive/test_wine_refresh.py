"""Preserved-prefix upgrades must follow Wine's real INF timestamp policy."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import client_login_diagnostic as guest


class WineRefreshTests(unittest.TestCase):
    INF_MTIME = 1767225600
    REGISTRATION = (
        '002c:trace:wineboot:start_rundll32 machine 1 starting L"C:\\windows\\system32\\rundll32.exe"\n'
        '002c:trace:wineboot:start_rundll32 machine 1 starting L"C:\\windows\\system32\\rundll32.exe"\n'
        '002c:trace:wineboot:start_rundll32 machine 14c starting L"C:\\windows\\syswow64\\rundll32.exe"\n'
        '002c:trace:wineboot:update_wineprefix wine: configuration in L"/private-prefix" has been updated.\n')

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.state, self.assets = self.root / 'state', self.root / 'assets'
        self.assets.mkdir()
        (self.assets / 'runtime-lock.json').write_text('{"runtime":"same-pinned-archive"}\n')
        self.wine = self.root / 'runtime/bin/wine'
        self.wine.parent.mkdir(parents=True)
        self.inf = self.root / 'runtime/share/wine/wine.inf'
        self.inf.parent.mkdir(parents=True)
        self.inf.write_text('[Version]\nSignature="$CHICAGO$"\n')
        os.utime(self.inf, (self.INF_MTIME, self.INF_MTIME))
        self.context = guest.base.Context(self.state, total_timeout=900)
        self.runner = guest.ClientLoginDiagnostic.__new__(guest.ClientLoginDiagnostic)
        guest.base.Diagnostic.__init__(self.runner,
            SimpleNamespace(state=self.state, assets=self.assets, wine=self.wine, client_probe=False), self.context)
        self.addCleanup(self.runner.lock.close)
        self.addCleanup(lambda: [child.stop() for child in self.context.children])
        self.prefix = self.runner.wineprefix
        self.prefix.mkdir()
        self.timestamp = self.prefix / '.update-timestamp'
        self.marker = self.prefix / '.coh-wine-ready.json'
        self.sentinel = self.prefix / 'user.reg'
        self.sentinel.write_text('keep existing settings\n')
        self.cache = self.runner.root / 'client-work-preserved/cache.generated'
        self.cache.parent.mkdir()
        self.cache.write_bytes(b'existing generated game cache\x00')

    def ready_prefix(self, timestamp):
        self.marker.write_text(json.dumps({'format': 1, 'purpose': 'coh-wine-initialization',
            'runtime_lock_sha256': guest.base.file_hash(self.assets / 'runtime-lock.json')}) + '\n')
        self.timestamp.write_text(f'{timestamp}\n')

    def fake_wine(self, output, *, expected_timestamp=None, result_timestamp=INF_MTIME,
                  exit_code=0, alter_inf=False):
        check = ('assert not timestamp.exists(),"Expected real registration preparation"\n'
                 if expected_timestamp is None else
                 f'assert timestamp.read_text()=={str(expected_timestamp) + chr(10)!r},"Warm timestamp changed"\n')
        source = (f'#!{sys.executable}\nimport os,sys\nfrom pathlib import Path\n'
            'assert sys.argv[1:]==["wineboot","-i"],sys.argv\n'
            'timestamp=Path(os.environ["WINEPREFIX"],".update-timestamp")\n' + check +
            f'timestamp.write_bytes({(str(result_timestamp) + chr(13) + chr(10)).encode("ascii")!r})\n' +
            (f'os.utime({str(self.inf)!r},({self.INF_MTIME+1},{self.INF_MTIME+1}))\n' if alter_inf else '') +
            f'print({output!r},end="",flush=True)\nsys.exit({exit_code})\n')
        self.wine.write_text(source)
        self.wine.chmod(0o700)

    def initialize(self):
        with redirect_stdout(io.StringIO()):
            self.runner.initialize_wine()
        return self.context.report['wine_initialization']

    def test_upgrade_refresh_matches_thor_registration_without_recreating_prefix_or_cache(self):
        self.ready_prefix(self.INF_MTIME - 1)
        prefix_inode, cache_inode = self.prefix.stat().st_ino, self.cache.stat().st_ino
        self.fake_wine(self.REGISTRATION)
        receipt = self.initialize()
        self.assertTrue(receipt['prior_ready_prefix'])
        self.assertFalse(receipt['ready_prefix_reused'])
        self.assertTrue(receipt['existing_prefix_preserved'])
        self.assertEqual(receipt['refresh_reason'], 'wine_inf_timestamp_changed')
        self.assertTrue(receipt['update_timestamp_removed'])
        self.assertEqual(receipt['update_timestamp_content_before'], self.INF_MTIME - 1)
        self.assertEqual(receipt['update_timestamp_content_after'], self.INF_MTIME)
        self.assertTrue(receipt['registration_timestamp_verified'])
        self.assertEqual(tuple(receipt[key] for key in ('registration_processes',
            'wow64_registration_processes', 'registration_passes')), (3, 1, 1))
        self.assertEqual(receipt['state'], 'initialized')
        self.assertFalse(self.marker.exists(), 'A new real PE32 runtime probe must renew readiness')
        self.assertEqual(self.prefix.stat().st_ino, prefix_inode)
        self.assertEqual(self.cache.stat().st_ino, cache_inode)
        self.assertEqual(self.cache.read_bytes(), b'existing generated game cache\x00')
        self.assertEqual(self.sentinel.read_text(), 'keep existing settings\n')

    def test_matching_content_reuses_prefix_despite_timestamp_files_own_mtime(self):
        for ending in ('\n', '\r\n'):
            with self.subTest(ending=ending):
                self.ready_prefix(self.INF_MTIME)
                self.timestamp.write_bytes(f'{self.INF_MTIME}{ending}'.encode('ascii'))
                os.utime(self.timestamp, (1, 1))
                self.fake_wine('002c:trace:wineboot:main Operation done\n', expected_timestamp=self.INF_MTIME)
                receipt = self.initialize()
                self.assertTrue(receipt['prior_ready_prefix'])
                self.assertTrue(receipt['ready_prefix_reused'])
                self.assertFalse(receipt['update_timestamp_removed'])
                self.assertEqual(receipt['refresh_reason'], 'none')
                self.assertEqual(receipt['registration_processes'], 0)
                self.assertEqual(receipt['update_timestamp_content_after'], self.INF_MTIME)
                self.assertFalse(self.marker.exists())

    def test_matching_stamp_with_unexpected_registration_still_fails(self):
        self.ready_prefix(self.INF_MTIME)
        self.fake_wine(self.REGISTRATION, expected_timestamp=self.INF_MTIME)
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'registration evidence differs'):
            self.initialize()
        self.assertEqual(self.runner.wine_initialization['state'], 'failed')
        self.assertFalse(self.marker.exists())

    def test_real_runtime_change_requires_registration_with_unchanged_inf_date(self):
        self.ready_prefix(self.INF_MTIME)
        (self.assets / 'runtime-lock.json').write_text('{"runtime":"genuine-new-archive"}\n')
        self.fake_wine(self.REGISTRATION)
        receipt = self.initialize()
        self.assertFalse(receipt['prior_ready_prefix'])
        self.assertFalse(receipt['ready_prefix_reused'])
        self.assertTrue(receipt['update_timestamp_removed'])
        self.assertEqual(receipt['registration_processes'], 3)
        self.assertEqual(receipt['wow64_registration_processes'], 1)
        self.assertEqual(receipt['registration_passes'], 1)
        self.assertTrue(receipt['registration_timestamp_verified'])
        self.assertFalse(self.marker.exists())  # Real PE32 proof still publishes readiness later.
        self.assertEqual(self.sentinel.read_text(), 'keep existing settings\n')
        self.assertEqual(self.cache.read_bytes(), b'existing generated game cache\x00')

    def test_actual_archive_epoch_zero_migrates_then_reuses_and_still_repairs_real_upgrades(self):
        # The hash-pinned runtime-fex-v3 archive actually stores wine.inf at
        # Unix epoch zero. Zero is a valid numeric stamp, never a missing proof.
        os.utime(self.inf, (0, 0))
        for previous, upgraded, registrations in ((self.INF_MTIME, False, 3),
                                                   (0, False, 0), (0, True, 3)):
            with self.subTest(previous=previous, real_upgrade=upgraded):
                self.ready_prefix(previous)
                if upgraded:
                    (self.assets / 'runtime-lock.json').write_text('{"runtime":"genuine-new-archive"}\n')
                self.fake_wine(self.REGISTRATION if registrations else '002c:trace:wineboot:main Operation done\n',
                               expected_timestamp=0 if not registrations else None, result_timestamp=0)
                receipt = self.initialize()
                expected = (3, 1, 1) if registrations else (0, 0, 0)
                self.assertEqual(expected, tuple(receipt[key] for key in
                    ('registration_processes', 'wow64_registration_processes', 'registration_passes')))
                self.assertEqual(0, receipt['update_timestamp_content_after'])
                self.assertTrue(receipt['registration_timestamp_verified'])
                self.assertEqual(not registrations, receipt['ready_prefix_reused'])
                self.assertFalse(self.marker.exists(), 'The actual PE32 probe must renew readiness')
                self.assertEqual('keep existing settings\n', self.sentinel.read_text())
                self.assertEqual(b'existing generated game cache\x00', self.cache.read_bytes())
    def test_failed_08_consumed_marker_requires_normal_single_pass_repair(self):
        self.timestamp.write_text(f'{self.INF_MTIME}\n')
        self.fake_wine(self.REGISTRATION)
        receipt = self.initialize()
        self.assertFalse(receipt['prior_ready_prefix'])
        self.assertFalse(receipt['ready_prefix_reused'])
        self.assertTrue(receipt['existing_prefix_preserved'])
        self.assertEqual(receipt['refresh_reason'], 'no_current_readiness_proof')
        self.assertTrue(receipt['registration_timestamp_verified'])
        self.assertEqual(self.sentinel.read_text(), 'keep existing settings\n')
        self.assertFalse(self.marker.exists())

    def test_fresh_prefix_is_not_reported_as_previously_preserved(self):
        self.sentinel.unlink()
        self.prefix.rmdir()
        self.fake_wine(self.REGISTRATION)
        receipt = self.initialize()
        self.assertFalse(receipt['existing_prefix_preserved'])
        self.assertFalse(receipt['prior_ready_prefix'])

    def test_refresh_retains_exact_counts_exit_status_and_internal_timeout_checks(self):
        for output, exit_code, error in [
            ('', 0, 'registration evidence differs'),
            (self.REGISTRATION * 2, 0, 'registration evidence differs'),
            (self.REGISTRATION.replace('machine 14c', 'machine 1'), 0, 'registration evidence differs'),
            (self.REGISTRATION + 'err:environ:run_wineboot boot event wait timed out\n', 0, 'internal bootstrap timed out'),
            (self.REGISTRATION, 2, 'wineboot failed')]:
            with self.subTest(exit_code=exit_code, error=error, output=output):
                self.ready_prefix(self.INF_MTIME - 1)
                self.fake_wine(output, exit_code=exit_code)
                with self.assertRaisesRegex(guest.base.DiagnosticError, error):
                    self.initialize()
                self.assertFalse(self.marker.exists())
                self.assertEqual(self.runner.wine_initialization['state'], 'failed')

    def test_changed_inf_or_wrong_postboot_timestamp_cannot_pass(self):
        for alter_inf, result, error in [(False, self.INF_MTIME - 1, 'timestamp differs'),
                                        (True, self.INF_MTIME, 'input changed')]:
            with self.subTest(alter_inf=alter_inf):
                os.utime(self.inf, (self.INF_MTIME, self.INF_MTIME))
                self.ready_prefix(self.INF_MTIME - 1)
                self.fake_wine(self.REGISTRATION, alter_inf=alter_inf, result_timestamp=result)
                with self.assertRaisesRegex(guest.base.DiagnosticError, error):
                    self.initialize()
                self.assertFalse(self.marker.exists())
                self.assertFalse(self.runner.wine_initialization['registration_timestamp_verified'])

    def test_malformed_warm_timestamp_and_linked_inf_are_refused_before_execution(self):
        self.fake_wine(self.REGISTRATION)
        for value in ('', 'disable\n', '1234', '1234\r', '1234\r\r\n',
                      '1234\nextra', '1234\r\nextra', '1234\n\n', '9'*33):
            with self.subTest(value=value):
                self.ready_prefix(self.INF_MTIME)
                self.timestamp.write_text(value)
                with self.assertRaises(guest.base.DiagnosticError):
                    self.initialize()
                self.assertFalse(self.context.children)
                self.assertFalse(self.marker.exists())
        foreign = self.inf.with_name('foreign.inf')
        self.inf.rename(foreign)
        self.inf.symlink_to(foreign)
        with self.assertRaises(OSError):
            self.initialize()
        self.assertFalse(self.context.children)


if __name__ == '__main__':
    unittest.main()
