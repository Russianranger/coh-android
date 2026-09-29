"""Pure acceptance of Atlas/TestClient protocol and committed SQL evidence.

These functions do not launch a process, query SQL, or substitute log messages
for protocol evidence. Raw console and pipe records remain private to the run.
"""
import copy
import math
from pathlib import Path
import re
import sys

sys.path.insert(0, '/opt/coh' if Path('/opt/coh/diagnostic.py').is_file()
                else str(Path(__file__).resolve().parent))
import diagnostic as base

require = base.require
MAP_ID = 1
MAP_PATH = 'maps/City_Zones/City_01_01/City_01_01.txt'
MAP_UDP_PORT = 7001
INFLUENCE = 12345
LOG_LIMIT = 16 * 1024 * 1024
EVENT_LIMIT = 8 * 1024 * 1024
GAME_LOOPBACK_ENV = 'COH_GAME_LOOPBACK_ONLY'
GAME_LOOPBACK_ACK = 'COH_GAME_LOOPBACK_ONLY=1 active: IPv4 loopback binding policy'
GAME_LOOPBACK_RECORD = re.compile(r'COH_GAME_LOOPBACK_ONLY bind verified: protocol=(tcp|udp) '
                                  r'address=(127\.0\.0\.1) port=([1-9][0-9]{0,4})\Z')
GAME_LOOPBACK_METADATA = {
    'environment_variable': GAME_LOOPBACK_ENV, 'enabled_value': '1', 'disabled_by_default': True,
    'activation': 'before_common_startup',
    'late_activation': 'refused_after_first_explicit_or_client_UDP_bind_attempt',
    'wildcard_address': '127.0.0.1', 'explicit_addresses': 'IPv4_127/8_only',
    'client_UDP': 'explicit_loopback_ephemeral_bind_before_first_send',
    'endpoint_verification': 'getsockname_and_SO_TYPE_after_each_successful_bind',
    'socket_types': ['tcp', 'udp'], 'endpoint_record': 'protocol_address_port',
    'scope': 'explicit_IPv4_listeners_and_client_UDP_bindings',
    'network_namespace_isolation': False, 'outbound_connections_restricted': False,
    'outbound_TCP': 'unchanged', 'failure': 'close_socket_and_exit_2',
    'startup_acknowledgement': GAME_LOOPBACK_ACK, 'android_execution_validated': False,
}
IDENTITY_FIELDS = ('containerid', 'authid', 'authname', 'name')
SELECTED = {
    'ents': IDENTITY_FIELDS + ('class', 'origin', 'level', 'experiencepoints',
        'influencepoints', 'description', 'motto', 'datecreated'),
    'ents2': ('containerid', 'subid', 'curbuild', 'originalprimary',
        'originalsecondary', 'praetorianprogress', 'playersubtype', 'influencetype'),
    'powers': ('containerid', 'subid', 'powerid', 'categoryname', 'powersetname',
        'powername', 'powerlevelbought', 'powernumboostsbought',
        'powersetlevelbought', 'buildnum', 'uniqueid'),
    'costumeparts': ('containerid', 'subid', 'name', 'geom', 'tex1', 'tex2',
        'displayname', 'region', 'bodyset', 'color1', 'color2', 'costumenum',
        'fxname', 'color3', 'color4'),
}
ROW_KEYS = {'ents': ('containerid',), **{table: ('containerid', 'subid')
    for table in ('ents2', 'powers', 'costumeparts')}}
ATTRIBUTE_FIELDS = {
    'ents': ('class', 'origin'),
    'powers': ('categoryname', 'powersetname', 'powername'),
    'costumeparts': ('name', 'geom', 'tex1', 'tex2', 'displayname', 'region',
        'bodyset', 'fxname'),
}
ACCOUNT = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,31}\Z', re.ASCII)
FAILURE = re.compile(r'\b(?:fatal|assertion failed|SQL_ERROR|SQLERROR|PG_FIFO_FAILED|'
    r'INVALID PARAMETER|Giving up|Bad output file|Error binding|SQLSTATE|ODBC error|SQL error|'
    r'CRASH|Exception caught|CRT Error|Errorf|Unable to locate character|'
    r'Character creation did not reach|Error logging on|Error connecting to MapServer|'
    r'Error calling choosePlayerWrapper|Did not get players|Server timeout|'
    r'No free slots|does not have a character in slot|dbQuery failed|Failed to connect to DbServer)\b|'
    r'^\s*ERROR[:\s]', re.I)
CRITICAL_ASSET = re.compile(r'(?:cannot|can\x27t|could not|couldn\x27t|failed to|unable to)\s+'
    r'(?:find|open|load|read)\b.*\.(?:geo|anim|texture|pigg|txt)|'
    r'\bmissing\s+(?:geometry|animation|map|texture)\b', re.I)
BENIGN_NOTICE = re.compile(
    r'(?:\d{6} \d{2}:\d{2}:\d{2} -?\d+ )?SQLERROR: -1 (?:'
    r'00000 NOTICE: (?:relation "(?:ents|ents2)" does not exist, skipping|'
    r'constraint "fk_ents2_leaguesid_leagues" of relation "ents2" does not exist, skipping|'
    r'constraint "fk_ents_teamupsid_teamups" of relation "ents" does not exist, skipping)|'
    r'42P07 NOTICE: relation "coh_[0-9a-f]{32}" already exists, skipping)')


def _text(text):
    require(isinstance(text, str) and '\0' not in text and
            len(text.encode('utf-8')) <= LOG_LIMIT, 'Invalid or oversized text evidence')
    return text


def game_listener_bindings(text, role, *, enabled=True, pending=False):
    """Parse ordered getsockname records from one owned process's complete output.

    Sequential client sockets can legitimately reuse a port after closing. Keep
    every record and its order so a later capture must preserve the live prefix.
    """
    require(role in ('atlas', 'client'), 'Unknown game listener role')
    output = _text(text)
    if pending:
        output = output[:output.rfind('\n') + 1]
    lines = [line for line in output.splitlines() if GAME_LOOPBACK_ENV in line]
    if not enabled:
        require(not lines, 'Game listener policy activated outside the selected profile')
        return None
    if not lines and pending:
        return False
    require(lines and lines[0] == GAME_LOOPBACK_ACK, 'Game listener activation is missing or malformed')
    require(len(lines) <= 129, 'Game listener record count exceeded bound')
    endpoints = []
    for line in lines[1:]:
        match = GAME_LOOPBACK_RECORD.fullmatch(line)
        require(match is not None, 'Malformed or non-loopback game binding evidence')
        protocol, address, port = match.groups()
        require(protocol == 'udp' and 1 <= int(port) <= 65535,
                'Unexpected game transport or invalid actual bound port')
        endpoints.append({'protocol': protocol, 'address': address, 'port': int(port)})
    if role == 'atlas':
        required = [{'protocol': 'udp', 'address': '127.0.0.1', 'port': MAP_UDP_PORT}]
        require(not endpoints or endpoints == required, 'Atlas listener differs from the UDP 7001 contract')
        ready = endpoints == required
    else:
        ready = len(endpoints) >= 2  # Database login and map connection sockets.
    if pending and not ready:
        return False
    require(ready, 'Game listener proof is incomplete for ' + role)
    return {'requested': True, 'startup_acknowledgement': GAME_LOOPBACK_ACK, 'endpoints': endpoints}


def _identity(account, identifier=None, name=None):
    require(isinstance(account, str) and ACCOUNT.fullmatch(account), 'Invalid diagnostic account')
    if identifier is not None:
        require(type(identifier) is int and identifier > 0, 'Character ID must be a positive integer')
    if name is not None:
        require(isinstance(name, str) and bool(name.strip()) and len(name) <= 128 and
                not any(ord(c) < 32 for c in name), 'Invalid recorded character name')


def diagnostic_failures(text, allow_requested_logout=False):
    failures = []
    for line in _text(text).splitlines():
        if allow_requested_logout and (re.fullmatch(r'\s*Fatal Error: Booted back to login screen\s*', line)
                or re.fullmatch(r'[^\r\n]*\bFATAL\b[^\r\n]*Was booted back to login screen\s*', line)):
            continue
        if (FAILURE.search(line) and not BENIGN_NOTICE.fullmatch(line.strip())) or CRITICAL_ASSET.search(line):
            failures.append(line[:2000])
    return failures


def _ipv4(address):
    return bool(re.fullmatch(r'(?:[0-9]{1,3}\.){3}[0-9]{1,3}', address)) and all(
        0 <= int(part) <= 255 for part in address.split('.'))


def parse_find(text):
    require(not diagnostic_failures(text), 'Character find query emitted failure diagnostics')
    matches = re.findall(r'^\s*container_id = (-?\d+)\s*$', text, re.M)
    require(len(matches) == 1 and int(matches[0]) > 0, 'Missing or ambiguous positive character ID')
    return int(matches[0])


def parse_map_status(text, allow_missing=False):
    require(not diagnostic_failures(text), 'Map status query emitted failure diagnostics')
    missing = [line for line in text.splitlines() if line.strip() == 'invalid container request']
    matches = [match.groups() for line in text.splitlines() if
               (match := re.fullmatch(r'\s*(\d+)\s+(\S+)\s+(.+?)\s*', line))]
    if missing:
        require(allow_missing and len(missing) == 1 and not matches, 'Unexpected or ambiguous missing map')
        return {'ready': False, 'not_started': False, 'missing': True}
    require(len(matches) == 1 and matches[0][0] == '1', 'Missing or ambiguous Atlas map1 response')
    _, name, fields = matches[0]
    require(name.replace('\\', '/').casefold() in (MAP_PATH.casefold(), 'city_01_01.txt'),
            'Map status identifies a different map')
    not_ready = re.findall(r'\bNotReady\s+(\S+)', fields)
    require(not not_ready or not_ready == ['1'], 'Unrecognized not-ready map status')
    if fields.startswith('NotReady'):
        require(re.fullmatch(r'NotReady 1 \(Not started\) Info(?: .*)?', fields) is not None,
                'Unrecognized unstarted map status')
        return {'ready': False, 'not_started': True, 'map_id': MAP_ID}
    match = re.match(r'S:\s*(\d+)\s*/\s*(\d+)\s+Ip:\s*([0-9.]+):(\d+)\s+Mem:', fields)
    require(match is not None, 'Unrecognized connected map status')
    network_age, stats_age, address, port = match.groups()
    require(_ipv4(address) and 0 < int(port) <= 65535, 'Invalid map endpoint')
    return {'ready': not not_ready, 'not_started': False, 'map_id': MAP_ID,
            'network_age_seconds': int(network_age), 'stats_age_seconds': int(stats_age),
            'address': address, 'port': int(port)}


def map_ready_current(status):
    return (isinstance(status, dict) and status.get('ready') is True and
            status.get('map_id') == MAP_ID and status.get('address') == '127.0.0.1' and
            type(status.get('port')) is int and status['port'] == MAP_UDP_PORT and
            all(type(status.get(key)) is int and 0 <= status[key] <= 20
                for key in ('network_age_seconds', 'stats_age_seconds')))


def parse_character_status(text, identifier, name, account, allow_missing=False):
    _identity(account, identifier, name)
    require(type(identifier) is int and identifier > 0, 'Character ID must be a positive integer')
    require(not diagnostic_failures(text), 'Character status query emitted failure diagnostics')
    missing = [line for line in text.splitlines() if line.strip() == 'invalid container request']
    pattern = re.compile(r'\s*(\d+)\s+Name\s+(.+?)\s+Auth\s+(\S+)\s+Ip\s+(\S+)\s+'
                         r'MapId\s+(\d+)\s+SmapId\s+(\d+)\s*(.*?)\s*')
    matches = [match.groups() for line in text.splitlines() if (match := pattern.fullmatch(line))]
    if missing:
        require(allow_missing and len(missing) == 1 and not matches, 'Unexpected or ambiguous missing character')
        return {'loaded': False, 'connected': False, 'in_map_transfer': False}
    require(len(matches) == 1, 'Missing or ambiguous character status response')
    ident, observed_name, observed_account, address, mapid, static_mapid, flags = matches[0]
    require(int(ident) == identifier and observed_name.rstrip() == name and observed_account == account,
            'Character status identity differs')
    tokens = flags.split()
    require(set(tokens).issubset({'NoConnect', 'InMapXfer'}) and len(tokens) == len(set(tokens)),
            'Unknown or duplicate character status flags')
    require(_ipv4(address), 'Invalid character status endpoint')
    return {'loaded': True, 'connected': 'NoConnect' not in tokens, 'in_map_transfer': 'InMapXfer' in tokens,
            'map_id': int(mapid), 'static_map_id': int(static_mapid), 'address': address}


def connected_on_atlas(status):
    return (isinstance(status, dict) and status.get('loaded') is True and status.get('connected') is True
            and status.get('in_map_transfer') is False and status.get('map_id') == MAP_ID
            and status.get('static_map_id') == MAP_ID)


def _events(events):
    require(isinstance(events, list) and len(events) <= 20000, 'Invalid or oversized bridge event list')
    previous_ms, total = 0, 0
    for sequence, event in enumerate(events, 1):
        require(isinstance(event, dict) and type(event.get('sequence')) is int and event['sequence'] == sequence,
                'Bridge event sequence is incomplete, duplicated or unordered')
        require(type(event.get('elapsed_ms')) is int and event['elapsed_ms'] >= previous_ms,
                'Invalid or decreasing bridge event timing')
        previous_ms = event['elapsed_ms']
        require(all(isinstance(event.get(key), str) and '\0' not in event[key] for key in ('kind', 'value', 'raw')),
                'Malformed bridge event text')
        total += len(event['raw'].encode('utf-8'))
        require(total <= EVENT_LIMIT and len(event['raw'].encode('utf-8')) < 100000,
                'Bridge event capture exceeds bound')
        if event['kind'] not in ('BridgeStarted', 'VersionReply', 'Command'):
            command, separator, value = event['raw'].partition(':')
            require(separator and command.strip().casefold() == event['kind'].casefold() and
                    value.strip() == event['value'], 'Bridge event decoded fields differ from raw evidence')
    return events


def pipe_identity(events, ready, account, expected_name=None, allow_logout_error=False):
    _identity(account, name=expected_name)
    _events(events)
    require(ready is None or isinstance(ready, dict), 'Invalid bridge readiness record')
    if not ready:
        return False
    pid = ready.get('child_pid')
    require(type(pid) is int and 0 < pid <= 0xffffffff and type(ready.get('transport_pid')) is int
            and ready['transport_pid'] == pid and ready.get('format') == 1 and
            all(ready.get(key) is True for key in ('console_attached', 'pipe_pid_verified',
                'protocol_pid_verified', 'initial_snapshot')) and
            type(ready.get('version_requests')) is int and ready['version_requests'] == 1 and
            ready.get('buffer_rows_limit') == 16384 and ready.get('capture_byte_limit') == LOG_LIMIT
            and ready.get('event_byte_limit') == EVENT_LIMIT, 'Bridge readiness identity or capture bounds differ')
    kinds = {kind: [event for event in events if event['kind'] == kind]
             for kind in ('PID', 'AuthName', 'VersionRequest', 'Player', 'MapName', 'Status', 'QuitNow')}
    require(len(kinds['PID']) == 1 and kinds['PID'][0]['value'] == str(pid), 'Protocol PID differs from owned Windows child')
    protocol = [event for event in events if event['kind'] not in ('BridgeStarted', 'VersionReply', 'Command')]
    require(protocol and protocol[0]['kind'] == 'PID', 'Launcher sent evidence before PID identity')
    require(len(kinds['VersionRequest']) == 1, 'Missing or repeated launcher version request')
    require(all(event['value'] == account for event in kinds['AuthName']), 'Launcher account identity differs')
    require(not any(event['value'] == 'CRASH' for event in kinds['Status']), 'TestClient reported CRASH')
    errors = [event for event in kinds['Status'] if event['value'] == 'ERROR']
    if errors:
        require(allow_logout_error and kinds['QuitNow'] and
                all(event['sequence'] > kinds['QuitNow'][0]['sequence'] for event in errors),
                'TestClient reported ERROR before a requested logout')
    require(allow_logout_error or not kinds['QuitNow'], 'TestClient requested premature logout')
    if not (kinds['AuthName'] and kinds['Player'] and kinds['MapName'] and
            any(event['value'] == 'Running' for event in kinds['Status'])):
        return False
    name = kinds['Player'][0]['value']
    _identity(account, name=name)
    require(expected_name is None or name == expected_name, 'Launcher returned a different character name')
    require(all(event['value'] == name for event in kinds['Player']), 'Launcher player identity changed')
    require(all(event['value'].replace('\\', '/').casefold() == MAP_PATH.casefold()
                for event in kinds['MapName']), 'Launcher returned a different map')
    return name


def live_currency_evidence(events, name, account, after_sequence, expected=INFLUENCE):
    _identity(account, name=name)
    _events(events)
    require(type(after_sequence) is int and after_sequence >= 0 and type(expected) is int and expected == INFLUENCE,
            'Unreviewed live currency target or event boundary')
    accepted = []
    for event in events:
        if event['sequence'] <= after_sequence or not event['raw'].startswith('ChatText:conPrintf:0:'):
            continue
        body = event['raw'][len('ChatText:conPrintf:0:'):]
        players = re.findall(r'^\s*Player:\s*([^\r\n]+?)\s*$', body, re.M)
        accounts = re.findall(r'^\s*Login:\s*([^\r\n]+?)\s*$', body, re.M)
        values = re.findall(r'^\s*Current cash:\s*(\d+)\s+\(Influence\)\s*$', body, re.M)
        if not players and not accounts and not values:
            continue
        require(len(players) == len(accounts) == len(values) == 1, 'Malformed or ambiguous live currency diagnostic')
        require(players[0] == name and accounts[0] == account, 'Live currency identifies another character or account')
        if int(values[0]) == expected:
            accepted.append({'player': name, 'account': account, 'influence': expected,
                             'elapsed_ms': event['elapsed_ms'], 'sequence': event['sequence']})
    return accepted[-1] if accepted else False


def accept_sustained_resume(text, events, ready, account, name, identifier, exit_code=None):
    _identity(account, identifier, name)
    require(type(identifier) is int and identifier > 0, 'Character ID must be a positive integer')
    require(exit_code is None, 'Sustained resume client exited before session observation')
    require(not diagnostic_failures(text), 'Resume emitted failure diagnostics')
    require('simulateCharacterCreate' not in text and not re.search(r'Character creation|Create a new character', text, re.I),
            'Resume attempted character creation')
    matches = re.findall(r'^Found character (.+) in slot (\d+)\s*$', text, re.M)
    require(len(matches) == 1 and matches[0][0] == name, 'Exact-name existing character match was not observed')
    slot = int(matches[0][1])
    require(re.search(r'^Resuming character in slot ' + str(slot) + r'\.\.\.', text, re.M) and
            'commReqScene()' in text, 'Resume branch or scene exchange is missing')
    selections = [line for line in text.splitlines() if line.startswith('COH_RESUME_ONLY_SELECTED')]
    require(selections == [f'COH_RESUME_ONLY_SELECTED slot={slot} name={name}'], 'Resume selection lacks exact name and slot')
    require('COH_RESUME_ONLY_MISSING' not in text, 'Positive resume reported a missing character')
    updates = [line for line in text.splitlines() if line.startswith('COH_RESUME_ONLY_SERVER_UPDATE')]
    require(updates == [f'COH_RESUME_ONLY_SERVER_UPDATE id={identifier} name={name}'],
            'Resume lacks one processed server update for original database ID and name')
    require(pipe_identity(events, ready, account, name) == name, 'Resume lacks live player and map pipe identity')
    return {'slot': slot, 'database_id': identifier, 'exact_name': name, 'creation_disabled': True,
            'database_id_source': 'processed MapServer player entity update', 'scene_exchange_observed': True,
            'processed_server_update_for_original_player': True, 'active_gameplay_confirmed': False}


def validate_attributes(attributes):
    require(isinstance(attributes, dict) and 'attributes' in attributes, 'Missing character attribute mapping')
    for table, rows in attributes.items():
        require(isinstance(table, str) and re.fullmatch(r'[a-z_][a-z0-9_]*', table) and isinstance(rows, list),
                'Malformed attribute table')
        require(all(isinstance(row, dict) and set(row) == {'id', 'name'} and type(row['id']) is int and
                    row['id'] > 0 and isinstance(row['name'], str) for row in rows), 'Malformed attribute IDs or names')
        ids = [row['id'] for row in rows]
        require(ids == sorted(set(ids)), 'Duplicate or unordered attribute IDs')
    return attributes


def validate_snapshot(rows, inventory, attributes, account, identifier, name, expected_login_count,
                      expected_influence=INFLUENCE):
    _identity(account, identifier, name)
    require(type(identifier) is int and identifier > 0, 'Character ID must be a positive integer')
    require(type(expected_login_count) is int and expected_login_count in (1, 2), 'Unreviewed LoginCount target')
    require(type(expected_influence) is int and expected_influence == INFLUENCE, 'Unreviewed saved influence target')
    require(isinstance(rows, dict) and set(rows) == set(SELECTED), 'Missing or unexpected selected SQL tables')
    validate_attributes(attributes)
    for table, fields in SELECTED.items():
        columns = set(fields + (('logincount',) if table == 'ents' else ()))
        values = rows[table]
        require(isinstance(values, list) and values and all(isinstance(row, dict) and set(row) == columns
                for row in values), 'Required character rows or selected fields are missing: ' + table)
        require(all(type(row['containerid']) is int and row['containerid'] == identifier for row in values),
                'Parent or child references a different character: ' + table)
        require(all(value is None or type(value) in (str, int, bool) or
                    (type(value) is float and math.isfinite(value)) for row in values for value in row.values()),
                'Malformed selected SQL value: ' + table)
        if table in ('ents', 'ents2'):
            require(len(values) == 1, 'Expected exactly one character row: ' + table)
        if table != 'ents':
            keys = [row['subid'] for row in values]
            require(all(type(key) is int and key >= 0 for key in keys) and keys == sorted(set(keys)),
                    'Invalid, duplicate or unordered child keys: ' + table)
            require(table != 'ents2' or keys == [0], 'Ents2 child must use subid zero')
    parent = rows['ents'][0]
    require(type(parent['authid']) is int and parent['authid'] > 0 and isinstance(parent['authname'], str) and
            parent['authname'].lower() == account.lower() and parent['name'] == name,
            'SQL character or account identity differs from recorded client')
    require(type(parent['influencepoints']) is int and parent['influencepoints'] == expected_influence,
            'Independent SQL influence differs from requested game command')
    require(type(parent['logincount']) is int and parent['logincount'] == expected_login_count,
            'Saved character LoginCount differs from the required session')
    identity = {key: parent[key] for key in IDENTITY_FIELDS}
    require(isinstance(inventory, list) and len(inventory) == 1 and isinstance(inventory[0], dict) and
            set(inventory[0]) == set(IDENTITY_FIELDS + ('logincount',)) and
            all(type(inventory[0][key]) is int for key in ('containerid', 'authid', 'logincount')) and
            inventory == [dict(identity, logincount=expected_login_count)],
            'Disposable database has missing, changed or extra character rows')
    known = {row['id'] for row in attributes['attributes']}
    for table, columns in ATTRIBUTE_FIELDS.items():
        for row in rows[table]:
            for column in columns:
                value = row[column]
                require((table == 'costumeparts' and (value is None or type(value) is int and value == 0)) or
                        (type(value) is int and value > 0 and value in known),
                        'Selected attribute absent from mapping: ' + table + '.' + column)
    result = copy.deepcopy(rows)
    result['ents'][0].pop('logincount')
    return {'identity': identity, 'login_count': expected_login_count, 'rows': result}


def _same(first, second):
    if type(first) is not type(second):
        return False
    if isinstance(first, dict):
        return set(first) == set(second) and all(_same(first[key], second[key]) for key in first)
    if isinstance(first, list):
        return len(first) == len(second) and all(_same(a, b) for a, b in zip(first, second))
    return first == second


def compare_snapshots(before, after, phase):
    require(phase in ('restart', 'second_logout'), 'Unknown saved character comparison phase')
    require(isinstance(before, dict) and isinstance(after, dict) and all(
            set(item) == {'identity', 'login_count', 'rows'} for item in (before, after)), 'Malformed saved snapshots')
    require(_same(before['identity'], after['identity']), 'Character identity changed after ' + phase)
    require(isinstance(before['rows'], dict) and set(before['rows']) == set(SELECTED) and
            _same(before['rows'], after['rows']), 'Selected character rows changed after ' + phase)
    expected = (1, 1) if phase == 'restart' else (1, 2)
    require(type(before['login_count']) is int and type(after['login_count']) is int and
            (before['login_count'], after['login_count']) == expected, 'Unexpected LoginCount progression after ' + phase)
    return {'phase': phase, 'identity_unchanged': True, 'selected_rows_unchanged': True,
            'login_count_before': before['login_count'], 'login_count_after': after['login_count'],
            'row_counts': {table: len(after['rows'][table]) for table in SELECTED}}


def compare_attributes(before, after):
    validate_attributes(before)
    validate_attributes(after)
    require(_same(before, after), 'Attribute mappings changed during persistence experiment')
    return {'unchanged': True, 'row_counts': {table: len(rows) for table, rows in after.items()}}
