"""Finite native station travel with read-only SQL and exact owned evidence.

Legacy Atlas 1/101 retains its stock logger route and original producer contract.
The separately qualified MapServer adds a distinct immediate stream for the
actual Atlas/Kings Row station route; Game and DbServer bytes are unchanged.
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
import character_session_budget as session_budget
import character_zoning_scheduler as scheduler
import native_monorail_events as monorail_events
import native_monorail_contract as monorail_contract

base, require = character.base, character.require
MAPS = {1: {'name': 'Atlas Park', 'port': 7001, 'instance': 1, 'world': 'City_01_01'},
        101: {'name': 'Atlas Park instance 2', 'port': 7002, 'instance': 2, 'world': 'City_01_01'},
        5: {'name': "King's Row", 'port': 7003, 'instance': 1, 'world': 'City_01_02'}}
MAX_EPOCHS = 4
PREPARE_SECONDS = 600
WARM_PREPARE_SECONDS = 90
# Cold Kings preparation and native startup are distinct bounded phases. The
# .31 Thor run completed both but its single 600-second clock expired first.
# These are lifecycle allowances, not a measured loading-speed improvement.
KINGS_PYTHON_PREPARE_SECONDS = 420
KINGS_NATIVE_READY_SECONDS = 360
KINGS_TOTAL_PREPARE_SECONDS = 720
TRANSFER_SECONDS = 180
REQUEST_AGE_MS = 120000
NUMBER = character.character_events.NUMBER
PREPARATION_FIELDS = (
    'requested_utc_ms', 'preparation_started_utc_ms', 'preparation_ready_utc_ms',
    'preparation_elapsed_ms', 'preparation_kind', 'preparation_budget_seconds',
    'python_preparation_budget_seconds', 'native_ready_budget_seconds',
    'preparation_budget_policy', 'preparation_phase', 'preparation_deadline_utc_ms',
    'preparation_absolute_cap_basis', 'preparation_request_age_ms',
    'python_preparation_started_utc_ms', 'python_preparation_finished_utc_ms',
    'python_preparation_elapsed_ms', 'runtime_preparation_elapsed_ms', 'python_preparation_completed',
    'python_preparation_deadline_utc_ms', 'native_ready_started_utc_ms',
    'native_ready_finished_utc_ms', 'native_ready_elapsed_ms', 'native_ready_deadline_utc_ms',
    'departure_deadline_utc_ms', 'session_deadline_utc_ms', 'session_budget_extended', 'manual_session')


def travel_window(deadline, now, now_ms, preparation_seconds, *, manual=False):
    """Reserve arrival, neutral wait and ordinary save within the existing cap."""
    if manual:
        return {'preparation_budget_seconds': preparation_seconds,
            'transfer_budget_seconds': TRANSFER_SECONDS,
            'departure_deadline_utc_ms': 0, 'session_deadline_utc_ms': 0,
            'session_budget_extended': False, 'manual_session': True}
    require(type(deadline) in (int, float) and math.isfinite(deadline),
            'Zoning requires the existing connected session budget')
    movement_end = deadline - (session_budget.NEUTRAL_RESERVE_MS
                              + session_budget.SAVE_PROOF_RESERVE_MS) / 1000
    departure = movement_end - TRANSFER_SECONDS
    require(now + preparation_seconds < departure,
            'Not enough session time for preparation, arrival and ordinary save; save and reopen')
    return {'preparation_budget_seconds': preparation_seconds,
        'transfer_budget_seconds': TRANSFER_SECONDS,
        'departure_deadline_utc_ms': now_ms + int((departure - now) * 1000),
        'session_deadline_utc_ms': now_ms + int((deadline - now) * 1000),
        'session_budget_extended': False}


def preparation_budgets(map_id, resident):
    require(supported(map_id) and type(resident) is bool, 'Invalid zoning preparation identity')
    python_seconds = KINGS_PYTHON_PREPARE_SECONDS if map_id == 5 and not resident else 0
    native_seconds = (WARM_PREPARE_SECONDS if resident else
                      KINGS_NATIVE_READY_SECONDS if map_id == 5 else PREPARE_SECONDS)
    return {'python_preparation_budget_seconds': python_seconds,
            'native_ready_budget_seconds': native_seconds,
            'preparation_budget_seconds': (KINGS_TOTAL_PREPARE_SECONDS if python_seconds
                                           else native_seconds),
            'preparation_budget_policy': 'bounded_python_then_native_ready_v1'}


def scan_new_console(owned):
    """Scan each appended byte once, retaining overlap for split crash markers."""
    output = owned['process'].output
    offset, size = owned.get('crash_scan_offset', 0), len(output)
    require(size >= offset, 'Owned zoning console was truncated')
    # Pattern has one bounded fixed prefix and an uppercase suffix. Its exact
    # failure prefix alone is decisive, including when split across writes.
    chunk = bytes(output[max(0, offset - 64):size])
    require(re.search(rb'Program crash detected|Exception caught: EXCEPTION_[A-Z_]+', chunk) is None,
            'Owned zoning MapServer crashed')
    owned['crash_scan_offset'] = size
    owned['console_bytes_scanned'] = owned.get('console_bytes_scanned', 0) + len(chunk)


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
    require(name.replace('\\', '/').split('/')[-1].casefold() == MAPS[map_id]['world'].lower() + '.txt',
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
    route = MAPS[map_id]['world'] + '_' + str(MAPS[map_id]['instance'])
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
        self.native_station_seen = {}
        self.request_history = {}
        self.delivery_history = {}
        self.zoning_report = {'format': 1, 'scope': 'native_station_or_Atlas_instance_handoff',
            'supported_maps': MAPS, 'events': [], 'transfers': [], 'epoch_limit': MAX_EPOCHS,
            'new_city_asset_coverage': False, 'sql_game_mutations_performed': False,
            'target_seconds': 30, 'physical_zoning_validated': False}
        self.zoning_report.update(preparations=[], native_build_reused=True,
            total_travel_includes_preparation=True, preparation_overlap_with_gameplay=True,
            cold_definition='destination_process_not_resident_filesystem_cache_unknown',
            finite_process_limit=2, preparation_stage_observations=[], preparation_schedulers=[],
            preparation_phase_observations=[])
        self.ctx.report['character_zoning'] = self.zoning_report
        self.creation_report.update(zoning_enabled=True, connected_on_supported_map=False)

    def monorail_enabled(self):
        return getattr(self, 'monorail_qualified', False) is True

    def capture_baseline(self):
        # The inherited baseline checks the complete accepted identity and
        # selected SQL rows before character_position selects the saved map.
        # This event is observational: it cannot authorize relocation or login.
        super().capture_baseline()
        prepared = getattr(self, 'startup_preparation_map_id', self.active_map_id)
        require(self.active_map_id == prepared,
                'Saved destination changed during startup; preserve data and export')
        destination = MAPS[self.active_map_id]
        position = self.creation_report['baseline']['saved_position']
        self.zoning_report['saved_startup'] = {
            'map_id': self.active_map_id, 'name': destination['name'],
            'world': destination['world'], 'port': destination['port'],
            'saved_position': dict(position), 'authority': 'preserved_postgresql_ents_staticmapid',
            'sql_game_mutations_performed': False, 'native_ready_verified': False,
            'character_world_entry_verified': False}
        self.ctx.event('saved_character_destination', session_id=self.owner.args.session_id,
            character_id=self.CHARACTER_ID, auth_id=self.baseline_snapshot['identity']['authid'],
            name=character.CHARACTER, account=character.ACCOUNT, map_id=self.active_map_id,
            map_name=destination['name'], world=destination['world'], port=destination['port'],
            existing_character_verified=True, saved_location_verified=True,
            sql_game_mutations_performed=False)
        self.persist_startup_observation()

    def qualify_monorail_preparation(self):
        if 'native_monorail' not in self.map_package:
            return
        monorail_contract.embedded_receipt(self.map_package)
        graph = self.creation_report.get('kings_row_beacon_graph', {})
        require(graph.get('verified') is True and graph.get('map_id') == 5,
                'Kings Row native collision/beacon package is not verified')
        self.monorail_qualified = True
        self.creation_report['monorail_enabled'] = True
        self.zoning_report.update(monorail_enabled=True, new_city_asset_coverage=True,
            station_line='ParagonCityMonorail', station_maps=[1, 5],
            readiness_transport='immediate_owned_native_console')

    def initial_map_preparation(self):
        # The persistent cluster is already open and eligibility checked. Bind
        # its full identity and saved position before deciding which expensive
        # native world provider to prepare; no SQL writes or default relocation.
        self.qualify_monorail_preparation()
        self.capture_baseline()
        self.startup_preparation_map_id = self.active_map_id
        return self.active_map_id

    def prepare_runtime(self):
        super().prepare_runtime()
        self.qualify_monorail_preparation()

    def monorail_environment(self, map_id):
        return {monorail_events.ENVIRONMENT: self.owner.args.session_id,
            monorail_events.REPLY_ENVIRONMENT: base.windows_path(
                self.runtime / ('monorail-' + str(map_id) + '-reply.txt'))}

    def map_native_events(self, map_id):
        owned = self.maps[map_id]
        current = self._map_progress(map_id)
        if not self.live_progress(current):
            return []
        values = monorail_events.records(monorail_events.console_events(owned), session=self.owner.args.session_id,
            progress=current, launch_utc_ms=owned['launch_utc_ms'], now_utc_ms=int(time.time()*1000),
            db_id=self.creation_report['character_id'], auth_id=self.auth_id, map_id=map_id)
        self.zoning_report.setdefault('native_event_observations', {})[str(map_id)] = {
            'event_count': len(values), 'latest_event': values[-1] if values else None,
            'console_bytes_scanned': owned.get('monorail_scan_offset', 0),
            'observed_utc_ms': int(time.time()*1000)}
        return values

    def _authorize_station(self, record):
        path = self.runtime / ('monorail-' + str(record['map_id']) + '-reply.txt')
        require(not path.is_symlink(), 'Linked monorail reply refused')
        temporary = path.with_suffix('.pending')
        require(not temporary.exists() and not temporary.is_symlink(), 'Stale monorail reply staging file')
        require(self.pending is not None and self.pending.get('phase') == 'ready'
                and not (self.owner.args.state / 'character-logout.json').exists(),
                'Monorail authorization cancelled for ordinary save')
        self._check_preparation_deadline()
        base.private_write(temporary, monorail_events.reply(record))
        self._check_preparation_deadline()
        # After publishing, native departure can race the next observer tick.
        # Any failure from here is an uncertain handoff and must stop gameplay.
        self.pending['native_authorization_issued'] = True
        os.replace(temporary, path)

    def _observe_station(self, now_ms):
        for record in self.map_native_events(self.active_map_id):
            if record['kind'] not in ('station_request', 'station_departure'):
                continue
            key = (self.active_map_id, record['sequence'])
            seen = getattr(self, 'native_station_seen', {})
            if key in seen:
                require(seen[key] == record['line_sha256'], 'Native station request history changed')
                continue
            self.native_station_seen[key] = record['line_sha256']
            if record['kind'] == 'station_request':
                require(not getattr(self, 'monorail_requires_reopen', False),
                    'After returning from the old Atlas instance, save, Finish and reopen for Kings Row')
                request = dict(format=1, session_id=self.owner.args.session_id,
                    client_pid=self.creation_report['client_pid'], character_id=1,
                    epoch=self.epoch + 1, action='prepare', from_map_id=self.active_map_id,
                    to_map_id=record['target'], requested_utc_ms=record['utc_ms'])
                # Set these before the first preparing event reaches Android.
                self.station_accepting = record
                try:
                    self._accept_prepare(request, now_ms)
                finally:
                    self.station_accepting = None
            else:
                require(self.pending is not None and self.pending.get('native_station_request_verified')
                    and record['request'] == self.pending['native_request_sequence']
                    and record['pid'] == self.pending['native_station_pid']
                    and record['target'] == self.pending['to_map_id'],
                    'Native station departure does not match prepared request')
                value = dict(format=1, session_id=self.owner.args.session_id,
                    client_pid=self.creation_report['client_pid'], character_id=1, epoch=self.epoch,
                    action='mapmove', from_map_id=self.active_map_id, to_map_id=record['target'],
                    sent_utc_ms=record['utc_ms'])
                self._accept_delivery(value, now_ms)
                self.pending['delivery']['native_station_departure'] = record

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
                    for k in ('posx', 'posy', 'posz')), 'Saved character is outside the supported local zones')
        require(value['staticmapid'] != 5 or self.monorail_enabled(),
                'Saved Kings Row character requires the verified monorail/zone package')
        if allow_unassigned_active_map:
            self.active_map_id = value['staticmapid']
            self.monorail_requires_reopen = self.active_map_id == 101
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
        metadata = super().connection_metadata()
        startup = self.zoning_report.get('saved_startup')
        if startup is not None:
            require(startup['map_id'] == self.active_map_id,
                    'Initial character connection differs from the saved destination')
            startup['character_world_entry_verified'] = True
        return dict(metadata, connected_on_supported_map=True, zoning_enabled=True,
                    monorail_enabled=self.monorail_enabled())

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
        if self.active_map_id == 1 and getattr(self, 'overlap_client_initialization', False) is not True:
            original = self.owner.wine_env
            if self.monorail_enabled():
                self.owner.wine_env = dict(original, **self.monorail_environment(1))
            try:
                super().start_map()
            finally:
                self.owner.wine_env = original
            self._remember_active()
        else:
            # Retain the accepted stage identifier while displaying the exact
            # PostgreSQL-selected destination and independently proving it.
            self.ctx.stage('local_atlas_startup')
            target = self.active_map_id
            destination = MAPS[target]
            self.ctx.event('stage', status='running',
                message='Preparing ' + destination['name'] + ' for saved THORHERO',
                map_id=target, map_name=destination['name'], world=destination['world'],
                port=destination['port'])
            baseline = parse_map_status(self.query(['-getstatus', '1', str(target)], 'zoning-reopen-baseline'),
                                        target, allow_missing=True)
            require(baseline.get('not_started') is True, 'Saved destination already has an unowned MapServer')
            self._spawn_map(target)
            launched = self.maps[target]
            self.creation_report['map_ready'] = False
            self.report['mapserver_started'] = self.ctx.report['mapserver_started'] = True
            started = launched.get('launch_monotonic', time.monotonic())
            self.initial_map_startup = {'map_id': target, 'ready': False,
                'deadline': min(self.ctx.deadline, started + character.MAP_STARTUP_SECONDS),
                'started_monotonic': started, 'next_query': 0, 'next_message': 0, 'next_observation': 0,
                'overlap_enabled': target in (1, 5) and getattr(self, 'overlap_client_initialization', False) is True}
            rows = self.ctx.report.get('stages', [])
            self.initial_map_stage = rows[-1] if rows and rows[-1].get('stage') == 'local_atlas_startup' else None
            if self.initial_map_startup['overlap_enabled']:
                self._activate(target)
                self.ready_floor_ms = self.map_launch_utc_ms - 999
                self.creation_report['startup_overlap'] = {
                    'format': 1, 'policy': 'owned_saved_map_and_client_initialization_v2',
                    'map_id': target, 'native_map_launch_utc_ms': self.map_launch_utc_ms,
                    'native_map_launch_monotonic': started,
                    'client_preparation_overlap_started_monotonic': time.monotonic(),
                    'private_map_preparation_complete': True,
                    'native_map_ready_verified': False, 'client_input_admitted': False,
                    'native_processes_share_mutable_data': False,
                    'initializing_progress_observations': [],
                    'physical_loading_gain_validated': False,
                    'peak_memory_effect_measured': False}
                self.sample_startup_observation(force=True)
                return
            while not self.poll_initial_map_startup():
                time.sleep(.2)
        startup = self.zoning_report.get('saved_startup')
        if startup is not None:
            startup.update(native_ready_verified=True, native_maps_started=sorted(self.maps))
        self.ready_floor_ms = self.map_launch_utc_ms - 999

    def client_startup_assets_allowed(self):
        """Only a completely prepared owned world can overlap client loading."""
        startup = getattr(self, 'initial_map_startup', None)
        if not startup or startup['ready'] or startup['overlap_enabled'] is not True:
            return False
        target = startup['map_id']
        owned = self.maps.get(target)
        if target == 5:
            expected_runtime = getattr(self, 'kings_row_runtime', None)
            graph = self.creation_report.get('kings_row_beacon_graph', {})
            graph_ready = graph.get('verified') is True and graph.get('map_id') == 5
        else:
            expected_runtime = getattr(self, 'atlas_map_runtime', None) or self.runtime
            graph = self.creation_report.get('atlas_beacon_graph', {})
            graph_ready = (graph.get('status') in ('installed_verified_graph', 'reused_verified_graph')
                and graph.get('map') == 'maps/city_zones/city_01_01/city_01_01.txt'
                and (not getattr(self, 'atlas_preparation_deferred', False)
                     or getattr(self, 'atlas_runtime_prepared', False) is True))
        require(target in (1, 5) and target == self.active_map_id == self.startup_preparation_map_id
                and expected_runtime is not None and owned is not None
                and owned.get('runtime') == expected_runtime and graph_ready
                and owned['process'].process.poll() is None and not owned['process'].overflow,
                'Client overlap lacks the prepared owned saved destination process')
        return True

    def poll_initial_map_startup(self):
        """Main-thread readiness join; never grant entry from process launch alone."""
        startup = getattr(self, 'initial_map_startup', None)
        if startup is None:
            return self.creation_report.get('map_ready') is True
        if startup['ready']:
            return True
        self.ctx.check()
        now = time.monotonic()
        target = startup['map_id']; destination = MAPS[target]
        require(now < startup['deadline'],
                'Saved ' + destination['name'] + ' startup timed out; preserve data and export')
        current = self._map_progress(target)
        self.observe_initial_map_progress(current, now)
        if self.live_progress(current) and now >= startup['next_query']:
            startup['next_query'] = now + 15
            sample = parse_map_status(self.query(['-getstatus', '1', str(target)], 'zoning-reopen-ready'), target)
            after = self._map_progress(target)
            if ready(sample, target) and self.live_progress(after):
                character.progress.compare_records(after, current)
                self.maps[target]['ready'] = True
                self._activate(target)
                self.creation_report.update(map_ready=True, map_startup_guard={'passed': True,
                    'protocol': sample, 'before': current, 'after': after,
                    'requires_completed_tick_before_protocol': True})
                startup['ready'] = True
                completed = time.monotonic()
                saved = self.zoning_report.get('saved_startup')
                if saved is not None:
                    saved.update(native_ready_verified=True, native_map=sample,
                        native_maps_started=sorted(self.maps))
                overlap = self.creation_report.get('startup_overlap')
                if overlap is not None:
                    client = getattr(self.owner, 'client', None)
                    client_started = getattr(client, 'started', None)
                    overlap.update(native_map_ready_verified=True,
                        native_map_ready_utc_ms=int(time.time() * 1000),
                        native_map_ready_monotonic=completed,
                        native_map_ready_seconds=round(completed - startup['started_monotonic'], 6),
                        native_ready_timing_is_sampled_upper_bound=True,
                        native_client_launch_monotonic=client_started,
                        observed_native_process_overlap_seconds=(round(max(0, completed
                            - max(client_started, startup['started_monotonic'])), 6)
                            if type(client_started) in (int, float) else 0),
                        observed_client_preparation_overlap_seconds=round(max(0, completed
                            - overlap['client_preparation_overlap_started_monotonic']), 6),
                        observed_native_initialization_overlap_lower_bound_seconds=(round(max(0,
                            overlap.get('last_initializing_progress_observed_monotonic', client_started)
                            - client_started), 6) if type(client_started) in (int, float) else 0),
                        overlap_scope='owned_process_residency_until_sampled_readiness; '
                                      'initialization_overlap_requires_zero_tick_progress_witness; '
                                      'not_an_isolated_cpu_speedup_measurement')
                    # Complete the map's original stage record. The current
                    # stage belongs to client loading and must not be marked
                    # passed by an independent MapServer readiness observation.
                    stage = getattr(self, 'initial_map_stage', None)
                    if stage is not None:
                        stage.update(status='passed', finished_utc=base.utc(), map_ready=True,
                            map_id=target, map=sample, readiness_completed_during_client_initialization=True)
                    self.ctx.event('saved_map_native_ready', session_id=self.owner.args.session_id,
                        map_id=target, map_name=destination['name'], world=destination['world'],
                        port=destination['port'], native_ready_verified=True,
                        elapsed_seconds=overlap['native_map_ready_seconds'])
                else:
                    self.ctx.passed(atlas_ready=True, map=sample, loopback_only=True)
                self.sample_startup_observation(force=True)
                return True
        if now >= startup['next_message']:
            self.ctx.event('stage', status='running',
                message='Starting ' + destination['name'] + (' and City of Heroes' if startup['overlap_enabled'] else ' for saved THORHERO'),
                map_id=target, map_name=destination['name'], world=destination['world'], port=destination['port'])
            startup['next_message'] = now + 5
        return False

    def observe_initial_map_progress(self, sample, now):
        overlap = self.creation_report.get('startup_overlap')
        if overlap is None or not isinstance(sample, dict) or sample.get('available') is not True:
            return
        if type(sample.get('tick_completed')) is int and sample['tick_completed'] == 0:
            overlap['last_initializing_progress_observed_monotonic'] = now
            stages = overlap['initializing_progress_observations']
            if (not stages or stages[-1]['stage'] != sample.get('stage')) and len(stages) < 64:
                stages.append({'stage': sample.get('stage'), 'observed_monotonic': now,
                    'observed_utc_ms': int(time.time() * 1000), 'completed_ticks': 0})
        elif self.live_progress(sample) and 'first_completed_tick_observed_monotonic' not in overlap:
            overlap.update(first_completed_tick_observed_monotonic=now,
                first_completed_tick_observed_utc_ms=int(time.time() * 1000),
                first_completed_tick_observed_seconds=round(now - self.initial_map_startup['started_monotonic'], 6),
                first_tick_observation_is_sampled_upper_bound=True,
                first_tick_alone_grants_readiness=False)

    def _spawn_map(self, map_id):
        require(supported(map_id) and map_id not in self.maps and len(self.maps) < 2,
                'Duplicate or unreviewed zoning MapServer launch')
        def prepare_destination():
            if map_id != 5:
                return self.prepare_atlas_runtime()
            prepared = self.prepare_kings_row_runtime()
            require(prepared.get('graph', {}).get('verified') is True
                    and prepared['graph'].get('map_id') == 5, 'Kings Row native graph installation failed')
            return prepared['runtime']

        bounded = (self.pending is not None and self.pending['to_map_id'] == map_id
                   and (map_id == 5 or getattr(self, 'atlas_preparation_deferred', False)))
        if bounded:
            self._check_preparation_deadline()
            runtime_started = time.monotonic()
            if map_id != 5:
                # Deferred Atlas consumes its existing shared preparation
                # allowance; this does not increase the native bridge timeout.
                self.pending.update(preparation_phase='python_inputs',
                    python_preparation_started_utc_ms=int(time.time() * 1000),
                    python_preparation_deadline_utc_ms=self.pending['preparation_deadline_utc_ms'])
            original_check = self.ctx.check
            def check_python_preparation():
                original_check()
                self._check_preparation_deadline()
                require(not (self.owner.args.state / 'character-logout.json').exists(),
                        'Preparation cancelled for the requested ordinary save')
            self.ctx.check = check_python_preparation
            try:
                self.ctx.check()
                map_runtime = prepare_destination()
            finally:
                self.ctx.check = original_check
                now = time.monotonic()
                self.pending.update(python_preparation_finished_utc_ms=int(time.time() * 1000),
                    python_preparation_elapsed_ms=round((now - self.pending['preparation_started_monotonic']) * 1000),
                    runtime_preparation_elapsed_ms=round((now - runtime_started) * 1000),
                    python_preparation_completed=False)
            now = time.monotonic()
            now_ms = int(time.time() * 1000)
            pending = self.pending
            self._check_preparation_deadline()
            require(not (self.owner.args.state / 'character-logout.json').exists(),
                    'Preparation cancelled for the requested ordinary save')
            pending.update(python_preparation_completed=True,
                           preparation_phase='native_readiness', native_ready_started_utc_ms=now_ms,
                           native_ready_started_monotonic=now)
            pending['deadline'] = min(now + pending['native_ready_budget_seconds'],
                pending['preparation_overall_deadline'], pending['departure_deadline_monotonic'])
            pending['native_ready_deadline_utc_ms'] = now_ms + int((pending['deadline'] - now) * 1000)
            self._preparation_observation()
            self._check_preparation_deadline()
        else:
            map_runtime = prepare_destination()
        character.game.check_game_port(MAPS[map_id]['port'], socket.SOCK_DGRAM)
        path = self.runtime / ('character-zoning-' + str(map_id) + '-progress.bin')
        require(not path.exists() and not path.is_symlink(), 'Stale zoning map progress file')
        environment = dict(self.owner.wine_env, **{character.evidence.GAME_LOOPBACK_ENV: '1',
            character.progress.ENVIRONMENT: base.windows_path(path)})
        pacing = None
        if self.pending is not None:
            pacing = scheduler.PreparationScheduler(self.owner, map_id)
            environment.update(pacing.environment)
            self.zoning_report['preparation_schedulers'].append(pacing.report)
            self._scheduler_observation('capability', pacing)
        if map_id == 1 and self.immediate_event_contract() is not None:
            character.character_events.validate_contract(self.immediate_event_contract())
            environment[character.character_events.ENVIRONMENT] = self.owner.args.session_id
            self.creation_report.setdefault('immediate_native_events', {'enabled': True,
                'contract': self.immediate_event_contract(), 'legacy_sorted_logs_used_for_ready_or_ground': False})
        if self.monorail_enabled():
            environment.update(self.monorail_environment(map_id))
        if self.pending is not None:
            self._check_preparation_deadline()
        launch_ms = int(time.time() * 1000)
        launch_monotonic = time.monotonic()
        process = self.ctx.start('local-character-zoning-' + str(map_id), ['/usr/bin/env', '--chdir=' + str(map_runtime),
            self.owner.args.wine, base.windows_path(map_runtime / 'MapServer.exe'), '-nogui', '-db', '127.0.0.1',
            '-nosharedmemory', '-nostats', '-udp', str(MAPS[map_id]['port']), '-tcp', '0', '-map_id', str(map_id),
            '-idleExitTimeout', '0', '-donotautogroup', *character.LOCAL_CLIENT_LINK_OPTIONS()], env=environment)
        self.maps[map_id] = {'process': process, 'progress_path': path, 'previous': None,
                             'launch_utc_ms': launch_ms, 'ready': False, 'scheduler': pacing,
                             'runtime': map_runtime, 'launch_monotonic': launch_monotonic}

    def _check_preparation_deadline(self):
        """Read fresh clocks; phase allowances cannot extend the connected cap."""
        now = time.monotonic()
        pending = self.pending
        require(pending is not None, 'Zoning preparation has no current request')
        phase = pending.get('preparation_phase', 'native_readiness')
        destination = 'Kings Row' if pending.get('to_map_id') == 5 else 'Atlas Park'
        message = (destination + ' Python preparation timed out before native startup; preserve the current map and export'
                   if phase == 'python_inputs' else
                   'Zoning native readiness timed out before departure; save on the current map and export')
        if pending.get('phase') == 'arrival':
            message = 'Zoning arrival timed out; preserve the profile and export this report'
        require(now < pending['deadline'], message)
        # Arrival has already passed the station departure gate. Its separate
        # existing bound still ends before the neutral/save reserves.
        if pending.get('phase') != 'arrival' and 'departure_deadline_monotonic' in pending:
            require(now < pending['departure_deadline_monotonic'],
                    'Preparation exhausted the reserved arrival and ordinary-save budget')
        return now

    def _preparation_observation(self):
        """Phase diagnostics leave the strict station request state unchanged."""
        pending = self.pending
        value = {'epoch': self.epoch, 'map_id': pending['to_map_id'],
            'observation_kind': 'phase_budget', 'observed_utc_ms': int(time.time() * 1000),
            'observed_monotonic_ms': int(time.monotonic() * 1000),
            'native_arrival_verified': False, 'physical_performance_gain_verified': False,
            **{key: pending[key] for key in PREPARATION_FIELDS if key in pending}}
        self.zoning_report.setdefault('preparation_phase_observations', []).append(value)
        self.ctx.event('character_zoning_preparation', session_id=self.owner.args.session_id,
            client_pid=self.creation_report['client_pid'], character_id=1, **value)

    def _scheduler_observation(self, phase, pacing):
        report = pacing.report
        if not isinstance(report, dict):
            return
        self.ctx.event('character_zoning_preparation', session_id=self.owner.args.session_id,
            client_pid=self.creation_report['client_pid'], character_id=1, epoch=self.epoch,
            map_id=report['map_id'], observation_kind='scheduler', scheduler_phase=phase,
            observed_utc_ms=int(time.time() * 1000), observed_monotonic_ms=int(time.monotonic()*1000),
            capability=report['capability'], changed_threads=report['changed_threads'],
            restored_threads=report['restored_threads'], exited_threads=report['exited_threads'],
            restore_complete=report['restore_complete'], exact_destination_only=True,
            physical_performance_gain_verified=False)

    def _restore_preparation(self, pacing):
        previously_restored = pacing.restored
        pacing.restore()
        if not previously_restored:
            self._scheduler_observation('restored', pacing)

    def _map_progress(self, map_id):
        owned = self.maps[map_id]
        require(owned['process'].process.poll() is None and not owned['process'].overflow,
                'Owned zoning MapServer exited or overflowed')
        scan_new_console(owned)
        try:
            owned['previous'] = character.progress.read_record(owned['progress_path'], owned.get('previous'))
        except (FileNotFoundError, character.progress.PublicationPending):
            return None
        if map_id == self.active_map_id:
            self.map_previous = owned['previous']
        if self.pending is not None and map_id == self.pending['to_map_id']:
            sample = owned['previous']
            stage = sample['stage'] if sample['tick_completed'] == 0 else 'COMPLETED_TICK'
            if stage != owned.get('last_observed_stage'):
                owned['last_observed_stage'] = stage
                rows = self.zoning_report['preparation_stage_observations']
                if len(rows) < 128:
                    observation = {'epoch': self.epoch, 'map_id': map_id,
                        'observed_utc_ms': int(time.time() * 1000),
                        'observed_monotonic_ms': int(time.monotonic() * 1000),
                        'stage': stage, 'windows_pid': sample['windows_pid'],
                        'tick_completed': sample['tick_completed'],
                        'native_stage_duration_measured': False}
                    rows.append(observation)
                    self.ctx.event('character_zoning_preparation', session_id=self.owner.args.session_id,
                        client_pid=self.creation_report['client_pid'], character_id=1, **observation)
        return owned['previous']

    def health(self):
        super().health()
        startup = getattr(self, 'initial_map_startup', None)
        if startup is not None and not startup['ready']:
            now = time.monotonic()
            require(now < startup['deadline'],
                    'Saved map native startup timed out; preserve data and export')
            if now >= startup['next_observation']:
                startup['next_observation'] = now + 5
                # No process launch or ctx.check recursion in health. This
                # small native record also distinguishes initialization from
                # an already-ready MapServer resident beside the client.
                self.observe_initial_map_progress(self._map_progress(startup['map_id']), now)
        # Read-only health checks never spawn a process or recurse through ctx.check.
        for map_id, owned in self.maps.items():
            if map_id == self.active_map_id:
                continue
            require(not owned['process'].overflow, 'Zoning MapServer console overflowed')
            if owned.get('ready'):
                require(owned['process'].process.poll() is None, 'Ready zoning destination exited; export the report')

    def map_crash_observation(self):
        scans = getattr(self, '_active_console_scans', None)
        if scans is None:
            scans = self._active_console_scans = {}
        owned = scans.setdefault(self.map_process, {'process': self.map_process})
        try:
            scan_new_console(owned)
        except base.DiagnosticError:
            # Decode/hash the complete console only upon the unchanged native
            # crash marker; retained rich failure evidence stays identical.
            crash = super().map_crash_observation()
            require(crash is not None, 'Owned zoning console history changed')
            return crash
        return None

    def current_native_events(self):
        if self.monorail_enabled():
            return self.map_native_events(self.active_map_id)
        return super().current_native_events() if self.active_map_id == 1 else None

    def native_ready_record(self):
        if self.monorail_enabled():
            value = monorail_events.latest_ready(self.current_native_events())
            return value if value is not None and value['utc_ms'] >= self.ready_floor_ms else None
        if self.active_map_id == 1:
            value = super().native_ready_record()
            if value is not None and value.get('utc_ms', 0) >= self.ready_floor_ms:
                return value
            return None
        return stock_ready(self.current_logs(), self.active_map_id, self.ready_floor_ms, int(time.time() * 1000))

    def native_positions(self):
        if self.monorail_enabled():
            return [row for row in monorail_events.positions_after_ready(self.current_native_events())
                    if row['utc_ms'] >= self.ready_floor_ms]
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
        target = self.pending['to_map_id'] if self.pending else (
            (5 if self.monorail_enabled() else 101) if self.active_map_id == 1 else 1)
        value = {'format': 1, 'session_id': self.owner.args.session_id,
            'client_pid': self.creation_report['client_pid'], 'character_id': 1,
            'epoch': self.epoch, 'status': status, 'current_map_id': self.active_map_id,
            'target_map_id': target, 'current_map_name': MAPS[self.active_map_id]['name'],
            'target_map_name': MAPS[target]['name'], 'generated_utc_ms': int(time.time() * 1000),
            'epoch_limit': MAX_EPOCHS, **fields}
        value.update(monorail_enabled=self.monorail_enabled(),
            travel_method='stock_monorail' if self.monorail_enabled() and self.active_map_id != 101
                and not getattr(self, 'monorail_requires_reopen', False) else 'mapmove',
            monorail_requires_reopen=getattr(self, 'monorail_requires_reopen', False))
        if self.pending is not None:
            for key in ('native_request_sequence', 'native_station_pid', 'native_station_request_verified',
                        *PREPARATION_FIELDS):
                if key in self.pending:
                    value[key] = self.pending[key]
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
        target = value['to_map_id']
        require(target != 5 or self.monorail_enabled(), 'Kings Row assets/native route are not qualified')
        resident = target in self.maps
        budgets = preparation_budgets(target, resident)
        now = time.monotonic()
        window = travel_window(getattr(getattr(self.owner, 'session_budget', None), 'deadline', None),
            now, now_ms, budgets['preparation_budget_seconds'],
            manual=getattr(self.owner, 'MANUAL_SESSION', False))
        initial_seconds = budgets['python_preparation_budget_seconds'] or budgets['native_ready_budget_seconds']
        # The native bridge starts its own clock when it emits the station
        # request, before the guest can observe it. Never grant that unseen
        # observation delay again as extra cold Kings preparation lifetime.
        request_age_ms = now_ms - value['requested_utc_ms']
        absolute_seconds = budgets['preparation_budget_seconds'] - (
            request_age_ms / 1000 if budgets['python_preparation_budget_seconds'] else 0)
        require(absolute_seconds > 0, 'Native station request exhausted its preparation budget')
        initial_seconds = min(initial_seconds, absolute_seconds)
        self.epoch += 1
        self.request_history[self.epoch] = dict(value)
        self.pending = dict(value, phase='baseline',
            deadline=now + initial_seconds, **window,
            next_query=0, transfer_requested=False, preparation_started_utc_ms=now_ms,
            preparation_started_monotonic=now,
            preparation_overall_deadline=now + absolute_seconds,
            preparation_deadline_utc_ms=now_ms + round(absolute_seconds * 1000),
            preparation_absolute_cap_basis=('validated_request_utc_ms' if budgets['python_preparation_budget_seconds']
                                            else 'accepted_preparation_clock'),
            preparation_request_age_ms=request_age_ms,
            departure_deadline_monotonic=(float('inf') if window.get('manual_session') else
                now + (window['departure_deadline_utc_ms'] - now_ms) / 1000),
            preparation_kind='resident_warm' if resident else 'cold',
            preparation_phase='python_inputs' if budgets['python_preparation_budget_seconds'] else 'native_readiness')
        self.pending.update(budgets)
        if budgets['python_preparation_budget_seconds']:
            self.pending.update(python_preparation_started_utc_ms=now_ms,
                python_preparation_deadline_utc_ms=now_ms + round(initial_seconds * 1000))
        else:
            self.pending.update(native_ready_started_utc_ms=now_ms, native_ready_started_monotonic=now,
                native_ready_deadline_utc_ms=now_ms + round(initial_seconds * 1000))
        native = getattr(self, 'station_accepting', None)
        if native is not None:
            self.pending.update(native_station_request=native, native_request_sequence=native['request'],
                native_station_pid=native['pid'], native_station_request_verified=True)
        self._emit('preparing', current_map_verified=True, destination_ready=False)
        self._preparation_observation()
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
        require(self.pending.get('manual_session') or now_ms < self.pending['departure_deadline_utc_ms']
                and value['sent_utc_ms'] < self.pending['departure_deadline_utc_ms'],
                'Zoning command exceeded the reserved arrival and ordinary-save budget')
        require(self.live_progress(self._map_progress(value['to_map_id'])), 'Prepared destination became stale')
        now = self._check_preparation_deadline()
        self.delivery_history[self.epoch] = dict(value)
        self.pending.update(phase='arrival', delivery=dict(value), transfer_requested=True,
                            deadline=now + TRANSFER_SECONDS, next_query=0)
        self._emit('transferring', current_map_verified=False, transfer_requested=True,
                   sent_utc_ms=value['sent_utc_ms'],
                   native_station_departure_verified=self.pending.get('native_station_request_verified') is True)

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
            minimum = pending['delivery']['sent_utc_ms'] - (0 if self.monorail_enabled() else 999)
            native = (monorail_events.latest_ready(self.map_native_events(target))
                      if self.monorail_enabled() else stock_ready(self.current_logs(), target, minimum, now_ms))
            if native is not None and native['utc_ms'] < minimum:
                native = None
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
                monorail_enabled=self.monorail_enabled(),
                recovery_requested=False, recovery_verified=False, ordinary_stuck_observed=False,
                on_atlas_safe_position=False, stable_ground_verified=False, committed_safe_position_verified=False)
            leg = {'epoch': self.epoch, 'from_map_id': origin, 'to_map_id': target,
                'delivery': pending['delivery'], 'native_ready': native,
                'character_status': sample, 'initial_character_status': pending.get('arrival_character', sample),
                'map_status': pending['arrival_map'], 'owned_progress': current,
                'elapsed_ms': now_ms - pending['delivery']['sent_utc_ms'],
                'native_timestamp_precision_ms': 1 if self.monorail_enabled() else 1000, 'same_client_pid': self.creation_report['client_pid'],
                'observed_transfer_flag_or_disconnected': pending.get('observed_transition', False),
                'arrival_native_verified': True, 'sql_transfer_commit_acknowledged': False}
            leg.update({key: pending[key] for key in PREPARATION_FIELDS
                if key in pending})
            leg.update(travel_method='stock_monorail' if pending.get('native_station_request_verified') else 'mapmove',
                native_transfer_observed_ms=leg['elapsed_ms'],
                total_to_native_arrival_ms=now_ms - pending.get('requested_utc_ms',
                    pending['delivery']['sent_utc_ms']),
                native_ready_after_send_lower_bound_ms=max(0, native['utc_ms'] - pending['delivery']['sent_utc_ms']),
                native_ready_after_send_upper_bound_ms=max(0, native['utc_ms'] + (0 if self.monorail_enabled() else 999) - pending['delivery']['sent_utc_ms']),
                observer_queries_included=True, fresh_android_display_included=False)
            self.zoning_report['transfers'].append(leg)
            self._emit('arrived', current_map_verified=True, destination_ready=True,
                arrival_native_verified=True, mapserver_pid=current['windows_pid'],
                elapsed_ms=leg['elapsed_ms'], exact_destination_endpoint_verified=True,
                character_identity_preserved=True, native_ready_utc_ms=native['utc_ms'],
                native_transfer_observed_ms=leg['native_transfer_observed_ms'],
                total_to_native_arrival_ms=leg['total_to_native_arrival_ms'])
            self.pending = None
            return
        if self.zoning_query is None and time.monotonic() >= pending['next_query']:
            if self.monorail_enabled():
                # The .27 report showed five-second translated status helpers
                # competing with loading while waiting for buffered stock logs.
                # Wait on the immediate current-process CLIENT_READY first;
                # then retain fresh endpoint and final exact character queries.
                native = monorail_events.latest_ready(self.map_native_events(target))
                if (native is None or native['utc_ms'] < pending['delivery']['sent_utc_ms']
                        or native['line_sha256'] in pending.get('prior_ready_hashes', [])):
                    return
                pending['arrival_native'] = native
                self._query_start(['-getstatus', '1', str(target)], 'arrival_map')
            else:
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
            if self.monorail_enabled():
                self._observe_station(now_ms)
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
            now = self._check_preparation_deadline()
            now_ms = int(time.time() * 1000)
            require(pending.get('transfer_requested') or pending.get('native_authorization_issued') or
                    not (self.owner.args.state / 'character-logout.json').exists(),
                    'Preparation cancelled for the requested ordinary save')
            result = self._query_poll()
            now = self._check_preparation_deadline()
            now_ms = int(time.time() * 1000)
            if pending['phase'] == 'arrival':
                self._observe_arrival(result, now_ms)
                return
            if result is not None and result[0] == 'baseline':
                baseline = parse_map_status(result[1], target, allow_missing=True)
                require(baseline.get('not_started') is True, 'Zoning destination already belongs to another process')
                pending['baseline'] = baseline
                self._spawn_map(target)
                now = self._check_preparation_deadline()
                now_ms = int(time.time() * 1000)
                pending['phase'] = 'map_ready'
            if pending['phase'] == 'map_ready':
                pacing = self.maps[target].get('scheduler')
                current = self._map_progress(target)
                if pacing is not None and current is not None:
                    pacing.sample()
                    if (isinstance(pacing.report, dict) and pacing.report['changed_threads']
                            and not pacing.report.get('weighted_checkpoint_emitted')):
                        pacing.report['weighted_checkpoint_emitted'] = True
                        self._scheduler_observation('restored' if pacing.restored else 'weighted', pacing)
                if result is not None and result[0] == 'prepared_map':
                    sample = parse_map_status(result[1], target)
                    if ready(sample, target) and self.live_progress(current):
                        if pacing is not None:
                            self._restore_preparation(pacing)
                        logs = self.current_logs()
                        ready_now_ms = int(time.time() * 1000)
                        prior = (monorail_events.latest_ready(self.map_native_events(target))
                                 if self.monorail_enabled() else stock_ready(logs, target, 0, ready_now_ms))
                        current = self._map_progress(target)
                        require(self.live_progress(current), 'Destination progress became stale before readiness')
                        ready_now = self._check_preparation_deadline()
                        ready_now_ms = int(time.time() * 1000)
                        self.maps[target]['ready'] = True
                        pending.update(phase='ready', ready_utc_ms=ready_now_ms, destination_status=sample,
                            prior_ready_hashes=[prior['line_sha256']] if prior else [],
                            preparation_ready_utc_ms=ready_now_ms,
                            preparation_elapsed_ms=ready_now_ms - pending['requested_utc_ms'],
                            native_ready_finished_utc_ms=ready_now_ms,
                            native_ready_elapsed_ms=round((ready_now - pending['native_ready_started_monotonic']) * 1000))
                        self.zoning_report.setdefault('preparations', []).append({key: pending[key]
                            for key in ('epoch', 'from_map_id', 'to_map_id', *PREPARATION_FIELDS)
                            if key in pending})
                        self._emit('ready', current_map_verified=True, destination_ready=True,
                                   mapserver_pid=current['windows_pid'])
                        if pending.get('native_station_request_verified'):
                            self._authorize_station(pending['native_station_request'])
                        return
                now = self._check_preparation_deadline()
                if self.zoning_query is None and self.live_progress(current) and now >= pending['next_query']:
                    pending['next_query'] = now + 10
                    self._query_start(['-getstatus', '1', str(target)], 'prepared_map')
        except (base.DiagnosticError, OSError, ValueError, KeyError, TypeError) as failure:
            if self.pending is not None:
                pacing = self.maps.get(self.pending['to_map_id'], {}).get('scheduler')
                if pacing is not None:
                    # Restoration failure deliberately escapes this recoverable
                    # preparation branch: never publish ready for weighted tasks.
                    self._restore_preparation(pacing)
            if isinstance(failure, base.Cancelled):
                # Abort is an operation-wide request, not a recoverable cold
                # destination timeout that permits continued gameplay/save.
                raise
            uncertain = unseen_delivery or bool(self.pending and (self.pending.get('transfer_requested')
                or self.pending.get('native_authorization_issued')))
            self.zoning_report['failure'] = {'message': str(failure)[:300], 'transfer_requested': uncertain}
            if self.pending is not None:
                failed_now = time.monotonic()
                self.zoning_report['failure'].update(
                    preparation_phase=self.pending.get('preparation_phase', 'native_readiness'),
                    elapsed_since_preparation_started_ms=max(0, round((failed_now
                        - self.pending.get('preparation_started_monotonic', failed_now)) * 1000)),
                    session_budget_extended=False)
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
        self.remember_reward_connection()
        self.tick_zoning()
        if self.pending is not None and (self.pending.get('transfer_requested')
                or self.pending.get('native_authorization_issued')):
            return None
        # The ordinary Atlas save path is retained, with only map-scoped native
        # witnesses and read-only finite-map position validation overridden.
        return super().character_evidence()

    def saved_metadata(self, snapshot):
        return dict(super().saved_metadata(snapshot), zoning_enabled=True,
            connected_on_supported_map=True, map_id=self.active_map_id,
            monorail_enabled=self.monorail_enabled(), zoning_epoch=self.epoch, ordinary_save_after_native_zoning=True)

    def collect(self, target):
        # Keep the retained archive member for older readers, but identify its
        # actual owning map rather than attributing a Kings console to Atlas.
        if self.map_process is not None:
            self.zoning_report['active_console'] = {'archive_member': 'character-atlas-console.txt',
                'retained_member_name': True, 'map_id': self.active_map_id,
                'map_name': MAPS[self.active_map_id]['name'], 'world': MAPS[self.active_map_id]['world'],
                'port': MAPS[self.active_map_id]['port'], 'session_id': self.owner.args.session_id,
                'launch_utc_ms': self.map_launch_utc_ms}
        super().collect(target)
        self.zoning_report['console_scan_work'] = {
            'destination_bytes': sum(row.get('console_bytes_scanned', 0) for row in self.maps.values()),
            'active_bytes': sum(row.get('console_bytes_scanned', 0)
                for row in getattr(self, '_active_console_scans', {}).values()),
            'retained_overlap_bytes_per_sample': 64, 'full_decode_only_on_crash_or_export': True}
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
        and (proof['map_id'] != 5 or proof.get('monorail_enabled') is True)
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
