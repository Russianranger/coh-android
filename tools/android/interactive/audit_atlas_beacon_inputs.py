#!/usr/bin/env python3
"""Read-only Atlas beacon input preflight; never generates, installs or loads a graph.

Default: audit the pinned source contract and shipped inventory metadata, writing
JSON to stdout. Optional --bcn/--date inputs only verify a bounded binary prefix
and date-sidecar comparison. Even pinned files with a matching supplied CRC need
a full native graph read and a CRC calculated from the actual loaded Atlas world.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct

ROOT = Path(__file__).resolve().parents[3]
MAX_JSON_BYTES = 64 * 1024 * 1024
MAX_BCN_BYTES = 128 * 1024 * 1024
SOURCE_FILES = (
    'MapServer/src/beacon/beaconFile.c',
    'MapServer/src/beacon/beaconClientServer.c',
    'MapServer/src/cmdparse/cmdserver.c',
)
INVENTORIES = (
    ('docs/source-manifest.json', 'source_snapshot'),
    ('docs/data-manifest.json', 'text_data_snapshot'),
    ('assets/reference-inputs-manifest.json', 'accepted_binary_asset_inventory'),
    ('assets/atlas-world-supplement-manifest.json', 'shipped_atlas_geometry_texture_inventory'),
    ('docs/android-evidence/client-cache-manifest-36707839624.json', 'accepted_client_cache_inventory'),
    ('docs/android-evidence/mapserver-progress-package-36630872719.json', 'accepted_mapserver_package_metadata'),
)


class AuditError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AuditError(message)


def read_regular(path, limit):
    """Bound the read, refuse special files/symlink leaves, and detect replacement."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode), 'Input must be a regular file')
        require(0 < before.st_size <= limit, 'Input is empty or exceeds the byte bound')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
        after = os.fstat(fd)
        identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
        require(len(raw) == before.st_size and identity(before) == identity(after),
                'Input changed while reading')
        return raw
    finally:
        os.close(fd)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def load_json(path):
    raw = read_regular(path, MAX_JSON_BYTES)
    value = json.loads(raw)
    require(isinstance(value, dict), 'Metadata must be a JSON object')
    return value, {'bytes': len(raw), 'sha256': sha256(raw)}


def pin_matches(raw, expected):
    if expected is None:
        return False
    require(re.fullmatch(r'[0-9a-f]{64}', expected) is not None, 'Invalid SHA-256 pin')
    require(sha256(raw) == expected, 'Input differs from supplied SHA-256 pin')
    return True


def packed_u32(raw, offset):
    require(offset < len(raw), 'Truncated packed integer')
    size = (1, 2, 3, 5)[raw[offset] & 3]
    require(offset + size <= len(raw), 'Truncated packed integer')
    value = int.from_bytes(raw[offset:offset + size], 'little') >> 2
    require(value <= 0xffffffff, 'Packed integer exceeds U32')
    return value, offset + size


def probe_v8_prefix(raw):
    """Only the version/check flag/regular-count prefix, never the graph body."""
    require(len(raw) >= 18, 'Beacon input is too short for a v8 stream')
    version, checks = struct.unpack_from('<ii', raw)
    require(version == 8, 'Bounded candidate probe supports v8 only; native loader also accepts v6/v7')
    require(checks in (0, 1), 'Beacon check-marker flag must be zero or one')
    obsolete, offset = packed_u32(raw, 8)
    require(obsolete == 0, 'Unexpected obsolete bad-connections flag')
    if checks:
        require(raw[offset:offset + 7] == b'regular', 'Missing native regular section check marker')
        offset += 7
    count, offset = packed_u32(raw, offset)
    require(count <= 1000000, 'Regular beacon count exceeds preflight bound')
    require(len(raw) - offset >= count * 16, 'Truncated regular-beacon position/radius prefix')
    return {'version': version, 'check_markers': bool(checks), 'regular_beacon_count': count,
            'prefix_bytes_read': offset, 'structural_prefix_verified': True,
            'full_graph_structure_verified': False}


def probe_candidate(bcn, date=None, bcn_sha=None, date_sha=None, native_crc=None):
    raw = read_regular(bcn, MAX_BCN_BYTES)
    prefix = probe_v8_prefix(raw)
    result = {'status': 'candidate_unqualified', 'file': {'bytes': len(raw), 'sha256': sha256(raw)},
              'bcn_sha256_pin_verified': pin_matches(raw, bcn_sha), 'prefix': prefix,
              'native_graph_load_verified': False, 'authentic_generated_graph_verified': False,
              'loaded_world_crc_verified': False,
              'crc_evidence': {'status': 'missing_date_sidecar', 'matches_supplied_crc': None}}
    if date is not None:
        metadata = read_regular(date, 12)
        require(len(metadata) == 12, 'v9 beacon date sidecar must contain exactly three 32-bit fields')
        version, newest_data_time, full_map_crc = struct.unpack('<iII', metadata)
        require(version == 9, 'Only the current v9 CRC-bearing date sidecar is accepted by preflight')
        pinned = pin_matches(metadata, date_sha)
        result['date'] = {'bytes': len(metadata), 'sha256': sha256(metadata), 'version': version,
                          'latest_data_file_time': newest_data_time, 'full_map_crc': f'0x{full_map_crc:08x}',
                          'sha256_pin_verified': pinned}
        require(native_crc is None or type(native_crc) is int and 0 <= native_crc <= 0xffffffff,
                'Supplied native full-map CRC is outside U32')
        matches = None if native_crc is None else full_map_crc == native_crc
        if matches is False:
            raise AuditError('Date-sidecar CRC differs from supplied native full-map CRC')
        result['crc_evidence'] = {
            'status': 'supplied_crc_comparison_verified' if matches else 'native_full_map_crc_missing',
            'matches_supplied_crc': matches,
            'supplied_crc_provenance_verified': False,
            'scope': 'Comparison only: the tool does not execute beaconGetMapCRC(0,0,...) or bind this sidecar to this graph.'}
    else:
        require(date_sha is None and native_crc is None, 'A date sidecar is required for date pin or CRC comparison')
    result['remaining'] = ['Verify full graph body with the matching native readBeaconFile reader.',
                           'Calculate the full map CRC from the actual loaded Atlas geometry and match the v9 sidecar.',
                           'Establish generator/donor provenance and qualify a server-only installer.',
                           'Observe the genuine graph load and native pathing before NPC/combat acceptance.']
    return result


def inventory_paths(value):
    entries = value.get('entries', value.get('files'))
    require(isinstance(entries, (list, dict)), 'Inventory has no entries/files collection')
    paths = list(entries) if isinstance(entries, dict) else [entry.get('path') for entry in entries]
    require(all(isinstance(path, str) and PurePosixPath(path).as_posix() == path
                and '..' not in PurePosixPath(path).parts and not path.startswith('/')
                and '\\' not in path for path in paths), 'Invalid inventory path')
    return paths


def audit_repo(root=ROOT):
    target, _ = load_json(root / 'source-target.json')
    source_manifest, _ = load_json(root / 'docs/source-manifest.json')
    source_pins = {entry['path']: entry for entry in source_manifest['entries']}
    require(source_manifest['commit'] == target['source_commit'], 'Source snapshot commit differs')
    sources, texts = {}, {}
    for name in SOURCE_FILES:
        raw = read_regular(root / 'upstream/ouroboros' / name, MAX_JSON_BYTES)
        require(name in source_pins and source_pins[name]['sha256'] == sha256(raw)
                and source_pins[name]['size'] == len(raw), 'Native source differs from pinned snapshot: ' + name)
        sources[name] = {'bytes': len(raw), 'sha256': sha256(raw), 'snapshot_pin_verified': True}
        texts[name] = raw.decode('utf-8')
    file_text = texts[SOURCE_FILES[0]]
    constants = {name: int(re.search(r'\b' + name + r'\s*=\s*(\d+);', file_text).group(1))
                 for name in ('curBeaconFileVersion', 'oldestAllowableBeaconFileVersion', 'curBeaconDateFileVersion')}
    require(constants == {'curBeaconFileVersion': 8, 'oldestAllowableBeaconFileVersion': 6,
                          'curBeaconDateFileVersion': 9}, 'Native beacon contract changed; review preflight')
    table = texts[SOURCE_FILES[2]]
    commands = {name: bool(re.search(r'^\s*\{\s*9,\s*"' + name + '"', table, re.M))
                for name in ('beacongenerate', 'beaconprocess', 'beaconprocessforced',
                             'beaconprocesstraffic', 'beaconprocessnpc', 'beaconreadfile')}
    flags = re.findall(r'HANDLER\("(-beacon[^"\s]+)"\)', texts[SOURCE_FILES[1]])
    inventories = []
    for path, scope in INVENTORIES:
        value, pin = load_json(root / path)
        paths = inventory_paths(value)
        beacons = sorted(name for name in paths if name.casefold().endswith(('.bcn', '.bcn.date')))
        inventories.append(dict(path=path, scope=scope, pin=pin, entries=len(paths),
                                generated_beacon_files=beacons, physical_archive_bytes_inspected=False))
    # Bind the two shipped data inventories to their existing accepted metadata.
    receipt, _ = load_json(root / 'assets/reference-inputs-receipt.json')
    reference = next(item for item in inventories if item['scope'] == 'accepted_binary_asset_inventory')
    require(reference['pin']['sha256'] == receipt['manifest_sha256'], 'Accepted binary inventory pin differs')
    world_text = read_regular(root / 'android/guest/atlas_world_assets.py', MAX_JSON_BYTES).decode()
    world_pin = re.search(r"^MANIFEST_SHA256 = '([0-9a-f]{64})'", world_text, re.M).group(1)
    world_inventory = next(item for item in inventories if item['scope'] == 'shipped_atlas_geometry_texture_inventory')
    require(world_inventory['pin']['sha256'] == world_pin, 'Shipped world inventory pin differs')
    cache_review, _ = load_json(root / 'docs/android-evidence/client-test-package-review-36707839624.json')
    cache = next(item for item in inventories if item['scope'] == 'accepted_client_cache_inventory')
    require(cache['pin'] == cache_review['prepared_cache']['manifest'], 'Accepted cache inventory pin differs')
    present = any(item['generated_beacon_files'] for item in inventories)
    authored = 'data/maps/city_zones/city_01_01/city_01_01_layer_beacons.txt'
    data_manifest, _ = load_json(root / 'docs/data-manifest.json')
    authored_pin = next(entry for entry in data_manifest['entries'] if entry['path'] == authored)
    authored_raw = read_regular(root / 'upstream/i24' / authored, MAX_JSON_BYTES)
    require(sha256(authored_raw) == authored_pin['sha256'], 'Authored Atlas beacon placement layer differs')
    return {
        'format': 1, 'scope': 'atlas_beacon_input_preflight_only',
        'status': 'inventory_contains_beacon_candidates' if present else 'no_input',
        'preflight_completed': True, 'native_graph_load_verified': False,
        'authentic_generated_graph_verified': False, 'loaded_world_crc_verified': False,
        'source_commit': target['source_commit'], 'source_pins': sources,
        'native_contract': {
            'world': 'maps/City_Zones/City_01_01/City_01_01.txt',
            'current_file': 'server/maps/City_Zones/City_01_01/City_01_01.txt.v8.bcn',
            'date_sidecar': 'server/maps/City_Zones/City_01_01/City_01_01.txt.v8.bcn.date',
            'read_versions': [6, 7, 8], 'current_write_version': 8, 'date_version': 9,
            'date_fields': ['S32 version', 'U32 latestDataFileTime', 'U32 fullMapCRC'],
            'map_crc_route': 'beaconCalculateMapCRC -> beaconGetMapCRC(0, 0, printFullInfo)',
            'date_crc_is_not_a_graph_content_hash': True,
            'normal_beaconReload_checks_date_crc': False,
            'compatibility_check': 'beaconDoesTheBeaconFileMatchTheMap separately calculates full map CRC and reads the .date sidecar.'},
        'inventories': inventories,
        'authored_placement_layer': {'path': 'upstream/i24/' + authored,
                                    'sha256': sha256(authored_raw), 'snapshot_pin_verified': True,
                                    'is_generated_combat_graph': False},
        'generation_routes': {
            'chat_commands_active': commands, 'native_beaconizer_argument_handlers': sorted(flags),
            'matching_runtime_generator_qualified': False, 'bounded_one_map_generator_ready': False,
            'note': 'Source Beaconizer client/server modes exist; no runnable one-map generator is qualified by this audit.'},
        'installer': {'existing_world_supplement_accepts_bcn': False,
                      'requires_separate_server_only_verified_input_installer': True},
        'limitations': ['Inventory metadata inspected; archived APK/runtime payload bytes are not re-extracted.',
                        'Authored placements and generated client caches do not prove a native combat beacon graph.',
                        'A genuine BCN plus its v9 sidecar, provenance and actual loaded-world CRC remain required.'],
        'next_steps': ['Acquire a genuine Atlas v8 BCN and matching v9 date sidecar with donor/generator evidence.',
                       'Or qualify the native Beaconizer route for one pinned Atlas map under a bounded runtime.',
                       'Verify native graph reading, full-map CRC compatibility and server-only installation before NPC/combat.'],
        'runtime_or_apk_modified': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--bcn', type=Path, help='Optional supplied Atlas v8 graph; no installation occurs')
    parser.add_argument('--date', type=Path, help='Optional matching v9 .bcn.date sidecar')
    parser.add_argument('--bcn-sha256')
    parser.add_argument('--date-sha256')
    parser.add_argument('--native-map-crc', type=lambda value: int(value, 0), help='Caller-supplied full-map CRC; provenance is not established here')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    try:
        report = audit_repo(args.root)
        if args.bcn:
            report['candidate'] = probe_candidate(args.bcn, args.date, args.bcn_sha256,
                                                  args.date_sha256, args.native_map_crc)
            report['status'] = 'candidate_unqualified'
        else:
            require(not any((args.date, args.bcn_sha256, args.date_sha256, args.native_map_crc is not None)),
                    'Candidate evidence arguments require --bcn')
        exit_code = 0
    except (AuditError, OSError, ValueError, KeyError, StopIteration, AttributeError) as failure:
        report = {'format': 1, 'scope': 'atlas_beacon_input_preflight_only',
                  'status': 'invalid_input', 'preflight_completed': False,
                  'native_graph_load_verified': False, 'error': str(failure)}
        exit_code = 2
    raw = json.dumps(report, sort_keys=True, indent=2) + '\n'
    if args.out:
        args.out.write_text(raw, encoding='utf-8')
    else:
        print(raw, end='')
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
