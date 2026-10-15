#!/usr/bin/env python3
"""Bounded scene/frame analysis of an owned Thor support ZIP.

Native frame cadence is distinct from GPU completion and Android display FPS.
Scene phases can nest; their durations must not be summed into a startup total.
"""
import argparse
from datetime import datetime, timezone
import io
import json
import math
from pathlib import Path
import re
import zipfile

from analyze_thor_performance import analyze as analyze_startup, read_member

SCENE_PREFIX = 'COH_CLIENT_SCENE_PHASE_V1 '
FRAME_PREFIX = 'COH_CLIENT_FRAME_TIMING_V1 '
MAX_CONSOLE = 16 * 1024**2
MAX_FRAME_RECORDS = 240
MAX_SCENE_RECORDS = 512
BOUNDS = [16, 33, 50, 66, 83, 100, 110, 125, 150, 200, 250, 333, 500,
          750, 1000, 2000, 5000, 10000, 30000, 60000, 120000, None]
MAIN_METRICS = frozenset(('frame_interval', 'frame_wall', 'engine_wall',
                         'submit_wall', 'pacing_wall', 'work_wall'))
PRESENT_METRICS = frozenset(('presentation_interval', 'present_wall', 'swap_wall'))


def integer(value, minimum=0, maximum=2**32-1):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError('Invalid native timing integer')
    return value


def number(value, minimum=0, maximum=2**32-1):
    if type(value) not in (int, float) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError('Invalid native timing number')
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate native timing JSON key')
        result[key] = value
    return result


def records(console, prefix, maximum):
    result = []
    for line in console.splitlines():
        if prefix not in line:
            continue
        # Timestamped logging may precede the marker; malformed/interleaved
        # records must never silently become an apparently valid measurement.
        raw = line.split(prefix, 1)[1]
        if len(raw) > 16384 or len(result) >= maximum:
            raise ValueError('Native timing report budget exceeded')
        value = json.loads(raw, object_pairs_hook=unique_object)
        if not isinstance(value, dict):
            raise ValueError('Native timing record must be an object')
        result.append(value)
    return result


def quantile(histogram, percent):
    count = sum(histogram)
    if not count:
        return None
    rank, seen = (count * percent + 99) // 100, 0
    for bound, value in zip(BOUNDS, histogram):
        seen += value
        if seen >= rank:
            return bound
    raise ValueError('Incomplete frame histogram')


def validate_metric(metric):
    fields = {'count', 'mean_ms', 'max_ms', 'p50_upper_ms', 'p95_upper_ms',
              'over_125ms_count', 'over_200ms_count', 'histogram'}
    if not isinstance(metric, dict) or set(metric) != fields:
        raise ValueError('Native metric schema differs')
    count = integer(metric['count'], 1, 10_000_000)
    mean, maximum = number(metric['mean_ms']), number(metric['max_ms'])
    if mean > maximum:
        raise ValueError('Native mean exceeds maximum')
    histogram = metric['histogram']
    if not isinstance(histogram, list) or len(histogram) != len(BOUNDS):
        raise ValueError('Native histogram shape differs')
    for value in histogram:
        integer(value, 0, count)
    if sum(histogram) != count:
        raise ValueError('Native histogram count differs')
    for percent in (50, 95):
        if metric[f'p{percent}_upper_ms'] != quantile(histogram, percent):
            raise ValueError('Native histogram percentile differs')
    for threshold in (125, 200):
        value = integer(metric[f'over_{threshold}ms_count'], 0, count)
        if value != sum(histogram[BOUNDS.index(threshold)+1:]):
            raise ValueError('Native stutter count differs from histogram')
    return count


def summarize_frames(frame_records):
    streams, previous = {}, {}
    for record in frame_records:
        if set(record) != {'role', 'report', 'window_ms', 'thread_cpu_ms', 'histogram_upper_ms', 'states'}:
            raise ValueError('Native frame schema differs')
        role = record['role']
        if role not in ('main', 'presentation'):
            raise ValueError('Unknown native frame role')
        index = integer(record['report'], 1, 120)
        if index != previous.get(role, 0) + 1:
            raise ValueError('Native frame report sequence differs')
        previous[role] = index
        elapsed = number(record['window_ms'], 10000)
        cpu = record['thread_cpu_ms']
        if cpu is not None:
            number(cpu)
        if record['histogram_upper_ms'] != BOUNDS:
            raise ValueError('Native histogram bounds differ')
        states = record['states']
        allowed_states = {'unclassified'} if role == 'presentation' else {'menu', 'loading', 'gameplay', 'mixed'}
        allowed_metrics = PRESENT_METRICS if role == 'presentation' else MAIN_METRICS
        if not isinstance(states, dict) or not states or not set(states) <= allowed_states:
            raise ValueError('Native frame states differ')
        stream = streams.setdefault(role, {'reports': 0, 'window_ms': 0,
                                         'measured_thread_cpu_ms': 0, 'cpu_windows': 0, 'states': {}})
        stream['reports'] += 1
        stream['window_ms'] += elapsed
        if cpu is not None:
            stream['measured_thread_cpu_ms'] += cpu
            stream['cpu_windows'] += 1
        for state, metrics in states.items():
            if not isinstance(metrics, dict) or not metrics or not set(metrics) <= allowed_metrics:
                raise ValueError('Native frame metric role differs')
            totals = stream['states'].setdefault(state, {})
            for name, metric in metrics.items():
                count = validate_metric(metric)
                total = totals.setdefault(name, {'count': 0, '_sum_ms': 0, 'max_ms': 0,
                                                'over_125ms_count': 0, 'over_200ms_count': 0,
                                                'histogram': [0]*len(BOUNDS)})
                total['count'] += count
                total['_sum_ms'] += metric['mean_ms'] * count
                total['max_ms'] = max(total['max_ms'], metric['max_ms'])
                for threshold in (125, 200):
                    total[f'over_{threshold}ms_count'] += metric[f'over_{threshold}ms_count']
                total['histogram'] = [a+b for a, b in zip(total['histogram'], metric['histogram'])]
    for stream in streams.values():
        if not stream['cpu_windows']:
            stream['measured_thread_cpu_ms'] = None
        for metrics in stream['states'].values():
            for name, metric in metrics.items():
                metric['mean_ms'] = round(metric.pop('_sum_ms')/metric['count'], 3)
                metric['p50_upper_ms'] = quantile(metric['histogram'], 50)
                metric['p95_upper_ms'] = quantile(metric['histogram'], 95)
                if name in ('frame_interval', 'presentation_interval'):
                    metric['mean_cadence_hz'] = round(1000/metric['mean_ms'], 3) if metric['mean_ms'] else None
    return streams


def summarize_scene(scene_records):
    result = {}
    for record in scene_records:
        if set(record) != {'phase', 'milliseconds', 'success', 'ordinal', 'clock', 'bound_per_translation_unit'}:
            raise ValueError('Native scene schema differs')
        phase = record['phase']
        if not isinstance(phase, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,79}', phase):
            raise ValueError('Invalid native scene phase')
        elapsed = integer(record['milliseconds'])
        success = integer(record['success'], 0, 1)
        integer(record['ordinal'], 1, 128)
        if record['clock'] != 'GetTickCount' or integer(record['bound_per_translation_unit'], 128, 128) != 128:
            raise ValueError('Native scene clock or budget differs')
        row = result.setdefault(phase, {'calls': 0, 'successful_calls': 0, 'total_ms': 0,
                                      'max_ms': 0, 'samples_ms': []})
        row['calls'] += 1; row['successful_calls'] += success
        row['total_ms'] += elapsed; row['max_ms'] = max(row['max_ms'], elapsed)
        row['samples_ms'].append(elapsed)
    return result


def scene_entry(console, guest):
    ready = guest.get('character_reopen', {}).get('client_ready_evidence', {})
    ready_ms = ready.get('utc_ms')
    if type(ready_ms) is not int or ready.get('loaded_world_assets') is not True:
        return None
    connections = re.findall(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\] \[INFO\] Connecting to MapServer', console)
    times = [datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc).timestamp()*1000
             for value in connections]
    prior = [value for value in times if 0 <= ready_ms-value <= 600_000]
    if not prior:
        return None
    return {'client_connect_to_native_ready_seconds': round((ready_ms-max(prior))/1000, 6),
            'native_ready_utc_ms': ready_ms,
            'scope': 'First map connection through loaded-world CLIENT_READY; excludes character-selection delay.'}


def analyze(path):
    startup = analyze_startup(path)
    with zipfile.ZipFile(path) as outer:
        with zipfile.ZipFile(io.BytesIO(read_member(outer, 'guest-report.zip', 64*1024**2))) as guest_zip:
            guest = json.loads(read_member(guest_zip, 'latest-report.json', 8*1024**2))
            console = read_member(guest_zip, 'client-evidence/client-console.log', MAX_CONSOLE).decode('utf-8', errors='replace')
    frames = records(console, FRAME_PREFIX, MAX_FRAME_RECORDS)
    scenes = records(console, SCENE_PREFIX, MAX_SCENE_RECORDS)
    return {'format': 1, 'support_zip': startup['support_zip'], 'app_version': startup['app_version'],
            'startup': startup, 'scene_entry': scene_entry(console, guest),
            'native_frame_instrumentation_present': bool(frames), 'native_scene_instrumentation_present': bool(scenes),
            'native_frames': summarize_frames(frames), 'native_scene_phases_non_additive': summarize_scene(scenes),
            'native_frame_records': frames,
            'limitations': ['No GPU completion or Android/RFB display-latency measurement.',
                'Native interval cadence is separate from Android delivered frames.',
                'Thread CPU describes only the sampled main/render thread, not llvmpipe/Wine/FEX workers.',
                'Histogram percentiles are bucket upper bounds; null means overflow.',
                'Scene phases nest and must not be summed into startup or scene totals.',
                'Native diagnostics are bounded and may omit a final partial ten-second window.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('support_zip', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    raw = json.dumps(analyze(args.support_zip), indent=2, sort_keys=True)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(raw)
    else:
        print(raw, end='')


if __name__ == '__main__':
    main()
