"""Refusals and authentic animation parity; controls grant no native authority."""
import copy
import os
from pathlib import Path
import unittest
import aggregate_native_map_world_pools_037 as aggregate


class AggregateRefusals(unittest.TestCase):
    def test_wrong_source_or_branch_refused(self):
        for run in ({'head_sha':'0'*40,'head_branch':'main','path':'.github/workflows/android-native-map-world-037.yml'},
                    {'head_sha':'a'*40,'head_branch':'main','path':'.github/workflows/android-native-map-world-037.yml'}):
            with self.subTest(run=run),self.assertRaises(ValueError):
                aggregate.join({}, {},run,{}, {},'a'*40)

    def test_missing_pool_never_becomes_success(self):
        run={'head_sha':'a'*40,'head_branch':'codex/native-map-world-037','path':'.github/workflows/android-native-map-world-037.yml'}
        with self.assertRaises(ValueError):aggregate.join({}, {},run,{}, {},'a'*40)

    def test_native_case_cleanup_and_SQL_required(self):
        case={'map_id':5,'fx_variant':'server_only','world_markers':{'PhysX_objects':2166},
              'native_Db_status':{'map_id':5,'port':7003},'synthetic_row_unchanged':False,'owned_cleanup_verified':True}
        with self.assertRaises(ValueError):aggregate.native_case_ok(case,5,'server_only')
        case['synthetic_row_unchanged']=True;case['owned_cleanup_verified']=False
        with self.assertRaises(ValueError):aggregate.native_case_ok(case,5,'server_only')


class ActualAnimationParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value=os.environ.get('COH_WORLD_PARTIAL_TEST_ARCHIVE')
        if not value:raise RuntimeError('Explicit authenticated original partial artifact required for these tests')
        recovered,_=aggregate.partial.recover(Path(value))
        cls.actual=recovered['recovered_individual_cases']

    def test_authentic_original_both_FX_Atlas_and_Kings_consumers_pass(self):
        self.assertEqual({case['fx_variant'] for case in self.actual if case['map_id']==1},
                         {'server_only','full'})
        for map_id in (1,5):aggregate.require_map_animation_parity(self.actual,map_id)

    def test_only_hash_and_stock_timing_are_excluded(self):
        cases=copy.deepcopy(self.actual)
        latest=cases[-2]['actual_certified_animation_consumption']['latest_counters']
        latest['hash_us']+=1;latest['stock_us']+=1
        aggregate.require_map_animation_parity(cases,1)
        for key in latest:
            if key in ('hash_us','stock_us'):continue
            changed=copy.deepcopy(cases)
            changed[-2]['actual_certified_animation_consumption']['latest_counters'][key]+=1
            with self.subTest(counter=key),self.assertRaises(ValueError):
                aggregate.require_map_animation_parity(changed,1)

    def test_cross_FX_subset_change_refused_even_when_each_pool_is_consistent(self):
        cases=copy.deepcopy(self.actual)
        for case in cases:
            if case['map_id']==1 and case['fx_variant']=='full':
                case['actual_certified_animation_consumption']['latest_counters']['raw_bytes']+=596
        for variant in ('server_only','full'):
            aggregate.require_map_animation_parity([case for case in cases if case['fx_variant']==variant],1)
        with self.assertRaises(ValueError):aggregate.require_map_animation_parity(cases,1)

    def test_controlled_sixteen_member_frontier_checks_last_Kings_consumer(self):
        # Copies exercise membership only; seven Kings native executions remain pending.
        cases=copy.deepcopy(self.actual)+[copy.deepcopy(self.actual[-1]) for _ in range(7)]
        self.assertEqual(len(cases),16)
        for map_id in (1,5):aggregate.require_map_animation_parity(cases,map_id)
        cases[-1]['actual_certified_animation_consumption']['latest_counters']['opened']+=1
        with self.assertRaises(ValueError):aggregate.require_map_animation_parity(cases,5)


if __name__=='__main__':unittest.main()
