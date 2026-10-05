#!/usr/bin/env python3
"""Qualify the exact genuine Atlas graph retained from native generation.

The failed overall run honestly remains failed: its primary real generator
completed and the former NONE geometry assumption was disproved. This bounded
lane authenticates that output, reconstructs required exact source geometry,
and runs two fresh native CRC/full-readback/32-route proofs. Host tools never ship.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import prepare_atlas_beacon_generator_source as producer

DONOR = {'bytes': 1535592811, 'sha256': '81f199d6380faa09261a85efea6fd3abca6ed58749b8cc68c75d1cd579d454a4'}
DONOR_COMMIT = 'be955678b4b82f889b31c4071b3b979b0aef6771'
STOCK_MAPSERVER = '6a5bf60b2130c31df74f1767510de65c581652caa90f639a5a6e4a9453b47d36'
ARCHIVE = 'atlas-beacons.zip'
MANIFEST = 'atlas-beacon-manifest.json'
REPORT = 'atlas-beacon-generation-report.json'
GRAPH = 'data/server/maps/city_zones/city_01_01/city_01_01.txt.v8.bcn'
DATE = GRAPH + '.date'
MAX_LOG = 128 * 1024 * 1024
MAX_GRAPH = 128 * 1024 * 1024
HEARTBEAT_SECONDS = 60
MAX_FAILURE_TAIL = 8192
VISUAL_OBJECT_GEOS = 406
PROFILES = ('required_geometry_cold', 'client_visual_reopen')
COMMON_INPUT_SHA256 = '3bd8cd7305d8066adb2e2ae88bf761d4bcac546c786257027e0b7d28f5a15a08'
REQUIRED_INPUT_SHA256 = '039f2a761ac11c01338ec1060a8656c6a9c833dc47b294a65d4dfa90648555f8'
QUALIFICATION_VISUAL_ARCHIVE = {'bytes': 859075775, 'sha256': '5f91b7d4ebe91e6a547923d702e2fcd56d7fc1d36fb7bffbb66463562d977d60'}
QUALIFICATION_VISUAL_MANIFEST = {'bytes': 48591999, 'sha256': '8587015400e1af639e2118649f0d9c77a089d564bfe2c97cbf9d80baaee5f9a2'}
VISUAL_MANIFEST_PIN = {'bytes': 42553059, 'sha256': 'e1f1702c9d5b38f38bb324b1171ac7aeaa5cba7e12072dd8face4efbc09a5fa3'}
VISUAL_GEO_SOURCE_SHA256 = '208393ade4edbb9608e200fc7103279217ce95a0cc316eac8018bfe558f54f1f'
VISUAL_OBJECT_SOURCE_SHA256 = 'c5eddbe19511356d1c9eb26890728b169db6989917da9e1375b6f1692f41bb43'
HOST_COMPILE_REUSE = {
    'run_id': 37357540374, 'job_id': 111924222126,
    'repository_commit': '780b030b73fef34b5000b7303ba4fe828020a229',
    'artifact': {'id': 11366950301, 'bytes': 16542485,
                 'sha256': 'd37e6d13bd619e9c39014b784d193773830ad950d2abd3e252f025588c58020b'},
}

PRIMARY_RECOVERY = {
    "run_id": 37377053417,
    "job_id": 111989203448,
    "repository_commit": "3124723b93b4ae83b211f9319ffa8d6d8a3e851d",
    "run_conclusion": "failure",
    "primary_generation_server_returncode": 0,
    "generator": {"bytes": 6880256, "sha256": "243184510a89e39f765c9aa8ff49b1ce9807c4a92ac626e96d1814850cc18e8b"},
    "build_input": {"bytes": 13166, "sha256": "904e1fa5d24b05abab36f771641be82c7fe897e14d410bbeaf3187c49ef492f9"},
    "artifact": {
        "id": 11379217768,
        "bytes": 33296543,
        "sha256": "a23fe422656874009013f56bc8a41a243a0511afb1d4fcb828196c03054731a4"
    },
    "graph": {
        "bytes": 39069559,
        "sha256": "6a3c9a6661a07cc3aec3a11baa9ca29395cc9b64d783b21e58282b2eb20845f8"
    },
    "date": {
        "bytes": 12,
        "sha256": "ce64be4b49e4a8a4e61f01b31c651e603dc955551fb5c471ad3b75d2bb4f1711"
    },
    "native": {
        "full_world_crc": "0xb0c21ded",
        "combat_beacons": 163544,
        "connected_beacons": 163527,
        "ground_connections": 1805050,
        "raised_connections": 2698868,
        "grid_blocks": 602,
        "native_pathfinder_successes": 32,
        "date_version": 9,
        "date_latest_data_time": 0,
        "fresh_ordinary_world_crc_verified": True,
        "native_full_graph_readback_verified": True
    }
}
PRIMARY_GENERATION_SOURCES = {
    "tools/prepare_atlas_beacon_generator_source.py": {
        "bytes": 4867,
        "sha256": "34836711f431f7e7a74e7226a791ed462a2add65cfaa36d956b59c0838ffe10a"
    },
    "tools/android/interactive/generate_atlas_beacons.py": {
        "bytes": 44424,
        "sha256": "eb89c170f0780e0b3ac61b0bd6e957b3f07b928dbeaf1c91653e7977720f16c2"
    },
    "patches/atlas-beacons/0001-host-only-atlas-generator.patch": {
        "bytes": 11155,
        "sha256": "e7684871c8a6680be1d25bcf2c352d1c57c1ac9c9f64b41a9714cd3a0df95eb9"
    },
    "android/atlas/src/main/java/io/github/russianranger/cohatlas/AtlasAssetImporter.java": {
        "bytes": 37139,
        "sha256": "e5da4a7a4a0cd3a55be56055f5556537e66095b190d466d9c9838990a0f5c46b"
    },
    "tools/android/atlas/java/io/github/russianranger/cohatlas/HostImport.java": {
        "bytes": 4090,
        "sha256": "1164a1df37d8502b663dd4e51b0b7cb17d3d107d58812416503643ed93de3896"
    },
    "assets/reference-inputs-receipt.json": {
        "bytes": 1014,
        "sha256": "ff1b88a63803d945b00ebbab8f05412f159d1dc3368134e2b6149d6803ffc198"
    },
    "source-target.json": {
        "bytes": 1011,
        "sha256": "042ea89d24d116981602b543c8d17eda8a97f518cac79a33688eefcc15222c5f"
    },
    "android/guest/atlas_world_assets.py": {
        "bytes": 24268,
        "sha256": "4189cff59dce2f9da6d045d754ecc1fda56a09241124f842566b1da69b5865b6"
    }
}

FRESH_NATIVE = re.compile(rb'COH_ATLAS_BEACON_FRESH_WORLD_V1 crc=(0x[0-9a-fA-F]{8})')
NATIVE = re.compile(rb'COH_ATLAS_BEACON_NATIVE_V1 crc=(0x[0-9a-fA-F]{8}) combat=(\d+) connected=(\d+) ground=(\d+) raised=(\d+) blocks=(\d+) paths=(\d+)')
GENERATION_SOURCES = (
    'tools/prepare_atlas_beacon_generator_source.py',
    'tools/android/interactive/generate_atlas_beacons.py', producer.PATCH,
    'android/atlas/src/main/java/io/github/russianranger/cohatlas/AtlasAssetImporter.java',
    'tools/android/atlas/java/io/github/russianranger/cohatlas/HostImport.java',
    'assets/reference-inputs-receipt.json', 'source-target.json',
    'android/guest/atlas_world_assets.py',
)


def require(condition, message):
    if not condition: raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def pin(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): digest.update(block)
    return {'bytes': Path(path).stat().st_size, 'sha256': digest.hexdigest()}


def safe(name):
    require(isinstance(name, str) and name and not name.startswith('/') and '\\' not in name
            and ':' not in name and all(part not in ('', '.', '..') for part in name.split('/')),
            'Unsafe package member')
    return name


def copy_pinned(stream, target, expected, *, overwrite=False):
    target.parent.mkdir(parents=True, exist_ok=True)
    if overwrite and target.exists(): target.chmod(0o600)
    with target.open('wb' if overwrite else 'xb') as dest: shutil.copyfileobj(stream, dest, 1024 * 1024)
    require(pin(target) == {key: expected[key] for key in ('bytes', 'sha256')}, 'Payload pin differs: ' + target.name)


def extract_assets(apk, receipt, output):
    require(pin(apk) == DONOR, 'Exact 0.13.13 donor differs')
    value = json.loads(receipt.read_bytes())
    require(value['repository_commit'] == DONOR_COMMIT and value['version_name'] == '0.13.13'
            and value['signature_verified'] is True and value['payload_bytes_verified'] is True
            and {key: value[key] for key in ('bytes', 'sha256')} == DONOR, 'Donor publication receipt differs')
    output.mkdir()
    with zipfile.ZipFile(apk) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())), 'Duplicate donor APK members')
        for name, expected in value['payloads'].items():
            if not name.startswith('assets/'): continue
            safe(name); require(name.count('/') == 2, 'Unexpected asset nesting')
            target = output / ('atlas' if name.startswith('assets/atlas/') else 'runtime') / Path(name).name
            with archive.open(name) as source: copy_pinned(source, target, expected)
    return value


def import_data(assets, archive, work, evidence):
    expected = json.loads((ROOT / 'assets/reference-inputs-receipt.json').read_bytes())
    require(pin(archive) == {'bytes': expected['archive_bytes'], 'sha256': expected['archive_sha256']},
            'Reviewed base asset archive differs')
    classes = work / 'classes'; classes.mkdir()
    sources = [ROOT / 'android/atlas/src/main/java/io/github/russianranger/cohatlas/AtlasAssetImporter.java',
               ROOT / 'tools/android/atlas/java/io/github/russianranger/cohatlas/HostImport.java']
    with (evidence / 'java-import.log').open('wb') as log:
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8', '-d', str(classes),
                        *map(str, sources)], check=True, stdout=log, stderr=subprocess.STDOUT, timeout=120)
        subprocess.run(['java', '-Xmx512m', '-cp', str(classes), 'io.github.russianranger.cohatlas.HostImport',
                        str(assets / 'atlas'), str(archive), str(work / 'imported'), str(evidence / 'import.properties')],
                       check=True, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
    props = dict(line.split('=', 1) for line in (evidence / 'import.properties').read_text().splitlines() if '=' in line)
    require(props['status'] == 'passed' and props['count'] == '173011' and props['bytes'] == '2977730517',
            'Exact native import receipt differs')
    return Path(props['data.directory'])


def extract_tar(path, runtime, manifest_name):
    with tarfile.open(path, 'r:gz') as archive:
        entries = archive.getmembers()
        require(all(entry.isfile() and not entry.issym() and not entry.islnk() for entry in entries), 'Nonregular TAR member')
        names = [safe(entry.name) for entry in entries]
        manifest = json.loads(archive.extractfile(manifest_name).read())
        require(len(names) == len(set(names)) and set(names) == set(manifest['files']) | {manifest_name}, 'TAR closure differs')
        for entry in entries:
            if entry.name == manifest_name: continue
            copy_pinned(archive.extractfile(entry), runtime / entry.name, manifest['files'][entry.name], overwrite=True)
    return manifest


def overlay_zip(path, manifest_path, runtime):
    manifest = json.loads(manifest_path.read_bytes())
    expected = manifest['archive']
    require(pin(path) == {key: expected[key] for key in ('bytes', 'sha256')}, 'Supplement ZIP pin differs')
    files = manifest['files']
    with zipfile.ZipFile(path) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())) and set(archive.namelist()) == set(files), 'Supplement closure differs')
        for name, expected in files.items():
            safe(name); target = runtime / name
            if target.exists(): continue  # Exactly the shipped missing-only precedence.
            with archive.open(name) as source: copy_pinned(source, target, expected)
    return manifest


WORLD_CASE_SOURCE = ROOT / 'android/guest/atlas_world_assets.py'
_WORLD_RESOLVE_TARGETS = None


class HostPathContext:
    def check(self): pass


def resolve_world_targets(runtime, names):
    """Use exactly the shipped resolver without importing Android diagnostics."""
    global _WORLD_RESOLVE_TARGETS
    if _WORLD_RESOLVE_TARGETS is None:
        source = ast.parse(WORLD_CASE_SOURCE.read_text(encoding='utf-8'))
        required = ('real_directory', 'resolve_targets')
        functions = {node.name: node for node in source.body
                     if isinstance(node, ast.FunctionDef) and node.name in required}
        require(set(functions) == set(required), 'Authoritative world case resolver is missing')
        namespace = {'Path': Path, 'stat': stat, 'require': require}
        module = ast.Module(body=[functions[name] for name in required], type_ignores=[])
        exec(compile(ast.fix_missing_locations(module), str(WORLD_CASE_SOURCE), 'exec'), namespace)
        _WORLD_RESOLVE_TARGETS = namespace['resolve_targets']
    runtime = Path(runtime).absolute()
    require(runtime.is_dir() and not runtime.is_symlink(), 'Owned native input directory required')
    return _WORLD_RESOLVE_TARGETS(runtime, names, HostPathContext())


def canonical_input_name(name):
    """Normalize directory keys only; retain exact immutable leaf spelling."""
    safe(name)
    parts = name.split('/')
    return '/'.join([*(part.casefold() for part in parts[:-1]), parts[-1]])


def physical_pins(records):
    """Project rich donor source records to the exact on-disk byte identity."""
    require(isinstance(records, dict), 'Physical source records must be a mapping')
    result = {}
    for name, record in records.items():
        safe(name)
        require(isinstance(record, dict) and type(record.get('bytes')) is int
                and 0 < record['bytes'] <= MAX_LOG
                and re.fullmatch('[0-9a-f]{64}', str(record.get('sha256'))),
                'Invalid physical source pin')
        result[name] = {key: record[key] for key in ('bytes', 'sha256')}
    return result


def audit_visual_geometry_manifest(donor_apk):
    """Audit the actual frozen donor without native import or model generation."""
    donor_apk = Path(donor_apk)
    require(pin(donor_apk) == DONOR, 'Actual preflight public donor differs')
    with zipfile.ZipFile(donor_apk) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())), 'Duplicate donor APK member')
        name = 'assets/runtime/client-visual-manifest.json'
        require(archive.getinfo(name).file_size == VISUAL_MANIFEST_PIN['bytes'], 'Donor visual manifest size differs')
        raw = archive.read(name)
    require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == VISUAL_MANIFEST_PIN,
            'Actual donor visual source manifest differs')
    value = json.loads(raw)
    geo = {name: record for name, record in value['files'].items() if name.endswith('.geo')}
    original = {name: record for name, record in geo.items() if name.startswith('data/object_library/')}
    optional = physical_pins(original)
    require(len(geo) == 927 and len(optional) == VISUAL_OBJECT_GEOS
            and hashlib.sha256(canonical(geo)).hexdigest() == VISUAL_GEO_SOURCE_SHA256
            and hashlib.sha256(canonical(original)).hexdigest() == VISUAL_OBJECT_SOURCE_SHA256,
            'Exact original donor geometry source records differ')
    keys = {}
    for record in original.values():
        shape = ','.join(sorted(record))
        keys[shape] = keys.get(shape, 0) + 1
    return {'format': 1, 'status': 'passed', 'donor': DONOR, 'visual_source_manifest': VISUAL_MANIFEST_PIN,
            'visual_geometry_sha256': VISUAL_GEO_SOURCE_SHA256,
            'visual_object_geometry_sha256': VISUAL_OBJECT_SOURCE_SHA256,
            'optional_physical_geometry_sha256': hashlib.sha256(canonical(optional)).hexdigest(),
            'optional_files': len(optional), 'optional_bytes': sum(row['bytes'] for row in optional.values()),
            'original_record_keys': keys, 'optional_input_files': optional,
            'native_import_performed': False, 'native_generation_performed': False}


def record_profile_inventory(evidence, common, optional, warm, cold):
    """Retain bounded actual differences before enforcing exact cold/warm closure."""
    expected = {**common, **optional}
    def difference(actual, wanted):
        missing, extra = sorted(set(wanted) - set(actual)), sorted(set(actual) - set(wanted))
        changed = sorted(name for name in set(actual).intersection(wanted) if actual[name] != wanted[name])
        return {'missing_count': len(missing), 'missing_first_16': missing[:16],
                'extra_count': len(extra), 'extra_first_16': extra[:16],
                'changed_count': len(changed),
                'changed_first_16': [{'name': name, 'actual': actual[name], 'expected': wanted[name]}
                                     for name in changed[:16]]}
    record = {'format': 1, 'status': 'passed' if warm == expected and cold == expected else 'mismatch',
              'common_files': len(common), 'optional_files': len(optional),
              'common_sha256': hashlib.sha256(canonical(common)).hexdigest(),
              'optional_physical_geometry_sha256': hashlib.sha256(canonical(optional)).hexdigest(),
              'warm_sha256': hashlib.sha256(canonical(warm)).hexdigest(),
              'cold_sha256': hashlib.sha256(canonical(cold)).hexdigest(),
              'warm_difference': difference(warm, expected), 'cold_difference': difference(cold, expected)}
    (Path(evidence) / 'native-input-profiles.json').write_bytes(canonical(record))
    print('COH_ATLAS_BEACON_INPUT_PROFILES ' + canonical(record).decode('ascii'), flush=True)
    return record


def overlay_object_geometry(path, manifest_path, runtime):
    """Expose only original supplemental object GEOs to the host collision load."""
    manifest = json.loads(manifest_path.read_bytes())
    require(pin(path) == {key: manifest['archive'][key] for key in ('bytes', 'sha256')}, 'Visual ZIP pin differs')
    selected = physical_pins({name: expected for name, expected in manifest['files'].items()
                              if name.startswith('data/object_library/') and name.endswith('.geo')})
    require(len(selected) == VISUAL_OBJECT_GEOS, 'Exact optional object GEO inventory differs')
    targets = resolve_world_targets(runtime, selected)
    with zipfile.ZipFile(path) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist()))
                and set(archive.namelist()) == set(manifest['files']), 'Visual ZIP closure differs')
        for name, expected in selected.items():
            safe(name); target = targets[name]
            require(not target.exists(), 'Optional visual geometry overlaps the base/world profile')
            with archive.open(name) as source: copy_pinned(source, target, expected)
    return manifest, selected


def mirror_cold_runtime(runtime, destination):
    """Fresh process data shares readonly inputs and isolates every cache root."""
    runtime, destination = Path(runtime), Path(destination)
    require(not destination.exists(), 'Cold readback runtime must be new')
    destination.mkdir()
    count = total = 0
    for source in runtime.rglob('*'):
        require(not source.is_symlink(), 'Linked host donor path refused')
        relative = source.relative_to(runtime); target = destination / relative
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        require(source.is_file(), 'Nonregular host donor path refused')
        count += 1; total += source.stat().st_size
        require(count <= 200000 and total <= 6 * 1024**3, 'Cold readback mirror exceeds owned input bound')
        target.parent.mkdir(parents=True, exist_ok=True)
        private = (relative.parts[0].casefold() != 'data' or len(relative.parts) > 1
                   and relative.parts[1].casefold() in ('bin', 'geobin', 'server'))
        if private:
            shutil.copyfile(source, target); target.chmod(0o600)
        else:
            source.chmod(0o400); os.link(source, target)
    return {'files': count, 'bytes': total, 'readonly_inputs_hardlinked': True,
            'private_cache_roots': ['data/bin', 'data/geobin', 'data/server'],
            'created_before_visual_overlay_and_generation': True}


def geometry_inputs(runtime):
    """Bind exact leaves under canonical directory keys and refuse case aliases."""
    runtime = Path(runtime).absolute()
    require(runtime.is_dir() and not runtime.is_symlink(), 'Owned native input directory required')
    scopes = ('data/object_library', 'data/maps/city_zones/city_01_01', 'data/tricks')
    roots = resolve_world_targets(runtime, [name + '/.atlas-beacon-inventory' for name in scopes])
    records, seen, count = {}, {}, 0
    for scope in scopes:
        root = roots[scope + '/.atlas-beacon-inventory'].parent
        require(root.is_dir() and not root.is_symlink(), 'Native collision input scope is missing or linked')
        for path in root.rglob('*'):
            count += 1
            require(count <= 200000 and not path.is_symlink(), 'Native input tree is linked or oversized')
            raw_name = path.relative_to(runtime).as_posix()
            folded = raw_name.casefold()
            require(folded not in seen, 'Ambiguous case-conflicting native input inventory')
            seen[folded] = raw_name
            if path.is_dir(): continue
            require(path.is_file(), 'Nonregular native source input refused')
            suffixes = ('.geo', '.txt') if scope == 'data/object_library' else ('.txt',)
            if path.suffix.casefold() not in suffixes: continue
            name = canonical_input_name(raw_name)
            require(name not in records, 'Duplicate canonical native input')
            records[name] = pin(path)
    require(100 < len(records) <= 12288, 'Collision input scope exceeds producer bound')
    # A folded comparison alone would accidentally permit a different leaf.
    # The authoritative resolver must recover exactly each enumerated leaf.
    targets = resolve_world_targets(runtime, records)
    require(all(target.name == Path(name).name and pin(target) == records[name]
                for name, target in targets.items()), 'Canonical native input leaf/byte mapping differs')
    return dict(sorted(records.items()))


def native_evidence(log, date):
    matches = NATIVE.findall(log)
    require(len(matches) == 1, 'One native graph/CRC/path witness required')
    crc, *values = matches[0]
    fresh = FRESH_NATIVE.findall(log)
    require(len(fresh) == 1 and fresh[0] == crc
            and FRESH_NATIVE.search(log).start() < NATIVE.search(log).start(),
            'One matching fresh ordinary-world CRC capture required before graph readback')
    combat, connected, ground, raised, blocks, paths = map(int, values)
    require(1000 < combat <= 1000000 and 1000 < connected <= combat and ground > 1000
            and raised >= 0 and blocks > 0 and paths == 32, 'Native graph/path witness outside bounds')
    require(len(date) == 12, 'Native v9 date sidecar must have exactly 12 bytes')
    version, newest, date_crc = struct.unpack('<iII', date)
    require(version == 9, f'Native date version differs: {version}')
    require(date_crc == int(crc, 16),
            f'Native loaded-world CRC and date sidecar differ: marker={crc.decode("ascii")} date=0x{date_crc:08x}')
    return {'full_world_crc': f'0x{date_crc:08x}', 'combat_beacons': combat,
            'connected_beacons': connected, 'ground_connections': ground,
            'raised_connections': raised, 'grid_blocks': blocks, 'native_pathfinder_successes': paths,
            'date_version': version, 'date_latest_data_time': newest,
            'fresh_ordinary_world_crc_verified': True, 'native_full_graph_readback_verified': True}


def clear_private_geometry_caches(runtime):
    """Clear owned map/object binary caches; retained definition bins are untouched."""
    name = 'data/geobin/.atlas-beacon-cache'
    root = resolve_world_targets(runtime, [name])[name].parent
    if not root.exists(): return {'policy': 'empty_private_geobin_before_fresh_readback',
                                  'removed_files': [], 'remaining_geometry_cache_files': 0}
    require(root.is_dir() and not root.is_symlink(), 'Owned private geobin directory required')
    records = []
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'Linked native geometry cache refused')
        if path.is_dir(): continue
        require(path.is_file(), 'Nonregular native geometry cache refused')
        if path.suffix.casefold() not in ('.bin', '.dep', '.bounds'): continue
        require(len(records) < 65536 and path.stat().st_size <= MAX_LOG,
                'Private geometry cache cleanup exceeds bound')
        records.append({'path': path.relative_to(runtime).as_posix(), **pin(path)})
    records.sort(key=lambda row: row['path'])
    require(sum(row['bytes'] for row in records) <= 1024**3, 'Private cache cleanup byte bound exceeded')
    for row in records:
        target = runtime / row['path']; target.chmod(0o600); target.unlink()
    return {'policy': 'empty_private_geobin_before_fresh_readback', 'removed_files': records,
            'remaining_geometry_cache_files': 0}


def validate_recovered_origin(value, directory, build_input, generator_pin):
    require(value.get('kind') == 'recovered_primary_native_generation'
            and value.get('source') == PRIMARY_RECOVERY
            and value.get('original_run_conclusion') == 'failure'
            and value.get('primary_generation_server_returncode') == 0
            and value.get('generation_sources') == PRIMARY_GENERATION_SOURCES
            and value.get('build_input') == build_input and value.get('generator') == generator_pin == PRIMARY_RECOVERY['generator']
            and value.get('native') == PRIMARY_RECOVERY['native']
            and value.get('original_owned_roles') == 4
            and value.get('original_cleanup_complete') is True
            and value.get('original_native_worker_spawning_allowed') is False
            and value.get('fresh_qualification_still_required') is True,
            'Original native graph origin/source/cleanup differs')
    directory = Path(directory)
    validate_primary_implementation_inputs()
    validate_recovery_metadata(json.loads((directory / 'evidence/primary-recovery-metadata.json').read_bytes()))
    require(pin(directory / 'evidence/primary-original-generation-source.py')
            == PRIMARY_GENERATION_SOURCES['tools/android/interactive/generate_atlas_beacons.py'],
            'Original generation implementation evidence differs')
    require(json.loads((directory / 'evidence/primary-build-input.json').read_bytes()) == build_input,
            'Original compiled native source evidence differs')
    require(pin(directory / 'evidence/primary-build-input.json') == PRIMARY_RECOVERY['build_input'],
            'Original compile receipt bytes differ')
    primary = json.loads((directory / 'evidence/primary-unqualified-output.json').read_bytes())
    require(primary['native_generation_server_returncode'] == 0
            and primary['status'] == 'unqualified_native_output'
            and primary['files'] == {'unqualified-native-graph.bcn': PRIMARY_RECOVERY['graph'],
                                     'unqualified-native-graph.bcn.date': PRIMARY_RECOVERY['date']},
            'Original actual primary output evidence differs')
    return value


def validate_package(directory, repository_commit):
    directory = Path(directory)
    value = json.loads((directory / REPORT).read_bytes())
    require(value.get('format') == 3 and value.get('status') == 'passed' and re.fullmatch('[0-9a-f]{40}', value.get('repository_commit', ''))
            and re.fullmatch('[0-9a-f]{40}', repository_commit), 'Generation provenance/commit differs')
    require(value.get('generation_sources') == {name: pin(ROOT / name) for name in GENERATION_SOURCES},
            'Qualification implementation changed; new fresh native proofs are required')
    require(value['build_input'] == producer.expected(), 'Host producer source receipt differs')
    reuse_path = directory / 'evidence/host-compile-reuse.json'
    if reuse_path.exists():
        require('evidence/host-compile-reuse.json' in value['evidence'], 'Host compile receipt must be bound')
        validate_compile_reuse_receipt(json.loads(reuse_path.read_bytes()), value['build_input'], value['generator'])
    require(value['donor'] == DONOR and value['stock_mapserver_sha256'] == STOCK_MAPSERVER,
            'Stock native compatibility differs')
    require(value.get('cleanup_complete') is True and value.get('owned_roles') == 0
            and value.get('qualification_mode') == 'recovered_primary_fresh_proofs'
            and value.get('native_worker_spawning_allowed') is False,
            'Owned proof-only native containment/cleanup differs')
    validate_recovered_origin(value['graph_origin'], directory, value['build_input'], value['generator'])
    for name, expected in value['evidence'].items():
        require(pin(directory / safe(name)) == expected, 'Generation evidence changed')
    manifest = json.loads((directory / MANIFEST).read_bytes())
    require(pin(directory / MANIFEST) == value['manifest'] and pin(directory / ARCHIVE) == value['archive'],
            'Generated package pin differs')
    require(manifest['files'] == {GRAPH: PRIMARY_RECOVERY['graph'], DATE: PRIMARY_RECOVERY['date']},
            'Package graph/date differ from actual original native generation')
    require(manifest.get('format') == 3 and manifest['map'] == producer.MAP and set(manifest['files']) == {GRAPH, DATE}
            and manifest['stock_mapserver_sha256'] == STOCK_MAPSERVER, 'Generated graph scope differs')
    require(manifest['native'] == native_evidence((directory / 'evidence/server.log').read_bytes(),
                                                 _date_from_archive(directory / ARCHIVE)), 'Native transcript differs')
    identity = manifest['input_identity']
    require(identity['visual_source_manifest'] == VISUAL_MANIFEST_PIN
            and identity['visual_geometry_sha256'] == VISUAL_GEO_SOURCE_SHA256
            and identity['visual_object_geometry_sha256'] == VISUAL_OBJECT_SOURCE_SHA256,
            'Original donor geometry source provenance differs')
    common, required = manifest['input_files'], manifest['required_geometry_files']
    require(len(common) == 5231 and len(required) == VISUAL_OBJECT_GEOS and not set(common).intersection(required)
            and set(manifest['input_profiles']) == set(PROFILES), 'Native input profiles differ')
    require(manifest['input_files_sha256'] == hashlib.sha256(canonical(common)).hexdigest()
            and manifest['input_identity']['required_geometry_sha256']
                == hashlib.sha256(canonical(required)).hexdigest() == VISUAL_OBJECT_SOURCE_SHA256
            and manifest['input_files_sha256'] == COMMON_INPUT_SHA256
            and hashlib.sha256(canonical({**common, **required})).hexdigest() == REQUIRED_INPUT_SHA256, 'Native physical input pins differ')
    for profile in PROFILES:
        selected = {**common, **required}
        native = native_evidence((directory / ('evidence/' + profile + '.log')).read_bytes(),
                                _date_from_archive(directory / ARCHIVE))
        require(native == manifest['native'] == manifest['input_profiles'][profile]['native']
                and hashlib.sha256(canonical(selected)).hexdigest()
                == manifest['input_profiles'][profile]['input_files_sha256'], 'Fresh native profile proof differs')
    require(value['profile_verification_processes'] == 2 and value['profile_proofs'] == manifest['input_profiles']
            and value['cold_mirror']['required_geometry_installed_before_mirror'] is True
            and value['cold_mirror']['created_before_full_visual_overlay_and_readback'] is True
            and value['cold_mirror']['readonly_inputs_hardlinked'] is True
            and value['cold_mirror']['private_cache_roots'] == ['data/bin', 'data/geobin', 'data/server'],
            'Fresh isolated native profile provenance differs')
    require(value.get('qualification_visual') == {
        'archive': QUALIFICATION_VISUAL_ARCHIVE, 'manifest': QUALIFICATION_VISUAL_MANIFEST,
        'files': 10401, 'retained_files': 9613, 'added_original_textures': 788,
        'required_geometry_files': VISUAL_OBJECT_GEOS}, 'Full client visual proof source differs')
    require(set(value['profile_cache_isolation']) == set(PROFILES)
            and all(row['policy'] == 'empty_private_geobin_before_fresh_readback'
                    and row['remaining_geometry_cache_files'] == 0
                    for row in value['profile_cache_isolation'].values()), 'Private native geometry cache isolation differs')
    with zipfile.ZipFile(directory / ARCHIVE) as archive:
        require(len(archive.namelist()) == 3 and set(archive.namelist()) == {GRAPH, DATE, MANIFEST}, 'Beacon package closure differs')
        require(archive.read(MANIFEST) == (directory / MANIFEST).read_bytes(), 'Embedded manifest differs')
        for name, expected in manifest['files'].items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected, 'Graph pin differs')
    return manifest


def _date_from_archive(path):
    with zipfile.ZipFile(path) as archive: return archive.read(DATE)



def record_native_output(evidence, runtime, server_returncode):
    """Preserve real completed output for diagnosis, without qualifying it."""
    files = {}
    for source_name, evidence_name, limit in (
            (GRAPH, 'unqualified-native-graph.bcn', MAX_GRAPH),
            (DATE, 'unqualified-native-graph.bcn.date', 12)):
        source = resolve_world_targets(runtime, [source_name])[source_name]
        info = source.lstat()
        require(stat.S_ISREG(info.st_mode) and not source.is_symlink()
                and 0 < info.st_size <= limit, 'Bounded regular native output required')
        target = evidence / evidence_name
        shutil.copyfile(source, target)
        actual = pin(source)
        require(pin(target) == actual, 'Native output changed during evidence capture')
        files[evidence_name] = actual
    raw = (evidence / 'unqualified-native-graph.bcn.date').read_bytes()
    date = {'bytes': len(raw), 'hex': raw.hex()}
    if len(raw) == 12:
        version, newest, crc = struct.unpack('<iII', raw)
        date.update(version=version, latest_data_time=newest, full_world_crc=f'0x{crc:08x}')
    log = evidence / 'server.log'
    require(log.stat().st_size <= MAX_LOG, 'Bounded native server log required')
    raw_log = log.read_bytes()
    matches = NATIVE.findall(raw_log)
    fresh_markers = FRESH_NATIVE.findall(raw_log)
    require(len(matches) <= 16 and len(fresh_markers) <= 16, 'Native marker diagnostic exceeds bound')
    markers = [{'crc': row[0].decode('ascii'),
                'combat': int(row[1]), 'connected': int(row[2]),
                'ground': int(row[3]), 'raised': int(row[4]),
                'blocks': int(row[5]), 'paths': int(row[6])} for row in matches]
    value = {'format': 1, 'status': 'unqualified_native_output',
             'native_generation_server_returncode': server_returncode,
             'both_fresh_profile_proofs_required': True,
             'files': files, 'date': date, 'native_markers': markers,
             'fresh_world_markers': [crc.decode('ascii') for crc in fresh_markers]}
    (evidence / 'unqualified-native-output.json').write_bytes(canonical(value))
    print('COH_ATLAS_BEACON_UNQUALIFIED_OUTPUT ' + canonical(value).decode('ascii'), flush=True)
    return value


def record_role_heartbeat(evidence, processes, started, phase):
    """Print bounded owned-role progress; this supplies no graph proof."""
    roles = {}
    for role, process in processes.items():
        path = evidence / (role + '.log')
        size = path.stat().st_size
        require(size <= MAX_LOG, 'Native role log exceeded bound')
        with path.open('rb') as stream:
            stream.seek(max(0, size - MAX_FAILURE_TAIL))
            tail = stream.read(MAX_FAILURE_TAIL)
        lines = [line for line in tail.splitlines() if line.strip()]
        last = lines[-1][-512:] if lines else b''
        roles[role] = {'returncode': process.poll(), 'log_bytes': size,
                       'last_progress_line': last.decode('utf-8', errors='replace')
                           .encode('ascii', errors='backslashreplace').decode('ascii')[-512:]}
    value = {'format': 1, 'status': 'native_progress_only', 'phase': phase,
             'elapsed_seconds': max(0, round(time.monotonic() - started, 3)), 'roles': roles}
    print('COH_ATLAS_BEACON_HEARTBEAT ' + canonical(value).decode('ascii'), flush=True)
    return value


def record_role_failure(evidence, processes, commands, failure, before_cleanup=None):
    """Keep bounded native diagnostics even when artifact publication fails."""
    roles, tails = {}, {}
    for role, process in processes.items():
        path = evidence / (role + '.log')
        code = process.returncode
        with path.open('rb') as stream:
            stream.seek(max(0, path.stat().st_size - MAX_FAILURE_TAIL))
            tail = stream.read(MAX_FAILURE_TAIL).decode('utf-8', errors='replace')
        original = (before_cleanup or {}).get(role, code)
        roles[role] = {'returncode': code, 'windows_exit_hex': None if code is None else f'0x{code & 0xffffffff:08x}',
                       'returncode_before_cleanup': original,
                       'windows_exit_before_cleanup': None if original is None else f'0x{original & 0xffffffff:08x}',
                       'command': commands[role], 'log': pin(path), 'tail_bytes_limit': MAX_FAILURE_TAIL}
        tails[role] = tail.encode('ascii', errors='backslashreplace').decode('ascii')[-MAX_FAILURE_TAIL:]
    record = {'format': 1, 'status': 'failed', 'exception_type': type(failure).__name__,
              'reason': str(failure), 'roles': roles,
              'cleanup_complete': all(process.poll() is not None for process in processes.values())}
    (evidence / 'native-role-failure.json').write_bytes(canonical(record))
    # Windows Actions may use cp1252. Save durable JSON before rendering any
    # native UTF-8/invalid byte tails, and print only representable ASCII.
    for role, tail in tails.items():
        print(f'COH_ATLAS_BEACON_ROLE_FAILURE role={role} exit={roles[role]["windows_exit_before_cleanup"]}', flush=True)
        print(tail, flush=True)


def role_environment(environment=None):
    # Native progress initialization distinguishes absent from empty. Host roles
    # do not own an Android observer mapping and must never request one.
    env = dict(os.environ if environment is None else environment)
    for name in ('COH_WINE_MAP_PROGRESS', 'COH_CLIENT_DEPENDENCY_PRELOAD',
                 'COH_MANUAL_ATLAS_DB', 'COH_WINE_GAME_LISTENERS', 'COH_ATLAS_BEACON_VERIFY_ONLY'):
        env.pop(name, None)
    # Accepted native startup activates this before any explicit socket bind.
    # netInit's second argument is UDP port, so address policy belongs here.
    env['COH_GAME_LOOPBACK_ONLY'] = '1'
    return env


def validate_compile_reuse_receipt(value, build_input, generator_pin):
    """A retained successful compile supplies no accepted graph or role proof."""
    require(isinstance(value, dict) and value.get('format') == 1
            and value.get('status') == 'reused_exact_compatible_native_compile'
            and value.get('compile') == HOST_COMPILE_REUSE
            and value.get('build_input') == build_input
            and value.get('generator') == generator_pin,
            'Retained host compile/source/artifact identity differs')
    return value


def validate_recovery_metadata(value):
    """Authenticate a failed overall run without upgrading its conclusion."""
    source = PRIMARY_RECOVERY
    require(isinstance(value, dict) and value.get('format') == 1
            and value.get('status') == 'authenticated_failed_run_primary_candidate'
            and value.get('source') == source, 'Primary recovery source/artifact identity differs')
    require(value.get('run') == {
        'id': source['run_id'], 'head_sha': source['repository_commit'],
        'head_branch': 'codex/character-persistence-continuation',
        'path': '.github/workflows/android-atlas-beacon-generation.yml',
        'status': 'completed', 'conclusion': 'failure', 'run_attempt': 1},
        'Original failed-run API provenance differs')
    require(value.get('job') == {
        'id': source['job_id'], 'name': 'generate', 'conclusion': 'failure',
        'source_stage_conclusion': 'success', 'compile_conclusion': 'success'},
        'Original native compile/job provenance differs')
    artifact = source['artifact']
    require(value.get('artifact') == {
        'id': artifact['id'], 'name': 'coh-ui-beacon-generation-evidence',
        'expired': False, 'size_in_bytes': artifact['bytes'],
        'digest': 'sha256:' + artifact['sha256'],
        'run_id': source['run_id'], 'head_sha': source['repository_commit']},
        'Original authenticated artifact metadata differs')
    return value


def validate_primary_implementation_inputs():
    # The qualifier changes; native algorithms, host C patch, source staging,
    # importer and authoritative path resolver must remain exactly as generated.
    for name in GENERATION_SOURCES:
        if name == 'tools/android/interactive/generate_atlas_beacons.py': continue
        require(pin(ROOT / name) == PRIMARY_GENERATION_SOURCES[name],
                'Primary native/import input implementation changed: ' + name)


def recover_primary_artifact(archive_path, metadata_path, generator_path,
                             build_input_path, evidence, original_source_path):
    """Recover exact primary output; only later new processes can qualify it."""
    require(pin(archive_path) == {key: PRIMARY_RECOVERY['artifact'][key] for key in ('bytes', 'sha256')}, 'Primary artifact ZIP differs')
    metadata = validate_recovery_metadata(json.loads(Path(metadata_path).read_bytes()))
    validate_primary_implementation_inputs()
    require(pin(original_source_path) == PRIMARY_GENERATION_SOURCES[
        'tools/android/interactive/generate_atlas_beacons.py'], 'Original generator implementation differs')
    evidence = Path(evidence)
    with zipfile.ZipFile(archive_path) as archive:
        rows = archive.infolist()
        require(0 < len(rows) <= 512 and sum(row.file_size for row in rows) <= 256 * 1024**2,
                'Bounded primary artifact required')
        names = [safe(row.filename.rstrip('/')) for row in rows]
        require(len({name.casefold() for name in names}) == len(names),
                'Primary artifact contains ambiguous members')
        def member(leaf, limit):
            found = [row for row in rows if Path(row.filename).name == leaf and not row.is_dir()]
            require(len(found) == 1 and 0 < found[0].file_size <= limit,
                    'One bounded primary artifact member required: ' + leaf)
            mode = found[0].external_attr >> 16
            require(not mode or not stat.S_ISLNK(mode), 'Linked primary artifact member refused')
            return archive.read(found[0])
        graph = member('unqualified-native-graph.bcn', MAX_GRAPH)
        date = member('unqualified-native-graph.bcn.date', 12)
        raw_capture = member('unqualified-native-output.json', 1024**2)
        capture = json.loads(raw_capture)
        require(capture.get('format') == 1 and capture.get('status') == 'unqualified_native_output'
                and capture.get('native_generation_server_returncode') == 0
                and capture.get('both_fresh_profile_proofs_required') is True,
                'Primary native output was not completed successfully')
        actual = {'unqualified-native-graph.bcn': {
            'bytes': len(graph), 'sha256': hashlib.sha256(graph).hexdigest()},
            'unqualified-native-graph.bcn.date': {
            'bytes': len(date), 'sha256': hashlib.sha256(date).hexdigest()}}
        require(actual == {'unqualified-native-graph.bcn': PRIMARY_RECOVERY['graph'],
                           'unqualified-native-graph.bcn.date': PRIMARY_RECOVERY['date']}
                and capture.get('files') == actual, 'Retained actual native graph/date pins differ')
        primary_log = member('server.log', MAX_LOG)
        witness = native_evidence(primary_log, date)
        require(witness == PRIMARY_RECOVERY['native'], 'Primary fresh CRC/readback/32-route witness differs')
        failure_raw = member('native-role-failure.json', 1024**2)
        failure = json.loads(failure_raw)
        require(failure.get('status') == 'failed' and failure.get('cleanup_complete') is True
                and failure.get('roles', {}).get('server', {}).get('returncode') == 0
                and failure.get('roles', {}).get('base_world', {}).get('returncode') == 3,
                'Original primary completion/owned cleanup/cold refusal evidence differs')
        build_raw = member('atlas-beacon-generator-build-input.json', 1024**2)
        require({'bytes': len(build_raw), 'sha256': hashlib.sha256(build_raw).hexdigest()}
                == PRIMARY_RECOVERY['build_input'], 'Actual retained compile receipt bytes differ')
        build_input = json.loads(build_raw)
        require(build_input == producer.expected()
                and build_input == json.loads(Path(build_input_path).read_bytes()),
                'Retained successful native compile source receipt differs')
        binary = member('host-only-beacon-generator.exe', MAX_LOG)
        require({'bytes': len(binary), 'sha256': hashlib.sha256(binary).hexdigest()}
                == PRIMARY_RECOVERY['generator'], 'Actual retained native executable bytes differ')
        require(binary[:2] == b'MZ' and len(binary) > 256, 'Retained native executable header differs')
        pe = struct.unpack_from('<I', binary, 0x3c)[0]
        require(pe + 6 < len(binary) and binary[pe:pe+4] == b'PE\0\0'
                and struct.unpack_from('<H', binary, pe+4)[0] == 0x14c, 'Retained Win32 ABI differs')
        generator_path = Path(generator_path)
        require(not generator_path.exists(), 'Fresh owned retained-generator path required')
        generator_path.parent.mkdir(parents=True, exist_ok=True)
        generator_path.write_bytes(binary)
        symbols = member('host-only-beacon-generator.pdb', MAX_LOG)
        generator_path.with_suffix('.pdb').write_bytes(symbols)
        inventory = json.loads(member('native-input-profiles.json', 1024**2))
        require(inventory.get('status') == 'passed' and inventory.get('common_files') == 5231
                and inventory.get('optional_files') == VISUAL_OBJECT_GEOS
                and inventory.get('common_sha256') == COMMON_INPUT_SHA256
                and inventory.get('warm_sha256') == REQUIRED_INPUT_SHA256
                and inventory.get('optional_physical_geometry_sha256') == VISUAL_OBJECT_SOURCE_SHA256,
                'Primary native effective geometry inventory differs')
    for name, raw in {'server.log': primary_log, 'primary-unqualified-output.json': raw_capture,
                      'primary-role-failure.json': failure_raw,
                      'primary-build-input.json': build_raw,
                      'primary-original-generation-source.py': Path(original_source_path).read_bytes()}.items():
        (evidence / name).write_bytes(raw)
    shutil.copyfile(metadata_path, evidence / 'primary-recovery-metadata.json')
    origin = {'kind': 'recovered_primary_native_generation', 'source': PRIMARY_RECOVERY,
              'original_run_conclusion': 'failure', 'primary_generation_server_returncode': 0,
              'generation_sources': PRIMARY_GENERATION_SOURCES, 'build_input': build_input,
              'generator': pin(generator_path), 'native': witness,
              'original_owned_roles': 4, 'original_cleanup_complete': True,
              'original_native_worker_spawning_allowed': False,
              'fresh_qualification_still_required': True}
    (evidence / 'primary-graph-origin.json').write_bytes(canonical(origin))
    return origin, graph, date


def overlay_complete_visual(path, manifest_path, original_manifest, required, runtime):
    """Prove the shipped UI extension while retaining every original byte stream."""
    require(pin(path) == QUALIFICATION_VISUAL_ARCHIVE and pin(manifest_path) == QUALIFICATION_VISUAL_MANIFEST,
            'Frozen UI preparation pair differs')
    value = json.loads(Path(manifest_path).read_bytes())
    require({key: value['archive'][key] for key in ('bytes', 'sha256')} == QUALIFICATION_VISUAL_ARCHIVE,
            'Frozen client visual archive receipt differs')
    files = value['files']
    require(len(files) == 10401 and len(original_manifest['files']) == 9613
            and set(original_manifest['files']).issubset(files)
            and all(files[name] == record for name, record in original_manifest['files'].items()),
            'Retained original visual source streams changed')
    added = set(files) - set(original_manifest['files'])
    require(len(added) == 788 and all(name.startswith('data/texture_library/') for name in added),
            'UI source supplement exceeds its exact texture-only scope')
    selected = physical_pins({name: row for name, row in files.items()
                             if name.startswith('data/object_library/') and name.endswith('.geo')})
    require(selected == required, 'Full client visual collision geometry differs')
    targets = resolve_world_targets(runtime, files)
    with zipfile.ZipFile(path) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist()))
                and set(archive.namelist()) == set(files), 'Complete client visual ZIP closure differs')
        for name, row in files.items():
            target = targets[name]
            if target.exists():
                require(pin(target) == physical_pins({name: row})[name],
                        'Existing immutable visual source changed: ' + name)
                continue
            with archive.open(name) as source: copy_pinned(source, target, row)
            os.utime(target, (1767225600, 1767225600))
    return {'archive': pin(path), 'manifest': pin(manifest_path), 'files': len(files),
            'retained_files': 9613, 'added_original_textures': 788, 'required_geometry_files': len(required)}


def generate(args):
    require(os.name == 'nt', 'Native qualification requires an isolated Windows runner')
    for name in ('donor_apk', 'donor_receipt', 'asset_archive', 'generator', 'build_input', 'work', 'output',
                 'client_visual_archive', 'client_visual_manifest'):
        setattr(args, name, Path(getattr(args, name)).resolve())
    for name in ('recovery_artifact', 'recovery_metadata', 'original_generation_source'):
        value = getattr(args, name, None)
        if value is not None: setattr(args, name, Path(value).resolve())
    recovering = args.recovery_artifact is not None
    require(recovering, 'This qualification lane requires the exact retained real primary graph')
    require(recovering == (args.recovery_metadata is not None) == (args.original_generation_source is not None),
            'All primary recovery provenance inputs are required together')
    require(30 <= args.timeout_seconds <= 5400 and re.fullmatch('[0-9a-f]{40}', args.repository_commit), 'Invalid timeout/commit')
    require(not args.work.exists() and not args.output.exists(), 'Fresh generator work/output required')
    args.work.mkdir(parents=True); args.output.mkdir(parents=True)
    evidence = args.output / 'evidence'; evidence.mkdir()
    build_input = json.loads(args.build_input.read_bytes())
    require(build_input == producer.expected(), 'Native generator source receipt differs')
    reuse_path = args.build_input.with_name('atlas-beacon-generator-compile-reuse.json')
    if reuse_path.exists():
        require(reuse_path.is_file() and not reuse_path.is_symlink() and reuse_path.stat().st_size < 1024**2,
                'Finite private host compile receipt required')
        validate_compile_reuse_receipt(json.loads(reuse_path.read_bytes()), build_input, pin(args.generator))
        shutil.copyfile(reuse_path, evidence / 'host-compile-reuse.json')
    assets = args.work / 'donor'; extract_assets(args.donor_apk, args.donor_receipt, assets)
    data = import_data(assets, args.asset_archive, args.work, evidence).resolve(strict=True)
    imported_runtime = data.parent.resolve(strict=True)
    runtime = args.work / 'r'
    require(not runtime.exists(), 'Fresh short owned native runtime required')
    imported_runtime.rename(runtime)
    data = runtime / 'data'
    require(len(str(runtime / 'AtlasBeaconGenerator.exe')) < 100,
            'Host roles require a short owned executable/runtime path')
    native = extract_tar(assets / 'runtime/game-package.tar.gz', runtime, 'game-package.json')
    require(pin(runtime / 'MapServer.exe')['sha256'] == STOCK_MAPSERVER, 'Retained native MapServer differs')
    extract_tar(assets / 'runtime/dbserver-schema.tar.gz', runtime, 'schema-manifest.json')
    world = overlay_zip(assets / 'runtime/atlas-world-supplement.zip', assets / 'runtime/atlas-world-supplement-manifest.json', runtime)
    # Retain immutable byte inputs and common loader epoch. The host source only
    # writes caches and two server-only graph files under this isolated tree.
    for path in data.rglob('*'):
        if path.is_file(): os.utime(path, (1767225600, 1767225600))
    common_inputs = geometry_inputs(runtime)
    require(hashlib.sha256(canonical(common_inputs)).hexdigest() == COMMON_INPUT_SHA256,
            'Exact common geometry/text source inventory differs')
    visual_path = assets / 'runtime/client-visual-manifest.json'
    visual, required_inputs = overlay_object_geometry(assets / 'runtime/client-visual-assets.zip', visual_path, runtime)
    for target in resolve_world_targets(runtime, required_inputs).values():
        os.utime(target, (1767225600, 1767225600))
    inputs = geometry_inputs(runtime)
    require(hashlib.sha256(canonical(inputs)).hexdigest() == REQUIRED_INPUT_SHA256,
            'Required original object geometry source inventory differs')
    # Both fresh layouts contain the actual required collision GEOs. Never prove
    # compatibility against the disproved legacy NONE profile (CRC1583f117).
    cold_runtime = args.work / 'c'
    cold_mirror = mirror_cold_runtime(runtime, cold_runtime)
    cold_mirror['required_geometry_installed_before_mirror'] = True
    cold_mirror['created_before_full_visual_overlay_and_readback'] = True
    cold_mirror.pop('created_before_visual_overlay_and_generation')
    qualification_visual = overlay_complete_visual(
        args.client_visual_archive, args.client_visual_manifest, visual, required_inputs, runtime)
    inventory = record_profile_inventory(evidence, common_inputs, required_inputs, geometry_inputs(runtime),
                                         geometry_inputs(cold_runtime))
    require(inventory['status'] == 'passed', 'Required cold/full collision inventories differ')
    (runtime / 'tools').mkdir(exist_ok=True)
    generator = runtime / 'AtlasBeaconGenerator.exe'
    graph_origin = None
    if recovering:
        graph_origin, recovered_graph, recovered_date = recover_primary_artifact(
            args.recovery_artifact, args.recovery_metadata, args.generator,
            args.build_input, evidence, args.original_generation_source)
    shutil.copyfile(args.generator, generator)
    processes, commands = {}, {}
    started = time.monotonic()
    for name, raw in ((GRAPH, recovered_graph), (DATE, recovered_date)):
        target = resolve_world_targets(runtime, [name])[name]
        require(not target.exists(), 'Recovered graph must enter a fresh private native cache')
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw); target.chmod(0o400)
    require((runtime / GRAPH).is_file() and (runtime / DATE).is_file(), 'Native graph files missing')
    record_native_output(evidence, runtime, 0)
    require(geometry_inputs(runtime) == inputs, 'Native generation modified an immutable collision input')
    witness = native_evidence((evidence / 'server.log').read_bytes(), (runtime / DATE).read_bytes())
    profile_proofs, profile_cache_isolation = {}, {}
    for profile, profile_runtime in (('required_geometry_cold', cold_runtime), ('client_visual_reopen', runtime)):
        for name in (GRAPH, DATE):
            target = profile_runtime / name
            if profile_runtime != runtime:
                target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(runtime / name, target); target.chmod(0o400)
        profile_cache_isolation[profile] = clear_private_geometry_caches(profile_runtime)
        profile_generator = profile_runtime / 'AtlasBeaconGenerator.exe'
        if profile_runtime != runtime: shutil.copyfile(generator, profile_generator)
        profile_common = ['-nogui', '-nopigs', '-noencrypt', '-beaconallownovodex',
                          '-beacondatatoolsrootpath', str(profile_runtime)]
        command = [str(profile_generator), *profile_common, '-beaconserver', '127.0.0.1', '-beaconnonetstart']
        commands[profile] = command
        log_path = evidence / (profile + '.log')
        with log_path.open('wb') as log:
            process = subprocess.Popen(command, cwd=profile_runtime,
                env=dict(role_environment(), COH_ATLAS_BEACON_VERIFY_ONLY='1'),
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            processes[profile] = process
            failure = None
            try:
                deadline = min(started + args.timeout_seconds, time.monotonic() + 600)
                while process.poll() is None:
                    require(time.monotonic() < deadline and log_path.stat().st_size <= MAX_LOG,
                            'Fresh native profile exceeded owned time/log bound: ' + profile)
                    time.sleep(0.5)
                require(process.returncode == 0, 'Fresh native profile readback failed: ' + profile)
            except Exception as error:
                failure = error
                raise
            finally:
                before_cleanup = {role: owned.poll() for role, owned in processes.items()}
                if process.poll() is None: process.terminate()
                try: process.wait(timeout=15)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=15)
                log.flush()
                if failure is not None: record_role_failure(evidence, processes, commands, failure, before_cleanup)
        require(geometry_inputs(profile_runtime) == inputs,
                'Fresh native readback modified an immutable input: ' + profile)
        verified = native_evidence(log_path.read_bytes(), (profile_runtime / DATE).read_bytes())
        require(verified == witness, 'Required geometry/full visual CRC or graph/path proof differs')
        selected = inputs
        profile_proofs[profile] = {'native': verified, 'input_files_sha256': hashlib.sha256(canonical(selected)).hexdigest()}
    geo_files = {name: value for name, value in visual['files'].items() if name.endswith('.geo')}
    manifest = {'format': 3, 'role': 'authentic_native_atlas_beacon_graph', 'map': producer.MAP,
                'stock_mapserver_sha256': STOCK_MAPSERVER, 'source_commit': build_input['source_commit'],
                'data_commit': visual['data_commit'], 'files': {name: pin(runtime / name) for name in (GRAPH, DATE)},
                'native': witness, 'input_identity': {'asset_archive': pin(args.asset_archive),
                    'world_manifest': pin(assets / 'runtime/atlas-world-supplement-manifest.json'),
                    'visual_source_manifest': pin(visual_path),
                    'visual_geometry_sha256': hashlib.sha256(canonical(geo_files)).hexdigest(),
                    'visual_object_geometry_sha256': hashlib.sha256(canonical({name: record for name, record in geo_files.items()
                        if name.startswith('data/object_library/')})).hexdigest(),
                    'required_geometry_sha256': hashlib.sha256(canonical(required_inputs)).hexdigest()},
                'input_files': common_inputs, 'input_files_sha256': hashlib.sha256(canonical(common_inputs)).hexdigest(),
                'required_geometry_files': required_inputs, 'input_profiles': profile_proofs,
                'generator_sha256': pin(generator)['sha256'], 'runtime_graph_readback': True,
                'physical_npc_pathing_validated': False}
    require(manifest['files'] == {GRAPH: PRIMARY_RECOVERY['graph'], DATE: PRIMARY_RECOVERY['date']},
            'Qualified graph differs from actual recovered primary generation')
    raw = canonical(manifest); (args.output / MANIFEST).write_bytes(raw)
    with zipfile.ZipFile(args.output / ARCHIVE, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in (GRAPH, DATE): archive.write(resolve_world_targets(runtime, [name])[name], name)
        archive.writestr(MANIFEST, raw)
    value = {'format': 3, 'status': 'passed', 'repository_commit': args.repository_commit,
             'donor': DONOR, 'stock_mapserver_sha256': STOCK_MAPSERVER, 'build_input': build_input,
             'generator': pin(generator), 'native': witness, 'manifest': pin(args.output / MANIFEST),
             'generation_sources': {name: pin(ROOT / name) for name in GENERATION_SOURCES},
             'archive': pin(args.output / ARCHIVE), 'elapsed_seconds': round(time.monotonic() - started, 3),
             'commands': commands, 'owned_roles': 0, 'native_worker_spawning_allowed': False,
             'qualification_mode': 'recovered_primary_fresh_proofs',
             'graph_origin': graph_origin, 'qualification_visual': qualification_visual,
             'profile_verification_processes': 2, 'profile_proofs': profile_proofs, 'cold_mirror': cold_mirror,
             'profile_cache_isolation': profile_cache_isolation,
             'cleanup_complete': all(process.poll() is not None for process in processes.values()),
             'evidence': {path.relative_to(args.output).as_posix(): pin(path) for path in evidence.iterdir() if path.is_file()}}
    (args.output / REPORT).write_bytes(canonical(value))
    validate_package(args.output, args.repository_commit)
    print(json.dumps({'status': value['status'], 'native': witness, 'archive': value['archive']}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('donor-apk', 'donor-receipt', 'asset-archive', 'generator', 'build-input', 'work', 'output',
                 'client-visual-archive', 'client-visual-manifest'):
        parser.add_argument('--' + name, required=True, type=Path)
    for name in ('recovery-artifact', 'recovery-metadata', 'original-generation-source'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--timeout-seconds', type=int, default=5400)
    args = parser.parse_args()
    generate(args)


if __name__ == '__main__': main()
