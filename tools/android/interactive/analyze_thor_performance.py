#!/usr/bin/env python3
"""Read a Thor support ZIP into a bounded, non-overlapping performance summary."""
import argparse
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import zipfile

MAX_REPORT = 8 * 1024**2
MAX_GUEST_ZIP = 64 * 1024**2


def read_member(archive, name, maximum):
    matches = [item for item in archive.infolist() if item.filename == name]
    if len(matches) != 1 or not 0 < matches[0].file_size <= maximum:
        raise ValueError('Missing, duplicate or oversized report member: ' + name)
    return archive.read(matches[0])


def duration(start, end):
    seconds = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()
    if seconds < 0:
        raise ValueError('Reversed report interval')
    return round(seconds, 6)


def uptime_interval(android, start, end):
    a, b = android.get(start), android.get(end)
    if isinstance(a, int) and isinstance(b, int) and 0 <= a <= b:
        return round((b-a)/1000, 3)
    return None


def summarize(android, guest):
    stages = []
    for item in guest.get('stages', []):
        if item.get('finished_utc'):
            stages.append({'stage': item['stage'], 'seconds': duration(item['started_utc'], item['finished_utc']),
                'started_utc': item['started_utc'], 'finished_utc': item['finished_utc']})
    startup = [row for row in stages if row['stage'] != 'actual_client_interaction']
    for before, after in zip(startup, startup[1:]):
        if datetime.fromisoformat(before['finished_utc']) > datetime.fromisoformat(after['started_utc']):
            raise ValueError('Overlapping top-level stages must not be added')
    by_name = {row['stage']: row['seconds'] for row in stages}
    private = guest.get('character_reopen', {}).get('private_map_data', {})
    prep = private.get('preparation_elapsed_seconds')
    dbtotal = by_name.get('local_dbserver_startup')
    residual = round(dbtotal-prep, 6) if isinstance(prep, (int, float)) and dbtotal is not None else None
    if residual is not None and residual < 0:
        raise ValueError('Server preparation exceeds containing stage')
    cache = private.get('server_data_cache', {})
    top_total = duration(startup[0]['started_utc'], startup[-1]['finished_utc']) if startup else None
    header = guest.get('texture_header_index', {})
    # Subphases explain parent intervals and gaps; they are never added to the
    # top-level total because animation/beacon work may already be nested.
    subphases = {name: guest.get(name, {}) for name in ('atlas_required_geometry', 'atlas_beacon_graph',
        'atlas_world_supplement', 'client_texture_startup_schedule', 'texture_header_index')}
    subphases['server_preparation'] = {
        'seconds': prep, 'containing_stage': 'local_dbserver_startup',
        'remaining_stage_seconds': residual, 'remaining_stage_includes': 'native launch, readiness and SQL verification',
        'cache_key': cache.get('key'), 'reused': cache.get('reused'),
        'migration_refused': cache.get('migration_refused'),
        'counts': {key: value for key, value in private.items() if key in ('files', 'directories') or key.endswith(('_files', '_directories'))},
        'phases': private.get('preparation_phase_seconds', {}),
        'native_startup': guest.get('local_login', {}).get('startup_timing', {}),
    }
    renderer = guest.get('graphics_observation', {})
    interaction = by_name.get('actual_client_interaction')
    frames = android.get('decoded_frame_count')
    return {
        'format': 1, 'app_version': android.get('app_version'), 'session_id': android.get('session_id'),
        'operation': android.get('operation'), 'stage_seconds': by_name, 'stages': stages,
        'timing_seconds': {
            'operation_to_login_observation': uptime_interval(android, 'started_uptime_ms', 'login_observed_uptime_ms'),
            'operation_to_world_observation': uptime_interval(android, 'started_uptime_ms', 'character_connected_observed_uptime_ms'),
            'login_to_world_observation': uptime_interval(android, 'login_observed_uptime_ms', 'character_connected_observed_uptime_ms'),
            'guest_to_client_ready': top_total,
            'unlabelled_preparation_and_gaps': round(top_total-sum(row['seconds'] for row in startup), 6) if top_total is not None else None,
        },
        'subphases_not_additive': subphases,
        'visual_preparation': {key: guest.get('client_visual_supplement', {}).get(key) for key in
            ('file_count', 'installed_files', 'reused_files', 'fingerprint_reused', 'archive_read_bytes',
             'decoded_files', 'decoded_payload_bytes', 'verified_existing_bytes', 'preparation_elapsed_seconds')},
        'renderer': renderer,
        'observer_metrics': guest.get('client_observer_metrics', {}),
        'steady_state_policy': guest.get('character_observer_metrics', {}).get('steady_state_policy'),
        'delivered_frame_count': frames, 'interaction_seconds': interaction,
        'measured_game_fps': None,
        'cache_work_observation': 'First update versus unchanged warm run must be compared separately; one report cannot prove every-run repetition.',
        'result': {key: android.get(key) for key in ('passed', 'cleanup_verified', 'character_reopen_verified')},
        'limitations': ['Operation start does not measure time before pressing Reopen or APK/runtime installation.',
            'Login/world observation includes typing and selection; guest client-ready is reported separately.',
            'Delivered Android frames include initialization and UI; they are not native game FPS.',
            'Subphases overlap containing stages and must not be added a second time.'],
    }


def analyze(path):
    path = Path(path)
    with zipfile.ZipFile(path) as outer:
        android = json.loads(read_member(outer, 'android-client-report.json', MAX_REPORT))
        raw = read_member(outer, 'guest-report.zip', MAX_GUEST_ZIP)
    with zipfile.ZipFile(io.BytesIO(raw)) as inner:
        guest = json.loads(read_member(inner, 'latest-report.json', MAX_REPORT))
    result = summarize(android, guest)
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024**2), b''): digest.update(block)
    result['support_zip'] = {'filename': path.name, 'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('support_zip', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(); raw = json.dumps(analyze(args.support_zip), indent=2, sort_keys=True)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(raw)
    else: print(raw, end='')


if __name__ == '__main__': main()
