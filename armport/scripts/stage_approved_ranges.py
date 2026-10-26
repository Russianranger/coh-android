#!/usr/bin/env python3
"""Stage only exact files found for the user's approved M3 range requests.

Profiles: the 15 dispatch requests (m3-approved-range-assets.json) and the
three base cape geometries logged after map load in Atlas 40373337135
(m3-approved-cape-ranges.json; user authority relayed in PR #6 6419236533).

The committed manifest freezes bounded original PIGG ranges, decoded SHA-256,
stored SHA-256, table MD5 and cached-header SHA-256. Absent exact names stay
unresolved. This never substitutes a similar name or fetches an entire PIGG.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
import urllib.request
import zlib

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'armport/evidence/m3-approved-range-assets.json'
GEOMETRY = {'player_library/' + name + '.geo' for name in
            ('huge_belt', 'huge_boot', 'huge_hair', 'huge_head', 'huge_pants', 'huge_shirt', 'v_huge_spadr')}
TEXTURES = {'chest_stripe_1', 'face_skin_head_09', 'hips_miniskirt_1', 'hips_skin_tights',
            'x_enforcer_glove_01_mask', 'x_gear_pads', 'x_imperialdefense_belt_01',
            'tickertape_steel_canyon_south'}


CAPE_GEOMETRY = {'player_library/' + name + '.geo' for name in ('male_cape', 'fem_cape', 'huge_cape')}
CAPE_MANIFEST = ROOT / 'armport/evidence/m3-approved-cape-ranges.json'
PROFILES = {
    MANIFEST.name: dict(scope='user_approved_m3_dispatch_missing_files', geometry=GEOMETRY, textures=TEXTURES),
    CAPE_MANIFEST.name: dict(scope='user_approved_m3_after_load_cape_geometry', geometry=CAPE_GEOMETRY,
                             textures=frozenset()),
}


def require(value, message):
    if not value:
        raise ValueError(message)


def read_manifest(path=MANIFEST):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size < 256 * 1024,
            'Missing/oversized approved range manifest')
    doc = json.loads(path.read_text())
    profiles = [p for p in PROFILES.values() if p['scope'] == doc.get('scope')]
    require(len(profiles) == 1, 'Approved request scope differs')
    profile = profiles[0]
    GEOMETRY, TEXTURES = profile['geometry'], profile['textures']
    count = len(GEOMETRY | TEXTURES)
    require(doc['format'] == 1 and doc['scope'] == profile['scope']
            and set(doc['requests']) == GEOMETRY | TEXTURES and len(doc['requests']) == count
            and set(doc['files']) == set(doc['provenance']) and 0 < len(doc['files']) <= count,
            'Approved request scope differs')
    covered = set()
    for name, record in doc['provenance'].items():
        relative = name.removeprefix('data/')
        path = PurePosixPath(relative)
        require(name == 'data/' + path.as_posix() and name == name.casefold() and name.isascii()
                and '..' not in path.parts and '\\' not in name and ':' not in name,
                'Unsafe approved file path')
        request = relative if relative in GEOMETRY else path.stem
        require(relative in GEOMETRY or (relative.startswith('texture_library/')
                and path.suffix == '.texture' and request in TEXTURES), 'Unapproved payload name')
        require(request not in covered, 'Ambiguous approved texture request')
        covered.add(request)
        require(doc['matches'][request] == [dict(archive=record['source_archive'], path=record['path'])]
                and record['path'].casefold() == relative, 'Exact source selection differs')
        require(re.fullmatch(r'[A-Za-z0-9]+[.]pigg', record['source_archive'])
                and record['source_url'] == 'https://dists.thunderspy.org/piggs/' + record['source_archive']
                and 0 < record['bytes'] <= 32 * 1024**2
                and 0 < record['stored_bytes'] <= 16 * 1024**2
                and 0 <= record['offset'] < record['source_archive_bytes'] <= 2 * 1024**3
                and record['offset'] + record['stored_bytes'] <= record['source_archive_bytes']
                and type(record['compressed']) is bool, 'Unbounded source range')
        expected = f"bytes {record['offset']}-{record['offset'] + record['stored_bytes'] - 1}/{record['source_archive_bytes']}"
        require(record['source_content_range'] == expected
                and doc['files'][name] == {key: record[key] for key in ('bytes', 'sha256')},
                'Source range or decoded file pin differs')
        for key in ('sha256', 'stored_sha256', 'cached_header_sha256', 'source_metadata_sha256'):
            require(re.fullmatch('[0-9a-f]{64}', record[key]), 'Invalid digest')
        require(re.fullmatch('[0-9a-f]{32}', record['md5_table']) and
                0 < record['cached_header_bytes'] <= record['bytes'], 'Invalid cached header or MD5')
    require(set(doc['unresolved']) == (GEOMETRY | TEXTURES) - covered
            and set(doc['matches']) == GEOMETRY | TEXTURES
            and all(not doc['matches'][name] for name in doc['unresolved'])
            and len(doc['files']) == doc['file_count']
            and sum(row['bytes'] for row in doc['files'].values()) == doc['payload_bytes'] <= 64 * 1024**2,
            'Approved selection accounting differs')
    return doc


def decode(stored, record):
    require(len(stored) == record['stored_bytes']
            and hashlib.sha256(stored).hexdigest() == record['stored_sha256'], 'Stored range pin differs')
    raw = stored
    if record['compressed']:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(stored, record['bytes'] + 1)
        require(decoder.eof and not decoder.unconsumed_tail and not decoder.unused_data,
                'Invalid or oversized selected zlib stream')
    require(len(raw) == record['bytes'] and hashlib.sha256(raw).hexdigest() == record['sha256']
            and hashlib.md5(raw).hexdigest() == record['md5_table']
            and hashlib.sha256(raw[:record['cached_header_bytes']]).hexdigest() == record['cached_header_sha256'],
            'Decoded payload or cached header differs')
    return raw


def download(record, receipts=None):
    start, size = record['offset'], record['stored_bytes']
    request = urllib.request.Request(record['source_url'], headers={
        'Range': f'bytes={start}-{start + size - 1}', 'If-Match': record['source_etag'],
        'User-Agent': 'coh-armport-approved-ranges/1'})
    with urllib.request.urlopen(request, timeout=45) as response:
        require(response.status == 206 and response.geturl() == record['source_url']
                and response.headers.get('ETag') == record['source_etag']
                and response.headers.get('Last-Modified') == record['source_last_modified']
                and response.headers.get('Content-Range') == record['source_content_range']
                and int(response.headers.get('Content-Length', -1)) == size,
                'Donor changed or refused exact pinned partial transfer')
        stored = response.read(size + 1)
        if receipts is not None:
            receipts.append(dict(source_archive=record['source_archive'], path=record['path'],
                status=response.status, content_range=response.headers.get('Content-Range'),
                bytes_received=len(stored)))
        return stored


def verify(output, document):
    require(output.is_dir() and not output.is_symlink(), 'Missing or linked approved layer')
    files = {}
    for path in output.rglob('*'):
        require(not path.is_symlink(), 'Linked approved layer member')
        if path.is_file():
            name = 'data/' + path.relative_to(output).as_posix()
            require(name in document['files'], 'Unexpected approved layer member')
            expected = document['files'][name]
            require(path.stat().st_size == expected['bytes'], 'Approved layer file size differs')
            files[name] = dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        else:
            require(path.is_dir(), 'Non-regular approved layer member')
    require(files == document['files'], 'Approved layer inventory or digest differs')


def stage(output, document, downloader=download):
    require(not output.exists() and not output.is_symlink(), 'Approved output already exists')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.approved-ranges-', dir=output.parent) as tmp:
        root = Path(tmp) / 'data'
        root.mkdir()
        for name, record in document['provenance'].items():
            raw = decode(downloader(record), record)
            target = root / name.removeprefix('data/')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        verify(root, document)
        root.rename(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--manifest', type=Path, default=MANIFEST)
    args = parser.parse_args()
    doc = read_manifest(args.manifest)
    receipts = []
    if not args.verify_only:
        stage(args.output, doc, downloader=lambda record: download(record, receipts))
    verify(args.output, doc)
    print('::notice title=ArmPort approved ranges::' + json.dumps(dict(manifest=args.manifest.name, files=doc['file_count'], bytes=doc['payload_bytes'],
        unresolved=doc['unresolved'], source_archives_fully_downloaded=False, runtime_validated=False,
        verified_cached_layer=args.verify_only, transfers=receipts)))


if __name__ == '__main__':
    main()
