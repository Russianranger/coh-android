#!/usr/bin/env python3
"""Offline HTTP failure controls using genuine recovered Huge animation bytes."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import tempfile
import zlib
from acquire_received_sources import fetch, CHUNK


class Response:
    def __init__(self, body, size, mode):
        self.body, self.mode, self.reads = io.BytesIO(body), mode, 0
        self.status = 200 if mode == '200' else 206
        self.headers = {'Content-Range': f'bytes 100-{100 + size - 1}/100000', 'ETag': '"fixed"', 'Content-Length': str(size)}
        if mode == 'etag':
            self.headers['ETag'] = '"changed"'
        if mode == 'range':
            self.headers['Content-Range'] = 'bytes 0-1/100000'

    def read(self, size):
        assert size <= CHUNK
        self.reads += 1
        if self.mode == 'allocation':
            raise MemoryError('Injected source read allocation failure')
        return self.body.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.body.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True, type=Path)
    args = parser.parse_args()
    original = args.base.read_bytes()
    assert len(original) == 6171 and hashlib.sha256(original).hexdigest() == '19edb695bb8ca18ea492ac556a68809e7eaebe40fe8d0bf550b7902f78f604e6'
    stored = zlib.compress(original)
    name = 'data/player_library/animations/huge/skel_ready.anim'
    pin = {'path': name[5:], 'bytes': len(original), 'stored_bytes': len(stored), 'offset': 100,
           'sha256': hashlib.sha256(original).hexdigest(), 'stored_sha256': hashlib.sha256(stored).hexdigest(),
           'source_url': 'https://dists.thunderspy.org/piggs/control.pigg', 'source_archive': 'control.pigg',
           'source_archive_bytes': 100000, 'source_etag': '"fixed"', 'compressed': True}
    controls = 0
    with tempfile.TemporaryDirectory(prefix='coh-fixed-member-controls-') as temporary:
        root = Path(temporary)
        for mode in ('valid', '200', 'etag', 'range', 'hash', 'overrun', 'truncated', 'decoded_hash', 'allocation'):
            body = stored + b'x' if mode == 'overrun' else stored[:-1] if mode == 'truncated' else stored
            selected = dict(pin)
            if mode in ('hash', 'decoded_hash'):
                selected['stored_sha256' if mode == 'hash' else 'sha256'] = '0' * 64
            response = Response(body, len(stored), mode)
            output = root / mode
            try:
                result = fetch({name: selected}, output, opener=lambda *_args, **_kwargs: response)
                assert mode == 'valid' and (output / name).read_bytes() == original and result[0]['pinned_etag']
                controls += 1
            except (ValueError, zlib.error, MemoryError):
                assert mode != 'valid' and not (output / name).exists() and not list(output.rglob('*.part'))
                if mode in ('200', 'etag', 'range'):
                    assert response.reads == 0
                controls += 1
        reused = fetch({name: pin}, root / 'valid', opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('Cache triggered network')))
        assert reused[0]['reused'] and reused[0]['compressed_read'] == 0
        controls += 1
        cache = root / 'wrong-cache' / name
        cache.parent.mkdir(parents=True)
        cache.write_bytes(b'x')
        try:
            fetch({name: pin}, root / 'wrong-cache', opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('Wrong cache triggered network')))
            raise AssertionError('Wrong existing source cache overwritten')
        except ValueError:
            assert cache.read_bytes() == b'x'
            controls += 1
    print(json.dumps({'passed': True, 'controls': controls, 'network_requests': 0,
                      'scope': 'Generated compressed transport controls containing genuine pinned Huge animation body'}))


if __name__ == '__main__':
    main()
