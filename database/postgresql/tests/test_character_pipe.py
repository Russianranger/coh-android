"""Parser/drain tests everywhere, plus real Win32 child pipe loopback on Windows."""
from collections import deque
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest

import character_pipe as driver


def wait_until(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.005)
    raise AssertionError('Bounded wait expired')


class FakeTransport:
    def __init__(self, pid=123):
        self.pid = pid
        self.packets = deque()
        self.writes = []
        self.writable = True
        self.disconnected = False
        self.closed = False

    def connect(self):
        return self.pid

    def read(self):
        if self.packets:
            return self.packets.popleft()
        if self.disconnected:
            raise driver._Disconnected()
        return None

    def write(self, payload):
        if self.writable:
            self.writes.append(payload)
        return self.writable

    def close(self):
        self.closed = True

    def feed(self, message):
        self.packets.append((message.encode('ascii') + b'\0', True))


class DecoderTests(unittest.TestCase):
    def test_split_nul_frames_and_multiple_frames_preserve_values(self):
        decoder = driver.NulMessageDecoder()
        self.assertEqual(decoder.feed(b'Player: Hero'), [])
        self.assertEqual(decoder.feed(b' One\0MapName: maps/test.txt\0Sta'),
                         ['Player: Hero One', 'MapName: maps/test.txt'])
        self.assertEqual(decoder.feed(b'tus: Running\0'), ['Status: Running'])
        decoder.finish()

    def test_bounded_frame_with_and_without_nul(self):
        for value in (b'12345678901', b'1234567890\0'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                driver.NulMessageDecoder(10).feed(value)
        decoder = driver.NulMessageDecoder(10)
        self.assertEqual(decoder.feed(b'123456789\0'), ['123456789'])
        self.assertEqual(decoder.feed(b'a\0' * 20), ['a'] * 20)

    def test_disconnect_rejects_unterminated_partial_evidence(self):
        decoder = driver.NulMessageDecoder()
        decoder.feed(b'Status: Running')
        with self.assertRaisesRegex(ValueError, 'unterminated'):
            decoder.finish()

    def test_non_ascii_evidence_preserves_original_bytes(self):
        raw = b'ChatText: \x81\xff'
        self.assertEqual(driver.NulMessageDecoder().feed(raw + b'\0')[0].encode('latin-1'), raw)

    def test_status_colons_unknown_lines_and_event_timestamp(self):
        event = driver.parse_launcher_message(' Status: ERROR: connection failed ', monotonic=12.5, time_utc='fixture')
        self.assertEqual(event['kind'], 'Status')
        self.assertEqual(event['value'], 'ERROR: connection failed')
        self.assertEqual(event['monotonic'], 12.5)
        self.assertEqual(event['time_utc'], 'fixture')
        self.assertEqual(driver.parse_launcher_message('Status Running')['kind'], 'Unparsed')
        with self.assertRaises(ValueError):
            driver.parse_launcher_message('Player: A\0Status: Running')


class DrainTests(unittest.TestCase):
    def start_pipe(self, transport=None, **kwargs):
        transport = transport or FakeTransport()
        pipe = driver.TestClientPipe('fixture-version', _transport_factory=lambda: transport, **kwargs)
        pipe.start()
        self.addCleanup(pipe.close)
        return pipe, transport

    def verified_pipe(self):
        pipe, transport = self.start_pipe()
        pipe.bind_process(123)
        transport.feed('PID: 123')
        wait_until(lambda: pipe.snapshot()['pid_verified'])
        return pipe, transport

    def test_background_drain_version_exchange_and_retained_disconnect_evidence(self):
        pipe, transport = self.start_pipe()
        transport.feed('PID: 123')
        transport.feed('VersionRequest: NULL')
        # A connected peer's traffic is not trusted before binding the child.
        self.assertFalse(pipe.snapshot()['pid_verified'])
        self.assertEqual(transport.writes, [])
        pipe.bind_process(123)
        wait_until(lambda: transport.writes)
        self.assertEqual(transport.writes, [b'fixture-version\0'])
        for _ in range(300):
            transport.feed('HP: 100/100')
        for message in ('Player: Fixture Hero', 'MapName: maps/City_01_01.txt', 'Status: Running', 'QuitNow: 1'):
            transport.feed(message)
        wait_until(lambda: pipe.snapshot()['quit_now'])
        pipe.send('CMD logout')
        self.assertEqual(transport.writes[-1], b'CMD logout\0')
        transport.disconnected = True
        snapshot = wait_until(lambda: pipe.snapshot() if pipe.snapshot()['disconnected'] else None)
        self.assertIsNone(snapshot['error'])
        self.assertTrue(snapshot['pid_verified'])
        self.assertEqual(snapshot['version_requests'], 1)
        self.assertEqual(snapshot['player'], 'Fixture Hero')
        self.assertEqual(snapshot['map_name'], 'maps/City_01_01.txt')
        self.assertEqual(snapshot['status'], 'Running')
        self.assertEqual(len(snapshot['events']), 306)
        self.assertEqual([e['sequence'] for e in snapshot['events']], list(range(1, 307)))
        self.assertEqual(sorted(e['monotonic'] for e in snapshot['events']),
                         [e['monotonic'] for e in snapshot['events']])

    def test_os_pid_mismatch_rejects_even_a_spoofed_protocol_pid(self):
        pipe, transport = self.start_pipe(FakeTransport(pid=999))
        transport.feed('PID: 123')
        transport.feed('VersionRequest: NULL')
        pipe.bind_process(123)
        wait_until(lambda: pipe.snapshot()['error'])
        self.assertIn('Windows pipe client PID', pipe.snapshot()['error'])
        self.assertFalse(pipe.snapshot()['pid_verified'])
        self.assertEqual(pipe.snapshot()['events'], [])
        self.assertEqual(transport.writes, [])

    def test_protocol_pid_and_order_are_required(self):
        for first in ('PID: 124', 'PID: 0', 'PID: 123 junk', 'Status: Running', 'VersionRequest: NULL'):
            with self.subTest(first=first):
                pipe, transport = self.start_pipe()
                pipe.bind_process(123)
                transport.feed(first)
                wait_until(lambda: pipe.snapshot()['error'])
                self.assertFalse(pipe.snapshot()['pid_verified'])
                self.assertEqual(transport.writes, [])
                pipe.close()

    def test_duplicate_version_request_is_a_failure(self):
        pipe, transport = self.verified_pipe()
        transport.feed('VersionRequest: NULL')
        wait_until(lambda: transport.writes)
        transport.feed('VersionRequest: NULL')
        wait_until(lambda: pipe.snapshot()['error'])
        self.assertIn('repeated', pipe.snapshot()['error'])
        self.assertEqual(len(transport.writes), 1)

    def test_nonblocking_full_output_retries_and_times_out_boundedly(self):
        pipe, transport = self.verified_pipe()
        transport.writable = False
        started = time.monotonic()
        with self.assertRaises((TimeoutError, RuntimeError)):
            pipe.send('CMD logout', timeout=0.05)
        self.assertLess(time.monotonic() - started, 1)
        self.assertIn('timed out', pipe.snapshot()['error'])
        self.assertEqual(transport.writes, [])

    def test_no_send_to_unverified_or_closed_peer_and_no_double_binding(self):
        pipe, transport = self.start_pipe()
        with self.assertRaises(RuntimeError):
            pipe.send('CMD logout')
        for pid in (True, 0, -1, 0x100000000):
            with self.assertRaises(ValueError):
                pipe.bind_process(pid)
        pipe.bind_process(123)
        with self.assertRaises(RuntimeError):
            pipe.bind_process(123)
        pipe.close()
        self.assertTrue(transport.closed)
        with self.assertRaises(RuntimeError):
            pipe.send('CMD logout')

    def test_evidence_bound_and_native_message_boundary_fail_closed(self):
        pipe, transport = self.start_pipe(max_events=1)
        pipe.bind_process(123)
        transport.feed('PID: 123')
        transport.feed('Status: Running')
        wait_until(lambda: pipe.snapshot()['error'])
        self.assertIn('bound', pipe.snapshot()['error'])
        self.assertIsNone(pipe.snapshot()['status'])
        second, other = self.verified_pipe()
        other.packets.append((b'Status: Running', True))
        wait_until(lambda: second.snapshot()['error'])
        self.assertIn('unterminated', second.snapshot()['error'])
        self.assertIsNone(second.snapshot()['status'])


def windows_loopback_client(mode):
    """Independent stock CreateFileW peer; runs only in a fixture subprocess."""
    import ctypes as c
    from ctypes import wintypes as w
    api = c.WinDLL('kernel32', use_last_error=True)
    signatures = {
        'CreateFileW': ([w.LPCWSTR, w.DWORD, w.DWORD, w.LPVOID, w.DWORD, w.DWORD, w.HANDLE], w.HANDLE),
        'SetNamedPipeHandleState': ([w.HANDLE, c.POINTER(w.DWORD), c.POINTER(w.DWORD), c.POINTER(w.DWORD)], w.BOOL),
        'ReadFile': ([w.HANDLE, w.LPVOID, w.DWORD, c.POINTER(w.DWORD), w.LPVOID], w.BOOL),
        'WriteFile': ([w.HANDLE, w.LPCVOID, w.DWORD, c.POINTER(w.DWORD), w.LPVOID], w.BOOL),
        'CloseHandle': ([w.HANDLE], w.BOOL),
    }
    for name, (arguments, result) in signatures.items():
        getattr(api, name).argtypes = arguments
        getattr(api, name).restype = result
    handle = api.CreateFileW(driver.PIPE_NAME, 0xc0000000, 0, None, 3, 0, None)
    if handle == c.c_void_p(-1).value:
        raise c.WinError(c.get_last_error())
    state = w.DWORD(0x2 | 0x1)  # MESSAGE + NOWAIT, bounded fixture reads/writes.
    if not api.SetNamedPipeHandleState(handle, c.byref(state), None, None):
        raise c.WinError(c.get_last_error())

    def write(message):
        payload = message.encode('ascii') + b'\0'
        buffer = c.create_string_buffer(payload)
        written = w.DWORD()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if not api.WriteFile(handle, buffer, len(payload), c.byref(written), None):
                raise c.WinError(c.get_last_error())
            if written.value == len(payload):
                return
            if written.value:
                raise AssertionError('partial fixture message write')
            time.sleep(0.01)
        raise TimeoutError('fixture write timeout')

    def read():
        buffer = c.create_string_buffer(driver.MAX_MESSAGE)
        size = w.DWORD()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if api.ReadFile(handle, buffer, len(buffer), c.byref(size), None):
                return buffer.raw[:size.value]
            error = c.get_last_error()
            if error != 232:
                raise c.WinError(error)
            time.sleep(0.01)
        raise TimeoutError('fixture read timeout')

    try:
        write(f'PID: {os.getpid()}')
        if mode == 'idle':
            # Deliberately never read the server's output queue.
            time.sleep(5)
            return
        write('VersionRequest: NULL')
        if read() != b'loopback-version\0':
            raise AssertionError('incorrect or non-NUL version reply')
        # Exceeds the server ReadFile chunk size; exercises ERROR_MORE_DATA.
        write('SCREEN: ' + 'x' * 70000)
        for message in ('Player: Loopback Hero', 'MapName: maps/City_01_01.txt', 'Status: Running'):
            write(message)
        if read() != b'CMD logout\0':
            raise AssertionError('incorrect or non-NUL command')
        write('QuitNow: 1')
    finally:
        api.CloseHandle(handle)


@unittest.skipUnless(os.name == 'nt', 'Live Win32 named-pipe tests require Windows')
class WindowsLoopbackTests(unittest.TestCase):
    def launch_peer(self, mode='normal'):
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--pipe-client', mode],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(self.stop_peer, process)
        return process

    @staticmethod
    def stop_peer(process):
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=3)

    def test_real_message_mode_pipe_pid_version_fragment_drain_command_disconnect(self):
        with driver.TestClientPipe('loopback-version') as pipe:
            process = self.launch_peer()
            pipe.bind_process(process.pid)
            wait_until(lambda: pipe.snapshot()['status'] == 'Running', timeout=8)
            snapshot = pipe.snapshot()
            self.assertIsNone(snapshot['error'])
            self.assertTrue(snapshot['pid_verified'])
            self.assertEqual(snapshot['client_pid'], process.pid)
            self.assertEqual(snapshot['player'], 'Loopback Hero')
            self.assertEqual(snapshot['version_requests'], 1)
            self.assertEqual(len(next(e['value'] for e in snapshot['events'] if e['kind'] == 'SCREEN')), 70000)
            pipe.send('CMD logout')
            stdout, stderr = process.communicate(timeout=8)
            self.assertEqual(process.returncode, 0, (stdout + stderr).decode(errors='replace'))
            wait_until(lambda: pipe.snapshot()['disconnected'])
            self.assertTrue(pipe.snapshot()['quit_now'])
            self.assertIsNone(pipe.snapshot()['error'])

    def test_real_pipe_rejects_other_child_pid(self):
        with driver.TestClientPipe('loopback-version') as pipe:
            process = self.launch_peer()
            pipe.bind_process(process.pid + 1)
            wait_until(lambda: pipe.snapshot()['error'], timeout=8)
            self.assertIn('Windows pipe client PID', pipe.snapshot()['error'])
            self.assertFalse(pipe.snapshot()['pid_verified'])
            self.assertEqual(pipe.snapshot()['events'], [])

    def test_real_pipe_full_output_timeout_is_bounded(self):
        with driver.TestClientPipe('loopback-version') as pipe:
            process = self.launch_peer('idle')
            pipe.bind_process(process.pid)
            wait_until(lambda: pipe.snapshot()['pid_verified'], timeout=8)
            start = time.monotonic()
            with self.assertRaises((TimeoutError, RuntimeError)):
                for _ in range(64):
                    pipe.send('X' * 90000, timeout=0.1)
            self.assertLess(time.monotonic() - start, 3)
            self.assertIn('timed out', pipe.snapshot()['error'])


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--pipe-client':
        windows_loopback_client(sys.argv[2])
    else:
        unittest.main()
