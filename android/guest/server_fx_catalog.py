"""Exact stock-schema FX projection for private server trees only.

The original client BIN remains unchanged. This supplement removes only the
Input/Condition children unused by the server, preserving every outer record,
name, scalar byte, dependency and schema CRC. Present unknown private caches
always take precedence. The ordinary native freshness/Parse6 loader remains.
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

PAYLOAD = 'server-fx-catalog.bin'
MANIFEST = 'server-fx-catalog-manifest.json'
ROLE = 'qualified_private_server_stock_parse6_fx_projection'
TARGET = 'data/bin/fxinfo.bin'
BASE = {'bytes': 58505496, 'sha256': '3b1af6d146db65aa2a00fa9dbe4502776409cdea15f94f717e5455a3cda5fe70'}
PROJECTED = {'bytes': 3380680, 'sha256': 'ab97aa3d9ec2a8edf1ea77d3c807e630e21c3d78555b3650bf80c1025bce8890'}
MAPSERVER = {'bytes': 6892032, 'sha256': '53ff6ee013690670abbaed39e44d66267caf8753486fbc05c64766a56d9c0713'}
MONORAIL_RECEIPT = 'e0ab383a91b83c258bfacbc44acf328f1a0c1435c0e4a385eb5ad643566f3178'
RETAINED_FX_SOURCES = {
    'Common/fxinfo.c': '61f36247ec92e56395cc6548689c34b1e341283a25c78490627327eafd5e9a13',
    'libs/UtilitiesLib/src/utils/textparser.c': '22be253a9e48e2565086e051d469ff92e68c2ae5a84802d8dc3d90713c766fef'}
QUALIFICATION_STATUS = 'stock_parse6_all_fx_ids_and_private_provider_verified'
MAX_MANIFEST = 16384
require, canonical, pin_bytes = caches.require, caches.canonical, caches.pin_bytes


class Cursor:
    def __init__(self, raw, position=0, end=None):
        self.raw, self.position, self.end = raw, position, len(raw) if end is None else end
    def take(self, count):
        require(type(count) is int and count >= 0 and self.position + count <= self.end,
                'FX table exceeds declared bounds')
        start = self.position; self.position += count
        return self.raw[start:self.position]
    def u32(self):
        return struct.unpack('<I', self.take(4))[0]
    def string(self):
        count = struct.unpack('<H', self.take(2))[0]
        require(0 < count <= 1024, 'FX name length differs')
        raw = self.take(count)
        require(b'\0' not in raw, 'FX name contains nul')
        require(self.take((-(count + 2)) % 4) == bytes((-(count + 2)) % 4), 'FX string padding differs')
        name = raw.decode('ascii')
        require(re.fullmatch(r'[A-Za-z0-9_&\-/ .~]+\.FX', name, re.I) is not None
                and ':' not in name and '\\' not in name
                and all(part not in ('', '.', '..') for part in name.split('/')), 'Unsafe FX name')
        return name
    def children(self):
        count = self.u32()
        require(count <= (self.end - self.position) // 4, 'FX child count exceeds record')
        for _ in range(count):
            length = self.u32()
            require(length >= 4, 'FX child table too short')
            self.take(length)
        return count


def inspect(raw, *, exact=True):
    """Decode only the audited envelope/outer fields; original children stay opaque.

    Exact source SHA authenticates their full contents. Each child's declared
    extent and every outer field/root length is checked independently through EOF.
    """
    require(isinstance(raw, bytes), 'FX input must be bytes')
    envelope = caches.inspect_parse6(raw)
    cursor = Cursor(raw, 12)
    for expected in (b'Parse6', b'Files1'):
        count = struct.unpack('<H', cursor.take(2))[0]
        require(cursor.take(count) == expected, 'FX Parse6 signature differs')
        require(cursor.take((-(count + 2)) % 4) == bytes((-(count + 2)) % 4), 'FX envelope padding differs')
    cursor.take(cursor.u32())
    root_offset = cursor.position
    root_length = cursor.u32()
    require(root_length == len(raw) - cursor.position, 'FX root length differs')
    count = cursor.u32()
    require(0 < count <= 19607, 'FX outer record count differs')
    rows = []; inputs = conditions = 0
    for _ in range(count):
        length = cursor.u32(); end = cursor.position + length
        require(end <= len(raw), 'FX outer record exceeds root')
        child = Cursor(raw, cursor.position, end); beginning = child.position
        name = child.string(); child.take(12); prefix = raw[beginning:child.position]
        inputs += child.children(); conditions += child.children()
        tail = child.take(40)
        require(child.position == end, 'FX outer scalar layout differs')
        rows.append({'name': name, 'prefix': prefix, 'tail': tail})
        cursor.position = end
    require(cursor.position == len(raw), 'FX trailing data')
    names = [row['name'] for row in rows]
    identity = {'schema_crc': envelope['schema_crc'], 'dependency_count': envelope['dependency_count'],
        'dependency_sha256': envelope['dependency_sha256'], 'outer_records': count,
        'unique_names': len({name.casefold() for name in names}),
        'ordered_name_scalar_sha256': hashlib.sha256(b''.join(row['prefix'] + row['tail'] for row in rows)).hexdigest()}
    if exact:
        require(pin_bytes(raw) in (BASE, PROJECTED), 'Unqualified FX input bytes')
        require(identity['schema_crc'] == '4cb7d9cb' and count == 19607
                and identity['unique_names'] == envelope['dependency_count'] == 19606, 'Accepted FX identity differs')
        require((inputs, conditions) == ((11387, 62570) if pin_bytes(raw) == BASE else (0, 0)),
                'FX child conservation differs')
    return {'identity': identity, 'names': names, 'input_records': inputs,
            'condition_records': conditions, 'root_offset': root_offset, 'rows': rows,
            'envelope': envelope}


def project(raw):
    base = inspect(raw)
    require(pin_bytes(raw) == BASE, 'Projection requires exact original client FX BIN')
    records = []
    for row in base['rows']:
        body = row['prefix'] + bytes(8) + row['tail']
        records.append(struct.pack('<I', len(body)) + body)
    body = struct.pack('<I', len(records)) + b''.join(records)
    result = raw[:base['root_offset']] + struct.pack('<I', len(body)) + body
    candidate = inspect(result)
    require(pin_bytes(result) == PROJECTED and candidate['identity'] == base['identity']
            and candidate['envelope'] == base['envelope'] | {'body_bytes': len(body)}, 'FX projection conservation differs')
    return result, base['identity']


def _regular(path, maximum, *, owner=None, shared_source=False, allow_empty=False):
    path = Path(path); info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and (0 if allow_empty else 1) <= info.st_size <= maximum
            and (info.st_nlink == 1 or shared_source and not info.st_mode & 0o222)
            and (owner is None or info.st_uid == owner), 'FX file is linked, unowned, special or oversized')
    return info


def _unchanged_leaf(info):
    # Reading may legitimately change atime. Integrity/lifetime checks use only
    # the inode, ownership, mode, links, extent and mutation timestamps.
    return tuple(getattr(info, name) for name in ('st_dev', 'st_ino', 'st_uid', 'st_mode',
                  'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


def read_manifest(assets):
    path = Path(assets) / MANIFEST
    _regular(path, MAX_MANIFEST, shared_source=True)
    value = json.loads(path.read_bytes(), object_pairs_hook=caches.unique_object)
    require(set(value) == {'format', 'role', 'repository_commit', 'base', 'projected', 'native_mapserver',
                          'identity', 'native_qualification', 'client_fx_changed', 'physical_timing_validated'}
            and value['format'] == 1 and value['role'] == ROLE
            and caches.HEX40.fullmatch(str(value['repository_commit']))
            and value['base'] == BASE and value['projected'] == PROJECTED and value['native_mapserver'] == MAPSERVER
            and value['client_fx_changed'] is False and value['physical_timing_validated'] is False,
            'FX supplement identity/scope differs')
    proof = value['native_qualification']
    require(isinstance(proof, dict) and set(proof) == {'status', 'report', 'indexed_names', 'native_schema_crc',
                'all_native_ids_equal', 'private_provider_verified', 'shipping_native_changed', 'startup_native_consumer'}
            and proof['status'] == QUALIFICATION_STATUS and proof['indexed_names'] == 19606
            and proof['native_schema_crc'] == '4cb7d9cb' and proof['all_native_ids_equal'] is True
            and proof['private_provider_verified'] is True and proof['shipping_native_changed'] is False
            and isinstance(proof['report'], dict) and set(proof['report']) == {'bytes', 'sha256'}
            and type(proof['report'].get('bytes')) is int and proof['report']['bytes'] > 0
            and caches.HEX64.fullmatch(str(proof['report'].get('sha256'))), 'Native FX qualification is required')
    candidate = proof['startup_native_consumer']
    require(isinstance(candidate,dict) and set(candidate) == {'mapserver','build_manifest','preload_processes',
                'normal_full_and_compact_preloads','private_provider_verified','certified_animation_path_observed',
                'physical_timing_validated'}
            and candidate['preload_processes'] == 2 and candidate['normal_full_and_compact_preloads'] is True
            and candidate['private_provider_verified'] is True and candidate['certified_animation_path_observed'] is True
            and candidate['physical_timing_validated'] is False, 'Actual startup native FX/animation preload proof is required')
    for pin in (candidate['mapserver'],candidate['build_manifest']):
        require(isinstance(pin,dict) and set(pin) == {'bytes','sha256'} and type(pin['bytes']) is int
                and 0 < pin['bytes'] < 64*1024**2 and caches.HEX64.fullmatch(str(pin['sha256'])),
                'Actual startup native component pin differs')
    require(candidate['mapserver'] != MAPSERVER, 'Original FX control cannot substitute the actual startup candidate')
    return value


def verify_package(assets):
    value = read_manifest(assets); path = Path(assets) / PAYLOAD
    _regular(path, PROJECTED['bytes'], shared_source=True)
    raw = path.read_bytes()
    require(pin_bytes(raw) == PROJECTED and inspect(raw)['identity'] == value['identity'], 'Projected FX payload differs')
    return value, raw


def verify_consumer(runtime, mapserver_package):
    """Keep the original FX control identity; admit only a typed additive reader.

    The animation supplement may change raw animation validation while the exact
    ordinary FX parser, registry and source algorithms remain untouched.
    """
    actual = caches.file_pin(Path(runtime)/'MapServer.exe')
    require(isinstance(mapserver_package, dict)
            and mapserver_package.get('native_monorail', {}).get('receipt_sha256') == MONORAIL_RECEIPT,
            'FX supplement requires the exact accepted station-aware MapServer ancestry')
    if actual == MAPSERVER:
        return caches.verify_mapserver_compatibility(Path(runtime)/'MapServer.exe', mapserver_package)
    require(isinstance(mapserver_package.get('native_map_startup'), dict),
            'FX supplement requires the exact accepted native startup consumer')
    import native_map_startup_contract as startup
    receipt = startup.embedded_receipt(mapserver_package)
    proof = startup.verify_current_map(Path(runtime)/'MapServer.exe', mapserver_package)
    previous = receipt.get('previous_mapserver', {})
    require({'bytes':previous.get('bytes',previous.get('size')), 'sha256':previous.get('sha256')} == MAPSERVER
            and all(receipt.get('build_input',{}).get('retained_sources_sha256',{}).get(name) == expected
                    for name, expected in RETAINED_FX_SOURCES.items()),
            'Native startup consumer changed the qualified FX source/parser')
    return dict(proof, native_fx_loader_source_unchanged=True, fx_native_control_mapserver=MAPSERVER)


def install(assets, runtime, *, context=None, mapserver_package=None):
    """Caller supplies APK-owned assets and an owned server runtime, never Game.

    Packaging recomputes the native proof from its raw evidence before admitting
    these APK assets. The manifest is not accepted from an external asset volume.
    """
    assets, runtime = Path(assets), Path(runtime)
    if not (assets / PAYLOAD).exists() and not (assets / MANIFEST).exists():
        return {'format': 1, 'status': 'ordinary_fx_loader', 'installed_files': 0}
    require(re.fullmatch(r'local-login-server-[0-9a-f]{32}(?:-kings-row|-atlas-park)?', runtime.name) is not None,
            'FX projection is restricted to the owned Atlas/Kings server namespace')
    value, raw = verify_package(assets)
    verify_consumer(runtime, mapserver_package)
    actual = caches.file_pin(runtime/'MapServer.exe')
    if actual != MAPSERVER:
        require(actual == value['native_qualification']['startup_native_consumer']['mapserver'],
                'FX supplement was qualified for different startup native bytes')
    owner = runtime.lstat().st_uid
    require(runtime.is_dir() and not runtime.is_symlink(), 'Owned FX server runtime required')
    for directory in (runtime / 'data', runtime / 'data/bin'):
        info = directory.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == owner, 'Private FX ancestor differs')
    target = runtime / TARGET
    if context is not None: context.check()
    snapshot = None
    if os.path.lexists(target):
        snapshot = _regular(target, caches.MAX_FILE, owner=owner, allow_empty=True)
        actual = caches.file_pin(target)
        if actual == PROJECTED:
            return {'format': 1, 'status': 'reused_verified_server_fx_projection', 'installed_files': 0,
                    'target': TARGET, 'projected': PROJECTED, 'client_fx_changed': False}
        if actual != BASE:
            return {'format': 1, 'status': 'preserved_existing_fx_native_fallback', 'installed_files': 0,
                    'target': TARGET, 'client_fx_changed': False}
    # No read-only import links can enter this path. Recheck the exact old inode
    # before atomic replacement; only authenticated full/compact bytes are eligible.
    descriptor, pending = tempfile.mkstemp(prefix='.fx-catalog-', dir=target.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.chmod(pending, 0o600); os.utime(pending, ns=(caches.EPOCH * 10**9,) * 2)
        if context is not None: context.check()
        if snapshot is not None:
            require(_unchanged_leaf(target.lstat()) == _unchanged_leaf(snapshot)
                    and caches.file_pin(target) == BASE, 'Private FX changed during projection install')
        else:
            require(not os.path.lexists(target), 'Private FX appeared during projection install')
        os.replace(pending, target)
        require(caches.file_pin(target) == PROJECTED, 'Installed FX projection differs')
    finally:
        if os.path.lexists(pending): os.unlink(pending)
    return {'format': 1, 'status': 'installed_verified_server_fx_projection', 'installed_files': 1,
            'target': TARGET, 'base': BASE, 'projected': PROJECTED, 'client_fx_changed': False,
            'native_freshness_loader_unchanged': True, 'physical_timing_validated': False}
