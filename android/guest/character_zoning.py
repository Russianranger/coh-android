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
import secrets
import socket
import stat
import threading
import time
from types import MappingProxyType

import local_character_server as character
import character_session_budget as session_budget
import character_zoning_scheduler as scheduler
import native_monorail_events as monorail_events
import native_monorail_contract as monorail_contract
import zone_travel
import zone_index

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
# Optional background start of the next zone (King's Row) beside Atlas Park.
PRESTART_ENV = 'COH_PRESTART_NEXT_ZONE'
PRESTART_MAP_ID = 5
PRESTART_DELAY_SECONDS = 20
PRESTART_OBSERVE_SECONDS = 5
PRESTART_JOIN_SECONDS = 120
PRESTART_THREAD_NICE = 10
# King's Row preparation peaked at 1772 MiB RSS on Thor (.44); keep headroom.
PRESTART_MIN_AVAILABLE_MIB = 3072
# Idle priority for a resident MapServer the player is not on (launch option).
IDLE_ENV = 'COH_IDLE_RESIDENT_MAPS'
PRIORITY_SAMPLES = 12
PRIORITY_INTERVAL_SECONDS = 120
# The game's own travel: a third zone asks the DbServer where the hero is (one
# -getstatus process); keep the rest of the 160-query budget for the save proof.
STOCK_PROBE_QUERY_LIMIT = 140
# The game's own travel (ARM64 client): no zone server runs before Enter Game.
# The zone the character is in, or a new character's starting zone, is started
# when the DbServer asks for it (dynamic_initial_requested); no other zone is
# admitted before the character first enters the world (owner, 2026-11-07:
# "Under no circumstances should characters be transported to Atlas Park
# unless they exist in that zone already").
DYNAMIC_INITIAL_POLICY = 'character_zone_started_by_dbserver_request_at_enter_game_v2'
# Display names for the static zones the shared zone tree serves (zone_index).
ZONE_DISPLAY_NAMES = {
    1: 'Atlas Park', 3: 'Cimerora', 4: 'Midnighter Club', 5: "King's Row", 6: 'Steel Canyon',
    7: 'Skyway City', 8: 'Talos Island', 9: 'Independence Port', 10: "Founders' Falls",
    11: 'Brickstown', 12: 'Perez Park', 13: 'Boomtown', 14: 'Dark Astoria (old)', 15: "Crey's Folly",
    16: 'Ouroboros', 17: 'Ouroboros', 18: 'Abandoned Sewer Network', 19: 'Faultline (old)',
    20: 'Terra Volta', 21: 'Eden', 22: 'The Hive', 23: 'Sewer Network', 24: 'Outbreak',
    29: 'Galaxy City', 36: 'Nova Praetoria', 37: 'Imperial City', 38: 'Neutropolis',
    39: 'Underground Nova', 40: 'Precinct Five', 41: 'Destroyed Galaxy City', 42: 'Underground Imperial',
    43: 'Dark Astoria', 49: 'First Ward', 51: 'Underground Neutropolis', 52: 'Night Ward',
    60: 'Rikti Crash Site', 61: 'Peregrine Island', 62: 'The Hollows', 65: 'Cascade Archipelago',
    66: 'The Chantry', 67: 'The Storm Palace', 68: 'Paragon Dance Party', 69: 'Striga Isle',
    70: 'Breakout', 71: 'Mercy Island', 72: 'Port Oakes', 73: 'Cap au Diable', 74: 'Sharkhead Isle',
    75: 'Nerva Archipelago', 76: 'St. Martial', 77: 'Grandville', 82: 'Croatoa', 83: 'Pocket D',
    84: 'Faultline', 85: 'Rikti War Zone', 86: 'The Abyss', 87: 'Monster Island', 626: 'Echo: Galaxy City'}
# ARM64 client (patch 0121): the frame cap while the player waits for a
# destination to be prepared. Input is held during that wait, and the 0.13.50
# Thor test drew Atlas at 30-60 FPS through a 9-minute King's Row preparation.
STATION_FPS_CAP = 10
STATION_FPS_CAP_PHASES = ('baseline', 'map_ready')
# Read-only tick timing of the occupied MapServer (shipping binaries report no
# tick durations). NPCs and cars are simulated and sent only every 15th tick
# (2 per second) and drawn 0.6 s in the past; a long tick there, or any tick
# over 2/30 s (lost game time), makes them stop and jump. 0.13.50 King's Row.
TICK_PROBE_INTERVAL_SECONDS = 30
TICK_PROBE_SECONDS = 4.0
TICK_PROBE_PERIOD_SECONDS = 0.02
TICK_PROBE_LIMIT = 120
TICK_PROBE_JOIN_SECONDS = 8


def tick_gap_probe(path, *, seconds=TICK_PROBE_SECONDS, period=TICK_PROBE_PERIOD_SECONDS,
                   clock=time.monotonic, sleep=time.sleep, read=None):
    """Sample one MapServer progress record at ~50 Hz and summarise completed-tick gaps.

    A gap is the time between two observed changes of tick_completed. With
    33 ms ticks and 20 ms sampling, normal gaps are 20-40 ms; a gap over
    67 ms is a tick that overran 2/30 s. Bounded, read-only, never a proof.
    """
    read = read or character.progress.read_record
    previous = last_tick = last_change = None
    gaps, reads, errors = [], 0, 0
    started = clock()
    end = started + seconds
    while clock() < end:
        try:
            previous = read(path, previous)
            reads += 1
        except (character.progress.PublicationPending, OSError):
            errors += 1
            sleep(period)
            continue
        now, tick = clock(), previous.get('tick_completed')
        if type(tick) is int:
            if last_tick is None or tick < last_tick:
                last_tick, last_change = tick, now
            elif tick != last_tick:
                gaps.append(((now - last_change) * 1000, tick - last_tick))
                last_tick, last_change = tick, now
        sleep(period)
    durations = sorted(gap for gap, _count in gaps)
    def over(limit):
        return sum(1 for gap in durations if gap > limit)
    return {'reads': reads, 'read_errors': errors, 'window_seconds': round(clock() - started, 3),
            'ticks': sum(count for _gap, count in gaps), 'gaps': len(durations),
            'max_gap_ms': round(durations[-1], 1) if durations else None,
            'p90_gap_ms': round(durations[int(len(durations) * .9)], 1) if durations else None,
            'gaps_over_67ms': over(1000 * 2 / 30), 'gaps_over_150ms': over(150), 'gaps_over_300ms': over(300)}


def available_memory_mib(path=Path('/proc/meminfo')):
    """MemAvailable in MiB, or None when the kernel does not report it."""
    try:
        for line in path.read_text().splitlines()[:64]:
            if line.startswith('MemAvailable:'):
                return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        return None
    return None
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


def prestarted_loading_budgets(map_id):
    """A prestarted destination already finished Python preparation; only native readiness remains."""
    budgets = preparation_budgets(map_id, False)
    native = budgets['native_ready_budget_seconds']
    return dict(budgets, python_preparation_budget_seconds=0, preparation_budget_seconds=native,
                preparation_budget_policy='prestarted_native_ready_v1')


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


def zone_name(map_id):
    if map_id in MAPS:
        return MAPS[map_id]['name']
    return ZONE_DISPLAY_NAMES.get(map_id, 'Zone %s' % map_id)


def register_zone(map_id):
    """A static zone served from the shared zone tree, known for this session.

    Atlas (1, 101) and King's Row (5) keep their fixed entries; every other
    static map in zone_index gets instance 1 and a port at its first launch.
    """
    if map_id in MAPS:
        return MAPS[map_id]
    require(type(map_id) is int and map_id in zone_index.ZONES, 'Unknown static zone')
    key, world, _ = zone_index.ZONES[map_id]
    MAPS[map_id] = {'name': ZONE_DISPLAY_NAMES.get(map_id, key), 'port': None, 'instance': 1, 'world': world,
                    'shared_zone_tree': True}
    return MAPS[map_id]


def zone_world(map_id):
    """The world a static map shows (Atlas Park's two instances share City_01_01)."""
    if type(map_id) is not int:
        return None
    if map_id in MAPS:
        return MAPS[map_id]['world'].casefold()
    if map_id in zone_index.ZONES:
        return zone_index.ZONES[map_id][1].casefold()
    return None


def same_zone(first, second):
    """One zone: the same map, or another instance of its world (Atlas Park 1 and 101)."""
    world = zone_world(first)
    return (type(first) is int and type(second) is int
            and (first == second or world is not None and world == zone_world(second)))


def free_zone_port(used):
    for port in range(zone_travel.FIRST_FREE_PORT, zone_travel.LAST_PORT + 1):
        if port not in used:
            return port
    raise base.DiagnosticError('No free zone server port')


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
    pattern = re.compile('^' + character.entity_name_prefix() + r' -?\d+ Connection:ResumeCharacter from '
                         r'127\.0\.0\.1:([1-9][0-9]{0,4}) AuthName "COHLOCAL"(?: [^\r\n]*)?$')
    result = []
    for message, record in entity_records(logs, map_id, minimum_ms=minimum_ms, now_ms=now_ms):
        match = pattern.fullmatch(message)
        if match is not None and int(match[1]) <= 65535:
            result.append(dict(record, account=character.ACCOUNT, name=character.CHARACTER,
                port=int(match[1]), loaded_world_assets=True,
                source='current_target_stock_CLIENT_READY_resumeCharacter_success'))
    return max(result, key=lambda r: (r['utc_ms'], r['line_ordinal'])) if result else None


def legacy_ready(logs, minimum_ms, now_ms):
    """Atlas CLIENT_READY from either stock log route of a legacy MapServer, newest first.

    character.ready_record returns the first match without a time; a zoning
    session needs the one after the current launch (second-resolution log time).
    """
    pattern = re.compile('^' + character.entity_name_prefix() + r' -?\d+ Connection:ResumeCharacter from '
                         r'127\.0\.0\.1:([1-9][0-9]{0,4}) AuthName "COHLOCAL"(?: [^\r\n]*)?$')
    result = []
    for ordinal, (message, record) in enumerate(character.entity_records(logs, map_id=1)):
        match = pattern.fullmatch(message)
        if match is None or int(match[1]) > 65535:
            continue
        utc_ms = int(time.mktime(time.strptime(record['log_timestamp'], '%y%m%d %H:%M:%S')) * 1000)
        if utc_ms < minimum_ms or utc_ms > now_ms + 999:
            continue
        result.append(dict(record, utc_ms=utc_ms, line_ordinal=ordinal, map_id=1, port=int(match[1]),
                           account=character.ACCOUNT, name=character.CHARACTER, loaded_world_assets=True,
                           source='current_owned_mapserver_CLIENT_READY_resumeCharacter_success'))
    return max(result, key=lambda r: (r['utc_ms'], r['line_ordinal'])) if result else None


def stock_transfers_begun(logs, map_id, minimum_ms, now_ms):
    """dbmapxfer.c "Step 1: Ent <name> moving to map N" on map_id's own route."""
    pattern = re.compile('^' + character.entity_name_prefix() + r' -?\d+ Step 1: Ent ' + re.escape(character.CHARACTER)
                         + r' moving to map ([1-9][0-9]{0,4})[, ][^\r\n]*$')
    rows = []
    for message, record in entity_records(logs, map_id, minimum_ms=minimum_ms, now_ms=now_ms):
        match = pattern.fullmatch(message)
        if match is not None:
            rows.append({'utc_ms': record['utc_ms'], 'from_map_id': map_id, 'to_map_id': int(match[1]),
                         'line_sha256': record['line_sha256']})
    return rows


def stock_positions(logs, map_id, minimum_ms, now_ms):
    pattern = re.compile('^' + character.entity_name_prefix() + r' -?\d+ PeriodicInfo pos=<('
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
        if re.fullmatch('^' + character.entity_name_prefix() + r' -?\d+ \[Disconnect:Logout timer expired\] [^\r\n]+$', message)]
    return max(rows, key=lambda r: (r['utc_ms'], r['line_ordinal'])) if rows else None


def terminal_position(logs, map_id, delivery, minimum_ms, now_ms):
    timer = None
    matches = []
    pattern = re.compile('^' + character.entity_name_prefix() + r' -?\d+ Logout location : map (\d+) '
                        r'\((' + NUMBER + ') (' + NUMBER + ') (' + NUMBER + r')\) [^\r\n]+$')
    for message, record in entity_records(logs, map_id, minimum_ms=minimum_ms, now_ms=now_ms):
        if re.fullmatch('^' + character.entity_name_prefix() + r' -?\d+ \[Disconnect:Logout timer expired\] [^\r\n]+$', message):
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


class MapLaunchHistory:
    """Bounded observations of launches; never ownership or shutdown authority.

    Native progress and the existing process owner remain authoritative. A
    resident map keeps its generation when the player returns; only a different
    owned launcher reference may produce another immutable launch descriptor.
    """
    LIMIT = MAX_EPOCHS + 1
    CONSOLE_BYTES = 256 * 1024

    def __init__(self, session):
        self.session, self._launches = session, ()
        self.errors, self.omitted = {}, 0

    def unavailable(self, reason):
        self.errors[reason] = min(self.errors.get(reason, 0) + 1, 65535)

    def observe(self, map_id, owned, epoch):
        try:
            process, path, launch = owned['process'], owned['progress_path'], owned['launch_utc_ms']
            child = getattr(process, 'process', None)
            capture = getattr(process, 'output', None)
            require(supported(map_id) and isinstance(path, Path) and process is not None
                    and isinstance(capture, (bytes, bytearray))
                    and type(launch) is int and launch > 0
                    and type(epoch) is int and 0 <= epoch <= MAX_EPOCHS,
                    'Incomplete launch observation')
            for record, previous, previous_path, previous_child, previous_capture in self._launches:
                if previous is process:
                    require(record['map_id'] == map_id and previous_path == path
                            and previous_child is child and record['launch_utc_ms'] == launch,
                            'Launch observation changed')
                    require(previous_capture is capture, 'Launch capture changed')
                    return record
            if len(self._launches) >= self.LIMIT:
                self.omitted = min(self.omitted + 1, 65535)
                return None
            number = len(self._launches) + 1
            pid = getattr(child, 'pid', None)
            record = MappingProxyType({'generation': number, 'map_id': map_id,
                'observed_at_epoch': epoch, 'launch_utc_ms': launch,
                'launcher_pid': pid if type(pid) is int and pid > 0 else None,
                'progress_member': path.name,
                'console_member': 'character-zoning-generation-' + str(number)
                    + '-map-' + str(map_id) + '-console-tail.txt'})
            self._launches += ((record, process, path, child, capture),)
            return record
        except Exception:
            # Optional evidence must not alter the launch/readiness/save path.
            self.unavailable('invalid_or_changed_launch_observation')
            return None

    def collect(self, target, maps, active_process, secrets):
        report = {'format': 1, 'session_id': self.session, 'retirement_enabled': False,
            'is_success_proof': False, 'identity_scope': 'owned_launcher_reference_only',
            'native_process_identity_verified': False, 'generation_limit': self.LIMIT,
            'console_tail_bytes_per_generation': self.CONSOLE_BYTES,
            'omitted_launch_observations': self.omitted, 'observation_errors': dict(self.errors),
            'generations': []}
        for record, process, _, child, capture in self._launches:
            resident = maps.get(record['map_id'], {})
            row = {'launch': dict(record), 'current_resident': resident.get('process') is process,
                'active_process_reference': active_process is process, 'console': {'available': False}}
            report['generations'].append(row)
            try:
                output = process.output
                require(getattr(process, 'process', None) is child and output is capture,
                        'Launch process or capture was replaced')
                # A multiline secret could straddle a complete-line tail edge.
                # The legacy full console remains available with its ordinary
                # redaction; omit this optional tail rather than export a part.
                require(not any('\n' in secret or '\r' in secret for secret in secrets if secret),
                        'Multiline secrets require full-console redaction')
                size = len(output)
                start = max(0, size - self.CONSOLE_BYTES)
                # Copy at most one small tail, not process.text()'s full log.
                chunk = bytes(output[start:size])
                first = chunk.find(b'\n') + 1 if start else 0
                if start and not first:
                    first = len(chunk)
                end = chunk.rfind(b'\n') + 1
                tail = chunk[first:max(first, end)]
                text = base.redact(tail.decode('utf-8', 'replace'), secrets)
                require(len(text.encode()) <= self.CONSOLE_BYTES, 'Redacted console tail exceeds bound')
                path = target / record['console_member']
                require(not path.exists() and not path.is_symlink(), 'Existing generation export refused')
                base.private_write(path, text)
                row['console'] = {'available': True, 'capture_bytes': size,
                    'exported_bytes': len(text.encode()), 'retained_source_bytes': len(tail),
                    'omitted_source_bytes': size - len(tail), 'complete_lines_only': True,
                    'overflow': getattr(process, 'overflow', False) is True,
                    'complete': start == 0 and first == 0 and end == len(chunk)
                        and getattr(process, 'overflow', False) is False}
            except Exception as error:
                row['console'] = {'available': False, 'reason': type(error).__name__}
        report['available'] = bool(report['generations'])
        report['complete'] = (report['available'] and not self.errors and not self.omitted
            and all(row['console'].get('complete') is True for row in report['generations']))
        return report


class LocalCharacterZoningServer(character.LocalCharacterReopenServer):
    """At most two owned static map processes, started only when requested."""
    # Atlas, its second instance and King's Row are started by this flow.
    EXTERNAL_SESSION_MAPS = frozenset(MAPS)
    def __init__(self, owner):
        super().__init__(owner)
        self.active_map_id = 1
        self.maps = {}
        self.map_launch_history = MapLaunchHistory(owner.args.session_id)
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
        self.prestart = None
        self.zoning_report['background_prestart'] = {'format': 1,
            'requested': os.environ.get(PRESTART_ENV) == '1', 'map_id': PRESTART_MAP_ID,
            'status': 'not_started', 'policy': 'prepare_then_start_next_zone_beside_current_v1',
            'preparation_thread_nice': PRESTART_THREAD_NICE, 'mapserver_priority_lowered': False}
        self.idle_capability = None
        self.zoning_report['idle_resident_maps'] = {'format': 1,
            'requested': os.environ.get(IDLE_ENV) == '1',
            'policy': 'resident_map_not_occupied_plus_10_nice_restored_before_return_v1',
            'nice_increment': scheduler.IDLE_NICE_INCREMENT, 'periods': [],
            'physical_performance_gain_verified': False}
        self.station_fps_cap = {'format': 1, 'policy': 'client_cap_while_trip_is_prepared_v1',
            'cap': STATION_FPS_CAP, 'client_supported': False, 'applied': 0, 'removed': 0, 'error': None}
        self.zoning_report['station_fps_cap'] = self.station_fps_cap
        self.tick_probe = None
        self.active_since_monotonic = None
        self.zoning_report['tick_probe'] = {'format': 1,
            'policy': 'read_only_occupied_map_completed_tick_gaps_v1',
            'interval_seconds': TICK_PROBE_INTERVAL_SECONDS, 'window_seconds': TICK_PROBE_SECONDS,
            'sample_period_seconds': TICK_PROBE_PERIOD_SECONDS, 'limit': TICK_PROBE_LIMIT,
            'samples': [], 'skipped_busy': 0, 'error': None, 'is_success_proof': False}
        self.stock = {'format': 1, 'requested': zone_travel.requested(), 'enabled': False,
            'policy': 'stock_doors_tunnels_monorail_two_zone_servers_v1',
            'capacity': zone_travel.MAX_ZONE_SERVERS, 'start_budget_seconds': zone_travel.START_SECONDS,
            'starts': [], 'evictions': [], 'arrivals': 0, 'transfer_wait_observed': 0, 'decisions': [],
            'transfers_begun': [], 'arrival_source': None}
        self.stock_starts = {}
        self.stock_log_next = 0
        self.stock_last_arrival_ms = None
        self.zoning_report['stock_travel'] = self.stock
        # The zone the character first enters, started at Enter Game (begin_initial_zone).
        self.initial_zone = None
        self.priority_next = 0
        self.zoning_report['wine_priorities'] = {'format': 1,
            'policy': 'read_only_thread_nice_by_wine_program_v1', 'samples': [],
            'sample_limit': PRIORITY_SAMPLES, 'interval_seconds': PRIORITY_INTERVAL_SECONDS,
            'priorities_changed': False}

    def start_tick_probe(self):
        """One daemon thread; it only reads the occupied map's progress file."""
        report = (getattr(self, 'zoning_report', None) or {}).get('tick_probe')
        if report is None or getattr(self, 'tick_probe', None) is not None:
            return
        if getattr(self, 'active_since_monotonic', None) is None:
            self.active_since_monotonic = time.monotonic()
        stop = threading.Event()

        def run():
            try:
                while not stop.wait(TICK_PROBE_INTERVAL_SECONDS) and len(report['samples']) < TICK_PROBE_LIMIT:
                    map_id, path = self.active_map_id, getattr(self, 'map_progress_path', None)
                    since = self.active_since_monotonic
                    if self.pending is not None or path is None:
                        report['skipped_busy'] += 1
                        continue
                    started_utc_ms = int(time.time() * 1000)
                    sample = tick_gap_probe(path)
                    if (self.pending is not None or self.active_map_id != map_id
                            or self.active_since_monotonic != since):
                        report['skipped_busy'] += 1
                        continue
                    sample.update(map_id=map_id, started_utc_ms=started_utc_ms,
                                  seconds_since_map_active=round(time.monotonic() - since, 1) if since else None)
                    report['samples'].append(sample)
            except Exception as error:   # observation only; never affects zoning
                report['error'] = type(error).__name__ + ': ' + str(error)[:160]

        thread = threading.Thread(target=run, name='coh-tick-probe', daemon=True)
        self.tick_probe = {'stop': stop, 'thread': thread}
        thread.start()

    def stop_tick_probe(self, timeout=TICK_PROBE_JOIN_SECONDS):
        probe = getattr(self, 'tick_probe', None)
        if probe is None:
            return True
        probe['stop'].set()
        probe['thread'].join(timeout)
        alive = probe['thread'].is_alive()
        self.zoning_report['tick_probe']['thread_joined'] = not alive
        return not alive

    def tick_priorities(self, now):
        """A few read-only samples in play: does Wine run the client at a higher nice?"""
        report = (getattr(self, 'zoning_report', None) or {}).get('wine_priorities')
        if report is None or len(report['samples']) >= PRIORITY_SAMPLES or now < self.priority_next:
            return
        self.priority_next = now + PRIORITY_INTERVAL_SECONDS
        try:
            sample = scheduler.wine_priority_snapshot()
        except (OSError, base.DiagnosticError) as error:
            sample = {'error_type': type(error).__name__, 'error': str(error)[:200]}
        sample.update(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                      active_map_id=self.active_map_id, resident_maps=sorted(self.maps))
        report['samples'].append(sample)

    # Background start of the next zone ------------------------------------
    def prestart_eligible(self):
        return (self.pending is None and self.active_map_id == 1 and self.monorail_enabled()
                and PRESTART_MAP_ID not in self.maps and len(self.maps) == 1
                and getattr(self, 'kings_row_prepared', None) is None)

    def start_background_prestart(self, now):
        """Run the King's Row Python preparation on a low-priority thread.

        The thread's ctx.check also honours a private stop flag, and its
        'stage' progress events are dropped so the foreground stage and the
        Android overlay stay on the live session. Other events are serialized.
        """
        report = self.zoning_report['background_prestart']
        state = {'phase': 'preparing', 'started_monotonic': now, 'cancel': False, 'error': None,
                 'thread': None}
        original_check, original_event, lock = self.ctx.check, self.ctx.event, threading.Lock()

        def check():
            original_check()
            if threading.current_thread() is state['thread'] and state['cancel']:
                raise base.Cancelled("Background King's Row preparation stopped")

        def event(kind, **fields):
            if threading.current_thread() is state['thread'] and kind == 'stage':
                return
            with lock:
                original_event(kind, **fields)

        def run():
            try:
                try:
                    os.setpriority(os.PRIO_PROCESS, threading.get_native_id(), PRESTART_THREAD_NICE)
                    report['preparation_thread_niced'] = True
                except (AttributeError, OSError):
                    report['preparation_thread_niced'] = False
                self.prepare_kings_row_runtime()
            except BaseException as error:   # reported by the supervisor thread
                state['error'] = error
            finally:
                state['finished_monotonic'] = time.monotonic()

        self.ctx.check, self.ctx.event = check, event
        state['thread'] = threading.Thread(target=run, name='kings-row-prestart', daemon=True)
        self.prestart = state
        self.prestart_timing = self.begin_startup_timing('background_prestart', map_id=PRESTART_MAP_ID,
                                                         now=now, utc_ms=int(time.time() * 1000))
        report.update(status='preparing', started_utc_ms=int(time.time() * 1000))
        state['thread'].start()

    def wait_background_prestart(self):
        """A zoning request during background preparation waits for, then reuses, its result."""
        state = getattr(self, 'prestart', None)
        if state is None or state['thread'] is None or state['phase'] != 'preparing':
            return
        while state['thread'].is_alive():
            state['thread'].join(.25)
            self.ctx.check()
        self.zoning_report['background_prestart']['joined_by_zoning_request'] = True
        if state['error'] is not None:
            raise state['error']

    def discard_prestarted_map(self, failure):
        owned = self.maps.pop(PRESTART_MAP_ID, None)
        report = self.zoning_report['background_prestart']
        report.update(status='failed', failure_phase='native_loading',
                      failure=str(failure)[:300], failure_type=type(failure).__name__)
        if owned is None:
            return
        if owned['process'].process.poll() is None:
            owned['process'].process.terminate()
        path = owned['progress_path']
        if path.exists() or path.is_symlink():
            # A later cold zoning spawn requires a fresh progress file.
            path.rename(path.with_name(path.name + '.prestart-failed'))

    # Idle priority for resident maps --------------------------------------
    def idle_token(self):
        """Only a requested idle policy adds a launch token; the default launch is unchanged."""
        report = getattr(self, 'zoning_report', {}).get('idle_resident_maps')
        if not isinstance(report, dict) or report.get('requested') is not True:
            return None
        token = secrets.token_hex(32)
        self.ctx.secrets.append(token)
        return token

    def idle_lower(self, map_id, reason):
        """Weight a ready resident map the player is not on; never fails zoning."""
        report = self.zoning_report.get('idle_resident_maps')
        owned = self.maps.get(map_id)
        if (not isinstance(report, dict) or report.get('requested') is not True or owned is None or map_id == self.active_map_id
                or owned.get('idle') is not None or not owned.get('idle_token')
                or len(report['periods']) >= 16):
            return
        period = {'map_id': map_id, 'reason': reason, 'lowered_utc_ms': int(time.time() * 1000)}
        report['periods'].append(period)
        try:
            idle = scheduler.PreparationScheduler(self.owner, map_id, probe=self.idle_capability,
                token=owned['idle_token'], environment_name=scheduler.IDLE_ENVIRONMENT,
                increment=scheduler.IDLE_NICE_INCREMENT, policy='idle_resident_plus_10_nice',
                sample_limit=scheduler.IDLE_SAMPLE_LIMIT)
            self.idle_capability = idle.capability
            period['scheduler'] = idle.report
            owned['idle'] = idle
            idle.sample()
            period['changed_threads'] = idle.report['changed_threads']
        except (base.DiagnosticError, OSError, ValueError) as failure:
            period.update(status='lower_failed', failure=str(failure)[:300], failure_type=type(failure).__name__)

    def idle_restore(self, map_id, reason):
        """Restore before the player returns (or cleanup); a failure is reported, not hidden."""
        owned = self.maps.get(map_id)
        idle = None if owned is None else owned.get('idle')
        if idle is None:
            return True
        owned['idle'] = None
        period = next((row for row in reversed(self.zoning_report.get('idle_resident_maps', {}).get('periods', []))
                       if row.get('map_id') == map_id and 'restored_utc_ms' not in row), {})
        try:
            idle.restore()
            period.update(status='restored', restored_utc_ms=int(time.time() * 1000), restore_reason=reason,
                          restored_threads=idle.report['restored_threads'])
            return True
        except (base.DiagnosticError, OSError, ValueError) as failure:
            period.update(status='restore_failed', restored_utc_ms=int(time.time() * 1000), restore_reason=reason,
                          failure=str(failure)[:300], failure_type=type(failure).__name__)
            return False

    def tick_idle(self):
        for map_id, owned in list(self.maps.items()):
            idle = owned.get('idle')
            if idle is None:
                continue
            if map_id == self.active_map_id:
                self.idle_restore(map_id, 'became_active')
                continue
            try:
                idle.sample()   # bounded: every 5 s, discovers new threads every 15 s
            except (base.DiagnosticError, OSError, ValueError):
                self.idle_restore(map_id, 'observation_error')

    def restore_idle_maps(self, reason):
        return all([self.idle_restore(map_id, reason) for map_id in list(self.maps)])

    def tick_prestart(self, now):
        report = self.zoning_report.get('background_prestart')
        if not isinstance(report, dict) or report.get('requested') is not True:
            return
        state = getattr(self, 'prestart', None)
        try:
            if state is None:
                if report['status'] != 'not_started' or not self.prestart_eligible():
                    return
                eligible = report.setdefault('eligible_monotonic', now + PRESTART_DELAY_SECONDS)
                if now < eligible:
                    return
                available = available_memory_mib()
                report.update(available_memory_mib_at_start=available,
                              minimum_available_memory_mib=PRESTART_MIN_AVAILABLE_MIB)
                if available is None or available < PRESTART_MIN_AVAILABLE_MIB:
                    report['status'] = 'skipped_low_memory'
                    return
                self.start_background_prestart(now)
                return
            if state['phase'] == 'preparing':
                if state['thread'].is_alive():
                    return
                state['phase'] = 'prepared'
                report['preparation_seconds'] = round(state.get('finished_monotonic', now) - state['started_monotonic'], 3)
                if state['error'] is not None:
                    if isinstance(state['error'], base.Cancelled) and self.ctx.cancelled():
                        raise state['error']
                    state['phase'] = 'done'
                    report.update(status='failed', failure_phase='preparing', failure=str(state['error'])[:300],
                                  failure_type=type(state['error']).__name__)
                    return
            if state['phase'] == 'prepared':
                if self.pending is not None or PRESTART_MAP_ID in self.maps or self.active_map_id != 1:
                    state['phase'] = 'done'
                    report['status'] = 'prepared_then_used_by_zoning'
                    return
                self._spawn_map(PRESTART_MAP_ID)   # reuses the prepared runtime
                self.maps[PRESTART_MAP_ID]['prestarted'] = True
                self.mark_startup_timing(self.prestart_timing, 'map_spawn_requested')
                state.update(phase='loading', next_observation=now + PRESTART_OBSERVE_SECONDS)
                report.update(status='native_loading', native_spawn_seconds=round(now - state['started_monotonic'], 3))
                return
            if state['phase'] == 'loading':
                owned = self.maps.get(PRESTART_MAP_ID)
                if owned is None or self.pending is not None:
                    state['phase'] = 'done'
                    report['status'] = 'loading_handed_to_zoning'
                    return
                if now < state['next_observation']:
                    return
                state['next_observation'] = now + PRESTART_OBSERVE_SECONDS
                try:
                    current = self._map_progress(PRESTART_MAP_ID)
                except (base.DiagnosticError, OSError, ValueError, KeyError, TypeError) as failure:
                    state['phase'] = 'done'
                    self.discard_prestarted_map(failure)
                    return
                if self.live_progress(current):
                    owned['native_ticking'] = True
                    self.mark_startup_timing(self.prestart_timing, 'first_completed_tick_observed')
                    state['phase'] = 'done'
                    report.update(status='native_ticking',
                                  native_ticking_seconds=round(now - state['started_monotonic'], 3))
                    self.idle_lower(PRESTART_MAP_ID, 'prestarted_ready')
        except base.Cancelled:
            raise
        except (base.DiagnosticError, OSError, ValueError, KeyError, TypeError) as failure:
            # Background work never disables foreground zoning.
            if state is not None:
                state['phase'] = 'done'
            report.update(status='failed', failure=str(failure)[:300], failure_type=type(failure).__name__)

    def stop_background_prestart(self, timeout=PRESTART_JOIN_SECONDS):
        """Cleanup stops and joins the preparation thread before any cache return."""
        state = getattr(self, 'prestart', None)
        if state is None or state['thread'] is None:
            return True
        state['cancel'] = True
        state['thread'].join(timeout)
        alive = state['thread'].is_alive()
        self.zoning_report['background_prestart'].update(stopped_for_cleanup=True, thread_joined=not alive)
        if alive and hasattr(self, 'kings_row_data_cache'):
            # Never return a data tree another thread may still be writing.
            del self.kings_row_data_cache
        return not alive

    def cleanup_config(self):
        # The preparation thread starts no processes; join it before the
        # inherited cache return so no tree is returned while being written.
        self.stop_background_prestart()
        self.stop_tick_probe()
        path = getattr(self.owner, 'armport_fps_cap_file', None)
        if getattr(self, 'station_fps_cap', None) is not None and path is not None:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        self.restore_idle_maps('cleanup')
        super().cleanup_config()

    def map_startup_timing(self, map_id):
        row = getattr(self, 'prestart_timing', None)
        if row is not None and self.pending is None and map_id == PRESTART_MAP_ID:
            return row
        # A trip's start has its own row; the first zone's start keeps the initial one.
        row = getattr(self, 'stock_spawn_timing', None)
        if row is not None and self.pending is None:
            row['map_id'] = map_id
            return row
        return super().map_startup_timing(map_id)

    def monorail_enabled(self):
        """The station queue; off when the game's own zone travel is active."""
        return getattr(self, 'monorail_qualified', False) is True and not self.stock_travel_active()

    def session_map_options(self):
        """The game's own zone travel: the loading screen comes at once (owner, 2026-11-05).

        The stock MapServer defaults to a two-stage transfer (dbmapxfer.c,
        s_UseTwoStageMapXfer): the hero stays in the world, targetable, until the
        destination has started, which takes minutes here. -notwostagemapxfer
        (svr_init.c) sends SERVER_MAP_XFER_WAIT immediately: frozen,
        untargetable, invincible, loading screen; then the transfer completes
        when the DbServer reports the destination ready, or is undone.
        """
        return ['-notwostagemapxfer'] if self.stock_travel_active() else []

    def stock_travel_active(self):
        """COH_STOCK_TRAVEL=1 with the external-maps DbServer layer installed."""
        stock = getattr(self, 'stock', None)
        layer = (getattr(self, 'manual_atlas_startup', None) or {}).get('external_maps')
        return isinstance(stock, dict) and stock['requested'] is True and layer is not None

    def capture_baseline(self):
        # The inherited baseline checks the complete accepted identity and
        # selected SQL rows before character_position selects the saved map.
        # This event is observational: it cannot authorize relocation or login.
        super().capture_baseline()
        saved = self.active_map_id
        require(saved == getattr(self, 'startup_saved_map_id', saved),
                'Saved destination changed during startup; preserve data and export')
        self.startup_saved_map_id = saved
        dynamic = self.dynamic_initial_requested()
        if dynamic:
            # No zone server before Enter Game: the saved zone is started when
            # the DbServer asks for it, and only that zone is admitted.
            require(self.zone_tree_for(saved) is not None,
                    character.CHARACTER + ' is saved in ' + zone_name(saved) + ', which this runtime cannot start; '
                    'preserve data and export')
            self.monorail_requires_reopen = False
            self.begin_initial_zone(saved)
        else:
            prepared = getattr(self, 'startup_preparation_map_id', self.active_map_id)
            require(self.active_map_id == prepared,
                    'Saved destination changed during startup; preserve data and export')
        destination = MAPS[saved]
        port = None if dynamic else destination['port']
        position = self.creation_report['baseline']['saved_position']
        self.zoning_report['saved_startup'] = {
            'map_id': saved, 'name': destination['name'],
            'world': destination['world'], 'port': port,
            'saved_position': dict(position), 'authority': 'preserved_postgresql_ents_staticmapid',
            'sql_game_mutations_performed': False, 'native_ready_verified': False,
            'character_world_entry_verified': False}
        if dynamic:
            self.zoning_report['saved_startup']['dynamic_start'] = self.initial_zone
        self.ctx.event('saved_character_destination', session_id=self.owner.args.session_id,
            character_id=self.CHARACTER_ID, auth_id=self.baseline_snapshot['identity']['authid'],
            name=character.CHARACTER, account=character.ACCOUNT, map_id=saved,
            map_name=destination['name'], world=destination['world'], port=port,
            existing_character_verified=True, saved_location_verified=True,
            sql_game_mutations_performed=False, dynamic_start=dynamic)
        self.persist_startup_observation()

    def dynamic_initial_requested(self):
        """No zone server before Enter Game (the game's own travel, ARM64 client).

        The character reaches its zone the way the game itself does it: at
        Enter Game the DbServer finds the character's static map not running
        and asks for it (handleChoosePlayer -> setNewMap -> startMapIfStatic;
        a new character's starting zone comes from determineStartMapId: Atlas
        Park, Mercy Island, Nova Praetoria or a tutorial). The supervisor starts
        it like any trip, and the client waits up to 900 s for the answer
        (patch 0126). Thor 0.13.57: starting King's Row while the client
        started ended with Android's low-memory killer closing the app; 0.13.58
        started Atlas Park first (owner, 2026-11-07: no Atlas Park unless the
        character is there). The zone now starts while the client waits at its
        character list, like the destination of a trip.
        """
        return (getattr(self, 'stock', {}).get('requested') is True
                and os.environ.get('COH_CLIENT_ARCH', 'x86') == 'arm64')

    def begin_initial_zone(self, expected):
        """The record of the first zone; expected is the saved map (None: a new character)."""
        if self.initial_zone is None:
            self.initial_zone = {'format': 2, 'policy': DYNAMIC_INITIAL_POLICY,
                'expected_map_id': expected, 'map_id': expected, 'zone_servers_before_enter_game': 0,
                'requested': False, 'started': False, 'ready': False, 'activated': False,
                'attempts': [], 'refused_requests': [], 'sql_game_mutations_performed': False,
                'available_memory_mib_at_baseline': available_memory_mib()}
            self.zoning_report['initial_zone'] = self.initial_zone
        require(self.initial_zone['expected_map_id'] == expected,
                'Saved destination changed during startup; preserve data and export')
        return self.initial_zone

    def dynamic_initial(self):
        value = getattr(self, 'initial_zone', None)
        return value if isinstance(value, dict) else None

    def initial_zone_pending(self):
        initial = self.dynamic_initial()
        return (initial is not None and initial['activated'] is not True
                and not self.creation_report.get('connected_on_atlas'))

    def admit_zone_request(self, map_id):
        """Before the character first enters the world, only its own zone may start.

        The DbServer asks for the saved zone at Enter Game (or a new character's
        starting zone). Any other request then, or a second one while the first
        is starting, is refused: the game reports that the map failed and the
        character stays at the character list. Nothing is moved.
        """
        if not self.initial_zone_pending():
            return None
        initial = self.dynamic_initial()
        reason = None
        if any(other != map_id for other in self.maps):
            reason = 'initial_zone_already_starting'
        elif initial['expected_map_id'] is not None and not same_zone(map_id, initial['expected_map_id']):
            reason = 'not_the_saved_zone'
        if reason is not None:
            initial['refused_requests'].append({'map_id': map_id, 'reason': reason,
                                                'utc_ms': int(time.time() * 1000)})
            del initial['refused_requests'][:-8]
        return reason

    def initial_zone_wait_seconds(self, now=None):
        """Seconds spent waiting for the first zone after the game asked for it (bounded)."""
        initial = self.dynamic_initial()
        if initial is None:
            return 0
        now = time.monotonic() if now is None else now
        total = 0.0
        for attempt in initial['attempts']:
            started = attempt.get('started_monotonic')
            if type(started) in (int, float):
                ended = attempt.get('ended_monotonic', now)
                total += max(0.0, min(ended, now) - started)
        return min(total, 2 * zone_travel.START_SECONDS)

    def tick_dynamic_initial(self):
        """Before the first connection, follow the zone the DbServer asked for and activate it."""
        initial = self.dynamic_initial()
        if initial is None or not self.initial_zone_pending():
            return
        now, now_ms = time.monotonic(), int(time.time() * 1000)
        attempts = initial['attempts']
        if attempts and 'ended_monotonic' not in attempts[-1] and attempts[-1]['map_id'] not in self.maps:
            # The start failed or ran out of time; the game told the client.
            attempts[-1].update(ended_monotonic=now, ended_utc_ms=now_ms, outcome='not_ready')
            self.initial_zone_event('not_ready', attempts[-1]['map_id'])
        target = next((map_id for map_id, owned in self.maps.items() if owned.get('stock')), None)
        if target is None:
            return
        owned = self.maps[target]
        require(initial['expected_map_id'] is None or same_zone(target, initial['expected_map_id']),
                'The game started ' + zone_name(target) + ' for ' + character.character_label() + ', not the saved '
                + zone_name(initial['expected_map_id']) + '; nothing was moved; export this report')
        launch = [target, owned.get('cookie'), owned.get('launch_utc_ms')]
        if attempts and 'ended_monotonic' not in attempts[-1] and attempts[-1]['launch'] != launch:
            attempts[-1].update(ended_monotonic=now, ended_utc_ms=now_ms, outcome='replaced')
        if not attempts or 'ended_monotonic' in attempts[-1]:
            row = self._latest_stock_start(target)
            # The wait counts from the game's request: the zone's preparation came first.
            attempts.append({'map_id': target, 'launch': launch, 'launch_utc_ms': owned.get('launch_utc_ms'),
                             'started_monotonic': owned.get('stock_started_monotonic',
                                                            owned.get('launch_monotonic', now)),
                             'requested_utc_ms': None if row is None else row.get('requested_utc_ms')})
            del attempts[:-8]
            initial.update(requested=True, started=True, map_id=target, map_name=zone_name(target),
                           started_utc_ms=owned.get('launch_utc_ms'))
            self.report['mapserver_started'] = self.ctx.report['mapserver_started'] = True
        if owned.get('ready') is not True:
            return
        self._activate(target)
        owned['last_occupied'] = now
        # The character's CLIENT_READY on this zone's route comes after its launch.
        self.ready_floor_ms = owned['launch_utc_ms'] - 999
        attempts[-1].update(ended_monotonic=now, ended_utc_ms=now_ms, outcome='ready')
        initial.update(ready=True, activated=True, activated_utc_ms=now_ms,
                       zone_servers_at_ready=sorted(self.maps),
                       available_memory_mib_at_ready=available_memory_mib())
        row = self._latest_stock_start(target)
        if row is not None:
            row['initial_login'] = True
            initial['request_to_ready_ms'] = (now_ms - row['requested_utc_ms']
                                              if type(row.get('requested_utc_ms')) is int else None)
        timing = getattr(self, 'initial_startup_timing', None)
        if timing is not None:
            timing.update(map_id=target, initial_zone_started_by_dbserver_request=True)
            self.mark_startup_timing(timing, 'map_ready_observed', now=now, utc_ms=now_ms)
        self.creation_report['map_ready'] = True
        startup = self.zoning_report.get('saved_startup')
        if startup is not None:
            startup.update(native_ready_verified=True, native_maps_started=sorted(self.maps))
        self.initial_zone_event('ready', target)
        self.sample_startup_observation(force=True)

    INITIAL_ZONE_MESSAGES = {
        'starting': 'Starting {zone} for {who}. The game screen can stay still for a few minutes until it is ready.',
        'ready': '{zone} is ready; {who} is entering it.',
        'not_ready': '{zone} did not start in time and the game reported it. Press Enter Game again, or export the report.',
        'failed': '{zone} could not be started ({reason}). The game reported it and nothing was moved; '
                  'export this report.',
        # 0.13.61: the DbServer keeps a new character whose first zone failed
        # (unloaded, not deleted); Resume removes that row so it can be created again.
        'failed_creation': '{zone} could not be started ({reason}). The game reported it; export this report. '
                           'The new character never entered the game: Resume first character creation removes '
                           'it so you can create it again.'}

    def initial_zone_event(self, status, map_id, *, failure=None):
        """The app shows this while the client waits for the zone (its screen does not move).

        A start that failed is sent as not_ready (the app then clears the
        starting line and returns the wait to the creator) with its reason.
        """
        key = status if failure is None else 'failed' if getattr(self, 'requires_saved_character', True) else 'failed_creation'
        fields = {} if failure is None else {'failure': failure}
        self.ctx.event('character_initial_zone', format=1, session_id=self.owner.args.session_id, status=status,
                       map_id=map_id, map_name=zone_name(map_id), generated_utc_ms=int(time.time() * 1000),
                       message=self.INITIAL_ZONE_MESSAGES[key].format(zone=zone_name(map_id), reason=failure,
                                                                      who=character.character_label()),
                       **fields)

    def initial_zone_start_failed(self, entry, failure):
        """The first zone's start failed before its server ran (its preparation stopped).

        Thor 0.13.59: a new villain's Mercy Island preparation stopped and the
        report's initial_zone still said nothing had been requested. The game
        already told the client (the start is delinked); nothing was moved, and
        Enter Game may ask again.
        """
        map_id = entry.get('map_id')
        if self.dynamic_initial() is None or not self.initial_zone_pending() or map_id in self.maps:
            return
        initial = self.dynamic_initial()
        now, now_ms = time.monotonic(), int(time.time() * 1000)
        began = getattr(self, 'stock_start_began', None)
        reason = str(failure)[:200]
        attempts = initial['attempts']
        attempts.append({'map_id': map_id, 'launch': [map_id, entry.get('cookie'), None], 'launch_utc_ms': None,
                         'started_monotonic': began if type(began) in (int, float) else now,
                         'requested_utc_ms': entry.get('seen_utc_ms'),
                         'ended_monotonic': now, 'ended_utc_ms': now_ms, 'outcome': 'failed', 'failure': reason})
        del attempts[:-8]
        initial.update(requested=True, map_id=map_id, map_name=zone_name(map_id))
        self.initial_zone_event('not_ready', map_id, failure=reason)

    def _latest_stock_start(self, map_id):
        return next((row for row in reversed(self.stock['starts']) if row['map_id'] == map_id), None)

    def qualify_monorail_preparation(self):
        if 'native_monorail' not in self.map_package:
            return
        monorail_contract.current_receipt(self.map_package_dir / 'MapServer.exe', self.map_package)
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
        # None: no zone is prepared before Enter Game (the DbServer asks for it).
        self.startup_preparation_map_id = None if self.dynamic_initial() is not None else self.active_map_id
        return self.startup_preparation_map_id

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
        if (type(value.get('staticmapid')) is int and value['staticmapid'] not in MAPS
                and value['staticmapid'] in zone_index.ZONES
                and getattr(self, 'zone_asset_document', None) is not None):
            register_zone(value['staticmapid'])   # saved in a zone served by the shared tree
        require(type(value['containerid']) is int and value['containerid'] == 1
            and supported(value['staticmapid'])
            and (type(value['mapid']) is int and value['mapid'] == value['staticmapid']
                 or allow_unassigned_active_map and value['mapid'] is None)
            and all(type(value[k]) in (int, float) and math.isfinite(value[k]) and abs(value[k]) <= 1000000
                    for k in ('posx', 'posy', 'posz')), 'Saved character is outside the supported local zones')
        require(value['staticmapid'] != 5 or getattr(self, 'monorail_qualified', False) is True,
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
        self._observe_stock_move(sample)
        if sample.get('loaded') and not sample.get('in_map_transfer'):
            require(type(sample.get('map_id')) is int and sample['map_id'] == self.active_map_id
                    and type(sample.get('static_map_id')) is int and sample['static_map_id'] == self.active_map_id,
                    'Character moved outside the verified zoning epoch')
        return connected(sample, self.active_map_id)

    def connection_metadata(self):
        metadata = super().connection_metadata()
        startup = self.zoning_report.get('saved_startup')
        initial = self.dynamic_initial()
        if initial is not None:
            self.verify_initial_connection(initial)
            if startup is not None:
                startup['character_world_entry_verified'] = True
        elif startup is not None:
            require(startup['map_id'] == self.active_map_id,
                    'Initial character connection differs from the saved destination')
            startup['character_world_entry_verified'] = True
        return dict(metadata, connected_on_supported_map=True, zoning_enabled=True,
                    monorail_enabled=self.monorail_enabled(),
                    stock_travel=getattr(self, 'stock', {}).get('enabled') is True)

    def verify_initial_connection(self, initial):
        """The first connection is on the zone the game started: the saved zone, or a new character's start."""
        require(initial['activated'] is True and self.active_map_id == initial['map_id']
                and (initial['expected_map_id'] is None or same_zone(self.active_map_id, initial['expected_map_id'])),
                'Initial character connection differs from the zone the game started; preserve data and export')
        initial['connected_map_id'] = self.active_map_id
        initial['connected_utc_ms'] = int(time.time() * 1000)

    def _remember_active(self):
        self.maps[self.active_map_id] = {'process': self.map_process, 'progress_path': self.map_progress_path,
            'previous': self.map_previous, 'launch_utc_ms': self.map_launch_utc_ms, 'ready': True,
            'server_metrics_enabled': getattr(self, 'server_metrics_enabled', False)}
        self.map_launch_history.observe(self.active_map_id, self.maps[self.active_map_id], self.epoch)

    def _activate(self, map_id):
        if self.map_process is not None and self.active_map_id in self.maps:
            self.maps[self.active_map_id]['previous'] = self.map_previous
        self.active_map_id = map_id
        self.active_since_monotonic = time.monotonic()
        owned = self.maps[map_id]
        self.map_process, self.map_progress_path = owned['process'], owned['progress_path']
        self.map_previous, self.map_launch_utc_ms = owned.get('previous'), owned['launch_utc_ms']
        self.map_progress_next = 0
        self.creation_report['map_id'] = map_id
        self.map_launch_history.observe(map_id, owned, self.epoch)

    def start_map(self):
        if self.dynamic_initial() is not None:
            self.defer_initial_zone()
            return
        if self.active_map_id == 1 and getattr(self, 'overlap_client_initialization', False) is not True:
            original = self.owner.wine_env
            initial_idle_token = self.idle_token()
            if initial_idle_token is not None:
                self.owner.wine_env = dict(original, **{scheduler.IDLE_ENVIRONMENT: initial_idle_token})
            if self.monorail_enabled():
                self.owner.wine_env = dict(self.owner.wine_env, **self.monorail_environment(1))
            try:
                super().start_map()
            finally:
                self.owner.wine_env = original
                if self.map_process is not None:
                    # Capture an actual launch even if inherited readiness
                    # raises. This does not insert it into the ready maps set.
                    self.map_launch_history.observe(1, {'process': self.map_process,
                        'progress_path': getattr(self, 'map_progress_path', None),
                        'launch_utc_ms': getattr(self, 'map_launch_utc_ms', None)}, self.epoch)
            self._remember_active()
            self.maps[self.active_map_id]['idle_token'] = initial_idle_token
        else:
            # Retain the accepted stage identifier while displaying the exact
            # PostgreSQL-selected destination and independently proving it.
            timing = self.map_startup_timing(self.active_map_id)
            self.mark_startup_timing(timing, 'map_baseline_check_started')
            self.ctx.stage('local_atlas_startup')
            target = self.active_map_id
            destination = MAPS[target]
            self.ctx.event('stage', status='running',
                message='Preparing ' + destination['name'] + ' for saved ' + character.CHARACTER,
                map_id=target, map_name=destination['name'], world=destination['world'],
                port=destination['port'])
            baseline = parse_map_status(self.query(['-getstatus', '1', str(target)], 'zoning-reopen-baseline'),
                                        target, allow_missing=True)
            require(baseline.get('not_started') is True, 'Saved destination already has an unowned MapServer')
            timing['baseline_destination_not_started'] = True
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

    def defer_initial_zone(self):
        """No zone server before Enter Game; the DbServer asks for the character's zone then.

        The stage keeps its accepted identifier (the app's stage contract) and
        records that no MapServer was started for it.
        """
        initial = self.dynamic_initial()
        expected = initial['expected_map_id']
        require(self.stock_travel_active() and self.stock.get('enabled') is True,
                (character.CHARACTER + ' is saved in ' + zone_name(expected) + '; starting it' if expected is not None
                 else "Starting the new character's zone") + " needs the game's own zone travel, which this "
                'runtime lacks; preserve data and export')
        self.ctx.stage('local_atlas_startup')
        self.initial_map_startup = None
        self.creation_report['map_ready'] = False
        initial['deferred_utc_ms'] = int(time.time() * 1000)
        startup = self.zoning_report.get('saved_startup')
        if startup is not None:
            startup['native_maps_started'] = []
        if expected is not None:
            message = (zone_name(expected) + ' starts when ' + character.CHARACTER + ' enters the game (Enter Game); '
                       'the game screen can stay still for a few minutes while it loads')
        else:
            message = ("The new character's starting zone starts after the character creator (Enter Game); "
                       'the game screen can stay still for a few minutes while it loads')
        self.ctx.event('stage', status='running', message=message, map_id=expected,
                       map_name=None if expected is None else zone_name(expected))
        self.ctx.passed(map_ready=False, map_id=expected, zone_servers_started=0,
                        initial_zone='started_by_the_game_at_enter_game', policy=DYNAMIC_INITIAL_POLICY)
        self.sample_startup_observation(force=True)

    def client_startup_assets_allowed(self):
        """Only a completely prepared owned world can overlap client loading."""
        if self.dynamic_initial() is not None and getattr(self, 'initial_map_startup', None) is None:
            # No zone server before Enter Game: nothing for client loading to overlap or seal.
            return True
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
        try:
            return self._poll_initial_map_startup()
        except BaseException as failure:
            # Overlapped client initialization joins this method after start()
            # returned. Preserve that failed attempt without swallowing or
            # reclassifying its existing lifecycle exception.
            timing = self.map_startup_timing((getattr(self, 'initial_map_startup', None) or {}).get('map_id'))
            if timing['status'] != 'map_readiness_observed':
                timing.update(status='failed_before_map_readiness', failure_type=type(failure).__name__)
            raise

    def _poll_initial_map_startup(self):
        """Main-thread readiness join; never grant entry from process launch alone."""
        startup = getattr(self, 'initial_map_startup', None)
        if startup is None:
            # A dynamic start has no zone to wait for before the client's input:
            # the character list and the creator need only the DbServer.
            return self.creation_report.get('map_ready') is True or self.dynamic_initial() is not None
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
                self.mark_startup_timing(self.map_startup_timing(target), 'map_ready_observed', now=completed)
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
                message='Starting ' + destination['name'] + (' and City of Heroes' if startup['overlap_enabled']
                                                             else ' for saved ' + character.CHARACTER),
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

    def _spawn_map(self, map_id, *, cookie=None, port=None, options=()):
        require(supported(map_id) and map_id not in self.maps and len(self.maps) < 2,
                'Duplicate or unreviewed zoning MapServer launch')
        require(cookie is None or type(cookie) is int and 0 < cookie < 2 ** 31, 'Invalid map start cookie')
        if port is None:
            port = MAPS[map_id]['port'] or free_zone_port({owned.get('port', MAPS.get(other, {}).get('port'))
                                                          for other, owned in self.maps.items()})
        if MAPS[map_id].get('shared_zone_tree'):
            MAPS[map_id]['port'] = port
        timing = self.map_startup_timing(map_id)
        def prepare_destination():
            if MAPS[map_id].get('shared_zone_tree'):
                runtime = self.prepare_zone_runtime()['runtime']
                # Its navigation graph, before its MapServer loads the map (pets and NPCs path).
                self.install_zone_beacon_graph(map_id, runtime)
                return runtime
            if map_id != 5:
                return self.prepare_atlas_runtime()
            self.wait_background_prestart()
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
        character.game.check_game_port(port, socket.SOCK_DGRAM)
        path = self.runtime / ('character-zoning-' + str(map_id) + '-progress.bin')
        require(not path.exists() and not path.is_symlink(), 'Stale zoning map progress file')
        environment = dict(self.owner.wine_env, **{character.evidence.GAME_LOOPBACK_ENV: '1',
            character.progress.ENVIRONMENT: base.windows_path(path)})
        idle_token = self.idle_token()
        if idle_token is not None:
            environment[scheduler.IDLE_ENVIRONMENT] = idle_token
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
        environment = self.map_metrics_environment(environment, map_runtime)
        launch_ms = int(time.time() * 1000)
        launch_monotonic = time.monotonic()
        self.mark_startup_timing(timing, 'map_spawn_requested', now=launch_monotonic, utc_ms=launch_ms)
        process = self.ctx.start('local-character-zoning-' + str(map_id), ['/usr/bin/env', '--chdir=' + str(map_runtime),
            self.owner.args.wine, base.windows_path(map_runtime / 'MapServer.exe'), '-nogui', '-db', '127.0.0.1',
            *character.mapserver_memory_arguments(), '-nostats', '-udp', str(port), '-tcp', '0',
            '-map_id', str(map_id), *(('-cookie', str(cookie)) if cookie is not None else ()),
            '-idleExitTimeout', '0', '-donotautogroup', *character.LOCAL_CLIENT_LINK_OPTIONS(),
            *self.session_map_options(), *options],
            env=environment)
        self.maps[map_id] = {'process': process, 'progress_path': path, 'previous': None,
                             'launch_utc_ms': launch_ms, 'ready': False, 'scheduler': pacing,
                             'idle_token': idle_token,
                             'runtime': map_runtime, 'launch_monotonic': launch_monotonic,
                             'server_metrics_enabled': self.server_metrics_enabled}
        self.map_launch_history.observe(map_id, self.maps[map_id], self.epoch)

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
        if self.initial_zone_pending() and self.map_process is None:
            return None   # no zone server yet: the game starts it at Enter Game
        if self.monorail_enabled():
            value = monorail_events.latest_ready(self.current_native_events())
            return value if value is not None and value['utc_ms'] >= self.ready_floor_ms else None
        if self.active_map_id == 1:
            if self.immediate_event_contract() is None:
                # Retained legacy MapServer (the CI donor): its first log match
                # has no time; take the newest CLIENT_READY after this launch.
                return legacy_ready(self.current_logs(), self.ready_floor_ms, int(time.time() * 1000))
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
        stock = getattr(self, 'stock', {}).get('enabled') is True
        target = self.pending['to_map_id'] if self.pending else self.active_map_id if stock else (
            (5 if self.monorail_enabled() else 101) if self.active_map_id == 1 else 1)
        value = {'format': 1, 'session_id': self.owner.args.session_id,
            'client_pid': self.creation_report['client_pid'], 'character_id': 1,
            'epoch': self.epoch, 'status': status, 'current_map_id': self.active_map_id,
            'target_map_id': target, 'current_map_name': zone_name(self.active_map_id),
            'target_map_name': zone_name(target), 'generated_utc_ms': int(time.time() * 1000),
            'epoch_limit': 0 if stock else MAX_EPOCHS, **fields}
        value.update(monorail_enabled=self.monorail_enabled(),
            travel_method='stock_travel' if stock else 'stock_monorail' if self.monorail_enabled()
                and self.active_map_id != 101 and not getattr(self, 'monorail_requires_reopen', False) else 'mapmove',
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
        request_observed_at, request_observed_utc_ms = time.monotonic(), int(time.time() * 1000)
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
        self.idle_restore(target, 'travel_requested')
        resident = target in self.maps
        loading = (resident and self.maps[target].get('prestarted') is True
                   and self.maps[target].get('native_ticking') is not True)
        budgets = prestarted_loading_budgets(target) if loading else preparation_budgets(target, resident)
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
            preparation_kind='prestarted_loading' if loading else 'resident_warm' if resident else 'cold',
            preparation_phase='python_inputs' if budgets['python_preparation_budget_seconds'] else 'native_readiness')
        self.pending.update(budgets)
        self.pending['startup_timing'] = self.begin_startup_timing('zoning_supervisor_request',
            map_id=target, epoch=self.epoch, resident=resident,
            now=request_observed_at, utc_ms=request_observed_utc_ms)
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
            self.mark_startup_timing(self.pending['startup_timing'], 'map_baseline_check_started', now=now, utc_ms=now_ms)
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
            self.mark_startup_timing(pending.get('startup_timing'), 'client_world_ready_observed', utc_ms=now_ms)
            self.pending = None
            self.idle_lower(pending.get('from_map_id'), 'player_left')
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
            self.start_tick_probe()
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
            # Before this tick can block in the destination's Python preparation.
            self._sync_station_fps_cap()
            if delivery is not None:
                old = self.delivery_history.get(delivery.get('epoch'))
                if old is not None:
                    require(delivery == old, 'Accepted zoning delivery receipt changed')
                else:
                    unseen_delivery = True
                    self._accept_delivery(delivery, now_ms)
            self.tick_prestart(time.monotonic())
            self.tick_idle()
            self.tick_priorities(time.monotonic())
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
                self.map_startup_timing(target)['baseline_destination_not_started'] = True
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
                        self.mark_startup_timing(self.map_startup_timing(target), 'map_ready_observed',
                            now=ready_now, utc_ms=ready_now_ms)
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
                timing = self.pending.get('startup_timing')
                if timing is not None and timing['status'] != 'map_readiness_observed':
                    timing.update(status='failed_before_map_readiness', failure_type=type(failure).__name__)
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
        finally:
            # Ready, arrival, failure or a cancelled request lifts the cap.
            self._sync_station_fps_cap()

    def _sync_station_fps_cap(self):
        """Hold the ARM64 client at STATION_FPS_CAP while a trip is prepared.

        The client polls the file once a second (patch 0121) and restores its
        previous cap when the file is gone, unless /maxfps changed it meanwhile.
        A failure here never affects zoning; it is reported and the cap is lifted.
        """
        path = getattr(self.owner, 'armport_fps_cap_file', None)
        record = getattr(self, 'station_fps_cap', None)
        if record is None:
            return
        # Only the ARM64 client (armport_interactive) carries patch 0121.
        record['client_supported'] = path is not None
        if path is None:
            return
        pending = self.pending
        want = (record['error'] is None and pending is not None
                and pending.get('phase') in STATION_FPS_CAP_PHASES and not pending.get('transfer_requested'))
        try:
            present = path.exists() or path.is_symlink()
            if want and not present:
                staged = path.with_name(path.name + '.tmp')
                staged.unlink(missing_ok=True)
                staged.write_text(str(STATION_FPS_CAP) + '\n')
                os.replace(staged, path)
                record['applied'] += 1
            elif present and not want:
                path.unlink()
                record['removed'] += 1
        except OSError as failure:
            record['error'] = type(failure).__name__ + ': ' + str(failure)[:160]
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    # The game's own zone travel (COH_STOCK_TRAVEL=1) -------------------------
    def external_maps_options(self):
        if not self.stock_travel_active():
            return super().external_maps_options()
        self.zone_policy = zone_travel.ZoneTravelPolicy(tree_for=self.zone_tree_for,
            running=self.zone_servers, occupied=self.stock_occupied, admit=self.admit_zone_request)
        self.stock['enabled'] = True
        # Maps this flow owns (started at session start or for a request) are
        # never delinked; every other request goes through the policy.
        return {'session_maps': lambda map_id: map_id in self.maps, 'policy': self.zone_policy}

    def zone_tree_for(self, map_id):
        if map_id in (1, 101):
            return 'atlas'
        if map_id == 5:
            return 'kings_row' if getattr(self, 'monorail_qualified', False) is True else None
        if map_id in zone_index.ZONES and getattr(self, 'zone_asset_document', None) is not None:
            return 'zones'
        return None

    def stock_occupied(self):
        """The zone the hero is on, asked of the DbServer when a request needs room.

        The stock entity log reaches the guest 30-60 s late (the MapServer
        resends logs every 30 s; Thor 0.13.56: ResumeCharacter in King's Row at
        15:18:33 was read at 15:19:40), so active_map_id can still name the zone
        the hero just left; stopping the "idle" one would then drop the hero.
        One -getstatus 3 probe (only for a third zone) gives the DbServer's own
        answer: during the request the hero is still on the origin map
        (InMapXfer). An owned, ready map other than active_map_id is recorded as
        the arrival it is. None (unknown) makes the policy delink: the game
        says the map failed and the hero stays where they are.
        """
        if self.query_count >= STOCK_PROBE_QUERY_LIMIT:
            return None
        try:
            sample = character.evidence.parse_character_status(
                self.query(['-getstatus', '3', '1'], 'stock-occupied'), 1, character.CHARACTER, character.ACCOUNT,
                allow_missing=True)
        except base.Cancelled:
            raise
        except (base.DiagnosticError, OSError, ValueError):
            return None
        self.stock['occupied_probes'] = self.stock.get('occupied_probes', 0) + 1
        map_id = sample.get('map_id')
        if (sample.get('loaded') is not True or sample.get('connected') is not True or type(map_id) is not int
                or sample.get('static_map_id') != map_id or map_id not in self.maps
                or self.maps[map_id].get('ready') is not True):
            return None
        if map_id != self.active_map_id:
            self._stock_arrival(map_id, {'source': 'stock_occupied_probe', 'map_id': map_id,
                                         'in_map_transfer': sample.get('in_map_transfer') is True})
            # Older log lines (this zone's own resume among them) are not a later arrival.
            self.stock_last_arrival_ms = int(time.time() * 1000)
        return map_id

    def zone_servers(self):
        return {map_id: {'ready': owned.get('ready') is True,
                         'port': owned.get('port', MAPS.get(map_id, {}).get('port')),
                         'last_occupied': owned.get('last_occupied', 0)}
                for map_id, owned in self.maps.items()}

    def serve_external_maps(self, supervisor):
        if not self.stock['enabled']:
            return
        self.stock['decisions'] = self.zone_policy.report()['decisions']
        entry = supervisor.next_start()
        while entry is not None:
            try:
                self._start_stock_map(supervisor, entry)
            except (base.DiagnosticError, OSError, ValueError, KeyError) as failure:
                if isinstance(failure, base.Cancelled):
                    raise
                supervisor.start_failed(entry, failure)
                self._stock_row(entry)['failure'] = str(failure)[:200]
                self.initial_zone_start_failed(entry, failure)
            entry = supervisor.next_start()
        self._tick_stock_starts(supervisor)

    def _stock_row(self, entry):
        key = (entry['map_id'], entry['cookie'])
        for row in self.stock['starts']:
            if (row['map_id'], row['cookie']) == key:
                return row
        row = {'map_id': key[0], 'cookie': key[1], 'map_name': entry.get('map_name'),
               'requested_utc_ms': entry.get('seen_utc_ms')}
        self.stock['starts'].append(row)
        del self.stock['starts'][:-32]
        return row

    def _evict_map(self, map_id, reason):
        require(map_id != self.active_map_id and map_id not in self.stock_starts,
                'Refusing to stop the occupied or a starting zone')
        owned = self.maps.pop(map_id)
        if owned['process'].process.poll() is None:
            owned['process'].process.terminate()
        path = owned['progress_path']
        if path.exists() or path.is_symlink():
            # A later start of this zone needs a fresh progress file.
            path.rename(path.with_name(path.name + '.stopped-' + str(len(self.stock['evictions']) + 1)))
        self.stock['evictions'].append({'map_id': map_id, 'reason': reason, 'utc_ms': int(time.time() * 1000)})
        del self.stock['evictions'][:-32]

    def _start_stock_map(self, supervisor, entry):
        plan = entry['plan']
        map_id = entry['map_id']
        row = self._stock_row(entry)
        self.stock_start_began = None
        for other in plan['evict']:
            self._evict_map(other, 'room_for_' + str(map_id))
        started = self.stock_start_began = time.monotonic()
        if plan['tree'] == 'zones':
            register_zone(map_id)
        # Before 0.13.59 a trip's spawn relabelled the session's initial timing
        # row (its map_id became the trip's; its times stayed the first zone's).
        initial = self.initial_zone_pending()
        timing = (None if initial else self.begin_startup_timing('stock_travel_request',
                  map_id=map_id, epoch=self.epoch + 1, now=started))
        if initial:
            # Announced before the zone's preparation, which runs here and can take minutes.
            self.initial_zone_event('starting', map_id)
        self.stock_spawn_timing = timing
        try:
            self._spawn_map(map_id, cookie=entry['cookie'], port=plan['port'],
                            options=tuple(entry.get('options', {}).get('kept', ())))
        finally:
            self.stock_spawn_timing = None
        owned = self.maps[map_id]
        owned.update(stock=True, cookie=entry['cookie'], port=plan['port'], startup_timing=timing,
                     stock_started_monotonic=started)
        self.stock_starts[map_id] = {'entry': entry, 'started': started,
                                     'deadline': started + plan['budget_seconds']}
        supervisor.start_launched(entry, port=plan['port'], tree=plan['tree'], evicted=list(plan['evict']))
        row.update(tree=plan['tree'], port=plan['port'], evicted=list(plan['evict']),
                   launched_utc_ms=int(time.time() * 1000))

    def _tick_stock_starts(self, supervisor):
        for map_id, state in list(self.stock_starts.items()):
            entry, now = state['entry'], time.monotonic()
            row = self._stock_row(entry)
            failure = None
            try:
                current = self._map_progress(map_id)
                if self.live_progress(current):
                    self.maps[map_id]['ready'] = True
                    del self.stock_starts[map_id]
                    self.mark_startup_timing(self.maps[map_id].get('startup_timing'), 'map_ready_observed', now=now)
                    supervisor.start_ready(entry, elapsed_seconds=now - state['started'])
                    row.update(ready=True, ready_seconds=round(now - state['started'], 3))
                    continue
                if now >= state['deadline']:
                    failure = 'not ready within %d s' % zone_travel.START_SECONDS
            except base.DiagnosticError as error:
                if isinstance(error, base.Cancelled):
                    raise
                failure = str(error)
            if failure is not None:
                del self.stock_starts[map_id]
                owned = self.maps.pop(map_id, None)
                if owned is not None and owned['process'].process.poll() is None:
                    owned['process'].process.terminate()
                supervisor.start_failed(entry, failure, elapsed_seconds=now - state['started'])
                row.update(ready=False, failure=failure[:200], failed_seconds=round(now - state['started'], 3))

    def _observe_stock_move(self, sample):
        """The game's own travel: the character connected on another owned, ready zone."""
        if not getattr(self, 'stock', {}).get('enabled'):
            return
        if self.dynamic_initial() is not None and not self.creation_report.get('connected_on_atlas'):
            # The first connection after a dynamic start is not a trip.
            self.tick_dynamic_initial()
            return
        if sample.get('loaded') is True and sample.get('connected') is True and sample.get('in_map_transfer') is False:
            moved = sample.get('map_id')
            if (type(moved) is int and moved != self.active_map_id and moved in self.maps
                    and sample.get('static_map_id') == moved and self.maps[moved].get('ready') is True):
                self._stock_arrival(moved, sample)
        elif sample.get('in_map_transfer') is True:
            self.stock['transfer_wait_observed'] += 1

    def _poll_stock_logs(self, now=None):
        """The game's own travel, read from the stock entity log (every POLL_SECONDS).

        Once the connection is proved the base flow stops its translated status
        probes (steady-state policy), so a zone change must be read where the
        game writes it: "Step 1: Ent ... moving to map N" on the current map's
        route, then CLIENT_READY (resumeCharacter) on another owned, ready map's
        route, newer than the last arrival. CI r56z4: the hero reached map 101
        (City_01_01_2 ResumeCharacter) while the samples still said map 1.
        """
        stock = getattr(self, 'stock', {})
        if (not stock.get('enabled') or self.creation_report.get('verified')
                or not self.creation_report.get('connected_on_atlas')):
            return None
        now = time.monotonic() if now is None else now
        if now < self.stock_log_next:
            return None
        self.stock_log_next = now + character.POLL_SECONDS
        now_ms = int(time.time() * 1000)
        if self.stock_last_arrival_ms is None:
            self.stock_last_arrival_ms = self.creation_report.get('client_ready_observed_utc_ms') or now_ms
        logs = self.current_logs()
        begun = stock_transfers_begun(logs, self.active_map_id, self.stock_last_arrival_ms, now_ms)
        known = {(row['utc_ms'], row['to_map_id']) for row in stock['transfers_begun']}
        for row in begun:
            if (row['utc_ms'], row['to_map_id']) not in known:
                stock['transfers_begun'].append(row)
                stock['transfer_wait_observed'] += 1
        del stock['transfers_begun'][:-16]
        arrivals = []
        for map_id, owned in self.maps.items():
            if map_id == self.active_map_id or owned.get('ready') is not True or not supported(map_id):
                continue
            floor = max(self.stock_last_arrival_ms + 1, owned['launch_utc_ms'] - 999)
            record = stock_ready(logs, map_id, floor, now_ms)
            if record is not None:
                arrivals.append(record)
        if not arrivals:
            return None
        record = max(arrivals, key=lambda r: (r['utc_ms'], r['line_ordinal']))
        self.stock_last_arrival_ms = record['utc_ms']
        stock['arrival_source'] = 'stock_entity_log_resume_character'
        self._stock_arrival(record['map_id'], {'source': 'stock_entity_log', 'map_id': record['map_id'],
                                               'resume_utc_ms': record['utc_ms'], 'log_route': record['log_route'],
                                               'line_sha256': record['line_sha256']})
        return record

    def _stock_arrival(self, target, sample):
        now, now_ms = time.monotonic(), int(time.time() * 1000)
        origin = self.active_map_id
        self.maps[origin]['last_occupied'] = now
        self._activate(target)
        self.maps[target]['last_occupied'] = now
        self.epoch += 1
        self.stock['arrivals'] += 1
        self.creation_report.update(connected_on_supported_map=True, map_id=target, zoning_epoch=self.epoch,
            monorail_enabled=False, recovery_requested=False, recovery_verified=False,
            ordinary_stuck_observed=False, on_atlas_safe_position=False, stable_ground_verified=False,
            committed_safe_position_verified=False)
        # The first zone's own start (initial_login) is not a trip's destination start.
        start = next((row for row in reversed(self.stock['starts'])
                      if row['map_id'] == target and row.get('ready') and not row.get('initial_login')), None)
        leg = {'epoch': self.epoch, 'from_map_id': origin, 'to_map_id': target, 'travel_method': 'stock_travel',
               'character_status': sample, 'arrival_observed_utc_ms': now_ms,
               'destination_started_for_request': start is not None and start.get('arrived_utc_ms') is None,
               'request_to_arrival_ms': (now_ms - start['requested_utc_ms']
                                         if start is not None and start.get('arrived_utc_ms') is None
                                         and type(start.get('requested_utc_ms')) is int else None)}
        if start is not None and start.get('arrived_utc_ms') is None:
            start['arrived_utc_ms'] = now_ms
            self.mark_startup_timing(self.maps[target].get('startup_timing'), 'client_world_ready_observed',
                                     now=now, utc_ms=now_ms)
        self.zoning_report['transfers'].append(leg)
        del self.zoning_report['transfers'][:-32]
        self._emit('arrived', current_map_verified=True, destination_ready=True, travel_method='stock_travel',
                   arrival_native_verified=False, character_identity_preserved=True,
                   from_map_id=origin)

    def character_evidence(self):
        self.remember_reward_connection()
        self.tick_zoning()
        self.tick_external_maps()
        self.tick_dynamic_initial()
        self._poll_stock_logs()
        if self.pending is not None and (self.pending.get('transfer_requested')
                or self.pending.get('native_authorization_issued')):
            return None
        # The ordinary Atlas save path is retained, with only map-scoped native
        # witnesses and read-only finite-map position validation overridden.
        return super().character_evidence()

    def saved_metadata(self, snapshot):
        return dict(super().saved_metadata(snapshot), **self.zoning_saved_metadata())

    def zoning_saved_metadata(self):
        return dict(zoning_enabled=True, connected_on_supported_map=True, map_id=self.active_map_id,
            monorail_enabled=self.monorail_enabled(), zoning_epoch=self.epoch, ordinary_save_after_native_zoning=True)

    def collect_character(self, target):
        """The character flow's own evidence (the reopen's; creation overrides it)."""
        super().collect(target)

    def collect(self, target):
        # Keep the retained archive member for older readers, but identify its
        # actual owning map rather than attributing a Kings console to Atlas.
        if self.map_process is not None:
            self.zoning_report['active_console'] = {'archive_member': 'character-atlas-console.txt',
                'retained_member_name': True, 'map_id': self.active_map_id,
                'map_name': MAPS[self.active_map_id]['name'], 'world': MAPS[self.active_map_id]['world'],
                'port': MAPS[self.active_map_id]['port'], 'session_id': self.owner.args.session_id,
                'launch_utc_ms': self.map_launch_utc_ms}
        self.collect_character(target)
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
            self.zoning_report.setdefault('shared_heap_consoles', {})[str(map_id)] = character.shared_heap_console(raw)
        try:
            self.zoning_report['launch_history'] = self.map_launch_history.collect(
                target, self.maps, self.map_process, self.ctx.secrets)
        except Exception as error:
            self.zoning_report['launch_history'] = {'format': 1, 'available': False,
                'complete': False, 'is_success_proof': False, 'retirement_enabled': False,
                'reason': type(error).__name__[:80]}
        base.private_write(target / 'character-zoning.json', json.dumps(self.zoning_report, indent=2) + '\n')


class LocalCharacterZoningCreationServer(LocalCharacterZoningServer):
    """Character creation with the game's own zone travel (ARM64 client).

    No zone server runs before Enter Game. After the creator, the DbServer asks
    for the new character's starting zone (determineStartMapId: Atlas Park for
    a Primal hero, Mercy Island for a villain, Nova Praetoria for a Praetorian,
    or that side's tutorial); the zone policy starts it, the character enters
    it, and the ordinary creation save is proved there. The creation identity
    (empty account, character ID 1 under any name, committed rows) is the base creation's.
    """
    REPORT_KEY = 'character_creation'
    requires_saved_character = False
    # Set by the reopen constructor; a creation report never carries them.
    REOPEN_FIELDS = ('before_character_id', 'baseline_character_id', 'existing_character_verified',
        'preserved_existing_identity', 'powers_preserved', 'costume_preserved', 'native_client_ready_observed',
        'ordinary_stuck_observed', 'on_atlas_safe_position', 'stable_ground_verified', 'recovery_requested',
        'recovery_verified', 'committed_native_position_verified', 'committed_safe_position_verified', 'operation')

    def __init__(self, owner):
        super().__init__(owner)
        for key in self.REOPEN_FIELDS:
            self.creation_report.pop(key, None)
        # Unknown until the DbServer asks for the starting zone.
        self.active_map_id = None
        self.creation_report['map_id'] = None
        self.zoning_report['scope'] = 'stock_travel_character_creation_starting_zone'

    def initialize(self):
        character.LocalCharacterServer.initialize(self)

    def initial_map_preparation(self):
        self.qualify_monorail_preparation()
        require(self.dynamic_initial_requested(),
                "Creating a character with the game's own zone travel needs the ARM64 client")
        self.begin_initial_zone(None)
        self.startup_preparation_map_id = None
        return None

    def capture_baseline(self):
        character.LocalCharacterServer.capture_baseline(self)

    def login_evidence(self):
        return character.LocalCharacterServer.login_evidence(self)

    def verify_current_identity(self, identity, inventory):
        return character.LocalCharacterServer.verify_current_identity(self, identity, inventory)

    def validate_saved_rows(self, rows, inventory):
        return character.LocalCharacterServer.validate_saved_rows(self, rows, inventory)

    def remember_reward_connection(self):
        pass

    def observe_connected_character(self):
        pass

    def connection_metadata(self):
        initial = self.dynamic_initial()
        require(initial is not None, 'New character connection lacks its starting zone')
        self.verify_initial_connection(initial)
        return {'connected_on_supported_map': True, 'zoning_enabled': True, 'monorail_enabled': False,
                'stock_travel': self.stock.get('enabled') is True, 'starting_zone_map_id': initial['map_id']}

    def saved_metadata(self, snapshot):
        return dict(self.zoning_saved_metadata(), stock_travel=self.stock.get('enabled') is True)

    def collect_character(self, target):
        character.LocalCharacterServer.collect(self, target)


def creation_identity(proof, session):
    """A new character connected in the starting zone the game started (stock travel)."""
    return (isinstance(proof, dict) and proof.get('session_id') == session
        and character.valid_character_name(proof.get('name')) and proof.get('name') == character.CHARACTER
        and proof.get('account') == 'COHLOCAL'
        and type(proof.get('character_id')) is int and proof['character_id'] == 1
        and type(proof.get('auth_id')) is int and 0 < proof['auth_id'] <= 4294967295
        and type(proof.get('map_id')) is int and 1 <= proof['map_id'] <= 999 and supported(proof['map_id'])
        and all(proof.get(key) is True for key in ('connected_on_atlas', 'connected_on_supported_map',
                                                   'zoning_enabled', 'stock_travel')))


def creation_save_verified(proof, session):
    return (creation_identity(proof, session) and proof.get('verified') is True
        and proof.get('committed_sql_verified') is True and proof.get('requested_logout_observed') is True
        and proof.get('logout_timer_observed') is True
        and proof.get('disconnected_before_sql') is True and proof.get('forced_stop_before_save') is False)


def character_identity(proof, session):
    return (isinstance(proof, dict) and proof.get('session_id') == session
        and character.valid_character_name(proof.get('name')) and proof.get('name') == character.CHARACTER
        and proof.get('account') == 'COHLOCAL'
        and type(proof.get('character_id')) is int and proof['character_id'] == 1
        and type(proof.get('auth_id')) is int and proof['auth_id'] > 0 and supported(proof.get('map_id'))
        # King's Row needs its verified package: the station monorail, or the
        # game's own travel, whose supervisor starts it only from that package
        # (zone_tree_for). Thor 0.13.56: arrival by stock monorail ended here.
        and (proof['map_id'] != 5 or proof.get('monorail_enabled') is True or proof.get('stock_travel') is True)
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
