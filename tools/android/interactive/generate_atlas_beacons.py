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
    require(value.get('status') == 'passed' and re.fullmatch('[0-9a-f]{40}', value.get('repository_commit', ''))
            and re.fullmatch('[0-9a-f]{40}', repository_commit), 'Generation provenance/commit differs')
    require(value.get('generation_sources') == {name: pin(ROOT / name) for name in GENERATION_SOURCES},
            'Generation implementation changed; a fresh native generation is required')
    require(value['build_input'] == producer.expected(), 'Host producer source receipt differs')
    require(value['donor'] == DONOR and value['stock_mapserver_sha256'] == STOCK_MAPSERVER,
            'Stock native compatibility differs')
    for name, expected in value['evidence'].items():
        require(pin(directory / safe(name)) == expected, 'Generation evidence changed')
    manifest = json.loads((directory / MANIFEST).read_bytes())
    require(pin(directory / MANIFEST) == value['manifest'] and pin(directory / ARCHIVE) == value['archive'],
            'Generated package pin differs')
    require(manifest['map'] == producer.MAP and set(manifest['files']) == {GRAPH, DATE}
            and manifest['stock_mapserver_sha256'] == STOCK_MAPSERVER, 'Generated graph scope differs')
    require(manifest['native'] == native_evidence((directory / 'evidence/server.log').read_bytes(),
                                                 _date_from_archive(directory / ARCHIVE)), 'Native transcript differs')
    with zipfile.ZipFile(directory / ARCHIVE) as archive:
        require(len(archive.namelist()) == 3 and set(archive.namelist()) == {GRAPH, DATE, MANIFEST}, 'Beacon package closure differs')
        require(archive.read(MANIFEST) == (directory / MANIFEST).read_bytes(), 'Embedded manifest differs')
        for name, expected in manifest['files'].items():
            raw = archive.read(name)
            require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected, 'Graph pin differs')
    return manifest


def _date_from_archive(path):
    with zipfile.ZipFile(path) as archive: return archive.read(DATE)


def generate(args):
    require(os.name == 'nt', 'Native generation requires an isolated Windows runner')
    require(30 <= args.timeout_seconds <= 5400 and re.fullmatch('[0-9a-f]{40}', args.repository_commit), 'Invalid timeout/commit')
    require(not args.work.exists() and not args.output.exists(), 'Fresh generator work/output required')
    args.work.mkdir(parents=True); args.output.mkdir(parents=True)
    evidence = args.output / 'evidence'; evidence.mkdir()
    build_input = json.loads(args.build_input.read_bytes())
    require(build_input == producer.expected(), 'Native generator source receipt differs')
    assets = args.work / 'donor'; extract_assets(args.donor_apk, args.donor_receipt, assets)
    data = import_data(assets, args.asset_archive, args.work, evidence); runtime = data.parent
    native = extract_tar(assets / 'runtime/game-package.tar.gz', runtime, 'game-package.json')
    require(pin(runtime / 'MapServer.exe')['sha256'] == STOCK_MAPSERVER, 'Retained native MapServer differs')
    extract_tar(assets / 'runtime/dbserver-schema.tar.gz', runtime, 'schema-manifest.json')
    world = overlay_zip(assets / 'runtime/atlas-world-supplement.zip', assets / 'runtime/atlas-world-supplement-manifest.json', runtime)
    visual = overlay_zip(assets / 'runtime/client-visual-assets.zip', assets / 'runtime/client-visual-manifest.json', runtime)
    # Retain immutable byte inputs and common loader epoch. The host source only
    # writes caches and two server-only graph files under this isolated tree.
    for path in data.rglob('*'):
        if path.is_file(): os.utime(path, (1767225600, 1767225600))
    inputs = geometry_inputs(runtime)
    (runtime / 'tools').mkdir(exist_ok=True)
    generator = runtime / 'AtlasBeaconGenerator.exe'; shutil.copyfile(args.generator, generator)
    env = dict(os.environ, COH_WINE_MAP_PROGRESS='')
    for name in ('COH_CLIENT_DEPENDENCY_PRELOAD', 'COH_MANUAL_ATLAS_DB', 'COH_WINE_GAME_LISTENERS'): env.pop(name, None)
    common = ['-nogui', '-nopigs', '-noencrypt', '-beaconallownovodex', '-beacondatatoolsrootpath', str(runtime)]
    roles = [('master', ['-beaconmasterserver', '-beaconrequestcachedir', str(args.work / 'requests')]),
             ('server', ['-beaconserver', '127.0.0.1', '-beacononepassonly', '-beaconforcerebuild']),
             ('sentry', ['-beaconclient', '127.0.0.1', '-beaconworkduringuseractivity']),
             ('worker', ['-beaconclient', '127.0.0.1', '-beaconworkduringuseractivity'])]
    processes, logs, commands = {}, {}, {}
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
                    require(processes[role].poll() is None and time.monotonic() < deadline, 'Native role startup failed: ' + role)
                    time.sleep(0.5)
        while processes['server'].poll() is None:
            require(time.monotonic() - started < args.timeout_seconds, 'Atlas generation exceeded owned deadline')
            for role, path in ((role, evidence / (role + '.log')) for role in processes):
                require(path.stat().st_size <= MAX_LOG, 'Native role log exceeded bound')
                require(role == 'server' or processes[role].poll() is None, 'Owned native role exited: ' + role)
            time.sleep(1)
        require(processes['server'].returncode == 0, 'Native Atlas graph producer failed')
    finally:
        for process in processes.values():
            if process.poll() is None: process.terminate()
        for process in processes.values():
            try: process.wait(timeout=15)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=15)
        for stream in logs.values(): stream.close()
    require((runtime / GRAPH).is_file() and (runtime / DATE).is_file(), 'Native graph files missing')
    require(geometry_inputs(runtime) == inputs, 'Native generation modified an immutable collision input')
    witness = native_evidence((evidence / 'server.log').read_bytes(), (runtime / DATE).read_bytes())
    geo_files = {name: value for name, value in visual['files'].items() if name.endswith('.geo')}
    manifest = {'format': 1, 'role': 'authentic_native_atlas_beacon_graph', 'map': producer.MAP,
                'stock_mapserver_sha256': STOCK_MAPSERVER, 'source_commit': build_input['source_commit'],
                'data_commit': visual['data_commit'], 'files': {name: pin(runtime / name) for name in (GRAPH, DATE)},
                'native': witness, 'input_identity': {'asset_archive': pin(args.asset_archive),
                    'world_manifest': pin(assets / 'runtime/atlas-world-supplement-manifest.json'),
                    'visual_geometry_sha256': hashlib.sha256(canonical(geo_files)).hexdigest()},
                'input_files': inputs, 'input_files_sha256': hashlib.sha256(canonical(inputs)).hexdigest(),
                'generator_sha256': pin(generator)['sha256'], 'runtime_graph_readback': True,
                'physical_npc_pathing_validated': False}
    raw = canonical(manifest); (args.output / MANIFEST).write_bytes(raw)
    with zipfile.ZipFile(args.output / ARCHIVE, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in (GRAPH, DATE): archive.write(runtime / name, name)
        archive.writestr(MANIFEST, raw)
    value = {'format': 1, 'status': 'passed', 'repository_commit': args.repository_commit,
             'donor': DONOR, 'stock_mapserver_sha256': STOCK_MAPSERVER, 'build_input': build_input,
             'generator': pin(generator), 'native': witness, 'manifest': pin(args.output / MANIFEST),
             'generation_sources': {name: pin(ROOT / name) for name in GENERATION_SOURCES},
             'archive': pin(args.output / ARCHIVE), 'elapsed_seconds': round(time.monotonic() - started, 3),
             'commands': commands, 'owned_roles': 4, 'native_worker_spawning_allowed': False,
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
    for name in ('donor_apk', 'donor_receipt', 'asset_archive', 'generator', 'build_input', 'work', 'output'):
        setattr(args, name, getattr(args, name).resolve())
    generate(args)


if __name__ == '__main__': main()
