#!/usr/bin/env python3
"""Read frozen donor metadata and only exact Atlas encounter texture leaves.

This discovery never publishes, mutates imports or downloads a whole PIGG.
The old metadata SHA256/ETag inventory fixes overwrite order; selected original
payloads additionally pass size/zlib/table MD5 and cached-header checks.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct
import sys
import urllib.request
import zlib

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import inspect_piggs
import prepare_atlas_world_assets as donor

CONSOLE_PIN = {'bytes': 1334723, 'sha256': 'ebec9cac51bfa68b5dcd1ec40ec0c85b74041af1b4ef7faf5cf5bd1e2eb3ed5c'}
TARGETS = ('chest_bm_labcoat_01a', 'chest_bm_labcoat_01b', 'face_skin_bf_25asian3',
    'face_skin_bf_45black1', 'chest_bm_flannel_01a', 'chest_bm_flannel_01b')
BASE_URL = 'https://dists.thunderspy.org/piggs/'
MAX_METADATA_BYTES = 40 * 1024**2
MAX_PAYLOAD_BYTES = 16 * 1024**2
require = donor.require


def partial(url, start, size, identity):
    total = identity['source_archive_bytes']
    require(url == BASE_URL + identity['archive'] and 0 <= start < total
        and 0 < size <= MAX_METADATA_BYTES and start + size <= total,
        'Candidate discovery requested an unbounded or unreviewed donor range')
    expected = f'bytes {start}-{start + size - 1}/{total}'
    request = urllib.request.Request(url, headers={'Range': f'bytes={start}-{start + size - 1}',
        'If-Match': identity['source_etag'], 'User-Agent': 'coh-exact-atlas-encounter-leaves/1'})
    with urllib.request.urlopen(request, timeout=45) as response:
        require(response.status == 206 and response.geturl() == url
            and response.headers.get('ETag') == identity['source_etag']
            and response.headers.get('Last-Modified') == identity['source_last_modified']
            and response.headers.get('Content-Range') == expected
            and int(response.headers.get('Content-Length', -1)) == size,
            'Candidate donor changed or refused the exact pinned partial transfer')
        data = response.read(size + 1)
    require(len(data) == size, 'Candidate partial transfer was truncated')
    return data, expected


def metadata(identity):
    url = BASE_URL + identity['archive']
    raw, _ = partial(url, 0, identity['source_metadata_bytes'], identity)
    require(hashlib.sha256(raw).hexdigest() == identity['source_metadata_sha256'],
        'Candidate source metadata differs from the retained 0.13.8 donor')
    magic, creator, reader, hs, es, count = inspect_piggs.HEADER.unpack_from(raw)
    require((magic, creator, hs, es) == (0x123, 2, 16, 48) and reader <= 2,
        'Unsupported candidate PIGG metadata layout')
    names, pos = inspect_piggs.pool(raw, hs + count * es, 0x6789)
    headers, end = inspect_piggs.pool(raw, pos, 0x9ABC)
    require(end == len(raw) and len(names) == count,
        'Candidate metadata prefix is not exactly the complete frozen tables')
    found, seen = {}, set()
    for index in range(count):
        flag, nameid, size, stamp, offset, reserved, headerid, md5, packed = inspect_piggs.ENTRY.unpack_from(raw, hs + index * es)
        require(flag == 0x3456 and reserved == 0 and 0 <= nameid < count
            and (headerid == -1 or 0 <= headerid < len(headers)), 'Invalid candidate file table')
        name = inspect_piggs.safe_name(names[nameid])
        lower = name.casefold()
        require(lower not in seen, 'Candidate metadata has case-colliding paths')
        seen.add(lower)
        if not lower.startswith('texture_library/') or not lower.endswith('.texture'):
            continue
        stem = PurePosixPath(lower).stem
        if stem not in TARGETS:
            continue
        require(stem not in found and headerid >= 0 and offset >= end
            and 0 < size <= MAX_PAYLOAD_BYTES and 0 < (packed or size) <= MAX_PAYLOAD_BYTES
            and offset + (packed or size) <= identity['source_archive_bytes'],
            'Candidate exact texture has ambiguous names or invalid payload bounds')
        found[stem] = {'identity': identity, 'path': name, 'offset': offset, 'bytes': size,
            'stored_bytes': packed or size, 'compressed': bool(packed), 'md5_table': md5.hex(),
            'cached_header_id': headerid, 'cached_header': headers[headerid]}
    return identity['archive'], found


def texture(selected):
    identity, name = selected['identity'], selected['path']
    raw, content_range = partial(BASE_URL + identity['archive'], selected['offset'], selected['stored_bytes'], identity)
    stored = raw
    if selected['compressed']:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(stored, selected['bytes'] + 1)
        require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
            'Candidate texture zlib stream differs')
    require(len(raw) == selected['bytes'] and hashlib.md5(raw).hexdigest() == selected['md5_table']
        and raw.startswith(selected['cached_header']), 'Candidate texture size/MD5/cached header differs')
    header, body, width, height = struct.unpack_from('<IIII', raw)
    require(32 < header <= 1056 and len(raw) >= header + body
        and 0 < width <= 16384 and 0 < height <= 16384 and b'\0' in raw[32:header],
        'Candidate original texture header is invalid')
    original = raw[32:header].split(b'\0')[0].decode('ascii')
    require(original.casefold().startswith('texture_library/')
        and PurePosixPath(original).stem.casefold() == PurePosixPath(name).stem.casefold(),
        'Candidate original texture name differs')
    record = {key: selected[key] for key in ('path', 'offset', 'bytes', 'stored_bytes', 'compressed',
        'md5_table', 'cached_header_id')}
    record.update({'source_url': BASE_URL + identity['archive'], 'source_archive': identity['archive'],
        **{k: identity[k] for k in ('source_archive_bytes', 'source_etag', 'source_last_modified', 'source_metadata_sha256')},
        'source_content_range': content_range, 'sha256': hashlib.sha256(raw).hexdigest(),
        'stored_sha256': hashlib.sha256(stored).hexdigest(),
        'cached_header_bytes': len(selected['cached_header']),
        'cached_header_sha256': hashlib.sha256(selected['cached_header']).hexdigest(),
        'cached_header_verified': True,
        'integrity': 'exact_http_206_range_stable_etag_zlib_size_and_table_md5_passed',
        'texture_header': {'data_bounds_verified': True, 'header_bytes': header, 'height': height,
            'width': width, 'original_name': original, 'struct_bytes': 32}})
    return 'data/' + name.casefold(), record, stored


def discover(output):
    output = Path(output)
    require(not output.exists() and not output.is_symlink(), 'Discovery output already exists')
    value = json.loads((ROOT / 'assets/client-visual-manifest.json').read_text())
    identities = value['provenance']['metadata_archives']
    require(sum(row['source_metadata_bytes'] for row in identities) <= MAX_METADATA_BYTES
        and [r['archive'] for r in identities] == sorted([r['archive'] for r in identities], key=str.casefold),
        'Candidate retained donor metadata inventory is unbounded or unordered')
    chosen, matches = {}, {name: [] for name in TARGETS}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for archive, rows in pool.map(metadata, identities):
            for stem, selected in rows.items():
                chosen[stem] = selected
                matches[stem].append({'archive': archive, 'path': selected['path']})
    require(chosen and sum(row['bytes'] for row in chosen.values()) <= MAX_PAYLOAD_BYTES,
        'No bounded exact original texture candidates were found')
    with ThreadPoolExecutor(max_workers=6) as pool:
        result = list(pool.map(texture, [chosen[n] for n in sorted(chosen)]))
    output.mkdir(parents=True)
    donor.write_donor_zip(output / 'atlas-encounter-candidates.zip', result)
    entries = {name: record for name, record, stored in result}
    report = {'format': 1, 'scope': 'exact_post_world_atlas_npc_texture_candidates',
        'source_console': CONSOLE_PIN, 'target_names': list(TARGETS), 'matches': matches,
        'unresolved_names': sorted(set(TARGETS) - set(chosen)), 'provenance': entries,
        'file_count': len(entries), 'payload_bytes': sum(r['bytes'] for r in entries.values()),
        'archive': donor.pin(output / 'atlas-encounter-candidates.zip'),
        'source_archives_fully_downloaded': False, 'source_archive_sha256_verified': False,
        'metadata_archives': identities, 'runtime_visual_validated': False, 'npc_identity_claimed': False}
    (output / 'atlas-encounter-candidates.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'file_count': len(entries), 'payload_bytes': report['payload_bytes'],
        'unresolved_names': report['unresolved_names'], 'archive': report['archive']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    discover(parser.parse_args().output)
