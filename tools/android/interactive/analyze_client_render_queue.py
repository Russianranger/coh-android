#!/usr/bin/env python3
"""Summarize sparse scene timings and cumulative render-queue observations.

These measurements do not establish GPU duration or an improvement in FPS.
The retained frame streams supply cadence; independently anchored streams are
never joined by their report numbers.
"""
import argparse
import io
import json
from pathlib import Path
import re
import zipfile

import analyze_client_render_pipeline as pipeline

renderer = pipeline.renderer
PREFIX = 'COH_CLIENT_RENDER_QUEUE_V1 '
MAX_RECORDS = 120
MAX_LINE = 8192
UINT64_MAX = 2**64 - 1
FIELDS = frozenset(('format', 'event', 'scope', 'queue_scope', 'report', 'window_ms',
    'sample_interval', 'gameplay_frames', 'sampled_frames', 'incomplete_frames',
    'queue_counters_saturated', 'queue_counters', 'bucket_upper_ms', 'metrics'))
COUNTERS = frozenset(('commands', 'armed_observations', 'wake_signals',
    'wake_signal_failures', 'pending_commands', 'ring_waits', 'ring_wait_iterations',
    'ring_wait_clock_failures'))
WALL_COUNTERS = frozenset(('ring_wait_wall_ms', 'ring_wait_max_ms'))
METRICS = frozenset(('setup_wall', 'sort_wall', 'draw_wall'))


def validate_distribution(metric):
    """Match the queue header's UINT32 count and finite 1e12 ms limits."""
    count = renderer.scene.integer(metric['count'], 1)
    mean = renderer.scene.number(metric['mean_ms'], 0, 1e12)
    maximum = renderer.scene.number(metric['max_ms'], 0, 1e12)
    if mean * count > 1e12 + count * .001:
        raise ValueError('Render queue metric aggregate exceeds native bound')
    histogram = metric['histogram']
    bounds = renderer.scene.BOUNDS
    if not isinstance(histogram, list) or len(histogram) != len(bounds):
        raise ValueError('Render queue histogram shape differs')
    for value in histogram:
        renderer.scene.integer(value, 0, count)
    if sum(histogram) != count or mean > maximum:
        raise ValueError('Render queue histogram count or mean differs')
    last = max(i for i, value in enumerate(histogram) if value)
    lower, upper = bounds[last-1] if last else 0, bounds[last]
    if maximum < lower - .001 or (upper is not None and maximum > upper + .001):
        raise ValueError('Render queue maximum differs from histogram')
    low_sum = sum(value * (bounds[i-1] if i else 0) for i, value in enumerate(histogram))
    high_sum = sum(value * min(bound if bound is not None else maximum, maximum)
        for bound, value in zip(bounds, histogram))
    if not low_sum/count - .001 <= mean <= high_sum/count + .001:
        raise ValueError('Render queue mean differs from histogram')
    supplied = metric['p95_upper_ms']
    if supplied is not None:
        renderer.scene.integer(supplied)
    if supplied != renderer.scene.quantile(histogram, 95):
        raise ValueError('Render queue percentile differs from histogram')


def queue_records(console):
    rows = []
    for line in console.splitlines():
        if PREFIX not in line:
            continue
        raw = line.split(PREFIX, 1)[1]
        if len(raw.encode('utf-8')) >= MAX_LINE or len(rows) >= MAX_RECORDS:
            raise ValueError('Render queue record budget exceeded')
        rows.append(renderer.strict_json(raw))
    return rows


def validate_queue(rows):
    previous = None
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError('Render queue schema differs')
        renderer.scene.integer(row['format'], 1, 1)
        if (row['event'] != 'window' or row['scope'] != 'gameplay'
                or row['queue_scope'] != 'process_cumulative'):
            raise ValueError('Render queue scope differs')
        if renderer.scene.integer(row['report'], 1, MAX_RECORDS) != index:
            raise ValueError('Render queue sequence differs')
        renderer.scene.number(row['window_ms'], 10000, 1e12)
        renderer.scene.integer(row['sample_interval'], 32, 32)
        frames = renderer.scene.integer(row['gameplay_frames'])
        samples = renderer.scene.integer(row['sampled_frames'], 0, frames)
        renderer.scene.integer(row['incomplete_frames'])
        if (not isinstance(row['bucket_upper_ms'], list)
                or row['bucket_upper_ms'] != renderer.scene.BOUNDS
                or any(type(value) is not int for value in row['bucket_upper_ms'][:-1])
                or row['bucket_upper_ms'][-1] is not None):
            raise ValueError('Render queue histogram bounds differ')
        metrics = row['metrics']
        if not isinstance(metrics, dict) or set(metrics) != (METRICS if samples else set()):
            raise ValueError('Render queue sampled metrics differ')
        for metric in metrics.values():
            if not isinstance(metric, dict) or set(metric) != pipeline.METRIC_FIELDS:
                raise ValueError('Render queue metric schema differs')
            validate_distribution(metric)
            if metric['count'] != samples:
                raise ValueError('Render queue sampled metric count differs')
        counters = row['queue_counters']
        if not isinstance(counters, dict) or set(counters) != COUNTERS | WALL_COUNTERS:
            raise ValueError('Render queue counter schema differs')
        for name in COUNTERS:
            renderer.scene.integer(counters[name], 0, UINT64_MAX)
        for name in WALL_COUNTERS:
            renderer.scene.number(counters[name], 0, 1e12)
        saturated = any(counters[name] == UINT64_MAX for name in COUNTERS)
        if type(row['queue_counters_saturated']) is not bool or row['queue_counters_saturated'] != saturated:
            raise ValueError('Render queue saturation flag differs')
        if counters['ring_wait_max_ms'] > counters['ring_wait_wall_ms']:
            raise ValueError('Render queue wait maximum exceeds total')
        if (counters['armed_observations'] > counters['commands']
                or counters['pending_commands'] > counters['commands']
                or counters['wake_signals'] > counters['armed_observations']
                or counters['wake_signal_failures'] > counters['armed_observations']
                or (counters['armed_observations'] != UINT64_MAX
                    and counters['wake_signals'] + counters['wake_signal_failures'] > counters['armed_observations'])
                or counters['ring_waits'] > counters['ring_wait_iterations']
                or counters['ring_wait_clock_failures'] > counters['ring_waits']):
            raise ValueError('Render queue counter conservation differs')
        if previous is not None and any(counters[name] < previous[name] for name in counters):
            raise ValueError('Render queue cumulative counter decreased')
        previous = counters


def summarize_queue(rows):
    if not rows:
        return None
    # Reuse the distribution pooling only; no cadence or CPU inference is made
    # from this stream's window wall time or sparse phase count.
    projected = [dict(role='queue', window_ms=row['window_ms'], report=row['report'],
        scope=row['scope'], thread_cpu_ms=None, incomplete_batches=row['incomplete_frames'],
        metrics=row['metrics']) for row in rows]
    pooled = pipeline.summarize_pipeline(projected)['queue']
    last = rows[-1]
    result = {'reports': [row['report'] for row in rows],
        'window_wall_ms': pooled['window_ms'], 'sample_interval': 32,
        'gameplay_frames': sum(row['gameplay_frames'] for row in rows),
        'sampled_frames': sum(row['sampled_frames'] for row in rows),
        'incomplete_frames': sum(row['incomplete_frames'] for row in rows),
        'sampled_scene_metrics': pooled['metrics'],
        'latest_process_cumulative_queue_counters': dict(last['queue_counters']),
        'queue_counters_saturated': last['queue_counters_saturated'],
        'queue_counter_increase_between_first_and_last_report': None,
        'queue_scope': 'process_cumulative_including_non_gameplay',
        'scene_scope': 'first_then_every_32nd_ordinary_gameplay_frame'}
    if len(rows) > 1 and not last['queue_counters_saturated']:
        result['queue_counter_increase_between_first_and_last_report'] = {
            name: round(last['queue_counters'][name] - rows[0]['queue_counters'][name], 3)
            for name in COUNTERS | {'ring_wait_wall_ms'}}
    return result


def validate_identity_fields(value):
    if value is None:
        return
    if not isinstance(value, dict):
        raise ValueError('Render queue identity must be an object')
    for name, item in value.items():
        if item is None:
            continue
        length = 64 if name.endswith('_sha256') else 40 if name.endswith('_commit') else None
        if length and (not isinstance(item, str) or re.fullmatch('[0-9a-f]{'+str(length)+'}', item) is None):
            raise ValueError('Render queue supplied identity hash is invalid: '+name)
        if name in ('enabled', 'verified') and type(item) is not bool:
            raise ValueError('Render queue supplied identity flag is invalid: '+name)


def producer_summary(guest):
    current = guest.get('client_render_queue')
    if current is None:
        return {'current_render_queue_producer_receipt': None,
            'retained_pipeline_attribution': pipeline.producer_summary(guest),
            'supplied_identity_checks': 0, 'supplied_identity_fields_consistent': None,
            'source_closure_reverified_by_host_analysis': False}
    parent = guest.get('client_render_pipeline')
    environment = guest.get('client_render_queue_environment')
    prior_environment = guest.get('client_render_pipeline_environment')
    validate_identity_fields({'client_executable_sha256': guest.get('client_executable_sha256')})
    validate_identity_fields(guest.get('client_renderer_attribution'))
    for name, value in (('producer', current), ('parent', parent),
            ('environment', environment), ('pipeline environment', prior_environment)):
        if value is not None and not isinstance(value, dict):
            raise ValueError('Render queue ' + name + ' must be an object')
        validate_identity_fields(value)
    checks = []
    def compare(left, right):
        if left is not None and right is not None:
            checks.append(left == right)
    compare(current.get('client_executable_sha256'), guest.get('client_executable_sha256'))
    if parent is not None:
        compare(current.get('base_client_executable_sha256'), parent.get('client_executable_sha256'))
        compare(current.get('base_client_render_pipeline_manifest_sha256'), parent.get('manifest_sha256'))
    if environment is not None:
        compare(current.get('client_executable_sha256'), environment.get('client_executable_sha256'))
        compare(current.get('manifest_sha256'), environment.get('producer_manifest_sha256'))
        compare(current.get('native_source_sha256'), environment.get('native_source_sha256'))
    if prior_environment is not None:
        compare(current.get('client_executable_sha256'), prior_environment.get('client_executable_sha256'))
        compare(current.get('manifest_sha256'), prior_environment.get('current_Game_manifest_sha256'))
        compare(current.get('repository_commit'), prior_environment.get('current_Game_repository_commit'))
        if parent is not None:
            compare(parent.get('client_executable_sha256'), prior_environment.get('pipeline_producer_executable_sha256'))
            compare(parent.get('manifest_sha256'), prior_environment.get('producer_manifest_sha256'))
            compare(parent.get('native_source_sha256'), prior_environment.get('native_source_sha256'))
            compare(parent.get('repository_commit'), prior_environment.get('pipeline_producer_repository_commit'))
    attempts = guest.get('client_gpu_profile_attempts', [])
    if not isinstance(attempts, list) or len(attempts) > 64:
        raise ValueError('Render queue GPU attempt list differs')
    for profile in [guest.get('client_gpu_profile'), *attempts]:
        if profile is None:
            continue
        if not isinstance(profile, dict):
            raise ValueError('Render queue GPU profile must be an object')
        supplied = profile.get('game_producer')
        validate_identity_fields(supplied)
        if supplied is not None:
            for name in ('repository_commit', 'manifest_sha256', 'client_executable_sha256', 'native_source_sha256'):
                compare(current.get(name), supplied.get(name))
    if checks and not all(checks):
        raise ValueError('Render queue current/parent/environment identity differs')
    # Verify the historical .22 -> .19 edge without mislabelling the current
    # executable or passing its operational environment as the .22 environment.
    history = pipeline.producer_summary({key: guest[key] for key in
        ('client_render_pipeline', 'client_renderer_attribution') if key in guest})
    return {'current_render_queue_producer_receipt': current,
        'queue_environment_receipt': environment,
        'operational_pipeline_environment_receipt': prior_environment,
        'retained_pipeline_attribution': history,
        'top_level_current_Game_executable_sha256': guest.get('client_executable_sha256'),
        'supplied_identity_checks': len(checks),
        'supplied_identity_fields_consistent': all(checks) if checks else None,
        'current_producer_verified_by_guest_report': current.get('verified'),
        'source_closure_reverified_by_host_analysis': False}


def analyze(path):
    result = renderer.analyze(path)
    with zipfile.ZipFile(path) as outer:
        raw = renderer.thor.read_member(outer, 'guest-report.zip', renderer.thor.MAX_GUEST_ZIP)
    with zipfile.ZipFile(io.BytesIO(raw)) as inner:
        guest = renderer.strict_json(renderer.thor.read_member(inner, 'latest-report.json', renderer.thor.MAX_REPORT))
        present = any(item.filename == 'client-evidence/client-console.log' for item in inner.infolist())
        console = (renderer.thor.read_member(inner, 'client-evidence/client-console.log',
            renderer.scene.MAX_CONSOLE).decode('utf-8', errors='replace') if present else '')
    rows = queue_records(console)
    validate_queue(rows)
    prior = pipeline.pipeline_records(console)
    pipeline.validate_pipeline(prior)
    result['native_render_queue_present'] = bool(rows)
    result['render_queue_observations'] = summarize_queue(rows)
    result['native_render_pipeline_present'] = bool(prior)
    result['render_pipeline_streams_all_states_unaligned'] = pipeline.summarize_pipeline(prior)
    identity = producer_summary(guest)
    result['render_queue_Game_source_attribution'] = identity
    current = identity['current_render_queue_producer_receipt']
    if current is None:
        current = guest.get('client_render_pipeline')
    if current is not None:
        backend = result['gpu_profile_and_actual_backend']
        backend['inherited_renderer_attribution_producer'] = backend['game_producer']
        backend['game_producer'] = {key: current.get(key)
            for key in ('repository_commit', 'client_executable_sha256', 'manifest_sha256')}
        backend['game_producer_scope'] = ('current_render_queue_Game_receipt'
            if identity['current_render_queue_producer_receipt'] is not None else 'current_render_pipeline_Game_receipt')
    result['render_queue_limitations'] = [
        'Missing records or unsampled metrics remain missing, not zero work.',
        'Scene phases cover one in 32 ordinary gameplay frames; sampling can miss stalls.',
        'Window wall includes intervening non-gameplay time. Do not derive gameplay FPS or CPU from these window totals.',
        'Queue counters are cumulative for the process, including startup and menus; snapshots must not be summed.',
        'Pending commands observe state 2. They are not a measured count of avoided event calls.',
        'Wake signals count producer command notifications only; unchanged control, monitor and full-ring flush signals are excluded.',
        'Immediate unthreaded dispatch does not contribute to producer queue counters.',
        'Cumulative differences exclude the first snapshot and do not align with scene or renderer windows.',
        'Ring wait wall overlaps scene submission and includes scheduling; phase and queue durations must not be added.',
        'Draw phase covers sorted-model passes, not all particles, sky, UI or other rendering.',
        'Wake counts and ring waits do not measure pure GPU execution, driver cost, or total render synchronization.',
        'Native main, renderer, presentation, pipeline and queue reports have independent boundaries; report ordinals are not frame identities.',
        'Histograms supply bucket upper bounds. Saturated counters cannot establish exact totals or deltas.',
        'Current queue Game is distinct from historical pipeline/renderer producers; host parsing does not requalify native source closure.',
        'This analysis preserves strict save, cleanup and gameplay results and does not establish physical FPS improvement.']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('support_zip', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    raw = json.dumps(analyze(args.support_zip), indent=2, sort_keys=True, allow_nan=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw, encoding='utf-8')
    else:
        print(raw, end='')


if __name__ == '__main__':
    main()
