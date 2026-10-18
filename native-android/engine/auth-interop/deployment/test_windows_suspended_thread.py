"""Finite API-double controls only; no Windows/DLL/thread/process execution."""

import argparse
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys
import unittest
from unittest import mock

import windows_suspended_thread as t


ROOT = Path(__file__).resolve().parents[4]
PID, TID, HANDLE, START = 912345678, 612345678, 0x123456789, 0x1234567800001234


class Process:
    pid, _handle = PID, HANDLE
    def __init__(self):
        self.polls = 0
        self.exit_at = None
    def poll(self):
        self.polls += 1
        return 0 if self.polls == self.exit_at else None


class Api:
    calls_total = 0
    max_owned = 0
    refusal_sites = 0
    def __init__(self):
        self.calls, self.owned, self.fail_at = [], {}, set()
        self.rows = [[(33, 0), (TID, PID), (44, 55)]] * 2
        self.positions, self.snapshots = {}, 0
        self.process_queries = self.thread_queries = 0
        self.process_values = [(PID, START)] * 2
        self.thread_values = [(TID, PID, START+1)] * 2
        self.previous = 1
        self.resume_calls = 0
        self.hook = None
    def call(self, name, *args):
        self.calls.append((name, args))
        Api.calls_total += 1
        if len(self.calls) in self.fail_at:
            raise t.ThreadApiError('API_FAILED')
        if self.hook:
            self.hook(name, *args)
    def own(self, handle, kind):
        self.owned[handle] = kind
        Api.max_owned = max(Api.max_owned, len(self.owned))
        return handle
    def process_identity(self, handle):
        self.call('process_identity', handle)
        self.process_queries += 1
        return self.process_values[self.process_queries-1]
    def snapshot(self):
        self.call('snapshot')
        handle = 1000+self.snapshots
        self.snapshots += 1
        self.positions[handle] = -1
        return self.own(handle, 'snapshot')
    def first(self, handle):
        self.call('first', handle)
        self.positions[handle] = 0
        rows = self.rows[handle-1000]
        return rows[0] if rows else None
    def next(self, handle):
        self.call('next', handle)
        self.positions[handle] += 1
        at = self.positions[handle]
        rows = self.rows[handle-1000]
        return rows[at] if at < len(rows) else None
    def open_thread(self, tid):
        self.call('open_thread', tid)
        return self.own(2000, 'thread')
    def thread_identity(self, handle):
        self.call('thread_identity', handle)
        self.thread_queries += 1
        return self.thread_values[self.thread_queries-1]
    def resume(self, handle):
        self.call('resume', handle)
        self.resume_calls += 1
        return self.previous
    def close(self, handle):
        self.call('close', handle)
        del self.owned[handle]


class SuspendedThreadTests(unittest.TestCase):
    def check_failure(self, process, api, code=None):
        result = t.resume_primary(process, api=api)
        self.assertFalse(result['passed'])
        if code:
            self.assertEqual(result['failure'], code)
        self.assertEqual(result['schema'], t.SCHEMA)
        self.assertNotIn(str(PID), json.dumps(result))
        self.assertNotIn(str(TID), json.dumps(result))
        self.assertNotIn(str(START), json.dumps(result))
        return result

    def test_import_and_function_binding_are_platform_inert(self):
        path = Path(t.__file__)
        spec = importlib.util.spec_from_file_location('_coh_thread_import_control', path)
        module = importlib.util.module_from_spec(spec)
        with mock.patch('ctypes.WinDLL', create=True, side_effect=AssertionError('native forbidden')):
            spec.loader.exec_module(module)
            self.assertTrue(callable(module.resume_primary))
            self.assertTrue(callable(module.NativeThreadApi))

    def test_success_exact_projection_identity_sequence_and_no_process_close(self):
        process, api = Process(), Api()
        result = t.resume_primary(process, api=api)
        self.assertEqual(set(result), t.TRUE_FIELDS | {
            'schema', 'failure', 'snapshot_passes', 'snapshot_entries_examined', 'secondary_close_failures'})
        self.assertTrue(all(result[name] is True for name in t.TRUE_FIELDS))
        self.assertEqual((result['snapshot_passes'], result['snapshot_entries_examined'],
                          result['secondary_close_failures'], result['failure']), (2, 6, 0, 'NONE'))
        self.assertEqual(api.owned, {})
        self.assertEqual(api.calls[-4:], [('process_identity', (HANDLE,)),
            ('thread_identity', (2000,)), ('resume', (2000,)), ('close', (2000,))])
        self.assertEqual(api.resume_calls, 1)
        self.assertEqual([args[0] for name, args in api.calls if name == 'close'], [1000, 1001, 2000])
        self.assertNotIn(str(PID), json.dumps(result))
        self.assertNotIn(str(TID), json.dumps(result))
        self.assertNotIn(str(START), json.dumps(result))

    def test_input_and_exited_process_refuse_before_api_use(self):
        for attribute, value in (('pid', True), ('pid', 0), ('pid', 2**32),
                                 ('_handle', False), ('_handle', 0), ('_handle', -1),
                                 ('_handle', 2**64-1), ('_handle', 'private')):
            process, api = Process(), Api()
            setattr(process, attribute, value)
            with self.subTest(attribute=attribute, value=value):
                self.check_failure(process, api, 'INPUT')
                self.assertEqual(api.calls, [])
        process, api = Process(), Api()
        process.exit_at = 1
        self.check_failure(process, api, 'PROCESS_EXITED')
        self.assertEqual(api.calls, [])

    def test_process_identity_generation_and_popen_field_refusals(self):
        for value in ((PID+1, START), (True, START), (PID, 0), (PID, 2**64), [PID, START]):
            api = Api();api.process_values[0] = value
            self.check_failure(Process(), api, 'PROCESS_IDENTITY')
            self.assertEqual(api.resume_calls, 0)
        api = Api();api.process_values[1] = (PID, START+1)
        self.check_failure(Process(), api, 'GENERATION_CHANGED')
        self.assertEqual(api.owned, {})
        for attribute, value in (('pid', PID+1), ('_handle', HANDLE+1)):
            process, api = Process(), Api()
            def hook(name, *args):
                if name == 'close' and args[0] == 1001:
                    setattr(process, attribute, value)
            api.hook = hook
            self.check_failure(process, api, 'GENERATION_CHANGED')
            self.assertEqual(api.resume_calls, 0)
        for exit_at in (2, 3):
            process, api = Process(), Api();process.exit_at = exit_at
            self.check_failure(process, api, 'PROCESS_EXITED')
            self.assertEqual(api.resume_calls, 0)

    def test_single_thread_extent_zero_duplicate_and_changed_snapshot_refusals(self):
        for rows in ([], [(9, 0)], [(TID, PID), (TID+1, PID)],
                     [(TID, PID), (TID, PID)], [(0, PID)], [(TID, True)],
                     [(TID, 2**32)], [(TID, PID, 1)], [[TID, PID]]):
            api = Api();api.rows[0] = rows
            self.check_failure(Process(), api)
            self.assertEqual(api.resume_calls, 0)
            self.assertEqual(api.owned, {})
        api = Api();api.rows[1] = [(TID+1, PID)]
        self.check_failure(Process(), api, 'GENERATION_CHANGED')
        self.assertEqual(api.resume_calls, 0)
        self.assertEqual(api.owned, {})

    def test_thread_handle_id_owner_creation_and_recheck_refusals(self):
        for value in ((TID+1, PID, START+1), (TID, PID+1, START+1),
                      (TID, PID, START-1), (TID, PID, 0), (TID, PID, 2**64),
                      (TID, True, START+1), [TID, PID, START+1]):
            api = Api();api.thread_values[0] = value
            self.check_failure(Process(), api, 'THREAD_IDENTITY')
            self.assertEqual(api.resume_calls, 0)
            self.assertEqual(api.owned, {})
        api = Api();api.thread_values[1] = (TID, PID, START+2)
        self.check_failure(Process(), api, 'GENERATION_CHANGED')
        self.assertEqual(api.resume_calls, 0)
        self.assertEqual(api.owned, {})

    def test_resume_requires_strict_previous_count_one_and_never_repeats(self):
        for value in (0, 2, 127, 0xFFFFFFFF, True, 1.0, None):
            api = Api();api.previous = value
            result = self.check_failure(Process(), api, 'RESUME_COUNT')
            self.assertTrue(result['resume_attempted'])
            self.assertFalse(result['previous_suspend_count_one'])
            self.assertFalse(result['resume_observed'])
            self.assertTrue(result['cleanup_verified'])
            self.assertEqual(api.resume_calls, 1)

    def test_all_controlled_api_failure_sites_close_owned_handles(self):
        baseline = Api()
        self.assertTrue(t.resume_primary(Process(), api=baseline)['passed'])
        Api.refusal_sites = len(baseline.calls)
        for at in range(1, len(baseline.calls)+1):
            api = Api();api.fail_at = {at}
            with self.subTest(at=at):
                result = self.check_failure(Process(), api)
                self.assertLessEqual(api.resume_calls, 1)
                if at == len(baseline.calls):
                    self.assertTrue(result['resume_observed'])
                    self.assertFalse(result['cleanup_verified'])
                    self.assertEqual(api.owned, {2000: 'thread'})
                else:
                    self.assertTrue(result['cleanup_verified'])
                    self.assertEqual(api.owned, {})

    def test_primary_failure_preserved_and_all_secondary_closes_attempted(self):
        api = Api()
        def hook(name, *args):
            if name == 'next' and args[0] == 1001:
                raise t.ThreadApiError('SNAPSHOT_ENUM')
            if name == 'close' and args[0] in (1001, 2000):
                raise RuntimeError('PRIVATE_PATH_CANARY')
        api.hook = hook
        result = self.check_failure(Process(), api, 'SNAPSHOT_ENUM')
        self.assertEqual(result['secondary_close_failures'], 2)
        self.assertFalse(result['cleanup_verified'])
        self.assertEqual(api.calls[-2:], [('close', (1001,)), ('close', (2000,))])
        self.assertNotIn('PRIVATE_PATH_CANARY', json.dumps(result))
        self.assertEqual(api.resume_calls, 0)
        api = Api()
        api.hook = lambda name, *args: (_ for _ in ()).throw(RuntimeError('PRIVATE_PATH_CANARY'))
        self.check_failure(Process(), api, 'API_FAILED')

    def test_interruption_preserved_after_independent_close_attempts(self):
        api = Api();interruption = KeyboardInterrupt()
        def hook(name, *args):
            if name == 'next' and args[0] == 1001:
                raise interruption
            if name == 'close' and args[0] == 1001:
                raise OSError('PRIVATE_CANARY')
        api.hook = hook
        with self.assertRaises(KeyboardInterrupt) as caught:
            t.resume_primary(Process(), api=api)
        self.assertIs(caught.exception, interruption)
        self.assertEqual(api.calls[-2:], [('close', (1001,)), ('close', (2000,))])
        self.assertEqual(api.owned, {1001: 'snapshot'})

    def test_snapshot_exact_limit_and_one_past_refusal(self):
        api = Api()
        api.rows = [[(3, 0)]*(t.MAX_THREAD_ENTRIES-1)+[(TID, PID)]]*2
        result = t.resume_primary(Process(), api=api)
        self.assertTrue(result['passed'])
        self.assertEqual(result['snapshot_entries_examined'], 2*t.MAX_THREAD_ENTRIES)
        api = Api();api.rows[0] = [(3, 0)]*t.MAX_THREAD_ENTRIES+[(TID, PID)]
        result = self.check_failure(Process(), api, 'SNAPSHOT_LIMIT')
        self.assertEqual(result['snapshot_entries_examined'], t.MAX_THREAD_ENTRIES)
        self.assertEqual(api.resume_calls, 0)
        self.assertEqual(api.owned, {})

    def test_native_binding_wire_arguments_metadata_and_error_controls(self):
        class Function:
            def __init__(self, callback):self.callback = callback
            def __call__(self, *args):return self.callback(*args)
        class DLL:
            def __init__(self):
                self.calls, self.overrides, self.entry_size = [], {}, 16
                names = ('GetProcessId','GetProcessTimes','CreateToolhelp32Snapshot',
                         'Thread32First','Thread32Next','OpenThread','GetThreadId',
                         'GetProcessIdOfThread','GetThreadTimes','ResumeThread','CloseHandle')
                for name in names:
                    setattr(self, name, Function(lambda *args, name=name: self.call(name, args)))
            def call(self, name, args):
                self.calls.append((name, args))
                if name in self.overrides:return self.overrides[name]
                if name in ('GetProcessTimes','GetThreadTimes'):
                    stamp = START if name == 'GetProcessTimes' else START+1
                    for pointer in args[1:]:
                        value = ctypes.cast(pointer, ctypes.POINTER(native._FileTime)).contents
                        value.low = value.high = 0xDEADBEEF  # exit/kernel/user undefined, ignored
                    value = ctypes.cast(args[1], ctypes.POINTER(native._FileTime)).contents
                    value.low, value.high = stamp & 0xFFFFFFFF, stamp >> 32
                    return 1
                if name in ('Thread32First','Thread32Next'):
                    entry = ctypes.cast(args[1], ctypes.POINTER(native._ThreadEntry)).contents
                    self.assert_size(entry.size)
                    entry.size, entry.thread, entry.process = self.entry_size, TID, PID
                    return 1
                return {'GetProcessId': PID, 'CreateToolhelp32Snapshot':1000,
                        'OpenThread':2000, 'GetThreadId':TID, 'GetProcessIdOfThread':PID,
                        'ResumeThread':1, 'CloseHandle':1}[name]
            @staticmethod
            def assert_size(size):
                if size != 28:raise AssertionError('entry dwSize not reset')
        dll = DLL()
        with mock.patch.object(t.os, 'name', 'nt'), mock.patch('ctypes.WinDLL', create=True, return_value=dll) as loader:
            native = t.NativeThreadApi()
        loader.assert_called_once_with('kernel32.dll', use_last_error=True, winmode=0x0800)
        self.assertEqual(ctypes.sizeof(native._FileTime), 8)
        self.assertEqual(ctypes.sizeof(native._ThreadEntry), 28)
        self.assertEqual(native._ThreadEntry.process.offset, 12)
        self.assertEqual(native.process_identity(HANDLE), (PID, START))
        self.assertEqual(native.snapshot(), 1000)
        self.assertEqual(dll.calls[-1], ('CreateToolhelp32Snapshot', (4, 0)))
        self.assertEqual(native.first(1000), (TID, PID))
        self.assertEqual(native.next(1000), (TID, PID))
        self.assertEqual(native.open_thread(TID), 2000)
        self.assertEqual(dll.calls[-1], ('OpenThread', (0x42, False, TID)))
        self.assertEqual(native.thread_identity(2000), (TID, PID, START+1))
        self.assertEqual(native.resume(2000), 1)
        native.close(2000)
        lengths = {'GetProcessId':1,'GetProcessTimes':5,'CreateToolhelp32Snapshot':2,
                   'Thread32First':2,'Thread32Next':2,'OpenThread':3,'GetThreadId':1,
                   'GetProcessIdOfThread':1,'GetThreadTimes':5,'ResumeThread':1,'CloseHandle':1}
        for name, length in lengths.items():
            self.assertEqual(len(getattr(dll, name).argtypes), length)
        self.assertIs(dll.CreateToolhelp32Snapshot.restype, ctypes.c_void_p)
        self.assertIs(dll.OpenThread.restype, ctypes.c_void_p)
        self.assertIs(dll.ResumeThread.restype, ctypes.c_uint32)
        for size in (0, 15, 29):
            dll.entry_size = size
            with self.assertRaisesRegex(t.ThreadApiError, '^SNAPSHOT_ENTRY$'):native.first(1000)
        for name, call, code in (
                ('GetProcessId', lambda:native.process_identity(HANDLE), 'PROCESS_QUERY'),
                ('GetProcessTimes', lambda:native.process_identity(HANDLE), 'PROCESS_QUERY'),
                ('OpenThread', lambda:native.open_thread(TID), 'THREAD_OPEN'),
                ('GetThreadId', lambda:native.thread_identity(2000), 'THREAD_QUERY'),
                ('GetProcessIdOfThread', lambda:native.thread_identity(2000), 'THREAD_QUERY'),
                ('GetThreadTimes', lambda:native.thread_identity(2000), 'THREAD_QUERY'),
                ('CloseHandle', lambda:native.close(2000), 'HANDLE_CLOSE')):
            dll.overrides = {name:0}
            with self.subTest(name=name), self.assertRaisesRegex(t.ThreadApiError, '^'+code+'$'):call()
        for value in (None, 0, 2**64-1):
            dll.overrides = {'CreateToolhelp32Snapshot':value}
            with self.assertRaisesRegex(t.ThreadApiError, '^SNAPSHOT_CREATE$'):native.snapshot()
        dll.overrides = {'ResumeThread':0xFFFFFFFF}
        with self.assertRaisesRegex(t.ThreadApiError, '^RESUME_API$'):native.resume(2000)
        for name, call in (('Thread32First', native.first), ('Thread32Next', native.next)):
            dll.overrides = {name:0}
            with mock.patch('ctypes.get_last_error', create=True, return_value=18):
                self.assertIsNone(call(1000))
            with mock.patch('ctypes.get_last_error', create=True, return_value=5):
                with self.assertRaisesRegex(t.ThreadApiError, '^SNAPSHOT_ENUM$'):call(1000)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    paths = [Path(__file__).resolve(), Path(t.__file__).resolve(),
             Path(__file__).with_name('WINDOWS-SUSPENDED-THREAD.md')]
    before = {str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    if args.output and (args.output.exists() or args.output.is_symlink()):parser.error('output_must_be_fresh')
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SuspendedThreadTests))
    after = {str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    if before != after:raise ValueError('source_changed_during_controls')
    receipt = {'schema':1, 'scope':'suspended_primary_thread_source_and_api_doubles_only',
               'passed':result.wasSuccessful(), 'test_methods':result.testsRun,
               'failures':len(result.failures), 'errors':len(result.errors),
               'controlled_api_calls':Api.calls_total, 'controlled_failure_sites':Api.refusal_sites,
               'controlled_max_owned_handles':Api.max_owned,
               'snapshot_entries_limit_per_pass':t.MAX_THREAD_ENTRIES, 'snapshot_passes':2,
               'source_sha256':before, 'python_version':platform.python_version(), 'host_platform':sys.platform,
               'actual_windows_or_native_api_executed':False, 'process_or_thread_created':False,
               'compiler_or_service_executed':False, 'driver_integration_qualified':False}
    if args.output:
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':sys.exit(main())
