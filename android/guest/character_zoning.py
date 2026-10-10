"""Finite native Atlas-instance zoning; read-only SQL and owned native evidence.

The .25 native client/server bytes are reused. Map 101 intentionally uses the
stock, explicitly labelled embedded logger route: the retained immediate event
producer observes only map 1 and its contract is never widened here.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import socket
import stat
import time

import local_character_server as character

base, require = character.base, character.require
MAPS = {1: {'name': 'Atlas Park', 'port': 7001, 'instance': 1},
        101: {'name': 'Atlas Park instance 2', 'port': 7002, 'instance': 2}}
MAX_EPOCHS = 4
PREPARE_SECONDS = 600
TRANSFER_SECONDS = 180
REQUEST_AGE_MS = 120000
NUMBER = character.character_events.NUMBER


def supported(map_id):
    return type(map_id) is int and map_id in MAPS


def connected(sample, map_id):
    return (supported(map_id) and type(sample) is dict
        and sample.get('loaded') is True and sample.get('connected') is True
        and sample.get('in_map_transfer') is False and type(sample.get('map_id')) is int
        and sample['map_id'] == map_id and type(sample.get('static_map_id')) is int
        and sample['static_map_id'] == map_id and sample.get('address') == '127.0.0.1')


def parse_map_status(text, map_id, *, allow_missing=False):
    require(supported(map_id), 'Unsupported zoning destination')
    require(not character.evidence.diagnostic_failures(text), 'Zoning map status failed')
    missing = [line for line in text.splitlines() if line.strip() == 'invalid container request']
    rows = [m.groups() for line in text.splitlines()
            if (m := re.fullmatch(r'\s*(\d+)\s+(\S+)\s+((?:NotReady|S:).*)', line))]
    if missing:
        require(allow_missing and len(missing) == 1 and not rows, 'Ambiguous zoning map status')
        return {'map_id': map_id, 'ready': False, 'missing': True}
    require(len(rows) == 1 and int(rows[0][0]) == map_id,
            'Zoning status lacks exact destination container')
    _, name, fields = rows[0]
    require(name.replace('\\', '/').split('/')[-1].casefold() == 'city_01_01.txt',
            'Zoning destination uses unreviewed world assets')
    not_ready = re.findall(r'\bNotReady\s+(\S+)', fields)
    require(not not_ready or not_ready == ['1'], 'Unknown zoning map not-ready flag')
    if fields.startswith('NotReady'):
        require(re.fullmatch(r'NotReady 1 \(Not started\) Info(?: .*)?', fields) is not None,
                'Unexpected zoning map not-ready response')
        return {'map_id': map_id, 'ready': False, 'not_started': True}
    match = re.match(r'S:\s*(\d+)\s*/\s*(\d+)\s+Ip:\s*([0-9.]+):(\d+)\s+Mem:', fields)
    require(match is not None, 'Malformed zoning map endpoint')
    network, stats, address, port = match.groups()
    require(address == '127.0.0.1' and int(port) == MAPS[map_id]['port'],
            'Zoning destination is not the owned loopback endpoint')
    return {'map_id': map_id, 'ready': not not_ready, 'address': address, 'port': int(port),
            'network_age_seconds': int(network), 'stats_age_seconds': int(stats)}


def ready(sample, map_id):
    return (supported(map_id) and isinstance(sample, dict) and sample.get('ready') is True
        and type(sample.get('map_id')) is int and sample['map_id'] == map_id
        and sample.get('address') == '127.0.0.1' and type(sample.get('port')) is int
        and sample['port'] == MAPS[map_id]['port']
        and all(type(sample.get(k)) is int and 0 <= sample[k] <= 20
                for k in ('network_age_seconds', 'stats_age_seconds')))


def read_request(path):
    """Read one atomic bounded private receipt, including replacement races."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == os.geteuid()
                and before.st_nlink == 1 and 0 < before.st_size <= 2048,
                'Invalid zoning request file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(2049)
        after = os.fstat(fd)
        require(len(raw) == before.st_size and
                (before.st_ino, before.st_size, before.st_mtime_ns, before.st_nlink) ==
                (after.st_ino, after.st_size, after.st_mtime_ns, after.st_nlink),
                'Zoning request changed while reading')
    finally:
        os.close(fd)
    value = json.loads(raw)
    require(type(value) is dict, 'Malformed zoning request')
    return value


def validate_request(value, *, session, client_pid, epoch, origin, action, now_ms):
    clock = 'requested_utc_ms' if action == 'prepare' else 'sent_utc_ms'
    fields = {'format', 'session_id', 'client_pid', 'character_id', 'epoch', 'action',
              'from_map_id', 'to_map_id', clock}
    require(type(value) is dict and set(value) == fields and value.get('format') == 1
        and type(value['format']) is int and value['session_id'] == session
        and type(value['client_pid']) is int and value['client_pid'] == client_pid and client_pid > 0
        and type(value['character_id']) is int and value['character_id'] == 1
        and type(value['epoch']) is int and value['epoch'] == epoch and 1 <= epoch <= MAX_EPOCHS
        and value['action'] == action and supported(value['from_map_id'])
        and value['from_map_id'] == origin and supported(value['to_map_id'])
        and value['to_map_id'] != origin and type(value[clock]) is int
        and 0 <= now_ms - value[clock] <= REQUEST_AGE_MS,
        'Zoning request is stale, foreign, duplicated or outside the supported route')
    return value


def entity_records(logs, map_id, *, minimum_ms=0, now_ms=None):
    """Only the stock embedded logger's exact map-instance route is authoritative.

    Shared unprefixed mapserver/entity.log lines cannot identify a destination.
    The fixed maps.db order and native StaticMapInfo assign instances 1 and 2.
    """
    require(supported(map_id), 'Unreviewed zoning log route')
    route = 'City_01_01_' + str(MAPS[map_id]['instance'])
    pattern = re.compile(r'^(?P<time>\d{6} \d{2}:\d{2}:\d{2}) '
        + re.escape(route) + r':127\.0\.0\.1:127\.0\.0\.1 +(?P<message>[^\r\n]+)$', re.I)
    seen = set()
    for name, text in logs:
        path = Path(name)
        if path.parent != Path('logs/dbserver') or not re.fullmatch(r'entity_[0-9][0-9_-]*\.log', path.name):
            continue
        for ordinal, line in enumerate(text[:text.rfind('\n') + 1].splitlines()):
            match = pattern.fullmatch(line)
            if match is None:
                continue
            utc_ms = int(time.mktime(time.strptime(match['time'], '%y%m%d %H:%M:%S')) * 1000)
            if utc_ms < minimum_ms or now_ms is not None and utc_ms > now_ms + 999:
                continue
            digest = hashlib.sha256(line.encode()).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            yield match['message'], {'path': name, 'line_sha256': digest, 'line_ordinal': ordinal,
                'log_timestamp': match['time'], 'utc_ms': utc_ms, 'map_id': map_id,
                'map_instance': route, 'log_route': 'embedded_dbserver_logserver',
                'native_log_contains_session_or_client_pid': False,
                'native_log_contains_character_db_id': False,
                'connection_binding': 'owned_map_progress_exact_dbserver_character_status_and_current_epoch'}


def stock_ready(logs, map_id, minimum_ms, now_ms):
    pattern = re.compile(r'^"THORHERO:COHLOCAL" -?\d+ Connection:ResumeCharacter from '
                         r'127\.0\.0\.1:([1-9][0-9]{0,4}) AuthName "COHLOCAL"(?: [^\r\n]*)?$')
    result = []
    for message, record in entity_records(logs, map_id, minimum_ms=minimum_ms, now_ms=now_ms):
        match = pattern.fullmatch(message)
        if match is not None and int(match[1]) <= 65535:
            result.append(dict(record, account=character.ACCOUNT, name=character.CHARACTER,
                port=int(match[1]), loaded_world_assets=True,
                source='current_target_stock_CLIENT_READY_resumeCharacter_success'))
    return max(result, key=lambda r: (r['utc_ms'], r['line_ordinal'])) if result else None


def stock_positions(logs, map_id, minimum_ms, now_ms):
    pattern = re.compile(r'^"THORHERO:COHLOCAL" -?\d+ PeriodicInfo pos=<('
                         + NUMBER + '),(' + NUMBER + '),(' + NUMBER + r')> [^\r\n]+$')
    result = {}
    for message, record in entity_records(logs, map_id, minimum_ms=minimum_ms, now_ms=now_ms):
        match = pattern.fullmatch(message)
        if match is None:
            continue
        position = list(map(float, match.groups()))
        require(all(math.isfinite(v) and abs(v) <= 1000000 for v in position),
                'Invalid zoning native position')
        value = dict(record, position=position, account=character.ACCOUNT, name=character.CHARACTER,
                     source='current_target_stock_PeriodicInfo_position')
        require(record['utc_ms'] not in result or result[record['utc_ms']]['position'] == position,
                'Conflicting zoning native positions')
        result[record['utc_ms']] = value
    return [result[key] for key in sorted(result)]


def stock_logout(logs, map_id, minimum_ms, now_ms):
    rows = [dict(record, reason='Logout timer expired', account=character.ACCOUNT,
                 name=character.CHARACTER, source='current_target_stock_logout_timer')
        for message, record in entity_records(logs, map_id, minimum_ms=minimum_ms, now_ms=now_ms)
        if re.fullmatch(r'^"THORHERO:COHLOCAL" -?\d+ \[Disconnect:Logout timer expired\] [^\r\n]+$', message)]
    return max(rows, key=lambda r: (r['utc_ms'], r['line_ordinal'])) if rows else None


def terminal_position(logs, map_id, delivery, minimum_ms, now_ms):
    timer = None
    matches = []
    pattern = re.compile(r'^"THORHERO:COHLOCAL" -?\d+ Logout location : map (\d+) '
                        r'\((' + NUMBER + ') (' + NUMBER + ') (' + NUMBER + r')\) [^\r\n]+$')
    for message, record in entity_records(logs, map_id, minimum_ms=minimum_ms, now_ms=now_ms):
        if re.fullmatch(r'^"THORHERO:COHLOCAL" -?\d+ \[Disconnect:Logout timer expired\] [^\r\n]+$', message):
            timer = record
            continue
        match = pattern.fullmatch(message)
        if match is None or timer is None or int(match[1]) != map_id:
            continue
        if record['path'] != timer['path'] or record['utc_ms'] != timer['utc_ms']:
            continue
        if not character.logout_follows_delivery(timer, delivery):
            continue
        position = [float(match[i]) for i in (2, 3, 4)]
        require(all(math.isfinite(v) and abs(v) <= 1000000 for v in position)
                and character.above_native_fall_floor(position[1]), 'Invalid zoning logout position')
        matches.append(dict(record, position=position, logout_timer_evidence=timer,
                            source='current_target_stock_ordinary_logout_position'))
    require(not matches or all(row['position'] == matches[0]['position'] for row in matches),
            'Conflicting zoning logout positions')
    return matches[-1] if matches else None


class LocalCharacterZoningServer(character.LocalCharacterReopenServer):
    """At most two owned static map processes, started only when requested."""
    def __init__(self, owner):
        super().__init__(owner)
        self.active_map_id = 1
        self.maps = {}
        self.ready_floor_ms = 0
        self.zoning_next = 0
        self.zoning_query = None
        self.pending = None
        self.epoch = 0
        self.enabled_announced = False
        self.request_history = {}
        self.delivery_history = {}
        self.zoning_report = {'format': 1, 'scope': 'native_Atlas_instance_handoff',
            'supported_maps': MAPS, 'events': [], 'transfers': [], 'epoch_limit': MAX_EPOCHS,
            'new_city_asset_coverage': False, 'sql_game_mutations_performed': False,
            'target_seconds': 30, 'physical_zoning_validated': False}
        self.ctx.report['character_zoning'] = self.zoning_report
        self.creation_report.update(zoning_enabled=True, connected_on_supported_map=False)

    def character_position(self, *, allow_unassigned_active_map=False):
        values = self.sql_rows('ents', ('containerid', 'mapid', 'staticmapid', 'posx', 'posy', 'posz'),
                              ('containerid',), 'containerid=1')
        require(len(values) == 1 and set(values[0]) == {'containerid', 'mapid', 'staticmapid', 'posx', 'posy', 'posz'},
                'Zoning character position fields differ')
        value = values[0]
        require(type(value['containerid']) is int and value['containerid'] == 1
            and supported(value['staticmapid'])
            and (type(value['mapid']) is int and value['mapid'] == value['staticmapid']
                 or allow_unassigned_active_map and value['mapid'] is None)
            and all(type(value[k]) in (int, float) and math.isfinite(value[k]) and abs(value[k]) <= 1000000
                    for k in ('posx', 'posy', 'posz')), 'Saved character is outside the supported Atlas instances')
        if allow_unassigned_active_map:
            self.active_map_id = value['staticmapid']
            self.creation_report['map_id'] = self.active_map_id
            self.zoning_report['saved_destination_map_id'] = self.active_map_id
        else:
            require(value['staticmapid'] == self.active_map_id,
                    'Committed character destination changed during ordinary save')
        return value

    def connected_status(self, sample):
        if sample.get('loaded') and not sample.get('in_map_transfer'):
            require(type(sample.get('map_id')) is int and sample['map_id'] == self.active_map_id
                    and type(sample.get('static_map_id')) is int and sample['static_map_id'] == self.active_map_id,
                    'Character moved outside the verified zoning epoch')
        return connected(sample, self.active_map_id)

    def connection_metadata(self):
        return dict(super().connection_metadata(), connected_on_supported_map=True, zoning_enabled=True)

    def _remember_active(self):
        self.maps[self.active_map_id] = {'process': self.map_process, 'progress_path': self.map_progress_path,
            'previous': self.map_previous, 'launch_utc_ms': self.map_launch_utc_ms, 'ready': True}

    def _activate(self, map_id):
        if self.map_process is not None and self.active_map_id in self.maps:
            self.maps[self.active_map_id]['previous'] = self.map_previous
        self.active_map_id = map_id
        owned = self.maps[map_id]
        self.map_process, self.map_progress_path = owned['process'], owned['progress_path']
        self.map_previous, self.map_launch_utc_ms = owned.get('previous'), owned['launch_utc_ms']
        self.map_progress_next = 0
        self.creation_report['map_id'] = map_id

    def start_map(self):
        if self.active_map_id == 1:
            super().start_map()
            self._remember_active()
        else:
            self.ctx.stage('local_atlas_instance_startup')
            baseline = parse_map_status(self.query(['-getstatus', '1', '101'], 'zoning-reopen-baseline'),
                                        101, allow_missing=True)
            require(baseline.get('not_started') is True, 'Saved destination already has an unowned MapServer')
            self._spawn_map(101)
            deadline = min(self.ctx.deadline, time.monotonic() + character.MAP_STARTUP_SECONDS)
            next_query = 0
            while True:
                self.ctx.check()
                require(time.monotonic() < deadline, 'Saved Atlas instance startup timed out; preserve data and export')
                current = self._map_progress(101)
                if self.live_progress(current) and time.monotonic() >= next_query:
                    next_query = time.monotonic() + 15
                    sample = parse_map_status(self.query(['-getstatus', '1', '101'], 'zoning-reopen-ready'), 101)
                    if ready(sample, 101) and self.live_progress(self._map_progress(101)):
                        self.maps[101]['ready'] = True
                        self._activate(101)
                        self.creation_report.update(map_ready=True, map_startup_guard={'passed': True,
                            'protocol': sample, 'after': current, 'requires_completed_tick_before_protocol': True})
                        self.report['mapserver_started'] = self.ctx.report['mapserver_started'] = True
                        self.ctx.passed(atlas_ready=True, map=sample, loopback_only=True)
                        break
                time.sleep(.2)
        self.ready_floor_ms = self.map_launch_utc_ms - 999

    def _spawn_map(self, map_id):
        require(supported(map_id) and map_id not in self.maps and len(self.maps) < 2,
                'Duplicate or unreviewed zoning MapServer launch')
        character.game.check_game_port(MAPS[map_id]['port'], socket.SOCK_DGRAM)
        path = self.runtime / ('character-zoning-' + str(map_id) + '-progress.bin')
        require(not path.exists() and not path.is_symlink(), 'Stale zoning map progress file')
        environment = dict(self.owner.wine_env, **{character.evidence.GAME_LOOPBACK_ENV: '1',
            character.progress.ENVIRONMENT: base.windows_path(path)})
        if map_id == 1 and self.immediate_event_contract() is not None:
            character.character_events.validate_contract(self.immediate_event_contract())
            environment[character.character_events.ENVIRONMENT] = self.owner.args.session_id
            self.creation_report.setdefault('immediate_native_events', {'enabled': True,
                'contract': self.immediate_event_contract(), 'legacy_sorted_logs_used_for_ready_or_ground': False})
        launch_ms = int(time.time() * 1000)
        process = self.ctx.start('local-character-zoning-' + str(map_id), ['/usr/bin/env', '--chdir=' + str(self.runtime),
            self.owner.args.wine, base.windows_path(self.runtime / 'MapServer.exe'), '-nogui', '-db', '127.0.0.1',
            '-nosharedmemory', '-nostats', '-udp', str(MAPS[map_id]['port']), '-tcp', '0', '-map_id', str(map_id),
            '-idleExitTimeout', '0', '-donotautogroup'], env=environment)
        self.maps[map_id] = {'process': process, 'progress_path': path, 'previous': None,
                             'launch_utc_ms': launch_ms, 'ready': False}

    def _map_progress(self, map_id):
        owned = self.maps[map_id]
        require(owned['process'].process.poll() is None and not owned['process'].overflow,
                'Owned zoning MapServer exited or overflowed')
        console = owned['process'].text()
        require(re.search(r'Program crash detected|Exception caught: EXCEPTION_[A-Z_]+', console) is None,
                'Owned zoning MapServer crashed')
        try:
            owned['previous'] = character.progress.read_record(owned['progress_path'], owned.get('previous'))
        except (FileNotFoundError, character.progress.PublicationPending):
            return None
        if map_id == self.active_map_id:
            self.map_previous = owned['previous']
        return owned['previous']

    def health(self):
        super().health()
        # Read-only health checks never spawn a process or recurse through ctx.check.
        for map_id, owned in self.maps.items():
            if map_id == self.active_map_id:
                continue
            require(not owned['process'].overflow, 'Zoning MapServer console overflowed')
            if owned.get('ready'):
                require(owned['process'].process.poll() is None, 'Ready zoning destination exited; export the report')

    def current_native_events(self):
        return super().current_native_events() if self.active_map_id == 1 else None

    def native_ready_record(self):
        if self.active_map_id == 1:
            value = super().native_ready_record()
            if value is not None and value.get('utc_ms', 0) >= self.ready_floor_ms:
                return value
            return None
        return stock_ready(self.current_logs(), self.active_map_id, self.ready_floor_ms, int(time.time() * 1000))

    def native_positions(self):
        if self.active_map_id == 1:
            return [p for p in super().native_positions() if p['utc_ms'] >= self.ready_floor_ms]
        return stock_positions(self.current_logs(), self.active_map_id, self.ready_floor_ms, int(time.time() * 1000))

    def native_ground_evidence(self, delivery, *, max_age_ms=180000):
        return character.stable_ground_evidence([], delivery, int(time.time() * 1000),
            max_age_ms=max_age_ms, positions=self.native_positions())

    def native_logout_record(self):
        return stock_logout(self.current_logs(), self.active_map_id, self.ready_floor_ms, int(time.time() * 1000))

    def native_terminal_position(self, delivery, ready_utc_ms, now_utc_ms):
        return terminal_position(self.current_logs(), self.active_map_id, delivery, ready_utc_ms, now_utc_ms)

    def _emit(self, status, **fields):
        target = self.pending['to_map_id'] if self.pending else (101 if self.active_map_id == 1 else 1)
        value = {'format': 1, 'session_id': self.owner.args.session_id,
            'client_pid': self.creation_report['client_pid'], 'character_id': 1,
            'epoch': self.epoch, 'status': status, 'current_map_id': self.active_map_id,
            'target_map_id': target, 'current_map_name': MAPS[self.active_map_id]['name'],
            'target_map_name': MAPS[target]['name'], 'generated_utc_ms': int(time.time() * 1000),
            'epoch_limit': MAX_EPOCHS, **fields}
        self.zoning_report['events'].append(value)
        self.zoning_report['status'] = status
        self.ctx.event('character_zoning', **value)
        return value

    def _query_start(self, arguments, label):
        require(self.zoning_query is None, 'Concurrent zoning protocol query refused')
        self.query_count += 1
        require(self.query_count <= 160, 'Character protocol query budget exceeded')
        child = self.ctx.start('zoning-' + label, ['/usr/bin/env', '--chdir=' + str(self.runtime),
            self.owner.args.wine, base.windows_path(self.runtime / 'MapServer.exe'), '-nogui',
            '-db', '127.0.0.1', '-dbquery', '-timeout', '10000', *arguments], env=self.owner.wine_env)
        self.zoning_query = (label, child, time.monotonic() + 90)

    def _query_poll(self):
        if self.zoning_query is None:
            return None
        label, child, deadline = self.zoning_query
        require(time.monotonic() < deadline, 'Zoning protocol query timed out')
        if child.process.poll() is None or child.reader.is_alive():
            return None
        require(child.process.poll() == 0 and not child.overflow, 'Zoning protocol query failed')
        child.completion = {'policy': 'leader_exit_and_output_eof', 'leader_exit_code': 0,
            'output_capture_open': False, 'elapsed_seconds': round(time.monotonic() - child.started, 3)}
        self.ctx.record(child)
        self.zoning_query = None
        return label, child.text()

    def _accept_prepare(self, value, now_ms):
        validate_request(value, session=self.owner.args.session_id, client_pid=self.creation_report['client_pid'],
            epoch=self.epoch + 1, origin=self.active_map_id, action='prepare', now_ms=now_ms)
        require(self.pending is None and self.creation_report.get('verified') is not True,
                'Zoning preparation overlaps another transfer or completed save')
        require(not (self.owner.args.state / 'character-logout.json').exists(), 'Zoning requested after logout')
        require(self.creation_report.get('recovery_requested') is False
                and not (self.owner.args.state / 'character-relocation.json').exists(),
                'Finish the current recovery/save session before testing zoning')
        self.epoch += 1
        self.request_history[self.epoch] = dict(value)
        self.pending = dict(value, phase='baseline', deadline=time.monotonic() + PREPARE_SECONDS,
                            next_query=0, transfer_requested=False)
        self._emit('preparing', current_map_verified=True, destination_ready=False)
        target = value['to_map_id']
        if target in self.maps:
            self.pending['phase'] = 'map_ready'
        else:
            self._query_start(['-getstatus', '1', str(target)], 'baseline')

    def _accept_delivery(self, value, now_ms):
        require(self.pending is not None and self.pending['phase'] == 'ready',
                'Zoning command lacks a prepared destination')
        validate_request(value, session=self.owner.args.session_id, client_pid=self.creation_report['client_pid'],
            epoch=self.epoch, origin=self.active_map_id, action='mapmove', now_ms=now_ms)
        require(value['to_map_id'] == self.pending['to_map_id']
                and value['sent_utc_ms'] >= self.pending['ready_utc_ms'],
                'Zoning command preceded destination readiness')
        require(self.live_progress(self._map_progress(value['to_map_id'])), 'Prepared destination became stale')
        self.delivery_history[self.epoch] = dict(value)
        self.pending.update(phase='arrival', delivery=dict(value), transfer_requested=True,
                            deadline=time.monotonic() + TRANSFER_SECONDS, next_query=0)
        self._emit('transferring', current_map_verified=False, transfer_requested=True)

    def _observe_arrival(self, result, now_ms):
        pending = self.pending
        target = pending['to_map_id']
        if result is not None and result[0] == 'arrival_character':
            sample = character.evidence.parse_character_status(result[1], 1, character.CHARACTER, character.ACCOUNT)
            pending['arrival_character'] = sample
            if not connected(sample, target):
                pending['observed_transition'] = True
                pending['next_query'] = time.monotonic() + 3
                return
            self._query_start(['-getstatus', '1', str(target)], 'arrival_map')
            return
        if result is not None and result[0] == 'arrival_map':
            sample = parse_map_status(result[1], target)
            current = self._map_progress(target)
            if not ready(sample, target) or not self.live_progress(current):
                pending['next_query'] = time.monotonic() + 3
                return
            # Fresh native CLIENT_READY follows world loading. An assigned
            # DbServer container alone cannot satisfy arrival.
            minimum = pending['delivery']['sent_utc_ms'] - 999
            native = stock_ready(self.current_logs(), target, minimum, now_ms)
            if native is None or native['line_sha256'] in pending.get('prior_ready_hashes', []):
                pending['next_query'] = time.monotonic() + 3
                return
            pending.update(arrival_map=sample, arrival_native=native)
            self._query_start(['-getstatus', '3', '1'], 'arrival_final_character')
            return
        if result is not None and result[0] == 'arrival_final_character':
            sample = character.evidence.parse_character_status(result[1], 1, character.CHARACTER, character.ACCOUNT)
            current = self._map_progress(target)
            if not connected(sample, target) or not self.live_progress(current):
                pending['observed_transition'] = True
                pending['next_query'] = time.monotonic() + 3
                return
            require(self.ctx.report.get('client_launch', {}).get('pid') == self.creation_report['client_pid']
                    and self.owner.client.process.poll() is None,
                    'Graphical client process changed during native zoning')
            native = pending['arrival_native']
            require(native['utc_ms'] >= pending['delivery']['sent_utc_ms'] - 999,
                    'Zoning native readiness became stale')
            origin = self.active_map_id
            self._activate(target)
            self.ready_floor_ms = native['utc_ms']
            self.creation_report.update(client_ready_evidence=native, client_ready_observed_utc=base.utc(),
                client_ready_observed_utc_ms=native['utc_ms'], connected_on_supported_map=True,
                connected_on_atlas=True, map_id=target, zoning_epoch=self.epoch,
                recovery_requested=False, recovery_verified=False, ordinary_stuck_observed=False,
                on_atlas_safe_position=False, stable_ground_verified=False, committed_safe_position_verified=False)
            leg = {'epoch': self.epoch, 'from_map_id': origin, 'to_map_id': target,
                'delivery': pending['delivery'], 'native_ready': native,
                'character_status': sample, 'initial_character_status': pending['arrival_character'],
                'map_status': pending['arrival_map'], 'owned_progress': current,
                'elapsed_ms': now_ms - pending['delivery']['sent_utc_ms'],
                'native_timestamp_precision_ms': 1000, 'same_client_pid': self.creation_report['client_pid'],
                'observed_transfer_flag_or_disconnected': pending.get('observed_transition', False),
                'arrival_native_verified': True, 'sql_transfer_commit_acknowledged': False}
            self.zoning_report['transfers'].append(leg)
            self._emit('arrived', current_map_verified=True, destination_ready=True,
                arrival_native_verified=True, mapserver_pid=current['windows_pid'],
                elapsed_ms=leg['elapsed_ms'], exact_destination_endpoint_verified=True,
                character_identity_preserved=True, native_ready_utc_ms=native['utc_ms'])
            self.pending = None
            return
        if self.zoning_query is None and time.monotonic() >= pending['next_query']:
            self._query_start(['-getstatus', '3', '1'], 'arrival_character')

    def tick_zoning(self):
        if not self.creation_report.get('connected_on_atlas') or not self.creation_report.get('client_pid'):
            return
        now = time.monotonic()
        if now < self.zoning_next:
            return
        self.zoning_next = now + 1
        if not self.enabled_announced:
            self.enabled_announced = True
            self._emit('enabled', current_map_verified=True, zoning_enabled=True)
        # A corrupt/foreign post-send receipt cannot be treated as proof that
        # no command was sent. Only a fully parsed, unchanged historical receipt
        # can clear this conservative uncertainty flag.
        delivery_path = self.owner.args.state / 'character-zoning-delivery.json'
        unseen_delivery = delivery_path.exists() or delivery_path.is_symlink()
        try:
            now_ms = int(time.time() * 1000)
            delivery = read_request(delivery_path)
            if delivery is not None and delivery == self.delivery_history.get(delivery.get('epoch')):
                unseen_delivery = False
            request = read_request(self.owner.args.state / 'character-zoning-request.json')
            if request is not None:
                old = self.request_history.get(request.get('epoch'))
                if old is not None:
                    require(request == old, 'Accepted zoning preparation receipt changed')
                else:
                    self._accept_prepare(request, now_ms)
            if delivery is not None:
                old = self.delivery_history.get(delivery.get('epoch'))
                if old is not None:
                    require(delivery == old, 'Accepted zoning delivery receipt changed')
                else:
                    unseen_delivery = True
                    self._accept_delivery(delivery, now_ms)
            if self.pending is None:
                return
            pending, target = self.pending, self.pending['to_map_id']
            require(now < pending['deadline'], 'Zoning preparation or arrival timed out; export this report')
            result = self._query_poll()
            if pending['phase'] == 'arrival':
                self._observe_arrival(result, now_ms)
                return
            if result is not None and result[0] == 'baseline':
                baseline = parse_map_status(result[1], target, allow_missing=True)
                require(baseline.get('not_started') is True, 'Zoning destination already belongs to another process')
                pending['baseline'] = baseline
                self._spawn_map(target)
                pending['phase'] = 'map_ready'
            if pending['phase'] == 'map_ready':
                current = self._map_progress(target)
                if result is not None and result[0] == 'prepared_map':
                    sample = parse_map_status(result[1], target)
                    if ready(sample, target) and self.live_progress(current):
                        self.maps[target]['ready'] = True
                        logs = self.current_logs()
                        prior = stock_ready(logs, target, 0, now_ms)
                        pending.update(phase='ready', ready_utc_ms=now_ms, destination_status=sample,
                                       prior_ready_hashes=[prior['line_sha256']] if prior else [])
                        self._emit('ready', current_map_verified=True, destination_ready=True,
                                   mapserver_pid=current['windows_pid'])
                        return
                if self.zoning_query is None and self.live_progress(current) and now >= pending['next_query']:
                    pending['next_query'] = now + 10
                    self._query_start(['-getstatus', '1', str(target)], 'prepared_map')
        except (base.DiagnosticError, OSError, ValueError, KeyError, TypeError) as failure:
            uncertain = unseen_delivery or bool(self.pending and self.pending.get('transfer_requested'))
            self.zoning_report['failure'] = {'message': str(failure)[:300], 'transfer_requested': uncertain}
            self._emit('failed', message=str(failure)[:300], transfer_requested=uncertain,
                       current_map_verified=not uncertain)
            # Do not continue playing or report an ordinary save after an
            # uncertain handoff. Cleanup preserves the real committed profile.
            if uncertain:
                raise
            self.zoning_report['preparation_failed'] = True
            self.pending = None
            self.zoning_next = float('inf')

    def character_evidence(self):
        self.tick_zoning()
        if self.pending is not None and self.pending.get('transfer_requested'):
            return None
        # The ordinary Atlas save path is retained, with only map-scoped native
        # witnesses and read-only finite-map position validation overridden.
        return super().character_evidence()

    def saved_metadata(self, snapshot):
        return dict(super().saved_metadata(snapshot), zoning_enabled=True,
            connected_on_supported_map=True, map_id=self.active_map_id,
            zoning_epoch=self.epoch, ordinary_save_after_native_zoning=True)

    def collect(self, target):
        super().collect(target)
        for map_id, owned in self.maps.items():
            if owned['process'] is self.map_process:
                continue
            raw = base.redact(owned['process'].text(), self.ctx.secrets)
            require(len(raw.encode()) <= 16 * 1024 * 1024, 'Zoning server console export exceeded bound')
            base.private_write(target / ('character-zoning-map-' + str(map_id) + '-console.txt'), raw)
        base.private_write(target / 'character-zoning.json', json.dumps(self.zoning_report, indent=2) + '\n')


def character_identity(proof, session):
    return (isinstance(proof, dict) and proof.get('session_id') == session
        and proof.get('name') == 'THORHERO' and proof.get('account') == 'COHLOCAL'
        and type(proof.get('character_id')) is int and proof['character_id'] == 1
        and type(proof.get('auth_id')) is int and proof['auth_id'] > 0 and supported(proof.get('map_id'))
        and type(proof.get('before_character_id')) is int and proof['before_character_id'] == 1
        and type(proof.get('baseline_character_id')) is int and proof['baseline_character_id'] == 1
        and all(proof.get(k) is True for k in ('zoning_enabled', 'connected_on_atlas',
            'connected_on_supported_map', 'existing_character_verified', 'reopen_verified',
            'preserved_existing_identity', 'native_client_ready_observed')))


def save_verified(proof, session):
    if not character_identity(proof, session):
        return False
    required = ('verified', 'committed_sql_verified', 'requested_logout_observed', 'logout_timer_observed',
        'disconnected_before_sql', 'powers_preserved', 'costume_preserved', 'selected_rows_preserved',
        'committed_native_position_verified')
    if not all(proof.get(k) is True for k in required) or proof.get('forced_stop_before_save') is not False:
        return False
    if type(proof.get('recovery_requested')) is not bool:
        return False
    recovery = ('recovery_verified', 'ordinary_stuck_observed', 'on_atlas_safe_position',
                'stable_ground_verified', 'committed_safe_position_verified')
    if not all(proof.get(k) is proof['recovery_requested'] for k in recovery):
        return False
    before, after = proof.get('before_login_count'), proof.get('login_count')
    return type(before) is int and 0 < before < 2**31 - 1 and type(after) is int and after == before + 1
