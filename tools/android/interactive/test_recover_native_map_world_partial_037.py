"""Refusal controls and authentic cancelled-case recovery; no native replay."""
import copy
import os
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import recover_native_map_world_partial_037 as partial


class ActualPartialRecovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value=os.environ.get('COH_WORLD_PARTIAL_TEST_ARCHIVE')
        if not value:raise RuntimeError('Explicit authenticated original partial artifact required for these tests')
        cls.path=Path(value);cls.recovered,cls.values=partial.recover(cls.path)

    def test_exact_original_nine_frontier_and_cancelled_status_retained(self):
        self.assertEqual(len(self.recovered['recovered_individual_cases']),9)
        self.assertEqual(self.recovered['remaining_fresh_native_cases'],7)
        self.assertEqual(self.recovered['original_run_result'],'cancelled')
        self.assertFalse(self.recovered['original_global_cleanup_verified'])
        self.assertFalse(self.recovered['shipping_allowed'])

    def test_selected_pool_requires_complete_typed_supported_selectors(self):
        self.assertEqual(partial.world.selected_pool(SimpleNamespace(pool_map_id=5,pool_fx_variant='server_only')),
                         {'map_id':5,'fx_variant':'server_only'})
        for map_id,variant in ((5,None),(None,'full'),(True,'full'),(9,'full'),(5,'unknown')):
            with self.subTest(map_id=map_id,variant=variant),self.assertRaises(ValueError):
                partial.world.selected_pool(SimpleNamespace(pool_map_id=map_id,pool_fx_variant=variant))

    def test_namespace_summary_retains_scope_without_full_ledger_or_native_claim(self):
        value={'format':'closed','runtime':'owned','root_identity':{},'namespace_sha256':'a'*64,
               'owned_error_log':None,'full_namespace_verified':True,
               'content_schema_native_SQL_gates_supplied':False,'unknown_leaf_deletion_allowed':False,
               'shipping_allowed':False,'files':{'x':{'bytes':12}},'directories':{'d':{}}}
        summary=partial.world.namespace_summary(value)
        self.assertEqual(summary['ordinary_file_bytes'],12)
        self.assertNotIn('files',summary)
        self.assertFalse(summary['content_schema_native_SQL_gates_supplied'])
        self.assertFalse(summary['shipping_allowed'])

    def test_original04b_execution_is_not_relabelled3a(self):
        first=self.recovered['recovered_individual_cases'][0]
        self.assertEqual(first['recovered_individual_case_authority']['native_execution_source'],
                         '04b7a623ef21d7ad48774a58b3122c69ae07f46b')

    def test_wrong_whole_zip_pin_refused(self):
        with patch.object(partial.world,'pin',return_value={'bytes':1,'sha256':'0'*64}):
            with self.assertRaises(ValueError):partial.read_archive(self.path)

    def edited_case(self,field,value,label='1-server_only-baseline-forward'):
        values=dict(self.values);import json
        record=json.loads(values[label+'/phase.json']);record[field]=value
        values[label+'/phase.json']=json.dumps(record).encode();return values,label

    def test_lost_cleanup_SQL_status_or_native_identity_refused(self):
        for field,value in (('owned_cleanup_verified',False),('synthetic_row_unchanged',False),
                            ('actual_native',{'bytes':1,'sha256':'0'*64})):
            values,label=self.edited_case(field,value)
            with self.subTest(field=field),self.assertRaises(ValueError):partial.audit_case(values,label)

    def test_cache_date_or_source_delta_mutation_refused(self):
        original=self.recovered['recovered_individual_cases'][1]
        dates=copy.deepcopy(original['cache_dates_after']);name=next(iter(dates));dates[name]+=100
        values,label=self.edited_case('cache_dates_after',dates)
        with self.assertRaises(ValueError):partial.audit_case(values,label)
        values,label=self.edited_case('original_source_delta',{'added':{'unknown':{}},'removed':{},'changed':{}})
        with self.assertRaises(ValueError):partial.audit_case(values,label)

    def test_missing_original_raw_stdout_refused(self):
        values={n:r for n,r in self.values.items() if not(n.startswith('1-server_only-baseline-forward/log-')
                and b'COH_NATIVE_STARTUP_PROFILE_V1' in r)}
        with self.assertRaises(ValueError):partial.audit_case(values,'1-server_only-baseline-forward')

    def test_map_or_physics_count_mutation_refused(self):
        markers=copy.deepcopy(self.recovered['recovered_individual_cases'][1]['world_markers']);markers['PhysX_objects']=2166
        values,label=self.edited_case('world_markers',markers)
        with self.assertRaises(ValueError):partial.audit_case(values,label)


if __name__=='__main__':unittest.main()
