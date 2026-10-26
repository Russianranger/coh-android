#!/usr/bin/env python3
"""Inspect every entry in the 15 pinned audio metadata tables; fetch no payloads."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/android/interactive'))
import discover_client_visual_sweep as sweep


def audit(identities, cache):
    sweep.require(len(identities) == 15 and len({r['archive'] for r in identities}) == 15,
                  'Expected exactly 15 distinct audio archives')
    sweep.require(all(r['archive'].startswith('sound') and '/' not in r['archive']
                      and '\\' not in r['archive'] and r['archive'].endswith('.pigg') for r in identities),
                  'Expected audio archive names')
    sweep.require(sum(r['source_metadata_bytes'] for r in identities) <= 1024 * 1024,
                  'Audio metadata exceeds audit budget')
    results = []
    for identity in identities:
        selected = sweep.metadata(identity, cache)
        raw = (cache / identity['archive']).read_bytes()
        _, _, _, hs, es, count = sweep.inspect_piggs.HEADER.unpack_from(raw)
        names, _ = sweep.inspect_piggs.pool(raw, hs + count * es, 0x6789)
        paths = []
        for index in range(count):
            entry = sweep.inspect_piggs.ENTRY.unpack_from(raw, hs + index * es)
            paths.append(sweep.inspect_piggs.safe_name(names[entry[1]]))
        sweep.require(len(paths) == len({p.casefold() for p in paths}) == count,
                      'Incomplete or duplicate file table')
        results.append(dict(identity=identity, file_count=count, paths=sorted(paths),
                            texture_geometry_paths=sorted(selected)))
    return dict(scope='complete pinned audio file tables only; no payload retrieval or exception activation',
                archives=results, archive_count=len(results),
                file_count=sum(r['file_count'] for r in results),
                metadata_bytes=sum(r['identity']['source_metadata_bytes'] for r in results),
                texture_geometry_count=sum(len(r['texture_geometry_paths']) for r in results))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--identities', type=Path, default=ROOT / 'assets/zones-audio-metadata.json')
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.identities.read_bytes()
    report = audit(json.loads(raw), args.cache)
    report['identities_sha256'] = hashlib.sha256(raw).hexdigest()
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('archive_count', 'file_count', 'metadata_bytes',
                                           'texture_geometry_count', 'identities_sha256')}))
