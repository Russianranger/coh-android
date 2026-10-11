#!/usr/bin/env python3
"""Bounded host execution of actual packaged guest asset installers.

This checks exact immutable Assets 1.0.0 against a candidate runtime, including
all animations and both qualified collision inventories. It starts no native
process, database, Android activity or physical device session.
"""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[3]
SOURCE_FILES = ('tools/android/interactive/qualify_runtime_asset_preflight.py',
                'tools/android/interactive/test_runtime_asset_preflight.py')
SCOPE = 'actual_packaged_guest_external_asset_installers'
RELEASE_URL = 'https://github.com/Russianranger/coh-android/releases/download/coh-assets-v1.0.0/'
VOLUMES = {
    'Reference': {'bytes': 615545248, 'sha256': 'e15cf9519dbff750ed900a69a826bd424e81d6c004eaff2fe77197a1596b840e'},
    'Base': {'bytes': 1630092780, 'sha256': '6d6e3304e48b89f8fdb218754a57380b3108140ef31bddb30f699ebcf28c2e3d'},
    'Zones': {'bytes': 1693058889, 'sha256': 'f3a3f78caceeccbe00dc97723244e12910161e2c952347e70e83b56a29558087'},
}
ASSET_PINS = {'atlas/atlas-assets.zip': {'bytes': 615541018, 'sha256': '28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07'}, 'atlas/atlas-text.zip': {'bytes': 312807038,
                          'sha256': '53f1892c8704b8a14612b3ea29e6d746d1c132ce6663862b1c25c5df65f63d3c'},
 'runtime/atlas-beacon-manifest.json': {'bytes': 934650,
                                        'sha256': 'ee11bb703eed85229948b30b41277c515faf80da31ccd0436171862765ba41f4'},
 'runtime/atlas-beacons.zip': {'bytes': 16150904,
                               'sha256': '0c7f602d31a438c6e67409bbb89da5d45ee3aacf13c96a50de9401d7973b2949'},
 'runtime/atlas-world-supplement-manifest.json': {'bytes': 4258210,
                                                  'sha256': '204a7f0da20cdbbb4ea8b8e2d9e9b5ebccfaa10d5213fff03bbb85cc7f9e3c86'},
 'runtime/atlas-world-supplement.zip': {'bytes': 207803201,
                                        'sha256': 'c7ed82aaaf987410fa471e19ee2b19115ef660892a06f79e2e2401d5672b095f'},
 'runtime/character-avatar-defaults-manifest.json': {'bytes': 28554,
                                                     'sha256': '2a96ff8fb24b686502d62e1e1ed25453681d4c15389c59b1f35ce3fbf1a5feb7'},
 'runtime/character-avatar-defaults.zip': {'bytes': 1842488,
                                           'sha256': '03f980c983702c2c9d21b0f674903e151129d0554b25d800b8724036f2cb4a29'},
 'runtime/client-visual-assets.zip': {'bytes': 859075775,
                                      'sha256': '5f91b7d4ebe91e6a547923d702e2fcd56d7fc1d36fb7bffbb66463562d977d60'},
 'runtime/kings-row-beacon-manifest.json': {'bytes': 1426843,
                                            'sha256': '0b2ade9719e30fe4267782a8affa556c6245a02ad9f421a57195c115afde4694'},
 'runtime/kings-row-beacons.zip': {'bytes': 23708626,
                                   'sha256': '6a7bcfba0d6f64a13d31fc6c31bd8cd366344c6ffa92b546a26ef3f132c2d64c'},
 'runtime/server-animation-manifest.json': {'bytes': 1005794,
                                            'sha256': '8f752dceeffa632287602176f26722c3129fcdc9941709793d8b26d22151859f'},
 'runtime/server-animations.pigg': {'bytes': 97084456,
                                    'sha256': '465d69a266f2b07afd800b8a7bd3f5e63fa16a24955391f826264d7f8d3a968b'},
 'runtime/server-cache-manifest.json': {'bytes': 39041,
                                        'sha256': '4e1a4c9c148509ef34245768f64ca2be4bb83659db845c6ef94ed594666b3fff'},
 'runtime/server-caches.zip': {'bytes': 29825263,
                               'sha256': '7439d4557ae9fd74bb4bb4a324b6a676829387124be0817eb1da3c8adff10b17'},
 'runtime/zones-world-supplement-manifest.json': {'bytes': 4237139,
                                                  'sha256': 'f466ad6c8ab6e84dabd16d404c3a05bcb9fbca3cfad5746852d53b04132d8f74'},
 'runtime/zones-world-supplement.zip': {'bytes': 1663681523,
                                        'sha256': 'f12a0994cec20ab6d13c158495fe01402e89113ae756e412357e9c4a04833ad3'}}


def require(condition, message):
    if not condition: raise ValueError(message)


def pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Regular preflight input required: '+path.name)
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024*1024), b''): digest.update(block)
    return {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def checked(path, expected):
    require(pin(path) == expected, 'Preflight input pin differs: '+Path(path).name)


def safe(name):
    return (isinstance(name, str) and name and not name.startswith('/') and '\\' not in name
        and ':' not in name and all(part not in ('', '.', '..') for part in name.split('/')))


def ensure_assets(cache_dir):
    """Reuse exact public volumes; download only missing original bytes."""
    cache = Path(cache_dir); cache.mkdir(parents=True, exist_ok=True)
    assets = cache/'payloads'; assets.mkdir(exist_ok=True)
    missing = [name for name, expected in ASSET_PINS.items()
               if not (assets/Path(name).name).exists()]
    if missing:
        for volume, expected in VOLUMES.items():
            names = [name for name in missing if ('Reference' if name == 'atlas/atlas-assets.zip' else 'Zones' if name.startswith('runtime/kings-row-')
                or name.startswith('runtime/zones-') else 'Base') == volume]
            if not names: continue
            filename = 'COH-Assets-1.0.0-'+volume+'.zip'; source = cache/filename
            if not source.exists():
                pending = source.with_suffix('.partial')
                try:
                    with urllib.request.urlopen(RELEASE_URL+filename, timeout=120) as response, pending.open('wb') as out:
                        count = 0
                        while block := response.read(1024*1024):
                            count += len(block); require(count <= expected['bytes'], 'Asset volume exceeds exact bound')
                            out.write(block)
                    checked(pending, expected); os.replace(pending, source)
                finally: pending.unlink(missing_ok=True)
            checked(source, expected)
            with zipfile.ZipFile(source) as archive:
                for name in names:
                    entry = archive.getinfo('payloads/'+name)
                    require(not entry.is_dir() and not entry.flag_bits & 1
                        and stat.S_IFMT(entry.external_attr >> 16) in (0, stat.S_IFREG)
                        and entry.file_size == ASSET_PINS[name]['bytes'], 'Unsafe external asset member')
                    target = assets/Path(name).name
                    with archive.open(entry) as stream, target.open('xb') as out:
                        shutil.copyfileobj(stream, out, 1024*1024)
                    checked(target, ASSET_PINS[name]); target.chmod(0o444)
    validate_assets(assets)
    return assets


def validate_assets(assets):
    for name, expected in ASSET_PINS.items(): checked(Path(assets)/Path(name).name, expected)
    return {Path(name).name: expected for name, expected in ASSET_PINS.items()}


def materialize(runtime, selected, archives, tar_payloads):
    """Copy exact selected original leaves; never synthesize collision inputs."""
    runtime = Path(runtime)
    require(len(selected) <= 25000 and all(safe(name) for name in selected), 'Unsafe preflight source inventory')
    indexes = []
    for archive in archives:
        entries = archive.infolist()
        require(len({e.filename.casefold() for e in entries}) == len(entries), 'Case-conflicting source archive')
        # Original reference ZIP uses assets/; the existing importer places that
        # immutable namespace under data/. Other prepared ZIPs already use data/.
        logical = lambda name: ('data/'+name[7:] if name.startswith('assets/') else name).casefold()
        require(len({logical(e.filename) for e in entries}) == len(entries), 'Ambiguous logical source namespace')
        indexes.append((archive, {logical(entry.filename): entry for entry in entries}))
    copied = 0
    for name, expected in sorted(selected.items()):
        options = []
        for archive, index in indexes:
            entry = index.get(name.casefold())
            if entry is not None:
                require(not entry.is_dir() and not entry.flag_bits & 1 and entry.file_size <= 128*1024**2,
                        'Invalid collision source member')
                options.append(lambda a=archive, e=entry: a.read(e))
        if name in tar_payloads: options.append(lambda n=name: tar_payloads[n])
        accepted = None
        for read in options:
            raw = read()
            if {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected:
                accepted = raw; break
        require(accepted is not None, 'Exact preflight collision/identifier source missing: '+name)
        target = runtime/name; target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        require(not target.exists() and not target.is_symlink(), 'Preflight source destination already exists')
        target.write_bytes(accepted); target.chmod(0o444); os.utime(target, (1767225600, 1767225600))
        copied += len(accepted)
    return {'files': len(selected), 'bytes': copied,
            'inventory_sha256': hashlib.sha256(json.dumps(selected, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}


def stable(value):
    """Drop measurements; retain every validation result for reproducible receipts."""
    if isinstance(value, dict):
        return {k: stable(v) for k,v in value.items() if not k.endswith('elapsed_seconds')}
    if isinstance(value, list): return [stable(v) for v in value]
    return value


class Context:
    def check(self): pass


def worker(runtime_assets, external):
    # Import from extracted candidate APK bytes, never a preimported repository
    # guest module. The parent invokes this in a fresh process for that reason.
    runtime_assets, external = Path(runtime_assets).resolve(), Path(external).resolve()
    sys.path.insert(0, str(runtime_assets))
    import local_character_server as server
    import local_login_server as login
    import server_animation_package as animation
    import server_cache_package as caches
    import atlas_beacon_package as atlas
    import kings_row_beacon_package as kings
    import zone_asset_package as zones
    imports = (server, login, animation, caches, atlas, kings, zones)
    require(all(Path(m.__file__).resolve().parent == runtime_assets for m in imports),
            'Preflight must import the actual packaged guest modules')
    asset_pins = validate_assets(external)
    guest_sources = {p.name: pin(p) for p in sorted(runtime_assets.glob('*.py'))}
    context = Context()
    with tempfile.TemporaryDirectory(prefix='coh-actual-asset-installers-') as temporary, contextlib.ExitStack() as stack:
        root = Path(temporary); assets = root/'assets'; assets.mkdir()
        for name in asset_pins:
            os.link(external/name, assets/name)
        for name in ('client-manifest.json', kings.LOCK): shutil.copyfile(runtime_assets/name, assets/name)
        archives = [stack.enter_context(zipfile.ZipFile(assets/name)) for name in
            ('atlas-assets.zip', 'atlas-text.zip', 'atlas-world-supplement.zip', 'character-avatar-defaults.zip', 'client-visual-assets.zip')]
        archives.append(stack.enter_context(zipfile.ZipFile(runtime_assets/'client-prerequisites.zip')))
        with tarfile.open(runtime_assets/'dbserver-schema.tar.gz', 'r:gz') as schema:
            tar_payloads = {m.name: schema.extractfile(m).read() for m in schema.getmembers() if m.isfile()}
        cache_manifest = caches.verify_archive(assets/caches.ARCHIVE)
        atlas_manifest = atlas.read_manifest(assets/atlas.MANIFEST)
        kings_manifest, lock = kings.read_manifest(assets/kings.MANIFEST, assets/kings.LOCK)
        zone_document = zones.package(assets)
        candidate = json.loads((runtime_assets/'native-responsiveness.json').read_bytes())
        outputs = {}
        for label, owner in (('atlas', server.LocalCharacterServer), ('kings', server.LocalCharacterReopenServer)):
            runtime = root/label
            login.extract_regular(runtime_assets/'game-package.tar.gz', runtime)
            package = owner.verify_map_payload(runtime, candidate)
            selected = dict(cache_manifest['identity']['identifier_files'])
            if label == 'atlas': selected.update(atlas_manifest['input_files']); selected.update(atlas_manifest['required_geometry_files'])
            else: selected.update({n:p for n,p in kings_manifest['input_files'].items()
                                   if n not in zone_document['kings_row_collision_files']})
            materialized = materialize(runtime, selected, archives, tar_payloads)
            # Empty logical roots still participate in exact inventory validation.
            for relative in ('data/object_library', 'data/tricks', 'data/maps/city_zones/'+('city_01_01' if label == 'atlas' else 'city_01_02')):
                (runtime/relative).mkdir(parents=True, exist_ok=True)
            overlay = zones.install(runtime, assets, context, collision_only=True) if label == 'kings' else None
            donor_identity = caches.build_expected_identity(runtime/'data', runtime/'MapServer.exe', mapserver_package=package)
            cold_cache = caches.install(assets/caches.ARCHIVE, runtime/'data', donor_identity, context=context)
            require(cold_cache['status'] == 'installed' and cold_cache['installed_files'] > 0, 'Prepared cache cold installer did not pass')
            cold_animation = animation.install(assets/animation.PIGG, assets/animation.MANIFEST, runtime,
                                                context=context, mapserver_package=package)
            require(cold_animation['installed'] is True and cold_animation['reused'] is False
                    and cold_animation['pigg']['animation_count'] == 5878, 'Full animation cold installer did not pass')
            graph = atlas if label == 'atlas' else kings
            kwargs = {'mapserver_package': package} if label == 'atlas' else {'lock_path': assets/kings.LOCK}
            cold_graph = graph.install(assets/graph.ARCHIVE, assets/graph.MANIFEST, runtime,
                context=context, imported_inputs_readonly=True, **kwargs)
            require(cold_graph['status'] == 'installed_verified_graph' and cold_graph['installed_files'] == 2,
                    'Real graph cold installer did not pass')
            warm_cache = caches.install(assets/caches.ARCHIVE, runtime/'data', donor_identity, context=context)
            warm_animation = animation.install(assets/animation.PIGG, assets/animation.MANIFEST, runtime,
                                                context=context, mapserver_package=package)
            warm_graph = graph.install(assets/graph.ARCHIVE, assets/graph.MANIFEST, runtime,
                context=context, imported_inputs_readonly=True, **kwargs)
            require(warm_cache['status'] == 'preserved_existing_native_caches'
                    and warm_animation['installed'] is True and warm_animation['reused'] is True
                    and warm_graph['status'] == 'reused_verified_graph', 'Actual installer warm reuse did not pass')
            outputs[label] = stable({'materialized_sources': materialized, 'collision_overlay': overlay,
                'mapserver': pin(runtime/'MapServer.exe'), 'prepared_cache_cold': cold_cache,
                'prepared_cache_reuse': warm_cache, 'animation_cold': cold_animation,
                'animation_reuse': warm_animation, 'graph_cold': cold_graph, 'graph_reuse': warm_graph})
        return {'format': 1, 'status': 'passed', 'scope': SCOPE, 'asset_version': '1.0.0',
            'asset_inputs': asset_pins, 'packaged_guest_sources': guest_sources,
            'game_archive': pin(runtime_assets/'game-package.tar.gz'), 'animation_count': 5878,
            'fresh_create_payload_verified': True, 'saved_reopen_payload_verified': True,
            'atlas_cold_and_reuse_verified': True, 'kings_cold_and_reuse_verified': True,
            'prepared_caches_verified': True, 'native_runtime_booted': False,
            'physical_execution_validated': False, 'full_private_worktree_mirror_executed': False,
            'animation_archive_original_bytes_verified': True, 'installers': outputs}


def preflight(runtime_assets, asset_directory):
    with tempfile.TemporaryDirectory(prefix='coh-asset-preflight-receipt-') as temporary:
        output = Path(temporary)/'proof.json'
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--worker',
            '--runtime-assets', str(Path(runtime_assets).resolve()), '--asset-directory', str(Path(asset_directory).resolve()),
            '--output', str(output)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=900)
        require(result.returncode == 0, 'Actual packaged asset installer preflight failed:\n'+result.stderr[-12000:])
        value = json.loads(output.read_bytes())
        require(value.get('status') == 'passed' and value.get('scope') == SCOPE, 'Asset preflight receipt differs')
        return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-assets', required=True, type=Path)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--asset-directory', type=Path); choice.add_argument('--asset-cache', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    assets = args.asset_directory or ensure_assets(args.asset_cache)
    result = worker(args.runtime_assets, assets) if args.worker else preflight(args.runtime_assets, assets)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, separators=(',', ':'))+'\n')


if __name__ == '__main__': main()
