#!/usr/bin/env python3
"""Freeze finite original missing-asset dependencies recorded by the 0.13.9 client.

Only frozen PIGG metadata prefixes and individually bounded original file ranges
are read. The output appends to the immediate accepted visual ZIP and preserves
its encoded member streams. Discovery does not change native rendering, caches,
costumes, imported assets or preload assets into the client.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct
import subprocess
import sys
import time
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import inspect_piggs
import client_visual_geometry as geometry
import client_visual_tricks as tricks
import discover_client_visual_candidates as ranges
import prepare_atlas_world_assets as donor

BASE_ARCHIVE_PIN = {'bytes': 25400546, 'sha256': 'e7caf3f505ecf9fef0efc4dbb34c1aedc2905afbe58c0ac26bbcc03f6f71ccda'}
BASE_MANIFEST_PIN = {'bytes': 1145658, 'sha256': '32cd85c643e2748532bf5ea4ba66d4ef843d58af07c5ebd276f99bad8e38014c'}
BASE_FILES_SHA256 = '07b61f301355f2bb0174db2b41f1254b3f2b80cfd660d5f467415c7f33707c09'
CONSOLE_PIN = {'bytes': 1902345, 'sha256': '1f532e7a18c57b5e0cb77fa7e79d9d5f85dee628b7af6aa1a63de46995c9fba2'}
SCOPE = 'recorded_client_missing_asset_dependency_closure'
REQUEST_SCOPE = 'recorded_client_missing_asset_dependency'
MAX_METADATA_BYTES, MAX_ENTRY_BYTES = 40 * 1024**2, 32 * 1024**2
MAX_ARCHIVE_BYTES, MAX_MANIFEST_BYTES = 512 * 1024**2, 16 * 1024**2
MAX_DECODED_BYTES = 1024 * 1024**2
MAX_RANGE_BYTES, MAX_RANGE_GAP = 16 * 1024**2, 32768
MAX_TOTAL_GAP_BYTES = 64 * 1024**2
require, canonical, pin = donor.require, donor.canonical, donor.pin


def safe_payload(name):
    path = PurePosixPath(name)
    return (name == name.casefold() and path.as_posix() == name and name.isascii()
        and '\\' not in name and ':' not in name and '..' not in path.parts
        and (name.startswith(('data/player_library/', 'data/object_library/')) and path.suffix == '.geo'
             or name.startswith('data/texture_library/') and path.suffix == '.texture'))


def unique_rows(rows):
    """Preserve every distinct source witness without multiplying shared edges."""
    return [json.loads(key) for key in sorted({canonical(row).decode() for row in rows})]


def evidence_rows(rows):
    output = []
    for original in rows:
        row = dict(original)
        row['evidence_scope'] = row.pop('scope', 'source_dependency')
        row['scope'] = REQUEST_SCOPE
        output.append(row)
    return unique_rows(output)


def metadata(identity, cache):
    path = Path(cache) / identity['archive']
    if path.is_file():
        raw = path.read_bytes()
    else:
        raw, _ = ranges.partial(ranges.BASE_URL + identity['archive'], 0,
            identity['source_metadata_bytes'], identity)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    require(len(raw) == identity['source_metadata_bytes']
        and hashlib.sha256(raw).hexdigest() == identity['source_metadata_sha256'],
        'Sweep metadata prefix differs from accepted frozen donor: ' + identity['archive'])
    magic, creator, reader, hs, es, count = inspect_piggs.HEADER.unpack_from(raw)
    require((magic, creator, hs, es) == (0x123, 2, 16, 48) and reader <= 2,
        'Unsupported sweep PIGG metadata layout')
    names, pos = inspect_piggs.pool(raw, hs + count * es, 0x6789)
    headers, end = inspect_piggs.pool(raw, pos, 0x9ABC)
    require(end == len(raw) and len(names) == count, 'Sweep metadata prefix is incomplete')
    result, seen = {}, set()
    for index in range(count):
        flag, nameid, size, stamp, offset, reserved, headerid, md5, packed = inspect_piggs.ENTRY.unpack_from(raw, hs + index * es)
        require(flag == 0x3456 and reserved == 0 and 0 <= nameid < count
            and (headerid == -1 or 0 <= headerid < len(headers)), 'Invalid sweep file table')
        name = inspect_piggs.safe_name(names[nameid])
        lower = name.casefold()
        require(lower not in seen, 'Sweep metadata has case-colliding paths')
        seen.add(lower)
        if not safe_payload('data/' + lower):
            continue
        require(headerid >= 0 and offset >= end and 0 < size <= MAX_ENTRY_BYTES
            and 0 < (packed or size) <= MAX_ENTRY_BYTES
            and offset + (packed or size) <= identity['source_archive_bytes'],
            'Sweep original leaf lacks a cached header or has invalid bounds')
        result[lower] = {'identity': identity, 'path': name, 'offset': offset, 'bytes': size,
            'stored_bytes': packed or size, 'compressed': bool(packed), 'md5_table': md5.hex(),
            'cached_header_id': headerid, 'cached_header': headers[headerid]}
    return result


def retained_names(root, baseline):
    original = json.loads((root / 'assets/reference-inputs-manifest.json').read_text())
    retained = {'data/' + row['path'].casefold() for row in original['files']}
    for filename in ('character-avatar-defaults-manifest.json', 'atlas-world-supplement-manifest.json'):
        retained.update(json.loads((root / 'assets' / filename).read_text())['files'])
    retained.update(baseline['files'])
    return retained


def plan(files, requests, retained, trick_index):
    """Resolve exact filename/model/material edges before any payload download."""
    # These keys have already undergone one native texFixName normalization.
    # The source rows retain literal tokens so dot-bearing stems are never
    # stripped a second time while traversing stock definitions.
    texture_requests = {name: list(rows) for name, rows in requests.get('textures', {}).items()}
    chosen, selected_requests, proofs, unresolved = {}, {}, {}, []
    for name, rows in sorted(requests.get('geometry', {}).items()):
        require(safe_payload(name) and name.endswith('.geo') and rows,
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
                'reason': str(exc), 'cached_header_pin': pin_bytes(selected['cached_header']), 'sources': rows})
            continue
        # A startup missing-file warning proves the filename, without inventing
        # a particular rendered model request. Its native model inventory still
        # supplies the finite original material dependency set.
        if proof['absent_requested_models']:
            unresolved.extend({'kind': 'geometry_model', 'target': model, 'geometry': name,
                'sources': rows} for model in proof['absent_requested_models'])
        if name not in retained:
            chosen[name], selected_requests[name], proofs[name] = selected, evidence_rows(rows), proof
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
                aliases[stem] = unique_rows(rows)
            else:
                unresolved.append({'kind': 'texture_or_material', 'target': stem,
                    'sources': unique_rows(rows)})
            continue
        require(len(candidates) == 1, 'Sweep refuses ambiguous original texture stems: ' + stem)
        name = 'data/' + candidates[0]
        if name in retained:
            existing[name] = unique_rows(rows)
        else:
            chosen[name], selected_requests[name] = files[candidates[0]], evidence_rows(rows)
    require(sum(row['bytes'] for row in chosen.values()) <= MAX_DECODED_BYTES
        and sum(row['stored_bytes'] for row in chosen.values()) + BASE_ARCHIVE_PIN['bytes'] < MAX_ARCHIVE_BYTES,
        'Finite sweep exceeds reviewed decoded/storage bounds')
    return {'selected': chosen, 'requests': selected_requests, 'requested_model_proof': proofs,
        'unresolved_dependencies': unresolved, 'stock_composite_aliases': aliases,
        'existing_leaf_dependencies': existing, 'stock_definition_closure': closure['stock_definition_closure'],
        'ambiguous_stock_definitions': closure['ambiguous_stock_definitions'], 'cycles': closure['cycles'],
        'native_leaf_backedges': closure['native_leaf_backedges']}


def verified_payload(selected, stored):
    raw = stored
    if selected['compressed']:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(stored, selected['bytes'] + 1)
        require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
            'Sweep original zlib stream differs')
    require(len(stored) == selected['stored_bytes'] and len(raw) == selected['bytes']
        and hashlib.md5(raw).hexdigest() == selected['md5_table']
        and raw.startswith(selected['cached_header']), 'Sweep original size/MD5/cached header differs')
    record = {key: selected[key] for key in ('path', 'offset', 'bytes', 'stored_bytes', 'compressed',
        'md5_table', 'cached_header_id')}
    identity = selected['identity']
    record.update({'source_url': ranges.BASE_URL + identity['archive'], 'source_archive': identity['archive'],
        **{key: identity[key] for key in ('source_archive_bytes', 'source_etag', 'source_last_modified', 'source_metadata_sha256')},
        'source_content_range': f"bytes {selected['offset']}-{selected['offset'] + selected['stored_bytes'] - 1}/{identity['source_archive_bytes']}",
        'sha256': hashlib.sha256(raw).hexdigest(), 'stored_sha256': hashlib.sha256(stored).hexdigest(),
        'cached_header_bytes': len(selected['cached_header']),
        'cached_header_sha256': hashlib.sha256(selected['cached_header']).hexdigest(), 'cached_header_verified': True,
        'integrity': 'exact_http_206_range_stable_etag_zlib_size_and_table_md5_passed'})
    if selected['path'].casefold().endswith('.geo'):
        record['geometry_header'] = inspect_piggs.geometry_header(raw)
        require(record['geometry_header'].get('baseline_loader_accepts_version') is True
            and geometry.tables(raw) == geometry.tables(selected['cached_header']),
            'Sweep payload native GEO model table differs from frozen metadata')
    else:
        header, body, width, height = struct.unpack_from('<IIII', raw)
        require(32 < header <= 1056 and len(raw) >= header + body
            and 0 < width <= 16384 and 0 < height <= 16384 and b'\0' in raw[32:header],
            'Sweep original texture header is invalid')
        original = raw[32:header].split(b'\0')[0].decode('ascii')
        require(original.casefold().startswith('texture_library/')
            and tricks.texture_stem(original) == tricks.texture_stem(selected['path']),
            'Sweep original texture name differs')
        record['texture_header'] = {'data_bounds_verified': True, 'header_bytes': header,
            'height': height, 'width': width, 'original_name': original, 'struct_bytes': 32}
    return record


def materialize_one(item, cache):
    name, selected = item
    cache_path = Path(cache) / hashlib.sha256(name.encode()).hexdigest()
    if cache_path.is_file():
        stored = cache_path.read_bytes()
    else:
        error = None
        for attempt in range(3):
            try:
                stored, _ = ranges.partial(ranges.BASE_URL + selected['identity']['archive'],
                    selected['offset'], selected['stored_bytes'], selected['identity'])
                break
            except Exception as exc:
                error = exc
                if attempt == 2:
                    raise
                time.sleep(attempt + 1)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(stored)
    return name, verified_payload(selected, stored)


def payload_groups(selected):
    """Coalesce only bounded neighboring requested original file streams."""
    rows = sorted(selected.items(), key=lambda item: (item[1]['identity']['archive'], item[1]['offset']))
    groups, gap_bytes = [], 0
    for name, row in rows:
        start, end = row['offset'], row['offset'] + row['stored_bytes']
        previous = groups[-1] if groups else None
        gap = start - previous['end'] if previous else 0
        if (previous and previous['identity'] == row['identity'] and 0 <= gap <= MAX_RANGE_GAP
                and end - previous['start'] <= MAX_RANGE_BYTES
                and gap_bytes + gap <= MAX_TOTAL_GAP_BYTES):
            previous['end'] = end
            previous['members'].append((name, row))
            gap_bytes += gap
        else:
            groups.append({'identity': row['identity'], 'start': start, 'end': end,
                'members': [(name, row)]})
    return groups, gap_bytes


def materialize_group(group, cache):
    identity = group['identity']
    range_text = f"bytes {group['start']}-{group['end'] - 1}/{identity['source_archive_bytes']}"
    cached, download_proof = True, None
    for name, row in group['members']:
        path = Path(cache) / hashlib.sha256(name.encode()).hexdigest()
        receipt = path.with_suffix('.download')
        proof = json.loads(receipt.read_text()) if receipt.is_file() else None
        if (not path.is_file() or proof is None or proof.get('content_range') != range_text
                or proof.get('bytes') != group['end'] - group['start']
                or len(proof.get('sha256', '')) != 64
                or download_proof is not None and proof != download_proof):
            cached = False
            break
        download_proof = proof
    transferred = None
    if not cached:
        for attempt in range(3):
            try:
                transferred, receipt = ranges.partial(ranges.BASE_URL + identity['archive'],
                    group['start'], group['end'] - group['start'], identity)
                require(receipt == range_text, 'Sweep grouped range receipt differs')
                download_proof = {'content_range': range_text,
                    'bytes': len(transferred), 'sha256': hashlib.sha256(transferred).hexdigest()}
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(attempt + 1)
    result = []
    Path(cache).mkdir(parents=True, exist_ok=True)
    for name, row in group['members']:
        path = Path(cache) / hashlib.sha256(name.encode()).hexdigest()
        stored = (path.read_bytes() if transferred is None else
            transferred[row['offset'] - group['start']:row['offset'] - group['start'] + row['stored_bytes']])
        record = verified_payload(row, stored)
        # source_content_range is the precise member range the stable producer
        # can replay. This separate receipt records the actual HTTP response,
        # including any explicitly bounded neighboring bytes.
        record.update({'source_member_range': record['source_content_range'],
            'source_download_content_range': download_proof['content_range'],
            'source_download_bytes': download_proof['bytes'],
            'source_download_sha256': download_proof['sha256'],
            'source_download_member_bytes': row['stored_bytes']})
        if transferred is not None:
            temporary = path.with_suffix('.tmp')
            temporary.write_bytes(stored)
            temporary.replace(path)
            path.with_suffix('.download').write_bytes(canonical(download_proof))
        result.append((name, record))
    return result


def centralize_downloads(records):
    """Bind every member to one actual receipt without repeating it thousands of times."""
    receipts = {}
    for row in records.values():
        key = row['source_archive'], row['source_download_content_range']
        proof = {'source_archive': key[0], 'content_range': key[1],
            'bytes': row['source_download_bytes'], 'sha256': row['source_download_sha256']}
        require(key not in receipts or receipts[key] == proof, 'Sweep grouped source receipts disagree')
        receipts[key] = proof
    keys = {key: 'r' + str(index).zfill(4) for index, key in enumerate(sorted(receipts))}
    for row in records.values():
        key = row['source_archive'], row['source_download_content_range']
        row['source_download_receipt'] = keys[key]
        for field in ('source_download_content_range', 'source_download_bytes',
                'source_download_sha256', 'source_download_member_bytes'):
            del row[field]
    return {keys[key]: receipts[key] for key in sorted(receipts)}


def write_extended_zip(output, baseline_archive, baseline, records, cache):
    """Only one decoded leaf is live; accepted raw DEFLATE bytes remain exact."""
    with zipfile.ZipFile(baseline_archive) as original, Path(baseline_archive).open('rb') as source:
        require({info.filename for info in original.infolist()} == set(baseline['files']),
            'Immediate donor ZIP inventory differs')
        def members():
            for name in sorted(set(baseline['files']) | set(records)):
                if name in records:
                    stored = (Path(cache) / hashlib.sha256(name.encode()).hexdigest()).read_bytes()
                    yield name, *donor.decode_entry(stored, records[name])
                    continue
                info = original.getinfo(name)
                raw = original.read(info)
                require(pin_bytes(raw) == baseline['files'][name] and info.flag_bits == 0,
                    'Immediate donor visual payload differs')
                source.seek(info.header_offset)
                header = source.read(30)
                signature, _, flags, method, _, _, crc, packed, size, name_size, extra_size = struct.unpack('<IHHHHHIIIHH', header)
                require(signature == 0x04034b50 and flags == 0 and method == info.compress_type
                    and crc == info.CRC and packed == info.compress_size and size == info.file_size
                    and source.read(name_size) == name.encode('ascii') and extra_size == 0,
                    'Immediate donor visual ZIP header differs')
                encoded = source.read(packed)
                require(len(encoded) == packed, 'Immediate donor visual encoded member is truncated')
                yield name, raw, encoded, method
        donor.write_zip_members(output, members())


def pin_bytes(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def verify_sources(root, sources):
    for name, expected in sources.items():
        relative = PurePosixPath(name)
        require(relative.as_posix() == name and '..' not in relative.parts
            and ':' not in name and '\\' not in name
            and name.startswith(('upstream/', 'assets/', 'tools/')),
            'Unsafe sweep source proof path')
        path = root / name
        if path.is_file():
            actual = pin(path)
        else:
            # Sparse local checkouts can verify the tracked original blob;
            # hosted full checkouts read exactly the same tracked source file.
            raw = subprocess.run(['git', 'show', 'HEAD:' + name], cwd=root,
                check=True, capture_output=True).stdout
            require(0 < len(raw) <= 8 * 1024**2, 'Sweep source proof exceeds byte bound')
            actual = pin_bytes(raw)
        require(actual == expected, 'Sweep stock source proof changed: ' + name)


def discover(args):
    output, root = args.output, ROOT
    require(not output.exists(), 'Sweep output already exists')
    require(pin(args.baseline_archive) == BASE_ARCHIVE_PIN and pin(args.baseline_manifest) == BASE_MANIFEST_PIN,
        'Sweep must retain exact immediate 0.13.9 visual donor')
    baseline = json.loads(args.baseline_manifest.read_text())
    require(len(baseline['files']) == 329 and hashlib.sha256(canonical(baseline['files'])).hexdigest() == BASE_FILES_SHA256,
        'Sweep baseline visual leaf pins differ')
    requests = json.loads(args.requests.read_text())
    require(requests.get('source_console') == CONSOLE_PIN, 'Sweep request console identity differs')
    identities = baseline['provenance']['metadata_archives']
    require(sum(row['source_metadata_bytes'] for row in identities) <= MAX_METADATA_BYTES
        and [row['archive'] for row in identities] == sorted([row['archive'] for row in identities], key=str.casefold),
        'Sweep metadata inventory exceeds reviewed bounds or overwrite order')
    files = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for rows in pool.map(lambda identity: metadata(identity, args.metadata_cache), identities):
            files.update(rows)
    trick_index, trick_pins = tricks.stock_tricks(root)
    planned = plan(files, requests, retained_names(root, baseline), trick_index)
    sources = dict(requests.get('source_files', {}))
    for item in planned['stock_definition_closure']:
        sources[item['source_path']] = trick_pins[item['source_path']]
    verify_sources(root, sources)
    public = {key: value for key, value in planned.items() if key != 'selected'}
    public.update({'format': 1, 'scope': SCOPE, 'source_console': CONSOLE_PIN,
        'file_count': len(planned['selected']), 'payload_bytes': sum(row['bytes'] for row in planned['selected'].values()),
        'stored_payload_bytes': sum(row['stored_bytes'] for row in planned['selected'].values()), 'source_files': sources,
        'runtime_visual_validated': False, 'native_renderer_changed': False, 'preloading': False,
        'full_global_asset_closure': False, 'source_archives_fully_downloaded': False})
    output.mkdir(parents=True)
    (output / 'client-visual-sweep-plan.json').write_text(json.dumps(public, indent=2, sort_keys=True) + '\n')
    print(json.dumps({key: public[key] for key in ('file_count', 'payload_bytes', 'stored_payload_bytes')}, sort_keys=True), flush=True)
    if args.plan_only:
        return
    records = {}
    groups, gap_bytes = payload_groups(planned['selected'])
    public.update({'payload_partial_transfer_count': len(groups), 'bounded_transfer_gap_bytes': gap_bytes,
        'maximum_partial_transfer_bytes': max(group['end'] - group['start'] for group in groups)})
    print(json.dumps({key: public[key] for key in ('payload_partial_transfer_count',
        'bounded_transfer_gap_bytes', 'maximum_partial_transfer_bytes')}, sort_keys=True), flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = [pool.submit(materialize_group, group, args.payload_cache) for group in groups]
        next_notice = 200
        for job in as_completed(jobs):
            records.update(job.result())
            if len(records) >= next_notice:
                print(json.dumps({'verified_original_leaves': len(records), 'total': len(planned['selected'])}), flush=True)
                next_notice = (len(records) // 200 + 1) * 200
    additions = {name: {'bytes': row['bytes'], 'sha256': row['sha256']} for name, row in sorted(records.items())}
    downloads = centralize_downloads(records)
    baseline['files'].update(additions)
    baseline['requests'].update(planned['requests'])
    baseline['provenance']['entries'].update(records)
    baseline['provenance']['sweep_downloads'] = downloads
    baseline['source_files'].update(sources)
    baseline['file_count'] = len(baseline['files'])
    baseline['payload_bytes'] = sum(row['bytes'] for row in baseline['files'].values())
    baseline['files_sha256'] = hashlib.sha256(canonical(baseline['files'])).hexdigest()
    extension = {'scope': SCOPE, 'missing_only': True, 'baseline_payloads_preserved': True,
        'baseline_archive_pin': BASE_ARCHIVE_PIN, 'baseline_manifest_pin': BASE_MANIFEST_PIN,
        'baseline_file_count': 329, 'baseline_payload_bytes': 39521237, 'baseline_files_sha256': BASE_FILES_SHA256,
        'file_count': len(additions), 'payload_bytes': public['payload_bytes'],
        'files_sha256': hashlib.sha256(canonical(additions)).hexdigest(),
        'files': {name: {'requests_sha256': hashlib.sha256(canonical(rows)).hexdigest()}
            for name, rows in planned['requests'].items()},
        'discovery_requests_pin': pin(args.requests),
        'source_console': CONSOLE_PIN, 'requested_model_proof': planned['requested_model_proof'],
        'unresolved_dependencies': planned['unresolved_dependencies'],
        'stock_composite_aliases': {stem: {'requests_sha256': hashlib.sha256(canonical(rows)).hexdigest(),
            'request_count': len(rows)} for stem, rows in planned['stock_composite_aliases'].items()},
        'ambiguous_stock_definitions': planned['ambiguous_stock_definitions'], 'cycles': planned['cycles'],
        'native_leaf_backedges': planned['native_leaf_backedges'],
        'runtime_visual_validated': False, 'full_global_asset_closure': False, 'native_renderer_changed': False,
        'preloading': False, 'full_archive_verified': False}
    baseline['sweep_extension'] = extension
    # The historical object is copied first so composition cannot erase its
    # accepted 329-leaf rows, requests, provenance or prior evidence objects.
    original_baseline = json.loads(args.baseline_manifest.read_text())
    archive = output / 'client-visual-assets.zip'
    write_extended_zip(archive, args.baseline_archive, original_baseline, records, args.payload_cache)
    require(archive.stat().st_size <= MAX_ARCHIVE_BYTES, 'Sweep output archive exceeds reviewed bound')
    baseline['archive'] = {'filename': archive.name, **pin(archive)}
    manifest = output / 'client-visual-manifest.json'
    manifest.write_bytes(canonical(baseline) + b'\n')
    require(manifest.stat().st_size <= MAX_MANIFEST_BYTES, 'Sweep output manifest exceeds reviewed bound')
    public.update({'archive': pin(archive), 'manifest': pin(manifest),
        'added_files_sha256': extension['files_sha256'], 'files_sha256': baseline['files_sha256'],
        'total_file_count': baseline['file_count'], 'total_payload_bytes': baseline['payload_bytes']})
    (output / 'client-visual-sweep-result.json').write_text(json.dumps(public, indent=2, sort_keys=True) + '\n')
    print(json.dumps({key: public[key] for key in ('archive', 'manifest', 'total_file_count', 'total_payload_bytes',
        'added_files_sha256', 'files_sha256')}, sort_keys=True), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--requests', type=Path, default=ROOT / 'assets/client-visual-sweep-requests.json')
    parser.add_argument('--baseline-archive', type=Path, required=True)
    parser.add_argument('--baseline-manifest', type=Path, required=True)
    parser.add_argument('--metadata-cache', type=Path, required=True)
    parser.add_argument('--payload-cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=8, choices=range(1, 17))
    parser.add_argument('--plan-only', action='store_true')
    discover(parser.parse_args())
