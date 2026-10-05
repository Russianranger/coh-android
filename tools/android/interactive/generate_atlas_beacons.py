#!/usr/bin/env python3
"""Generate one genuine Atlas graph with four bounded owned native Win32 roles.

The host-only executable never ships. The unchanged algorithms generate from
exact imported/supplemented data; the native server reopens the graph, compares
its date CRC with a freshly loaded ordinary world, and proves 32 native routes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
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
MAX_FAILURE_TAIL = 8192
VISUAL_OBJECT_GEOS = 406
PROFILES = ('base_world', 'base_world_visual')
VISUAL_MANIFEST_PIN = {'bytes': 42553059, 'sha256': 'e1f1702c9d5b38f38bb324b1171ac7aeaa5cba7e12072dd8face4efbc09a5fa3'}
VISUAL_GEO_SOURCE_SHA256 = '208393ade4edbb9608e200fc7103279217ce95a0cc316eac8018bfe558f54f1f'
VISUAL_OBJECT_SOURCE_SHA256 = 'c5eddbe19511356d1c9eb26890728b169db6989917da9e1375b6f1692f41bb43'
NATIVE = re.compile(rb'COH_ATLAS_BEACON_NATIVE_V1 crc=(0x[0-9a-fA-F]{8}) combat=(\d+) connected=(\d+) ground=(\d+) raised=(\d+) blocks=(\d+) paths=(\d+)')
GENERATION_SOURCES = (
    'tools/prepare_atlas_beacon_generator_source.py',
    'tools/android/interactive/generate_atlas_beacons.py', producer.PATCH,
    'android/atlas/src/main/java/io/github/russianranger/cohatlas/AtlasAssetImporter.java',
    'tools/android/atlas/java/io/github/russianranger/cohatlas/HostImport.java',
    'assets/reference-inputs-receipt.json', 'source-target.json',
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
    record = {'format': 1, 'status': 'passed' if warm == expected and cold == common else 'mismatch',
              'common_files': len(common), 'optional_files': len(optional),
              'common_sha256': hashlib.sha256(canonical(common)).hexdigest(),
              'optional_physical_geometry_sha256': hashlib.sha256(canonical(optional)).hexdigest(),
              'warm_sha256': hashlib.sha256(canonical(warm)).hexdigest(),
              'cold_sha256': hashlib.sha256(canonical(cold)).hexdigest(),
              'warm_difference': difference(warm, expected), 'cold_difference': difference(cold, common)}
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
    with zipfile.ZipFile(path) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist()))
                and set(archive.namelist()) == set(manifest['files']), 'Visual ZIP closure differs')
        for name, expected in selected.items():
            safe(name); target = runtime / name
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
        private = (relative.parts[0] != 'data' or len(relative.parts) > 1
                   and relative.parts[1] in ('bin', 'geobin', 'server'))
        if private:
            shutil.copyfile(source, target); target.chmod(0o600)
        else:
            source.chmod(0o400); os.link(source, target)
    return {'files': count, 'bytes': total, 'readonly_inputs_hardlinked': True,
            'private_cache_roots': ['data/bin', 'data/geobin', 'data/server'],
            'created_before_visual_overlay_and_generation': True}


def geometry_inputs(runtime):
    """Physical collision donors plus Atlas placement/trick source inputs."""
    data = runtime / 'data'
    paths = set((data / 'object_library').rglob('*.geo'))
    paths.update((data / 'object_library').rglob('*.txt'))
    paths.update((data / 'maps/city_zones/city_01_01').rglob('*.txt'))
    paths.update((data / 'tricks').rglob('*.txt'))
    require(100 < len(paths) <= 12288 and all(path.is_file() and not path.is_symlink() for path in paths),
            'Collision input scope exceeds producer bound')
    return {path.relative_to(runtime).as_posix(): pin(path) for path in sorted(paths)}


def native_evidence(log, date):
    matches = NATIVE.findall(log)
    require(len(matches) == 1, 'One native graph/CRC/path witness required')
    crc, *values = matches[0]
    combat, connected, ground, raised, blocks, paths = map(int, values)
    require(1000 < combat <= 1000000 and 1000 < connected <= combat and ground > 1000
            and raised >= 0 and blocks > 0 and paths == 32, 'Native graph/path witness outside bounds')
    require(len(date) == 12, 'Native v9 date sidecar must have exactly 12 bytes')
    version, newest, date_crc = struct.unpack('<iII', date)
    require(version == 9 and date_crc == int(crc, 16), 'Native loaded-world CRC and date sidecar differ')
    return {'full_world_crc': f'0x{date_crc:08x}', 'combat_beacons': combat,
            'connected_beacons': connected, 'ground_connections': ground,
            'raised_connections': raised, 'grid_blocks': blocks, 'native_pathfinder_successes': paths,
            'date_version': version, 'date_latest_data_time': newest,
            'fresh_ordinary_world_crc_verified': True, 'native_full_graph_readback_verified': True}


def validate_package(directory, repository_commit):
    directory = Path(directory)
    value = json.loads((directory / REPORT).read_bytes())
    require(value.get('format') == 2 and value.get('status') == 'passed' and re.fullmatch('[0-9a-f]{40}', value.get('repository_commit', ''))
            and re.fullmatch('[0-9a-f]{40}', repository_commit), 'Generation provenance/commit differs')
    require(value.get('generation_sources') == {name: pin(ROOT / name) for name in GENERATION_SOURCES},
            'Generation implementation changed; a fresh native generation is required')
    require(value['build_input'] == producer.expected(), 'Host producer source receipt differs')
    require(value['donor'] == DONOR and value['stock_mapserver_sha256'] == STOCK_MAPSERVER,
            'Stock native compatibility differs')
    require(value.get('cleanup_complete') is True and value.get('owned_roles') == 4
            and value.get('native_worker_spawning_allowed') is False,
            'Owned native generation containment/cleanup proof differs')
    for name, expected in value['evidence'].items():
        require(pin(directory / safe(name)) == expected, 'Generation evidence changed')
    manifest = json.loads((directory / MANIFEST).read_bytes())
    require(pin(directory / MANIFEST) == value['manifest'] and pin(directory / ARCHIVE) == value['archive'],
            'Generated package pin differs')
    require(manifest.get('format') == 2 and manifest['map'] == producer.MAP and set(manifest['files']) == {GRAPH, DATE}
            and manifest['stock_mapserver_sha256'] == STOCK_MAPSERVER, 'Generated graph scope differs')
    require(manifest['native'] == native_evidence((directory / 'evidence/server.log').read_bytes(),
                                                 _date_from_archive(directory / ARCHIVE)), 'Native transcript differs')
    identity = manifest['input_identity']
    require(identity['visual_source_manifest'] == VISUAL_MANIFEST_PIN
            and identity['visual_geometry_sha256'] == VISUAL_GEO_SOURCE_SHA256
            and identity['visual_object_geometry_sha256'] == VISUAL_OBJECT_SOURCE_SHA256,
            'Original donor geometry source provenance differs')
    common, optional = manifest['input_files'], manifest['optional_input_files']
    require(len(optional) == VISUAL_OBJECT_GEOS and not set(common).intersection(optional)
            and set(manifest['input_profiles']) == set(PROFILES), 'Native input profiles differ')
    require(manifest['input_files_sha256'] == hashlib.sha256(canonical(common)).hexdigest()
            and manifest['input_identity']['optional_physical_geometry_sha256']
                == hashlib.sha256(canonical(optional)).hexdigest(), 'Native physical input pins differ')
    for profile in PROFILES:
        selected = common if profile == 'base_world' else {**common, **optional}
        native = native_evidence((directory / ('evidence/' + profile + '.log')).read_bytes(),
                                _date_from_archive(directory / ARCHIVE))
        require(native == manifest['native'] == manifest['input_profiles'][profile]['native']
                and hashlib.sha256(canonical(selected)).hexdigest()
                == manifest['input_profiles'][profile]['input_files_sha256'], 'Fresh native profile proof differs')
    require(value['profile_verification_processes'] == 2 and value['profile_proofs'] == manifest['input_profiles']
            and value['cold_mirror']['created_before_visual_overlay_and_generation'] is True,
            'Fresh isolated native profile provenance differs')
    with zipfile.ZipFile(directory / ARCHIVE) as archive:
        require(len(archive.namelist()) == 3 and set(archive.namelist()) == {GRAPH, DATE, MANIFEST}, 'Beacon package closure differs')
        require(archive.read(MANIFEST) == (directory / MANIFEST).read_bytes(), 'Embedded manifest differs')
        for name, expected in manifest['files'].items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected, 'Graph pin differs')
    return manifest


def _date_from_archive(path):
    with zipfile.ZipFile(path) as archive: return archive.read(DATE)


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
    return env


def generate(args):
    require(os.name == 'nt', 'Native generation requires an isolated Windows runner')
    for name in ('donor_apk', 'donor_receipt', 'asset_archive', 'generator', 'build_input', 'work', 'output'):
        setattr(args, name, Path(getattr(args, name)).resolve())
    require(30 <= args.timeout_seconds <= 5400 and re.fullmatch('[0-9a-f]{40}', args.repository_commit), 'Invalid timeout/commit')
    require(not args.work.exists() and not args.output.exists(), 'Fresh generator work/output required')
    args.work.mkdir(parents=True); args.output.mkdir(parents=True)
    evidence = args.output / 'evidence'; evidence.mkdir()
    build_input = json.loads(args.build_input.read_bytes())
    require(build_input == producer.expected(), 'Native generator source receipt differs')
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
    cold_runtime = args.work / 'c'
    cold_mirror = mirror_cold_runtime(runtime, cold_runtime)
    visual_path = assets / 'runtime/client-visual-manifest.json'
    visual, optional_inputs = overlay_object_geometry(assets / 'runtime/client-visual-assets.zip', visual_path, runtime)
    for name in optional_inputs: os.utime(runtime / name, (1767225600, 1767225600))
    inputs = geometry_inputs(runtime)
    inventory = record_profile_inventory(evidence, common_inputs, optional_inputs, inputs, geometry_inputs(cold_runtime))
    require(inventory['status'] == 'passed', 'Cold/warm physical geometry profiles differ from their exact inventories')
    (runtime / 'tools').mkdir(exist_ok=True)
    generator = runtime / 'AtlasBeaconGenerator.exe'; shutil.copyfile(args.generator, generator)
    env = role_environment()
    common = ['-nogui', '-nopigs', '-noencrypt', '-beaconallownovodex', '-beacondatatoolsrootpath', str(runtime)]
    requests = (args.work / 'requests').resolve()
    require(runtime.is_absolute() and requests.is_absolute(), 'Native cwd/root/cache paths must be absolute')
    roles = [('master', ['-beaconmasterserver', '-beaconrequestcachedir', str(requests)]),
             ('server', ['-beaconserver', '127.0.0.1', '-beacononepassonly', '-beaconforcerebuild']),
             ('sentry', ['-beaconclient', '127.0.0.1', '-beaconworkduringuseractivity']),
             ('worker', ['-beaconclient', '127.0.0.1', '-beaconworkduringuseractivity'])]
    processes, logs, commands, failure, before_cleanup = {}, {}, {}, None, {}
    started = time.monotonic()
    try:
        for role, flags in roles:
            command = [str(generator), *common, *flags]; commands[role] = command
            logs[role] = (evidence / (role + '.log')).open('wb')
            processes[role] = subprocess.Popen(command, cwd=runtime, env=env, stdin=subprocess.DEVNULL,
                                                stdout=logs[role], stderr=subprocess.STDOUT)
            if role in ('master', 'sentry'):
                expected = b'BEACON MASTER SERVER RUNNING' if role == 'master' else b"I'm the sentry!!!"
                deadline = min(started + args.timeout_seconds, time.monotonic() + 300)
                while expected not in (evidence / (role + '.log')).read_bytes():
                    require((evidence / (role + '.log')).stat().st_size <= MAX_LOG, 'Native role startup log exceeded bound')
                    require(processes[role].poll() is None and time.monotonic() < deadline, 'Native role startup failed: ' + role)
                    time.sleep(0.5)
        while processes['server'].poll() is None:
            require(time.monotonic() - started < args.timeout_seconds, 'Atlas generation exceeded owned deadline')
            for role, path in ((role, evidence / (role + '.log')) for role in processes):
                require(path.stat().st_size <= MAX_LOG, 'Native role log exceeded bound')
                require(role == 'server' or processes[role].poll() is None, 'Owned native role exited: ' + role)
            time.sleep(1)
        require(processes['server'].returncode == 0, 'Native Atlas graph producer failed')
    except Exception as error:
        failure = error
        raise
    finally:
        before_cleanup = {role: process.poll() for role, process in processes.items()}
        for process in processes.values():
            if process.poll() is None: process.terminate()
        for process in processes.values():
            try: process.wait(timeout=15)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=15)
        for stream in logs.values(): stream.close()
        if failure is not None: record_role_failure(evidence, processes, commands, failure, before_cleanup)
    require((runtime / GRAPH).is_file() and (runtime / DATE).is_file(), 'Native graph files missing')
    require(geometry_inputs(runtime) == inputs, 'Native generation modified an immutable collision input')
    witness = native_evidence((evidence / 'server.log').read_bytes(), (runtime / DATE).read_bytes())
    profile_proofs = {}
    for profile, profile_runtime in (('base_world', cold_runtime), ('base_world_visual', runtime)):
        for name in (GRAPH, DATE):
            target = profile_runtime / name
            if profile_runtime != runtime:
                target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(runtime / name, target); target.chmod(0o400)
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
        require(geometry_inputs(profile_runtime) == (common_inputs if profile == 'base_world' else inputs),
                'Fresh native readback modified an immutable input: ' + profile)
        verified = native_evidence(log_path.read_bytes(), (profile_runtime / DATE).read_bytes())
        require(verified == witness, 'Cold/warm full-world CRC or graph/path proof differs')
        selected = common_inputs if profile == 'base_world' else inputs
        profile_proofs[profile] = {'native': verified, 'input_files_sha256': hashlib.sha256(canonical(selected)).hexdigest()}
    geo_files = {name: value for name, value in visual['files'].items() if name.endswith('.geo')}
    manifest = {'format': 2, 'role': 'authentic_native_atlas_beacon_graph', 'map': producer.MAP,
                'stock_mapserver_sha256': STOCK_MAPSERVER, 'source_commit': build_input['source_commit'],
                'data_commit': visual['data_commit'], 'files': {name: pin(runtime / name) for name in (GRAPH, DATE)},
                'native': witness, 'input_identity': {'asset_archive': pin(args.asset_archive),
                    'world_manifest': pin(assets / 'runtime/atlas-world-supplement-manifest.json'),
                    'visual_source_manifest': pin(visual_path),
                    'visual_geometry_sha256': hashlib.sha256(canonical(geo_files)).hexdigest(),
                    'visual_object_geometry_sha256': hashlib.sha256(canonical({name: record for name, record in geo_files.items()
                        if name.startswith('data/object_library/')})).hexdigest(),
                    'optional_physical_geometry_sha256': hashlib.sha256(canonical(optional_inputs)).hexdigest()},
                'input_files': common_inputs, 'input_files_sha256': hashlib.sha256(canonical(common_inputs)).hexdigest(),
                'optional_input_files': optional_inputs, 'input_profiles': profile_proofs,
                'generator_sha256': pin(generator)['sha256'], 'runtime_graph_readback': True,
                'physical_npc_pathing_validated': False}
    raw = canonical(manifest); (args.output / MANIFEST).write_bytes(raw)
    with zipfile.ZipFile(args.output / ARCHIVE, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in (GRAPH, DATE): archive.write(runtime / name, name)
        archive.writestr(MANIFEST, raw)
    value = {'format': 2, 'status': 'passed', 'repository_commit': args.repository_commit,
             'donor': DONOR, 'stock_mapserver_sha256': STOCK_MAPSERVER, 'build_input': build_input,
             'generator': pin(generator), 'native': witness, 'manifest': pin(args.output / MANIFEST),
             'generation_sources': {name: pin(ROOT / name) for name in GENERATION_SOURCES},
             'archive': pin(args.output / ARCHIVE), 'elapsed_seconds': round(time.monotonic() - started, 3),
             'commands': commands, 'owned_roles': 4, 'native_worker_spawning_allowed': False,
             'profile_verification_processes': 2, 'profile_proofs': profile_proofs, 'cold_mirror': cold_mirror,
             'cleanup_complete': all(process.poll() is not None for process in processes.values()),
             'evidence': {path.relative_to(args.output).as_posix(): pin(path) for path in evidence.iterdir() if path.is_file()}}
    (args.output / REPORT).write_bytes(canonical(value))
    validate_package(args.output, args.repository_commit)
    print(json.dumps({'status': value['status'], 'native': witness, 'archive': value['archive']}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('donor-apk', 'donor-receipt', 'asset-archive', 'generator', 'build-input', 'work', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--timeout-seconds', type=int, default=5400)
    args = parser.parse_args()
    generate(args)


if __name__ == '__main__': main()
