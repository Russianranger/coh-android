#!/usr/bin/env python3
"""Reproduce exact-name discovery for the 14 user-approved M3 asset requests.

Reads only the previously frozen metadata prefixes, then selected ranges for
unique exact matches. Does not follow composite dependencies or similar names.
Writes a new candidate directory; it never updates the committed manifest.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys

from stage_approved_ranges import ROOT, GEOMETRY, TEXTURES, require
sys.path.insert(0, str(ROOT / 'tools/android/interactive'))
import prepare_client_visual_assets as visual
import discover_client_visual_sweep as sweep
import prepare_atlas_world_assets as donor


def discover(output, cache):
    require(not output.exists() and not output.is_symlink(), 'Discovery output exists')
    baseline = visual.read_manifest(ROOT / 'assets/client-visual-manifest.json')
    identities = baseline['provenance']['metadata_archives']
    require(sum(row['source_metadata_bytes'] for row in identities) <= 40 * 1024**2,
            'Frozen metadata exceeds discovery bound')
    matches = {name: [] for name in sorted(GEOMETRY | TEXTURES)}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for rows in pool.map(lambda identity: sweep.metadata(identity, cache), identities):
            for path, row in rows.items():
                key = path if path in GEOMETRY else Path(path).stem
                if path in GEOMETRY or (path.startswith('texture_library/') and key in TEXTURES):
                    matches[key].append(row)
    require(all(len(rows) <= 1 for rows in matches.values()), 'Ambiguous exact donor match')
    result = []
    for request, rows in matches.items():
        if not rows:
            continue
        row = rows[0]
        stored, _ = sweep.ranges.partial(sweep.ranges.BASE_URL + row['identity']['archive'],
                                         row['offset'], row['stored_bytes'], row['identity'])
        record = sweep.verified_payload(row, stored)
        result.append(('data/' + row['path'].casefold(), record, stored))
    require(result, 'No exact approved donor matches')
    output.mkdir(parents=True)
    archive = output / 'm3-approved-assets.zip'
    donor.write_donor_zip(archive, result)
    report = dict(format=1, scope='user_approved_m3_dispatch_missing_files',
        approval='https://github.com/Russianranger/coh-android/pull/6#issuecomment-6386664502',
        requests=list(matches),
        matches={name: [dict(archive=r['identity']['archive'], path=r['path']) for r in rows]
                 for name, rows in matches.items()},
        unresolved=sorted(name for name, rows in matches.items() if not rows),
        files={name: {key: r[key] for key in ('bytes', 'sha256')} for name, r, _ in result},
        provenance={name: r for name, r, _ in result}, file_count=len(result),
        payload_bytes=sum(r['bytes'] for _, r, _ in result), archive=donor.pin(archive),
        metadata_archives=identities,
        source_archives_fully_downloaded=False, source_archive_sha256_verified=False,
        runtime_validated=False)
    (output / 'm3-approved-range-assets.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(files=report['file_count'], bytes=report['payload_bytes'], unresolved=report['unresolved'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--metadata-cache', type=Path, required=True)
    args = parser.parse_args()
    discover(args.output, args.metadata_cache)
