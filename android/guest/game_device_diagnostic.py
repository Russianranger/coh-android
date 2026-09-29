#!/usr/bin/env python3
"""Run the accepted Atlas proof against a completed private Android import.

The accepted orchestration remains in game_diagnostic.py. This adapter validates
the separate immutable inventory and copies the imported generation into a new
writable session before the original eighteen stages run. Android execution is
attested by the native application, never by a guest command-line flag.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import game_diagnostic as game

base, dbserver, require = game.base, game.dbserver, game.require
SOURCE_COMMIT = '0b75ade0c801735e10c5798f641948a45cc50488'
DATA_COMMIT = 'd51533ec8e6a9cf726b9214968077a05fdcf19f3'
GAME_COMMIT = 'ac4c1f7978be444a893f65f5177641191861d42f'
BASE_COMMIT = '9dc58f62c58dc4fc5c01288071429bf2aa06d2f4'
BASE_MANIFEST_SHA256 = 'fba5afaeb8ceaa4fb113102e436f3677d957a1c09d1d20f543cca630979d4203'
PACKAGE_SHA256 = 'ebfdbbab3984627f7c39220f42a9c3e67b78ffe555aa742621a7a1450731fb2a'
PACKAGE_RUN_ID = 36510836956
MAP_PROGRESS_PROFILE = 'dispatch_progress_v1'
MAP_PROGRESS_RUN_ID = 36630872719
MAP_PROGRESS_COMMIT = '003b07bcd98cb100c1505c15670c07d11a240c8f'
MAP_PROGRESS_PACKAGE_SHA256 = 'ef1e5b1aa7cad69f2e25d286cc579531c86417d3f7f1a5de86843a350f4024cd'
MAP_PROGRESS_PRODUCER = {'repository_commit': MAP_PROGRESS_COMMIT,
    'manifest_sha256': 'b8b79639fbb180fd5f039c6d03f4f5f95d0cc4df7fd7db9b21779fb008c731e1',
    'mapserver_sha256': '52f85c9e2cccfe88eb92f0a2c379a45b14eb997339ce902ed7ba5d470f3690fb'}
SCHEMA_SHA256 = 'b89136892e69ceb39db640613d3f8a34abf2ef8e75e947f4034728b935938b92'
DATA_MANIFEST_SHA256 = 'b367cc35d3f3826d9988ffa5dadb0a240ffc0967f0d248586e54d8ac545615f4'
DATA_MANIFEST_BYTES = 32184737
DATA_COUNT = 173011
DATA_BYTES = 2977730517
GUEST_FILES = ('game_diagnostic.py', 'dbserver_diagnostic.py', 'game_evidence.py',
               'game_hang_evidence.py', 'game_device_diagnostic.py', 'game_map_progress.py')
COPY_BLOCK = 1024 * 1024
RUNTIME_RESERVE_BYTES = 2 * 1024**3
DBSERVER_STARTUP_SECONDS = 600
DBSERVER_STARTUP_WAITS = {
    'DbServer schema and local listener': 'schema_and_listener',
    'DbServer main-thread dispatch publication': 'positive_main_loop',
}


def checked_file(path, limit):
    path = Path(path)
    require(path.is_absolute(), 'Input path must be absolute')
    current = Path(path.anchor)
    for part in path.parts[1:]:
        require(part not in ('.', '..'), 'Unsafe input path')
        current /= part
        require(not current.is_symlink(), 'Linked input refused')
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= limit,
            'Missing, nonregular or oversized input: ' + path.name)
    return path


def pinned_json(path, expected, limit):
    path = checked_file(path, limit)
    require(base.file_hash(path) == expected, 'Accepted input digest differs: ' + path.name)
    return dbserver.load_json(path, limit)


def read_properties(path, limit):
    raw = checked_file(path, limit).read_bytes()
    try:
        lines = raw.decode('ascii').splitlines()
    except UnicodeDecodeError as exc:
        raise base.DiagnosticError('Content properties must be ASCII') from exc
    require(raw.endswith(b'\n'), 'Incomplete content properties')
    properties = {}
    for line in lines:
        key, separator, value = line.partition('=')
        require(separator and key not in properties and re.fullmatch(r'[a-z0-9.]+', key)
                and value and all(32 <= ord(char) < 127 for char in value)
                and '\\' not in value, 'Duplicate or malformed content properties')
        properties[key] = value
    return properties, hashlib.sha256(raw).hexdigest()


def import_contract(path, repository_commit):
    properties, digest = read_properties(path, 16384)
    require(all(properties.get(name) == value for name, value in {
        'format': '1', 'source.commit': SOURCE_COMMIT, 'data.commit': DATA_COMMIT,
        'repository.commit': repository_commit, 'total.count': str(DATA_COUNT),
        'total.bytes': str(DATA_BYTES),
        'asset.archive.sha256': '28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07',
        'asset.archive.bytes': '615541018',
        'asset.manifest.sha256': 'cf96742b1b65306356df69d065fcfb5bda0986ec8700d47ae1422452a1c0db7f',
    }.items()), 'APK import content or candidate repository contract differs')
    return digest


def import_receipt(generation, contract_sha256):
    """Accept only the exact four-field receipt written by AtlasAssetImporter."""
    require(not generation.is_symlink() and generation.is_dir(), 'Invalid imported generation')
    path = checked_file(generation / 'complete.properties', 4096)
    properties, digest = read_properties(path, 4096)
    require(set(properties) == {'generation', 'contract.sha256', 'count', 'bytes'}
            and re.fullmatch(r'generation-[0-9a-f]{32}', properties['generation'])
            and properties['generation'] == generation.name
            and properties['contract.sha256'] == contract_sha256
            and properties['count'] == str(DATA_COUNT) and properties['bytes'] == str(DATA_BYTES),
            'Imported generation identity or content contract differs')
    require(not (generation / 'data').is_symlink() and (generation / 'data').is_dir(),
            'Imported generation data is missing or linked')
    return {'generation': properties['generation'], 'contract_sha256': properties['contract.sha256'],
            'receipt_sha256': digest, 'file_count': DATA_COUNT,
            'total_bytes': DATA_BYTES, 'private_copy_verified': False,
            'source_generation_unchanged': False}


def selected_package_metadata(profile=None):
    require(profile in (None, MAP_PROGRESS_PROFILE), 'Unknown Android MapServer progress profile')
    value = {'selected_package_run_id': PACKAGE_RUN_ID,
             'selected_package_repository_commit': GAME_COMMIT,
             'selected_package_manifest_sha256': PACKAGE_SHA256}
    if profile is not None:
        value.update(selected_package_run_id=MAP_PROGRESS_RUN_ID,
                     selected_package_repository_commit=MAP_PROGRESS_COMMIT,
                     selected_package_manifest_sha256=MAP_PROGRESS_PACKAGE_SHA256,
                     mapserver_progress_profile=profile, mapserver_progress_producer=dict(MAP_PROGRESS_PRODUCER))
    return value


def candidate_metadata(assets):
    accepted = pinned_json(assets / 'accepted-runtime-manifest.json', BASE_MANIFEST_SHA256, 256 * 1024)
    current = dbserver.load_json(checked_file(assets / 'runtime-manifest.json', 1024 * 1024), 1024 * 1024)
    require(accepted.get('format') == current.get('format') == 1
            and accepted.get('repository_commit') == BASE_COMMIT
            and dbserver.COMMIT.fullmatch(current.get('repository_commit', '')),
            'Accepted base or candidate runtime identity differs')
    original_files, files = accepted.get('files', {}), current.get('files', {})
    require(isinstance(original_files, dict) and len(original_files) == 12 and isinstance(files, dict)
            and all(dbserver.exact_contract(files.get(name), record) for name, record in original_files.items()),
            'Candidate substituted accepted base runtime inputs')
    for name in set(accepted) - {'files', 'repository_commit', 'scope'}:
        require(dbserver.exact_contract(current.get(name), accepted[name]),
                'Candidate changed accepted base runtime contract: ' + name)
    bundle = current.get('atlas_device_bundle', {})
    selected = selected_package_metadata(bundle.get('mapserver_progress_profile'))
    expected = {key.removeprefix('selected_'): value for key, value in selected.items()}
    require(all(dbserver.exact_contract(bundle.get(key), value) for key, value in expected.items())
            and ('mapserver_progress_producer' in bundle) == ('mapserver_progress_producer' in selected)
            and isinstance(bundle.get('guest_scripts'), list)
            and len(bundle['guest_scripts']) == len(GUEST_FILES) and set(bundle['guest_scripts']) == set(GUEST_FILES),
            'Android selected package or guest inventory contract differs')
    guests = {}
    for name in GUEST_FILES:
        path = checked_file(assets / name, 256 * 1024)
        actual = base.file_hash(path)
        record = files.get(name, {})
        expected = record.get('sha256') if isinstance(record, dict) else record
        require(actual == expected, 'Candidate guest source differs: ' + name)
        guests[name] = actual
    return {'candidate_repository_commit': current['repository_commit'],
            'accepted_runtime_manifest_sha256': BASE_MANIFEST_SHA256,
            'accepted_game_repository_commit': GAME_COMMIT, 'guest_source_sha256': guests, **selected}


def validate_selected_package(package, adapter):
    profile = adapter.get('mapserver_progress_profile')
    selected = selected_package_metadata(profile)
    require(all(dbserver.exact_contract(adapter.get(key), value) for key, value in selected.items()),
            'Android selected package provenance differs')
    require(package.get('repository_commit') == selected['selected_package_repository_commit']
            and package.get('source_commit') == SOURCE_COMMIT and package.get('data_commit') == DATA_COMMIT
            and package.get('dbserver_profile') == package.get('game_listener_profile') == 'loopback'
            and package.get('postgresql_persistence_fixture') is False
            and package.get('mapserver_progress_profile') == profile,
            'Android Atlas requires the selected qualified loopback game package')
    if profile is not None:
        contract = game.mapserver_progress_contract(package)
        require(dbserver.exact_contract(contract['producer'], selected['mapserver_progress_producer']),
                'Android MapServer progress producer differs from qualified donor')
    else:
        require('mapserver_progress' not in package.get('inputs', {}), 'Unexpected Android progress donor')


class ManifestDirectory:
    """Read-only adapter for the original constructor's one manifest lookup.

    The original constructor reads and fingerprints game-data-manifest.json;
    prepare_runtime below uses the actual imported generation separately.
    Keeping this narrow rejects any future unreviewed data-directory use.
    """
    def __init__(self, manifest):
        self.manifest = manifest

    def __truediv__(self, name):
        require(name == 'game-data-manifest.json', 'Unexpected imported-data adapter lookup')
        return self.manifest


class DeviceWineProcessOwner(base.WineProcessOwner):
    """Handle a worker exiting during a private-token ownership read.

    A zombie leader can outlive its workers. Android may deny a worker's
    namespace/environment read or return ESRCH while that worker is exiting,
    before its proc directory disappears. Only verified termination or a fresh
    complete ownership check resolves that error; a persistently unreadable live task
    still fails closed. Signaling remains the accepted identity/pidfd policy.
    """
    PERMISSION_ATTEMPTS = 3
    PERMISSION_PAUSE = .025
    OBSERVATION_LIMIT = 16

    def __init__(self, context, proc_root=Path('/proc')):
        super().__init__(context, proc_root)
        self.receipt.update(permission_read_retries=0, worker_exit_rechecks=0,
                            permission_observations=[], permission_observations_omitted=0,
                            proc_read_retries=0, proc_read_observations=[],
                            proc_read_observations_omitted=0, last_inspection_failure=None)

    def observe_proc(self, observation):
        if len(self.receipt['proc_read_observations']) < self.OBSERVATION_LIMIT:
            self.receipt['proc_read_observations'] = [*self.receipt['proc_read_observations'], observation]
        else:
            self.receipt['proc_read_observations_omitted'] += 1
        return observation

    def proc_read(self, path, operation, reader, task_disappearance=False):
        try:
            return reader()
        except (OSError, ValueError, KeyError, IndexError) as exc:
            parts = path.relative_to(self.proc_root).parts
            observation = {'operation': operation, 'error_type': type(exc).__name__,
                'errno': getattr(exc, 'errno', None),
                'group_pid': int(parts[0]) if parts and parts[0].isdecimal() else None,
                'worker_tid': int(parts[2]) if len(parts) == 3 and parts[1] == 'task'
                    and parts[2].isdecimal() else None, 'resolution': 'unresolved'}
            exc.ownership_observation = observation
            # proc status/stat read callbacks return ESRCH when get_pid_task no
            # longer resolves the task, including an FD opened before exit.
            # Environment/ns ESRCH has different semantics (a missing mm can
            # leave live workers), so it must take the identity recheck below.
            if task_disappearance and isinstance(exc, ProcessLookupError):
                observation['resolution'] = 'task_disappeared'
                self.observe_proc(observation)
                raise FileNotFoundError(exc.errno, 'Proc task disappeared') from exc
            raise

    def status(self, path):
        return self.proc_read(path, 'status', lambda: super(DeviceWineProcessOwner, self).status(path), True)

    def process_stat(self, path):
        return self.proc_read(path, 'stat', lambda: super(DeviceWineProcessOwner, self).process_stat(path), True)

    def has_token(self, path):
        return self.proc_read(path, 'environment', lambda: super(DeviceWineProcessOwner, self).has_token(path))

    def pid_namespace(self, path):
        return self.proc_read(path, 'pid_namespace', lambda: os.readlink(path / 'ns/pid'))

    def live_tasks(self, path, deadline=None):
        try:
            yield from super().live_tasks(path, deadline)
        except (OSError, ValueError, KeyError, IndexError) as exc:
            observation = getattr(exc, 'ownership_observation', None) or {
                'operation': 'task_inspection', 'group_pid': int(path.name) if path.name.isdecimal() else None,
                'error_type': type(exc).__name__, 'errno': getattr(exc, 'errno', None),
                'resolution': 'unresolved'}
            # Directory enumeration ESRCH does not prove every worker exited.
            # signal_owned also invokes this iterator outside inspect(), so its
            # unreadable error must not reach the signal-syscall ESRCH handler.
            self.terminal_failure(exc, observation)
            if isinstance(exc, ProcessLookupError):
                self.raise_unreadable(exc, observation)
            raise

    def count_failure(self, error):
        if not getattr(error, 'ownership_failure_counted', False):
            self.receipt['inspection_failures'] += 1
            error.ownership_failure_counted = True

    def terminal_failure(self, error, fallback=None):
        observation = getattr(error, 'ownership_observation', None) or fallback
        if observation is None:
            observation = {'operation': 'group_inspection', 'error_type': type(error).__name__,
                           'errno': getattr(error, 'errno', None), 'resolution': 'unresolved'}
        # Reserve a terminal record even when benign exits exhausted the bounded
        # observation list. Replacement also preserves earlier restart receipts.
        self.receipt['last_inspection_failure'] = dict(observation)

    def raise_unreadable(self, error, observation, verified_recheck_failed=False):
        error.ownership_observation = observation
        self.terminal_failure(error)
        if isinstance(error, ProcessLookupError) or verified_recheck_failed:
            # signal_owned legitimately catches ESRCH from the signal syscall;
            # an unverified *live* proc read must never reach that catch.
            failure = base.DiagnosticError('Cannot verify live Wine ownership after proc read failure')
            failure.ownership_observation = observation
            self.count_failure(failure)
            raise failure from error
        raise error

    def failed_recheck(self, observation, error, operation):
        detail = getattr(error, 'ownership_observation', {})
        observation.update(resolution='identity_recheck_failed',
            recheck_operation=detail.get('operation', operation),
            recheck_error_type=type(error).__name__, recheck_errno=getattr(error, 'errno', None))
        error.ownership_observation = observation
        # This task's identity was already known. A failed recheck cannot use
        # scan's initial unknown/foreign-UID permission exception. Count even
        # EIO/parse failures here: signal_owned rechecks outside the base scan.
        if isinstance(error, base.DiagnosticError):
            self.terminal_failure(error)
            self.count_failure(error)
            raise error
        self.raise_unreadable(error, observation, verified_recheck_failed=True)

    def observe_permission(self, group, worker, operation, error, attempt):
        observation = {'group_pid': group['pid'], 'group_starttime': group['starttime'],
            'worker_tid': worker['pid'], 'worker_starttime': worker['starttime'],
            'operation': operation, 'errno': error.errno, 'error_type': type(error).__name__, 'attempt': attempt,
            'worker_state_before': worker['state'], 'resolution': 'unresolved'}
        if isinstance(error, ProcessLookupError):
            return self.observe_proc(observation)
        if len(self.receipt['permission_observations']) < self.OBSERVATION_LIMIT:
            # The accepted restart captures dict(receipt). Give each subsequent
            # scan a new list so final cleanup cannot amend that earlier proof.
            self.receipt['permission_observations'] = [*self.receipt['permission_observations'], observation]
        else:
            self.receipt['permission_observations_omitted'] += 1
        return observation

    def inspect(self, proc_pid, deadline=None):
        before = len(self.receipt['permission_observations']) + self.receipt['permission_observations_omitted']
        try:
            return self.inspect_group(proc_pid, deadline)
        except PermissionError as exc:
            recorded = len(self.receipt['permission_observations']) + self.receipt['permission_observations_omitted']
            try:
                known_same_uid = proc_pid not in self.excluded and self.status(
                    self.proc_root / str(proc_pid))['uid'] == self.real_uid
            except (OSError, ValueError, KeyError, IndexError):
                known_same_uid = False
            if recorded == before and known_same_uid:
                # This is outside the worker read covered below. Record its
                # identity when readable, but do not infer ownership or retry
                # an unknown denied operation. The base scanner still refuses it.
                try:
                    current = self.process_stat(self.proc_root / str(proc_pid))
                except (OSError, ValueError, KeyError, IndexError):
                    current = {'pid': proc_pid, 'starttime': None, 'state': 'unavailable'}
                observation = self.observe_permission(current, current, 'group_inspection', exc, 1)
                observation['resolution'] = 'unresolved_group_permission_denied'
                self.terminal_failure(exc, observation)
            elif known_same_uid:
                self.terminal_failure(exc)
            raise
        except (OSError, ValueError, KeyError, IndexError, base.DiagnosticError) as exc:
            observation = getattr(exc, 'ownership_observation', None) or {
                'group_pid': proc_pid, 'operation': 'group_inspection',
                'error_type': type(exc).__name__, 'errno': getattr(exc, 'errno', None),
                'resolution': 'unresolved'}
            self.terminal_failure(exc, observation)
            if isinstance(exc, ProcessLookupError):
                self.raise_unreadable(exc, observation)
            if isinstance(exc, base.DiagnosticError):
                # The accepted scan counts OSError/parse failures itself, but
                # not a failed identity proof expressed as DiagnosticError.
                self.count_failure(exc)
            raise

    def inspect_group(self, proc_pid, deadline):
        # Same accepted ownership policy; only env/ns ESRCH joins the existing
        # exact-leader transition recheck instead of escaping as task absence.
        path = self.proc_root / str(proc_pid)
        try:
            status = self.status(path)
        except FileNotFoundError:
            return None
        if status['uid'] != self.real_uid or proc_pid in self.excluded:
            return None
        if not self.direct_pid_view and len(status['namespace_pids']) != self.namespace_depth:
            return None
        try:
            identity = self.process_stat(path)
            require(identity['pid'] == proc_pid == status['pid'], 'Wine cleanup PID view changed')
            if identity['starttime'] < self.diagnostic_starttime:
                return None
            if identity['state'] == 'Z':
                if not self.inspect_dead_leader(path, identity, deadline):
                    return None
            else:
                unreadable, observation = None, None
                operation = 'group_pid_namespace'
                try:
                    if not self.direct_pid_view and self.pid_namespace(path) != self.namespace:
                        return None
                    operation = 'group_environment'
                    token_present = self.has_token(path)
                except (PermissionError, ProcessLookupError) as exc:
                    unreadable, token_present = exc, False
                    if isinstance(exc, ProcessLookupError):
                        observation = self.observe_permission(identity, identity, operation, exc, 1)
                        exc.ownership_observation = observation
                if not token_present:
                    try:
                        changed = self.process_stat(path)
                        require(changed['pid'] == identity['pid'] and changed['starttime'] == identity['starttime'],
                                'Wine cleanup group identity changed')
                    except FileNotFoundError:
                        if observation is not None:
                            observation['resolution'] = 'verified_disappearance'
                        return None
                    except Exception as exc:
                        if observation is not None:
                            self.failed_recheck(observation, exc, 'group_identity_after_read')
                        raise
                    if changed['state'] != 'Z':
                        if unreadable is not None:
                            if observation is not None:
                                observation['resolution'] = 'persistent_live_read_failure'
                                self.raise_unreadable(unreadable, observation)
                            raise unreadable
                        return None
                    self.receipt['leader_exit_retries'] += 1
                    if observation is not None:
                        observation['resolution'] = 'same_leader_became_zombie_check_workers'
                    if not self.inspect_dead_leader(path, changed, deadline):
                        return None
        except FileNotFoundError:
            return None
        pid = proc_pid if self.direct_pid_view else status['namespace_pids'][-1]
        require(pid > 0 and pid != os.getpid(), 'Invalid owned Wine PID')
        return {'proc_pid': proc_pid, 'pid': pid, 'starttime': identity['starttime']}

    def inspect_dead_leader(self, path, identity, deadline):
        for task, worker in self.live_tasks(path, deadline):
            group_key = (identity['pid'], identity['starttime'])
            require(len(self.dead_leaders) < 4096 or group_key in self.dead_leaders,
                    'Wine ownership group count exceeds bound')
            self.dead_leaders.add(group_key)
            self.receipt['dead_leaders_with_live_tasks'] = len(self.dead_leaders)
            previous_denial = None
            for attempt in range(1, self.PERMISSION_ATTEMPTS + 1):
                operation = 'worker_status'
                try:
                    require(deadline is None or time.monotonic() < deadline,
                            'Wine ownership task inspection timed out')
                    status = self.status(task)
                    require(status['uid'] == self.real_uid and status['tgid'] == identity['pid']
                            and status['pid'] == worker['pid'], 'Cannot verify Wine worker group membership')
                    if not self.direct_pid_view:
                        operation = 'worker_pid_namespace'
                        if (len(status['namespace_pids']) != self.namespace_depth
                                or self.pid_namespace(task) != self.namespace):
                            return False
                    operation = 'worker_environment'
                    token_present = self.has_token(task)
                    operation = 'worker_identity_after_read'
                    current_worker = self.process_stat(task)
                    require(current_worker['pid'] == worker['pid']
                            and current_worker['starttime'] == worker['starttime'],
                            'Wine cleanup worker identity changed')
                    operation = 'group_identity_after_read'
                    current_group = self.process_stat(path)
                    require(current_group['pid'] == identity['pid']
                            and current_group['starttime'] == identity['starttime'],
                            'Wine cleanup group identity changed')
                    if previous_denial is not None:
                        previous_denial.update(resolution='complete_ownership_read',
                            worker_state_after=current_worker['state'], token_matched=token_present)
                    if not token_present or current_worker['state'] == 'Z':
                        break
                    worker_key = (*group_key, worker['pid'], worker['starttime'])
                    require(len(self.owned_workers) < 4096 or worker_key in self.owned_workers,
                            'Wine ownership worker count exceeds bound')
                    self.owned_workers.add(worker_key)
                    self.receipt['owned_live_workers'] = len(self.owned_workers)
                    return True
                except FileNotFoundError:
                    if previous_denial is not None:
                        previous_denial['resolution'] = 'verified_disappearance'
                        self.receipt['worker_exit_rechecks'] += 1
                    break
                except (PermissionError, ProcessLookupError) as exc:
                    observation = self.observe_permission(identity, worker, operation, exc, attempt)
                    exc.ownership_observation = observation
                    try:
                        recheck_operation = 'group_identity_after_read'
                        current_group = self.process_stat(path)
                        require(current_group['pid'] == identity['pid']
                                and current_group['starttime'] == identity['starttime'],
                                'Wine cleanup group identity changed during permission recheck')
                        recheck_operation = 'worker_identity_after_read'
                        current_worker = self.process_stat(task)
                        require(current_worker['pid'] == worker['pid']
                                and current_worker['starttime'] == worker['starttime'],
                                'Wine cleanup worker identity changed during permission recheck')
                    except FileNotFoundError:
                        observation['resolution'] = 'verified_disappearance'
                        self.receipt['worker_exit_rechecks'] += 1
                        break
                    except Exception as recheck_error:
                        self.failed_recheck(observation, recheck_error, recheck_operation)
                        raise
                    observation['worker_state_after'] = current_worker['state']
                    if current_worker['state'] == 'Z':
                        observation['resolution'] = 'same_worker_became_zombie'
                        self.receipt['worker_exit_rechecks'] += 1
                        break
                    if attempt == self.PERMISSION_ATTEMPTS or (deadline is not None
                            and time.monotonic() + self.PERMISSION_PAUSE >= deadline):
                        observation['resolution'] = ('persistent_live_permission_denied'
                            if isinstance(exc, PermissionError) else 'persistent_live_read_failure')
                        self.raise_unreadable(exc, observation)
                    observation['resolution'] = 'retry_same_live_worker'
                    previous_denial = observation
                    self.receipt['permission_read_retries' if isinstance(exc, PermissionError)
                                 else 'proc_read_retries'] += 1
                    time.sleep(self.PERMISSION_PAUSE)
                except (OSError, ValueError, KeyError, IndexError, base.DiagnosticError) as exc:
                    if previous_denial is not None:
                        self.failed_recheck(previous_denial, exc, operation)
                    elif not hasattr(exc, 'ownership_observation'):
                        exc.ownership_observation = {'group_pid': identity['pid'],
                            'group_starttime': identity['starttime'], 'worker_tid': worker['pid'],
                            'worker_starttime': worker['starttime'], 'operation': operation,
                            'error_type': type(exc).__name__, 'errno': getattr(exc, 'errno', None),
                            'resolution': 'unresolved'}
                    raise
        return False


class WineMemorySampler:
    """Bounded read-only samples; a missing measurement cannot fail gameplay proof.

    This deliberately excludes PostgreSQL, Python, Java and app memory. RSS is
    summed across token-owned Wine/FEX processes and can double-count shared
    pages. Its largest sample is not a measured instantaneous peak or PSS.
    Sampling runs on the guest loop, with no worker to delay Stop or cleanup.
    """
    def __init__(self, diagnostic):
        self.diagnostic = diagnostic
        self.next_sample = 0
        self.scanner = object.__new__(type(diagnostic.wine_owner))
        self.scanner.__dict__.update(diagnostic.wine_owner.__dict__)
        self.scanner.initialized = False
        self.scanner.receipt = copy.deepcopy(diagnostic.wine_owner.receipt)
        self.scanner.dead_leaders, self.scanner.owned_workers = set(), set()
        self.report = {'scope': 'run_token_owned_Wine_FEX_processes_only',
            'measurement': 'sampled_sum_of_process_VmRSS_kibibytes', 'minimum_interval_seconds': 5,
            'inspection_budget_seconds': 1, 'excludes': ['PostgreSQL', 'Python', 'Java', 'Android app'],
            'shared_pages_may_be_counted_more_than_once': True, 'instantaneous_peak_measured': False,
            'pss_measured': False, 'successful_samples': 0, 'unavailable_samples': 0,
            'maximum_sampled_rss_kib': None, 'samples': []}
        diagnostic.ctx.report['memory_observation'] = self.report

    def sample(self):
        now = time.monotonic()
        if not self.diagnostic.wine_started or now < self.next_sample:
            return
        self.next_sample = now + 5
        try:
            deadline = now + 1
            owned = self.scanner.scan(deadline)
            total, observed = 0, 0
            for identity in owned:
                require(time.monotonic() < deadline, 'Resource sample exceeded inspection budget')
                path = self.scanner.proc_root / str(identity['proc_pid'])
                try:
                    before = self.scanner.process_stat(path)
                    status = (path / 'status').read_text()
                    after = self.scanner.process_stat(path)
                except FileNotFoundError:
                    continue
                require(before['pid'] == after['pid'] == identity['proc_pid']
                        and before['starttime'] == after['starttime'] == identity['starttime'],
                        'Resource sample process identity changed')
                if before['state'] == 'Z' or after['state'] == 'Z':
                    continue
                values = re.findall(r'^VmRSS:\s+(\d+)\s+kB$', status, re.MULTILINE)
                require(len(values) == 1, 'Owned process RSS is unavailable')
                total += int(values[0])
                observed += 1
            require(observed > 0, 'No owned Wine RSS was observable')
            require(len(self.report['samples']) < 2048, 'Resource sample count exceeded bound')
            self.report['samples'].append({'stage': self.diagnostic.ctx.stage_name,
                                          'owned_processes': observed, 'rss_kib': total})
            self.report['successful_samples'] += 1
            self.report['maximum_sampled_rss_kib'] = max(total, self.report['maximum_sampled_rss_kib'] or 0)
        except Exception as exc:
            self.report['unavailable_samples'] += 1
            self.report['last_unavailable_type'] = type(exc).__name__


class DeviceGameContext(game.GameContext):
    memory_sampler = None

    def check(self):
        super().check()
        if self.memory_sampler is not None:
            self.memory_sampler.sample()


def copy_verified(source, target, record, check):
    """Copy without links, with cancellation between bounded reads and hashes."""
    descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as incoming:
        before = os.fstat(incoming.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and before.st_size == record['bytes'], 'Game input is linked, nonregular or has wrong size')
        total = 0
        with target.open('xb') as output:
            while True:
                check()
                chunk = incoming.read(COPY_BLOCK)
                if not chunk:
                    break
                total += len(chunk)
                require(total <= record['bytes'], 'Game input grew during copy')
                output.write(chunk)
        after = os.fstat(incoming.fileno())
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                and total == record['bytes'], 'Game input changed during copy')
    digest = hashlib.sha256()
    with target.open('rb') as copied:
        while True:
            check()
            chunk = copied.read(COPY_BLOCK)
            if not chunk:
                break
            digest.update(chunk)
    require(digest.hexdigest() == record['sha256'], 'Copied game data hash differs: ' + target.name)


class DeviceGameDiagnostic(game.GameDiagnostic):
    def __init__(self, args, context):
        args.listener_policy = dbserver.listener_policy(args.execution_platform, args.listener_policy)
        context.report['listener_policy'] = args.listener_policy
        adapter = candidate_metadata(args.assets)
        contract_sha256 = import_contract(args.import_contract, adapter['candidate_repository_commit'])
        imported = import_receipt(args.game_data, contract_sha256)
        package = pinned_json(args.game_package / 'game-package.json',
                              adapter['selected_package_manifest_sha256'], 8 * 1024 * 1024)
        pinned_json(args.schema / 'schema-manifest.json', SCHEMA_SHA256, 8 * 1024 * 1024)
        checked_file(args.game_data_manifest, DATA_MANIFEST_BYTES)
        require(args.game_data_manifest.stat().st_size == DATA_MANIFEST_BYTES
                and base.file_hash(args.game_data_manifest) == DATA_MANIFEST_SHA256,
                'Accepted game data manifest differs')
        validate_selected_package(package, adapter)
        if args.android_metadata is not None:
            context.report['android_context_unverified'] = dbserver.load_json(
                checked_file(args.android_metadata, 16384), 16384)
        self.import_generation = args.game_data
        adapted = argparse.Namespace(**vars(args))
        adapted.game_data = ManifestDirectory(args.game_data_manifest)
        super().__init__(adapted, context)
        require(not self.wine_started, 'Device ownership guard must be installed before Wine starts')
        self.wine_owner = DeviceWineProcessOwner(self.ctx, self.wine_owner.proc_root)
        self.wine_env.update(self.wine_owner.environment)
        self.imported = imported
        self.ctx.report['imported_content'] = imported
        self.ctx.report['device_adapter'] = adapter
        self.ctx.memory_sampler = WineMemorySampler(self)

    def map_status(self, label, *, allow_missing=False, timeout=25):
        phase = {'first-ready': 'first', 'restart-ready': 'restart'}.get(label)
        if phase is None or self.package.get('mapserver_progress_profile') != MAP_PROGRESS_PROFILE:
            return super().map_status(label, allow_missing=allow_missing, timeout=timeout)
        # This extra selected-profile guard remains inside the original Atlas
        # startup loop and deadline. A fresh failed read never reuses a cache.
        require(self.map_progress_phase == phase, 'MapServer startup progress phase differs')
        proof = self.game.setdefault('mapserver_startup', {
            'profile': MAP_PROGRESS_PROFILE, 'requires_completed_tick_before_protocol': True, 'phases': {}})
        prior = proof['phases'].get(phase, {})
        attempt = {'attempts': prior.get('attempts', 0) + 1, 'status': 'waiting',
                   'before': self.sample_map_progress('startup-tick-before:' + label, force=True),
                   'after': None, 'protocol': None}
        proof['phases'][phase] = attempt
        before = attempt['before']
        if not before or not before.get('available') or before['tick_completed'] <= 0:
            return {'ready': False}
        sample = super().map_status(label, allow_missing=allow_missing, timeout=timeout)
        attempt['protocol'] = sample
        after = self.sample_map_progress('startup-tick-after:' + label, force=True)
        attempt['after'] = after
        if not after or not after.get('available') or after['tick_completed'] <= 0:
            return {'ready': False}
        game.map_progress_module().compare_records(after, before)
        if game.evidence.map_ready_current(sample):
            attempt['status'] = 'passed'
        return sample

    def start_services(self, label):
        """One DbServer startup budget includes both SQL and dispatch readiness.

        On restart the retained SQL columns already exist when dbNetInit opens
        the listener, before DbServer finishes its ODBC/schema work and minimum
        launcher wait. The accepted positive-loop predicate remains necessary;
        it shares the original 600-second startup budget instead of beginning
        a separate 30-second countdown at that early SQL observation.
        """
        require(getattr(self, '_dbserver_startup', None) is None, 'Nested DbServer service startup refused')
        started = time.monotonic()
        record = {'scope': 'service_startup_entry_through_positive_main_loop',
                  'budget_seconds': DBSERVER_STARTUP_SECONDS, 'milestones': {}}
        self.game.setdefault('device_dbserver_startup', {})[label] = record
        self._dbserver_startup = {
            'started': started, 'deadline': min(self.ctx.deadline, started + DBSERVER_STARTUP_SECONDS),
            'record': record}
        try:
            return super().start_services(label)
        finally:
            self._dbserver_startup = None

    def wait(self, predicate, seconds, label, **options):
        startup = getattr(self, '_dbserver_startup', None)
        if startup is None or label not in DBSERVER_STARTUP_WAITS:
            return super().wait(predicate, seconds, label, **options)
        deadline = startup['deadline']
        remaining = deadline - time.monotonic()
        milestone = {'status': 'waiting'}
        startup['record']['milestones'][DBSERVER_STARTUP_WAITS[label]] = milestone
        def within_startup_budget():
            require(time.monotonic() < deadline, 'Timed out waiting for ' + label + ' within shared DbServer startup budget')
            result = predicate()
            require(time.monotonic() < deadline, 'Timed out waiting for ' + label + ' within shared DbServer startup budget')
            return result
        try:
            require(remaining > 0, 'Timed out waiting for ' + label + ' within shared DbServer startup budget')
            result = super().wait(within_startup_budget, remaining, label, **options)
            milestone['status'] = 'passed'
            return result
        except base.Cancelled:
            milestone['status'] = 'cancelled'
            raise
        except Exception:
            milestone['status'] = 'failed'
            raise
        finally:
            milestone['elapsed_since_startup_seconds'] = round(time.monotonic() - startup['started'], 3)

    def prepare_runtime(self):
        self.ctx.stage('game_private_runtime')
        files = self.data.get('files')
        require(isinstance(files, dict) and len(files) == self.data.get('file_count') == DATA_COUNT
                and self.data.get('total_bytes') == DATA_BYTES, 'Invalid accepted game data inventory')
        minimum_free = DATA_BYTES + DATA_COUNT * 4096 + RUNTIME_RESERVE_BYTES
        require(shutil.disk_usage(self.root).free >= minimum_free,
                'Insufficient private storage for a fresh game copy and runtime reserve')
        self.runtime.mkdir(mode=0o700)
        (self.runtime / 'tools').mkdir(mode=0o700)
        created = {self.runtime, self.runtime / 'tools'}
        names, total = {}, 0
        next_progress = time.monotonic()
        for number, (name, record) in enumerate(files.items(), 1):
            self.ctx.check()
            require(game.safe_path(name).parts[0] == 'data' and name.casefold() not in names,
                    'Unexpected or case-colliding game data path')
            require(isinstance(record, dict) and type(record.get('bytes')) is int and record['bytes'] >= 0
                    and isinstance(record.get('sha256'), str) and dbserver.HEX64.fullmatch(record['sha256']),
                    'Invalid game data digest record')
            total += record['bytes']
            require(total <= DATA_BYTES, 'Game data exceeds accepted byte bound')
            source = game.regular_path(self.import_generation, name)
            target = self.runtime / name
            game.create_private_parents(target.parent, self.runtime, created)
            copy_verified(source, target, record, self.ctx.check)
            names[name.casefold()] = name
            if time.monotonic() >= next_progress:
                self.ctx.event('stage', status='running', message='Staging verified imported game inputs', files=number)
                next_progress = time.monotonic() + 5
        actual = game.inventory_files(self.import_generation, self.ctx.check)
        require(actual == set(files) | {'complete.properties'} and total == DATA_BYTES,
                'Imported game data inventory has extra/missing files or bytes')
        require(import_receipt(self.import_generation, self.imported['contract_sha256']) == self.imported,
                'Imported generation receipt changed')
        for name in self.schema['files']:
            target = self.runtime / names.get(name.casefold(), name)
            game.create_private_parents(target.parent, self.runtime, created)
            shutil.copyfile(self.args.schema / name, target)
        require(len(self.schema['files']) == 62, 'Fixed-input game schema must contain 62 accepted files')
        self.fixed_schema_paths = {names.get(name.casefold(), name) for name in self.schema['files']}
        for name in self.package['files']:
            shutil.copyfile(self.args.game_package / name, self.runtime / name)
        require(not (self.runtime / 'gamedatadir.txt').exists(), 'External game data roots are forbidden')
        self.imported.update(private_copy_verified=True, source_generation_unchanged=True)
        self.ctx.log_root = self.runtime
        self.ctx.passed(input_files=len(files), input_bytes=total, accepted_schema_overlay_files=62)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name, default in (('state', '/state'), ('assets', '/opt/coh'), ('game-package', '/opt/coh-game-package'),
                          ('game-data', '/opt/coh-game-data'), ('schema', '/opt/coh-schema'),
                          ('game-data-manifest', '/opt/coh-game-data-manifest.json'),
                          ('import-contract', '/opt/coh-import-contract.properties'),
                          ('pg-bin', '/opt/coh/pgsql/bin'), ('wine', '/opt/wine/bin/wine'),
                          ('wineserver', '/opt/wine/bin/wineserver'), ('xserver', '/usr/bin/Xtigervnc')):
        parser.add_argument('--' + name, type=Path, default=Path(default))
    parser.add_argument('--timeout-seconds', type=int, default=5400)
    parser.add_argument('--execution-platform', choices=('host', 'android'), required=True)
    parser.add_argument('--listener-policy', choices=('host-default', 'device'))
    parser.add_argument('--android-metadata', type=Path)
    args = parser.parse_args(argv)
    args.client_probe = False
    os.umask(0o077)
    context = DeviceGameContext(args.state, args.timeout_seconds)
    context.report.update(diagnostic_mode='atlas_character_persistence',
        execution_platform_requested=args.execution_platform,
        scope='Private imported Atlas data, managed local servers and diagnostic create/save/restart/exact-name resume on ARM64 Wine/FEX',
        android_execution_validated=False, gameplay_validated=False, android_surface_validated=False,
        hardware_acceleration_validated=False, interactive_rendering_validated=False,
        android_listener_binding_validated=False)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda _sig, _frame: setattr(context, 'cancel_requested', True))
    diagnostic = None
    try:
        require(60 <= args.timeout_seconds <= 7200, 'Timeout must be 60 to 7200 seconds')
        context.check()
        diagnostic = DeviceGameDiagnostic(args, context)
        diagnostic.execute()
        context.report['status'] = 'passed'
    except base.Cancelled as exc:
        context.report.update(status='cancelled', failures=[str(exc)])
    except Exception as exc:
        context.report.update(status='failed', failures=[str(exc)])
    finally:
        # Preserve whether runtimes were ever started before cleanup changes
        # their state. A Stop while copying inputs has nothing to shut down;
        # native acceptance must distinguish that from an unproved shutdown.
        context.report['cleanup_execution'] = {
            'diagnostic_initialized': diagnostic is not None,
            'wine_started': bool(diagnostic is not None and diagnostic.wine_started),
            'postgres_started': any(child.label in ('postgres_first_start', 'postgres_game_restart')
                                    for child in context.children),
            'owned_child_count': len(context.children)}
        if diagnostic is not None:
            if context.report['status'] == 'failed':
                try:
                    game.hang_evidence.capture(diagnostic)
                except Exception as exc:
                    context.report.setdefault('observation_failures', []).append(
                        'Cannot capture pre-cleanup game evidence: ' + str(exc))
            try:
                context.report['failures'].extend(diagnostic.cleanup())
            except Exception as exc:
                context.report['failures'].append('Owned cleanup failed: ' + str(exc))
            for label, export in (('game', diagnostic.export_captures), ('service', diagnostic.export_service_captures)):
                try:
                    export()
                except Exception as exc:
                    context.report['failures'].append('Cannot export bounded ' + label + ' evidence: ' + str(exc))
        # Cleanup can launch its own bounded stop/wait helpers. Bind the final
        # count to every owned child, including helpers whose capture failed.
        context.report['cleanup_execution']['owned_child_count'] = len(context.children)
        context.report['finished_utc'] = base.utc()
        context.report['cleanup_complete'] = all(child.process.poll() is not None and not child.reader.is_alive()
                                                and not child.writer.is_alive() for child in context.children)
        context.report['cleanup'] = diagnostic.cleanup_status if diagnostic else {
            'postgres_graceful': False, 'wine_prefix_stopped': False, 'owned_processes_reaped': False}
        context.report['passed'] = context.report['status'] == 'passed' and not context.report['failures'] \
            and context.report['cleanup_complete'] and all(context.report['cleanup'].values())
        if context.report['status'] == 'passed' and not context.report['passed']:
            context.report['status'] = 'failed'
            context.report['failures'].append('Required owned cleanup was not proved')
        try:
            text = json.dumps(base.redacted_value(context.report, context.secrets), indent=2) + '\n'
            require(len(text.encode()) <= 2 * 1024 * 1024, 'Report exceeded bound')
            base.private_write(args.state / 'latest-report.json', text)
        except Exception as exc:
            context.report.update(status='failed', passed=False)
            context.report['failures'].append('Cannot persist game report: ' + str(exc))
        context.event('result', status=context.report['status'], passed=context.report['passed'],
                      report='/state/latest-report.json', failures=context.report['failures'])
    return 0 if context.report['passed'] else 2 if context.report['status'] == 'cancelled' else 1


if __name__ == '__main__':
    sys.exit(main())
