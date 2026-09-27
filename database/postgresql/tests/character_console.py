"""Bounded private observation of the stock GUI TestClient's own console.

Start after Popen and before releasing TestClient's launcher-version handshake.
A separate helper attaches to that exact PID and remains attached after the
client exits. It grows only the screen buffer dimensions (never writes console
characters), so one final snapshot retains real repeated lines without merging
overlapping samples. Reaching the final row fails closed rather than accepting
evidence which may have scrolled away. No raw screen text is public evidence.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import run_network_ack as network
from run_generated_schema import LOG_LIMIT, require


BUFFER_ROWS = 16384
MIN_WIDTH = 200
MAX_WIDTH = 256
MAX_SECONDS = 7200
POLL_SECONDS = 0.05
METADATA_LIMIT = 8192


def screen_text(cells, width, rows):
    """Keep physical rows and genuine duplicate lines; remove padding only."""
    require(type(width) is int and type(rows) is int and
            0 < width <= MAX_WIDTH and 0 < rows <= BUFFER_ROWS,
            'Console snapshot dimensions exceed capture bound')
    require(len(cells) == width * rows, 'Console snapshot was short')
    lines = [cells[start:start + width].rstrip(' ') for start in range(0, len(cells), width)]
    while lines and not lines[-1]:
        lines.pop()
    text = '\n'.join(lines) + ('\n' if lines else '')
    require(len(text.encode('utf-8', errors='replace')) <= LOG_LIMIT,
            'Console output exceeded capture bound')
    return text


def _paths(logs, label):
    return {kind: logs / (label + '-console' + suffix) for kind, suffix in
            (('capture', '.log'), ('ready', '-ready.json'), ('result', '-result.json'),
             ('error', '-error.json'), ('stop', '-stop'))}


def _atomic_write(path, value):
    data = value.encode('utf-8', errors='replace')
    require(len(data) <= (LOG_LIMIT if path.suffix == '.log' else METADATA_LIMIT),
            'Console evidence exceeded capture bound')
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('wb') as stream:
        stream.write(data)
    # Windows can briefly deny replacement while the parent reads the old
    # snapshot. Keep every published snapshot complete, with a bounded retry.
    deadline = time.monotonic() + 1
    while True:
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.01)


class ConsoleCapture:
    def __init__(self, pid, logs, label):
        require(type(pid) is int and 0 < pid <= 0xffffffff, 'Invalid console child PID')
        require(re.fullmatch(r'[A-Za-z0-9_-]{1,80}', label) is not None, 'Invalid console capture label')
        self.pid, self.logs, self.label = pid, Path(logs).resolve(), label
        self.paths = _paths(self.logs, label)
        self.process = None
        self._started = False
        self._stop_requested = False
        self._ready = False

    def start(self, timeout=10):
        require(os.name == 'nt', 'TestClient console observation requires Windows')
        require(not self._started and not self._stop_requested, 'Console capture can only start once')
        require(0 < timeout <= 10, 'Console readiness timeout must be at most ten seconds')
        require(self.logs.is_dir(), 'Private console log directory does not exist')
        require(all(not p.exists() and not p.is_symlink() and
                    not p.with_name(p.name + '.tmp').exists() for p in self.paths.values()),
                'Console capture paths must be new')
        self._started = True
        self.process = network.Process(
            [sys.executable, str(Path(__file__).resolve()), '--observe', str(self.pid),
             '--logs', str(self.logs), '--label', self.label],
            self.logs, self.logs, self.label + '-console-observer')
        deadline = time.monotonic() + timeout
        try:
            while True:
                self.check_bounds()
                if self.paths['ready'].exists():
                    ready = json.loads(self.paths['ready'].read_text(encoding='utf-8'))
                    require(ready.get('pid') == self.pid and ready.get('attached') is True and
                            ready.get('initial_snapshot') is True and self.paths['capture'].is_file(),
                            'Console readiness identity/snapshot is invalid')
                    self._ready = True
                    return self
                require(time.monotonic() < deadline, 'Timed out attaching TestClient console observer')
                time.sleep(POLL_SECONDS)
        except Exception:
            self.stop()
            raise

    def check_bounds(self):
        for kind, path in self.paths.items():
            for candidate in (path, path.with_name(path.name + '.tmp')):
                try:
                    size = candidate.stat().st_size
                except FileNotFoundError:  # The helper may just have atomically renamed its temporary file.
                    continue
                require(not candidate.is_symlink() and size <=
                        (LOG_LIMIT if kind == 'capture' else METADATA_LIMIT),
                        'Console evidence exceeded capture bound: ' + self.label)
        if self.process is not None:
            self.process.check_bounds()
        if self.paths['error'].exists():
            error = json.loads(self.paths['error'].read_text(encoding='utf-8'))
            raise ValueError('TestClient console observer failed: ' + error['error'])
        if self.process is not None and self.process.child.poll() is not None:
            require(self._stop_requested and self.process.child.returncode == 0 and
                    self.paths['result'].is_file(), 'TestClient console observer exited unexpectedly')
            result = json.loads(self.paths['result'].read_text(encoding='utf-8'))
            require(result.get('final_snapshot') is True, 'Console observer lacks its final snapshot')

    def text(self):
        self.check_bounds()
        path = self.paths['capture']
        return path.read_text(encoding='utf-8') if path.exists() else ''

    def stop(self):
        # Safe during partial/failed start as well as repeated driver cleanup.
        self._stop_requested = True
        if self.process is None:
            return
        if self.process.child.poll() is None:
            self.paths['stop'].touch(exist_ok=True)
            try:
                self.process.child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
        self.process.stop()

    def report(self):
        result = {'label': self.label, 'ready': self._ready,
                  'method': 'exact_pid_console_screen_buffer', 'raw_evidence_private': True,
                  'buffer_rows_limit': BUFFER_ROWS, 'capture_byte_limit': LOG_LIMIT}
        for name in ('ready', 'result', 'error'):
            path = self.paths[name]
            try:
                if not path.exists():
                    continue
                require(not path.is_symlink() and path.stat().st_size <= METADATA_LIMIT,
                        'Console report metadata exceeded bound')
                data = json.loads(path.read_text(encoding='utf-8'))
                require(isinstance(data, dict), 'Console report metadata must be an object')
                result.update({key: data[key] for key in
                               ('width', 'height', 'snapshots', 'used_rows', 'final_snapshot') if key in data})
                if name == 'error':
                    result['observer_error'] = str(data.get('error', 'Missing observer error detail'))[:2000]
            except (OSError, ValueError, TypeError) as error:
                # Reporting runs during failure cleanup. Invalid private
                # metadata must not hide the original harness failure.
                result.setdefault('metadata_errors', []).append(name + ': ' + type(error).__name__)
        if self.process is not None:
            result['observer'] = self.process.record()
        return result


class _ChangingScreen(Exception):
    pass


class _WindowsConsole:
    def __init__(self, pid, timeout=8):
        require(os.name == 'nt', 'Console helper requires Windows')
        import ctypes
        from ctypes import wintypes as w
        self.c, self.w = ctypes, w
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.handle = None
        self.attached = False

        class Coord(ctypes.Structure):
            _fields_ = [('X', w.SHORT), ('Y', w.SHORT)]

        class Rect(ctypes.Structure):
            _fields_ = [('Left', w.SHORT), ('Top', w.SHORT), ('Right', w.SHORT), ('Bottom', w.SHORT)]

        class Info(ctypes.Structure):
            _fields_ = [('dwSize', Coord), ('dwCursorPosition', Coord), ('wAttributes', w.WORD),
                        ('srWindow', Rect), ('dwMaximumWindowSize', Coord)]

        self.Coord, self.Info = Coord, Info
        signatures = {
            'FreeConsole': ([], w.BOOL), 'AttachConsole': ([w.DWORD], w.BOOL),
            'GetConsoleProcessList': ([ctypes.POINTER(w.DWORD), w.DWORD], w.DWORD),
            'CreateFileW': ([w.LPCWSTR, w.DWORD, w.DWORD, w.LPVOID, w.DWORD, w.DWORD, w.HANDLE], w.HANDLE),
            'GetConsoleScreenBufferInfo': ([w.HANDLE, ctypes.POINTER(Info)], w.BOOL),
            'SetConsoleScreenBufferSize': ([w.HANDLE, Coord], w.BOOL),
            'ReadConsoleOutputCharacterW': ([w.HANDLE, w.LPWSTR, w.DWORD, Coord,
                                             ctypes.POINTER(w.DWORD)], w.BOOL),
            'CloseHandle': ([w.HANDLE], w.BOOL),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.api, name)
            function.argtypes, function.restype = args, result
        try:
            # Never detach the harness itself; this runs in a separate helper.
            if not self.api.FreeConsole():
                self._raise_api('FreeConsole')
            deadline = time.monotonic() + timeout
            while not self.api.AttachConsole(pid):
                error = ctypes.get_last_error()
                if error != 6 or time.monotonic() >= deadline:  # ERROR_INVALID_HANDLE: no console yet.
                    self._raise_api('AttachConsole', error)
                time.sleep(POLL_SECONDS)
            self.attached = True
            peers = (w.DWORD * 32)()
            count = self.api.GetConsoleProcessList(peers, len(peers))
            if count == 0:
                self._raise_api('GetConsoleProcessList')
            require(0 < count <= len(peers), 'Console process list exceeded verification bound')
            require({pid, os.getpid()}.issubset(set(peers[:count])), 'Console is not attached to expected client PID')
            # Request both access rights for the bounded screen-buffer resize.
            # No console-character write API is called. Explicit CONOUT$ avoids
            # inherited redirected handles (the observed GUI capture failure).
            self.handle = self.api.CreateFileW('CONOUT$', 0x80000000 | 0x40000000, 0x1 | 0x2, None, 3, 0, None)
            if self.handle == ctypes.c_void_p(-1).value:
                self.handle = None
                self._raise_api('CreateFileW(CONOUT$)')
            before = self.info()
            require(0 < before.dwSize.X <= MAX_WIDTH and
                    before.dwCursorPosition.Y < before.dwSize.Y - 1,
                    'Initial console may already have scrolled beyond capture')
            self.width = max(MIN_WIDTH, before.dwSize.X)
            require(before.dwSize.Y <= BUFFER_ROWS, 'Initial console height exceeds capture bound')
            if not self.api.SetConsoleScreenBufferSize(self.handle, Coord(self.width, BUFFER_ROWS)):
                self._raise_api('SetConsoleScreenBufferSize')
            self.last_y = 0
        except Exception:
            self.close()
            raise

    def info(self):
        info = self.Info()
        if not self.api.GetConsoleScreenBufferInfo(self.handle, self.c.byref(info)):
            self._raise_api('GetConsoleScreenBufferInfo')
        return info

    def _raise_api(self, operation, error=None):
        code = self.c.get_last_error() if error is None else error
        raise OSError(f'{operation} failed: {self.c.WinError(code)}')

    def _validate(self, info):
        require((info.dwSize.X, info.dwSize.Y) == (self.width, BUFFER_ROWS),
                'Console dimensions changed after observer readiness')
        x, y = info.dwCursorPosition.X, info.dwCursorPosition.Y
        require(0 <= x < self.width and self.last_y <= y < BUFFER_ROWS - 1,
                'Console cursor reached capture bound or moved above retained output')
        return x, y

    def snapshot(self):
        for _ in range(5):
            before = self.info()
            x, y = self._validate(before)
            length = self.width * (y + 1)
            buffer = self.c.create_unicode_buffer(length)
            read = self.w.DWORD()
            if not self.api.ReadConsoleOutputCharacterW(self.handle, buffer, length, self.Coord(0, 0),
                                                         self.c.byref(read)):
                self._raise_api('ReadConsoleOutputCharacterW')
            require(read.value == length, 'Console snapshot read was incomplete')
            after = self.info()
            after_cursor = self._validate(after)
            if after_cursor == (x, y):
                self.last_y = y
                return screen_text(buffer[:length], self.width, y + 1), y + 1
        raise _ChangingScreen()

    def close(self):
        if self.handle is not None:
            self.api.CloseHandle(self.handle)
            self.handle = None
        if self.attached:
            self.api.FreeConsole()
            self.attached = False


def _observe(pid, logs, label):
    paths = _paths(logs, label)
    console = None
    started = time.monotonic()
    snapshots, previous, ready = 0, None, False
    try:
        console = _WindowsConsole(pid)
        while True:
            require(time.monotonic() - started < MAX_SECONDS, 'Console observation exceeded time bound')
            stopping = paths['stop'].exists()
            try:
                current, used_rows = console.snapshot()
            except _ChangingScreen:
                require(not stopping, 'Final console snapshot did not become stable')
                time.sleep(POLL_SECONDS)
                continue
            snapshots += 1
            if current != previous or stopping:
                _atomic_write(paths['capture'], current)
                previous = current
            record = {'pid': pid, 'attached': True, 'width': console.width, 'height': BUFFER_ROWS,
                      'snapshots': snapshots, 'used_rows': used_rows}
            if not ready:
                _atomic_write(paths['ready'], json.dumps(dict(record, initial_snapshot=True)))
                ready = True
            if stopping:
                _atomic_write(paths['result'], json.dumps(dict(record, final_snapshot=True)))
                return 0
            time.sleep(POLL_SECONDS)
    except Exception as error:
        _atomic_write(paths['error'], json.dumps({'error': str(error)[:2000]}))
        return 1
    finally:
        if console is not None:
            console.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observe', type=int, required=True)
    parser.add_argument('--logs', type=Path, required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    # Reuse public input/path validation without starting another helper.
    capture = ConsoleCapture(args.observe, args.logs, args.label)
    sys.exit(_observe(capture.pid, capture.logs, capture.label))
