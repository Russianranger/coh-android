#!/usr/bin/env python3
"""Audit every named maps.db destination against pinned source/donor resources.

Includes stock map import/library/scene/sky closure and original geometry
submodels; reports missing source-era definitions separately from archive bytes.
Only a native map load can establish collision and authentic beacon readiness.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

import audit_kings_row_foundation as kings
import client_visual_geometry as geometry
import client_visual_tricks as tricks
import prepare_zones_world_assets as zones

ROOT = Path(__file__).resolve().parents[3]


class AllZoneSources(kings.Sources):
    """Pinned legacy Windows map text may contain non-UTF8 comment bytes.

    Preserve those byte values one-to-one; native command/path keywords remain
    ASCII. Every fallback file is recorded, and its original SHA is unchanged.
    """
    def __init__(self, root):
        super().__init__(root)
        self.legacy_byte_text = set()

    def read(self, name):
        try:
            return super().read(name)
        except UnicodeDecodeError:
            name = kings.data_path(name)
            raw = (self.root / 'upstream/i24' / self.entries[name]['path']).read_bytes()
            zones.require(kings.pin_bytes(raw) == self.pins['upstream/i24/' + self.entries[name]['path']],
                          'Legacy source changed during decoding')
            self.legacy_byte_text.add(name)
            self.rows[name] = list(kings.source_tokens(raw.decode('latin-1')))
            return self.rows[name]


def map_records(root):
    raw = (root / 'upstream/i24/data/server/db/maps.db').read_text()
    rows = []
    for match in re.finditer(r'(?ms)^Container (\d+)\s*\n(.*?)^ContainerEnd', raw):
        name = re.search(r'(?m)^\s*MapName\s+"([^"]+)"', match[2])
        if name:
            key = re.search(r'(?m)^\s*MapKey\s+(\S+)', match[2])
            rows.append({'map_id': int(match[1]), 'map': name[1].replace('\\', '/').casefold(),
                         'key': key[1] if key else None})
    return rows


def audit(root, cache, kings_audit=None):
    retained, records, originals, current = kings.retained_inventory(root)
    sources = AllZoneSources(root)
    all_resources, visual_archives, visual = {}, {}, {}
    for identity in current['provenance']['metadata_archives']:
        all_resources.update(zones.all_metadata(identity, cache)[0])
        rows = kings.sweep.metadata(identity, cache)
        visual.update(rows); visual_archives[identity['archive']] = rows
    visual = kings.preserve_retained_headers(visual, visual_archives, retained, records, originals)
    sounds = defaultdict(list)
    for name in all_resources:
        if name.endswith('.ogg'):
            sounds[PurePosixPath(name).stem].append(name)
    output = {'format': 1, 'scope': 'all_named_stock_destinations_original_asset_inventory_v1',
        'source_commit': kings.SOURCE, 'data_commit': kings.DATA,
        'frozen_metadata_archive_count': len(current['provenance']['metadata_archives']),
        'available_resource_count': len(all_resources),
        'maps': [], 'physical_all_zone_qualification': False,
        'full_dynamic_source_dependency_closure': False,
        'limitations': ['All named static maps are audited; clone IDs inherit their BaseMapID world.',
            'Whole library traversal conservatively includes unused authored variants.',
            'Source and payload integrity do not qualify collision, pathing, arrival or save.',
            'Generated donor BIN/bounds caches are deliberately excluded; native source-compatible caches must be used.']}
    for entry in map_records(root):
        if entry['map'] not in sources.entries:
            output['maps'].append({**entry, 'source_present': False, 'source_graph_complete': False})
            continue
        request = kings.group_requests(sources, entry['map'])
        models_missing, geometry_absent, malformed_headers = [], [], []
        for name, rows in request['geometry'].items():
            original = visual.get(name.removeprefix('data/'))
            if original is None:
                geometry_absent.append(name); continue
            try:
                proof = geometry.requested_model_proof(original['cached_header'], rows)
                if proof['absent_requested_models']:
                    models_missing.append({'geometry': name, 'models': proof['absent_requested_models']})
            except ValueError as error:
                malformed_headers.append({'geometry': name, 'reason': str(error)})
        audio = {}
        for name in request['map_files'] + request['library_files']:
            encoded = (root / 'upstream/i24' / sources.entries[name]['path']).read_bytes()
            raw = encoded.decode('latin-1' if name in sources.legacy_byte_text else 'utf-8-sig')
            for line, tokens in kings.costumes.line_tokens(raw):
                if len(tokens) > 1 and tokens[0].casefold() == 'sound':
                    audio.setdefault(tokens[1].casefold(), []).append({'source': name, 'line': line})
        row = {**entry, 'source_present': True, 'source_graph_complete': not request['unresolved_source_edges'],
            'map_files': len(request['map_files']), 'library_files': len(request['library_files']),
            'geometry_requests': len(request['geometry']),
            'new_geometry_files': sorted(set(request['geometry']) - set(retained)),
            'missing_original_geometry_files': geometry_absent,
            'missing_original_submodels': models_missing,
            'geometry_header_gaps': malformed_headers,
            'source_graph_gaps': request['unresolved_source_edges'],
            'authored_map_library_sound_names': sorted(audio),
            'missing_original_sound_names': {name: witness for name, witness in audio.items()
                if name not in sounds and name not in ('none', 'null')},
            'native_collision_verified': False, 'native_beacon_graph_verified': False,
            'map_enabled_by_this_audit': False}
        output['maps'].append(row)
        print(json.dumps({'map_audited': entry['map_id'], 'key': entry['key']}), flush=True)
    output['legacy_source_byte_decoding'] = sorted(sources.legacy_byte_text)
    output['summary'] = {'named_maps': len(output['maps']),
        'source_present': sum(row['source_present'] for row in output['maps']),
        'source_graph_complete': sum(row['source_graph_complete'] for row in output['maps']),
        'maps_with_missing_original_geometry': sum(bool(row.get('missing_original_geometry_files')) for row in output['maps']),
        'maps_with_missing_original_submodels': sum(bool(row.get('missing_original_submodels')) for row in output['maps']),
        'maps_with_missing_original_sound_names': sum(bool(row.get('missing_original_sound_names')) for row in output['maps'])}
    if kings_audit:
        data = json.loads(kings_audit.read_bytes())
        output['kings_row_complete_appearance_review'] = {
            'source_audit_pin': zones.pin(kings_audit),
            'source_graph_gaps': data['source_graph']['unresolved_source_edges'],
            'visual_dependency_gaps': data['plan']['unresolved_dependencies'],
            'candidate_counts': data['plan']['summary'],
            'all_available_candidates_in_supplement': all(
                name in all_resources for name in data['plan']['selected_original_candidates']),
            'full_dynamic_closure': False}
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--metadata-cache', type=Path, required=True)
    parser.add_argument('--kings-audit', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    zones.require(not args.output.exists(), 'Preserve existing audit output')
    result = audit(args.root, args.metadata_cache, args.kings_audit)
    args.output.write_bytes(zones.canonical(result) + b'\n')
    print(json.dumps(result['summary'], sort_keys=True))


if __name__ == '__main__':
    main()
