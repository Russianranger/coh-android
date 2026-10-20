#!/usr/bin/env python3
"""Read only selected original spans from the existing pinned appearance source.

No complete archive, sparse archive or fallback HTTP body is acquired. Each
decoded body is staged and published only after both original source hashes pass.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import tempfile
import urllib.request
import zlib
from imported_archive import safe_path, BODY_LIMIT, CHUNK

COMPRESSED_LIMIT = 4 << 20


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise ValueError('Pinned source redirected; no alternate acquisition attempted')


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(CHUNK), b''):
            digest.update(chunk)
    return digest.hexdigest()


def validate(records):
    if not 0 < len(records) <= 64:
        raise ValueError('Selected source request count differs')
    total = 0
    for name, pin in records.items():
        if (not safe_path(name) or name != 'data/' + pin['path'].casefold()
                or not re.fullmatch(r'https://dists[.]thunderspy[.]org/piggs/[A-Za-z0-9]+[.]pigg', pin['source_url'])
                or pin['source_url'].rsplit('/', 1)[1] != pin['source_archive']
                or not 0 < pin['bytes'] <= BODY_LIMIT or not 0 < pin['stored_bytes'] <= COMPRESSED_LIMIT
                or pin['offset'] < 0 or pin['stored_bytes'] > pin['source_archive_bytes'] - pin['offset']
                or not isinstance(pin['compressed'], bool)
                or not re.fullmatch(r'"[^"\r\n]+"', pin['source_etag'])
                or any(not re.fullmatch('[0-9a-f]{64}', pin[key]) for key in ('sha256', 'stored_sha256'))):
            raise ValueError('Selected original source record differs: ' + name)
        total += pin['stored_bytes']
    if total > COMPRESSED_LIMIT:
        raise ValueError('Selected compressed aggregate exceeds 4 MiB')


def fetch(records, output, opener=None, progress=None):
    validate(records)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if output.is_symlink():
        raise ValueError('Source output is a symlink')
    opener = opener or urllib.request.build_opener(NoRedirect()).open
    results = []
    for name, pin in records.items():
        final = output / name
        if not final.resolve().is_relative_to(output.resolve()):
            raise ValueError('Selected source output escapes its directory')
        if final.exists() or final.is_symlink():
            if final.is_symlink() or not final.is_file() or final.stat().st_size != pin['bytes'] or file_hash(final) != pin['sha256']:
                raise ValueError('Existing source cache differs: ' + name)
            result = {'path': str(final), 'bytes': pin['bytes'], 'sha256': pin['sha256'], 'compressed_read': 0, 'reused': True}
        else:
            start, size = pin['offset'], pin['stored_bytes']
            content_range = f"bytes {start}-{start + size - 1}/{pin['source_archive_bytes']}"
            request = urllib.request.Request(pin['source_url'], headers={
                'Range': f'bytes={start}-{start + size - 1}', 'If-Range': pin['source_etag'],
                'Accept-Encoding': 'identity', 'User-Agent': 'CoH-selected-original-source/1'})
            stage = None
            try:
                with opener(request, timeout=30) as response:
                    if (response.status != 206 or response.headers.get('Content-Range') != content_range
                            or response.headers.get('ETag') != pin['source_etag']
                            or response.headers.get('Content-Length') != str(size)
                            or response.headers.get('Content-Encoding', 'identity') != 'identity'):
                        raise ValueError('Pinned range headers differ; response body not read')
                    final.parent.mkdir(parents=True, exist_ok=True)
                    fd, temporary = tempfile.mkstemp(prefix=final.name + '.', suffix='.part', dir=final.parent)
                    stage = Path(temporary)
                    compressed, decoded = hashlib.sha256(), hashlib.sha256()
                    decoder = zlib.decompressobj() if pin['compressed'] else None
                    received, written = 0, 0
                    with os.fdopen(fd, 'wb') as sink:
                        def emit(raw):
                            nonlocal written
                            if len(raw) > pin['bytes'] - written:
                                raise ValueError('Original decoded source exceeds pinned size')
                            sink.write(raw)
                            decoded.update(raw)
                            written += len(raw)

                        while received < size:
                            wanted = min(CHUNK, size - received)
                            chunk = response.read(wanted)
                            if not chunk or len(chunk) > wanted:
                                raise ValueError('Original compressed source truncated or overrun')
                            received += len(chunk)
                            compressed.update(chunk)
                            if decoder is None:
                                emit(chunk)
                            else:
                                while chunk:
                                    before = len(chunk)
                                    raw = decoder.decompress(chunk, CHUNK)
                                    emit(raw)
                                    chunk = decoder.unconsumed_tail
                                    if decoder.eof:
                                        if decoder.unused_data or chunk or received != size:
                                            raise ValueError('Original compressed source has trailing data')
                                        break
                                    if not raw and len(chunk) == before:
                                        raise ValueError('Original source inflate made no progress')
                        if response.read(1):
                            raise ValueError('Original compressed response exceeds selected range')
                        if decoder is not None:
                            while not decoder.eof:
                                raw = decoder.decompress(b'', CHUNK)
                                if not raw and not decoder.eof:
                                    raise ValueError('Original compressed source ended early')
                                emit(raw)
                    if compressed.hexdigest() != pin['stored_sha256'] or written != pin['bytes'] or decoded.hexdigest() != pin['sha256']:
                        raise ValueError('Pinned compressed/decoded source SHA differs')
                    os.rename(stage, final)
                    stage = None
                    result = {'path': str(final), 'bytes': written, 'sha256': decoded.hexdigest(),
                              'compressed_read': received, 'source_range': content_range, 'pinned_etag': True}
            finally:
                if stage is not None:
                    stage.unlink(missing_ok=True)
        results.append(result)
        if progress:
            progress(result)
    return results


def main():
    from source_manifest_records import selected_records
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--path', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    records = selected_records(args.manifest, [path.casefold() for path in args.path])
    result = fetch(records, args.output, progress=lambda row: print(json.dumps(row), flush=True))
    print(json.dumps({'passed': True, 'files': len(result), 'compressed_read': sum(row['compressed_read'] for row in result),
                      'whole_archive_download': False}))


if __name__ == '__main__':
    main()
