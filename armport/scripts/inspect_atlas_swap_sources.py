#!/usr/bin/env python3
"""Metadata-only exact-name inspection for the Atlas 40189560565 swap warning."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/android/interactive'))
import discover_client_visual_sweep as sweep

TARGETS = {'tickertape_steel_canyon_south', 'tickertape_talos_island'}


def inspect(cache):
    manifest = ROOT / 'armport/evidence/m3-approved-range-assets.json'
    identities = json.loads(manifest.read_text())['metadata_archives']
    sweep.require(sum(r['source_metadata_bytes'] for r in identities) <= 40 * 1024**2,
                  'Frozen metadata exceeds budget')
    def scan(identity):
        rows = sweep.metadata(identity, cache)
        return [{k: v for k, v in row.items() if k != 'cached_header'}
                for path, row in rows.items()
                if path.startswith('texture_library/') and Path(path).stem in TARGETS]
    with ThreadPoolExecutor(max_workers=2) as pool:
        matches = [row for found in pool.map(scan, identities) for row in found]
    return dict(run_id=40189560565, requests=sorted(TARGETS),
                metadata_archives=identities, matches=matches, payloads_fetched=False,
                scope='exact-name source inspection only; no staging or acceptance change')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = inspect(args.cache)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(archives=len(report['metadata_archives']), matches=report['matches'])))
