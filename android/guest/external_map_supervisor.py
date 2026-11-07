"""On-demand zone requests from the external-maps DbServer.

The DbServer layer `manual_atlas_dbserver_external_maps` (database/external-maps,
patches/external-maps/0001) publishes every map start as `map-<id>-<cookie>.json`
in a directory this supervisor owns, prints one request marker per record, and
keeps the map "starting" exactly as it would for a Launcher.

Each request is read and decided once:

- a map the session flow is starting or running itself is left alone: that
  process registers without a cookie, which the DbServer accepts (dbinit.c);
- with a start policy (the game's own zone travel, `zone_travel.py`), a map the
  policy can serve is started by the owner with the request's cookie
  (`start_arguments`: the record's own game options checked against an
  allowlist); a start that fails or is not ready in time is delinked;
- every other request is delinked (`MapServer.exe -dbquery -delink <id>`), so a
  waiting player is told the map failed and stays where they were, instead of
  waiting on the loading screen. The layer never deletes a static zone that has
  no Launcher (mapxfer.c), and a delink only resets it (freeMapContainer), so
  the zone can be requested again.

Everything here is bounded; anything unexpected is recorded and refused rather
than acted on.
"""
import json
import os
from pathlib import Path
import re
import stat
import time

FORMAT = 1
# App/launch option; the DbServer must also carry the exact external-maps layer.
ENABLE_ENVIRONMENT = 'COH_EXTERNAL_MAPS'
DB_ENVIRONMENT = 'COH_WINE_DB_EXTERNAL_MAPS'
DB_DIRECTORY_ENVIRONMENT = 'COH_WINE_DB_EXTERNAL_MAPS_DIR'
# The overlay's own strings (database/external-maps/overlay/DBServer/src/wine_external_maps.h).
ACK = ('COH_WINE_DB_EXTERNAL_MAPS=1 active: map starts are published to the supervisor; '
       'no Launcher is used')
MARKER = 'COH_WINE_DB_EXTERNAL_MAP_REQUEST_V1'
DIRECTORY_LIMIT = 199          # the DbServer refuses a directory of 200 characters or more
RECORD_BYTES = 8192
MAX_REQUESTS = 64
MAX_DELINKS = 16
MAX_STARTS = 32
MAX_ENTRIES = 256
MARKER_GRACE_SECONDS = 10
DELINK_SECONDS = 90
INT_MAX = 2 ** 31 - 1
REPORT_REQUESTS = 16
REPORT_ANOMALIES = 8

FILE_NAME = re.compile(r'map-([1-9][0-9]{0,9})-([1-9][0-9]{0,9})\.json\Z')
TEMPORARY_NAME = re.compile(r'map-[1-9][0-9]{0,9}-[1-9][0-9]{0,9}\.json\.tmp\Z')
MARKER_LINE = re.compile(r'^' + MARKER + r' map_id=([1-9][0-9]{0,9}) cookie=([1-9][0-9]{0,9}) static=([01])\r?$')
INT_FIELDS = ('format', 'sequence', 'map_id', 'cookie', 'base_map_id', 'is_static', 'transient',
              'dont_auto_start', 'preload_transient', 'db_process_id')
FLAG_FIELDS = ('is_static', 'transient', 'dont_auto_start', 'preload_transient')
STRING_LIMITS = {'map_name': 1023, 'mission_info': 1023, 'command': 4096}

# launcherCommStartProcess: ".\mapserver.exe -db <host> -udp -1 -map_id N -launcher -cookie C" + options.
# Game options are kept; process and infrastructure options are the supervisor's own.
PASS_FLAGS = frozenset({'-transient', '-preloadtransient', '-completebrokentasks'})
PASS_INTEGER = frozenset({'-aggrocap', '-targetcapmode', '-clientlogouttime', '-maxLevel',
                          '-maxCoHLevel', '-maxCoVLevel'})
PASS_DECIMAL = frozenset({'-xpscale', '-influencescale', '-prestigescale', '-aescale',
                          '-aeinfluencescale', '-aeprestigescale', '-ticketscale'})
PASS_PATTERN = {'-blockedmapkeys': re.compile(r'[A-Za-z0-9_]+(,[A-Za-z0-9_]+)*\Z'),
                '-WeeklyTFTokens': re.compile(r'-?[0-9]{1,10}(:[A-Za-z0-9_.]{1,64}){1,32}\Z')}
# The shipped servers.cfg adds MapServerParams "-productionmode" and, through
# servercfg.c, -idleExitTimeout 30 (MapserverIdleExit), -idleUpkeep 30
# (MapserverIdleUpkeep) and -MARTY_enabled (MARTYEnabled); -IsBetaShard and
# -dailyUpkeep A B are its other additions. The session's own MapServers
# (Atlas, King's Row) run without any of them, and the owner decides when a zone
# stops (its own -idleExitTimeout 0 and eviction), so a started zone drops them.
DROP_FLAGS = frozenset({'-nostats', '-diffdebug', '-cod', '-productionmode', '-MARTY_enabled', '-IsBetaShard'})
DROP_VALUE = frozenset({'-assertmode', '-logserver', '-beaconusemasterserver', '-idleExitTimeout', '-idleUpkeep'})
INTEGER = re.compile(r'-?[0-9]{1,9}\Z')
DECIMAL = re.compile(r'-?[0-9]{1,6}(\.[0-9]{1,6})?\Z')


class RequestRefused(ValueError):
    def __init__(self, reason, detail=None):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


def refuse(condition, reason):
    if not condition:
        raise RequestRefused(reason)


def parse_record(data):
    """One request record, exactly as the overlay writes it, or RequestRefused."""
    refuse(isinstance(data, bytes) and 2 < len(data) <= RECORD_BYTES and data.endswith(b'}\n'), 'record_bounds')
    try:
        text = data.decode('ascii')
    except UnicodeDecodeError:
        raise RequestRefused('non_ascii') from None

    def pairs(items):
        keys = [key for key, _ in items]
        refuse(len(keys) == len(set(keys)), 'duplicate_field')
        return dict(items)

    def no_decimal(_):
        raise RequestRefused('decimal_field')

    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_float=no_decimal, parse_constant=no_decimal)
    except ValueError as failure:
        if isinstance(failure, RequestRefused):
            raise
        raise RequestRefused('not_json') from None
    refuse(isinstance(value, dict) and set(value) == set(INT_FIELDS) | set(STRING_LIMITS), 'fields')
    for key in INT_FIELDS:
        refuse(type(value[key]) is int and 0 <= value[key] <= INT_MAX, 'integer_' + key)
    for key, limit in STRING_LIMITS.items():
        refuse(type(value[key]) is str and len(value[key]) <= limit, 'string_' + key)
    refuse(value['format'] == FORMAT, 'format')
    for key in ('sequence', 'map_id', 'cookie', 'db_process_id'):
        refuse(value[key] > 0, 'integer_' + key)
    for key in FLAG_FIELDS:
        refuse(value[key] in (0, 1), 'flag_' + key)
    return value


def command_options(record):
    """The record command's game options (kept) and the ones the supervisor replaces."""
    tokens = record['command'].split(' ')
    refuse(all(tokens), 'command_shape')
    prefix = ['.\\mapserver.exe', '-db', None, '-udp', '-1', '-map_id', str(record['map_id']),
              '-launcher', '-cookie', str(record['cookie'])]
    refuse(len(tokens) >= len(prefix) and all(want is None or got == want for got, want in zip(tokens, prefix)),
           'command_prefix')
    kept, dropped, index = [], [], len(prefix)
    while index < len(tokens):
        option = tokens[index]
        value = tokens[index + 1] if index + 1 < len(tokens) else None
        if option in PASS_FLAGS:
            refuse(option not in kept, 'repeated_option')
            kept.append(option); index += 1
        elif option in DROP_FLAGS:
            dropped.append(option); index += 1
        elif option in PASS_INTEGER:
            refuse(value is not None and INTEGER.match(value), 'option_value')
            kept += [option, value]; index += 2
        elif option in PASS_DECIMAL:
            refuse(value is not None and DECIMAL.match(value), 'option_value')
            kept += [option, value]; index += 2
        elif option in PASS_PATTERN:
            refuse(value is not None and PASS_PATTERN[option].match(value), 'option_value')
            kept += [option, value]; index += 2
        elif option in DROP_VALUE:
            refuse(value is not None, 'option_value')
            dropped.append(option); index += 2
        elif option == '-dailyUpkeep':
            later = tokens[index + 2] if index + 2 < len(tokens) else None
            refuse(value is not None and later is not None and INTEGER.match(value) and INTEGER.match(later),
                   'option_value')
            dropped.append(option); index += 3
        elif option == '-locale':
            # Always sent; the device runs English (0). Another language is not
            # set up here, and -locale writes the Wine registry (svr_init.c).
            refuse(value == '0', 'unsupported_locale')
            dropped.append(option); index += 2
        else:
            # Name the option in the report (bounded, printable) so the next one is a one-line fix.
            raise RequestRefused('unrecognized_option', re.sub(r'[^-A-Za-z0-9_.]', '?', option)[:40])
    refuse(('-transient' in kept) == bool(record['transient']), 'transient_mismatch')
    refuse(('-preloadtransient' in kept) == bool(record['preload_transient']), 'preload_mismatch')
    return {'kept': kept, 'dropped': dropped}


def start_arguments(record, port, options):
    """MapServer arguments for this request: the owner adds its own memory and link options."""
    refuse(type(port) is int and 1024 < port < 65536, 'port')
    return ['-nogui', '-db', '127.0.0.1', '-nostats', '-udp', str(port), '-tcp', '0',
            '-map_id', str(record['map_id']), '-cookie', str(record['cookie']), '-donotautogroup',
            *options['kept']]


class ExternalMapSupervisor:
    def __init__(self, directory, *, session_maps, clock=time.monotonic, utc_ms=None, policy=None):
        self.directory = Path(directory)
        # A fixed set, or a callable answering for the maps the session flow
        # is starting or running right now (the game's own zone travel).
        self.session_maps = session_maps if callable(session_maps) else frozenset(session_maps)
        # policy(record, options) -> ('start', details) or ('delink', reason).
        self.policy = policy
        self.starts = []
        self.clock = clock
        self.utc_ms = utc_ms or (lambda: int(time.time() * 1000))
        self.requests = {}
        self.order = []
        self.unconfirmed = {}
        self.foreign = set()
        self.anomalies = []
        self.delinks = []
        self.db_process_id = None
        self.last_sequence = 0
        self.ack_observed = False
        self.found = {}
        self.console_offset = 0
        self.stopped = None
        self.counts = {'requests': 0, 'session_flow': 0, 'delink': 0, 'refused': 0,
                       'delink_finished': 0, 'delink_failed': 0,
                       'start': 0, 'started': 0, 'start_ready': 0, 'start_failed': 0}

    @classmethod
    def create(cls, parent, name, *, session_maps, **keywords):
        """A fresh private request directory (never reused)."""
        directory = Path(parent) / name
        refuse(not os.path.lexists(directory), 'stale_directory')
        directory.mkdir(mode=0o700)
        return cls(directory, session_maps=session_maps, **keywords)

    def anomaly(self, reason, **fields):
        self.anomalies.append(dict(fields, reason=reason, utc_ms=self.utc_ms()))
        del self.anomalies[:-REPORT_ANOMALIES]

    def stop(self, reason):
        if self.stopped is None:
            self.stopped = reason
            self.delinks.clear()
            self.starts.clear()

    def session_owned(self, map_id):
        return self.session_maps(map_id) if callable(self.session_maps) else map_id in self.session_maps

    def markers(self, console):
        """Acknowledgement and request markers from complete new console lines."""
        end = console.rfind('\n') + 1
        if end < self.console_offset:
            self.stop('console_rewound')
            return self.found
        for line in console[self.console_offset:end].splitlines():
            if line.rstrip('\r') == ACK:
                if self.ack_observed:
                    self.stop('repeated_acknowledgement')
                self.ack_observed = True
                continue
            match = MARKER_LINE.match(line)
            if match is None:
                continue
            key = (int(match.group(1)), int(match.group(2)))
            if key in self.found:
                self.stop('repeated_marker')
            if not self.ack_observed:
                self.stop('marker_without_acknowledgement')
            self.found[key] = int(match.group(3))
        self.console_offset = end
        return self.found

    def entries(self):
        names = []
        with os.scandir(self.directory) as listing:
            for entry in listing:
                names.append(entry.name)
                if len(names) > MAX_ENTRIES:
                    self.stop('directory_entries')
                    return []
        return sorted(names)

    def read(self, name):
        path = self.directory / name
        info = os.lstat(path)
        refuse(stat.S_ISREG(info.st_mode) and info.st_size <= RECORD_BYTES, 'not_regular_file')
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(descriptor, 'rb') as stream:
            return stream.read(RECORD_BYTES + 1)

    def poll(self, console, now=None):
        """New requests, decided once each; returns the entries added by this poll."""
        if self.stopped is not None:
            return []
        now = self.clock() if now is None else now
        markers = self.markers(console)
        if self.stopped is not None:
            return []
        parsed = []
        for name in self.entries():
            if TEMPORARY_NAME.match(name):
                continue
            match = FILE_NAME.match(name)
            if match is None:
                if name not in self.foreign:
                    self.foreign.add(name)
                    self.anomaly('foreign_entry', name=name[:80])
                continue
            key = (int(match.group(1)), int(match.group(2)))
            if key in self.requests:
                continue
            if key not in markers:
                first = self.unconfirmed.setdefault(key, now)
                if now - first > MARKER_GRACE_SECONDS:
                    # Not announced by the owned DbServer: never acted on.
                    self.unconfirmed.pop(key)
                    self.requests[key] = self.entry(key, None, 'refused', 'unconfirmed_request')
                    self.order.append(key)
                    self.counts['refused'] += 1
                    self.anomaly('unconfirmed_request', map_id=key[0], cookie=key[1])
                continue
            self.unconfirmed.pop(key, None)
            try:
                record = parse_record(self.read(name))
                refuse((record['map_id'], record['cookie']) == key, 'name_mismatch')
                refuse(record['is_static'] == markers[key], 'marker_mismatch')
                parsed.append((record['sequence'], key, record, None))
            except (RequestRefused, OSError) as failure:
                reason = failure.reason if isinstance(failure, RequestRefused) else 'unreadable'
                parsed.append((0, key, None, reason))
        added = []
        for _, key, record, reason in sorted(parsed, key=lambda item: (item[0], item[1])):
            if self.stopped is not None:
                break
            if len(self.requests) >= MAX_REQUESTS:
                self.stop('request_budget')
                break
            entry = self.decide(key, record, reason)
            self.requests[key] = entry
            self.order.append(key)
            added.append(entry)
        return added

    def decide(self, key, record, reason):
        """The map id and cookie come from the owned DbServer's own marker line."""
        self.counts['requests'] += 1
        if record is not None:
            if self.db_process_id is None:
                self.db_process_id = record['db_process_id']
            if record['db_process_id'] != self.db_process_id:
                self.counts['refused'] += 1
                self.anomaly('other_dbserver', map_id=key[0], cookie=key[1])
                self.stop('other_dbserver')
                return self.entry(key, record, 'refused', 'other_dbserver')
            if record['sequence'] <= self.last_sequence:
                reason = 'sequence_regressed'
            else:
                self.last_sequence = record['sequence']
        if self.session_owned(key[0]):
            # Never delink a map the session flow may be starting itself.
            self.counts['session_flow'] += 1
            return self.entry(key, record, 'session_flow', reason or 'started_by_session_flow')
        options = refused = None
        if reason is None:
            try:
                options = command_options(record)
                reason = 'zone_not_served_yet'
            except RequestRefused as failure:
                reason, refused = failure.reason, failure.detail
        if reason == 'zone_not_served_yet' and self.policy is not None:
            decision, detail = self.policy(record, options)
            if decision == 'start':
                entry = self.entry(key, record, 'start', 'served', options)
                entry['plan'] = detail
                if self.counts['start'] >= MAX_STARTS:
                    self.anomaly('start_budget', map_id=key[0], cookie=key[1])
                    return self.schedule_delink(key, entry, 'start_budget')
                self.counts['start'] += 1
                self.starts.append(key)
                return entry
            reason = detail
        elif reason != 'zone_not_served_yet':
            self.anomaly(reason, map_id=key[0], cookie=key[1])
        entry = self.entry(key, record, 'delink', reason, options)
        if refused is not None:
            entry['refused_option'] = refused
        return self.schedule_delink(key, entry, reason)

    def schedule_delink(self, key, entry, reason):
        entry.update(decision='delink', reason=reason)
        if self.counts['delink'] >= MAX_DELINKS:
            self.stop('delink_budget')
            entry['decision'] = 'refused'
            self.counts['refused'] += 1
            return entry
        self.counts['delink'] += 1
        self.delinks.append(key)
        return entry

    def entry(self, key, record, decision, reason, options=None):
        value = {'map_id': key[0], 'cookie': key[1], 'decision': decision, 'reason': reason,
                 'seen_utc_ms': self.utc_ms()}
        if record is not None:
            value.update(sequence=record['sequence'], base_map_id=record['base_map_id'],
                         map_name=record['map_name'][-120:],
                         **{key: record[key] for key in FLAG_FIELDS})
        if options is not None:
            value['options'] = options
        return value

    def next_delink(self):
        if self.stopped is not None or not self.delinks:
            return None
        return self.requests[self.delinks.pop(0)]

    def next_start(self):
        if self.stopped is not None or not self.starts:
            return None
        return self.requests[self.starts.pop(0)]

    def start_launched(self, entry, **fields):
        entry['start'] = dict(fields, launched_utc_ms=self.utc_ms())
        self.counts['started'] += 1

    def start_ready(self, entry, *, elapsed_seconds):
        entry['start'].update(ready=True, ready_seconds=round(elapsed_seconds, 3), ready_utc_ms=self.utc_ms())
        self.counts['start_ready'] += 1

    def start_failed(self, entry, reason, *, elapsed_seconds=None):
        """A start that could not be made or was not ready in time: delink it."""
        start = entry.setdefault('start', {})
        start.update(ready=False, failure=str(reason)[:160], failed_utc_ms=self.utc_ms())
        if elapsed_seconds is not None:
            start['failed_seconds'] = round(elapsed_seconds, 3)
        self.counts['start_failed'] += 1
        key = (entry['map_id'], entry['cookie'])
        if self.stopped is None:
            self.schedule_delink(key, entry, 'start_failed')

    def delink_finished(self, entry, *, exit_code, elapsed_seconds, timed_out=False):
        passed = exit_code == 0 and not timed_out
        entry['delink'] = {'exit_code': exit_code, 'timed_out': timed_out, 'passed': passed,
                           'elapsed_seconds': round(elapsed_seconds, 3), 'finished_utc_ms': self.utc_ms()}
        self.counts['delink_finished' if passed else 'delink_failed'] += 1
        if not passed:
            self.stop('delink_failed')

    def report(self):
        return {'format': FORMAT, 'directory': self.directory.name, 'acknowledgement_observed': self.ack_observed,
                'db_process_id': self.db_process_id, 'stopped': self.stopped, 'counts': dict(self.counts),
                'session_maps': 'dynamic' if callable(self.session_maps) else sorted(self.session_maps),
                'map_starts_executed': self.counts['started'] > 0,
                'requests': [self.requests[key] for key in self.order[-REPORT_REQUESTS:]],
                'anomalies': list(self.anomalies)}
