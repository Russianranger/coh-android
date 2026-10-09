#!/usr/bin/env python3
"""Materialize the pinned 0.13.11 appearance append over the public 0.13.10 ZIP.

Only frozen selected HTTP ranges are fetched. Every accepted decoded leaf and
every one of the 5,476 accepted encoded ZIP streams is retained byte for byte.
The source envelope is transport-only: the guest receives exact plaintext JSON.
"""
from __future__ import annotations
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import tempfile
import zipfile
import zlib

import discover_client_appearance_assets as discovery
import discover_client_visual_sweep as previous
import prepare_client_visual_assets as baseline

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE, MANIFEST = baseline.ARCHIVE, baseline.MANIFEST
SOURCE_MANIFEST = 'client-appearance-manifest.json'
SOURCE_MANIFEST_SCOPE = 'coh_client_appearance_source_manifest_v1'
SOURCE_REQUESTS_SCOPE = 'coh_client_appearance_source_requests_v1'
MAX_ARCHIVE_BYTES, MAX_MANIFEST_BYTES = discovery.MAX_ARCHIVE_BYTES, discovery.MAX_MANIFEST_BYTES
MAX_SOURCE_MANIFEST_BYTES, MAX_SOURCE_GZIP_BYTES = 12 * 1024**2, 8 * 1024**2
MAX_PAYLOAD_BYTES, MAX_ENTRY_BYTES = discovery.MAX_PAYLOAD_BYTES, baseline.MAX_ENTRY_BYTES
# Set from the fully verified original donor output, never from a build host.
ARCHIVE_PIN = {'bytes': 854341235, 'sha256': '840619b3b40c24f206576580dfaedb779a66582f1df189f37002dd59c5399cb9'}
MANIFEST_PIN = {'bytes': 42257673, 'sha256': '8b3f579a9ff48e80f40e06e252c91fe3357daf9f0b01441dea5bceaa5801f1e6'}
REQUESTS_PIN = {'bytes': 13943112, 'sha256': 'd775d0f7a86b1073edac75c403fd18f43ee8d362bb9613c9a42a728f4b380ec2'}
FILES_SHA256 = 'e23299918437e5d0afa2e9d2003eb966151f59471eaeb430313d2824d42fe341'
FILE_COUNT, PAYLOAD_BYTES, APPEARANCE_FILE_COUNT = 9490, 1505717817, 4014
APPEARANCE_FILES_SHA256 = 'c18ee3f0d2551249bfb98b921be8c230db5923a5a531cec2a55d0c03e80810ae'
require, pin, canonical = baseline.require, baseline.pin, baseline.canonical


def pin_bytes(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def source_bytes(path, expected, scope):
    """Read only the pinned plaintext manifest or its bounded source envelope."""
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Missing or linked appearance manifest')
    require(0 < expected['bytes'] <= MAX_MANIFEST_BYTES,
        'Appearance decoded manifest pin exceeds bound')
    with path.open('rb') as stream:
        raw = stream.read(MAX_MANIFEST_BYTES + 1)
    require(0 < len(raw) <= MAX_MANIFEST_BYTES, 'Appearance source manifest exceeds bound')
    if pin_bytes(raw) == expected:
        return raw
    require(len(raw) <= MAX_SOURCE_MANIFEST_BYTES, 'Appearance source envelope exceeds bound')
    def unique_fields(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Appearance source envelope has duplicate fields')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique_fields)
    require(isinstance(value, dict) and set(value) == {'format', 'scope', 'encoding', 'decoded', 'gzip', 'data'}
        and type(value['format']) is int and value['format'] == 1
        and value['scope'] == scope and value['encoding'] == 'gzip+base64'
        and value['decoded'] == expected, 'Appearance source envelope metadata differs')
    encoded, packed_pin = value['data'], value['gzip']
    require(isinstance(encoded, str) and isinstance(packed_pin, dict)
        and set(packed_pin) == {'bytes', 'sha256'} and type(packed_pin['bytes']) is int
        and 0 < packed_pin['bytes'] <= MAX_SOURCE_GZIP_BYTES
        and isinstance(packed_pin['sha256'], str) and re.fullmatch('[0-9a-f]{64}', packed_pin['sha256'])
        and len(encoded) == 4 * ((packed_pin['bytes'] + 2) // 3),
        'Appearance encoded source stream exceeds bound or differs')
    packed = base64.b64decode(encoded, validate=True)
    require(pin_bytes(packed) == packed_pin, 'Appearance source gzip stream differs')
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        decoded = decoder.decompress(packed, expected['bytes'] + 1)
    except zlib.error as exc:
        raise ValueError('Appearance source gzip stream is invalid') from exc
    require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
        and pin_bytes(decoded) == expected, 'Appearance decoded source bytes differ or exceed bound')
    return decoded


def manifest_bytes(path):
    return source_bytes(path, MANIFEST_PIN, SOURCE_MANIFEST_SCOPE)


def requests_bytes(path):
    return source_bytes(path, REQUESTS_PIN, SOURCE_REQUESTS_SCOPE)


def appearance_files(value):
    """Validate the new leaf partition without changing ancestral validators."""
    delta, files = value.get('appearance_extension', {}), value.get('files', {})
    names = set(delta.get('files', {}))
    additions = {name: files[name] for name in names if name in files}
    require(delta.get('scope') == discovery.SCOPE and delta.get('missing_only') is True
        and delta.get('baseline_payloads_preserved') is True
        and delta.get('baseline_archive_pin') == baseline.ARCHIVE_PIN
        and delta.get('baseline_manifest_pin') == baseline.MANIFEST_PIN
        and delta.get('baseline_file_count') == baseline.FILE_COUNT
        and delta.get('baseline_payload_bytes') == baseline.PAYLOAD_BYTES
        and delta.get('baseline_files_sha256') == baseline.FILES_SHA256
        and len(names) == len(additions) == delta.get('file_count') == APPEARANCE_FILE_COUNT
        and hashlib.sha256(canonical(additions)).hexdigest() == delta.get('files_sha256') == APPEARANCE_FILES_SHA256
        and sum(row['bytes'] for row in additions.values()) == delta.get('payload_bytes')
        and all(delta.get(key) is False for key in ('runtime_visual_validated', 'full_global_asset_closure',
            'native_renderer_changed', 'preloading', 'full_archive_verified')),
        'Appearance append bounds or preservation scope differ')
    for name, expected in delta['files'].items():
        require(baseline.safe_payload(name) and isinstance(expected, dict)
            and set(expected) == {'requests_sha256'}
            and expected['requests_sha256'] == hashlib.sha256(canonical(value['requests'][name])).hexdigest()
            and value['requests'][name], 'Appearance leaf has no reviewed source request')
    require(set(delta.get('requested_model_proof', {})) == {name for name in names if name.endswith('.geo')},
        'Appearance native geometry proof partition differs')
    return names


def read_manifest(manifest, *, root=ROOT):
    root = Path(root)
    value = json.loads(manifest_bytes(manifest))
    require(value.get('format') == 1 and value.get('scope') == baseline.SCOPE
        and value.get('archive') == {'filename': ARCHIVE, **ARCHIVE_PIN}
        and 0 < ARCHIVE_PIN['bytes'] <= MAX_ARCHIVE_BYTES
        and value.get('file_count') == FILE_COUNT and value.get('payload_bytes') == PAYLOAD_BYTES
        and 0 < PAYLOAD_BYTES <= MAX_PAYLOAD_BYTES and value.get('files_sha256') == FILES_SHA256
        and len(value.get('files', {})) == FILE_COUNT
        and sum(row['bytes'] for row in value['files'].values()) == PAYLOAD_BYTES
        and hashlib.sha256(canonical(value['files'])).hexdigest() == FILES_SHA256,
        'Appearance composed inventory or output pins differ')
    names = appearance_files(value)
    old = baseline.read_manifest(root/'assets'/baseline.MANIFEST, root=root)
    require(set(value) == set(old) | {'appearance_extension'}, 'Appearance changes ancestor document fields')
    # Compare every accepted row/proof/policy/receipt to the exact public recipe.
    projected = copy.deepcopy(value)
    del projected['appearance_extension']
    for key in ('archive', 'file_count', 'payload_bytes', 'files_sha256'):
        projected[key] = old[key]
    for key in ('files', 'requests'):
        require(set(projected[key]) == set(old[key]) | names, 'Appearance ancestor partition differs')
        projected[key] = {name: projected[key][name] for name in old[key]}
    entries = projected['provenance']['entries']
    require(set(entries) == set(old['provenance']['entries']) | names, 'Appearance selected provenance differs')
    projected['provenance']['entries'] = {name: entries[name] for name in old['provenance']['entries']}
    for key in ('source_files',):
        require(set(old[key]) <= set(projected[key]), 'Appearance discards an accepted source pin')
        projected[key] = {name: projected[key][name] for name in old[key]}
    receipts = projected['provenance']['sweep_downloads']
    old_receipts = old['provenance']['sweep_downloads']
    require(set(old_receipts) <= set(receipts), 'Appearance discards an accepted source receipt')
    projected['provenance']['sweep_downloads'] = {name: receipts[name] for name in old_receipts}
    require(projected == old, 'Appearance changes the exact accepted 0.13.10 recipe')
    previous.verify_sources(root, value['source_files'])
    delta = value['appearance_extension']
    request_path = root/'assets/client-appearance-requests.json'
    require(pin_bytes(requests_bytes(request_path)) == delta['discovery_requests_pin'],
        'Appearance source discovery requests differ')
    for name in names:
        row, record = value['files'][name], value['provenance']['entries'][name]
        require(type(row.get('bytes')) is int and 0 < row['bytes'] <= MAX_ENTRY_BYTES
            and re.fullmatch('[0-9a-f]{64}', row.get('sha256', ''))
            and record.get('path', '').casefold() == name.removeprefix('data/')
            and record.get('bytes') == row['bytes'] and record.get('sha256') == row['sha256']
            and record.get('integrity') == 'exact_http_206_range_stable_etag_zlib_size_and_table_md5_passed'
            and record.get('cached_header_verified') is True
            and re.fullmatch('https://dists[.]thunderspy[.]org/piggs/[A-Za-z0-9]+[.]pigg', record.get('source_url', ''))
            and re.fullmatch('[0-9a-f]{32}', record.get('md5_table', ''))
            and re.fullmatch('[0-9a-f]{64}', record.get('stored_sha256', '')),
            'Appearance selected original PIGG leaf differs')
        baseline.selected_download_record(value, record)
    return value


def model_proofs(value):
    result = {}
    for key in ('closure', 'visual_extension', 'sweep_extension', 'appearance_extension'):
        result.update(value.get(key, {}).get('requested_model_proof', {}))
    return result


def verify(archive, manifest, *, root=ROOT):
    value = read_manifest(manifest, root=root)
    require(pin(archive) == ARCHIVE_PIN, 'Appearance composed archive differs')
    proofs = model_proofs(value)
    with zipfile.ZipFile(archive) as source:
        entries = source.infolist()
        require(len(entries) == len({row.filename for row in entries}) == FILE_COUNT
            and {row.filename for row in entries} == set(value['files']), 'Appearance ZIP inventory differs')
        for entry in entries:
            expected = value['files'][entry.filename]
            require(not entry.is_dir() and entry.flag_bits == 0 and stat.S_ISREG(entry.external_attr >> 16)
                and entry.file_size == expected['bytes'] and entry.file_size <= MAX_ENTRY_BYTES
                and entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                'Appearance ZIP member bounds or encoding differs')
            baseline.verify_payload(entry.filename, source.read(entry), expected,
                value['provenance']['entries'][entry.filename], requests=value['requests'][entry.filename],
                model_proof=proofs.get(entry.filename))
    return value


def encoded_member(stream, info):
    stream.seek(info.header_offset)
    header = stream.read(30)
    require(len(header) == 30, 'Appearance preserved ZIP header is truncated')
    signature, _, flags, method, _, _, crc, packed, size, name_size, extra_size = struct.unpack('<IHHHHHIIIHH', header)
    require(signature == 0x04034b50 and flags == info.flag_bits == 0 and method == info.compress_type
        and crc == info.CRC and packed == info.compress_size and size == info.file_size
        and stream.read(name_size) == info.filename.encode('ascii') and extra_size == 0,
        'Appearance preserved ZIP header differs')
    encoded = stream.read(packed)
    require(len(encoded) == packed, 'Appearance preserved ZIP stream is truncated')
    return encoded


def verify_preserved(archive, baseline_archive, value):
    old_names = set(value['files']) - set(value['appearance_extension']['files'])
    require(pin(baseline_archive) == baseline.ARCHIVE_PIN and len(old_names) == baseline.FILE_COUNT,
        'Appearance immediate donor archive differs')
    with zipfile.ZipFile(archive) as new, zipfile.ZipFile(baseline_archive) as old, \
            Path(archive).open('rb') as new_stream, Path(baseline_archive).open('rb') as old_stream:
        require(set(old.namelist()) == old_names, 'Appearance immediate donor inventory differs')
        for name in sorted(old_names):
            require(encoded_member(new_stream, new.getinfo(name)) == encoded_member(old_stream, old.getinfo(name)),
                'Appearance changes an accepted encoded stream: ' + name)
    return {'retained_encoded_streams': len(old_names), 'retained_encoded_streams_byte_identical': True}


def verify_discovery_plan(directory, manifest, *, root=ROOT):
    directory = Path(directory)
    value = read_manifest(manifest, root=root)
    delta = value['appearance_extension']
    require(pin(directory/'client-appearance-plan.json') == delta['discovery_plan_pin']
        and pin(directory/'client-appearance-requests.json') == delta['discovery_requests_pin'],
        'Appearance fresh discovery does not reproduce frozen plan or request bytes')
    return {'status': 'fresh_discovery_reproduces_frozen_plan_and_requests',
        'plan_pin': delta['discovery_plan_pin'], 'requests_pin': delta['discovery_requests_pin']}


def bundle_contract():
    return {'scope': baseline.SCOPE, 'archive': ARCHIVE, 'archive_pin': ARCHIVE_PIN,
        'manifest_file': MANIFEST, 'manifest_pin': MANIFEST_PIN,
        'file_count': FILE_COUNT, 'payload_bytes': PAYLOAD_BYTES, 'files_sha256': FILES_SHA256,
        'appearance_file_count': APPEARANCE_FILE_COUNT, 'appearance_scope': discovery.SCOPE,
        'installation': 'private_client_worktree_missing_files_only',
        'imported_assets_modified': False, 'prepared_caches_modified': False,
        'existing_supplements_modified': False, 'runtime_visual_validated': False,
        'gameplay_validated': False}


def materialize(manifest, baseline_directory, output, *, root=ROOT, downloader=baseline.download_selected_range):
    manifest, baseline_directory, output = Path(manifest), Path(baseline_directory), Path(output)
    value = read_manifest(manifest, root=root)
    require(output.is_dir() and not output.is_symlink(), 'Appearance output must be an existing regular directory')
    old_archive, old_manifest = baseline_directory/ARCHIVE, baseline_directory/MANIFEST
    require(pin(old_archive) == baseline.ARCHIVE_PIN and pin(old_manifest) == baseline.MANIFEST_PIN,
        'Appearance baseline directory differs from exact public 0.13.10')
    for name in (ARCHIVE, MANIFEST):
        require(not (output/name).exists() and not (output/name).is_symlink(), 'Appearance output already exists')
    names = appearance_files(value)
    groups = {}
    for name in sorted(names):
        record = baseline.selected_download_record(value, value['provenance']['entries'][name])
        key = tuple(record[k] for k in ('source_url', 'source_etag', 'source_last_modified', 'source_archive_bytes')) \
            + (record.get('source_download_content_range', record['source_content_range']),)
        groups.setdefault(key, []).append((name, record))
    with tempfile.TemporaryDirectory(prefix='.client-appearance-', dir=output) as temporary:
        temporary = Path(temporary)
        def fetch(group):
            count = 0
            for name, record, stored in downloader(group):
                require(name in names and pin_bytes(stored) == {'bytes': record['stored_bytes'],
                    'sha256': record['stored_sha256']}, 'Appearance downloaded original stream differs')
                baseline.donor.decode_entry(stored, record)
                (temporary/hashlib.sha256(name.encode()).hexdigest()).write_bytes(stored)
                count += 1
            return count
        with ThreadPoolExecutor(max_workers=8) as pool:
            require(sum(pool.map(fetch, groups.items())) == len(names), 'Appearance selected range inventory differs')
        records = {name: value['provenance']['entries'][name] for name in names}
        target = temporary/ARCHIVE
        previous.write_extended_zip(target, old_archive, json.loads(old_manifest.read_bytes()), records, temporary)
        verified = verify(target, manifest, root=root)
        preservation = verify_preserved(target, old_archive, verified)
        (output/MANIFEST).write_bytes(manifest_bytes(manifest))
        os.link(target, output/ARCHIVE, follow_symlinks=False)
    return bundle_contract() | preservation | {'status': 'reconstructed_from_verified_selected_ranges',
        'downloaded_ranges': len(groups), 'source_archives_fully_downloaded': False,
        'source_archive_sha256_verified': False, 'original_donor_deflate_streams_reused': True}


def prepare(output, *, root=ROOT):
    output, root = Path(output), Path(root)
    assets = root/'assets'
    require(output.is_dir() and not output.is_symlink(), 'Appearance output must be an existing regular directory')
    verify(assets/ARCHIVE, assets/SOURCE_MANIFEST, root=root)
    for name in (ARCHIVE, MANIFEST):
        require(not (output/name).exists() and not (output/name).is_symlink(), 'Appearance output already exists')
    shutil.copyfile(assets/ARCHIVE, output/ARCHIVE)
    (output/MANIFEST).write_bytes(manifest_bytes(assets/SOURCE_MANIFEST))
    return bundle_contract()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT/'assets'/SOURCE_MANIFEST)
    parser.add_argument('--materialize', action='store_true')
    parser.add_argument('--baseline-directory', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path, metavar='ARCHIVE')
    args = parser.parse_args()
    if args.materialize:
        require(args.baseline_directory is not None and args.output is not None,
            'Appearance materialization requires --baseline-directory and --output')
        print(json.dumps(materialize(args.manifest, args.baseline_directory, args.output), indent=2))
    elif args.verify:
        verify(args.verify, args.manifest)
        print(json.dumps(bundle_contract(), indent=2))
    elif args.output:
        print(json.dumps(prepare(args.output), indent=2))
    else:
        parser.error('Select --materialize, --verify ARCHIVE or --output DIR')
