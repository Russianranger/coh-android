#!/usr/bin/env python3
"""Inspect PIGG v2 archives with Python only; never execute game code.

Format references: pinned UtilitiesLib piglib_internal.h, datapool.c,
serialize.c and structInternals.c. Checksums prove internal consistency,
not trusted provenance or compatibility with a particular client/server.
Optional staging copies only candidate binary assets into a NEW directory.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
HEADER = struct.Struct('<IHHHHI')
ENTRY = struct.Struct('<IiIIIIi16sI')
ASSET_SUFFIXES = {'.geo', '.texture', '.ogg', '.wav', '.anim', '.ttf', '.ttc', '.otf'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def region(data, offset, size):
    require(0 <= offset <= len(data) and 0 <= size <= len(data) - offset,
            'Truncated or out-of-bounds structure')
    return data[offset:offset + size]


def pool(data, offset, expected_flag):
    flag, count, size = struct.unpack('<III', region(data, offset, 12))
    require(flag == expected_flag and count <= size // 4, 'Invalid data pool')
    block = region(data, offset + 12, size)
    items, pos = [], 0
    for _ in range(count):
        length, = struct.unpack('<I', region(block, pos, 4))
        pos += 4
        items.append(region(block, pos, length))
        pos += length
    require(pos == size, 'Data pool has trailing bytes')
    return items, offset + 12 + size


def safe_name(raw):
    require(raw.endswith(b'\0') and b'\0' not in raw[:-1], 'Invalid filename string')
    name = raw[:-1].decode('utf-8').replace('\\', '/')
    parts = name.split('/')
    require(name and not name.startswith('/') and ':' not in name and
            all(p not in ('', '.', '..') for p in parts) and
            all(ord(c) >= 32 for c in name), 'Unsafe archive path')
    return name


def pascal(data, pos):
    length, = struct.unpack('<H', region(data, pos, 2))
    value = region(data, pos + 2, length).decode('utf-8')
    size = (length + 2 + 3) & ~3
    region(data, pos, size)
    return value, pos + size


def serialized_header(data, baseline):
    if not data.startswith(b'CrypticS'):
        return None
    crc, = struct.unpack('<I', region(data, 8, 4))
    signature, pos = pascal(data, 12)
    result = {'signature': signature, 'schema_crc': f'{crc:08x}'}
    if signature != 'Parse6':
        return result
    section, pos = pascal(data, pos)
    if section != 'Files1':
        result['dependency_section'] = section
        return result
    size, = struct.unpack('<I', region(data, pos, 4))
    block = region(data, pos + 4, size)
    count, = struct.unpack('<I', region(block, 0, 4))
    require(count <= len(block) // 8, 'Invalid dependency count')
    names, cursor = [], 4
    for _ in range(count):
        name, cursor = pascal(block, cursor)
        region(block, cursor, 4)  # Source timestamp, not a content hash.
        cursor += 4
        names.append(name.replace('\\', '/').lower())
    require(cursor == len(block), 'Dependency section length mismatch')
    result['dependency_count'] = count
    if baseline is not None:
        missing = sorted({name for name in names if 'data/' + name not in baseline})
        result['dependency_paths_absent_from_baseline'] = missing
        result['dependency_paths_present_in_baseline'] = count - sum(
            'data/' + name not in baseline for name in names)
    return result


def category(name):
    lower = name.lower()
    if lower.startswith(('bin/', 'geobin/', 'server/bin/')) or lower.endswith(('.bin', '.bounds')):
        return 'generated_cache'
    if PurePosixPath(lower).suffix in ASSET_SUFFIXES:
        return 'candidate_binary_asset'
    return 'other_content'


def geometry_header(data):
    """Check the header envelope accepted by Common/seq/anim.c:geoLoadStubs.

    This does not decode meshes, collision grids, models or texture references.
    Unsupported versions are reported separately from archive integrity.
    """
    biased_size, unpacked_size = struct.unpack('<II', region(data, 0, 8))
    if unpacked_size == 0:
        version, unpacked_size = struct.unpack('<II', region(data, 8, 8))
        start, packed_size, data_offset = 16, biased_size - 12, biased_size + 4
        supported = 2 <= version <= 8 and version != 6
    else:
        version = 0  # Legacy unversioned layout in the source reader.
        start, packed_size, data_offset = 8, biased_size - 4, biased_size + 8
        supported = True
    result = {'version': version, 'baseline_loader_accepts_version': supported,
              'runtime_compatibility': 'unverified'}
    if not supported:
        return result
    require(16 <= unpacked_size <= 128 * 1024**2 and packed_size > 0,
            'Invalid/oversized geometry header')
    packed = region(data, start, packed_size)
    decoder = zlib.decompressobj()
    header = decoder.decompress(packed, unpacked_size + 1)
    require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail and
            len(header) == unpacked_size, 'Geometry header decompression mismatch')
    data_size, = struct.unpack('<I', region(header, 0, 4))
    region(data, data_offset, data_size)
    result.update({'header_uncompressed_bytes': unpacked_size,
                   'header_decompression_verified': True, 'data_block_bounds_verified': True})
    return result


def inspect(path, baseline, max_entry, budget, stage, staged):
    require(not path.is_symlink() and path.is_file(), 'Input must be a regular file')
    require(path.stat().st_size <= 2 * 1024**3, 'Archive exceeds 2 GiB inspection limit')
    data = path.read_bytes()
    magic, creator, reader, head_size, entry_size, count = HEADER.unpack(region(data, 0, HEADER.size))
    require(magic == 0x123 and creator == 2 and reader <= 2 and
            head_size == 16 and entry_size == 48, 'Unsupported PIGG header/layout')
    region(data, head_size, count * entry_size)
    names, pos = pool(data, head_size + count * entry_size, 0x6789)
    cached_headers, metadata_end = pool(data, pos, 0x9ABC)
    require(len(names) == count, 'Filename count does not match entries')
    entries, seen, ranges = [], set(), []
    for i in range(count):
        flag, name_id, size, timestamp, offset, reserved, header_id, md5, packed = ENTRY.unpack_from(
            data, head_size + i * entry_size)
        require(flag == 0x3456 and reserved == 0 and 0 <= name_id < count,
                'Invalid file header')
        require(header_id == -1 or 0 <= header_id < len(cached_headers), 'Invalid cached header ID')
        name = safe_name(names[name_id])
        key = name.lower()
        require(key not in seen, 'Duplicate/case-colliding path: ' + name)
        seen.add(key)
        require(size <= max_entry and size <= budget[0], 'Uncompressed inspection limit exceeded')
        budget[0] -= size
        require(offset >= metadata_end, 'Payload overlaps archive metadata')
        payload = region(data, offset, packed or size)
        if payload:
            ranges.append((offset, offset + len(payload)))
        if packed:
            decoder = zlib.decompressobj()
            body = decoder.decompress(payload, size + 1)
            require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
                    'Invalid/truncated/oversized zlib stream: ' + name)
        else:
            body = payload
        require(len(body) == size, 'Uncompressed size mismatch: ' + name)
        observed_md5 = hashlib.md5(body).digest() if size else bytes(16)
        require(observed_md5 == md5, 'PIGG MD5 mismatch: ' + name)
        if header_id != -1:
            require(body.startswith(cached_headers[header_id]), 'Cached header differs from payload: ' + name)
        kind = category(name)
        sha = hashlib.sha256(body).hexdigest()
        entry = {'path': name, 'size': size, 'stored_size': packed or size,
                 'md5': md5.hex(), 'sha256': sha, 'category': kind}
        header = serialized_header(body, baseline)
        if header:
            entry['serialized_header'] = header
        if PurePosixPath(key).suffix == '.geo':
            entry['geometry_header'] = geometry_header(body)
        if baseline is not None:
            original = baseline.get('data/' + key)
            entry['baseline_comparison'] = ('identical' if original == sha else 'different') if original else 'absent'
        if stage and kind == 'candidate_binary_asset':
            require(key not in staged, 'Candidate asset occurs in multiple archives: ' + name)
            staged.add(key)
            target = stage.joinpath(*PurePosixPath(key).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(body)
        entries.append(entry)
    ranges.sort()
    require(all(left[1] <= right[0] for left, right in zip(ranges, ranges[1:])),
            'Archive payloads overlap')
    return {'archive': path.name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'creator_version': creator, 'required_reader_version': reader,
            'entry_count': count, 'uncompressed_bytes': sum(x['size'] for x in entries),
            'integrity': 'all_entry_sizes_zlib_and_md5_passed',
            'categories': dict(Counter(x['category'] for x in entries)),
            'extensions': dict(Counter(PurePosixPath(x['path']).suffix.lower() for x in entries)),
            'baseline_comparisons': dict(Counter(x.get('baseline_comparison', 'not_compared') for x in entries)),
            'serialized_signatures': dict(Counter(x['serialized_header']['signature'] for x in entries if 'serialized_header' in x)),
            'entries': entries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archives', type=Path, nargs='+')
    parser.add_argument('--baseline-manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True, help='New JSON report')
    parser.add_argument('--stage-assets', type=Path, help='New candidate asset directory; NOT a validated runtime')
    parser.add_argument('--max-entry-mib', type=int, default=512)
    parser.add_argument('--max-total-mib', type=int, default=8192)
    args = parser.parse_args()
    require(args.max_entry_mib > 0 and args.max_total_mib > 0, 'Limits must be positive')
    baseline = None
    if args.baseline_manifest:
        doc = json.loads(args.baseline_manifest.read_text())
        baseline = {x['path'].lower(): x['sha256'] for x in doc['entries']}
    for output in (args.output, args.stage_assets):
        if output:
            require(not output.exists() and not output.is_symlink(), 'Output already exists')
            resolved = output.resolve()
            require(resolved != ROOT / 'upstream' and ROOT / 'upstream' not in resolved.parents,
                    'Outputs must stay outside immutable upstream snapshots')
    if args.stage_assets:
        args.stage_assets.mkdir(parents=True)
        (args.stage_assets / '.inspection-incomplete').write_text('Discard staging if inspection fails.\n')
    budget, staged, reports = [args.max_total_mib * 1024**2], set(), []
    for path in args.archives:
        report = inspect(path, baseline, args.max_entry_mib * 1024**2, budget, args.stage_assets, staged)
        reports.append(report)
        print(f'{path.name}: {report["entry_count"]} entries verified', flush=True)
    result = {'status': 'archive_integrity_verified_runtime_compatibility_unverified',
              'archive_count': len(reports), 'entry_count': sum(r['entry_count'] for r in reports),
              'candidate_assets_staged': len(staged), 'archives': reports}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    if args.stage_assets:
        (args.stage_assets / '.inspection-incomplete').unlink()
    print(f'Report: {args.output}; runtime compatibility remains unverified.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, struct.error, zlib.error) as error:
        print('Inspection failed: ' + str(error), file=sys.stderr)
        sys.exit(1)
