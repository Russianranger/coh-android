"""Receipt guards and read-only SQL fixture; this suite never boots a native map.

Typed native admission itself is covered by its existing genuine-package tests.
These negative tests inject only its returned pin to isolate this adapter's new
claims. The full-assets worker runs independently during package qualification.
"""
import copy
import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'android/guest'), str(Path(__file__).parent)]
import qualify_saved_map_preparation as module
import local_character_server as server
import test_saved_map_startup as fixture


class SavedMapPreparationProofTests(unittest.TestCase):
    def proof(self):
        full = module.transport.worker_module('full_startup')
        native = {'bytes': 123, 'sha256': module.PROJECTED_MAP}
        sources = {'character_zoning.py': {'bytes': 1, 'sha256': 'a'*64}}
        inventory = {'files': 10, 'bytes': 100, 'scope': 'host_input_inventory_not_native_reads'}
        case = dict(actual_server_data_files=10,excluded_client_texture_inventory=copy.deepcopy(inventory),selected_map_id=5, selected_port=7003, native_processes_started=0,
            sql_baseline={'sql_boundary': module.BOUNDARY['saved_map_sql_boundary'],
                'rows_unchanged': True, 'identity_and_selected_powers_costume_preserved': True,
                'selected_row_reads': 7, 'selected_rows_sha256': 'b'*64,
                'saved_position': dict(containerid=1,mapid=None,staticmapid=5,posx=12.5,posy=-20.,posz=40.25)},
            source_projection={'policy': 'exact_native_excluded_texture_directory_v1',
                'excluded_top_level_directories': ['texture_library'],
                'native_consumer_sha256': module.PROJECTED_MAP,
                'native_source_path': 'MapServer/src/svr/svr_init.c',
                'native_source_sha256': module.PROJECTION_SOURCE,
                'client_inputs_modified': False, 'native_bytes_changed': False})
        for key in ('unassigned_prelogin_mapid_preserved','db_schema_only_before_destination',
                    'atlas_deferred_until_explicit_prepare','atlas_runtime_separate_from_live_db',
                    'db_schema_and_config_inodes_and_bytes_preserved','texture_tree_excluded_from_server_only',
                    'both_caches_returned_after_controlled_cleanup','closed_cache_credentials_removed'):
            case[key] = True
        cases = {}
        for label, reused in (('cold',False),('warm',True)):
            cases[label] = value = copy.deepcopy(case)
            for name in ('kings','atlas_on_demand'):
                value[name] = dict(cache_reused=reused,graph_status='installed_verified_graph',
                    native_mapserver=copy.deepcopy(native),native_dbserver=copy.deepcopy(full.ORIGINAL_DBSERVER))
            value['kings'].update(animation_count=5878,graph_map_id=5,prepared_cache_status='installed')
        return dict(format=1,status='passed',scope=module.SCOPE,asset_version='1.0.0',
            original_import=dict(files=full.COUNT,bytes=full.BYTES,all_leaf_sha256_checked=True,
                android_import_service_executed=False,inventory_sha256='c'*64,
                contract_sha256=hashlib.sha256(full.IMPORT_CONTRACT).hexdigest()),
            native_admission={'test_boundary': 'typed_admission_reader_mock_only'}, cases=cases,
            original_import_texture_inventory=copy.deepcopy(inventory),
            process_and_sql_boundary='not_executed',native_runtime_booted=False,
            physical_execution_validated=False,live_database_and_saved_character_executed=False,
            client_visual_readiness_boundary_stubbed=True,
            cache_cleanup_prerequisites_stubbed_no_native_processes_started=True,
            packaged_guest_sources=sources), native

    def validate(self, value, native):
        with patch.object(module.leaf,'validate_native_binding',return_value=native) as reader:
            result = module.validate_saved(value)
            reader.assert_called_once_with(value['native_admission'])
        return result

    def test_readonly_fixture_runs_production_identity_and_saved_map_baseline(self):
        f = fixture.SavedMapStartupTests(); self.addCleanup(f.doCleanups)
        value = f.instance(); del value.inventory
        verify = module.sql_fixture(value)
        value.capture_baseline()
        result = verify()
        self.assertTrue(value.creation_report['existing_character_verified'])
        self.assertEqual(value.active_map_id,5)
        self.assertEqual(result['saved_position']['mapid'],None)
        self.assertEqual(value.baseline_snapshot['login_count'],3)
        self.assertGreaterEqual(result['selected_row_reads'],7)
        self.assertFalse(value.creation_report['sql_game_mutations_performed'])
        value.ctx.start.assert_not_called()

    def test_readonly_fixture_rejects_mutations_and_unreviewed_queries(self):
        f = fixture.SavedMapStartupTests(); self.addCleanup(f.doCleanups)
        value = f.instance(); del value.inventory
        verify = module.sql_fixture(value); value.capture_baseline()
        before = copy.deepcopy(value.baseline_snapshot)
        for sql in ('UPDATE dbo.ents SET staticmapid=1;', 'DELETE FROM dbo.ents;', 'SELECT * FROM dbo.ents;'):
            with self.subTest(sql=sql), self.assertRaisesRegex(ValueError,'unreviewed SQL'):
                value.sql(sql,game=True)
        with self.assertRaisesRegex(ValueError,'unreviewed selected'):
            value.sql_rows('ents',('containerid','authid'),('containerid',),'containerid=1')
        self.assertEqual(value.baseline_snapshot,before); verify()

    def test_complete_receipt_remains_host_only_and_preserves_cold_warm(self):
        value,native = self.proof()
        self.assertIs(self.validate(value,native),value)
        for key in ('native_runtime_booted','physical_execution_validated','live_database_and_saved_character_executed'):
            invalid = copy.deepcopy(value); invalid[key]=True
            with self.subTest(key=key), self.assertRaisesRegex(ValueError,'cannot claim'):
                self.validate(invalid,native)
        invalid=copy.deepcopy(value); invalid['cases']['warm']['kings']['cache_reused']=False
        with self.assertRaisesRegex(ValueError,'cold/warm'): self.validate(invalid,native)
        invalid=copy.deepcopy(value); del invalid['cases']['cold']
        with self.assertRaisesRegex(ValueError,'cold/warm'): self.validate(invalid,native)

    def test_receipt_rejects_position_identity_or_unauthenticated_projection(self):
        value,native = self.proof()
        for path,replacement in ((('selected_map_id',),1), (('selected_port',),7002),
                (('sql_baseline','saved_position','mapid'),5),
                (('sql_baseline','saved_position','staticmapid'),1),
                (('sql_baseline','saved_position','posx'),0),
                (('source_projection','native_consumer_sha256'),'0'*64),
                (('source_projection','native_source_sha256'),'0'*64),
                (('source_projection','excluded_top_level_directories'),['texture_library','defs'])):
            invalid=copy.deepcopy(value); cursor=invalid['cases']['cold']
            for key in path[:-1]: cursor=cursor[key]
            cursor[path[-1]]=replacement
            with self.subTest(path=path),self.assertRaises(ValueError): self.validate(invalid,native)

    def test_receipt_requires_original_full_import_and_destination_native_dependencies(self):
        value,native=self.proof()
        for field,replacement in (('files',5000),('all_leaf_sha256_checked',False),('contract_sha256','0'*64)):
            invalid=copy.deepcopy(value); invalid['original_import'][field]=replacement
            with self.subTest(field=field),self.assertRaises(ValueError):self.validate(invalid,native)
        for destination in ('kings','atlas_on_demand'):
            invalid=copy.deepcopy(value)
            invalid['cases']['cold'][destination]['native_dbserver']={'bytes':1,'sha256':'0'*64}
            with self.subTest(destination=destination),self.assertRaises(ValueError): self.validate(invalid,native)
        invalid=copy.deepcopy(value); invalid['cases']['warm']['kings']['graph_map_id']=1
        with self.assertRaises(ValueError): self.validate(invalid,native)

    def test_receipt_requires_schema_preservation_and_controlled_owned_cleanup(self):
        value,native=self.proof()
        for key in ('db_schema_and_config_inodes_and_bytes_preserved','atlas_runtime_separate_from_live_db',
                    'atlas_deferred_until_explicit_prepare','both_caches_returned_after_controlled_cleanup',
                    'closed_cache_credentials_removed'):
            invalid=copy.deepcopy(value); invalid['cases']['warm'][key]=False
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate(invalid,native)
        invalid=copy.deepcopy(value); invalid['cases']['cold']['native_processes_started']=1
        with self.assertRaises(ValueError):self.validate(invalid,native)

    def test_wrapper_binds_sources_workers_and_explicit_historical_boundary(self):
        saved,native=self.proof()
        full=module.transport.worker_module('full_startup')
        wrapper=dict(format=1,status='passed',adapter_boundary=copy.deepcopy(module.BOUNDARY),
            full_startup={'packaged_guest_sources':saved['packaged_guest_sources']},saved_map_preparation=saved,
            source_pins=module.source_pins(),frozen_workers=copy.deepcopy(module.transport.WORKERS))
        # The historical full-startup reader has its separate frozen suite; here
        # isolate only wrapper claims and source attribution.
        with patch.object(full,'validate_proof',side_effect=lambda value:value), \
                patch.object(module.leaf,'validate_native_binding',return_value=native):
            self.assertIs(module.validate_proof(wrapper),wrapper)
            for name in ('adapter_boundary','source_pins','frozen_workers'):
                invalid=copy.deepcopy(wrapper); invalid[name]={}
                with self.subTest(name=name),self.assertRaises(ValueError):module.validate_proof(invalid)
            invalid=copy.deepcopy(wrapper); invalid['full_startup']['packaged_guest_sources']={}
            with self.assertRaisesRegex(ValueError,'different APK'):module.validate_proof(invalid)

    def test_truthy_format_and_missing_boundary_cannot_be_admitted(self):
        value,native=self.proof()
        for field,replacement in (('format',True),('process_and_sql_boundary','native_passed'),
                ('client_visual_readiness_boundary_stubbed',False),
                ('cache_cleanup_prerequisites_stubbed_no_native_processes_started',False)):
            invalid=copy.deepcopy(value); invalid[field]=replacement
            with self.subTest(field=field),self.assertRaises(ValueError):self.validate(invalid,native)


if __name__=='__main__':unittest.main()
