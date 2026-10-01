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

import local_login_server as login
import game_device_diagnostic as device
import game_evidence as evidence
import game_map_progress as progress

base, game, dbserver, require = login.base, login.game, login.dbserver, login.require
PROFILE, ACCOUNT, CHARACTER = login.PROFILE, login.ACCOUNT, 'THORHERO'
POLL_SECONDS = 15
MAP_STARTUP_SECONDS = 2400
SNAPSHOT_LIMIT = 2 * 1024 * 1024


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def logout_record(logs):
    """The live client link's ordinary logout timer precedes entity unlinking.

    Network/crash disconnects deinitialize the link and clear entity.client
    first, so their later timer cannot produce this live-client LOG_ENT line.
    Source: svr_tick.c logDisconnect; svr_player.c unload/deinitialize paths.
    """
    pattern = re.compile(r'^\d{6} \d{2}:\d{2}:\d{2} (?:-?\d+ )?'
        r'"THORHERO:COHLOCAL" -?\d+ \[Disconnect:Logout timer expired\] [^\r\n]+$')
    for name, text in logs:
        if not Path(name).name.casefold().startswith('entity_'): continue
        for line in text[:text.rfind('\n') + 1].splitlines():
            if pattern.fullmatch(line):
                return {'path': name, 'line_sha256': hashlib.sha256(line.encode()).hexdigest(),
                    'reason': 'Logout timer expired', 'account': ACCOUNT, 'name': CHARACTER,
                    'source': 'current_owned_server_entity_log_live_client_logout_timer'}
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
            'committed_sql_verified': False, 'protocol_logout_verified': False,
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
        # The large immutable trees are reused without 173,011 new links. All
        # generated cache roots and the server/configuration subtree are copied
        # into this owned session; no writable location points into the import.
        for entry in sorted(source.iterdir()):
            self.ctx.check()
            target = self.runtime / 'data' / entry.name
            require(not entry.is_symlink() or entry.is_file(), 'Unexpected linked client data directory')
            if entry.name in ('server', 'bin', 'geobin'):
                self.copy_private_data(entry, target)
            elif not target.exists():
                target.symlink_to(entry, target_is_directory=entry.is_dir())
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
            'private_cache_roots': ['bin', 'geobin', 'server/bin']}

    def copy_private_data(self, source, target):
        count = total = 0
        pending = [(source, target)]
        while pending:
            self.ctx.check()
            current, destination = pending.pop()
            if current.is_dir():
                require(not current.is_symlink(), 'Linked writable source directory refused')
                require(not destination.is_symlink(), 'Linked private destination refused')
                destination.mkdir(parents=True, exist_ok=True, mode=0o700)
                pending.extend((item, destination / item.name) for item in current.iterdir())
            else:
                resolved = current.resolve(strict=True)
                roots = (self.owner.work.resolve(), self.owner.args.game_data.resolve())
                require(any(root == resolved or root in resolved.parents for root in roots)
                        and resolved.is_file(), 'Private map copy escaped verified data roots')
                count += 1; total += resolved.stat().st_size
                require(count <= device.DATA_COUNT and total <= 1024**3, 'Private server/cache copy exceeded bound')
                if not destination.exists():
                    shutil.copyfile(resolved, destination)
                    destination.chmod(0o600)
                    os.utime(destination, ns=(resolved.stat().st_atime_ns, resolved.stat().st_mtime_ns))
                else:
                    require(destination.is_file() and not destination.is_symlink(), 'Invalid staged schema file')

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
            self.creation_report['connected_on_atlas'] = True
            return None
        if not self.creation_report['connected_on_atlas'] or sample.get('connected') or sample.get('in_map_transfer'):
            return None
        logout = logout_record(self.current_logs())
        if logout is None: return None
        rows = {table: self.sql_rows(table, tuple(fields) + (('logincount',) if table == 'ents' else ()),
                evidence.ROW_KEYS[table], 'containerid=' + str(identifier))
                for table, fields in evidence.SELECTED.items()}
        snapshot = validate_character_rows(rows, self.baseline, inventory, self.schema['expected_attributes'], self.auth_id)
        if snapshot is None: return None
        final_progress = self.sample_progress(force=True)
        if not self.live_progress(final_progress): return None
        self.snapshot = snapshot
        self.creation_report.update(verified=True, committed_sql_verified=True, disconnected_before_sql=True,
            protocol_logout_verified=True, forced_stop_before_save=False,
            protocol_logout_evidence=logout, map_progress_at_save=final_progress,
            saved_utc=base.utc(), snapshot_sha256=digest_json(snapshot),
            table_sha256={name: digest_json(value) for name, value in rows.items()},
            row_counts={name: len(value) for name, value in rows.items()},
            evidence_scope='fresh_graphical_character_connected_on_atlas_then_disconnected_with_committed_full_character_rows')
        return self.creation_report

    def collect(self, target):
        super().collect(target)
        if self.map_process is not None:
            raw = base.redact(self.map_process.text(), self.ctx.secrets).encode()
            require(len(raw) <= 16 * 1024 * 1024, 'Atlas console evidence exceeded export bound')
            base.private_write(target / 'character-atlas-console.txt', raw.decode())
        if self.snapshot is not None:
            base.private_write(target / 'character-saved-snapshot.json', json.dumps(self.snapshot, indent=2) + '\n')
