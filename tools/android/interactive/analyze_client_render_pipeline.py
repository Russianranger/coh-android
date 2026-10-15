#!/usr/bin/env python3
"""Summarize bounded native render phases and worker dispatch/gaps from a Thor ZIP.

The existing frame/renderer report is retained. New pipeline streams are never
ordinal-joined, and sampled dispatch/gap durations are not GPU completion times.
"""
import argparse
import io
import json
from pathlib import Path
import zipfile

import analyze_client_renderer_performance as renderer

PREFIX = 'COH_CLIENT_RENDER_PIPELINE_V1 '
MAX_RECORDS = 2 * 120
MAIN_METRICS = frozenset(('gfx_wall', 'aux_viewport_wall', 'main_viewport_wall',
    'sun_wall', 'postprocessing_wall', 'ui_wall', 'finish_wall', 'queue_flush_wall'))
RENDERER_METRICS = frozenset(('renderer_batch_wall', 'renderer_command_wall',
    'renderer_queue_gap_wall'))
WINDOW_FIELDS = frozenset(('format', 'event', 'role', 'report', 'window_ms',
    'scope', 'thread_cpu_ms', 'incomplete_batches', 'bucket_upper_ms', 'metrics'))
SAMPLE_FIELDS = frozenset(('sample_interval', 'sampled_batches', 'sampled_command_count'))
METRIC_FIELDS = frozenset(('count', 'mean_ms', 'max_ms', 'p95_upper_ms', 'histogram'))


def pipeline_records(console):
    rows = []
    for line in console.splitlines():
        if PREFIX not in line:
            continue
        raw = line.split(PREFIX, 1)[1]
        if len(raw) > 16384 or len(rows) >= MAX_RECORDS:
            raise ValueError('Render pipeline report budget exceeded')
        rows.append(renderer.strict_json(raw))
    return rows


def validate_pipeline(rows):
    """Reject malformed or incomplete bounded streams before reporting timings."""
    previous = {}
    for row in rows:
        if renderer.scene.integer(row.get('format'), 1, 1) != 1:
            raise ValueError('Render pipeline format differs')
        role = row.get('role')
        fields = WINDOW_FIELDS | (SAMPLE_FIELDS if role == 'renderer' else set())
        if row.get('event') != 'window' or role not in ('main', 'renderer') or set(row) != fields:
            raise ValueError('Render pipeline window schema or role differs')
        if row['scope'] != ('gameplay' if role == 'main' else 'all_states_independent'):
            raise ValueError('Render pipeline scope differs from role')
        index = renderer.scene.integer(row['report'], 1, 120)
        if index != previous.get(role, 0) + 1:
            raise ValueError('Render pipeline window sequence differs')
        previous[role] = index
        renderer.scene.number(row['window_ms'], 10000)
        if row['thread_cpu_ms'] is not None:
            renderer.scene.number(row['thread_cpu_ms'])
        renderer.scene.integer(row['incomplete_batches'])
        if row['bucket_upper_ms'] != renderer.scene.BOUNDS:
            raise ValueError('Render pipeline histogram bounds differ')
        metrics = row['metrics']
        if role == 'renderer':
            renderer.scene.integer(row['sample_interval'], 16, 16)
            batches = renderer.scene.integer(row['sampled_batches'], 0, 10_000_000)
            commands = renderer.scene.integer(row['sampled_command_count'], 0, 2**32 - 1)
            if not batches and commands:
                raise ValueError('Render pipeline commands exist without sampled batches')
        allowed = (MAIN_METRICS if role == 'main' else RENDERER_METRICS if batches
            else frozenset(('renderer_batch_wall',)))
        if not isinstance(metrics, dict) or set(metrics) != allowed:
            raise ValueError('Render pipeline metric role differs')
        for metric in metrics.values():
            if not isinstance(metric, dict) or set(metric) != METRIC_FIELDS:
                raise ValueError('Render pipeline metric schema differs')
            renderer.validate_distribution(metric)
        if role == 'main':
            if len({metric['count'] for metric in metrics.values()}) != 1:
                raise ValueError('Render pipeline per-frame metric counts differ')
        else:
            if (metrics['renderer_batch_wall']['count'] < batches
                    or (batches and (metrics['renderer_command_wall']['count'] != batches
                    or metrics['renderer_queue_gap_wall']['count'] != batches))):
                raise ValueError('Render pipeline sampled metric counts differ')


def summarize_pipeline(rows):
    """Pool each metric by its own sample count without joining native threads."""
    streams = {}
    for row in rows:
        stream = streams.setdefault(row['role'], {'reports': [], 'window_ms': 0,
            'cpu_windows': 0, 'measured_thread_cpu_ms': 0, 'incomplete_batches': 0,
            'native_record_scope': row['scope'], 'metrics': {}})
        stream['reports'].append(row['report'])
        stream['window_ms'] += row['window_ms']
        stream['incomplete_batches'] += row['incomplete_batches']
        if row['thread_cpu_ms'] is not None:
            stream['measured_thread_cpu_ms'] += row['thread_cpu_ms']
            stream['cpu_windows'] += 1
        if row['role'] == 'renderer':
            stream['sample_interval'] = row['sample_interval']
            for key in ('sampled_batches', 'sampled_command_count'):
                stream[key] = stream.get(key, 0) + row[key]
        for name, value in row['metrics'].items():
            metric = stream['metrics'].setdefault(name, {'count': 0,
                '_sum_ms': 0, 'max_ms': 0, 'histogram': [0] * len(renderer.scene.BOUNDS)})
            metric['count'] += value['count']
            metric['_sum_ms'] += value['mean_ms'] * value['count']
            metric['max_ms'] = max(metric['max_ms'], value['max_ms'])
            metric['histogram'] = [a + b for a, b in zip(metric['histogram'], value['histogram'])]
    for stream in streams.values():
        stream['window_ms'] = round(stream['window_ms'], 3)
        if stream['cpu_windows'] == 0:
            stream['measured_thread_cpu_ms'] = None
        for metric in stream['metrics'].values():
            total = metric.pop('_sum_ms')
            metric['sample_sum_ms'] = round(total, 3)
            metric['mean_ms'] = round(total / metric['count'], 3)
            for percent in (50, 95):
                metric[f'p{percent}_upper_ms'] = renderer.scene.quantile(metric['histogram'], percent)
    worker = streams.get('renderer')
    if worker:
        active = worker['metrics'].get('renderer_command_wall', {}).get('sample_sum_ms')
        gap = worker['metrics'].get('renderer_queue_gap_wall', {}).get('sample_sum_ms')
        worker['sampled_dispatch_fraction_of_sampled_span'] = (
            round(active / (active + gap), 6) if active is not None and active + gap else None)
        worker['sampled_span_ms'] = round(active + gap, 3) if active is not None else None
        worker['scope'] = ('Batch wall measures all completed renderer batches. Command and gap '
            'metrics measure sampled batches only; gap includes scheduling, upstream command '
            'production and instrumentation overhead. Active dispatch can include driver waits.')
    if 'main' in streams:
        streams['main']['scope'] = ('Gameplay main gfx frames; phase and flush '
            'metrics may overlap and must not be summed or equated with pure CPU scene time.')
        streams['main']['window_clock_scope'] = ('Window wall/CPU boundaries can include intervening '
            'menus, loading or inactivity. Gameplay-only per-frame CPU must not be derived '
            'from these window CPU totals without proving an uninterrupted interval.')
    return streams


def producer_summary(guest):
    """Keep the .22 current producer separate from its frozen .19 ancestor."""
    current = guest.get('client_render_pipeline')
    ancestor = guest.get('client_renderer_attribution')
    environment = guest.get('client_render_pipeline_environment')
    for label, value in (('current Game producer', current), ('ancestor producer', ancestor),
                         ('pipeline environment', environment)):
        if value is not None and not isinstance(value, dict):
            raise ValueError('Render pipeline ' + label + ' must be an object')
    top_sha = guest.get('client_executable_sha256')
    checks = []
    if current is not None:
        current_sha = current.get('client_executable_sha256')
        if top_sha is not None and current_sha is not None:
            checks.append(top_sha == current_sha)
        if environment is not None and environment.get('enabled') is True:
            for left, right in (('client_executable_sha256', 'client_executable_sha256'),
                                ('manifest_sha256', 'producer_manifest_sha256')):
                if current.get(left) is not None and environment.get(right) is not None:
                    checks.append(current[left] == environment[right])
        if ancestor is not None:
            for left, right in (('base_client_executable_sha256', 'client_executable_sha256'),
                    ('base_client_renderer_attribution_manifest_sha256', 'manifest_sha256')):
                if current.get(left) is not None and ancestor.get(right) is not None:
                    checks.append(current[left] == ancestor[right])
    if checks and not all(checks):
        raise ValueError('Render pipeline current/ancestor/environment producer identity differs')
    return {'current_render_pipeline_producer_receipt': current,
        'retained_renderer_attribution_producer_receipt': ancestor,
        'pipeline_environment_receipt': environment,
        'top_level_current_Game_executable_sha256': top_sha,
        'supplied_identity_checks': len(checks),
        'supplied_identity_fields_consistent': all(checks) if checks else None,
        'current_producer_verified_by_guest_report': current.get('verified') if current else None,
        'source_closure_reverified_by_host_analysis': False,
        'scope': ('The current client_render_pipeline receipt identifies the .22 Game; '
            'client_renderer_attribution remains a historical parent. Missing producer '
            'or environment fields remain missing; log parsing does not qualify the native source closure.')}


def analyze(path):
    result = renderer.analyze(path)
    with zipfile.ZipFile(path) as outer:
        raw = renderer.thor.read_member(outer, 'guest-report.zip', renderer.thor.MAX_GUEST_ZIP)
    with zipfile.ZipFile(io.BytesIO(raw)) as inner:
        guest = renderer.strict_json(renderer.thor.read_member(inner, 'latest-report.json', renderer.thor.MAX_REPORT))
        present = any(item.filename == 'client-evidence/client-console.log' for item in inner.infolist())
        console = (renderer.thor.read_member(inner, 'client-evidence/client-console.log',
            renderer.scene.MAX_CONSOLE).decode('utf-8', errors='replace') if present else '')
    rows = pipeline_records(console)
    validate_pipeline(rows)
    result['native_render_pipeline_present'] = bool(rows)
    result['render_pipeline_streams_all_states_unaligned'] = summarize_pipeline(rows)
    result['render_pipeline_Game_source_attribution'] = producer_summary(guest)
    current = result['render_pipeline_Game_source_attribution']['current_render_pipeline_producer_receipt']
    if current is not None:
        backend = result['gpu_profile_and_actual_backend']
        backend['inherited_renderer_attribution_producer'] = backend['game_producer']
        backend['game_producer'] = {key: current.get(key)
            for key in ('repository_commit', 'client_executable_sha256', 'manifest_sha256')}
        backend['game_producer_scope'] = 'current_render_pipeline_Game_receipt'
    result['render_pipeline_limitations'] = [
        'No pipeline record means missing instrumentation, not zero rendering work.',
        'Main and renderer report boundaries are independent; ordinals do not establish frame correspondence.',
        'Main pipeline records explicitly scope gameplay; renderer records span all states independently. Neither has cap labels or cross-stream frame identities.',
        'Main phase and queue-flush durations overlap; phases and threads must not be added.',
        'Renderer command/gap durations cover the first then every 16th batch, not all batches. Sampling can miss stalls.',
        'Renderer batch wall includes active dispatch, queue starvation, scheduling and timing overhead.',
        'Active dispatch includes driver waits; gap includes upstream command production and scheduling. Neither is GPU duration.',
        'Thread CPU samples cover only the measured thread. Missing CPU data remains missing.',
        'Gameplay main phase counts exclude non-gameplay gfx calls, but window wall/CPU totals can include time between those calls; they are not gameplay-only CPU totals.',
        'Current .22 Game producer receipts are separate from retained .19 ancestor receipts; the host analyzer does not requalify their source closure.',
        'Histogram p50/p95 are bucket upper bounds. Cadence gains require a physical comparison at retained fidelity.',
        'This analysis does not change strict save acceptance, cleanup status or gameplay qualification.']
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
