"""Bounded TestClientLauncher named pipe and its platform-independent decoder.

Create this server before launching TestClient, then bind_process(child.pid).
The only supported peer is that exact local Windows process. Raw events remain
in memory; callers decide whether/how to retain private evidence on disk.
"""
from collections import deque
from datetime import datetime, timezone
import os
import re
import threading
import time


PIPE_NAME = r'\\.\pipe\TestClientLauncher'
MAX_MESSAGE = 100000  # PipeClientSendMessage's stock buffer, including NUL.
_KINDS = {name.casefold(): name for name in
          ('PID', 'Player', 'MapName', 'Status', 'QuitNow', 'VersionRequest', 'Host', 'AuthName')}


def parse_launcher_message(raw, *, monotonic=None, time_utc=None):
    """Parse the first colon only; a status's value can itself contain colons."""
    if '\0' in raw:
        raise ValueError('Embedded NUL in decoded launcher message')
    command, separator, value = raw.partition(':')
    kind = _KINDS.get(command.strip().casefold(), command.strip()) if separator else 'Unparsed'
    return {'kind': kind, 'value': value.strip() if separator else raw,
            'raw': raw, 'monotonic': time.monotonic() if monotonic is None else monotonic,
            'time_utc': datetime.now(timezone.utc).isoformat() if time_utc is None else time_utc}


class NulMessageDecoder:
    """Preserve framing across ReadFile fragments and reject unbounded input."""
    def __init__(self, limit=MAX_MESSAGE):
        self.limit = limit
        self.pending = bytearray()

    def feed(self, data):
        if len(self.pending) + len(data) > self.limit and b'\0' not in data:
            raise ValueError('Launcher message exceeds bounded frame size')
        self.pending.extend(data)
        messages = []
        while b'\0' in self.pending:
            end = self.pending.index(0)
            if end + 1 > self.limit:
                raise ValueError('Launcher message exceeds bounded frame size')
            raw = bytes(self.pending[:end])
            del self.pending[:end + 1]
            # The fixture protocol is ASCII. Preserve other ANSI bytes one for
            # one in raw evidence without guessing the child's Windows locale.
            messages.append(raw.decode('latin-1'))
        if len(self.pending) >= self.limit:
            raise ValueError('Launcher message is missing its bounded NUL terminator')
        return messages

    def finish(self):
        if self.pending:
            raise ValueError('Launcher disconnected with an unterminated message')


class _Disconnected(Exception):
    pass


class _WindowsPipe:
    """All operations use PIPE_NOWAIT; no FlushFileBuffers or blocking connect."""
    def __init__(self):
        if os.name != 'nt':
            raise OSError('The TestClient launcher pipe requires Windows')
        import ctypes
        from ctypes import wintypes as w
        self.c = ctypes
        self.w = w
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        signatures = {
            'CreateNamedPipeW': ([w.LPCWSTR, w.DWORD, w.DWORD, w.DWORD, w.DWORD,
                                  w.DWORD, w.DWORD, w.LPVOID], w.HANDLE),
            'ConnectNamedPipe': ([w.HANDLE, w.LPVOID], w.BOOL),
            'GetNamedPipeClientProcessId': ([w.HANDLE, ctypes.POINTER(w.ULONG)], w.BOOL),
            'PeekNamedPipe': ([w.HANDLE, w.LPVOID, w.DWORD, ctypes.POINTER(w.DWORD),
                               ctypes.POINTER(w.DWORD), ctypes.POINTER(w.DWORD)], w.BOOL),
            'ReadFile': ([w.HANDLE, w.LPVOID, w.DWORD, ctypes.POINTER(w.DWORD), w.LPVOID], w.BOOL),
            'WriteFile': ([w.HANDLE, w.LPCVOID, w.DWORD, ctypes.POINTER(w.DWORD), w.LPVOID], w.BOOL),
            'DisconnectNamedPipe': ([w.HANDLE], w.BOOL),
            'CloseHandle': ([w.HANDLE], w.BOOL),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.api, name)
            function.argtypes, function.restype = args, result
        # FIRST_PIPE_INSTANCE fails closed if the real launcher/another harness
        # already owns this name. REJECT_REMOTE_CLIENTS keeps PID binding local.
        self.handle = self.api.CreateNamedPipeW(
            PIPE_NAME, 0x3 | 0x80000, 0x4 | 0x2 | 0x1 | 0x8,
            1, 131072, 131072, 0, None)
        if self.handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())

    def connect(self):
        if self.api.ConnectNamedPipe(self.handle, None):
            # In NOWAIT mode success can mean only "entered listening state".
            # The next poll reports PIPE_CONNECTED once a real client exists.
            return None
        error = self.c.get_last_error()
        if error == 536:  # ERROR_PIPE_LISTENING
            return None
        if error != 535:  # ERROR_PIPE_CONNECTED (including the connect race)
            raise self.c.WinError(error)
        pid = self.w.ULONG()
        if not self.api.GetNamedPipeClientProcessId(self.handle, self.c.byref(pid)):
            raise self.c.WinError(self.c.get_last_error())
        return pid.value

    def read(self):
        available = self.w.DWORD()
        if not self.api.PeekNamedPipe(self.handle, None, 0, None, self.c.byref(available), None):
            error = self.c.get_last_error()
            if error in (109, 232, 233):
                raise _Disconnected()
            raise self.c.WinError(error)
        if not available.value:
            return None
        buffer = self.c.create_string_buffer(65536)
        read = self.w.DWORD()
        success = self.api.ReadFile(self.handle, buffer, len(buffer), self.c.byref(read), None)
        if not success:
            error = self.c.get_last_error()
            if error == 232:  # NOWAIT, no message is available.
                return None
            if error in (109, 233):
                raise _Disconnected()
            if error != 234:  # ERROR_MORE_DATA: preserve this partial message.
                raise self.c.WinError(error)
        if not read.value:
            raise ValueError('Empty Windows pipe message lacks a NUL terminator')
        return buffer.raw[:read.value], bool(success)

    def write(self, payload):
        written = self.w.DWORD()
        buffer = self.c.create_string_buffer(payload)
        success = self.api.WriteFile(self.handle, buffer, len(payload), self.c.byref(written), None)
        if not success:
            error = self.c.get_last_error()
            if error == 232:
                return False
            if error in (109, 233):
                raise _Disconnected()
            raise self.c.WinError(error)
        # Message-mode NOWAIT WriteFile can succeed with zero bytes when its
        # output quota is exhausted. Retry the WHOLE message with a deadline.
        if written.value == 0:
            return False
        if written.value != len(payload):
            raise ValueError('Unexpected partial message-mode pipe write')
        return True

    def close(self):
        if self.handle is not None:
            self.api.DisconnectNamedPipe(self.handle)
            self.api.CloseHandle(self.handle)
            self.handle = None


class _Write:
    def __init__(self, payload, timeout):
        self.payload = payload
        self.deadline = time.monotonic() + timeout
        self.done = threading.Event()
        self.error = None


class TestClientPipe:
    """One-child, continuously drained launcher pipe with bounded evidence.

    Use ``with TestClientPipe(version) as pipe`` BEFORE Popen, and immediately
    call ``pipe.bind_process(child.pid)``. A successful bind is required both
    at the Windows transport level and in TestClient's initial PID message.
    ``send`` acknowledges completion of WriteFile, not execution by TestClient.
    """
    __test__ = False

    def __init__(self, version, *, max_events=20000, max_evidence_bytes=8 * 1024 * 1024,
                 _transport_factory=None):
        self.version = self._encode(version)
        self.max_events = max_events
        self.max_evidence_bytes = max_evidence_bytes
        self._transport_factory = _transport_factory or _WindowsPipe
        self._transport = None
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread = None
        self._writes = deque()
        self._decoder = NulMessageDecoder()
        self._expected_pid = None
        self._events = []
        self._evidence_bytes = 0
        self._state = {'connected': False, 'disconnected': False, 'client_pid': None,
                       'pid_verified': False, 'player': None, 'map_name': None,
                       'status': None, 'quit_now': False, 'version_requests': 0, 'error': None}

    @staticmethod
    def _encode(message):
        if not isinstance(message, str) or not message or '\0' in message:
            raise ValueError('Pipe output must be nonempty text without NUL')
        payload = message.encode('ascii') + b'\0'
        if len(payload) > MAX_MESSAGE:
            raise ValueError('Pipe output exceeds bounded message size')
        return payload

    def start(self):
        if self._thread is not None or self._stop.is_set():
            raise RuntimeError('A launcher pipe instance can only be started once')
        self._transport = self._transport_factory()
        self._thread = threading.Thread(target=self._run, name='TestClient-pipe-drain', daemon=True)
        self._thread.start()
        return self

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc, traceback):
        self.close()

    def bind_process(self, pid):
        if type(pid) is not int or not 0 < pid <= 0xffffffff:
            raise ValueError('Expected a positive Windows child process ID')
        with self._lock:
            if self._expected_pid is not None:
                raise RuntimeError('Launcher pipe is already bound to a child')
            self._expected_pid = pid
        self._wake.set()

    def snapshot(self):
        with self._lock:
            return dict(self._state, events=[dict(event) for event in self._events])

    def send(self, command, timeout=3):
        if not 0 < timeout <= 60:
            raise ValueError('Pipe write timeout must be between zero and 60 seconds')
        payload = self._encode(command)
        with self._lock:
            if not self._state['pid_verified'] or self._state['error'] or self._state['disconnected'] or self._stop.is_set():
                raise RuntimeError('Cannot send without a live, verified TestClient pipe')
            request = self._enqueue(payload, timeout)
        self._wake.set()
        if not request.done.wait(timeout):
            self._fail('Launcher pipe write timed out')
            raise TimeoutError('Launcher pipe write timed out')
        if request.error:
            raise RuntimeError(request.error)

    def _enqueue(self, payload, timeout):
        if len(self._writes) >= 64:
            raise ValueError('Launcher pipe write queue exceeded its bound')
        request = _Write(payload, timeout)
        self._writes.append(request)
        return request

    def _fail(self, reason):
        with self._lock:
            if self._state['error'] is None:
                self._state['error'] = reason
        self._stop.set()
        self._wake.set()

    def _record(self, raw):
        event = parse_launcher_message(raw)
        with self._lock:
            if len(self._events) >= self.max_events or self._evidence_bytes + len(raw) > self.max_evidence_bytes:
                raise ValueError('Launcher evidence exceeded its configured bound')
            if event['kind'] == 'PID':
                if not re.fullmatch(r'[1-9][0-9]{0,9}', event['value']) or int(event['value']) != self._expected_pid:
                    raise ValueError('TestClient protocol PID does not match the launched child')
                self._state['pid_verified'] = True
            elif not self._state['pid_verified']:
                raise ValueError('TestClient sent evidence before its required PID message')
            event['sequence'] = len(self._events) + 1
            self._events.append(event)
            self._evidence_bytes += len(raw)
            fields = {'Player': 'player', 'MapName': 'map_name', 'Status': 'status'}
            if event['kind'] in fields:
                self._state[fields[event['kind']]] = event['value']
            elif event['kind'] == 'QuitNow':
                self._state['quit_now'] = True
            elif event['kind'] == 'VersionRequest':
                self._state['version_requests'] += 1
                if self._state['version_requests'] != 1:
                    raise ValueError('Unexpected repeated TestClient version request')
                self._enqueue(self.version, 3)

    def _run(self):
        try:
            while not self._stop.is_set():
                with self._lock:
                    client_pid = self._state['client_pid']
                    expected_pid = self._expected_pid
                if client_pid is None:
                    client_pid = self._transport.connect()
                    if client_pid is not None:
                        with self._lock:
                            self._state['client_pid'] = client_pid
                            self._state['connected'] = True
                if client_pid is not None and expected_pid is not None:
                    if client_pid != expected_pid:
                        raise ValueError('Windows pipe client PID does not match the launched child')
                    # A bounded batch keeps outgoing writes and stop responsive
                    # even while the stock client streams continuous statistics.
                    for _ in range(128):
                        if self._stop.is_set():
                            break
                        packet = self._transport.read()
                        if packet is None:
                            break
                        data, message_complete = packet
                        for raw in self._decoder.feed(data):
                            self._record(raw)
                        if message_complete:
                            self._decoder.finish()
                    with self._lock:
                        if self._writes:
                            request = self._writes[0]
                            if time.monotonic() >= request.deadline:
                                raise TimeoutError('Launcher pipe write timed out')
                            if self._transport.write(request.payload):
                                self._writes.popleft()
                                request.done.set()
                self._wake.wait(0.01)
                self._wake.clear()
        except _Disconnected:
            with self._lock:
                self._state['disconnected'] = True
                self._state['connected'] = False
            try:
                self._decoder.finish()
            except ValueError as exc:
                self._fail(str(exc))
        except Exception as exc:
            self._fail(f'{type(exc).__name__}: {exc}')
        finally:
            with self._lock:
                while self._writes:
                    request = self._writes.popleft()
                    request.error = self._state['error'] or 'TestClient pipe disconnected or closed'
                    request.done.set()
            self._stop.set()

    def close(self):
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(2)
            if self._thread.is_alive():
                raise RuntimeError('Nonblocking TestClient pipe thread did not stop within two seconds')
        if self._transport is not None:
            self._transport.close()
            self._transport = None
        with self._lock:
            self._state['connected'] = False
