"""New mock-only controls for the diagnostic adapter around the frozen core.

The runner admits both source files before importing this module. These tests
never invoke Git, a compiler, the native verifier, an extractor, or the old
failure-projection suite. Private-looking names are inert controlled sentinels.
"""
from contextlib import ExitStack
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import types
import unittest
from unittest import mock

import check_source_snapshot_verifier_status as adapter


PRIVATE = 'CONTROLLED_PRIVATE_adapter_capture_account_packet_729c'
CAPTURE = Path('/__controlled_private__/capture.cohsrc')
PACKET = Path('/__controlled_private__/groups.bin')
WORK = Path('/__controlled_private__/work')
OUTPUT = WORK / 'receipt.json'
BINARY = WORK / 'build' / 'verify-source-snapshot'
SOURCE = WORK / 'source'
REVISION = 'a' * 40
CORE_BYTES = b'CONTROLLED_FROZEN_CORE_SOURCE'
BINDING = (REVISION, {
    'native-android/engine/scenecatalog-server/check_source_snapshot_verifier.py': CORE_BYTES,
    'native-android/engine/scenecatalog-server/check_source_snapshot_verifier_status.py': b'CONTROLLED_ADAPTER_SOURCE',
})


class ControlledInterruption(BaseException):
    pass


class SnapshotStatusAdapter(unittest.TestCase):
    delegated_inspections = 0
    native_mock_invocations = 0
    binding_mock_invocations = 0
    public_stdout_checks = 0

    def harness(self, inspect=None, bindings=None, native=b'CONTROLLED_NATIVE_RESULT'):
        """Patch every executable boundary; yield only a small controlled core."""
        stack = ExitStack()
        original = mock.Mock(name='original_core_run', return_value=b'CONTROLLED_CORE_RESULT')
        core = types.SimpleNamespace(run=original)
        if inspect is None:
            inspect = lambda *args: {'private_receipt': PRIVATE}
        core.inspect = mock.Mock(name='whole_original_inspect', side_effect=inspect)

        def bind():
            type(self).binding_mock_invocations += 1
            if bindings is None:
                return BINDING
            value = next(bindings)
            if isinstance(value, BaseException):
                raise value
            return value

        def run_native(*args):
            type(self).native_mock_invocations += 1
            if isinstance(native, BaseException):
                raise native
            return native

        binding = stack.enter_context(mock.patch.object(adapter, 'source_binding', side_effect=bind))
        loader = stack.enter_context(mock.patch.object(adapter, 'load_core', return_value=core))
        native_call = stack.enter_context(mock.patch.object(adapter, 'run_native', side_effect=run_native))
        # No fallback boundary may accidentally invoke a real process.
        processes = stack.enter_context(mock.patch.object(adapter.subprocess, 'run', side_effect=AssertionError('real process boundary')))
        return stack, core, original, binding, loader, native_call, processes

    def inspect_once(self):
        type(self).delegated_inspections += 1
        return adapter.run_inspection(CAPTURE, PACKET, WORK, OUTPUT)

    def test_delegates_whole_inspect_and_preserves_private_return(self):
        receipt = {'private_receipt': PRIVATE, 'nested': {'opaque': object()}}
        h = self.harness(inspect=lambda *args: receipt)
        stack, core, original, binding, loader, native, processes = h
        with stack:
            result = self.inspect_once()
        self.assertIs(result, receipt)
        core.inspect.assert_called_once_with(CAPTURE, PACKET, WORK, OUTPUT)
        loader.assert_called_once_with(CORE_BYTES)
        self.assertEqual(binding.call_count, 2)
        self.assertIs(core.run, original)
        native.assert_not_called()
        processes.assert_not_called()

    def test_only_exact_native_pair_is_intercepted(self):
        for command in ([BINARY, SOURCE], (str(BINARY), str(SOURCE))):
            with self.subTest(command_type=type(command).__name__):
                h = self.harness()
                stack, core, original, binding, loader, native, processes = h
                core.inspect.side_effect = lambda *args: core.run(command, timeout=180)
                with stack:
                    result = self.inspect_once()
                self.assertEqual(result, b'CONTROLLED_NATIVE_RESULT')
                native.assert_called_once_with(BINARY, SOURCE)
                original.assert_not_called()
                self.assertIs(core.run, original)
                self.assertEqual(binding.call_count, 2)
                processes.assert_not_called()

    def test_other_commands_keep_original_objects_and_timeout(self):
        cases = (
            (['cc', '-MM', PRIVATE], 180),
            (['git', 'rev-parse', 'HEAD'], 30),
            ([BINARY], 180),
            ([BINARY, SOURCE, PRIVATE], 180),
            ([BINARY.with_name('other-verifier'), SOURCE], 180),
            ([BINARY, SOURCE.with_name('other-source')], 180),
            ([str(BINARY) + '-suffix', str(SOURCE)], 180),
            (['prefix-' + str(BINARY), str(SOURCE)], 180),
            (['/other-root/work/build/verify-source-snapshot', SOURCE], 180),
            ([WORK / 'build' / '..' / 'build' / 'verify-source-snapshot', SOURCE], 180),
        )
        for command, timeout in cases:
            with self.subTest(command=repr(command), timeout=timeout):
                h = self.harness()
                stack, core, original, binding, loader, native, processes = h
                core.inspect.side_effect = lambda *args: core.run(command, timeout=timeout)
                with stack:
                    result = self.inspect_once()
                self.assertEqual(result, b'CONTROLLED_CORE_RESULT')
                original.assert_called_once_with(command, timeout)
                self.assertIs(original.call_args.args[0], command)
                native.assert_not_called()
                self.assertIs(core.run, original)
                processes.assert_not_called()

    def test_nonexact_container_and_argument_types_are_not_inspected(self):
        class OpaqueList(list):
            def __iter__(self):
                raise AssertionError('nonexact command inspected')
        class OpaqueStr(str):
            def __str__(self):
                raise AssertionError('nonexact argument converted')
        commands = (OpaqueList([BINARY, SOURCE]),
                    [OpaqueStr(str(BINARY)), SOURCE],
                    iter((BINARY, SOURCE)),
                    str(BINARY))
        for command in commands:
            with self.subTest(command_type=type(command).__name__):
                h = self.harness()
                stack, core, original, binding, loader, native, processes = h
                core.inspect.side_effect = lambda *args: core.run(command, timeout=30)
                with stack:
                    self.assertEqual(self.inspect_once(), b'CONTROLLED_CORE_RESULT')
                self.assertIs(original.call_args.args[0], command)
                self.assertEqual(original.call_args.args[1], 30)
                native.assert_not_called()
                self.assertIs(core.run, original)

    def test_multiple_non_native_commands_delegate_in_order(self):
        commands = [(['cc', PRIVATE], 180), (['git', 'show', 'HEAD:controlled'], 30), (['cc', '--version'], 180)]
        h = self.harness()
        stack, core, original, binding, loader, native, processes = h
        def inspect(*args):
            return [core.run(command, timeout=timeout) for command, timeout in commands]
        core.inspect.side_effect = inspect
        with stack:
            self.assertEqual(self.inspect_once(), [b'CONTROLLED_CORE_RESULT'] * len(commands))
        self.assertEqual(original.call_args_list, [mock.call(command, timeout) for command, timeout in commands])
        native.assert_not_called()
        self.assertIs(core.run, original)

    def test_exact_native_timeout_must_be_exact_int_180(self):
        for timeout in (None, True, False, 0, 179, 181, 180.0, '180'):
            with self.subTest(timeout=repr(timeout)):
                h = self.harness()
                stack, core, original, binding, loader, native, processes = h
                core.inspect.side_effect = lambda *args: core.run([BINARY, SOURCE], timeout=timeout)
                with stack:
                    with self.assertRaises(adapter.SnapshotFailure):
                        self.inspect_once()
                native.assert_not_called()
                original.assert_not_called()
                self.assertEqual(binding.call_count, 2)
                self.assertIs(core.run, original)

    def test_second_native_call_refuses_without_a_second_execution(self):
        h = self.harness()
        stack, core, original, binding, loader, native, processes = h
        def inspect(*args):
            core.run([BINARY, SOURCE], timeout=180)
            return core.run([BINARY, SOURCE], timeout=180)
        core.inspect.side_effect = inspect
        with stack:
            with self.assertRaises(adapter.SnapshotFailure):
                self.inspect_once()
        native.assert_called_once_with(BINARY, SOURCE)
        original.assert_not_called()
        self.assertEqual(binding.call_count, 2)
        self.assertIs(core.run, original)

    def test_native_exception_restores_original_before_final_binding(self):
        for error in (ValueError(PRIVATE), adapter.SnapshotFailure('NATIVE_EXECUTION', 3, 4), ControlledInterruption(PRIVATE)):
            with self.subTest(error_type=type(error).__name__):
                h = self.harness(native=error)
                stack, core, original, binding, loader, native, processes = h
                core.inspect.side_effect = lambda *args: core.run([BINARY, SOURCE], timeout=180)
                calls = 0
                def bind():
                    nonlocal calls
                    calls += 1
                    type(self).binding_mock_invocations += 1
                    if calls == 2:
                        self.assertIs(core.run, original)
                    return BINDING
                binding.side_effect = bind
                with stack:
                    expected = adapter.SnapshotFailure if type(error) is ValueError else type(error)
                    with self.assertRaises(expected) as caught:
                        self.inspect_once()
                if type(error) is ValueError:
                    self.assertIs(type(caught.exception), adapter.SnapshotFailure)
                    self.assertEqual(caught.exception.phase, 'NATIVE_EXECUTION')
                    self.assertIsNone(caught.exception.native_stage)
                    self.assertIsNone(caught.exception.native_status)
                    self.assertNotIn(PRIVATE, str(caught.exception))
                else:
                    self.assertIs(caught.exception, error)
                self.assertEqual(calls, 2)
                native.assert_called_once_with(BINARY, SOURCE)
                self.assertIs(core.run, original)

    def test_whole_inspect_exception_restores_run_and_rechecks_sources(self):
        for error in (ValueError(PRIVATE), ControlledInterruption(PRIVATE)):
            with self.subTest(error_type=type(error).__name__):
                def inspect(*args):
                    raise error
                h = self.harness(inspect=inspect)
                stack, core, original, binding, loader, native, processes = h
                with stack:
                    with self.assertRaises(type(error)) as caught:
                        self.inspect_once()
                self.assertIs(caught.exception, error)
                self.assertIs(core.run, original)
                self.assertEqual(binding.call_count, 2)
                native.assert_not_called()

    def test_pre_binding_refusal_does_not_load_or_delegate(self):
        h = self.harness(bindings=iter((ValueError(PRIVATE),)))
        stack, core, original, binding, loader, native, processes = h
        with stack:
            with self.assertRaises(Exception):
                self.inspect_once()
        self.assertEqual(binding.call_count, 1)
        loader.assert_not_called()
        core.inspect.assert_not_called()
        native.assert_not_called()
        original.assert_not_called()

    def test_load_refusal_does_not_delegate_or_replace_core_run(self):
        h = self.harness()
        stack, core, original, binding, loader, native, processes = h
        error = ValueError(PRIVATE)
        loader.side_effect = error
        with stack:
            with self.assertRaises(ValueError) as caught:
                self.inspect_once()
        self.assertIs(caught.exception, error)
        self.assertEqual(binding.call_count, 1)
        core.inspect.assert_not_called()
        native.assert_not_called()
        self.assertIs(core.run, original)

    def test_post_binding_change_refuses_a_successful_private_receipt(self):
        changes = (
            ('b' * 40, dict(BINDING[1])),
            (REVISION, {**BINDING[1], next(iter(BINDING[1])): b'CHANGED_CORE'}),
            (REVISION, {**BINDING[1], adapter.WRAPPER_RELATIVE: b'CHANGED_WRAPPER'}),
            (REVISION, dict(list(BINDING[1].items())[:1])),
        )
        for changed in changes:
            with self.subTest(changed=repr(changed)):
                h = self.harness(bindings=iter((BINDING, changed)))
                stack, core, original, binding, loader, native, processes = h
                with stack:
                    with self.assertRaises(ValueError):
                        self.inspect_once()
                core.inspect.assert_called_once()
                self.assertEqual(binding.call_count, 2)
                self.assertIs(core.run, original)
                native.assert_not_called()

    def test_post_binding_exception_restores_run_and_cannot_return_success(self):
        error = ValueError(PRIVATE)
        h = self.harness(bindings=iter((BINDING, error)))
        stack, core, original, binding, loader, native, processes = h
        with stack:
            with self.assertRaises(ValueError) as caught:
                self.inspect_once()
        self.assertIs(caught.exception, error)
        self.assertEqual(binding.call_count, 2)
        self.assertIs(core.run, original)

    def test_late_source_refusal_suppresses_native_pair_in_public_result(self):
        changes = (('b' * 40, dict(BINDING[1])), ValueError(PRIVATE))
        for changed in changes:
            with self.subTest(late_type=type(changed).__name__):
                h = self.harness(bindings=iter((BINDING, changed)),
                    native=adapter.SnapshotFailure('NATIVE_EXECUTION', 3, 4))
                stack, core, original, binding, loader, native, processes = h
                core.inspect.side_effect = lambda *args: core.run([BINARY, SOURCE], timeout=180)
                output = io.StringIO()
                argv = ['controlled-adapter', '--capture', str(CAPTURE),
                        '--native-packet', str(PACKET), '--work', str(WORK),
                        '--output', str(OUTPUT)]
                with stack, mock.patch.object(adapter.sys, 'argv', argv), \
                     mock.patch.object(adapter.sys, 'stdout', output):
                    self.assertEqual(adapter.main(), 2)
                type(self).public_stdout_checks += 1
                result = json.loads(output.getvalue())
                self.assertEqual(result, {'schema': adapter.SCHEMA, 'passed': False,
                    'failure': 'verification_refused', 'phase': 'UNKNOWN',
                    'native_stage': None, 'native_status': None,
                    'source_generation_admitted': False, 'world_authority': False})
                self.assertNotIn(PRIVATE, output.getvalue())
                self.assertEqual(binding.call_count, 2)
                native.assert_called_once_with(BINARY, SOURCE)
                self.assertIs(core.run, original)

    def test_main_only_exposes_fixed_success_or_failure_projection(self):
        success = {'schema': adapter.SCHEMA, 'passed': True,
                   'private_receipt_written': True,
                   'source_generation_admitted': False, 'world_authority': False}
        cases = (
            ({'private_receipt': PRIVATE}, 0, success),
            (ValueError(PRIVATE), 2, {'schema': adapter.SCHEMA, 'passed': False,
                'failure': 'verification_refused', 'phase': 'UNKNOWN',
                'native_stage': None, 'native_status': None,
                'source_generation_admitted': False, 'world_authority': False}),
            (adapter.SnapshotFailure('NATIVE_EXECUTION', 3, 4), 2,
             {'schema': adapter.SCHEMA, 'passed': False,
              'failure': 'verification_refused', 'phase': 'NATIVE_EXECUTION',
              'native_stage': 3, 'native_status': 4,
              'source_generation_admitted': False, 'world_authority': False}),
        )
        for result, status, expected in cases:
            with self.subTest(status=status, result_type=type(result).__name__):
                output = io.StringIO()
                def inspect(*args):
                    if isinstance(result, Exception):
                        raise result
                    return result
                argv = ['controlled-adapter', '--capture', str(CAPTURE),
                        '--native-packet', str(PACKET), '--work', str(WORK),
                        '--output', str(OUTPUT)]
                with mock.patch.object(adapter, 'run_inspection', side_effect=inspect) as call, \
                     mock.patch.object(adapter.sys, 'argv', argv), \
                     mock.patch.object(adapter.sys, 'stdout', output), \
                     mock.patch.object(adapter.subprocess, 'run', side_effect=AssertionError('real process boundary')) as process:
                    self.assertEqual(adapter.main(), status)
                type(self).public_stdout_checks += 1
                raw = output.getvalue()
                self.assertEqual(raw.count('\n'), 1)
                self.assertEqual(json.loads(raw), expected)
                self.assertNotIn(PRIVATE, raw)
                self.assertNotIn(str(CAPTURE), raw)
                self.assertNotIn(str(WORK), raw)
                call.assert_called_once_with(CAPTURE, PACKET, WORK, OUTPUT)
                process.assert_not_called()


class SnapshotAdapterSourceGuards(unittest.TestCase):
    source_binding_cases = 0
    source_read_cases = 0

    def test_fixed_core_pin_and_source_names(self):
        self.assertEqual(adapter.CORE_SHA256, '6285a25fb727c86d6d2b9cd1eeacc3c1f398058f4dceb4821122a30a97600d6d')
        self.assertEqual(adapter.CORE_RELATIVE, 'native-android/engine/scenecatalog-server/check_source_snapshot_verifier.py')
        self.assertEqual(adapter.WRAPPER_RELATIVE, 'native-android/engine/scenecatalog-server/check_source_snapshot_verifier_status.py')
        self.assertEqual(adapter.SOURCE_LIMIT, 1024 * 1024)

    def binding_harness(self, revision=None, committed=None, reads=None, digest=None):
        stack = ExitStack()
        checkout = Path('/__controlled_private__/checkout')
        wrapper = b'CONTROLLED_WRAPPER_SOURCE'
        source = {adapter.WRAPPER_RELATIVE: wrapper, adapter.CORE_RELATIVE: CORE_BYTES}
        raw_revision = REVISION.encode() + b'\n' if revision is None else revision
        def run(command, **kwargs):
            if command == ['git', 'rev-parse', 'HEAD']:
                value = raw_revision
            else:
                self.assertEqual(command[:2], ['git', 'show'])
                self.assertTrue(command[2].startswith(REVISION + ':'))
                name = command[2].split(':', 1)[1]
                self.assertIn(name, source)
                value = source[name] if committed is None else committed.get(name, source[name])
            if isinstance(value, BaseException):
                raise value
            if isinstance(value, subprocess.CompletedProcess):
                return value
            return subprocess.CompletedProcess(command, 0, value, b'')
        def read(path):
            if reads is not None:
                value = next(reads)
                if isinstance(value, BaseException):
                    raise value
                return value
            return source[str(path.relative_to(checkout))]
        stack.enter_context(mock.patch.object(adapter, 'ROOT', checkout))
        stack.enter_context(mock.patch.object(adapter, '__file__', str(checkout / adapter.WRAPPER_RELATIVE)))
        stack.enter_context(mock.patch.object(type(checkout), 'resolve', lambda path: path))
        reader = stack.enter_context(mock.patch.object(adapter, 'source_bytes', side_effect=read))
        git = stack.enter_context(mock.patch.object(adapter.subprocess, 'run', side_effect=run))
        hasher = stack.enter_context(mock.patch.object(adapter.hashlib, 'sha256', return_value=types.SimpleNamespace(hexdigest=lambda: adapter.CORE_SHA256 if digest is None else digest)))
        return stack, checkout, source, reader, git, hasher

    def binding_once(self):
        type(self).source_binding_cases += 1
        return adapter.source_binding()

    def test_binding_admits_own_and_core_current_bytes_and_rereads(self):
        h = self.binding_harness()
        stack, checkout, source, reader, git, hasher = h
        with stack:
            self.assertEqual(self.binding_once(), (REVISION, source))
        expected_paths = [checkout / adapter.WRAPPER_RELATIVE, checkout / adapter.CORE_RELATIVE] * 2
        self.assertEqual(reader.call_args_list, [mock.call(path) for path in expected_paths])
        self.assertEqual(git.call_count, 3)
        for call in git.call_args_list:
            self.assertEqual(call.kwargs, {'cwd': checkout, 'capture_output': True, 'timeout': 30})
        hasher.assert_called_once_with(CORE_BYTES)

    def test_binding_rejects_bad_revision_before_reading_source(self):
        bad = (b'', b'a' * 40, b'a' * 40 + b'\n\n', b'g' * 40 + b'\n',
               b'A' * 40 + b'\n', b'\xff' * 40 + b'\n',
               subprocess.CompletedProcess([], 1, REVISION.encode() + b'\n', b''),
               subprocess.CompletedProcess([], 0, REVISION.encode() + b'\n', PRIVATE.encode()),
               subprocess.TimeoutExpired(['git'], 30, output=PRIVATE.encode()))
        for revision in bad:
            with self.subTest(revision_type=type(revision).__name__, revision=repr(revision)):
                h = self.binding_harness(revision=revision)
                stack, checkout, source, reader, git, hasher = h
                with stack:
                    with self.assertRaises(Exception):
                        self.binding_once()
                reader.assert_not_called()
                self.assertEqual(git.call_count, 1)
                hasher.assert_not_called()

    def test_binding_rejects_wrong_checkout_before_git(self):
        h = self.binding_harness()
        stack, checkout, source, reader, git, hasher = h
        with stack, mock.patch.object(adapter, '__file__', str(checkout / 'other.py')):
            with self.assertRaises(ValueError):
                self.binding_once()
        git.assert_not_called()
        reader.assert_not_called()

    def test_binding_rejects_core_pin_before_committed_source_queries(self):
        h = self.binding_harness(digest='b' * 64)
        stack, checkout, source, reader, git, hasher = h
        with stack:
            with self.assertRaises(ValueError):
                self.binding_once()
        self.assertEqual(reader.call_count, 2)
        self.assertEqual(git.call_count, 1)

    def test_binding_refuses_either_git_source_mismatch_and_api_failure(self):
        values = (b'CHANGED_SOURCE', b'', b'x' * (adapter.SOURCE_LIMIT + 1),
                  subprocess.CompletedProcess([], 1, b'', PRIVATE.encode()),
                  subprocess.CompletedProcess([], 0, CORE_BYTES, PRIVATE.encode()),
                  subprocess.TimeoutExpired(['git'], 30, output=PRIVATE.encode()))
        for name in (adapter.WRAPPER_RELATIVE, adapter.CORE_RELATIVE):
            for value in values:
                with self.subTest(name=name, value_type=type(value).__name__):
                    h = self.binding_harness(committed={name: value})
                    stack, checkout, source, reader, git, hasher = h
                    with stack:
                        with self.assertRaises(Exception):
                            self.binding_once()
                    self.assertLessEqual(reader.call_count, 2)

    def test_binding_reread_change_or_error_cannot_be_admitted(self):
        for reads in (
            (b'CONTROLLED_WRAPPER_SOURCE', CORE_BYTES, b'CHANGED_WRAPPER'),
            (b'CONTROLLED_WRAPPER_SOURCE', CORE_BYTES, b'CONTROLLED_WRAPPER_SOURCE', b'CHANGED_CORE'),
            (b'CONTROLLED_WRAPPER_SOURCE', CORE_BYTES, ValueError(PRIVATE)),
        ):
            with self.subTest(read_count=len(reads)):
                h = self.binding_harness(reads=iter(reads))
                stack, checkout, source, reader, git, hasher = h
                with stack:
                    with self.assertRaises(ValueError):
                        self.binding_once()
                self.assertEqual(git.call_count, 3)

    def test_loader_executes_only_verified_bytes_with_original_core_file(self):
        marker = object()
        with mock.patch.object(adapter.hashlib, 'sha256', return_value=types.SimpleNamespace(hexdigest=lambda: adapter.CORE_SHA256)) as hasher, \
             mock.patch('builtins.compile', return_value=marker) as compiler, \
             mock.patch('builtins.exec') as execute, \
             mock.patch.object(adapter.subprocess, 'run', side_effect=AssertionError('real process boundary')) as process:
            core = adapter.load_core(CORE_BYTES)
        self.assertIs(type(core), types.ModuleType)
        self.assertEqual(core.__name__, 'coh_byte_exact_private_source_snapshot_core')
        self.assertEqual(core.__file__, str(adapter.ROOT / adapter.CORE_RELATIVE))
        hasher.assert_called_once_with(CORE_BYTES)
        compiler.assert_called_once_with(CORE_BYTES, core.__file__, 'exec')
        execute.assert_called_once_with(marker, core.__dict__)
        process.assert_not_called()

    def test_loader_rejects_nonbytes_or_wrong_pin_before_compile(self):
        for raw in (None, '', bytearray(CORE_BYTES), memoryview(CORE_BYTES), CORE_BYTES):
            with self.subTest(raw_type=type(raw).__name__):
                with mock.patch.object(adapter.hashlib, 'sha256', return_value=types.SimpleNamespace(hexdigest=lambda: 'b' * 64)), \
                     mock.patch('builtins.compile') as compiler, mock.patch('builtins.exec') as execute:
                    with self.assertRaises(ValueError):
                        adapter.load_core(raw)
                compiler.assert_not_called()
                execute.assert_not_called()

    def source_read(self, raw=b'bounded source', *, records=None, symlink=False):
        type(self).source_read_cases += 1
        info = types.SimpleNamespace(st_dev=1, st_ino=2, st_uid=3, st_nlink=1,
            st_size=len(raw), st_mtime_ns=4, st_ctime_ns=5, st_mode=stat.S_IFREG | 0o600)
        sequence = [info] * 5 if records is None else records(info)
        stream = mock.MagicMock(name='controlled_source_stream')
        stream.fileno.return_value = 987654
        stream.read.return_value = raw
        stream.__enter__.return_value = stream
        with mock.patch.object(type(CAPTURE), 'is_symlink', return_value=symlink), \
             mock.patch.object(type(CAPTURE), 'lstat', side_effect=(sequence[0], sequence[4])) as lstat, \
             mock.patch.object(adapter.os, 'open', return_value=987654) as opened, \
             mock.patch.object(adapter.os, 'fdopen', return_value=stream) as fdopen, \
             mock.patch.object(adapter.os, 'fstat', side_effect=sequence[1:4]) as fstat:
            try:
                result = adapter.source_bytes(CAPTURE)
                error = None
            except Exception as caught:
                result = None
                error = caught
        return result, error, stream, lstat, opened, fdopen, fstat

    def test_source_reader_bounded_regular_identity_and_context_cleanup(self):
        raw = b'controlled bounded source'
        result, error, stream, lstat, opened, fdopen, fstat = self.source_read(raw)
        self.assertIsNone(error)
        self.assertEqual(result, raw)
        self.assertEqual(lstat.call_count, 2)
        self.assertEqual(fstat.call_count, 2)
        opened.assert_called_once_with(CAPTURE, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        fdopen.assert_called_once_with(987654, 'rb')
        stream.read.assert_called_once_with(adapter.SOURCE_LIMIT + 1)
        stream.__exit__.assert_called_once()

    def test_source_reader_refuses_links_invalid_extent_and_mutation(self):
        def changed(info, field, value):
            return types.SimpleNamespace(**{**vars(info), field: value})
        cases = [('symlink', True, None)]
        for field, value in (('st_nlink', 2), ('st_size', 0), ('st_size', adapter.SOURCE_LIMIT + 1), ('st_mode', stat.S_IFDIR | 0o700)):
            cases.append((field, False, lambda info, f=field, v=value: [changed(info, f, v)] * 5))
        for index in (1, 2, 4):
            for field in ('st_dev', 'st_ino', 'st_uid', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns'):
                def records(info, i=index, f=field):
                    result = [info] * 5
                    result[i] = changed(info, f, getattr(info, f) + 1)
                    return result
                cases.append((str(index) + ':' + field, False, records))
        for label, symlink, records in cases:
            with self.subTest(case=label):
                result, error, stream, lstat, opened, fdopen, fstat = self.source_read(symlink=symlink, records=records)
                self.assertIsNone(result)
                self.assertIsInstance(error, ValueError)
                if symlink or label in ('st_nlink', 'st_size', 'st_mode'):
                    opened.assert_not_called()
                else:
                    stream.__exit__.assert_called_once()


class ControlledResult(unittest.TextTestResult):
    successful_subtests = 0
    failed_subtests = 0
    def addSubTest(self, test, subtest, err):
        if err is None:
            self.successful_subtests += 1
        else:
            self.failed_subtests += 1
        super().addSubTest(test, subtest, err)


def case_counts(result):
    return {
        'schema': 'coh-snapshot-status-adapter-mocks-v1',
        'passed': result.wasSuccessful(),
        'test_methods': result.testsRun,
        'controlled_subtest_cases': result.successful_subtests + result.failed_subtests,
        'mock_only': True,
        'old_projection_tests_reexecuted': False,
        'compiler_or_native_executed': False,
    }


if __name__ == '__main__':
    result = unittest.TextTestRunner(resultclass=ControlledResult, verbosity=1).run(
        unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__)))
    print(json.dumps(case_counts(result), sort_keys=True))
    raise SystemExit(0 if result.wasSuccessful() else 1)
