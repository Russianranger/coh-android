#!/usr/bin/env python3
"""Materialize the exact original interface sweep over accepted 0.13.13.

Every ancestral recipe row and every one of 9,613 encoded visual ZIP streams
is conserved. The source envelope transports the pinned plaintext manifest.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import zipfile

import discover_client_ui_sweep_assets as discovery
import discover_client_visual_sweep as previous
import prepare_client_ui_repair_assets as ancestor
import prepare_client_visual_assets as original

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE, MANIFEST = ancestor.ARCHIVE, ancestor.MANIFEST
SOURCE_MANIFEST = 'client-ui-sweep-manifest.json'
SOURCE_MANIFEST_SCOPE = 'coh_client_ui_sweep_append_source_manifest_v1'
APPEND_RECIPE_SCOPE = 'coh_client_ui_sweep_exact_append_recipe_v1'
APPEND_RECIPE_PIN = {'bytes': 6039617, 'sha256': 'f2cce28d10ad9b47abd454634c3490a321f79030693822f7d18aee8e6fb2aee1'}
SOURCE_REQUESTS = 'client-ui-sweep-requests.json'
SOURCE_REQUESTS_SCOPE = 'coh_client_ui_sweep_source_requests_v1'
SOURCE_PLAN = 'client-ui-sweep-plan.json'
SOURCE_PLAN_SCOPE = 'coh_client_ui_sweep_source_plan_v1'
MAX_ARCHIVE_BYTES, MAX_MANIFEST_BYTES = ancestor.MAX_ARCHIVE_BYTES, ancestor.MAX_MANIFEST_BYTES
MAX_PAYLOAD_BYTES, MAX_ENTRY_BYTES = ancestor.MAX_PAYLOAD_BYTES, ancestor.MAX_ENTRY_BYTES
# Frozen from fully checked original donor ranges, not from a build host.
ARCHIVE_PIN = {'bytes': 859075775, 'sha256': '5f91b7d4ebe91e6a547923d702e2fcd56d7fc1d36fb7bffbb66463562d977d60'}
MANIFEST_PIN = {'bytes': 48591999, 'sha256': '8587015400e1af639e2118649f0d9c77a089d564bfe2c97cbf9d80baaee5f9a2'}
REQUESTS_PIN = {'bytes': 4642613, 'sha256': '13a3ddd9bc6c07f136a607c157e7399ff87d4aeec8ea9218b5a257c8d232612d'}
PLAN_PIN = {'bytes': 4702988, 'sha256': '0d5f3e9355322d5b4fc345c52b07df44240f621c1dc666328aa531a12703566a'}
FILES_SHA256 = '11345ad8a72f14f2bb1cca5b88f2f9a09c724aa5e6f4f4ce2c73526a77884e12'
FILE_COUNT, PAYLOAD_BYTES, UI_FILE_COUNT = 10401, 1534806726, 788
UI_FILES_SHA256 = 'a52f89042248557d75f650524134c5ba506bd73c286521190a090810284c7a57'
require, pin, canonical = ancestor.require, ancestor.pin, ancestor.canonical
pin_bytes = ancestor.pin_bytes


def manifest_bytes(path, *, root=ROOT):
    """Reconstruct exactly the pinned plaintext from a small immutable append.

    The accepted 0.13.13 source manifest is already owned by the repository;
    copying its millions of unchanged provenance rows into another source blob
    would add no evidence. Final plaintext identity is checked before return.
    """
    path, root = Path(path), Path(root)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_MANIFEST_BYTES,
        'UI sweep source manifest is missing, linked or oversized')
    raw = path.read_bytes()
    if pin_bytes(raw) == MANIFEST_PIN:
        return raw
    recipe = json.loads(ancestor.ancestor.source_bytes(path, APPEND_RECIPE_PIN, SOURCE_MANIFEST_SCOPE))
    require(set(recipe) == {'format', 'scope', 'baseline_manifest_pin', 'current_manifest_pin',
            'identity_update', 'files', 'requests', 'provenance_entries', 'source_files',
            'sweep_downloads', 'ui_sweep_extension'}
        and recipe['format'] == 1 and recipe['scope'] == APPEND_RECIPE_SCOPE
        and recipe['baseline_manifest_pin'] == ancestor.MANIFEST_PIN
        and recipe['current_manifest_pin'] == MANIFEST_PIN
        and set(recipe['identity_update']) == {'archive', 'file_count', 'payload_bytes', 'files_sha256'},
        'UI sweep exact append recipe identity differs')
    value = json.loads(ancestor.manifest_bytes(root/'assets'/ancestor.SOURCE_MANIFEST))
    for key in ('files', 'requests', 'source_files'):
        require(not set(value[key]).intersection(recipe[key]), 'UI sweep source append replaces an old ' + key)
        value[key].update(recipe[key])
    for key, source in (('entries', 'provenance_entries'), ('sweep_downloads', 'sweep_downloads')):
        require(not set(value['provenance'][key]).intersection(recipe[source]),
            'UI sweep source append replaces old provenance')
        value['provenance'][key].update(recipe[source])
    value.update(recipe['identity_update'])
    value['ui_sweep_extension'] = recipe['ui_sweep_extension']
    decoded = canonical(value) + b'\n'
    require(pin_bytes(decoded) == MANIFEST_PIN, 'UI sweep reconstructed plaintext identity differs')
    return decoded


def requests_bytes(path):
    try:
        return ancestor.ancestor.source_bytes(path, REQUESTS_PIN, SOURCE_REQUESTS_SCOPE)
    except ValueError as exc:
        raise ValueError('UI frozen requests differ: ' + str(exc)) from exc


def plan_bytes(path):
    return ancestor.ancestor.source_bytes(path, PLAN_PIN, SOURCE_PLAN_SCOPE)


def ui_files(value):
    delta, files = value.get('ui_sweep_extension', {}), value.get('files', {})
    names = set(delta.get('files', {}))
    additions = {name: files[name] for name in names if name in files}
    require(delta.get('scope') == discovery.SCOPE and delta.get('missing_only') is True
        and delta.get('baseline_payloads_preserved') is True
        and delta.get('baseline_archive_pin') == ancestor.ARCHIVE_PIN
        and delta.get('baseline_manifest_pin') == ancestor.MANIFEST_PIN
        and delta.get('baseline_file_count') == ancestor.FILE_COUNT
        and delta.get('baseline_payload_bytes') == ancestor.PAYLOAD_BYTES
        and delta.get('baseline_files_sha256') == ancestor.FILES_SHA256
        and len(names) == len(additions) == delta.get('file_count') == UI_FILE_COUNT
        and 0 < UI_FILE_COUNT <= discovery.MAX_ADDITIONS
        and hashlib.sha256(canonical(additions)).hexdigest() == delta.get('files_sha256') == UI_FILES_SHA256
        and sum(row['bytes'] for row in additions.values()) == delta.get('payload_bytes')
        and 0 < delta.get('payload_bytes', 0) <= discovery.MAX_NEW_PAYLOAD_BYTES
        and delta.get('discovery_requests_pin') == REQUESTS_PIN
        and delta.get('discovery_plan_pin') == PLAN_PIN
        and all(delta.get(key) is False for key in ('runtime_visual_validated',
            'native_renderer_changed', 'native_gameplay_changed', 'full_global_asset_closure',
            'preloading', 'full_archive_verified')),
        'UI append bounds, source pins or preservation policy differ')
    for name, expected in delta['files'].items():
        rows = value.get('requests', {}).get(name, [])
        require(previous.safe_payload(name) and name.endswith('.texture')
            and isinstance(expected, dict) and set(expected) == {'requests_sha256'}
            and expected['requests_sha256'] == hashlib.sha256(canonical(rows)).hexdigest()
            and rows and all(row.get('scope') == discovery.REQUEST_SCOPE
                and row.get('source_path') in value.get('source_files', {})
                and type(row.get('source_line')) is int and row['source_line'] > 0
                and row.get('native_texture_key') == PurePosixPath(name).stem
                for row in rows), 'UI leaf lacks exact native source requests')
    return names


def ancestor_projection(value, old):
    """Remove only the append and compare all accepted ancestor fields exactly."""
    names = set(value['ui_sweep_extension']['files'])
    projected = copy.deepcopy(value)
    del projected['ui_sweep_extension']
    for key in ('archive', 'file_count', 'payload_bytes', 'files_sha256'):
        projected[key] = old[key]
    for key in ('files', 'requests'):
        require(set(projected[key]) == set(old[key]) | names,
            'UI ancestor leaf partition differs')
        projected[key] = {name: projected[key][name] for name in old[key]}
    entries = projected['provenance']['entries']
    require(set(entries) == set(old['provenance']['entries']) | names,
        'UI ancestor provenance partition differs')
    projected['provenance']['entries'] = {name: entries[name] for name in old['provenance']['entries']}
    require(set(old['source_files']) <= set(projected['source_files']),
        'UI discards an accepted source witness')
    projected['source_files'] = {name: projected['source_files'][name] for name in old['source_files']}
    receipts, old_receipts = projected['provenance']['sweep_downloads'], old['provenance']['sweep_downloads']
    require(set(old_receipts) <= set(receipts), 'UI discards an accepted source receipt')
    projected['provenance']['sweep_downloads'] = {name: receipts[name] for name in old_receipts}
    require(projected == old, 'UI changes the exact accepted 0.13.13 recipe')
    return projected


def read_manifest(manifest, *, root=ROOT):
    root = Path(root)
    value = json.loads(manifest_bytes(manifest, root=root))
    require(value.get('format') == 1 and value.get('scope') == original.SCOPE
        and value.get('archive') == {'filename': ARCHIVE, **ARCHIVE_PIN}
        and 0 < ARCHIVE_PIN['bytes'] <= MAX_ARCHIVE_BYTES
        and value.get('file_count') == FILE_COUNT == ancestor.FILE_COUNT + UI_FILE_COUNT
        and value.get('payload_bytes') == PAYLOAD_BYTES
        and 0 < PAYLOAD_BYTES <= MAX_PAYLOAD_BYTES
        and value.get('files_sha256') == FILES_SHA256
        and len(value.get('files', {})) == FILE_COUNT
        and sum(row['bytes'] for row in value['files'].values()) == PAYLOAD_BYTES
        and hashlib.sha256(canonical(value['files'])).hexdigest() == FILES_SHA256,
        'UI composed inventory or output pins differ')
    names = ui_files(value)
    old = ancestor.read_manifest(root/'assets'/ancestor.SOURCE_MANIFEST, root=root)
    require(set(value) == set(old) | {'ui_sweep_extension'}, 'UI changes ancestor document fields')
    ancestor_projection(value, old)
    previous.verify_sources(root, value['source_files'])
    requests = json.loads(requests_bytes(root/'assets'/SOURCE_REQUESTS))
    require(json.loads(plan_bytes(root/'assets'/SOURCE_PLAN))['source_files'] == requests['source_files'],
        'UI frozen discovery plan source partition differs')
    require(requests == json.loads(canonical(discovery.source_requests(root))),
        'UI frozen requests do not reproduce finite native caller/definition scope')
    expected_sources = set(old['source_files']) | set(requests['source_files'])
    require(set(value['source_files']) == expected_sources, 'UI adds unreviewed source witnesses')
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
            'UI selected original PIGG texture differs')
        original.selected_download_record(value, record)
    return value


def model_proofs(value):
    return ancestor.model_proofs(value)


def verify(archive, manifest, *, root=ROOT):
    value = read_manifest(manifest, root=root)
    require(pin(archive) == ARCHIVE_PIN, 'UI composed archive differs')
    proofs = model_proofs(value)
    with zipfile.ZipFile(archive) as source:
        entries = source.infolist()
        require(len(entries) == len({row.filename for row in entries}) == FILE_COUNT
            and {row.filename for row in entries} == set(value['files']), 'UI ZIP inventory differs')
        for entry in entries:
            expected = value['files'][entry.filename]
            require(not entry.is_dir() and entry.flag_bits == 0 and stat.S_ISREG(entry.external_attr >> 16)
                and entry.file_size == expected['bytes'] and entry.file_size <= MAX_ENTRY_BYTES
                and entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                'UI ZIP member bounds or encoding differs')
            original.verify_payload(entry.filename, source.read(entry), expected,
                value['provenance']['entries'][entry.filename], requests=value['requests'][entry.filename],
                model_proof=proofs.get(entry.filename))
    return value


def verify_preserved(archive, baseline_archive, value):
    old_names = set(value['files']) - set(value['ui_sweep_extension']['files'])
    require(pin(baseline_archive) == ancestor.ARCHIVE_PIN and len(old_names) == ancestor.FILE_COUNT,
        'UI immediate donor archive differs')
    with zipfile.ZipFile(archive) as new, zipfile.ZipFile(baseline_archive) as old, \
            Path(archive).open('rb') as new_stream, Path(baseline_archive).open('rb') as old_stream:
        require(set(old.namelist()) == old_names, 'UI immediate donor inventory differs')
        for name in sorted(old_names):
            require(ancestor.ancestor.encoded_member(new_stream, new.getinfo(name)) == ancestor.ancestor.encoded_member(old_stream, old.getinfo(name)),
                'UI changes an accepted encoded stream: ' + name)
    return {'retained_encoded_streams': len(old_names), 'retained_encoded_streams_byte_identical': True}


def verify_original_ui_streams(archive, value, payload_cache):
    """Compare each new ZIP stream to the independently verified original range."""
    names = ui_files(value)
    with zipfile.ZipFile(archive) as source, Path(archive).open('rb') as stream:
        for name in sorted(names):
            record = value['provenance']['entries'][name]
            path = Path(payload_cache)/hashlib.sha256(name.encode()).hexdigest()
            stored = path.read_bytes()
            require(pin_bytes(stored) == {'bytes': record['stored_bytes'], 'sha256': record['stored_sha256']},
                'UI original range cache differs')
            raw, encoded, method = original.donor.decode_entry(stored, record)
            require(pin_bytes(raw) == value['files'][name]
                and source.getinfo(name).compress_type == method
                and ancestor.ancestor.encoded_member(stream, source.getinfo(name)) == encoded,
                'UI ZIP recompresses or changes an original donor stream')
    return {'new_original_texture_streams': len(names), 'new_original_texture_streams_byte_identical': True}


def verify_discovery_plan(directory, manifest, *, root=ROOT):
    value = read_manifest(manifest, root=root)
    directory = Path(directory)
    require(pin(directory/'client-ui-sweep-plan.json') == PLAN_PIN
        and pin(directory/SOURCE_REQUESTS) == REQUESTS_PIN,
        'UI fresh discovery does not reproduce frozen plan/requests')
    return {'status': 'fresh_discovery_reproduces_frozen_plan_and_requests',
        'plan_pin': PLAN_PIN, 'requests_pin': REQUESTS_PIN}


def bundle_contract():
    return ancestor.bundle_contract() | {'archive_pin': ARCHIVE_PIN,
        'manifest_pin': MANIFEST_PIN, 'file_count': FILE_COUNT, 'payload_bytes': PAYLOAD_BYTES,
        'files_sha256': FILES_SHA256, 'ui_sweep_file_count': UI_FILE_COUNT,
        'ui_sweep_scope': discovery.SCOPE, 'retained_immediate_visual_files': ancestor.FILE_COUNT}


def materialize(manifest, baseline_directory, output, *, root=ROOT, downloader=original.download_selected_range):
    manifest, baseline_directory, output = Path(manifest), Path(baseline_directory), Path(output)
    value = read_manifest(manifest, root=root)
    require(output.is_dir() and not output.is_symlink(), 'UI output must be an existing regular directory')
    old_archive, old_manifest = baseline_directory/ARCHIVE, baseline_directory/MANIFEST
    require(pin(old_archive) == ancestor.ARCHIVE_PIN and pin(old_manifest) == ancestor.MANIFEST_PIN,
        'UI baseline directory differs from exact public 0.13.13')
    for name in (ARCHIVE, MANIFEST):
        require(not (output/name).exists() and not (output/name).is_symlink(), 'UI output already exists')
    names = ui_files(value)
    groups = {}
    for name in sorted(names):
        record = original.selected_download_record(value, value['provenance']['entries'][name])
        key = tuple(record[k] for k in ('source_url', 'source_etag', 'source_last_modified', 'source_archive_bytes')) \
            + (record.get('source_download_content_range', record['source_content_range']),)
        groups.setdefault(key, []).append((name, record))
    with tempfile.TemporaryDirectory(prefix='.client-ui-', dir=output) as temporary:
        temporary = Path(temporary)
        def fetch(group):
            count = 0
            for name, record, stored in downloader(group):
                require(name in names and pin_bytes(stored) == {'bytes': record['stored_bytes'],
                    'sha256': record['stored_sha256']}, 'UI downloaded original stream differs')
                original.donor.decode_entry(stored, record)
                (temporary/hashlib.sha256(name.encode()).hexdigest()).write_bytes(stored)
                count += 1
            return count
        with ThreadPoolExecutor(max_workers=8) as pool:
            require(sum(pool.map(fetch, groups.items())) == len(names), 'UI selected range inventory differs')
        records = {name: value['provenance']['entries'][name] for name in names}
        target = temporary/ARCHIVE
        previous.write_extended_zip(target, old_archive, json.loads(old_manifest.read_bytes()), records, temporary)
        verified = verify(target, manifest, root=root)
        preservation = verify_preserved(target, old_archive, verified)
        (output/MANIFEST).write_bytes(manifest_bytes(manifest, root=root))
        os.link(target, output/ARCHIVE, follow_symlinks=False)
    return bundle_contract() | preservation | {'status': 'reconstructed_from_verified_selected_ranges',
        'downloaded_ranges': len(groups), 'source_archives_fully_downloaded': False,
        'source_archive_sha256_verified': False, 'original_donor_deflate_streams_reused': True}


def prepare(output, *, root=ROOT):
    output, root = Path(output), Path(root)
    assets = root/'assets'
    require(output.is_dir() and not output.is_symlink(), 'UI output must be an existing regular directory')
    verify(assets/ARCHIVE, assets/SOURCE_MANIFEST, root=root)
    for name in (ARCHIVE, MANIFEST):
        require(not (output/name).exists() and not (output/name).is_symlink(), 'UI output already exists')
    shutil.copyfile(assets/ARCHIVE, output/ARCHIVE)
    (output/MANIFEST).write_bytes(manifest_bytes(assets/SOURCE_MANIFEST, root=root))
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
            'UI materialization requires --baseline-directory and --output')
        print(json.dumps(materialize(args.manifest, args.baseline_directory, args.output), indent=2))
    elif args.verify:
        verify(args.verify, args.manifest)
        print(json.dumps(bundle_contract(), indent=2))
    elif args.output:
        print(json.dumps(prepare(args.output), indent=2))
    else:
        parser.error('Select --materialize, --verify ARCHIVE or --output')
