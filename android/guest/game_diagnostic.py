#!/usr/bin/env python3
"""Owned Atlas/TestClient character persistence on hosted ARM64 Wine/FEX.

Only disposable fake-auth characters are created. This does not validate an
Android surface, a human-operated client, graphics, or general gameplay.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import signal
import socket
import stat
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dbserver_diagnostic as dbserver
import game_evidence as evidence
import game_hang_evidence as hang_evidence

base = dbserver.base
require = base.require
EXES = ('DbServer.exe', 'MapServer.exe', 'TestClientCreate.exe', 'TestClientResume.exe', 'TestClientBridge.exe')
PROCESS_LIMIT = 240
QUERY_LIMIT = 80
READINESS_LIMIT = 20
EVENT_LIMIT = 8 * 1024 * 1024
CONSOLE_LIMIT = 16 * 1024 * 1024
SERVICE_LABELS = ('first-dbserver', 'first-atlas', 'restart-dbserver', 'restart-atlas')
SERVICE_STDOUT_LIMIT = 6 * 1024 * 1024
SERVICE_LOG_LIMIT = 4 * 1024 * 1024
SERVICE_LOG_SEGMENT = 512 * 1024
FIXED_INPUT_FILE_LIMIT = 512
FIXED_INPUT_BYTE_LIMIT = 256 * 1024 * 1024
FIXED_INPUT_DIRECTORY_LIMIT = 512
FIXED_INPUT_ROOT = 'data/server/db'
MAP_PROGRESS_PROFILE = 'dispatch_progress_v1'
MAP_PROGRESS_ENVIRONMENT = 'COH_WINE_MAP_PROGRESS'


def map_progress_module():
    # Ordinary accepted Android bundles intentionally keep their existing five
    # guest scripts. Only the separately packaged opt-in host profile needs it.
    import game_map_progress
    return game_map_progress


def check_game_port(port, protocol):
    """Match Wine's native TCP reuse policy while rejecting live listeners."""
    transport = 'TCP' if protocol == socket.SOCK_STREAM else 'UDP'
    try:
        with socket.socket(socket.AF_INET, protocol) as check:
            if protocol == socket.SOCK_STREAM:
                # Pinned Wine server/sock.c enables this for all native TCP
                # sockets. A bare bind wrongly rejects their closed TIME_WAIT
                # connections during restart; UDP must remain exclusive.
                check.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            check.bind(('0.0.0.0', port))
    except OSError as exc:
        raise base.DiagnosticError(f'Game {transport} port {port} unavailable: {exc}') from exc


def safe_path(name):
    require(isinstance(name, str) and '\\' not in name and ':' not in name and '\x00' not in name,
            'Invalid game payload path')
    value = PurePosixPath(name)
    require(value.parts and not value.is_absolute() and str(value) == name
            and all(part not in ('.', '..') for part in value.parts), 'Unsafe game payload path')
    return value


def regular_path(root, name):
    target = root
    for part in safe_path(name).parts:
        target /= part
        require(not target.is_symlink(), 'Linked game payload refused')
    require(target.is_file(), 'Missing game payload: ' + name)
    return target


def inventory_files(root, check=lambda: None):
    """One no-follow tree inventory; DirEntry avoids repeated Path stat calls."""
    require(not root.is_symlink() and root.is_dir(), 'Invalid game inventory root')
    files, pending = set(), [root]
    while pending:
        check()
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                require(not entry.is_symlink(), 'Linked game input refused')
                path = Path(entry.path)
                if entry.is_dir(follow_symlinks=False):
                    pending.append(path)
                else:
                    require(entry.is_file(follow_symlinks=False), 'Nonregular game input refused')
                    files.add(path.relative_to(root).as_posix())
    return files


def create_private_parents(path, root, created):
    """Create each parent once within a freshly owned, still unlaunched tree."""
    require(path == root or root in path.parents, 'Private game parent escaped runtime')
    missing = []
    while path not in created:
        missing.append(path)
        path = path.parent
    for parent in reversed(missing):
        parent.mkdir(mode=0o700)
        created.add(parent)


def game_config(original, database, connection):
    settings = {
        'advertisedip': 'AdvertisedIp 127.0.0.1', 'usefakeauth': 'UseFakeAuth 1',
        'usequeueserver': 'UseQueueServer 0', 'defaultaccesslevel': 'DefaultAccessLevel 9',
        'blockfreeplayersifnoaccountserver': 'BlockFreePlayersIfNoAccountServer 0',
        'assertmode': 'AssertMode Exit', 'nostats': 'NoStats 1',
        'donotlaunchbeaconmasterserver': 'DoNotLaunchBeaconMasterServer 1',
        'donotlaunchbeaconclients': 'DoNotLaunchBeaconClients 1',
        'donotlaunchmapservertsr': 'DoNotLaunchMapServerTSR 1',
        'disablecontainerbackups': 'DisableContainerBackups 1'}
    kept = [line for line in original.splitlines()
            if not line.split() or line.split()[0].lower() not in settings]
    return dbserver.private_config('\n'.join(kept + list(settings.values())) + '\n', database, connection)


def fixed_inputs_acknowledgement(child):
    """Only complete lines in this owned process's full output can acknowledge activation."""
    require(not child.overflow, 'Fixed-input startup output overflowed')
    output = child.text()
    complete = output[:output.rfind('\n') + 1]
    if dbserver.FIXED_INPUTS_ENV not in complete:
        return False
    return dbserver.validate_fixed_inputs(complete, True)


def game_loopback_contract(package):
    """The new hosted profile uses the separately qualified loopback donor only."""
    profile = package.get('dbserver_profile', 'accepted')
    require(profile in ('accepted', 'loopback'), 'Unknown game DbServer profile')
    if profile == 'accepted':
        return None
    donor = package.get('inputs', {}).get('dbserver', {})
    manifest = donor.get('manifest', {})
    require(type(donor.get('run_id')) is int and donor['run_id'] == dbserver.DEVICE_PACKAGE_RUN
            and donor.get('manifest_sha256') == dbserver.DEVICE_PACKAGE_MANIFEST
            and donor.get('repository_commit') == manifest.get('repository_commit')
            == 'eed2ce1f5388195f65a07853919761a93657aca6',
            'Loopback game profile requires the qualified DbServer donor')
    normal = manifest.get('variants', {}).get('normal', {})
    files = normal.get('files', {})
    require(normal.get('postgresql_persistence_fixture') is False
            and files.get('DbServer.exe', {}).get('sha256')
            == '535bfd6df77ce09bc3d1048accd95d7910552f8861c3a9c4e356d522786d585c'
            and all(dbserver.exact_contract(package.get('files', {}).get(name), record)
                    for name, record in files.items()),
            'Loopback game profile does not preserve the qualified normal dependency closure')
    build = manifest.get('wine_build_input', {})
    metadata = build.get('loopback_only')
    dbserver.validate_loopback_metadata(metadata)
    endpoints = dbserver.loopback_expectations(build.get('normal_schema_listeners'))
    return {'metadata': metadata, 'endpoints': endpoints}


def loopback_acknowledgement(child, expected):
    """Wait for complete required bind records; malformed complete records fail immediately."""
    require(not child.overflow, 'Loopback startup output overflowed')
    output = child.text()
    complete = output[:output.rfind('\n') + 1]
    markers = [line for line in complete.splitlines() if dbserver.LOOPBACK_ENV in line]
    if not markers:
        return False
    require(markers[0] == dbserver.LOOPBACK_ACK, 'Loopback startup acknowledgement differs')
    observed = []
    allowed = expected['required'] + expected['optional']
    for line in markers[1:]:
        match = dbserver.LOOPBACK_RECORD.fullmatch(line)
        require(match is not None, 'Malformed or non-loopback game listener evidence')
        protocol, address, port = match.groups()
        endpoint = {'protocol': protocol, 'address': address, 'port': int(port)}
        require(endpoint in allowed and endpoint not in observed,
                'Unexpected or duplicate game listener evidence')
        observed.append(endpoint)
    if not all(endpoint in observed for endpoint in expected['required']):
        return False
    return dbserver.validate_loopback(complete, True, expected)


def game_listener_contract(package):
    profile = package.get('game_listener_profile', 'accepted')
    require(profile in ('accepted', 'loopback'), 'Unknown game listener profile')
    if profile == 'accepted':
        require('loopback_game' not in package.get('inputs', {}), 'Unexpected game listener donor')
        return None
    require(package.get('dbserver_profile') == 'loopback', 'Game listener profile requires the loopback DbServer')
    donor = package.get('inputs', {}).get('loopback_game', {})
    manifest = donor.get('manifest', {})
    progress_enabled = package.get('mapserver_progress_profile') == MAP_PROGRESS_PROFILE
    expected_commit = ('ac4c1f7978be444a893f65f5177641191861d42f' if progress_enabled
                       else package.get('repository_commit'))
    require(donor.get('repository_commit') == manifest.get('repository_commit') == expected_commit
            and manifest.get('schema_version') == 1
            and manifest.get('build_role') == 'loopback_game_diagnostic'
            and manifest.get('status') == 'diagnostic_build_packaged_runtime_unverified'
            and manifest.get('configuration') == 'OptDebug' and manifest.get('architecture') == 'Win32'
            and manifest.get('runtime_execution_validated') is False
            and manifest.get('source_commit') == package.get('source_commit')
            and manifest.get('postgresql_persistence_fixture') is False,
            'Game listener donor identity or fixture mode differs')
    encoded = json.dumps(manifest, indent=2) + '\n'
    require(donor.get('manifest_sha256') in {hashlib.sha256(encoded.encode()).hexdigest(),
            hashlib.sha256(encoded.replace('\n', '\r\n').encode()).hexdigest()},
            'Game listener donor receipt bytes differ')
    require(not progress_enabled or donor.get('manifest_sha256') ==
            'd10e61be69555da91cea1f5b4a0f9852f0c564f9a768a91896b485f0774c0791',
            'MapServer progress requires the accepted supporting game listener donor')
    for name in ('MapServer.exe', 'TestClientCreate.exe', 'TestClientResume.exe'):
        record = manifest.get('files', {}).get(name)
        require(isinstance(record, dict) and type(record.get('size')) is int and record['size'] > 0,
                'Game listener donor file record differs')
        normalized = {key: value for key, value in record.items() if key != 'size'}
        normalized['bytes'] = record['size']
        require((name == 'MapServer.exe' and package.get('mapserver_progress_profile') == MAP_PROGRESS_PROFILE)
                or dbserver.exact_contract(package.get('files', {}).get(name), normalized),
                'Game listener executable differs from its source-bound donor')
    variants = manifest.get('variants', {})
    require(set(variants) == {'creation', 'resume'}, 'Game listener donor variants differ')
    metadata = variants['creation'].get('build_input', {}).get('loopback_only')
    require(dbserver.exact_contract(metadata, evidence.GAME_LOOPBACK_METADATA),
            'Game listener metadata differs')
    require(dbserver.exact_contract(metadata, variants['resume'].get('build_input', {}).get('loopback_only')),
            'Game listener variants use different binding policies')
    return metadata


def mapserver_progress_contract(package):
    """Bind the opt-in binary, complete source receipt and exact publication ABI."""
    profile = package.get('mapserver_progress_profile')
    if profile is None:
        require('mapserver_progress' not in package.get('inputs', {}), 'Unexpected MapServer progress donor')
        return None
    require(profile == MAP_PROGRESS_PROFILE, 'Unknown MapServer progress profile')
    require(package.get('dbserver_profile') == 'loopback' and package.get('game_listener_profile') == 'loopback',
            'MapServer progress requires both explicit loopback profiles')
    if 'native_responsiveness' in package:
        import native_responsiveness_contract as native_candidate
        candidate = native_candidate.events_progress_contract(package)
        require(candidate['contract'] == map_progress_module().validate_contract(
                    candidate['contract'], source=True),
                'Native candidate changed the accepted progress ABI')
        return candidate
    donor = package.get('inputs', {}).get('mapserver_progress', {})
    manifest = donor.get('manifest', {})
    require(donor.get('repository_commit') == manifest.get('repository_commit') == package.get('repository_commit')
            and isinstance(package.get('repository_commit'), str)
            and dbserver.COMMIT.fullmatch(package['repository_commit'])
            and manifest.get('schema_version') == 1 and manifest.get('build_role') == 'mapserver_progress'
            and manifest.get('status') == 'diagnostic_build_packaged_runtime_unverified'
            and manifest.get('configuration') == 'OptDebug' and manifest.get('architecture') == 'Win32'
            and manifest.get('postgresql_persistence_fixture') is False
            and manifest.get('runtime_execution_validated') is False
            and manifest.get('build_targets') == ['MapServer']
            and manifest.get('source_commit') == package.get('source_commit')
            and manifest.get('data_commit') == package.get('data_commit'),
            'MapServer progress donor identity or fixture mode differs')
    encoded = json.dumps(manifest, indent=2) + '\n'
    require(donor.get('manifest_sha256') in {hashlib.sha256(encoded.encode()).hexdigest(),
            hashlib.sha256(encoded.replace('\n', '\r\n').encode()).hexdigest()},
            'MapServer progress donor receipt bytes differ')
    build = manifest.get('build_input', {})
    contract = map_progress_module().validate_contract(manifest.get('progress_contract'), source=True)
    require(build.get('schema_version') == 1 and build.get('build_role') == 'mapserver_progress'
            and build.get('source_commit') == package.get('source_commit')
            and build.get('build_targets') == ['MapServer'] and build.get('runtime_validation') == 'unverified'
            and dbserver.exact_contract(build.get('progress_contract'), contract),
            'MapServer progress source receipt differs')
    game_build = build.get('game_build_input')
    require(isinstance(game_build, dict) and build.get('game_build_input_canonical_sha256') == hashlib.sha256(
                json.dumps(game_build, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'MapServer progress base source receipt digest differs')
    source_record = manifest.get('files', {}).get('mapserver-progress-build-input.json', {})
    source = json.dumps(build, indent=2) + '\n'
    require(any(source_record.get('size') == len(raw) and source_record.get('sha256') == hashlib.sha256(raw).hexdigest()
                for raw in (source.encode(), source.replace('\n', '\r\n').encode())),
            'MapServer progress source receipt bytes differ')
    record = manifest.get('files', {}).get('MapServer.exe')
    require(isinstance(record, dict) and type(record.get('size')) is int and record['size'] > 0,
            'MapServer progress binary record differs')
    normalized = {key: value for key, value in record.items() if key != 'size'}
    normalized['bytes'] = record['size']
    require(dbserver.exact_contract(package.get('files', {}).get('MapServer.exe'), normalized),
            'MapServer progress executable differs from its source-bound donor')
    return {'contract': contract, 'producer': {'repository_commit': donor['repository_commit'],
            'manifest_sha256': donor['manifest_sha256'], 'mapserver_sha256': record['sha256']}}


def fixed_input_snapshot(runtime, schema_paths, check=lambda: None):
    """Bind the schema/configuration union; generated caches outside it remain writable."""
    def checked_path(name, directory=False):
        path = runtime
        require(path.is_dir() and not path.is_symlink(), 'Invalid fixed-input runtime')
        for part in safe_path(name).parts:
            path /= part
            info = path.lstat()
            require(not stat.S_ISLNK(info.st_mode), 'Linked fixed input refused')
        require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode),
                'Nonregular fixed input refused: ' + name)
        return path

    def inventory():
        checked_path(FIXED_INPUT_ROOT, directory=True)
        files, directories, pending = set(), {}, [FIXED_INPUT_ROOT]
        while pending:
            check()
            name = pending.pop()
            path = checked_path(name, directory=True)
            info = path.lstat()
            directories[name] = (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_ctime_ns)
            require(len(directories) <= FIXED_INPUT_DIRECTORY_LIMIT, 'Fixed-input directory count exceeded bound')
            with os.scandir(path) as entries:
                for entry in entries:
                    relative = name + '/' + entry.name
                    safe_path(relative)
                    require(not entry.is_symlink(), 'Linked fixed input refused')
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(relative)
                        require(len(pending) + len(directories) <= FIXED_INPUT_DIRECTORY_LIMIT,
                                'Fixed-input directory count exceeded bound')
                    else:
                        require(entry.is_file(follow_symlinks=False), 'Nonregular fixed input refused')
                        files.add(relative)
                        require(len(files) <= FIXED_INPUT_FILE_LIMIT, 'Fixed-input file count exceeded bound')
        return files, directories

    schema_paths = set(schema_paths)
    for name in schema_paths:
        require(safe_path(name).parts[0] == 'data', 'Fixed schema path must remain under data')
    config_files, directories = inventory()
    names = config_files | schema_paths
    require(0 < len(names) <= FIXED_INPUT_FILE_LIMIT, 'Fixed-input file count exceeded bound')
    require(len({name.casefold() for name in names}) == len(names), 'Case-conflicting fixed inputs refused')
    files, identities, total = {}, {}, 0
    for name in sorted(names):
        check()
        path = checked_path(name)
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(descriptor)
            require(stat.S_ISREG(before.st_mode) and before.st_uid == os.getuid() and before.st_nlink == 1,
                    'Fixed input must be an owned regular file with one link')
            total += before.st_size
            require(total <= FIXED_INPUT_BYTE_LIMIT, 'Fixed-input bytes exceeded bound')
            identity = lambda item: (item.st_dev, item.st_ino, item.st_size,
                                     item.st_mtime_ns, item.st_ctime_ns, item.st_nlink)
            hashed, count = hashlib.sha256(), 0
            while True:
                check()
                chunk = os.read(descriptor, min(1024 * 1024, before.st_size - count + 1))
                if not chunk:
                    break
                count += len(chunk)
                require(count <= before.st_size, 'Fixed input grew during hashing')
                hashed.update(chunk)
            require(count == before.st_size and identity(before) == identity(os.fstat(descriptor))
                    == identity(checked_path(name).lstat()), 'Fixed input changed during hashing')
            files[name] = {'bytes': count, 'sha256': hashed.hexdigest()}
            identities[name] = identity(before)
        finally:
            os.close(descriptor)
    require(inventory() == (config_files, directories), 'Fixed-input directory inventory changed during hashing')
    payload = {'files': files, 'directories': sorted(directories)}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {**payload, 'inventory_sha256': digest, 'file_count': len(files), 'total_bytes': total}, {
        'files': identities, 'directories': directories}


class GameContext(dbserver.DbServerContext):
    """A separate bounded game budget; accepted M2/M3 lifecycle is unchanged."""
    def start(self, label, argv, *, env=None, input_text=None, cleanup=False):
        if not cleanup:
            self.check()
        require(len(self.children) < PROCESS_LIMIT, 'Game process count exceeded bound')
        child = base.OwnedProcess(label, argv, env or os.environ.copy(), input_text)
        self.children.append(child)
        return child

    def log_paths(self):
        if self.log_root is None:
            return []
        # UtilitiesLib/log.c:logSetDir writes under the data root's sibling
        # logs/. Avoid rescanning 173k immutable input files on every poll.
        paths = list(self.log_root.glob('*.log'))
        logs = self.log_root / 'logs'
        require(not logs.is_symlink(), 'Linked game log root refused')
        if logs.exists():
            paths.extend(logs.rglob('*.log'))
        require(len(paths) <= 128 and all(p.is_file() and not p.is_symlink() for p in paths),
                'Invalid or excessive game logs')
        sizes = [p.stat().st_size for p in paths]
        require(all(size <= CONSOLE_LIMIT for size in sizes) and sum(sizes) <= 64 * 1024 * 1024,
                'Game log capture exceeded bound')
        return paths


class BridgeSession:
    def __init__(self, diagnostic, label, executable, arguments):
        self.diagnostic, self.ctx, self.label = diagnostic, diagnostic.ctx, label
        self.root = diagnostic.root / ('bridge-' + label + '-' + secrets.token_hex(6))
        self.root.mkdir(mode=0o700)
        self.commands = 0
        self.acknowledged_commands = 0
        self.last_event_count = 0
        self.stopped = False
        self.proof_complete = False
        argv = ['/usr/bin/env', '--chdir=' + str(diagnostic.runtime), diagnostic.args.wine,
                base.windows_path(diagnostic.runtime / 'TestClientBridge.exe'),
                '--output', base.windows_path(self.root), '--version', diagnostic.package['client_version'],
                '--timeout', '1200', '--', base.windows_path(diagnostic.runtime / executable), *arguments]
        self.child = self.ctx.start('bridge-' + label, argv, env=diagnostic.game_environment(executable))

    def small(self, name):
        path = self.root / name
        return dbserver.load_json(path, 16384) if path.exists() else None

    def events(self):
        path = self.root / 'events.jsonl'
        if not path.exists():
            return []
        require(path.is_file() and not path.is_symlink() and path.stat().st_size <= EVENT_LIMIT,
                'Bridge events exceeded bound')
        raw = path.read_bytes()
        lines = raw.split(b'\n')[:-1]  # A currently appended final fragment is not evidence.
        require(len(lines) <= 50000, 'Bridge event count exceeded bound')
        values = [json.loads(line) for line in lines]
        for sequence, value in enumerate(values, 1):
            require(isinstance(value, dict) and value.get('sequence') == sequence
                    and all(isinstance(value.get(key), str) for key in ('kind', 'value', 'raw'))
                    and type(value.get('elapsed_ms')) is int and value['elapsed_ms'] >= 0,
                    'Malformed or reordered bridge evidence')
            require(value['kind'] != 'BridgeError', 'Bridge reported an error: ' + value['value'])
        require(len(values) >= self.last_event_count, 'Bridge event evidence was truncated')
        self.last_event_count = len(values)
        return values

    def console(self):
        path = self.root / 'console.txt'
        if not path.exists():
            return ''
        require(path.is_file() and not path.is_symlink() and path.stat().st_size <= CONSOLE_LIMIT,
                'Bridge console exceeded bound')
        return path.read_text(encoding='utf-8', errors='replace')

    def ready(self):
        value = self.small('ready.json')
        if value is None:
            return None
        require(value.get('format') == 1 and type(value.get('child_pid')) is int
                and value['child_pid'] > 0 and value.get('transport_pid') == value['child_pid']
                and all(value.get(name) is True for name in ('console_attached', 'pipe_pid_verified',
                    'protocol_pid_verified', 'initial_snapshot')) and value.get('version_requests') == 1,
                'Bridge did not bind the observed console and pipe to its launched Windows process')
        return value

    def check(self, *, require_live=False):
        self.events()
        self.console()
        result = self.small('result.json')
        if result is not None:
            require(result.get('error') is None, 'Bridge failed: ' + str(result.get('error')))
            require(not require_live or result.get('child_exit_code') is None,
                    'TestClient exited before its live-session proof')
            require(self.proof_complete or result.get('child_forced_stop') is False,
                    'TestClient was forcibly stopped before save proof')
        if self.child.process.poll() is not None:
            require(result is not None and self.child.process.returncode == 0,
                    'Bridge exited without a successful receipt')
            require(not require_live, 'Bridge exited before its live-session proof')

    def send(self, command):
        self.check(require_live=True)
        require(self.ready() is not None and isinstance(command, str) and command.isascii()
                and 0 < len(command) <= 4096 and not any(c in command for c in '\r\n\0')
                and self.commands < 64, 'Invalid or excessive bridge command')
        self.commands += 1
        path = self.root / ('command-' + str(self.commands).zfill(6) + '.txt')
        require(not path.exists(), 'Bridge command would overwrite prior control')
        base.private_write(path, command)
        def acknowledged():
            records = [item for item in self.events() if item['kind'] == 'Command'
                       and item.get('command_sequence') == self.commands]
            require(len(records) <= 1, 'Bridge duplicated a command acknowledgement')
            if not records:
                return False
            require(records[0]['value'] == command, 'Bridge acknowledged a different command')
            return True
        self.diagnostic.wait(acknowledged, 15, 'Bridge command acknowledgement', session=self)
        self.acknowledged_commands = self.commands
        return self.commands

    def stop(self):
        require(self.proof_complete and self.acknowledged_commands == self.commands,
                'Bridge stop requires completed save proof and command acknowledgements')
        if not self.stopped:
            base.private_write(self.root / 'stop', 'stop\n')
            self.stopped = True
        deadline = time.monotonic() + 17
        while self.child.process.poll() is None or self.child.reader.is_alive():
            self.ctx.check()
            require(time.monotonic() < deadline, 'Bridge did not finish its bounded final capture')
            time.sleep(.05)
        result = self.small('result.json')
        ready = self.ready()
        require(result is not None and ready is not None and self.child.process.returncode == 0
                and result.get('child_pid') == ready['child_pid'] and result.get('error') is None
                and result.get('final_snapshot') is True and result.get('pipe_framing_complete') is True
                and result.get('pipe_disconnected') is True and type(result.get('child_exit_code')) is int
                and result.get('capture_byte_limit') == CONSOLE_LIMIT and result.get('event_byte_limit') == EVENT_LIMIT
                and result.get('version_requests') == 1 and result.get('command_count') == self.commands,
                'Bridge final capture or control receipt is incomplete')
        events = self.events()
        require(result.get('event_count') == len(events), 'Bridge final event count differs')
        path = self.root / 'events.jsonl'
        require(not path.exists() or path.read_bytes().endswith(b'\n'), 'Bridge retained incomplete final event')
        self.ctx.record(self.child, refresh=True)
        return {'ready': ready, 'result': result, 'proof_completed_before_stop': self.proof_complete,
                'console_sha256': hashlib.sha256(self.console().encode()).hexdigest(),
                'events_sha256': base.file_hash(path), 'commands': self.commands}


class GameDiagnostic(dbserver.DbServerDiagnostic):
    def observe_odbc_failure(self, child):
        # Context.run invokes this while the timed-out query still exists,
        # before child.stop() can discard the decisive waiting state.
        hang_evidence.capture(self, child)

    def __init__(self, args, context):
        self.package = dbserver.load_json(args.game_package / 'game-package.json')
        self.data = dbserver.load_json(args.game_data / 'game-data-manifest.json', 64 * 1024 * 1024)
        self.schema = dbserver.load_json(args.schema / 'schema-manifest.json')
        require(self.package.get('format') == 1 and self.package.get('role') == 'wine_game_runtime',
                'Invalid game executable package')
        require(self.data.get('format') == 1 and self.data.get('scope') == 'reviewed_game_data'
                and self.schema.get('scope') == 'accepted_generated_schema_inputs', 'Invalid accepted game/schema input')
        for name in ('source_commit', 'data_commit'):
            require(dbserver.COMMIT.fullmatch(self.package.get(name, ''))
                    and self.data.get(name) == self.package[name] and self.schema.get(name) == self.package[name],
                    'Game/schema source pin mismatch')
        require(dbserver.COMMIT.fullmatch(self.package.get('repository_commit', '')),
                'Game harness repository identity missing')
        version = self.package.get('client_version')
        require(isinstance(version, str) and version.isascii() and 0 < len(version) <= 128
                and not any(ord(c) < 32 for c in version), 'Missing explicit TestClient launcher version')
        files = self.package.get('files', {})
        require(all(name in files for name in EXES), 'Missing game executable')
        dbserver.verify_inventory(args.game_package, files, manifest='game-package.json', binary=True)
        for name in files:
            base.verify_pe32(args.game_package / name)
        dbserver.verify_inventory(args.schema, self.schema.get('files'), manifest='schema-manifest.json')
        require(self.schema.get('schema_status') == 'schema_data_only_outputs_checked_runtime_unvalidated'
                and isinstance(self.schema.get('expected_tables'), dict)
                and isinstance(self.schema.get('expected_attributes'), dict), 'Schema acceptance is incomplete')
        base.Diagnostic.__init__(self, args, context)
        self.created_databases, self.private_connections = [], []
        self.services, self.sessions = [], []
        for environment in (self.base_env, self.wine_env):
            environment.pop(dbserver.FIXED_INPUTS_ENV, None)
            environment.pop(dbserver.LOOPBACK_ENV, None)
            environment.pop(evidence.GAME_LOOPBACK_ENV, None)
            environment.pop(MAP_PROGRESS_ENVIRONMENT, None)
        self.loopback_contract = game_loopback_contract(self.package)
        self.loopback_enabled = self.loopback_contract is not None
        self.game_listener_metadata = game_listener_contract(self.package)
        self.game_listener_enabled = self.game_listener_metadata is not None
        self.map_progress_contract = mapserver_progress_contract(self.package)
        self.map_progress_paths, self.map_progress_previous = {}, {}
        self.map_progress_phase = None
        self.map_progress_next_sample = 0
        fixed_inputs = self.package.get('inputs', {}).get('dbserver', {}).get('manifest', {}).get(
            'wine_build_input', {}).get('fixed_inputs')
        dbserver.validate_fixed_inputs_metadata(fixed_inputs)
        dispatch = self.package.get('inputs', {}).get('dbserver', {}).get('manifest', {}).get(
            'wine_build_input', {}).get('dispatch_progress', {})
        require(dispatch.get('environment_variable') == 'COH_WINE_DB_PROGRESS'
                and dispatch.get('format') == 1 and dispatch.get('record_bytes') == 128
                and dispatch.get('mapping_bytes') == 4096 and isinstance(dispatch.get('stages'), dict),
                'Game DbServer lacks the pinned opt-in dispatch observer')
        self.dispatch_stages = dispatch['stages']
        self.dispatch_paths, self.dispatch_phase = {}, None
        self.completed_logout = False
        self.snapshots = {}
        self.query_count = self.readiness_count = 0
        self.runtime = self.root / ('game-' + secrets.token_hex(6))
        self.game = {'status': 'running', 'phases': [], 'map_samples': [], 'character_samples': [], 'sessions': {}}
        if self.loopback_enabled:
            self.game['dbserver_profile'] = 'loopback'
            self.game['loopback_only'] = {'requested': True, 'metadata': self.loopback_contract['metadata']}
        if self.game_listener_enabled:
            self.game['game_listener_profile'] = 'loopback'
            self.game['game_listener_policy'] = {'requested': True, 'metadata': self.game_listener_metadata}
            self.game['client_listener_observations'] = {}
        self.game['fixed_inputs'] = {'requested': True, 'metadata': fixed_inputs,
            'scope': 'accepted_schema_and_db_configuration', 'schema_file_count': 62, 'checks': []}
        self.game['dispatch_progress'] = {'enabled': True, 'format': 1,
            'environment_variable': 'COH_WINE_DB_PROGRESS', 'record_bytes': 128,
            'mapping_bytes': 4096, 'stages': self.dispatch_stages, 'phases': {}, 'is_success_proof': False}
        if self.map_progress_contract is not None:
            self.game['mapserver_progress'] = map_progress_module().evidence(self.map_progress_contract['producer'])
        self.game['startup_policy'] = {'first_atlas_timeout_seconds': 2400, 'restart_atlas_timeout_seconds': 900,
            'startup_query_timeout_seconds': 90, 'first_poll_interval_seconds': 60,
            'restart_poll_interval_seconds': 30, 'live_query_timeout_seconds': 25,
            'overall_timeout_seconds': args.timeout_seconds}
        self.ctx.report['game'] = self.game
        self.ctx.report['inputs'] = {
            'runtime_manifest_sha256': base.file_hash(args.assets / 'runtime-manifest.json'),
            'game_package_sha256': base.file_hash(args.game_package / 'game-package.json'),
            'game_data_manifest_sha256': base.file_hash(args.game_data / 'game-data-manifest.json'),
            'schema_manifest_sha256': base.file_hash(args.schema / 'schema-manifest.json'),
            'source_commit': self.package['source_commit'], 'data_commit': self.package['data_commit'],
            'repository_commit': self.package['repository_commit'],
            'binary_sha256': {name: files[name]['sha256'] for name in EXES}}

    def prepare_runtime(self):
        self.ctx.stage('game_private_runtime')
        files = self.data.get('files')
        require(isinstance(files, dict) and 0 < len(files) <= 250000
                and self.data.get('file_count') == len(files), 'Invalid full game data inventory')
        self.runtime.mkdir(mode=0o700)
        (self.runtime / 'tools').mkdir(mode=0o700)
        created = {self.runtime, self.runtime / 'tools'}
        names, total = {}, 0
        next_progress = time.monotonic()
        for number, (name, record) in enumerate(files.items(), 1):
            self.ctx.check()
            require(safe_path(name).parts[0] == 'data' and name.casefold() not in names,
                    'Unexpected or case-colliding game data path')
            require(isinstance(record, dict) and type(record.get('bytes')) is int and record['bytes'] >= 0
                    and isinstance(record.get('sha256'), str) and dbserver.HEX64.fullmatch(record['sha256']),
                    'Invalid game data digest record')
            total += record['bytes']
            require(total <= 4 * 1024 * 1024 * 1024, 'Game data exceeds byte bound')
            source = regular_path(self.args.game_data, name)
            require(source.stat().st_size == record['bytes'], 'Game data size differs: ' + name)
            target = self.runtime / name
            create_private_parents(target.parent, self.runtime, created)
            shutil.copyfile(source, target)
            require(base.file_hash(target) == record['sha256'], 'Copied game data hash differs: ' + name)
            names[name.casefold()] = name
            if time.monotonic() >= next_progress:
                self.ctx.event('stage', status='running', message='Staging verified game inputs', files=number)
                next_progress = time.monotonic() + 5
        actual = inventory_files(self.args.game_data, self.ctx.check)
        require(actual == set(files) | {'game-data-manifest.json'} and total == self.data.get('total_bytes'),
                'Game data inventory has extra/missing files or bytes')
        for name in self.schema['files']:
            target = self.runtime / names.get(name.casefold(), name)
            create_private_parents(target.parent, self.runtime, created)
            shutil.copyfile(self.args.schema / name, target)
        require(len(self.schema['files']) == 62, 'Fixed-input game schema must contain 62 accepted files')
        self.fixed_schema_paths = {names.get(name.casefold(), name) for name in self.schema['files']}
        for name in self.package['files']:
            shutil.copyfile(self.args.game_package / name, self.runtime / name)
        require(not (self.runtime / 'gamedatadir.txt').exists(), 'External game data roots are forbidden')
        self.ctx.log_root = self.runtime
        self.ctx.passed(input_files=len(files), input_bytes=total, accepted_schema_overlay_files=len(self.schema['files']))

    def bind_fixed_inputs(self):
        require('baseline' not in self.game['fixed_inputs'], 'Fixed-input baseline is already bound')
        baseline, self.fixed_input_identities = fixed_input_snapshot(self.runtime, self.fixed_schema_paths, self.ctx.check)
        self.game['fixed_inputs']['baseline'] = baseline

    def check_fixed_inputs(self, phase):
        phases = ('before-first', 'after-first-save', 'before-restart', 'after-second-save')
        checks = self.game['fixed_inputs']['checks']
        require(len(checks) < len(phases) and phase == phases[len(checks)],
                'Fixed-input check phase is repeated, out of order or exceeds its bound')
        current, identities = fixed_input_snapshot(self.runtime, self.fixed_schema_paths, self.ctx.check)
        require(current == self.game['fixed_inputs']['baseline'] and identities == self.fixed_input_identities,
                'Fixed-input schema or configuration changed: ' + phase)
        self.game['fixed_inputs']['checks'].append({'phase': phase, 'unchanged': True,
            **{key: current[key] for key in ('inventory_sha256', 'file_count', 'total_bytes')}})

    def health(self):
        self.ctx.check()
        require(self.pg is not None and self.pg.process.poll() is None, 'Owned PostgreSQL exited during game proof')
        for service in self.services:
            require(service.process.poll() is None, 'Owned game service exited: ' + service.label)

    def wait(self, predicate, seconds, label, *, session=None, live=False, interval=.2):
        deadline = min(self.ctx.deadline, time.monotonic() + seconds)
        next_progress = time.monotonic()
        while True:
            self.health()
            if session is not None:
                session.check(require_live=live)
            self.sample_map_progress('wait:' + label)
            value = predicate()
            if value:
                return value
            require(time.monotonic() < deadline, 'Timed out waiting for ' + label)
            if time.monotonic() >= next_progress:
                self.ctx.event('stage', status='running', message=label)
                next_progress = time.monotonic() + 5
            time.sleep(interval)

    def game_environment(self, executable, env=None):
        environment = (self.wine_env if env is None else env).copy()
        environment.pop(MAP_PROGRESS_ENVIRONMENT, None)
        environment.pop(dbserver.LOOPBACK_ENV, None)
        environment.pop(evidence.GAME_LOOPBACK_ENV, None)
        if executable == 'DbServer.exe' and getattr(self, 'loopback_enabled', False):
            environment[dbserver.LOOPBACK_ENV] = '1'
        if executable in ('MapServer.exe', 'TestClientCreate.exe', 'TestClientResume.exe') \
                and getattr(self, 'game_listener_enabled', False):
            environment[evidence.GAME_LOOPBACK_ENV] = '1'
        return environment

    def begin_map_progress(self, label):
        if getattr(self, 'map_progress_contract', None) is None:
            return
        require(label in ('first', 'restart') and label not in self.map_progress_paths,
                'MapServer progress phase must be a fresh owned launch')
        path = self.runtime / ('coh-map-progress-' + label + '-' + secrets.token_hex(8) + '.bin')
        require(not path.exists() and not path.is_symlink(), 'Refusing stale MapServer progress record')
        self.map_progress_paths[label], self.map_progress_phase = path, label
        self.game['mapserver_progress']['phases'][label] = {
            'path_name': path.name, 'process_label': label + '-atlas', 'launch_utc': base.utc(),
            'launch_monotonic': time.monotonic(), 'fresh_path_before_launch': True,
            'sample_count': 0, 'dropped_samples': 0, 'samples': []}
        self.sample_map_progress('before-launch', force=True)

    def sample_map_progress(self, reason, *, force=False):
        label = getattr(self, 'map_progress_phase', None)
        if label is None:
            return None
        map_progress = map_progress_module()
        now = time.monotonic()
        if not force and now < self.map_progress_next_sample:
            return None
        self.map_progress_next_sample = now + map_progress.SAMPLE_INTERVAL
        try:
            value = map_progress.read_record(self.map_progress_paths[label], self.map_progress_previous.get(label))
            self.map_progress_previous[label] = value
        except Exception as exc:
            value = dict(hang_evidence.error(exc), sampled_utc=base.utc(), observed_monotonic=now,
                         is_success_proof=False)
        value = dict(value, reason=reason)
        map_progress.append_sample(self.game['mapserver_progress']['phases'][label], value)
        return value

    def start_game(self, label, executable, arguments, *, env=None):
        environment = self.game_environment(executable, env)
        phase = getattr(self, 'map_progress_phase', None)
        if (getattr(self, 'map_progress_contract', None) is not None and phase in ('first', 'restart')
                and label == phase + '-atlas' and executable == 'MapServer.exe'):
            environment[MAP_PROGRESS_ENVIRONMENT] = base.windows_path(self.map_progress_paths[phase])
        child = self.ctx.start(label, ['/usr/bin/env', '--chdir=' + str(self.runtime), self.args.wine,
                               base.windows_path(self.runtime / executable), *arguments],
                               env=environment)
        self.services.append(child)
        if phase is not None and label == phase + '-atlas':
            self.game['mapserver_progress']['phases'][phase]['launcher_pid'] = child.process.pid
        return child

    def query(self, arguments, label, *, timeout=25):
        self.health()
        require(self.query_count < QUERY_LIMIT, 'Game protocol query budget exceeded')
        self.query_count += 1
        result, text = self.run_windows('game-query-' + label, self.runtime / 'MapServer.exe',
            ['-nogui', '-db', '127.0.0.1', '-dbquery', '-timeout', '10000', *arguments],
            self.runtime, timeout=timeout)
        require(result['exit_code'] == 0, 'Game protocol query failed')
        return text

    def map_status(self, label, *, allow_missing=False, timeout=25):
        self.sample_map_progress('before-map-status:' + label, force=True)
        sample = evidence.parse_map_status(self.query(['-getstatus', '1', '1'], label, timeout=timeout), allow_missing=allow_missing)
        self.sample_map_progress('after-map-status:' + label, force=True)
        sample.update(phase=label, sampled_utc=base.utc(), monotonic=time.monotonic())
        self.game['map_samples'].append(sample)
        return sample

    def start_services(self, label):
        self.ctx.stage('game_services_' + label)
        self.check_fixed_inputs('before-' + label)
        for port, protocol in ((6997, socket.SOCK_STREAM), (7001, socket.SOCK_DGRAM)):
            check_game_port(port, protocol)
        require(label in ('first', 'restart') and label not in self.dispatch_paths,
                'Dispatch phase must be a fresh owned launch')
        dispatch_path = self.runtime / ('coh-db-progress-' + label + '.bin')
        require(not dispatch_path.exists() and not dispatch_path.is_symlink(),
                'Refusing stale dispatch record')
        self.dispatch_paths[label], self.dispatch_phase = dispatch_path, label
        database_env = dict(self.wine_env, COH_WINE_DB_PROGRESS=base.windows_path(dispatch_path),
                            COH_WINE_DB_FIXED_INPUTS='1')
        database_env.pop(dbserver.LOOPBACK_ENV, None)
        if self.loopback_enabled:
            database_env[dbserver.LOOPBACK_ENV] = '1'
        database = self.start_game(label + '-dbserver', 'DbServer.exe', ['-start', '0'], env=database_env)
        next_query = 0
        expected_columns = sum(map(len, self.schema['expected_tables'].values()))
        def database_ready():
            nonlocal next_query
            if time.monotonic() < next_query:
                return False
            with socket.socket() as probe:
                probe.settimeout(.2)
                if probe.connect_ex(('127.0.0.1', 6997)) != 0:
                    return False
            next_query = time.monotonic() + 15
            require(self.readiness_count < READINESS_LIMIT, 'SQL readiness query budget exceeded')
            self.readiness_count += 1
            return self.sql("SELECT count(*) FROM information_schema.columns WHERE table_schema='dbo';", game=True) == str(expected_columns)
        self.wait(database_ready, 600, 'DbServer schema and local listener')
        catalog = self.schema_snapshot()
        def published():
            try:
                observation = hang_evidence.read_dispatch_record(dispatch_path, self.dispatch_stages)
            except hang_evidence.DispatchPublicationPending:
                return False
            if observation['loop_count']:
                self.game['dispatch_progress']['phases'][label] = observation
                return observation
            return False
        self.wait(published, 30, 'DbServer main-thread dispatch publication')
        fixed_inputs = self.wait(lambda: fixed_inputs_acknowledgement(database), 30,
                                 'DbServer fixed-input activation acknowledgement')
        if self.loopback_enabled:
            # These listeners are initialized by dbInit before main dispatch
            # under this fake-auth/no-queue/embedded-log configuration, just as
            # in the donor schema gate. This run separately proves Atlas use.
            self.wait(lambda: loopback_acknowledgement(database, self.loopback_contract['endpoints']), 30,
                      'DbServer loopback listener acknowledgements')
        next_baseline = 0
        def unstarted():
            nonlocal next_baseline
            if time.monotonic() < next_baseline:
                return False
            next_baseline = time.monotonic() + 10
            baseline = self.map_status(label + '-baseline', allow_missing=True, timeout=90)
            require(not baseline['ready'], 'Atlas was running before the owned launch')
            return baseline if baseline.get('not_started') else False
        self.wait(unstarted, 60, 'Unstarted Atlas baseline')
        self.begin_map_progress(label)
        atlas = self.start_game(label + '-atlas', 'MapServer.exe', ['-nogui', '-db', '127.0.0.1',
            '-nosharedmemory', '-nostats', '-udp', '7001', '-tcp', '0', '-map_id', '1'])
        self.sample_map_progress('after-launch', force=True)
        next_status = 0
        readiness_timeout = 2400 if label == 'first' else 900
        poll_interval = 60 if label == 'first' else 30
        def ready():
            nonlocal next_status
            if time.monotonic() < next_status:
                return False
            sample = self.map_status(label + '-ready', timeout=90)
            next_status = time.monotonic() + poll_interval
            return sample if evidence.map_ready_current(sample) else False
        sample = self.wait(ready, readiness_timeout, 'Atlas DB-confirmed readiness')
        self.sample_map_progress('startup-ready', force=True)
        phase = {'phase': label + '_services_ready', 'status': 'passed',
                                    'fixed_inputs': fixed_inputs,
                                    'baseline_not_started': True, 'schema': catalog, 'map': sample,
                                    'readiness_timeout_seconds': readiness_timeout,
                                    'query_timeout_seconds': 90, 'poll_interval_seconds': poll_interval}
        if self.loopback_enabled:
            phase['loopback_only'] = dbserver.validate_loopback(database.text(), True,
                                                                self.loopback_contract['endpoints'])
        else:
            dbserver.validate_loopback(database.text(), False, {})
        if getattr(self, 'game_listener_enabled', False):
            require(not atlas.overflow, 'Atlas listener capture overflowed')
            phase['game_listeners'] = self.wait(lambda: evidence.game_listener_bindings(
                atlas.text(), 'atlas', pending=True), 30, 'Atlas actual loopback UDP binding')
        else:
            evidence.game_listener_bindings(atlas.text(), 'atlas', enabled=False)
        self.game['phases'].append(phase)
        self.ctx.passed(baseline_not_started=True, atlas_ready=True, table_count=catalog['table_count'])

    def observe_atlas(self):
        self.ctx.stage('atlas_ready_observation')
        started = time.monotonic()
        samples = []
        while True:
            sample = self.map_status('first-observation')
            self.sample_map_progress('ready-observation', force=True)
            require(evidence.map_ready_current(sample), 'Atlas lost current readiness during observation')
            samples.append(sample)
            elapsed = time.monotonic() - started
            if elapsed >= 30:
                break
            self.wait(lambda: time.monotonic() - started >= min(30, elapsed + 10), 15, 'Observing live Atlas heartbeats')
        self.game['atlas_observation'] = {'seconds': elapsed, 'minimum_seconds': 30, 'samples': samples,
                                         'db_confirmed_ready': True, 'current_heartbeats': True}
        self.ctx.passed(observed_ready_seconds=elapsed, current_heartbeats=True)

    def character_status(self, label, *, allow_missing=False):
        character = self.game['character']
        sample = evidence.parse_character_status(self.query(['-getstatus', '3', str(character['container_id'])], label),
            character['container_id'], character['name'], character['account'], allow_missing=allow_missing)
        self.game['character_samples'].append(dict(sample, phase=label))
        return sample

    def sql_rows(self, table, fields, keys, where='TRUE'):
        require(table in self.schema['expected_tables'] and all(field in self.schema['expected_tables'][table]
                and dbserver.IDENTIFIER.fullmatch(field) for field in fields), 'Character schema contract differs')
        return json.loads(self.sql("SELECT coalesce(json_agg(x ORDER BY " + ','.join(keys)
            + "),'[]'::json) FROM (SELECT " + ','.join(fields) + ' FROM dbo.' + table + ' WHERE ' + where + ') x;', game=True))

    def inventory(self):
        return self.sql_rows('ents', ('containerid', 'authid', 'authname', 'name', 'logincount'), ('containerid',))

    def snapshot(self, login_count):
        character = self.game['character']
        rows = {}
        for table, fields in evidence.SELECTED.items():
            fields = tuple(fields) + (('logincount',) if table == 'ents' else ())
            rows[table] = self.sql_rows(table, fields, evidence.ROW_KEYS[table],
                                       'containerid=' + str(character['container_id']))
        return evidence.validate_snapshot(rows, self.inventory(), self.schema['expected_attributes'],
            character['account'], character['container_id'], character['name'], login_count, 12345)

    def new_client(self, label, *, resume=False):
        args = ['-db', '127.0.0.1', '-fakeauth', '-authname', self.game['account'], '-dontpause', '-nosharedmemory']
        if resume:
            # The legacy GUI WinMain splits on whitespace without CRT quoting.
            require(re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', self.game['character']['name']),
                    'Recorded character cannot be passed unchanged through legacy TestClient arguments')
            args += ['-resumeonly', '-character', self.game['character']['name']]
        else:
            args += ['-nolevel', '-TEAMACCEPT', '-FOLLOW', '-SUPERGROUPACCEPT', '-LEAGUEACCEPT']
        session = BridgeSession(self, label, 'TestClientResume.exe' if resume else 'TestClientCreate.exe', args)
        self.sessions.append(session)
        self.wait(lambda: session.ready(), 120, 'Owned TestClient console and launcher pipe', session=session, live=True)
        return session

    def create_character(self):
        self.ctx.stage('game_create_and_connect')
        require(self.inventory() == [], 'Disposable database already contains a character')
        session = self.new_client('create')
        name = self.wait(lambda: evidence.pipe_identity(session.events(), session.ready(), self.game['account']),
                         600, 'Fresh character launcher identity', session=session, live=True)
        identifier = evidence.parse_find(self.query(['-find', '3', 'Name', name], 'find-created'))
        self.game['character'] = {'container_id': identifier, 'name': name, 'account': self.game['account']}
        next_status = 0
        def connected():
            nonlocal next_status
            if time.monotonic() < next_status:
                return False
            next_status = time.monotonic() + 10
            return evidence.connected_on_atlas(self.character_status('created'))
        self.wait(connected, 300, 'Created character connected on Atlas', session=session, live=True)
        self.observe_client_listeners(session, 'first')
        require('simulateCharacterCreate()' in session.console(), 'Fresh creation branch was not captured')
        self.clean_logs(session=session)
        self.game['created_connected'] = True
        self.ctx.passed(character_id=identifier, map_id=1, fresh_creation_branch=True)
        return session

    def observe_client_listeners(self, session, label):
        if getattr(self, 'game_listener_enabled', False):
            record = self.wait(lambda: evidence.game_listener_bindings(session.console(), 'client', pending=True),
                30, 'TestClient actual loopback UDP bindings', session=session, live=True)
            self.game['client_listener_observations'][label] = record
        else:
            evidence.game_listener_bindings(session.console(), 'client', enabled=False)

    def live_currency(self, session):
        self.ctx.stage('game_live_currency')
        character = self.game['character']
        require(re.fullmatch(r'[A-Za-z0-9 _.-]{1,128}', character['name']), 'Unsafe diagnostic character command name')
        after = session.events()[-1]['sequence']
        session.send('CMD influence 12345')
        next_debug = 0
        def received():
            nonlocal next_debug
            events = session.events()
            evidence.pipe_identity(events, session.ready(), self.game['account'], character['name'])
            value = evidence.live_currency_evidence(events, character['name'], self.game['account'], after)
            if value:
                require(evidence.connected_on_atlas(self.character_status('currency')), 'Character left Atlas before currency proof')
                return value
            if time.monotonic() >= next_debug:
                session.send('CMD debug "' + character['name'] + '"')
                next_debug = time.monotonic() + 10
            return False
        self.game['live_currency'] = self.wait(received, 180, 'Live MapServer influence response', session=session, live=True)
        self.clean_logs(session=session)
        self.ctx.passed(influence=12345, live_entity_confirmed=True, sql_mutation_used=False)

    def logout(self, session, label, login_count):
        self.ctx.stage('game_protocol_logout_' + label)
        self.clean_logs(session=session)
        session.send('CMD quit')
        self.wait(lambda: any(item['kind'] == 'QuitNow' for item in session.events()), 30,
                  'Protocol QuitNow request confirmation', session=session)
        next_status = 0
        def saved():
            nonlocal next_status
            events = session.events()
            evidence.pipe_identity(events, session.ready(), self.game['account'], self.game['character']['name'],
                                   allow_logout_error=True)
            if time.monotonic() < next_status:
                return False
            next_status = time.monotonic() + 10
            status = self.character_status(label + '-logout', allow_missing=True)
            if status['connected'] or status['in_map_transfer']:
                return False
            try:
                return self.snapshot(login_count)
            except base.DiagnosticError as exc:
                self.game['last_pending_save'] = str(exc)
                return False
        snapshot = self.wait(saved, 300, 'Protocol logout and independently committed SQL', session=session)
        self.clean_logs(session=session, allow_logout=True)
        self.completed_logout = True
        self.snapshots[label] = snapshot
        session.proof_complete = True
        receipt = session.stop()
        if getattr(self, 'game_listener_enabled', False):
            receipt['game_listeners'] = evidence.game_listener_bindings(session.console(), 'client')
            earlier = self.game['client_listener_observations'][label]['endpoints']
            require(receipt['game_listeners']['endpoints'][:len(earlier)] == earlier,
                    'Final TestClient bind capture lost live-session evidence')
        final_events = session.events()
        require(evidence.pipe_identity(final_events, session.ready(), self.game['account'], self.game['character']['name'],
                    allow_logout_error=True), 'Final launcher identity is incomplete')
        if any(item['kind'] == 'Status' and item['value'].strip() == 'ERROR' for item in final_events):
            require(any(line.strip() == 'Fatal Error: Booted back to login screen'
                        for line in session.console().splitlines()),
                    'Post-quit client error lacks the known requested logout diagnostic')
        self.clean_logs(session=session, allow_logout=True)
        self.game['sessions'][label] = receipt
        proof = {'protocol_quit': True, 'quitnow_is_save_ack': False, 'disconnected_before_sql': True,
                 'independent_committed_sql': True, 'forced_stop_before_save': False,
                 'login_count': snapshot['login_count'], 'influence': 12345,
                 'snapshot_sha256': hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                 'row_counts': {table: len(rows) for table, rows in snapshot['rows'].items()}}
        self.game[label + '_save'] = proof
        self.ctx.passed(**proof)
        return snapshot

    def clean_logs(self, *, session=None, allow_logout=False):
        texts = [child.text() for child in self.services]
        for child, text in zip(self.services, texts):
            if getattr(child, 'label', None) in ('first-dbserver', 'restart-dbserver'):
                enabled = self.loopback_enabled
                dbserver.validate_loopback(text, enabled,
                    self.loopback_contract['endpoints'] if enabled else {})
                require(evidence.GAME_LOOPBACK_ENV not in text, 'Game binding mode leaked into DbServer')
            elif getattr(child, 'label', None) in ('first-atlas', 'restart-atlas'):
                require(not getattr(child, 'overflow', False), 'Atlas listener capture overflowed')
                evidence.game_listener_bindings(text, 'atlas', enabled=getattr(self, 'game_listener_enabled', False))
        texts.extend(path.read_text(encoding='utf-8', errors='replace') for path in self.ctx.log_paths())
        failures = []
        for text in texts:
            failures.extend(evidence.diagnostic_failures(text,
                allow_requested_logout=allow_logout or self.completed_logout))
        if session is not None:
            evidence.game_listener_bindings(session.console(), 'client',
                                            enabled=getattr(self, 'game_listener_enabled', False))
            failures.extend(evidence.diagnostic_failures(session.console(), allow_requested_logout=allow_logout))
        require(not failures, 'Game diagnostic failure: ' + '\n'.join(base.redact(line, self.ctx.secrets) for line in failures[:20]))

    def restart(self, before):
        self.ctx.stage('game_restart')
        self.sample_map_progress('before-restart-stop', force=True)
        self.map_progress_phase = None
        self.dispatch_phase = None
        self.services.clear()
        stopped = self.ctx.run('game-wine-stop', [self.args.wineserver, '-k'], timeout=3, env=self.wine_env, check=False)
        self.ctx.run('game-wine-wait', [self.args.wineserver, '-w'], timeout=5, env=self.wine_env)
        require(stopped['exit_code'] in (0, 1), 'Wine service stop failed')
        shutdown = base.verify_wine_stopped(self.wineprefix)
        owned = dict(self.wine_owner.cleanup(min(self.ctx.deadline, time.monotonic() + 6)))
        for child in self.ctx.children:
            if child in (self.pg, self.xserver):
                continue
            child.reader.join(timeout=1)
            require(child.process.poll() is not None and not child.reader.is_alive() and not child.writer.is_alive(),
                    'Wine service capture did not close before restart: ' + child.label)
            self.ctx.record(child, refresh=True)
        self.stop_postgres()
        self.ctx.passed(wine_prefix_stopped=True, postgres_graceful=True, **shutdown)
        self.start_postgres('postgres_game_restart')
        self.start_services('restart')
        after = self.snapshot(1)
        self.snapshots['restart'] = after
        comparison = evidence.compare_snapshots(before, after, 'restart')
        self.game['restart'] = {'same_cluster': True, 'same_database': True, 'no_reseed_or_restore': True,
                                'wine_shutdown': shutdown, 'owned_cleanup': owned,
                                'snapshot_sha256': hashlib.sha256(json.dumps(after, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest(), **comparison}

    def resume(self):
        self.ctx.stage('game_resume_exact_name')
        session = self.new_client('resume', resume=True)
        character = self.game['character']
        def received():
            text = session.console()
            if 'COH_RESUME_ONLY_SERVER_UPDATE' not in text:
                return False
            if not evidence.pipe_identity(session.events(), session.ready(), self.game['account'], character['name']):
                return False
            return evidence.accept_sustained_resume(text, session.events(), session.ready(), self.game['account'],
                                                   character['name'], character['container_id'])
        proof = self.wait(received, 600, 'Exact-name resume and processed server entity update', session=session, live=True)
        next_status = 0
        def connected():
            nonlocal next_status
            if time.monotonic() < next_status:
                return False
            next_status = time.monotonic() + 10
            return evidence.connected_on_atlas(self.character_status('resumed'))
        self.wait(connected, 300, 'Resumed character connected on Atlas', session=session, live=True)
        self.observe_client_listeners(session, 'second')
        self.clean_logs(session=session)
        self.game['resume'] = dict(proof, creation_disabled=True, connected_on_atlas=True, processed_server_update=True)
        self.ctx.passed(creation_disabled=True, exact_name=True, processed_server_update=True, map_id=1)
        return session

    def execute(self):
        self.prepare_runtime()
        self.initialize()
        self.start_postgres('postgres_first_start')
        self.prepare_database()
        self.start_wine()
        self.ctx.stage('win32_runtime_dll')
        result = self.ctx.run('runtime-probe', [self.args.wine, base.windows_path(self.args.assets / 'runtime-probe.exe')],
                              timeout=60, env=self.wine_env)
        self.ctx.passed(**base.validate_runtime_probe(result['output']))
        self.mark_wine_ready()
        config = self.runtime / 'data/server/db/servers.cfg'
        base.private_write(config, game_config(config.read_text(), self.database, self.connection_for(self.database)))
        self.private_connections.append(config)
        self.bind_fixed_inputs()
        self.game['account'] = 'CohA' + secrets.token_hex(5)
        self.start_services('first')
        self.observe_atlas()
        session = self.create_character()
        self.live_currency(session)
        first = self.logout(session, 'first', 1)
        self.check_fixed_inputs('after-first-save')
        self.restart(first)
        resumed = self.resume()
        second = self.logout(resumed, 'second', 2)
        self.check_fixed_inputs('after-second-save')
        self.game['second_save']['comparison'] = evidence.compare_snapshots(first, second, 'second_logout')
        final_schema = self.schema_snapshot()
        self.game['attributes_unchanged'] = final_schema['attribute_sha256'] == self.game['phases'][0]['schema']['attribute_sha256']
        require(self.game['attributes_unchanged'], 'Character sessions changed generated attribute IDs')
        self.clean_logs()
        self.sample_map_progress('before-success-cleanup', force=True)
        self.game.update(status='passed', query_processes=self.query_count, readiness_queries=self.readiness_count,
                         process_budget=PROCESS_LIMIT, query_budget=QUERY_LIMIT)

    def export_captures(self):
        """Export only bounded diagnostic evidence, including partial failed runs."""
        root = self.args.state / 'game-captures'
        require(not root.exists(), 'Refusing stale game captures')
        root.mkdir(mode=0o700)
        inventory = {}
        def write(name, text, limit):
            require(len(text.encode()) <= limit, 'Exported game capture exceeded bound')
            path = root / name
            base.private_write(path, text)
            inventory[name] = {'bytes': path.stat().st_size, 'sha256': base.file_hash(path)}
        for session in self.sessions:
            label = {'create': 'first', 'resume': 'second'}[session.label]
            for name, limit in (('ready.json', 16384), ('result.json', 16384),
                                ('events.jsonl', EVENT_LIMIT), ('console.txt', CONSOLE_LIMIT)):
                path = session.root / name
                if not path.exists():
                    continue
                require(path.is_file() and not path.is_symlink() and path.stat().st_size <= limit,
                        'Invalid or oversized bridge capture')
                raw = path.read_text(encoding='utf-8', errors='replace')
                if name.endswith('.json'):
                    text = json.dumps(base.redacted_value(json.loads(raw), self.ctx.secrets), sort_keys=True) + '\n'
                elif name.endswith('.jsonl'):
                    # Only complete records are reviewable if capture failed mid-write.
                    text = ''.join(json.dumps(base.redacted_value(json.loads(line), self.ctx.secrets),
                                              separators=(',', ':')) + '\n' for line in raw.split('\n')[:-1])
                else:
                    text = base.redact(raw, self.ctx.secrets)
                write(label + '-' + name, text, limit)
                receipt = self.game['sessions'].get(label)
                if receipt is not None and name in ('events.jsonl', 'console.txt'):
                    receipt['events_sha256' if name == 'events.jsonl' else 'console_sha256'] = inventory[label + '-' + name]['sha256']
        for label, snapshot in self.snapshots.items():
            value = base.redacted_value(snapshot, self.ctx.secrets)
            write(label + '-snapshot.json', json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n', 1024 * 1024)
        if 'mapserver_progress' in self.game:
            write('mapserver-progress.json', json.dumps(self.game['mapserver_progress'], indent=2) + '\n',
                  map_progress_module().EXPORT_LIMIT)
        self.game['capture_files'] = inventory

    def export_service_captures(self):
        """Keep full bounded owned stdout and explicit bounded startup/log tails."""
        root = self.args.state / 'game-service-captures'
        require(not root.exists(), 'Refusing stale game service captures')
        root.mkdir(mode=0o700)
        files, inventory = {}, {}
        manifest = {'format': 1, 'files': files, 'selected_log_limit': 32,
                    'log_segment_bytes': SERVICE_LOG_SEGMENT, 'unselected_logs': 0}
        def write(name, text, limit, metadata):
            require(len(text.encode()) <= limit, 'Game service capture exceeded export bound')
            path = root / name
            base.private_write(path, text)
            inventory[name] = {'bytes': path.stat().st_size, 'sha256': base.file_hash(path)}
            files[name] = {**inventory[name], **metadata}
        try:
            for label in SERVICE_LABELS:
                matches = [child for child in self.ctx.children if child.label == label]
                require(len(matches) <= 1, 'Repeated service process label')
                if not matches:
                    continue
                child = matches[0]
                require(len(child.output) <= base.OUTPUT_LIMIT, 'Owned service capture exceeded original bound')
                write(label + '-stdout.txt', base.redact(child.text(), self.ctx.secrets), SERVICE_STDOUT_LIMIT,
                      {'kind': 'owned_service_stdout', 'process_label': label,
                       'original_bytes': len(child.output), 'truncated': child.overflow,
                       'capture_closed': not child.reader.is_alive(), 'overflow': child.overflow})
            log_root = self.ctx.log_root
            paths = []
            if log_root is not None:
                require(not log_root.is_symlink() and log_root.is_dir(), 'Invalid service log root')
                pending, examined = [log_root], 0
                while pending:
                    directory = pending.pop()
                    with os.scandir(directory) as entries:
                        for entry in entries:
                            examined += 1
                            require(examined <= 4096, 'Service log inventory exceeds bound')
                            path = Path(entry.path)
                            # Only root *.log and the engine-owned logs/ subtree.
                            if directory == log_root and entry.name != 'logs' and not entry.name.endswith('.log'):
                                continue
                            require(not entry.is_symlink(), 'Linked service log refused')
                            if entry.is_dir(follow_symlinks=False):
                                if directory != log_root or entry.name == 'logs':
                                    pending.append(path)
                            else:
                                require(entry.is_file(follow_symlinks=False), 'Nonregular service log refused')
                                if entry.name.endswith('.log'):
                                    paths.append(path)
            paths.sort(key=lambda path: path.relative_to(log_root).as_posix())
            manifest['unselected_logs'] = max(0, len(paths) - 32)
            for number, path in enumerate(paths[:32], 1):
                with path.open('rb') as source:
                    size = os.fstat(source.fileno()).st_size
                    raw = source.read(2 * SERVICE_LOG_SEGMENT)
                    truncated = size > 2 * SERVICE_LOG_SEGMENT
                    if truncated:
                        source.seek(-SERVICE_LOG_SEGMENT, os.SEEK_END)
                        raw = raw[:SERVICE_LOG_SEGMENT] + b'\n[diagnostic capture: middle omitted]\n' + source.read(SERVICE_LOG_SEGMENT)
                write('log-' + str(number).zfill(3) + '.txt',
                      base.redact(raw.decode('utf-8', errors='replace'), self.ctx.secrets), SERVICE_LOG_LIMIT,
                      {'kind': 'runtime_log', 'source_relative_path': path.relative_to(log_root).as_posix(),
                       'original_bytes': size, 'truncated': truncated})
        except Exception as exc:
            manifest['inspection_failure'] = base.redact(str(exc), self.ctx.secrets)
            raise
        finally:
            text = json.dumps(manifest, indent=2) + '\n'
            require(len(text.encode()) <= 128 * 1024, 'Service capture manifest exceeds bound')
            path = root / 'manifest.json'
            base.private_write(path, text)
            inventory['manifest.json'] = {'bytes': path.stat().st_size, 'sha256': base.file_hash(path)}
            self.game['service_capture_files'] = inventory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name, default in (('state', '/state'), ('assets', '/opt/coh'), ('game-package', '/opt/coh-game-package'),
                          ('game-data', '/opt/coh-game-data'), ('schema', '/opt/coh-schema'),
                          ('pg-bin', '/opt/coh/pgsql/bin'), ('wine', '/opt/wine/bin/wine'),
                          ('wineserver', '/opt/wine/bin/wineserver'), ('xserver', '/usr/bin/Xtigervnc')):
        parser.add_argument('--' + name, type=Path, default=Path(default))
    parser.add_argument('--timeout-seconds', type=int, default=3600)
    parser.add_argument('--execution-platform', choices=('host',), default='host')
    args = parser.parse_args(argv)
    args.client_probe = False
    os.umask(0o077)
    context = GameContext(args.state, args.timeout_seconds)
    context.report.update(diagnostic_mode='atlas_character_persistence', execution_platform_requested='host',
        scope='Managed Atlas MapServer, stock fake-auth create/save, restart and diagnostic exact-name resume through ARM64 Wine/FEX',
        android_execution_validated=False, gameplay_validated=False, android_surface_validated=False,
        hardware_acceleration_validated=False, interactive_rendering_validated=False)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda _sig, _frame: setattr(context, 'cancel_requested', True))
    diagnostic = None
    try:
        require(60 <= args.timeout_seconds <= 7200, 'Timeout must be60 to7200 seconds')
        context.check()
        diagnostic = GameDiagnostic(args, context)
        diagnostic.execute()
        context.report['status'] = 'passed'
    except base.Cancelled as exc:
        context.report.update(status='cancelled', failures=[str(exc)])
    except Exception as exc:
        context.report.update(status='failed', failures=[str(exc)])
    finally:
        if diagnostic is not None:
            if context.report['status'] == 'failed':
                try:
                    # Covers failures raised outside run_windows. A pre-stop
                    # snapshot is never replaced by this later observation.
                    hang_evidence.capture(diagnostic)
                except Exception as exc:
                    context.report.setdefault('observation_failures', []).append(
                        'Cannot capture pre-cleanup game evidence: ' + str(exc))
            try:
                context.report['failures'].extend(diagnostic.cleanup())
            except Exception as exc:
                context.report['failures'].append('Owned cleanup failed: ' + str(exc))
            try:
                diagnostic.export_captures()
            except Exception as exc:
                context.report['failures'].append('Cannot export bounded game evidence: ' + str(exc))
            try:
                diagnostic.export_service_captures()
            except Exception as exc:
                context.report['failures'].append('Cannot export bounded service evidence: ' + str(exc))
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
