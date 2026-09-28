#!/usr/bin/env python3
"""Bounded failure-only snapshots of this game's owned, still-live services.

Linux /proc stacks are kernel stacks; Windows contexts come from the separate
PE32 observer. The pinned Wine/FEX backend can return saved startup contexts,
so successful context APIs do not prove a current execution location. Neither
observation substitutes for a successful game runtime milestone.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import time

import diagnostic as base

SNAPSHOT_LIMIT = 1024 * 1024
WINDOWS_LIMIT = 384 * 1024
PROC_TEXT_LIMIT = 512 * 1024
PROCESS_LIMIT = 64
TASK_LIMIT = 256
FD_LIMIT = 512
PG_SESSION_LIMIT = 80
PG_RESULT_LIMIT = 192 * 1024
OBSERVATION_SECONDS = 28
DISPATCH_RECORD_BYTES = 128
DISPATCH_MAPPING_BYTES = 4096
DISPATCH_HEADER = struct.Struct('<8s9I')


class DispatchPublicationPending(base.DiagnosticError):
    """The bounded read did not yet observe a stable, even publication."""


def error(exc):
    return {'available': False, 'error_type': type(exc).__name__, 'error': str(exc)[-512:]}


def read_dispatch_record(path, stages, previous=None):
    """Read one stable main-thread publication, without a debugger or target IO."""
    base.require(isinstance(stages, dict) and 0 < len(stages) <= 128
                 and all(isinstance(key, str) and key.isdecimal() and 0 < int(key) <= 128
                         and isinstance(value, str) and re.fullmatch(r'[A-Z_]{1,64}', value)
                         for key, value in stages.items()), 'Invalid dispatch stage contract')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        identity = os.fstat(descriptor)
        base.require(stat.S_ISREG(identity.st_mode) and identity.st_size == DISPATCH_MAPPING_BYTES
                     and identity.st_uid == os.getuid(), 'Dispatch record is not an owned bounded regular file')
        raw = None
        for _ in range(16):
            first = os.pread(descriptor, DISPATCH_RECORD_BYTES, 0)
            second = os.pread(descriptor, DISPATCH_RECORD_BYTES, 0)
            if len(first) == DISPATCH_RECORD_BYTES and first == second:
                values = DISPATCH_HEADER.unpack_from(first)
                if values[5] and not values[5] & 1:
                    raw = first
                    break
            time.sleep(.001)
        current = os.stat(path, follow_symlinks=False)
        base.require((current.st_dev, current.st_ino, current.st_size) ==
                     (identity.st_dev, identity.st_ino, DISPATCH_MAPPING_BYTES),
                     'Dispatch record changed identity during observation')
        if raw is None:
            raise DispatchPublicationPending('Dispatch publication is incomplete or changing')
        (magic, version, size, pid, tid, sequence, stage, loops, flags, count) = values
        base.require(magic == b'COHDBP1\0' and version == 1 and size == DISPATCH_RECORD_BYTES
                     and count == len(stages) and str(stage) in stages and pid > 0 and tid > 0
                     and flags == 0 and not any(raw[DISPATCH_HEADER.size:]),
                     'Dispatch record format, identity, stage or overflow flag differs')
        value = {'available': True, 'sampled_utc': base.utc(), 'format': version,
                 'windows_pid': pid, 'main_thread_id': tid, 'sequence': sequence,
                 'stage_id': stage, 'stage': stages[str(stage)], 'loop_count': loops,
                 'flags': flags, 'stage_count': count,
                 'file_identity': {'device': identity.st_dev, 'inode': identity.st_ino},
                 'raw_record_hex': raw.hex(), 'raw_record_sha256': hashlib.sha256(raw).hexdigest(),
                 'source': 'opt-in DbServer main-thread publication', 'is_success_proof': False}
        if previous is not None:
            base.require(all(value[key] == previous[key] for key in
                             ('windows_pid', 'main_thread_id', 'file_identity'))
                         and sequence >= previous['sequence'] and loops >= previous['loop_count'],
                         'Dispatch identity or monotonic counters changed')
        return value
    finally:
        os.close(descriptor)


def capture_dispatch(diagnostic, previous=None):
    observations = {}
    for phase, path in getattr(diagnostic, 'dispatch_paths', {}).items():
        try:
            baseline = (previous if previous is not None else
                        diagnostic.game['dispatch_progress']['phases']).get(phase)
            observations[phase] = read_dispatch_record(path, diagnostic.dispatch_stages,
                                                       baseline if baseline and baseline.get('available') else None)
        except Exception as exc:
            observations[phase] = error(exc)
    return {'available': bool(observations) and all(item.get('available') for item in observations.values()),
            'active_phase': getattr(diagnostic, 'dispatch_phase', None),
            'phases': observations, 'is_success_proof': False}


def checked_identity(owner, identity, deadline):
    base.require(time.monotonic() < deadline, 'Hang inspection deadline exceeded')
    base.require(owner.inspect(identity['proc_pid'], deadline) == identity,
                 'Owned process changed during hang inspection')


class ProcCapture:
    def __init__(self, deadline):
        self.deadline = deadline
        self.remaining = PROC_TEXT_LIMIT
        self.tasks = self.fds = 0

    def check(self):
        base.require(time.monotonic() < self.deadline, 'Hang /proc deadline exceeded')

    def read(self, path, limit):
        try:
            self.check()
            limit = min(limit, self.remaining)
            if not limit:
                return {'available': False, 'omitted': 'aggregate text bound'}
            with path.open('rb') as source:
                raw = source.read(limit + 1)
            value = raw[:limit]
            self.remaining -= len(value)
            return {'available': True, 'text': value.decode('utf-8', errors='replace'),
                    'bytes': len(value), 'truncated': len(raw) > limit}
        except Exception as exc:
            return error(exc)

    def process(self, owner, identity):
        checked_identity(owner, identity, self.deadline)
        path = owner.proc_root / str(identity['proc_pid'])
        result = {'identity': identity, 'sampled_utc': base.utc(), 'tasks': [], 'socket_fds': []}
        for field, limit in (('stat', 4096), ('status', 8192), ('cmdline', 4096), ('wchan', 1024),
                             ('syscall', 4096), ('stack', 8192)):
            result[field] = self.read(path / field, limit)
        try:
            for task in (path / 'task').iterdir():
                self.check()
                if not task.name.isdecimal():
                    continue
                if self.tasks >= TASK_LIMIT:
                    result['tasks_omitted'] = 'aggregate task bound'
                    break
                self.tasks += 1
                try:
                    before = owner.process_stat(task)
                    base.require(before['pid'] == int(task.name), 'Hang task identity changed')
                    status = owner.status(task)
                    base.require(status['uid'] == owner.real_uid and status['tgid'] == identity['proc_pid'],
                                 'Hang task is outside owned group')
                    record = {'identity': before}
                    for field, limit in (('stat', 4096), ('status', 4096), ('wchan', 1024), ('syscall', 4096), ('stack', 8192)):
                        record[field] = self.read(task / field, limit)
                    after = owner.process_stat(task)
                    base.require(after['pid'] == before['pid'] and after['starttime'] == before['starttime'],
                                 'Hang task identity changed')
                    result['tasks'].append(record)
                except Exception as exc:
                    result['tasks'].append({'tid': int(task.name), **error(exc)})
        except Exception as exc:
            result['task_inspection'] = error(exc)
        try:
            for fd in (path / 'fd').iterdir():
                self.check()
                if self.fds >= FD_LIMIT:
                    result['fds_omitted'] = 'aggregate descriptor bound'
                    break
                self.fds += 1
                try:
                    target = os.readlink(fd)
                    match = re.fullmatch(r'socket:\[(\d+)\]', target)
                    if match:
                        result['socket_fds'].append({'fd': int(fd.name), 'inode': match.group(1)})
                except FileNotFoundError:
                    continue
        except Exception as exc:
            result['fd_inspection'] = error(exc)
        # Never export reads under a PID that was reused midway through capture.
        checked_identity(owner, identity, self.deadline)
        return result

    def sockets(self, owner, identities, inodes):
        if not identities:
            return {'available': False, 'omitted': 'no verified owned process namespace'}
        source = identities[0]
        checked_identity(owner, source, self.deadline)
        root = owner.proc_root / str(source['proc_pid']) / 'net'
        result = {'policy': 'only socket inodes held by verified owned processes', 'tables': {}}
        for name in ('tcp', 'tcp6', 'udp', 'udp6', 'unix'):
            table = self.read(root / name, 128 * 1024)
            if table.get('available'):
                lines = table.pop('text').splitlines()
                index = 6 if name == 'unix' else 9
                table['header'] = lines[0] if lines else ''
                table['rows'] = [line for line in lines[1:]
                                 if len(line.split()) > index and line.split()[index] in inodes]
                table['read_bytes'] = table.pop('bytes')
            result['tables'][name] = table
        checked_identity(owner, source, self.deadline)
        return result


def capture_processes(diagnostic, deadline):
    owner = diagnostic.wine_owner
    capture = ProcCapture(deadline)
    result = {'ownership_policy': 'existing same-real-uid and private-run-token guard',
              'stack_kind': 'Linux kernel stack only; not a Windows user stack',
              'process_limit': PROCESS_LIMIT, 'task_limit': TASK_LIMIT, 'fd_limit': FD_LIMIT,
              'text_byte_limit': PROC_TEXT_LIMIT, 'processes': []}
    try:
        identities = owner.scan(deadline)
        result['owned_process_count'] = len(identities)
        result['processes_omitted'] = max(0, len(identities) - PROCESS_LIMIT)
        verified = []
        for identity in identities[:PROCESS_LIMIT]:
            try:
                record = capture.process(owner, identity)
                record['launcher_labels'] = [child.label for child in diagnostic.ctx.children
                                            if child.process.pid == identity['pid']]
                result['processes'].append(record)
                verified.append(identity)
            except Exception as exc:
                result['processes'].append({'identity': identity, **error(exc)})
        inodes = {fd['inode'] for item in result['processes'] for fd in item.get('socket_fds', [])}
        # Reserve socket capacity even if task status exhausted its own budget.
        network = ProcCapture(deadline)
        network.remaining = 128 * 1024
        result['sockets'] = network.sockets(owner, verified, inodes)
        result['socket_table_bytes'] = 128 * 1024 - network.remaining
    except Exception as exc:
        result['inspection'] = error(exc)
    result.update(tasks_examined=capture.tasks, fds_examined=capture.fds,
                  text_bytes=PROC_TEXT_LIMIT - capture.remaining)
    return result


def capture_postgres(diagnostic, deadline):
    if diagnostic.pg is None or diagnostic.pg.process.poll() is not None:
        return {'available': False, 'omitted': 'private PostgreSQL is not running'}
    base.require(re.fullmatch(r'coh_test_[0-9a-f]{16}', diagnostic.database), 'Unowned game database')
    remaining = deadline - time.monotonic()
    base.require(remaining > 0, 'Hang SQL observation deadline exceeded')
    env = diagnostic.base_env.copy()
    env.update(PGPASSWORD=diagnostic.credentials['cohdiag_admin'], PGCONNECT_TIMEOUT='2',
               PGOPTIONS='-c statement_timeout=2000 -c lock_timeout=1000')
    query = """WITH activity AS (
 SELECT pid, backend_type, application_name, client_addr, client_port,
        backend_start, state, wait_event_type, wait_event, query_start, xact_start,
        state_change, backend_xid, backend_xmin, query, octet_length(query) AS query_bytes
 FROM pg_stat_activity WHERE datname='%s' AND usename='cohtest'
), selected AS (SELECT * FROM activity ORDER BY pid LIMIT %d)
SELECT json_build_object('sampled_at', clock_timestamp(),
 'query_text_source', 'pg_stat_activity.query; server activity buffer limit applies',
 'track_activity_query_size', current_setting('track_activity_query_size'),
 'session_count', (SELECT count(*) FROM activity),
 'sessions', coalesce((SELECT json_agg(row_to_json(selected)) FROM selected), '[]'::json));
""" % (diagnostic.database, PG_SESSION_LIMIT)
    ctx = diagnostic.ctx
    before = len(ctx.children)
    result = ctx.run('game-hang-postgres', [diagnostic.pgtool('psql'), '-X', '-w', '-A', '-t',
        '-v', 'ON_ERROR_STOP=1', '-h', str(diagnostic.socket_dir), '-p', str(diagnostic.port),
        '-U', 'cohdiag_admin', '-d', 'postgres'],
        env=env, input_text=query, timeout=min(3, remaining), cleanup=True)
    child = ctx.children[before]
    raw = child.text()
    base.require(not child.overflow and len(raw.encode()) <= PG_RESULT_LIMIT,
                 'PostgreSQL hang evidence exceeds bound')
    value = json.loads(raw)
    base.require(isinstance(value.get('sessions'), list) and len(value['sessions']) <= PG_SESSION_LIMIT
                 and type(value.get('session_count')) is int, 'Invalid PostgreSQL hang evidence')
    value.update(available=True, exit_code=result['exit_code'], session_limit=PG_SESSION_LIMIT,
                 sessions_omitted=max(0, value['session_count'] - len(value['sessions'])),
                 credentials_redacted=True, query_text_included=True)
    return value


def capture_windows(diagnostic, deadline):
    executable = Path('/opt/coh-m3/GameStackProbe.exe')
    if not executable.is_file() or executable.is_symlink():
        return {'available': False, 'omitted': 'PE32 GameStackProbe.exe is not staged'}, None
    remaining = deadline - time.monotonic()
    base.require(remaining > 0, 'Windows context observation deadline exceeded')
    ctx = diagnostic.ctx
    before = len(ctx.children)
    metadata = {'sampled_utc': base.utc(), 'kind': 'Windows x86 raw contexts, stack words and module addresses',
                'symbolized': False, 'current_execution_validated': False,
                'context_limitation': 'Pinned Wine/FEX GetThreadContext can return saved WOW64 startup state',
                'timeout_seconds': min(15, remaining)}
    try:
        result = ctx.run('game-hang-windows', ['/usr/bin/env', '--chdir=' + str(diagnostic.runtime),
            diagnostic.args.wine, base.windows_path(executable), '--runtime-dir',
            base.windows_path(diagnostic.runtime)], timeout=min(15, remaining), env=diagnostic.wine_env,
            cleanup=True, check=False)
        metadata['exit_code'] = result['exit_code']
    except Exception as exc:
        metadata.update(error(exc))
    raw = None
    if len(ctx.children) > before:
        child = ctx.children[before]
        raw = base.redact(child.text(), ctx.secrets)
        encoded = raw.encode()
        metadata.update(output_bytes=len(encoded), output_overflow=child.overflow,
                        output_capture_closed=not child.reader.is_alive(), forced_stop=child.forced_stop,
                        truncated=len(encoded) > WINDOWS_LIMIT)
        if len(encoded) > WINDOWS_LIMIT:
            raw = encoded[:WINDOWS_LIMIT].decode('utf-8', errors='ignore')
        records = []
        for line in raw.splitlines():
            try:
                value = json.loads(line)
                if isinstance(value, dict) and value.get('kind') == 'complete':
                    records.append(value)
            except ValueError:
                pass
        metadata['completion'] = records[0] if len(records) == 1 else None
        complete = records[0] if len(records) == 1 else {}
        metadata['available'] = (metadata.get('exit_code') == 0 and len(records) == 1
            and not child.overflow and not child.forced_stop and not metadata['truncated']
            and complete.get('format') == 1 and complete.get('truncated') is False
            and complete.get('errors') == 0
            and type(complete.get('processes')) is int and 0 < complete['processes'] <= 8
            and type(complete.get('threads')) is int and 0 < complete['threads'] <= 128)
    return metadata, raw


def capture(diagnostic, child=None):
    """Called once before the failed query is stopped, or before service cleanup."""
    if diagnostic.game.get('hang_capture') is not None:
        return
    ctx = diagnostic.ctx
    if ctx.cancelled():
        diagnostic.game['hang_capture'] = {'attempted': False, 'omitted': 'cancellation prioritizes owned cleanup'}
        return
    started = time.monotonic()
    deadline = started + OBSERVATION_SECONDS
    summary = {'attempted': True, 'started_utc': base.utc(), 'before_service_cleanup': True,
               'before_failed_query_stop': child is not None,
               'trigger_label': child.label if child else None,
               'trigger_alive': child.process.poll() is None if child else None}
    diagnostic.game['hang_capture'] = summary  # Re-entry or final fallback never takes a later substitute.
    snapshot = {'format': 1, **summary, 'deadline_seconds': OBSERVATION_SECONDS,
                'failure_observation': getattr(child, 'failure_observation', None),
                'services': [{'label': service.label, 'pid': service.process.pid,
                              'alive': service.process.poll() is None, 'forced_stop': service.forced_stop}
                             for service in diagnostic.services]}
    ctx.event('stage', status='running', message='Capturing bounded game hang evidence before owned cleanup')
    root = diagnostic.args.state / 'game-hang-captures'
    base.require(not root.exists(), 'Refusing stale game hang evidence')
    root.mkdir(mode=0o700)
    files = {}
    diagnostic.game['hang_capture_files'] = files

    def write(name, text, limit):
        text = base.redact(text, ctx.secrets)
        payload = text.encode()
        base.require(len(payload) <= limit, 'Game hang evidence exceeds export bound')
        base.private_write(root / name, text)
        files[name] = {'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}

    try:
        # The database observation happens before attaching the Windows observer.
        snapshot['dispatch_before'] = capture_dispatch(diagnostic)
        try:
            snapshot['postgres'] = capture_postgres(diagnostic, deadline)
        except Exception as exc:
            snapshot['postgres'] = error(exc)
        snapshot['linux'] = capture_processes(diagnostic, min(deadline, time.monotonic() + 6))
        try:
            metadata, output = capture_windows(diagnostic, deadline)
            snapshot['windows'] = metadata
            if output is not None:
                write('windows-contexts.jsonl', output, WINDOWS_LIMIT)
        except Exception as exc:
            snapshot['windows'] = error(exc)
        snapshot['dispatch_after'] = capture_dispatch(diagnostic, snapshot['dispatch_before']['phases'])
        active = snapshot['dispatch_after']['active_phase']
        before_dispatch = snapshot['dispatch_before']['phases'].get(active, {})
        after_dispatch = snapshot['dispatch_after']['phases'].get(active, {})
        if before_dispatch.get('available') and after_dispatch.get('available'):
            summary.update(dispatch_stage_before=before_dispatch['stage'],
                           dispatch_stage_after=after_dispatch['stage'],
                           dispatch_sequence_advanced=after_dispatch['sequence'] > before_dispatch['sequence'],
                           dispatch_loop_advanced=after_dispatch['loop_count'] > before_dispatch['loop_count'])
        snapshot.update(finished_utc=base.utc(), elapsed_seconds=round(time.monotonic() - started, 3),
                        trigger_alive_after=child.process.poll() is None if child else None)
        write('snapshot.json', json.dumps(snapshot, indent=2) + '\n', SNAPSHOT_LIMIT)
        summary.update(snapshot_written=True, elapsed_seconds=snapshot['elapsed_seconds'],
                       windows_contexts_available=snapshot['windows'].get('available') is True)
    except Exception as exc:
        summary['inspection_failure'] = base.redact(str(exc), ctx.secrets)
        raise
    finally:
        manifest = {'format': 1, 'scope': 'bounded failure-only observations before owned service cleanup',
                    'snapshot_byte_limit': SNAPSHOT_LIMIT, 'windows_byte_limit': WINDOWS_LIMIT,
                    'files': dict(files), 'summary': summary}
        write('manifest.json', json.dumps(manifest, indent=2) + '\n', 64 * 1024)
