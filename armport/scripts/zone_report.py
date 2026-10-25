#!/usr/bin/env python3
"""Export bounded M3 load diagnostics in a separate Actions step.

The ordinary smoke report can exhaust its annotation budget on asset warnings.
This report always reserves entries for load progress and sampled stacks.
"""
import argparse
import json
from pathlib import Path
import client_errors
import world_draw_report


def tail(text, limit=3600):
    return text if len(text) <= limit else '[earlier text omitted]\n' + text[-limit:]


def read(path):
    return path.read_text(errors='replace') if path.is_file() else ''


def sections(evidence, client):
    raw = read(evidence / 'login-driver.json')
    status = json.loads(raw) if raw else {}
    keys = ('client_started', 'client_exit', 'client_error', 'enter_by_layout',
            'play_sent', 'world_rendered', 'zone_load_seconds', 'diagnostic_seconds_excluded', 'loading_brightness', 'load_samples',
            'qa_notice_last_check', 'qa_notice_actions')
    summary = {key: status[key] for key in keys if key in status}
    raw = read(evidence / 'armport-game-report.json')
    report = json.loads(raw) if raw else {}
    record = report.get('game', {}).get('armport_client', {})
    summary['guest'] = {key: record.get(key) for key in (
        'connected_on_atlas', 'connected_utc', 'final_status', 'still_connected')}
    # Compact JSON keeps all 50 progress samples and brightness values intact.
    yield 'ArmPort M3 load status', json.dumps(summary, separators=(',', ':'))
    stdio = client / 'armport_stdio.txt'
    if stdio.is_file():
        trace = client / 'zone-trace.jsonl'
        errors = client_errors.inventory(stdio, evidence / 'client-errors.json',
                                         trace if trace.exists() else None)
        yield 'ArmPort M3 game errors', json.dumps(dict(count=errors['count'], unique=errors['unique'],
            inventory='client-errors.json', source=errors['source'],
            complete_messages=errors['complete_messages'], trace_record_count=errors['trace_records'],
            integrity_failures=errors['integrity_failures'],
            phase_counts=errors['phase_counts'], examples=errors['errors'][:3]))
    traces = [line for line in read(client / 'armport_stdio.txt').splitlines()
              if line.startswith('ArmPort zone: ')]
    world = world_draw_report.summarize(traces)
    (evidence / 'world-draw-summary.json').write_text(json.dumps(world, indent=2) + '\n')
    yield 'ArmPort M3 world traversal', json.dumps(
        {key: value for key, value in world.items() if key != 'samples'}, separators=(',', ':'))
    if status.get('frame_checks'):
        yield 'ArmPort M3 final frame check', json.dumps(status['frame_checks'][-1], separators=(',', ':'))
    if status.get('qa_notice_actions'):
        yield 'ArmPort M3 QA notice input', json.dumps(status['qa_notice_actions'], separators=(',', ':'))
    yield 'ArmPort M3 zone stages', tail('\n'.join(line for line in traces if ' library.' not in line)) or 'no zone traces'
    yield 'ArmPort M3 library progress', tail('\n'.join(line for line in traces if ' library.' in line)) or 'no library traces'
    for path in sorted(evidence.glob('stall-*.txt'))[:2]:
        text = read(path)
        # Full samples are in the artifact. Keep main-thread frames, thread
        # states and PE symbolization in annotations instead of Mesa workers.
        selected = [line for line in text.splitlines() if not line.startswith('task ')]
        yield 'ArmPort M3 ' + path.stem, tail('\n'.join(selected))
    yield 'ArmPort M3 mapserver tail', tail(read(evidence / 'first-atlas-stdout.txt')) or 'no mapserver output'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--evidence', type=Path, required=True)
    ap.add_argument('--client', type=Path, required=True)
    a = ap.parse_args()
    for title, body in sections(a.evidence, a.client):
        print('--- ' + title + '\n' + body)
        body = tail(body, 3700).replace('%', '%25').replace('\r', '').replace('\n', '%0A')
        print(f'::notice title={title}::{body}')


if __name__ == '__main__':
    main()
