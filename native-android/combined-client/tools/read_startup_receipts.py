#!/usr/bin/env python3
"""Bounded offline reader for existing guest startup receipts/JSON-line logs.

Select ZIP members explicitly (at most two levels). Never extract files, print
raw logs, recover omitted private context or infer hits from phase duration.
"""
import argparse
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import sys
import zipfile
import zlib

import analyze_startup_resources as a
base = a.base
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_NESTED = 32 * 1024 * 1024
MAX_DOCUMENT = 2 * 1024 * 1024
MAX_LOG_LINES = 8192
MAX_DIRECTORY = 256 * 1024
EOCD = struct.Struct('<4s4H2IH')
CENTRAL = struct.Struct('<4s6H3I5H2I')
SCHEMA = 'coh-offline-existing-startup-receipts-v1'
UTC = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)')
PIN = re.compile(r'[0-9a-f]{64}')
SCOPES = frozenset(('actual_character_creation_guest', 'actual_character_reopen_guest'))


def digest(raw): return hashlib.sha256(raw).hexdigest()


def utc_ms(value):
    if type(value) is not str or len(value) > 40 or not UTC.fullmatch(value): return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return round(parsed.timestamp() * 1000) if 2000 <= parsed.year <= 2100 else None
    except ValueError: return None


def file_pin(value):
    value = base.obj(value)
    pin = value.get('sha256')
    size = base.number(value.get('bytes'))
    return {'bytes': size, 'sha256': pin} if type(pin) is str and PIN.fullmatch(pin) and size is not None else None


def bounded_read(source, limit):
    raw = source.read(limit + 1)
    base.need(len(raw) <= limit, 'INPUT_SIZE_BOUND')
    return raw


def preflight_zip(source):
    """Admit actual bounded central headers BEFORE ZipFile allocates ZipInfo.

    This deliberately supports ordinary single-disk ZIP only, without ZIP64,
    prepended executables or central-directory signatures. No archive contents
    are decompressed here, and directory metadata is capped at 256 KiB.
    """
    source.seek(0, 2); size = source.tell()
    base.need(EOCD.size <= size <= MAX_ARCHIVE, 'ARCHIVE_SIZE_BOUND')
    tail_size = min(size, EOCD.size + 65535)
    source.seek(size - tail_size); tail = source.read(tail_size)
    base.need(len(tail) == tail_size, 'ARCHIVE_SIZE_CHANGED')
    offset = tail.rfind(b'PK\x05\x06')
    base.need(offset >= 0 and offset + EOCD.size <= len(tail), 'ZIP_END_RECORD')
    end = EOCD.unpack_from(tail, offset)
    _, disk, cd_disk, disk_count, count, cd_bytes, cd_offset, comment = end
    end_position = size - tail_size + offset
    base.need(offset + EOCD.size + comment == len(tail), 'ZIP_END_RECORD')
    base.need(disk == 0 and cd_disk == 0 and disk_count == count, 'MULTIDISK_UNSUPPORTED')
    base.need(count != 0xffff and cd_bytes != 0xffffffff and cd_offset != 0xffffffff
              and (offset < 20 or tail[offset-20:offset-16] != b'PK\x06\x07'), 'ZIP64_UNSUPPORTED')
    base.need(count <= 256, 'DIRECTORY_ENTRY_BOUND')
    base.need(cd_bytes <= MAX_DIRECTORY and cd_offset <= end_position
              and cd_offset + cd_bytes == end_position, 'DIRECTORY_BYTE_BOUND')
    source.seek(cd_offset); directory = source.read(cd_bytes)
    base.need(len(directory) == cd_bytes, 'DIRECTORY_SIZE_CHANGED')
    cursor = actual = 0
    while cursor < len(directory):
        actual += 1; base.need(actual <= 256, 'DIRECTORY_ENTRY_BOUND')
        base.need(cursor + CENTRAL.size <= len(directory), 'DIRECTORY_HEADER')
        header = CENTRAL.unpack_from(directory, cursor)
        base.need(header[0] == b'PK\x01\x02', 'DIRECTORY_HEADER')
        name, extra, note = header[10:13]
        base.need(0 < name <= 240 and extra <= 4096 and note <= 4096, 'DIRECTORY_FIELD_BOUND')
        base.need(header[13] == 0, 'MULTIDISK_UNSUPPORTED')
        base.need(all(header[i] != 0xffffffff for i in (8, 9, 16)), 'ZIP64_UNSUPPORTED')
        end_entry = cursor + CENTRAL.size + name + extra + note
        base.need(end_entry <= len(directory), 'DIRECTORY_HEADER')
        raw_name = directory[cursor + CENTRAL.size:cursor + CENTRAL.size + name]
        base.need(b'\x00' not in raw_name, 'MEMBER_NAME')
        extra_cursor = cursor + CENTRAL.size + name
        extra_end = extra_cursor + extra
        while extra_cursor < extra_end:
            base.need(extra_cursor + 4 <= extra_end, 'DIRECTORY_EXTRA')
            tag, length = struct.unpack_from('<HH', directory, extra_cursor)
            base.need(tag != 1, 'ZIP64_UNSUPPORTED')
            extra_cursor += 4 + length
            base.need(extra_cursor <= extra_end, 'DIRECTORY_EXTRA')
        cursor = end_entry
    base.need(cursor == cd_bytes and actual == count, 'DIRECTORY_COUNT_MISMATCH')
    source.seek(0)


def member_body(source, name, limit):
    preflight_zip(source)
    with zipfile.ZipFile(source) as archive:
        entries = archive.infolist()
        base.need(len(entries) <= 256, 'MEMBER_COUNT_BOUND')
        seen = set(); total = 0
        for entry in entries:
            path = PurePosixPath(entry.filename)
            base.need(0 < len(entry.filename) <= 240 and not path.is_absolute()
                and '\\' not in entry.filename and '\x00' not in entry.filename
                and '..' not in path.parts and len(path.parts) <= 8
                and path.as_posix() == entry.filename.rstrip('/'), 'MEMBER_NAME')
            base.need(entry.filename not in seen, 'DUPLICATE_MEMBER'); seen.add(entry.filename)
            base.need(not stat.S_ISLNK(entry.external_attr >> 16), 'MEMBER_TYPE')
            base.need(not entry.flag_bits & 1, 'ENCRYPTED_MEMBER')
            base.need(entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), 'COMPRESSION_TYPE')
            total += entry.file_size
            base.need(total <= 256 * 1024 * 1024, 'DECLARED_CONTENT_BOUND')
        base.need(name in seen, 'SELECTED_MEMBER_MISSING')
        entry = archive.getinfo(name)
        base.need(not entry.is_dir() and 0 <= entry.file_size <= limit, 'SELECTED_MEMBER_BOUND')
        with archive.open(entry) as selected: raw = bounded_read(selected, limit)
        base.need(len(raw) == entry.file_size, 'MEMBER_SIZE_CHANGED')
        return raw


def read_input(path, members):
    base.need(len(members) <= 2, 'NESTING_BOUND')
    # Outer ZIP hashing streams; only explicitly selected members are inflated.
    with Path(path).open('rb') as source:
        import os
        before = os.fstat(source.fileno())
        limit = MAX_ARCHIVE if members else MAX_DOCUMENT
        base.need(stat.S_ISREG(before.st_mode) and before.st_size <= limit, 'INPUT_SIZE_BOUND')
        sha = hashlib.sha256(); count = 0
        while block := source.read(1024 * 1024):
            count += len(block); base.need(count <= limit, 'INPUT_SIZE_BOUND'); sha.update(block)
        source.seek(0)
        pins = [{'level': 0, 'bytes': count, 'sha256': sha.hexdigest()}]
        if members:
            raw = member_body(source, members[0], MAX_NESTED if len(members) == 2 else MAX_DOCUMENT)
            pins.append({'level': 1, 'bytes': len(raw), 'sha256': digest(raw)})
            if len(members) == 2:
                raw = member_body(io.BytesIO(raw), members[1], MAX_DOCUMENT)
                pins.append({'level': 2, 'bytes': len(raw), 'sha256': digest(raw)})
        else: raw = bounded_read(source, MAX_DOCUMENT)
        after = os.fstat(source.fileno())
        base.need((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                  (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'INPUT_CHANGED')
    return raw, pins


def stage_intervals(stages):
    stages = base.rows(stages, 128)
    out = []
    for row in stages:
        stage = a.enum(row.get('stage'), base.STAGES)
        if stage == 'unknown': continue
        start, end = utc_ms(row.get('started_utc')), utc_ms(row.get('finished_utc'))
        if start is not None and end is not None:
            base.need(0 <= end - start <= 604800000, 'STAGE_CLOCK')
        out.append({'stage': stage, 'started_utc_ms': start, 'finished_utc_ms': end,
            'recorded_wall_interval_ms': end - start if start is not None and end is not None else None,
            'scope': 'recorded_wall_clock_pair_only_not_native_cpu'})
    return out


def cache_outcome(projection):
    data, definitions, beacon = projection['server_data'], projection['definitions'], projection['beacon']
    return {
        'server_data': 'hit' if data['reused'] is True else 'refused' if data['refusal_present'] else 'unknown',
        'definitions': {'installed': 'installed_missing', 'preserved_existing_native_caches': 'preserved',
                        'skipped_native_fallback': 'refused'}.get(definitions['status'], 'unknown'),
        'beacon': {'reused_verified_graph': 'hit', 'installed_verified_graph': 'installed'}.get(beacon['status'], 'unknown')}


def map_rows(value):
    base.need(type(value) is dict and set(value) <= {'1', '5'}, 'MAP_BOUND_OR_ID')
    out = []
    for key, row in sorted(value.items()):
        base.need(type(row) is dict and type(row.get('format')) is int and row['format'] == 1
                  and type(row.get('map_id')) is int and row['map_id'] == int(key), 'MAP_IDENTITY')
        graph = base.obj(row.get('collision_input_proof'))
        projection = a.projected_caches({'atlas_beacon_graph': graph})
        out.append({'map_id': int(key), 'beacon': projection['beacon'],
            'beacon_outcome': cache_outcome(projection)['beacon'],
            'prepared_mapserver': file_pin(row.get('actual_installed_mapserver')),
            'launched_mapserver': file_pin(row.get('actual_launched_mapserver')),
            'source_package_mapserver_pin_equal': base.boolean(row.get('source_package_mapserver_pin_equal')),
            'launched': base.boolean(row.get('launched')),
            'launch_utc_ms': base.number(row.get('launch_utc_ms')),
            'preparation_finished_utc_ms': base.number(row.get('preparation_finished_utc_ms')),
            'preparation_elapsed_seconds': base.seconds(row.get('preparation_elapsed_seconds')),
            'native_ready_verified_reported': base.boolean(row.get('native_ready_verified')),
            'native_ready_elapsed_sampled_upper_bound_seconds': base.seconds(row.get('native_ready_elapsed_seconds')),
            'ready_time_scope': 'sampled_upper_bound_observer_delay_unbounded_not_exact_readiness',
            'source_identities_independently_verified_by_this_reader': False})
    return out


def analyze_document(document):
    # Wrapper interpretation is explicit; wrappers do not confer Android/session acceptance.
    wrapped = False
    if 'guest' in document:
        document = base.obj(document['guest']); wrapped = True
    session = document.get('session_id')
    base.need(base.same_session(session, session), 'RECEIPT_SESSION_REQUIRED')
    if document.get('app_id') == base.APP:
        base.guest_summary(document)
        kind, creation = 'combined_guest_final_receipt', document
        maps = {}
        stages = document.get('stage_history', [])
    elif 'maps' in document:
        base.need(type(document.get('format')) is int and document['format'] == 1, 'MAP_RECEIPT_FORMAT')
        kind, creation = 'standalone_map_startup_observation', {}
        maps = document['maps']; stages = []
    else:
        base.need(document.get('scope') in SCOPES, 'GUEST_SCOPE')
        candidates = [document[k] for k in ('character_creation', 'character_reopen') if k in document]
        base.need(len(candidates) == 1 and type(candidates[0]) is dict, 'CHARACTER_RECEIPT_REQUIRED')
        creation = candidates[0]
        base.need(base.same_session(session, creation.get('session_id')), 'CROSS_SESSION_CREATION')
        kind = 'conventional_guest_report'
        maps = creation.get('map_startup_observation', document.get('map_startup_observation', {}))
        stages = document.get('stages', [])
    projection = a.projected_caches(creation)
    return {'kind': kind, 'wrapper_present': wrapped,
        'session_binding': 'internal_receipt_session_only_not_android_wrapper_acceptance',
        'cache_outcomes': cache_outcome(projection), 'cache_projection': projection,
        'maps': map_rows(maps), 'stage_intervals': stage_intervals(stages),
        'source_report_warm_phase_present': 'warm_schema_restore' in base.obj(creation.get('server_preparation_phase_seconds')),
        'source_report_cold_phase_present': 'cold_server_data_mirror' in base.obj(creation.get('server_preparation_phase_seconds')),
        'native_cache_consumption_proven': False, 'speedup_measured': False}


def analyze_log(raw):
    try: text = raw.decode('utf-8')
    except UnicodeError: raise base.Rejected('LOG_ENCODING') from None
    lines = text.splitlines(); base.need(len(lines) <= MAX_LOG_LINES, 'LOG_LINE_BOUND')
    pending = None; observations = []; ignored = 0; events = 0
    for line in lines:
        base.need(len(line.encode()) <= 16384, 'LOG_LINE_SIZE')
        if not line.startswith('{'): ignored += 1; continue
        try: row = base.parse(line)
        except base.Rejected: ignored += 1; continue
        # Original stdout running events include both Context.stage starts and
        # same-stage progress heartbeats. They are indistinguishable here.
        # Any explicit terminal interruption invalidates an outstanding pair.
        if (row.get('type') in ('error', 'failure', 'cancelled', 'result', 'server_stopped')
                or row.get('status') in ('failed', 'cancelled', 'cleanup_failed', 'stopped', 'interrupted_unverified')):
            pending = None; ignored += 1; continue
        if row.get('type') != 'stage' or type(row.get('stage')) is not str or row['stage'] not in base.STAGES:
            ignored += 1; continue
        timestamp = utc_ms(row.get('time_utc'))
        if timestamp is None: ignored += 1; continue
        events += 1; base.need(events <= 256, 'LOG_EVENT_BOUND')
        stage = row['stage']; status = row.get('status')
        if status == 'running':
            pending = (stage, timestamp)
        elif status == 'passed' and pending is not None and pending[0] == stage:
            base.need(0 <= timestamp - pending[1] <= 604800000, 'STAGE_CLOCK')
            observations.append({'stage': stage, 'started_utc_ms': pending[1],
                'finished_utc_ms': timestamp, 'recorded_wall_interval_ms': timestamp-pending[1],
                'scope': 'latest_explicit_running_to_passed_pair_not_total_stage_duration'})
            pending = None
    return {'kind': 'original_json_line_stage_events', 'session_binding': 'unbound_log_never_joined_to_receipts',
        'events': events, 'ignored_lines': ignored, 'unclosed_stage': pending is not None,
        'stage_intervals': observations, 'cache_outcomes': {'server_data': 'unknown', 'definitions': 'unknown', 'beacon': 'unknown'},
        'scope': 'latest_explicit_running_passed_UTC_pairs_only_not_total_stage_or_native_cpu',
        'running_event_may_be_progress_heartbeat': True, 'speedup_measured': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--member', action='append', default=[], help='Explicit ZIP member; repeat once for nested ZIP')
    parser.add_argument('--json-lines', action='store_true')
    args = parser.parse_args(argv)
    try:
        raw, pins = read_input(args.input, args.member)
        result = analyze_log(raw) if args.json_lines else analyze_document(base.parse(raw))
        output = {'schema': SCHEMA, 'provenance': pins, 'observation': result,
            'runtime_modified': False, 'private_context_recovered_or_exported': False,
            'new_device_execution': False}
    except base.Rejected as error:
        print(json.dumps({'schema': SCHEMA, 'error': str(error)})); return 2
    except (OSError, ValueError, TypeError, KeyError, OverflowError, zipfile.BadZipFile, RuntimeError, zlib.error):
        print(json.dumps({'schema': SCHEMA, 'error': 'INPUT_UNAVAILABLE_OR_INVALID'})); return 2
    print(json.dumps(output, indent=2, sort_keys=True, allow_nan=False)); return 0


if __name__ == '__main__': sys.exit(main())
