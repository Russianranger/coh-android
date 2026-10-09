#!/usr/bin/env python3
"""Verify/reproduce selected missing Atlas visual assets without replacing the baseline.

The reviewed ZIP reuses original verified donor DEFLATE streams. Full source
PIGGs are never downloaded or claimed authenticated; selected file sizes, zlib,
PIGG table MD5, cached headers and frozen SHA256 pins are checked independently.
"""
from __future__ import annotations
import argparse
import base64
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
import urllib.error
import urllib.request
import zipfile
import zlib

import prepare_atlas_world_assets as donor

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE, MANIFEST = 'client-visual-assets.zip', 'client-visual-manifest.json'
SCOPE = 'atlas_client_missing_visual_assets'
ARCHIVE_PIN = {'bytes': 515813056, 'sha256': '1ae0892bc76e44d864bfd97a59702c125693c6850e41bd63999a82e8639389ea'}
MANIFEST_PIN = {'bytes': 16272899, 'sha256': '447868d63b0eea536cba6355fe69763e3d7b24a703a756b13e0ebafb4031a34b'}
FILES_SHA256 = '99021fe01af691b88335f9d3e6fc6c16687ab12dbf652b80ff432f266f617542'
FILE_COUNT, PAYLOAD_BYTES = 5476, 873255284
BASE_ARCHIVE_PIN = {'bytes': 23887359, 'sha256': '2cb25dbf8a5749c6e2cf9abc4a7dab305f5b2698d6c59e460d638b9756a40809'}
BASE_MANIFEST_PIN = {'bytes': 782080, 'sha256': '6b93b50a2b4d2bf6d2b16b5827517dec20f8b666c4fb853ccd58906659945c1b'}
BASE_FILES_SHA256 = 'f47229c7d9f2474b542f761b6058299c5400df709ba892e6ca3f9b35b839028e'
EXTENSION_SCOPE = 'recorded_atlas_vegetation_lod_and_blood_brother_chopper_assets'
EXTENSION_FILES_SHA256 = '3b904fd8e99d0c00ec6a07b87e0dc387fcca89835920aba8332723e10b50caa2'
ENCOUNTER_SCOPE = 'recorded_atlas_post_world_npc_texture_leaves'
ENCOUNTER_FILES_SHA256 = 'd2c2ea6b9bacb7691b53944e852180698edc255c54b231d1743b8fc3ffd7e85d'
IMMEDIATE_ARCHIVE_PIN = {'bytes': 25221661, 'sha256': 'db8a831bc674df6db41ec5d7a7e75e0256d20d4ad8cd3caa097a545f96090f24'}
IMMEDIATE_MANIFEST_PIN = {'bytes': 1113867, 'sha256': '0b3ef76dad49ff018485c7cf03f5f0c1b9a9ca7bd5272043484f0913e2ce4e22'}
IMMEDIATE_FILES_SHA256 = 'f5577769ef6df22437f9eda6b0388358cd1c28013eb5fbc35aece9af0febd4f7'
# The finite 0.13.10 diagnostic/dependency sweep is stored on disk; it is not a
# preload. The installer streams each bounded leaf and retains all old bytes.
MAX_ARCHIVE_BYTES, MAX_MANIFEST_BYTES = 512 * 1024**2, 16 * 1024**2
# Repository transport encodes the reviewed plaintext manifest only. The APK
# and guest always receive its exact original bytes and retain the same pin.
SOURCE_MANIFEST_SCOPE = 'coh_client_visual_source_manifest_v1'
MAX_SOURCE_MANIFEST_BYTES, MAX_SOURCE_GZIP_BYTES = 4 * 1024**2, 3 * 1024**2
MAX_ENTRY_BYTES = 32 * 1024**2
SWEEP_SCOPE = 'recorded_client_missing_asset_dependency_closure'
SWEEP_FILE_COUNT, SWEEP_PAYLOAD_BYTES = 5147, 833734047
SWEEP_FILES_SHA256 = '7159ada9851057278f934f55c577b7063e4979d1fe2a2ce11718ded79440e8e6'
SWEEP_BASE_ARCHIVE_PIN = {'bytes': 25400546, 'sha256': 'e7caf3f505ecf9fef0efc4dbb34c1aedc2905afbe58c0ac26bbcc03f6f71ccda'}
SWEEP_BASE_MANIFEST_PIN = {'bytes': 1145658, 'sha256': '32cd85c643e2748532bf5ea4ba66d4ef843d58af07c5ebd276f99bad8e38014c'}
SWEEP_BASE_FILES_SHA256 = '07b61f301355f2bb0174db2b41f1254b3f2b80cfd660d5f467415c7f33707c09'
SWEEP_BASE_PAYLOAD_BYTES = 39521237
SOURCE, DATA = donor.SOURCE, donor.DATA
require, pin, canonical = donor.require, donor.pin, donor.canonical


def safe_payload(name):
    if not isinstance(name, str):
        return False
    path = PurePosixPath(name)
    return (name == name.casefold() and path.as_posix() == name and name.isascii()
        and '\\' not in name and ':' not in name and all(p not in ('', '.', '..') for p in path.parts)
        and (name.startswith(('data/player_library/', 'data/object_library/')) and path.suffix == '.geo'
             or name.startswith('data/texture_library/') and path.suffix == '.texture'))


def bundle_contract():
    return {'scope': SCOPE, 'archive': ARCHIVE, 'archive_pin': dict(ARCHIVE_PIN),
        'manifest_file': MANIFEST, 'manifest_pin': dict(MANIFEST_PIN),
        'file_count': FILE_COUNT, 'payload_bytes': PAYLOAD_BYTES, 'files_sha256': FILES_SHA256,
        'installation': 'private_client_worktree_missing_files_only',
        'imported_assets_modified': False, 'prepared_caches_modified': False,
        'existing_supplements_modified': False, 'runtime_visual_validated': False, 'gameplay_validated': False,
        'visual_extension_scope': EXTENSION_SCOPE, 'retained_visual_files': 290,
        'added_visual_files': 33, 'added_visual_payload_bytes': 2646051,
        'encounter_extension_scope': ENCOUNTER_SCOPE, 'retained_immediate_visual_files': 323,
        'added_encounter_texture_files': 6, 'added_encounter_payload_bytes': 291538,
        'sweep_extension_scope': SWEEP_SCOPE, 'retained_sweep_visual_files': 329,
        'added_sweep_visual_files': SWEEP_FILE_COUNT, 'added_sweep_payload_bytes': SWEEP_PAYLOAD_BYTES,
        'entire_client_preloaded': False}


def encounter_files(value):
    """Require six observed NPC texture leaves while preserving all 323 prior files."""
    extension, files = value.get('encounter_extension', {}), value.get('files', {})
    additions = extension.get('files', {})
    require(extension.get('scope') == ENCOUNTER_SCOPE and extension.get('missing_only') is True
        and extension.get('baseline_payloads_preserved') is True
        and extension.get('baseline_archive_pin') == IMMEDIATE_ARCHIVE_PIN
        and extension.get('baseline_manifest_pin') == IMMEDIATE_MANIFEST_PIN
        and extension.get('baseline_file_count') == 323 and extension.get('baseline_payload_bytes') == 39229699
        and extension.get('baseline_files_sha256') == IMMEDIATE_FILES_SHA256
        and isinstance(additions, dict) and len(additions) == extension.get('file_count') == 6
        and extension.get('payload_bytes') == 291538
        and extension.get('files_sha256') == ENCOUNTER_FILES_SHA256
        and set(additions) <= set(files)
        and all(name.startswith('data/texture_library/npcs/') and name.endswith('.texture') for name in additions)
        and {PurePosixPath(name).stem for name in additions} == {'chest_bm_labcoat_01a', 'chest_bm_labcoat_01b',
            'face_skin_bf_25asian3', 'face_skin_bf_45black1', 'chest_bm_flannel_01a', 'chest_bm_flannel_01b'}
        and extension.get('unresolved_names') == []
        and all(extension.get(key) is False for key in ('runtime_visual_validated', 'npc_identity_claimed',
            'native_renderer_changed', 'global_lod_distances_changed', 'full_global_asset_closure')),
        'Client visual exact encounter extension bounds or evidence differ')
    sweeps = set(value.get('sweep_extension', {}).get('files', {}))
    baseline = {name: row for name, row in files.items() if name not in additions and name not in sweeps}
    selected = {name: files[name] for name in sorted(additions)}
    require(len(baseline) == 323 and sum(row['bytes'] for row in baseline.values()) == 39229699
        and hashlib.sha256(canonical(baseline)).hexdigest() == IMMEDIATE_FILES_SHA256
        and sum(row['bytes'] for row in selected.values()) == 291538
        and hashlib.sha256(canonical(selected)).hexdigest() == ENCOUNTER_FILES_SHA256,
        'Client visual encounter extension changes a preserved 0.13.8 payload')
    require(extension.get('source_console') == {'bytes': 1334723,
        'sha256': 'ebec9cac51bfa68b5dcd1ec40ec0c85b74041af1b4ef7faf5cf5bd1e2eb3ed5c'}
        and all(value['requests'].get(name) == rows and rows
            and all(row.get('scope') == 'observed_atlas_post_world_npc_texture'
                and row.get('body') in ('BF', 'BM', 'BM_FAT') and row.get('bone') in ('HEAD', 'CHEST')
                and row.get('preceding_timestamp_utc', '').startswith('2026-10-04 12:1')
                and row.get('console_line', '').startswith('CUSTOM TEXTURE ERROR: ')
                for row in rows) for name, rows in additions.items()),
        'Client visual encounter extension lacks exact post-world console evidence')
    return set(additions)


def extension_files(value, *, root=ROOT):
    """The newer recipe may only append the reviewed 33 leaves to 0.13.7."""
    extension, files = value.get('visual_extension', {}), value.get('files', {})
    additions = extension.get('files', {})
    require(extension.get('scope') == EXTENSION_SCOPE and extension.get('missing_only') is True
        and extension.get('baseline_payloads_preserved') is True
        and extension.get('baseline_archive_pin') == BASE_ARCHIVE_PIN
        and extension.get('baseline_manifest_pin') == BASE_MANIFEST_PIN
        and extension.get('baseline_file_count') == 290 and extension.get('baseline_payload_bytes') == 36583648
        and extension.get('baseline_files_sha256') == BASE_FILES_SHA256
        and isinstance(additions, dict) and len(additions) == extension.get('file_count') == 33
        and extension.get('payload_bytes') == 2646051
        and extension.get('files_sha256') == EXTENSION_FILES_SHA256
        and set(additions) <= set(files)
        and all(extension.get(key) is False for key in ('runtime_visual_validated',
            'full_global_asset_closure', 'native_renderer_changed', 'global_lod_distances_changed')),
        'Client visual extension bounds or preservation policy differ')
    encounters = set(value.get('encounter_extension', {}).get('files', {})) | set(value.get('sweep_extension', {}).get('files', {}))
    baseline = {name: row for name, row in files.items() if name not in additions and name not in encounters}
    selected = {name: files[name] for name in sorted(additions)}
    require(len(baseline) == 290 and sum(row['bytes'] for row in baseline.values()) == 36583648
        and hashlib.sha256(canonical(baseline)).hexdigest() == BASE_FILES_SHA256
        and sum(row['bytes'] for row in selected.values()) == 2646051
        and hashlib.sha256(canonical(selected)).hexdigest() == EXTENSION_FILES_SHA256,
        'Client visual extension changes a preserved 0.13.7 payload')
    require(extension.get('unresolved_dependencies') == []
        and set(extension.get('requested_model_proof', {})) == {n for n in additions if n.endswith('.geo')}
        and len(extension['requested_model_proof']) == 8
        and all(row.get('absent_requested_models') == [] for row in extension['requested_model_proof'].values())
        and extension.get('hostile_identity', {}).get('display_name') == 'Blood Brother Chopper'
        and extension['hostile_identity'].get('message_id') == 'P222712670'
        and extension['hostile_identity'].get('villain_definition') == 'Hellions_Axe_Thug'
        and set(extension['hostile_identity'].get('costumes', {})) == {f'Thug_Hellion_{i:02}' for i in range(1, 7)},
        'Client visual hostile family or selected geometry closure differs')
    world = json.loads((Path(root) / 'assets/atlas-world-supplement-manifest.json').read_text())['files']
    proofs = extension.get('preserved_world_geometry_proof', {})
    require(set(proofs) == {
        'data/object_library/city_zones/praetoria/nature/bushes/praet_bushes_urban01.geo',
        'data/object_library/city_zones/praetoria/nature/trees/praet_tree_urban01.geo',
        'data/object_library/city_zones/praetoria/nature/park/praet_altaspark_tree.geo'},
        'Client visual vegetation proof broadens the reviewed Atlas geometry families')
    for name, proof in proofs.items():
        require({k: proof.get(k) for k in ('bytes', 'sha256')} == world[name]
            and proof.get('version') == 8 and isinstance(proof.get('models'), list)
            and hashlib.sha256(canonical(proof['models'])).hexdigest() == proof.get('model_table_sha256'),
            'Client visual preserved vegetation geometry or material edges differ')
    return set(additions)


def sweep_files(value, *, root=ROOT):
    """Bind the finite recorded dependency sweep to all immediate 329 leaves."""
    if SWEEP_FILE_COUNT == 0:
        require('sweep_extension' not in value, 'Unexpected sweep extension in baseline')
        return set()
    extension, files = value.get('sweep_extension', {}), value.get('files', {})
    additions = extension.get('files', {})
    require(extension.get('scope') == SWEEP_SCOPE and extension.get('missing_only') is True
        and extension.get('baseline_payloads_preserved') is True
        and extension.get('baseline_archive_pin') == SWEEP_BASE_ARCHIVE_PIN
        and extension.get('baseline_manifest_pin') == SWEEP_BASE_MANIFEST_PIN
        and extension.get('baseline_file_count') == 329
        and extension.get('baseline_payload_bytes') == SWEEP_BASE_PAYLOAD_BYTES
        and extension.get('baseline_files_sha256') == SWEEP_BASE_FILES_SHA256
        and isinstance(additions, dict) and len(additions) == extension.get('file_count') == SWEEP_FILE_COUNT
        and extension.get('payload_bytes') == SWEEP_PAYLOAD_BYTES
        and extension.get('files_sha256') == SWEEP_FILES_SHA256
        and set(additions) <= set(files)
        and all(isinstance(binding, dict) and set(binding) == {'requests_sha256'}
            and isinstance(value.get('requests', {}).get(name), list) and value['requests'][name]
            and binding['requests_sha256'] == hashlib.sha256(canonical(value['requests'][name])).hexdigest()
            for name, binding in additions.items())
        and extension.get('discovery_requests_pin') == pin(Path(root) / 'assets/client-visual-sweep-requests.json')
        and extension.get('source_console') == {'bytes': 1902345,
            'sha256': '1f532e7a18c57b5e0cb77fa7e79d9d5f85dee628b7af6aa1a63de46995c9fba2'}
        and all(extension.get(key) is False for key in ('runtime_visual_validated',
            'full_global_asset_closure', 'native_renderer_changed', 'full_archive_verified', 'preloading')),
        'Client visual recorded sweep bounds or source evidence differ')
    baseline = {name: row for name, row in files.items() if name not in additions}
    selected = {name: files[name] for name in sorted(additions)}
    require(len(baseline) == 329 and sum(row['bytes'] for row in baseline.values()) == SWEEP_BASE_PAYLOAD_BYTES
        and hashlib.sha256(canonical(baseline)).hexdigest() == SWEEP_BASE_FILES_SHA256
        and sum(row['bytes'] for row in selected.values()) == SWEEP_PAYLOAD_BYTES
        and hashlib.sha256(canonical(selected)).hexdigest() == SWEEP_FILES_SHA256,
        'Client visual sweep changes a preserved 0.13.9 payload')
    proofs = extension.get('requested_model_proof', {})
    require(isinstance(proofs, dict) and set(proofs) == {name for name in additions if name.endswith('.geo')}
        and isinstance(extension.get('unresolved_dependencies'), list),
        'Client visual sweep lacks exact model-table or unresolved dependency proof')
    return set(additions)


def verify_preserved_world_geometry(archive, value):
    """Recheck all original high/low vegetation edges against the retained donor ZIP."""
    import client_visual_geometry
    proofs = value['visual_extension']['preserved_world_geometry_proof']
    with zipfile.ZipFile(archive) as source:
        for name, proof in proofs.items():
            raw = source.read(name)
            require(len(raw) == proof['bytes'] and hashlib.sha256(raw).hexdigest() == proof['sha256']
                and client_visual_geometry.tables(raw) == (proof['version'], proof['models']),
                'Client visual vegetation material proof differs from retained Atlas bytes')


def manifest_bytes(manifest):
    """Decode source transport only, retaining the exact reviewed output pin.

    Plaintext final/runtime manifests remain accepted. A source envelope may
    contain one bounded original gzip stream; duplicate fields, extra streams,
    trailing content and over-bound expansion are rejected before publication.
    """
    require(0 < MANIFEST_PIN['bytes'] <= MAX_MANIFEST_BYTES,
        'Client visual manifest differs from reviewed metadata')
    manifest = Path(manifest)
    require(manifest.is_file() and not manifest.is_symlink(),
        'Missing or linked client visual manifest input: ' + manifest.name)
    with manifest.open('rb') as source:
        raw = source.read(MAX_MANIFEST_BYTES + 1)
    require(0 < len(raw) <= MAX_MANIFEST_BYTES,
        'Client visual manifest exceeds reviewed metadata bound')
    if {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == MANIFEST_PIN:
        return raw
    require(len(raw) <= MAX_SOURCE_MANIFEST_BYTES,
        'Client visual source manifest envelope exceeds bound')

    def unique_fields(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Client visual source manifest has duplicate fields')
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=unique_fields)
    require(isinstance(value, dict) and set(value) == {
            'format', 'scope', 'encoding', 'decoded', 'gzip', 'data'}
        and type(value['format']) is int and value['format'] == 1
        and value['scope'] == SOURCE_MANIFEST_SCOPE and value['encoding'] == 'gzip+base64'
        and value['decoded'] == MANIFEST_PIN,
        'Client visual source manifest envelope differs from reviewed metadata')
    encoded, packed_pin = value['data'], value['gzip']
    require(isinstance(encoded, str) and isinstance(packed_pin, dict)
        and set(packed_pin) == {'bytes', 'sha256'} and type(packed_pin['bytes']) is int
        and 0 < packed_pin['bytes'] <= MAX_SOURCE_GZIP_BYTES
        and isinstance(packed_pin['sha256'], str) and re.fullmatch('[0-9a-f]{64}', packed_pin['sha256'])
        and len(encoded) == 4 * ((packed_pin['bytes'] + 2) // 3),
        'Client visual source manifest encoded stream exceeds bound or differs')
    packed = base64.b64decode(encoded, validate=True)
    require({'bytes': len(packed), 'sha256': hashlib.sha256(packed).hexdigest()} == packed_pin,
        'Client visual source manifest gzip stream differs')
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        decoded = decoder.decompress(packed, MANIFEST_PIN['bytes'] + 1)
    except zlib.error as exc:
        raise ValueError('Client visual source manifest gzip stream is invalid') from exc
    require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
        and {'bytes': len(decoded), 'sha256': hashlib.sha256(decoded).hexdigest()} == MANIFEST_PIN,
        'Client visual source manifest decoded bytes differ or exceed bound')
    return decoded


def read_manifest(manifest, *, root=ROOT):
    root, manifest = Path(root), Path(manifest)
    value = json.loads(manifest_bytes(manifest))
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
    additions = extension_files(value, root=root) | encounter_files(value) | sweep_files(value, root=root)
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
                'current_atlas_gui', 'atlas_composite_layer', 'current_atlas_npc_geometry_texture',
                'observed_atlas_hostile_geometry', 'observed_atlas_hostile_texture',
                'blood_brother_chopper_costume', 'preserved_atlas_vegetation_model_material',
                'observed_atlas_hostile_geometry_material', 'atlas_vegetation_or_hostile_composite_layer',
                'observed_atlas_post_world_npc_texture',
                'observed_client_missing_texture', 'observed_client_missing_geometry',
                'observed_client_material_dependency', 'observed_player_catalog_texture',
                'observed_player_catalog_geometry', 'preserved_atlas_world_material_dependency',
                'recorded_atlas_costume_geometry', 'recorded_atlas_costume_texture',
                'recorded_client_geometry_material', 'recorded_client_composite_layer',
                'recorded_client_missing_asset_dependency')
                for r in value['requests'][name]),
            'Client visual payload lacks bounded source request evidence')
    for name, expected in value.get('source_files', {}).items():
        relative = PurePosixPath(name)
        require(relative.as_posix() == name and '..' not in relative.parts and ':' not in name and '\\' not in name
            and (name.startswith(('upstream/i24/data/tricks/', 'upstream/i24/data/defs/',
                    'upstream/i24/data/menu/costume/',
                    'upstream/i24/data/object_library/', 'upstream/ouroboros/Game/src/UI/'))
                or name in ('upstream/ouroboros/Common/seq/anim.c', 'upstream/ouroboros/Common/seq/anim.h',
                    'upstream/ouroboros/Common/seq/tricks.c', 'upstream/ouroboros/Common/seq/tricks.h',
                    'upstream/ouroboros/Common/gameData/costume_data.c',
                    'upstream/ouroboros/Common/entity/costume.c',
                    'upstream/ouroboros/Common/gameData/BodyPart.c',
                    'upstream/ouroboros/Common/gameComm/NPC.c',
                    'upstream/ouroboros/libs/UtilitiesLib/src/utils/utils.c',
                    'assets/atlas-world-supplement-manifest.json',
                    'tools/android/interactive/client_visual_geometry.py',
                    'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/components/gridpoly.h',
                    'upstream/ouroboros/Game/src/render/thread/rt_model_cache.h',
                    'upstream/ouroboros/Game/src/entity/entclient.c',
                    'upstream/ouroboros/Game/src/entity/costume_client.c',
                    'upstream/i24/data/defs/ui/bodyparts.bp',
                    'upstream/i24/data/defs/npc/npcs_signature.nd',
                    'upstream/i24/data/defs/villaincostume/thugs.nd',
                    'upstream/i24/data/defs/villains/hellions.villain',
                    'upstream/i24/data/texts/english/villains/villains.xls.ms',
                    'upstream/i24/data/object_library/city_zones/Atlas_Park_makeover/Block_Foundations/block_foundations.txt',
                    'upstream/i24/data/object_library/city_zones/Praetoria/Nature/Bushes/bushes.txt',
                    'upstream/i24/data/object_library/city_zones/Praetoria/Nature/Trees/trees.txt',
                    'upstream/ouroboros/Game/src/render/tex.c',
                    'upstream/ouroboros/Game/src/render/rendermodel.c'))
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
        and set(closure.get('requested_model_proof', {})) == {name for name in files if name.endswith('.geo') and name not in additions}
        and closure.get('full_global_asset_closure') is False
        and closure.get('selected_current_atlas_npc_geometry_files') == sum(name.endswith('.geo') for name in files if name not in additions)
        and closure.get('selected_texture_files') == sum(name.endswith('.texture') for name in files if name not in additions),
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
        actual = client_visual_geometry.requested_model_proof(raw, requests or [])
        if isinstance(model_proof, dict) and 'request_basis' in model_proof:
            actual['request_basis'] = ('exact_source_or_runtime_model_name'
                if any('model' in row for row in requests or [])
                else 'recorded_missing_filename_native_model_inventory')
        require(requests is not None and model_proof is not None
            and actual == model_proof,
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
                requests=value['requests'][entry.filename], model_proof=(
                    value['closure']['requested_model_proof'] | value['visual_extension']['requested_model_proof']
                    | value.get('sweep_extension', {}).get('requested_model_proof', {})).get(entry.filename))
    return value


def download_selected_range(group):
    """Replay frozen bounded partial responses, including their neighboring bytes."""
    key, names = group
    if not any('source_download_content_range' in row for _, row in names):
        return donor.download_range(group)
    url, etag, modified, total, range_text = key
    match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', range_text)
    require(match is not None and int(match[3]) == total, 'Invalid client visual source range')
    start, end = int(match[1]), int(match[2])
    size = end - start + 1
    require(0 <= start <= end < total <= 2 * 1024**3 and size <= donor.MAX_RANGE_BYTES,
        'Client visual partial response exceeds bound')
    proofs = {(row.get('source_download_content_range'), row.get('source_download_bytes'),
        row.get('source_download_sha256')) for _, row in names}
    require(len(proofs) == 1, 'Client visual partial response receipts differ')
    reviewed_range, reviewed_size, reviewed_sha = next(iter(proofs))
    require(reviewed_range == range_text and reviewed_size == size
        and isinstance(reviewed_sha, str) and re.fullmatch('[0-9a-f]{64}', reviewed_sha),
        'Client visual partial response receipt is invalid')
    request = urllib.request.Request(url, headers={'Range': f'bytes={start}-{end}',
        'If-Match': etag, 'User-Agent': 'coh-android-reviewed-visual-ranges/1'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                require(response.status == 206 and response.geturl() == url
                    and response.headers.get('ETag') == etag
                    and response.headers.get('Last-Modified') == modified
                    and response.headers.get('Content-Range') == range_text
                    and int(response.headers.get('Content-Length', -1)) == size,
                    'Client visual donor changed or exact partial transfer was refused')
                source = response.read(size + 1)
            break
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == 2:
                raise
    require(len(source) == size and hashlib.sha256(source).hexdigest() == reviewed_sha,
        'Client visual partial response bytes differ')
    result = []
    for name, record in names:
        offset = record['offset'] - start
        member_range = f"bytes {record['offset']}-{record['offset'] + record['stored_bytes'] - 1}/{total}"
        require(0 <= offset and record['stored_bytes'] <= len(source) - offset
            and record.get('source_member_range') == record.get('source_content_range') == member_range
            and record.get('source_download_member_bytes') == record['stored_bytes'],
            'Client visual member escaped its reviewed partial response')
        stored = source[offset:offset + record['stored_bytes']]
        donor.decode_entry(stored, record)
        result.append((name, record, stored))
    return result


def selected_download_record(value, record):
    """Expand a pinned shared response receipt without modifying manifest evidence."""
    reference = record.get('source_download_receipt')
    if reference is None:
        return record
    receipt = value.get('provenance', {}).get('sweep_downloads', {}).get(reference)
    require(isinstance(receipt, dict) and receipt.get('source_archive') == record.get('source_archive'),
        'Client visual shared partial response receipt is missing or foreign')
    return record | {'source_download_content_range': receipt.get('content_range'),
        'source_download_bytes': receipt.get('bytes'), 'source_download_sha256': receipt.get('sha256'),
        'source_download_member_bytes': record['stored_bytes']}


def materialize(archive=None, manifest=None, *, root=ROOT, downloader=download_selected_range):
    assets = Path(root) / 'assets'
    archive, manifest = Path(archive or assets / ARCHIVE), Path(manifest or assets / MANIFEST)
    value = read_manifest(manifest, root=root)
    if archive.exists() or archive.is_symlink():
        verify(archive, manifest, root=root)
        return bundle_contract() | {'status': 'verified_existing_archive'}
    groups = {}
    for name, record in value['provenance']['entries'].items():
        record = selected_download_record(value, record)
        key = tuple(record[k] for k in ('source_url', 'source_etag', 'source_last_modified',
            'source_archive_bytes')) + (record.get('source_download_content_range', record['source_content_range']),)
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
    shutil.copyfile(assets / ARCHIVE, output / ARCHIVE)
    (output / MANIFEST).write_bytes(manifest_bytes(assets / MANIFEST))
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
