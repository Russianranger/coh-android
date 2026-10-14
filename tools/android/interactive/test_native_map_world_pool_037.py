import hashlib
import ctypes
import json
import os
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest import mock

import native_map_world_pool_037 as pool


def fixture_temp_parent():
    # Hosted Windows TEMP can use an 8.3 spelling. Allocate the controlled
    # fixture under its physical spelling; production alias refusal stays strict.
    raw = Path(tempfile.gettempdir()).absolute()
    return raw, raw.resolve(strict=True)


class PoolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_temp_parent, cls.canonical_temp_parent = fixture_temp_parent()
        print('COH_POOL_FIXTURE_TEMP_V1 ' + json.dumps({
            'raw_temp_parent': str(cls.raw_temp_parent),
            'resolved_temp_parent': str(cls.canonical_temp_parent),
            'lexical_parent_differs': os.path.normcase(str(cls.raw_temp_parent))
                != os.path.normcase(str(cls.canonical_temp_parent)),
            'production_alias_refusal_unchanged': True,
        }, sort_keys=True), flush=True)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=self.canonical_temp_parent)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'runtime'
        self.archive = Path(self.tmp.name) / 'evidence'
        self.archive.mkdir()
        self.provider = {'MapServer.exe', pool.CONFIG, 'data/fx/known.fx', 'PhysXCore.dll'}
        self.caches = {'data/bin/sequencers.bin'}
        for name in self.provider | self.caches:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode())

    def census(self):
        return pool.closed_namespace(self.root, self.provider, self.caches)

    def test_canonical_fixture_parent_does_not_admit_aliased_directory(self):
        self.assertEqual(Path(self.tmp.name).parent, self.canonical_temp_parent)
        alias = Path(self.tmp.name) / 'configured-temp-alias'
        self.directory_alias(alias, self.archive)
        with mock.patch.object(tempfile, 'gettempdir', return_value=str(alias)):
            raw, resolved = fixture_temp_parent()
        self.assertEqual(raw, alias)
        self.assertEqual(resolved, self.archive)
        with self.assertRaisesRegex(ValueError, 'ancestor'):
            with pool.directory_custody(raw):
                self.fail('Production custody admitted a directory alias')
        with tempfile.TemporaryDirectory(dir=resolved) as temporary:
            with pool.directory_custody(Path(temporary)):
                self.assertEqual(Path(temporary).parent, self.archive)

    def directory_alias(self, alias, target):
        try:
            alias.symlink_to(target, target_is_directory=True)
        except OSError as error:
            if os.name != 'nt' or getattr(error, 'winerror', None) != 1314:
                raise
            result = subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(alias), str(target)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, check=False)
            self.assertEqual(result.returncode, 0, repr(result.stdout + result.stderr))
            self.assertTrue(alias.lstat().st_file_attributes & 0x400)

    def handle_count(self):
        if os.name != 'nt':
            return len(list(Path('/proc/self/fd').iterdir()))
        from ctypes import wintypes
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.GetCurrentProcess.argtypes, api.GetCurrentProcess.restype = [], wintypes.HANDLE
        api.GetProcessHandleCount.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        api.GetProcessHandleCount.restype = wintypes.BOOL
        count = wintypes.DWORD()
        self.assertTrue(api.GetProcessHandleCount(api.GetCurrentProcess(), ctypes.byref(count)))
        return count.value

    def log(self):
        path = self.root / pool.ERROR_LOG
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'owned current native error log\n')
        return path

    def test_complete_real_namespace_without_extra_content_hashing(self):
        value = self.census()
        self.assertEqual(set(value['files']), self.provider | self.caches)
        self.assertTrue(value['full_namespace_verified'])
        self.assertFalse(value['content_schema_native_SQL_gates_supplied'])
        self.assertFalse(value['shipping_allowed'])

    def test_unknown_file_and_empty_directory_preserved_on_refusal(self):
        unknown = self.root / 'unrelated-profile'
        unknown.write_bytes(b'preserve')
        with self.assertRaisesRegex(ValueError, 'Unknown pool file'):
            self.census()
        self.assertEqual(unknown.read_bytes(), b'preserve')
        unknown.unlink()
        extra = self.root / 'unknown-empty'
        extra.mkdir()
        with self.assertRaisesRegex(ValueError, 'Unknown pool directory'):
            self.census()
        self.assertTrue(extra.is_dir())

    def test_missing_member_and_unsafe_cache_refused(self):
        (self.root / 'PhysXCore.dll').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing exact'):
            self.census()
        with self.assertRaisesRegex(ValueError, 'cache path'):
            pool.closed_namespace(self.root, self.provider, {'data/character.bin'})

    def test_case_alias_and_path_alias_refused(self):
        with self.assertRaisesRegex(ValueError, 'case alias'):
            pool.closed_namespace(self.root, self.provider | {'mapserver.EXE'}, self.caches)
        for name in ('../other', 'data//a', 'data/a:stream', 'data/a.', '/other', 'data\\a'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                pool.closed_namespace(self.root, {name}, self.caches)

    def test_hardlink_and_directory_symlink_refused(self):
        path = self.root / 'data/fx/known.fx'
        other = Path(self.tmp.name) / 'outside-alias'
        os.link(path, other)
        with self.assertRaisesRegex(ValueError, 'hardlink'):
            self.census()
        other.unlink()
        # Actual source tree remains; no unknown target is removed by the helper.
        alias = self.root / 'alias'
        self.directory_alias(alias, path.parent)
        with self.assertRaises(ValueError):
            self.census()
        self.assertTrue(alias.is_symlink() or getattr(alias.lstat(), 'st_file_attributes', 0) & 0x400)

    def test_fatal_enumeration_error_has_no_partial_success(self):
        original = os.scandir
        def fail(path):
            if Path(path) == self.root / 'data/fx':
                raise PermissionError('injected enumeration failure')
            return original(path)
        with mock.patch.object(pool.os, 'scandir', side_effect=fail):
            with self.assertRaises(PermissionError):
                self.census()

    def test_mutation_during_enumeration_refused(self):
        original = os.scandir
        class Mutating:
            def __init__(self, path):
                self.inner = original(path)
                self.path = Path(path)
            def __enter__(self):
                return self.inner.__enter__()
            def __exit__(self, *args):
                result = self.inner.__exit__(*args)
                if self.path == self_root / 'data/fx':
                    (self.path / 'new.fx').write_bytes(b'new')
                return result
        self_root = self.root
        with mock.patch.object(pool.os, 'scandir', side_effect=Mutating):
            with self.assertRaisesRegex(ValueError, 'directory changed'):
                self.census()

    def test_real_owned_log_transfer_preserves_bytes_and_date(self):
        path = self.log()
        raw = path.read_bytes()
        date = path.stat().st_mtime_ns
        receipt = self.census()
        result = pool.quarantine_owned_error_log(self.root, self.archive, 'atlas-forward', receipt, stopped=True)
        target = Path(result['archive'])
        self.assertFalse(path.exists())
        self.assertEqual(target.read_bytes(), raw)
        self.assertEqual(target.stat().st_mtime_ns, date)
        self.assertEqual(target.stat().st_nlink, 1)
        self.assertEqual(result['transferred']['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertFalse(result['unknown_files_removed'])
        self.census()

    def test_live_missing_cleanup_and_archive_collision_preserve_log(self):
        path = self.log()
        receipt = self.census()
        for stopped in (False, None, 1):
            with self.assertRaisesRegex(ValueError, 'cleanup'):
                pool.quarantine_owned_error_log(self.root, self.archive, 'case', receipt, stopped=stopped)
        target = self.archive / 'case-native-error.log'
        target.write_bytes(b'earlier evidence')
        with self.assertRaisesRegex(ValueError, 'Fresh native-log'):
            pool.quarantine_owned_error_log(self.root, self.archive, 'case', receipt, stopped=True)
        self.assertEqual(target.read_bytes(), b'earlier evidence')
        self.assertTrue(path.exists())

    def test_changed_log_after_census_refused(self):
        path = self.log()
        receipt = self.census()
        path.write_bytes(b'changed current bytes')
        with self.assertRaisesRegex(ValueError, 'log changed'):
            pool.quarantine_owned_error_log(self.root, self.archive, 'case', receipt, stopped=True)
        self.assertTrue(path.exists())
        self.assertFalse(list(self.archive.iterdir()))

    def test_uncaptured_log_appearance_refused(self):
        # Admit the native log directories before the first empty census.
        (self.root / 'logs/mapserver').mkdir(parents=True)
        receipt = self.census()
        self.log()
        with self.assertRaisesRegex(ValueError, 'Uncaptured|log parent changed'):
            pool.quarantine_owned_error_log(self.root, self.archive, 'case', receipt, stopped=True)

    def test_replaced_log_parent_preserves_original_owned_file(self):
        path = self.log()
        receipt = self.census()
        old = self.root / 'logs/mapserver'
        held = self.root / 'logs/renamed-owned'
        old.rename(held)
        old.mkdir()
        with self.assertRaisesRegex(ValueError, 'log parent changed'):
            pool.quarantine_owned_error_log(self.root, self.archive, 'case', receipt, stopped=True)
        self.assertTrue((held / 'error.log').is_file())
        self.assertFalse(list(self.archive.iterdir()))

    def test_unknown_rotation_path_and_excessive_log_refused(self):
        path = self.root / 'errorLogLastRun.log'
        path.write_bytes(b'preserve rotation')
        with self.assertRaisesRegex(ValueError, 'Unknown pool file'):
            self.census()
        path.unlink()
        log = self.log()
        with mock.patch.object(pool, 'MAX_LOG_BYTES', 4):
            with self.assertRaisesRegex(ValueError, 'log exceeds'):
                self.census()
        self.assertTrue(log.exists())

    def test_archive_inside_pool_refused_without_change(self):
        path = self.log()
        receipt = self.census()
        with self.assertRaisesRegex(ValueError, 'outside reusable'):
            pool.quarantine_owned_error_log(self.root, self.root / 'data/fx', 'case', receipt, stopped=True)
        self.assertTrue(path.exists())

    def test_archive_ancestor_alias_into_provider_refused_before_transfer(self):
        path = self.log()
        receipt = self.census()
        alias = Path(self.tmp.name) / 'ancestor-alias'
        self.directory_alias(alias, self.root / 'data')
        with self.assertRaisesRegex(ValueError, 'ancestor'):
            pool.quarantine_owned_error_log(self.root, alias / 'fx', 'case', receipt, stopped=True)
        self.assertTrue(path.is_file())
        self.assertFalse((self.root / 'data/fx/case-native-error.log').exists())

    def test_archive_outside_ancestor_alias_refused_before_transfer(self):
        path = self.log()
        receipt = self.census()
        outside = Path(self.tmp.name) / 'outside'
        outside.mkdir()
        leaf = outside / 'evidence'
        leaf.mkdir()
        alias = Path(self.tmp.name) / 'outside-alias'
        self.directory_alias(alias, outside)
        with self.assertRaisesRegex(ValueError, 'ancestor'):
            pool.quarantine_owned_error_log(self.root, alias / 'evidence', 'case', receipt, stopped=True)
        self.assertTrue(path.is_file())
        self.assertFalse(list(leaf.iterdir()))

    def test_runtime_ancestor_alias_refused_before_census(self):
        alias = Path(self.tmp.name) / 'runtime-parent-alias'
        self.directory_alias(alias, Path(self.tmp.name))
        with self.assertRaisesRegex(ValueError, 'ancestor'):
            pool.closed_namespace(alias / 'runtime', self.provider, self.caches)

    def test_held_directory_custody_detects_rename_and_closes_descriptors(self):
        target = Path(self.tmp.name) / 'held'
        target.mkdir()
        descriptor_count = self.handle_count()
        if os.name == 'nt':
            with pool.directory_custody(target):
                with self.assertRaises(OSError):
                    target.rename(Path(self.tmp.name) / 'moved')
            self.assertTrue(target.is_dir())
        else:
            with self.assertRaisesRegex(ValueError, 'ancestor changed'):
                with pool.directory_custody(target):
                    target.rename(Path(self.tmp.name) / 'moved')
                    target.mkdir()
        self.assertEqual(self.handle_count(), descriptor_count)

    def test_native_windows_alternate_stream_refusal(self):
        if os.name != 'nt':
            # This module's portable preparation runs Linux. The explicit
            # Windows fixture step is mandatory before any native pool work.
            self.assertTrue(callable(pool.ordinary_streams))
            return
        path = self.root / 'data/fx/known.fx'
        pool.ordinary_streams(path)
        stream = Path(str(path) + ':unrelated-evidence')
        stream.write_bytes(b'unknown alternate stream')
        with self.assertRaisesRegex(ValueError, 'alternate stream'):
            self.census()
        self.assertEqual(stream.read_bytes(), b'unknown alternate stream')

    def test_error_before_source_removal_releases_only_new_reservation(self):
        path = self.log()
        receipt = self.census()
        original = pool.os.unlink
        def refuse(source, *args, **kwargs):
            if Path(source) == path:
                raise PermissionError('injected source unlink refusal')
            return original(source, *args, **kwargs)
        with mock.patch.object(pool.os, 'unlink', side_effect=refuse):
            with self.assertRaises(PermissionError):
                pool.quarantine_owned_error_log(self.root, self.archive, 'case', receipt, stopped=True)
        self.assertTrue(path.exists())
        self.assertEqual(path.stat().st_nlink, 1)
        self.assertFalse(list(self.archive.iterdir()))

    def test_error_after_source_removal_retains_archived_evidence(self):
        path = self.log()
        receipt = self.census()
        original = pool.pin_log
        def refuse(target, *args, **kwargs):
            if Path(target).parent == self.archive:
                raise PermissionError('injected archive recheck refusal')
            return original(target, *args, **kwargs)
        with mock.patch.object(pool, 'pin_log', side_effect=refuse):
            with self.assertRaises(PermissionError):
                pool.quarantine_owned_error_log(self.root, self.archive, 'case', receipt, stopped=True)
        self.assertFalse(path.exists())
        self.assertEqual((self.archive / 'case-native-error.log').read_bytes(), b'owned current native error log\n')

    def test_budgets_and_phase_costs_are_host_only_and_finite(self):
        for invalid in (0, -1, 7201, True, float('nan')):
            with self.assertRaises(ValueError):
                pool.Budget(invalid)
        with mock.patch.object(pool.time, 'monotonic', side_effect=[10, 11, 13]):
            budget = pool.Budget(2)
            self.assertEqual(budget.remaining(), 1)
            with self.assertRaisesRegex(ValueError, 'exhausted'):
                budget.check('hashing')
        records = []
        with self.assertRaisesRegex(RuntimeError, 'injected'):
            with pool.PhaseTimer(None, 'copy-provider', records):
                raise RuntimeError('injected')
        self.assertEqual(records[0]['status'], 'failed')
        self.assertEqual(records[0]['scope'], 'host_qualification_not_native_or_device_loading')


if __name__ == '__main__':
    unittest.main()
