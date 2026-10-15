#!/usr/bin/env python3
"""Freeze exact original interface dependencies over the accepted 0.13.13 donor.

Audit native UI callers, literal arrays, shared frame/button constructors and
stock enhancement definitions. Read frozen PIGG table prefixes and bounded
selected payload ranges only; conserve all 9,613 accepted visual streams.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

import discover_client_appearance_assets as appearance
import discover_client_visual_sweep as previous
import prepare_client_ui_repair_assets as ancestor

ROOT = Path(__file__).resolve().parents[3]
SCOPE = 'native_client_interface_texture_dependency_sweep'
REQUEST_SCOPE = 'exact_native_client_ui_texture_sweep'
MAX_ADDITIONS, MAX_NEW_PAYLOAD_BYTES = 2048, 64 * 1024**2
BASE_ARCHIVE_PIN, BASE_MANIFEST_PIN = dict(ancestor.ARCHIVE_PIN), dict(ancestor.MANIFEST_PIN)
require, pin, canonical = previous.require, previous.pin, previous.canonical

# All interface C modules, shared frame/button constructors and enhancement
# definitions are audited. This scope excludes world/model/archive bulk import.
UI_DIRECTORY = 'upstream/ouroboros/Game/src/UI'
FRAME_CALLS = ('drawFrame', 'drawFlatFrame', 'drawFrameBox', 'drawFlatFrameBox',
    'drawFrameStyle', 'drawFrameStyleColor', 'drawFlatThreeToneFrame',
    'drawFlatSectionFrame', 'drawSectionFrame', 'drawFlatMultiToneFrame',
    'drawTabbedFlatFrameBox', 'drawTabbedFrameStyle', 'drawFrameOpenTopStyle',
    'drawFrameTabStyle', 'drawFrameWithBounds', 'drawJoinedFrame2Panel',
    'drawJoinedFlatFrame2Panel', 'drawJoinedFrame2PanelStyle',
    'drawJoinedFrame3Panel', 'drawJoinedFlatFrame3Panel', 'drawJoinedFrame3PanelStyle')
function_span = ancestor.discovery.function_span


def uncomment(text):
    """Exclude real C comments while retaining markers inside quoted filenames."""
    tokens = re.compile(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|/\*.*?\*/|//[^\n]*", re.S)
    def replace(match):
        token = match[0]
        return ''.join('\n' if char == '\n' else ' ' for char in token) if token.startswith('/') else token
    return tokens.sub(replace, text)



def source_requests(root=ROOT):
    root = Path(root)
    output = {'format': 1, 'scope': SCOPE, 'textures': {}, 'source_files': {},
        'native_directory_scope': UI_DIRECTORY, 'enhancement_definition_scope':
        'upstream/i24/data/defs/powers/boosts_*.powers',
        'native_gameplay_changed': False, 'native_renderer_changed': False,
        'full_global_asset_closure': False,
        'training_third_pane': 'native_pool_and_epic_choices_first_available_at_display_levels_4_and_35'}

    def add(token, relative, line, witness, **extra):
        stem = previous.tricks.texture_stem(token[:-4] if token.endswith('.tga') else token)
        require(re.fullmatch(r"[a-z0-9_.'-]+", stem) is not None,
            'Unsafe exact UI sweep request')
        if stem in ('white', 'black', 'invisible'):
            return  # Native renderer sentinels are generated, not imported.
        output['textures'].setdefault(stem, []).append({'scope': REQUEST_SCOPE,
            'target': token, 'source_path': relative, 'source_line': line,
            'source_witness': witness, 'native_texture_key': stem, **extra})

    pairs = {}
    for path in sorted((root/UI_DIRECTORY).rglob('*.c')):
        relative = path.relative_to(root).as_posix()
        text = uncomment(path.read_text())
        output['source_files'][relative] = pin(path)
        # Direct callers plus complete filename literals used by native arrays,
        # cursor setters and wrapper functions. String fragments are excluded.
        for match in re.finditer(r'atlasLoadTexture\(\s*"([^"\n]+)"|"([^"\n]+[.]tga)"', text, re.I):
            token = match[1] or match[2]
            line_context = text[text.rfind('\n', 0, match.start()) + 1:match.start()]
            if match[2] and 'STR_COMBINE_CAT' in line_context:
                continue  # Constructor suffix, not a complete filename.
            if '%' not in token and re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]*', token):
                add(token, relative, text[:match.start()].count('\n') + 1,
                    match[0], native_request='literal_or_native_filename_array')
        # Variables such as the three tip alert/read/glow textures are loaded
        # indirectly and were deliberately missed by the earlier finite pass.
        variables = set(re.findall(r'atlasLoadTexture\(\s*([A-Za-z_]\w*)\s*\)', text))
        for variable in sorted(variables):
            for match in re.finditer(r'\b' + re.escape(variable) + r'\s*=\s*"([A-Za-z][A-Za-z0-9_.-]*)"', text):
                add(match[1], relative, text[:match.start()].count('\n') + 1,
                    match[0], native_request='variable_texture_literal', variable=variable)
        pattern = r'\b(' + '|'.join(FRAME_CALLS) + r')\(\s*(PIX[1-4]|[1-4])\s*,\s*(R\d+|\d+)'
        for match in re.finditer(pattern, text):
            size, radius = int(match[2].removeprefix('PIX')), int(match[3].removeprefix('R'))
            require(0 <= radius <= 32, 'Native interface frame radius exceeds reviewed bounds')
            pairs.setdefault((size, radius), []).append((relative,
                text[:match.start()].count('\n') + 1, match[0]))

    # Derive shared frame variants from actual interface PIX/radius calls, not
    # broad donor prefixes. Constructor fragments and bounds are source-pinned.
    frame = UI_DIRECTORY + '/uiUtilGame.c'
    header = UI_DIRECTORY + '/uiUtil.h'
    output['source_files'][header] = pin(root/header)
    text = uncomment((root/frame).read_text())
    require('strcpy(pch, "Frame_")' in text and 'strcat(pch, "px_")' in text
        and 'strcat(pch, "r_")' in text and 'strcat(pch, ".tga")' in text,
        'Native frame constructor changed')
    corners = ('UL', 'LL', 'LR', 'UR')
    backgrounds = tuple('Background_' + corner + suffix for corner in corners for suffix in ('', '_INV'))
    for (size, radius), witnesses in sorted(pairs.items()):
        for relative, line, witness in witnesses:
            for style in ('', 'Flat_'):
                join_parts = ('join_L', 'join_R') if witness.startswith('drawJoined') else ()
                for part in corners + join_parts:
                    add(f'Frame_{style}{size}px_{radius}r_{part}.tga', relative, line, witness,
                        native_request='shared_frame_constructor', constructor_source=frame)
                for part in ('vert', 'horiz'):
                    add(f'Frame_{style}{size}px_{part}.tga', relative, line, witness,
                        native_request='shared_frame_constructor', constructor_source=frame)
            join_backgrounds = ('join_Background_L', 'join_Background_R') if witness.startswith('drawJoined') else ()
            for part in backgrounds + join_backgrounds:
                add(f'Frame_{size}px_{radius}r_{part}.tga', relative, line, witness,
                    native_request='shared_frame_background_constructor', constructor_source=frame)

    # Atlas calls through native minimap structs use extensionless literals.
    automap = UI_DIRECTORY + '/uiAutomap.c'
    text = uncomment((root/automap).read_text())
    for name in ('minimap_items', 'iconChoices'):
        match = re.search(r'\b' + name + r'\[\]\s*=\s*\{(.*?)\n\};', text, re.S)
        require(match is not None, 'Native map icon array changed')
        for row in re.finditer(r'\{[^{}]*?"([^"\n]+)"[^{}]*?"([^"\n]+)"[^{}]*?\}', match[1]):
            add(row[2], automap, text[:match.start(1) + row.start()].count('\n') + 1,
                row[0], native_request='map_icon_struct_array', native_array=name)

    reticle = UI_DIRECTORY + '/uiReticle.c'
    text = uncomment((root/reticle).read_text())
    require('strcpy(ach, "v_archetypeicon_")' in text and 'strcpy(ach, "archetypeicon_")' in text,
        'Native archetype icon prefixes changed')
    for path in sorted((root/'upstream/i24/data/defs/classes').glob('pc_*.def')):
        relative = path.relative_to(root).as_posix()
        definition = uncomment(path.read_text())
        match = re.search(r'\bName\s+"?(Class_\w+)', definition)
        require(match is not None, 'Player archetype class name missing')
        output['source_files'][relative] = pin(path)
        suffix = match[1].split('_', 1)[1]
        for prefix in ('v_archetypeicon_', 'archetypeicon_'):
            add(prefix + suffix, relative, definition[:match.start()].count('\n') + 1,
                match[0], native_request='archetype_icon_constructor', constructor_source=reticle)

    util = UI_DIRECTORY + '/uiUtil.c'
    body, first = function_span((root/util).read_text(), 'drawStdButton')
    require('STR_COMBINE_CAT("GenericButton_")' in body and 'strcpy( press, "press")' in body,
        'Native generic button constructor changed')
    tails = re.findall(r'LOAD\(\w+,\s*"([^"\n]+)"', body)
    require(len(tails) == 12, 'Native button layer scope changed')
    for state in ('rest', 'press'):
        for tail in tails:
            add(f'GenericButton_{state}_{tail}.tga', util, first,
                'GenericButton_ + press + _ + tail + .tga',
                native_request='button_layer_constructor', expansion={'state': state, 'tail': tail})

    combine = UI_DIRECTORY + '/uiCombineSpec.c'
    text = uncomment((root/combine).read_text())
    for match in re.finditer(r'strcpy\( frameName, "(E_orgin_[A-Za-z]+)"', text):
        for side in ('L', 'R'):
            add(match[1] + '_' + side + '.tga', combine,
                text[:match.start()].count('\n') + 1, match[0],
                native_request='enhancement_origin_frame_constructor')

    for path in sorted((root/'upstream/i24/data/defs/powers').glob('boosts_*.powers')):
        relative = path.relative_to(root).as_posix()
        text = uncomment(path.read_text())
        output['source_files'][relative] = pin(path)
        for match in re.finditer(r'\bIconName\s+"([^"\n]+)"', text):
            add(match[1], relative, text[:match.start()].count('\n') + 1, match[0],
                definition_field='IconName', native_request='enhancement_power_icon')
    for relative, pattern, field in (
        ('upstream/i24/data/defs/attrib_names.def', r'\bBoost\s+\S+\s+"[^"\n]+"\s+"([^"\n]+)"', 'BoostIcon'),
        ('upstream/i24/data/defs/origins.def', r'\bIcon\s+(\S+)', 'OriginIcon'),
    ):
        path = root/relative
        text = uncomment(path.read_text())
        output['source_files'][relative] = pin(path)
        for match in re.finditer(pattern, text):
            add(match[1], relative, text[:match.start()].count('\n') + 1,
                match[0], definition_field=field)
    # Three native contact-overhead FX refer to a retained exact GEO. Resolve
    # only its three model/material edges; this is not a new world sweep.
    geo = 'data/object_library/iconsandui/icons_contact.geo'
    table_sha256 = 'df33a4599af2413bc0c7192904ed9bb224d395cc9400242632ffd079df75f814'
    rootnames = 'upstream/i24/data/object_library/IconsAndUI/icons_contact.rootnames'
    output['source_files'][rootnames] = pin(root/rootnames)
    contact = []
    for suffix, model_suffix, texture in (
        ('available', 'Available', 'MissionAvailable.tga'),
        ('inprogress', 'InProgress', 'MissionInProgress.tga'),
        ('completed', 'Completed', 'X_Icon_Contact_MissionCompleted'),
    ):
        relative = 'upstream/i24/data/fx/ui/icon_mission' + suffix + '.fx'
        text = (root/relative).read_text()
        model = 'Icons_Contact_Mission' + model_suffix
        match = re.search(r'\bGEOM\s+' + re.escape(model) + r'\b', text)
        require(match is not None and ('Obj ' + model) in (root/rootnames).read_text(),
            'Native UI contact FX exact model edge changed')
        output['source_files'][relative] = pin(root/relative)
        add(texture, relative, text[:match.start()].count('\n') + 1, match[0],
            native_request='retained_ui_contact_geometry_material', geometry=geo,
            model=model, native_model_table_sha256=table_sha256)
        contact.append({'model': model, 'texture': texture})
    trick_path = 'upstream/i24/data/tricks/iconsandui/icons.txt'
    output['source_files'][trick_path] = pin(root/trick_path)
    definitions = previous.tricks.parse_texture_tricks_text((root/trick_path).read_text(), trick_path)
    completed = [row for row in definitions if row['name'] == 'X_Icon_Contact_MissionCompleted']
    require(len(completed) == 1 and completed[0]['composite_generation']['composite_alias_can_be_created'],
        'Native completed-contact composite definition changed')
    output['stock_composite_aliases'] = {'x_icon_contact_missioncompleted': completed[0]}
    for edge in completed[0]['edges']:
        add(edge['alias'], trick_path, edge['source_line'], edge['slot'] + ' ' + edge['alias'],
            native_request='stock_ui_contact_composite_slot', stock_composite='X_Icon_Contact_MissionCompleted')

    output['ui_contact_geometry_audit'] = {'geometry': geo, 'models': contact,
        'model_table_sha256': table_sha256, 'existing_geometry_preserved': True,
        'mesh_or_skinning_execution_validated': False}

    schedule = 'upstream/i24/data/defs/schedules.def'
    text = uncomment((root/schedule).read_text())
    require(re.search(r'PoolPowerSet\s+3,', text) and re.search(r'EpicPowerSet\s+34', text),
        'Native pool/epic level schedule changed')
    output['source_files'][schedule] = pin(root/schedule)
    output['frame_size_radius_pairs'] = [list(pair) for pair in sorted(pairs)]
    output['textures'] = {key: previous.unique_rows(rows) for key, rows in sorted(output['textures'].items())}
    return output


def plan(files, requests, retained):
    by_stem = {}
    for path in files:
        if path.startswith('texture_library/'):
            by_stem.setdefault(PurePosixPath(path).stem, []).append(path)
    selected, proofs, existing, unresolved = {}, {}, [], []
    retained_stems = {PurePosixPath(path).stem for path in retained if path.endswith('.texture')}
    for stem, rows in sorted(requests['textures'].items()):
        candidates = by_stem.get(stem, [])
        require(len(candidates) <= 1, 'Ambiguous exact UI basename: ' + stem)
        if stem in retained_stems:
            existing.append({'target': stem, 'sources': rows})
        elif not candidates and stem in requests.get('stock_composite_aliases', {}):
            continue  # Native stock composite already has its finite slot closure.
        elif not candidates:
            unresolved.append({'kind': 'exact_ui_texture_absent_from_frozen_donor', 'target': stem, 'sources': rows})
        else:
            name = 'data/' + candidates[0]
            require(name not in retained and previous.safe_payload(name), 'UI would replace an accepted leaf')
            selected[name] = files[candidates[0]]
            proofs[name] = rows
    require(0 < len(selected) <= MAX_ADDITIONS
        and sum(row['bytes'] for row in selected.values()) <= MAX_NEW_PAYLOAD_BYTES,
        'UI texture repair exceeds finite reviewed bounds')
    return {'selected': selected, 'requests': proofs, 'existing_leaf_dependencies': existing,
        'unresolved_dependencies': unresolved, 'stock_composite_aliases': requests.get('stock_composite_aliases', {})}


def discover(args):
    require(pin(args.baseline_archive) == BASE_ARCHIVE_PIN and pin(args.baseline_manifest) == BASE_MANIFEST_PIN,
        'UI sweep requires exact public 0.13.13 visual donor')
    old = ancestor.read_manifest(args.baseline_manifest, root=args.root)
    files = appearance.load_metadata(old, args.metadata_cache)
    requests = source_requests(args.root)
    contact = requests['ui_contact_geometry_audit']
    geo = contact['geometry']
    require(geo in old['files'], 'UI contact exact geometry is absent from accepted donor')
    version, models = previous.geometry.tables(files[geo.removeprefix('data/')]['cached_header'])
    require(hashlib.sha256(canonical(models)).hexdigest() == contact['model_table_sha256']
        and {model['name'].split('__', 1)[0]: model['direct_texture_names'] for model in models}
            == {row['model']: [row['texture']] for row in contact['models']},
        'Retained UI contact original GEO model/material table changed')
    retained = previous.retained_names(args.root, old)
    planned = plan(files, requests, retained)
    previous.verify_sources(args.root, requests['source_files'])
    args.output.mkdir(parents=True)
    request_path = args.output/'client-ui-sweep-requests.json'
    request_path.write_bytes(canonical(requests) + b'\n')
    public = {key: value for key, value in planned.items() if key != 'selected'}
    public.update({'format': 1, 'scope': SCOPE, 'source_files': requests['source_files'],
        'discovery_requests_pin': pin(request_path), 'file_count': len(planned['selected']),
        'payload_bytes': sum(row['bytes'] for row in planned['selected'].values()),
        'stored_payload_bytes': sum(row['stored_bytes'] for row in planned['selected'].values()),
        'retained_baseline_file_count': ancestor.FILE_COUNT,
        'runtime_visual_validated': False, 'native_renderer_changed': False,
        'native_gameplay_changed': False, 'full_global_asset_closure': False, 'preloading': False})
    plan_path = args.output/'client-ui-sweep-plan.json'
    plan_path.write_bytes(canonical(public) + b'\n')
    print(json.dumps({key: public[key] for key in ('file_count', 'payload_bytes', 'stored_payload_bytes')}) , flush=True)
    if args.plan_only:
        return
    records = {}
    groups, gap_bytes = previous.payload_groups(planned['selected'])
    with ThreadPoolExecutor(max_workers=8) as pool:
        for rows in pool.map(lambda group: previous.materialize_group(group, args.payload_cache), groups):
            records.update(rows)
    downloads = previous.centralize_downloads(records)
    downloads = {'s'+key.removeprefix('r'): value for key, value in downloads.items()}
    for row in records.values():
        row['source_download_receipt'] = 's'+row['source_download_receipt'].removeprefix('r')
    require(not set(downloads).intersection(old['provenance']['sweep_downloads']),
        'UI source receipts overlap an accepted receipt')
    value = copy.deepcopy(old)
    value['provenance']['sweep_downloads'].update(downloads)
    additions = {name: {'bytes': row['bytes'], 'sha256': row['sha256']} for name, row in sorted(records.items())}
    extension = {key: public[key] for key in ('scope', 'file_count', 'payload_bytes',
        'existing_leaf_dependencies', 'unresolved_dependencies', 'stock_composite_aliases', 'runtime_visual_validated',
        'native_renderer_changed', 'native_gameplay_changed', 'full_global_asset_closure', 'preloading')}
    extension.update({'missing_only': True, 'baseline_payloads_preserved': True,
        'baseline_archive_pin': BASE_ARCHIVE_PIN, 'baseline_manifest_pin': BASE_MANIFEST_PIN,
        'baseline_file_count': ancestor.FILE_COUNT, 'baseline_payload_bytes': ancestor.PAYLOAD_BYTES,
        'baseline_files_sha256': ancestor.FILES_SHA256,
        'files_sha256': hashlib.sha256(canonical(additions)).hexdigest(),
        'files': {name: {'requests_sha256': hashlib.sha256(canonical(rows)).hexdigest()}
            for name, rows in planned['requests'].items()},
        'discovery_plan_pin': pin(plan_path), 'discovery_requests_pin': pin(request_path),
        'full_archive_verified': False})
    value['files'].update(additions); value['requests'].update(planned['requests'])
    value['provenance']['entries'].update(records)
    for name, expected in requests['source_files'].items():
        require(name not in value['source_files'] or value['source_files'][name] == expected,
            'UI changes an accepted source witness')
    value['source_files'].update(requests['source_files'])
    value['ui_sweep_extension'] = extension
    value['file_count'] = len(value['files'])
    value['payload_bytes'] = sum(row['bytes'] for row in value['files'].values())
    value['files_sha256'] = hashlib.sha256(canonical(value['files'])).hexdigest()
    archive = args.output/ancestor.ARCHIVE
    previous.write_extended_zip(archive, args.baseline_archive, old, records, args.payload_cache)
    require(archive.stat().st_size <= ancestor.MAX_ARCHIVE_BYTES, 'UI composed archive exceeds accepted bound')
    value['archive'] = {'filename': archive.name, **pin(archive)}
    manifest = args.output/ancestor.MANIFEST
    manifest.write_bytes(canonical(value) + b'\n')
    require(manifest.stat().st_size <= ancestor.MAX_MANIFEST_BYTES, 'UI composed manifest exceeds accepted bound')
    public.update({'archive': pin(archive), 'manifest': pin(manifest),
        'added_files_sha256': extension['files_sha256'], 'files_sha256': value['files_sha256'],
        'total_file_count': value['file_count'], 'total_payload_bytes': value['payload_bytes'],
        'payload_partial_transfer_count': len(groups), 'bounded_transfer_gap_bytes': gap_bytes})
    (args.output/'client-ui-sweep-result.json').write_bytes(canonical(public) + b'\n')
    print(json.dumps({key: public[key] for key in ('archive', 'manifest', 'total_file_count', 'total_payload_bytes')}), flush=True)


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--baseline-archive', type=Path, required=True)
    parser.add_argument('--baseline-manifest', type=Path, required=True)
    parser.add_argument('--metadata-cache', type=Path, required=True)
    parser.add_argument('--payload-cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--plan-only', action='store_true')
    return parser.parse_args(argv)


if __name__ == '__main__':
    discover(arguments())
