#!/usr/bin/env python3
"""Verify exact native server caches and seed only missing private cache files.

This module never accepts templates, attributes, DB-ID maps or source inputs as
payloads. Incompatible or absent donors leave the ordinary native loader in
charge; existing device-generated cache files always take precedence.
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


def build_expected_identity(runtime_data, mapserver_path):
    require(file_pin(mapserver_path)['sha256'] == MAPSERVER_SHA256, 'Server-cache executable identity differs')
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
