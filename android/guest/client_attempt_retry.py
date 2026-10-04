"""One early client retry while the current operation still owns live servers.

This does not retain services after Finish/Stop, adopt an earlier operation, or
extend a deadline.  Native exit evidence, closed output pipes and absent windows
must prove the previous client ended before another client can be started.
"""
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import time

import client_startup_diagnostic as startup

base, require = startup.base, startup.require
EXIT_MARKER = 'COH_CLIENT_EXIT_V1 '
MAX_ATTEMPTS = 2
# Leave room for the current client's 128 MiB console and bounded server/log
# evidence within the existing 256 MiB character support archive allowance.
FAILED_CONSOLE_LIMIT = 64 * 1024 * 1024


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def native_exit(output, session):
    """The pinned launcher emits this only after waiting on its actual child."""
    launch = startup.parse_launch(output, session)
    require(launch is not None, 'Early retry lacks the actual native client identity')
    values = [json.loads(line[len(EXIT_MARKER):]) for line in output.splitlines()
              if line.startswith(EXIT_MARKER)]
    require(len(values) == 1, 'Early retry lacks one native client exit receipt')
    value = values[0]
    require(isinstance(value, dict) and set(value) == {'session_id', 'exit_code'}
            and value['session_id'] == session and type(value['exit_code']) is int
            and 0 <= value['exit_code'] < 2**32 and value['exit_code'] != 259,
            'Early retry native exit identity/code differs')
    require('COH_CLIENT_LAUNCHER_TIMEOUT_V1' not in output
            and 'COH_CLIENT_CONSOLE_TRUNCATED_V1' not in output,
            'Timed-out or truncated client cannot be retried')
    return dict(launch, exit_code=value['exit_code'])


def directory_identity(path):
    path = Path(path)
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) and not path.is_symlink(), 'Retry service directory is not owned')
    return {'path': str(path.resolve(strict=True)), 'device': info.st_dev,
            'inode': info.st_ino, 'uid': info.st_uid, 'mode': stat.S_IMODE(info.st_mode)}


def service_identity(owner):
    server = owner.local_server
    processes = {'postgres': owner.pg, 'dbserver': server.process,
                 'atlas': server.map_process, 'display': owner.xserver}
    require(all(child is not None and child.process.poll() is None for child in processes.values()),
            'Early retry requires the still-live current owned native services')
    return {'processes': {name: child.process.pid for name, child in processes.items()},
            'runtime': directory_identity(server.runtime),
            'data': directory_identity(server.runtime / 'data'),
            'client_worktree': directory_identity(owner.work),
            'wine_prefix': directory_identity(owner.wineprefix),
            'profile': directory_identity(server.profile),
            'wine_owner_token_sha256': hashlib.sha256(
                owner.wine_env[base.WineProcessOwner.ENV_KEY].encode()).hexdigest()}


def archive_logs(source, target):
    """Retain bounded tails before clearing this attempt's client log directory."""
    source, target = Path(source), Path(target)
    require(not source.is_symlink() and not target.exists() and not target.is_symlink(),
            'Early retry log archive path is not fresh')
    if not source.exists():
        return {'files': 0, 'bytes': 0}
    require(source.is_dir(), 'Early retry client logs are not a directory')
    count, total, entries = 0, 0, 0
    for current, directories, files in os.walk(source, followlinks=False):
        entries += len(directories) + len(files)
        require(entries <= 4096, 'Early retry log directory exceeded bound')
        for name in directories:
            require(not (Path(current) / name).is_symlink(), 'Linked early retry log directory refused')
        for name in files:
            path = Path(current) / name
            info = path.lstat()
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                    'Nonregular or shared early retry client log refused')
            count += 1
            require(count <= 64, 'Early retry client log count exceeded bound')
            with path.open('rb') as handle:
                handle.seek(max(0, info.st_size - 256 * 1024))
                payload = handle.read(256 * 1024)
            total += len(payload)
            require(total <= 4 * 1024 * 1024, 'Early retry client logs exceeded bound')
            destination = target / path.relative_to(source)
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with destination.open('xb') as handle:
                handle.write(payload)
    return {'files': count, 'bytes': total}


class ClientAttemptRetry:
    def __init__(self, owner, started, deadline):
        self.owner, self.deadline = owner, deadline
        self.enabled = owner.ctx.report.get('diagnostic_mode') == 'actual_character_reopen'
        self.identity = service_identity(owner) if self.enabled else None
        self.attempts = []
        self.started = started
        self.previous_pid = None
        self.record = {'format': 1, 'enabled': self.enabled, 'scope': 'early_startup_same_live_operation',
            'maximum_attempts': MAX_ATTEMPTS, 'original_startup_deadline_monotonic': deadline,
            'original_overall_deadline_monotonic': getattr(owner.ctx, 'deadline', None),
            'deadlines_extended': False, 'reuse_count': 0, 'retained_after_operation': False,
            'full_owned_cleanup_required': True, 'attempts': self.attempts}
        owner.ctx.report['warm_client_retry'] = self.record
        self.begin(owner.client, started)

    def begin(self, child, started):
        require(len(self.attempts) < MAX_ATTEMPTS, 'Early client retry count exceeded bound')
        self.started = started
        attempt = {'attempt': len(self.attempts) + 1, 'attempt_id': secrets.token_hex(16),
            'session_id': self.owner.args.session_id, 'started_monotonic': started,
            'launcher_process_pid': child.process.pid, 'console_byte_watermark': 0,
            'fresh_owned_console_buffer': True, 'client_log_watermark': 'empty_after_registry_and_logs_reset'}
        self.attempts.append(attempt)
        self.record['current_attempt_id'] = attempt['attempt_id']
        self.owner.ctx.event('client_attempt_started', session_id=self.owner.args.session_id,
            attempt=attempt['attempt'], attempt_id=attempt['attempt_id'],
            startup_deadline_monotonic=self.deadline, server_reused=attempt['attempt'] > 1)

    def observe_launch(self, launch):
        if not self.enabled or launch is None:
            return
        pid = launch['pid']
        require(pid != self.previous_pid, 'Retry reused the previous native client PID')
        attempt = self.attempts[-1]
        require(attempt.get('native_client_pid', pid) == pid, 'Current client attempt identity changed')
        attempt['native_client_pid'] = pid

    def prepare(self, ready_at):
        owner, child = self.owner, self.owner.client
        preparation_started = time.monotonic()
        if (not self.enabled or ready_at is not None or len(self.attempts) >= MAX_ATTEMPTS
                or time.monotonic() >= self.deadline):
            return False
        owner.ctx.check()
        require(not owner.ctx.report.get('startup_observed') and not getattr(owner, 'login_announced', False)
                and not getattr(owner, 'connected_announced', False) and not getattr(owner, 'saved_announced', False)
                and owner.local_server.creation_report.get('connected_on_atlas') is False
                and owner.local_server.creation_report.get('native_client_ready_observed') is False
                and owner.local_server.report.get('character_list_sent') is False,
                'Client readiness/login/save evidence forbids an early retry')
        require(child.process.poll() is not None and not child.forced_stop and not child.overflow,
                'Early retry requires the naturally closed current launcher')
        child.reader.join(timeout=.2); child.writer.join(timeout=.2)
        require(not child.reader.is_alive() and not child.writer.is_alive(),
                'Early retry launcher input/output or descendants remain open')
        output = child.text()
        ended = native_exit(output, owner.args.session_id)
        self.observe_launch(ended)
        windows = owner.observer.windows()
        require(not any(startup.current_client_title(row.get('title'), ended) for row in windows),
                'Previous native client window remains during early retry')
        owner.local_server.health()
        require(service_identity(owner) == self.identity, 'Current owned native services changed before retry')
        live = owner.local_server.sample_progress(force=True)
        require(owner.local_server.live_progress(live), 'Atlas completed-tick progress is stale before retry')
        # No input was enabled for this attempt. Require the committed character
        # inventory and all baseline selected rows to remain exactly unchanged.
        require(owner.local_server.inventory() == owner.local_server.baseline,
                'Preserved character inventory changed before early retry')
        rows = owner.local_server.character_rows(owner.local_server.CHARACTER_ID)
        expected = owner.local_server.creation_report['baseline']['table_sha256']
        require({name: digest(value) for name, value in rows.items()} == expected,
                'Preserved character rows changed before early retry')
        attempt = self.attempts[-1]
        name = 'client-attempt-' + str(attempt['attempt'])
        console_path = owner.capture_dir / (name + '-console.log')
        require(not console_path.exists() and not console_path.is_symlink(), 'Retry console archive already exists')
        require(len(child.output) <= FAILED_CONSOLE_LIMIT,
                'Early retry console exceeded its support archive reserve')
        payload = bytes(child.output)
        with console_path.open('xb') as handle:
            handle.write(payload)
        logs = archive_logs(owner.work / 'logs', owner.capture_dir / (name + '-logs'))
        attempt.update(ended_monotonic=time.monotonic(), native_exit=ended,
            native_client_terminated=True, launcher_and_pipes_closed=True, prior_client_window_absent=True,
            console={'path': console_path.name, 'bytes': len(payload),
                     'sha256': hashlib.sha256(payload).hexdigest()}, logs=logs,
            services_unchanged=True, selected_sql_rows_unchanged=True, atlas_progress=live)
        owner.ctx.record(child, refresh=True)
        self.previous_pid = ended['pid']
        owner.reset_client_startup_inputs()
        for key in ('client_launch', 'client_console_observation', 'observed_windows', 'client_windows',
                    'graphics_observation'):
            owner.ctx.report.pop(key, None)
        for key in ('client_process_started', 'renderer_initialized', 'all_data_loaded',
                    'client_main_loop_reached', 'client_window_observed', 'startup_observed'):
            owner.ctx.report[key] = False
        owner.ctx.check()
        require(time.monotonic() < self.deadline, 'Original client startup deadline expired before retry')
        require(service_identity(owner) == self.identity, 'Current native services changed during retry preparation')
        owner.launch_client_attempt(label='actual-coh-client-retry')
        self.begin(owner.client, time.monotonic())
        self.record.update(reuse_count=1, retained_service_identity=self.identity,
            preparation_elapsed_seconds=round(time.monotonic() - preparation_started, 6),
            retained_services_elapsed_seconds={name: round(time.monotonic() - process.started, 6)
                for name, process in {'postgres': owner.pg, 'dbserver': owner.local_server.process,
                                      'atlas': owner.local_server.map_process, 'display': owner.xserver}.items()},
            startup_stages_not_repeated=['postgres_local_login', 'local_dbserver_startup', 'local_atlas_startup'])
        owner.ctx.event('client_retry_started', session_id=owner.args.session_id,
            attempt_id=self.record['current_attempt_id'], previous_client_pid=self.previous_pid,
            original_startup_deadline_monotonic=self.deadline,
            message='Retrying the client with the current Atlas server still running')
        return True
