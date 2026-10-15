#!/usr/bin/env python3
"""Bounded, host-only renderer/cadence summary of a complete Thor support ZIP.

Frame caps, prerequisite probes and delivered Android frames are not measured
gameplay FPS. Independent native streams are intentionally never ordinal-joined.
"""
import argparse
import io
import json
from pathlib import Path
import zipfile

import analyze_client_scene_performance as scene
import analyze_thor_performance as thor

PREFIX = 'COH_CLIENT_RENDERER_ATTRIBUTION_V1 '
MAX_RECORDS = 2 * 120 + 64
MAIN_METRICS = frozenset(('gfx_wall', 'backpressure_wall', 'gfx_other_wall'))
RENDERER_METRICS = frozenset(('renderer_batch_wall', 'renderer_batch_non_swap_wall',
    'swap_wall', 'texture_copy_wall', 'texture_subcopy_wall', 'vbo_create_wall',
    'framebuffer_readback_wall'))
WINDOW_FIELDS = {'format', 'event', 'role', 'report', 'window_ms', 'thread_cpu_ms',
    'wait_iterations', 'incomplete_batches', 'callback_counts', 'bucket_upper_ms', 'metrics'}


def strict_json(raw):
    def constant(value):
        raise ValueError('Nonfinite report JSON number: ' + value)
    value = json.loads(raw, object_pairs_hook=scene.unique_object, parse_constant=constant)
    if not isinstance(value, dict):
        raise ValueError('Report must be a JSON object')
    return value


def validate_distribution(metric):
    """Check extrema/mean against populated buckets, allowing native rounding."""
    count = scene.integer(metric['count'], 1, 10_000_000)
    mean, maximum = scene.number(metric['mean_ms']), scene.number(metric['max_ms'])
    histogram = metric['histogram']
    if not isinstance(histogram, list) or len(histogram) != len(scene.BOUNDS):
        raise ValueError('Renderer histogram shape differs')
    for value in histogram:
        scene.integer(value, 0, count)
    if sum(histogram) != count or mean > maximum:
        raise ValueError('Renderer histogram count or mean differs')
    last = max(i for i, value in enumerate(histogram) if value)
    lower = scene.BOUNDS[last - 1] if last else 0
    upper = scene.BOUNDS[last]
    # Native values are printed to .001 ms; a sample just above a bucket
    # boundary can therefore have a rounded maximum equal to that boundary.
    if maximum < lower - .001 or (upper is not None and maximum > upper + .001):
        raise ValueError('Renderer maximum differs from populated histogram')
    minimum_sum = sum(value * (scene.BOUNDS[i - 1] if i else 0)
                      for i, value in enumerate(histogram))
    maximum_sum = sum(value * min(bound if bound is not None else maximum, maximum)
                      for bound, value in zip(scene.BOUNDS, histogram))
    if not minimum_sum / count - .001 <= mean <= maximum_sum / count + .001:
        raise ValueError('Renderer mean differs from populated histogram')
    for percent in (50, 95):
        key = f'p{percent}_upper_ms'
        if key in metric:
            supplied = metric[key]
            if supplied is not None:
                scene.integer(supplied)
            if supplied != scene.quantile(histogram, percent):
                raise ValueError('Renderer percentile differs from histogram')


def validate_attribution(rows):
    previous, ordinal = {}, 0
    for row in rows:
        if scene.integer(row.get('format'), 1, 1) != 1:
            raise ValueError('Renderer attribution format differs')
        if row.get('event') == 'state':
            if set(row) != {'format', 'event', 'ordinal', 'maxfps', 'showfps'}:
                raise ValueError('Renderer state schema differs')
            if scene.integer(row['ordinal'], 1, 64) != ordinal + 1:
                raise ValueError('Renderer state sequence differs')
            ordinal += 1
            scene.integer(row['maxfps'], -(2**31), 2**31 - 1)
            scene.number(row['showfps'])
            continue
        role = row.get('role')
        fields = WINDOW_FIELDS | ({'configuration'} if role == 'main' else set())
        if row.get('event') != 'window' or role not in ('main', 'renderer') or set(row) != fields:
            raise ValueError('Renderer window schema or role differs')
        index = scene.integer(row['report'], 1, 120)
        if index != previous.get(role, 0) + 1:
            raise ValueError('Renderer window sequence differs')
        previous[role] = index
        scene.number(row['window_ms'], 10000)
        if row['thread_cpu_ms'] is not None:
            scene.number(row['thread_cpu_ms'])
        scene.integer(row['wait_iterations'])
        scene.integer(row['incomplete_batches'])
        callbacks = row['callback_counts']
        if not isinstance(callbacks, list) or len(callbacks) != 4:
            raise ValueError('Renderer callback counts shape differs')
        for value in callbacks:
            scene.integer(value)
        if row['bucket_upper_ms'] != scene.BOUNDS:
            raise ValueError('Renderer histogram bounds differ')
        if role == 'main':
            config = row['configuration']
            if not isinstance(config, dict) or set(config) != {
                    'allow_frames_buffered', 'threaded', 'sli_limit', 'frame_delay'}:
                raise ValueError('Renderer configuration schema differs')
            for key, value in config.items():
                scene.integer(value, 0 if key == 'sli_limit' else -(2**31),
                              2**32 - 1 if key == 'sli_limit' else 2**31 - 1)
        allowed = MAIN_METRICS if role == 'main' else RENDERER_METRICS
        if not isinstance(row['metrics'], dict) or set(row['metrics']) != allowed:
            raise ValueError('Renderer metric role differs')
        counts = set()
        for metric in row['metrics'].values():
            if not isinstance(metric, dict) or set(metric) != {
                    'count', 'mean_ms', 'max_ms', 'p95_upper_ms', 'histogram'}:
                raise ValueError('Renderer metric schema differs')
            validate_distribution(metric)
            counts.add(metric['count'])
        if len(counts) != 1:
            raise ValueError('Renderer per-batch metric counts differ')


def summarize_attribution(rows):
    streams = {}
    for row in rows:
        if row['event'] != 'window':
            continue
        stream = streams.setdefault(row['role'], {'reports': [], 'window_ms': 0,
            'measured_thread_cpu_ms': 0, 'cpu_windows': 0, 'wait_iterations': 0,
            'incomplete_batches': 0, 'callback_counts': [0] * 4, 'metrics': {}})
        stream['reports'].append(row['report'])
        stream['window_ms'] += row['window_ms']
        if row['thread_cpu_ms'] is not None:
            stream['measured_thread_cpu_ms'] += row['thread_cpu_ms']
            stream['cpu_windows'] += 1
        for key in ('wait_iterations', 'incomplete_batches'):
            stream[key] += row[key]
        stream['callback_counts'] = [a + b for a, b in zip(stream['callback_counts'], row['callback_counts'])]
        for key, value in row['metrics'].items():
            metric = stream['metrics'].setdefault(key, {'count': 0, '_sum_ms': 0,
                'max_ms': 0, 'histogram': [0] * len(scene.BOUNDS)})
            metric['count'] += value['count']
            metric['_sum_ms'] += value['mean_ms'] * value['count']
            metric['max_ms'] = max(metric['max_ms'], value['max_ms'])
            metric['histogram'] = [a + b for a, b in zip(metric['histogram'], value['histogram'])]
    for stream in streams.values():
        if not stream['cpu_windows']:
            stream['measured_thread_cpu_ms'] = None
        for metric in stream['metrics'].values():
            metric['sample_sum_ms'] = round(metric.pop('_sum_ms'), 3)
            metric['mean_ms'] = round(metric['sample_sum_ms'] / metric['count'], 3)
            for percent in (50, 95):
                metric[f'p{percent}_upper_ms'] = scene.quantile(metric['histogram'], percent)
    return streams


def partition_main_windows(console):
    """Assign only main-thread windows using ordered main-thread state records.

    A first report after ANY state update may straddle that update and is
    excluded. Main attribution and frame windows have independent boundaries.
    Renderer/presentation logs carry no state labels and are never assigned caps.
    """
    states, frame_groups, attribution_groups = [], {}, {}
    coverage = {'frame': [], 'attribution': []}
    pending = {'frame': False, 'attribution': False}
    state = None
    for line in console.splitlines():
        prefix = next((value for value in (scene.FRAME_PREFIX, PREFIX) if value in line), None)
        if prefix is None:
            continue
        row = strict_json(line.split(prefix, 1)[1])
        if prefix == PREFIX and row['event'] == 'state':
            state = row
            states.append(row)
            pending = {'frame': True, 'attribution': True}
            continue
        if row['role'] != 'main':
            continue
        kind = 'frame' if prefix == scene.FRAME_PREFIX else 'attribution'
        classification = ('state_bound_reached' if state and state['ordinal'] == 64 else
                          'unclassified' if state is None else
                          'transition' if pending[kind] else 'stable_cap')
        pending[kind] = False
        cap = state['maxfps'] if classification == 'stable_cap' else None
        entry = {'report': row['report'], 'classification': classification, 'maxfps': cap}
        if kind == 'frame':
            entry['states'] = list(row['states'])
            entry['pure_gameplay'] = set(row['states']) == {'gameplay'}
            if classification == 'stable_cap' and entry['pure_gameplay']:
                frame_groups.setdefault(str(cap), []).append(row)
        elif classification == 'stable_cap':
            attribution_groups.setdefault(str(cap), []).append(row)
        coverage[kind].append(entry)
    # Existing validator enforces report 1..N; each selected subset must retain
    # its actual report IDs separately rather than being mistaken for a stream.
    gameplay = {}
    for cap, rows in frame_groups.items():
        ids = [row['report'] for row in rows]
        renumbered = [dict(row, report=i) for i, row in enumerate(rows, 1)]
        gameplay[cap] = scene.summarize_frames(renumbered)['main']
        gameplay[cap]['reports'] = ids
    return {'state_changes': states, 'main_window_coverage': coverage,
        'pure_gameplay_main_frames_by_cap': gameplay,
        'main_attribution_by_stable_cap_game_state_unavailable': {
            cap: summarize_attribution(rows)['main'] for cap, rows in attribution_groups.items()}}


def gpu_summary(guest):
    profile = guest.get('client_gpu_profile')
    if profile is not None and not isinstance(profile, dict):
        raise ValueError('GPU profile receipt must be an object')
    graphics = guest.get('graphics_observation', {})
    if not isinstance(graphics, dict):
        raise ValueError('Game graphics observation must be an object')
    renderer = graphics.get('renderer', '')
    if not isinstance(renderer, str):
        raise ValueError('Game renderer must be a string')
    software = (any(name in renderer.lower() for name in ('llvmpipe', 'softpipe',
        'lavapipe', 'swrast', 'swiftshader', 'software rasterizer', 'gdi generic'))
        if renderer.strip() else None)
    attempts = guest.get('client_gpu_profile_attempts', [])
    if not isinstance(attempts, list) or len(attempts) > 4 or any(not isinstance(value, dict) for value in attempts):
        raise ValueError('GPU profile attempts exceed bounded receipt inventory')
    def receipt(value):
        if value is None:
            return {}
        return {'requested': value.get('requested'), 'selected_environment': value.get('selected'),
            'prerequisite_state': value.get('state'), 'fallback_reason': value.get('fallback_reason'),
            'probe_cleanup_safe': value.get('probe_cleanup_safe'), 'launch_label': value.get('launch_label'),
            'archive_sha256': value.get('archive_sha256'),
            'prerequisite_receipts': {key: value.get(key) for key in ('vulkan_probe', 'wine_gl_probe')}}
    requested = profile.get('requested') if profile else None
    selected = profile.get('selected') if profile else None
    producer = guest.get('client_renderer_attribution', {})
    if not isinstance(producer, dict):
        raise ValueError('Game producer receipt must be an object')
    return {'profile_receipt_present': profile is not None, **receipt(profile),
        'requested_selected_differ': requested != selected if requested is not None and selected is not None else None,
        'gpu_selected_but_actual_game_software_observed': selected == 'turnip' and software
            if selected is not None and software is not None else None,
        'bounded_attempt_receipts': [receipt(value) for value in attempts],
        'reported_total_attempt_count': guest.get('client_gpu_profile_attempt_count'),
        'game_producer': {key: producer.get(key) for key in ('repository_commit', 'client_executable_sha256')},
        'actual_game_graphics_observation': graphics,
        'actual_game_renderer_observed': bool(renderer.strip()),
        'software_renderer_observed': software,
        'hardware_acceleration_validated_by_this_analysis': False,
        'physical_fps_improvement_validated_by_this_analysis': False}


def analyze(path):
    with zipfile.ZipFile(path) as outer:
        android = strict_json(thor.read_member(outer, 'android-client-report.json', thor.MAX_REPORT))
        raw = thor.read_member(outer, 'guest-report.zip', thor.MAX_GUEST_ZIP)
    with zipfile.ZipFile(io.BytesIO(raw)) as guest_zip:
        guest = strict_json(thor.read_member(guest_zip, 'latest-report.json', thor.MAX_REPORT))
        console_present = any(item.filename == 'client-evidence/client-console.log'
                              for item in guest_zip.infolist())
        console = (thor.read_member(guest_zip, 'client-evidence/client-console.log', scene.MAX_CONSOLE)
                   .decode('utf-8', errors='replace') if console_present else '')
    frames = scene.records(console, scene.FRAME_PREFIX, scene.MAX_FRAME_RECORDS)
    attribution = scene.records(console, PREFIX, MAX_RECORDS)
    phases = scene.records(console, scene.SCENE_PREFIX, scene.MAX_SCENE_RECORDS)
    native_frames = scene.summarize_frames(frames)
    for row in frames:
        for metrics in row['states'].values():
            for metric in metrics.values():
                validate_distribution(metric)
    validate_attribution(attribution)
    reopen = guest.get('character_reopen', {})
    return {'format': 1, 'startup': thor.analyze(path),
        'client_console_present': console_present,
        'native_frame_instrumentation_present': bool(frames),
        'native_renderer_attribution_present': bool(attribution),
        'scene_entry': scene.scene_entry(console, guest),
        'native_frames_all_caps_and_game_states': native_frames,
        'renderer_attribution_all_game_states_unaligned': summarize_attribution(attribution),
        **partition_main_windows(console),
        'native_scene_phases_non_additive': scene.summarize_scene(phases),
        'gpu_profile_and_actual_backend': gpu_summary(guest),
        'android_capture_diagnostics': android.get('android_capture_diagnostics'),
        'strict_save_result': {
            'android_passed': android.get('passed'), 'guest_passed': guest.get('passed'),
            'android_character_reopen_verified': android.get('character_reopen_verified'),
            'guest_character_reopen_verified': reopen.get('verified'),
            'failures': guest.get('failures', []),
            'save_comparison_failure': reopen.get('save_comparison_failure'),
            'analysis_changes_save_acceptance': False},
        'limitations': [
            'Native frame interval cadence is measured separately from configured caps and Android delivered frames; it is not GPU completion or display FPS.',
            'Main state records have no timestamps or per-window cap labels. First windows after each state change are conservatively excluded; state record 64 exhausts the cap attribution bound.',
            'Only pure gameplay main windows enter cap groups. Routes/actions are unlabelled; these groups do not establish a controlled performance gain.',
            'Main attribution has no gameplay state. Renderer and presentation have independent boundaries and no cap/state labels; report ordinals cannot align streams.',
            'Thread CPU covers only each sampled thread, excluding llvmpipe/Wine/FEX workers. Missing CPU windows remain missing.',
            'gfx/backpressure overlap submit/work. Renderer batches include queue starvation, scheduling and driver waits; nested phases and threads must not be added.',
            'Texture/VBO callbacks exclude disk/decode and eventual GPU completion. Zero instrumented readback does not exclude readback elsewhere.',
            'Histogram p50/p95 are bucket upper bounds; null is overflow. Weighted cadence uses sample counts, not an average of per-window FPS.',
            'PixelCopy/encoding diagnostics exclude retained PNG verification/callback costs; off-main encoding can still compete for CPU.',
            'GPU selection and prerequisite receipts do not validate Game shaders, Android presentation, hardware acceleration or physical FPS improvement.',
            'Missing console evidence (for example, a pre-Game failure) means no native measurements; it does not imply zero work or successful rendering.',
            'Diagnostics are bounded to 120 roughly ten-second windows per thread and can omit final partial windows; scene completions have separate bounds.',
            'This analysis does not diagnose the cause or resolution of black tearing, change strict save results, or prove character preservation after a failed save.']}


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
