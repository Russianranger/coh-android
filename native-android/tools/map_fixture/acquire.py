#!/usr/bin/env python3
"""Acquire eight pinned map inputs using the accepted bounded ZIP range reader.

These are exact source members from the published asset packs. No complete PIGG
or ZIP archive is downloaded, and no full archive hash verification is claimed.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import struct
import tempfile
import zipfile
import zlib

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
EXPECTED = {
    'misc.geo', 'trainstation.geo', 'bench.texture', 'sign.texture',
    'white.texture', 'grey.texture', 'mono_station_infloor.texture',
    'mono_station_infloor_sml.texture',
}
RANGE_BUDGET = 8 << 20


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pin_records():
    records, sources = [], []
    for relative in ('world_fixture/pins.json', 'walkable_fixture/pins.json'):
        path = TOOLS / relative
        raw = path.read_bytes()
        pins = json.loads(raw)
        sources.append({'path': relative, 'bytes': len(raw), 'sha256': digest(raw)})
        for item in pins['records']:
            record = dict(item)
            for field in ('outer_asset_url', 'outer_expected_bytes', 'inner_member',
                          'inner_expected_bytes'):
                record.setdefault(field, pins[field])
            require(re.fullmatch(r'[a-z0-9_]+\.(geo|texture)', record['file_name']),
                    'unsafe output file name')
            require(0 < record['size'] <= 2 << 20, 'source member exceeds bound')
            require(0 < record['compressed'] <= 2 << 20, 'stored member exceeds bound')
            require(record['method'] in (0, 8), 'unsupported ZIP method')
            require(re.fullmatch('[0-9a-f]{64}', record['sha256']), 'invalid SHA256 pin')
            require(re.fullmatch('[0-9a-f]{8}', record['crc32']), 'invalid CRC32 pin')
            require(0 <= record['offset'] < record['inner_expected_bytes'],
                    'member offset outside archive')
            records.append(record)
    names = [record['file_name'] for record in records]
    require(len(names) == len(EXPECTED) and set(names) == EXPECTED,
            'map source allowlist differs or contains duplicates')
    return records, sources


def verify_raw(raw, pin):
    require(len(raw) == pin['size'], 'source member size differs')
    require(f'{zlib.crc32(raw):08x}' == pin['crc32'], 'source member CRC32 differs')
    require(digest(raw) == pin['sha256'], 'source member SHA256 differs')


def exact(stream, size):
    raw = stream.read(size)
    require(len(raw) == size, 'truncated ZIP member envelope')
    return raw


def extract_member(stream, pin):
    stream.seek(pin['offset'])
    header = exact(stream, 30)
    require(header[:4] == b'PK\x03\x04', 'ZIP local signature differs')
    flags, method = struct.unpack_from('<HH', header, 6)
    require(not flags & 1 and method == pin['method'], 'ZIP encryption/method differs')
    name_length, extra_length = struct.unpack_from('<HH', header, 26)
    require(name_length <= 4096 and extra_length <= 65535, 'ZIP header exceeds bound')
    name = exact(stream, name_length).decode('utf8')
    require(name == pin['name'], 'ZIP source identity differs')
    position = pin['offset'] + 30 + name_length + extra_length
    require(position + pin['compressed'] <= stream.size, 'stored member outside archive')
    stream.seek(position)
    stored = exact(stream, pin['compressed'])
    if method == 8:
        decoder = zlib.decompressobj(-15)
        raw = decoder.decompress(stored, pin['size'] + 1)
        require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
                'deflate envelope differs')
    else:
        raw = stored
    verify_raw(raw, pin)
    return raw


def publish(path, raw):
    require(not path.is_symlink(), 'output member must not be a symlink')
    descriptor, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(raw)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def acquire(output, use_verified_local=False):
    records, sources = pin_records()
    spec = importlib.util.spec_from_file_location(
        'map_accepted_material_ranges', TOOLS / 'material_fixture/acquire.py')
    ranges = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ranges)
    output.mkdir(parents=True, exist_ok=True)
    readers, receipts, reused, reacquired = {}, [], [], []
    # Both source files and the success receipt are replaced atomically only
    # after verification. A failed attempt exits nonzero and preserves earlier
    # completed files; callers must require successful process completion.
    receipt_path = output / 'corpus.json'
    require(not receipt_path.is_symlink(), 'receipt must not be a symlink')
    for pin in records:
        target = output / pin['file_name']
        require(not target.is_symlink(), 'source output must not be a symlink')
        raw = None
        if use_verified_local and target.is_file():
            # Refuse oversized local reads before hashing. Invalid files are
            # retained until a verified replacement is ready.
            if target.stat().st_size == pin['size']:
                candidate = target.read_bytes()
                try:
                    verify_raw(candidate, pin)
                except ValueError:
                    pass
                else:
                    raw = candidate
                    reused.append(pin['file_name'])
        if raw is None:
            key = pin['outer_asset_url'], pin['inner_member']
            if key not in readers:
                reader = ranges.HTTPRange(key[0], pin['outer_expected_bytes'], RANGE_BUDGET)
                with zipfile.ZipFile(reader) as archive:
                    info = archive.getinfo(key[1])
                    require(not info.flag_bits & 1 and info.compress_type == zipfile.ZIP_STORED,
                            'inner ZIP is encrypted or compressed')
                    require(info.file_size == pin['inner_expected_bytes'],
                            'inner ZIP exact size differs')
                    stream = ranges.subzip(reader, info)
                readers[key] = reader, stream
            reader, stream = readers[key]
            raw = extract_member(stream, pin)
            publish(target, raw)
            reacquired.append(pin['file_name'])
        receipts.append({'file_name': pin['file_name'], 'name': pin['name'],
                         'bytes': len(raw), 'sha256': digest(raw), 'crc32': pin['crc32']})
        print(f'{pin["file_name"]}: {len(raw)} bytes SHA256 verified', flush=True)
    receipt = {
        'schema': 'coh-map-source-acquisition-v1', 'passed': True,
        'acquisition_passed': True, 'pin_sources': sources, 'records': receipts,
        'locally_reused_after_size_crc_sha_verification': reused,
        'acquired_members': reacquired,
        'range_bytes_downloaded': sum(reader.total for reader, _ in readers.values()),
        'range_count': sum(len(reader.requests) for reader, _ in readers.values()),
        'range_budget_bytes_per_archive': RANGE_BUDGET,
        'exact_http_range_enforced': True, 'etag_stable': True,
        'zip_member_crc32_verified': True, 'all_fixture_sha256_verified': True,
        'outer_full_hash_locally_verified': False,
        'inner_full_hash_locally_verified': False,
        'ranges_by_archive': [{'outer_asset_url': key[0], 'inner_member': key[1],
                               'ranges': reader.requests}
                              for key, (reader, _) in readers.items()],
    }
    publish(receipt_path, (json.dumps(receipt, indent=2) + '\n').encode())
    return receipt


def self_test():
    # Exercise acquisition admission only; do not repeat any accepted decoder,
    # collision, renderer, or source qualification suite.
    raw = b'bounded original source member\x00'
    compressor = zlib.compressobj(wbits=-15)
    stored = compressor.compress(raw) + compressor.flush()
    name = b'data/texture_library/example.texture'
    pin = {'size': len(raw), 'sha256': digest(raw), 'crc32': f'{zlib.crc32(raw):08x}',
           'method': 8, 'offset': 0, 'compressed': len(stored), 'name': name.decode()}
    header = struct.pack('<4s5H3I2H', b'PK\x03\x04', 20, 0, 8, 0, 0,
                         zlib.crc32(raw), len(stored), len(raw), len(name), 0)

    class Member(io.BytesIO):
        def __init__(self, data):
            super().__init__(data)
            self.size = len(data)

    envelope = header + name + stored
    require(extract_member(Member(envelope), pin) == raw, 'valid member rejected')
    count = 1

    def reject(label, data=envelope, change=None):
        nonlocal count
        other = dict(pin)
        other.update(change or {})
        try:
            extract_member(Member(data), other)
        except (ValueError, zlib.error, UnicodeDecodeError):
            count += 1
        else:
            raise AssertionError('invalid member accepted: ' + label)

    reject('signature', b'NOPE' + envelope[4:])
    reject('encryption', envelope[:6] + b'\x01\x00' + envelope[8:])
    reject('method', change={'method': 0})
    reject('identity', change={'name': 'data/another.texture'})
    reject('truncated header', envelope[:20])
    reject('truncated member', envelope[:-1])
    reject('size', change={'size': len(raw) - 1})
    reject('CRC32', change={'crc32': '00000000'})
    reject('SHA256', change={'sha256': '0' * 64})
    reject('trailing deflate data', envelope + b'x', {'compressed': len(stored) + 1})
    pin_records()
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        target = root / 'source.texture'
        publish(target, raw)
        require(target.read_bytes() == raw, 'atomic output differs')
        count += 1
        target.unlink()
        target.symlink_to(root / 'unrelated')
        try:
            publish(target, raw)
        except ValueError:
            count += 1
        else:
            raise AssertionError('symlink output accepted')
    return {'schema': 'coh-map-source-acquisition-admission-v1', 'passed': True,
            'checks': count, 'network_accessed': False, 'raw_allowlist': sorted(EXPECTED)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--use-verified-local', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), indent=2))
        return
    if args.output is None:
        parser.error('--output is required unless --self-test is selected')
    result = acquire(args.output, args.use_verified_local)
    print(json.dumps({key: result[key] for key in
                      ('passed', 'range_bytes_downloaded', 'range_count', 'acquired_members')}))


if __name__ == '__main__':
    main()
