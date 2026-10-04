#!/usr/bin/env python3
"""Add the pinned Atlas geometry/textures and refresh only private map caches."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import time
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
REUSE_MARKER = 'atlas-world-reuse.json'
REUSE_POLICY = 'pinned_world_filesystem_receipt_v1'
MAX_RECEIPT_BYTES = 4 * 1024**2
BLOCK_BYTES = 1024**2
MAX_MANIFEST_BYTES = 16 * 1024**2
MAX_ARCHIVE_BYTES = 256 * 1024**2
MAX_CACHE_FILES, MAX_CACHE_BYTES = 20000, 512 * 1024**2


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def fingerprint(info):
    # ctime catches ordinary rewrites even when the pinned mtime is restored.
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns,
        info.st_mode, info.st_uid, info.st_gid, info.st_nlink]


def checked_info(path, info, limit, *, installed=False):
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
        and info.st_uid == os.geteuid() and 0 < info.st_size <= limit,
        'Invalid world supplement file: ' + path.name)
    if installed:
        require(stat.S_IMODE(info.st_mode) == 0o444 and int(info.st_mtime) == client.CACHE_EPOCH,
            'World supplement permissions or timestamp differ: ' + path.name)
    return fingerprint(info)


def file_state(path, limit, *, installed=False):
    return checked_info(path, path.lstat(), limit, installed=installed)


def unchanged(path, descriptor, before):
    require(fingerprint(os.fstat(descriptor)) == before
        and fingerprint(path.lstat()) == before, 'World supplement changed while reading')


def read_regular(path, limit, *, installed=False):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = checked_info(path, os.fstat(descriptor), limit, installed=installed)
        with os.fdopen(descriptor, 'rb', closefd=False) as source:
            raw = source.read(limit + 1)
        require(len(raw) == before[2], 'World supplement changed while reading')
        unchanged(path, descriptor, before)
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
        and all(isinstance(pin, dict) and type(pin.get('bytes')) is int
            and 0 < pin['bytes'] <= 32 * 1024**2
            and isinstance(pin.get('sha256'), str) and re.fullmatch('[0-9a-f]{64}', pin['sha256'])
            for pin in files.values()) and sum(pin['bytes'] for pin in files.values()) == PAYLOAD_BYTES
        and hashlib.sha256(canonical(files)).hexdigest() == FILES_SHA256
        and manifest.get('archive') == {'filename': ARCHIVE, 'bytes': ARCHIVE_BYTES, 'sha256': ARCHIVE_SHA256}
        and manifest.get('runtime_visual_validated') is False and manifest.get('gameplay_validated') is False,
        'World supplement provenance or allowlist differs')
    return manifest


def hash_stream(source, context, limit):
    digest, total = hashlib.sha256(), 0
    while True:
        context.check()
        raw = source.read(BLOCK_BYTES)
        if not raw:
            break
        total += len(raw)
        require(total <= limit, 'World supplement grew while reading')
        digest.update(raw)
    return total, digest.hexdigest()


@contextmanager
def reviewed_archive(assets, files, expected_state, context):
    """Hash and decode from one descriptor, keeping only one bounded block in RAM."""
    path = assets / ARCHIVE
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = checked_info(path, os.fstat(descriptor), MAX_ARCHIVE_BYTES)
        require(before == expected_state and before[2] == ARCHIVE_BYTES,
            'World archive changed before verification')
        with os.fdopen(descriptor, 'rb', closefd=False) as source:
            size, digest = hash_stream(source, context, before[2])
            require(size == ARCHIVE_BYTES and digest == ARCHIVE_SHA256,
                'World archive differs from reviewed payload bytes')
            unchanged(path, descriptor, before)
            source.seek(0)
            with zipfile.ZipFile(source) as archive:
                validate_inventory(archive, files, context)
                yield archive
            unchanged(path, descriptor, before)
    finally:
        os.close(descriptor)


def validate_inventory(archive, files, context):
    entries = archive.infolist()
    require(len(entries) == FILE_COUNT and {entry.filename for entry in entries} == set(files),
        'World ZIP inventory differs')
    for entry in entries:
        context.check()
        pin = files[entry.filename]
        require(not entry.is_dir() and not entry.flag_bits & 1 and stat.S_ISREG(entry.external_attr >> 16)
            and entry.file_size == pin['bytes'] and 0 < entry.file_size <= 32 * 1024**2,
            'Invalid world ZIP payload')


def real_directory(path):
    require(path.is_absolute() and '..' not in path.parts, 'Expected an absolute private world directory')
    for current in [*reversed(path.parents), path]:
        require(stat.S_ISDIR(current.lstat().st_mode), 'Linked or non-directory world destination refused')


def hash_regular(path, limit, context, *, installed=False):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = checked_info(path, os.fstat(descriptor), limit, installed=installed)
        with os.fdopen(descriptor, 'rb', closefd=False) as source:
            size, digest = hash_stream(source, context, before[2])
        unchanged(path, descriptor, before)
        require(size == before[2], 'World supplement changed while reading')
        return size, digest, before
    finally:
        os.close(descriptor)


def verify_target(path, pin, context):
    try:
        size, digest, before = hash_regular(path, pin['bytes'], context, installed=True)
    except FileNotFoundError:
        return False
    require(size == pin['bytes'] and digest == pin['sha256'],
        'Existing world supplement conflicts with the reviewed payload: ' + path.name)
    return before


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
                size, digest, _ = hash_regular(entry, MAX_CACHE_BYTES, context)
                total += size
                require(total <= MAX_CACHE_BYTES, 'Private world cache refresh exceeds byte bound')
                result.append({'path': 'data/geobin/' + relative.as_posix(), 'bytes': size,
                    'sha256': digest})
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


def source_state(assets):
    result = {MANIFEST: file_state(assets / MANIFEST, MAX_MANIFEST_BYTES),
        ARCHIVE: file_state(assets / ARCHIVE, MAX_ARCHIVE_BYTES)}
    require(result[ARCHIVE][2] == ARCHIVE_BYTES, 'World archive size differs from reviewed payload bytes')
    return result


def reuse_identity(worktree, previous):
    receipt = worktree / 'client-work.json'
    client_work = None
    if receipt.exists() or receipt.is_symlink():
        client_work = hashlib.sha256(read_regular(receipt, 1024**2)).hexdigest()
    return {'format': 1, 'policy': REUSE_POLICY, 'source_commit': client.SOURCE,
        'data_commit': client.DATA, 'manifest_sha256': MANIFEST_SHA256,
        'archive_sha256': ARCHIVE_SHA256, 'files_sha256': FILES_SHA256,
        'file_count': FILE_COUNT, 'payload_bytes': PAYLOAD_BYTES, 'cache_policy': CACHE_POLICY,
        'normalized_mtime_epoch': client.CACHE_EPOCH, 'worktree': str(worktree),
        'directories': [[p.stat().st_dev, p.stat().st_ino] for p in (worktree, worktree / 'data')],
        'client_work_sha256': client_work,
        'installation_marker_sha256': hashlib.sha256(canonical(previous)).hexdigest()}


def reuse_state(worktree):
    path = worktree / REUSE_MARKER
    if not path.exists() and not path.is_symlink():
        return None
    raw = read_regular(path, MAX_RECEIPT_BYTES, installed=True)
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        return None
    # A malformed derived receipt only disables reuse. Owned/link/mode checks
    # remain mandatory before it can be replaced after content verification.
    return value if isinstance(value, dict) else None


def publish_reuse(worktree, value, context):
    """Replace only the owned derived receipt; the installation history is immutable."""
    target = worktree / REUSE_MARKER
    before = file_state(target, MAX_RECEIPT_BYTES, installed=True) if os.path.lexists(target) else None
    descriptor, name = tempfile.mkstemp(prefix='.world-reuse-', dir=worktree)
    temporary = Path(name)
    try:
        raw = canonical(value)
        require(len(raw) <= MAX_RECEIPT_BYTES, 'World reuse receipt exceeds bound')
        with os.fdopen(descriptor, 'wb') as output:
            output.write(raw); output.flush(); os.fsync(output.fileno())
        temporary.chmod(0o444)
        os.utime(temporary, (client.CACHE_EPOCH, client.CACHE_EPOCH))
        context.check()
        if before is None:
            client.publish_new_regular_file(temporary, target)
        else:
            require(file_state(target, MAX_RECEIPT_BYTES, installed=True) == before,
                'World reuse receipt changed before publication')
            os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def resolve_targets(worktree, files, context):
    directories, targets = {}, {}
    for name in sorted(files):
        context.check()
        target = worktree
        parts = Path(name).parts
        for index, part in enumerate(parts):
            actual = part
            if target.exists() or target.is_symlink():
                if target not in directories:
                    real_directory(target)
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
                        # The next iteration validates this directory. Each
                        # independent resolution pass checks it once.
                    else:
                        require(matches == [part], 'Case-conflicting world leaf refused')
            target /= actual
        targets[name] = target
    return targets


def output_state(worktree, targets, files, context):
    result = {}
    for name, target in targets.items():
        context.check()
        try:
            info = file_state(target, files[name]['bytes'], installed=True)
        except FileNotFoundError:
            info = None
        if info is not None:
            require(info[2] == files[name]['bytes'],
                'Existing world supplement conflicts with the reviewed payload: ' + target.name)
        result[name] = {'path': target.relative_to(worktree).as_posix(), 'stat': info}
    return result


def extract_payload(archive, name, pin, output, context):
    digest, size = hashlib.sha256(), 0
    with archive.open(name) as source:
        while True:
            context.check()
            raw = source.read(BLOCK_BYTES)
            if not raw:
                break
            size += len(raw)
            require(size <= pin['bytes'], 'World ZIP payload exceeds reviewed size: ' + name)
            digest.update(raw); output.write(raw)
    require(size == pin['bytes'] and digest.hexdigest() == pin['sha256'],
        'World ZIP payload differs: ' + name)


def verify_generation(worktree, assets, files, targets, inputs, outputs, identity, previous, context):
    """Never seal an output generation that changed after its pinned verification."""
    context.check()
    real_directory(assets)
    require(resolve_targets(worktree, files, context) == targets,
        'World destination changed during preparation')
    final_outputs = output_state(worktree, targets, files, context)
    require(all(row['stat'] is not None for row in final_outputs.values()),
        'World payload disappeared during preparation')
    require(final_outputs == outputs, 'World payload changed during preparation')
    require(source_state(assets) == inputs, 'World supplement inputs changed during preparation')
    require(marker_state(worktree) == previous, 'World installation marker changed during preparation')
    require(reuse_identity(worktree, previous) == identity, 'World preparation identity changed')


def remove_cache(target, row, context):
    real_directory(target.parent)
    descriptor = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parent = os.fstat(descriptor)
        size, digest, before = hash_regular(target, MAX_CACHE_BYTES, context)
        require(size == row['bytes'] and digest == row['sha256'],
            'Private world cache changed before refresh')
        real_directory(target.parent)
        current = target.parent.lstat()
        require((current.st_dev, current.st_ino) == (parent.st_dev, parent.st_ino)
            and file_state(target, MAX_CACHE_BYTES) == before, 'Private world cache path changed before refresh')
        context.check()
        # Keep the deletion anchored to the proved private directory, including
        # if its pathname changes after the final check.
        os.unlink(target.name, dir_fd=descriptor)
    finally:
        os.close(descriptor)


def install(worktree, assets, context):
    """Reuse proved immutable supplements, preserving inputs and one-time cache history."""
    started = time.monotonic()
    context.check()
    real_directory(worktree); real_directory(worktree / 'data'); real_directory(assets)
    inputs = source_state(assets)
    manifest = package(assets)
    require(source_state(assets) == inputs, 'World supplement inputs changed before preparation')
    files = manifest['files']
    previous, saved = marker_state(worktree), reuse_state(worktree)
    identity = reuse_identity(worktree, previous)
    targets = resolve_targets(worktree, files, context)
    outputs = output_state(worktree, targets, files, context)
    verified = {name: row['stat'] is not None for name, row in outputs.items()}
    require(previous is None or all(verified.values()), 'World marker exists but an installed payload is missing')
    reused = (previous is not None and saved == {'identity': identity, 'inputs': inputs, 'outputs': outputs})
    if not reused:
        for name, target in targets.items():
            context.check()
            proved = verify_target(target, files[name], context)
            verified[name] = bool(proved)
            outputs[name]['stat'] = proved if proved else None
        require(previous is None or all(verified.values()), 'World marker exists but an installed payload is missing')
    removed = cache_inventory(worktree, manifest['files'], context) if previous is None else []
    installed = decoded_bytes = 0
    if not reused:
        with reviewed_archive(assets, files, inputs[ARCHIVE], context) as archive:
            for name in sorted(files):
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
                        extract_payload(archive, name, files[name], output, context)
                        output.flush(); os.fsync(output.fileno())
                    temporary.chmod(0o444)
                    os.utime(temporary, (client.CACHE_EPOCH, client.CACHE_EPOCH))
                    context.check()
                    client.publish_new_regular_file(temporary, target)
                finally:
                    temporary.unlink(missing_ok=True)
                proved = verify_target(target, files[name], context)
                require(proved, 'World payload publication failed')
                outputs[name]['stat'] = proved
                installed += 1; decoded_bytes += files[name]['bytes']
    if previous is None:
        verify_generation(worktree, assets, files, targets, inputs, outputs, identity, previous, context)
        for row in removed:
            context.check()
            remove_cache(worktree / row['path'], row, context)
        refresh = {'policy': CACHE_POLICY, 'performed': True, 'removed_files': len(removed),
            'removed_bytes': sum(row['bytes'] for row in removed),
            'removed_inventory_sha256': hashlib.sha256(canonical(removed)).hexdigest(),
            'accepted_cache_archive_modified': False}
        verify_generation(worktree, assets, files, targets, inputs, outputs, identity, previous, context)
        previous = {'format': 1, 'manifest_sha256': MANIFEST_SHA256, 'archive_sha256': ARCHIVE_SHA256,
            'files_sha256': FILES_SHA256, 'cache_refresh': refresh, 'removed_cache_files': removed}
        context.check()
        publish_marker(worktree, previous)
    else:
        refresh = dict(previous['cache_refresh']) | {'performed': False}
    final_identity = dict(identity, installation_marker_sha256=hashlib.sha256(canonical(previous)).hexdigest())
    verify_generation(worktree, assets, files, targets, inputs, outputs, final_identity, previous, context)
    if not reused:
        publish_reuse(worktree, {'identity': final_identity, 'inputs': inputs, 'outputs': outputs}, context)
    return {'format': 1, 'scope': SCOPE, 'manifest_sha256': MANIFEST_SHA256,
        'archive_sha256': ARCHIVE_SHA256, 'file_count': FILE_COUNT, 'verified_file_count': FILE_COUNT,
        'payload_bytes': PAYLOAD_BYTES, 'files_sha256': FILES_SHA256,
        'installed_files': installed, 'reused_files': FILE_COUNT - installed,
        'worktree': worktree.name, 'normalized_mtime_epoch': client.CACHE_EPOCH,
        'imported_files_modified': False, 'worktree_identity_modified': False,
        'accepted_cache_archive_modified': False, 'cache_refresh': refresh,
        'runtime_visual_validated': False, 'visual_scope': manifest['visual_scope'],
        'reuse_validation': 'unchanged_filesystem_receipt' if reused else 'pinned_content_verification',
        'archive_read_bytes': 0 if reused else ARCHIVE_BYTES,
        'decoded_files': installed, 'decoded_payload_bytes': decoded_bytes,
        'preparation_elapsed_seconds': round(time.monotonic() - started, 6)}
