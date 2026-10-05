"""Pack exact immutable texture headers for one verified client generation.

Only the 32-byte header, original name and original cached mip bytes are packed.
Full .texture files remain unchanged. A native failure falls back to file reads.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import stat
import struct
import time
import zlib

FORMAT = 1
MAX_RECORDS = 65536
MAX_BYTES = 64 * 1024 * 1024
MAX_HEADER = 1056
PACK = 'coh-texture-header-index.bin'
MARKER = 'coh-texture-header-index.json'
IDENTITY_POLICY = 'verified_client_content_v1'


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def worktree_identity(client):
    """Use the already verified data/native closure, excluding wrapper lineage."""
    from client_startup_diagnostic import worktree_data_identity
    content = client.get('content_identity_sha256')
    require(isinstance(content, str) and re.fullmatch(r'[0-9a-f]{64}', content),
            'Missing verified client content identity')
    try:
        data = worktree_data_identity(client)
    except KeyError as error:
        raise ValueError('Incomplete verified client data identity') from error
    return {'content_identity_sha256': content, 'data_contract': data}


def pack_identity(client_identity, import_identity, executable_sha256, inventory_sha):
    return hashlib.sha256(canonical({'format': FORMAT, 'import': import_identity,
        'client_executable_sha256': executable_sha256, 'client_work': client_identity,
        'texture_inventory_sha256': inventory_sha})).hexdigest()


def rebind_legacy_pack(contents, old_identity, identity, records):
    """Rebind only the envelope; an exactly proved old payload stays unchanged."""
    require(contents[:8] == b'COHTHI1\0' and 64 <= len(contents) <= MAX_BYTES,
            'Invalid previous texture pack envelope')
    require(struct.unpack_from('<IIIIII', contents, 8) == (
                FORMAT, 32, records, len(contents) - 64, zlib.crc32(contents[64:]), 0)
            and contents[32:64] == bytes.fromhex(old_identity),
            'Previous texture pack identity or checksum differs')
    return contents[:32] + bytes.fromhex(identity) + contents[64:]


def texture_inputs(work, context):
    data = work / 'data'
    root = data / 'texture_library'
    require(root.is_dir() and not root.is_symlink(), 'Private texture directory unavailable')
    marker = work / 'client-work.json'
    require(marker.is_file() and not marker.is_symlink() and marker.stat().st_size <= 1024**2,
            'Missing or oversized verified client worktree')
    client = json.loads(marker.read_bytes())
    imported = Path(client['source_data']).resolve()
    # Resolve the shared private root once; every leaf still gets its original
    # strict resolution, readonly metadata checks and complete inventory entry.
    # Recheck the root after the walk so a changed ancestor is never accepted
    # because of this cached comparison path.
    private = data.resolve(strict=True)
    inventory, records = [], []
    for current, directories, files in os.walk(root, followlinks=False):
        context.check()
        # Match the native scanner's _ directory exclusion exactly.
        directories[:] = sorted(name for name in directories if not name.startswith('_'))
        files.sort()
        for name in directories:
            require(not (Path(current) / name).is_symlink(), 'Linked texture directory refused')
        directory = Path(current)
        info = directory.stat()
        relative_directory = directory.relative_to(data).as_posix()
        inventory.append([relative_directory, info.st_ino, info.st_mtime_ns, info.st_ctime_ns])
        for name in files:
            if not name.lower().endswith('.texture') or name.startswith('_'):
                continue
            path = directory / name
            resolved = path.resolve(strict=True)
            require(resolved.is_relative_to(imported) or resolved.is_relative_to(private),
                    'Texture link escapes verified immutable input')
            info = resolved.stat()
            require(stat.S_ISREG(info.st_mode) and not info.st_mode & 0o222,
                    'Texture index requires readonly regular inputs')
            relative = (relative_directory + '/' + name).lower()
            require(relative.isascii() and 25 <= len(relative) < 260 and '\\' not in relative
                    and ':' not in relative and all(p not in ('', '.', '..') for p in relative.split('/')),
                    'Texture index path exceeds native contract')
            inventory.append([relative, str(resolved), info.st_ino, info.st_size,
                              info.st_mtime_ns, info.st_ctime_ns, info.st_mode])
            records.append((relative, path))
            require(len(records) <= MAX_RECORDS, 'Texture inventory exceeds native bound')
    require(data.resolve(strict=True) == private, 'Private texture root changed while indexing')
    records.sort(key=lambda item: item[0])
    require(records and len({name for name, _ in records}) == len(records),
            'Empty or ambiguous texture inventory')
    return records, hashlib.sha256(canonical(inventory)).hexdigest(), client


def make_pack(records, identity, context):
    payload = bytearray()
    header_digest = hashlib.sha256()
    for relative, path in records:
        context.check()
        with path.open('rb') as stream:
            fixed = stream.read(32)
            require(len(fixed) == 32, 'Truncated texture header: ' + relative)
            size, data_bytes, width, height = struct.unpack_from('<IIII', fixed)
            require(32 < size <= MAX_HEADER and 0 < width <= 16384 and 0 < height <= 16384,
                    'Invalid original texture header: ' + relative)
            extra = stream.read(size - 32)
            require(len(extra) == size - 32 and b'\0' in extra and path.stat().st_size >= size + data_bytes,
                    'Invalid original texture data/name: ' + relative)
        header = fixed + extra
        encoded = relative.encode('ascii')
        payload.extend(struct.pack('<HH', len(encoded), len(header)))
        payload.extend(encoded)
        payload.extend(header)
        header_digest.update(encoded + b'\0' + header)
        require(len(payload) + 64 <= MAX_BYTES, 'Texture header pack exceeds native bound')
    envelope = b'COHTHI1\0' + struct.pack('<IIIIII', FORMAT, 32, len(records), len(payload),
                                          zlib.crc32(payload), 0) + bytes.fromhex(identity)
    return envelope + payload, header_digest.hexdigest()


def atomic_write(path, data):
    temporary = path.with_name(path.name + '.pending-' + os.urandom(8).hex())
    try:
        with temporary.open('xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o400)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def prepare(work, import_identity, executable_sha256, context):
    """Return (timing/provenance receipt, Wine environment) after supplements.

    Inventory metadata includes inode, size, mode, mtime and ctime for every
    readonly texture and its directories. Thus ordinary content/identity changes
    invalidate the pack, including rewrites followed by restored mtime.
    """
    started = time.monotonic()
    work = Path(work)
    inventory_seconds = 0.0
    inventory_passes = 0
    header_seconds = 0.0
    def inspect_inputs():
        nonlocal inventory_seconds, inventory_passes
        begin = time.monotonic()
        result = texture_inputs(work, context)
        inventory_seconds += time.monotonic() - begin
        inventory_passes += 1
        return result
    records, inventory_sha, client = inspect_inputs()
    stable_client = worktree_identity(client)
    require(stable_client['data_contract']['import'] == import_identity,
            'Texture import identity differs from verified client worktree')
    identity = pack_identity(stable_client, import_identity, executable_sha256, inventory_sha)
    target, marker = work / PACK, work / MARKER
    expected = {'format': FORMAT, 'identity': identity, 'records': len(records),
                'inventory_sha256': inventory_sha, 'client_executable_sha256': executable_sha256,
                'identity_policy': IDENTITY_POLICY,
                'client_content_identity_sha256': stable_client['content_identity_sha256']}
    saved = None
    migrated = False
    native_migrated = False
    interrupted_recovered = False
    if (marker.is_file() and not marker.is_symlink() and marker.stat().st_size < 16384
            and target.is_file() and not target.is_symlink() and 64 <= target.stat().st_size <= MAX_BYTES):
        try:
            candidate = json.loads(marker.read_bytes())
            require(isinstance(candidate, dict), 'Invalid previous texture index receipt')
            contents = target.read_bytes()
            valid_payload = (candidate.get('bytes') == len(contents)
                             and candidate.get('sha256') == hashlib.sha256(contents).hexdigest())
            if (not valid_payload and candidate.get('bytes') == len(contents)
                    and candidate.get('records') == len(records)
                    and re.fullmatch(r'[0-9a-f]{64}', str(candidate.get('identity', '')))):
                # A durable envelope rename may precede its marker rename.
                # Only a byte-exact reverse rebind to the old owned SHA proves
                # this state; changed header payloads still require regeneration.
                restored = rebind_legacy_pack(contents, identity, candidate['identity'], len(records))
                if candidate.get('sha256') == hashlib.sha256(restored).hexdigest():
                    contents = restored
                    valid_payload = True
                    interrupted_recovered = True
            if valid_payload and all(candidate.get(key) == value for key, value in expected.items()):
                saved = candidate
            elif valid_payload:
                # prepare_worktree supplies this snapshot only after checking
                # the previous native/prerequisite closure. It is report-only,
                # never recursive metadata persisted in client-work.json.
                report = getattr(context, 'report', {}).get('client_worktree', {})
                previous = report.get('previous_verified_client_worktree')
                native = report.get('native_texture_index_migration')
                if (report.get('source_root_preserved') is True and isinstance(native, dict)
                        and set(native) == {'format', 'policy', 'previous_client_identity',
                            'previous_executable_sha256', 'client_executable_sha256',
                            'content_identity_sha256', 'layer_manifest_sha256',
                            'texture_header_struct_bytes', 'native_source_closure_verified'}
                        and type(native['format']) is int and native['format'] == 1
                        and native['policy'] in ('verified_startup_client_layer_v1',
                                                'verified_client_loading_layer_v1',
                                                'verified_client_startup_followup_layer_v1')
                        and native['native_source_closure_verified'] is True
                        and native['texture_header_struct_bytes'] == 32
                        and native['client_executable_sha256'] == executable_sha256
                        and native['previous_executable_sha256'] != executable_sha256
                        and native['content_identity_sha256'] == stable_client['content_identity_sha256']
                        and all(re.fullmatch(r'[0-9a-f]{64}', str(native[key])) for key in
                            ('previous_executable_sha256', 'client_executable_sha256', 'layer_manifest_sha256'))
                        and isinstance(native['previous_client_identity'], dict)
                        and set(native['previous_client_identity']) == {'content_identity_sha256', 'data_contract'}
                        and re.fullmatch(r'[0-9a-f]{64}', str(native['previous_client_identity']['content_identity_sha256']))
                        and native['previous_client_identity']['data_contract'] == stable_client['data_contract']):
                    old = native['previous_client_identity']
                    old_identity = pack_identity(old, import_identity, native['previous_executable_sha256'], inventory_sha)
                    old_expected = dict(expected, identity=old_identity,
                        client_executable_sha256=native['previous_executable_sha256'],
                        client_content_identity_sha256=old['content_identity_sha256'])
                    if all(candidate.get(key) == value for key, value in old_expected.items()):
                        contents = rebind_legacy_pack(contents, old_identity, identity, len(records))
                        _, after, after_client = inspect_inputs()
                        require(after == inventory_sha and worktree_identity(after_client) == stable_client,
                                'Texture generation changed while rebinding native index')
                        saved = dict(candidate, **expected, sha256=hashlib.sha256(contents).hexdigest())
                        atomic_write(target, contents)
                        atomic_write(marker, canonical(saved) + b'\n')
                        native_migrated = True
                if (saved is None and report.get('wrapper_only_migration') is True
                        and report.get('source_root_preserved') is True
                        and isinstance(previous, dict)):
                    from client_startup_diagnostic import worktree_data_identity
                    legacy = pack_identity(previous, import_identity, executable_sha256, inventory_sha)
                    legacy_expected = {'format': FORMAT, 'identity': legacy, 'records': len(records),
                        'inventory_sha256': inventory_sha, 'client_executable_sha256': executable_sha256}
                    if (worktree_data_identity(previous) == stable_client['data_contract']
                            and all(candidate.get(key) == value for key, value in legacy_expected.items())):
                        contents = rebind_legacy_pack(contents, legacy, identity, len(records))
                        _, after, after_client = inspect_inputs()
                        require(after == inventory_sha and worktree_identity(after_client) == stable_client,
                                'Texture generation changed while migrating index')
                        saved = dict(candidate, **expected, sha256=hashlib.sha256(contents).hexdigest())
                        atomic_write(target, contents)
                        atomic_write(marker, canonical(saved) + b'\n')
                        migrated = True
        except (ValueError, OSError, KeyError, TypeError):
            pass
    reused = saved is not None
    if saved is None:
        context.event('stage', status='running', message='Indexing immutable texture headers', records=len(records))
        header_started = time.monotonic()
        contents, header_sha = make_pack(records, identity, context)
        header_seconds = time.monotonic() - header_started
        # Reject a concurrent mutation rather than publish a mixed generation.
        _, after, after_client = inspect_inputs()
        require(after == inventory_sha and worktree_identity(after_client) == stable_client,
                'Texture generation changed while indexing')
        saved = dict(expected, bytes=len(contents), sha256=hashlib.sha256(contents).hexdigest(),
                     original_header_bytes_sha256=header_sha)
        require(not target.is_symlink() and not marker.is_symlink(), 'Linked texture index output refused')
        atomic_write(target, contents)
        atomic_write(marker, canonical(saved) + b'\n')
    elapsed = time.monotonic() - started
    receipt = dict(saved, reused=reused, preparation_seconds=round(elapsed, 3),
                   inventory_scan_passes=inventory_passes,
                   preparation_phase_seconds={
                       'complete_inventory': round(inventory_seconds, 3),
                       'original_header_reads': round(header_seconds, 3),
                       'validation_and_publication': round(max(0,
                           elapsed - inventory_seconds - header_seconds), 3)},
                   legacy_identity_migrated=migrated,
                   native_layer_identity_migrated=native_migrated,
                   interrupted_envelope_recovered=interrupted_recovered,
                   native_file_opens_avoidable=len(records), original_texture_files_unchanged=True,
                   native_fallback_available=True)
    environment = {'COH_TEXTURE_HEADER_PACK': 'Z:' + str(target).replace('/', '\\'),
                   'COH_TEXTURE_HEADER_ID': identity, 'COH_TEXTURE_DIAGNOSTIC_DEDUP': '1',
                   'COH_TEXTURE_HEADER_ROOT': 'Z:' + str(work / 'data').replace('/', '\\'),
                   'COH_STARTUP_DIAGNOSTIC_BOUND': '1'}
    return receipt, environment
