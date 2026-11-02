#!/usr/bin/env python3
"""Extract existing Thor report startup observations; does not decide acceptance."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

MAX_JSON = 8 * 1024**2
MAX_GUEST_ZIP = 260 * 1024**2  # ClientRuntime's production guest-archive bound.
MAX_CONSOLE = 16 * 1024**2
PREFIX = 'ARMPORT_SERVER_STARTUP_V1'
CONSOLE = re.compile(r'client-evidence/(?:character-atlas|character-zoning-map-[15])-console\.txt\Z')
NATIVE = re.compile(r'ARMPORT_SERVER_STARTUP_V1 status=ok map_id=(-?\d+) pid=(\d+) '
    r'sequence=(\d+) phase=([a-z_]+) elapsed_ms=(\d+(?:\.\d+)?) phase_ms=(\d+(?:\.\d+)?) '
    r'scope=main_entry_to_checkpoint(?:\s|$)')
RESULT_KEYS = ('status', 'passed', 'failures', 'cleanup', 'cleanup_complete', 'cleanup_verified',
    'cleanup_blocked', 'cancelled', 'committed_save_observed', 'character_reopen_verified',
    'qualification_gates', 'verified', 'committed_sql_verified', 'requested_logout_observed',
    'disconnected_before_sql', 'forced_stop_before_save', 'reopen_verified', 'gameplay_verified')


def member(archive, name, maximum):
    matches = [row for row in archive.infolist() if row.filename == name]
    if len(matches) != 1 or not 0 < matches[0].file_size <= maximum:
        raise ValueError('Missing, duplicate or oversized member: ' + name)
    return matches[0]


def document(archive, name):
    value = json.loads(archive.read(member(archive, name, MAX_JSON)))
    if not isinstance(value, dict):
        raise ValueError('Report is not an object: ' + name)
    return value


def select_result(value):
    return {key: value[key] for key in RESULT_KEYS if key in value}


ANDROID_DURATIONS = {
    'service_receipt_to_map_ready_seconds': ('service_receipt_elapsed_realtime_ms', 'map_ready_receipt_elapsed_realtime_ms'),
    'ui_action_to_map_ready_seconds': ('ui_action_elapsed_realtime_ms', 'map_ready_receipt_elapsed_realtime_ms'),
    'service_receipt_to_client_world_ready_seconds': ('service_receipt_elapsed_realtime_ms', 'client_world_ready_receipt_elapsed_realtime_ms'),
    'ui_action_to_client_world_ready_seconds': ('ui_action_elapsed_realtime_ms', 'client_world_ready_receipt_elapsed_realtime_ms'),
}


def android_clock_consistent(timing, session):
    """Check only the stored Android clock/event; never combine guest or QPC points."""
    if (type(timing.get('format')) is not int or timing['format'] != 1 or timing.get('clock') != 'android_elapsed_realtime_milliseconds'
            or timing.get('clock_valid') is not True or timing.get('includes_system_suspend') is not True):
        return False
    ui, service = timing.get('ui_action_elapsed_realtime_ms'), timing.get('service_receipt_elapsed_realtime_ms')
    if ui is not None and (type(ui) is not int or type(service) is not int or not 0 <= ui <= service):
        return False
    ready, world = timing.get('map_ready_receipt_elapsed_realtime_ms'), timing.get('client_world_ready_receipt_elapsed_realtime_ms')
    if world is not None and (type(world) is not int or type(ready) is not int or world < ready):
        return False
    for key, (start_key, end_key) in ANDROID_DURATIONS.items():
        value, start, end = timing.get(key), timing.get(start_key), timing.get(end_key)
        if value is None:
            continue
        if (type(value) not in (int, float) or not math.isfinite(value) or value < 0
                or type(start) is not int or type(end) is not int or not 0 <= start <= end
                or abs(value - (end - start) / 1000) > 0.000001):
            return False
    if timing.get('service_receipt_to_map_ready_seconds') is None:
        return False
    event = timing.get('map_ready_event')
    return (isinstance(event, dict) and isinstance(session, str) and re.fullmatch(r'[0-9a-f]{32}', session) is not None
        and event.get('type') == 'map_server_ready_observed' and type(event.get('format')) is int and event['format'] == 1
        and event.get('session_id') == session and event.get('request_kind') == 'initial_guest_service_request'
        and 'epoch' in event and event['epoch'] is None and event.get('destination_already_resident') is False
        and type(event.get('map_id')) is int and event['map_id'] in (1, 5)
        and event.get('readiness_proof') == 'existing_owned_completed_tick_and_DbServer_endpoint_status'
        and event.get('process_spawn_observed') is True and event.get('native_ready_observed') is True)


def owned_memory_rows(guest, result):
    # Normal reports alias these maps at the root and under character_*.
    # Prefer the character location; retain the root for interrupted early state.
    seen = set()
    sources = [(key + '.map_startup_observation', value.get('map_startup_observation'))
        for key in ('character_creation', 'character_reopen')
        if isinstance((value := guest.get(key)), dict)]
    sources.append(('map_startup_observation', guest.get('map_startup_observation')))
    for source, maps in sources:
        if not isinstance(maps, dict):
            continue
        for map_id, row in maps.items():
            if not isinstance(row, dict) or not isinstance(row.get('owned_launch_memory_at_first_native_ready'), dict):
                continue
            observation = row['owned_launch_memory_at_first_native_ready']
            identity = (str(map_id), json.dumps(observation, sort_keys=True))
            if identity in seen:
                continue
            seen.add(identity)
            result['owned_launch_memory_rows'].append({'report_key': source, 'map_id': map_id,
                'observation': observation})


def read_guest(archive, result, *, read_latest=True):
    latest = None
    if read_latest:
        try:
            latest = document(archive, 'latest-report.json')
        except (ValueError, KeyError, UnicodeError) as error:
            result['errors'].append(str(error))
    for name in dict.fromkeys(row.filename for row in archive.infolist() if CONSOLE.fullmatch(row.filename)):
        try:
            raw = archive.read(member(archive, name, MAX_CONSOLE)).decode('utf-8', errors='replace')
            for line in raw.splitlines():
                position = line.find(PREFIX)
                if position < 0:
                    continue
                text = line[position:]
                parsed = NATIVE.match(text)
                phase = {'console_member': name, 'raw': text[:1024]}
                if parsed:
                    map_id, pid, sequence, label, elapsed, interval = parsed.groups()
                    phase.update(status='ok', map_id=int(map_id), windows_pid=int(pid),
                        sequence=int(sequence), phase=label, elapsed_ms=float(elapsed), phase_ms=float(interval),
                        scope='main_entry_to_checkpoint')
                else:
                    phase['status'] = 'clock_error' if 'status=clock_error ' in text else 'unparsed'
                result['native_phase_rows'].append(phase)
        except (ValueError, KeyError) as error:
            result['errors'].append(str(error))
    return latest


def analyze(path):
    path = Path(path)
    result = {'file': str(path), 'errors': [], 'supervisor_rows': [], 'native_phase_rows': [],
        'acceptance_evaluated': False, 'android_startup_timing_rows': [], 'owned_launch_memory_rows': [],
        **{key: None for key in ANDROID_DURATIONS}, 'android_thermal_observations': None,
        'full_tap_to_ready_seconds': None,
        'full_tap_to_movable_character_seconds': None, 'live_peak_memory_bytes': None,
        'live_thermal_observations': None}
    try:
        with path.open('rb') as source:
            digest = hashlib.sha256()
            for block in iter(lambda: source.read(1024**2), b''):
                digest.update(block)
            result['sha256'] = digest.hexdigest()
        with zipfile.ZipFile(path) as outer:
            names = {row.filename for row in outer.infolist()}
            android, checkpoint, guest, nested_guest = {}, {}, None, None
            if 'recovery-manifest.json' in names:
                result['recovery_manifest'] = document(outer, 'recovery-manifest.json')
            if 'android-client-report.json' in names:
                android = document(outer, 'android-client-report.json')
                result['android_result'] = select_result(android)
                result['identity'] = {key: android.get(key) for key in ('session_id', 'run_id', 'app_id',
                    'app_version', 'device', 'android_sdk', 'runtime_manifest_sha256',
                    'client_architecture_requested', 'graphics_profile_requested', 'gpu_profile_requested')}
                start, end = android.get('started_uptime_ms'), android.get('character_connected_observed_uptime_ms')
                result['android_operation_to_world_observation_seconds'] = (
                    round((end-start)/1000, 3) if type(start) is int and type(end) is int and 0 < start <= end else None)
            if 'android-recovery-checkpoint.json' in names:
                try:
                    checkpoint = document(outer, 'android-recovery-checkpoint.json')
                    result['android_checkpoint_result'] = select_result(checkpoint)
                except (ValueError, KeyError, UnicodeError) as error:
                    result['errors'].append('Android recovery checkpoint: ' + str(error))
            for name, value in (('android-client-report.json', android), ('android-recovery-checkpoint.json', checkpoint)):
                timing = value.get('android_startup_timing')
                if isinstance(timing, dict):
                    result['android_startup_timing_rows'].append({'report_member': name,
                        'session_id': value.get('session_id'), 'run_id': value.get('run_id'), 'timing': timing,
                        'clock_and_ready_event_consistent': android_clock_consistent(timing, value.get('session_id')),
                        'session_attribution_verified': False})
            # Interrupted carriers can retain compact guest state without an
            # android-client-report.json. That state never proves attribution
            # to the interrupted Android operation.
            if 'guest-output/latest-report.json' in names:
                try:
                    guest = document(outer, 'guest-output/latest-report.json')
                except (ValueError, KeyError, UnicodeError) as error:
                    result['errors'].append(str(error))
            if 'guest-report.zip' in names:
                info = member(outer, 'guest-report.zip', MAX_GUEST_ZIP)
                # No arbitrary archive paths are extracted onto the filesystem.
                with tempfile.SpooledTemporaryFile(max_size=8*1024**2) as temporary:
                    with outer.open(info) as source:
                        shutil.copyfileobj(source, temporary, length=1024**2)
                    temporary.seek(0)
                    try:
                        with zipfile.ZipFile(temporary) as nested:
                            nested_guest = read_guest(nested, result)
                    except (ValueError, KeyError, zipfile.BadZipFile) as error:
                        result['errors'].append('Nested guest report: ' + str(error))
            elif 'latest-report.json' in names:
                nested_guest = read_guest(outer, result)
            guest = guest if guest is not None else nested_guest
            if guest is None:
                raise ValueError('No complete or recovered guest latest-report.json found')
            result['session_id'] = guest.get('session_id')
            identities = [value for value in (android.get('session_id'), checkpoint.get('session_id'), guest.get('session_id'),
                (nested_guest or {}).get('session_id')) if value is not None]
            result['session_identity_consistent'] = bool(identities) and len(set(identities)) == 1
            result['android_operation_session_attribution_verified'] = (
                bool(android.get('session_id')) and result['session_identity_consistent']
                and result.get('recovery_manifest', {}).get('session_attribution_verified') is not False)
            if not result['session_identity_consistent']:
                result['errors'].append('Missing or inconsistent session identity; do not associate clocks or native rows')
            for row in result['android_startup_timing_rows']:
                row['session_attribution_verified'] = (result['android_operation_session_attribution_verified']
                    and row['session_id'] == android.get('session_id') and row['report_member'] == 'android-client-report.json')
                if row['session_attribution_verified'] and row['clock_and_ready_event_consistent']:
                    for key in ANDROID_DURATIONS:
                        result[key] = row['timing'].get(key)
                    result['android_thermal_observations'] = row['timing'].get('thermal_observations')
            owned_memory_rows(guest, result)
            result['guest_result'] = select_result(guest)
            for key in ('character_creation', 'character_reopen'):
                value = guest.get(key)
                if not isinstance(value, dict):
                    continue
                result[key + '_result'] = select_result(value)
                rows = value.get('map_startup_timing', [])
                if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                    result['errors'].append('Malformed map_startup_timing in ' + key)
                    continue
                # Preserve original failed/pending/resident rows and their scopes verbatim.
                result['supervisor_rows'].extend(dict(row, report_key=key) for row in rows)
            if not result['supervisor_rows']:
                result['errors'].append('No supervisor startup rows observed; earlier boundaries remain unknown')
            if not result['native_phase_rows']:
                result['errors'].append('No native startup phase rows found in retained full consoles')
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, RuntimeError) as error:
        result['errors'].append(str(error))
    return result


def summarize(paths):
    reports, sessions = [], {}
    for path in paths:
        row = analyze(path)
        session = row.get('session_id')
        if session:
            if session in sessions:
                row['duplicate_session_export_of'] = sessions[session]
            else:
                sessions[session] = str(path)
        reports.append(row)
    return {'acceptance_evaluated': False, 'reports': reports, 'limitations': [
        'Primary service_receipt_to_map_ready_seconds uses Android elapsedRealtime from first onStartCommand to owned ready-event receipt, including delivery delay.',
        'Guest request_to_map_ready_seconds starts later and is diagnostic; guest monotonic, Android elapsedRealtime and native QPC clocks are never combined.',
        'Resident returns and dependency-running zoning must remain distinct from fully stopped initial sessions.',
        'Missing, failed and duplicate reports are retained; no acceptance or qualifying-run count is inferred.',
        'UI action intervals begin in the app action handler, not a physical finger timestamp; world readiness is not proof of movement and can include manual login.',
        'Owned-launch VmHWM/RSS excludes other Wine/FEX workers, DbServer and client; aggregate MapServer peak and PSS remain unmeasured.',
        'Sparse Android thermal severity and battery temperature are not CPU temperature or a continuous thermal trace.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reports', nargs='+', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    raw = json.dumps(summarize(args.reports), indent=2, sort_keys=True, allow_nan=False) + '\n'
    if args.output:
        args.output.write_text(raw)
    else:
        print(raw, end='')


if __name__ == '__main__':
    main()
