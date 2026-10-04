import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import character_console as console
import run_network_ack as network


def cells(*rows, width=80):
    return ''.join(row.ljust(width) for row in rows)


class ConsoleSnapshotTests(unittest.TestCase):
    def test_snapshot_keeps_exact_diagnostics_and_actual_duplicate_lines(self):
        marker = 'Found character Synthetic Hero in slot 2'
        text = console.screen_text(cells(' simulateCharacterCreate()', '', marker, marker, ''), 80, 5)
        self.assertEqual(text, ' simulateCharacterCreate()\n\n' + marker + '\n' + marker + '\n')
        self.assertEqual(text.count(marker), 2)

    def test_final_snapshot_replaces_partial_progress_without_repeating_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'private-console.log'
            console._atomic_write(path, console.screen_text(cells('Found character Hero in sl'), 80, 1))
            final = 'Found character Hero in slot 2\nResuming character in slot 2...done\n'
            console._atomic_write(path, console.screen_text(cells(*final.splitlines()), 80, 2))
            self.assertEqual(path.read_text(), final)
            self.assertFalse(path.with_name(path.name + '.tmp').exists())

    def test_snapshot_dimensions_short_reads_and_bytes_are_bounded(self):
        for width, height, data in ((0, 1, ''), (257, 1, ''), (80, 16385, ''), (80, 1, 'short')):
            with self.subTest(width=width, height=height), self.assertRaises(ValueError):
                console.screen_text(data, width, height)
        with patch.object(console, 'LOG_LIMIT', 5), self.assertRaisesRegex(ValueError, 'capture bound'):
            console.screen_text(cells('larger'), 80, 1)

    def test_atomic_snapshot_retries_only_bounded_sharing_races(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'private-console.log'
            replace = os.replace
            with patch.object(console.os, 'replace', side_effect=[PermissionError('sharing'), None]) as move:
                console._atomic_write(path, 'marker\n')
                self.assertEqual(move.call_count, 2)
            replace(path.with_name(path.name + '.tmp'), path)
            self.assertEqual(path.read_text(), 'marker\n')
            with patch.object(console.os, 'replace', side_effect=PermissionError('sharing')), \
                    patch.object(console.time, 'monotonic', side_effect=[0, 2]), \
                    self.assertRaises(PermissionError):
                console._atomic_write(path, 'changed\n')

    def test_partial_start_cleanup_and_capture_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            capture = console.ConsoleCapture(42, Path(directory), 'test-client')
            capture.stop()
            capture.stop()
            capture.check_bounds()
            self.assertFalse(capture.report()['ready'])
            self.assertEqual(capture.text(), '')
            capture.paths['capture'].write_text('too much')
            with patch.object(console, 'LOG_LIMIT', 3), self.assertRaisesRegex(ValueError, 'capture bound'):
                capture.text()

    def test_capture_rejects_bad_identity_and_path_labels(self):
        for pid in (0, -1, True, 2 ** 32):
            with self.assertRaises(ValueError):
                console.ConsoleCapture(pid, Path('.'), 'client')
        for label in ('../client', 'with spaces', '', 'a' * 81):
            with self.assertRaises(ValueError):
                console.ConsoleCapture(42, Path('.'), label)

    def test_observer_errors_cannot_be_read_as_successful_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            capture = console.ConsoleCapture(42, Path(directory), 'client')
            capture.paths['capture'].write_text('Found character Hero in slot 2\n')
            capture.paths['error'].write_text(json.dumps({'error': 'Console cursor reached capture bound'}))
            with self.assertRaisesRegex(ValueError, 'capture bound'):
                capture.text()
            self.assertIn('capture bound', capture.report()['observer_error'])
            capture.paths['error'].write_text('malformed')
            self.assertIn('error: JSONDecodeError', capture.report()['metadata_errors'])

    def test_cursor_overflow_resize_and_backwards_movement_fail_closed(self):
        from types import SimpleNamespace as Item
        observer = console._WindowsConsole.__new__(console._WindowsConsole)
        observer.width, observer.last_y = 200, 10
        def info(x=0, y=10, width=200, height=console.BUFFER_ROWS):
            return Item(dwSize=Item(X=width, Y=height), dwCursorPosition=Item(X=x, Y=y))
        self.assertEqual(observer._validate(info()), (0, 10))
        for value in (info(y=console.BUFFER_ROWS - 1), info(y=9), info(width=80), info(x=200)):
            with self.assertRaises(ValueError):
                observer._validate(value)

    def test_windows_errors_identify_the_failing_api(self):
        from types import SimpleNamespace
        observer = console._WindowsConsole.__new__(console._WindowsConsole)
        observer.c = SimpleNamespace(get_last_error=lambda: 5, WinError=lambda code: f'WinError {code}')
        with self.assertRaisesRegex(OSError, 'SetConsoleScreenBufferSize failed: WinError 5'):
            observer._raise_api('SetConsoleScreenBufferSize')


GUI_FIXTURE = r'''
import ctypes
from ctypes import wintypes as w
import json
from pathlib import Path
import sys
import time

api = ctypes.WinDLL('kernel32', use_last_error=True)
api.FreeConsole.argtypes, api.FreeConsole.restype = [], w.BOOL
api.AllocConsole.argtypes, api.AllocConsole.restype = [], w.BOOL
api.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, w.LPVOID, w.DWORD, w.DWORD, w.HANDLE]
api.CreateFileW.restype = w.HANDLE
api.WriteConsoleW.argtypes = [w.HANDLE, w.LPCWSTR, w.DWORD, ctypes.POINTER(w.DWORD), w.LPVOID]
api.WriteConsoleW.restype = w.BOOL
api.CloseHandle.argtypes, api.CloseHandle.restype = [w.HANDLE], w.BOOL
api.FreeConsole()
if not api.AllocConsole():
    raise ctypes.WinError(ctypes.get_last_error())
handle = api.CreateFileW('CONOUT$', 0x40000000, 3, None, 3, 0, None)
if handle == ctypes.c_void_p(-1).value:
    raise ctypes.WinError(ctypes.get_last_error())
def write(text):
    written = w.DWORD()
    if not api.WriteConsoleW(handle, text, len(text), ctypes.byref(written), None):
        raise ctypes.WinError(ctypes.get_last_error())
    if written.value != len(text):
        raise RuntimeError('Fixture console write was short')
write('simulateCharacterCreate() BEFORE_RELEASE\r\n')
entered = Path(sys.argv[1])
temporary = entered.with_name(entered.name + '.tmp')
temporary.write_text(json.dumps({'pid': __import__('os').getpid()}))
temporary.replace(entered)
deadline = time.monotonic() + 30
while not Path(sys.argv[2]).exists():
    if time.monotonic() > deadline:
        raise RuntimeError('Fixture release timed out')
    time.sleep(0.01)
# More than a stock 300-row console: the first marker must remain available.
write(''.join('filler %04d\r\n' % number for number in range(400)))
write('Found character Synthetic Hero in slot 2\r\n')
write('Resuming character in slot 2...done\r\n')
write('commReqScene() AFTER_RELEASE\r\n')
write('ACTUAL_REPEATED_LINE\r\nACTUAL_REPEATED_LINE\r\n')
api.CloseHandle(handle)
# Immediate exit intentionally gives the polling observer no guaranteed chance
# to read the final marker until the GUI process has already disappeared.
'''


@unittest.skipUnless(os.name == 'nt', 'Retained stock GUI console acceptance requires Windows')
class WindowsConsoleTests(unittest.TestCase):
    def test_final_console_snapshot_survives_later_forced_client_tree_cleanup(self):
        pythonw = Path(sys.executable).with_name('pythonw.exe')
        self.assertTrue(pythonw.is_file())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entered, release = root / 'entered.json', root / 'release'
            script = GUI_FIXTURE + '\nwhile True: time.sleep(0.1)\n'
            child = network.Process([str(pythonw), '-c', script, str(entered), str(release)],
                                    root, root, 'persistent-gui')
            capture = console.ConsoleCapture(child.child.pid, root, 'persistent-gui')
            try:
                deadline = time.monotonic() + 10
                while not entered.exists():
                    self.assertIsNone(child.poll())
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(0.02)
                capture.start()
                release.touch()
                deadline = time.monotonic() + 10
                while 'commReqScene() AFTER_RELEASE\n' not in capture.text():
                    self.assertIsNone(child.poll())
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(0.02)
                self.assertIsNone(child.poll())
                capture.stop()  # Final capture precedes taskkill /T of the GUI/conhost tree.
                capture.check_bounds()
                saved = capture.text()
                child.stop()
                self.assertTrue(child.forced_stop)
                capture.check_bounds()  # Later restart health checks must still pass.
                self.assertEqual(capture.text(), saved)
                self.assertTrue(capture.report()['final_snapshot'])
                self.assertFalse(capture.report()['observer']['forced_stop'])
            finally:
                capture.stop()
                child.stop()

    def test_console_ready_before_release_and_final_diagnostics_retained_after_exit(self):
        pythonw = Path(sys.executable).with_name('pythonw.exe')
        self.assertTrue(pythonw.is_file(), 'Windows acceptance needs GUI-subsystem pythonw.exe')
        executable = pythonw.read_bytes()
        pe = struct.unpack_from('<I', executable, 0x3c)[0]
        self.assertEqual(struct.unpack_from('<H', executable, pe + 24 + 68)[0], 2)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entered, release = root / 'entered.json', root / 'release'
            child = network.Process([str(pythonw), '-c', GUI_FIXTURE, str(entered), str(release)],
                                    root, root, 'stock-gui')
            capture = console.ConsoleCapture(child.child.pid, root, 'stock-gui')
            try:
                deadline = time.monotonic() + 10
                while not entered.exists():
                    self.assertIsNone(child.poll(), 'GUI fixture exited before AllocConsole output')
                    self.assertLess(time.monotonic(), deadline, 'GUI fixture did not allocate its console')
                    time.sleep(0.02)
                self.assertEqual(json.loads(entered.read_text())['pid'], child.child.pid)
                capture.start()
                self.assertIn('simulateCharacterCreate() BEFORE_RELEASE\n', capture.text())
                self.assertNotIn('AFTER_RELEASE', capture.text())
                self.assertNotIn('BEFORE_RELEASE', child.text())
                self.assertIsNone(child.poll())
                self.assertIsNone(capture.process.child.poll())
                release.touch()
                self.assertEqual(child.wait(10), 0)
                self.assertIsNone(capture.process.child.poll(), 'Observer must retain console after child exits')
                capture.stop()
                text = capture.text()
                self.assertIn('simulateCharacterCreate() BEFORE_RELEASE\n', text)
                self.assertEqual(text.count('Found character Synthetic Hero in slot 2\n'), 1)
                self.assertIn('Resuming character in slot 2...done\n', text)
                self.assertIn('commReqScene() AFTER_RELEASE\n', text)
                self.assertEqual(text.count('ACTUAL_REPEATED_LINE\n'), 2)
                self.assertEqual(sum(line.startswith('filler ') for line in text.splitlines()), 400)
                self.assertTrue(capture.report()['final_snapshot'])
                self.assertFalse(capture.report()['observer']['forced_stop'])
                capture.check_bounds()  # Later driver phases still check stopped captures.
            finally:
                child.stop()
                capture.stop()


if __name__ == '__main__':
    unittest.main()
