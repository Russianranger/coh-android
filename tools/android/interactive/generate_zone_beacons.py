#!/usr/bin/env python3
"""Generate one shared-zone-tree map's genuine beacons and prove cold/reopened native world identity.

Mercy Island (map 71) first: Thor 0.13.63's MapServer logged "Beacon file not
loaded for map: maps/City_Zones/V_City_01_01/V_City_01_01.txt", so its pets and
NPCs could not walk to a target. The world is King's Row's generator world with
the shared zone tree's collision leaves (zone_index.COLLISION_FILES, a superset
of King's Row's 52) in place of King's Row's, which is what prepare_zone_runtime
builds on the phone. The separately compiled host tool (prepare_zone_beacon_
generator_source.py) takes its map from COH_ZONE_BEACON_MAP and fails on missing
world geometry or members. No host tool enters the APK. No host elapsed time is
an Android loading claim.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import time
import zipfile
import generate_kings_row_beacons as kings
shared = kings.shared
ROOT = shared.ROOT
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'android/guest'))
import prepare_zone_beacon_generator_source as producer
import zone_index
require, pin, canonical = shared.require, shared.pin, shared.canonical
PROFILES = ('cold_world', 'reopened_world')
MAX_GENERATION_SECONDS = 14400
ROLE = 'authentic_native_zone_beacon_graph'
SOURCE_FILES = ('tools/prepare_zone_beacon_generator_source.py', producer.PATCH,
                'tools/android/interactive/generate_zone_beacons.py',
                'tools/android/interactive/generate_kings_row_beacons.py',
                'tools/android/interactive/generate_atlas_beacons.py',
                'tools/prepare_atlas_beacon_generator_source.py', producer.atlas.PATCH,
                'android/guest/atlas_beacon_package.py', 'android/guest/zone_beacon_package.py',
                'android/guest/zone_index.py')
MAP_LINE = re.compile(rb'COH_ZONE_BEACON_MAP_V1 map=([a-z0-9_./]+)\r?\n')


def manifest_validator():
    """The shipped guest validator, run without its Android-only imports (as King's Row's)."""
    namespace = {'Path': Path, 'PurePosixPath': PurePosixPath, 'hashlib': hashlib,
                 'json': json, 're': re, 'stat': stat}
    atlas = kings.portable_definitions(ROOT / 'android/guest/atlas_beacon_package.py',
        {'SOURCE_COMMIT', 'DATA_COMMIT', 'MAX_MANIFEST', 'MAX_GRAPH', 'MAX_INPUTS',
         'require', 'canonical', 'regular', 'pin', 'safe'}, dict(namespace))
    return kings.portable_definitions(ROOT / 'android/guest/zone_beacon_package.py',
        {'ROLE', 'PROFILES', 'WORLDS', 'MAX_GRAPH', 'MAX_BEACONS', 'require', 'canonical', 'pin', 'names',
         'input_name', 'read_manifest'},
        dict(namespace, atlas=atlas))


def zone(map_id):
    """Names of one zone whose graph the guest accepts; never Atlas Park or King's Row.

    Six zones' audited source graphs name sky/moon models or one encounter group
    that the data lacks (zone_index.ZONES[...][2] False); they are not refused
    here because the native collision load itself must still report no missing
    group or root model before any graph is accepted.
    """
    guest = manifest_validator()
    require(map_id in zone_index.ZONES and map_id not in (1, 5)
            and map_id in guest.WORLDS and guest.WORLDS[map_id] == zone_index.world(map_id),
            'A static zone of the shared zone tree is required')
    value = guest.names(map_id)
    return dict(value, map_id=map_id, report='zone-beacons-%d-generation-report.json' % map_id)


def overlay_collision(archive_path, manifest_path, runtime):
    """The shared zone tree's leaves, as zone_asset_package.install(collision_names=...) writes them."""
    value = json.loads(Path(manifest_path).read_bytes())
    require(pin(archive_path) == {k: value['archive'][k] for k in ('bytes', 'sha256')}, 'Zone archive pin differs')
    names = zone_index.COLLISION_FILES
    require(hashlib.sha256(canonical(list(names))).hexdigest() == zone_index.COLLISION_FILES_SHA256
            and len(set(names)) == len(names) <= 4096
            and set(value.get('kings_row_collision_files', {})) <= set(names), 'Shared zone collision set differs')
    selected = {}
    for name in names:
        record = value['files'].get(name)
        require(isinstance(record, dict) and name.startswith('data/object_library/') and name.endswith('.geo'),
                'Shared zone leaf outside the pinned zone archive: ' + name)
        selected[name] = {k: record[k] for k in ('bytes', 'sha256')}
    targets = shared.resolve_world_targets(runtime, selected)
    installed = 0
    with zipfile.ZipFile(archive_path) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())), 'Zone archive duplicates')
        for name, record in selected.items():
            shared.safe(name)
            target = targets[name]
            if target.exists():
                require(pin(target) == record, 'Existing world geometry conflicts with the zone leaf: ' + name)
                continue
            with archive.open(name) as source: shared.copy_pinned(source, target, record)
            os.utime(target, (1767225600, 1767225600)); installed += 1
    return {'archive': pin(archive_path), 'manifest': pin(manifest_path), 'files': selected,
            'files_sha256': zone_index.COLLISION_FILES_SHA256, 'installed': installed}


def geometry_inputs(runtime, names):
    scopes = ('data/object_library', 'data/maps/city_zones/' + names['world'], 'data/tricks')
    targets = shared.resolve_world_targets(runtime, [scope + '/.zone-inventory' for scope in scopes])
    records = {}; seen = set(); count = 0
    for scope in scopes:
        root = targets[scope + '/.zone-inventory'].parent
        require(root.is_dir() and not root.is_symlink(), 'Missing collision root: ' + scope)
        for path in root.rglob('*'):
            count += 1
            name = path.relative_to(runtime).as_posix()
            require(count <= 200000 and not path.is_symlink() and name.casefold() not in seen, 'Unsafe/ambiguous collision tree')
            seen.add(name.casefold())
            if path.is_dir(): continue
            require(path.is_file(), 'Special collision input')
            suffixes = ('.geo', '.txt', '.rootnames') if scope == 'data/object_library' else ('.txt',)
            if path.suffix.casefold() in suffixes: records[shared.canonical_input_name(name)] = pin(path)
    require(100 < len(records) <= 12288 and ('data/' + names['map']) in records, 'Incomplete zone world input inventory')
    return dict(sorted(records.items()))


def native_evidence(log, date, names):
    # Share the v8 reader / v9 CRC / 32-path parser, never an Atlas graph or pin.
    require(MAP_LINE.findall(log) == [names['map'].encode()], 'Native graph proof names another map')
    require(log.count(b'COH_ZONE_COLLISION_LOAD_V1 missing_groups=0 missing_root_models=0') == 1,
            'Fresh collision load failed or lacks missing-input refusal witness')
    require(b'Host zone collision missing' not in log, 'Native world collision input missing')
    result = shared.native_evidence(log.replace(b'COH_ZONE_BEACON_', b'COH_ATLAS_BEACON_'), date)
    return dict(result, missing_groups=0, missing_root_models=0, native_collision_load_verified=True)


DEFAULT_WORKERS = 3
MAX_WORKERS = 8


def worker_roles(workers):
    """The owned worker clients: 'worker', then 'worker2'... (one Mercy Island worker took 2 h 20 min)."""
    require(type(workers) is int and 1 <= workers <= MAX_WORKERS, 'Owned worker count must be 1-8')
    return tuple('worker' if index == 1 else 'worker%d' % index for index in range(1, workers + 1))


def role_environment(names, verify=False, workers=None):
    env = shared.role_environment()
    env.pop('COH_ZONE_BEACON_VERIFY_ONLY', None); env.pop('COH_KINGS_ROW_BEACON_VERIFY_ONLY', None)
    env.pop(producer.WORKER_ENVIRONMENT, None)
    env['COH_ZONE_BEACON_MAP'] = names['map']
    if verify: env['COH_ZONE_BEACON_VERIFY_ONLY'] = '1'
    if workers is not None:
        worker_roles(workers); env[producer.WORKER_ENVIRONMENT] = str(workers)
    return env


def worker_summary(evidence, workers):
    """How much of the native work each owned worker did (blocks and beacon batches)."""
    summary = {}
    for role in worker_roles(workers):
        raw = (evidence / (role + '.log')).read_bytes()
        summary[role] = {'log_bytes': len(raw), 'blocks': raw.count(b'Processing '), 'beacon_batches': raw.count(b'Connecting ')}
    return summary


def run_generation(runtime, generator, evidence, timeout, names, workers=DEFAULT_WORKERS):
    common = ['-nogui', '-nopigs', '-noencrypt', '-beaconallownovodex', '-beacondatatoolsrootpath', str(runtime)]
    client = ['-beaconclient', '127.0.0.1', '-beaconworkduringuseractivity']
    roles = [('master', ['-beaconmasterserver', '-beaconrequestcachedir', str(runtime.parent / 'requests')]),
             ('server', ['-beaconserver', '127.0.0.1', '-beacononepassonly', '-beaconforcerebuild']),
             ('sentry', client), *((role, client) for role in worker_roles(workers))]
    environment = role_environment(names, workers=workers)
    processes, logs, commands = {}, {}, {}; started = time.monotonic(); failure = None
    try:
        for role, flags in roles:
            command = [str(generator), *common, *flags]; commands[role] = command
            logs[role] = (evidence / (role + '.log')).open('wb')
            processes[role] = subprocess.Popen(command, cwd=runtime, env=environment, stdin=subprocess.DEVNULL,
                                               stdout=logs[role], stderr=subprocess.STDOUT)
            if role in ('master', 'sentry'):
                marker = b'BEACON MASTER SERVER RUNNING' if role == 'master' else b"I'm the sentry!!!"
                deadline = min(started + timeout, time.monotonic() + 300)
                while marker not in (evidence / (role + '.log')).read_bytes():
                    require((evidence / (role + '.log')).stat().st_size <= shared.MAX_LOG, 'Native startup log limit')
                    require(processes[role].poll() is None and time.monotonic() < deadline, 'Native role failed: ' + role)
                    time.sleep(.5)
                if role == 'sentry':
                    # The native sentry names the owned count it accepts; it ends any client beyond it.
                    require((evidence / 'sentry.log').read_bytes().count(
                        b'COH_ZONE_BEACON_WORKERS_V1 workers=%d' % workers) == 1, 'Native sentry worker count differs')
        heartbeat = 0
        while processes['server'].poll() is None:
            require(time.monotonic() - started < timeout, 'Zone generation time bound exceeded')
            for role, process in processes.items():
                require((evidence / (role + '.log')).stat().st_size <= shared.MAX_LOG, 'Native role log bound')
                require(role == 'server' or process.poll() is None, 'Native role exited: ' + role)
            if time.monotonic() >= heartbeat:
                shared.record_role_heartbeat(evidence, processes, started, 'zone_generation')
                heartbeat = time.monotonic() + 60
            time.sleep(1)
        require(processes['server'].returncode == 0, 'Native zone graph producer failed')
    except BaseException as error:
        failure = error; raise
    finally:
        before = {role: p.poll() for role, p in processes.items()}
        kings.stop_roles(processes)
        for stream in logs.values(): stream.close()
        if failure: shared.record_role_failure(evidence, processes, commands, failure, before)
    return commands


def verify_profile(runtime, generator, evidence, profile, timeout, names):
    shared.clear_private_geometry_caches(runtime)
    command = [str(generator), '-nogui', '-nopigs', '-noencrypt', '-beaconallownovodex',
               '-beacondatatoolsrootpath', str(runtime), '-beaconserver', '127.0.0.1', '-beaconnonetstart']
    path = evidence / (profile + '.log')
    with path.open('wb') as log:
        process = subprocess.Popen(command, cwd=runtime, env=role_environment(names, True), stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + min(timeout, 900)
            while process.poll() is None:
                require(time.monotonic() < deadline and path.stat().st_size <= shared.MAX_LOG, 'Fresh native proof bound')
                time.sleep(.5)
            require(process.returncode == 0, 'Fresh native proof failed: ' + profile)
        finally: kings.stop_roles({profile: process})
    return native_evidence(path.read_bytes(), (runtime / names['date']).read_bytes(), names), command


def validate_package(directory, map_id, repository_commit=None):
    names = zone(map_id)
    directory = Path(directory); value = json.loads((directory / names['manifest']).read_bytes())
    report = json.loads((directory / names['report']).read_bytes())
    guest = manifest_validator()
    locked_value, lock = guest.read_manifest(directory / names['manifest'], directory / names['lock'], map_id)
    require(locked_value == value and lock['archive'] == pin(directory / names['archive']), 'APK lock or graph differs')
    require(value['format'] == 1 and value['role'] == ROLE and value['map'] == names['map']
            and value['map_id'] == map_id and value['physical_zoning_verified'] is False, 'Zone graph identity differs')
    require(report['status'] == 'passed' and report['cleanup_complete'] is True and report['owned_roles'] == 0
            and report['native_worker_spawning_allowed'] is False and report['build_input'] == producer.expected(),
            'Zone generator provenance or cleanup differs')
    if repository_commit is not None: require(report['repository_commit'] == repository_commit, 'Zone source commit differs')
    require(report['manifest'] == pin(directory / names['manifest']) and report['archive'] == pin(directory / names['archive'])
            and report['native'] == value['native'] and report['profile_proofs'] == value['input_profiles']
            and report['map_id'] == map_id and report['map'] == names['map']
            and report['source_files'] == {n: pin(ROOT / n) for n in SOURCE_FILES}, 'Zone package source/proof pins differ')
    require(set(value['input_profiles']) == set(PROFILES), 'Both fresh native proofs required')
    for profile in PROFILES:
        require(value['input_profiles'][profile] == {'native': value['native'], 'input_files_sha256': value['input_files_sha256']},
                'Native proof profiles differ')
    require(hashlib.sha256(canonical(value['input_files'])).hexdigest() == value['input_files_sha256'], 'Collision source inventory differs')
    require(value['zone_collision']['files_sha256'] == zone_index.COLLISION_FILES_SHA256
            and list(value['zone_collision']['files']) == sorted(zone_index.COLLISION_FILES),
            'Zone graph was not generated from the shared zone tree leaves')
    with zipfile.ZipFile(directory / names['archive']) as archive:
        require(set(archive.namelist()) == {names['graph'], names['date'], names['manifest']} and len(archive.namelist()) == 3,
                'Zone graph archive closure differs')
        require(archive.read(names['manifest']) == (directory / names['manifest']).read_bytes(), 'Embedded manifest differs')
        for name in (names['graph'], names['date']):
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == value['files'][name], 'Graph payload differs')
    return value


def generate(args):
    require(os.name == 'nt', 'Genuine native generation requires Windows')
    require(60 <= args.timeout_seconds <= MAX_GENERATION_SECONDS and re.fullmatch('[0-9a-f]{40}', args.repository_commit),
            'Bounded exact source invocation required')
    names = zone(args.map_id); worker_roles(args.workers)
    for name in ('donor_apk', 'asset_archive', 'zones_archive', 'zones_manifest', 'generator', 'build_input', 'work', 'output'):
        setattr(args, name, Path(getattr(args, name)).resolve())
    require(not args.work.exists() and not args.output.exists(), 'Fresh native owned directories required')
    args.work.mkdir(parents=True); args.output.mkdir(parents=True); evidence = args.output / 'evidence'; evidence.mkdir()
    build = json.loads(args.build_input.read_bytes()); require(build == producer.expected(), 'Host generator source receipt differs')
    assets = args.work / 'donor'; kings.extract_donor(args.donor_apk, assets)
    data = shared.import_data(assets, args.asset_archive, args.work, evidence).resolve(strict=True)
    runtime = args.work / 'r'; data.parent.rename(runtime)
    shared.extract_tar(assets / 'runtime/game-package.tar.gz', runtime, 'game-package.json')
    shared.extract_tar(assets / 'runtime/dbserver-schema.tar.gz', runtime, 'schema-manifest.json')
    shared.overlay_zip(assets / 'runtime/atlas-world-supplement.zip', assets / 'runtime/atlas-world-supplement-manifest.json', runtime)
    # The same accepted required 406 original object GEOs as King's Row's world.
    visual = json.loads((assets / 'runtime/client-visual-manifest.json').read_bytes())
    selected = {n: r for n, r in visual['files'].items() if n.startswith('data/object_library/') and n.endswith('.geo')}
    require(len(selected) == 406, 'Retained Atlas object geometry identity changed')
    targets = shared.resolve_world_targets(runtime, selected)
    with zipfile.ZipFile(assets / 'runtime/client-visual-assets.zip') as archive:
        for name, row in selected.items():
            target = targets[name]
            if target.exists(): require(pin(target) == {k: row[k] for k in ('bytes', 'sha256')}, 'Retained original overlap differs'); continue
            with archive.open(name) as source: shared.copy_pinned(source, target, row)
    collision = overlay_collision(args.zones_archive, args.zones_manifest, runtime)
    for path in (runtime / 'data').rglob('*'):
        if path.is_file(): os.utime(path, (1767225600, 1767225600))
    # geometry_inputs also refuses a world without the zone's own map file.
    inputs = geometry_inputs(runtime, names); cold = args.work / 'c'; mirror = shared.mirror_cold_runtime(runtime, cold)
    mirror.pop('created_before_visual_overlay_and_generation')
    mirror.update(created_before_generation=True, required_geometry_installed_before_mirror=True)
    generator = runtime / 'ZoneBeaconGenerator.exe'; shutil.copyfile(args.generator, generator)
    (runtime / 'tools').mkdir(exist_ok=True)
    started = time.monotonic()
    commands = run_generation(runtime, generator, evidence, args.timeout_seconds, names, args.workers)
    generated_at = round(time.monotonic() - started, 3); workers = worker_summary(evidence, args.workers)
    require(all((runtime / n).is_file() for n in (names['graph'], names['date'])), 'Native graph/date absent')
    witness = native_evidence((evidence / 'server.log').read_bytes(), (runtime / names['date']).read_bytes(), names)
    profiles = {}
    for profile, tree in (('cold_world', cold), ('reopened_world', runtime)):
        if tree != runtime:
            for name in (names['graph'], names['date']):
                target = tree / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(runtime / name, target)
            shutil.copyfile(generator, tree / generator.name)
        proof, command = verify_profile(tree, tree / generator.name, evidence, profile, args.timeout_seconds, names)
        require(proof == witness and geometry_inputs(tree, names) == inputs, 'Fresh world graph/CRC/path/input mismatch')
        profiles[profile] = {'native': proof, 'input_files_sha256': hashlib.sha256(canonical(inputs)).hexdigest()}; commands[profile] = command
    manifest = {'format': 1, 'role': ROLE, 'map': names['map'], 'map_id': args.map_id,
                'source_commit': build['source_commit'], 'data_commit': visual['data_commit'],
                'files': {n: pin(runtime / n) for n in (names['graph'], names['date'])}, 'native': witness,
                'input_files': inputs, 'input_files_sha256': hashlib.sha256(canonical(inputs)).hexdigest(),
                'input_profiles': profiles, 'zone_collision': {k: collision[k] for k in ('archive', 'manifest', 'files', 'files_sha256')},
                'generator': pin(generator), 'runtime_graph_readback': True, 'physical_zoning_verified': False}
    raw = canonical(manifest); (args.output / names['manifest']).write_bytes(raw)
    with zipfile.ZipFile(args.output / names['archive'], 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in (names['graph'], names['date']): archive.write(runtime / name, name)
        archive.writestr(names['manifest'], raw)
    report = {'format': 1, 'status': 'passed', 'repository_commit': args.repository_commit, 'build_input': build,
              'map': names['map'], 'map_id': args.map_id,
              'generator': pin(generator), 'donor': kings.DONOR, 'archive': pin(args.output / names['archive']),
              'manifest': pin(args.output / names['manifest']), 'native': witness, 'profile_proofs': profiles,
              'commands': commands, 'cleanup_complete': True, 'owned_roles': 0,
              'native_worker_spawning_allowed': False, 'owned_workers': args.workers, 'worker_work': workers,
              'physical_zoning_verified': False, 'cold_mirror': mirror,
              'collision_leaves_installed': collision['installed'],
              'source_files': {n: pin(ROOT / n) for n in SOURCE_FILES}, 'generation_seconds': generated_at,
              'elapsed_seconds': round(time.monotonic() - started, 3)}
    (args.output / names['report']).write_bytes(canonical(report))
    (args.output / names['lock']).write_bytes(canonical({'format': 1, 'map_id': args.map_id,
                                                         'archive': report['archive'], 'manifest': report['manifest']}))
    validate_package(args.output, args.map_id, args.repository_commit)
    print(json.dumps({'status': 'passed', 'map_id': args.map_id, 'native': witness, 'archive': report['archive']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('donor-apk', 'asset-archive', 'zones-archive', 'zones-manifest', 'generator', 'build-input', 'work', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--map-id', required=True, type=int)
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--timeout-seconds', type=int, default=5400)
    parser.add_argument('--workers', type=int, default=DEFAULT_WORKERS,
                        help='Owned native worker clients (1-8); the sentry accepts exactly this many')
    generate(parser.parse_args())
