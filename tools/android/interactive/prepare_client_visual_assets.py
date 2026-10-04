#!/usr/bin/env python3
"""Verify/reproduce selected missing Atlas visual assets without replacing the baseline.

The reviewed ZIP reuses original verified donor DEFLATE streams. Full source
PIGGs are never downloaded or claimed authenticated; selected file sizes, zlib,
PIGG table MD5, cached headers and frozen SHA256 pins are checked independently.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import struct
import tempfile
import zipfile

import prepare_atlas_world_assets as donor

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE, MANIFEST = 'client-visual-assets.zip', 'client-visual-manifest.json'
SCOPE = 'atlas_client_missing_visual_assets'
ARCHIVE_PIN = {'bytes': 23887359, 'sha256': '2cb25dbf8a5749c6e2cf9abc4a7dab305f5b2698d6c59e460d638b9756a40809'}
MANIFEST_PIN = {'bytes': 782080, 'sha256': '6b93b50a2b4d2bf6d2b16b5827517dec20f8b666c4fb853ccd58906659945c1b'}
FILES_SHA256 = 'f47229c7d9f2474b542f761b6058299c5400df709ba892e6ca3f9b35b839028e'
FILE_COUNT, PAYLOAD_BYTES = 290, 36583648
MAX_ARCHIVE_BYTES, MAX_MANIFEST_BYTES = 64 * 1024**2, 2 * 1024**2
MAX_ENTRY_BYTES = 32 * 1024**2
SOURCE, DATA = donor.SOURCE, donor.DATA
require, pin, canonical = donor.require, donor.pin, donor.canonical


def safe_payload(name):
    if not isinstance(name, str):
        return False
    path = PurePosixPath(name)
    return (name == name.casefold() and path.as_posix() == name and name.isascii()
        and '\\' not in name and ':' not in name and all(p not in ('', '.', '..') for p in path.parts)
        and (name.startswith('data/player_library/') and path.suffix == '.geo'
             or name.startswith('data/texture_library/') and path.suffix == '.texture'))


def bundle_contract():
    return {'scope': SCOPE, 'archive': ARCHIVE, 'archive_pin': dict(ARCHIVE_PIN),
        'manifest_file': MANIFEST, 'manifest_pin': dict(MANIFEST_PIN),
        'file_count': FILE_COUNT, 'payload_bytes': PAYLOAD_BYTES, 'files_sha256': FILES_SHA256,
        'installation': 'private_client_worktree_missing_files_only',
        'imported_assets_modified': False, 'prepared_caches_modified': False,
        'existing_supplements_modified': False, 'runtime_visual_validated': False, 'gameplay_validated': False}


def read_manifest(manifest, *, root=ROOT):
    root, manifest = Path(root), Path(manifest)
    require(pin(manifest) == MANIFEST_PIN and MANIFEST_PIN['bytes'] <= MAX_MANIFEST_BYTES,
        'Client visual manifest differs from reviewed metadata')
    value = json.loads(manifest.read_text())
    files, provenance = value.get('files', {}), value.get('provenance', {})
    require(value.get('format') == 1 and value.get('scope') == SCOPE
        and value.get('source_commit') == SOURCE and value.get('data_commit') == DATA
        and value.get('archive') == {'filename': ARCHIVE, **ARCHIVE_PIN}
        and 0 < ARCHIVE_PIN['bytes'] <= MAX_ARCHIVE_BYTES and value.get('file_count') == FILE_COUNT
        and value.get('payload_bytes') == PAYLOAD_BYTES and value.get('files_sha256') == FILES_SHA256
        and isinstance(files, dict) and len(files) == FILE_COUNT
        and sum(row['bytes'] for row in files.values()) == PAYLOAD_BYTES
        and hashlib.sha256(canonical(files)).hexdigest() == FILES_SHA256
        and value.get('installation') == 'private_client_worktree_missing_files_only'
        and all(value.get(key) is False for key in ('runtime_visual_validated', 'gameplay_validated',
            'imported_assets_modified', 'prepared_caches_modified', 'existing_supplements_modified')),
        'Client visual inventory, source identity or missing-only policy differs')
    require(provenance.get('source_archives_fully_downloaded') is False
        and provenance.get('source_archive_sha256_verified') is False
        and set(provenance.get('entries', {})) == set(value.get('requests', {})) == set(files),
        'Client visual selected provenance differs')
    original = json.loads((root / 'assets/reference-inputs-manifest.json').read_text())
    baseline = {'data/' + row['path'].casefold() for row in original['files']}
    for name in ('character-avatar-defaults-manifest.json', 'atlas-world-supplement-manifest.json'):
        baseline.update(json.loads((root / 'assets' / name).read_text())['files'])
    require(not baseline.intersection(files), 'Client visual supplement would replace a preserved asset')
    for name, row in files.items():
        require(safe_payload(name) and type(row.get('bytes')) is int and 0 < row['bytes'] <= MAX_ENTRY_BYTES
            and re.fullmatch('[0-9a-f]{64}', row.get('sha256', '')), 'Unsafe client visual payload or pin')
        record = provenance['entries'][name]
        require(record.get('path', '').casefold() == name.removeprefix('data/')
            and record.get('bytes') == row['bytes'] and record.get('sha256') == row['sha256']
            and record.get('integrity') == 'exact_http_206_range_stable_etag_zlib_size_and_table_md5_passed'
            and record.get('cached_header_verified') is True
            and re.fullmatch('https://dists[.]thunderspy[.]org/piggs/[A-Za-z0-9]+[.]pigg', record.get('source_url', ''))
            and re.fullmatch('[0-9a-f]{32}', record.get('md5_table', ''))
            and re.fullmatch('[0-9a-f]{64}', record.get('stored_sha256', ''))
            and re.fullmatch('[0-9a-f]{64}', record.get('source_metadata_sha256', '')),
            'Client visual selected PIGG entry differs')
        require(isinstance(value['requests'][name], list) and value['requests'][name]
            and all(r.get('scope') in ('current_atlas_npc_geometry', 'current_atlas_npc_texture',
                'current_atlas_gui', 'atlas_composite_layer', 'current_atlas_npc_geometry_texture') for r in value['requests'][name]),
            'Client visual payload lacks bounded source request evidence')
    for name, expected in value.get('source_files', {}).items():
        relative = PurePosixPath(name)
        require(relative.as_posix() == name and '..' not in relative.parts and ':' not in name and '\\' not in name
            and (name.startswith(('upstream/i24/data/tricks/', 'upstream/ouroboros/Game/src/UI/'))
                or name in ('upstream/ouroboros/Common/seq/anim.c', 'upstream/ouroboros/Common/seq/anim.h',
                    'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/components/gridpoly.h',
                    'upstream/ouroboros/Game/src/render/thread/rt_model_cache.h',
                    'upstream/ouroboros/Game/src/entity/entclient.c',
                    'upstream/ouroboros/Game/src/entity/costume_client.c',
                    'upstream/i24/data/defs/ui/bodyparts.bp',
                    'upstream/i24/data/defs/npc/npcs_signature.nd'))
            and pin(root / name) == expected, 'Client visual native or trick source changed: ' + name)
    catalog = json.loads((root / 'assets/catalog.json').read_text())['archives']
    require([row['archive'] for row in provenance.get('metadata_archives', [])] == sorted(
        [row['name'] for row in catalog if not row['name'].casefold().startswith('sound')], key=str.casefold),
        'Client visual donor overwrite-order coverage differs')
    closure = value.get('closure', {})
    require(isinstance(closure.get('unresolved_dependencies'), list) and len(closure['unresolved_dependencies']) == 9
        and {row['target'] for row in closure['unresolved_dependencies']} == {'bf_boot_clogs', 'bm_eyes_glasses_01a',
            'bm_boot_business_shoe', 'bm_chest_bum_flannel_01a', 'emblem_hero_corp'}
        and all(row.get('source', {}).get('scope') == 'current_atlas_npc_geometry_texture'
            and row['source'].get('geometry') in files for row in closure['unresolved_dependencies'])
        and closure.get('absent_requested_models') == [
            {'geometry': 'data/player_library/male_collar.geo', 'model': 'GEO_Collar_MAGIC'}]
        and set(closure.get('requested_model_proof', {})) == {name for name in files if name.endswith('.geo')}
        and closure.get('full_global_asset_closure') is False
        and closure.get('selected_current_atlas_npc_geometry_files') == sum(name.endswith('.geo') for name in files)
        and closure.get('selected_texture_files') == sum(name.endswith('.texture') for name in files),
        'Client visual selected closure is incomplete or misrepresented')
    return value


def verify_payload(name, raw, expected, record, *, requests=None, model_proof=None):
    require(len(raw) == expected['bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256']
        and hashlib.md5(raw).hexdigest() == record['md5_table'], 'Client visual payload differs: ' + name)
    if record.get('cached_header_bytes'):
        size = record['cached_header_bytes']
        require(0 < size <= len(raw) and hashlib.sha256(raw[:size]).hexdigest() == record['cached_header_sha256'],
            'Client visual original cached header differs')
    if name.endswith('.texture'):
        hs, fs, width, height = struct.unpack_from('<IIII', raw)
        require(32 < hs <= 1056 and 0 < width <= 16384 and 0 < height <= 16384
            and len(raw) >= hs + fs and b'\0' in raw[32:hs], 'Client visual texture header or data bounds differ')
        original = raw[32:hs].split(b'\0')[0].decode('ascii')
        require(original == record['texture_header']['original_name'] and original.casefold().startswith('texture_library/')
            and PurePosixPath(original).stem.casefold() == PurePosixPath(name).stem,
            'Client visual original native texture name differs')
    else:
        # The shared inspector executes the production geoLoadStubs envelope bounds.
        import sys
        tools_path = str(ROOT / 'tools')
        if tools_path not in sys.path:
            sys.path.insert(0, tools_path)
        import inspect_piggs
        header = inspect_piggs.geometry_header(raw)
        require(header == record['geometry_header'] and header['baseline_loader_accepts_version'] is True
            and header['header_decompression_verified'] is True, 'Client visual geometry header differs')
        import client_visual_geometry
        require(requests is not None and model_proof is not None
            and client_visual_geometry.requested_model_proof(raw, requests) == model_proof,
            'Client visual requested native model table or direct material edges differ')


def verify(archive, manifest, *, root=ROOT):
    value = read_manifest(manifest, root=root)
    require(pin(archive) == ARCHIVE_PIN, 'Client visual archive differs from reviewed bytes')
    with zipfile.ZipFile(archive) as source:
        entries = source.infolist()
        require(len(entries) == len({row.filename for row in entries}) == FILE_COUNT
            and {row.filename for row in entries} == set(value['files']), 'Client visual ZIP inventory differs')
        for entry in entries:
            expected = value['files'][entry.filename]
            require(not entry.is_dir() and not entry.flag_bits & 1 and stat.S_ISREG(entry.external_attr >> 16)
                and entry.file_size == expected['bytes'] and entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                'Invalid client visual ZIP member')
            verify_payload(entry.filename, source.read(entry), expected, value['provenance']['entries'][entry.filename],
                requests=value['requests'][entry.filename], model_proof=value['closure']['requested_model_proof'].get(entry.filename))
    return value


def materialize(archive=None, manifest=None, *, root=ROOT, downloader=donor.download_range):
    assets = Path(root) / 'assets'
    archive, manifest = Path(archive or assets / ARCHIVE), Path(manifest or assets / MANIFEST)
    value = read_manifest(manifest, root=root)
    if archive.exists() or archive.is_symlink():
        verify(archive, manifest, root=root)
        return bundle_contract() | {'status': 'verified_existing_archive'}
    groups = {}
    for name, record in value['provenance']['entries'].items():
        key = tuple(record[k] for k in ('source_url', 'source_etag', 'source_last_modified',
            'source_archive_bytes', 'source_content_range'))
        groups.setdefault(key, []).append((name, record))
    with tempfile.TemporaryDirectory(prefix='.client-visual-', dir=archive.parent) as temporary:
        target, entries = Path(temporary) / ARCHIVE, []
        with ThreadPoolExecutor(max_workers=8) as pool:
            for rows in pool.map(downloader, groups.items()):
                entries.extend(rows)
        donor.write_donor_zip(target, entries)
        verify(target, manifest, root=root)
        os.link(target, archive, follow_symlinks=False)
    return bundle_contract() | {'status': 'reconstructed_from_verified_selected_ranges',
        'downloaded_ranges': len(groups), 'source_archives_fully_downloaded': False,
        'source_archive_sha256_verified': False, 'original_donor_deflate_streams_reused': True}


def prepare(output, *, root=ROOT):
    output, assets = Path(output), Path(root) / 'assets'
    require(output.is_dir() and not output.is_symlink(), 'Client visual output must be a regular directory')
    verify(assets / ARCHIVE, assets / MANIFEST, root=root)
    for name in (ARCHIVE, MANIFEST):
        require(not (output / name).exists() and not (output / name).is_symlink(), 'Client visual output already exists')
    for name in (ARCHIVE, MANIFEST):
        shutil.copyfile(assets / name, output / name)
    verify(output / ARCHIVE, output / MANIFEST, root=root)
    return bundle_contract()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--materialize', action='store_true')
    parser.add_argument('--verify', action='store_true')
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
        parser.error('Select --materialize, --verify, or --output')
