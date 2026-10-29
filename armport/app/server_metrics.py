"""Bounded, observational server/owned-process samples for ARM64 Thor exports.

No readiness decisions, subprocesses, environment/command-line export, or new
threads. Linux CPU counters are not Wine request counts. Map tick counters come
from the retained native progress publisher; they cannot reveal the longest
individual tick or time inside file loads. Opt-in 0119 console windows supply
separate post-ready main-thread durations, with their narrower scope retained.
"""
import copy
import json
import os
from pathlib import Path
import re
import stat
import time

SCHEMA = 'ARMPORT_SERVER_METRICS_V1'
INTERVAL = 5.0
BUDGET = .05
PROCESS_LIMIT = 32
PROC_SCAN_LIMIT = 8192
THREAD_LIMIT = 128
THREAD_TOTAL_LIMIT = 256
THREAD_EXPORT_LIMIT = 6
MAP_LIMIT = 8
SAMPLE_LIMIT = 2048
EXPORT_BYTES = 4 * 1024 * 1024
READ_BYTES = 8192
NATIVE_BUDGET = .005
NATIVE_BYTES_PER_MAP = 8192
NATIVE_TOTAL_BYTES = 32768
NATIVE_LINE_BYTES = 480
NATIVE_LINES = 256
NATIVE_WINDOWS = 8
NATIVE_STALE_SECONDS = 15
NATIVE_SCOPE = 'post_ready_main_thread_outer_filealloc'
NATIVE_PREFIX = b'ARMPORT_SERVER_METRICS_V1 '
_UINT = rb'([0-9]{1,20})'
_MS = rb'([0-9]{1,24}\.[0-9]{3})'
_NATIVE_OK = re.compile(NATIVE_PREFIX + rb'status=ok map_id=' + _UINT + rb' pid=' + _UINT
    + rb' seconds=([0-9]{1,24}\.[0-9]{6}) ticks=' + _UINT + rb' max_tick_ms=' + _MS
    + rb' max_loop_ms=' + _MS + rb' filealloc_ms=' + _MS + rb' filealloc_calls=' + _UINT
    + rb' filealloc_failures=' + _UINT + rb' counter_saturated=([01]) scope=' + NATIVE_SCOPE.encode())
_NATIVE_ERROR = re.compile(NATIVE_PREFIX + rb'status=clock_error map_id=' + _UINT + rb' pid=' + _UINT)


def parse_native_window(line, map_id, windows_pid):
    """Parse the actual 0119 record, never raw text or arbitrary key/value fields.

    pid is the native Windows PID, not the Linux launcher PID. None means an
    unrelated console line; malformed/foreign records cannot become zeros.
    """
    if NATIVE_PREFIX not in line:
        return None
    if len(line) >= NATIVE_LINE_BYTES:
        raise ValueError('native metrics line exceeds bound')
    line = line.removesuffix(b'\r')
    match = _NATIVE_OK.fullmatch(line)
    error = _NATIVE_ERROR.fullmatch(line) if match is None else None
    if match is None and error is None:
        raise ValueError('native metrics format differs')
    fields = (match or error).groups()
    identity = tuple(int(value) for value in fields[:2])
    if not (0 < identity[0] <= 0x7fffffff and 0 < identity[1] <= 0xffffffff):
        raise ValueError('invalid native metrics identity')
    if identity != (map_id, windows_pid):
        raise LookupError('native metrics generation identity differs')
    if error is not None:
        return {'status': 'clock_error', 'map_id': map_id, 'windows_pid': windows_pid}
    seconds, ticks, tick_ms, loop_ms, file_ms, calls, failures, saturated = fields[2:]
    seconds, tick_ms, loop_ms, file_ms = map(float, (seconds, tick_ms, loop_ms, file_ms))
    ticks, calls, failures = map(int, (ticks, calls, failures))
    if (seconds < 5 or not 0 < ticks <= 0xffffffffffffffff
            or not 0 <= failures <= calls <= 0xffffffffffffffff
            or tick_ms > loop_ms + .002 or loop_ms > seconds * 1000 + .002
            or file_ms > seconds * 1000 + .002):
        raise ValueError('native metrics counters or durations differ')
    return {'status': 'ok', 'map_id': map_id, 'windows_pid': windows_pid,
        'seconds': seconds, 'ticks': ticks, 'max_tick_ms': tick_ms, 'max_loop_ms': loop_ms,
        'filealloc_ms': file_ms, 'filealloc_calls': calls, 'filealloc_failures': failures,
        'counter_saturated': saturated == b'1', 'scope': NATIVE_SCOPE}


class NativeConsoleTail:
    """Independent bounded offsets for one already-owned map console generation."""
    def __init__(self, binding, output):
        self.binding, self.output = binding, output
        self.offset, self.pending, self.discarding = 0, b'', False
        self.last_record_at = self.caught_up_at = None
        self.clock_error = False

    def sample(self, map_id, windows_pid, now, clock, deadline, maximum):
        result = {'available': False, 'is_success_proof': False, 'status': 'missing',
            'windows': [], 'bytes_scanned': 0, 'bytes_copied': 0, 'bytes_skipped': 0, 'lines_scanned': 0,
            'malformed_records': 0, 'identity_mismatches': 0, 'windows_omitted': 0,
            'partial_line_bytes': len(self.pending), 'complete': True,
            'scope': NATIVE_SCOPE, 'window_end_time_unknown': True,
            'freshness_basis': 'console_observation_not_native_emission_timestamp'}
        size = len(self.output)
        if size < self.offset:
            raise ValueError('owned native metrics console shrank')
        if clock() >= deadline or maximum <= 0:
            result.update(status='partial', complete=False, reason='sample_budget_exhausted')
            return result
        maximum = min(maximum, NATIVE_BYTES_PER_MAP)
        # Prefer current windows to an unbounded scan of startup logging. Drop
        # the first fragment after a skip, never parse a substring as a record.
        if size - self.offset > maximum:
            result['bytes_skipped'] = size - self.offset - maximum
            self.offset = size - maximum
            self.pending, self.discarding, self.caught_up_at = b'', True, None
            result['complete'] = False
        start, end = self.offset, min(size, self.offset + maximum)
        chunk = bytes(self.output[start:end])
        result['bytes_copied'] = len(chunk)
        position = 0
        while position < len(chunk):
            if result['lines_scanned'] >= NATIVE_LINES or clock() >= deadline:
                result['complete'] = False
                break
            newline = chunk.find(b'\n', position)
            finish = newline + 1 if newline >= 0 else len(chunk)
            fragment = chunk[position:newline if newline >= 0 else finish]
            position = finish
            if self.discarding:
                if newline >= 0:
                    self.discarding = False
            elif len(self.pending) + len(fragment) >= NATIVE_LINE_BYTES:
                if NATIVE_PREFIX in self.pending + fragment[:NATIVE_LINE_BYTES]:
                    result['malformed_records'] += 1
                self.pending = b''
                self.discarding = newline < 0
                result['complete'] = False
            else:
                self.pending += fragment
                if newline >= 0:
                    try:
                        value = parse_native_window(self.pending, map_id, windows_pid)
                        if value is not None:
                            value['console_end_offset'] = start + finish
                            # This only bounds when bytes reached our captured
                            # console; pipe/reader buffering can predate it.
                            value['since_previous_caught_up_sample_seconds'] = (
                                None if self.caught_up_at is None else round(max(0, now - self.caught_up_at), 6))
                            if value['status'] == 'clock_error':
                                self.clock_error = True
                            elif self.clock_error:
                                result['malformed_records'] += 1
                            else:
                                self.last_record_at = now
                                result['windows'].append(value)
                                if len(result['windows']) > NATIVE_WINDOWS:
                                    del result['windows'][0]
                                    result['windows_omitted'] += 1
                                    result['complete'] = False
                    except LookupError:
                        result['identity_mismatches'] += 1
                    except ValueError:
                        result['malformed_records'] += 1
                    self.pending = b''
            if newline >= 0:
                result['lines_scanned'] += 1
        self.offset = start + position
        result.update(bytes_scanned=position, partial_line_bytes=len(self.pending),
            discarding_oversized_or_skipped_line=self.discarding,
            unscanned_bytes=size - self.offset, available=bool(result['windows']))
        if self.offset == size and not self.pending and not self.discarding:
            self.caught_up_at = now
        else:
            result['complete'] = False
        result['seconds_since_last_record_observed'] = (
            None if self.last_record_at is None else round(max(0, now - self.last_record_at), 6))
        result['last_record_stale'] = (self.last_record_at is not None
                                       and now - self.last_record_at >= NATIVE_STALE_SECONDS)
        if self.clock_error:
            result['status'] = 'clock_error'
        elif result['malformed_records'] or result['identity_mismatches']:
            result.update(status='malformed', complete=False)
        elif not result['complete'] or any(row['counter_saturated'] for row in result['windows']):
            result.update(status='partial', complete=False)
        elif result['windows']:
            result['status'] = 'measured'
        elif self.last_record_at is not None:
            result['status'] = 'stale' if result['last_record_stale'] else 'no_new_record'
        return result


def bounded_read(path):
    with path.open('rb') as source:
        value = source.read(READ_BYTES + 1)
    if len(value) > READ_BYTES:
        raise ValueError('proc record exceeds bound')
    return value


def parse_stat(raw):
    """Linux /proc stat: comm can contain spaces and closing parentheses."""
    text = raw.decode('utf-8', 'replace') if isinstance(raw, bytes) else raw
    if len(text) > READ_BYTES:
        raise ValueError('proc stat exceeds bound')
    pid, rest = text.split(' (', 1)
    _, fields = rest.rsplit(') ', 1)
    fields = fields.split()
    value = {'proc_pid': int(pid), 'starttime': int(fields[19]),
             'user_ticks': int(fields[11]), 'system_ticks': int(fields[12]),
             'threads': int(fields[17])}
    if value['proc_pid'] <= 0 or any(number < 0 for number in value.values()):
        raise ValueError('invalid proc counters')
    return value


def process_role(raw):
    """Export an allowlisted role and map number only, never executable args."""
    parts = raw.lower().split(b'\0')
    basenames = [part.replace(b'\\', b'/').rsplit(b'/', 1)[-1] for part in parts]
    role = next((role for name, role in (('mapserver.exe', 'mapserver'),
                ('dbserver.exe', 'dbserver'), ('cityofheroes.exe', 'client'),
                ('wineserver', 'wineserver')) if name.encode() in basenames), 'other')
    map_id = None
    if role == 'mapserver' and b'-map_id' in parts:
        index = parts.index(b'-map_id') + 1
        if index < len(parts) and parts[index].isdigit() and len(parts[index]) <= 10:
            candidate = int(parts[index])
            if 0 < candidate <= 0xffffffff:
                map_id = candidate
    return role, map_id


def delta(current, previous, identities, counters):
    """Never convert resets, PID reuse, or backwards clocks into huge rates."""
    if previous is None:
        return {'delta_status': 'initial', 'window_seconds': None}
    if any(current[key] != previous[key] for key in identities):
        return {'delta_status': 'identity_changed', 'window_seconds': None}
    elapsed = current['observed_monotonic'] - previous['observed_monotonic']
    if round(elapsed, 6) <= 0:
        return {'delta_status': 'nonadvancing_clock', 'window_seconds': None}
    if any(current[key] < previous[key] for key in counters):
        return {'delta_status': 'counter_regressed', 'window_seconds': None}
    return {'delta_status': 'measured', 'window_seconds': round(elapsed, 6),
            **{key + '_delta': current[key] - previous[key] for key in counters}}


def cpu_delta(current, previous, hz):
    if not isinstance(hz, int) or hz <= 0:
        raise ValueError('invalid clock tick frequency')
    result = delta(current, previous, ('proc_pid', 'starttime'), ('user_ticks', 'system_ticks'))
    result.update(cpu_user_ms=None, cpu_system_ms=None, cpu_percent_one_core=None)
    if result['delta_status'] == 'measured':
        user = result.pop('user_ticks_delta') * 1000 / hz
        system = result.pop('system_ticks_delta') * 1000 / hz
        result.update(cpu_user_ms=round(user, 3), cpu_system_ms=round(system, 3),
                      cpu_percent_one_core=round((user + system) / (result['window_seconds'] * 10), 3))
    return result


def map_delta(current, previous):
    result = delta(current, previous, ('windows_pid', 'main_thread_id', 'file_identity'),
                   ('tick_completed', 'sequence'))
    result['ticks_per_second'] = None
    if result['delta_status'] == 'measured':
        result['ticks_per_second'] = round(result['tick_completed_delta'] / result['window_seconds'], 3)
    return result


def detached_owner(owner):
    """Give ownership reads private scratch state, without copying history.

    Inspection creates new receipt observations and can invalidate cached
    lineage. It does not need old diagnostic lists or the cleanup census sets.
    Only the exact group being inspected receives a bounded lineage snapshot.
    """
    observer = copy.copy(owner)
    observer.receipt = {name: [] if isinstance(value, list) else {} if isinstance(value, dict) else value
                        for name, value in owner.receipt.items()}
    observer.dead_leaders, observer.owned_workers = set(), set()
    if hasattr(owner, 'live_lineage'):
        observer.live_lineage = dict(owner.live_lineage, groups={})
        # This optional stronger proof exists for future cleanup. A telemetry
        # reader must neither collect it into cleanup's registry nor spend its
        # short sampling budget rebuilding the worker history.
        observer.remember_readable_workers = lambda *args, **kwargs: None
    if not observer.initialized:
        observer.initialize()
    return observer


class ServerMetrics:
    def __init__(self, diagnostic, *, clock=time.monotonic, wall=time.time):
        self.diagnostic, self.clock, self.wall = diagnostic, clock, wall
        self.next_sample = 0
        self.known_cursor = 0
        self._proc_entries = self._proc_root = None
        self._discovery_retry = None
        self._lineage_entries = self._lineage_groups = None
        self.stopped = False
        self.process_previous, self.thread_previous, self.map_previous = {}, {}, {}
        self.native_context, self.native_tails = {}, {}
        self.native_cursor = 0
        self.hz = int(os.sysconf('SC_CLK_TCK'))
        self.path = Path(diagnostic.capture_dir) / 'server-metrics.jsonl'
        self.summary = {'schema': SCHEMA, 'format': 1, 'is_success_proof': False,
            'file': self.path.name, 'interval_seconds': INTERVAL, 'budget_seconds': BUDGET,
            'samples_written': 0, 'samples_omitted': 0, 'errors': 0, 'last_error_type': None,
            'export_bytes': 0, 'export_limit_bytes': EXPORT_BYTES, 'sample_limit': SAMPLE_LIMIT,
            'cpu_clock_ticks_per_second': self.hz,
            'sampling': 'cooperative_health_callback_not_a_realtime_schedule',
            'longest_tick_ms': {'available': False, 'reason': 'no_native_window_observed'},
            'file_load_ms': {'available': False, 'reason': 'no_native_window_observed'},
            'native_duration_windows_observed': 0,
            'native_duration_scope': {'max_tick_ms': 'post_ready_main_thread_work_excludes_sleep',
                'max_loop_ms': 'post_ready_main_thread_work_and_sleep_excludes_metrics_logging',
                'filealloc_ms': 'inclusive_outer_fileAlloc_and_fileAllocEx_attempts_during_tick_work',
                'filealloc_excludes': ['startup', 'background_threads', 'other_file_IO'],
                'filealloc_is_disk_only_time': False, 'windows_align_with_host_samples': False},
            'wineserver_requests': {'available': False, 'reason': 'request_counter_producer_not_wired'}}
        diagnostic.ctx.report['armport_server_metrics'] = self.summary

    def failure(self, exc):
        self.summary['errors'] += 1
        self.summary['last_error_type'] = type(exc).__name__

    def close(self):
        self.stopped = True
        if self._proc_entries is not None:
            self._proc_entries.close()
            self._proc_entries = None
        self._discovery_retry = None
        self._lineage_entries = self._lineage_groups = None

    def lineage_candidates(self, owner, deadline):
        """Rotate through group keys only; never enumerate all worker records."""
        groups = getattr(owner, 'live_lineage', {}).get('groups', {})
        if groups is not self._lineage_groups:
            self._lineage_groups, self._lineage_entries = groups, None
        if self._lineage_entries is None:
            self._lineage_entries = iter(groups)
        pids, complete = [], True
        while len(pids) < PROCESS_LIMIT:
            if self.clock() >= deadline:
                complete = False
                break
            try:
                pid, _ = next(self._lineage_entries)
            except StopIteration:
                self._lineage_entries = None
                break
            except RuntimeError:
                # The authoritative registry may change between callbacks.
                # Restart its key scan next time; /proc discovery is separate.
                self._lineage_entries = None
                complete = False
                break
            pids.append(pid)
        if self._lineage_entries is not None:
            complete = False
        return pids, complete

    def snapshot_lineage(self, observer, owner, pid, starttime, deadline):
        if not hasattr(observer, 'live_lineage'):
            return
        observer.live_lineage['groups'] = {}
        key = (pid, starttime)
        record = owner.live_lineage['groups'].get(key)
        if record is None:
            return
        # An oversized cache stays unavailable, but a live group may still
        # pass fresh ownership checks. Never truncate cached worker proofs.
        if len(record['workers']) > THREAD_LIMIT:
            return False
        workers = {}
        for name, worker in record['workers'].items():
            if self.clock() >= deadline:
                raise TimeoutError('sample budget exhausted')
            workers[name] = copy.deepcopy(worker)
        if self.clock() >= deadline:
            raise TimeoutError('sample budget exhausted')
        observer.live_lineage['groups'][key] = {
            'stat': dict(record['stat']), 'status': copy.deepcopy(record['status']),
            'prefix_sha256': record['prefix_sha256'], 'workers': workers}

    def thread_samples(self, observer, path, group, deadline, remaining):
        rows, previous = [], {}
        complete, errors, seen = True, 0, 0
        try:
            with os.scandir(path / 'task') as tasks:
                for task in tasks:
                    if not task.name.isdecimal():
                        continue
                    if seen >= min(THREAD_LIMIT, remaining) or self.clock() >= deadline:
                        complete = False
                        break
                    seen += 1
                    target = Path(task.path)
                    try:
                        before = parse_stat(bounded_read(target / 'stat'))
                        status = observer.status(target)
                        after = parse_stat(bounded_read(target / 'stat'))
                        if (before['proc_pid'], before['starttime']) != (after['proc_pid'], after['starttime']) \
                                or after['proc_pid'] != int(task.name) or status['tgid'] != group['proc_pid'] \
                                or status['pid'] != after['proc_pid'] or status['uid'] != observer.real_uid:
                            raise ValueError('thread identity changed')
                        after['observed_monotonic'] = self.clock()
                        key = (group['proc_pid'], group['starttime'], after['proc_pid'], after['starttime'])
                        row = {**after, **cpu_delta(after, self.thread_previous.get(key), self.hz)}
                        rows.append(row)
                        previous[key] = after
                    except Exception:
                        errors += 1
                        complete = False
        except Exception:
            errors += 1
            complete = False
        rows.sort(key=lambda row: (row['cpu_user_ms'] or 0) + (row['cpu_system_ms'] or 0), reverse=True)
        return rows[:THREAD_EXPORT_LIMIT], previous, {'complete': complete, 'tasks_scanned': seen,
            'errors': errors, 'rows_omitted': max(0, len(rows) - THREAD_EXPORT_LIMIT),
            'export_order': 'largest_measured_cpu_delta_first'}, seen

    def processes(self, deadline):
        owner = self.diagnostic.wine_owner
        observer = detached_owner(owner) if self.clock() < deadline else None
        rows, processes, threads, inspected = [], {}, {}, set()
        errors, visited, task_total, complete = 0, 0, 0, True
        retried, lineage_complete, lineage_omissions = False, True, 0

        def inspect(pid, *, retry_on_timeout=False):
            nonlocal errors, lineage_omissions
            inspected.add(pid)
            try:
                if self.clock() >= deadline:
                    raise TimeoutError('sample budget exhausted')
                path = observer.proc_root / str(pid)
                first = parse_stat(bounded_read(path / 'stat'))
                if self.snapshot_lineage(observer, owner, pid, first['starttime'], deadline) is False:
                    lineage_omissions += 1
                if self.clock() >= deadline:
                    raise TimeoutError('sample budget exhausted')
                before = observer.inspect(pid, deadline)
                if before is None:
                    return
                if self.clock() >= deadline:
                    raise TimeoutError('sample budget exhausted')
                value = parse_stat(bounded_read(path / 'stat'))
                if self.clock() >= deadline:
                    raise TimeoutError('sample budget exhausted')
                role, map_id = process_role(bounded_read(path / 'cmdline'))
                if self.clock() >= deadline:
                    raise TimeoutError('sample budget exhausted')
                after = observer.inspect(pid, deadline)
                if before != after or (value['proc_pid'], value['starttime']) != (pid, before['starttime']):
                    raise ValueError('process ownership changed during sample')
                if self.clock() >= deadline:
                    raise TimeoutError('sample budget exhausted')
                value['observed_monotonic'] = self.clock()
                rows.append({**value, 'pid': before['pid'], 'role': role, 'map_id': map_id,
                    **cpu_delta(value, self.process_previous.get(pid), self.hz),
                    'thread_cpu': [], 'thread_sampling': {'complete': False, 'unavailable_reason': 'budget_or_role'},
                    'ownership_rechecked_before_and_after': True})
                processes[pid] = value
            except Exception:
                errors += 1
                if retry_on_timeout and self.clock() >= deadline:
                    # The directory iterator has already advanced. Retry this
                    # exact entry first with a fresh window, once. A process
                    # too expensive even for a whole window cannot monopolize
                    # every future sample; the iterator resumes after it.
                    self._discovery_retry = pid

        retry = self._discovery_retry
        if retry is not None and observer is not None and self.clock() < deadline:
            self._discovery_retry = None
            retried = True
            inspect(retry)

        # Previously observed groups first so unrelated /proc entries cannot
        # repeatedly starve the resident servers under the bounded scan.
        known = list(self.process_previous)
        candidates, lineage_complete = (self.lineage_candidates(owner, deadline)
                                        if observer is not None else ([], False))
        for pid in candidates:
            if pid not in known:
                known.append(pid)
        # Reserve at least half the callback budget and half the row capacity
        # for discovery. Rotate both inventories on truncation so a newly
        # launched second zone is not starved by an expensive resident group.
        known = sorted(set(known))
        known = [pid for pid in known if pid > self.known_cursor] + [pid for pid in known if pid <= self.known_cursor]
        known_deadline = self.clock() + max(0, deadline - self.clock()) / 2
        for pid in known[:max(1, PROCESS_LIMIT // 2)]:
            if self.clock() >= known_deadline:
                complete = False
                break
            self.known_cursor = pid
            if pid not in inspected:
                inspect(pid)
        resumed = self._proc_entries is not None
        if resumed:
            complete = False  # a continuation is a subset of this window
        proc_root = owner.proc_root
        if self._proc_root != proc_root and self._proc_entries is not None:
            self._proc_entries.close()
            self._proc_entries = None
        if self._proc_entries is None and self.clock() < deadline:
            self._proc_entries = os.scandir(proc_root)
            self._proc_root = proc_root
        # Retain the iterator only until the next cooperative sample. This
        # resumes even when procfs directory order is not numeric and avoids
        # repeatedly inspecting an expensive prefix. close() releases it when
        # the existing cleanup begins; there is no concurrent reader.
        while True:
            if visited >= PROC_SCAN_LIMIT or len(rows) >= PROCESS_LIMIT or self.clock() >= deadline:
                complete = False
                break
            try:
                entry = next(self._proc_entries)
            except StopIteration:
                self._proc_entries.close()
                self._proc_entries = None
                break
            visited += 1
            if entry.name.isdecimal() and int(entry.name) not in inspected:
                inspect(int(entry.name), retry_on_timeout=True)
        # Totals for all groups take precedence over optional thread detail.
        for row in sorted(rows, key=lambda value: value['role'] != 'dbserver'):
            if row['role'] == 'other' or self.clock() >= deadline or task_total >= THREAD_TOTAL_LIMIT:
                continue
            pid = row['proc_pid']
            try:
                if self.snapshot_lineage(observer, owner, pid, row['starttime'], deadline) is False:
                    lineage_omissions += 1
                before = observer.inspect(pid, deadline)
                if before is None or before['starttime'] != row['starttime']:
                    raise ValueError('process changed before thread sampling')
                task_rows, task_previous, task_info, used = self.thread_samples(
                    observer, observer.proc_root / str(pid), before, deadline, THREAD_TOTAL_LIMIT - task_total)
                task_total += used
                after = observer.inspect(pid, deadline)
                if before != after:
                    raise ValueError('process changed during thread sampling')
                row.update(thread_cpu=task_rows, thread_sampling=task_info)
                threads.update(task_previous)
            except Exception as exc:
                row['thread_sampling'] = {'complete': False, 'unavailable_reason': type(exc).__name__}
        self.process_previous, self.thread_previous = processes, threads
        return rows, {'complete': complete and lineage_complete and not errors and not lineage_omissions,
                      'errors': errors, 'proc_entries_visited': visited,
                      'process_limit': PROCESS_LIMIT, 'thread_tasks_scanned': task_total,
                      'lineage_key_scan_complete': lineage_complete,
                      'lineage_snapshot_omissions': lineage_omissions,
                      'discovery_retried_before_scan': retried,
                      'discovery_retry_pending': self._discovery_retry is not None,
                      'discovery_resumed_from_prior_sample': resumed,
                      'discovery_continues_next_sample': self._proc_entries is not None}

    def maps(self, deadline):
        import game_map_progress as progress
        owned = self.owned_maps()
        rows, previous = [], {}
        self.native_context = {}
        for map_id, entry in list(owned.items())[:MAP_LIMIT]:
            row = {'map_id': map_id, 'available': False, 'is_success_proof': False}
            try:
                if self.clock() >= deadline:
                    raise TimeoutError('sample budget exhausted')
                process = entry['process'].process
                if process.poll() is not None:
                    raise ProcessLookupError('map launcher exited')
                # Own observation history: never mutate readiness's previous
                # record or freshness bookkeeping. Reader binds the file inode.
                value = progress.read_record(entry['progress_path'])
                if process.poll() is not None:
                    raise ProcessLookupError('map launcher exited during sample')
                row.update(available=True, launcher_pid=process.pid,
                    **{name: value[name] for name in ('windows_pid', 'main_thread_id', 'file_identity',
                        'sequence', 'tick_started', 'tick_completed', 'stage', 'observed_monotonic')},
                    **map_delta(value, self.map_previous.get(map_id)))
                previous[map_id] = value
                self.native_context[map_id] = (entry['process'], entry['progress_path'],
                    entry.get('launch_utc_ms'), value)
            except Exception as exc:
                row['unavailable_reason'] = type(exc).__name__
            rows.append(row)
        self.map_previous = previous
        return rows, {'maps_omitted': max(0, len(owned) - MAP_LIMIT)}

    def owned_maps(self):
        server = getattr(self.diagnostic, 'local_server', None)
        owned = dict(getattr(server, 'maps', {}))
        if not owned and getattr(server, 'map_process', None) is not None:
            owned[getattr(server, 'active_map_id', 1)] = {'process': server.map_process,
                'progress_path': server.map_progress_path,
                'launch_utc_ms': getattr(server, 'map_launch_utc_ms', None),
                'server_metrics_enabled': getattr(server, 'server_metrics_enabled', None)}
        return owned

    def native_qualified(self):
        server = getattr(self.diagnostic, 'local_server', None)
        contract = getattr(server, 'map_contract', None)
        producer = contract.get('producer') if isinstance(contract, dict) else None
        proof = producer.get('armport_server_metrics') if isinstance(producer, dict) else None
        return isinstance(proof, dict) and bool(proof)

    def native_durations(self, rows, deadline):
        """Use only the console generation whose progress was sampled this turn.

        Package admission owns environment activation. This parser cannot enable
        the producer, qualify a binary, alter health, or grant readiness.
        """
        deadline = min(deadline, self.clock() + NATIVE_BUDGET)
        owned = self.owned_maps()
        qualified = self.native_qualified()
        remaining, scanned, copied, windows = NATIVE_TOTAL_BYTES, 0, 0, 0
        current = {row['map_id']: row for row in rows}
        self.native_tails = {key: value for key, value in self.native_tails.items() if key in current}
        order = sorted(current)
        order = [key for key in order if key > self.native_cursor] + [key for key in order if key <= self.native_cursor]
        for map_id in order:
            row, entry = current[map_id], owned.get(map_id)
            unavailable = {'available': False, 'is_success_proof': False, 'windows': []}
            if not qualified or (entry is not None and entry.get('server_metrics_enabled') is False):
                row['native_durations'] = dict(unavailable, status='disabled',
                    reason='producer_not_qualified' if not qualified else 'producer_not_enabled')
                self.native_tails.pop(map_id, None)
                continue
            if entry is None or entry.get('server_metrics_enabled') is not True:
                row['native_durations'] = dict(unavailable, status='activation_unknown',
                    reason='qualified_producer_without_launch_activation_receipt')
                continue
            context = self.native_context.get(map_id)
            if context is None:
                row['native_durations'] = dict(unavailable, status='identity_unavailable', reason='map_progress_unavailable')
                continue
            handle, path, launch_ms, value = context
            try:
                if (entry is None or entry.get('process') is not handle or entry.get('progress_path') != path
                        or entry.get('launch_utc_ms') != launch_ms or handle.process.poll() is not None):
                    raise LookupError('map generation changed before console sample')
                output = handle.output
                if not isinstance(output, bytearray) or handle.overflow:
                    raise ValueError('owned console is unavailable or overflowed')
                binding = (handle, path, launch_ms, value['windows_pid'], value['main_thread_id'],
                           tuple(sorted(value['file_identity'].items())))
                tail = self.native_tails.get(map_id)
                if tail is not None and tail.binding[0] is handle and tail.binding != binding:
                    raise LookupError('progress identity changed within map generation')
                if tail is None or tail.binding != binding:
                    tail = NativeConsoleTail(binding, output)
                    self.native_tails[map_id] = tail
                if tail.output is not output:
                    raise LookupError('owned console replaced within map generation')
                result = tail.sample(map_id, value['windows_pid'], self.clock(), self.clock, deadline, remaining)
                if result.get('reason') != 'sample_budget_exhausted':
                    self.native_cursor = map_id
                remaining -= result['bytes_copied']
                copied += result['bytes_copied']
                scanned += result['bytes_scanned']
                after = self.owned_maps().get(map_id)
                if (after is None or after.get('process') is not handle or after.get('progress_path') != path
                        or after.get('launch_utc_ms') != launch_ms or handle.process.poll() is not None
                        or handle.output is not output or len(output) < tail.offset or handle.overflow):
                    raise LookupError('map generation changed during console sample')
                row['native_durations'] = result
                windows += len(result['windows'])
            except Exception as exc:
                row['native_durations'] = dict(unavailable, status='identity_unavailable', reason=type(exc).__name__)
        self.summary['native_duration_windows_observed'] += windows
        for key in ('longest_tick_ms', 'file_load_ms'):
            self.summary[key] = {'available': self.summary['native_duration_windows_observed'] > 0,
                'reason': 'per_map_native_windows' if self.summary['native_duration_windows_observed']
                          else 'no_native_window_observed', 'scope': NATIVE_SCOPE}
        return {'bytes_scanned': scanned, 'bytes_copied': copied,
            'byte_limit': NATIVE_TOTAL_BYTES, 'line_limit_per_map': NATIVE_LINES,
            'windows_observed': windows, 'qualified_producer': qualified,
            'reserved_within_callback_budget_seconds': NATIVE_BUDGET,
            'stale_after_seconds_without_new_console_record': NATIVE_STALE_SECONDS}

    def append(self, sample):
        raw = (json.dumps(sample, sort_keys=True, separators=(',', ':')) + '\n').encode()
        descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != self.summary['export_bytes']:
                raise ValueError('metrics output identity or size changed')
            if info.st_size + len(raw) > EXPORT_BYTES:
                self.summary['samples_omitted'] += 1
                return
            with os.fdopen(descriptor, 'ab', closefd=False) as target:
                target.write(raw)
            self.summary['export_bytes'] += len(raw)
            self.summary['samples_written'] += 1
        finally:
            os.close(descriptor)

    def observe(self):
        """Best effort; optional telemetry can never fail the original health check."""
        now = self.clock()
        if self.stopped or now < self.next_sample:
            return
        self.next_sample = now + INTERVAL
        if self.summary['samples_written'] >= SAMPLE_LIMIT or self.summary['export_bytes'] >= EXPORT_BYTES:
            self.summary['samples_omitted'] += 1
            return
        deadline = now + BUDGET
        sample = {'schema': SCHEMA, 'format': 1, 'is_success_proof': False,
                  'observed_monotonic': now, 'observed_utc_ms': int(self.wall() * 1000),
                  'longest_tick_ms': None, 'file_load_ms': None, 'wineserver_requests': None}
        try:
            sample['maps'], sample['map_sampling'] = self.maps(deadline)
            process_deadline = deadline - NATIVE_BUDGET if self.native_qualified() and self.native_context else deadline
            sample['processes'], sample['process_sampling'] = self.processes(process_deadline)
        except Exception as exc:
            self.failure(exc)
            sample['sample_error_type'] = type(exc).__name__
        if 'maps' in sample:
            try:
                sample['native_duration_sampling'] = self.native_durations(sample['maps'], deadline)
            except Exception as exc:
                self.failure(exc)
                sample['native_duration_error_type'] = type(exc).__name__
        sample['collection_overhead_ms'] = round((self.clock() - now) * 1000, 3)
        sample['budget_exceeded'] = self.clock() >= deadline
        try:
            self.append(sample)
        except Exception as exc:
            self.failure(exc)
        self.summary['last_callback_overhead_ms'] = round((self.clock() - now) * 1000, 3)
