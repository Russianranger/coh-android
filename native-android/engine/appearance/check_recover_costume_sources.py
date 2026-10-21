#!/usr/bin/env python3
"""Offline source-provider controls; fixture bodies retain genuine Huge identity."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import os
import struct
import tempfile
import zlib
from recover_costume_sources import (metadata_range, query_plan, selected_composites,
                                    source_indexes, selected_texture_headers)
from costume_texture_inventory import texture_inventory
from pigg_source_index import PiggSourceIndex, ENTRY
from zone_source_index import selected_provenance


class Response:
    def __init__(self, raw, count, mode):
        self.body, self.reads = io.BytesIO(raw), 0
        self.status = 200 if mode == '200' else 206
        self.headers = {'Content-Range': f'bytes 100-{99 + count}/100000',
                        'ETag': '"fixed"', 'Content-Length': str(count)}
        if mode == 'etag':
            self.headers['ETag'] = '"changed"'
        if mode == 'range':
            self.headers['Content-Range'] = 'bytes 0-1/100000'

    def read(self, count):
        assert 0 < count <= 65536
        self.reads += 1
        return self.body.read(count)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.body.close()


def metadata_fixture(raw):
    name = b'player_library/animations/huge/skel_ready.anim\0'
    header = raw[:32]
    pools = (struct.pack('<III', 0x6789, 1, len(name) + 4) + struct.pack('<I', len(name)) + name
             + struct.pack('<III', 0x9abc, 1, len(header) + 4) + struct.pack('<I', len(header)) + header)
    size = 16 + ENTRY.size + len(pools)
    return (struct.pack('<IHHHHI', 0x123, 2, 2, 16, ENTRY.size, 1)
            + ENTRY.pack(0x3456, 0, len(raw), 0, size, 0, 0, hashlib.md5(raw).digest(), 0) + pools)


def controls(root, genuine, inventory_cache=None, texture=None):
    raw = genuine.read_bytes()
    assert len(raw) == 6171 and hashlib.sha256(raw).hexdigest() == '19edb695bb8ca18ea492ac556a68809e7eaebe40fe8d0bf550b7902f78f604e6'
    packed, passed = zlib.compress(raw), 0
    identity = {'archive': 'control.pigg', 'source_archive_bytes': 100000, 'source_etag': '"fixed"'}
    with tempfile.TemporaryDirectory(prefix='coh-costume-provider-') as temporary:
        scratch = Path(temporary)
        for mode in ('valid', '200', 'etag', 'range', 'overrun', 'truncated', 'hash', 'md5', 'header'):
            body = packed + b'x' if mode == 'overrun' else packed[:-1] if mode == 'truncated' else packed
            response = Response(body, len(packed), mode)
            path = scratch / mode
            try:
                result = metadata_range(identity, 100, len(packed), len(raw),
                    '0' * 64 if mode == 'hash' else hashlib.sha256(raw).hexdigest(), path,
                    compressed=True, md5='0' * 32 if mode == 'md5' else hashlib.md5(raw).hexdigest(),
                    cached_header={'bytes': 32, 'sha256': '0' * 64 if mode == 'header' else hashlib.sha256(raw[:32]).hexdigest()},
                    opener=lambda *_args, **_kwargs: response)
                assert mode == 'valid' and path.read_bytes() == raw
                assert not result['compressed_sha256_independently_pinned']
                assert result['compressed_sha256'] == hashlib.sha256(packed).hexdigest()
            except (ValueError, zlib.error):
                assert mode != 'valid' and not path.exists() and not list(scratch.glob('*.part'))
                if mode in ('200', 'etag', 'range'):
                    assert response.reads == 0
            passed += 1
        reused = metadata_range(identity, 100, len(packed), len(raw), hashlib.sha256(raw).hexdigest(), scratch/'valid',
                                opener=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError('Cache read network')))
        assert reused['reused']
        passed += 1
        meta = metadata_fixture(raw)
        path = scratch/'metadata.pigg'
        path.write_bytes(meta)
        pin = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        meta_identity = {**identity, 'source_metadata_bytes': len(meta), 'source_metadata_sha256': hashlib.sha256(meta).hexdigest()}
        fd = os.open(path, os.O_RDONLY)
        try:
            with PiggSourceIndex(fd, meta_identity) as source:
                found = source.rows({'data/player_library/animations/huge/skel_ready.anim': pin})
                row = next(iter(found.values()))
                assert row['offset'] == len(meta) and row['md5_table'] == hashlib.md5(raw).hexdigest()
                assert row['cached_header_sha256'] == hashlib.sha256(raw[:32]).hexdigest()
                assert 'stored_sha256' not in row
                path.write_bytes(meta + b'x')
                try:
                    source.rows({'data/player_library/animations/huge/skel_ready.anim': pin})
                    raise AssertionError('Changed metadata owner accepted')
                except ValueError:
                    passed += 1
            passed += 1
        finally:
            os.close(fd)
        for mode in ('hash', 'writable', 'oversize'):
            fd = os.open(path, os.O_RDWR if mode == 'writable' else os.O_RDONLY)
            try:
                changed = {**meta_identity}
                if mode == 'hash':
                    changed['source_metadata_sha256'] = '0' * 64
                if mode == 'oversize':
                    changed['source_metadata_bytes'] = (4 << 20) + 1
                try:
                    PiggSourceIndex(fd, changed)
                    raise AssertionError('Bad metadata identity accepted')
                except ValueError:
                    passed += 1
            finally:
                os.close(fd)
        path = scratch/'plan.json'
        good = root/'native-android/engine/appearance/received_huge_source_requests.json'
        plan, geometry, names = query_plan(good)
        assert len(plan['parts']) == 13 and len(geometry) == 13
        path.write_text(json.dumps({**plan, 'dbid': 123}))
        try:
            query_plan(path)
            raise AssertionError('Private packet field admitted')
        except ValueError:
            passed += 1
        definitions, sources, leaves = selected_composites(root, scratch, names)
        assert len(definitions) == 3 and len(sources) == 3 and 'swappable' not in leaves and 'none' not in leaves
        assert {'shader_reflect_chrome_01', 'shader_reflect_chrome_02'} <= leaves
        passed += 1
        selected = {'data/player_library/huge_emblem.geo': {'bytes': 1, 'sha256': 'a' * 64}}
        payload = json.dumps({'entries': selected, 'other': {'ignored': True}})
        assert selected_provenance(iter(payload[i:i+7] for i in range(0, len(payload), 7)), list(selected)) == selected
        passed += 1
        def bad_eof():
            yield payload
            raise ValueError('Injected source EOF hash mismatch')
        try:
            selected_provenance(bad_eof(), list(selected))
            raise AssertionError('Unverified source EOF admitted')
        except ValueError:
            passed += 1
        if inventory_cache:
            indexes = source_indexes(root, inventory_cache)
            inventory = texture_inventory(indexes, sorted(names | leaves))
            assert all(not row['present'] for key, row in inventory['lookup'].items() if key.startswith('sh_'))
            assert all(len(inventory['lookup'][key]['paths']) == 1 for key in leaves)
            assert all(not row['ambiguous'] for row in inventory['lookup'].values())
            passed += 1
        if texture:
            texture_raw = texture.read_bytes()
            assert hashlib.sha256(texture_raw).hexdigest() == '0d0658a7b4113d97dce8097db372c60187602fc26d0e8f52049916a421ee4cf1'
            name = 'data/texture_library/players/avatar/male/hips/tights/hips_pants.texture'
            path = scratch / name
            path.parent.mkdir(parents=True)
            path.write_bytes(texture_raw)
            headers = selected_texture_headers(scratch, {name: {'bytes': len(texture_raw)}})
            assert headers[name]['basic_key'] == 'hips_pants'
            passed += 1
            wrong = path.with_name('wrong.texture')
            wrong.write_bytes(texture_raw)
            try:
                selected_texture_headers(scratch, {wrong.relative_to(scratch).as_posix(): {'bytes': len(texture_raw)}})
                raise AssertionError('Cached-key/filename mismatch admitted')
            except ValueError:
                passed += 1
    return passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--inventory-cache', type=Path)
    parser.add_argument('--texture', type=Path)
    args = parser.parse_args()
    print(json.dumps({'passed': True, 'controls': controls(args.source_root, args.base, args.inventory_cache, args.texture),
                      'network_requests': 0, 'metadata_format_fixture_is_original_archive_proof': False}))


if __name__ == '__main__':
    main()
