#!/usr/bin/env python3
"""Verify and reproduce the pinned missing-only Atlas world supplement.

The archive reuses original donor DEFLATE streams, so its reviewed digest does
not depend on the builder's zlib compressor version. Complete donor archives
are neither downloaded nor claimed verified.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import struct
import tempfile
import urllib.request
import urllib.error
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE = 'atlas-world-supplement.zip'
MANIFEST = 'atlas-world-supplement-manifest.json'
ARCHIVE_PIN = {'bytes': 203438405, 'sha256': '499d50fe7bb399465dcd30d046dec99551dd5f98181947e98f9d5d99a3880c60'}
MANIFEST_PIN = {'bytes': 4209334, 'sha256': '2566bed7c2948b53ac169e090086613da571ec45008d72a6eb00e092acc2d203'}
FILE_COUNT, PAYLOAD_BYTES = 2877, 309655940
FILES_SHA256 = 'c21ea231a2cd280faef2ae915c9c21776548718421031d4c1382604183eaf19d'
SOURCE = '0b75ade0c801735e10c5798f641948a45cc50488'
DATA = 'd51533ec8e6a9cf726b9214968077a05fdcf19f3'
SCOPE = 'atlas_world_geometry_texture_supplement'
MAX_ARCHIVE_BYTES = 256 * 1024**2
MAX_MANIFEST_BYTES = 16 * 1024**2
MAX_ENTRY_BYTES = 32 * 1024**2
MAX_RANGE_BYTES = 16 * 1024**2


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Missing or linked world input: ' + path.name)
    with path.open('rb') as stream:
        return {'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def bundle_contract():
    return {'scope': SCOPE, 'archive': ARCHIVE, 'archive_pin': dict(ARCHIVE_PIN),
        'manifest_file': MANIFEST, 'manifest_pin': dict(MANIFEST_PIN),
        'file_count': FILE_COUNT, 'payload_bytes': PAYLOAD_BYTES, 'files_sha256': FILES_SHA256,
        'installation': 'private_client_and_server_worktrees_missing_files_only',
        'imported_assets_modified': False, 'accepted_cache_archive_modified': False,
        'runtime_visual_validated': False, 'gameplay_validated': False}


def safe_payload(name):
    path = PurePosixPath(name)
    return (name == name.casefold() and path.as_posix() == name and '..' not in path.parts
        and '\\' not in name and ':' not in name and name.isascii()
        and (name.startswith('data/object_library/') and path.suffix == '.geo'
             or name.startswith('data/texture_library/') and path.suffix == '.texture'))


def read_manifest(manifest, *, root=ROOT):
    manifest = Path(manifest)
    require(pin(manifest) == MANIFEST_PIN and MANIFEST_PIN['bytes'] <= MAX_MANIFEST_BYTES,
        'World manifest differs from reviewed metadata')
    document = json.loads(manifest.read_text())
    require(document.get('format') == 1 and document.get('scope') == SCOPE
        and document.get('source_commit') == SOURCE and document.get('data_commit') == DATA,
        'World baseline identity differs')
    require(document.get('archive') == {'filename': ARCHIVE, **ARCHIVE_PIN}
        and 0 < ARCHIVE_PIN['bytes'] <= MAX_ARCHIVE_BYTES
        and document.get('file_count') == FILE_COUNT and document.get('payload_bytes') == PAYLOAD_BYTES
        and document.get('runtime_visual_validated') is False and document.get('gameplay_validated') is False,
        'World inventory bounds or validation scope differ')
    files, provenance = document.get('files', {}), document.get('provenance', {})
    require(isinstance(files, dict) and len(files) == FILE_COUNT and set(files) == set(provenance.get('entries', {}))
        and sum(row['bytes'] for row in files.values()) == PAYLOAD_BYTES
        and hashlib.sha256(canonical(files)).hexdigest() == FILES_SHA256,
        'World file inventory differs')
    require(provenance.get('source_archives_fully_downloaded') is False
        and provenance.get('source_archive_sha256_verified') is False,
        'Selected ranges must not claim full donor verification')
    accepted = json.loads((Path(root) / 'assets/reference-inputs-manifest.json').read_text())
    originals = {'data/' + row['path'].casefold() for row in accepted['files']}
    avatar = json.loads((Path(root) / 'assets/character-avatar-defaults-manifest.json').read_text())
    require(not originals.intersection(files) and not set(avatar['files']).intersection(files),
        'World supplement would replace an accepted imported or avatar asset')
    for name, row in files.items():
        require(safe_payload(name) and 0 < row['bytes'] <= MAX_ENTRY_BYTES
            and re.fullmatch('[0-9a-f]{64}', row['sha256']), 'Invalid world payload path or pin')
        donor = provenance['entries'][name]
        require(donor.get('bytes') == row['bytes'] and donor.get('sha256') == row['sha256']
            and donor.get('path', '').casefold() == name.removeprefix('data/')
            and donor.get('integrity') == 'exact_http_206_range_stable_etag_zlib_size_and_table_md5_passed'
            and re.fullmatch('https://dists[.]thunderspy[.]org/piggs/[A-Za-z0-9]+[.]pigg', donor.get('source_url', ''))
            and re.fullmatch('[0-9a-f]{64}', donor.get('stored_sha256', ''))
            and re.fullmatch('[0-9a-f]{32}', donor.get('md5_table', '')),
            'World selected donor identity differs')
    return document


def verify(archive, manifest, *, root=ROOT):
    document = read_manifest(manifest, root=root)
    require(pin(archive) == ARCHIVE_PIN, 'World archive differs from reviewed bytes')
    with zipfile.ZipFile(archive) as payload:
        entries = payload.infolist()
        require(len(entries) == FILE_COUNT and len({row.filename for row in entries}) == FILE_COUNT
            and {row.filename for row in entries} == set(document['files']), 'World ZIP inventory differs')
        for entry in entries:
            expected = document['files'][entry.filename]
            require(not entry.is_dir() and not entry.flag_bits & 1
                and stat.S_ISREG(entry.external_attr >> 16) and entry.file_size == expected['bytes']
                and entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), 'Invalid world ZIP member')
            raw = payload.read(entry)
            require(len(raw) == expected['bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256']
                and hashlib.md5(raw).hexdigest() == document['provenance']['entries'][entry.filename]['md5_table'],
                'World ZIP payload differs: ' + entry.filename)
    return document


def decode_entry(stored, donor):
    require(len(stored) == donor['stored_bytes'] and hashlib.sha256(stored).hexdigest() == donor['stored_sha256'],
        'World selected stored range differs')
    if donor['compressed']:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(stored, donor['bytes'] + 1)
        require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
            and len(stored) >= 6 and stored[0] & 15 == 8 and not stored[1] & 32,
            'World selected zlib envelope differs')
        encoded, method = stored[2:-4], zipfile.ZIP_DEFLATED
    else:
        raw, encoded, method = stored, stored, zipfile.ZIP_STORED
    require(len(raw) == donor['bytes'] and hashlib.sha256(raw).hexdigest() == donor['sha256']
        and hashlib.md5(raw).hexdigest() == donor['md5_table'], 'World selected decoded payload differs')
    return raw, encoded, method


def write_donor_zip(output, entries):
    """Write classic ZIP headers around verified, original donor streams."""
    directory = bytearray()
    with Path(output).open('xb') as archive:
        for name, donor, stored in sorted(entries, key=lambda row: row[0]):
            raw, encoded, method = decode_entry(stored, donor)
            filename = name.encode('ascii')
            crc, offset = zlib.crc32(raw), archive.tell()
            flags, dostime, dosdate = 0, 0, ((2026 - 1980) << 9) | (1 << 5) | 1
            archive.write(struct.pack('<IHHHHHIIIHH', 0x04034b50, 20, flags, method, dostime, dosdate,
                crc, len(encoded), len(raw), len(filename), 0))
            archive.write(filename); archive.write(encoded)
            directory += struct.pack('<IHHHHHHIIIHHHHHII', 0x02014b50, (3 << 8) | 20, 20,
                flags, method, dostime, dosdate, crc, len(encoded), len(raw), len(filename),
                0, 0, 0, 0, (stat.S_IFREG | 0o444) << 16, offset) + filename
        start = archive.tell(); archive.write(directory)
        archive.write(struct.pack('<IHHHHIIH', 0x06054b50, 0, 0, len(entries), len(entries), len(directory), start, 0))


def download_range(group):
    key, names = group
    url, etag, modified, total, range_text = key
    match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', range_text)
    require(match is not None and int(match[3]) == total, 'Invalid reviewed world source range')
    start, end = int(match[1]), int(match[2])
    require(0 <= start <= end < total <= 2 * 1024**3 and end - start + 1 <= MAX_RANGE_BYTES,
        'Reviewed world source range exceeds bound')
    request = urllib.request.Request(url, headers={'Range': f'bytes={start}-{end}',
        'If-Match': etag, 'User-Agent': 'coh-android-reviewed-world-ranges/1'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                require(response.status == 206 and response.geturl() == url
                    and response.headers.get('ETag') == etag and response.headers.get('Last-Modified') == modified
                    and response.headers.get('Content-Range') == range_text
                    and int(response.headers.get('Content-Length', -1)) == end - start + 1,
                    'World donor changed or exact partial transfer was refused')
                source = response.read(end - start + 2)
            break
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == 2:
                raise
    require(len(source) == end - start + 1, 'World donor partial transfer length differs')
    result = []
    for name, donor in names:
        offset = donor['offset'] - start
        require(0 <= offset and donor['stored_bytes'] <= len(source) - offset,
            'World entry escaped reviewed transfer range')
        stored = source[offset:offset + donor['stored_bytes']]
        decode_entry(stored, donor)
        result.append((name, donor, stored))
    return result


def materialize(archive=None, manifest=None, *, root=ROOT, downloader=download_range):
    source = Path(root) / 'assets'
    archive, manifest = Path(archive or source / ARCHIVE), Path(manifest or source / MANIFEST)
    document = read_manifest(manifest, root=root)
    if archive.exists() or archive.is_symlink():
        verify(archive, manifest, root=root)
        return bundle_contract() | {'status': 'verified_existing_archive', 'source_archives_fully_downloaded': False}
    groups = {}
    for name, donor in document['provenance']['entries'].items():
        key = (donor['source_url'], donor['source_etag'], donor['source_last_modified'],
            donor['source_archive_bytes'], donor['source_content_range'])
        groups.setdefault(key, []).append((name, donor))
    with tempfile.TemporaryDirectory(prefix='.atlas-world-', dir=archive.parent) as staging:
        temporary = Path(staging) / ARCHIVE
        entries = []
        with ThreadPoolExecutor(max_workers=8) as pool:
            for rows in pool.map(downloader, groups.items()):
                entries.extend(rows)
        write_donor_zip(temporary, entries)
        verify(temporary, manifest, root=root)
        os.link(temporary, archive, follow_symlinks=False)
    return bundle_contract() | {'status': 'reconstructed_from_verified_selected_ranges',
        'downloaded_ranges': len(groups), 'source_archives_fully_downloaded': False,
        'source_archive_sha256_verified': False, 'original_donor_deflate_streams_reused': True}


def prepare(output, *, root=ROOT):
    output = Path(output)
    require(output.is_dir() and not output.is_symlink(), 'World output must be a regular directory')
    source = Path(root) / 'assets'
    verify(source / ARCHIVE, source / MANIFEST, root=root)
    for name in (ARCHIVE, MANIFEST):
        require(not (output / name).exists() and not (output / name).is_symlink(), 'World output already exists')
    for name in (ARCHIVE, MANIFEST):
        shutil.copyfile(source / name, output / name)
    verify(output / ARCHIVE, output / MANIFEST, root=root)
    return bundle_contract()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--materialize', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.materialize:
        print(json.dumps(materialize(), indent=2))
    elif args.verify:
        verify(ROOT / 'assets' / ARCHIVE, ROOT / 'assets' / MANIFEST)
        print(json.dumps(bundle_contract(), indent=2))
    elif args.output:
        print(json.dumps(prepare(args.output), indent=2))
    else:
        parser.error('Select --materialize, --verify or --output')
