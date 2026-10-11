#!/usr/bin/env python3
"""Execute complete packaged guest preparation on every original imported leaf.

The runtime worker imports only APK guest bytes. It calls the production client
worktree and complete Atlas/Kings Row server preparation methods, including
owned cache return and subsequent checkout. Process launch, live SQL, protocol
readiness and Android pixels remain separate, explicitly unexecuted gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import urllib.request
import zipfile

import qualify_runtime_asset_preflight as leaf

SOURCE_FILES = ('tools/android/interactive/qualify_full_startup_preflight.py',
                'tools/android/interactive/test_full_startup_preflight.py')
SCOPE = 'actual_packaged_guest_full_startup_orchestration'
COUNT, BYTES, EPOCH = 173011, 2977730517, 1767225600
IMPORT_INPUTS = {
    'atlas/atlas-assets-index.tsv': {'bytes': 2379733, 'sha256': '1df633c5dc22667861380824f09eb6d98463a0ae025fd756b1e15ca29b933480'},
    'atlas/atlas-text-index.tsv': {'bytes': 21187391, 'sha256': '35bc97e032b286677bde32122c8cb3d14146bba2ded1f1fdc1a9a9486d37a5e8'},
    'runtime/client-caches.zip': {'bytes': 27071659, 'sha256': '5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051'},
    'runtime/client-visual-manifest.json': {'bytes': 48591999, 'sha256': '8587015400e1af639e2118649f0d9c77a089d564bfe2c97cbf9d80baaee5f9a2'},
    'runtime/zones-audio-supplement-manifest.json': {'bytes': 316144, 'sha256': 'c819e1af90c1f29a64eac57a20b0bdfb61a50bd9791206ab1ce18c05d210ec6f'},
    'runtime/zones-audio-supplement.zip': {'bytes': 847802311, 'sha256': '3bbc5773f50593e5b2e667c7e01e7f971c3a6a65137f149e0823423798d7b2a7'},
}
AUDIO_VOLUME = {'bytes': 848122891, 'sha256': '2c4bff8917d30a3835bd92e4f139a948f3c76f1e60900db01bc524b434e39d0b'}
RETAINED_MAPSERVER = {'bytes': 6892032, 'sha256': '53ff6ee013690670abbaed39e44d66267caf8753486fbc05c64766a56d9c0713'}
ORIGINAL_DBSERVER = {'bytes': 1661440, 'sha256': '535bfd6df77ce09bc3d1048accd95d7910552f8861c3a9c4e356d522786d585c'}
ATLAS_MANUAL_DBSERVER = {'bytes': 1664512, 'sha256': 'ea1d43d7a1ed61559376563bd8bad68987fbf47a4ec41f0d6fe8fe16cfe933ba'}
# The Android importer checks this exact byte contract. Here its immutable
# original leaf inventories are independently checked before a host fixture is
# published; this is not an Android ContentResolver/import-service execution.
IMPORT_CONTRACT = b'''asset.archive.bytes=615541018
asset.archive.sha256=28b4aa8f0b3a71287e9a596df23097722bd71db9ddb9a5a906b5af9d6152cc07
asset.bytes=985644857
asset.count=16721
asset.index.bytes=2379733
asset.index.sha256=1df633c5dc22667861380824f09eb6d98463a0ae025fd756b1e15ca29b933480
asset.manifest.bytes=3832869
asset.manifest.sha256=cf96742b1b65306356df69d065fcfb5bda0986ec8700d47ae1422452a1c0db7f
data.commit=d51533ec8e6a9cf726b9214968077a05fdcf19f3
format=1
repository.commit=e30c0b58b0e53534f92e77cdb7b8b93fe3ddc5ce
source.commit=0b75ade0c801735e10c5798f641948a45cc50488
storage.per.file.bytes=4096
storage.reserve.bytes=268435456
text.archive.bytes=312807038
text.archive.sha256=53f1892c8704b8a14612b3ea29e6d746d1c132ce6663862b1c25c5df65f63d3c
text.bytes=1992085660
text.count=156290
text.index.bytes=21187391
text.index.sha256=35bc97e032b286677bde32122c8cb3d14146bba2ded1f1fdc1a9a9486d37a5e8
total.bytes=2977730517
total.count=173011
'''
GATES = (
    ('original_import_leaf_inventory', 'executed_exact_original_bytes', []),
    ('client_worktree_cold_and_reuse', 'executed_production_method', ['test_stable_worktree_identity']),
    ('atlas_full_prepare_cold_and_reopen_reuse', 'executed_production_method', ['test_character_map_data', 'test_server_worktree_reuse']),
    ('kings_full_prepare_cold_and_reuse', 'executed_production_method', ['test_character_monorail', 'test_character_zoning']),
    ('client_visual_animation_zone_preparation', 'executed_production_method_after_stubbed_readiness', ['test_client_asset_closure_package']),
    ('profile_eligibility_and_preservation', 'separate_regression_and_real_postgresql_gate', ['test_character_profile_eligibility', 'test_fresh_profile_recovery', 'test_character_reopen_guest']),
    ('postgresql_persistent_profile_initialization', 'not_executed_native_boundary', ['test_login_guest']),
    ('wine_registration_odbc_driver_loading', 'not_executed_native_boundary', ['test_runtime_setup_reuse']),
    ('native_dbserver_fixed_inputs_loopback_dispatch_schema', 'not_executed_native_boundary', ['test_character_server', 'test_login_guest']),
    ('native_mapserver_tick_listener_and_protocol_readiness', 'not_executed_native_boundary', ['test_character_readiness', 'test_character_server']),
    ('native_game_login_creator_connection_and_gpu_rendering', 'not_executed_native_boundary', ['test_character_guest', 'test_character_reopen_guest']),
    ('logout_delivery_native_timer_and_committed_full_sql_save', 'not_executed_native_boundary', ['test_character_server', 'test_character_reopen_guest', 'test_startup_bundle_save']),
    ('next_session_preserved_identity_power_costume_and_position', 'not_executed_native_boundary', ['test_character_reopen_guest', 'test_character_reopen_host']),
    ('native_station_monorail_transfer_and_return', 'not_executed_native_boundary', ['test_character_monorail', 'test_character_zoning']),
    ('complete_runtime_asset_inventory_and_client_audio', 'executed_production_method', ['test_zone_asset_package']),
    ('android_contentresolver_all_four_imports', 'not_executed_android_boundary', ['test_asset_pack_import']),
    ('android_surface_input_lifecycle_capture_and_log_export', 'not_executed_android_boundary', ['test_character_readiness', 'test_character_host']),
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def index_rows(raw, prefix):
    """Parse the pinned importer index without accepting aliases or duplicates."""
    previous = ''
    for line in raw.decode('ascii').splitlines():
        fields = line.split('\t')
        require(len(fields) == 3, 'Import index fields differ')
        size, digest, name = fields
        require(size.isdigit() and str(int(size)) == size and 0 <= int(size) <= 128*1024**2
                and re.fullmatch('[0-9a-f]{64}', digest) is not None
                and leaf.safe(name) and name.startswith(prefix) and name > previous,
                'Unsafe or unordered import index')
        previous = name
        yield name, {'bytes': int(size), 'sha256': digest}


def extra_inputs(payloads):
    """Recover small omitted prerequisites from an already qualified Base volume."""
    payloads = Path(payloads)
    missing = [name for name in IMPORT_INPUTS if not (payloads/Path(name).name).exists()]
    if missing:
        for label, expected in (('Base', leaf.VOLUMES['Base']), ('Audio', AUDIO_VOLUME)):
            selected = [name for name in missing if (name.startswith('runtime/zones-audio-')) is (label == 'Audio')]
            if not selected:
                continue
            volume = payloads.parent/('COH-Assets-1.0.0-'+label+'.zip')
            if not volume.exists():
                require(label == 'Audio', 'Already qualified Base volume is required')
                pending = volume.with_suffix('.partial')
                try:
                    with urllib.request.urlopen(leaf.RELEASE_URL+volume.name, timeout=120) as response, pending.open('wb') as output:
                        count = 0
                        while block := response.read(1024*1024):
                            count += len(block); require(count <= expected['bytes'], 'Audio volume exceeded pin')
                            output.write(block)
                    leaf.checked(pending, expected); os.replace(pending, volume)
                finally:
                    pending.unlink(missing_ok=True)
            leaf.checked(volume, expected)
            with zipfile.ZipFile(volume) as archive:
                for name in selected:
                    entry = archive.getinfo('payloads/'+name)
                    require(not entry.is_dir() and entry.file_size == IMPORT_INPUTS[name]['bytes'],
                            'Import prerequisite ZIP member differs')
                    target = payloads/Path(name).name
                    with archive.open(entry) as source, target.open('xb') as output:
                        shutil.copyfileobj(source, output, 1024*1024)
                    leaf.checked(target, IMPORT_INPUTS[name]); target.chmod(0o444)
    for name, expected in IMPORT_INPUTS.items():
        leaf.checked(payloads/Path(name).name, expected)


def materialize_import(payloads, destination):
    """A fresh complete import fixture; never a selected collision-only tree."""
    payloads, destination = Path(payloads), Path(destination)
    require(not destination.exists() and not destination.is_symlink(), 'Fresh import fixture required')
    destination.mkdir(mode=0o700)
    data = destination/'data'; data.mkdir(mode=0o700)
    inventory = hashlib.sha256(); count = total = 0; logical_names = set(); directories = {}
    # AtlasAssetImporter.extract uses text first and canonicalPath retains the
    # first encountered directory spelling; original asset leaves follow it.
    for archive_name, index_name, prefix in (
            ('atlas-text.zip', 'atlas-text-index.tsv', 'data/'),
            ('atlas-assets.zip', 'atlas-assets-index.tsv', 'assets/')):
        raw_index = (payloads/index_name).read_bytes()
        selected = list(index_rows(raw_index, prefix))
        with zipfile.ZipFile(payloads/archive_name) as archive:
            entries = archive.infolist()
            expected_names = {name for name, _ in selected}
            if prefix == 'assets/':
                expected_names.add('asset-manifest.json')
            require(len(entries) == len(expected_names) and {entry.filename for entry in entries} == expected_names,
                    'Complete imported archive inventory differs')
            for name, expected in selected:
                relative = name[len(prefix):]
                require(relative.casefold() not in logical_names, 'Case-conflicting original import path')
                logical_names.add(relative.casefold())
                entry = archive.getinfo(name)
                require(not entry.is_dir() and not entry.flag_bits & 1
                        and stat.S_IFMT(entry.external_attr >> 16) == stat.S_IFREG
                        and entry.file_size == expected['bytes'], 'Original import member differs')
                parts = relative.split('/'); directory = ''
                for part in parts[:-1]:
                    proposed = directory+'/'+part if directory else part
                    directory = directories.setdefault(proposed.casefold(), proposed)
                relative = directory+'/'+parts[-1] if directory else parts[-1]
                target = data/relative
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                digest = hashlib.sha256()
                with archive.open(entry) as source, target.open('xb') as output:
                    for block in iter(lambda: source.read(1024*1024), b''):
                        digest.update(block); output.write(block)
                require(digest.hexdigest() == expected['sha256'], 'Original import leaf hash differs: '+name)
                target.chmod(0o444); os.utime(target, (EPOCH, EPOCH))
                count += 1; total += expected['bytes']
                inventory.update((relative+'\t'+str(expected['bytes'])+'\t'+expected['sha256']+'\n').encode())
    require((count, total) == (COUNT, BYTES), 'Full imported leaf count/bytes differ')
    contract_sha = hashlib.sha256(IMPORT_CONTRACT).hexdigest()
    (destination/'complete.properties').write_text('generation=generation-'+ '0'*32 +
        '\ncontract.sha256='+contract_sha+'\ncount='+str(COUNT)+'\nbytes='+str(BYTES)+'\n')
    return data, {'files': count, 'bytes': total, 'all_leaf_sha256_checked': True,
                  'inventory_sha256': inventory.hexdigest(), 'contract_sha256': contract_sha,
                  'android_import_service_executed': False}


def checked_import_fixture(payloads):
    """Keep expensive exact inputs; independently rehash every leaf on reuse."""
    payloads = Path(payloads); destination = payloads.parent/'full-original-import-fixture-v1'
    marker = destination/'original-import-proof.json'
    if not destination.exists():
        staging = Path(tempfile.mkdtemp(prefix='full-original-import-pending-', dir=payloads.parent))
        staging.rmdir()
        try:
            _, proof = materialize_import(payloads, staging)
            (staging/marker.name).write_text(json.dumps(proof, sort_keys=True)+'\n')
            staging.rename(destination)
        finally:
            if staging.exists(): shutil.rmtree(staging)
    require(destination.is_dir() and not destination.is_symlink() and marker.is_file()
            and not marker.is_symlink() and marker.stat().st_nlink == 1, 'Invalid complete import fixture')
    saved = json.loads(marker.read_text()); data = destination/'data'
    directories = {}; digest = hashlib.sha256(); count = total = 0
    for index_name, prefix in (('atlas-text-index.tsv', 'data/'), ('atlas-assets-index.tsv', 'assets/')):
        for name, expected in index_rows((payloads/index_name).read_bytes(), prefix):
            parts = name[len(prefix):].split('/'); directory = ''
            for part in parts[:-1]:
                proposed = directory+'/'+part if directory else part
                directory = directories.setdefault(proposed.casefold(), proposed)
            relative = directory+'/'+parts[-1] if directory else parts[-1]
            target = data/relative; info = target.lstat()
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and not info.st_mode & 0o222
                    and int(info.st_mtime) == EPOCH, 'Complete import fixture leaf ownership changed')
            leaf.checked(target, expected)
            count += 1; total += expected['bytes']
            digest.update((relative+'\t'+str(expected['bytes'])+'\t'+expected['sha256']+'\n').encode())
    visited = 0; pending = [data]
    while pending:
        current = pending.pop()
        require(current.is_dir() and not current.is_symlink(), 'Linked complete import fixture directory')
        with os.scandir(current) as entries:
            for entry in entries:
                require(not entry.is_symlink(), 'Linked complete import fixture entry')
                if entry.is_dir(follow_symlinks=False): pending.append(Path(entry.path))
                else:
                    require(entry.is_file(follow_symlinks=False), 'Nonregular complete import fixture entry')
                    visited += 1
    proof = {'files': count, 'bytes': total, 'all_leaf_sha256_checked': True,
        'inventory_sha256': digest.hexdigest(), 'contract_sha256': hashlib.sha256(IMPORT_CONTRACT).hexdigest(),
        'android_import_service_executed': False}
    require((count, total, visited) == (COUNT, BYTES, COUNT) and proof == saved,
            'Complete immutable import fixture inventory changed')
    return data, proof


def verify_inputs_before_import(client, assets, payloads):
    """A missing/tampered required APK input cannot trigger the large mirror."""
    hashes = client.verify_assets(assets)
    data, proof = checked_import_fixture(payloads)
    return hashes, data, proof


class Context:
    """No process or SQL API: production preparation can only touch owned files."""
    def __init__(self):
        self.report = {}; self.events = []; self.deadline = float('inf')
    def check(self):
        pass
    def event(self, kind, **fields):
        if kind != 'stage':
            self.events.append({'kind': kind, **fields})
    def stage(self, name):
        self.events.append({'stage': name})
    def passed(self, **fields):
        pass


def phase_result(server):
    report = server.creation_report
    require(report['server_animation_pack']['installed'] is True
            and report['atlas_beacon_graph']['status'] in ('installed_verified_graph', 'reused_verified_graph')
            and report['prepared_server_caches']['status'] in ('installed', 'preserved_existing_native_caches'),
            'Full Atlas preparation did not install every required native asset')
    return {
        'private_data_files': report['private_map_data']['files'],
        'private_data_bytes': report['private_map_data']['bytes'],
        'directory_count': report['private_map_data']['directories'],
        'cache_reused': server.data_cache.summary['reused'],
        'prepared_cache_status': report['prepared_server_caches']['status'],
        'prepared_cache_files_installed': report['prepared_server_caches']['installed_files'],
        'animation_installed': report['server_animation_pack']['installed'],
        'animation_count': report['server_animation_pack']['pigg']['animation_count'],
        'graph_status': report['atlas_beacon_graph']['status'],
        'all_preparation_phases': list(report['server_preparation_phase_seconds']),
        'native_mapserver': leaf.pin(server.runtime/'MapServer.exe'),
        'manual_atlas_dbserver': leaf.pin(server.runtime/'DbServer.exe'),
    }


def worker(runtime_assets, payloads):
    runtime_assets, payloads = Path(runtime_assets).resolve(), Path(payloads).resolve()
    sys.path.insert(0, str(runtime_assets))
    import client_startup_diagnostic as client
    import character_creation_diagnostic as creation
    import local_character_server as server
    import character_zoning as zoning
    import character_avatar_assets as avatar
    import atlas_world_assets as world
    require(all(Path(m.__file__).resolve().parent == runtime_assets for m in
                (client, creation, server, zoning, avatar, world)),
            'Full startup must import actual packaged guest modules')
    asset_pins = leaf.validate_assets(payloads)
    extra_inputs(payloads)
    original_verify = server.server_data_cache.CheckedInputResolver.verify
    def verify_with_failure_trace(resolver):
        try:
            return original_verify(resolver)
        except Exception:
            changed = []
            for path, previous in resolver.observed.items():
                current = resolver.directory_identity(path.lstat())
                if current != previous:
                    changed.append({'path': str(path), 'before': list(previous), 'after': list(current)})
            (payloads.parent/'full-startup-input-mutation-trace.json').write_text(json.dumps(changed, indent=2)+'\n')
            raise
    server.server_data_cache.CheckedInputResolver.verify = verify_with_failure_trace
    with tempfile.TemporaryDirectory(prefix='coh-complete-startup-') as temporary:
        root = Path(temporary); assets = root/'assets'; assets.mkdir()
        for source in sorted(runtime_assets.iterdir()):
            if source.is_file():
                # JSON/runtime helpers use production single-owner file gates.
                # These small APK payloads must retain nlink=1 in the fixture.
                shutil.copyfile(source, assets/source.name)
        for name in set(asset_pins) | {Path(n).name for n in IMPORT_INPUTS}:
            target = assets/name
            if target.exists():
                require(leaf.pin(target) == leaf.pin(payloads/name), 'APK/external payload collision differs')
            else:
                if name.endswith('.json'):
                    shutil.copyfile(payloads/name, target)
                else:
                    os.link(payloads/name, target)
        # Verify the entire manifest before the expensive worktree mirror;
        # this includes Audio and the full visual metadata absent leaf-only CI.
        asset_hashes, data, import_proof = verify_inputs_before_import(client, assets, payloads)
        context = Context(); state = root/'state'; state.mkdir(); owned = root/'owned'; owned.mkdir()
        identity = client.import_identity(data)
        work, receipt = client.prepare_worktree(owned, data, assets, identity, context)
        require(receipt['reused'] is False and receipt['input_files'] == COUNT
                and receipt['imported_inputs_readonly'] is True, 'Cold full client worktree did not pass')
        context.report['client_worktree'] = receipt
        context.report['character_avatar_supplement'] = avatar.install(work, assets, context)
        context.report['atlas_world_supplement'] = world.install(work, assets, context)
        prepared = {}
        for label, owner_class, session in (
                ('fresh_create', server.LocalCharacterServer, '1'*32),
                ('saved_reopen', zoning.LocalCharacterZoningServer, '2'*32)):
            owner = SimpleNamespace(root=owned, work=work, ctx=context,
                args=SimpleNamespace(assets=assets, game_data=data, session_id=session, state=state),
                cleanup_status={'wine_prefix_stopped': True, 'owned_processes_reaped': True})
            instance = owner_class(owner)
            instance.payloads()
            instance.prepare_runtime()
            prepared[label] = phase_result(instance)
            require(instance.data_cache.summary['reused'] is (label == 'saved_reopen'),
                    'Expected production Atlas cold/reuse cache path was not executed')
            # The real visual orchestration runs only after native readiness.
            # Here those two process-boundary facts are explicitly stubs. No
            # readiness/client/rendering claim can be inferred from this call.
            instance.report['server_ready'] = True; instance.creation_report['map_ready'] = True
            context.report['asset_sha256'] = asset_hashes
            diagnostic = creation.CharacterCreationDiagnostic.__new__(creation.CharacterCreationDiagnostic)
            diagnostic.work, diagnostic.ctx, diagnostic.local_server = work, context, instance
            diagnostic.args = owner.args
            diagnostic.prepare_client_visual_inputs()
            kings = instance.prepare_kings_row_runtime()
            k = kings['preparation']
            require(leaf.pin(instance.runtime/'DbServer.exe') == ATLAS_MANUAL_DBSERVER
                    and leaf.pin(instance.map_package_dir/'DbServer.exe') == ORIGINAL_DBSERVER
                    and leaf.pin(kings['runtime']/'DbServer.exe') == ORIGINAL_DBSERVER
                    and leaf.pin(instance.runtime/'MapServer.exe') == RETAINED_MAPSERVER
                    and leaf.pin(kings['runtime']/'MapServer.exe') == RETAINED_MAPSERVER,
                    'Atlas manual/Kings original dependency pins changed')
            require(k['server_data_cache']['reused'] is (label == 'saved_reopen')
                    and k['graph']['status'] in ('installed_verified_graph', 'reused_verified_graph')
                    and k['animation']['installed'] is True,
                    'Full Kings Row cold/reuse path did not pass')
            prepared[label]['kings_row'] = {
                'cache_reused': k['server_data_cache']['reused'],
                'graph_status': k['graph']['status'],
                'animation_count': k['animation']['pigg']['animation_count'],
                'prepared_cache_status': k['prepared_server_caches']['status'],
                'collision_geometry': leaf.stable(k['geometry']),
                'native_mapserver': leaf.pin(kings['runtime']/'MapServer.exe'),
                'native_dbserver': leaf.pin(kings['runtime']/'DbServer.exe'),
                'authenticated_original_dbserver': leaf.pin(instance.map_package_dir/'DbServer.exe'),
            }
            instance.cleanup_config()
            require(instance.data_cache.summary.get('returned_after_owned_cleanup') is True
                    and instance.kings_row_data_cache.summary.get('returned_after_owned_cleanup') is True,
                    'Production preparation caches were not returned to closed ownership')
            require(not (instance.data_cache.path/'data/server/db/servers.cfg').exists()
                    and not (instance.kings_row_data_cache.path/'data/server/db/servers.cfg').exists(),
                    'Closed cache retained database connection configuration')
            if label == 'fresh_create':
                next_work, next_receipt = client.prepare_worktree(owned, data, assets, identity, context)
                require(next_work == work and next_receipt['reused'] is True, 'Full client reopen worktree was not reused')
                context.report['client_worktree'] = next_receipt
        return {
            'format': 1, 'status': 'passed', 'scope': SCOPE, 'asset_version': '1.0.0',
            'packaged_guest_sources': {p.name: leaf.pin(p) for p in sorted(runtime_assets.glob('*.py'))},
            'game_archive': leaf.pin(runtime_assets/'game-package.tar.gz'),
            'original_import': import_proof, 'preparation': prepared,
            'full_private_worktree_mirror_executed': True, 'full_prepare_runtime_executed': True,
            'fresh_create_cold_preparation_verified': True, 'saved_reopen_warm_preparation_verified': True,
            'full_kings_row_cold_and_reuse_preparation_verified': True,
            'client_visual_orchestration_executed': True, 'client_visual_readiness_boundary_stubbed': True,
            'complete_runtime_asset_inventory_verified': True, 'client_audio_orchestration_executed': True,
            'all_external_runtime_asset_pins': {**asset_pins, **{Path(n).name:p for n,p in IMPORT_INPUTS.items()}},
            'owned_cache_return_and_credential_removal_executed': True,
            'atlas_manual_and_kings_stock_dbserver_pins_verified': True,
            'cache_cleanup_prerequisites_stubbed_no_native_processes_started': True,
            'native_runtime_booted': False, 'physical_execution_validated': False,
            'live_database_and_saved_character_executed': False,
            'process_and_sql_boundary': 'not_executed',
            'production_methods_executed': {
                'client_startup_diagnostic.prepare_worktree': 2,
                'character_avatar_assets.install': 1, 'atlas_world_assets.install': 1,
                'LocalCharacterServer.payloads': 2, 'LocalCharacterServer.prepare_runtime': 2,
                'CharacterCreationDiagnostic.prepare_client_visual_inputs': 2,
                'LocalCharacterServer.prepare_kings_row_runtime': 2,
                'LocalCharacterServer.cleanup_config': 2},
            'gate_inventory': [{'stage': stage, 'execution': execution, 'regression_suites': suites}
                               for stage, execution, suites in GATES],
        }


def validate_proof(value):
    require(isinstance(value, dict) and value.get('status') == 'passed' and value.get('scope') == SCOPE,
            'Full startup preflight receipt differs')
    for flag in ('full_private_worktree_mirror_executed', 'full_prepare_runtime_executed',
                 'fresh_create_cold_preparation_verified', 'saved_reopen_warm_preparation_verified',
                 'full_kings_row_cold_and_reuse_preparation_verified',
                 'client_visual_orchestration_executed', 'client_visual_readiness_boundary_stubbed',
                 'complete_runtime_asset_inventory_verified', 'client_audio_orchestration_executed',
                 'atlas_manual_and_kings_stock_dbserver_pins_verified',
                 'owned_cache_return_and_credential_removal_executed',
                 'cache_cleanup_prerequisites_stubbed_no_native_processes_started'):
        require(value.get(flag) is True, 'Required full startup execution absent: '+flag)
    for flag in ('native_runtime_booted', 'physical_execution_validated', 'live_database_and_saved_character_executed'):
        require(value.get(flag) is False, 'Host preparation cannot claim native/device execution: '+flag)
    require(value.get('process_and_sql_boundary') == 'not_executed', 'Native boundary claim differs')
    original = value.get('original_import', {})
    require(original.get('files') == COUNT and original.get('bytes') == BYTES
            and original.get('all_leaf_sha256_checked') is True
            and original.get('android_import_service_executed') is False
            and re.fullmatch('[0-9a-f]{64}', str(original.get('inventory_sha256'))) is not None
            and original.get('contract_sha256') == hashlib.sha256(IMPORT_CONTRACT).hexdigest(),
            'Complete original import proof differs')
    methods = {'client_startup_diagnostic.prepare_worktree': 2,
        'character_avatar_assets.install': 1, 'atlas_world_assets.install': 1,
        'LocalCharacterServer.payloads': 2, 'LocalCharacterServer.prepare_runtime': 2,
        'CharacterCreationDiagnostic.prepare_client_visual_inputs': 2,
        'LocalCharacterServer.prepare_kings_row_runtime': 2, 'LocalCharacterServer.cleanup_config': 2}
    require(value.get('production_methods_executed') == methods, 'Production startup method inventory differs')
    preparation = value.get('preparation', {})
    require(set(preparation) == {'fresh_create', 'saved_reopen'}, 'Complete creation/reopen preparation proof missing')
    for label, expected_reuse in (('fresh_create', False), ('saved_reopen', True)):
        phase = preparation[label]; kings = phase.get('kings_row', {})
        require(phase.get('cache_reused') is expected_reuse and kings.get('cache_reused') is expected_reuse
                and phase.get('private_data_files', 0) >= COUNT and phase.get('private_data_bytes', 0) >= BYTES
                and phase.get('animation_installed') is True and phase.get('animation_count') == 5878
                and kings.get('animation_count') == 5878
                and phase.get('graph_status') in ('installed_verified_graph', 'reused_verified_graph')
                and kings.get('graph_status') in ('installed_verified_graph', 'reused_verified_graph')
                and phase.get('prepared_cache_status') in ('installed', 'preserved_existing_native_caches')
                and kings.get('prepared_cache_status') in ('installed', 'preserved_existing_native_caches'),
                'Complete production cold/reuse preparation differs: '+label)
        require(phase.get('native_mapserver') == RETAINED_MAPSERVER
                and kings.get('native_mapserver') == RETAINED_MAPSERVER
                and phase.get('manual_atlas_dbserver') == ATLAS_MANUAL_DBSERVER
                and kings.get('native_dbserver') == ORIGINAL_DBSERVER
                and kings.get('authenticated_original_dbserver') == ORIGINAL_DBSERVER,
                'Retained Atlas manual/Kings original native pins differ: '+label)
    require(value.get('gate_inventory') == [{'stage': stage, 'execution': execution, 'regression_suites': suites}
                                          for stage, execution, suites in GATES], 'Startup gate inventory differs')
    return value


def preflight(runtime_assets, payloads):
    with tempfile.TemporaryDirectory(prefix='coh-full-startup-receipt-') as temporary:
        output = Path(temporary)/'proof.json'
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--worker',
            '--runtime-assets', str(Path(runtime_assets).resolve()), '--payloads', str(Path(payloads).resolve()),
            '--output', str(output)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1800)
        require(result.returncode == 0, 'Actual packaged full startup preflight failed:\n'+result.stderr[-18000:])
        return validate_proof(json.loads(output.read_bytes()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-assets', type=Path, required=True)
    parser.add_argument('--payloads', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    value = worker(args.runtime_assets, args.payloads) if args.worker else preflight(args.runtime_assets, args.payloads)
    validate_proof(value)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n')


if __name__ == '__main__':
    main()
