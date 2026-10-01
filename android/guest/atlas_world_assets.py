#!/usr/bin/env python3
"""Add the pinned Atlas geometry/textures and refresh only private map caches."""
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import zipfile

import client_startup_diagnostic as client

require = client.require
MANIFEST = 'atlas-world-supplement-manifest.json'
ARCHIVE = 'atlas-world-supplement.zip'
MANIFEST_SHA256 = '204a7f0da20cdbbb4ea8b8e2d9e9b5ebccfaa10d5213fff03bbb85cc7f9e3c86'
ARCHIVE_SHA256 = 'c7ed82aaaf987410fa471e19ee2b19115ef660892a06f79e2e2401d5672b095f'
ARCHIVE_BYTES, PAYLOAD_BYTES, FILE_COUNT = 207803201, 318611871, 2904
FILES_SHA256 = '1e61d6991a83949750184b2b8cc6496310730d53598c66b58445ec9b2f6d69d4'
SCOPE = 'atlas_world_geometry_texture_supplement'
CACHE_POLICY = 'once_per_world_manifest_private_atlas_geobin_and_supplemented_object_library_only'
MARKER = 'atlas-world-installed.json'
MAX_MANIFEST_BYTES = 16 * 1024**2
MAX_ARCHIVE_BYTES = 256 * 1024**2
MAX_CACHE_FILES, MAX_CACHE_BYTES = 20000, 512 * 1024**2


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def read_regular(path, limit, *, installed=False):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
            and before.st_uid == os.geteuid() and 0 < before.st_size <= limit,
            'Invalid world supplement file: ' + path.name)
        if installed:
            require(stat.S_IMODE(before.st_mode) == 0o444 and int(before.st_mtime) == client.CACHE_EPOCH,
                'World supplement permissions or timestamp differ: ' + path.name)
        with os.fdopen(descriptor, 'rb', closefd=False) as source:
            raw = source.read(limit + 1)
        after = os.fstat(descriptor)
        require(len(raw) == before.st_size and (after.st_size, after.st_mtime_ns, after.st_nlink)
            == (before.st_size, before.st_mtime_ns, 1), 'World supplement changed while reading')
        return raw
    finally:
        os.close(descriptor)


def safe_payload(name):
    path = PurePosixPath(name)
    return (name == name.casefold() and path.as_posix() == name and '..' not in path.parts
        and '\\' not in name and ':' not in name and name.isascii()
        and (name.startswith('data/object_library/') and path.suffix == '.geo'
             or name.startswith('data/texture_library/') and path.suffix == '.texture'))


def package(assets):
    manifest_raw = read_regular(assets / MANIFEST, MAX_MANIFEST_BYTES)
    require(hashlib.sha256(manifest_raw).hexdigest() == MANIFEST_SHA256,
        'World manifest differs from reviewed metadata')
    manifest = json.loads(manifest_raw)
    files = manifest.get('files', {})
    require(manifest.get('format') == 1 and manifest.get('scope') == SCOPE
        and manifest.get('source_commit') == client.SOURCE and manifest.get('data_commit') == client.DATA
        and manifest.get('file_count') == FILE_COUNT and manifest.get('payload_bytes') == PAYLOAD_BYTES
        and isinstance(files, dict) and len(files) == FILE_COUNT and all(safe_payload(name) for name in files)
        and hashlib.sha256(canonical(files)).hexdigest() == FILES_SHA256
        and manifest.get('archive') == {'filename': ARCHIVE, 'bytes': ARCHIVE_BYTES, 'sha256': ARCHIVE_SHA256}
        and manifest.get('runtime_visual_validated') is False and manifest.get('gameplay_validated') is False,
        'World supplement provenance or allowlist differs')
    raw = read_regular(assets / ARCHIVE, MAX_ARCHIVE_BYTES)
    require(len(raw) == ARCHIVE_BYTES and hashlib.sha256(raw).hexdigest() == ARCHIVE_SHA256,
        'World archive differs from reviewed payload bytes')
    payloads = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        require(len(entries) == FILE_COUNT and {entry.filename for entry in entries} == set(files),
            'World ZIP inventory differs')
        for entry in entries:
            pin = files[entry.filename]
            require(not entry.is_dir() and not entry.flag_bits & 1 and stat.S_ISREG(entry.external_attr >> 16)
                and entry.file_size == pin['bytes'] and 0 < entry.file_size <= 32 * 1024**2,
                'Invalid world ZIP payload')
            content = archive.read(entry)
            require(len(content) == pin['bytes'] and hashlib.sha256(content).hexdigest() == pin['sha256'],
                'World ZIP payload differs: ' + entry.filename)
            payloads[entry.filename] = content
    require(sum(map(len, payloads.values())) == PAYLOAD_BYTES, 'World payload byte bound differs')
    return manifest, payloads


def real_directory(path):
    require(path.is_absolute() and '..' not in path.parts, 'Expected an absolute private world directory')
    for current in [*reversed(path.parents), path]:
        require(stat.S_ISDIR(current.lstat().st_mode), 'Linked or non-directory world destination refused')


def verify_target(path, pin):
    try:
        raw = read_regular(path, pin['bytes'], installed=True)
    except FileNotFoundError:
        return False
    require(len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256'],
        'Existing world supplement conflicts with the reviewed payload: ' + path.name)
    return True


def cache_path_allowed(relative, geometry):
    relative = relative.as_posix().casefold()
    path = PurePosixPath(relative)
    if path.suffix not in ('.bin', '.dep', '.bounds'):
        return False
    if relative.startswith('maps/city_zones/city_01_01/'):
        return True
    return path.with_suffix('.geo').as_posix() in geometry


def cache_inventory(worktree, files, context):
    """Inspect only real, owned private geobin leaves; imported roots are untouched."""
    root = worktree / 'data/geobin'
    if not root.exists() and not root.is_symlink():
        return []
    real_directory(root)
    geometry = {name.removeprefix('data/') for name in files if name.endswith('.geo')}
    pending, scanned, total, result = [root], 0, 0, []
    while pending:
        context.check()
        current = pending.pop()
        real_directory(current)
        for entry in current.iterdir():
            info = entry.lstat()
            require(not stat.S_ISLNK(info.st_mode), 'Linked private world cache refused')
            if stat.S_ISDIR(info.st_mode):
                pending.append(entry)
            else:
                scanned += 1
                require(scanned <= MAX_CACHE_FILES and stat.S_ISREG(info.st_mode), 'Private world cache scan exceeds bound')
                relative = entry.relative_to(root)
                if not cache_path_allowed(relative, geometry):
                    continue
                raw = read_regular(entry, MAX_CACHE_BYTES)
                total += len(raw)
                require(total <= MAX_CACHE_BYTES, 'Private world cache refresh exceeds byte bound')
                result.append({'path': 'data/geobin/' + relative.as_posix(), 'bytes': len(raw),
                    'sha256': hashlib.sha256(raw).hexdigest()})
    return sorted(result, key=lambda row: row['path'])


def marker_state(worktree):
    path = worktree / MARKER
    if not path.exists() and not path.is_symlink():
        return None
    value = json.loads(read_regular(path, 4 * 1024**2, installed=True))
    require(value.get('format') == 1 and value.get('manifest_sha256') == MANIFEST_SHA256
        and value.get('archive_sha256') == ARCHIVE_SHA256 and value.get('files_sha256') == FILES_SHA256
        and value.get('cache_refresh', {}).get('policy') == CACHE_POLICY,
        'Existing world installation marker differs')
    refresh, removed = value['cache_refresh'], value.get('removed_cache_files')
    require(isinstance(removed, list) and len(removed) <= MAX_CACHE_FILES
        and refresh.get('performed') is True and refresh.get('accepted_cache_archive_modified') is False
        and refresh.get('removed_files') == len(removed)
        and refresh.get('removed_bytes') == sum(row['bytes'] for row in removed)
        and 0 <= refresh['removed_bytes'] <= MAX_CACHE_BYTES
        and refresh.get('removed_inventory_sha256') == hashlib.sha256(canonical(removed)).hexdigest(),
        'Existing world cache refresh receipt differs')
    for row in removed:
        path = PurePosixPath(row['path'])
        require(path.as_posix() == row['path'] and row['path'].startswith('data/geobin/')
            and '..' not in path.parts and '\\' not in row['path'] and ':' not in row['path']
            and isinstance(row['bytes'], int) and 0 < row['bytes'] <= MAX_CACHE_BYTES
            and re.fullmatch('[0-9a-f]{64}', row['sha256']), 'Invalid prior world cache refresh inventory')
    return value


def publish_marker(worktree, value):
    descriptor, name = tempfile.mkstemp(prefix='.world-marker-', dir=worktree)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(canonical(value)); output.flush(); os.fsync(output.fileno())
        temporary.chmod(0o444)
        os.utime(temporary, (client.CACHE_EPOCH, client.CACHE_EPOCH))
        client.publish_new_regular_file(temporary, worktree / MARKER)
    finally:
        temporary.unlink(missing_ok=True)


def install(worktree, assets, context):
    """Preserve original leaves, verify every supplement, and refresh derived caches once."""
    real_directory(worktree); real_directory(worktree / 'data')
    manifest, payloads = package(assets)
    directories, verified, targets = {}, {}, {}
    for name in sorted(payloads):
        context.check()
        target = worktree
        parts = Path(name).parts
        for index, part in enumerate(parts):
            actual = part
            if target.exists() or target.is_symlink():
                real_directory(target)
                if target not in directories:
                    names = {}
                    for item in target.iterdir():
                        names.setdefault(item.name.casefold(), []).append(item.name)
                    directories[target] = names
                matches = directories[target].get(part.casefold(), [])
                require(len(matches) <= 1, 'Ambiguous case-conflicting world destination refused')
                if matches:
                    if index < len(parts) - 1:
                        # Text inputs establish canonical directory spellings.
                        # Reuse that spelling instead of creating case aliases.
                        actual = matches[0]
                        real_directory(target / actual)
                    else:
                        require(matches == [part], 'Case-conflicting world leaf refused')
            target /= actual
        targets[name] = target
        verified[name] = verify_target(target, manifest['files'][name])
    previous = marker_state(worktree)
    require(previous is None or all(verified.values()), 'World marker exists but an installed payload is missing')
    removed = cache_inventory(worktree, manifest['files'], context) if previous is None else []
    installed = 0
    for name in sorted(payloads):
        context.check()
        if verified[name]:
            continue
        target, parent = targets[name], worktree
        for part in target.relative_to(worktree).parts[:-1]:
            parent /= part
            parent.mkdir(mode=0o700, exist_ok=True); real_directory(parent)
        descriptor, name_tmp = tempfile.mkstemp(prefix='.world-pending-', dir=target.parent)
        temporary = Path(name_tmp)
        try:
            with os.fdopen(descriptor, 'wb') as output:
                output.write(payloads[name]); output.flush(); os.fsync(output.fileno())
            temporary.chmod(0o444)
            os.utime(temporary, (client.CACHE_EPOCH, client.CACHE_EPOCH))
            client.publish_new_regular_file(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        require(verify_target(target, manifest['files'][name]), 'World payload publication failed')
        installed += 1
    if previous is None:
        for row in removed:
            context.check()
            target = worktree / row['path']
            raw = read_regular(target, MAX_CACHE_BYTES)
            require(len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'],
                'Private world cache changed before refresh')
            target.unlink()
        refresh = {'policy': CACHE_POLICY, 'performed': True, 'removed_files': len(removed),
            'removed_bytes': sum(row['bytes'] for row in removed),
            'removed_inventory_sha256': hashlib.sha256(canonical(removed)).hexdigest(),
            'accepted_cache_archive_modified': False}
        previous = {'format': 1, 'manifest_sha256': MANIFEST_SHA256, 'archive_sha256': ARCHIVE_SHA256,
            'files_sha256': FILES_SHA256, 'cache_refresh': refresh, 'removed_cache_files': removed}
        publish_marker(worktree, previous)
    else:
        refresh = dict(previous['cache_refresh']) | {'performed': False}
    return {'format': 1, 'scope': SCOPE, 'manifest_sha256': MANIFEST_SHA256,
        'archive_sha256': ARCHIVE_SHA256, 'file_count': FILE_COUNT, 'verified_file_count': FILE_COUNT,
        'payload_bytes': PAYLOAD_BYTES, 'files_sha256': FILES_SHA256,
        'installed_files': installed, 'reused_files': FILE_COUNT - installed,
        'worktree': worktree.name, 'normalized_mtime_epoch': client.CACHE_EPOCH,
        'imported_files_modified': False, 'worktree_identity_modified': False,
        'accepted_cache_archive_modified': False, 'cache_refresh': refresh,
        'runtime_visual_validated': False, 'visual_scope': manifest['visual_scope']}
