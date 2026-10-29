"""Bounded, observational server/owned-process samples for ARM64 Thor exports.

No readiness decisions, subprocesses, environment/command-line export, or new
threads. Linux CPU counters are not Wine request counts. Map tick counters come
from the retained native progress publisher; they cannot reveal the longest
individual tick or time inside file loads.
"""
import copy
import json
import os
from pathlib import Path
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
    """Optional observations must not amend authoritative cleanup receipts."""
    observer = copy.copy(owner)
    observer.receipt = copy.deepcopy(owner.receipt)
    observer.dead_leaders, observer.owned_workers = set(owner.dead_leaders), set(owner.owned_workers)
    if hasattr(owner, 'live_lineage'):
        observer.live_lineage = copy.deepcopy(owner.live_lineage)
    if not observer.initialized:
        observer.initialize()
    return observer


class ServerMetrics:
    def __init__(self, diagnostic, *, clock=time.monotonic, wall=time.time):
        self.diagnostic, self.clock, self.wall = diagnostic, clock, wall
        self.next_sample = 0
        self.known_cursor = 0
        self._proc_entries = self._proc_root = None
        self.stopped = False
        self.process_previous, self.thread_previous, self.map_previous = {}, {}, {}
        self.hz = int(os.sysconf('SC_CLK_TCK'))
        self.path = Path(diagnostic.capture_dir) / 'server-metrics.jsonl'
        self.summary = {'schema': SCHEMA, 'format': 1, 'is_success_proof': False,
            'file': self.path.name, 'interval_seconds': INTERVAL, 'budget_seconds': BUDGET,
            'samples_written': 0, 'samples_omitted': 0, 'errors': 0, 'last_error_type': None,
            'export_bytes': 0, 'export_limit_bytes': EXPORT_BYTES, 'sample_limit': SAMPLE_LIMIT,
            'cpu_clock_ticks_per_second': self.hz,
            'sampling': 'cooperative_health_callback_not_a_realtime_schedule',
            'longest_tick_ms': {'available': False, 'reason': 'native_duration_producer_not_wired'},
            'file_load_ms': {'available': False, 'reason': 'native_duration_producer_not_wired'},
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
        observer = detached_owner(self.diagnostic.wine_owner)
        rows, processes, threads, inspected = [], {}, {}, set()
        errors, visited, task_total, complete = 0, 0, 0, True

        def inspect(pid):
            nonlocal errors
            inspected.add(pid)
            try:
                before = observer.inspect(pid, deadline)
                if before is None:
                    return
                path = observer.proc_root / str(pid)
                value = parse_stat(bounded_read(path / 'stat'))
                role, map_id = process_role(bounded_read(path / 'cmdline'))
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

        # Previously observed groups first so unrelated /proc entries cannot
        # repeatedly starve the resident servers under the bounded scan.
        known = list(self.process_previous)
        for pid, _ in getattr(observer, 'live_lineage', {}).get('groups', {}):
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
            inspect(pid)
        resumed = self._proc_entries is not None
        if resumed:
            complete = False  # a continuation is a subset of this window
        if self._proc_root != observer.proc_root and self._proc_entries is not None:
            self._proc_entries.close()
            self._proc_entries = None
        if self._proc_entries is None:
            self._proc_entries = os.scandir(observer.proc_root)
            self._proc_root = observer.proc_root
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
                inspect(int(entry.name))
        # Totals for all groups take precedence over optional thread detail.
        for row in sorted(rows, key=lambda value: value['role'] != 'dbserver'):
            if row['role'] == 'other' or self.clock() >= deadline or task_total >= THREAD_TOTAL_LIMIT:
                continue
            pid = row['proc_pid']
            try:
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
        return rows, {'complete': complete and not errors, 'errors': errors, 'proc_entries_visited': visited,
                      'process_limit': PROCESS_LIMIT, 'thread_tasks_scanned': task_total,
                      'discovery_resumed_from_prior_sample': resumed,
                      'discovery_continues_next_sample': self._proc_entries is not None}

    def maps(self, deadline):
        import game_map_progress as progress
        server = getattr(self.diagnostic, 'local_server', None)
        owned = dict(getattr(server, 'maps', {}))
        if not owned and getattr(server, 'map_process', None) is not None:
            owned[getattr(server, 'active_map_id', 1)] = {'process': server.map_process,
                'progress_path': server.map_progress_path}
        rows, previous = [], {}
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
            except Exception as exc:
                row['unavailable_reason'] = type(exc).__name__
            rows.append(row)
        self.map_previous = previous
        return rows, {'maps_omitted': max(0, len(owned) - MAP_LIMIT)}

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
            sample['processes'], sample['process_sampling'] = self.processes(deadline)
        except Exception as exc:
            self.failure(exc)
            sample['sample_error_type'] = type(exc).__name__
        sample['collection_overhead_ms'] = round((self.clock() - now) * 1000, 3)
        sample['budget_exceeded'] = self.clock() >= deadline
        try:
            self.append(sample)
        except Exception as exc:
            self.failure(exc)
        self.summary['last_callback_overhead_ms'] = round((self.clock() - now) * 1000, 3)
