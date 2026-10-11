#!/usr/bin/env python3
"""Build the versioned missing-only original all-zone visual/audio supplement.

The frozen 57 donor name tables, not a running city's observed warnings, define
the complete available resource inventory. Existing imports and all accepted
supplements win. Generated donor BIN/bounds files never replace source-version
caches. Payload integrity is distinct from live map/collision/beacon readiness.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import time
import zipfile
import zlib

import audit_kings_row_foundation as kings
import discover_client_visual_sweep as sweep
import prepare_atlas_world_assets as donor

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE = 'zones-world-supplement.zip'
MANIFEST = 'zones-world-supplement-manifest.json'
VERSION = '1.0.0'
SCOPE = 'coh_all_zones_original_asset_supplement_v1'
MAX_FILES = 30000
MAX_DECODED = 4 * 1024**3
MAX_STORED = 1900 * 1024**2
MAX_ENTRY = 32 * 1024**2
require, canonical, pin = donor.require, donor.canonical, donor.pin


def safe_payload(name):
    if not isinstance(name, str) or not name.isascii() or name != name.casefold():
        return False
    path = PurePosixPath(name)
    return (path.as_posix() == name and not path.is_absolute()
            and all(part not in ('', '.', '..') for part in path.parts)
            and '\\' not in name and ':' not in name
            and (name.startswith(('data/object_library/', 'data/player_library/'))
                 and path.suffix == '.geo'
                 or name.startswith('data/texture_library/') and path.suffix == '.texture'
                 or name.startswith('data/sound/ogg/') and path.suffix == '.ogg'))


def all_metadata(identity, cache):
    # Existing implementation owns exact HTTPS range/ETag/Last-Modified pins.
    sweep.metadata(identity, cache)
    raw = (Path(cache) / identity['archive']).read_bytes()
    pigg = sweep.inspect_piggs
    _, _, _, header, entry, count = pigg.HEADER.unpack_from(raw)
    names, pos = pigg.pool(raw, header + count * entry, 0x6789)
    headers, end = pigg.pool(raw, pos, 0x9ABC)
    require(end == len(raw), 'Incomplete frozen donor metadata')
    files, excluded, ranges = {}, Counter(), []
    for index in range(count):
        flag, nameid, size, _, offset, reserved, headerid, md5, packed = pigg.ENTRY.unpack_from(
            raw, header + index * entry)
        name = pigg.safe_name(names[nameid]); key = 'data/' + name.casefold()
        if not safe_payload(key):
            excluded[PurePosixPath(name).suffix.casefold()] += 1
            continue
        require(flag == 0x3456 and reserved == 0 and offset >= end
                and 0 < size <= MAX_ENTRY and 0 < (packed or size) <= MAX_ENTRY
                and offset + (packed or size) <= identity['source_archive_bytes']
                and (headerid == -1 or 0 <= headerid < len(headers)),
                'Invalid bounded zone payload table')
        require(key not in files, 'Case-colliding zone donor name')
        files[key] = {'identity': identity, 'path': name, 'offset': offset, 'bytes': size,
            'stored_bytes': packed or size, 'compressed': bool(packed), 'md5_table': md5.hex(),
            'cached_header_id': headerid,
            'cached_header': headers[headerid] if headerid >= 0 else b''}
        ranges.append((offset, offset + (packed or size)))
    ranges.sort()
    require(all(a[1] <= b[0] for a, b in zip(ranges, ranges[1:])), 'Overlapping zone payloads')
    return files, dict(excluded)


def build_plan(root, cache):
    names, _, _, current = kings.retained_inventory(root)
    files, excluded = {}, {}
    for identity in current['provenance']['metadata_archives']:
        entries, excluded[identity['archive']] = all_metadata(identity, cache)
        files.update(entries)  # Same frozen last-wins donor ordering as accepted pack.
    selected = {name: row for name, row in files.items() if name not in names}
    require(len(selected) <= MAX_FILES and sum(r['bytes'] for r in selected.values()) <= MAX_DECODED
            and sum(r['stored_bytes'] for r in selected.values()) < MAX_STORED,
            'All-zone supplement exceeds reviewed transport limits')
    sound_names = defaultdict(list)
    for name in files:
        if name.endswith('.ogg'):
            # Native soundLoadCallback indexes basename and stores the original
            # path in an 80-byte buffer; avoid shipping a newly reachable assert.
            require(len(name.removeprefix('data/')) + 1 < 80, 'Sound path exceeds native buffer')
            sound_names[PurePosixPath(name).stem].append(name)
    require(all(len(rows) == 1 for rows in sound_names.values()), 'Ambiguous native sound basename')
    return selected, {'format': 1, 'scope': SCOPE, 'version': VERSION,
        'source_commit': kings.SOURCE, 'data_commit': kings.DATA,
        'selection': 'all_missing_original_geometry_textures_audio_in_57_frozen_donor_tables',
        'frozen_metadata_archives': current['provenance']['metadata_archives'],
        'available_resource_count': len(files), 'retained_file_count': len(names),
        'retained_files_sha256': hashlib.sha256(canonical(names)).hexdigest(),
        'retained_resources_preserved': True, 'missing_only': True,
        'native_sound_name_inventory': {'unique_names': len(sound_names),
            'native_80_byte_path_bound_verified': True, 'duplicate_basename_count': 0,
            'rule_source': 'upstream/ouroboros/Game/src/sound/sound.c:soundLoadCallback'},
        'selected_file_count': len(selected),
        'selected_extensions': dict(sorted(Counter(PurePosixPath(n).suffix for n in selected).items())),
        'decoded_bytes': sum(r['bytes'] for r in selected.values()),
        'original_stored_bytes': sum(r['stored_bytes'] for r in selected.values()),
        'excluded_donor_entries_by_archive_and_suffix': excluded,
        'donor_generated_caches_installed': False,
        'full_source_dependency_closure': False, 'native_all_zone_qualification': False,
        'limitations': ['Availability covers the exact 57 frozen original donor tables, not unlisted archives.',
            'Whole geometry/texture/audio availability does not resolve absent source-era definitions or submodels.',
            'All 5,878 accepted animations and pinned companion scripts/FX/map text remain in the base pack.',
            'Map-specific collision, authentic beacons, arrival and save qualification are separate gates.']}


def verify_payload(row, stored):
    suffix = PurePosixPath(row['path']).suffix.casefold()
    if suffix == '.texture':
        # Full payload size/MD5/header and native geometry/texture structural checks.
        return sweep.verified_payload(row, stored)
    raw = stored
    if row['compressed']:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(stored, row['bytes'] + 1)
        require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
                'Truncated or oversized original audio zlib stream')
    require(len(stored) == row['stored_bytes'] and len(raw) == row['bytes']
            and hashlib.md5(raw).hexdigest() == row['md5_table']
            and raw.startswith(row['cached_header']),
            'Original resource size/MD5/header differs')
    identity = row['identity']
    record = {**{k: row[k] for k in ('path', 'offset', 'bytes', 'stored_bytes', 'compressed',
                                  'md5_table', 'cached_header_id')},
        'source_archive': identity['archive'], 'source_url': sweep.ranges.BASE_URL + identity['archive'],
        **{k: identity[k] for k in ('source_archive_bytes', 'source_etag', 'source_last_modified',
                                    'source_metadata_sha256')},
        'source_content_range': f"bytes {row['offset']}-{row['offset'] + row['stored_bytes'] - 1}/{identity['source_archive_bytes']}",
        'sha256': hashlib.sha256(raw).hexdigest(), 'stored_sha256': hashlib.sha256(stored).hexdigest(),
        'cached_header_sha256': hashlib.sha256(row['cached_header']).hexdigest(),
        'cached_header_bytes': len(row['cached_header']), 'cached_header_verified': True,
        'integrity': 'exact_http_206_range_stable_etag_zlib_size_and_table_md5_passed'}
    if suffix == '.geo':
        record['geometry_header'] = sweep.inspect_piggs.geometry_header(raw)
        require(record['geometry_header']['baseline_loader_accepts_version'], 'Unsupported zone geometry version')
        try:
            require(sweep.geometry.tables(raw) == sweep.geometry.tables(row['cached_header']),
                    'Geometry native model tables changed from frozen header')
            record['model_table_verified'] = True
        except ValueError as error:
            # Empty stock FX placeholders are original donor data, not invented
            # substitutes. Retain and explicitly report the unresolved table;
            # they cannot satisfy a required map collision/model witness.
            require(str(error) == 'Client visual geometry model count differs',
                    'Invalid zone geometry model table: ' + str(error))
            biased, unpacked = struct.unpack_from('<II', raw)
            if unpacked:
                version, start, packed = 0, 8, biased - 4
            else:
                version, _ = struct.unpack_from('<II', raw, 8)
                start, packed = 16, biased - 12
            header = zlib.decompress(raw[start:start + packed])
            blocks = 5 if 2 <= version <= 6 else 4
            sizes = struct.unpack_from('<' + 'I' * blocks, header)
            count_offset = blocks * 4 + sum(sizes[1:]) + 136
            require(sweep.geometry.u32(header, count_offset) == 0,
                    'Nonzero unsupported geometry model count')
            record['model_table_verified'] = False
            record['model_table_gap'] = str(error)
            record['original_model_count'] = 0
        return record
    require(suffix == '.ogg' and raw.startswith(b'OggS\x00'), 'Invalid original Ogg header')
    # Walk every Ogg page. This verifies container framing, not codec fidelity.
    offset, pages = 0, 0
    while offset < len(raw):
        require(offset + 27 <= len(raw) and raw[offset:offset + 5] == b'OggS\x00',
                'Invalid original Ogg page')
        segments = raw[offset + 26]
        require(offset + 27 + segments <= len(raw), 'Truncated Ogg lacing table')
        offset += 27 + segments + sum(raw[offset + 27:offset + 27 + segments])
        require(offset <= len(raw), 'Ogg page exceeds original audio')
        pages += 1
    return {**record,
        'ogg_container': {'pages': pages, 'framing_verified': True, 'codec_playback_verified': False}}


def materialize(group, cache):
    identity = group['identity']
    members = group['members']
    cached = all((cache / hashlib.sha256(name.encode()).hexdigest()).is_file() for name, _ in members)
    transferred = None
    if not cached:
        for attempt in range(3):
            try:
                transferred, receipt = sweep.ranges.partial(sweep.ranges.BASE_URL + identity['archive'],
                    group['start'], group['end'] - group['start'], identity)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(attempt + 1)
    records = {}
    for name, row in members:
        path = cache / hashlib.sha256(name.encode()).hexdigest()
        require(not path.is_symlink(), 'Linked payload cache refused')
        stored = (path.read_bytes() if transferred is None else transferred[
            row['offset'] - group['start']:row['offset'] - group['start'] + row['stored_bytes']])
        record = verify_payload(row, stored)
        if transferred is not None:
            temporary = path.with_suffix('.part')
            require(not temporary.is_symlink(), 'Linked temporary cache refused')
            temporary.write_bytes(stored); temporary.replace(path)
        records[name] = record
    return records


def verify_archive(path, document):
    require(pin(path) == {k: document['archive'][k] for k in ('bytes', 'sha256')},
            'Zone supplement archive pin differs')
    with zipfile.ZipFile(path) as source:
        infos = source.infolist()
        require(len(infos) == len(document['files']) and len({r.filename for r in infos}) == len(infos)
                and {r.filename for r in infos} == set(document['files']), 'Zone supplement inventory differs')
        for row in infos:
            require(safe_payload(row.filename) and stat.S_ISREG(row.external_attr >> 16)
                    and row.flag_bits == 0 and row.compress_type in (0, 8), 'Unsafe zone ZIP entry')
            raw = source.read(row)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                    == document['files'][row.filename], 'Zone supplement decoded payload differs')
    return {'files_verified': len(document['files']), 'payload_bytes': document['payload_bytes']}


def prepare(root, metadata_cache, payload_cache, output, workers=8):
    require(not output.exists() and not output.is_symlink(), 'Preserve existing output; choose a new directory')
    output.mkdir(parents=True)
    payload_cache.mkdir(parents=True, exist_ok=True)
    selected, report = build_plan(root, metadata_cache)
    (output / 'zones-world-plan.json').write_bytes(canonical(report) + b'\n')
    groups, gap_bytes = sweep.payload_groups(selected)
    print(json.dumps({'selected': len(selected), 'groups': len(groups), 'gap_bytes': gap_bytes,
                      'stored_bytes': report['original_stored_bytes']}), flush=True)
    records = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(materialize, group, payload_cache) for group in groups]
        for index, future in enumerate(as_completed(futures), 1):
            records.update(future.result())
            if index % 50 == 0 or index == len(groups):
                print(json.dumps({'groups_completed': index, 'groups_total': len(groups),
                                  'files_verified': len(records)}), flush=True)
    require(set(records) == set(selected), 'Zone materialization incomplete')
    def members():
        for name, row in sorted(records.items()):
            stored = (payload_cache / hashlib.sha256(name.encode()).hexdigest()).read_bytes()
            yield name, *donor.decode_entry(stored, row)
    donor.write_zip_members(output / ARCHIVE, members())
    files = {name: {k: row[k] for k in ('bytes', 'sha256')} for name, row in sorted(records.items())}
    source_world = kings.group_requests(kings.Sources(root))
    retained = kings.retained_inventory(root)[0]
    collision_names = sorted(set(source_world['geometry']) - set(retained))
    require(not source_world['unresolved_source_edges'] and set(collision_names) <= set(files)
            and all(records[name].get('model_table_verified') is True for name in collision_names),
            'Kings Row source-world geometry closure is incomplete')
    collision_files = {name: files[name] for name in collision_names}
    document = {**report, 'archive': {'filename': ARCHIVE, **pin(output / ARCHIVE)},
        'file_count': len(files), 'payload_bytes': sum(row['bytes'] for row in files.values()),
        'files_sha256': hashlib.sha256(canonical(files)).hexdigest(), 'files': files,
        'provenance': {'entries': dict(sorted(records.items()))},
        'kings_row_collision_files': collision_files,
        'kings_row_collision_files_sha256': hashlib.sha256(canonical(collision_files)).hexdigest(),
        'kings_row_source_world_graph_complete': True,
        'model_table_gaps': {name: row['model_table_gap'] for name, row in records.items()
                             if 'model_table_gap' in row},
        'original_payloads_verified': True, 'native_world_load_verified': False,
        'collision_verified': False, 'native_beacon_graph_verified': False,
        'physical_zoning_verified': False}
    verification = verify_archive(output / ARCHIVE, document)
    (output / MANIFEST).write_bytes(canonical(document) + b'\n')
    print(json.dumps({'archive': document['archive'], 'verification': verification}), flush=True)
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--metadata-cache', type=Path, required=True)
    parser.add_argument('--payload-cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    require(1 <= args.workers <= 12, 'Worker bound differs')
    prepare(args.root, args.metadata_cache, args.payload_cache, args.output, args.workers)


if __name__ == '__main__':
    main()
