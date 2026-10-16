#!/usr/bin/env python3
"""Read a Combined export offline; emit only bounded allowlisted observations.

No extraction, server execution, input modification, session IDs, arbitrary
strings, command lines, accounts, paths or packet bodies enter the output.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import zipfile
import zlib

APP = 'org.coh.nativecombined'
LIMIT = 2 * 1024 * 1024
ARCHIVE_LIMIT = 16 * 1024 * 1024
MAX_NUMBER = 1 << 50
SESSION = re.compile(r'[0-9a-f]{32}')
MEMBERS = frozenset(('combined-report.json', 'combined-server-latest-report.json',
    'previous-session-combined-server-latest-report.json',
    'combined-server-previous-attempts.json', 'native-client-report.json',
    'previous-app-native-client-report.json'))
STAGES = frozenset(('guest_starting', 'server_memory_admission',
    'prepare_immutable_server_inputs', 'preflight_local_server_ports',
    'server_only_input_admission', 'prepare_private_server_inputs',
    'isolated_required_geometry_preparation', 'persistent_server_profile',
    'postgres_native_combined', 'preflight_selected_map_port',
    'prepare_owned_presentation_endpoint', 'presentation_display',
    'wine_initialization', 'local_login_odbc', 'local_dbserver_startup',
    'local_atlas_startup', 'local_kings_row_startup', 'logical_profile_import',
    'server_running_manual_native_client'))
PHASES = frozenset(('base_schema_and_native_runtime', 'required_original_geometry',
    'native_dependencies_and_manual_atlas', 'server_data_cache_checkout',
    'cold_server_data_mirror', 'cold_server_data_receipt_seal', 'warm_schema_restore',
    'prepared_server_definition_caches', 'server_fx_catalog', 'server_animation_pack',
    'atlas_beacon_graph'))
MEMORY_FIELDS = ('samples', 'invalid_samples', 'pressure_samples',
    'minimum_system_headroom_bytes', 'minimum_java_heap_headroom_bytes',
    'sample_interval_ms', 'retained_sample_limit', 'last_elapsed_ms')
RESOURCE_FIELDS = ('rss_kib', 'peak_rss_kib', 'children_peak_rss_kib',
    'cgroup_current_bytes', 'cgroup_max_bytes', 'cgroup_oom_kill_count')
CLEANUP_FIELDS = ('postgres_graceful', 'wine_prefix_stopped',
    'owned_processes_reaped', 'presentation_socket_removed')


class Rejected(ValueError):
    pass


def need(condition, code):
    if not condition:
        raise Rejected(code)


def number(value):
    return value if type(value) is int and 0 <= value <= MAX_NUMBER else None


def seconds(value):
    return value if type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 604800 else None


def boolean(value):
    return value if type(value) is bool else None


def obj(value):
    return value if type(value) is dict else {}


def rows(value, maximum):
    need(type(value) is list and len(value) <= maximum, 'ARRAY_BOUND_OR_TYPE')
    need(all(type(row) is dict for row in value), 'ROW_TYPE')
    return value


def pairs(values):
    out = {}
    for key, value in values:
        need(key not in out, 'DUPLICATE_JSON_KEY')
        out[key] = value
    return out


def parse(raw):
    def constant(_):
        raise Rejected('NONFINITE_JSON')
    try:
        out = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as error:
        if isinstance(error, Rejected):
            raise
        raise Rejected('INVALID_JSON') from None
    need(type(out) is dict, 'DOCUMENT_TYPE')
    pending, count = [(out, 0)], 0
    while pending:
        node, depth = pending.pop()
        count += 1
        need(depth <= 32 and count <= 100000, 'JSON_STRUCTURE_BOUND')
        if type(node) is dict:
            pending.extend((v, depth + 1) for v in node.values())
        elif type(node) is list:
            pending.extend((v, depth + 1) for v in node)
    return out


def same_session(left, right):
    return type(left) is str and SESSION.fullmatch(left) is not None and left == right


def guest_matches(guest, session):
    return (guest.get('app_id') == APP and type(guest.get('format')) is int
            and guest['format'] == 1 and same_session(session, guest.get('session_id')))


def read_archive(path):
    # File descriptors stay read-only and a strict read limit bounds races/growth.
    with Path(path).open('rb') as source:
        raw = source.read(ARCHIVE_LIMIT + 1)
    need(len(raw) <= ARCHIVE_LIMIT, 'ARCHIVE_SIZE_BOUND')
    docs, provenance = {}, []
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            need(len(entries) <= 16, 'MEMBER_COUNT_BOUND')
            seen, total = set(), 0
            for entry in entries:
                name = entry.filename
                need(name not in seen, 'DUPLICATE_MEMBER')
                seen.add(name)
                need(name in MEMBERS and PurePosixPath(name).name == name
                     and '\\' not in name and '\x00' not in name, 'MEMBER_NAME')
                mode = entry.external_attr >> 16
                need(not stat.S_ISLNK(mode) and not entry.is_dir(), 'MEMBER_TYPE')
                need(not entry.flag_bits & 1, 'ENCRYPTED_MEMBER')
                need(entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), 'COMPRESSION_TYPE')
                total += entry.file_size
                need(0 <= entry.file_size <= LIMIT and total <= 8 * LIMIT, 'MEMBER_SIZE_BOUND')
                with archive.open(entry) as member:
                    body = member.read(LIMIT + 1)
                need(len(body) == entry.file_size and len(body) <= LIMIT, 'MEMBER_SIZE_CHANGED')
                # Native payload is deliberately neither parsed nor summarized.
                if name not in ('native-client-report.json', 'previous-app-native-client-report.json'):
                    docs[name] = parse(body)
                provenance.append({'member': name, 'bytes': len(body),
                                   'sha256': hashlib.sha256(body).hexdigest()})
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, EOFError, zlib.error):
        raise Rejected('INVALID_ARCHIVE') from None
    need('combined-report.json' in docs, 'CURRENT_APP_MISSING')
    return docs, {'archive_bytes': len(raw), 'archive_sha256': hashlib.sha256(raw).hexdigest(),
                  'members': provenance}


def app_summary(app):
    need(app.get('schema') == 'coh-native-combined-app-v1' and app.get('package') == APP, 'APP_SCHEMA')
    server = obj(app.get('server'))
    stages = rows(server.get('stages', []), 64)
    normalized, previous = [], -1
    for row in stages:
        elapsed = number(row.get('elapsed_ms'))
        need(elapsed is not None and elapsed >= previous, 'STAGE_CLOCK')
        previous = elapsed
        normalized.append({'stage': row.get('stage') if type(row.get('stage')) is str and row['stage'] in STAGES else 'unknown_stage',
                           'entered_ms': elapsed, 'next_boundary_delta_ms': None})
    for i in range(len(normalized) - 1):
        normalized[i]['next_boundary_delta_ms'] = normalized[i + 1]['entered_ms'] - normalized[i]['entered_ms']
    ready = [row['entered_ms'] for row in normalized if row['stage'] == 'server_running_manual_native_client']
    need(len(ready) <= 1, 'MULTIPLE_READY_BOUNDARIES')
    memory = obj(app.get('server_memory'))
    resources = rows(app.get('guest_resources', []), 32)
    measured = {}
    for field in RESOURCE_FIELDS:
        values = [number(row.get(field)) for row in resources]
        values = [v for v in values if v is not None]
        measured[field + '_sample_max'] = max(values) if values else None
    exits = rows(app.get('android_process_exits', []), 8)
    phase = server.get('phase')
    return {
        'version_code': number(app.get('version_code')),
        'phase': phase if type(phase) is str and phase in ('ready', 'starting', 'stopped', 'failed', 'cleanup_failed') else 'unknown',
        'ready': boolean(server.get('ready')),
        'owned_process_alive': boolean(server.get('owned_process_alive')),
        'observed_elapsed_ms': number(server.get('elapsed_ms')),
        'ready_boundary_ms': ready[0] if ready else None,
        'stages': normalized,
        'memory': {**{k: number(memory.get(k)) for k in MEMORY_FIELDS},
                   'admitted': boolean(memory.get('admitted')),
                   'stop_requested': boolean(memory.get('stop_requested'))},
        'guest_resources': {'retained_boundary_samples': len(resources), **measured,
            'scope': 'self_and_reaped_child_high_water_observations_not_concurrent_process_tree_peak'},
        'android_exit_history': {'records': len(exits),
            'reason_3_records': sum(type(e.get('reason')) is int and e['reason'] == 3 for e in exits),
            'temporal_attribution': 'unknown_without_bound_wall_clock_origin',
            'allocation_cause_established': False}}


def guest_summary(guest):
    need(guest_matches(guest, guest.get('session_id')), 'GUEST_SCHEMA')
    phases = obj(guest.get('server_preparation_phase_seconds'))
    timed = {k: seconds(phases[k]) for k in sorted(PHASES & phases.keys())}
    need(all(v is not None for v in timed.values()), 'PREPARATION_TIME')
    cold, warm = 'cold_server_data_mirror' in timed, 'warm_schema_restore' in timed
    classification = ('cold_mirror_observed' if cold else 'warm_schema_restore_observed') if cold != warm else 'unknown'
    cleanup = obj(guest.get('cleanup'))
    geometry = obj(guest.get('geometry_preparation'))
    processes = rows(guest.get('processes', []), 512)
    output_bytes = [number(row.get('output_bytes')) for row in processes]
    return {'cache_classification': classification, 'preparation_seconds': timed,
        'cleanup': {k: boolean(cleanup.get(k)) for k in CLEANUP_FIELDS},
        'cleanup_complete': boolean(guest.get('cleanup_complete')),
        'profile_preserved': boolean(guest.get('profile_preserved')),
        'geometry': {k: number(geometry.get(k)) for k in
            ('worker_peak_rss_kib', 'parent_rss_kib_before', 'parent_rss_kib_after', 'input_files_checked')},
        'process_records': len(processes),
        'recorded_output_bytes': sum(output_bytes) if all(v is not None for v in output_bytes) else None}


def analyze(docs, provenance=None):
    app = docs['combined-report.json']
    current = app_summary(app)
    session = obj(app.get('server')).get('session_id')
    need(same_session(session, session), 'CURRENT_SESSION_ID')
    current_guests, historical_guests = [], []
    for name in ('combined-server-latest-report.json', 'previous-session-combined-server-latest-report.json'):
        guest = docs.get(name)
        if guest is not None:
            need(guest_matches(guest, guest.get('session_id')), 'GUEST_SCHEMA')
            (current_guests if guest_matches(guest, session) else historical_guests).append(guest)
    need(len(current_guests) <= 1, 'MULTIPLE_CURRENT_GUESTS')
    current['guest_detail'] = guest_summary(current_guests[0]) if current_guests else None
    current['cache_classification'] = current['guest_detail']['cache_classification'] if current_guests else 'unknown'
    history = obj(docs.get('combined-server-previous-attempts.json'))
    attempts = rows(history.get('attempts', []), 4)
    summaries = []
    for index, attempt in enumerate(attempts):
        old_app, guest = obj(attempt.get('app')), obj(attempt.get('guest'))
        old_session = obj(old_app.get('server')).get('session_id')
        need(same_session(old_session, attempt.get('session_id')), 'HISTORICAL_SESSION_ID')
        need(not same_session(old_session, session), 'CURRENT_IN_HISTORY')
        summary = app_summary(old_app)
        summary['history_index'] = index
        summary['guest_detail'] = guest_summary(guest) if guest_matches(guest, old_session) else None
        summaries.append(summary)
    return {'schema': 'coh-offline-startup-analysis-v1',
        'provenance': provenance,
        'current': current,
        'historical_attempts': summaries,
        'standalone_historical_guest_count': len(historical_guests),
        'standalone_historical_guest_matches_attempt': [
            any(g == obj(a.get('guest')) for a in attempts) for g in historical_guests],
        'interpretation': {'age_fields_used_as_stage_duration': False,
            'current_cold_warm_inferred_from_historical_receipt': False,
            'whole_server_peak_memory_established': False,
            'android_kill_prevention_established': False,
            'runtime_modified': False}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('export_zip', type=Path)
    args = parser.parse_args(argv)
    try:
        docs, provenance = read_archive(args.export_zip)
        result = analyze(docs, provenance)
    except Rejected as error:
        print(json.dumps({'schema': 'coh-offline-startup-analysis-v1', 'error': str(error)}))
        return 2
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        print(json.dumps({'schema': 'coh-offline-startup-analysis-v1', 'error': 'INPUT_UNAVAILABLE_OR_INVALID'}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
