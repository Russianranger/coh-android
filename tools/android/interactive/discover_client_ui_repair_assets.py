#!/usr/bin/env python3
"""Freeze exact original HUD/training texture leaves over the 0.13.11 donor.

This finite pass follows the photographed status, inspiration and native trainer
widgets. It reads frozen PIGG table prefixes and selected payload ranges only;
the complete 9,490-file appearance donor is conserved byte for byte.
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
import prepare_client_appearance_assets as ancestor

ROOT = Path(__file__).resolve().parents[3]
SCOPE = 'recorded_status_inspiration_and_trainer_ui_dependency_closure'
REQUEST_SCOPE = 'exact_native_hud_and_trainer_ui_texture'
MAX_ADDITIONS, MAX_NEW_PAYLOAD_BYTES = 256, 32 * 1024**2
BASE_ARCHIVE_PIN, BASE_MANIFEST_PIN = dict(ancestor.ARCHIVE_PIN), dict(ancestor.MANIFEST_PIN)
require, pin, canonical = previous.require, previous.pin, previous.canonical

NATIVE_FUNCTIONS = {
    'upstream/ouroboros/Game/src/UI/uiStatus.c': (
        'status_notify', 'drawHeartBeatGlow', 'drawRagePulse', 'drawHealthBarFrame',
        'drawHealthBar', 'drawExperienceFrame', 'drawExperience', 'statusWindow'),
    'upstream/ouroboros/Game/src/UI/uiInspiration.c': (
        'inspirationcm_init', 'inspirationUpdate', 'drawInspirationSlots', 'inspirationWindow'),
    'upstream/ouroboros/Game/src/UI/uiUtilMenu.c': (
        'drawBackground', 'drawMenuHeader', 'drawMenuFrame', 'drawNextCircle',
        'drawNextButton', 'drawMenuTitle', 'drawCheckBox', 'drawCheckBarEx',
        'drawMenuBarSquished', 'drawLargeCapsule'),
    'upstream/ouroboros/Game/src/UI/uiTray.c': None,
}
POWER_SOURCES = tuple('upstream/i24/data/defs/powers/' + name for name in (
    'blaster_ranged_archery.powers', 'blaster_support_gadgets.powers',
    'inspirations_small.powers', 'inspirations_medium.powers', 'inspirations_large.powers'))


def uncomment(text):
    """Keep line numbering while excluding authored comments from requests."""
    text = re.sub(r'/\*.*?\*/', lambda m: '\n' * m[0].count('\n'), text, flags=re.S)
    return re.sub(r'//[^\n]*', '', text)


def function_span(text, name):
    clean = uncomment(text)
    found = re.search(r'^\s*[^\n;{}]+\b' + re.escape(name) + r'\s*\([^;{}]*\)\s*\{', clean, re.M)
    require(found is not None, 'Missing finite native UI function: ' + name)
    start = clean.index('{', found.start())
    # Strip strings for brace counting while preserving positions and newlines.
    masked = re.sub(r'"(?:\\.|[^"\\])*"', lambda m: ' ' * len(m[0]), clean)
    depth = 1
    end = start + 1
    while depth and end < len(masked):
        depth += (masked[end] == '{') - (masked[end] == '}')
        end += 1
    require(depth == 0, 'Unclosed finite native UI function: ' + name)
    return clean[start:end], clean[:start].count('\n') + 1


def source_requests(root=ROOT):
    root = Path(root)
    output = {'format': 1, 'scope': SCOPE, 'textures': {}, 'source_files': {},
        'native_function_scope': NATIVE_FUNCTIONS, 'power_definition_scope': POWER_SOURCES,
        'no_per_row_power_icon_change': True, 'native_gameplay_changed': False}

    def add(token, relative, line, witness, **extra):
        stem = PurePosixPath(token).stem.casefold()
        require(re.fullmatch(r'[a-z0-9_.-]+', stem) is not None,
            'Unsafe exact UI texture request')
        output['textures'].setdefault(stem, []).append({'scope': REQUEST_SCOPE,
            'target': token, 'source_path': relative, 'source_line': line,
            'source_witness': witness, **extra})

    for relative, functions in NATIVE_FUNCTIONS.items():
        path = root/relative
        text = path.read_text()
        output['source_files'][relative] = pin(path)
        bodies = [(uncomment(text), 1, 'native_tray_hud')] if functions is None else [
            (*function_span(text, function), function) for function in functions]
        for body, first, function in bodies:
            for match in re.finditer(r'atlasLoadTexture\(\s*"([^"\n]+)"', body):
                add(match[1], relative, first + body[:match.start()].count('\n'),
                    match[0], native_function=function)

    status = 'upstream/ouroboros/Game/src/UI/uiStatus.c'
    text = (root/status).read_text()
    for template in ('healthbar_exp_dot_%02d.tga', 'healthbar_exp_dot_empty_%02d.tga'):
        require(template in text and 'i < 10' in function_span(text, 'drawExperience')[0],
            'Native XP tick range/template changed')
        line = text[:text.index(template)].count('\n') + 1
        for number in range(1, 11):
            add(template % number, status, line, template,
                native_function='drawExperience', expansion={'range': [1, 10], 'value': number})

    inspiration = 'upstream/ouroboros/Game/src/UI/uiInspiration.c'
    text = (root/inspiration).read_text()
    header = 'upstream/ouroboros/Common/entity/character_base.h'
    header_text = (root/header).read_text()
    require('#define CHAR_INSP_MAX_COLS (5)' in header_text
        and 'STR_COMBINE_CAT("tray_ring_number_F")' in text
        and 'STR_COMBINE_CAT_D(col+1)' in text,
        'Native inspiration key label bounds/template changed')
    output['source_files'][header] = pin(root/header)
    line = text[:text.index('STR_COMBINE_CAT("tray_ring_number_F")')].count('\n') + 1
    for number in range(1, 6):
        add(f'tray_ring_number_F{number}.tga', inspiration, line,
            'tray_ring_number_F + col+1 + .tga', expansion={'range': [1, 5], 'value': number})

    util = 'upstream/ouroboros/Game/src/UI/uiUtilMenu.c'
    text = (root/util).read_text()
    for function, templates, arguments in (
        ('drawNextButton', ('next_%sbutton_%c.tga', 'next_%sfade_afterimage_%c.tga',
            'next_%sfade_tail_%c.tga'), [(locked, side) for locked in ('', 'locked_') for side in ('L', 'R')]),
        ('drawCheckBarEx', ('checkbar_frame_%s_%sL_bulb.tga', 'checkbar_frame_%s_%sMID.tga',
            'checkbar_frame_%s_%sR.tga', 'checkbar_frame_%s_%sL_bulb_tintable.tga',
            'checkbar_frame_%s_%sMID_tintable.tga', 'checkbar_frame_%s_%sR_tintable.tga'),
            [('lg', selected) for selected in ('', 'selected_')]),
        ('drawMenuBarSquished', ('checkbar_frame_lg_%sL.tga', 'checkbar_frame_lg_%sMID.tga',
            'checkbar_frame_lg_%sR.tga', 'checkbar_frame_lg_%sL_tintable.tga',
            'checkbar_frame_lg_%sMID_tintable.tga', 'checkbar_frame_lg_%sR_tintable.tga'),
            [('',), ('selected_',)]),
    ):
        body, first = function_span(text, function)
        for template in templates:
            require(template in body, 'Finite native UI format string changed')
            line = first + body[:body.index(template)].count('\n')
            for argument in arguments:
                add(template % argument, util, line, template,
                    native_function=function, expansion={'arguments': list(argument)})
    require('next_button_%c_glow.tga' in text, 'Native next button glow template changed')
    line = text[:text.index('next_button_%c_glow.tga')].count('\n') + 1
    for side in ('L', 'R'):
        add(f'next_button_{side}_glow.tga', util, line, 'next_button_%c_glow.tga',
            native_function='drawNextButton', expansion={'arguments': [side]})

    for relative in POWER_SOURCES:
        path = root/relative
        text = uncomment(path.read_text())
        output['source_files'][relative] = pin(path)
        for match in re.finditer(r'\bIconName\s+"([^"\n]+)"', text):
            add(match[1], relative, text[:match.start()].count('\n') + 1, match[0],
                definition_field='IconName')
    # The trainer deliberately uses generic checked/unchecked boxes and a
    # hovered power help icon. Blank row checkmarks are not missing power icons.
    relative = 'upstream/ouroboros/Game/src/UI/uiLevelPower.c'
    require('powerSetHelp( atlasLoadTexture(psetBase->ppPowers[j]->pchIconName)' in
        (root/relative).read_text(), 'Native trainer dynamic icon caller changed')
    output['source_files'][relative] = pin(root/relative)
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
        'unresolved_dependencies': unresolved}


def discover(args):
    require(pin(args.baseline_archive) == BASE_ARCHIVE_PIN and pin(args.baseline_manifest) == BASE_MANIFEST_PIN,
        'UI requires exact public 0.13.11 appearance donor')
    old = ancestor.read_manifest(args.baseline_manifest, root=args.root)
    files = appearance.load_metadata(old, args.metadata_cache)
    requests = source_requests(args.root)
    retained = previous.retained_names(args.root, old)
    planned = plan(files, requests, retained)
    previous.verify_sources(args.root, requests['source_files'])
    args.output.mkdir(parents=True)
    request_path = args.output/'client-ui-repair-requests.json'
    request_path.write_bytes(canonical(requests) + b'\n')
    public = {key: value for key, value in planned.items() if key != 'selected'}
    public.update({'format': 1, 'scope': SCOPE, 'source_files': requests['source_files'],
        'discovery_requests_pin': pin(request_path), 'file_count': len(planned['selected']),
        'payload_bytes': sum(row['bytes'] for row in planned['selected'].values()),
        'stored_payload_bytes': sum(row['stored_bytes'] for row in planned['selected'].values()),
        'retained_baseline_file_count': ancestor.FILE_COUNT,
        'runtime_visual_validated': False, 'native_renderer_changed': False,
        'native_gameplay_changed': False, 'full_global_asset_closure': False, 'preloading': False})
    plan_path = args.output/'client-ui-repair-plan.json'
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
    downloads = {'u'+key.removeprefix('r'): value for key, value in downloads.items()}
    for row in records.values():
        row['source_download_receipt'] = 'u'+row['source_download_receipt'].removeprefix('r')
    require(not set(downloads).intersection(old['provenance']['sweep_downloads']),
        'UI source receipts overlap an accepted receipt')
    value = copy.deepcopy(old)
    value['provenance']['sweep_downloads'].update(downloads)
    additions = {name: {'bytes': row['bytes'], 'sha256': row['sha256']} for name, row in sorted(records.items())}
    extension = {key: public[key] for key in ('scope', 'file_count', 'payload_bytes',
        'existing_leaf_dependencies', 'unresolved_dependencies', 'runtime_visual_validated',
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
    value['ui_repair_extension'] = extension
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
    (args.output/'client-ui-repair-result.json').write_bytes(canonical(public) + b'\n')
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
