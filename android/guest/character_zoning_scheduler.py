"""Temporary destination-only CPU weighting; unsupported kernels stay unchanged.

This is not a GPU timer or a performance claim. A separate child proves the
inherited nice limit and round-trip permission before any MapServer is changed.
Every observed task is bound to the diagnostic token, an additional unique map
launch token, the real UID, its thread group and both PID start times.
"""
import copy
import json
import os
from pathlib import Path
import resource
import secrets
import subprocess
import sys
import time

import diagnostic as base

ENVIRONMENT = 'COH_ZONING_PREPARATION_OWNER'
NICE_INCREMENT = 5
TASK_LIMIT = 128
GROUP_LIMIT = 16
SAMPLE_LIMIT = 160


def pressure_observation(proc_root):
    """Optional system-wide stall counters; these do not attribute a cause."""
    result = {'scope': 'system_wide_not_attributed_to_destination', 'pressure': {}, 'vmstat': {}}
    for kind in ('cpu', 'memory', 'io'):
        try:
            with (proc_root / 'pressure' / kind).open() as source:
                raw = source.read(4097)
            result['pressure'][kind] = raw if len(raw) <= 4096 else 'unavailable_oversized'
        except OSError:
            result['pressure'][kind] = 'unavailable'
    try:
        with (proc_root / 'vmstat').open() as source:
            raw = source.read(65537)
        base.require(len(raw) <= 65536, 'System VM statistics exceeded bound')
        for line in raw.splitlines():
            name, value = line.split()
            if name in ('pgfault', 'pgmajfault', 'pswpin', 'pswpout') or name.startswith('workingset_refault'):
                result['vmstat'][name] = int(value)
    except (OSError, ValueError, base.DiagnosticError):
        result['vmstat'] = {'unavailable': True}
    return result


def priority_probe():
    """Called only in a disposable child; a denied restore cannot affect play."""
    original = os.getpriority(os.PRIO_PROCESS, 0)
    limits = resource.getrlimit(resource.RLIMIT_NICE)
    result = {'supported': False, 'original_nice': original,
              'rlimit_nice_soft': limits[0], 'rlimit_nice_hard': limits[1]}
    # Linux permits an unprivileged decrease down to 20 - rlim_cur. Do not
    # even lower the disposable child when its advertised limit cannot restore.
    if limits[0] != resource.RLIM_INFINITY and 20 - limits[0] > original:
        return dict(result, reason='inherited_limit_cannot_restore')
    target = min(19, original + NICE_INCREMENT)
    if target == original:
        return dict(result, reason='already_lowest_priority')
    try:
        os.setpriority(os.PRIO_PROCESS, 0, target)
        lowered = os.getpriority(os.PRIO_PROCESS, 0)
        os.setpriority(os.PRIO_PROCESS, 0, original)
        restored = os.getpriority(os.PRIO_PROCESS, 0)
        return dict(result, supported=lowered == target and restored == original,
                    lowered_nice=lowered, restored_nice=restored)
    except OSError as failure:
        return dict(result, reason='kernel_denied_probe', errno=failure.errno)


def checked_probe():
    try:
        child = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--probe'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3, check=False)
        base.require(child.returncode == 0 and len(child.stdout) <= 2048 and not child.stderr,
                     'Preparation scheduler probe failed')
        value = json.loads(child.stdout)
        base.require(type(value) is dict and type(value.get('supported')) is bool
                     and type(value.get('original_nice')) is int
                     and -20 <= value['original_nice'] <= 19, 'Malformed scheduler capability')
        if value['supported']:
            base.require(value.get('restored_nice') == value['original_nice']
                and value.get('lowered_nice') == min(19, value['original_nice'] + NICE_INCREMENT),
                'Scheduler probe did not prove restoration')
        return value
    except (OSError, ValueError, subprocess.TimeoutExpired, base.DiagnosticError) as failure:
        return {'supported': False, 'reason': 'probe_unavailable', 'error_type': type(failure).__name__}


class PreparationScheduler:
    """Lower only a new destination's tasks, restoring before readiness publication."""
    def __init__(self, owner, map_id, *, probe=None):
        self.owner = owner
        self.scanner = copy.copy(owner.wine_owner)
        self.scanner.initialized = False
        self.scanner.receipt = copy.deepcopy(owner.wine_owner.receipt)
        self.scanner.dead_leaders, self.scanner.owned_workers = set(), set()
        self.token = secrets.token_hex(32)
        owner.ctx.secrets.append(self.token)
        self.needle = (ENVIRONMENT + '=' + self.token).encode()
        self.environment = {ENVIRONMENT: self.token}
        self.changed = {}
        self.groups = {}
        self.unresolved_inheritance = False
        self.next_sample = 0
        self.next_discovery = 0
        self.restored = False
        self.capability = checked_probe() if probe is None else probe
        self.report = {'format': 1, 'map_id': map_id,
            'policy': 'temporary_plus_5_nice_exact_destination_threads',
            'ownership': 'diagnostic_and_unique_map_tokens_real_uid_group_and_thread_starttimes',
            'capability': self.capability, 'samples': [], 'changed_threads': 0,
            'restored_threads': 0, 'exited_threads': 0, 'unavailable_samples': 0,
            'restore_complete': False, 'game_or_shared_wine_processes_changed': False,
            'gpu_time_measured': False, 'physical_performance_gain_verified': False,
            'rss_is_not_pss': True, 'shared_pages_may_be_counted_more_than_once': True,
            'cpu_ticks_per_second': os.sysconf('SC_CLK_TCK'),
            'resource_scope': 'exact_destination_token_processes_only'}

    def _group_original(self, identity, tasks):
        key = (identity['proc_pid'], identity['starttime'])
        existing = self.groups.get(('nice', *key))
        if existing is not None or not tasks:
            return existing
        values = {os.getpriority(os.PRIO_PROCESS, task[2]) for task in tasks}
        if len(values) != 1:
            # Creator-TID provenance is absent from procfs; do not guess the
            # inherited baseline of a heterogeneous group.
            self.report['heterogeneous_groups_unchanged'] = self.report.get('heterogeneous_groups_unchanged', 0) + 1
            return None
        original = values.pop()
        stat = self.scanner.process_stat(self.scanner.proc_root / str(identity['proc_pid']))
        parents = [record for parent, record in self.groups.items()
                   if len(parent) == 2 and parent[0] == stat['parent']]
        inherited = False
        for parent in parents:
            parent_key = (parent['proc_pid'], parent['starttime'])
            parent_original = self.groups.get(('nice', *parent_key))
            if parent_original is not None and any(k[:2] == parent_key for k in self.changed):
                current = self.scanner.process_stat(self.scanner.proc_root / str(parent['proc_pid']))
                base.require(current['starttime'] == parent['starttime'], 'Destination parent identity changed')
                if original == min(19, parent_original + NICE_INCREMENT):
                    original, inherited = parent_original, True
        if not inherited and any(original == record[5] for record in self.changed.values()):
            self.unresolved_inheritance = True
            base.require(False, 'Unattributed destination child inherited scheduling weight')
        self.groups[('nice', *key)] = original
        if inherited:
            for task, info, tid in tasks:
                self.changed[(*key, info['pid'], info['starttime'])] = (
                    identity, task, info, tid, original, min(19, original + NICE_INCREMENT))
            self.report['changed_threads'] = len(self.changed)
        return original

    def _remember_group(self, identity):
        key = (identity['proc_pid'], identity['starttime'])
        base.require(key in self.groups or sum(len(k) == 2 for k in self.groups) < GROUP_LIMIT,
                     'Destination process observation bound exceeded')
        self.groups[key] = identity
        return key

    def _map_group(self, identity, deadline):
        current = self.scanner.inspect(identity['proc_pid'], deadline)
        if current is None:
            return None
        base.require(current == identity, 'Destination process identity changed')
        path = self.scanner.proc_root / str(identity['proc_pid'])
        def map_token(task):
            with (task / 'environ').open('rb') as environment:
                raw = environment.read(1024 * 1024 + 1)
            base.require(len(raw) <= 1024 * 1024, 'Destination environment exceeded bound')
            return self.needle in raw.split(b'\0')
        info = self.scanner.process_stat(path)
        if info['state'] != 'Z':
            return path if map_token(path) else None
        # Wine/FEX may leave a zombie Unix leader while workers still own the
        # process. Reuse the established owner's verified worker policy; the
        # empty leader environment alone is not proof that the map token left.
        for task, worker in self.scanner.live_tasks(path, deadline):
            status = self.scanner.status(task)
            base.require(status['uid'] == self.scanner.real_uid
                and status['tgid'] == identity['proc_pid'] and status['pid'] == worker['pid'],
                'Destination live worker group differs')
            if not self.scanner.has_token(task) or not map_token(task):
                continue
            after = self.scanner.process_stat(task)
            leader = self.scanner.process_stat(path)
            base.require(after['pid'] == worker['pid'] and after['starttime'] == worker['starttime']
                and leader['starttime'] == identity['starttime'], 'Destination live worker identity changed')
            if after['state'] != 'Z':
                return path
        return None

    def _tasks(self, identity, deadline):
        path = self._map_group(identity, deadline)
        if path is None:
            return
        entries = list((path / 'task').iterdir())
        base.require(len(entries) <= TASK_LIMIT, 'Destination task bound exceeded')
        for task in entries:
            base.require(time.monotonic() < deadline, 'Destination task observation timed out')
            if not task.name.isdecimal():
                continue
            try:
                status = self.scanner.status(task)
                info = self.scanner.process_stat(task)
                base.require(status['uid'] == self.scanner.real_uid
                    and status['tgid'] == identity['proc_pid']
                    and status['pid'] == info['pid'] == int(task.name), 'Destination task owner differs')
                if info['state'] == 'Z':
                    continue
                if self.scanner.direct_pid_view:
                    tid = info['pid']
                else:
                    base.require(len(status['namespace_pids']) == self.scanner.namespace_depth,
                                 'Destination task namespace differs')
                    tid = status['namespace_pids'][-1]
                base.require(tid > 0 and tid != os.getpid(), 'Invalid destination task')
                yield task, info, tid
            except FileNotFoundError:
                continue

    def _check_task(self, identity, task, info, deadline):
        current = self.scanner.process_stat(task)
        if current['state'] == 'Z' and current['starttime'] == info['starttime']:
            raise ProcessLookupError('Destination task exited')
        base.require(self._map_group(identity, deadline) is not None, 'Destination ownership disappeared')
        base.require(current['pid'] == info['pid'] and current['starttime'] == info['starttime']
                     and current['state'] != 'Z', 'Destination task identity changed')

    def sample(self):
        now = time.monotonic()
        if self.restored or now < self.next_sample:
            return
        self.next_sample = now + 5
        deadline = now + .5
        rows = []
        try:
            identities = [value for key, value in self.groups.items() if len(key) == 2]
            if now >= self.next_discovery:
                self.next_discovery = now + 15
                identities = self.scanner.scan(deadline)
            for identity in identities:
                try:
                    path = self._map_group(identity, deadline)
                    if path is None:
                        continue
                    group_key = self._remember_group(identity)
                    tasks = list(self._tasks(identity, deadline))
                    group_original = self._group_original(identity, tasks)
                    values = []
                    for task, info, tid in tasks:
                        key = (*group_key, info['pid'], info['starttime'])
                        before = os.getpriority(os.PRIO_PROCESS, tid)
                        target = min(19, group_original + NICE_INCREMENT) if group_original is not None else None
                        limit = self.capability.get('rlimit_nice_soft', 0)
                        restorable = limit == resource.RLIM_INFINITY or 20 - limit <= before
                        if (self.capability.get('supported') is True and group_original is not None
                                and restorable and key not in self.changed):
                            # A task created by an already weighted parent inherits
                            # its temporary nice value; restore it to that group's
                            # original weight, never to a guessed global default.
                            original = group_original if before == target and any(
                                k[:2] == group_key for k in self.changed) else before
                            lower = min(19, original + NICE_INCREMENT)
                            self._check_task(identity, task, info, deadline)
                            if before != lower:
                                os.setpriority(os.PRIO_PROCESS, tid, lower)
                            self.changed[key] = (identity, task, info, tid, original, lower)
                            self.report['changed_threads'] = len(self.changed)
                            self._check_task(identity, task, info, deadline)
                            base.require(os.getpriority(os.PRIO_PROCESS, tid) == lower,
                                         'Destination scheduler readback differs')
                        raw = (task / 'stat').read_text().rsplit(') ', 1)[1].split()
                        values.append({'tid': tid, 'starttime': info['starttime'],
                            'nice': os.getpriority(os.PRIO_PROCESS, tid),
                            'cpu_ticks': int(raw[11]) + int(raw[12])})
                    raw = (path / 'status').read_text().splitlines()
                    rss = [int(row.split()[1]) for row in raw if row.startswith('VmRSS:')]
                    membership = {}
                    for name in ('cgroup', 'autogroup'):
                        try:
                            value = (path / name).read_text()
                            membership[name] = value[:4096] if len(value) <= 4096 else 'unavailable_oversized'
                        except OSError:
                            membership[name] = 'unavailable'
                    rows.append({'pid': identity['pid'], 'starttime': identity['starttime'],
                        'rss_kib': rss[0] if len(rss) == 1 else None, 'tasks': values, **membership})
                except (FileNotFoundError, ProcessLookupError):
                    continue
            self.report['changed_threads'] = len(self.changed)
            if len(self.report['samples']) < SAMPLE_LIMIT:
                pressure = pressure_observation(self.scanner.proc_root)
                self.report['samples'].append({'utc_ms': int(time.time() * 1000),
                    'monotonic_ms': int(now * 1000), 'processes': rows,
                    'observation_elapsed_ms': round((time.monotonic() - now) * 1000, 3),
                    'system_pressure': pressure})
        except (OSError, ValueError, base.DiagnosticError) as failure:
            self.report['unavailable_samples'] += 1
            self.report['last_error'] = type(failure).__name__
            # Once weighting started, unavailable ownership/readback cannot be
            # silently treated as an unchanged fallback. Restore or fail closed.
            if self.changed:
                self.restore()
            self.capability = dict(self.capability, supported=False)
            self.report['weighting_disabled_after_observation_error'] = True

    def restore(self):
        if self.restored:
            return
        if not self.changed:
            # No task was ever weighted, so no descendant can have inherited
            # our weight. Unsupported/denied telemetry must not delay readiness
            # or turn an unchanged fallback into a process-inspection failure.
            self.report.update(restore_complete=True, restoration_policy='no_mutations_to_restore')
            self.restored = True
            return
        deadline = time.monotonic() + 3
        base.require(not self.unresolved_inheritance, 'Destination inherited priority cannot be restored safely')
        previous_live = None
        completed, exited = set(), set()
        for attempt in range(4):
            live = set()
            # Restore creators first, then rediscover both processes and tasks.
            # Two unchanged passes rule out an omitted child of a lowered TID;
            # future children of restored creators inherit the original weight.
            for identity in self.scanner.scan(deadline):
                try:
                    if self._map_group(identity, deadline) is None:
                        continue
                    group_key = self._remember_group(identity)
                    tasks = list(self._tasks(identity, deadline))
                    original = self._group_original(identity, tasks)
                    for task, info, tid in tasks:
                        key = (*group_key, info['pid'], info['starttime'])
                        live.add(key)
                        if key not in self.changed and any(k[:2] == group_key for k in self.changed):
                            current = os.getpriority(os.PRIO_PROCESS, tid)
                            if current == min(19, original + NICE_INCREMENT):
                                self.changed[key] = (identity, task, info, tid, original, current)
                                self.report['changed_threads'] = len(self.changed)
                except (FileNotFoundError, ProcessLookupError):
                    continue
            for key, (identity, task, info, tid, original, lowered) in list(self.changed.items()):
                try:
                    self._check_task(identity, task, info, deadline)
                    current = os.getpriority(os.PRIO_PROCESS, tid)
                    base.require(current in (original, lowered), 'Destination priority changed outside preparation')
                    if current != original:
                        os.setpriority(os.PRIO_PROCESS, tid, original)
                    self._check_task(identity, task, info, deadline)
                    base.require(os.getpriority(os.PRIO_PROCESS, tid) == original,
                                 'Destination priority restoration failed')
                    completed.add(key)
                except (FileNotFoundError, ProcessLookupError):
                    exited.add(key)
            if live == previous_live:
                break
            previous_live = live
        else:
            base.require(False, 'Destination task population did not stabilize for restoration')
        self.report['restored_threads'], self.report['exited_threads'] = len(completed), len(exited)
        self.report['changed_threads'] = len(self.changed)
        self.report['restore_complete'] = True
        self.restored = True


if __name__ == '__main__':
    if sys.argv[1:] != ['--probe']:
        raise SystemExit(2)
    print(json.dumps(priority_probe(), separators=(',', ':')))
