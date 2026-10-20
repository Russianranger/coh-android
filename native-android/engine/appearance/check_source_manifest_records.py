#!/usr/bin/env python3
"""Focused checks for the existing pinned CLIENT manifest streaming selector."""
import argparse
import json
import tempfile
from pathlib import Path
from source_manifest_records import selected_records

PANTS = 'data/player_library/huge_pants.geo'
PANTS_SIZE = 119625
PANTS_SHA = '579f8e31c4e2d9a1ca89e120634f7b58dc520b2a7a114a9557c3607c6cc6509b'


def require(value, message):
    if not value:
        raise AssertionError(message)


def run(manifest):
    cases = 0

    def refused(path, names):
        nonlocal cases
        try:
            selected_records(path, names)
        except ValueError:
            cases += 1
            return
        raise AssertionError('Invalid manifest selection was admitted')

    refused(manifest, [])
    refused(manifest, [PANTS, PANTS.upper()])
    refused(manifest, [str(i) for i in range(65)])
    wrapper = json.loads(manifest.read_text())
    with tempfile.TemporaryDirectory(prefix='coh-manifest-record-controls-') as directory:
        directory = Path(directory)
        link = directory / 'symlink.json'
        link.symlink_to(manifest.resolve())
        refused(link, [PANTS])
        bad = directory / 'duplicate.json'
        bad.write_text('{"format":1,"format":1}')
        refused(bad, [PANTS])
        altered = dict(wrapper, decoded=dict(wrapper['decoded'], bytes=1))
        bad = directory / 'decoded-pin.json'
        bad.write_text(json.dumps(altered))
        refused(bad, [PANTS])
        altered = dict(wrapper, gzip=dict(wrapper['gzip'], sha256='0' * 64))
        bad = directory / 'gzip-pin.json'
        bad.write_text(json.dumps(altered))
        refused(bad, [PANTS])
    # One complete stream pass: original provenance fields survive unchanged,
    # while case-insensitive matching preserves the caller's requested key.
    result = selected_records(manifest, [PANTS.upper()])
    require(set(result) == {PANTS.upper()}, 'Requested key spelling changed')
    record = result[PANTS.upper()]
    require(record['bytes'] == PANTS_SIZE and record['sha256'] == PANTS_SHA,
            'Original Huge pants source identity differs')
    require(record['offset'] == 42509338 and record['stored_bytes'] == 100264
            and record['source_url'] == 'https://dists.thunderspy.org/piggs/stage1.pigg',
            'Original range provenance fields changed')
    cases += 1
    return {'passed': True, 'cases': cases, 'original_record_fields_preserved': True,
            'whole_decoded_catalog_retained': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.manifest)))
