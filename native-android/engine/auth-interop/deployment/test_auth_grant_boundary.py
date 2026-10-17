from pathlib import Path
import copy,json,types,unittest
SCRIPT=Path(__file__).with_name('auth_grant_boundary.py');q=types.ModuleType('checked_auth_grant_boundary');q.__file__=str(SCRIPT.resolve());exec(compile(SCRIPT.read_bytes(),str(SCRIPT),'exec'),q.__dict__)
ROOT=SCRIPT.resolve().parents[4];D=SCRIPT.parent.parent/'evidence/auth-success-38996587760';RAW=(D/'receipt.json').read_bytes();BINDER=(D/'source-binder.json').read_bytes()
class Boundary(unittest.TestCase):
 def test_actual_auth_only_receipt_cannot_be_fresh_grant(self):
  result=q.diagnose(RAW,BINDER,ROOT);self.assertTrue(result['encrypted_account_login_accepted']);self.assertFalse(result['fresh_authentication_grant_available']);self.assertEqual(result['historical_client_state'],'SHARDS_READY');self.assertEqual(result['historical_shards'],0);self.assertTrue(result['historical_generation_closed']);self.assertEqual(len(result['missing_prerequisites']),6)
  for forbidden in ('account','uid','cookie','game_key','authentication_generation'):self.assertNotIn(forbidden,result)
 def test_corrupt_missing_stale_and_injected_account_generation_refused(self):
  original=json.loads(RAW)
  variants=[]
  for name,value in [('github_run_id','future-run'),('account','fixture'),('authentication_generation',38996587760)]:
   changed=copy.deepcopy(original);changed[name]=value;variants.append(changed)
  changed=copy.deepcopy(original);del changed['owned_authserver_cleanup_complete'];variants.append(changed)
  changed=copy.deepcopy(original);changed['probe_results']['normal']['valid']['state']=7;changed['probe_results']['normal']['valid']['shards']=1;variants.append(changed)
  changed=copy.deepcopy(original);changed['authenticated_db_map_handoff_verified']=True;variants.append(changed)
  for value in variants:
   with self.assertRaises(ValueError):q.diagnose(json.dumps(value).encode(),BINDER,ROOT)
  with self.assertRaises(ValueError):q.diagnose(RAW[:-1],BINDER,ROOT)
 def test_binder_corruption_and_missing_git_provenance_refused(self):
  with self.assertRaises(ValueError):q.diagnose(RAW,BINDER+b' ',ROOT)
  with self.assertRaises(Exception):q.diagnose(RAW,BINDER,ROOT/'nonexistent-owned-repository')
if __name__=='__main__':unittest.main()
