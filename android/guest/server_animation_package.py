#!/usr/bin/env python3
"""Exact stored Pig v2 animation closure for the unchanged Win32 server loader.

The archive changes storage only. Native animReadTrackFile, skeleton linking,
lastFrame calculation and all movement/combat semantics remain unchanged. Loose
immutable animations remain installed, and are the fallback if no pack exists.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import tempfile

import server_cache_package as caches

PIGG = 'server-animations.pigg'
MANIFEST = 'server-animation-manifest.json'
ROLE = 'exact_native_server_animation_storage'
INVENTORY_SHA256 = 'c3ac97e4a18d17bfa3de529c24597a668d099329cfdb663021688e248ec43a38'
ASSET_MANIFEST_SHA256 = 'cf96742b1b65306356df69d065fcfb5bda0986ec8700d47ae1422452a1c0db7f'
ASSET_ARCHIVE_SHA256 = caches.compatibility_identity()['asset_archive_sha256']
ANIMATION_COUNT = 5878
ANIMATION_BYTES = 88380730
MAX_PACK = 128 * 1024 * 1024
MAX_FILE = 8 * 1024 * 1024
MAX_MANIFEST = 2 * 1024 * 1024
MAX_METADATA = 24 * 1024 * 1024
HEADER = struct.Struct('<IHHHHI')
ENTRY = struct.Struct('<IiIIIIi16sI')
NAME = re.compile(r'player_library/animations/[a-z0-9_&\-/]+\.anim\Z')
require, canonical, file_pin = caches.require, caches.canonical, caches.file_pin


def identity():
    return {'format': 1, 'source_commit': caches.compatibility_identity()['source_commit'],
            'data_commit': caches.compatibility_identity()['data_commit'],
            'mapserver_sha256': caches.MAPSERVER_SHA256,
            'asset_archive_sha256': ASSET_ARCHIVE_SHA256,
            'asset_manifest_sha256': ASSET_MANIFEST_SHA256,
            'animation_inventory_sha256': INVENTORY_SHA256,
            'normalized_mtime_epoch': caches.EPOCH,
            'native_format': 'Pig-v2-stored-original-Win32-anim-with-cached-header',
            'loader': 'stock-fileOpen-PigFileWrapper-animReadTrackFile'}


def safe_name(name):
    return (isinstance(name, str) and NAME.fullmatch(name) is not None
            and all(part not in ('', '.', '..') for part in name.split('/')))


def validate_inventory(files, *, exact=True):
    require(isinstance(files, dict) and 0 < len(files) <= ANIMATION_COUNT, 'Invalid animation inventory')
    for name, record in files.items():
        require(safe_name(name) and isinstance(record, dict)
                and set(record) == {'bytes', 'sha256', 'timestamp'}
                and type(record['bytes']) is int and 596 <= record['bytes'] <= MAX_FILE
                and isinstance(record['sha256'], str) and caches.HEX64.fullmatch(record['sha256'])
                and record['timestamp'] == caches.EPOCH, 'Animation record differs: ' + str(name))
    if exact:
        require(len(files) == ANIMATION_COUNT and sum(x['bytes'] for x in files.values()) == ANIMATION_BYTES
                and hashlib.sha256(canonical(files)).hexdigest() == INVENTORY_SHA256,
                'Exact accepted animation closure differs')
    return files


def read_manifest(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_MANIFEST,
            'Missing, linked or oversized animation manifest')
    document = json.loads(path.read_bytes(), object_pairs_hook=caches.unique_object)
    require(set(document) == {'format', 'role', 'repository_commit', 'identity', 'files', 'pigg',
                              'loose_inputs_preserved', 'native_client_or_server_recompiled',
                              'android_execution_validated', 'physical_startup_timing_validated'}
            and document['format'] == 1 and document['role'] == ROLE
            and isinstance(document['repository_commit'], str)
            and caches.HEX40.fullmatch(document['repository_commit'])
            and document['identity'] == identity()
            and document['loose_inputs_preserved'] is True
            and document['native_client_or_server_recompiled'] is False
            and document['android_execution_validated'] is False
            and document['physical_startup_timing_validated'] is False, 'Animation compatibility differs')
    validate_inventory(document['files'])
    return document


def pool(source, flag, *, maximum):
    raw = source.read(12)
    require(len(raw) == 12, 'Truncated Pig pool header')
    observed, count, size = struct.unpack('<III', raw)
    require(observed == flag and 0 <= count <= ANIMATION_COUNT and count * 4 <= size <= maximum,
            'Invalid Pig pool bounds')
    data = source.read(size)
    require(len(data) == size, 'Truncated Pig pool')
    entries, pos = [], 0
    for _ in range(count):
        require(pos + 4 <= size, 'Truncated Pig pool item')
        length, = struct.unpack_from('<I', data, pos); pos += 4
        require(0 < length <= size - pos, 'Invalid Pig pool item length')
        entries.append(data[pos:pos + length]); pos += length
    require(pos == size, 'Pig pool trailing bytes')
    return entries


def verify_pigg(path, files, *, exact=True, context=None):
    """Read every original byte and cached header; no manifest booleans certify it."""
    files = validate_inventory(files, exact=exact)
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_PACK,
            'Missing, linked or oversized animation Pig')
    digest = hashlib.sha256()
    with path.open('rb') as source:
        raw = source.read(HEADER.size)
        require(len(raw) == HEADER.size and HEADER.unpack(raw) == (0x123, 2, 2, 16, 48, len(files)),
                'Unsupported animation Pig layout')
        table = source.read(ENTRY.size * len(files))
        require(len(table) == ENTRY.size * len(files), 'Truncated animation Pig table')
        names = pool(source, 0x6789, maximum=MAX_METADATA)
        headers = pool(source, 0x9ABC, maximum=MAX_METADATA)
        require(len(names) == len(files) and len(headers) == len(files), 'Pig pool inventory differs')
        metadata_bytes = source.tell()
        require(metadata_bytes <= MAX_METADATA, 'Animation Pig metadata exceeds bound')
        expected_names = sorted(files, key=str.upper)
        payload_bytes = 0
        for index, name in enumerate(expected_names):
            if context is not None: context.check()
            flag, name_id, size, timestamp, offset, reserved, header_id, md5, packed = ENTRY.unpack_from(table, index * ENTRY.size)
            record = files[name]
            require(flag == 0x3456 and name_id == index and header_id == index
                    and names[index] == name.encode('ascii') + b'\0'
                    and size == record['bytes'] and timestamp == record['timestamp']
                    and offset == metadata_bytes + payload_bytes and reserved == 0 and packed == 0,
                    'Animation Pig native file record differs: ' + name)
            body = source.read(size)
            require(len(body) == size and hashlib.sha256(body).hexdigest() == record['sha256']
                    and hashlib.md5(body).digest() == md5, 'Animation Pig payload differs: ' + name)
            header_size, = struct.unpack_from('<i', body)
            require(596 <= header_size <= size and headers[index] == body[:header_size],
                    'Animation Pig cached native header differs: ' + name)
            payload_bytes += size
        require(not source.read(1), 'Animation Pig trailing payload')
        source.seek(0)
        for block in iter(lambda: source.read(1024 * 1024), b''):
            if context is not None: context.check()
            digest.update(block)
    return {'bytes': path.stat().st_size, 'sha256': digest.hexdigest(),
            'metadata_bytes': metadata_bytes, 'original_animation_bytes': payload_bytes,
            'animation_count': len(files)}


def verify_package(pigg, manifest, *, context=None):
    document = read_manifest(manifest)
    require(verify_pigg(pigg, document['files'], context=context) == document['pigg'],
            'Animation Pig pin differs')
    return document


def install(pigg, manifest, runtime, *, context=None):
    """Optional private top-level ./piggs storage; never mutate data or DB files."""
    runtime = Path(runtime)
    if not Path(pigg).exists() and not Path(manifest).exists():
        return {'format': 1, 'installed': False, 'fallback': 'ordinary_loose_animation_loader'}
    document = verify_package(pigg, manifest, context=context)
    require(runtime.is_dir() and not runtime.is_symlink()
            and file_pin(runtime / 'MapServer.exe')['sha256'] == document['identity']['mapserver_sha256'],
            'Animation runtime/native identity differs')
    directory = runtime / 'piggs'
    if not directory.exists(): directory.mkdir(mode=0o700)
    require(directory.is_dir() and not directory.is_symlink()
            and directory.stat().st_uid == runtime.stat().st_uid
            and set(path.name for path in directory.iterdir()) <= {PIGG},
            'Foreign or unowned animation Pig directory')
    target = directory / PIGG
    expected = {key: document['pigg'][key] for key in ('bytes', 'sha256')}
    if target.exists() or target.is_symlink():
        info = target.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == runtime.stat().st_uid
                and file_pin(target) == expected, 'Existing animation Pig differs')
        return {'format': 1, 'installed': True, 'reused': True, 'pigg': document['pigg'],
                'loose_inputs_preserved': True, 'fallback': 'ordinary_loose_animation_loader'}
    descriptor, pending = tempfile.mkstemp(prefix='.animation-', dir=directory)
    try:
        with os.fdopen(descriptor, 'wb') as output, Path(pigg).open('rb') as source:
            for block in iter(lambda: source.read(1024 * 1024), b''):
                if context is not None: context.check()
                output.write(block)
            output.flush(); os.fsync(output.fileno())
        require(file_pin(pending) == expected, 'Animation Pig copy differs')
        os.chmod(pending, 0o400); os.utime(pending, (caches.EPOCH, caches.EPOCH))
        require(not os.path.lexists(target), 'Animation Pig destination appeared during copy')
        os.rename(pending, target)
    finally:
        if os.path.exists(pending): os.unlink(pending)
    return {'format': 1, 'installed': True, 'reused': False, 'pigg': document['pigg'],
            'loose_inputs_preserved': True, 'fallback': 'ordinary_loose_animation_loader'}
