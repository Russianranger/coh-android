"""Install only the qualified native Atlas graph into the private server tree.

The native generator is a host-only tool and never ships. World inputs are
proved once against the exact geometry/group/trick inventory; subsequent starts
reuse the proof only while all readonly input and graph fingerprints match.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import tempfile
import time
import zipfile

ARCHIVE = 'atlas-beacons.zip'
MANIFEST = 'atlas-beacon-manifest.json'
ROLE = 'authentic_native_atlas_beacon_graph'
MAP = 'maps/city_zones/city_01_01/city_01_01.txt'
GRAPH = 'data/server/' + MAP + '.v8.bcn'
DATE = GRAPH + '.date'
MARKER = 'data/server/atlas-beacon-installed.json'
POLICY = 'exact_native_atlas_graph_two_proven_geometry_profiles_v2'
# Frozen only after the hosted producer completes real generation/readback/CRC/routes.
MANIFEST_SHA256 = 'pending_native_generation'
ARCHIVE_SHA256 = 'pending_native_generation'
ARCHIVE_BYTES = 0
STOCK_MAPSERVER_SHA256 = '6a5bf60b2130c31df74f1767510de65c581652caa90f639a5a6e4a9453b47d36'
SOURCE_COMMIT = '0b75ade0c801735e10c5798f641948a45cc50488'
DATA_COMMIT = 'd51533ec8e6a9cf726b9214968077a05fdcf19f3'
BASE_ARCHIVE = {'bytes': 615541018, 'sha256': '28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07'}
WORLD_MANIFEST_SHA256 = '204a7f0da20cdbbb4ea8b8e2d9e9b5ebccfaa10d5213fff03bbb85cc7f9e3c86'
VISUAL_GEOMETRY_SHA256 = '208393ade4edbb9608e200fc7103279217ce95a0cc316eac8018bfe558f54f1f'
VISUAL_SOURCE_MANIFEST = {'bytes': 42553059, 'sha256': 'e1f1702c9d5b38f38bb324b1171ac7aeaa5cba7e12072dd8face4efbc09a5fa3'}
VISUAL_OBJECT_GEOMETRY_SHA256 = 'c5eddbe19511356d1c9eb26890728b169db6989917da9e1375b6f1692f41bb43'
OPTIONAL_GEOS = 406
PROFILES = ('base_world', 'base_world_visual')
MAX_MANIFEST = 8 * 1024 * 1024
MAX_GRAPH = 128 * 1024 * 1024
MAX_INPUTS = 12288
EPOCH = 1767225600


def require(condition, message):
    if not condition: raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def regular(path, limit, *, readonly=False):
    path = Path(path)
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 < info.st_size <= limit,
            'Linked, special, empty or oversized beacon package file')
    require(not readonly or not info.st_mode & 0o222, 'Beacon proof requires readonly input')
    return info


def pin(path, context=None):
    digest = hashlib.sha256(); total = 0
    with Path(path).open('rb') as stream:
        for raw in iter(lambda: stream.read(1024 * 1024), b''):
            if context is not None: context.check()
            total += len(raw); digest.update(raw)
    return {'bytes': total, 'sha256': digest.hexdigest()}


def safe(name):
    return (isinstance(name, str) and name and name.isascii() and '\\' not in name and ':' not in name
            and PurePosixPath(name).as_posix() == name and not name.startswith('/')
            and all(part not in ('', '.', '..') for part in name.split('/')))


def input_name(name):
    return safe(name) and (
        name.startswith('data/object_library/') and name.endswith(('.geo', '.txt'))
        or name.startswith('data/maps/city_zones/city_01_01/') and name.endswith('.txt')
        or name.startswith('data/tricks/') and name.endswith('.txt'))


def read_manifest(path):
    regular(path, MAX_MANIFEST)
    raw = Path(path).read_bytes()
    require(re.fullmatch('[0-9a-f]{64}', MANIFEST_SHA256) and hashlib.sha256(raw).hexdigest() == MANIFEST_SHA256,
            'Atlas beacon manifest has not been qualified or differs')
    value = json.loads(raw)
    files, inputs, native = value.get('files'), value.get('input_files'), value.get('native')
    optional, profiles = value.get('optional_input_files'), value.get('input_profiles')
    require(value.get('format') == 2 and value.get('role') == ROLE and value.get('map') == MAP
            and value.get('source_commit') == SOURCE_COMMIT and value.get('data_commit') == DATA_COMMIT
            and value.get('stock_mapserver_sha256') == STOCK_MAPSERVER_SHA256
            and value.get('runtime_graph_readback') is True
            and value.get('physical_npc_pathing_validated') is False,
            'Atlas native graph provenance differs')
    require(isinstance(files, dict) and set(files) == {GRAPH, DATE}
            and files[DATE].get('bytes') == 12 and 18 < files[GRAPH].get('bytes', 0) <= MAX_GRAPH,
            'Only the native Atlas v8 graph and v9 sidecar may be installed')
    require(isinstance(inputs, dict) and 100 < len(inputs) <= MAX_INPUTS and all(input_name(name) for name in inputs)
            and 'data/' + MAP in inputs
            and hashlib.sha256(canonical(inputs)).hexdigest() == value.get('input_files_sha256'),
            'Atlas collision/group source identity differs')
    require(isinstance(optional, dict) and len(optional) == OPTIONAL_GEOS
            and all(input_name(name) and name.startswith('data/object_library/') and name.endswith('.geo')
                    for name in optional) and not set(inputs).intersection(optional)
            and len(inputs) + len(optional) <= MAX_INPUTS
            and hashlib.sha256(canonical(optional)).hexdigest() == VISUAL_OBJECT_GEOMETRY_SHA256,
            'Exact optional original object geometry identity differs')
    require(all(isinstance(record, dict) and set(record) == {'bytes', 'sha256'}
                and type(record['bytes']) is int and 0 < record['bytes'] <= MAX_GRAPH
                and re.fullmatch('[0-9a-f]{64}', str(record['sha256']))
                for record in list(files.values()) + list(inputs.values()) + list(optional.values())), 'Invalid native input/payload pin')
    identity = value.get('input_identity', {})
    require(identity.get('asset_archive') == BASE_ARCHIVE
            and identity.get('world_manifest', {}).get('sha256') == WORLD_MANIFEST_SHA256
            and identity.get('visual_geometry_sha256') == VISUAL_GEOMETRY_SHA256
            and identity.get('visual_source_manifest') == VISUAL_SOURCE_MANIFEST
            and identity.get('visual_object_geometry_sha256') == VISUAL_OBJECT_GEOMETRY_SHA256,
            'Native graph was generated from a different world/geometry supplement')
    require(isinstance(native, dict) and native.get('native_full_graph_readback_verified') is True
            and native.get('fresh_ordinary_world_crc_verified') is True
            and native.get('native_pathfinder_successes') == 32 and native.get('date_version') == 9
            and 1000 < native.get('connected_beacons', 0) <= native.get('combat_beacons', 0) <= 1000000
            and native.get('ground_connections', 0) > 1000 and native.get('grid_blocks', 0) > 0
            and re.fullmatch('0x[0-9a-f]{8}', str(native.get('full_world_crc'))),
            'Native generation, full reader, CRC or path proofs are incomplete')
    require(isinstance(profiles, dict) and set(profiles) == set(PROFILES), 'Both fresh native profiles are required')
    for profile in PROFILES:
        selected = inputs if profile == 'base_world' else {**inputs, **optional}
        require(profiles[profile] == {'native': native,
                    'input_files_sha256': hashlib.sha256(canonical(selected)).hexdigest()},
                'Fresh cold/warm native CRC, graph readback or path proofs differ')
    return value


def select_profile(runtime, manifest, context):
    """Accept only the two complete server inventories proved in fresh processes."""
    runtime = Path(runtime); optional = manifest['optional_input_files']
    present = 0
    for name in optional:
        context.check()
        present += os.path.lexists(runtime / name)
    require(present in (0, len(optional)), 'Partial optional Atlas geometry has no native profile proof')
    profile = 'base_world_visual' if present else 'base_world'
    selected = (manifest['input_files'] if not present else {**manifest['input_files'], **optional})
    # The enclosing server cache verifies immutable links; this finite inventory
    # also refuses extra source leaves whose collision contribution was not proved.
    actual = set()
    for relative in ('data/object_library', 'data/maps/city_zones/city_01_01', 'data/tricks'):
        root = runtime / relative
        require(root.is_dir() and not root.is_symlink(), 'Private Atlas source directory required')
        for path in root.rglob('*'):
            context.check()
            require(not (path.is_symlink() and path.is_dir()), 'Linked Atlas source directory refused')
            suffixes = ('.geo', '.txt') if relative == 'data/object_library' else ('.txt',)
            if path.suffix.lower() in suffixes and not path.is_dir():
                actual.add(path.relative_to(runtime).as_posix())
                require(len(actual) <= MAX_INPUTS, 'Atlas source inventory exceeds proof bound')
    require(actual == set(selected), 'Actual Atlas source inventory has no qualified native profile')
    return profile, selected


def fingerprint(path, *, immutable_input=False):
    path = Path(path)
    # Imported leaves may be the existing verified per-file links. Their targets
    # are already constrained by the enclosing private client/server worktree.
    info = path.stat() if immutable_input else regular(path, MAX_GRAPH, readonly=True)
    require(stat.S_ISREG(info.st_mode) and not info.st_mode & 0o222,
            'Atlas graph inputs must retain immutable leaf permissions')
    return {'device': info.st_dev, 'inode': info.st_ino, 'bytes': info.st_size,
            'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns,
            'mode': stat.S_IMODE(info.st_mode)}


def fingerprints(runtime, names, context, *, immutable_input=False):
    result = {}
    for name in names:
        context.check()
        result[name] = fingerprint(runtime / name, immutable_input=immutable_input)
    return result


def private_target(runtime, name):
    require(name in (GRAPH, DATE, MARKER), 'Unexpected beacon target')
    current = Path(runtime)
    require(current.is_dir() and not current.is_symlink(), 'Beacon runtime root must be private')
    for part in Path(name).parts[:-1]:
        current /= part
        if not current.exists(): current.mkdir(mode=0o700)
        require(current.is_dir() and not current.is_symlink(), 'Linked beacon parent refused')
    target = runtime / name
    require(not target.is_symlink(), 'Linked beacon target refused')
    return target


def atomic_bytes(path, raw):
    fd, name = tempfile.mkstemp(prefix='.atlas-beacon-', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        temporary.chmod(0o400); os.utime(temporary, (EPOCH, EPOCH))
        os.replace(temporary, path)
    finally:
        if temporary.exists(): temporary.unlink()


def install(archive, manifest_path, runtime, *, context, imported_inputs_readonly):
    started = time.monotonic(); runtime = Path(runtime)
    require(imported_inputs_readonly is True, 'Beacon installation requires the qualified readonly private world')
    value = read_manifest(manifest_path)
    profile, selected = select_profile(runtime, value, context)
    require(pin(runtime / 'MapServer.exe', context)['sha256'] == STOCK_MAPSERVER_SHA256,
            'A different MapServer cannot consume this qualified native graph')
    inputs = fingerprints(runtime, selected, context, immutable_input=True)
    targets = {name: private_target(runtime, name) for name in value['files']}
    marker = private_target(runtime, MARKER)
    prior = None
    if marker.exists():
        try:
            regular(marker, MAX_MANIFEST)
            prior = json.loads(marker.read_bytes())
        except (ValueError, OSError, json.JSONDecodeError): pass
    if (isinstance(prior, dict) and prior.get('format') == 2 and prior.get('policy') == POLICY
            and prior.get('manifest_sha256') == MANIFEST_SHA256 and prior.get('input_fingerprints') == inputs
            and prior.get('server_geometry_profile') == profile
            and all(path.exists() for path in targets.values())
            and prior.get('graph_fingerprints') == fingerprints(runtime, targets, context)):
        return {'format': 2, 'status': 'reused_verified_graph', 'map': MAP, 'server_geometry_profile': profile,
                'full_world_crc': value['native']['full_world_crc'], 'installed_files': 0,
                'input_files_checked': len(inputs), 'input_payload_bytes_hashed': 0,
                'archive_decoded': False, 'fingerprint_walk': True, 'input_inventory_walk': True,
                'preparation_elapsed_seconds': round(time.monotonic() - started, 6)}
    total = 0
    for name, expected in selected.items():
        context.check()
        require(pin(runtime / name, context) == expected, 'Actual Atlas collision/group input differs: ' + name)
        total += expected['bytes']
    require(inputs == fingerprints(runtime, selected, context, immutable_input=True)
            and select_profile(runtime, value, context)[0] == profile,
            'Atlas inputs changed while establishing native graph compatibility')
    regular(archive, 2 * MAX_GRAPH)
    require(ARCHIVE_BYTES > 0 and pin(archive, context) == {'bytes': ARCHIVE_BYTES, 'sha256': ARCHIVE_SHA256},
            'Atlas beacon archive differs from the qualified native producer')
    installed = 0
    with zipfile.ZipFile(archive) as source:
        entries = source.infolist(); names = [entry.filename for entry in entries]
        require(len(names) == 3 and set(names) == set(value['files']) | {MANIFEST}
                and len({name.casefold() for name in names}) == 3
                and all(not entry.is_dir() and not entry.flag_bits & 1
                        and stat.S_IFMT(entry.external_attr >> 16) in (0, stat.S_IFREG)
                        for entry in entries), 'Unsafe or unrelated beacon archive member')
        require(source.read(MANIFEST) == Path(manifest_path).read_bytes(), 'Embedded beacon manifest differs')
        for name, expected in value['files'].items():
            context.check(); require(source.getinfo(name).file_size == expected['bytes'], 'Beacon member size differs')
            raw = source.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected, 'Beacon member hash differs')
            if name == DATE:
                version, newest, crc = struct.unpack('<iII', raw)
                require(version == 9 and f'0x{crc:08x}' == value['native']['full_world_crc'],
                        'Beacon sidecar differs from the verified native loaded-world CRC')
            target = targets[name]
            if target.exists():
                regular(target, MAX_GRAPH)
                require(pin(target, context) == expected, 'An existing different beacon graph is preserved')
                target.chmod(0o400)
            else:
                atomic_bytes(target, raw); installed += 1
    record = {'format': 2, 'policy': POLICY, 'manifest_sha256': MANIFEST_SHA256,
              'server_geometry_profile': profile,
              'input_fingerprints': inputs,
              'graph_fingerprints': fingerprints(runtime, targets, context)}
    atomic_bytes(marker, canonical(record))
    return {'format': 2, 'status': 'installed_verified_graph', 'map': MAP, 'server_geometry_profile': profile,
            'full_world_crc': value['native']['full_world_crc'], 'installed_files': installed,
            'input_files_checked': len(inputs), 'input_payload_bytes_hashed': total,
            'archive_decoded': True, 'fingerprint_walk': True, 'input_inventory_walk': True,
            'native_graph_readback_qualified': True,
            'preparation_elapsed_seconds': round(time.monotonic() - started, 6)}
