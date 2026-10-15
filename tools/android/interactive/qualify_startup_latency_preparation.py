#!/usr/bin/env python3
"""Fresh full-import preparation proof for saved Atlas and Kings startup.

The .35 adapter retains its original full Atlas control and saved Kings
cold/warm cases, with its controlled SQL fixture extended for the current
read-only 34-field enhancement baseline. This adapter adds direct Atlas cold/warm and the
on-demand Kings provider using the actual APK's guest modules and input bytes.
Only SQL, process creation, UDP availability, and native status/publication are
controlled boundaries. No native executable, PostgreSQL or physical game runs.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

import qualify_saved_map_preparation as legacy

ROOT = Path(__file__).resolve().parents[3]
leaf, transport, require = legacy.leaf, legacy.transport, legacy.require
SCOPE = 'actual_packaged_guest_saved_atlas_cold_warm_and_kings_provider'
SOURCE_FILES = ('tools/android/interactive/qualify_startup_latency_preparation.py',
                'tools/android/interactive/test_startup_latency_preparation_proof.py')
BOUNDARY = {
    'legacy_adapter_bytes_changed': True,
    'legacy_scenarios_preserved': True,
    'controlled_sql_fixture_revision': 2,
    'production_preparation_methods_patched': False,
    'production_command_and_readiness_methods_patched': False,
    'saved_map_sql_boundary': 'controlled_read_only_selected_rows_not_PostgreSQL',
    'process_creation_boundary': 'recorded_command_no_executable_started',
    'native_readiness_boundary': 'controlled_status_and_progress_bytes_not_native_execution',
    'character_world_boundary': 'controlled_connected_status_not_Game',
    'client_visual_readiness_boundary': 'controlled_host_facts_no_native_readiness',
    'cleanup_prerequisites': 'controlled_no_native_processes_started',
    'native_runtime_booted': False, 'physical_execution_validated': False,
}
GUARANTEES = (
    'minimal_db_before_selected_world', 'unassigned_prelogin_mapid_preserved',
    'only_selected_map_initially_launched_at_controlled_boundary',
    'initial_native_readiness_separate_from_character_connection',
    'db_schema_and_config_inodes_and_bytes_preserved',
    'destination_runtimes_separate_from_live_db',
    'texture_tree_excluded_from_servers_only',
    'identity_position_powers_costume_preserved',
    'both_caches_returned_after_controlled_cleanup', 'closed_cache_credentials_removed',
)


def source_pins():
    return {name: leaf.pin(ROOT/name) for name in SOURCE_FILES}


def map_status(zoning, map_id, ready=True):
    destination = zoning.MAPS[map_id]
    return f'{map_id} maps/City_Zones/{destination["world"]}/{destination["world"]}.txt ' + (
        f'S: 1 / 2 Ip: 127.0.0.1:{destination["port"]} Mem: 100\n' if ready
        else 'NotReady 1 (Not started) Info\n')


class ControlledNativeBoundary:
    """Produce attributed fixture publications; never run Wine or a native map."""
    class Child:
        def __init__(self, argv, pid):
            self.process = SimpleNamespace(args=argv, pid=pid, poll=lambda: None)
            self.output = bytearray(); self.overflow = False; self.started = time.monotonic()

    def __init__(self, instance, zoning):
        self.instance, self.zoning = instance, zoning
        self.launches, self.queries = [], []

    def publish(self, map_id, sequence):
        progress = self.zoning.character.progress
        # Real production parser consumes the controlled fixed-size publication.
        raw = progress.HEADER.pack(b'COHMAP1\0', 1, progress.RECORD_BYTES,
            800 + map_id, 900 + map_id, sequence, 37, sequence, sequence, 0, 37) + bytes(80)
        path = self.instance.runtime / f'character-zoning-{map_id}-progress.bin'
        path.write_bytes(raw + bytes(progress.MAPPING_BYTES-progress.RECORD_BYTES))

    def start(self, label, argv, **kwargs):
        value, zoning = self.instance, self.zoning
        require(label.startswith('local-character-zoning-') and argv[:1] == ['/usr/bin/env']
                and set(kwargs) == {'env'}, 'Unreviewed native boundary call')
        map_id = int(argv[argv.index('-map_id')+1]); destination = zoning.MAPS[map_id]
        runtime = value.atlas_map_runtime if map_id == 1 else value.kings_row_runtime
        require(label == f'local-character-zoning-{map_id}'
                and argv[1] == '--chdir=' + str(runtime)
                and zoning.base.windows_path(runtime/'MapServer.exe') in argv
                and argv[argv.index('-udp')+1] == str(destination['port'])
                and argv[argv.index('-db')+1] == '127.0.0.1'
                and argv[argv.index('-idleExitTimeout')+1] == '0'
                and '-nosharedmemory' in argv and '-donotautogroup' in argv
                and kwargs['env'][zoning.monorail_events.ENVIRONMENT] == value.owner.args.session_id
                and kwargs['env'][zoning.character.evidence.GAME_LOOPBACK_ENV] == '1',
                'Selected native command/runtime/session ownership differs')
        self.publish(map_id, 2)
        self.launches.append({'map_id': map_id, 'port': destination['port'], 'world': destination['world'],
            'runtime_role': 'private_destination_' + str(map_id), 'loopback_only': True,
            'current_session_owned': True, 'native_executable': leaf.pin(runtime/'MapServer.exe')})
        return self.Child(argv, 10000+map_id)

    def query(self, argv, label):
        require(len(argv) == 3 and argv[:2] == ['-getstatus','1'], 'Unreviewed native status boundary')
        map_id = int(argv[2]); require(map_id in (1,5), 'Unreviewed native status destination')
        baseline = label.endswith('-baseline')
        require(baseline or label in ('zoning-reopen-ready','fixture-on-demand-ready'), 'Unreviewed query label')
        self.queries.append({'map_id': map_id, 'ready': not baseline})
        if not baseline: self.publish(map_id, 4)
        return map_status(self.zoning, map_id, not baseline)


def schema_snapshot(instance):
    return {name: ((instance.runtime/name).stat().st_ino, leaf.pin(instance.runtime/name))
            for name in instance.schema['files']}


def direct_atlas_worker(full, runtime_assets, payloads):
    import client_startup_diagnostic as client
    import character_creation_diagnostic as creation
    import local_character_server as server
    import character_zoning as zoning
    import character_avatar_assets as avatar
    import atlas_world_assets as world
    require(all(Path(m.__file__).resolve().parent == runtime_assets for m in
        (client, creation, server, zoning, avatar, world)), 'Direct Atlas guest import shadowed')
    with tempfile.TemporaryDirectory(prefix='coh-direct-atlas-assets-') as temporary:
        root = Path(temporary); assets = legacy.setup_assets(full, runtime_assets, payloads, root)
        hashes, data, imported = full.verify_inputs_before_import(client, assets, payloads)
        owned = root/'owned'; owned.mkdir(); state = root/'state'; state.mkdir()
        ctx = full.Context(); ctx.secrets = []
        identity = client.import_identity(data)
        work, receipt = client.prepare_worktree(owned, data, assets, identity, ctx)
        require(receipt['reused'] is False and receipt['input_files'] == full.COUNT,
                'Direct Atlas omitted original imported input bytes')
        ctx.report.update(client_worktree=receipt, asset_sha256=hashes)
        ctx.report['character_avatar_supplement'] = avatar.install(work, assets, ctx)
        ctx.report['atlas_world_supplement'] = world.install(work, assets, ctx)
        cases = {}; admission = None
        for label, session in (('cold','5'*32),('warm','6'*32)):
            owner = SimpleNamespace(root=owned, work=work, ctx=ctx, wine_env={},
                args=SimpleNamespace(assets=assets, game_data=data, session_id=session, state=state,
                                     wine='/controlled/no-wine-execution'),
                cleanup_status={'wine_prefix_stopped': True, 'owned_processes_reaped': True})
            instance = zoning.LocalCharacterZoningServer(owner)
            instance.overlap_client_initialization = True
            instance.payloads(); verify_sql = legacy.sql_fixture(instance, map_id=1)
            instance.prepare_runtime()
            require(instance.active_map_id == instance.startup_preparation_map_id == 1
                    and instance.atlas_preparation_deferred is True and not hasattr(instance,'data_cache')
                    and not instance.maps and '1' not in instance.creation_report.get('map_startup_observation',{})
                    and not (instance.runtime/'data/maps').exists()
                    and not (instance.runtime/'data/texture_library').exists(),
                    'Direct Atlas bulk world was not deferred behind minimal Db preparation')
            current = leaf.native_binding(instance.runtime, instance.map_package)
            if admission is None: admission = current
            require(leaf.canonical(current) == leaf.canonical(admission), 'Native admission changed between cold/warm')
            config = instance.runtime/'data/server/db/servers.cfg'; instance.config = config
            config_before = config.read_bytes(); db_before = schema_snapshot(instance)
            # Prepare actual visual inputs using the same explicit controlled
            # readiness boundary as the retained .35 full-import worker.
            instance.report['server_ready'] = instance.creation_report['map_ready'] = True
            visual = creation.CharacterCreationDiagnostic.__new__(creation.CharacterCreationDiagnostic)
            visual.work, visual.ctx, visual.local_server, visual.args = work, ctx, instance, owner.args
            visual.prepare_client_visual_inputs(); instance.creation_report['map_ready'] = False
            textures = legacy.texture_inventory(work/'data')
            native = ControlledNativeBoundary(instance, zoning)
            ctx.start = native.start; instance.query = native.query
            with patch.object(zoning.character.game, 'check_game_port'):
                instance.start_map()
                require(len(native.launches) == 1 and set(instance.maps) == {1}
                        and instance.client_startup_assets_allowed() is True
                        and not instance.zoning_report['saved_startup']['native_ready_verified']
                        and not instance.zoning_report['saved_startup']['character_world_entry_verified'],
                        'Process launch alone incorrectly became native/world readiness')
                require(instance.poll_initial_map_startup() is True
                        and instance.zoning_report['saved_startup']['native_ready_verified'] is True
                        and not instance.zoning_report['saved_startup']['character_world_entry_verified'],
                        'Native readiness did not remain independent of character entry')
                status = dict(loaded=True, connected=True, in_map_transfer=False, map_id=1,static_map_id=1,address='127.0.0.1')
                require(instance.connected_status(status) is True, 'Controlled Atlas connection rejected')
                instance.connection_metadata()
                require(instance.zoning_report['saved_startup']['character_world_entry_verified'] is True,
                        'Independent controlled Atlas connection missing')
                atlas = instance.atlas_map_runtime
                require(atlas != instance.runtime and instance.prepare_atlas_runtime() == atlas,
                        'Direct Atlas provider is not independently owned/reused')
                atlas_cache = copy.deepcopy(instance.data_cache.summary)
                atlas_graph = copy.deepcopy(instance.creation_report['atlas_beacon_graph'])
                atlas_files = instance.creation_report['private_map_data']['files']
                initial = copy.deepcopy(native.launches)
                before_kings = verify_sql()
                instance._spawn_map(5)
                kr = instance.kings_row_runtime; kings = instance.creation_report['kings_row_preparation']
                before = instance._map_progress(5)
                sample = zoning.parse_map_status(native.query(['-getstatus','1','5'],'fixture-on-demand-ready'),5)
                after = instance._map_progress(5)
                require(instance.live_progress(before) and zoning.ready(sample,5) and instance.live_progress(after),
                        'Controlled destination native readiness lacks independent evidence')
                zoning.character.progress.compare_records(after,before)
                instance.maps[5]['ready'] = True; instance._activate(5)
                require(instance.connected_status(dict(loaded=True,connected=True,in_map_transfer=False,
                        map_id=5,static_map_id=5,address='127.0.0.1')) is True, 'Controlled Kings connection rejected')
            require(schema_snapshot(instance) == db_before and config.read_bytes() == config_before
                    and (atlas/'data/server/db/servers.cfg').read_bytes() == config_before
                    and kr != instance.runtime and kr != atlas
                    and not (atlas/'data/texture_library').exists() and not (kr/'data/texture_library').exists()
                    and leaf.pin(work/'data/bin/fxinfo.bin') == leaf.CLIENT_FULL_FX,
                    'Destination preparation changed live Db schema/config or client input ownership')
            for runtime in (atlas,kr):
                require(leaf.pin(runtime/'MapServer.exe') == admission['authenticated_mapserver']
                        and leaf.pin(runtime/'DbServer.exe') == full.ORIGINAL_DBSERVER,
                        'Destination native dependencies differ')
            require(leaf.pin(instance.runtime/'DbServer.exe') == full.ATLAS_MANUAL_DBSERVER,
                    'Minimal Db native executable changed')
            require(atlas_cache['reused'] is (label=='warm')
                    and kings['server_data_cache']['reused'] is (label=='warm'), 'Cold/warm provider reuse differs')
            # Assert the actual optimization on original assets, independently
            # of fixture-only hash counters. Graph reuse never claims native I/O
            # or elapsed device savings; only exact host byte-proof work.
            graph = kings['graph']
            require((label == 'cold' and graph.get('input_full_byte_proof_reused_files',0) > 0
                        and graph.get('input_full_byte_proof_reused_bytes',0) > 0
                        and graph.get('input_full_byte_proof_reuse_policy') == 'exact_full_byte_proved_owned_immutable_provider')
                    or (label == 'warm' and graph.get('status') == 'reused_verified_graph'
                        and graph.get('input_payload_bytes_hashed') == 0),
                    'Actual destination did not reuse its authenticated collision evidence')
            case = {'selected_map_id':1,'selected_port':7001,'selected_world':'City_01_01',
                'actual_native_processes_started':0,'controlled_initial_launches':initial,
                'controlled_total_launches':native.launches,'sql_baseline':before_kings,
                'excluded_client_texture_inventory':textures,'actual_server_data_files':atlas_files,
                'atlas':{'cache_reused':atlas_cache['reused'],'graph_status':atlas_graph['status'],
                    'native_mapserver':leaf.pin(atlas/'MapServer.exe'),'native_dbserver':leaf.pin(atlas/'DbServer.exe')},
                'kings_on_demand':{'cache_reused':kings['server_data_cache']['reused'],
                    'graph_status':kings['graph']['status'],'graph_map_id':kings['graph']['map_id'],
                    'animation_count':kings['animation']['pigg']['animation_count'],
                    'input_full_byte_proof_reused_files':graph['input_full_byte_proof_reused_files'],
                    'input_full_byte_proof_reused_bytes':graph['input_full_byte_proof_reused_bytes'],
                    'input_full_byte_proof_reuse_policy':graph['input_full_byte_proof_reuse_policy'],
                    'input_payload_bytes_hashed':graph['input_payload_bytes_hashed'],
                    'native_mapserver':leaf.pin(kr/'MapServer.exe'),'native_dbserver':leaf.pin(kr/'DbServer.exe')},
                'native_readiness_scope':BOUNDARY['native_readiness_boundary'],
                'world_entry_scope':BOUNDARY['character_world_boundary']}
            instance.cleanup_config()
            require(instance.data_cache.summary.get('returned_after_owned_cleanup') is True
                    and instance.kings_row_data_cache.summary.get('returned_after_owned_cleanup') is True
                    and not (instance.data_cache.path/'data/server/db/servers.cfg').exists()
                    and not (instance.kings_row_data_cache.path/'data/server/db/servers.cfg').exists(),
                    'Both providers were not closed without session credentials')
            verify_sql(); case.update({name:True for name in GUARANTEES}); cases[label] = case
            if label == 'cold':
                next_work, receipt = client.prepare_worktree(owned,data,assets,identity,ctx)
                require(next_work == work and receipt['reused'] is True, 'Warm client checkout failed')
                ctx.report['client_worktree'] = receipt
        return {'format':1,'status':'passed','scope':SCOPE,'asset_version':'1.0.0',
            'original_import':imported,'native_admission':admission,'cases':cases,
            'boundary':copy.deepcopy(BOUNDARY),'native_runtime_booted':False,
            'physical_execution_validated':False,'live_database_and_saved_character_executed':False,
            'packaged_guest_sources':{p.name:leaf.pin(p) for p in sorted(runtime_assets.glob('*.py'))}}


def validate_direct(value):
    full = transport.worker_module('full_startup')
    require(type(value) is dict and type(value.get('format')) is int and value['format']==1
            and value.get('status')=='passed' and value.get('scope')==SCOPE
            and value.get('asset_version')=='1.0.0' and value.get('boundary')==BOUNDARY,
            'Direct Atlas preparation scope/boundary differs')
    for name in ('native_runtime_booted','physical_execution_validated','live_database_and_saved_character_executed'):
        require(value.get(name) is False, 'Controlled preparation cannot claim execution: '+name)
    native = leaf.validate_native_binding(value.get('native_admission'))
    imported=value.get('original_import',{})
    require(imported.get('files')==full.COUNT and imported.get('bytes')==full.BYTES
            and imported.get('all_leaf_sha256_checked') is True
            and imported.get('android_import_service_executed') is False
            and imported.get('contract_sha256')==hashlib.sha256(full.IMPORT_CONTRACT).hexdigest()
            and re.fullmatch('[0-9a-f]{64}',str(imported.get('inventory_sha256'))) is not None,
            'Direct Atlas original imported bytes not proved')
    require(set(value.get('cases',{}))=={'cold','warm'}, 'Direct Atlas cold/warm cases missing')
    for label,case in value['cases'].items():
        require(all(case.get(k) is True for k in GUARANTEES), 'Direct Atlas preservation guarantee missing')
        require(case.get('selected_map_id')==1 and case.get('selected_port')==7001
                and case.get('selected_world')=='City_01_01'
                and type(case.get('actual_native_processes_started')) is int
                and case['actual_native_processes_started']==0
                and case.get('native_readiness_scope')==BOUNDARY['native_readiness_boundary']
                and case.get('world_entry_scope')==BOUNDARY['character_world_boundary'],
                'Direct Atlas selected world or execution scope differs')
        baseline=case.get('sql_baseline',{})
        require(baseline.get('sql_boundary')==BOUNDARY['saved_map_sql_boundary']
                and baseline.get('rows_unchanged') is True
                and baseline.get('identity_and_selected_powers_costume_preserved') is True
                and type(baseline.get('selected_row_reads')) is int and baseline['selected_row_reads']>0
                and re.fullmatch('[0-9a-f]{64}',str(baseline.get('selected_rows_sha256'))) is not None
                and baseline.get('saved_position')==dict(containerid=1,mapid=None,staticmapid=1,posx=12.5,posy=-20.,posz=40.25),
                'Direct Atlas controlled identity/location differs')
        legacy.validate_enhancement_fixture(baseline.get('enhancement_fixture'))
        expected=[]
        for map_id,port,world in ((1,7001,'City_01_01'),(5,7003,'City_01_02')):
            expected.append(dict(map_id=map_id,port=port,world=world,runtime_role='private_destination_'+str(map_id),
                loopback_only=True,current_session_owned=True,native_executable=native))
        require(case.get('controlled_initial_launches')==expected[:1]
                and case.get('controlled_total_launches')==expected, 'Selected-only native command proof differs')
        for name in ('atlas','kings_on_demand'):
            row=case.get(name,{})
            require(row.get('cache_reused') is (label=='warm')
                    and row.get('graph_status') in ('installed_verified_graph','reused_verified_graph')
                    and row.get('native_mapserver')==native and row.get('native_dbserver')==full.ORIGINAL_DBSERVER,
                    'Direct Atlas destination asset/cache/native proof differs')
        require(case['kings_on_demand'].get('graph_map_id')==5
                and case['kings_on_demand'].get('animation_count')==5878,
                'On-demand Kings graph/animation proof missing')
        graph=case['kings_on_demand']
        require(all(type(graph.get(k)) is int and graph[k]>=0 for k in (
                    'input_full_byte_proof_reused_files','input_full_byte_proof_reused_bytes','input_payload_bytes_hashed'))
                and ((label=='cold' and graph['input_full_byte_proof_reused_files']>0
                    and graph['input_full_byte_proof_reused_bytes']>0
                    and graph.get('input_full_byte_proof_reuse_policy')=='exact_full_byte_proved_owned_immutable_provider')
                    or (label=='warm' and graph['graph_status']=='reused_verified_graph'
                        and graph['input_payload_bytes_hashed']==0
                        and graph.get('input_full_byte_proof_reuse_policy')=='unchanged_destination_full_byte_graph_receipt')),
                'Actual collision proof reuse counters missing or not qualified')
        inventory=case.get('excluded_client_texture_inventory',{})
        require(type(inventory.get('files')) is int and inventory['files']>0
                and type(inventory.get('bytes')) is int and inventory['bytes']>0
                and inventory.get('scope')=='host_input_inventory_not_native_reads'
                and type(case.get('actual_server_data_files')) is int and case['actual_server_data_files']>0,
                'Actual full asset input/mirror inventories missing')
    return value


def validate_proof(value):
    require(type(value) is dict and type(value.get('format')) is int and value['format']==1
            and value.get('status')=='passed' and value.get('source_pins')==source_pins()
            and value.get('adapter_boundary')==BOUNDARY, 'Startup latency adapter source/boundary differs')
    retained=value.get('retained_saved_map_adapter')
    legacy.validate_proof(retained)
    require(value.get('full_startup')==retained['full_startup']
            and value.get('saved_map_preparation')==retained['saved_map_preparation'],
            'Retained .35 preparation proof was replaced')
    validate_direct(value.get('direct_atlas_preparation'))
    require(value['direct_atlas_preparation']['packaged_guest_sources']
            ==value['saved_map_preparation']['packaged_guest_sources'], 'Preparation phases used different APK guest sources')
    return value


def worker(runtime_assets,payloads):
    runtime_assets,payloads=Path(runtime_assets).resolve(),Path(payloads).resolve()
    retained=legacy.worker(runtime_assets,payloads)
    direct=direct_atlas_worker(transport.worker_module('full_startup'),runtime_assets,payloads)
    return validate_proof(dict(format=1,status='passed',source_pins=source_pins(),adapter_boundary=copy.deepcopy(BOUNDARY),
        full_startup=retained['full_startup'],saved_map_preparation=retained['saved_map_preparation'],
        retained_saved_map_adapter=retained,direct_atlas_preparation=direct))


def preflight(runtime_assets,payloads):
    with tempfile.TemporaryDirectory(prefix='coh-startup-latency-proof-') as temporary:
        output=Path(temporary)/'proof.json'
        run=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',
            '--runtime-assets',str(Path(runtime_assets).resolve()),'--payloads',str(Path(payloads).resolve()),
            '--output',str(output)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=5400)
        require(run.returncode==0,'Actual startup latency preparation failed:\n'+run.stderr[-24000:])
        require(output.is_file() and not output.is_symlink() and 0<output.stat().st_size<=32*1024**2,
                'Fresh bounded startup latency proof required')
        return validate_proof(json.loads(output.read_bytes()))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('runtime-assets','payloads','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    proof=worker(args.runtime_assets,args.payloads) if args.worker else preflight(args.runtime_assets,args.payloads)
    require(not args.output.exists() and not args.output.is_symlink(),'Fresh proof output required')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(transport.encoded(proof))


if __name__=='__main__':main()
