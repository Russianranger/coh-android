#!/usr/bin/env python3
"""Read-only Kings Row foundation: pinned source graph and original-asset gaps.

No runtime/map enablement, install, replacement assets, cache mutation, or native
execution occurs. Optional metadata reads use the existing frozen PIGG prefixes;
even complete table coverage cannot qualify payloads, collision, or live zoning.
Whole loaded object-library files are traversed conservatively: the result is a
source dependency envelope, not a claim that every model is visible in the city.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

import audit_atlas_beacon_inputs as bounded
import client_appearance_costumes as costumes
import client_visual_tricks as tricks
import discover_client_appearance_assets as appearance
import discover_client_visual_sweep as sweep
import prepare_client_ui_sweep_assets as visual

ROOT = Path(__file__).resolve().parents[3]
MAP_ID = 5
MAP = 'maps/city_zones/city_01_02/city_01_02.txt'
SOURCE = '0b75ade0c801735e10c5798f641948a45cc50488'
DATA = 'd51533ec8e6a9cf726b9214968077a05fdcf19f3'
MAX_SOURCE_BYTES = 16 * 1024**2
MAX_SOURCE_FILES = 10000
MAX_SOURCE_TOTAL = 256 * 1024**2
MAX_METADATA_TOTAL = 40 * 1024**2
MAX_ADDITION_FILES = 4096
MAX_ADDITION_BYTES = 256 * 1024**2
NATIVE_SOURCES = (
    'Common/group/groupfilelib.c', 'Common/group/groupfileload.c',
    'Common/group/group.c', 'Game/src/graphics/sun.c',
    'MapServer/src/beacon/beaconFile.c', 'Common/seq/anim.c',
    'libs/UtilitiesLib/src/utils/utils.c',
    'Game/src/graphics/gfxLoadScreens.c', 'Game/src/UI/uiAutomap.c',
    'Game/src/render/tex.c',
)
COMMANDS = re.compile(r'^\s*(Def|RootMod|Import|Group|Obj|Scenefile|ReplaceTex|TexSwap|Sky|Dest|Name|MoonName|SkyName|Icon)\s+', re.I)
require = bounded.require


def pin_bytes(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def public_name(value):
    """groupNameIdx ignores path and a __ variant; '&' private renames stay local."""
    return value.replace('\\', '/').rsplit('/', 1)[-1].split('__', 1)[0].casefold()


def data_path(value):
    require(isinstance(value, str) and value and '\\' not in value and ':' not in value,
            'Unsafe source path')
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.as_posix() == value
            and all(part not in ('', '.', '..') for part in path.parts), 'Unsafe source path')
    return value.casefold()


def source_tokens(text):
    # Retain real line numbers while skipping the large numeric position arrays.
    clean = costumes.strip_comments(text)
    for number, line in enumerate(clean.splitlines(), 1):
        if COMMANDS.match(line):
            rows = list(costumes.line_tokens(line))
            if rows:
                yield number, rows[0][1]


class Sources:
    def __init__(self, root, *, max_source_files=MAX_SOURCE_FILES, max_source_total=MAX_SOURCE_TOTAL):
        self.root = Path(root)
        document, self.manifest_pin = bounded.load_json(self.root / 'docs/data-manifest.json')
        require(document.get('commit') == DATA, 'Companion data commit differs')
        self.entries = {data_path(row['path'][5:]): row for row in document['entries']
                        if row['path'].startswith('data/')}
        self.pins, self.rows, self.total = {}, {}, 0
        self.max_source_files, self.max_source_total = max_source_files, max_source_total

    def read(self, name):
        name = data_path(name)
        require(name in self.entries, 'Source missing from pinned companion data: ' + name)
        if name not in self.rows:
            entry = self.entries[name]
            raw = bounded.read_regular(self.root / 'upstream/i24' / entry['path'], MAX_SOURCE_BYTES)
            require(pin_bytes(raw) == {'bytes': entry['size'], 'sha256': entry['sha256']},
                    'Companion source differs from pinned snapshot: ' + name)
            self.total += len(raw)
            require(self.total <= self.max_source_total and len(self.rows) < self.max_source_files,
                    'Kings Row source closure exceeds audit bounds')
            self.pins['upstream/i24/' + entry['path']] = pin_bytes(raw)
            self.rows[name] = list(source_tokens(raw.decode('utf-8-sig')))
        return self.rows[name]

    def verify_external_pins(self, pins):
        data_entries = {'upstream/i24/' + row['path']: row for row in self.entries.values()}
        source, _ = bounded.load_json(self.root / 'docs/source-manifest.json')
        require(source.get('commit') == SOURCE, 'Native source commit differs')
        native_entries = {'upstream/ouroboros/' + row['path']: row for row in source['entries']}
        for name, identity in pins.items():
            entry = data_entries.get(name) or native_entries.get(name)
            require(entry is not None and identity == {'bytes': entry['size'], 'sha256': entry['sha256']},
                    'Dependency source differs from pinned snapshot: ' + name)

    def identity(self, name):
        relative = 'upstream/i24/' + self.entries[data_path(name)]['path']
        return relative, self.pins[relative]


def group_requests(sources, map_name=MAP):
    """Import and library closure, with all unresolved edges preserved explicitly."""
    index = defaultdict(set)
    for name in sorted(sources.entries):
        if name.startswith('object_library/') and PurePosixPath(name).suffix in ('.txt', '.rootnames'):
            for line, tokens in sources.read(name):
                if tokens[0].casefold() == 'def' and len(tokens) == 2 and not tokens[1].endswith('&'):
                    # addLibName stores declarations literally. Only lookup
                    # strips path/__ (groupNameIdx); do not invent an alias.
                    index[tokens[1].casefold()].add(str(PurePosixPath(name).with_suffix('')))
    geometry, textures, reasons, unresolved = defaultdict(list), defaultdict(list), {}, []
    queue, seen, groups, local_defs = [map_name], set(), [], set()
    scene_files, sky_files, map_files = set(), set(), set()

    def witness(name, line, field, value):
        return {'scope': 'kings_row_pinned_source_dependency', 'source_path': sources.identity(name)[0],
                'source_line': line, 'field': field, 'target': value}

    def texture(value, row):
        if tricks.valid_texture_name(value):
            textures[tricks.texture_stem(value)].append(row | {'alias': value})

    def model(value, row, direct=False):
        choices = sorted(index.get(public_name(value), ()))
        if len(choices) != 1:
            groups.append((value, row, choices, direct))
            return
        prefix = choices[0]
        for suffix in ('.rootnames', '.txt'):
            path = prefix + suffix
            if path in sources.entries:
                queue.append(path)
                reasons.setdefault(path, row)
        if direct:
            geometry['data/' + prefix + '.geo'].append(row | {'model': public_name(value)})

    while queue:
        name = data_path(queue.pop())
        if name in seen:
            continue
        if name not in sources.entries:
            unresolved.append({'kind': 'source_missing', 'target': name})
            continue
        seen.add(name)
        if name.startswith('maps/'):
            map_files.add(name)
        rows = sources.read(name)
        first_moon = True
        for line, tokens in rows:
            if len(tokens) < 2:
                continue
            field, value = tokens[0].casefold(), tokens[1]
            row = witness(name, line, tokens[0], value)
            if field in ('def', 'rootmod'):
                local_defs.add(public_name(value))
            elif field == 'import':
                queue.append(data_path(value.replace('\\', '/')))
            elif field == 'scenefile':
                child = data_path(value.replace('\\', '/'))
                scene_files.add(child); queue.append(child)
            elif field == 'sky' and name in scene_files:
                child = data_path('scenes/skies/' + value.replace('\\', '/'))
                sky_files.add(child); queue.append(child)
            elif field in ('group', 'obj'):
                model(value, row, field == 'obj')
            elif field == 'replacetex' and len(tokens) >= 3:
                texture(tokens[2], row | {'target': tokens[2]})
            elif field == 'texswap' and len(tokens) >= 3:
                texture(tokens[2], row | {'target': tokens[2]})
            elif field == 'dest' and name in scene_files:
                texture(value, row)
            elif field in ('name', 'moonname', 'skyname') and name in sky_files:
                model(value, row, True)
                if field == 'moonname' and first_moon:
                    glow = value.split('__', 1)[0] + 'glow__'
                    model(glow, row | {'native_expansion': 'first moon sun glow', 'target': glow}, True)
                    first_moon = False
    for value, row, choices, direct in groups:
        if direct or choices or public_name(value) not in local_defs:
            unresolved.append({'kind': 'ambiguous_library_name' if choices else 'group_or_model_missing',
                               'target': value, 'candidates': choices, 'source': row})
    return {'geometry': dict(geometry), 'textures': dict(textures), 'source_files': dict(
        sources.identity(name) for name in sorted(seen)),
        'map_files': sorted(map_files), 'scene_files': sorted(scene_files), 'sky_files': sorted(sky_files),
        'library_files': sorted(name for name in seen if name.startswith('object_library/')),
        'unresolved_source_edges': unresolved,
        'scope': 'Conservative complete loaded-library files, imported map layers and all authored scene skies; not visible-model liveness'}


def retained_inventory(root):
    root = Path(root)
    current = json.loads(visual.manifest_bytes(root / 'assets/client-ui-sweep-manifest.json', root=root))
    original, _ = bounded.load_json(root / 'assets/reference-inputs-manifest.json')
    require(original.get('source_commit') == SOURCE and original.get('text_data_commit') == DATA,
            'Accepted imported asset identity differs')
    names, records, original_records = {}, {}, {}
    for row in original['files']:
        name = 'data/' + data_path(row['path'])
        names[name] = {'bytes': row['size'], 'sha256': row['sha256']}
        original_records[name] = row
    for filename in ('character-avatar-defaults-manifest.json', 'atlas-world-supplement-manifest.json'):
        value, _ = bounded.load_json(root / 'assets' / filename)
        for name, pin in value['files'].items():
            require(name not in names or names[name] == pin, 'Retained asset inventories conflict')
            names[name] = pin
        records.update(value['provenance']['entries'])
    for name, pin in current['files'].items():
        require(name not in names or names[name] == pin, 'Retained visual inventory overwrites an import')
        names[name] = pin
    records.update(current['provenance']['entries'])
    return names, records, original_records, current


def donor_metadata(current, cache, *, fetch=False):
    identities = current['provenance']['metadata_archives']
    require(sum(row['source_metadata_bytes'] for row in identities) <= MAX_METADATA_TOTAL,
            'Frozen donor metadata exceeds bounded inventory')
    require([row['archive'] for row in identities] == sorted([row['archive'] for row in identities], key=str.casefold),
            'Frozen donor overwrite order differs')
    files, archives = {}, {}
    for identity in identities:
        require(re.fullmatch(r'[A-Za-z0-9]+\.pigg', identity['archive']), 'Unsafe frozen donor archive')
        path = Path(cache) / identity['archive']
        require(not path.is_symlink(), 'Linked donor metadata refused')
        require(fetch or path.is_file(), 'Frozen metadata missing; use explicit --fetch-metadata: ' + path.name)
        if path.is_file():
            raw = bounded.read_regular(path, identity['source_metadata_bytes'])
            require(pin_bytes(raw) == {'bytes': identity['source_metadata_bytes'],
                'sha256': identity['source_metadata_sha256']}, 'Frozen donor metadata pin differs')
        rows = sweep.metadata(identity, cache)
        files.update(rows); archives[identity['archive']] = rows
    return files, archives


def map_auxiliary_inventory(current, cache, retained):
    """Metadata-only map BIN/reflection inventory; never endorse donor caches."""
    selected, beacons = [], []
    for identity in current['provenance']['metadata_archives']:
        raw = bounded.read_regular(Path(cache) / identity['archive'], identity['source_metadata_bytes'])
        require(hashlib.sha256(raw).hexdigest() == identity['source_metadata_sha256'], 'Frozen metadata pin differs')
        pigg = sweep.inspect_piggs
        _, _, _, header, entry, count = pigg.HEADER.unpack_from(raw)
        names, _ = pigg.pool(raw, header + count * entry, 0x6789)
        for index in range(count):
            _, nameid, size, _, offset, _, _, md5, packed = pigg.ENTRY.unpack_from(raw, header + index * entry)
            name = pigg.safe_name(names[nameid]); key = name.casefold()
            if '.bcn' in key:
                beacons.append({'archive': identity['archive'], 'path': name})
            if not key.startswith(('geobin/maps/city_zones/city_01_02/',
                                   'texture_library/static_cubemaps/city_01_02/')):
                continue
            selected.append({'archive': identity['archive'], 'path': name, 'bytes': size,
                'stored_bytes': packed or size, 'offset': offset, 'md5_table': md5.hex(),
                'retained_inventory_contains_path': 'data/' + key in retained,
                'payload_or_native_compatibility_verified': False})
    return {'scope': 'All 57 frozen archive name tables; no claim about unlisted donor archives.',
        'map_bin_and_reflection_candidates': selected, 'beacon_members_in_frozen_tables': beacons,
        'donor_map_bin_qualified_for_retained_native_parser': False,
        'reflection_faces_bound_to_live_materials': False,
        'notes': ['A donor map BIN is not a substitute for fresh parser/source/collision qualification.',
            'Native tex.c loads five companion faces when a cubemap master is used; preserve all faces before claiming reflection fidelity.',
            'The current installer/cache refresh and authenticated graph target Atlas only; Kings Row requires its own bounded qualification.']}


def map_interface_requests(sources, request):
    # gfxLoadScreens tries the map basename first; uiAutomap uses map_<basename>.
    stem = PurePosixPath(MAP).stem
    for target, native in ((stem, 'Game/src/graphics/gfxLoadScreens.c'),
                           ('map_' + stem, 'Game/src/UI/uiAutomap.c')):
        request['textures'].setdefault(target, []).append({'scope': 'kings_row_native_map_interface',
            'target': target, 'alias': target, 'map': MAP, 'native_rule': 'upstream/ouroboros/' + native})
    selected = False
    for line, tokens in sources.read('menu/zones.map'):
        if len(tokens) < 2:
            continue
        if tokens[0].casefold() == 'name':
            selected = tokens[1].casefold() == MAP
        elif selected and tokens[0].casefold() == 'icon':
            target = tokens[1]
            request['textures'].setdefault(tricks.texture_stem(target), []).append({
                'scope': 'kings_row_pinned_zone_icon', 'target': target, 'alias': target,
                'source_path': sources.identity('menu/zones.map')[0], 'source_line': line})
    relative, pin = sources.identity('menu/zones.map')
    request['source_files'][relative] = pin


def preserve_retained_headers(files, archives, names, records, originals):
    """Use the retained file's donor header, never an unrelated last-wins version."""
    selected = dict(files)
    for name in names:
        if not name.endswith('.geo'):
            continue
        old, imported = records.get(name), originals.get(name)
        archive = imported['donor'] if imported else old.get('source_archive') if old else None
        row = archives.get(archive, {}).get(name.removeprefix('data/'))
        require(row is not None and row['bytes'] == names[name]['bytes'],
                'Retained GEO donor header missing or size differs: ' + name)
        if old:
            require(old['md5_table'] == row['md5_table'] and old['offset'] == row['offset'],
                    'Retained GEO donor record changed: ' + name)
            if old.get('cached_header_sha256'):
                require(old['cached_header_sha256'] == hashlib.sha256(row['cached_header']).hexdigest(),
                        'Retained GEO cached header differs: ' + name)
        selected[name.removeprefix('data/')] = row
    return selected


def normalize_native_requests(request):
    """modelFind strips __ trick suffixes; preserve the literal as evidence."""
    for rows in request['geometry'].values():
        for row in rows:
            if 'model' in row and '__' in row['model']:
                row['native_model_literal'] = row['model']
                row['model'] = row['model'].split('__', 1)[0]


def native_fx_root(value):
    # The costume walker prepends data/fx/ to the literal. Undo only that
    # transport prefix, then apply fxCleanFileName's authored /FX/ prefix rule.
    value = value.removeprefix('data/fx/').replace('\\', '/').casefold().lstrip('/')
    if '/fx/' in value:
        value = value.split('/fx/', 1)[1]
    return 'fx/' + value.removeprefix('fx/')


def verify_world_geometry_cache(files, missing_names, cache):
    """Offline verify the selected original GEO streams; never install them."""
    records = {}
    for name in missing_names:
        row = files.get(name.removeprefix('data/'))
        require(row is not None, 'No frozen donor for missing source-world geometry: ' + name)
        path = Path(cache) / hashlib.sha256(name.encode()).hexdigest()
        stored = bounded.read_regular(path, sweep.MAX_ENTRY_BYTES)
        record = sweep.verified_payload(row, stored)
        # verified_payload's producer wording includes HTTP. This offline audit
        # only proves the cached original against its frozen MD5/header table.
        record['integrity'] = 'cached_original_zlib_size_table_md5_and_header_verified'
        records[name] = record
    return {'scope': 'Missing source-world GEO payloads only; actor/texture inventory remains incomplete',
        'verified_file_count': len(records), 'files': records,
        'decoded_bytes': sum(row['bytes'] for row in records.values()),
        'stored_bytes': sum(row['stored_bytes'] for row in records.values()),
        'fresh_http_performed_by_this_check': False, 'runtime_installation_performed': False,
        'native_world_or_collision_verified': False, 'full_asset_closure': False}


def audit(root=ROOT, *, metadata_cache=None, fetch_metadata=False, include_actors=True,
          world_geometry_cache=None):
    root = Path(root)
    sources = Sources(root)
    db = root / 'upstream/i24/data/server/db/maps.db'
    raw = bounded.read_regular(db, MAX_SOURCE_BYTES)
    record = re.search(rb'(?im)^Container 5\s*\r?\n(.*?)^ContainerEnd', raw, re.S)
    require(record is not None and b'MapKey kingsrow' in record[1]
            and b'MapName "maps/City_Zones/City_01_02/City_01_02.txt"' in record[1], 'Map 5 identity differs')
    sources.verify_external_pins({'upstream/i24/data/server/db/maps.db': pin_bytes(raw)})
    native_pins = {name: pin_bytes(bounded.read_regular(root / name, MAX_SOURCE_BYTES))
                   for name in ('upstream/ouroboros/' + item for item in NATIVE_SOURCES)}
    sources.verify_external_pins(native_pins)
    request = group_requests(sources)
    map_interface_requests(sources, request)
    names, records, originals, current = retained_inventory(root)
    output = {'format': 1, 'scope': 'kings_row_original_asset_foundation_v1',
        'source_commit': SOURCE, 'data_commit': DATA, 'map_id': MAP_ID, 'map': MAP,
        'companion_source_manifest': sources.manifest_pin,
        'maps_db': pin_bytes(raw), 'native_rule_sources': native_pins,
        'retained_visual_manifest': visual.MANIFEST_PIN,
        'source_graph': request, 'retained_inventory_count': len(names),
        'source_world_geo_count': len(request['geometry']),
        'missing_source_world_geos': sorted(set(request['geometry']) - set(names)),
        'source_graph_complete': not request['unresolved_source_edges'],
        'original_payloads_verified': False, 'full_asset_closure': False,
        'native_world_load_verified': False, 'collision_verified': False,
        'native_beacon_graph_verified': False, 'physical_zoning_verified': False,
        'native_game_rebuilt': False, 'runtime_map_5_enabled': False,
        'graphics_or_existing_assets_modified': False,
        'audit_limits': ['Whole loaded object-library files and authored event/faction variants are a conservative envelope, not active visible-model liveness.',
            'Actor/FX witnesses retain historical Atlas walker scope labels; the selected map roots and spawnarea are Kings Row.',
            'Animation/audio payload closure, dynamic scripts and runtime-selected appearances are not established by GEO/texture metadata.',
            'Resolver gaps can include optional or unused stock definitions; no gap is silently discarded or replaced.'],
        'remaining_qualification': ['Resolve every scoped asset/source gap without placeholder or fidelity reduction.',
            'Verify selected original payload ranges and finite missing-only installation.',
            'Qualify real map load/collision and map-specific geobin freshness with retained binaries.',
            'Provide an authentic Kings Row beacon graph with loaded-world CRC and native readback/pathing.',
            'Qualify destination arrival, ordinary save and reopen before exposing map 5.']}
    if metadata_cache is None:
        require(not fetch_metadata and world_geometry_cache is None,
                'Metadata fetch or GEO verification requires --metadata-cache')
        output['metadata_status'] = 'not_supplied_no_network_access'
        return output
    files, archives = donor_metadata(current, metadata_cache, fetch=fetch_metadata)
    files = preserve_retained_headers(files, archives, names, records, originals)
    output['metadata_status'] = 'all_frozen_prefixes_verified'
    output['metadata_archives'] = current['provenance']['metadata_archives']
    output['map_auxiliary_inventory'] = map_auxiliary_inventory(current, metadata_cache, names)
    if world_geometry_cache is not None:
        output['world_geometry_payloads'] = verify_world_geometry_cache(files,
            output['missing_source_world_geos'], world_geometry_cache)
    if include_actors:
        actor = costumes.atlas_requests(root, files,
            map_files=[root / 'upstream/i24/data' / name for name in request['map_files']],
            spawnarea_file='server/spawnarea/city_01_02.txt')
        actor['source_files'] = {row['path']: {key: row[key] for key in ('bytes', 'sha256')}
                                 for row in actor['source_files']}
        fx = appearance.enttype_fx_requests(root, files, actor['enttypes'],
            [native_fx_root(name) for name in actor['fx']], native_path_normalization=True)
        appearance.rows_merge(request, actor); appearance.rows_merge(request, fx)
        request['unresolved_source_edges'].extend(actor['unresolved'] + fx['unresolved_source_edges'])
        output['actor_closure'] = actor['closure']
        output['actor_closure']['scope'] = 'all_authored_kings_row_layers_and_referenced_actor_appearance_envelope'
        output['actor_enttypes'] = sorted(actor['enttypes'])
        output['actor_fx_sources'] = sorted(actor['fx'])
    else:
        output['actor_closure'] = {'status': 'not_requested_still_required_for_city_qualification'}
    stock, stock_pins = tricks.stock_tricks(root)
    sources.verify_external_pins(request['source_files'] | stock_pins)
    normalize_native_requests(request)
    plan = appearance.exact_dependency_plan(files, request, names, stock)
    additions = plan.pop('selected')
    require(len(additions) <= MAX_ADDITION_FILES
            and sum(row['bytes'] for row in additions.values()) <= MAX_ADDITION_BYTES,
            'Kings Row candidate additions exceed finite foundation bounds')
    output['source_graph_complete'] = not request['unresolved_source_edges']
    output['plan'] = plan
    output['plan']['selected_original_candidates'] = {name: {
        **{key: value for key, value in row.items() if key != 'cached_header'},
        'cached_header_pin': pin_bytes(row['cached_header']), 'payload_verified': False}
        for name, row in sorted(additions.items())}
    output['plan']['summary'] = {'candidate_count': len(additions),
        'geometry_candidates': sum(name.endswith('.geo') for name in additions),
        'texture_candidates': sum(name.endswith('.texture') for name in additions),
        'decoded_candidate_bytes': sum(row['bytes'] for row in additions.values()),
        'stored_candidate_bytes': sum(row['stored_bytes'] for row in additions.values()),
        'unresolved_dependencies': len(plan['unresolved_dependencies']),
        'unresolved_source_edges': len(request['unresolved_source_edges']),
        'ambiguous_stock_definitions': len(plan['ambiguous_stock_definitions']), 'cycles': len(plan['cycles'])}
    prior = {(row['kind'], row.get('target')) for value in current.values() if isinstance(value, dict)
             for row in value.get('unresolved_dependencies', []) if 'kind' in row}
    output['plan']['baseline_gap_comparison'] = {
        'scope': 'kind/target match with retained visual manifests; not proof of live relevance or dispensability',
        'same_kind_target_previously_recorded': sum((row['kind'], row.get('target')) in prior
            for row in plan['unresolved_dependencies']),
        'new_kind_target_findings': [{'kind': row['kind'], 'target': row.get('target')}
            for row in plan['unresolved_dependencies'] if (row['kind'], row.get('target')) not in prior]}
    prior_source = {(row['kind'], row.get('target'))
        for row in current['appearance_extension']['source_closure_gaps']}
    output['plan']['baseline_gap_comparison']['source_same_kind_target_previously_recorded'] = sum(
        (row['kind'], row.get('target')) in prior_source for row in request['unresolved_source_edges'])
    return output


def compact(result):
    """Reviewable summary bound to reproducible full output; never acceptance."""
    raw = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    omitted = {'source_graph', 'plan', 'actor_closure'}
    output = {key: value for key, value in result.items() if key not in omitted}
    output['detailed_audit'] = {**pin_bytes(raw),
        'reproduce': 'python3 tools/android/interactive/audit_kings_row_foundation.py --metadata-cache CACHE'
            + (' --world-geometry-cache GEO_CACHE' if 'world_geometry_payloads' in result else '')
            + ' --output FULL.json',
        'metadata_fetch': 'Add --fetch-metadata only when the exact frozen metadata cache is absent.',
        'output_scope': 'Detailed full source/leaf witnesses are omitted here and bound by this digest.'}
    graph = result['source_graph']
    output['source_graph'] = {key: graph[key] for key in ('scope', 'map_files', 'scene_files', 'sky_files')}
    output['source_graph'].update({'library_source_files': len(graph['library_files']),
        'selected_source_files': len(graph['source_files']),
        'source_pins_sha256': hashlib.sha256(sweep.canonical(graph['source_files'])).hexdigest(),
        'geometry_requests': len(graph['geometry']),
        'unresolved_source_edges': graph['unresolved_source_edges']})
    if 'actor_closure' in result:
        output['actor_closure'] = {key: len(value) if isinstance(value, (list, dict)) else value
            for key, value in result['actor_closure'].items()}
    if 'plan' in result:
        plan = result['plan']; candidates = plan['selected_original_candidates']
        output['plan'] = {'summary': plan['summary'], 'baseline_gap_comparison': plan['baseline_gap_comparison'],
            'selected_candidate_inventory_sha256': hashlib.sha256(sweep.canonical(candidates)).hexdigest(),
            'world_geometry_candidates': {name: candidates[name] for name in result['missing_source_world_geos']
                if name in candidates},
            'unresolved_dependencies': [{**{key: value for key, value in row.items() if key != 'sources'},
                'source_witness_count': len(row.get('sources', [])),
                'first_source_witness': row.get('sources', [None])[0]}
                for row in plan['unresolved_dependencies']]}
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--metadata-cache', type=Path)
    parser.add_argument('--fetch-metadata', action='store_true', help='Fetch only the exact frozen metadata prefixes')
    parser.add_argument('--world-geometry-cache', type=Path,
                        help='Offline verify selected original GEO streams in an existing donor-range cache')
    parser.add_argument('--world-only', action='store_true', help='Leave actor/FX closure explicitly unassessed')
    parser.add_argument('--compact', action='store_true', help='Summarize witnesses, bound to the complete output hash')
    parser.add_argument('--output', type=Path, help='New JSON path; stdout otherwise')
    args = parser.parse_args(argv)
    if args.output:
        require(not args.output.exists() and not args.output.is_symlink(),
                'Existing output is preserved; choose a new JSON path')
    result = audit(args.root, metadata_cache=args.metadata_cache, fetch_metadata=args.fetch_metadata,
                   include_actors=not args.world_only, world_geometry_cache=args.world_geometry_cache)
    if args.compact:
        result = compact(result)
    text = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.output:
        with args.output.open('x') as stream:
            stream.write(text)
    else:
        print(text, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
