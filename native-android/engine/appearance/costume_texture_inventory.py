"""Complete requested basename lookup across retained inputs and zone additions.

The source set matches audit_kings_row_foundation.retained_inventory plus the
accepted all-zone missing-only supplement. Only requested names are retained.
Filename presence is separate from cached-header naming and duplicate winners.
"""
import base64
import codecs
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
from source_manifest_records import _JSONStream, _unique
from zone_source_index import MANIFEST_PIN as ZONE_PIN, pinned_chunks

# Exact accepted source files at d6327cd; encoded sources retain their own
# independently pinned decoded identities from the existing preparation tools.
SOURCES = [
    ('reference-inputs-manifest.json', 3832869, 'cf96742b1b65306356df69d065fcfb5bda0986ec8700d47ae1422452a1c0db7f', 'array'),
    ('character-avatar-defaults-manifest.json', 28554, '2a96ff8fb24b686502d62e1e1ed25453681d4c15389c59b1f35ce3fbf1a5feb7', 'map'),
    ('atlas-world-supplement-manifest.json', 4258210, '204a7f0da20cdbbb4ea8b8e2d9e9b5ebccfaa10d5213fff03bbb85cc7f9e3c86', 'map'),
    ('client-ui-repair-manifest.json', 6195900, '8b38cf47dd86ca61c2037736112c2c77f49b35bbf434c136eec5870b2d2e7d24', 'gzip'),
    ('client-ui-sweep-manifest.json', 665432, 'f91cde7bf5d1c7dbef2504299d96349b13cd6e4504abdd64b7b6292c5a679b0f', 'gzip'),
    ('zones-world-supplement-manifest.json', ZONE_PIN['bytes'], ZONE_PIN['sha256'], 'map'),
]


def wrapped_chunks(path, pin):
    # Verify the small encoded source first. Decode/parse the large catalog only
    # as 64 KiB pieces; no complete decoded JSON string or dictionary is built.
    for _ in pinned_chunks(path, pin):
        pass
    wrapper = json.loads(Path(path).read_bytes(), object_pairs_hook=_unique)
    if wrapper.get('format') != 1 or wrapper.get('encoding') != 'gzip+base64':
        raise ValueError('Encoded accepted index differs')
    packed = base64.b64decode(wrapper['data'], validate=True)
    if len(packed) > 8 << 20 or len(packed) != wrapper['gzip']['bytes'] or hashlib.sha256(packed).hexdigest() != wrapper['gzip']['sha256']:
        raise ValueError('Encoded accepted index gzip differs')
    expected = wrapper['decoded']
    del wrapper
    digest, total = hashlib.sha256(), 0
    utf8 = codecs.getincrementaldecoder('utf-8')('strict')
    with gzip.GzipFile(fileobj=io.BytesIO(packed)) as source:
        while True:
            raw = source.read(65536)
            if not raw:
                break
            total += len(raw)
            if total > expected['bytes']:
                raise ValueError('Decoded accepted index exceeds source pin')
            digest.update(raw)
            yield utf8.decode(raw)
    end = utf8.decode(b'', final=True)
    if end:
        yield end
    if total != expected['bytes'] or digest.hexdigest() != expected['sha256']:
        raise ValueError('Decoded accepted index SHA differs')


def texture_inventory(directory, requested_names):
    if (not 0 < len(requested_names) <= 64 or any(not isinstance(name, str) or not name
            or '/' in name or '\\' in name or len(name) > 255 for name in requested_names)):
        raise ValueError('Requested texture basename set differs')
    wanted = {PurePosixPath(name).stem.casefold() for name in requested_names}
    matches, evidence = {}, []
    for filename, size, digest, kind in SOURCES:
        pin = {'bytes': size, 'sha256': digest}
        chunks = wrapped_chunks(Path(directory) / filename, pin) if kind == 'gzip' else pinned_chunks(Path(directory) / filename, pin)
        source = _JSONStream(chunks)
        seen, count = False, 0

        def admit(path, value, original=None):
            if path in matches and matches[path]['pin'] != value:
                raise ValueError('Accepted texture inventories conflict')
            if path not in matches and len(matches) >= 64:
                raise ValueError('Requested texture matches exceed bounded retained rows')
            matches[path] = {'pin': value, 'index': filename, 'original_input': original}

        def file(name):
            nonlocal count
            count += 1
            if (name.startswith('data/texture_library/') and name.endswith('.texture')
                    and PurePosixPath(name).stem.casefold() in wanted):
                admit(name, source.record())
            else:
                source.value()

        def array():
            nonlocal count
            source.expect('[')
            source.whitespace()
            if source.peek() == ']':
                source.take()
                return
            while True:
                row = source.record()
                count += 1
                name = 'data/' + row['path'].casefold().replace('\\', '/')
                if (name.startswith('data/texture_library/') and name.endswith('.texture')
                        and PurePosixPath(name).stem.casefold() in wanted):
                    admit(name, {'bytes': row['size'], 'sha256': row['sha256']}, row)
                source.whitespace()
                separator = source.take()
                if separator == ']':
                    return
                if separator != ',':
                    raise ValueError('Invalid original file inventory')

        def root(key):
            nonlocal seen
            if key == 'files':
                if seen:
                    raise ValueError('Duplicate accepted file inventory')
                seen = True
                array() if kind == 'array' else source.object(file)
            else:
                source.value()

        source.object(root)
        source.whitespace()
        if source.peek() is not None or not seen:
            raise ValueError('Accepted source inventory structure differs')
        evidence.append({'file': filename, 'bytes': size, 'sha256': digest, 'file_rows': count})
    result = {}
    for key in sorted(wanted):
        paths = sorted(path for path in matches if PurePosixPath(path).stem.casefold() == key)
        result[key] = {'paths': paths, 'present': bool(paths), 'ambiguous': len(paths) > 1}
    return {'lookup': result, 'files': matches, 'source_indexes': evidence,
            'scope': 'Complete requested filename basenames in accepted retained imports plus all-zone supplement from 57 frozen donors; not unlisted archives or original cached-header enumeration',
            'duplicate_winner_selected': False}
