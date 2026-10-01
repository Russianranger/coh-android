#!/usr/bin/env python3
"""Owned Atlas service and read-only proof of one graphical character save."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import time
import zipfile

import local_login_server as login
import game_device_diagnostic as device
import game_evidence as evidence
import game_map_progress as progress

base, game, dbserver, require = login.base, login.game, login.dbserver, login.require
PROFILE, ACCOUNT, CHARACTER = login.PROFILE, login.ACCOUNT, 'THORHERO'
POLL_SECONDS = 15
MAP_STARTUP_SECONDS = 2400
SNAPSHOT_LIMIT = 2 * 1024 * 1024
LOGOUT_RECEIPT_LIMIT = 512
LOGOUT_MAX_AGE_MS = 120000
SERVER_LOG_FILE_LIMIT = 16 * 1024 * 1024
SERVER_LOG_TOTAL_LIMIT = 64 * 1024 * 1024
SERVER_LOG_COUNT_LIMIT = 128


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def read_logout_delivery(path, session, client_pid, character_id, ready_utc_ms, now_utc_ms):
    """Read the input sender's receipt; this is not a network-packet receipt."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid()
                and info.st_nlink == 1 and 0 < info.st_size <= LOGOUT_RECEIPT_LIMIT,
                'Invalid character logout delivery file')
        with os.fdopen(fd, 'rb', closefd=False) as source:
            raw = source.read(LOGOUT_RECEIPT_LIMIT + 1)
        after = os.fstat(fd)
        require(len(raw) == info.st_size and len(raw) <= LOGOUT_RECEIPT_LIMIT
                and (after.st_size, after.st_mtime_ns, after.st_nlink)
                    == (info.st_size, info.st_mtime_ns, info.st_nlink),
                'Character logout delivery changed or exceeded bound')
    finally:
        os.close(fd)
    value = json.loads(raw.decode('utf-8'))
    require(isinstance(value, dict) and set(value) == {
                'format', 'session_id', 'client_pid', 'character_id', 'action', 'sent_utc_ms'}
            and type(value['format']) is int and value['format'] == 1
            and isinstance(value['session_id'], str) and re.fullmatch(r'[0-9a-f]{32}', value['session_id'])
            and value['session_id'] == session
            and type(value['client_pid']) is int and value['client_pid'] > 0 and value['client_pid'] == client_pid
            and type(value['character_id']) is int and value['character_id'] > 0
            and value['character_id'] == character_id and value['action'] == 'quittologin'
            and type(value['sent_utc_ms']) is int and type(ready_utc_ms) is int
            and ready_utc_ms <= value['sent_utc_ms']
            and 0 <= now_utc_ms - value['sent_utc_ms'] <= LOGOUT_MAX_AGE_MS,
            'Character logout delivery does not match this ready client or its save window')
    return value


def logout_follows_delivery(logout, delivery):
    # The original logger uses FileTimeToLocalFileTime and one-second precision.
    try:
        timestamp = int(time.mktime(time.strptime(logout['log_timestamp'], '%y%m%d %H:%M:%S')) * 1000)
    except (KeyError, OverflowError, ValueError):
        return False
    return -999 <= timestamp - delivery['sent_utc_ms'] <= LOGOUT_MAX_AGE_MS


def entity_records(logs):
    """Yield IMPORTANT records from the two stock owned-server log routes.

    The embedded DbServer log server adds the Atlas map instance/host/DbServer
    prefix. If its connection fails, UtilitiesLib writes locally with level 0.
    """
    pattern = re.compile(r'^(?P<timestamp>\d{6} \d{2}:\d{2}:\d{2}) '
        r'(?:(?P<local_level>0)|(?P<map_instance>(?i:City_01_01)_1):127\.0\.0\.1:127\.0\.0\.1) +'
        r'(?P<message>[^\r\n]+)$')
    for name, text in logs:
        path = Path(name)
        if path.parent == Path('logs/mapserver') and path.name == 'entity.log':
            route = 'local_mapserver'
        elif (path.parent == Path('logs/dbserver')
                and re.fullmatch(r'entity_[0-9][0-9_-]*\.log', path.name)):
            route = 'embedded_dbserver_logserver'
        else:
            continue
        for line in text[:text.rfind('\n') + 1].splitlines():
            match = pattern.fullmatch(line)
            if match is None or (match['local_level'] is not None) != (route == 'local_mapserver'):
                continue
            yield match['message'], {'path': name, 'line_sha256': hashlib.sha256(line.encode()).hexdigest(),
                'log_timestamp': match['timestamp'], 'log_route': route,
                'map_instance': match['map_instance']}


def logout_record(logs):
    """Record the owned entity's live logout timer, not its underlying cause.

    A normal CLIENT_DISCONNECT and a still-linked stalled client can both take
    this timer path. Explicit command delivery must be bound separately.
    """
    pattern = re.compile(r'^"THORHERO:COHLOCAL" -?\d+ \[Disconnect:Logout timer expired\] [^\r\n]+$')
    for message, record in entity_records(logs):
        if pattern.fullmatch(message):
            return dict(record, reason='Logout timer expired', account=ACCOUNT, name=CHARACTER,
                source='current_owned_server_entity_log_live_client_logout_timer')
    return None


def ready_record(logs):
    """CLIENT_READY runs after the graphical client loads its world assets.

    The earlier DbServer connected flag only records map assignment. This
    current-session marker is emitted after resumeCharacter accepts CLIENT_READY.
    """
    pattern = re.compile(r'^"THORHERO:COHLOCAL" -?\d+ Connection:ResumeCharacter from '
        r'127\.0\.0\.1:(?P<port>[1-9][0-9]{0,4}) AuthName "COHLOCAL"(?: [^\r\n]*)?$')
    for message, record in entity_records(logs):
        match = pattern.fullmatch(message)
        if match and int(match['port']) <= 65535:
            return dict(record, account=ACCOUNT, name=CHARACTER,
                source='current_owned_mapserver_CLIENT_READY_resumeCharacter_success', loaded_world_assets=True)
    return None


def validate_character_rows(rows, baseline, inventory, attributes, auth_id):
    """Reject provisional name-only rows and bind every child to the new player."""
    require(isinstance(rows, dict) and set(rows) == set(evidence.SELECTED), 'Character snapshot tables differ')
    evidence.validate_attributes(attributes)
    require(type(auth_id) is int and auth_id > 0, 'Character account identity is missing')
    parents = rows['ents']
    if not parents: return None
    require(len(parents) == 1, 'Character name is ambiguous')
    parent = parents[0]
    identifier = parent.get('containerid')
    require(type(identifier) is int and identifier > 0 and identifier not in {r['containerid'] for r in baseline},
            'Character was present before this graphical session')
    require(parent.get('name') == CHARACTER and parent.get('authname') == ACCOUNT
            and parent.get('authid') == auth_id, 'Character/account SQL identity differs')
    if not parent.get('class') or not parent.get('origin') or not parent.get('logincount'):
        return None
    require(type(parent['logincount']) is int and parent['logincount'] == 1,
            'Character must have exactly its first map login')
    known = {row['id'] for row in attributes['attributes']}
    for table, selected in evidence.SELECTED.items():
        fields = set(selected) | ({'logincount'} if table == 'ents' else set())
        values = rows[table]
        if not values: return None
        require(isinstance(values, list) and all(isinstance(row, dict) and set(row) == fields for row in values),
                'Character snapshot fields differ: ' + table)
        require(all(type(row['containerid']) is int and row['containerid'] == identifier for row in values),
                'Character child references another parent: ' + table)
        if table in ('ents', 'ents2'):
            require(len(values) == 1, 'Expected one character parent/extension row')
        if table != 'ents':
            keys = [row['subid'] for row in values]
            require(all(type(key) is int and key >= 0 for key in keys) and keys == sorted(set(keys)),
                    'Duplicate, unordered or invalid character child keys')
            require(table != 'ents2' or keys == [0], 'Character extension must have subid zero')
        for row in values:
            for field in evidence.ATTRIBUTE_FIELDS.get(table, ()):
                value = row[field]
                require((table == 'costumeparts' and (value is None or type(value) is int and value == 0))
                        or type(value) is int and value > 0 and value in known,
                        'Character attribute is absent from the accepted mapping: ' + table + '.' + field)
    new_identity = {key: parent[key] for key in evidence.IDENTITY_FIELDS}
    current = [row for row in inventory if row['containerid'] != identifier]
    require(current == baseline and inventory == sorted(baseline + [new_identity], key=lambda r: r['containerid']),
            'Existing character identities changed or unexpected characters were created')
    return {'identity': new_identity, 'login_count': 1, 'rows': rows}


class LocalCharacterServer(login.LocalLoginServer):
    require_empty_account = False
    def __init__(self, owner):
        super().__init__(owner)
        self.map_process = None
        self.map_previous = None
        self.map_progress_next = 0
        self.character_next = 0
        self.query_count = 0
        self.baseline = None
        self.snapshot = None
        self.auth_id = None
        self.creation_report = {'session_id': owner.args.session_id, 'account': ACCOUNT,
            'name': CHARACTER, 'map_id': 1, 'verified': False, 'connected_on_atlas': False,
            'committed_sql_verified': False, 'requested_logout_observed': False, 'logout_timer_observed': False,
            'disconnected_before_sql': False, 'forced_stop_before_save': False,
            'reopen_verified': False, 'gameplay_verified': False, 'map_samples': [], 'character_samples': []}
        self.ctx.report['character_creation'] = self.creation_report

    def payloads(self):
        super().payloads()
        archive = self.owner.args.assets / 'game-package.tar.gz'
        destination = self.owner.root / ('character-map-payload-' + device.MAP_PROGRESS_PACKAGE_SHA256[:16])
        require(not destination.is_symlink(), 'Linked Atlas payload refused')
        if not destination.exists():
            pending = self.owner.root / ('character-map-pending-' + base.secrets.token_hex(8))
            try:
                login.extract_regular(archive, pending)
                self.verify_map_payload(pending)
                pending.rename(destination)
            finally:
                if pending.exists(): shutil.rmtree(pending)
        self.map_package = self.verify_map_payload(destination)
        self.map_package_dir = destination
        self.map_contract = game.mapserver_progress_contract(self.map_package)
        self.creation_report['mapserver_producer'] = self.map_contract['producer']

    @staticmethod
    def verify_map_payload(directory):
        path = directory / 'game-package.json'
        require(path.is_file() and not path.is_symlink()
                and base.file_hash(path) == device.MAP_PROGRESS_PACKAGE_SHA256,
                'Atlas package differs from the device-qualified progress donor')
        package = dbserver.load_json(path)
        require(package.get('repository_commit') == device.MAP_PROGRESS_COMMIT
                and package.get('source_commit') == device.SOURCE_COMMIT
                and package.get('data_commit') == device.DATA_COMMIT
                and package.get('postgresql_persistence_fixture') is False,
                'Atlas package provenance or fixture mode differs')
        dbserver.verify_inventory(directory, package['files'], manifest='game-package.json', binary=True)
        game.game_loopback_contract(package)
        game.game_listener_contract(package)
        contract = game.mapserver_progress_contract(package)
        require(contract['producer'] == device.MAP_PROGRESS_PRODUCER, 'Atlas progress producer differs')
        for name in package['files']: base.verify_pe32(directory / name)
        return package

    def prepare_runtime(self):
        super().prepare_runtime()
        source = self.owner.work / 'data'
        require(source.is_dir() and not source.is_symlink(), 'Verified private client data is missing')
        receipt = self.ctx.report.get('client_worktree', {})
        require(receipt.get('imported_inputs_readonly') is True,
                'Atlas requires the already protected private client worktree')
        # Wine FolderCache does not enumerate directory symlinks as directories.
        # Mirror actual directories as the accepted client worktree does, then
        # link individual immutable files. Keep caches/configuration private.
        staged = self.stage_map_data(source, self.runtime / 'data')
        for name, record in self.map_package['files'].items():
            target = self.runtime / name
            if target.exists():
                require(not target.is_symlink() and base.file_hash(target) == record['sha256'],
                        'Atlas and local DbServer dependency closures differ: ' + name)
            else:
                shutil.copyfile(self.map_package_dir / name, target)
                target.chmod(0o400)
        self.creation_report['private_map_data'] = {'source_worktree': self.owner.work.name,
            'imported_inputs_readonly': True, 'private_server_config': True,
            'private_cache_roots': ['bin', 'geobin', 'server/bin'],
            'directory_layout': 'real_directories_with_individual_immutable_file_links', **staged}

    def copy_private_data(self, source, target):
        return self.stage_map_data(source, target, force_private=True)

    def stage_map_data(self, source, target, *, force_private=False):
        """Mirror bounded verified inputs without directory links or source writes.

        The client worktree has real directories and immutable per-file links.
        Resolve those links only within its two verified roots; each writable
        cache, server file and dbidmap receives an independent regular copy.
        """
        roots = (self.owner.work.resolve(strict=True), self.owner.args.game_data.resolve(strict=True))
        source, target = Path(source), Path(target)
        result = {'files': 0, 'bytes': 0, 'directories': 0, 'linked_immutable_files': 0,
                  'copied_private_files': 0, 'preserved_schema_files': 0}
        pending = [(source, target)]
        next_message = time.monotonic() + 5
        while pending:
            self.ctx.check()
            current, destination = pending.pop()
            require(not destination.is_symlink(), 'Linked private destination refused')
            info = current.lstat()
            relative = current.relative_to(source)
            private = force_private or bool(relative.parts and relative.parts[0] in ('server', 'bin', 'geobin'))
            if stat.S_ISDIR(info.st_mode):
                resolved = current.resolve(strict=True)
                require(any(root == resolved or root in resolved.parents for root in roots),
                        'Map data directory escaped verified roots')
                require(not destination.exists() or destination.is_dir(), 'Invalid private data directory')
                destination.mkdir(parents=True, exist_ok=True, mode=0o700)
                result['directories'] += 1
                require(result['directories'] <= device.DATA_COUNT + 4096, 'Map directory count exceeded bound')
                with os.scandir(current) as entries:
                    pending.extend((Path(entry.path), destination / entry.name) for entry in entries)
            else:
                require(stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode), 'Nonregular map input refused')
                resolved = current.resolve(strict=True)
                resolved_info = resolved.stat()
                require(any(root == resolved or root in resolved.parents for root in roots)
                        and stat.S_ISREG(resolved_info.st_mode), 'Private map copy escaped verified data roots')
                result['files'] += 1; result['bytes'] += resolved_info.st_size
                # Include accepted prerequisites/prepared caches and bounded
                # generated client caches in addition to the imported inputs.
                require(result['files'] <= device.DATA_COUNT + 4096
                        and result['bytes'] <= device.DATA_BYTES + 1024**3,
                        'Private map data exceeded bound')
                private = private or current.suffix.casefold() == '.dbidmap' or bool(resolved_info.st_mode & 0o222)
                if destination.exists():
                    require(destination.is_file(), 'Invalid staged schema file')
                    require(private or base.file_hash(destination) == base.file_hash(resolved),
                            'Immutable map input conflicts with staged schema')
                    result['preserved_schema_files'] += 1
                elif private:
                    shutil.copyfile(resolved, destination)
                    destination.chmod(0o600)
                    os.utime(destination, ns=(resolved_info.st_atime_ns, resolved_info.st_mtime_ns))
                    result['copied_private_files'] += 1
                else:
                    destination.symlink_to(resolved)
                    result['linked_immutable_files'] += 1
            if time.monotonic() >= next_message:
                self.ctx.event('stage', status='running', message='Preparing Atlas data directories', files=result['files'])
                next_message = time.monotonic() + 5
        return result

    def start(self):
        super().start()
        self.baseline = self.inventory()
        require(not any(row['name'].casefold() == CHARACTER.casefold() for row in self.baseline),
                'THORHERO already exists; it was preserved. Export this report instead of deleting it.')
        self.creation_report.update(baseline_character_count=len(self.baseline),
                                    baseline_identity_sha256=digest_json(self.baseline))
        self.ctx.stage('local_atlas_startup')
        game.check_game_port(7001, socket.SOCK_DGRAM)
        baseline = evidence.parse_map_status(self.query(['-getstatus', '1', '1'], 'atlas-baseline'), allow_missing=True)
        require(not baseline.get('ready'), 'Atlas was already running before this owned launch')
        self.map_progress_path = self.runtime / 'character-atlas-progress.bin'
        require(not self.map_progress_path.exists(), 'Stale Atlas progress file')
        environment = dict(self.owner.wine_env, **{evidence.GAME_LOOPBACK_ENV: '1',
            progress.ENVIRONMENT: base.windows_path(self.map_progress_path)})
        self.map_process = self.ctx.start('local-character-atlas', ['/usr/bin/env', '--chdir=' + str(self.runtime),
            self.owner.args.wine, base.windows_path(self.runtime / 'MapServer.exe'),
            '-nogui', '-db', '127.0.0.1', '-nosharedmemory', '-nostats', '-udp', '7001', '-tcp', '0', '-map_id', '1'],
            env=environment)
        self.report['mapserver_started'] = self.ctx.report['mapserver_started'] = True
        deadline = min(self.ctx.deadline, time.monotonic() + MAP_STARTUP_SECONDS)
        next_query = next_message = 0
        while True:
            self.ctx.check(); self.health()
            now = time.monotonic()
            require(now < deadline, 'Atlas startup timed out; export this report without another boot')
            self.sample_progress()
            bindings = evidence.game_listener_bindings(self.map_process.text(), 'atlas', pending=True)
            if bindings and now >= next_query:
                next_query = now + 60
                before = self.sample_progress(force=True)
                if not self.live_progress(before):
                    next_query = now + 5
                    continue
                sample = evidence.parse_map_status(self.query(['-getstatus', '1', '1'], 'atlas-ready'))
                after = self.sample_progress(force=True)
                guard = {'before': before, 'after': after, 'protocol': sample,
                         'requires_completed_tick_before_protocol': True}
                self.creation_report['map_startup_guard'] = guard
                self.creation_report['map_samples'].append(sample)
                if self.live_progress(after) and evidence.map_ready_current(sample):
                    progress.compare_records(after, before)
                    guard['passed'] = True
                    self.creation_report.update(map_ready=True, map_listener=bindings)
                    self.ctx.passed(atlas_ready=True, map=sample, loopback_only=True)
                    return
            if now >= next_message:
                self.ctx.event('stage', status='running', message='Preparing Atlas Park for character creation')
                next_message = now + 5
            time.sleep(.2)

    @staticmethod
    def live_progress(value):
        return (isinstance(value, dict) and value.get('available') is True
                and type(value.get('tick_completed')) is int and value['tick_completed'] > 0
                and type(value.get('unchanged_seconds')) in (int, float) and value['unchanged_seconds'] <= 20)

    def sample_progress(self, *, force=False):
        now = time.monotonic()
        if not force and now < self.map_progress_next or self.map_process is None: return None
        self.map_progress_next = now + 5
        try:
            self.map_previous = progress.read_record(self.map_progress_path, self.map_previous)
            self.creation_report['map_progress_latest'] = self.map_previous
            return self.map_previous
        except (FileNotFoundError, progress.PublicationPending):
            return

    def health(self):
        super().health()
        if self.map_process is not None:
            console = self.map_process.text()
            crash = re.search(r'Program crash detected|Exception caught: EXCEPTION_[A-Z_]+', console)
            if crash is not None:
                self.creation_report['mapserver_crash'] = {
                    'marker': crash.group(), 'console_offset': crash.start(),
                    'context': console[max(0, crash.start() - 1000):crash.end() + 1000],
                    'console_sha256': hashlib.sha256(console.encode()).hexdigest()}
                require(False, 'Atlas crashed: ' + crash.group() + '; export the server console and report')
            require(self.map_process.process.poll() is None, 'Atlas exited during character creation')
            require(not self.map_process.overflow, 'Atlas console exceeded capture bound')

    def query(self, arguments, label):
        self.query_count += 1
        require(self.query_count <= 160, 'Character protocol query budget exceeded')
        result = self.ctx.run('character-' + label, ['/usr/bin/env', '--chdir=' + str(self.runtime),
            self.owner.args.wine, base.windows_path(self.runtime / 'MapServer.exe'), '-nogui',
            '-db', '127.0.0.1', '-dbquery', '-timeout', '10000', *arguments],
            timeout=90, env=self.owner.wine_env)
        require(result['exit_code'] == 0, 'Character protocol query failed')
        return self.ctx.children[-1].text()

    def sql_rows(self, table, fields, keys, where='TRUE'):
        require(table in self.schema['expected_tables'] and all(field in self.schema['expected_tables'][table]
                and dbserver.IDENTIFIER.fullmatch(field) for field in fields), 'Character schema contract differs')
        self.sql("SELECT coalesce(json_agg(x ORDER BY " + ','.join(keys) + "),'[]'::json) FROM (SELECT "
                 + ','.join(fields) + ' FROM dbo.' + table + ' WHERE ' + where + ') x;', game=True)
        output = self.ctx.children[-1].text().strip()
        require(len(output.encode()) <= SNAPSHOT_LIMIT, 'Character SQL evidence exceeded bound')
        values = json.loads(output)
        require(isinstance(values, list) and len(values) <= 10000, 'Malformed character SQL evidence')
        return values

    def inventory(self):
        return self.sql_rows('ents', evidence.IDENTITY_FIELDS, ('containerid',))

    def login_evidence(self):
        proof = super().login_evidence()
        if proof is not None:
            self.auth_id = proof['auth_id']
        return proof

    def character_evidence(self):
        if self.creation_report['verified']: return self.creation_report
        now = time.monotonic()
        if now < self.character_next: return None
        self.character_next = now + POLL_SECONDS
        self.health(); self.sample_progress()
        if self.auth_id is None: return None
        before = self.sample_progress(force=True)
        if not self.live_progress(before): return None
        inventory = self.inventory()
        candidates = [row for row in inventory if row.get('name') == CHARACTER]
        if not candidates: return None
        require(len(candidates) == 1, 'Ambiguous THORHERO identity')
        identity = candidates[0]
        identifier = identity['containerid']
        require(type(identifier) is int and identifier > 0 and identity.get('authname') == ACCOUNT
                and identity.get('authid') == self.auth_id
                and identifier not in {row['containerid'] for row in self.baseline},
                'Created character identity differs from this graphical session')
        sample = evidence.parse_character_status(self.query(['-getstatus', '3', str(identifier)], 'player-status'),
            identifier, CHARACTER, ACCOUNT, allow_missing=True)
        after = self.sample_progress(force=True)
        if not self.live_progress(after): return None
        progress.compare_records(after, before)
        self.creation_report['character_progress_guard'] = {'before': before, 'after': after, 'passed': True}
        self.creation_report['character_samples'].append(sample)
        self.creation_report.update(character_id=identifier, auth_id=self.auth_id)
        if evidence.connected_on_atlas(sample):
            self.creation_report['db_map_assignment_observed'] = True
            ready = ready_record(self.current_logs())
            if ready is not None and not self.creation_report['connected_on_atlas']:
                self.creation_report.update(connected_on_atlas=True, client_ready_evidence=ready,
                    client_ready_observed_utc=base.utc(), client_ready_observed_utc_ms=int(time.time() * 1000))
            return None
        if not self.creation_report['connected_on_atlas'] or sample.get('connected') or sample.get('in_map_transfer'):
            return None
        client_pid = self.creation_report.get('client_pid')
        if type(client_pid) is not int or client_pid <= 0: return None
        delivery = read_logout_delivery(self.owner.args.state / 'character-logout.json',
            self.owner.args.session_id, client_pid, identifier,
            self.creation_report.get('client_ready_observed_utc_ms'), int(time.time() * 1000))
        if delivery is None: return None
        logout = logout_record(self.current_logs())
        if logout is None or not logout_follows_delivery(logout, delivery): return None
        rows = {table: self.sql_rows(table, tuple(fields) + (('logincount',) if table == 'ents' else ()),
                evidence.ROW_KEYS[table], 'containerid=' + str(identifier))
                for table, fields in evidence.SELECTED.items()}
        snapshot = validate_character_rows(rows, self.baseline, inventory, self.schema['expected_attributes'], self.auth_id)
        if snapshot is None: return None
        final_progress = self.sample_progress(force=True)
        if not self.live_progress(final_progress): return None
        # SQL reads can take time; recheck the bounded receipt at the save point.
        final_delivery = read_logout_delivery(self.owner.args.state / 'character-logout.json',
            self.owner.args.session_id, client_pid, identifier,
            self.creation_report.get('client_ready_observed_utc_ms'), int(time.time() * 1000))
        require(final_delivery == delivery, 'Character logout delivery changed during save verification')
        self.snapshot = snapshot
        self.creation_report.update(verified=True, committed_sql_verified=True, disconnected_before_sql=True,
            requested_logout_observed=True, logout_timer_observed=True, forced_stop_before_save=False,
            logout_delivery=delivery, logout_timer_evidence=logout, map_progress_at_save=final_progress,
            saved_utc=base.utc(), snapshot_sha256=digest_json(snapshot),
            table_sha256={name: digest_json(value) for name, value in rows.items()},
            row_counts={name: len(value) for name, value in rows.items()},
            evidence_scope='fresh_graphical_character_ready_on_atlas_then_requested_logout_timer_and_committed_full_character_rows')
        return self.creation_report

    def collect(self, target):
        # Atlas has substantially more diagnostics than the login-only mode.
        # Keep its bounded complete logs in one member of the outer support ZIP.
        # Do not widen the accepted login-only collector's two-MiB limit.
        if self.process is not None:
            text = base.redact(self.process.text(), self.ctx.secrets)
            require(len(text.encode()) <= 2 * 1024 * 1024, 'Server console evidence exceeded bound')
            base.private_write(target / 'local-dbserver-console.txt', text)
        if self.map_process is not None:
            raw = base.redact(self.map_process.text(), self.ctx.secrets).encode()
            require(len(raw) <= 16 * 1024 * 1024, 'Atlas console evidence exceeded export bound')
            base.private_write(target / 'character-atlas-console.txt', raw.decode())
        if self.snapshot is not None:
            base.private_write(target / 'character-saved-snapshot.json', json.dumps(self.snapshot, indent=2) + '\n')
        self.collect_server_logs(target)

    def collect_server_logs(self, target):
        require(target.is_dir() and not target.is_symlink(), 'Linked server evidence directory refused')
        paths = [] if self.runtime is None else sorted(self.runtime.rglob('*.log'))
        require(len(paths) <= SERVER_LOG_COUNT_LIMIT, 'Character server log count exceeded bound')
        destination = target / 'character-server-logs.zip'
        require(not destination.is_symlink(), 'Linked server log archive refused')
        temporary = target / ('character-server-logs.tmp-' + base.secrets.token_hex(8))
        closed_sources = all(child is None or child.process.poll() is not None
                             for child in (self.process, self.map_process))
        manifest = {'format': 1, 'scope': 'current_owned_character_server_logs',
            'session_id': self.owner.args.session_id, 'truncated': False, 'files': {},
            'collection_phase': 'closed_server_logs' if closed_sources else 'live_snapshot'}
        source_total = exported_total = after_total = 0
        try:
            with temporary.open('xb') as output:
                os.chmod(temporary, 0o600)
                with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                    for path in paths:
                        # current_logs() already rejects linked leaves; preserve
                        # that protection and also reject linked parents/owners.
                        current = path.parent
                        while True:
                            require(current.is_dir() and not current.is_symlink(), 'Linked server log directory refused')
                            if current == self.runtime: break
                            require(self.runtime in current.parents, 'Server log path escaped its owned runtime')
                            current = current.parent
                        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                        try:
                            before = os.fstat(descriptor)
                            require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                                    and before.st_uid == os.geteuid() and before.st_size <= SERVER_LOG_FILE_LIMIT,
                                    'Invalid or oversized character server log')
                            with os.fdopen(descriptor, 'rb', closefd=False) as source:
                                raw = source.read(before.st_size)
                            after = os.fstat(descriptor)
                            require(after.st_nlink == 1 and after.st_uid == before.st_uid
                                    and len(raw) == before.st_size <= after.st_size <= SERVER_LOG_FILE_LIMIT
                                    and (not closed_sources or after.st_size == before.st_size),
                                    'Character server log changed or exceeded bound while reading')
                        finally:
                            os.close(descriptor)
                        # Preserve every non-secret byte, including non-UTF8
                        # legacy log text. Redaction is the only transformation.
                        redacted = base.redact(raw.decode('utf-8', errors='surrogateescape'),
                            self.ctx.secrets).encode('utf-8', errors='surrogateescape')
                        source_total += len(raw); exported_total += len(redacted); after_total += after.st_size
                        require(source_total <= SERVER_LOG_TOTAL_LIMIT
                                and after_total <= SERVER_LOG_TOTAL_LIMIT
                                and exported_total <= SERVER_LOG_TOTAL_LIMIT
                                and len(redacted) <= SERVER_LOG_FILE_LIMIT,
                                'Character server logs exceeded export bound')
                        name = path.relative_to(self.runtime).as_posix()
                        manifest['files'][name] = {'source_bytes': len(raw),
                            'source_sha256': hashlib.sha256(raw).hexdigest(), 'exported_bytes': len(redacted),
                            'exported_sha256': hashlib.sha256(redacted).hexdigest(),
                            'source_bytes_after_read': after.st_size,
                            'appended_bytes_after_snapshot': after.st_size - before.st_size,
                            'redacted': raw != redacted, 'truncated': False}
                        archive.writestr(name, redacted)
                    manifest.update(file_count=len(paths), source_bytes=source_total,
                                    source_bytes_after_read=after_total, exported_bytes=exported_total)
                    document = json.dumps(manifest, indent=2) + '\n'
                    require(len(document.encode()) <= 128 * 1024, 'Server log manifest exceeded bound')
                    archive.writestr('manifest.json', document)
                output.flush(); os.fsync(output.fileno())
            require(temporary.stat().st_size <= SERVER_LOG_TOTAL_LIMIT + 1024 * 1024,
                    'Character server log archive exceeded bound')
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        self.ctx.report['character_server_logs'] = {'path': destination.name,
            'bytes': destination.stat().st_size, 'sha256': base.file_hash(destination),
            'manifest_sha256': hashlib.sha256(document.encode()).hexdigest(),
            'file_count': len(paths), 'source_bytes': source_total, 'exported_bytes': exported_total,
            'source_bytes_after_read': after_total, 'collection_phase': manifest['collection_phase'],
            'truncated': False, 'redacted_files': sum(item['redacted'] for item in manifest['files'].values())}
