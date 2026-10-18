"""Verify and resume the sole initial thread of an owned suspended Popen.

The caller owns a one-shot, nonconcurrent CREATE_SUSPENDED launch, has already
successfully assigned its exact Popen to its job, and retains the process handle
through this call. No other actor may create/inject/resume threads in that child.
This helper does not launch, assign, reopen a process by PID, or accept raw
PID/TID selectors. A refused or interrupted call must never be retried: the
caller terminates its owned child/job, including after a late close failure.
"""

import os


MAX_THREAD_ENTRIES = 65536
SCHEMA = 'coh-owned-suspended-primary-thread-v1'
TRUE_FIELDS = frozenset({
    'passed', 'process_identity_verified', 'single_owned_thread_verified',
    'thread_identity_verified', 'generation_recheck_verified', 'resume_attempted',
    'previous_suspend_count_one', 'resume_observed', 'snapshots_closed',
    'thread_handle_closed', 'cleanup_verified',
})
_FAILURES = frozenset({
    'INPUT', 'PLATFORM', 'PROCESS_QUERY', 'PROCESS_IDENTITY', 'PROCESS_EXITED',
    'SNAPSHOT_CREATE', 'SNAPSHOT_ENUM', 'SNAPSHOT_ENTRY', 'SNAPSHOT_LIMIT',
    'SINGLE_THREAD', 'THREAD_OPEN', 'THREAD_QUERY', 'THREAD_IDENTITY',
    'GENERATION_CHANGED', 'RESUME_API', 'RESUME_COUNT', 'HANDLE_CLOSE', 'API_FAILED',
})


class ThreadApiError(ValueError):
    def __init__(self, code):
        super().__init__(code if code in _FAILURES else 'API_FAILED')


class NativeThreadApi:
    """Lazy System32 binding; successful open/snapshot transfers one handle.

    Failed acquisition transfers none. A failed close retains caller ownership.
    FILETIME exit fields are deliberately ignored: their contents are undefined
    for live processes/threads. No privilege adjustment or thread suspension is
    performed. Only THREAD_QUERY_INFORMATION | THREAD_SUSPEND_RESUME is requested.
    """

    def __init__(self):
        import ctypes as c
        if os.name != 'nt' or c.sizeof(c.c_void_p) != 8:
            raise ThreadApiError('PLATFORM')
        self._c = c
        class FileTime(c.Structure):
            _fields_ = [('low', c.c_uint32), ('high', c.c_uint32)]
        class ThreadEntry(c.Structure):
            _fields_ = [('size', c.c_uint32), ('usage', c.c_uint32),
                        ('thread', c.c_uint32), ('process', c.c_uint32),
                        ('priority', c.c_int32), ('delta', c.c_int32),
                        ('flags', c.c_uint32)]
        self._FileTime, self._ThreadEntry = FileTime, ThreadEntry
        if c.sizeof(FileTime) != 8 or c.sizeof(ThreadEntry) != 28:
            raise ThreadApiError('PLATFORM')
        dll = c.WinDLL('kernel32.dll', use_last_error=True, winmode=0x0800)
        h, d, b, p = c.c_void_p, c.c_uint32, c.c_int32, c.c_void_p
        self._pid = dll.GetProcessId
        self._pid.argtypes, self._pid.restype = [h], d
        self._process_times = dll.GetProcessTimes
        self._process_times.argtypes, self._process_times.restype = [h, p, p, p, p], b
        self._snapshot = dll.CreateToolhelp32Snapshot
        self._snapshot.argtypes, self._snapshot.restype = [d, d], h
        self._first, self._next = dll.Thread32First, dll.Thread32Next
        for function in (self._first, self._next):
            function.argtypes, function.restype = [h, p], b
        self._open = dll.OpenThread
        self._open.argtypes, self._open.restype = [d, b, d], h
        self._tid, self._thread_pid = dll.GetThreadId, dll.GetProcessIdOfThread
        for function in (self._tid, self._thread_pid):
            function.argtypes, function.restype = [h], d
        self._thread_times = dll.GetThreadTimes
        self._thread_times.argtypes, self._thread_times.restype = [h, p, p, p, p], b
        self._resume = dll.ResumeThread
        self._resume.argtypes, self._resume.restype = [h], d
        self._close = dll.CloseHandle
        self._close.argtypes, self._close.restype = [h], b

    def _creation(self, function, handle, code):
        times = [self._FileTime() for _ in range(4)]
        if not function(handle, *(self._c.byref(value) for value in times)):
            raise ThreadApiError(code)
        return times[0].low | times[0].high << 32

    def process_identity(self, handle):
        pid = self._pid(handle)
        if not pid:
            raise ThreadApiError('PROCESS_QUERY')
        return pid, self._creation(self._process_times, handle, 'PROCESS_QUERY')

    def snapshot(self):
        handle = self._snapshot(4, 0)  # TH32CS_SNAPTHREAD, no inheritance/modules
        if handle is None or handle in (0, (1 << 64)-1):
            raise ThreadApiError('SNAPSHOT_CREATE')
        return handle

    def _entry(self, function, snapshot):
        entry = self._ThreadEntry()
        entry.size = self._c.sizeof(entry)  # Reset for EVERY First/Next call.
        if not function(snapshot, self._c.byref(entry)):
            if self._c.get_last_error() == 18:  # ERROR_NO_MORE_FILES only
                return None
            raise ThreadApiError('SNAPSHOT_ENUM')
        if not 16 <= entry.size <= self._c.sizeof(entry):
            raise ThreadApiError('SNAPSHOT_ENTRY')
        return entry.thread, entry.process

    def first(self, snapshot):
        return self._entry(self._first, snapshot)

    def next(self, snapshot):
        return self._entry(self._next, snapshot)

    def open_thread(self, tid):
        handle = self._open(0x0042, False, tid)
        if not handle:
            raise ThreadApiError('THREAD_OPEN')
        return handle

    def thread_identity(self, handle):
        tid, pid = self._tid(handle), self._thread_pid(handle)
        if not tid or not pid:
            raise ThreadApiError('THREAD_QUERY')
        return tid, pid, self._creation(self._thread_times, handle, 'THREAD_QUERY')

    def resume(self, thread):
        previous = self._resume(thread)
        if previous == 0xFFFFFFFF:
            raise ThreadApiError('RESUME_API')
        return previous

    def close(self, handle):
        if not self._close(handle):
            raise ThreadApiError('HANDLE_CLOSE')


def _uint(value, maximum):
    return type(value) is int and 0 < value <= maximum


def _process_fields(process):
    # subprocess.Handle is an int subclass; exclude bool explicitly.
    handle, pid = process._handle, process.pid
    if (not isinstance(handle, int) or isinstance(handle, bool) or
            not 0 < int(handle) < (1 << 64)-1 or not _uint(pid, 0xFFFFFFFF)):
        raise ThreadApiError('INPUT')
    if process.poll() is not None:
        raise ThreadApiError('PROCESS_EXITED')
    return int(handle), pid


def _process_identity(api, handle, expected_pid):
    identity = api.process_identity(handle)
    if (type(identity) is not tuple or len(identity) != 2 or identity[0] != expected_pid
            or not _uint(identity[0], 0xFFFFFFFF) or not _uint(identity[1], (1 << 64)-1)):
        raise ThreadApiError('PROCESS_IDENTITY')
    return identity


def _thread_identity(api, handle, tid, pid, process_start):
    identity = api.thread_identity(handle)
    if (type(identity) is not tuple or len(identity) != 3
            or identity[:2] != (tid, pid) or not _uint(identity[0], 0xFFFFFFFF)
            or not _uint(identity[1], 0xFFFFFFFF) or not _uint(identity[2], (1 << 64)-1)
            or identity[2] < process_start):
        raise ThreadApiError('THREAD_IDENTITY')
    return identity


def resume_primary(process, *, api=None):
    """Return fixed evidence; ordinary refusals never export native error text.

    The caller must use its exact, fresh, already job-assigned CREATE_SUSPENDED
    Popen once. The helper borrows and never closes that process handle. All
    opened thread/snapshot handles are closed independently on every exit. A
    failed CloseHandle can leave a handle; cleanup_verified remains false.
    Even if cleanup later refuses, resume_observed records a prior count of one.
    """
    result = {'schema': SCHEMA, **{name: False for name in TRUE_FIELDS},
              'snapshot_passes': 0, 'snapshot_entries_examined': 0,
              'secondary_close_failures': 0, 'failure': 'NONE'}
    owned = []
    interrupted = None

    def close(item):
        try:
            api.close(item[1])
        except BaseException:
            result['secondary_close_failures'] += 1
            raise
        owned.remove(item)

    def scan(pid):
        snapshot = api.snapshot()
        item = ('snapshot', snapshot)
        owned.append(item)
        found, count = None, 0
        entry = api.first(snapshot)
        while entry is not None:
            if count == MAX_THREAD_ENTRIES:
                raise ThreadApiError('SNAPSHOT_LIMIT')
            count += 1
            result['snapshot_entries_examined'] += 1
            if (type(entry) is not tuple or len(entry) != 2
                    or any(type(value) is not int or not 0 <= value <= 0xFFFFFFFF for value in entry)):
                raise ThreadApiError('SNAPSHOT_ENTRY')
            if entry[1] == pid:
                if found is not None or not entry[0]:
                    raise ThreadApiError('SINGLE_THREAD')
                found = entry[0]
            entry = api.next(snapshot)
        if found is None:
            raise ThreadApiError('SINGLE_THREAD')
        # A close refusal aborts before ResumeThread; final cleanup retries it.
        close(item)
        result['snapshot_passes'] += 1
        return found

    try:
        handle, pid = _process_fields(process)
        if api is None:
            api = NativeThreadApi()
        process_identity = _process_identity(api, handle, pid)
        result['process_identity_verified'] = True
        tid = scan(pid)
        thread = api.open_thread(tid)
        owned.append(('thread', thread))
        thread_identity = _thread_identity(api, thread, tid, pid, process_identity[1])
        result['thread_identity_verified'] = True
        if scan(pid) != tid:
            raise ThreadApiError('GENERATION_CHANGED')
        result['single_owned_thread_verified'] = True
        if (_process_fields(process) != (handle, pid)
                or _process_identity(api, handle, pid) != process_identity
                or _thread_identity(api, thread, tid, pid, process_identity[1]) != thread_identity):
            raise ThreadApiError('GENERATION_CHANGED')
        if _process_fields(process) != (handle, pid):
            raise ThreadApiError('GENERATION_CHANGED')
        result['generation_recheck_verified'] = True
        result['resume_attempted'] = True
        previous = api.resume(thread)
        if type(previous) is not int or previous != 1:
            raise ThreadApiError('RESUME_COUNT')
        result['previous_suspend_count_one'] = result['resume_observed'] = True
    except BaseException as error:
        code = str(error) if type(error) is ThreadApiError else None
        result['failure'] = code if code in _FAILURES else 'API_FAILED'
        if not isinstance(error, Exception):
            interrupted = error
    finally:
        for item in tuple(reversed(owned)):
            try:
                close(item)
            except BaseException as error:
                if result['failure'] == 'NONE':
                    result['failure'] = 'HANDLE_CLOSE'
                if not isinstance(error, Exception) and interrupted is None:
                    interrupted = error
        result['snapshots_closed'] = not any(kind == 'snapshot' for kind, _ in owned)
        result['thread_handle_closed'] = not any(kind == 'thread' for kind, _ in owned)
        result['cleanup_verified'] = not owned
    if interrupted is not None:
        raise interrupted
    result['passed'] = result['failure'] == 'NONE' and result['cleanup_verified'] is True
    return result
