#!/usr/bin/env python3
"""Run full original assets through saved-Kings preparation and an Atlas control.

The frozen full-startup worker remains byte-identical and is freshly executed in
its original full-input Atlas control configuration. A separate unpatched APK
guest fixture exercises saved-Kings selection, schema-only Db preparation,
projected cold/warm Kings trees, deferred Atlas, and owned cache return. All SQL
rows, readiness facts and cleanup prerequisites are explicitly controlled host
boundaries. No native process, physical gameplay or committed save is claimed.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import map_startup_proof_transport as transport
import qualify_runtime_asset_preflight as leaf

ROOT = Path(__file__).resolve().parents[3]
SCOPE = 'actual_packaged_guest_saved_kings_preparation'
PROJECTED_MAP = 'fea96d0a20f5e245930abd0a97e8cc1da7c4ef4c83ff8a7d5a5c283ba8071363'
PROJECTION_SOURCE = '2048c22f8380931514cefb429790552295e52dd72e03617973820936e116639d'
SOURCE_FILES = ('tools/android/interactive/qualify_saved_map_preparation.py',
                'tools/android/interactive/test_saved_map_preparation_proof.py')
BOUNDARY = {
    'historical_worker_bytes_unchanged': True,
    'historical_initial_map_selection': 'controlled_Atlas_SQL_boundary',
    'historical_input_projection': 'retained_unprojected_full_input_control',
    'production_preparation_methods_patched': False,
    'saved_map_sql_boundary': 'controlled_read_only_selected_rows_not_PostgreSQL',
    'client_visual_readiness_boundary': 'controlled_host_facts_no_native_readiness',
    'cleanup_prerequisites': 'controlled_no_native_processes_started',
    'native_runtime_booted': False,
    'physical_execution_validated': False,
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def source_pins():
    return {name: leaf.pin(ROOT/name) for name in SOURCE_FILES}


def sql_fixture(instance, map_id=5):
    """Bind production SELECT callers to immutable fixture rows, never SQL writes."""
    import local_character_server as server
    evidence = server.evidence
    attributes = instance.schema['expected_attributes']['attributes']
    attr = next(row['id'] for row in attributes if type(row['id']) is int and row['id'] > 0)
    rows = {table: [{field: 1 for field in fields}] for table, fields in evidence.SELECTED.items()}
    for table, values in rows.items():
        values[0]['containerid'] = 1
        if table != 'ents': values[0]['subid'] = 0
        for field in evidence.ATTRIBUTE_FIELDS.get(table, ()):
            values[0][field] = attr
    rows['ents'][0].update(authid=77, authname='COHLOCAL', name='THORHERO', logincount=3,
        influencepoints=0, description='', motto='', datecreated='2026-10-01')
    identity = [{key: rows['ents'][0][key] for key in evidence.IDENTITY_FIELDS}]
    position = dict(containerid=1, mapid=None, staticmapid=map_id, posx=12.5, posy=-20.0, posz=40.25)
    snapshot = copy.deepcopy((rows, identity, position)); calls = []
    def sql(query, *, game=False, **kwargs):
        require(game is True and query == "SELECT containerid || '|' || authname FROM dbo.shardaccounts "
                "WHERE lower(authname)=lower('COHLOCAL') ORDER BY containerid;" and not kwargs,
                'Saved-map fixture refused an unreviewed SQL statement')
        calls.append({'kind': 'SELECT', 'table': 'shardaccounts'})
        return '77|COHLOCAL'
    def selected(table, fields, keys, where=None):
        if table == 'ents' and tuple(fields) == tuple(evidence.IDENTITY_FIELDS) and where is None:
            value = identity
        elif table == 'ents' and tuple(fields) == ('containerid','mapid','staticmapid','posx','posy','posz'):
            require(where == 'containerid=1', 'Position fixture identity differs')
            value = [position]
        else:
            require(table in rows and tuple(fields) == tuple(evidence.SELECTED[table])
                    + (('logincount',) if table == 'ents' else ()) and where == 'containerid=1',
                    'Saved-map fixture refused unreviewed selected columns')
            value = rows[table]
        calls.append({'kind': 'selected_rows', 'table': table, 'fields': list(fields)})
        return copy.deepcopy(value)
    instance.sql, instance.sql_rows = sql, selected
    def verify():
        require((rows, identity, position) == snapshot and calls, 'Fixture character state changed or was never read')
        require(instance.baseline_snapshot['rows'] == rows, 'Complete selected character baseline changed')
        return {'sql_boundary': 'controlled_read_only_selected_rows_not_PostgreSQL',
                'selected_row_reads': len(calls), 'rows_unchanged': True,
                'identity_and_selected_powers_costume_preserved': True,
                'saved_position': copy.deepcopy(position),
                'selected_rows_sha256': hashlib.sha256(leaf.canonical(rows)).hexdigest()}
    return verify


def setup_assets(full, runtime_assets, payloads, root):
    asset_pins = leaf.validate_assets(payloads)
    full.extra_inputs(payloads)
    assets = root/'assets'; assets.mkdir()
    for source in sorted(runtime_assets.iterdir()):
        if source.is_file(): shutil.copyfile(source, assets/source.name)
    for name in set(asset_pins) | {Path(n).name for n in full.IMPORT_INPUTS}:
        target = assets/name
        if target.exists():
            require(leaf.pin(target) == leaf.pin(payloads/name), 'APK/external asset collision differs')
        elif name.endswith('.json'):
            shutil.copyfile(payloads/name, target)
        else:
            os.link(payloads/name, target)
    return assets


def texture_inventory(data):
    """Host-only count of the exact excluded input tree; never a cache proof."""
    tree = Path(data)/'texture_library'
    require(tree.is_dir() and not tree.is_symlink(), 'Actual texture input tree missing or linked')
    count = total = 0
    for directory, names, files in os.walk(tree, followlinks=False):
        require(all(not (Path(directory)/name).is_symlink() for name in names),
                'Linked texture inventory directory refused')
        for name in files:
            source = Path(directory)/name
            require(source.is_file(), 'Non-file texture input refused')
            count += 1; total += source.stat().st_size
    return {'files': count, 'bytes': total, 'scope': 'host_input_inventory_not_native_reads'}


def saved_worker(full, runtime_assets, payloads):
    import client_startup_diagnostic as client
    import character_creation_diagnostic as creation
    import local_character_server as server
    import character_zoning as zoning
    import character_avatar_assets as avatar
    import atlas_world_assets as world
    require(all(Path(m.__file__).resolve().parent == runtime_assets for m in
            (client, creation, server, zoning, avatar, world)), 'Saved-map worker guest import was shadowed')
    with tempfile.TemporaryDirectory(prefix='coh-saved-map-assets-') as temporary:
        root = Path(temporary); assets = setup_assets(full, runtime_assets, payloads, root)
        hashes, data, imported = full.verify_inputs_before_import(client, assets, payloads)
        original_textures = texture_inventory(data)
        owned = root/'owned'; owned.mkdir(); state = root/'state'; state.mkdir()
        ctx = full.Context(); ctx.secrets = []
        identity = client.import_identity(data)
        work, receipt = client.prepare_worktree(owned, data, assets, identity, ctx)
        require(receipt['reused'] is False and receipt['input_files'] == full.COUNT,
                'Saved-map fixture did not prepare every original imported input')
        ctx.report.update(client_worktree=receipt, asset_sha256=hashes)
        ctx.report['character_avatar_supplement'] = avatar.install(work, assets, ctx)
        ctx.report['atlas_world_supplement'] = world.install(work, assets, ctx)
        cases = {}; admission = None
        for label, session in (('cold', '3'*32), ('warm', '4'*32)):
            owner = SimpleNamespace(root=owned, work=work, ctx=ctx,
                args=SimpleNamespace(assets=assets, game_data=data, session_id=session, state=state),
                cleanup_status={'wine_prefix_stopped': True, 'owned_processes_reaped': True})
            instance = zoning.LocalCharacterZoningServer(owner)
            instance.payloads(); verify_sql = sql_fixture(instance)
            instance.prepare_runtime()
            require(instance.active_map_id == 5 and instance.startup_preparation_map_id == 5
                    and instance.atlas_preparation_deferred is True and not hasattr(instance, 'data_cache')
                    and '1' not in instance.creation_report.get('map_startup_observation', {})
                    and not (instance.runtime/'data/maps').exists()
                    and not (instance.runtime/'data/texture_library').exists(),
                    'Saved Kings initial preparation unexpectedly built Atlas or changed the saved map')
            current = leaf.native_binding(instance.runtime, instance.map_package)
            if admission is None: admission = current
            require(leaf.canonical(admission) == leaf.canonical(current), 'Cold/warm native admission differs')
            config = instance.runtime/'data/server/db/servers.cfg'
            # No credential is introduced. The schema-only runtime's exact files
            # and inodes must stay stable while destination providers are built.
            db_before = {name: ((instance.runtime/name).stat().st_ino, leaf.pin(instance.runtime/name))
                         for name in instance.schema['files']}
            instance.config = config
            db_config = config.read_bytes()
            # This invokes actual packaged visual installation, with explicit
            # controlled readiness flags, before either world mirror observes it.
            instance.report['server_ready'] = True
            instance.creation_report['map_ready'] = True
            visual = creation.CharacterCreationDiagnostic.__new__(creation.CharacterCreationDiagnostic)
            visual.work, visual.ctx, visual.local_server, visual.args = work, ctx, instance, owner.args
            visual.prepare_client_visual_inputs()
            instance.creation_report['map_ready'] = False
            client_textures = texture_inventory(work/'data')
            kings = instance.prepare_kings_row_runtime()
            k = kings['preparation']; kr = kings['runtime']
            require(k['server_data_cache']['reused'] is (label == 'warm')
                    and not (kr/'data/texture_library').exists()
                    and k['graph']['verified'] is True and k['graph']['map_id'] == 5
                    and k['animation']['installed'] is True
                    and k['prepared_server_caches']['status'] in ('installed','preserved_existing_native_caches')
                    and not hasattr(instance, 'data_cache')
                    and '1' not in instance.creation_report.get('map_startup_observation', {}),
                    'Direct Kings cold/warm preparation did not retain its selected-map guarantees')
            require(leaf.pin(kr/'MapServer.exe') == admission['authenticated_mapserver']
                    and leaf.pin(kr/'DbServer.exe') == full.ORIGINAL_DBSERVER,
                    'Kings native dependencies differ')
            require(not instance.maps and instance.process is None and instance.map_process is None,
                    'Host preparation unexpectedly created a native process handle')
            before_atlas = verify_sql()
            atlas = instance.prepare_atlas_runtime()
            require(atlas != instance.runtime and instance.prepare_atlas_runtime() == atlas
                    and instance.data_cache.summary['reused'] is (label == 'warm')
                    and instance.creation_report['atlas_beacon_graph']['status'] in ('installed_verified_graph','reused_verified_graph')
                    and not (atlas/'data/texture_library').exists()
                    and (atlas/'data/server/db/servers.cfg').read_bytes() == db_config
                    and {name: ((instance.runtime/name).stat().st_ino, leaf.pin(instance.runtime/name))
                         for name in instance.schema['files']} == db_before,
                    'On-demand Atlas changed the active DbServer or failed cache/graph preparation')
            require(leaf.pin(atlas/'MapServer.exe') == admission['authenticated_mapserver']
                    and leaf.pin(atlas/'DbServer.exe') == full.ORIGINAL_DBSERVER
                    and leaf.pin(instance.runtime/'DbServer.exe') == full.ATLAS_MANUAL_DBSERVER
                    and leaf.pin(work/'data/bin/fxinfo.bin') == leaf.CLIENT_FULL_FX,
                    'Native dependencies or original client FX changed during deferred preparation')
            result = {
                'selected_map_id': 5, 'selected_port': 7003,
                'unassigned_prelogin_mapid_preserved': True,
                'db_schema_only_before_destination': True,
                'atlas_deferred_until_explicit_prepare': True,
                'atlas_runtime_separate_from_live_db': True,
                'db_schema_and_config_inodes_and_bytes_preserved': True,
                'texture_tree_excluded_from_server_only': True,
                'native_processes_started': 0,
                'sql_baseline': before_atlas,
                'kings': {'cache_reused': k['server_data_cache']['reused'], 'graph_status': k['graph']['status'],
                          'graph_map_id': k['graph']['map_id'], 'animation_count': k['animation']['pigg']['animation_count'],
                          'prepared_cache_status': k['prepared_server_caches']['status'],
                          'native_mapserver': leaf.pin(kr/'MapServer.exe'), 'native_dbserver': leaf.pin(kr/'DbServer.exe')},
                'atlas_on_demand': {'cache_reused': instance.data_cache.summary['reused'],
                          'graph_status': instance.creation_report['atlas_beacon_graph']['status'],
                          'native_mapserver': leaf.pin(atlas/'MapServer.exe'), 'native_dbserver': leaf.pin(atlas/'DbServer.exe')},
                'source_projection': server.server_input_projection(instance.map_package),
                'excluded_client_texture_inventory': client_textures,
                'actual_server_data_files': instance.creation_report['private_map_data']['files'],
            }
            instance.cleanup_config()
            require(instance.data_cache.summary.get('returned_after_owned_cleanup') is True
                    and instance.kings_row_data_cache.summary.get('returned_after_owned_cleanup') is True
                    and not (instance.data_cache.path/'data/server/db/servers.cfg').exists()
                    and not (instance.kings_row_data_cache.path/'data/server/db/servers.cfg').exists(),
                    'Saved-map caches were not closed and stripped of session configuration')
            verify_sql()
            result['both_caches_returned_after_controlled_cleanup'] = True
            result['closed_cache_credentials_removed'] = True
            cases[label] = result
            if label == 'cold':
                next_work, receipt = client.prepare_worktree(owned, data, assets, identity, ctx)
                require(next_work == work and receipt['reused'] is True, 'Saved-map warm client checkout failed')
                ctx.report['client_worktree'] = receipt
        return {'format': 1, 'status': 'passed', 'scope': SCOPE, 'asset_version': '1.0.0',
            'original_import': imported, 'original_import_texture_inventory': original_textures,
            'native_admission': admission, 'cases': cases,
            'packaged_guest_sources': {p.name: leaf.pin(p) for p in sorted(runtime_assets.glob('*.py'))},
            'process_and_sql_boundary': 'not_executed', 'native_runtime_booted': False,
            'physical_execution_validated': False, 'live_database_and_saved_character_executed': False,
            'client_visual_readiness_boundary_stubbed': True,
            'cache_cleanup_prerequisites_stubbed_no_native_processes_started': True}


def worker(runtime_assets, payloads):
    runtime_assets, payloads = Path(runtime_assets).resolve(), Path(payloads).resolve()
    full = transport.worker_module('full_startup')
    sys.path.insert(0, str(runtime_assets))
    import character_zoning as zoning
    import local_character_server as server
    require(Path(server.__file__).resolve().parent == runtime_assets
            and Path(zoning.__file__).resolve().parent == runtime_assets, 'Historical adapter guest import was shadowed')
    old_verify = server.server_data_cache.CheckedInputResolver.verify
    try:
        with patch.object(zoning.LocalCharacterZoningServer, 'initial_map_preparation', lambda self: 1), \
             patch.object(server, 'server_input_projection', lambda package: None):
            historical = full.validate_proof(full.worker(runtime_assets, payloads))
    finally:
        server.server_data_cache.CheckedInputResolver.verify = old_verify
    saved = saved_worker(full, runtime_assets, payloads)
    return validate_proof({'format': 1, 'status': 'passed', 'adapter_boundary': dict(BOUNDARY),
        'full_startup': historical, 'saved_map_preparation': saved,
        'source_pins': source_pins(), 'frozen_workers': transport.WORKERS})


def validate_saved(value):
    full = transport.worker_module('full_startup')
    require(type(value) is dict and type(value.get('format')) is int and value.get('format') == 1 and value.get('status') == 'passed'
            and value.get('scope') == SCOPE and value.get('asset_version') == '1.0.0', 'Saved-map proof scope differs')
    for key in ('native_runtime_booted','physical_execution_validated','live_database_and_saved_character_executed'):
        require(value.get(key) is False, 'Host preparation cannot claim native or player execution: ' + key)
    require(value.get('process_and_sql_boundary') == 'not_executed'
            and value.get('client_visual_readiness_boundary_stubbed') is True
            and value.get('cache_cleanup_prerequisites_stubbed_no_native_processes_started') is True,
            'Saved-map host boundary differs')
    native = leaf.validate_native_binding(value.get('native_admission'))
    imported = value.get('original_import', {})
    require(imported.get('files') == full.COUNT and imported.get('bytes') == full.BYTES
            and imported.get('all_leaf_sha256_checked') is True
            and imported.get('android_import_service_executed') is False
            and imported.get('contract_sha256') == hashlib.sha256(full.IMPORT_CONTRACT).hexdigest()
            and re.fullmatch('[0-9a-f]{64}', str(imported.get('inventory_sha256'))) is not None,
            'Saved-map original imported bytes not proved')
    inventories = [value.get('original_import_texture_inventory', {})]
    cases = value.get('cases', {})
    require(set(cases) == {'cold', 'warm'}, 'Saved-map cold/warm cases missing')
    for label, case in cases.items():
        for key in ('unassigned_prelogin_mapid_preserved','db_schema_only_before_destination',
                    'atlas_deferred_until_explicit_prepare','atlas_runtime_separate_from_live_db',
                    'db_schema_and_config_inodes_and_bytes_preserved','texture_tree_excluded_from_server_only',
                    'both_caches_returned_after_controlled_cleanup','closed_cache_credentials_removed'):
            require(case.get(key) is True, 'Saved-map preparation guarantee missing: ' + key)
        require(case.get('selected_map_id') == 5 and case.get('selected_port') == 7003
                and type(case.get('native_processes_started')) is int and case['native_processes_started'] == 0,
                'Saved-map selection or native-process claim differs')
        baseline = case.get('sql_baseline', {})
        require(baseline.get('sql_boundary') == BOUNDARY['saved_map_sql_boundary']
                and baseline.get('rows_unchanged') is True
                and baseline.get('identity_and_selected_powers_costume_preserved') is True
                and type(baseline.get('selected_row_reads')) is int and baseline['selected_row_reads'] > 0
                and re.fullmatch('[0-9a-f]{64}', str(baseline.get('selected_rows_sha256'))) is not None
                and baseline.get('saved_position') == dict(containerid=1, mapid=None, staticmapid=5,
                                                          posx=12.5, posy=-20.0, posz=40.25),
                'Controlled saved identity/position proof differs')
        inventories.append(case.get('excluded_client_texture_inventory', {}))
        require(type(case.get('actual_server_data_files')) is int and case['actual_server_data_files'] > 0,
                'Actual projected mirror inventory count missing')
        projection = case.get('source_projection', {})
        require(projection == {'policy': 'exact_native_excluded_texture_directory_v1',
            'excluded_top_level_directories': ['texture_library'],
            'native_consumer_sha256': PROJECTED_MAP,
            'native_source_path': 'MapServer/src/svr/svr_init.c',
            'native_source_sha256': PROJECTION_SOURCE, 'client_inputs_modified': False,
            'native_bytes_changed': False} and native['sha256'] == PROJECTED_MAP,
                'Exact server input projection missing')
        for key in ('kings','atlas_on_demand'):
            p = case.get(key, {})
            require(p.get('cache_reused') is (label == 'warm')
                    and p.get('graph_status') in ('installed_verified_graph','reused_verified_graph')
                    and p.get('native_mapserver') == native and p.get('native_dbserver') == full.ORIGINAL_DBSERVER,
                    'Saved-map native/cold/warm destination proof differs: '+key)
        k = case['kings']
        require(k.get('animation_count') == 5878 and k.get('graph_map_id') == 5
                and k.get('prepared_cache_status') in ('installed','preserved_existing_native_caches'),
                'Kings required graph/animation/cache proof missing')
    for inventory in inventories:
        require(type(inventory.get('files')) is int and inventory['files'] > 0
                and type(inventory.get('bytes')) is int and inventory['bytes'] > 0
                and inventory.get('scope') == 'host_input_inventory_not_native_reads',
                'Excluded texture inventory measurement missing')
    return value


def validate_proof(value):
    require(type(value) is dict and type(value.get('format')) is int and value.get('format') == 1 and value.get('status') == 'passed'
            and value.get('adapter_boundary') == BOUNDARY and value.get('source_pins') == source_pins()
            and leaf.canonical(value.get('frozen_workers')) == leaf.canonical(transport.WORKERS),
            'Saved-map full preparation adapter source/boundary differs')
    transport.worker_module('full_startup').validate_proof(value.get('full_startup'))
    validate_saved(value.get('saved_map_preparation'))
    require(value['full_startup']['packaged_guest_sources']
            == value['saved_map_preparation']['packaged_guest_sources'], 'Preparation phases used different APK guest sources')
    return value


def preflight(runtime_assets, payloads):
    with tempfile.TemporaryDirectory(prefix='coh-saved-map-proof-') as temporary:
        output = Path(temporary)/'proof.json'
        run = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--worker',
            '--runtime-assets', str(Path(runtime_assets).resolve()), '--payloads', str(Path(payloads).resolve()),
            '--output', str(output)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3600)
        require(run.returncode == 0, 'Actual saved-map preparation preflight failed:\n'+run.stderr[-24000:])
        require(output.is_file() and not output.is_symlink() and 0 < output.stat().st_size <= 24*1024**2,
                'Fresh bounded saved-map preparation output required')
        return validate_proof(json.loads(output.read_bytes()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('runtime-assets','payloads','output'): parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    proof = worker(args.runtime_assets, args.payloads) if args.worker else preflight(args.runtime_assets, args.payloads)
    require(not args.output.exists() and not args.output.is_symlink(), 'Fresh proof output required')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(transport.encoded(proof))


if __name__ == '__main__': main()
