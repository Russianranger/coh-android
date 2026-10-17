import copy,json,unittest
from pathlib import Path
import analyze
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
class Budgets(unittest.TestCase):
 def setUp(self):
  self.startup=json.loads((ROOT/'native-android/combined-client/evidence/20261016/thor-0.1.7-acceptance/startup-analysis.json').read_text());self.join=json.loads((HERE/'resource-join-source-receipt.json').read_text())
 def test_real_boundary_and_budget(self):
  r=analyze.analyze(self.startup,self.join);c=r['measurements']['current'];self.assertEqual(c['ready_ms'],387340);self.assertEqual(c['native_total_ms'],342414);self.assertEqual(c['other_exclusive_boundary_ms'],44926);self.assertEqual(r['resource_metadata_transaction']['remaining_named_payload_bytes'],48996871)
 def test_suboperations_not_added(self):
  self.startup['current']['guest_detail']['preparation_seconds']['atlas_beacon_graph']=200
  r=analyze.analyze(self.startup,self.join);self.assertEqual(r['measurements']['current']['native_total_ms'],342414);self.assertEqual(r['counterfactual_arithmetic_only'][-1]['ready_ms_if_native_unchanged'],342414)
 def test_contradictory_or_missing_resource_scope(self):
  for field in ['assets_admitted','world_authority','android_executed']:
   r=copy.deepcopy(self.join);r[field]=True
   with self.assertRaises(ValueError):analyze.analyze(self.startup,r)
  self.join['modes']['asan']['result']['rows']+=1
  with self.assertRaises(ValueError):analyze.analyze(self.startup,self.join)
 def test_invalid_stage_measurements(self):
  for value in [True,-1,float('nan'),float('inf')]:
   r=copy.deepcopy(self.startup);r['current']['ready_boundary_ms']=value
   with self.assertRaises(ValueError):analyze.analyze(r,self.join)
  r=copy.deepcopy(self.startup);r['current']['stages'].append(next(s for s in r['current']['stages'] if s['stage']=='local_atlas_startup'))
  with self.assertRaises(ValueError):analyze.analyze(r,self.join)
 def test_metadata_limit_refusal(self):
  with self.assertRaises(ValueError):analyze.analyze(self.startup,self.join,aggregate_limit=51666424)
if __name__=='__main__':unittest.main()
