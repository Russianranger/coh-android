"""Install only the pinned missing Atlas NPC, material and GUI assets.

Imported assets, existing supplements and every generated cache stay untouched.
Warm reuse checks the complete owned readonly file fingerprint receipt.
"""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import re
import stat
import tempfile
import time
import zipfile

import atlas_world_assets as world
import client_startup_diagnostic as client

require = client.require
ARCHIVE = 'client-visual-assets.zip'
MANIFEST = 'client-visual-manifest.json'
SCOPE = 'atlas_client_missing_visual_assets'
ARCHIVE_SHA256 = '840619b3b40c24f206576580dfaedb779a66582f1df189f37002dd59c5399cb9'
MANIFEST_SHA256 = '8b3f579a9ff48e80f40e06e252c91fe3357daf9f0b01441dea5bceaa5801f1e6'
FILES_SHA256 = 'e23299918437e5d0afa2e9d2003eb966151f59471eaeb430313d2824d42fe341'
ARCHIVE_BYTES = 854341235
FILE_COUNT, PAYLOAD_BYTES = 9490, 1505717817
BASE_FILE_COUNT, BASE_PAYLOAD_BYTES = 290, 36583648
BASE_FILES_SHA256 = 'f47229c7d9f2474b542f761b6058299c5400df709ba892e6ca3f9b35b839028e'
EXTENSION_FILE_COUNT, EXTENSION_PAYLOAD_BYTES = 33, 2646051
EXTENSION_FILES_SHA256 = '3b904fd8e99d0c00ec6a07b87e0dc387fcca89835920aba8332723e10b50caa2'
ENCOUNTER_FILE_COUNT, ENCOUNTER_PAYLOAD_BYTES = 6, 291538
ENCOUNTER_FILES_SHA256 = 'd2c2ea6b9bacb7691b53944e852180698edc255c54b231d1743b8fc3ffd7e85d'
IMMEDIATE_FILES_SHA256 = 'f5577769ef6df22437f9eda6b0388358cd1c28013eb5fbc35aece9af0febd4f7'
SWEEP_FILE_COUNT, SWEEP_PAYLOAD_BYTES = 5147, 833734047
SWEEP_FILES_SHA256 = '7159ada9851057278f934f55c577b7063e4979d1fe2a2ce11718ded79440e8e6'
SWEEP_BASE_FILES_SHA256 = '07b61f301355f2bb0174db2b41f1254b3f2b80cfd660d5f467415c7f33707c09'
SWEEP_BASE_PAYLOAD_BYTES = 39521237
APPEARANCE_FILE_COUNT, APPEARANCE_PAYLOAD_BYTES = 4014, 632462533
APPEARANCE_FILES_SHA256 = 'c18ee3f0d2551249bfb98b921be8c230db5923a5a531cec2a55d0c03e80810ae'
APPEARANCE_BASE_FILES_SHA256 = '99021fe01af691b88335f9d3e6fc6c16687ab12dbf652b80ff432f266f617542'
MAX_ARCHIVE_BYTES, MAX_MANIFEST_BYTES = 1024**3, 64 * 1024**2
MAX_PAYLOAD_BYTES = 2 * 1024**3
MAX_ENTRY_BYTES, MAX_RECEIPT_BYTES = 32 * 1024**2, 4 * 1024**2
MARKER = 'client-visual-installed.json'
POLICY = 'pinned_missing_only_client_visual_v1'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def safe_payload(name):
    if not isinstance(name, str):
        return False
    path = PurePosixPath(name)
    return (name == name.casefold() and path.as_posix() == name and name.isascii()
        and '\\' not in name and ':' not in name and all(p not in ('', '.', '..') for p in path.parts)
        and (name.startswith(('data/player_library/', 'data/object_library/')) and path.suffix == '.geo'
             or name.startswith('data/texture_library/') and path.suffix == '.texture'))


def package(assets):
    raw = world.read_regular(Path(assets) / MANIFEST, MAX_MANIFEST_BYTES)
    require(hashlib.sha256(raw).hexdigest() == MANIFEST_SHA256,
        'Client visual manifest differs from reviewed metadata')
    value = json.loads(raw)
    files = value.get('files', {})
    require(value.get('format') == 1 and value.get('scope') == SCOPE
        and value.get('source_commit') == client.SOURCE and value.get('data_commit') == client.DATA
        and value.get('file_count') == FILE_COUNT and value.get('payload_bytes') == PAYLOAD_BYTES <= MAX_PAYLOAD_BYTES
        and value.get('files_sha256') == FILES_SHA256 and isinstance(files, dict) and len(files) == FILE_COUNT
        and all(safe_payload(name) and isinstance(pin, dict) and type(pin.get('bytes')) is int
            and 0 < pin['bytes'] <= MAX_ENTRY_BYTES and re.fullmatch('[0-9a-f]{64}', pin.get('sha256', ''))
            for name, pin in files.items()) and sum(row['bytes'] for row in files.values()) == PAYLOAD_BYTES
        and hashlib.sha256(canonical(files)).hexdigest() == FILES_SHA256
        and value.get('archive') == {'filename': ARCHIVE, 'bytes': ARCHIVE_BYTES, 'sha256': ARCHIVE_SHA256}
        and value.get('installation') == 'private_client_worktree_missing_files_only'
        and all(value.get(key) is False for key in ('runtime_visual_validated', 'gameplay_validated',
            'imported_assets_modified', 'prepared_caches_modified', 'existing_supplements_modified')),
        'Client visual identity, missing-only policy or inventory differs')
    appearances = appearance_files(value)
    sweeps = sweep_files(value)
    encounters = encounter_files(value) | sweeps | appearances
    extension = value.get('visual_extension', {})
    additions = extension.get('files', {})
    require(isinstance(additions, dict) and set(additions) <= set(files)
        and len(additions) == extension.get('file_count') == EXTENSION_FILE_COUNT
        and extension.get('payload_bytes') == EXTENSION_PAYLOAD_BYTES
        and extension.get('baseline_payloads_preserved') is True
        and extension.get('missing_only') is True
        and extension.get('baseline_file_count') == BASE_FILE_COUNT
        and extension.get('baseline_payload_bytes') == BASE_PAYLOAD_BYTES
        and extension.get('baseline_files_sha256') == BASE_FILES_SHA256,
        'Client visual append-only baseline policy differs')
    baseline = {name: row for name, row in files.items() if name not in additions and name not in encounters}
    selected = {name: files[name] for name in sorted(additions)}
    require(len(baseline) == BASE_FILE_COUNT
        and sum(row['bytes'] for row in baseline.values()) == BASE_PAYLOAD_BYTES
        and hashlib.sha256(canonical(baseline)).hexdigest() == BASE_FILES_SHA256
        and sum(row['bytes'] for row in selected.values()) == EXTENSION_PAYLOAD_BYTES
        and hashlib.sha256(canonical(selected)).hexdigest() == EXTENSION_FILES_SHA256,
        'Client visual append-only recipe changes a preserved baseline payload')
    return value


def encounter_files(value):
    if ENCOUNTER_FILE_COUNT == 0:  # Small installer fixtures retain the original two-file policy tests.
        require('encounter_extension' not in value, 'Unexpected encounter extension in baseline fixture')
        return set()
    extension, files = value.get('encounter_extension', {}), value.get('files', {})
    additions = extension.get('files', {})
    require(isinstance(additions, dict) and set(additions) <= set(files)
        and len(additions) == extension.get('file_count') == ENCOUNTER_FILE_COUNT
        and extension.get('payload_bytes') == ENCOUNTER_PAYLOAD_BYTES
        and extension.get('baseline_payloads_preserved') is True and extension.get('missing_only') is True
        and extension.get('baseline_file_count') == 323 and extension.get('baseline_payload_bytes') == 39229699
        and extension.get('baseline_files_sha256') == IMMEDIATE_FILES_SHA256
        and all(name.startswith('data/texture_library/npcs/') and name.endswith('.texture') for name in additions),
        'Client visual encounter append-only baseline policy differs')
    sweeps = set(value.get('sweep_extension', {}).get('files', {}))
    appearances = set(value.get('appearance_extension', {}).get('files', {}))
    baseline = {name: row for name, row in files.items() if name not in additions and name not in sweeps and name not in appearances}
    selected = {name: files[name] for name in sorted(additions)}
    require(len(baseline) == 323 and sum(row['bytes'] for row in baseline.values()) == 39229699
        and hashlib.sha256(canonical(baseline)).hexdigest() == IMMEDIATE_FILES_SHA256
        and sum(row['bytes'] for row in selected.values()) == ENCOUNTER_PAYLOAD_BYTES
        and hashlib.sha256(canonical(selected)).hexdigest() == ENCOUNTER_FILES_SHA256,
        'Client visual encounter recipe changes a preserved 0.13.8 payload')
    return set(additions)


def sweep_files(value):
    if SWEEP_FILE_COUNT == 0:  # Small synthetic installer fixtures.
        require('sweep_extension' not in value, 'Unexpected sweep extension in baseline fixture')
        return set()
    extension, files = value.get('sweep_extension', {}), value.get('files', {})
    additions = extension.get('files', {})
    require(extension.get('scope') == 'recorded_client_missing_asset_dependency_closure'
        and isinstance(additions, dict) and set(additions) <= set(files)
        and len(additions) == extension.get('file_count') == SWEEP_FILE_COUNT
        and extension.get('payload_bytes') == SWEEP_PAYLOAD_BYTES
        and extension.get('files_sha256') == SWEEP_FILES_SHA256
        and extension.get('baseline_payloads_preserved') is True and extension.get('missing_only') is True
        and extension.get('baseline_file_count') == 329
        and extension.get('baseline_payload_bytes') == SWEEP_BASE_PAYLOAD_BYTES
        and extension.get('baseline_files_sha256') == SWEEP_BASE_FILES_SHA256,
        'Client visual sweep append-only baseline policy differs')
    appearances = set(value.get('appearance_extension', {}).get('files', {}))
    baseline = {name: row for name, row in files.items() if name not in additions and name not in appearances}
    selected = {name: files[name] for name in sorted(additions)}
    require(len(baseline) == 329 and sum(row['bytes'] for row in baseline.values()) == SWEEP_BASE_PAYLOAD_BYTES
        and hashlib.sha256(canonical(baseline)).hexdigest() == SWEEP_BASE_FILES_SHA256
        and sum(row['bytes'] for row in selected.values()) == SWEEP_PAYLOAD_BYTES
        and hashlib.sha256(canonical(selected)).hexdigest() == SWEEP_FILES_SHA256,
        'Client visual sweep changes a preserved 0.13.9 payload')
    return set(additions)


def appearance_files(value):
    if SWEEP_FILE_COUNT == 0:  # Only the small synthetic installer fixtures.
        require('appearance_extension' not in value, 'Unexpected appearance extension in historical fixture')
        return set()
    extension, files = value.get('appearance_extension', {}), value.get('files', {})
    additions = extension.get('files', {})
    require(extension.get('scope') == 'recorded_atlas_npc_sequence_and_costume_dependency_closure'
        and isinstance(additions, dict) and set(additions) <= set(files)
        and len(additions) == extension.get('file_count') == APPEARANCE_FILE_COUNT
        and extension.get('payload_bytes') == APPEARANCE_PAYLOAD_BYTES
        and extension.get('files_sha256') == APPEARANCE_FILES_SHA256
        and extension.get('baseline_payloads_preserved') is True and extension.get('missing_only') is True
        and extension.get('baseline_file_count') == 5476
        and extension.get('baseline_payload_bytes') == 873255284
        and extension.get('baseline_files_sha256') == APPEARANCE_BASE_FILES_SHA256,
        'Client appearance append-only baseline policy differs')
    baseline = {name: row for name, row in files.items() if name not in additions}
    selected = {name: files[name] for name in sorted(additions)}
    require(len(baseline) == 5476 and sum(row['bytes'] for row in baseline.values()) == 873255284
        and hashlib.sha256(canonical(baseline)).hexdigest() == APPEARANCE_BASE_FILES_SHA256
        and sum(row['bytes'] for row in selected.values()) == APPEARANCE_PAYLOAD_BYTES
        and hashlib.sha256(canonical(selected)).hexdigest() == APPEARANCE_FILES_SHA256,
        'Client appearance recipe changes a preserved 0.13.10 payload')
    return set(additions)


def source_state(assets):
    states = {name: world.file_state(Path(assets) / name, limit) for name, limit in
        ((MANIFEST, MAX_MANIFEST_BYTES), (ARCHIVE, MAX_ARCHIVE_BYTES))}
    require(states[ARCHIVE][2] == ARCHIVE_BYTES, 'Client visual archive size differs')
    return states


def validate_archive(archive, files, context):
    entries = archive.infolist()
    require(len(entries) == len({row.filename for row in entries}) == FILE_COUNT
        and {row.filename for row in entries} == set(files), 'Client visual ZIP member inventory differs')
    for entry in entries:
        context.check()
        require(not entry.is_dir() and not entry.flag_bits & 1
            and stat.S_ISREG(entry.external_attr >> 16) and entry.file_size == files[entry.filename]['bytes']
            and entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
            'Invalid client visual ZIP member')


def marker_state(worktree):
    path = worktree / MARKER
    if not os.path.lexists(path):
        return None
    raw = world.read_regular(path, MAX_RECEIPT_BYTES, installed=True)
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        return None
    return value if isinstance(value, dict) else None


def publish_marker(worktree, value, context):
    path = worktree / MARKER
    previous = world.file_state(path, MAX_RECEIPT_BYTES, installed=True) if os.path.lexists(path) else None
    descriptor, name = tempfile.mkstemp(prefix='.client-visual-marker-', dir=worktree)
    temporary = Path(name)
    try:
        raw = canonical(value)
        require(len(raw) <= MAX_RECEIPT_BYTES, 'Client visual receipt exceeds bound')
        with os.fdopen(descriptor, 'wb') as target:
            target.write(raw); target.flush(); os.fsync(target.fileno())
        temporary.chmod(0o444)
        os.utime(temporary, (client.CACHE_EPOCH, client.CACHE_EPOCH))
        context.check()
        if previous is None:
            client.publish_new_regular_file(temporary, path)
        else:
            require(world.file_state(path, MAX_RECEIPT_BYTES, installed=True) == previous,
                'Client visual receipt changed before publication')
            os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def install(worktree, assets, context):
    """Add reviewed files to the verified private client generation, never replace a leaf."""
    started = time.monotonic()
    worktree, assets = Path(worktree), Path(assets)
    context.check()
    world.real_directory(worktree); world.real_directory(worktree / 'data'); world.real_directory(assets)
    inputs = source_state(assets)
    document = package(assets)
    files = document['files']
    identity = {'format': 1, 'policy': POLICY, 'manifest_sha256': MANIFEST_SHA256,
        'archive_sha256': ARCHIVE_SHA256, 'files_sha256': FILES_SHA256,
        'worktree': str(worktree), 'directory_identity': [[p.stat().st_dev, p.stat().st_ino]
            for p in (worktree, worktree / 'data')],
        'client_work_sha256': hashlib.sha256(world.read_regular(worktree / 'client-work.json', 1024**2)).hexdigest()}
    targets = world.resolve_targets(worktree, files, context)
    before = world.output_state(worktree, targets, files, context)
    saved = marker_state(worktree)
    reused = all(row['stat'] is not None for row in before.values()) and saved == {
        'identity': identity, 'inputs': inputs, 'outputs': before}
    installed = verified_bytes = decoded_bytes = 0
    if not reused:
        for name, target in targets.items():
            context.check()
            if world.verify_target(target, files[name], context):
                verified_bytes += files[name]['bytes']
        descriptor = os.open(assets / ARCHIVE, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            require(world.checked_info(assets / ARCHIVE, os.fstat(descriptor), MAX_ARCHIVE_BYTES) == inputs[ARCHIVE],
                'Client visual archive changed before reading')
            with os.fdopen(descriptor, 'rb', closefd=False) as source:
                size, digest = world.hash_stream(source, context, ARCHIVE_BYTES)
                require(size == ARCHIVE_BYTES and digest == ARCHIVE_SHA256, 'Client visual archive differs')
                source.seek(0)
                with zipfile.ZipFile(source) as archive:
                    validate_archive(archive, files, context)
                    for name, target in targets.items():
                        context.check()
                        if before[name]['stat'] is not None:
                            continue
                        target.parent.mkdir(parents=True, exist_ok=True)
                        world.real_directory(target.parent)
                        descriptor2, temporary_name = tempfile.mkstemp(prefix='.client-visual-', dir=target.parent)
                        temporary = Path(temporary_name)
                        try:
                            with os.fdopen(descriptor2, 'wb') as output:
                                world.extract_payload(archive, name, files[name], output, context)
                                output.flush(); os.fsync(output.fileno())
                            temporary.chmod(0o444)
                            os.utime(temporary, (client.CACHE_EPOCH, client.CACHE_EPOCH))
                            context.check()
                            world.real_directory(target.parent)
                            client.publish_new_regular_file(temporary, target)
                            installed += 1; decoded_bytes += files[name]['bytes']
                        finally:
                            temporary.unlink(missing_ok=True)
            world.unchanged(assets / ARCHIVE, descriptor, inputs[ARCHIVE])
        finally:
            os.close(descriptor)
    context.check()
    require(source_state(assets) == inputs and world.resolve_targets(worktree, files, context) == targets,
        'Client visual sources or destination changed during preparation')
    after = world.output_state(worktree, targets, files, context)
    require(all(row['stat'] is not None for row in after.values()), 'Client visual installed payload disappeared')
    require(all(before[name]['stat'] is None or after[name] == before[name] for name in files),
        'Existing client visual file changed during preparation')
    final = {'identity': identity, 'inputs': inputs, 'outputs': after}
    require(identity['client_work_sha256'] == hashlib.sha256(
        world.read_regular(worktree / 'client-work.json', 1024**2)).hexdigest(), 'Verified client identity changed')
    if not reused:
        publish_marker(worktree, final, context)
    unresolved = sorted({row['target'] for section in ('closure', 'sweep_extension', 'appearance_extension')
        for row in document.get(section, {}).get('unresolved_dependencies', [])})
    return {'format': 1, 'scope': SCOPE, 'manifest_sha256': MANIFEST_SHA256,
        'archive_sha256': ARCHIVE_SHA256, 'files_sha256': FILES_SHA256, 'file_count': FILE_COUNT,
        'payload_bytes': PAYLOAD_BYTES, 'installed_files': installed, 'reused_files': FILE_COUNT - installed,
        'retained_baseline_file_count': BASE_FILE_COUNT, 'added_file_count': EXTENSION_FILE_COUNT,
        'retained_immediate_file_count': 323, 'added_encounter_file_count': ENCOUNTER_FILE_COUNT,
        'added_encounter_payload_bytes': ENCOUNTER_PAYLOAD_BYTES,
        'retained_sweep_baseline_file_count': 329, 'added_sweep_file_count': SWEEP_FILE_COUNT,
        'added_sweep_payload_bytes': SWEEP_PAYLOAD_BYTES,
        'retained_appearance_baseline_file_count': 5476, 'added_appearance_file_count': APPEARANCE_FILE_COUNT,
        'added_appearance_payload_bytes': APPEARANCE_PAYLOAD_BYTES,
        'retained_baseline_payloads_preserved': True,
        'reuse_validation': POLICY, 'fingerprint_reused': bool(reused), 'decoded_files': installed,
        'decoded_payload_bytes': decoded_bytes, 'verified_existing_bytes': verified_bytes,
        'archive_read_bytes': 0 if reused else ARCHIVE_BYTES, 'worktree': worktree.name,
        'normalized_mtime_epoch': client.CACHE_EPOCH, 'imported_files_modified': False,
        'generated_caches_modified': False, 'existing_supplements_modified': False,
        'runtime_visual_validated': False, 'full_global_asset_closure': False,
        'unresolved_direct_material_names': unresolved,
        'absent_requested_models': document.get('closure', {}).get('absent_requested_models', []),
        'unresolved_dependency_count': len(unresolved)
            + len(document.get('closure', {}).get('absent_requested_models', [])),
        'preparation_elapsed_seconds': round(time.monotonic() - started, 6)}
