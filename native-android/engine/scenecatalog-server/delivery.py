#!/usr/bin/env python3
"""Bounded catalog transport admission and compile-qualified candidate staging.

No command launches a process, reads a server profile, deploys a runtime or grants
source/authentication/scene authority. Trusted pins are supplied independently of
untrusted transport. Private exclusively owned input/output directories required.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CATALOG_MAX = 32 * 1024 * 1024
JSON_MAX = 64 * 1024
CHUNK = 64 * 1024
COMPILE_ZIP_SHA256 = 'a57cb97659db151d66941fa8c00baadb1c70eeedd1c37d46565e687a778b6529'
COMPILE_RECEIPT_SHA256 = '303bad9e25ed52bf505e98dc568cfe92d58403ddd31f26fe579b40664ae4cdd6'
EXPORTER_SHA256 = 'f96f5d51467083a58523187760458ad77e6a48d7b696b0d090aafa8e94e95f39'
SOURCE_REVISION = '887bef22f5f6403d8589ac00a1269c9438e263a6'
BINDING_SCHEMA = 'coh-catalog-delivery-binding-v1'


class Refused(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise Refused(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def sha(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), 'DIGEST')
    return value


def uint(value, maximum=0xffffffff, nonzero=False):
    require(type(value) is int and (1 if nonzero else 0) <= value <= maximum, 'INTEGER')
    return value


def path(value):
    result = Path(os.path.abspath(value))
    require(not any(p.is_symlink() for p in (result, *result.parents)), 'LINK')
    return result


def regular(value):
    result = path(value)
    info = result.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'REGULAR')
    return result


def read(value, maximum):
    source = regular(value)
    require(source.stat().st_size <= maximum, 'LIMIT')
    with source.open('rb') as stream:
        raw = stream.read(maximum + 1)
    require(len(raw) <= maximum, 'LIMIT')
    return raw


def hash_file(value, maximum):
    source = regular(value)
    require(source.stat().st_size <= maximum, 'LIMIT')
    total, result = 0, hashlib.sha256()
    with source.open('rb') as stream:
        while True:
            chunk = stream.read(CHUNK)
            if not chunk:
                break
            total += len(chunk)
            require(total <= maximum, 'LIMIT')
            result.update(chunk)
    return total, result.hexdigest()


def json_object(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'DUPLICATE')
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=pairs,
                           parse_constant=lambda _: require(False, 'NUMBER'))
    except (UnicodeError, ValueError, RecursionError):
        raise Refused('JSON') from None
    require(type(value) is dict, 'OBJECT')
    return value


def exact(value, keys):
    require(type(value) is dict and set(value) == set(keys), 'FIELDS')


def binding(raw, expected_digest):
    """Validate external trusted context. Never infer trust from the sidecar itself."""
    require(digest(raw) == sha(expected_digest), 'BINDING_HASH')
    item = json_object(raw)
    exact(item, ('schema', 'catalog', 'generation', 'groups', 'provenance'))
    require(item['schema'] == BINDING_SCHEMA, 'SCHEMA')
    uint(item['generation'], nonzero=True)
    catalog = item['catalog']
    exact(catalog, ('bytes', 'sha256'))
    uint(catalog['bytes'], CATALOG_MAX, True)
    require(catalog['bytes'] >= 48, 'CATALOG_SIZE')
    sha(catalog['sha256'])
    groups = item['groups']
    exact(groups, ('files', 'definitions_crc', 'references_crc', 'active_roots', 'receipt_sha256'))
    uint(groups['files'], 1024)
    uint(groups['definitions_crc']); uint(groups['references_crc'])
    uint(groups['active_roots'], 65536)
    sha(groups['receipt_sha256'])
    provenance = item['provenance']
    exact(provenance, ('source_revision', 'exporter_sha256', 'asset_inventory_sha256',
                      'profile_snapshot_sha256', 'map_identity_sha256', 'capture_receipt_sha256'))
    require(provenance['source_revision'] == SOURCE_REVISION and
            provenance['exporter_sha256'] == EXPORTER_SHA256, 'EXPORTER_IDENTITY')
    for key in ('asset_inventory_sha256', 'profile_snapshot_sha256',
                'map_identity_sha256', 'capture_receipt_sha256'):
        sha(provenance[key])
    return item


def inspect_catalog(catalog, item):
    """Storage admission only; the existing native load MUST follow before use."""
    total, actual = hash_file(catalog, CATALOG_MAX)
    require(total == item['catalog']['bytes'] and actual == item['catalog']['sha256'], 'CATALOG_HASH')
    with regular(catalog).open('rb') as stream:
        raw = stream.read(48)
    require(len(raw) == 48 and raw[:8] == b'COHCAT01', 'HEADER')
    version, size, extent, generation, files, definitions, defs_crc, refs_crc, roots, reserved = struct.unpack('<10I', raw[8:])
    require(version == 1 and size == 48 and extent == total and reserved == 0, 'HEADER')
    require(generation == item['generation'] and generation != 0 and definitions <= 65536, 'GENERATION')
    groups = item['groups']
    require((files, defs_crc, refs_crc, roots) == (groups['files'], groups['definitions_crc'],
            groups['references_crc'], groups['active_roots']), 'GROUPS_BINDING')
    return {'bytes': total, 'sha256': actual, 'generation': generation,
            'files': files, 'definitions': definitions, 'active_roots': roots,
            'definitions_crc': defs_crc, 'references_crc': refs_crc}


def absent_directory(value):
    destination = path(value)
    require(destination.parent.is_dir() and not destination.exists(), 'DESTINATION')
    return destination


def emit_json(destination, value):
    with destination.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def copy_verified(source, destination, expected, maximum):
    """Verify the copied bytes, not just an earlier read; never replace destination."""
    hasher, total = hashlib.sha256(), 0
    with regular(source).open('rb') as src, destination.open('xb') as dst:
        while True:
            chunk = src.read(CHUNK)
            if not chunk:
                break
            total += len(chunk)
            require(total <= maximum, 'LIMIT')
            hasher.update(chunk); dst.write(chunk)
        dst.flush(); os.fsync(dst.fileno())
    require(hasher.hexdigest() == expected, 'COPY_HASH')
    return total


def clean_created(destination, names):
    # Remove ONLY files this invocation created in its own new directory.
    for name in reversed(names):
        (destination / name).unlink(missing_ok=True)
    destination.rmdir()


def admit(catalog, binding_path, expected_binding_sha256, destination):
    raw = read(binding_path, JSON_MAX)
    item = binding(raw, expected_binding_sha256)
    observation = inspect_catalog(catalog, item)
    output = absent_directory(destination)
    receipt = {'schema': 'coh-catalog-storage-admission-v1', 'storage_admitted': True,
               'binding_sha256': digest(raw), 'catalog': observation,
               'native_decode_completed': False, 'provenance_independently_verified': False,
               'authentic_capture_established': False, 'graph_published': False,
               'renderer_authorized': False, 'apk_changed': False,
               'trust_requirement': 'binding_digest_and_provenance_receipts_validated_by_integration_owner'}
    created = []
    output.mkdir(mode=0o700)
    try:
        created.append('catalog.cohcat')
        count = copy_verified(catalog, output / created[-1], item['catalog']['sha256'], CATALOG_MAX)
        require(count == item['catalog']['bytes'], 'COPY_SIZE')
        created.append('binding.json')
        with (output / created[-1]).open('xb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        created.append('storage-admission.json')
        emit_json(output / created[-1], receipt)
    except Exception:
        clean_created(output, created)
        raise
    return receipt


def inspect_candidate(archive, source_root):
    """Admit only the already independently reviewed exact ten-member ZIP."""
    size, actual = hash_file(archive, 4 * 1024 * 1024)
    require(size == 3286082 and actual == COMPILE_ZIP_SHA256, 'COMPILE_ARCHIVE')
    root = path(source_root)
    with zipfile.ZipFile(regular(archive)) as bundle:
        names = bundle.namelist()
        require(len(names) == len(set(names)) == 10, 'BUNDLE_MEMBERS')
        require(sum(row.file_size for row in bundle.infolist()) < 9 * 1024 * 1024, 'BUNDLE_LIMIT')
        raw = bundle.read('compile-only-receipt.json')
        require(digest(raw) == COMPILE_RECEIPT_SHA256, 'COMPILE_RECEIPT')
        receipt = json_object(raw)
        require(set(names) == {'compile-only-receipt.json', *receipt['artifacts']}, 'BUNDLE_MEMBERS')
        for name, expected in receipt['artifacts'].items():
            data = bundle.read(name)
            require(len(data) == expected['bytes'] and digest(data) == expected['sha256'], 'MEMBER_HASH')
        require(receipt['source_revision'] == SOURCE_REVISION and receipt['passed'] is True and
                receipt['runtime_executed'] is False and receipt['deployed'] is False, 'COMPILE_SCOPE')
        for name, local in (
            ('coh_source_catalog_export.inc', root / 'native-android/engine/scenecatalog/source_export.inc'),
            ('coh_source_catalog_sink.inc', root / 'native-android/engine/scenecatalog-server/source_sink.inc')):
            staged = bundle.read('source/MapServer/src/group/' + name)
            require(read(local, 1024 * 1024).replace(b'\r\n', b'\n') == staged.replace(b'\r\n', b'\n'), 'SOURCE_DRIFT')
        executable = bundle.read('MapServer.exe')
        require(digest(executable) == EXPORTER_SHA256, 'PE_HASH')
    return raw, executable


def candidate(archive, source_root, destination):
    raw, executable = inspect_candidate(archive, source_root)
    output = absent_directory(destination)
    plan = {'schema': 'coh-disposable-catalog-candidate-v1',
            'source_revision': SOURCE_REVISION, 'exporter_sha256': EXPORTER_SHA256,
            'compile_archive_sha256': COMPILE_ZIP_SHA256, 'binary_rebuilt': False,
            'nonshipping': True, 'deployed': False, 'runtime_executed': False,
            'authentic_catalog_captured': False, 'actual_profile_compatibility_verified': False,
            'accepted_runtime_modified': False,
            'output_environment': 'COH_NATIVE_SCENE_CATALOG_OUTPUT',
            'generation_environment': 'COH_NATIVE_SCENE_CATALOG_GENERATION',
            'maximum_catalog_bytes': CATALOG_MAX,
            'requirements': ['approved isolated copy of complete matching server assets and profile',
                             'independent Windows or compatible Win32 runtime and server dependencies',
                             'separate DB service and ports; no connection to production DB',
                             'private exclusively owned output directory and stable loaded world',
                             'independent source, asset, map and profile identity inventory',
                             'complete capture and GROUPS receipts before catalog admission'],
            'rollback': 'stop only the disposable owned processes; discard only the owned candidate/capture directories'}
    output.mkdir(mode=0o700)
    created = []
    try:
        for name, data in (('MapServer.exe', executable), ('compile-only-receipt.json', raw)):
            created.append(name)
            with (output / name).open('xb') as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
        created.append('deployment-plan.json'); emit_json(output / created[-1], plan)
    except Exception:
        clean_created(output, created)
        raise
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    stage = sub.add_parser('candidate')
    stage.add_argument('--compile-archive', type=Path, required=True)
    stage.add_argument('--source-root', type=Path, default=ROOT)
    stage.add_argument('--output', type=Path, required=True)
    accept = sub.add_parser('admit')
    accept.add_argument('--catalog', type=Path, required=True)
    accept.add_argument('--binding', type=Path, required=True)
    accept.add_argument('--binding-sha256', required=True)
    accept.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'candidate':
            result = candidate(args.compile_archive, args.source_root, args.output)
        else:
            result = admit(args.catalog, args.binding, args.binding_sha256, args.output)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RecursionError, zipfile.BadZipFile):
        # Neither credentials, filesystem paths nor untrusted source data in diagnostics.
        print(json.dumps({'schema': 1, 'passed': False, 'status': 'delivery_refused'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
