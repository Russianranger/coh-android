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
import io
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

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
        # All 66 stock worlds share one cache; retain a separate finite host
        # bound while the focused Kings Row audit keeps its original limits.
        super().__init__(root, max_source_files=32768, max_source_total=1024 * 1024**2)
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


def observed_client_gaps(report, supplement, root=ROOT):
    """Account for recorded native errors without converting metadata to FPS proof."""
    with zipfile.ZipFile(report) as outer:
        zones.require(outer.getinfo('android-client-report.json').file_size <= 1024**2,
                      'Android report metadata exceeds audit bound')
        android_report = json.loads(outer.read('android-client-report.json'))
        zones.require(outer.getinfo('guest-report.zip').file_size <= 64 * 1024**2,
                      'Nested report exceeds audit bound')
        with zipfile.ZipFile(io.BytesIO(outer.read('guest-report.zip'))) as guest:
            zones.require(guest.getinfo('client-evidence/client-console.log').file_size <= 32 * 1024**2,
                          'Native console exceeds audit bound')
            raw = guest.read('client-evidence/client-console.log')
    text = raw.decode('utf-8', errors='replace')
    categories = {
        'missing_trick_texture': re.findall(r'Texture Trick "[^"]+" references missing texture "([^"]+)"', text),
        'missing_custom_texture': re.findall(r'CUSTOM TEXTURE ERROR: texture not found: ([^\r\n]+)', text),
        'missing_player_texture': re.findall(r"Player texture \d+ '([^']+)'[^\r\n]+ not found", text)}
    retained = kings.retained_inventory(root)[0]
    value = zones.frozen_manifest(root)
    leaves = {PurePosixPath(name).stem for name in set(retained) | set(value['files'])
              if name.endswith('.texture')}
    old_leaves = {PurePosixPath(name).stem for name in retained if name.endswith('.texture')}
    stock, _ = tricks.stock_tricks(root)
    roots = defaultdict(list)
    for category, names in categories.items():
        for name in names:
            roots[tricks.texture_stem(name)].append({'scope': category, 'alias': name, 'target': name})
    closure = tricks.resolve_trick_closure(stock, roots, native_texture_names=leaves)
    composites = {tricks.texture_stem(item['name']) for item in closure['stock_definition_closure']
                  if item['composite_generation']['composite_alias_can_be_created']}
    category_results = {}
    for category, names in categories.items():
        keys = {tricks.texture_stem(name) for name in names}
        category_results[category] = {'recorded_occurrences': len(names), 'unique_keys': len(keys),
            'new_original_texture_keys_in_pack': sorted(keys & (leaves - old_leaves)),
            'already_retained_texture_keys': sorted(keys & old_leaves),
            'stock_composite_alias_keys': sorted((keys - leaves) & composites),
            'unresolved_literal_keys': sorted(keys - leaves - composites),
            'native_retest_verified': False}
    geometry_name = 'data/object_library/fx/flags/flag_01.geo'
    with zipfile.ZipFile(supplement) as archive:
        body = archive.read(geometry_name)
    zones.require(kings.pin_bytes(body) == value['files'][geometry_name], 'Flag geometry differs')
    proof = geometry.requested_model_proof(body, [{'model': 'GEO_Flag_04'}, {'model': 'GEO_Flag_Harness_04'}])
    return {'report_archive': zones.pin(report), 'native_console': kings.pin_bytes(raw),
        'source_apk_version': android_report.get('app_version'),
        'observed_fileerror_blocks': text.count('ERRORLOG FILEERROR:'),
        'categories': category_results, 'flag_geometry': {'file': geometry_name, **proof},
        'expanded_missing_source_texture_keys': sorted(set(closure['requests']) - leaves - composites),
        'ambiguous_stock_definitions': closure['ambiguous_stock_definitions'],
        'composite_cycles': closure['cycles'],
        'limitations': ['Each major error category was capped at 1,024 occurrences in the native report.',
            'File/model availability is host evidence, not proof of physical rendering or improved FPS.',
            'A stock composite alias still requires its surviving leaf dependencies and native runtime generation.']}


def audit(root, cache, kings_audit=None):
    retained, records, originals, current = kings.retained_inventory(root)
    sources = AllZoneSources(root)
    audio_by_source = {}
    all_resources, visual_archives, visual = {}, {}, {}
    for identity in current['provenance']['metadata_archives']:
        all_resources.update(zones.all_metadata(identity, cache)[0])
        rows = kings.sweep.metadata(identity, cache)
        visual.update(rows); visual_archives[identity['archive']] = rows
    audio_metadata_path = root / 'assets/zones-audio-metadata.json'
    standalone_audio = json.loads(audio_metadata_path.read_bytes()) if audio_metadata_path.is_file() else []
    for identity in standalone_audio:
        all_resources.update(zones.all_metadata(identity, cache)[0])
    visual = kings.preserve_retained_headers(visual, visual_archives, retained, records, originals)
    sounds = defaultdict(list)
    for name in all_resources:
        if name.endswith('.ogg'):
            sounds[PurePosixPath(name).stem].append(name)
    output = {'format': 1, 'scope': 'all_named_stock_destinations_original_asset_inventory_v1',
        'source_commit': kings.SOURCE, 'data_commit': kings.DATA,
        'frozen_metadata_archive_count': len(current['provenance']['metadata_archives']) + len(standalone_audio),
        'standalone_audio_metadata': standalone_audio,
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
            if name not in audio_by_source:
                encoded = (root / 'upstream/i24' / sources.entries[name]['path']).read_bytes()
                raw = encoded.decode('latin-1' if name in sources.legacy_byte_text else 'utf-8-sig')
                sounds_in_file = []
                for line, text in enumerate(kings.costumes.strip_comments(raw).splitlines(), 1):
                    if re.match(r'^\s*Sound\s+', text, re.I):
                        tokens = next(kings.costumes.line_tokens(text))[1]
                        if len(tokens) > 1:
                            sounds_in_file.append((tokens[1].casefold(), line))
                audio_by_source[name] = sounds_in_file
            for sound_name, line in audio_by_source[name]:
                audio.setdefault(sound_name, []).append({'source': name, 'line': line})
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
