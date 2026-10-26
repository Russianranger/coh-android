#!/usr/bin/env python3
"""Itemize isolated dispatch errors without accepting any of them."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def itemize(path):
    rows, active, started, ended, last = [], None, False, False, None
    for number, line in enumerate(path.read_text().splitlines(), 1):
        row = json.loads(line)
        stage = row['stage']
        if stage == 'replay.dispatch.begin':
            active = last = int(row['text'])
            started = True
        elif stage == 'replay.dispatch.end':
            active = None
        elif stage == 'replay.drain.end':
            ended = True
        elif stage == 'client.error' and started and not ended:
            rows.append(dict(text=row['text'], tid=row['tid'], dispatch_index=active,
                after_dispatch_index=last if active is None else None, trace_line=number,
                error_class='missing_texture' if row['text'].startswith('CUSTOM TEXTURE ERROR:')
                else 'mission_room' if row['text'].startswith('mission.c: Room ') else 'other'))
    return dict(trace_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                count=len(rows), occurrences=rows)


def literal_counts(rows):
    return Counter((r['text'], r['dispatch_index'], r['after_dispatch_index']) for r in rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm64', type=Path, required=True)
    parser.add_argument('--i686', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = {name: itemize(path) for name, path in [('arm64', args.arm64), ('i686', args.i686)]}
    result['literal_text_count_index_equal'] = literal_counts(result['arm64']['occurrences']) == literal_counts(result['i686']['occurrences'])
    result['all_three_runs_available'] = False
    result['exceptions_enabled'] = False
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v['count'] if isinstance(v, dict) else v for k, v in result.items()}))
