"""Finite CI pool custody; no native, runtime-cache or player-data authority.

Content/schema/source and held-child cleanup remain the qualifier's gates. This
helper adds a complete namespace boundary and transfers only its captured native
error log after that caller has proved every writer stopped.
"""
from __future__ import annotations
import ctypes
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

MAX_FILES = 250000
MAX_DIRS = 16384
MAX_CACHES = 4096
MAX_LOG_BYTES = 8 * 1024 * 1024
ERROR_LOG = 'logs/mapserver/error.log'
CONFIG = 'data/server/db/servers.cfg'


def require(ok, message):
    if not ok:
        raise ValueError(message)


class Budget:
    def __init__(self, seconds=7200):
        require(type(seconds) in (int, float) and 0 < seconds <= 7200,
                'Finite CI pool budget required')
        self.started = time.monotonic()
        self.deadline = self.started + seconds

    def check(self, phase):
        require(time.monotonic() < self.deadline,
                'CI pool budget exhausted during ' + str(phase))

    def remaining(self):
        return max(0.0, self.deadline - time.monotonic())


class PhaseTimer:
    def __init__(self, budget, phase, records):
        self.budget, self.phase, self.records = budget, phase, records

    def __enter__(self):
        if self.budget is not None:
            self.budget.check(self.phase)
        self.started = time.monotonic()
        return self

    def __exit__(self, kind, value, traceback):
        self.records.append({'phase': self.phase,
            'elapsed_seconds': round(time.monotonic() - self.started, 6),
            'status': 'failed' if kind is not None else 'completed',
            'scope': 'host_qualification_not_native_or_device_loading'})
        if kind is None and self.budget is not None:
            self.budget.check(self.phase)
        return False


def safe_name(name):
    require(type(name) is str and 0 < len(name) < 240 and '\\' not in name
            and not name.startswith('/'), 'Safe relative pool member required')
    parts = name.split('/')
    require(all(p not in ('', '.', '..') and not any(c in p for c in ':*?<>|"\x00')
                and not p.endswith((' ', '.')) for p in parts),
            'Ambiguous pool member refused')
    return parts


def record(info):
    return {'device': info.st_dev, 'inode': info.st_ino, 'uid': info.st_uid,
            'mode': info.st_mode, 'links': info.st_nlink, 'bytes': info.st_size,
            'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns,
            'attributes': getattr(info, 'st_file_attributes', 0)}


def ordinary(info, directory=False):
    require(not getattr(info, 'st_file_attributes', 0) & 0x400,
            'Pool reparse point refused')
    require((stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)),
            'Pool directory or ordinary file required')
    if not directory:
        require(info.st_nlink == 1, 'Pool file hardlink refused')


def ordinary_streams(path):
    """Windows names do not enumerate alternate streams; reject them explicitly."""
    if os.name != 'nt':
        return
    from ctypes import wintypes
    class StreamData(ctypes.Structure):
        _fields_ = [('size', ctypes.c_longlong), ('name', ctypes.c_wchar * 296)]
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    first, next_stream, close = api.FindFirstStreamW, api.FindNextStreamW, api.FindClose
    first.argtypes = [wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(StreamData), wintypes.DWORD]
    first.restype = wintypes.HANDLE
    next_stream.argtypes = [wintypes.HANDLE, ctypes.POINTER(StreamData)]
    next_stream.restype = wintypes.BOOL
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    data = StreamData()
    handle = first(str(path), 0, ctypes.byref(data), 0)
    if handle == ctypes.c_void_p(-1).value:
        require(ctypes.get_last_error() == 38, 'Pool stream enumeration failed')
        return
    try:
        require(data.name == '::$DATA', 'Pool alternate stream refused')
        require(not next_stream(handle, ctypes.byref(data))
                and ctypes.get_last_error() == 38, 'Pool alternate stream or enumeration failure')
    finally:
        require(close(handle), 'Pool stream handle cleanup failed')


def directory_identity(info):
    return {k: record(info)[k] for k in ('device', 'inode', 'uid', 'mode', 'attributes')}


@contextmanager
def directory_custody(path):
    """Hold every nonlinked ancestor; Windows handles deny rename/delete.

    The CI caller supplies exclusive writer custody. POSIX descriptors bind the
    checked objects and detect namespace replacements; they are not a global
    filesystem mutation lease.
    """
    path = Path(path).absolute()
    require('..' not in path.parts, 'Ambiguous directory ancestor refused')
    require(os.path.normcase(str(path.resolve(strict=True))) == os.path.normcase(str(path)),
            'Linked directory ancestor refused')
    identities, handles = [], []
    close = os.close
    if os.name == 'nt':
        from ctypes import wintypes
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        create = api.CreateFileW
        create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
            ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        create.restype = wintypes.HANDLE
        close = api.CloseHandle
        close.argtypes, close.restype = [wintypes.HANDLE], wintypes.BOOL
    try:
        for ancestor in [*reversed(path.parents), path]:
            before = ancestor.lstat()
            ordinary(before, directory=True)
            ordinary_streams(ancestor)
            identity = directory_identity(before)
            if os.name == 'nt':
                # Share read/write only: replacement/rename requires delete
                # sharing and stays denied until this entire chain is released.
                handle = create(str(ancestor), 0x80, 3, None, 3, 0x02200000, None)
                require(handle != ctypes.c_void_p(-1).value, 'Directory custody handle open failed')
            else:
                handle = os.open(ancestor, os.O_RDONLY | os.O_DIRECTORY | getattr(os, 'O_NOFOLLOW', 0))
            handles.append(handle)
            require(directory_identity(ancestor.lstat()) == identity, 'Directory ancestor changed during custody')
            if os.name != 'nt':
                require(directory_identity(os.fstat(handle)) == identity, 'Held directory identity differs')
            identities.append((ancestor, identity))
        yield path
        for ancestor, identity in identities:
            require(directory_identity(ancestor.lstat()) == identity, 'Held directory ancestor changed')
    finally:
        errors = []
        for handle in reversed(handles):
            try:
                result = close(handle)
                if os.name == 'nt':
                    require(result, 'Directory custody handle close failed')
            except BaseException as error:
                errors.append(error)
        require(not errors, 'Directory custody handle cleanup failed: ' + repr(errors))


def names(values, maximum):
    require(type(values) in (dict, set, list, tuple) and len(values) <= maximum,
            'Bounded exact pool inventory required')
    result = set()
    folded = set()
    for name in values:
        safe_name(name)
        require(name.casefold() not in folded, 'Pool member case alias refused')
        result.add(name)
        folded.add(name.casefold())
    return result


def pin_log(path, expected=None, budget=None):
    before = path.lstat()
    ordinary(before)
    require(before.st_size <= MAX_LOG_BYTES, 'Native error log exceeds bounded custody')
    if expected is not None:
        require(record(before) == expected, 'Captured native error log changed')
    ordinary_streams(path)
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    descriptor = os.open(path, flags)
    try:
        require(record(os.fstat(descriptor)) == record(before), 'Native error log identity changed')
        sha = hashlib.sha256()
        size = 0
        while True:
            if budget is not None:
                budget.check('owned error-log hashing')
            chunk = os.read(descriptor, 65536)
            if not chunk:
                break
            size += len(chunk)
            require(size <= MAX_LOG_BYTES, 'Native error log grew beyond custody bound')
            sha.update(chunk)
        require(record(os.fstat(descriptor)) == record(before), 'Native error log changed while hashing')
    finally:
        os.close(descriptor)
    require(size == before.st_size and record(path.lstat()) == record(before),
            'Native error log name/content metadata changed')
    return {'bytes': size, 'sha256': sha.hexdigest(), 'identity': record(before),
            'mtime_ns': before.st_mtime_ns // 100 * 100}


def _closed_namespace(runtime, expected_provider_names, cache_names, budget=None):
    runtime = Path(runtime)
    provider = names(expected_provider_names, MAX_FILES)
    caches = names(cache_names, MAX_CACHES)
    for name in caches:
        require((name.startswith(('data/bin/', 'data/server/bin/')) and name.endswith('.bin'))
                or (name.startswith(('data/geobin/object_library/', 'data/geobin/maps/'))
                    and name.endswith('.bin'))
                or (name.startswith('data/geobin/object_library/') and name.endswith('.bounds')),
                'Pool cache path escapes exact native roots')
    required = provider | caches | {'MapServer.exe', CONFIG}
    require(len({n.casefold() for n in required}) == len(required), 'Pool case alias across classes')
    allowed = required | {ERROR_LOG}
    allowed_dirs = {'logs', 'logs/mapserver'}
    for name in allowed:
        parts = safe_name(name)
        allowed_dirs.update('/'.join(parts[:i]) for i in range(1, len(parts)))
    require(len(allowed_dirs) <= MAX_DIRS, 'Pool directory inventory exceeds bound')
    root_info = runtime.lstat()
    ordinary(root_info, directory=True)
    ordinary_streams(runtime)
    files, directories = {}, {}
    seen_folded = set()
    def walk(directory, relative=''):
        if budget is not None:
            budget.check('complete pool namespace')
        before = directory.lstat()
        ordinary(before, directory=True)
        require(before.st_uid == root_info.st_uid, 'Pool directory owner differs')
        ordinary_streams(directory)
        with os.scandir(directory) as entries:
            for entry in entries:
                if budget is not None:
                    budget.check('complete pool namespace')
                name = relative + '/' + entry.name if relative else entry.name
                safe_name(name)
                require(name.casefold() not in seen_folded, 'Pool namespace case alias refused')
                seen_folded.add(name.casefold())
                info = entry.stat(follow_symlinks=False)
                path = directory / entry.name
                require(info.st_uid == root_info.st_uid, 'Pool member owner differs')
                if stat.S_ISDIR(info.st_mode):
                    ordinary(info, directory=True)
                    require(name in allowed_dirs, 'Unknown pool directory: ' + name)
                    require(len(directories) < MAX_DIRS, 'Pool directory bound exceeded')
                    directories[name] = record(info)
                    walk(path, name)
                else:
                    ordinary(info)
                    require(name in allowed, 'Unknown pool file: ' + name)
                    require(len(files) < MAX_FILES, 'Pool file bound exceeded')
                    ordinary_streams(path)
                    files[name] = record(info)
                    require(record(path.lstat()) == files[name], 'Pool file changed during enumeration')
        require(record(directory.lstat()) == record(before), 'Pool directory changed during enumeration')
    walk(runtime)
    require(required <= files.keys(), 'Missing exact pool member')
    require(record(runtime.lstat()) == record(root_info), 'Pool root changed during enumeration')
    log = pin_log(runtime / ERROR_LOG, files[ERROR_LOG], budget) if ERROR_LOG in files else None
    payload = {'files': files, 'directories': directories}
    return {'format': 'closed-native-map-world-pool-namespace-v1',
            'runtime': str(runtime.absolute()), 'root_identity': record(root_info),
            **payload, 'namespace_sha256': hashlib.sha256(json.dumps(payload, sort_keys=True,
                separators=(',', ':')).encode()).hexdigest(), 'owned_error_log': log,
            'full_namespace_verified': True, 'content_schema_native_SQL_gates_supplied': False,
            'unknown_leaf_deletion_allowed': False, 'shipping_allowed': False}


def _quarantine_owned_error_log(runtime, private_archive, case_label, namespace_receipt, *, stopped=False):
    require(stopped is True, 'Held native writers/observers must have verified cleanup')
    require(type(case_label) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,96}', case_label),
            'Exact native case identity required')
    runtime, archive = Path(runtime), Path(private_archive)
    require(type(namespace_receipt) is dict
            and namespace_receipt.get('format') == 'closed-native-map-world-pool-namespace-v1'
            and namespace_receipt.get('full_namespace_verified') is True
            and namespace_receipt.get('runtime') == str(runtime.absolute())
            and record(runtime.lstat()) == namespace_receipt.get('root_identity'),
            'Current closed pool namespace required')
    for parent in ('logs', 'logs/mapserver'):
        expected_parent = namespace_receipt['directories'].get(parent)
        if expected_parent is not None:
            current_parent = (runtime / parent).lstat()
            ordinary(current_parent, directory=True)
            require(record(current_parent) == expected_parent, 'Captured native log parent changed')
    expected = namespace_receipt.get('owned_error_log')
    source = runtime / ERROR_LOG
    if expected is None:
        require(not source.exists() and not source.is_symlink(), 'Uncaptured native log appeared')
        return {'status': 'no_current_native_error_log', 'case': case_label}
    require(pin_log(source, expected['identity']) == expected, 'Captured native log pin differs')
    require(archive.is_dir() and not archive.is_symlink(), 'Existing private case archive required')
    archive_info = archive.lstat()
    ordinary(archive_info, directory=True)
    ordinary_streams(archive)
    require(archive_info.st_uid == namespace_receipt['root_identity']['uid'],
            'Private case archive owner differs')
    require(runtime.absolute() not in archive.absolute().parents and archive.absolute() != runtime.absolute(),
            'Native log archive must be outside reusable provider')
    target = archive / (case_label + '-native-error.log')
    require(not target.exists() and not target.is_symlink(), 'Fresh native-log archive path required')
    # Hard-link reservation atomically refuses collisions, preserves captured
    # bytes/date, and never replaces a destination. Remove only this proven
    # source name after checking the exact newly reserved object.
    os.link(source, target, follow_symlinks=False)
    transferred = False
    try:
        linked = source.lstat()
        target_info = target.lstat()
        require(linked.st_nlink == 2 and target_info.st_nlink == 2
                and linked.st_dev == target_info.st_dev and linked.st_ino == target_info.st_ino
                and linked.st_dev == expected['identity']['device']
                and linked.st_ino == expected['identity']['inode']
                and linked.st_size == expected['bytes']
                and linked.st_mtime_ns == expected['identity']['mtime_ns'],
                'Captured native log changed during exclusive transfer')
        os.unlink(source)
        transferred = True
        require(not source.exists() and not source.is_symlink(), 'Native log source path remains')
        after = pin_log(target)
        require({k: after[k] for k in ('bytes', 'sha256', 'mtime_ns')}
                == {k: expected[k] for k in ('bytes', 'sha256', 'mtime_ns')},
                'Transferred native log content/date differs')
        return {'status': 'owned_stopped_native_error_log_transferred', 'case': case_label,
            'source': ERROR_LOG, 'archive': str(target), 'captured': expected, 'transferred': after,
            'source_absent': True, 'unknown_files_removed': False}
    except BaseException:
        # Before source removal, release only the exact reservation we created.
        # After removal, retain the archived bytes even if a later gate fails.
        if not transferred:
            current = target.lstat()
            if (current.st_dev, current.st_ino) == (expected['identity']['device'], expected['identity']['inode']):
                os.unlink(target)
        raise


def closed_namespace(runtime, expected_provider_names, cache_names, budget=None):
    with directory_custody(runtime) as held_runtime:
        return _closed_namespace(held_runtime, expected_provider_names, cache_names, budget)


def quarantine_owned_error_log(runtime, private_archive, case_label, namespace_receipt, *, stopped=False):
    with directory_custody(runtime) as held_runtime, directory_custody(private_archive) as held_archive:
        require(os.path.commonpath([str(held_runtime), str(held_archive)]) != str(held_runtime),
                'Native log archive must be outside reusable provider')
        # Resolve only after every path component is held and nonlinked.
        require(held_archive.resolve(strict=True) != held_runtime.resolve(strict=True)
                and held_runtime.resolve(strict=True) not in held_archive.resolve(strict=True).parents,
                'Native log archive resolves inside reusable provider')
        return _quarantine_owned_error_log(held_runtime, held_archive, case_label, namespace_receipt, stopped=stopped)
