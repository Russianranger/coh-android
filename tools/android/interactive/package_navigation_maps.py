#!/usr/bin/env python3
"""Build the importable navigation map pack from passed armport-zone-beacons map jobs.

Owner, 2026-11-09: a navigation map (native beacon graph) for every zone, reaching
the phone as a separate pack to import, like the asset pack. The pack uses the
asset pack's volume format (package_external_assets.py; AssetPackArchive on the
phone): every volume carries the same descriptor, which the APK also carries, so an
imported ZIP cannot choose its own trusted hashes. Each map's archive, manifest,
lock and generation report must come from a successful map job of one
armport-zone-beacons run and pass the guest's own validator (zone_beacon_package
via generate_zone_beacons.manifest_validator) before it enters the pack.

Layout of --runs: one folder per run id holding run.json and jobs.json (GitHub's
run and jobs API answers) and the run's coh-zone-beacons-<map> artifact folders.
A later run listed in --order replaces an earlier run's graph for the same map.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import stat
import zipfile
import generate_zone_beacons as zone_graphs
import package_external_assets as assets

FORMAT = 1
PACK_ID = 'coh-navigation-maps'
MANIFEST = 'asset-pack-manifest.json'  # the volume member name AssetPackArchive expects
DESCRIPTOR = 'navigation-maps-manifest.json'  # the APK's copy (assets/runtime) and the release asset
WORKFLOW = '.github/workflows/armport-zone-beacons.yml'
MAX_VOLUME_BYTES = assets.MAX_VOLUME_BYTES
# Room for the descriptor and ZIP headers below GitHub's and AssetPackArchive's 2 GiB bound.
VOLUME_BUDGET = MAX_VOLUME_BYTES - 64 * 1024 * 1024
MAX_FILES = 256
require, encoded, file_pin = assets.require, assets.encoded, assets.file_pin


def volume_filename(version, volume):
    suffix = '' if volume == 'maps' else '-Part-' + volume.rsplit('-', 1)[1]
    return 'COH-Navigation-Maps-' + version + suffix + '.zip'


def validate_descriptor(value):
    require(type(value) is dict and value.get('format') == FORMAT and type(value.get('format')) is int
            and value.get('id') == PACK_ID and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', str(value.get('version', ''))),
            'Unsupported navigation map descriptor')
    files, volumes = value.get('files'), value.get('volumes')
    require(type(files) is dict and 0 < len(files) <= MAX_FILES and type(volumes) is dict and 0 < len(volumes) <= 16,
            'Bounded navigation map inventory required')
    graph = zone_graphs.manifest_validator()
    allowed = {'runtime/' + graph.names(m)[key] for m in graph.WORLDS for key in ('archive', 'manifest')}
    for name, expected in files.items():
        require(name in allowed and type(expected) is dict and set(expected) == {'bytes', 'sha256'}
                and type(expected['bytes']) is int and 0 < expected['bytes'] < MAX_VOLUME_BYTES
                and re.fullmatch('[0-9a-f]{64}', str(expected['sha256'])), 'Invalid navigation map pin: ' + str(name))
    for map_id in graph.WORLDS:
        present = {'runtime/' + graph.names(map_id)[key] in files for key in ('archive', 'manifest')}
        require(len(present) == 1, 'A map needs its archive and manifest together: ' + str(map_id))
    membership = []
    for volume, names in volumes.items():
        require(re.fullmatch(r'maps(-[1-9][0-9]?)?', volume) and type(names) is list and names == sorted(set(names))
                and names and set(names) <= set(files), 'Invalid navigation map volume')
        require(sum(files[name]['bytes'] for name in names) <= VOLUME_BUDGET, 'Navigation map volume exceeds its bound')
        membership += names
    require(len(membership) == len(set(membership)) and set(membership) == set(files),
            'Volumes must partition every navigation map file exactly once')
    require(len(encoded(value)) <= 262144, 'Navigation map descriptor exceeds the Android bound')
    return value


def checked_map(folder, map_id, run):
    """One map's package from a passed map job, checked as the guest and the APK check it."""
    graph = zone_graphs.manifest_validator(); names = graph.names(map_id)
    report_name = 'zone-beacons-%d-generation-report.json' % map_id
    present = sorted(p.name for p in folder.iterdir())
    require(present == sorted([names['archive'], names['manifest'], names['lock'], report_name]),
            'Incomplete or extra zone graph artifact for map %d' % map_id)
    for path in folder.iterdir():
        require(path.is_file() and not path.is_symlink(), 'Zone graph artifact members must be regular files')
    value, lock = graph.read_manifest(folder / names['manifest'], folder / names['lock'], map_id)
    report = json.loads((folder / report_name).read_bytes())
    archive, manifest = file_pin(folder / names['archive']), file_pin(folder / names['manifest'])
    require(report.get('status') == 'passed' and report.get('map_id') == map_id and report.get('map') == names['map']
            and report.get('repository_commit') == run['head_sha'] and report.get('cleanup_complete') is True
            and report.get('owned_roles') == 0 and report.get('native_worker_spawning_allowed') is False
            and report.get('archive') == lock['archive'] == archive and report.get('manifest') == lock['manifest'] == manifest
            and report.get('native') == value['native'], 'Zone graph %d does not match its own generation job' % map_id)
    with zipfile.ZipFile(folder / names['archive']) as packed:
        infos = packed.infolist()
        require(sorted(i.filename for i in infos) == sorted((names['graph'], names['date'], names['manifest']))
                and all(not i.is_dir() and not i.flag_bits & 1 and stat.S_IFMT(i.external_attr >> 16) in (0, stat.S_IFREG)
                        for i in infos)
                and packed.read(names['manifest']) == (folder / names['manifest']).read_bytes(),
                'Zone graph %d archive closure differs' % map_id)
        for name, expected in value['files'].items():
            digest = hashlib.sha256(); size = 0
            with packed.open(name) as stream:
                while block := stream.read(1024 * 1024):
                    size += len(block); digest.update(block)
            require({'bytes': size, 'sha256': digest.hexdigest()} == expected, 'Zone graph %d payload differs' % map_id)
    native = value['native']
    return {'map_id': map_id, 'map': names['map'], 'archive': archive, 'manifest': manifest,
            'graph_bytes': value['files'][names['graph']]['bytes'], 'full_world_crc': native['full_world_crc'],
            'combat_beacons': native['combat_beacons'], 'connected_beacons': native['connected_beacons'],
            'owned_workers': report.get('owned_workers', 1), 'generation_seconds': report.get('generation_seconds'),
            'paths': {'archive': folder / names['archive'], 'manifest': folder / names['manifest']}}


def collect(runs_root, order):
    """Every map that passed in the listed runs; a later run replaces an earlier one's map."""
    graph = zone_graphs.manifest_validator(); chosen = {}
    for run_id in order:
        folder = Path(runs_root) / str(run_id)
        run = json.loads((folder / 'run.json').read_bytes()); jobs = json.loads((folder / 'jobs.json').read_bytes())
        require(run.get('id') == run_id and run.get('path') == WORKFLOW and run.get('status') == 'completed'
                and re.fullmatch('[0-9a-f]{40}', str(run.get('head_sha', ''))), 'Run %s is not a completed zone graph run' % run_id)
        passed = {}
        for job in jobs.get('jobs', []):
            match = re.fullmatch(r'beacons \(([0-9]+)\)', str(job.get('name', '')))
            if match and job.get('conclusion') == 'success':
                passed[int(match.group(1))] = job.get('id')
        for map_id in sorted(passed):
            require(map_id in graph.WORLDS, 'Run %s generated an unknown map %d' % (run_id, map_id))
            artifact = folder / ('coh-zone-beacons-%d' % map_id)
            require(artifact.is_dir(), 'Passed map %d of run %s has no artifact' % (map_id, run_id))
            chosen[map_id] = dict(checked_map(artifact, map_id, run), run_id=run_id, job_id=passed[map_id],
                                  head_sha=run['head_sha'])
    require(chosen, 'No passed map to pack')
    return chosen


def plan_volumes(files):
    """The fewest volumes within the budget (largest first), named maps or maps-1, maps-2..."""
    bins = []
    for name in sorted(files, key=lambda n: (-files[n]['bytes'], n)):
        size = files[name]['bytes']; require(size <= VOLUME_BUDGET, 'A single navigation map file exceeds a volume')
        for members in bins:
            if sum(files[m]['bytes'] for m in members) + size <= VOLUME_BUDGET:
                members.append(name); break
        else:
            bins.append([name])
    if len(bins) == 1:
        return {'maps': sorted(bins[0])}
    return {'maps-%d' % (i + 1): sorted(members) for i, members in enumerate(bins)}


def write_volume(path, descriptor, volume, inputs):
    validate_descriptor(descriptor); raw = encoded(descriptor)
    require(not path.exists() and not path.is_symlink(), 'Fresh navigation map output required')
    try:
        with zipfile.ZipFile(path, 'x', allowZip64=False) as archive:
            archive.writestr(assets.zip_info(MANIFEST, len(raw)), raw)
            for name in descriptor['volumes'][volume]:
                expected = descriptor['files'][name]
                require(file_pin(inputs[name]) == expected, 'Navigation map changed after the descriptor: ' + name)
                with Path(inputs[name]).open('rb') as source, \
                        archive.open(assets.zip_info('payloads/' + name, expected['bytes']), 'w') as target:
                    shutil.copyfileobj(source, target, 1024 * 1024)
        require(path.stat().st_size < MAX_VOLUME_BYTES, 'Navigation map volume exceeded the transport bound')
        verify_volume(path, descriptor, volume)
    except Exception:
        path.unlink(missing_ok=True); raise
    return file_pin(path)


def verify_volume(path, descriptor, volume):
    """The same exact-inventory checks the asset pack volumes get (package_external_assets.verify_volume)."""
    raw = encoded(validate_descriptor(descriptor))
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist(); names = [entry.filename for entry in infos]
        require(names == [MANIFEST] + ['payloads/' + member for member in descriptor['volumes'][volume]]
                and archive.read(MANIFEST) == raw, 'Navigation map volume inventory differs')
        for entry in infos:
            require(entry.create_system == 3 and stat.S_IFMT(entry.external_attr >> 16) == stat.S_IFREG
                    and not entry.is_dir() and not entry.flag_bits & 1 and entry.compress_type == zipfile.ZIP_STORED,
                    'Only regular stored navigation map members allowed')
            expected = (file_pin_bytes(raw) if entry.filename == MANIFEST else descriptor['files'][entry.filename[9:]])
            digest = hashlib.sha256(); received = 0
            with archive.open(entry) as stream:
                while block := stream.read(1024 * 1024):
                    received += len(block); require(received <= expected['bytes'], 'Navigation map member too large')
                    digest.update(block)
            require({'bytes': received, 'sha256': digest.hexdigest()} == expected, 'Navigation map member differs')


def file_pin_bytes(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def build(runs_root, order, output, version):
    require(re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version), 'Navigation map pack version required')
    maps = collect(runs_root, order); output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    inputs, files = {}, {}
    graph = zone_graphs.manifest_validator()
    for map_id, row in sorted(maps.items()):
        for key in ('archive', 'manifest'):
            name = 'runtime/' + graph.names(map_id)[key]
            inputs[name] = row['paths'][key]; files[name] = row[key]
    descriptor = validate_descriptor({'format': FORMAT, 'id': PACK_ID, 'version': version,
                                      'files': dict(sorted(files.items())), 'volumes': plan_volumes(files)})
    (output / DESCRIPTOR).write_bytes(encoded(descriptor))
    receipts = {}
    for volume in sorted(descriptor['volumes']):
        path = output / volume_filename(version, volume)
        receipts[path.name] = dict(write_volume(path, descriptor, volume, inputs), volume=volume)
        path.with_name(path.name + '.sha256').write_text(receipts[path.name]['sha256'] + '  ' + path.name + '\n')
    missing = sorted(set(graph.WORLDS) - set(maps))
    report = {'format': 1, 'id': PACK_ID, 'version': version, 'descriptor': file_pin(output / DESCRIPTOR),
              'volumes': receipts, 'maps': {str(m): {k: v for k, v in row.items() if k != 'paths'} for m, row in sorted(maps.items())},
              'map_count': len(maps), 'maps_without_graph': missing,
              'zones_without_shared_tree_graph_slot': ['Atlas Park (1) and King\'s Row (5) keep their own graphs'],
              'all_members_streamed_and_verified': True, 'device_validated': False}
    (output / 'navigation-maps-build-report.json').write_bytes(encoded(report))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', required=True, type=Path, help='Folder of run-id folders (run.json, jobs.json, artifacts)')
    parser.add_argument('--order', required=True, help='Run ids, comma separated; a later run replaces an earlier map')
    parser.add_argument('--version', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    order = [int(value) for value in args.order.split(',')]
    require(len(order) == len(set(order)) and all(value > 0 for value in order), 'Distinct run ids required')
    result = build(args.runs, order, args.output, args.version)
    print(json.dumps({'status': 'built', 'version': result['version'], 'maps': result['map_count'],
                      'maps_without_graph': result['maps_without_graph'],
                      'volumes': {name: {k: v for k, v in row.items()} for name, row in result['volumes'].items()},
                      'descriptor': result['descriptor']}, sort_keys=True))
