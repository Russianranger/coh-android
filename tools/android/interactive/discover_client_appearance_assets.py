#!/usr/bin/env python3
"""Append original captured/Atlas costume and sequence dependencies to 0.13.10.

The previous finite sweep, its frozen namespace and every encoded archive member
remain unchanged. This new evidence pass follows newly exposed console names,
source-reachable Atlas costumes, silent ent-type Graphics and referenced FX.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile

import discover_client_visual_sweep as previous
import client_visual_geometry as geometry
import client_visual_tricks as tricks
import prepare_client_visual_assets as baseline_producer

ROOT = Path(__file__).resolve().parents[3]
BASE_ARCHIVE_PIN = dict(baseline_producer.ARCHIVE_PIN)
BASE_MANIFEST_PIN = dict(baseline_producer.MANIFEST_PIN)
BASE_FILES_SHA256 = baseline_producer.FILES_SHA256
BASE_FILE_COUNT, BASE_PAYLOAD_BYTES = 5476, 873255284
CONSOLE_PIN = {'bytes': 1810015, 'sha256': '9916a2e59f41b226cc31e6fae889a48a0b93908640ba6004ec431e5fed9c4f98'}
RESUME_REQUESTS_PIN = {'bytes': 13711043, 'sha256': '5e5899d261898c5a47068dbb608799ec85318c7c570f6eb56af3504b0395272a'}
SCOPE = 'recorded_atlas_npc_sequence_and_costume_dependency_closure'
MAX_ARCHIVE_BYTES, MAX_MANIFEST_BYTES = 1024**3, 64 * 1024**2
MAX_PAYLOAD_BYTES = 2 * 1024**3
require, pin, canonical = previous.require, previous.pin, previous.canonical


def rows_merge(target, source):
    for category in ('geometry', 'textures'):
        for name, rows in source.get(category, {}).items():
            target.setdefault(category, {}).setdefault(name, []).extend(rows)
    for name, expected in source.get('source_files', {}).items():
        require(name not in target['source_files'] or target['source_files'][name] == expected,
            'Appearance source pin conflict: ' + name)
        target['source_files'][name] = expected


def console_requests(console):
    raw = Path(console).read_bytes()
    require(0 < len(raw) <= 16 * 1024**2, 'Appearance console exceeds reviewed bound')
    result = {'format': 1, 'scope': SCOPE,
        'source_console': {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
        'geometry': {}, 'textures': {}, 'source_files': {}, 'observed_enttype_names': []}
    text = raw.decode('utf-8', errors='replace')
    read_types = set()
    for number, line in enumerate(text.splitlines(), 1):
        row = {'console_line_number': number, 'console_line': line}
        material = re.search(r'Texture Trick "([^"]+)" references missing texture "([^"]+)"', line)
        texture = re.search(r'CUSTOM TEXTURE ERROR: (\S+) wants nonexistent texture (\S+) as texture (\d+) on bone (\S+)\.', line)
        model = re.search(r"BAD DATA: Custom Geometry (\S+) in (\S+\.geo) doesn't exist!", line)
        if material:
            for role, name in [('material', material[1]), ('missing_layer', material[2])]:
                if tricks.valid_texture_name(name):
                    result['textures'].setdefault(tricks.texture_stem(name), []).append(row | {
                        'scope': 'new_console_material_dependency', 'alias': name, 'target': name,
                        'parent_material': material[1], 'role': role})
        if texture and tricks.valid_texture_name(texture[2]):
            name = texture[2]
            result['textures'].setdefault(tricks.texture_stem(name), []).append(row | {
                'scope': 'new_console_costume_texture', 'alias': name, 'target': name,
                'body': texture[1], 'bone': texture[4], 'texture_slot': int(texture[3])})
        if model:
            path = 'data/' + model[2].replace('\\', '/').casefold()
            require(previous.safe_payload(path), 'Unsafe exact console geometry filename')
            result['geometry'].setdefault(path, []).append(row | {
                'scope': 'new_console_costume_geometry', 'model': model[1]})
        loaded = re.search(r'\bReading ([^\r\n]+\.txt)\s*$', line)
        if loaded:
            read_types.add(loaded[1].replace('\\', '/').casefold())
    result['observed_enttype_names'] = sorted(read_types)
    return result


def source_lines(path):
    for number, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
        clean = (line.lstrip()[1:] if line.lstrip().casefold().startswith('#include ')
            else line.split('#', 1)[0]).split('//', 1)[0].strip()
        if clean:
            yield number, clean.split()


def enttype_fx_requests(root, files, entity_names, fx_roots=()):
    """Follow silent base Graphics, exact named FX models and particle textures."""
    root = Path(root)
    result = {'geometry': {}, 'textures': {}, 'source_files': {}, 'unresolved_source_edges': []}
    sources = {path.relative_to(root/'upstream/i24/data').as_posix().casefold(): path
        for folder in ('ent_types', 'fx', 'sequencers')
        for path in (root/'upstream/i24/data'/folder).rglob('*') if path.is_file()}
    models = {}
    for name, record in files.items():
        if not name.endswith('.geo'):
            continue
        try:
            _, tables = geometry.tables(record['cached_header'])
        except ValueError:
            continue
        for model in tables:
            models.setdefault(model['name'].split('__', 1)[0].casefold(), set()).add(name)

    def geometry_edge(path, witness, model=None):
        path = 'data/' + path.replace('\\', '/').casefold().removeprefix('data/')
        if not previous.safe_payload(path):
            result['unresolved_source_edges'].append(witness | {'target': path, 'kind': 'unsupported_geometry_path'})
            return
        result['geometry'].setdefault(path, []).append(witness | ({'model': model} if model else {}))

    def texture_edge(name, witness):
        if (tricks.valid_texture_name(name) and tricks.valid_texture_name(tricks.texture_stem(name))
                and name.casefold() not in ('0', 'none', 'null')):
            result['textures'].setdefault(tricks.texture_stem(name), []).append(witness | {
                'target': name, 'alias': name})

    def source_path(value, parent):
        value = value.strip('"').replace('\\', '/').casefold().lstrip('/')
        value = PurePosixPath(value).as_posix()
        if value.startswith(':'):
            key = parent.parent.relative_to(root/'upstream/i24/data').as_posix().casefold() + '/' + value[1:]
        else:
            key = value if value.startswith(('fx/', 'ent_types/', 'sequencers/')) else 'fx/' + value
        return sources.get(key)

    queue = []
    for name in sorted(set(entity_names)):
        key = 'ent_types/' + name.removeprefix('ent_types/').removesuffix('.txt') + '.txt'
        path = sources.get(key.casefold())
        if path:
            queue.append(path)
    for name in sorted(set(fx_roots)):
        key = name.replace('\\', '/').casefold().removeprefix('data/')
        path = sources.get(key)
        if path:
            queue.append(path)
        else:
            result['unresolved_source_edges'].append({'kind': 'exact_fx_root_absent', 'target': name})
    visited = set()
    while queue:
        path = queue.pop()
        if path in visited:
            continue
        visited.add(path)
        relative = path.relative_to(root).as_posix()
        result['source_files'][relative] = pin(path)
        lines = list(source_lines(path))
        values = {tokens[0].casefold(): tokens[1] for _, tokens in lines if len(tokens) > 1}
        for number, tokens in lines:
            if len(tokens) < 2:
                continue
            field, value = tokens[0].casefold(), tokens[1].strip('"')
            witness = {'scope': 'source_atlas_enttype_fx_dependency', 'source_path': relative,
                'source_line': number, 'field': tokens[0], 'target': value}
            if field == 'graphics':
                geometry_edge(value, witness)
            elif field in ('geofile', 'harnessfile'):
                model = values.get('geoname' if field == 'geofile' else 'harnessname')
                geometry_edge('player_library/' + value, witness, model)
            elif field == 'geom':
                if value.casefold() in ('none', '0', 'parent'):
                    continue
                candidates = models.get(value.split('__', 1)[0].casefold(), set())
                if not candidates:
                    result['unresolved_source_edges'].append(witness | {'kind': 'exact_fx_model_absent'})
                for candidate in sorted(candidates):
                    geometry_edge(candidate, witness | {'exact_model_candidate_count': len(candidates)}, value)
            elif field in ('texturename', 'texturename2', 'texture', 'texture1', 'texture2', 'tex1', 'tex2', 'tex3', 'tex4', 'innertex1', 'innertex2', 'shadowtexture'):
                texture_edge(value, witness)
            if field == 'splat':
                for slot, texture in enumerate(tokens[1:3], 1):
                    texture_edge(texture.strip('"'), witness | {'texture_slot': slot})
            for reference in tokens[1:]:
                reference = reference.strip(',"')
                suffix = PurePosixPath(reference.replace('\\', '/')).suffix.casefold()
                if (suffix == '.fx' or suffix in ('.part', '.bhvr', '.cape')
                        and field in ('cape', 'bhvr', 'behavior', 'behaviour', 'part',
                            'part1', 'part2', 'part3', 'part4', 'part5')):
                    child = source_path(reference, path)
                    if child:
                        queue.append(child)
                    else:
                        result['unresolved_source_edges'].append(witness | {
                            'target': reference, 'kind': 'exact_fx_source_absent'})
            if field == 'anim' and path.relative_to(root/'upstream/i24/data').as_posix().startswith('fx/'):
                child = sources.get('ent_types/' + value.replace('\\', '/').casefold().removesuffix('.txt') + '.txt')
                if child:
                    queue.append(child)
                else:
                    result['unresolved_source_edges'].append(witness | {'kind': 'exact_fx_animated_enttype_absent'})
            if field == 'include':
                child = sources.get(value.replace('\\', '/').casefold())
                if child:
                    queue.append(child)
                else:
                    result['unresolved_source_edges'].append(witness | {'kind': 'exact_sequence_include_absent'})
            if field == 'sequencer':
                child = sources.get('sequencers/' + value.replace('\\', '/').casefold())
                if child:
                    queue.append(child)
    result['source_file_count'] = len(visited)
    for relative in ('upstream/ouroboros/Common/fxinfo.c',
            'upstream/ouroboros/Game/src/graphics/FX/fxgeo.c',
            'upstream/ouroboros/Game/src/graphics/FX/fxcapes.c',
            'upstream/ouroboros/Common/seq/seqtype.c'):
        path = root/relative
        if path.is_file():
            result['source_files'][relative] = pin(path)
        elif (root/'.git').exists():
            raw = subprocess.run(['git', 'show', 'HEAD:' + relative], cwd=root,
                check=True, capture_output=True).stdout
            result['source_files'][relative] = previous.pin_bytes(raw)
    return result


def load_metadata(baseline, cache):
    files = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for rows in pool.map(lambda identity: previous.metadata(identity, cache),
                baseline['provenance']['metadata_archives']):
            files.update(rows)
    return files


def exact_dependency_plan(files, requests, retained, trick_index):
    """Resolve exact filename/model/material edges before any payload download."""
    # These keys have already undergone one native texFixName normalization.
    # The source rows retain literal tokens so dot-bearing stems are never
    # stripped a second time while traversing stock definitions.
    texture_requests = {name: list(rows) for name, rows in requests.get('textures', {}).items()}
    chosen, selected_requests, proofs, unresolved = {}, {}, {}, []
    for name, rows in sorted(requests.get('geometry', {}).items()):
        require(previous.safe_payload(name) and name.endswith('.geo') and rows,
            'Sweep geometry request is unsafe or lacks evidence')
        selected = files.get(name.removeprefix('data/'))
        if selected is None:
            unresolved.append({'kind': 'geometry', 'target': name, 'sources': rows})
            continue
        try:
            proof = geometry.requested_model_proof(selected['cached_header'], rows)
        except ValueError as exc:
            # An exact original filename alone cannot override a rejected
            # native table proof. Keep unsupported originals visible as gaps.
            unresolved.append({'kind': 'geometry_header', 'target': name,
                'reason': str(exc), 'cached_header_pin': previous.pin_bytes(selected['cached_header']), 'sources': rows})
            continue
        # A startup missing-file warning proves the filename, without inventing
        # a particular rendered model request. Its native model inventory still
        # supplies the finite original material dependency set.
        if proof['absent_requested_models']:
            unresolved.extend({'kind': 'geometry_model', 'target': model, 'geometry': name,
                'sources': rows} for model in proof['absent_requested_models'])
        if name not in retained:
            chosen[name], selected_requests[name], proofs[name] = selected, previous.evidence_rows(rows), proof
        _, models = geometry.tables(selected['cached_header'])
        if proof['requested_models']:
            models = [model for request in proof['requested_models'] for model in request['matches']]
        for model in models:
            for target in model['direct_texture_names']:
                if tricks.valid_texture_name(target):
                    texture_requests.setdefault(tricks.texture_stem(target), []).append({
                        'scope': 'recorded_geometry_material', 'geometry': name,
                        'model': model['name'], 'target': target, 'alias': target,
                        'native_model_table_sha256': proof['model_table_sha256']})
    texture_paths = {}
    for path in files:
        if path.startswith('texture_library/'):
            texture_paths.setdefault(PurePosixPath(path).stem, []).append(path)
    closure = tricks.resolve_trick_closure(trick_index, texture_requests, native_texture_names=texture_paths)
    composites = {tricks.texture_stem(item['name']) for item in closure['stock_definition_closure']
        if item['composite_generation']['composite_alias_can_be_created']}
    existing, aliases = {}, {}
    for stem, rows in sorted(closure['requests'].items()):
        candidates = texture_paths.get(stem, [])
        if not candidates:
            if stem in composites:
                aliases[stem] = previous.unique_rows(rows)
            else:
                unresolved.append({'kind': 'texture_or_material', 'target': stem,
                    'sources': previous.unique_rows(rows)})
            continue
        require(len(candidates) == 1, 'Sweep refuses ambiguous original texture stems: ' + stem)
        name = 'data/' + candidates[0]
        if name in retained:
            existing[name] = previous.unique_rows(rows)
        else:
            chosen[name], selected_requests[name] = files[candidates[0]], previous.evidence_rows(rows)
    require(sum(row['bytes'] for row in chosen.values()) + BASE_PAYLOAD_BYTES <= MAX_PAYLOAD_BYTES
        and sum(row['stored_bytes'] for row in chosen.values()) + BASE_ARCHIVE_PIN['bytes'] <= MAX_ARCHIVE_BYTES,
        'Appearance composed assets exceed reviewed decoded/storage bounds')
    return {'selected': chosen, 'requests': selected_requests, 'requested_model_proof': proofs,
        'unresolved_dependencies': unresolved, 'stock_composite_aliases': aliases,
        'existing_leaf_dependencies': existing, 'stock_definition_closure': closure['stock_definition_closure'],
        'ambiguous_stock_definitions': closure['ambiguous_stock_definitions'], 'cycles': closure['cycles'],
        'native_leaf_backedges': closure['native_leaf_backedges']}



def dependency_plan(files, requests, retained, stock):
    # The exact accepted resolver is retained above, with explicitly reviewed
    # composed bounds for this larger disk-only append-only appearance set.
    planned = exact_dependency_plan(files, requests, retained, stock)
    require(sum(row['bytes'] for row in planned['selected'].values()) + BASE_PAYLOAD_BYTES <= MAX_PAYLOAD_BYTES
        and sum(row['stored_bytes'] for row in planned['selected'].values()) + BASE_ARCHIVE_PIN['bytes'] <= MAX_ARCHIVE_BYTES,
        'Appearance composed original assets exceed reviewed streaming disk bounds')
    return planned


def reusable_records(selected, cache):
    """Reuse verified individual streams and their original bounded receipts."""
    result = {}
    cache = Path(cache)
    for name, row in sorted(selected.items()):
        path = cache/hashlib.sha256(name.encode()).hexdigest()
        proof_path = path.with_suffix('.download')
        if not path.is_file() or path.is_symlink() or not proof_path.is_file() or proof_path.is_symlink():
            continue
        try:
            require(path.stat().st_size == row['stored_bytes'] and proof_path.stat().st_size <= 4096,
                'Appearance cached source exceeds bound')
            proof = json.loads(proof_path.read_bytes())
            match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', proof.get('content_range', ''))
            require(match is not None, 'Appearance cached receipt is invalid')
            start, end, total = map(int, match.groups())
            require(0 <= start <= row['offset'] and row['offset'] + row['stored_bytes'] - 1 <= end < total
                and total == row['identity']['source_archive_bytes']
                and proof.get('bytes') == end - start + 1 <= previous.MAX_RANGE_BYTES
                and re.fullmatch('[0-9a-f]{64}', proof.get('sha256', '')),
                'Appearance cached member escaped its original receipt')
            record = previous.verified_payload(row, path.read_bytes())
            record.update({'source_member_range': record['source_content_range'],
                'source_download_content_range': proof['content_range'],
                'source_download_bytes': proof['bytes'], 'source_download_sha256': proof['sha256'],
                'source_download_member_bytes': row['stored_bytes']})
            result[name] = record
        except (ValueError, OSError, KeyError, TypeError):
            # A malformed cache is never accepted or silently counted as proof.
            # The bounded original HTTP range will be fetched and verified.
            continue
    return result


def discover(args):
    require(not args.output.exists(), 'Appearance output already exists')
    require(pin(args.baseline_archive) == BASE_ARCHIVE_PIN and pin(args.baseline_manifest) == BASE_MANIFEST_PIN,
        'Appearance requires exact public 0.13.10 visual archive and plaintext manifest')
    baseline = json.loads(args.baseline_manifest.read_bytes())
    require(len(baseline['files']) == BASE_FILE_COUNT and baseline['files_sha256'] == BASE_FILES_SHA256,
        'Appearance baseline inventory differs')
    files = load_metadata(baseline, args.metadata_cache)
    if args.resume_requests is not None:
        require(pin(args.resume_requests) == RESUME_REQUESTS_PIN, 'Appearance continuation request bytes differ')
        requests = json.loads(args.resume_requests.read_bytes())
    elif args.console is not None:
        requests = console_requests(args.console)
    else:
        import prepare_client_appearance_assets
        requests = json.loads(prepare_client_appearance_assets.requests_bytes(args.requests))
    require(requests.get('source_console') == CONSOLE_PIN, 'Appearance console identity differs from frozen device evidence')
    if args.resume_requests is not None:
        roots = ['data/' + name.removeprefix('upstream/i24/data/')
            for name in requests['source_files'] if name.startswith(('upstream/i24/data/fx/',
                'upstream/i24/data/ent_types/', 'upstream/i24/data/sequencers/'))]
        fx = enttype_fx_requests(ROOT, files, (), roots)
        rows_merge(requests, fx)
        requests['source_closure_gaps'] = fx['unresolved_source_edges']
    else:
        import client_appearance_costumes
        known_enttypes = {path.name.casefold() for path in (ROOT/'upstream/i24/data/ent_types').glob('*.txt')}
        costume = client_appearance_costumes.atlas_requests(ROOT, files,
            extra_enttypes=[name for name in requests['observed_enttype_names'] if name in known_enttypes])
        costume['source_files'] = {row['path']: {key: row[key] for key in ('bytes', 'sha256')}
            for row in costume['source_files']}
        rows_merge(requests, costume)
        entities = set(requests['observed_enttype_names']) | set(costume['enttypes'])
        fx = enttype_fx_requests(ROOT, files, entities, costume['fx'])
        rows_merge(requests, fx)
        requests['source_closure_gaps'] = costume['unresolved'] + fx['unresolved_source_edges']
        requests['atlas_source_closure'] = costume['closure']
    requests['source_closure_gaps'] = previous.unique_rows(requests['source_closure_gaps'])
    # modelFind compares the exact prefix before its native '__' trick suffix.
    # Keep that original suffix as evidence instead of reporting a false absence.
    for rows in requests['geometry'].values():
        for row in rows:
            if '__' in row.get('model', ''):
                row['model_find_literal'] = row['model']
                row['model'] = row['model'].split('__', 1)[0]
                row['model_find_rule'] = 'upstream/ouroboros/Common/seq/anim.c:171-172'
    for category in ('geometry', 'textures'):
        requests[category] = {name: previous.unique_rows(rows) for name, rows in sorted(requests[category].items())}
    stock, pins = tricks.stock_tricks(ROOT)
    retained = previous.retained_names(ROOT, baseline)
    planned = dependency_plan(files, requests, retained, stock)
    sources = dict(requests['source_files'])
    for item in planned['stock_definition_closure']:
        sources[item['source_path']] = pins[item['source_path']]
    requests['source_files'] = sources
    previous.verify_sources(ROOT, sources)
    args.output.mkdir(parents=True)
    request_path = args.output/'client-appearance-requests.json'
    request_path.write_bytes(canonical(requests) + b'\n')
    public = {key: value for key, value in planned.items() if key != 'selected'}
    public.update({'format': 1, 'scope': SCOPE, 'source_console': requests['source_console'],
        'source_files': sources, 'source_closure_gaps': requests['source_closure_gaps'],
        'atlas_source_closure': requests['atlas_source_closure'],
        'discovery_requests_pin': pin(request_path), 'file_count': len(planned['selected']),
        'payload_bytes': sum(row['bytes'] for row in planned['selected'].values()),
        'stored_payload_bytes': sum(row['stored_bytes'] for row in planned['selected'].values()),
        'runtime_visual_validated': False, 'native_renderer_changed': False,
        'full_global_asset_closure': False, 'preloading': False,
        'retained_baseline_file_count': BASE_FILE_COUNT})
    (args.output/'client-appearance-plan.json').write_bytes(canonical(public) + b'\n')
    print(json.dumps({k: public[k] for k in ('file_count', 'payload_bytes', 'stored_payload_bytes')}, sort_keys=True), flush=True)
    if args.plan_only:
        return
    records = {}
    records = reusable_records(planned['selected'], args.payload_cache)
    missing = {name: row for name, row in planned['selected'].items() if name not in records}
    print(json.dumps({'reused_verified_original_leaves': len(records), 'new_download_leaves': len(missing)}), flush=True)
    groups, gap_bytes = previous.payload_groups(missing)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = [pool.submit(previous.materialize_group, group, args.payload_cache) for group in groups]
        next_notice = 200
        for job in as_completed(jobs):
            records.update(job.result())
            if len(records) >= next_notice:
                print(json.dumps({'verified_original_leaves': len(records), 'total': len(planned['selected'])}), flush=True)
                next_notice = (len(records) // 200 + 1) * 200
    downloads = previous.centralize_downloads(records)
    renamed = {'a'+key.removeprefix('r'): row for key, row in downloads.items()}
    for row in records.values():
        if 'source_download_receipt' in row:
            row['source_download_receipt'] = 'a'+row['source_download_receipt'].removeprefix('r')
    require(not set(renamed).intersection(baseline['provenance'].get('sweep_downloads', {})),
        'Appearance response receipt would replace a preserved source receipt')
    baseline['provenance'].setdefault('sweep_downloads', {}).update(renamed)
    additions = {name: {'bytes': row['bytes'], 'sha256': row['sha256']} for name, row in sorted(records.items())}
    extension = {'scope': SCOPE, 'missing_only': True, 'baseline_payloads_preserved': True,
        'baseline_archive_pin': BASE_ARCHIVE_PIN, 'baseline_manifest_pin': BASE_MANIFEST_PIN,
        'baseline_file_count': BASE_FILE_COUNT, 'baseline_payload_bytes': BASE_PAYLOAD_BYTES,
        'baseline_files_sha256': BASE_FILES_SHA256, 'file_count': len(additions),
        'payload_bytes': public['payload_bytes'], 'files_sha256': hashlib.sha256(canonical(additions)).hexdigest(),
        'files': {name: {'requests_sha256': hashlib.sha256(canonical(rows)).hexdigest()}
            for name, rows in planned['requests'].items()},
        'discovery_requests_pin': pin(request_path),
        'discovery_plan_pin': pin(args.output/'client-appearance-plan.json'),
        'source_console': requests['source_console'],
        'requested_model_proof': planned['requested_model_proof'],
        'unresolved_dependencies': planned['unresolved_dependencies'],
        'source_closure_gaps': requests['source_closure_gaps'],
        'atlas_source_closure': requests['atlas_source_closure'],
        'full_global_asset_closure': False, 'runtime_visual_validated': False,
        'native_renderer_changed': False, 'preloading': False, 'full_archive_verified': False}
    for key in ('stock_composite_aliases', 'existing_leaf_dependencies', 'stock_definition_closure',
            'ambiguous_stock_definitions', 'cycles', 'native_leaf_backedges'):
        extension[key] = planned[key]
    require(not set(additions).intersection(baseline['files']), 'Appearance replaces a baseline leaf')
    baseline['files'].update(additions); baseline['requests'].update(planned['requests'])
    baseline['provenance']['entries'].update(records)
    for name, expected in sources.items():
        require(name not in baseline['source_files'] or baseline['source_files'][name] == expected,
            'Appearance would change a preserved source witness')
    baseline['source_files'].update(sources)
    baseline['appearance_extension'] = extension
    baseline['file_count'] = len(baseline['files'])
    baseline['payload_bytes'] = sum(row['bytes'] for row in baseline['files'].values())
    baseline['files_sha256'] = hashlib.sha256(canonical(baseline['files'])).hexdigest()
    archive = args.output/'client-visual-assets.zip'
    # The old stream writer copies original local/central records for every
    # retained member. Its inventory comes from the immediate public donor.
    previous.write_extended_zip(archive, args.baseline_archive,
        json.loads(args.baseline_manifest.read_bytes()), records, args.payload_cache)
    require(archive.stat().st_size <= MAX_ARCHIVE_BYTES, 'Appearance output archive exceeds bound')
    baseline['archive'] = {'filename': archive.name, **pin(archive)}
    manifest = args.output/'client-visual-manifest.json'
    manifest.write_bytes(canonical(baseline) + b'\n')
    require(manifest.stat().st_size <= MAX_MANIFEST_BYTES, 'Appearance output manifest exceeds bound')
    public.update({'archive': pin(archive), 'manifest': pin(manifest),
        'added_files_sha256': extension['files_sha256'], 'files_sha256': baseline['files_sha256'],
        'total_file_count': baseline['file_count'], 'total_payload_bytes': baseline['payload_bytes'],
        'payload_partial_transfer_count': len(groups), 'bounded_transfer_gap_bytes': gap_bytes})
    (args.output/'client-appearance-result.json').write_bytes(canonical(public) + b'\n')
    print(json.dumps({k: public[k] for k in ('archive', 'manifest', 'total_file_count', 'total_payload_bytes')}, sort_keys=True), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    evidence = parser.add_mutually_exclusive_group(required=True)
    evidence.add_argument('--console', type=Path)
    evidence.add_argument('--resume-requests', type=Path, help='Continue the exact recovered v3 source request checkpoint')
    evidence.add_argument('--requests', type=Path, help='Replay pinned console/source requests without a device attachment')
    parser.add_argument('--baseline-archive', type=Path, required=True)
    parser.add_argument('--baseline-manifest', type=Path, required=True)
    parser.add_argument('--metadata-cache', type=Path, required=True)
    parser.add_argument('--payload-cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=8, choices=range(1, 17))
    parser.add_argument('--plan-only', action='store_true')
    discover(parser.parse_args())
