"""Install source-bound genuine zone graphs into the shared zone tree.

Every static zone other than Atlas Park and King's Row runs from one shared
tree (prepare_zone_runtime) that had no beacon graph, so NPCs and pets there
could not walk to a target (Thor 0.13.63, Mercy Island: "Beacon file not loaded
for map: maps/City_Zones/V_City_01_01/V_City_01_01.txt"). Each graph here was
generated on the host from exactly that tree's world (generate_zone_beacons.py)
and the APK carries its archive, manifest and lock. Cold input hashes are
reused only while immutable world and graph fingerprints still match.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import time
import zipfile
import atlas_beacon_package as atlas

ROLE = 'authentic_native_zone_beacon_graph'
POLICY = 'native_shared_zone_tree_complete_collision_two_fresh_crc_graph_32routes_v1'
PROFILES = ('cold_world', 'reopened_world')
# Every static zone of the shared zone tree (map id: world folder, as zone_index.ZONES
# without Atlas Park 1 and King's Row 5, which keep their own trees and graphs).
# Mercy Island (71) first (0.13.65); every zone next (owner, 2026-11-09).
WORLDS = {
    3: 'city_03_04', 4: 'coop_02_01', 6: 'city_02_01', 7: 'city_02_02', 8: 'city_03_01', 9: 'city_03_02',
    10: 'city_04_01', 11: 'city_04_02', 12: 'hazard_01_01', 13: 'hazard_02_01', 14: 'hazard_03_01',
    15: 'hazard_04_01', 16: 'city_06_01', 17: 'v_city_06_01', 18: 'trial_01_01', 19: 'trial_02_01',
    20: 'trial_03_01', 21: 'trial_04_01', 22: 'trial_04_02', 23: 'trial_01_02', 24: 'city_00_01',
    29: 'city_01_03', 36: 'p_city_00_01', 37: 'p_city_00_02', 38: 'p_city_00_03', 39: 'p_city_00_06',
    40: 'p_city_00_05', 41: 'n_city_00_01', 42: 'p_city_00_07', 43: 'coop_06_01', 49: 'p_city_00_04',
    51: 'p_city_00_08', 52: 'p_city_00_09', 55: 'city_06_02', 56: 'v_city_06_02', 60: 'trial_05_01',
    61: 'city_05_01', 62: 'hazard_01_02', 63: 'hazard_01_03', 64: 'hazard_06_01', 65: 'hazard_06_02',
    66: 'hazard_06_03', 67: 'trial_06_01', 68: 'city_02_03', 69: 'hazard_03_02', 70: 'v_city_00_01',
    71: 'v_city_01_01', 72: 'v_city_01_02', 73: 'v_city_02_01', 74: 'v_city_03_01', 75: 'v_city_03_02',
    76: 'v_city_04_01', 77: 'v_city_05_01', 78: 'v_pvp_02_01', 79: 'v_pvp_03_01', 80: 'v_pvp_04_01',
    81: 'v_pvp_05_01', 82: 'city_03_03', 83: 'city_02_04', 84: 'city_02_05', 85: 'war_05_01',
    86: 'v_trial_04_02', 87: 'v_trial_04_03', 626: 'city_01_04'}
# A zone graph grows with its walkable area (Mercy Island: 407,225 beacons, 93,662,230
# bytes), so the largest zones may exceed the Atlas-sized bound; small indoor zones
# have far fewer beacons than Atlas Park. The native proofs below still apply.
MAX_GRAPH = 512 * 1024 * 1024
MAX_BEACONS = 4000000
# All zones' graphs (owner, 2026-11-09) come as a separate pack the app imports, like
# the asset pack: the APK carries its descriptor (this file beside the guest) and the
# app binds the imported objects (named by SHA-256) at /opt/coh-navigation.
NAVIGATION_PACK_ID = 'coh-navigation-maps'
NAVIGATION_DESCRIPTOR = 'navigation-maps-manifest.json'
NAVIGATION_ROOT = '/opt/coh-navigation'
require, canonical, pin = atlas.require, atlas.canonical, atlas.pin
# Collision inputs proven by a full hash: "device:inode" of the file an input resolves to ->
# [sha256, bytes, that file's state]. Zones share the object library, so a second zone's graph
# hashes only inputs not proven before; a proof file keeps them for later sessions.
_VERIFIED_INPUTS = {}
_LOADED_PROOFS = set()
PROOF_POLICY = 'resolved_input_inode_state_v1'
MAX_PROOFS = 200000
MAX_PROOF_BYTES = 64 * 1024 * 1024


def names(map_id):
    require(map_id in WORLDS, 'No zone graph is defined for map ' + str(map_id))
    world = WORLDS[map_id]
    map_name = 'maps/city_zones/' + world + '/' + world + '.txt'
    graph = 'data/server/' + map_name + '.v8.bcn'
    prefix = 'zone-beacons-' + str(map_id)
    return {'world': world, 'map': map_name, 'graph': graph, 'date': graph + '.date',
            'archive': prefix + '.zip', 'manifest': prefix + '-manifest.json', 'lock': prefix + '-lock.json',
            'marker': 'data/server/' + prefix + '-installed.json'}


def input_name(name, map_id):
    world = names(map_id)['world']
    return atlas.safe(name) and (name.startswith('data/object_library/') and name.lower().endswith(('.geo', '.txt', '.rootnames'))
        or name.startswith('data/maps/city_zones/' + world + '/') and name.lower().endswith('.txt')
        or name.startswith('data/tricks/') and name.lower().endswith('.txt'))


def pack_member(map_id, key):
    return 'runtime/' + names(map_id)[key]


def read_lock(lock, map_id):
    """The APK-owned pins of one zone graph: its lock file, or the APK's navigation map descriptor's."""
    if not isinstance(lock, dict):
        atlas.regular(lock, 4096, allow_shared_source=True); lock = json.loads(Path(lock).read_bytes())
    require(isinstance(lock, dict) and lock.get('format') == 1 and lock.get('map_id') == map_id
        and all(isinstance(lock.get(key), dict) and set(lock[key]) == {'bytes', 'sha256'} and type(lock[key]['bytes']) is int
                and 0 < lock[key]['bytes'] <= 2 * MAX_GRAPH and re.fullmatch('[0-9a-f]{64}', str(lock[key]['sha256']))
                for key in ('archive', 'manifest')), 'APK zone graph lock differs')
    return lock


def read_manifest(path, lock_path, map_id):
    zone = names(map_id)
    lock = read_lock(lock_path, map_id)
    atlas.regular(path, atlas.MAX_MANIFEST, allow_shared_source=True)
    require(pin(path) == lock.get('manifest'), 'Zone graph manifest differs from APK-owned lock')
    value = json.loads(Path(path).read_bytes()); native = value.get('native', {}); inputs = value.get('input_files', {})
    require(value.get('format') == 1 and value.get('role') == ROLE
        and value.get('map') == zone['map'] and value.get('map_id') == map_id
        and value.get('source_commit') == atlas.SOURCE_COMMIT and value.get('data_commit') == atlas.DATA_COMMIT
        and value.get('runtime_graph_readback') is True and value.get('physical_zoning_verified') is False,
        'Zone graph source/role differs')
    require(100 < len(inputs) <= atlas.MAX_INPUTS and all(input_name(n, map_id) for n in inputs)
        and 'data/' + zone['map'] in inputs and len({n.casefold() for n in inputs}) == len(inputs)
        and hashlib.sha256(canonical(inputs)).hexdigest() == value.get('input_files_sha256'),
        'Zone graph collision input identity differs')
    files = value.get('files', {})
    require(set(files) == {zone['graph'], zone['date']} and files[zone['date']].get('bytes') == 12
        and 18 < files[zone['graph']].get('bytes', 0) <= MAX_GRAPH, 'Zone native graph file closure differs')
    for row, limit in [*((row, MAX_GRAPH) for row in files.values()), *((row, atlas.MAX_GRAPH) for row in inputs.values())]:
        require(isinstance(row, dict) and set(row) == {'bytes', 'sha256'} and type(row['bytes']) is int
            and 0 < row['bytes'] <= limit and re.fullmatch('[0-9a-f]{64}', str(row['sha256'])),
            'Invalid zone graph payload pin')
    require(native.get('native_full_graph_readback_verified') is True
        and native.get('fresh_ordinary_world_crc_verified') is True
        and native.get('native_collision_load_verified') is True
        and native.get('missing_groups') == 0 and native.get('missing_root_models') == 0
        and native.get('native_pathfinder_successes') == 32 and native.get('date_version') == 9
        and 0 < native.get('connected_beacons', 0) <= native.get('combat_beacons', 0) <= MAX_BEACONS
        and native.get('ground_connections', 0) > 0 and native.get('grid_blocks', 0) > 0
        and re.fullmatch('0x[0-9a-f]{8}', str(native.get('full_world_crc'))),
        'Zone native collision/CRC/graph/path proof incomplete')
    # Only encounter spawn groups (markers, no geometry) may have loaded as empty placeholders.
    placeholders = native.get('noncollision_missing_groups', [])
    require(isinstance(placeholders, list) and len(placeholders) <= 16 and placeholders == sorted(set(placeholders))
        and ('noncollision_missing_groups' not in native or placeholders)
        and all(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9_./-]{1,200}', name)
                and name.casefold().startswith(('omni/encounterspawns/', 'object_library/omni/encounterspawns/'))
                for name in placeholders), 'Zone graph names a missing collision group')
    profiles = value.get('input_profiles', {})
    require(set(profiles) == set(PROFILES) and all(profiles[p] == {'native': native,
        'input_files_sha256': value['input_files_sha256']} for p in PROFILES), 'Zone native cold/reopen proofs differ')
    return value, lock


def available(assets):
    """Map ids whose archive, manifest and lock are all present beside this guest."""
    assets = Path(assets)
    return tuple(map_id for map_id in sorted(WORLDS)
                 if all((assets / names(map_id)[key]).exists() for key in ('archive', 'manifest', 'lock')))


def navigation_descriptor(assets):
    """The navigation map pack descriptor this APK pins, or None when it names no pack."""
    path = Path(assets) / NAVIGATION_DESCRIPTOR
    if not path.exists():
        return None
    atlas.regular(path, 1024 * 1024, allow_shared_source=True)
    value = json.loads(path.read_bytes())
    require(isinstance(value, dict) and value.get('format') == 1 and value.get('id') == NAVIGATION_PACK_ID
        and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', str(value.get('version'))) and isinstance(value.get('files'), dict)
        and isinstance(value.get('volumes'), dict), 'Navigation map pack descriptor differs')
    return value


def sources(assets, navigation=None):
    """Each zone's graph: the imported navigation map pack's (pinned by the APK's descriptor;
    objects named by SHA-256 under `navigation`), else one the APK carries itself (0.13.65)."""
    assets = Path(assets); found = {}
    for map_id in available(assets):
        zone = names(map_id)
        found[map_id] = {'origin': 'apk', 'archive': assets / zone['archive'], 'manifest': assets / zone['manifest'],
                         'lock': assets / zone['lock']}
    descriptor = None if navigation is None else navigation_descriptor(assets)
    if descriptor is None:
        return found
    root = Path(navigation)
    require(root.is_dir() and not root.is_symlink(), 'Navigation map objects are not a real directory')
    for map_id in sorted(WORLDS):
        archive, manifest = (descriptor['files'].get(pack_member(map_id, key)) for key in ('archive', 'manifest'))
        if not (isinstance(archive, dict) and isinstance(manifest, dict)):
            continue
        lock = read_lock({'format': 1, 'map_id': map_id, 'archive': archive, 'manifest': manifest}, map_id)
        paths = {key: root / lock[key]['sha256'] for key in ('archive', 'manifest')}
        if all(p.is_file() and not p.is_symlink() and p.stat().st_size == lock[key]['bytes'] for key, p in paths.items()):
            found[map_id] = {'origin': 'navigation_map_pack', 'version': descriptor['version'], **paths, 'lock': lock}
    return found


def input_state(path):
    """The file a collision input resolves to: its identity, size, times and mode.

    Thor 0.13.66: the shared zone tree holds every read-only input as a link to the imported
    data (local_character_server.stage_map_data), and a no-follow check here refused Mercy
    Island's graph ("Zone collision input is not a regular file"). The inventory has already
    accepted each link and its read-only regular target; the hash below reads that target.
    """
    info = os.stat(path)
    require(stat.S_ISREG(info.st_mode) and not info.st_mode & 0o222,
            'Zone collision input is not a read-only regular file')
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_mode]


def proven_input(path, expected, context):
    """Hash one collision input unless the same file state was proven before; bytes hashed."""
    before = input_state(path)
    key, proof = '%d:%d' % (before[0], before[1]), [expected['sha256'], expected['bytes'], before]
    if _VERIFIED_INPUTS.get(key) == proof:
        return 0
    require(pin(path, context) == expected and input_state(path) == before, 'Zone collision input differs: ' + str(path))
    _VERIFIED_INPUTS[key] = proof
    return expected['bytes']


def load_proofs(path):
    """Add the proofs an earlier session saved; an unusable file only costs the hashes again."""
    path = Path(path)
    if str(path) in _LOADED_PROOFS:
        return 0
    _LOADED_PROOFS.add(str(path))
    try:
        atlas.regular(path, MAX_PROOF_BYTES)
        value = json.loads(path.read_bytes())
        rows = value['proofs']
        require(value.get('format') == 1 and value.get('policy') == PROOF_POLICY and isinstance(rows, dict)
                and len(rows) <= MAX_PROOFS and all(
                    re.fullmatch('[0-9]+:[0-9]+', key) and isinstance(row, list) and len(row) == 3
                    and re.fullmatch('[0-9a-f]{64}', str(row[0])) and type(row[1]) is int
                    and isinstance(row[2], list) and len(row[2]) == 6 and all(type(n) is int for n in row[2])
                    and key == '%d:%d' % (row[2][0], row[2][1]) for key, row in rows.items()),
                'Zone collision input proofs differ')
    except Exception:  # any unusable proof file: hash again
        return 0
    for key, row in rows.items():
        _VERIFIED_INPUTS.setdefault(key, row)
    return len(rows)


def save_proofs(path):
    raw = canonical({'format': 1, 'policy': PROOF_POLICY, 'proofs': _VERIFIED_INPUTS})
    if len(_VERIFIED_INPUTS) <= MAX_PROOFS and len(raw) <= MAX_PROOF_BYTES:
        atlas.atomic_bytes(Path(path), raw)


def inventory(runtime, value, context, map_id, *, provider_records=None):
    return atlas.collision_input_snapshot(runtime, value['input_files'],
        (('data/object_library', ('.geo', '.txt', '.rootnames')),
         ('data/maps/city_zones/' + names(map_id)['world'], ('.txt',)), ('data/tricks', ('.txt',))),
        context, zone='zone ' + str(map_id), provider_records=provider_records)


def private_target(runtime, name, context, map_id):
    zone = names(map_id)
    require(name in (zone['graph'], zone['date'], zone['marker']), 'Zone graph private target scope differs')
    current = Path(runtime); atlas.world.real_directory(current)
    target = atlas.actual_targets(current, [name], context)[name]
    for part in target.relative_to(current).parts[:-1]:
        current /= part
        if not current.exists(): current.mkdir(mode=0o700)
        atlas.world.real_directory(current)
    require(not target.is_symlink(), 'Linked zone graph target')
    return target


def receipt_identity(source, runtime, map_id):
    """What a launch receipt for one zone's graph is bound to (0.13.70).

    The pack's lock and manifest for the zone, this code, and the shared zone tree itself.
    The receipt's directory rows (launch_receipts.py) then stand for the inputs: adding,
    removing, renaming or replacing an input or a graph file changes a row.
    """
    value, lock = read_manifest(source['manifest'], source['lock'], map_id)
    runtime = Path(runtime)
    code = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ('zone_beacon_package.py', 'atlas_beacon_package.py', 'launch_receipts.py')}
    return {'format': 1, 'step': 'zone_graph', 'map_id': map_id, 'policy': POLICY, 'origin': source['origin'],
            'lock': lock, 'input_files': len(value['input_files']), 'graph_files': sorted(value['files']),
            'code': code, 'tree_identity': [[info.st_dev, info.st_ino]
                                            for info in (os.lstat(runtime), os.lstat(runtime / 'data'))]}


def install(source, runtime, map_id, *, context, imported_inputs_readonly, proofs=None, leaves=None):
    """Verify one zone's graph (a `sources` entry) against the shared zone tree and write it there.

    `proofs` names a file that keeps the input hashes across sessions (565 MB for Mercy
    Island): an input is hashed again only when the file it resolves to has changed.
    """
    started = time.monotonic(); runtime = Path(runtime); zone = names(map_id)
    require(imported_inputs_readonly is True, 'Qualified readonly zone world required')
    value, lock = read_manifest(source['manifest'], source['lock'], map_id)
    inputs, input_targets = inventory(runtime, value, context, map_id)
    targets = {n: private_target(runtime, n, context, map_id) for n in value['files']}
    marker = private_target(runtime, zone['marker'], context, map_id)
    if leaves is not None:      # every file this result depends on, for the caller's launch receipt
        leaves.extend([*input_targets.values(), *targets.values(), marker])
    result = {'format': 1, 'verified': True, 'map_id': map_id, 'map': zone['map'], 'origin': source['origin'],
        'native_graph_readback_qualified': True, 'physical_zoning_verified': False,
        'full_world_crc': value['native']['full_world_crc'], 'combat_beacons': value['native']['combat_beacons'],
        'input_files_checked': len(inputs), 'input_validation': 'bounded_single_walk_inventory_and_fingerprints'}
    prior = None
    if marker.exists():
        try: atlas.regular(marker, atlas.MAX_MANIFEST); prior = json.loads(marker.read_bytes())
        except (OSError, ValueError): pass
    if isinstance(prior, dict) and prior.get('policy') == POLICY and prior.get('lock') == lock and prior.get('inputs') == inputs:
        if all(p.exists() for p in targets.values()) and prior.get('graphs') == atlas.fingerprints(runtime, targets, context):
            return dict(result, status='reused_verified_graph', installed_files=0, input_payload_bytes_hashed=0,
                        preparation_elapsed_seconds=round(time.monotonic() - started, 6))
    hashed = hashed_files = 0
    if proofs is not None:
        load_proofs(proofs)
    for name, expected in value['input_files'].items():
        context.check()
        size = proven_input(input_targets[name], expected, context)
        hashed += size; hashed_files += bool(size)
    require(inventory(runtime, value, context, map_id)[0] == inputs, 'Zone inputs changed during proof')
    if proofs is not None and hashed_files:
        save_proofs(proofs)
    archive = Path(source['archive']); manifest_bytes = Path(source['manifest']).read_bytes()
    require({'bytes': len(manifest_bytes), 'sha256': hashlib.sha256(manifest_bytes).hexdigest()} == lock['manifest'],
            'Zone graph manifest changed after validation')
    atlas.regular(archive, 2 * MAX_GRAPH, allow_shared_source=True)
    require(pin(archive, context) == lock['archive'], 'Zone graph archive differs from APK lock')
    installed = 0
    with zipfile.ZipFile(archive) as packed:
        entries = packed.infolist(); members = [e.filename for e in entries]
        require(len(members) == 3 and set(members) == {zone['graph'], zone['date'], zone['manifest']} and all(not e.is_dir()
            and not e.flag_bits & 1 and stat.S_IFMT(e.external_attr >> 16) in (0, stat.S_IFREG) for e in entries),
            'Zone graph archive closure unsafe')
        require(packed.read(zone['manifest']) == manifest_bytes, 'Zone embedded graph manifest differs')
        for name, expected in value['files'].items():
            context.check(); require(packed.getinfo(name).file_size == expected['bytes'], 'Zone graph member size differs')
            raw = packed.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected, 'Zone graph member hash differs')
            if name == zone['date']:
                version, newest, crc = struct.unpack('<iII', raw)
                require(version == 9 and f'0x{crc:08x}' == value['native']['full_world_crc'], 'Zone native date CRC differs')
            target = targets[name]
            if target.exists():
                atlas.regular(target, MAX_GRAPH); require(pin(target, context) == expected, 'Preserve existing different zone graph')
                target.chmod(0o400)
            else: atlas.atomic_bytes(target, raw); installed += 1
    require(inventory(runtime, value, context, map_id)[0] == inputs, 'Zone inputs changed before graph receipt')
    atlas.atomic_bytes(marker, canonical({'format': 1, 'policy': POLICY, 'lock': lock, 'inputs': inputs,
        'graphs': atlas.fingerprints(runtime, targets, context)}))
    return dict(result, status='installed_verified_graph', installed_files=installed, input_payload_bytes_hashed=hashed,
                input_files_hashed=hashed_files, preparation_elapsed_seconds=round(time.monotonic() - started, 6))
