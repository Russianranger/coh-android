#!/usr/bin/env python3
"""Owned server-only adapter for the native combined application.

The retained server stack is imported, not bundled here. No graphical CoH
client, native character creation or synthetic SQL character is used. Optional
fresh-profile provisioning uses the authentic source TestClient and server save.
"""
import argparse
import contextlib
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import resource
import secrets
import signal
import shutil
import socket
import stat
import sys
import time
import traceback

FORMAT = 1
APP_ID = 'org.coh.nativecombined'
GENERATION = re.compile(r'generation-[0-9a-f]{32}')
SESSION = re.compile(r'[0-9a-f]{32}')
BACKUP_MAX = 512 * 1024 * 1024
base = startup = character = zoning = login = wine_policy = None


class AdmissionError(RuntimeError):
    """A public constant code, never a process output or credential."""


def require(ok, code):
    if not ok:
        raise AdmissionError(code)


def real_private_path(path, *, directory=False, exists=True):
    path = Path(path)
    require(path.is_absolute() and path != Path('/') and '..' not in path.parts,
            'INVALID_PRIVATE_PATH')
    cursor = Path('/')
    for part in path.parts[1:]:
        cursor = cursor / part
        require(not cursor.is_symlink(), 'LINKED_PRIVATE_PATH')
    if exists:
        require(path.is_dir() if directory else path.is_file(), 'MISSING_PRIVATE_INPUT')
    return path


def presentation_endpoint(root, session):
    """Choose one absent endpoint in the existing private runtime directory.

    An interrupted older session may leave a socket inode. Its pathname is
    never reused, probed, removed or treated as proof of a live owned process.
    The retained X server still selects an unused display and validates its
    actual mode-0600 endpoint before any Wine initialization.
    """
    require(type(session) is str and SESSION.fullmatch(session), 'INVALID_RUN_IDENTITY')
    directory = real_private_path(Path(root) / 'runtime', directory=True)
    info = directory.lstat()
    require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700
            and info.st_uid == os.geteuid(), 'INVALID_PRIVATE_DISPLAY_DIRECTORY')
    # Keep room for PRoot's Android backing path as well as the guest path.
    # A 96-bit session digest avoids the fixed legacy endpoint and long UUID
    # suffix; an unexpected collision still fails closed below.
    endpoint = directory / ('v' + hashlib.sha256(session.encode('ascii')).hexdigest()[:24])
    # Linux sockaddr_un.sun_path is 108 bytes including the terminating NUL.
    require(len(os.fsencode(endpoint)) <= 107, 'OWNED_DISPLAY_SOCKET_PATH_TOO_LONG')
    require(not endpoint.exists() and not endpoint.is_symlink(), 'OWNED_DISPLAY_SOCKET_ALREADY_EXISTS')
    return endpoint


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for part in iter(lambda: source.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def backup_identity(path):
    path = real_private_path(path)
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
            and 16 <= before.st_size <= BACKUP_MAX, 'INVALID_LOGICAL_BACKUP')
    with path.open('rb') as source:
        require(source.read(5) == b'PGDMP', 'CUSTOM_LOGICAL_BACKUP_REQUIRED')
    result = {'bytes': before.st_size, 'sha256': digest(path)}
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
            'BACKUP_CHANGED_DURING_VERIFICATION')
    return result


def select_destination(rows, *, empty_map=1):
    """Read-only saved-map admission. Never substitute Atlas for a saved map."""
    require(type(rows) is list and len(rows) <= 64, 'INVALID_CHARACTER_INVENTORY')
    if not rows:
        require(empty_map == 1, 'EMPTY_PROFILE_ATLAS_ONLY')
        return {'map_id': 1, 'map_port': 7001, 'character_count': 0,
                'saved_character_available': False, 'selection_authority': 'explicit_empty_profile_atlas'}
    # One local-development account and character are admitted. The source
    # TestClient chooses its actual name; imported THORHERO is also preserved.
    require(len(rows) == 1, 'ONE_ACCEPTED_CHARACTER_REQUIRED')
    row = rows[0]
    require(type(row) is dict and set(row) == {'containerid', 'authname', 'name',
                'authid', 'mapid', 'staticmapid', 'posx', 'posy', 'posz'}, 'INVALID_CHARACTER_FIELDS')
    require(type(row['containerid']) is int and row['containerid'] == 1
            and row['authname'] == 'COHLOCAL'
            and type(row['name']) is str and re.fullmatch(r'[A-Za-z0-9 _.-]{1,63}', row['name'])
            and type(row['authid']) is int and 0 < row['authid'] <= 0xffffffff,
            'CHARACTER_IDENTITY_OUTSIDE_ACCEPTED_SCOPE')
    target = row['staticmapid']
    require(type(target) is int and target in (1, 5), 'UNSUPPORTED_SAVED_DESTINATION')
    require(row['mapid'] is None or type(row['mapid']) is int and row['mapid'] == target,
            'INCONSISTENT_SAVED_DESTINATION')
    require(all(type(row[k]) in (int, float) and math.isfinite(row[k]) and abs(row[k]) <= 1e6
                for k in ('posx', 'posy', 'posz')), 'INVALID_SAVED_POSITION')
    return {'map_id': target, 'map_port': {1: 7001, 5: 7003}[target],
            'character_count': 1, 'saved_character_available': True,
            'selection_authority': 'preserved_postgresql_ents_staticmapid'}


def ready_document(args, destination, *, assets_sha256, import_receipt_sha256):
    require(SESSION.fullmatch(args.session_id) and GENERATION.fullmatch(args.import_generation),
            'INVALID_RUN_IDENTITY')
    require(re.fullmatch(r'[0-9a-f]{64}', assets_sha256)
            and re.fullmatch(r'[0-9a-f]{64}', import_receipt_sha256), 'INVALID_INPUT_HASH')
    require(destination['map_id'] in (1, 5)
            and destination['map_port'] == {1: 7001, 5: 7003}[destination['map_id']],
            'INVALID_READY_DESTINATION')
    return {'format': FORMAT, 'app_id': APP_ID, 'type': 'server_ready',
            'session_id': args.session_id, 'import_generation': args.import_generation,
            'assets_manifest_sha256': assets_sha256, 'import_receipt_sha256': import_receipt_sha256,
            'db_address': '127.0.0.1', 'db_port': 7000, 'map_address': '127.0.0.1',
            'map_port': destination['map_port'], 'map_id': destination['map_id'],
            'account': 'COHLOCAL', 'local_fake_auth': True, 'endpoint_policy': 'owned_loopback_only',
            'saved_character_available': destination['saved_character_available'],
            'character_count': destination['character_count'],
            'selection_authority': destination['selection_authority'],
            'native_client_started': False, 'conventional_client_started': False,
            'encrypted_authentication_verified': False, 'native_world_entry_verified': False,
            'observed_utc_ms': int(time.time() * 1000), 'heartbeat_max_age_ms': 15000}


def load_guest_modules(directory):
    """Only the manifest-verified donor modules may implement retained behavior."""
    global base, startup, character, zoning, login, wine_policy
    directory = real_private_path(directory, directory=True)
    for name in ('diagnostic.py', 'client_startup_diagnostic.py', 'local_character_server.py',
                 'character_zoning.py', 'local_login_server.py', 'client_login_diagnostic.py'):
        real_private_path(directory / name)
    sys.path.insert(0, str(directory))
    import diagnostic
    import client_startup_diagnostic
    import local_character_server
    import character_zoning
    import local_login_server
    import client_login_diagnostic
    base, startup = diagnostic, client_startup_diagnostic
    character, zoning, login = local_character_server, character_zoning, local_login_server
    wine_policy = client_login_diagnostic


def admit_local_port(port, protocol):
    """Use the retained exact bind policy; no connection or discovery probe."""
    try:
        character.game.check_game_port(port, protocol)
    except base.DiagnosticError as exc:
        code = ('LOCAL_SERVER_PORT_IN_USE' if isinstance(exc.__cause__, OSError)
                and exc.__cause__.errno == errno.EADDRINUSE else 'LOCAL_SERVER_PORT_UNAVAILABLE')
        raise AdmissionError(code) from exc


def failure_metadata(exc):
    """Types and verified code locations only: never messages, locals or paths."""
    kind = type(exc).__name__
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,79}', kind):
        kind = 'Exception'
    sites = []
    roots = [Path(__file__).resolve().parent]
    if startup is not None:
        roots.append(Path(startup.__file__).resolve().parent)
    for frame in traceback.extract_tb(exc.__traceback__):
        filename = Path(frame.filename)
        if (filename.parent.resolve() in roots and re.fullmatch(r'[A-Za-z0-9_]+\.py', filename.name)
                and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_<>]{0,99}', frame.name)):
            sites.append({'file': filename.name, 'function': frame.name, 'line': frame.lineno})
    code = str(exc) if isinstance(exc, AdmissionError) else 'RETAINED_GUEST_DEPENDENCY_FAILED'
    if any(site['function'] == 'check_game_port' for site in sites):
        code = ('LOCAL_SERVER_PORT_IN_USE' if isinstance(exc.__cause__, OSError)
                and exc.__cause__.errno == errno.EADDRINUSE else 'LOCAL_SERVER_PORT_UNAVAILABLE')
    if not re.fullmatch(r'[A-Z][A-Z0-9_]{0,79}', code):
        code = 'INTERNAL_RUNTIME_FAILURE'
    metadata = {'primary_failure_code': code, 'exception_type': kind, 'failure_sites': sites[-8:]}
    cause = exc
    for _ in range(4):
        number = getattr(cause, 'errno', None)
        if isinstance(cause, OSError) and type(number) is int and 0 < number <= 4096:
            metadata['failure_errno'] = number
            break
        cause = getattr(cause, '__cause__', None)
        if cause is None:
            break
    return metadata


def report_identity(args):
    require(SESSION.fullmatch(args.session_id) and GENERATION.fullmatch(args.import_generation),
            'INVALID_RUN_IDENTITY')
    real_private_path(args.state, directory=True, exists=False)
    args.state.mkdir(mode=0o700, parents=True, exist_ok=True)
    real_private_path(args.state, directory=True)
    require(args.state.stat().st_uid == os.geteuid(), 'REPORT_STATE_OWNER_DIFFERS')
    return {'session_id': args.session_id, 'import_generation': args.import_generation}


def write_report(args, result):
    """Atomic owned-path publication also works before donor imports succeed."""
    report_identity(args)
    raw = (json.dumps(result, indent=2) + '\n').encode()
    require(len(raw) <= 256 * 1024, 'REPORT_SIZE_EXCEEDED')
    directory = os.open(args.state, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temporary = 'latest-report.tmp-' + secrets.token_hex(8)
    try:
        require(os.fstat(directory).st_uid == os.geteuid(), 'REPORT_STATE_OWNER_DIFFERS')
        try:
            previous = os.stat('latest-report.json', dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            previous = None
        require(previous is None or stat.S_ISREG(previous.st_mode) and previous.st_nlink == 1,
                'INVALID_REPORT_OUTPUT')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=directory)
        with os.fdopen(fd, 'wb') as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, 'latest-report.json', src_dir_fd=directory, dst_dir_fd=directory)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary, dir_fd=directory)
        os.close(directory)


def rss_kib():
    """Linux VmRSS only; no process command lines or environment are read."""
    try:
        with Path('/proc/self/status').open() as source:
            raw = source.read(16384)
        value = re.search(r'(?m)^VmRSS:\s+([0-9]+) kB$', raw)
        return int(value[1]) if value and int(value[1]) <= 8 * 1024 * 1024 else None
    except (OSError, ValueError, OverflowError, TypeError):
        return None


def guest_resource_sample():
    """Best-effort Linux numeric observations; never a memory-cause verdict.

    Cgroup discovery is deliberately deferred. An unverified or shared group
    must not be represented as this owned guest's memory accounting.
    """
    def peak(who):
        try:
            value = resource.getrusage(who).ru_maxrss
            return value if type(value) is int and 0 <= value <= 8 * 1024 * 1024 else None
        except (OSError, ValueError, OverflowError, TypeError, AttributeError):
            return None
    return {'rss_kib': rss_kib(), 'peak_rss_kib': peak(resource.RUSAGE_SELF),
            'children_peak_rss_kib': peak(resource.RUSAGE_CHILDREN),
            'cgroup_current_bytes': None, 'cgroup_max_bytes': None,
            'cgroup_oom_kill_count': None}


def geometry_worker_main(argv=None):
    """Run the original cold manifest/geometry validator in disposable memory."""
    parser = argparse.ArgumentParser(description='Internal original-geometry preparation worker')
    parser.add_argument('--geometry-worker', action='store_true', required=True)
    parser.add_argument('--guest-modules', type=Path, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--worktree', type=Path, required=True)
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--import-generation', required=True)
    args = parser.parse_args(argv)
    args.timeout_seconds = 900
    result = {'type': 'geometry_prepared', 'format': 1, 'status': 'failed',
              'server_processes_started': False}
    try:
        require(SESSION.fullmatch(args.session_id) and GENERATION.fullmatch(args.import_generation),
                'INVALID_RUN_IDENTITY')
        result.update(session_id=args.session_id, import_generation=args.import_generation)
        require(args.guest_modules == args.assets, 'GUEST_MODULES_MUST_BE_VERIFIED_ASSETS')
        for path in (args.assets, args.state, args.worktree):
            real_private_path(path, directory=True)
        load_guest_modules(args.guest_modules)
        Context, _ = runtime_classes()
        context = Context(args)
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda _sig, _frame: setattr(context, 'cancel_requested', True))
        import atlas_beacon_package as beacons
        # No altered module, compact substitute, or skipped source/archive pin.
        receipt = beacons.ensure_required_geometry(args.worktree, args.assets, context)
        require(not context.children and context.owned_start_attempts == 0,
                'GEOMETRY_WORKER_STARTED_UNEXPECTED_CHILD')
        identity = beacons.validate_required_geometry(args.worktree, context)
        result.update(status=receipt['status'], input_files_checked=receipt['input_files_checked'],
            required_geometry_sha256=identity['required_geometry_sha256'],
            worker_peak_rss_kib=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
        print(json.dumps(result, separators=(',', ':')), flush=True)
        return 0
    except BaseException as exc:
        result.update(failure_metadata(exc))
        print(json.dumps(result, separators=(',', ':')), flush=True)
        return 1


def prepare_geometry_before_servers(owner):
    """Join/reap the original cold validator before any PG or Wine residency."""
    require(owner.pg is None and owner.xserver is None and not owner.wine_started,
            'GEOMETRY_PREPARATION_REQUIRES_STOPPED_SERVERS')
    assets = owner.args.assets
    if not ((assets / 'atlas-beacons.zip').exists() or (assets / 'atlas-beacon-manifest.json').exists()):
        return
    context = owner.ctx
    context.stage('isolated_required_geometry_preparation')
    before = rss_kib()
    started = time.monotonic()
    import atlas_beacon_package as beacons
    import client_visual_assets as visual
    # Preserve the donor's fast warm path. Do not launch another interpreter
    # when the original durable outputs and immutable source fingerprints match.
    try:
        identity = beacons.validate_required_geometry(owner.work, context)
        saved = beacons.geometry_marker_state(owner.work)
        warm_ready = saved.get('source_state') == visual.source_state(assets)
    except (ValueError, FileNotFoundError):
        warm_ready = False
    if warm_ready:
        warm = beacons.ensure_required_geometry(owner.work, assets, context)
        require(warm.get('status') == 'reused_verified_required_geometry', 'GEOMETRY_WARM_REUSE_FAILED')
        context.report['geometry_preparation'] = {
            'policy': 'isolated_original_geometry_before_servers', 'worker_used': False,
            'worker_reaped': True, 'before_postgresql': True, 'before_wine': True,
            'worker_peak_rss_kib': 0, 'parent_rss_kib_before': before, 'parent_rss_kib_after': rss_kib(),
            'elapsed_seconds': round(time.monotonic() - started, 3), 'status': warm['status'],
            'input_files_checked': warm['input_files_checked'],
            'required_geometry_sha256': identity['required_geometry_sha256']}
        context.passed(original_geometry_reused_without_worker=True)
        return
    result = context.run('isolated-required-geometry', [sys.executable, str(Path(__file__).resolve()),
        '--geometry-worker', '--guest-modules', str(assets), '--assets', str(assets),
        '--state', str(owner.args.state), '--worktree', str(owner.work),
        '--session-id', owner.args.session_id, '--import-generation', owner.args.import_generation],
        timeout=900, env=owner.base_env, check=False,
        progress_message='Preparing exact original geometry before starting the servers')
    child = context.children[-1]
    require(child.process.poll() is not None and not child.reader.is_alive() and not child.writer.is_alive(),
            'GEOMETRY_PREPARATION_WORKER_NOT_REAPED')
    receipts = []
    for line in child.text().splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if type(value) is dict and value.get('type') == 'geometry_prepared':
            receipts.append(value)
    require(len(receipts) == 1, 'GEOMETRY_PREPARATION_RECEIPT_MISSING')
    receipt = receipts[0]
    require(receipt.get('session_id') == owner.args.session_id
            and receipt.get('import_generation') == owner.args.import_generation,
            'GEOMETRY_PREPARATION_IDENTITY_DIFFERS')
    require(result['exit_code'] == 0 and receipt.get('server_processes_started') is False
            and receipt.get('status') in ('installed_verified_required_geometry', 'reused_verified_required_geometry'),
            'GEOMETRY_PREPARATION_WORKER_FAILED')
    import atlas_beacon_package as beacons
    # Independent original durable/warm checks bind actual output fingerprints
    # and exact original geometry digest after the high-memory child has exited.
    warm = beacons.ensure_required_geometry(owner.work, assets, context)
    require(warm.get('status') == 'reused_verified_required_geometry'
            and beacons.validate_required_geometry(owner.work, context) == warm['identity'],
            'GEOMETRY_PREPARATION_WARM_PROOF_FAILED')
    require(receipt.get('required_geometry_sha256') == warm['identity']['required_geometry_sha256']
            and receipt.get('input_files_checked') == warm['input_files_checked'],
            'GEOMETRY_PREPARATION_OUTPUT_DIFFERS')
    peak = receipt.get('worker_peak_rss_kib')
    require(type(peak) is int and 0 <= peak <= 8 * 1024 * 1024, 'INVALID_GEOMETRY_MEMORY_RECEIPT')
    context.report['geometry_preparation'] = {'policy': 'isolated_original_geometry_before_servers',
        'worker_used': True, 'worker_reaped': True, 'before_postgresql': owner.pg is None,
        'before_wine': not owner.wine_started, 'worker_peak_rss_kib': peak,
        'parent_rss_kib_before': before, 'parent_rss_kib_after': rss_kib(),
        'elapsed_seconds': round(time.monotonic() - started, 3), 'status': receipt['status'],
        'input_files_checked': warm['input_files_checked'],
        'required_geometry_sha256': warm['identity']['required_geometry_sha256']}
    context.passed(geometry_preparation_worker_reaped=True)


def runtime_classes():
    require(base is not None, 'GUEST_MODULES_NOT_LOADED')

    class Context(base.Context):
        """Retain private captures for parser use, expose no process/SQL output."""
        def __init__(self, args):
            super().__init__(args.state, args.timeout_seconds)
            self.session_id = args.session_id
            self.public_events = 0
            self.log_root = None
            self.owned_start_attempts = 0
            self.stage_started_monotonic = None
            self.guest_resource_samples = []

        log_paths = character.game.GameContext.log_paths

        def resource_boundary(self, boundary):
            if boundary not in ('leaving', 'entered'):
                return
            stage = self.stage_name
            if type(stage) is not str or not re.fullmatch(r'[A-Za-z0-9_]{1,100}', stage):
                stage = 'unknown_stage'
            sample = {'type': 'guest_resources', 'stage': stage, 'boundary': boundary,
                      'session_id': self.session_id, 'time_utc': base.utc(), **guest_resource_sample()}
            self.guest_resource_samples.append(sample)
            self.guest_resource_samples = self.guest_resource_samples[-32:]
            print(json.dumps(sample, separators=(',', ':')), flush=True)

        def stage(self, name):
            self.resource_boundary('leaving')
            if self.stage_started_monotonic is not None and self.report['stages']:
                self.report['stages'][-1].setdefault('elapsed_seconds',
                    round(time.monotonic() - self.stage_started_monotonic, 3))
            base.Context.stage(self, name)
            self.stage_started_monotonic = time.monotonic()
            self.resource_boundary('entered')

        def passed(self, **evidence):
            base.Context.passed(self, **evidence)
            if self.stage_started_monotonic is not None:
                self.report['stages'][-1]['elapsed_seconds'] = round(
                    time.monotonic() - self.stage_started_monotonic, 3)

        def start(self, label, argv, *, env=None, input_text=None, cleanup=False):
            if not cleanup:
                self.check()
            # Retained map startup can use up to 160 actual status queries.
            # Match the accepted character-session finite child inventory.
            require(len(self.children) < 512, 'PROCESS_BUDGET_EXCEEDED')
            self.owned_start_attempts += 1
            child = base.OwnedProcess(label, argv, env or os.environ.copy(), input_text)
            self.children.append(child)
            return child

        def event(self, kind, **fields):
            if kind == 'log':
                return
            self.public_events += 1
            require(self.public_events <= 20000, 'EVENT_BUDGET_EXCEEDED')
            value = {'type': 'stage', 'stage': self.stage_name[:100],
                     'session_id': self.session_id, 'time_utc': base.utc()}
            if fields.get('status') in ('running', 'passed', 'failed'):
                value['status'] = fields['status']
            # Library messages are fixed progress descriptions. Drop arbitrary
            # evidence and all child output, account IDs, cookies, and SQL rows.
            if kind == 'stage' and isinstance(fields.get('message'), str):
                value['message'] = base.redact(fields['message'], self.secrets)[:200]
            print(json.dumps(value, separators=(',', ':')), flush=True)

        def record(self, child, *, refresh=False):
            lifetime = round(time.monotonic() - child.started, 3)
            completion = getattr(child, 'completion', None)
            completed_elapsed = completion.get('elapsed_seconds') if isinstance(completion, dict) else None
            if (type(completed_elapsed) not in (int, float) or not math.isfinite(completed_elapsed)
                    or completed_elapsed < 0):
                completed_elapsed = None
            receipt = {'label': child.label,
                       'elapsed_seconds': completed_elapsed if type(completed_elapsed) in (int, float) else lifetime,
                       'elapsed_scope': 'completed_execution' if completed_elapsed is not None else 'observed_lifetime',
                       'observed_lifetime_seconds': lifetime,
                       'output_bytes': len(getattr(child, 'output', b'')),
                       'output_overflow': bool(getattr(child, 'overflow', False)),
                       'exit_code': child.process.poll(), 'forced_stop': child.forced_stop,
                       'output_capture_closed': not child.reader.is_alive(),
                       'input_closed': not child.writer.is_alive()}
            if child.recorded is None:
                self.report['processes'].append(receipt)
                child.recorded = receipt
            else:
                child.recorded.update(receipt)
            # Existing parsers need complete bounded output, but it is never
            # inserted into public reports or emitted on stdout.
            return dict(receipt, output=base.redact(child.text(), self.secrets)[-16384:])

    class Server(zoning.LocalCharacterZoningServer):
        requires_saved_character = False

        def initialize(self):
            # LocalLogin initializes only the private compatibility schema.
            # It neither creates an account/character nor starts a game client.
            # On first import the compatibility schema is supplied by PGDMP.
            self.initialize_private_profile()
            self.destination = self.read_destination()
            self.active_map_id = self.destination['map_id']
            self.creation_report['map_id'] = self.active_map_id
            self.creation_report['server_only'] = True

        def initialize_private_profile(self):
            d = self.owner
            self.ctx.stage('persistent_server_profile')
            self.payloads()
            real_private_path(self.profile, directory=True, exists=False)
            marker = self.profile / 'profile.json'
            if self.profile.exists():
                require(self.profile.is_dir(), 'INVALID_PROFILE_DIRECTORY')
                record = login.profile_record(marker)
                reused = record['initialized']
            else:
                self.profile.mkdir(mode=0o700)
                base.private_write(marker, json.dumps(dict(login.PROFILE_IDENTITY, initialized=False)) + '\n')
                reused = False
            d.pgdata = self.profile / 'pgdata'
            d.socket_dir = base.private_dir(self.profile / 'socket')
            real_private_path(d.pgdata, directory=True, exists=False)
            credentials_path = self.profile / 'credentials.json'
            real_private_path(credentials_path, exists=False)
            if credentials_path.exists():
                require(credentials_path.stat().st_nlink == 1 and credentials_path.stat().st_size <= 4096,
                        'INVALID_PROFILE_CREDENTIALS')
                credentials = json.loads(credentials_path.read_text())
                require(type(credentials) is dict and set(credentials) == {'cohdiag_admin', 'cohtest'}
                        and all(type(v) is str and re.fullmatch(r'[0-9a-f]{64}', v)
                                for v in credentials.values()), 'INVALID_PROFILE_CREDENTIALS')
            else:
                require(not d.pgdata.exists() and not reused, 'MISSING_PROFILE_CREDENTIALS')
                credentials = {role: secrets.token_hex(32) for role in ('cohdiag_admin', 'cohtest')}
                base.private_write(credentials_path, json.dumps(credentials) + '\n')
            credentials_path.chmod(0o600)
            d.credentials = credentials
            self.ctx.secrets.extend(credentials.values())
            for name in ('initdb', 'postgres', 'pg_ctl', 'psql', 'pg_restore'):
                base.arm64_elf(d.args.pg_bin / name)
            if not d.pgdata.exists():
                require(not reused, 'MISSING_INITIALIZED_CLUSTER')
                require(len(list(self.profile.glob('init-pending-*'))) < 8, 'TOO_MANY_INTERRUPTED_INITIALIZATIONS')
                pending = self.profile / ('init-pending-' + secrets.token_hex(8))
                password = self.profile / 'init-password'
                base.private_write(password, credentials['cohdiag_admin'] + '\n')
                try:
                    self.ctx.run('native-initdb', [d.pgtool('initdb'), '-D', pending, '-U', 'cohdiag_admin',
                        '--pwfile', password, '--auth-local=scram-sha-256', '--auth-host=scram-sha-256',
                        '--encoding=UTF8', '--locale=C', '-c', 'shared_memory_type=mmap',
                        '-c', 'dynamic_shared_memory_type=mmap'], timeout=90, env=d.base_env)
                    pending.rename(d.pgdata)
                finally:
                    password.unlink(missing_ok=True)
            require((d.pgdata / 'PG_VERSION').is_file(), 'INCOMPLETE_OWNED_CLUSTER')
            status = self.ctx.run('native-cluster-status', [d.pgtool('pg_ctl'), '-D', d.pgdata, 'status'],
                                  check=False, env=d.base_env)
            require(status['exit_code'] == 3, 'PROFILE_ALREADY_RUNNING_OR_UNREADABLE')
            with socket.socket() as listener:
                listener.bind(('127.0.0.1', 0))
                d.port = listener.getsockname()[1]
            d.database = login.DATABASE
            d.database_created = False  # Persistent profile is never fixture cleanup.
            self.report.update(profile_reused=reused, database_preserved_by_policy=True)
            d.start_postgres('postgres_native_combined')
            names = self.sql("SELECT datname FROM pg_database WHERE datname NOT IN ('postgres','template0','template1') ORDER BY datname;")
            require(names in ('', login.DATABASE), 'UNEXPECTED_PRIVATE_DATABASE')
            role = self.sql("SELECT count(*) FROM pg_roles WHERE rolname='cohtest';")
            if role == '0':
                require(not reused, 'MISSING_INITIALIZED_ROLE')
                self.sql("CREATE ROLE cohtest LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD '"
                         + credentials['cohtest'] + "';")
            require(self.sql("SELECT (NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication)::int FROM pg_roles WHERE rolname='cohtest';") == '1',
                    'UNEXPECTED_ROLE_PRIVILEGES')
            if names == '':
                require(not reused, 'MISSING_INITIALIZED_DATABASE')
                self.sql('CREATE DATABASE "' + login.DATABASE + '" OWNER cohtest;')
            require(self.sql("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname='"
                             + login.DATABASE + "';") == 'cohtest', 'UNEXPECTED_DATABASE_OWNER')
            if not reused:
                self.sql('REVOKE ALL ON DATABASE ' + login.DATABASE + ' FROM PUBLIC;')
                self.sql('ALTER DATABASE ' + login.DATABASE + ' SET search_path=dbo,pg_catalog;')
                self.sql('REVOKE CREATE ON SCHEMA public FROM PUBLIC;', game=True)
                if d.args.logical_backup is not None:
                    self.restore_first_profile(d.args.logical_backup)
                else:
                    self.sql((d.args.assets / '001-coh-compat.sql').read_text(), game=True)
            elif d.args.logical_backup is not None:
                imported = self.profile / 'logical-import.json'
                require(imported.is_file() and not imported.is_symlink() and imported.stat().st_size <= 4096
                        and json.loads(imported.read_text()).get('backup') == backup_identity(d.args.logical_backup),
                        'REFUSING_REPLACEMENT_OF_INITIALIZED_PROFILE')
            require(self.sql("SELECT current_user || '|' || max(version) FROM coh_meta.schema_version;", game=True)
                    == 'cohtest|2', 'COMPATIBILITY_SCHEMA_IDENTITY_DIFFERS')
            if not reused and d.args.provision_test_character and d.args.logical_backup is None:
                base.private_write(self.profile / 'provision-requested.json',
                                   json.dumps({'format': 1, 'app_id': APP_ID}) + '\n')
            base.private_write(marker, json.dumps(dict(login.PROFILE_IDENTITY, initialized=True)) + '\n')
            self.report['profile_initialized'] = True
            self.ctx.passed(profile_initialized=True, profile_reused=reused)

        def restore_first_profile(self, backup):
            d = self.owner
            identity = backup_identity(backup)
            # A failed pg_restore transaction leaves no committed tables. A
            # completed import with its receipt is never repeated. If power
            # fails between PostgreSQL commit and receipt publication, retain
            # the nonempty database and require manual review; do not overwrite.
            marker = self.profile / 'logical-import.json'
            if marker.exists():
                require(not marker.is_symlink() and marker.stat().st_size <= 4096
                        and json.loads(marker.read_text()) == {'format': 1, 'backup': identity},
                        'LOGICAL_IMPORT_IDENTITY_DIFFERS')
                return
            count = self.sql("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%';", game=True)
            require(count == '0', 'LOGICAL_IMPORT_REQUIRES_EMPTY_OWNED_DATABASE')
            environment = dict(d.base_env, PGPASSWORD=d.credentials['cohtest'], PGCONNECT_TIMEOUT='5')
            self.ctx.stage('logical_profile_import')
            self.ctx.run('native-logical-restore', [d.pgtool('pg_restore'), '-h', str(d.socket_dir),
                '-p', str(d.port), '-U', 'cohtest', '-d', login.DATABASE,
                '--no-owner', '--no-privileges', '--exit-on-error', '--single-transaction',
                '--schema=dbo', '--schema=coh_meta', str(backup)],
                timeout=180, env=environment)
            require(backup_identity(backup) == identity, 'BACKUP_CHANGED_DURING_RESTORE')
            base.private_write(marker, json.dumps({'format': 1, 'backup': identity}) + '\n')
            self.ctx.passed(logical_backup_restored=True, original_profile_modified=False)

        def read_destination(self):
            presence = self.sql("SELECT CASE WHEN to_regclass('dbo.ents') IS NULL THEN 'missing' ELSE 'present' END;", game=True)
            require(presence in ('missing', 'present'), 'INVALID_CHARACTER_TABLE_PRESENCE')
            rows = [] if presence == 'missing' else self.sql_rows('ents',
                ('containerid', 'authname', 'name', 'authid', 'mapid', 'staticmapid', 'posx', 'posy', 'posz'),
                ('containerid',))
            return select_destination(rows)

        def capture_baseline(self):
            current = self.read_destination()
            require(current == self.destination, 'SAVED_DESTINATION_CHANGED_DURING_STARTUP')
            self.startup_preparation_map_id = self.active_map_id = current['map_id']

        def initial_map_preparation(self):
            self.qualify_monorail_preparation()
            self.capture_baseline()
            require(self.active_map_id != 5 or self.monorail_enabled(), 'SAVED_KINGS_ROW_REQUIRES_VERIFIED_ZONE_PACKAGE')
            return self.active_map_id

        def provision_if_requested(self):
            if not self.owner.args.provision_test_character:
                return
            require(self.owner.args.logical_backup is None, 'IMPORTED_PROFILE_PROVISIONING_FORBIDDEN')
            marker = self.profile / 'provision-complete.json'
            requested = self.profile / 'provision-requested.json'
            if marker.exists():
                require(not marker.is_symlink() and marker.stat().st_size <= 4096,
                        'INVALID_PROVISION_RECEIPT')
                self.provision = json.loads(marker.read_text())
                require(self.provision.get('format') == 1 and self.provision.get('app_id') == APP_ID
                        and self.provision.get('committed_sql_verified') is True
                        and self.provision.get('helper_reaped') is True
                        and self.provision.get('source_helper_used') is True
                        and self.provision.get('native_character_creation_verified') is False
                        and self.provision.get('implementation') == 'unchanged_source_TestClientCreate_bridge'
                        and re.fullmatch(r'[0-9a-f]{64}', self.provision.get('snapshot_sha256', '')),
                        'INVALID_PROVISION_RECEIPT')
                require(self.destination['saved_character_available'], 'PROVISIONED_CHARACTER_MISSING')
                return
            require(requested.is_file() and not requested.is_symlink() and requested.stat().st_size <= 4096
                    and json.loads(requested.read_text()) == {'format': 1, 'app_id': APP_ID},
                    'EXISTING_PROFILE_PROVISIONING_FORBIDDEN')
            require(not self.destination['saved_character_available'],
                    'INTERRUPTED_PROVISION_REQUIRES_REVIEW')
            require(self.sql("SELECT dbo.coh_container_high_water('dbo.ents'::regclass);", game=True) == '0',
                    'PREVIOUS_CHARACTER_ALLOCATION_FORBIDS_PROVISION')
            helper = Provisioner(self)
            self.owner.provisioner = helper
            session = helper.create_character()
            helper.live_currency(session)
            snapshot = helper.logout(session, 'first', 1)
            require(session.child.process.poll() is not None and not session.child.reader.is_alive()
                    and not session.child.writer.is_alive(), 'PROVISION_HELPER_NOT_REAPED')
            self.destination = self.read_destination()
            require(self.destination['saved_character_available'] and self.destination['map_id'] == 1,
                    'PROVISIONED_SAVED_CHARACTER_NOT_VERIFIED')
            self.provision = {'format': 1, 'app_id': APP_ID,
                'implementation': 'unchanged_source_TestClientCreate_bridge',
                'committed_sql_verified': True, 'helper_reaped': True,
                'native_character_creation_verified': False, 'source_helper_used': True,
                'snapshot_sha256': hashlib.sha256(json.dumps(snapshot, sort_keys=True,
                    separators=(',', ':')).encode()).hexdigest()}
            base.private_write(marker, json.dumps(self.provision) + '\n')
            # Account/cookie-bearing source-helper captures stay out of every
            # export and are removed after their hashes and save proof exist.
            for helper_session in helper.sessions:
                shutil.rmtree(helper_session.root)

        def start(self):
            # Skip LocalCharacterServer.start's graphical-character evidence;
            # retain its original server startup, preparation and native gates.
            login.LocalLoginServer.start(self)
            self.capture_baseline()
            self.start_map()
            self.provision_if_requested()

        def prepare_runtime(self):
            # LocalLoginServer.start reaches this seam only after its actual
            # PE32 ODBC install and validated driver probe. Preserve that Wine
            # proof before later map-data preparation can fail or be cancelled.
            self.owner.mark_wine_ready()
            character.LocalCharacterServer.prepare_runtime(self)
            self.qualify_monorail_preparation()
            require(self.manual_atlas_startup is not None,
                    'MANUAL_SERVER_DBSERVER_SUPPLEMENT_REQUIRED')

        def persist_startup_observation(self):
            # The inherited implementation serializes all private context
            # observations. Export only the adapter's curated numeric receipt.
            pass

    class Provisioner:
        # These are the unchanged accepted source-helper control and SQL proof
        # functions. No serialized or mocked character is inserted by this adapter.
        game_module = character.game
        wait = game_module.GameDiagnostic.wait
        game_environment = game_module.GameDiagnostic.game_environment
        inventory = game_module.GameDiagnostic.inventory
        new_client = game_module.GameDiagnostic.new_client
        create_character = game_module.GameDiagnostic.create_character
        observe_client_listeners = game_module.GameDiagnostic.observe_client_listeners
        live_currency = game_module.GameDiagnostic.live_currency
        character_status = game_module.GameDiagnostic.character_status
        snapshot = game_module.GameDiagnostic.snapshot
        logout = game_module.GameDiagnostic.logout
        clean_logs = game_module.GameDiagnostic.clean_logs

        def __init__(self, server):
            self.server, self.ctx = server, server.ctx
            owner = server.owner
            self.root, self.runtime, self.args = owner.root, server.runtime, owner.args
            self.wine_env, self.package, self.schema = owner.wine_env, server.map_package, server.schema
            self.ctx.log_root = self.runtime
            self.game_listener_enabled = self.game_module.game_listener_contract(self.package) is not None
            require(self.game_listener_enabled, 'PROVISION_HELPER_LOOPBACK_CONTRACT_REQUIRED')
            self.loopback_enabled = False
            self.completed_logout = False
            self.sessions, self.snapshots = [], {}
            self.services = [server.process, server.map_process]
            self.game = {'account': 'COHLOCAL', 'character_samples': [],
                         'client_listener_observations': {}, 'sessions': {}}

        def sample_map_progress(self, reason):
            # Map readiness was independently proved by the retained completed
            # tick plus DbServer status gates before the helper is admitted.
            return self.server.sample_progress()

        def health(self):
            self.ctx.check()
            self.server.health()

        def query(self, arguments, label):
            return self.server.query(arguments, label)

        def sql_rows(self, *args, **kwargs):
            return self.server.sql_rows(*args, **kwargs)

    class Owner(base.Diagnostic):
        def __init__(self, args, context):
            super().__init__(args, context)
            self.work = None
            self.client = None
            self.server = Server(self)
            self.ready_path = args.state / 'server-ready.json'
            self.ready_receipt = None
            self.provisioner = None
            self.presentation_socket = None
            self.presentation_socket_identity = None

        # DbServer's accepted helpers read complete bounded stdout, unlike the
        # short generic SQL report tail. No output is logged by our Context.
        def sql(self, text, *, game=False, cleanup=False):
            base.Diagnostic.sql(self, text, game=game, cleanup=cleanup)
            return self.ctx.children[-1].text().strip()

        def initialize(self):
            self.ctx.stage('preflight_local_server_ports')
            for port, protocol in ((6997, socket.SOCK_STREAM), (7000, socket.SOCK_DGRAM)):
                admit_local_port(port, protocol)
            self.ctx.passed(local_server_ports_available=True)
            self.ctx.stage('server_only_input_admission')
            require(platform.machine().lower() in ('aarch64', 'arm64'), 'ARM64_GUEST_REQUIRED')
            require(os.geteuid() == 1000, 'PROOT_UID_1000_REQUIRED')
            self.ctx.report['asset_sha256'] = startup.verify_assets(self.args.assets)
            for name in ('wine', 'wineserver'):
                base.arm64_elf(getattr(self.args, name))
            identity = startup.import_identity(self.args.game_data)
            require(identity['generation'] == self.args.import_generation, 'IMPORT_GENERATION_DIFFERS')
            self.ctx.report['import_identity'] = identity
            self.ctx.passed(import_generation_verified=True)
            self.ctx.stage('prepare_private_server_inputs')
            self.work, receipt = startup.prepare_worktree(self.root, self.args.game_data,
                                                          self.args.assets, identity, self.ctx)
            self.ctx.report['client_worktree'] = receipt
            character.avatar.install(self.work, self.args.assets, self.ctx)
            character.world.install(self.work, self.args.assets, self.ctx)
            self.ctx.passed(original_game_data_preserved=True)
            prepare_geometry_before_servers(self)
            self.server.initialize()
            self.ctx.stage('preflight_selected_map_port')
            admit_local_port(self.server.destination['map_port'], socket.SOCK_DGRAM)
            self.ctx.passed(selected_map_port_available=True)

        # Exact donor display/bootstrap path: no MSI installation or driver
        # probe here. LocalLoginServer.start retains the single original pair.
        def start_wine(self):
            self.ctx.stage('prepare_owned_presentation_endpoint')
            self.presentation_socket = presentation_endpoint(self.root, self.args.session_id)
            self.ctx.report['presentation_endpoint'] = {
                'policy': 'fresh_session_bound_private_rfb_socket',
                'session_bound': True, 'existing_endpoints_removed': 0,
                'legacy_fixed_endpoint_reused': False, 'original_display_bootstrap_reused': True}
            startup.presentation.PresentationDiagnostic.start_wine(self)

        def prepare_wine_initialization(self):
            registration = wine_policy.wine_registration_input(self.args.wine)
            prefix_existed = self.wineprefix.is_dir()
            base.Diagnostic.prepare_wine_initialization(self)
            self._wine_registration_input = registration
            receipt = self.wine_initialization
            prior_ready = receipt['ready_prefix_reused']
            receipt.update(prior_ready_prefix=prior_ready, existing_prefix_preserved=prefix_existed,
                installed_wine_inf=registration, refresh_reason='none' if prior_ready else 'no_current_readiness_proof',
                update_timestamp_content_before=None, update_timestamp_content_after=None,
                registration_timestamp_verified=False)
            if prior_ready:
                timestamp = self.wineprefix / '.update-timestamp'
                previous = wine_policy.wine_update_timestamp(timestamp)
                receipt['update_timestamp_content_before'] = previous
                if previous != registration['mtime_seconds']:
                    timestamp.unlink()
                    receipt.update(ready_prefix_reused=False, update_timestamp_removed=True,
                                   refresh_reason='wine_inf_timestamp_changed')
                    self.ctx.event('stage', status='running', message='Refreshing preserved Windows environment')

        def initialize_wine(self):
            try:
                base.Diagnostic.initialize_wine(self)
                current = wine_policy.wine_registration_input(self.args.wine)
                base.require(current == self._wine_registration_input,
                             'Wine registration input changed during initialization')
                timestamp = wine_policy.wine_update_timestamp(self.wineprefix / '.update-timestamp')
                self.wine_initialization['update_timestamp_content_after'] = timestamp
                base.require(timestamp == current['mtime_seconds'],
                             'Wine registration timestamp differs from installed input')
                self.wine_initialization['registration_timestamp_verified'] = True
            except BaseException:
                if hasattr(self, 'wine_initialization'):
                    self.wine_initialization['state'] = 'failed'
                raise

        def execute(self):
            self.initialize()
            # This owns a private headless X display required by retained Wine
            # registration/MSI; no CityOfHeroes.exe or client-launcher executes.
            self.start_wine()
            self.server.start()
            self.server.health()
            require(self.server.report.get('server_ready') is True
                    and self.server.creation_report.get('map_ready') is True,
                    'NATIVE_SERVER_READINESS_NOT_PROVED')
            config = self.server.config.read_text()
            require(re.search(r'(?im)^\s*UseFakeAuth\s+1\s*$', config) is not None,
                    'LOCAL_FAKE_AUTH_POLICY_REQUIRED')
            self.ready_receipt = ready_document(self.args, self.server.destination,
                assets_sha256=base.file_hash(self.args.assets / 'client-manifest.json'),
                import_receipt_sha256=self.ctx.report['import_identity']['receipt_sha256'])
            version = self.server.map_package.get('client_version')
            require(type(version) is str and version.isascii() and 0 < len(version) <= 128
                    and all(32 <= ord(ch) <= 126 for ch in version), 'INVALID_SERVER_CLIENT_VERSION')
            self.ready_receipt['client_version'] = version
            self.ready_receipt['source_helper_used'] = hasattr(self.server, 'provision')
            self.ready_receipt['native_character_creation_verified'] = False
            self.publish_ready(announce=True)
            self.ctx.stage('server_running_manual_native_client')
            next_heartbeat = 0
            while True:
                self.ctx.check()
                self.server.health()
                require(self.xserver is not None and self.xserver.process.poll() is None,
                        'OWNED_HEADLESS_DISPLAY_EXITED')
                if time.monotonic() >= next_heartbeat:
                    current = self.server.sample_progress(force=True)
                    require(self.server.live_progress(current), 'MAP_DISPATCH_NOT_FRESH')
                    self.publish_ready()
                    next_heartbeat = time.monotonic() + 5
                time.sleep(.25)

        def publish_ready(self, *, announce=False):
            self.ready_receipt['observed_utc_ms'] = int(time.time() * 1000)
            base.private_write(self.ready_path, json.dumps(self.ready_receipt) + '\n')
            if announce:
                print(json.dumps(self.ready_receipt, separators=(',', ':')), flush=True)

        def cleanup(self):
            self.ready_path.unlink(missing_ok=True)
            failures = super().cleanup()
            if self.presentation_socket_identity is not None:
                try:
                    if self.presentation_socket.exists() or self.presentation_socket.is_symlink():
                        info = self.presentation_socket.lstat()
                        require(stat.S_ISSOCK(info.st_mode)
                                and (info.st_dev, info.st_ino) == self.presentation_socket_identity,
                                'DISPLAY_SOCKET_IDENTITY_CHANGED')
                        require(self.xserver.process.poll() is not None and not self.xserver.reader.is_alive(),
                                'OWNED_DISPLAY_STILL_LIVE')
                        self.presentation_socket.unlink()
                    self.cleanup_status['presentation_socket_removed'] = True
                except Exception:
                    failures.append('Owned display socket cleanup incomplete')
                    self.cleanup_status['presentation_socket_removed'] = False
            if self.provisioner is not None:
                for helper_session in self.provisioner.sessions:
                    if helper_session.root.exists():
                        with contextlib.suppress(OSError):
                            shutil.rmtree(helper_session.root)
            try:
                self.server.cleanup_config()
            except Exception:
                failures.append('Private runtime configuration cleanup failed')
            return failures

    return Context, Owner


def arguments(argv=None, *, validate=True):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--guest-modules', type=Path, default=Path('/opt/coh'))
    parser.add_argument('--state', type=Path, default=Path('/state'))
    parser.add_argument('--assets', type=Path, default=Path('/opt/coh'))
    parser.add_argument('--game-data', type=Path, default=Path('/game/data'))
    parser.add_argument('--pg-bin', type=Path, default=Path('/opt/coh/pgsql/bin'))
    parser.add_argument('--wine', type=Path, default=Path('/opt/wine/bin/wine'))
    parser.add_argument('--wineserver', type=Path, default=Path('/opt/wine/bin/wineserver'))
    parser.add_argument('--xserver', type=Path, default=Path('/usr/bin/Xtigervnc'))
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--import-generation', required=True)
    parser.add_argument('--logical-backup', type=Path)
    parser.add_argument('--provision-test-character', action='store_true',
                        help='Fresh empty owned profile only: create/save one real character using source TestClient')
    parser.add_argument('--timeout-seconds', type=int, default=21600)
    args = parser.parse_args(argv)
    if validate:
        validate_arguments(args)
    return args


def validate_arguments(args):
    require(SESSION.fullmatch(args.session_id) and GENERATION.fullmatch(args.import_generation), 'INVALID_RUN_IDENTITY')
    require(600 <= args.timeout_seconds <= 21600, 'INVALID_RUNTIME_DURATION')
    require(args.guest_modules == args.assets, 'GUEST_MODULES_MUST_BE_VERIFIED_ASSETS')
    for name in ('guest_modules', 'state', 'assets', 'game_data', 'pg_bin', 'wine', 'wineserver', 'xserver'):
        real_private_path(getattr(args, name), directory=name in ('guest_modules', 'state', 'assets', 'game_data', 'pg_bin'),
                          exists=name != 'state')
    if args.logical_backup is not None:
        require(not args.provision_test_character, 'IMPORTED_PROFILE_PROVISIONING_FORBIDDEN')
        backup_identity(args.logical_backup)
    return args


def main(argv=None):
    os.umask(0o077)
    owner = context = args = None
    construction_started = False
    context_construction_started = False
    result = {'format': FORMAT, 'app_id': APP_ID, 'server_only': True,
              'conventional_client_started': False, 'native_client_started_by_guest': False,
              'encrypted_authentication_verified': False, 'native_world_entry_verified': False,
              'original_profile_modified': False, 'status': 'failed',
              'last_stage': 'preflight_input_admission',
              'cleanup_scope': 'current_attempt_only', 'primary_failure_code': None,
              'cleanup_failure_code': None}
    exit_code = 1
    try:
        args = arguments(argv, validate=False)
        result.update(report_identity(args))
        validate_arguments(args)
        load_guest_modules(args.guest_modules)
        Context, Owner = runtime_classes()
        context_construction_started = True
        context = Context(args)
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda _sig, _frame: setattr(context, 'cancel_requested', True))
        construction_started = True
        owner = Owner(args, context)
        owner.ready_path.unlink(missing_ok=True)
        owner.execute()
    except BaseException as exc:
        cancelled = context is not None and base is not None and isinstance(exc, base.Cancelled)
        result['status'] = 'stopped' if cancelled else 'failed'
        if not cancelled:
            result.update(failure_metadata(exc))
        exit_code = 0 if cancelled else 1
    finally:
        cleanup = []
        if owner is not None:
            try:
                cleanup = owner.cleanup()
            except Exception:
                cleanup = ['Owned cleanup did not complete']
            result['cleanup'] = owner.cleanup_status
            result['profile_preserved'] = True
            complete = not cleanup and bool(owner.cleanup_status.get('owned_processes_reaped'))
        else:
            # Constructors can fail after starting a child. Only a context with
            # zero start attempts and zero children proves no cleanup is due.
            complete = ((context is None and not context_construction_started) or
                        (context is not None and getattr(context, 'owned_start_attempts', None) == 0
                         and not context.children))
            result['cleanup'] = {'owner_constructed': False, 'construction_started': construction_started,
                'owned_start_attempts': getattr(context, 'owned_start_attempts', None) if context_construction_started else 0,
                'owned_processes_reaped': complete, 'no_owned_children_started': complete}
        result['cleanup_complete'] = complete
        if not complete:
            result['status'] = 'cleanup_failed'
            result['cleanup_failure_code'] = 'OWNED_CLEANUP_INCOMPLETE'
            exit_code = 1
        # Compatibility field retains the primary cause even when cleanup also
        # fails; callers can distinguish the separate cleanup failure code.
        result['failure_code'] = result['primary_failure_code'] or result['cleanup_failure_code']
        if context is not None:
            result['last_stage'] = context.stage_name
            result['processes'] = context.report['processes']
            if 'geometry_preparation' in context.report:
                result['geometry_preparation'] = context.report['geometry_preparation']
            if 'presentation_endpoint' in context.report:
                result['presentation_endpoint'] = context.report['presentation_endpoint']
            if getattr(context, 'guest_resource_samples', None):
                result['guest_resource_samples'] = context.guest_resource_samples
            stages = context.report.get('stages', [])[-128:]
            if stages and context.stage_started_monotonic is not None:
                stages[-1].setdefault('elapsed_seconds', round(time.monotonic() - context.stage_started_monotonic, 3))
            result['stage_history'] = [{key: row[key] for key in ('stage', 'started_utc', 'finished_utc', 'status', 'elapsed_seconds')
                                        if key in row} for row in stages]
            if owner is not None:
                phases = owner.server.creation_report.get('server_preparation_phase_seconds', {})
                result['server_preparation_phase_seconds'] = {key: value for key, value in phases.items()
                    if re.fullmatch(r'[A-Za-z0-9_]{1,100}', key) and type(value) in (int, float)
                    and math.isfinite(value) and value >= 0}
                if owner.ready_receipt is not None:
                    result['server_readiness'] = owner.ready_receipt
        report_written = False
        if args is not None:
            try:
                write_report(args, result)
                report_written = True
            except Exception:
                pass  # The bounded stdout receipt still carries the safe cause.
        print(json.dumps({'type': 'server_stopped', 'format': FORMAT, 'app_id': APP_ID,
            'session_id': result.get('session_id'), 'import_generation': result.get('import_generation'),
            'status': result['status'], 'failure_code': result['failure_code'],
            'primary_failure_code': result['primary_failure_code'],
            'cleanup_failure_code': result['cleanup_failure_code'],
            'exception_type': result.get('exception_type'), 'failure_sites': result.get('failure_sites', []),
            'failure_errno': result.get('failure_errno'),
            'cleanup_complete': complete, 'report_written': report_written}, separators=(',', ':')), flush=True)
    return exit_code


if __name__ == '__main__':
    if '--geometry-worker' in sys.argv[1:]:
        sys.exit(geometry_worker_main())
    sys.exit(main())
