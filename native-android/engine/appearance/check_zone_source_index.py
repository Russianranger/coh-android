#!/usr/bin/env python3
"""Check exact Huge supplement pins without materializing the source catalog."""
from pathlib import Path
import argparse
import json
import tempfile
from zone_source_index import zone_records

EXPECTED = {
    'data/player_library/huge_emblem.geo': {'bytes': 95950, 'sha256': '03f933720b45244ae025f46ac6004296193e52f0793b76ec94c977681da5425c'},
    'data/player_library/huge_uarmr.geo': {'bytes': 123414, 'sha256': 'd02570e14891fe5e49a9891164ee26ceabb3898f076628e251f2ad1a99e32500'},
    'data/player_library/huge_waist.geo': {'bytes': 19394, 'sha256': 'cd7dcb0bdb3320ea325abd51a69289deeb2b5e9dc8e95e2792ce13b0eda0c637'},
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    value = zone_records(args.manifest, paths=[name.upper() for name in EXPECTED], metadata_archives=['stage1.pigg'])
    assert value['files'] == EXPECTED
    identity = value['metadata_archives']['stage1.pigg']
    assert identity['source_metadata_bytes'] == 3698772 and identity['source_metadata_sha256'] == 'f6acbebf7181775cbba7b90e07ed690b095d59071049aec384c9f524b11bff02'
    controls = 2
    with tempfile.TemporaryDirectory(prefix='coh-zone-source-index-') as temporary:
        link = Path(temporary) / 'manifest.json'
        link.symlink_to(args.manifest.resolve())
        for path, requests in [(link, []), (args.manifest, ['../bad']), (args.manifest, ['x'] * 65)]:
            try:
                zone_records(path, paths=requests)
                raise AssertionError('Invalid supplement lookup accepted')
            except ValueError:
                controls += 1
    print(json.dumps({'passed': True, 'controls': controls, 'selected_genuine_geo_pins': len(EXPECTED),
                      'whole_catalog_retained': False}))


if __name__ == '__main__':
    main()
