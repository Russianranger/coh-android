#!/usr/bin/env python3
"""Verify exact native server caches and seed only missing private cache files.

This module never accepts templates, attributes, DB-ID maps or source inputs as
payloads. Incompatible or absent donors leave the ordinary native loader in
charge; existing device-generated cache files always take precedence.
"""
from __future__ import annotations
import hashlib
import copy
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import stat
import struct
import tempfile
import time
import zipfile

from server_message_cache_format import inspect_message_store

ROLE = 'actual_server_generated_caches'
ARCHIVE = 'server-caches.zip'
MANIFEST = 'server-cache-manifest.json'
EPOCH = 1767225600
MAX_ARCHIVE = 512 * 1024 * 1024
MAX_FILE = 256 * 1024 * 1024
MAX_TOTAL = 768 * 1024 * 1024
MAX_MANIFEST = 4 * 1024 * 1024
# Current Python operation only; no disk marker can populate this table.
_METADATA_ARCHIVE_WITNESSES = {}
MAPSERVER_SHA256 = '6a5bf60b2130c31df74f1767510de65c581652caa90f639a5a6e4a9453b47d36'
HEX64 = re.compile(r'[0-9a-f]{64}')
HEX40 = re.compile(r'[0-9a-f]{40}')
HEX32 = re.compile(r'[0-9a-f]{32}')
REQUIRED_PARSE6 = frozenset('data/server/bin/' + name + '.bin' for name in (
    'powercats', 'powersets', 'powers', 'tasksets', 'storyarc', 'contacts', 'dialog', 'spawndefs'))
REQUIRED_MESSAGES = frozenset('data/server/bin/' + name + '-en.bin' for name in (
    'messages', 'storyarcmsg', 'staticmsg'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def pin_bytes(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def file_pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Expected regular file: ' + str(path))
    digest, size = hashlib.sha256(), 0
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            size += len(block)
            digest.update(block)
    return {'bytes': size, 'sha256': digest.hexdigest()}


def compatibility_identity():
    """Cache ABI/content binding, independent of wrapper versions and ZIP bytes."""
    return {
        'format': 1,
        'source_commit': '0b75ade0c801735e10c5798f641948a45cc50488',
        'data_commit': 'd51533ec8e6a9cf726b9214968077a05fdcf19f3',
        'mapserver_sha256': MAPSERVER_SHA256,
        'asset_archive_sha256': '28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07',
        'prerequisites_manifest_sha256': '32c27465763cd08b9a210a75f0661634143f39fbe02d4bdaec43c819715a3c1f',
        'schema_manifest_sha256': 'b89136892e69ceb39db640613d3f8a34abf2ef8e75e947f4034728b935938b92',
        'world_manifest_sha256': '204a7f0da20cdbbb4ea8b8e2d9e9b5ebccfaa10d5213fff03bbb85cc7f9e3c86',
        'world_archive_sha256': 'c7ed82aaaf987410fa471e19ee2b19115ef660892a06f79e2e2401d5672b095f',
        'avatar_manifest_sha256': '2a96ff8fb24b686502d62e1e1ed25453681d4c15389c59b1f35ce3fbf1a5feb7',
        'avatar_archive_sha256': '03f980c983702c2c9d21b0f674903e151129d0554b25d800b8724036f2cb4a29',
        'normalized_mtime_epoch': EPOCH,
        'parser_contract': 'MapServer-Win32-Parse6-serveronly-MessageStore20090521-English',
    }


def regular_directory(path):
    path = Path(path)
    require(path.is_dir() and not path.is_symlink(), 'Expected private real directory: ' + str(path))
    return path


def private_ancestors(root, path, allow_missing=False):
    root = regular_directory(root)
    owner = root.lstat().st_uid
    current = root
    parts = Path(path).relative_to(root).parts
    require(all(part not in ('', '.', '..') for part in parts), 'Unsafe private cache ancestry')
    for part in parts:
        current /= part
        if not os.path.lexists(current):
            require(allow_missing, 'Private cache ancestor disappeared')
            return owner
        info = current.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == owner,
                'Linked or foreign private cache ancestor')
    return owner


def private_regular(path, owner):
    info = Path(path).lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == owner,
            'Linked or foreign private cache leaf')
    return info


def identifier_snapshot(runtime_data):
    """Hash the bounded identity-bearing leaves, not the bulk immutable tree."""
    runtime_data = regular_directory(runtime_data)
    result = {}
    for relative in ('defs', 'defs/dbidmaps', 'server/db/templates'):
        directory = runtime_data / relative
        if not directory.exists():
            continue
        owner = private_ancestors(runtime_data, directory)
        for path in sorted(directory.iterdir()):
            if path.suffix.casefold() not in ('.dbidmap', '.attribute'):
                continue
            info = private_regular(path, owner)
            require(0 < info.st_size <= 8 * 1024 * 1024, 'Identifier input exceeds bound')
            name = 'data/' + path.relative_to(runtime_data).as_posix()
            require(name.casefold() not in {key.casefold() for key in result}, 'Case-conflicting identifiers')
            result[name] = file_pin(path)
    require(0 < len(result) <= 128, 'Missing or oversized identifier input closure')
    return dict(sorted(result.items()))



def portable_metadata_provider(receipt, package, required_geometry):
    """Content recipe only; path, import generation and uid/inode stay local."""
    import native_startup_metadata_contract as metadata
    import client_startup_diagnostic as client
    imported = receipt.get('import')
    require(type(imported) is dict and set(imported) == {'generation', 'receipt_sha256',
        'contract_sha256', 'file_count', 'total_bytes'}
        and HEX64.fullmatch(str(imported['contract_sha256']))
        and type(imported['file_count']) is int and imported['file_count'] == client.DATA_COUNT
        and type(imported['total_bytes']) is int and imported['total_bytes'] == client.DATA_BYTES,
        'Authenticated original import content recipe required')
    require(package.get('source_commit') == client.SOURCE and package.get('data_commit') == client.DATA,
        'Metadata cache source/data recipe differs')
    for key in ('cache_archive_sha256', 'prerequisites_archive_sha256', 'prerequisites_manifest_sha256'):
        require(type(receipt.get(key)) is str and HEX64.fullmatch(receipt[key]), 'Typed prepared client recipe pin required')
    require(type(receipt.get('normalized_mtime_epoch')) is int
        and receipt['normalized_mtime_epoch'] == EPOCH, 'Metadata cache normalized source epoch differs')
    projection = metadata.map_texture_projection(package)
    # The same server source projection must have the same provider identity
    # across consumers. Current execution is bound independently, never omitted.
    projection = {key: projection[key] for key in ('policy', 'excluded_top_level_directories',
        'native_source_path', 'native_source_sha256', 'retained_texture_exclusion_source_sha256', 'client_inputs_modified')}
    return {'format': 1, 'role': 'portable_authenticated_server_provider_recipe',
        'source_commit': client.SOURCE, 'data_commit': client.DATA,
        'import': {key: imported[key] for key in ('contract_sha256', 'file_count', 'total_bytes')},
        'asset_archive_sha256': client.ASSET_ARCHIVE_SHA,
        'client_cache_archive_sha256': receipt['cache_archive_sha256'],
        'prerequisites_archive_sha256': receipt['prerequisites_archive_sha256'],
        'prerequisites_manifest_sha256': receipt['prerequisites_manifest_sha256'],
        'normalized_mtime_epoch': EPOCH,
        'server_source_compatibility': compatibility_identity(),
        'required_geometry': copy.deepcopy(required_geometry), 'server_input_projection': projection}


def _metadata_owned_snapshot(path, *, directory=False):
    """A local ownership witness; never part of a portable source identity."""
    import atlas_world_assets as world
    path = Path(path)
    require(path.is_absolute() and not any(parent.is_symlink() for parent in (path, *path.parents)),
        'Nonlinked absolute metadata provider ancestry required')
    info = path.lstat()
    require(info.st_uid == os.getuid() and (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
        and (directory or info.st_nlink == 1 or not info.st_mode & 0o222),
        'Metadata provider source owner/type differs')
    return world.fingerprint(info)


@contextmanager
def _metadata_authenticated_archive(path, expected, *, context=None, observations=None):
    """Hash once through a held no-follow fd; use the same fd for ZIP reads."""
    import atlas_world_assets as world
    import native_startup_metadata_contract as metadata
    import client_startup_diagnostic as client
    expected = metadata.pin_record(expected, MAX_ARCHIVE)
    path = Path(path); before = _metadata_owned_snapshot(path)
    require(before[2] == expected['bytes'], 'Metadata cache archive extent differs')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    opened_at = time.monotonic()
    try:
        require(world.fingerprint(os.fstat(descriptor)) == before, 'Cache archive changed before reading')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            # Reuse a full hash only from this same guest operation and only
            # while both the held fd and precise no-follow inode state match.
            reused = client.verified_asset_matches(path, expected)
            hashed = 0
            if not reused:
                digest = hashlib.sha256()
                for block in iter(lambda: stream.read(1024*1024), b''):
                    if context is not None: context.check()
                    hashed += len(block); digest.update(block)
                require(digest.hexdigest() == expected['sha256'], 'Actual metadata cache archive SHA differs')
                require(world.fingerprint(os.fstat(descriptor)) == before
                    and _metadata_owned_snapshot(path) == before, 'Archive changed during full hashing')
                client._VERIFIED_ASSET_STATES[str(path)] = (copy.deepcopy(expected), client.asset_fingerprint(path))
            observation = {'archive': path.name, 'archive_bytes': expected['bytes'],
                'payload_bytes_hashed': hashed, 'same_operation_full_hash_reused': reused,
                'authentication_elapsed_seconds': round(time.monotonic()-opened_at, 6),
                'decompressed_member_bytes_read': 0, 'member_reads': {}}
            if observations is not None: observations.append(observation)
            stream.seek(0)
            with zipfile.ZipFile(stream) as archive:
                original_read = archive.read
                def measured_read(name, *args, **kwargs):
                    body = original_read(name, *args, **kwargs)
                    leaf = name.filename if isinstance(name, zipfile.ZipInfo) else name
                    row = observation['member_reads'].setdefault(leaf, {'reads': 0, 'bytes': 0})
                    row['reads'] += 1; row['bytes'] += len(body)
                    observation['decompressed_member_bytes_read'] += len(body)
                    return body
                archive.read = measured_read
                yield archive
            require(world.fingerprint(os.fstat(descriptor)) == before
                and _metadata_owned_snapshot(path) == before, 'Metadata cache archive changed during validation')
    finally:
        os.close(descriptor)



def _metadata_original_server_manifest(archive, raw):
    """Validate metadata from an exact authenticated original ZIP/manifest.

    Frozen whole ZIP and manifest crypto pins already prove payload content.
    This path neither decodes bodies nor relabels their historical native proof.
    """
    manifest = json.loads(raw, object_pairs_hook=unique_object)
    names = archive.namelist(); files = manifest.get('files'); identity = manifest.get('identity')
    require(type(manifest.get('format')) is int and manifest['format'] == 1 and manifest.get('role') == ROLE
        and HEX40.fullmatch(str(manifest.get('repository_commit')))
        and type(identity) is dict and set(identity) == set(compatibility_identity()) | {'identifier_files'}
        and {key: identity[key] for key in compatibility_identity()} == compatibility_identity(),
        'Original server source/native donor identity differs')
    identifiers = identity['identifier_files']
    require(type(identifiers) is dict and 0 < len(identifiers) <= 128, 'Original identifier input closure differs')
    for name, row in identifiers.items():
        require(type(name) is str and name.startswith(('data/defs/', 'data/server/db/templates/'))
            and name.endswith(('.dbidmap', '.attribute')) and ':' not in name and '\\' not in name
            and all(part not in ('', '.', '..') for part in name.split('/'))
            and type(row) is dict and set(row) == {'bytes', 'sha256'} and type(row['bytes']) is int
            and 0 < row['bytes'] <= 8*1024**2 and HEX64.fullmatch(str(row['sha256'])),
            'Original identifier input pin differs')
    require(type(files) is dict and files and set(files) | {MANIFEST} == set(names)
        and REQUIRED_PARSE6 | REQUIRED_MESSAGES <= {name.casefold() for name in files},
        'Original server BIN donor coverage differs')
    validate_native_receipt(manifest.get('native_generation'), False, files)
    validate_native_receipt(manifest.get('native_consumption'), True, files)
    require(manifest.get('native_client_or_server_recompiled') is False
        and manifest.get('generated_noncache_outputs') == []
        and manifest.get('android_execution_validated') is False
        and manifest.get('physical_gameplay_validated') is False, 'Original server cache scope differs')
    total = 0
    for name, row in files.items():
        require(safe_cache(name) and type(row) is dict, 'Original server BIN donor path differs')
        entry = archive.getinfo(name); total += entry.file_size
        require(not entry.is_dir() and not entry.flag_bits & 1 and stat.S_IFMT(entry.external_attr >> 16) in (0, stat.S_IFREG)
            and type(row.get('bytes')) is int and 0 < row['bytes'] <= MAX_FILE
            and entry.file_size == row['bytes'] and HEX64.fullmatch(str(row.get('sha256')))
            and row.get('kind') in ('Parse6', 'MessageStore20090521') and type(row.get('structure')) is dict
            and total <= MAX_TOTAL, 'Original server BIN extent/schema record differs')
    return manifest


def construct_native_metadata_context(mapserver_package, mapserver_path, *, assets, worktree,
        game_data, receipt, required_geometry=None, context=None):
    """Construct the real common-path bridge from actual owned provider facts.

    Exact source-frozen qualification rows authorize particular BINs only.
    Geobin/collision caches are separate. Unknown inputs fail before checkout;
    callers preserve the current native generation and ordinary loader fallback.
    """
    import native_startup_metadata_contract as metadata
    import client_startup_diagnostic as client
    import atlas_world_assets as world
    started = time.monotonic()
    assets, worktree, game_data = map(Path, (assets, worktree, game_data))
    admitted = metadata.runtime_admission(mapserver_package, 'mapserver', mapserver_path)
    recipe = admitted['receipt']['compatibility'].get('runtime_cache_context')
    require(type(recipe) is dict and set(recipe) == {'policy', 'portable_provider', 'archives',
        'eligible_bins', 'qualified_per_bin', 'derived_native_proof', 'source_compatibility_review'}
        and recipe['policy'] == 'authenticated_immutable_provider_and_original_cache_v1',
        'Exact runtime provider/cache context recipe is not frozen')
    roots = (worktree, worktree/'data', game_data)
    before = {str(path): _metadata_owned_snapshot(path, directory=True) for path in roots}
    work_receipt = worktree/'client-work.json'
    work_raw = world.read_regular(work_receipt, 1024*1024)
    saved = json.loads(work_raw, object_pairs_hook=unique_object)
    require(metadata.same(client.worktree_data_identity(saved), client.worktree_data_identity(receipt))
        and saved.get('content_identity_sha256') == receipt.get('content_identity_sha256')
        and type(saved.get('format')) is int and saved['format'] == 1
        and Path(saved['source_data']) == game_data,
        'Current provider does not match the authenticated prepared worktree receipt')
    imported = client.import_identity(game_data)
    require(metadata.same(imported, saved['import']), 'Current immutable import identity changed')
    archive_observations = []
    prerequisites_path = assets/'client-prerequisites.zip'
    prerequisite_size = prerequisites_path.lstat().st_size
    require(0 < prerequisite_size <= 512*1024, 'Bounded original client prerequisite archive required')
    with _metadata_authenticated_archive(prerequisites_path, {'bytes': prerequisite_size,
            'sha256': saved['prerequisites_archive_sha256']}, context=context, observations=archive_observations) as archive:
        _, manifest_sha = client.prerequisites_manifest(archive)
        require(manifest_sha == saved['prerequisites_manifest_sha256'],
            'Actual source prerequisite manifest differs from prepared worktree recipe')
    portable = portable_metadata_provider(saved, mapserver_package, required_geometry)
    require(metadata.same(portable, recipe['portable_provider']), 'Actual portable provider recipe differs')
    provider_completed_at = time.monotonic()
    archives = recipe['archives']; eligible = recipe['eligible_bins']
    require(type(archives) is dict and archives and set(archives) <= {'client-caches.zip', 'server-caches.zip'}
        and type(eligible) is dict and 0 < len(eligible) <= 512
        and type(recipe['qualified_per_bin']) is dict and set(eligible) == set(recipe['qualified_per_bin'])
        and all(type(name) is str for name in eligible)
        and len({name.casefold() for name in eligible}) == len(eligible),
        'Exact bounded original cache origins and eligible BIN inventory required')
    # No bin/ and data/bin/ spelling can identify the same logical leaf twice.
    names = [name if name.startswith('data/') else 'data/'+name for name in eligible]
    require(len({name.casefold() for name in names}) == len(names), 'Aliased eligible cache directories refused')
    import native_map_startup_contract as startup
    derivation = startup.inspect_runtime_cache_derivation(recipe['derived_native_proof'])
    proof_source = derivation['output']
    for key, filename in (('client_cache_manifest', 'client-caches.zip'), ('server_cache_manifest', 'server-caches.zip')):
        donor = derivation['raw_inputs'][key]
        require(filename in archives and metadata.same(donor['component_zip'], archives[filename]['archive'])
            and metadata.same(donor['member_pin'], archives[filename]['manifest']),
            'Derived proof names another original public donor component or manifest')
    proof_raw = world.read_regular(assets/proof_source['filename'], 8*1024**2, allow_shared_source=True)
    require(pin_bytes(proof_raw) == proof_source['pin'], 'Current native cache proof bytes differ')
    fresh = json.loads(proof_raw, object_pairs_hook=unique_object)
    require(type(fresh) is dict and type(fresh.get('format')) is int and fresh['format'] == 1
        and fresh.get('role') == 'native_metadata_cache_consumer_parity'
        and metadata.same(fresh.get('derivation'), startup.runtime_cache_derivation_statement(derivation))
        and fresh.get('previous_shipping_consumer_sha256') == admitted['previous_consumer_sha256']
        and fresh.get('current_consumer_sha256') == admitted['current_consumer_sha256']
        and fresh.get('native_ID_tables_observed') is False
        and type(fresh.get('observed_native_bin_paths')) is list
        and fresh['observed_native_bin_paths'] == sorted(eligible)
        and metadata.same(fresh.get('qualified_per_bin'), recipe['qualified_per_bin']),
        'Fresh exact native schema/output/identifier-input/ordered-loader facts missing')
    controls = fresh.get('actual_tested_control_consumers')
    require(type(controls) is list and 0 < len(controls) <= 8
        and all(type(row) is dict for row in controls), 'Actual tested control consumer pins required')
    for row in controls: metadata.pin_record(row, 64*1024**2)
    candidate = metadata.native_record_pin(admitted['receipt']['native_record'])
    require(len({row['sha256'] for row in controls}) == len(controls)
        and candidate['sha256'] not in {row['sha256'] for row in controls}
        and metadata.same(fresh.get('actual_tested_candidate'), candidate),
        'Actual tested control/candidate provenance differs')
    import native_map_startup_contract as startup
    source_descriptor = recipe['source_compatibility_review']
    require(metadata.same(fresh.get('source_compatibility_review'), source_descriptor),
        'Native proof names another committed source-only review')
    source_review = startup.inspect_committed_source_review(source_descriptor,
        previous_shipping_consumer_sha256=admitted['previous_consumer_sha256'],
        actual_tested_control_consumers=controls, actual_tested_candidate=candidate)
    proof_completed_at = time.monotonic()
    records, schemas, historical = {}, {}, {}
    verified_server_witness = None
    asset_manifest_raw = world.read_regular(assets/'asset-pack-manifest.json', 8*1024**2, allow_shared_source=True)
    asset_manifest = json.loads(asset_manifest_raw, object_pairs_hook=unique_object)
    require(type(asset_manifest.get('format')) is int and asset_manifest['format'] == 1
        and asset_manifest.get('version') == '1.0.0' and type(asset_manifest.get('files')) is dict,
        'Original authenticated Assets 1.0.0 inventory required')
    for filename, archive_recipe in sorted(archives.items()):
        require(type(archive_recipe) is dict and set(archive_recipe) == {'archive', 'manifest'},
            'Exact archive and original manifest pins required')
        require(metadata.same(asset_manifest['files'].get('runtime/'+filename), archive_recipe['archive']),
            'Cache archive is absent from original Assets 1.0.0 inventory')
        manifest_name = 'client-cache-manifest.json' if filename == 'client-caches.zip' else MANIFEST
        with _metadata_authenticated_archive(assets/filename, archive_recipe['archive'],
                context=context, observations=archive_observations) as archive:
            infos = archive.infolist()
            require(1 < len(infos) <= 1025 and len(infos) == len({entry.filename.casefold() for entry in infos}),
                'Aliased original cache ZIP inventory refused')
            require(manifest_name in archive.namelist() and 0 < archive.getinfo(manifest_name).file_size <= MAX_MANIFEST,
                'Bounded original cache manifest leaf required')
            original_raw = archive.read(manifest_name)
            require(pin_bytes(original_raw) == metadata.pin_record(archive_recipe['manifest'], MAX_MANIFEST),
                'Original cache source/native producer manifest bytes differ')
            if filename == 'client-caches.zip':
                manifest = client.cache_manifest(archive)
                require(archive_recipe['archive']['sha256'] == saved['cache_archive_sha256'],
                    'Prepared worktree was generated from another client cache archive')
                historical[filename] = {key: manifest[key] for key in ('format', 'role', 'source_commit',
                    'data_commit', 'executable_sha256', 'asset_archive_sha256', 'reference_run_id',
                    'prerequisites_manifest_sha256', 'normalized_mtime_epoch')}
            else:
                manifest = _metadata_original_server_manifest(archive, original_raw)
                verified_server_witness = {'path': str(assets/filename), 'pin': copy.deepcopy(archive_recipe['archive']),
                    'manifest_pin': copy.deepcopy(archive_recipe['manifest']), 'manifest': copy.deepcopy(manifest),
                    'fingerprint': _metadata_owned_snapshot(assets/filename)}
                historical[filename] = {key: manifest[key] for key in ('identity', 'native_generation', 'native_consumption')}
            for logical, origin in eligible.items():
                require(type(logical) is str and re.fullmatch(r'(?:bin|data/bin|data/server/bin)/[A-Za-z0-9_-]+\.bin', logical)
                    and type(origin) is dict and set(origin) == {'archive', 'member'}
                    and origin['archive'] in archives and origin['member'] == (logical if logical.startswith('data/') else 'data/'+logical),
                    'Unreviewed or aliased original BIN origin refused')
                if origin['archive'] != filename: continue
                name = origin['member']; row = manifest['files'].get(name)
                require(type(row) is dict and name in archive.namelist(), 'Eligible BIN absent from original authenticated donor')
                info = archive.getinfo(name)
                require(not info.is_dir() and not info.flag_bits & 1 and stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG)
                    and info.file_size == row['bytes'] and 0 < row['bytes'] <= MAX_FILE,
                    'Original eligible BIN payload extent/type differs')
                # Exact authenticated original manifest records already name
                # these payload/schema facts. No BIN body needs rediscovery.
                actual = {key: row[key] for key in ('bytes', 'sha256')}
                kind = row.get('kind', 'Parse6')
                schema = metadata.canonical_sha({'kind': kind, 'original_manifest_record': row})
                qualified = recipe['qualified_per_bin'][logical]
                require(qualified['output_sha256'] == actual['sha256']
                    and qualified['schema_identity_sha256'] == schema,
                    'Fresh native parity refers to another original BIN output/schema record')
                # Current mutable bodies are deliberately unobserved here.
                # Existing generation owner checks and the unchanged native
                # schema/freshness loader continue deciding whether to use them.
                records[logical] = actual; schemas[logical] = {'kind': kind, 'schema_identity_sha256': schema}
    originals_completed_at = time.monotonic()
    require(set(records) == set(eligible), 'Incomplete original eligible BIN coverage')
    recipe_identity = {'format': 1, 'role': 'exact_original_bin_source_and_schema_recipe',
        'portable_provider': portable, 'archives': archives, 'eligible_origins': eligible,
        'output_pins': records, 'schemas': schemas}
    result = {'provider_identity_sha256': metadata.canonical_sha(portable),
        'bin_recipe_identity_sha256': metadata.canonical_sha(recipe_identity),
        'original_proof_sha256': metadata.canonical_sha(historical),
        'qualified_per_bin': copy.deepcopy(recipe['qualified_per_bin'])}
    import native_map_startup_contract as startup
    startup.verify_metadata_cache_context(mapserver_path, mapserver_package, result)
    require(all(_metadata_owned_snapshot(path, directory=True) == before[str(path)] for path in roots)
        and world.read_regular(work_receipt, 1024*1024) == work_raw
        and metadata.same(client.import_identity(game_data), imported),
        'Immutable provider ownership/receipt changed during cache bridge validation')
    if verified_server_witness is not None:
        _METADATA_ARCHIVE_WITNESSES[verified_server_witness['path']] = verified_server_witness
    return {'context': result, 'evidence': {'status': 'actual_owned_provider_and_original_donor_records_authenticated',
        'construction_elapsed_seconds': round(time.monotonic()-started, 6),
        'construction_phase_seconds': {
            'admission_provider_and_prerequisites': round(provider_completed_at-started, 6),
            'derived_proof_and_source_review': round(proof_completed_at-provider_completed_at, 6),
            'original_archives_and_manifest_records': round(originals_completed_at-proof_completed_at, 6),
            'final_context_and_owner_checks': round(time.monotonic()-originals_completed_at, 6)},
        'derived_proof_bytes_read': len(proof_raw), 'provider_receipt_bytes_read': 2*len(work_raw),
        'original_asset_manifest_bytes_read': len(asset_manifest_raw),
        'archive_payload_bytes_hashed': sum(row['payload_bytes_hashed'] for row in archive_observations),
        'archive_observations': archive_observations, 'original_bin_body_bytes_read': 0,
        'current_private_bin_body_bytes_read': 0,
        'decompressed_original_archive_member_bytes_read': sum(row['decompressed_member_bytes_read'] for row in archive_observations),
        'original_manifest_unique_bytes': sum(row['manifest']['bytes'] for row in archives.values()),
        'original_manifest_bytes_read_including_repeated_validation': sum(
            read['bytes'] for row in archive_observations for name, read in row['member_reads'].items()
            if name in ('client-cache-manifest.json', MANIFEST)),
        'eligible_original_bin_bytes_authenticated_by_exact_archive_and_manifest': sum(row['bytes'] for row in records.values()),
        'provider_identity_sha256': result['provider_identity_sha256'],
        'bin_recipe_identity_sha256': result['bin_recipe_identity_sha256'],
        'original_proof_sha256': result['original_proof_sha256'],
        'eligible_bin_paths': sorted(eligible), 'authenticated_original_bin_count': len(records),
        'native_consumption_scope': 'only_exact_authority_selected_observed_bin_operation_names',
        'unselected_original_inventory_claimed_freshly_consumed': False,
        'archive_names': sorted(archives), 'current_consumer_sha256': admitted['current_consumer_sha256'],
        'previous_shipping_consumer_sha256': admitted['previous_consumer_sha256'],
        'actual_tested_control_consumers': copy.deepcopy(controls), 'actual_tested_candidate': candidate,
        'committed_source_compatibility_review': source_review,
        'runtime_cache_proof_derivation': derivation,
        'local_owner_fingerprints': before,
        'current_private_cache_body_evidence': 'unknown_ordinary_native_schema_and_freshness_fallback',
        'current_private_or_device_generated_bin_body_equality_claimed': False,
        'portable_identity_excludes_path_generation_owner': True,
        'identifier_inputs_and_loader_decisions_basis': 'exact_authenticated_native_qualification_receipt_and_unchanged_decoder_source_closure',
        'native_ID_tables_observed': False,
        'behavioral_collision_validated': False, 'physical_timing_validated': False}}


def verify_mapserver_compatibility(mapserver_path, mapserver_package=None, *, metadata_cache_context=None):
    import native_startup_metadata_contract as metadata
    if isinstance(mapserver_package, dict) and metadata.WRAPPER in mapserver_package:
        import native_map_startup_contract as startup
        current = startup.verify_current_map(mapserver_path, mapserver_package)
        cache = startup.verify_metadata_cache_context(mapserver_path, mapserver_package, metadata_cache_context)
        receipt = startup.embedded_receipt(mapserver_package)
        require(current['original_cache_donor_mapserver_sha256'] == MAPSERVER_SHA256,
            'Metadata component altered original cache donor history')
        return dict(current, cache_donor_identity_preserved=True,
            cache_compatibility=cache, retained_schema_sources_sha256=receipt['schema_sources_sha256'])
    actual = file_pin(mapserver_path)['sha256']
    proof = {'format': 1, 'actual_mapserver_sha256': actual,
        'original_cache_donor_mapserver_sha256': MAPSERVER_SHA256,
        'cache_donor_identity_preserved': True, 'physical_loading_gain_validated': False}
    if actual == MAPSERVER_SHA256:
        return dict(proof, policy='exact_original_cache_producer')
    if isinstance(mapserver_package, dict) and 'native_map_startup' in mapserver_package:
        import native_map_startup_contract as startup
        result = startup.verify_current_map(mapserver_path, mapserver_package)
        require(result['original_cache_donor_mapserver_sha256'] == MAPSERVER_SHA256,
                'Map startup altered the original cache donor history')
        return dict(result, retained_schema_sources_sha256=startup.embedded_receipt(mapserver_package)['schema_sources_sha256'])
    import native_monorail_contract
    require(isinstance(mapserver_package, dict), 'Server-cache executable identity differs')
    receipt = native_monorail_contract.embedded_receipt(mapserver_package)
    require(receipt['mapserver']['sha256'] == actual
            and receipt['previous_mapserver']['sha256'] == MAPSERVER_SHA256,
            'Server-cache bridge changed parser/source ancestry')
    return dict(proof, policy='qualified_monorail_overlay_preserves_Parse6_and_source_definitions',
        native_build_repository_commit=receipt['native_build_repository_commit'],
        native_build_manifest=receipt['native_build_manifest'],
        monorail_receipt_sha256=mapserver_package['native_monorail']['receipt_sha256'],
        retained_schema_sources_sha256=receipt['schema_sources_sha256'],
        changed_source_sha256=receipt['build_input']['patched_sha256'],
        parser_or_definition_sources_changed=False)


def build_expected_identity(runtime_data, mapserver_path, *, mapserver_package=None, metadata_cache_context=None):
    verify_mapserver_compatibility(mapserver_path, mapserver_package,
        metadata_cache_context=metadata_cache_context)
    # Compatibility preserves the ORIGINAL donor identity. The new executable
    # has its own separate source/ABI receipt, never rewritten donor history.
    return {**compatibility_identity(), 'identifier_files': identifier_snapshot(runtime_data)}


def safe_cache(name):
    return (isinstance(name, str) and name.isascii() and name.startswith('data/server/bin/')
            and name.count('/') == 3 and name.lower().endswith('.bin')
            and all(part not in ('', '.', '..') for part in name.split('/'))
            and '\\' not in name and ':' not in name and '\x00' not in name)


def inspect_parse6(data):
    """Strict Parse6/Files1 envelope and normalized dependency closure bounds.

    Field-level semantics are separately established by the native consumption
    receipt. This verifier does not mislabel an outer envelope as schema decode.
    """
    require(isinstance(data, bytes) and 24 <= len(data) <= MAX_FILE and data[:8] == b'CrypticS',
            'Invalid Parse6 header or size')
    position = 12

    def integer():
        nonlocal position
        require(position + 4 <= len(data), 'Truncated Parse6 integer')
        value = struct.unpack_from('<I', data, position)[0]
        position += 4
        return value

    def string(limit):
        nonlocal position
        require(position + 2 <= len(data), 'Truncated Parse6 string length')
        size = struct.unpack_from('<H', data, position)[0]
        require(size <= limit, 'Oversized Parse6 string')
        end = position + ((size + 2 + 3) & ~3)
        require(end <= len(data), 'Truncated Parse6 string')
        value = data[position + 2:position + 2 + size]
        require(data[position + 2 + size:end] == b'\x00' * (end - position - 2 - size),
                'Nonzero Parse6 string padding')
        position = end
        return value

    require(string(16) == b'Parse6' and string(16) == b'Files1', 'Unexpected Parse6 signature')
    block_bytes = integer()
    block_end = position + block_bytes
    require(4 <= block_bytes <= 32 * 1024 * 1024 and block_end <= len(data),
            'Invalid Parse6 dependency block')
    count = integer()
    require(count <= block_bytes // 8, 'Invalid Parse6 dependency count')
    dependencies = []
    names = set()
    for unused in range(count):
        raw = string(1024)
        require(raw and b'\x00' not in raw, 'Empty or nul-containing dependency')
        name = raw.decode('utf-8', errors='strict').replace('\\', '/')
        require(not name.startswith('/') and ':' not in name
                and all(part not in ('', '.', '..') for part in name.split('/')), 'Unsafe dependency path')
        require(name.casefold() not in names, 'Duplicate Parse6 dependency')
        names.add(name.casefold())
        timestamp = integer()
        require(timestamp in (0, EPOCH - 3600, EPOCH, EPOCH + 3600),
                'Cache dependency date is not normalized: ' + name)
        require(position <= block_end, 'Dependency exceeds declared block')
        dependencies.append({'path': name, 'timestamp': timestamp})
    require(position == block_end, 'Parse6 dependency block length differs')
    body_bytes = integer()
    require(body_bytes >= 4 and position + body_bytes == len(data), 'Parse6 body length differs')
    # This integer is ParserReadBinaryTable's root length, not an additional
    # container around another root header. Native consumption checks fields.
    return {'format': 'Parse6', 'schema_crc': f'{struct.unpack_from("<I", data, 8)[0]:08x}',
            'dependency_count': count, 'dependency_sha256': hashlib.sha256(canonical(dependencies)).hexdigest(),
            'body_bytes': body_bytes, 'dependencies': dependencies}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate manifest key')
        result[key] = value
    return result


def inspect_payload(data, kind):
    if kind == 'Parse6':
        return {key: value for key, value in inspect_parse6(data).items() if key != 'dependencies'}
    require(kind == 'MessageStore20090521', 'Unknown server cache format')
    return inspect_message_store(data)


def validate_native_receipt(receipt, consumption, files):
    require(isinstance(receipt, dict) and receipt.get('format') == 1
            and receipt.get('stage') == ('consumption' if consumption else 'generation')
            and HEX32.fullmatch(str(receipt.get('session_id', '')))
            and type(receipt.get('mapserver_pid')) is int and 0 < receipt['mapserver_pid'] < 2**32
            and receipt.get('mapserver_sha256') == MAPSERVER_SHA256
            and receipt.get('native_exit_code') == 0 and receipt.get('launcher_exit_code') == 0
            and all(receipt.get(key) is True for key in ('completed_preload', 'console_owned',
                        'escape_sent', 'identifier_files_unchanged'))
            and receipt.get('timed_out') is False
            and receipt.get('native_errors', {}).get('status') == 'no_native_data_errors',
            'Incomplete native server cache completion/error receipt')
    if consumption:
        require(receipt.get('cache_writes') == [] and receipt.get('source_content_reads') == [],
                'Native consumption rebuilt/read source definitions')
        reads = receipt.get('cache_content_reads')
        require(isinstance(reads, dict) and set(reads) == set(files)
                and all(type(value) is int and value > 0 for value in reads.values()),
                'Native consumption did not read every selected cache')
        require(receipt.get('cache_files_unchanged') is True
                and HEX64.fullmatch(str(receipt.get('trace_receipt_sha256', ''))),
                'Native cache-consumption trace or byte stability missing')


def verify_archive(path, expected_identity=None):
    path = Path(path)
    witness = _METADATA_ARCHIVE_WITNESSES.get(str(path))
    if witness is not None:
        import client_startup_diagnostic as client
        if (client.verified_asset_matches(path, witness['pin'])
                and _metadata_owned_snapshot(path) == witness['fingerprint']):
            manifest = witness['manifest']
            require(expected_identity is None or manifest['identity'] == expected_identity,
                'Server donor/runtime inputs differ')
            return copy.deepcopy(manifest)
        _METADATA_ARCHIVE_WITNESSES.pop(str(path), None)
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= MAX_ARCHIVE,
            'Missing, linked or oversized server cache archive')
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(1 < len(names) <= 1025 and len(names) == len({name.casefold() for name in names}),
                'Duplicate or oversized server cache inventory')
        require(MANIFEST in names and archive.getinfo(MANIFEST).file_size <= MAX_MANIFEST,
                'Missing or oversized server cache manifest')
        manifest = json.loads(archive.read(MANIFEST), object_pairs_hook=unique_object)
        require(isinstance(manifest, dict) and manifest.get('format') == 1 and manifest.get('role') == ROLE
                and HEX40.fullmatch(str(manifest.get('repository_commit', ''))), 'Server donor provenance differs')
        identity = manifest.get('identity')
        require(isinstance(identity, dict) and {key: identity.get(key) for key in compatibility_identity()}
                == compatibility_identity() and set(identity) == set(compatibility_identity()) | {'identifier_files'},
                'Server donor compatibility identity differs')
        identifiers = identity['identifier_files']
        require(isinstance(identifiers, dict) and 0 < len(identifiers) <= 128, 'Invalid identifier closure')
        for name, record in identifiers.items():
            require(isinstance(name, str) and name.startswith(('data/defs/', 'data/server/db/templates/'))
                    and '\\' not in name and ':' not in name and '\x00' not in name
                    and all(part not in ('', '.', '..') for part in name.split('/'))
                    and name.lower().endswith(('.dbidmap', '.attribute'))
                    and isinstance(record, dict) and set(record) == {'bytes', 'sha256'}
                    and type(record['bytes']) is int and 0 < record['bytes'] <= 8 * 1024 * 1024
                    and HEX64.fullmatch(str(record['sha256'])), 'Invalid persistent identifier record')
        require(expected_identity is None or identity == expected_identity, 'Server donor/runtime inputs differ')
        files = manifest.get('files')
        require(isinstance(files, dict) and files and set(files) | {MANIFEST} == set(names),
                'Server cache payload inventory differs')
        require(REQUIRED_PARSE6 | REQUIRED_MESSAGES <= {name.casefold() for name in files},
                'Required power/story/spawn/message cache coverage missing')
        validate_native_receipt(manifest.get('native_generation'), False, files)
        validate_native_receipt(manifest.get('native_consumption'), True, files)
        require(manifest.get('native_client_or_server_recompiled') is False
                and manifest.get('generated_noncache_outputs') == []
                and manifest.get('android_execution_validated') is False
                and manifest.get('physical_gameplay_validated') is False, 'Server cache scope differs')
        total = 0
        for name, record in files.items():
            require(safe_cache(name) and isinstance(record, dict), 'Unsafe server cache path/record')
            entry = archive.getinfo(name)
            mode = entry.external_attr >> 16
            require(not entry.is_dir() and not entry.flag_bits & 1
                    and stat.S_IFMT(mode) in (0, stat.S_IFREG), 'Nonregular/encrypted server cache member')
            require(type(record.get('bytes')) is int and 0 < record['bytes'] <= MAX_FILE
                    and entry.file_size == record['bytes'] and HEX64.fullmatch(str(record.get('sha256', ''))),
                    'Server cache payload size/hash record differs')
            total += entry.file_size
            require(total <= MAX_TOTAL, 'Server cache package exceeds total bound')
            data = archive.read(entry)
            require(pin_bytes(data) == {key: record[key] for key in ('bytes', 'sha256')}, 'Server cache bytes differ')
            require(inspect_payload(data, record.get('kind')) == record.get('structure'),
                    'Server cache binary structure differs')
            if name.casefold() in REQUIRED_PARSE6:
                require(record['kind'] == 'Parse6', 'Required definition cache has wrong binary kind')
            if name.casefold() in REQUIRED_MESSAGES:
                require(record['kind'] == 'MessageStore20090521', 'Required message cache has wrong binary kind')
    return manifest


def install(archive, runtime_data, expected_identity, context=None):
    """Validate first, then seed missing private leaves; preserve native fallback."""
    archive, runtime_data = Path(archive), Path(runtime_data)
    if not archive.exists():
        return {'format': 1, 'status': 'skipped_native_fallback', 'reason': 'donor_absent', 'installed_files': 0}
    try:
        manifest = verify_archive(archive, expected_identity)
        regular_directory(runtime_data)
        owner = runtime_data.lstat().st_uid
        targets = {}
        for name in manifest['files']:
            current = runtime_data
            parts = Path(name).parts[1:]
            for part in parts[:-1]:
                require(not current.is_symlink(), 'Linked server cache ancestor refused')
                if current.exists():
                    regular_directory(current)
                    require(not any(item.name.casefold() == part.casefold() and item.name != part
                                    for item in current.iterdir()), 'Case-conflicting server cache directory')
                current /= part
            require(not current.is_symlink() and (not current.exists() or current.is_dir()),
                    'Invalid server cache directory')
            target = current / parts[-1]
            if current.exists():
                require(not any(item.name.casefold() == target.name.casefold() and item.name != target.name
                                for item in current.iterdir()), 'Case-conflicting server cache leaf')
            require(not target.is_symlink() and (not target.exists() or target.is_file()),
                    'Invalid existing server cache leaf')
            if target.exists():
                private_regular(target, owner)
            targets[name] = target
    except (ValueError, OSError, zipfile.BadZipFile, UnicodeError, KeyError, struct.error) as error:
        return {'format': 1, 'status': 'skipped_native_fallback', 'reason': str(error)[:300], 'installed_files': 0}
    installed, preserved = [], []
    with zipfile.ZipFile(archive) as source:
        for name, target in sorted(targets.items()):
            if context is not None:
                context.check()
            owner = private_ancestors(runtime_data, target.parent, allow_missing=True)
            if target.exists():
                private_regular(target, owner)
                preserved.append(name)
                continue
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            private_ancestors(runtime_data, target.parent)
            descriptor, temporary_name = tempfile.mkstemp(prefix='.server-cache-pending-', dir=target.parent)
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, 'wb') as output, source.open(name) as payload:
                    digest, size = hashlib.sha256(), 0
                    for block in iter(lambda: payload.read(1024 * 1024), b''):
                        if context is not None:
                            context.check()
                        size += len(block)
                        require(size <= manifest['files'][name]['bytes'], 'Cache changed while seeding')
                        output.write(block)
                        digest.update(block)
                    output.flush()
                    os.fsync(output.fileno())
                require({'bytes': size, 'sha256': digest.hexdigest()} ==
                        {key: manifest['files'][name][key] for key in ('bytes', 'sha256')},
                        'Cache changed while seeding')
                temporary.chmod(0o600)
                os.utime(temporary, (EPOCH, EPOCH))
                # Retain the accepted PRoot-safe atomic no-replace publisher.
                # Hard links can create PRoot backing files and violate the
                # private-cache single-link invariant.
                import client_startup_diagnostic as client
                try:
                    private_ancestors(runtime_data, target.parent)
                    client.publish_new_regular_file(temporary, target)
                    private_regular(target, owner)
                    installed.append(name)
                except FileExistsError:
                    private_regular(target, owner)
                    preserved.append(name)
            finally:
                temporary.unlink(missing_ok=True)
    return {'format': 1, 'status': 'installed' if installed else 'preserved_existing_native_caches',
            'scope': 'missing_exact_server_bins_only', 'archive': file_pin(archive),
            'manifest_sha256': hashlib.sha256(canonical(manifest)).hexdigest(),
            'compatibility': compatibility_identity(), 'installed_files': len(installed),
            'installed_paths': installed, 'preserved_existing_files': len(preserved),
            'preserved_paths': preserved, 'templates_attributes_or_dbidmaps_changed': False,
            'native_loader_fallback_retained': True}
