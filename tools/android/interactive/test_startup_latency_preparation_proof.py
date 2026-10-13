"""Source/claim guards and adverse Atlas production-readiness boundaries.

The actual full-input worker runs independently in package qualification. These
small fixtures test rejected ownership/assets/status/deadlines without claiming
that a host-controlled status is an actual native or physical world entry.
"""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'android/guest'),str(Path(__file__).parent)]
import qualify_startup_latency_preparation as module
import test_saved_map_preparation_proof as prior_proof
import test_saved_map_startup as startup_fixture
import character_zoning as zoning
import local_character_server as server


class StartupLatencyPreparationProofTests(unittest.TestCase):
    def receipt(self):
        old,native=prior_proof.SavedMapPreparationProofTests().proof()
        result={k:copy.deepcopy(old[k]) for k in ('format','status','asset_version','original_import',
            'native_admission','packaged_guest_sources','native_runtime_booted','physical_execution_validated',
            'live_database_and_saved_character_executed')}
        result.update(scope=module.SCOPE,boundary=copy.deepcopy(module.BOUNDARY),cases={})
        for label in ('cold','warm'):
            prior=old['cases'][label]
            launches=[dict(map_id=i,port=p,world=w,runtime_role='private_destination_'+str(i),
                loopback_only=True,current_session_owned=True,native_executable=native)
                for i,p,w in ((1,7001,'City_01_01'),(5,7003,'City_01_02'))]
            case={k:True for k in module.GUARANTEES}
            baseline=copy.deepcopy(prior['sql_baseline']);baseline['saved_position']['staticmapid']=1
            case.update(selected_map_id=1,selected_port=7001,selected_world='City_01_01',
                actual_native_processes_started=0,controlled_initial_launches=copy.deepcopy(launches[:1]),
                controlled_total_launches=copy.deepcopy(launches),sql_baseline=baseline,
                atlas=prior['atlas_on_demand'],kings_on_demand=prior['kings'],
                excluded_client_texture_inventory=prior['excluded_client_texture_inventory'],
                actual_server_data_files=prior['actual_server_data_files'],
                native_readiness_scope=module.BOUNDARY['native_readiness_boundary'],
                world_entry_scope=module.BOUNDARY['character_world_boundary'])
            case['kings_on_demand'].update(graph_status=('installed_verified_graph' if label=='cold' else 'reused_verified_graph'),
                input_full_byte_proof_reused_files=100 if label=='cold' else 0,
                input_full_byte_proof_reused_bytes=1000 if label=='cold' else 0,
                input_payload_bytes_hashed=100 if label=='cold' else 0,
                input_full_byte_proof_reuse_policy=('exact_full_byte_proved_owned_immutable_provider'
                    if label=='cold' else 'unchanged_destination_full_byte_graph_receipt'))
            result['cases'][label]=case
        return result,native

    def validate(self,value,native):
        with patch.object(module.leaf,'validate_native_binding',return_value=native):
            return module.validate_direct(value)

    def test_complete_host_receipt_is_accepted_but_never_as_native_execution(self):
        value,native=self.receipt();self.assertIs(self.validate(value,native),value)
        for key in ('native_runtime_booted','physical_execution_validated','live_database_and_saved_character_executed'):
            bad=copy.deepcopy(value);bad[key]=True
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate(bad,native)
        for key in ('native_readiness_scope','world_entry_scope'):
            bad=copy.deepcopy(value);bad['cases']['cold'][key]='physical_passed'
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate(bad,native)

    def test_receipt_rejects_wrong_saved_map_identity_location_or_extra_initial_process(self):
        value,native=self.receipt()
        for key,replacement in (('selected_map_id',5),('selected_port',7003),('selected_world','City_01_02'),
                ('actual_native_processes_started',True),('actual_native_processes_started',1)):
            bad=copy.deepcopy(value);bad['cases']['cold'][key]=replacement
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate(bad,native)
        for key,replacement in (('staticmapid',5),('mapid',1),('posx',0)):
            bad=copy.deepcopy(value);bad['cases']['warm']['sql_baseline']['saved_position'][key]=replacement
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate(bad,native)
        bad=copy.deepcopy(value);bad['cases']['cold']['controlled_initial_launches']=bad['cases']['cold']['controlled_total_launches']
        with self.assertRaisesRegex(ValueError,'Selected-only'):self.validate(bad,native)

    def test_receipt_rejects_missing_assets_cache_proof_and_live_database_mutation(self):
        value,native=self.receipt()
        for name in ('atlas','kings_on_demand'):
            for key,replacement in (('cache_reused',False),('graph_status','missing'),('native_mapserver',{})):
                bad=copy.deepcopy(value);bad['cases']['warm'][name][key]=replacement
                with self.subTest(name=name,key=key),self.assertRaises(ValueError):self.validate(bad,native)
        for key in module.GUARANTEES:
            bad=copy.deepcopy(value);bad['cases']['cold'][key]=False
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate(bad,native)
        bad=copy.deepcopy(value);bad['original_import']['all_leaf_sha256_checked']=False
        with self.assertRaises(ValueError):self.validate(bad,native)
        bad=copy.deepcopy(value);del bad['cases']['warm']
        with self.assertRaises(ValueError):self.validate(bad,native)

    def test_receipt_rejects_unexecuted_collision_reuse_or_fabricated_counters(self):
        value,native=self.receipt()
        for label,key,replacement in (
                ('cold','input_full_byte_proof_reused_files',0),
                ('cold','input_full_byte_proof_reused_bytes',False),
                ('cold','input_full_byte_proof_reuse_policy','unproved_directory_anchors'),
                ('warm','input_payload_bytes_hashed',1),
                ('warm','input_full_byte_proof_reuse_policy','unverified_warm_cache')):
            bad=copy.deepcopy(value);bad['cases'][label]['kings_on_demand'][key]=replacement
            with self.subTest(label=label,key=key),self.assertRaisesRegex(ValueError,'collision proof reuse'):
                self.validate(bad,native)

    def test_wrapper_preserves_legacy_proof_and_same_apk_guest_source(self):
        direct,native=self.receipt()
        retained={'full_startup':{'packaged_guest_sources':direct['packaged_guest_sources']},
                  'saved_map_preparation':{'packaged_guest_sources':direct['packaged_guest_sources']}}
        value=dict(format=1,status='passed',source_pins=module.source_pins(),
            adapter_boundary=copy.deepcopy(module.BOUNDARY),retained_saved_map_adapter=retained,
            full_startup=retained['full_startup'],saved_map_preparation=retained['saved_map_preparation'],
            direct_atlas_preparation=direct)
        with patch.object(module.legacy,'validate_proof',side_effect=lambda x:x), \
                patch.object(module.leaf,'validate_native_binding',return_value=native):
            self.assertIs(module.validate_proof(value),value)
            for key in ('adapter_boundary','source_pins','full_startup','saved_map_preparation'):
                bad=copy.deepcopy(value);bad[key]={}
                with self.subTest(key=key),self.assertRaises(ValueError):module.validate_proof(bad)
            bad=copy.deepcopy(value);bad['direct_atlas_preparation']['packaged_guest_sources']={}
            with self.assertRaisesRegex(ValueError,'different APK'):module.validate_proof(bad)

    def atlas(self):
        fixture=startup_fixture.SavedMapStartupTests();self.addCleanup(fixture.doCleanups)
        value=fixture.instance(map_id=1);fixture.baseline(value)
        value.startup_preparation_map_id=1;value.overlap_client_initialization=True
        target=value.runtime.with_name('atlas-map');target.mkdir()
        (target/'MapServer.exe').write_bytes(b'host-controlled-command-boundary-only')
        value.atlas_map_runtime=target;value.atlas_runtime_prepared=True;value.atlas_preparation_deferred=True
        value.creation_report['atlas_beacon_graph']={'status':'installed_verified_graph',
            'map':'maps/city_zones/city_01_01/city_01_01.txt'}
        value.prepare_atlas_runtime=Mock(return_value=target)
        native=module.ControlledNativeBoundary(value,zoning)
        value.ctx.start=Mock(side_effect=native.start);value.query=Mock(side_effect=native.query)
        return fixture,value,native

    def test_atlas_commands_progress_and_world_entry_are_independent_production_gates(self):
        fixture,value,native=self.atlas()
        with patch.object(zoning.character.game,'check_game_port') as port, \
                patch.object(zoning.time,'monotonic',return_value=100):
            value.start_map()
            self.assertEqual([x['map_id'] for x in native.launches],[1])
            self.assertTrue(value.client_startup_assets_allowed())
            self.assertFalse(value.zoning_report['saved_startup']['native_ready_verified'])
            self.assertTrue(value.poll_initial_map_startup())
        port.assert_called_once_with(7001,zoning.socket.SOCK_DGRAM)
        saved=value.zoning_report['saved_startup']
        self.assertTrue(saved['native_ready_verified']);self.assertFalse(saved['character_world_entry_verified'])
        self.assertFalse(value.connected_status(dict(loaded=True,connected=False,in_map_transfer=False,
            map_id=1,static_map_id=1,address='127.0.0.1')))
        self.assertTrue(value.connected_status(dict(loaded=True,connected=True,in_map_transfer=False,
            map_id=1,static_map_id=1,address='127.0.0.1')))
        value.connection_metadata();self.assertTrue(saved['character_world_entry_verified'])
        self.assertEqual(fixture.saved_position['staticmapid'],1)
        self.assertIsNone(fixture.saved_position['mapid'])

    def test_wrong_atlas_world_port_or_unowned_existing_map_never_grants_readiness(self):
        for reply in (module.map_status(zoning,1).replace('City_01_01','City_01_02'),
                module.map_status(zoning,1).replace(':7001',':7003')):
            fixture,value,native=self.atlas()
            with patch.object(zoning.character.game,'check_game_port'), \
                    patch.object(zoning.time,'monotonic',return_value=100):
                value.start_map();value.query=Mock(return_value=reply)
                with self.subTest(reply=reply),self.assertRaises(server.base.DiagnosticError):value.poll_initial_map_startup()
            self.assertFalse(value.zoning_report['saved_startup']['native_ready_verified'])
            self.assertEqual(fixture.saved_position['staticmapid'],1)
        fixture,value,native=self.atlas();value.query=Mock(return_value=module.map_status(zoning,1))
        with self.assertRaises(server.base.DiagnosticError):value.start_map()
        value.ctx.start.assert_not_called()

    def test_missing_graph_live_process_and_timeout_do_not_change_saved_destination(self):
        for broken in ('graph','process','timeout'):
            fixture,value,native=self.atlas()
            with patch.object(zoning.character.game,'check_game_port'), \
                    patch.object(zoning.time,'monotonic',return_value=100):
                value.start_map()
                if broken=='graph':value.creation_report['atlas_beacon_graph']['status']='missing'
                elif broken=='process':value.maps[1]['process'].process.poll=lambda:1
                else:value.initial_map_startup['deadline']=99
                action=value.poll_initial_map_startup if broken=='timeout' else value.client_startup_assets_allowed
                with self.subTest(broken=broken),self.assertRaises(server.base.DiagnosticError):action()
            self.assertEqual(fixture.saved_position['staticmapid'],1)
            self.assertFalse(value.zoning_report['saved_startup']['native_ready_verified'])
            self.assertFalse(value.creation_report['sql_game_mutations_performed'])

    def test_readonly_atlas_baseline_refuses_sql_writes_and_other_characters(self):
        fixture=startup_fixture.SavedMapStartupTests();self.addCleanup(fixture.doCleanups)
        value=fixture.instance(map_id=1);del value.inventory
        verify=module.legacy.sql_fixture(value,map_id=1);value.capture_baseline()
        self.assertTrue(verify()['rows_unchanged'])
        with self.assertRaisesRegex(ValueError,'unreviewed SQL'):value.sql('UPDATE dbo.ents SET staticmapid=5;',game=True)
        with self.assertRaisesRegex(ValueError,'identity differs'):
            value.sql_rows('ents',('containerid','mapid','staticmapid','posx','posy','posz'),('containerid',),'containerid=2')
        self.assertEqual(verify()['saved_position']['staticmapid'],1)


if __name__=='__main__':unittest.main()
