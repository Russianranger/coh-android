import copy,json,tempfile,unittest
from pathlib import Path,PureWindowsPath
from types import SimpleNamespace
from unittest.mock import patch
import admit_tool_inventory as a
import hosted_manual_atlas_compile as d

ROOT=Path(__file__).resolve().parents[4]
EVIDENCE=Path(__file__).resolve().parent.parent/'evidence/windows-tool-inventory-39005570623'

class InventoryAdmission(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.raw=(EVIDENCE/'receipt.json').read_bytes();cls.value=json.loads(cls.raw)
 def test_exact_actual_receipt_sources_and_unchanged_eight_tool_candidate(self):
  lock,review=a.verify_receipt(self.value,ROOT)
  self.assertEqual(a.sha(self.raw),a.RECEIPT_SHA);self.assertEqual(len(review['source_helper_map']),61)
  self.assertEqual(len(lock['tools']),8);self.assertEqual(lock['schema'],'coh-reviewed-windows-build-tool-lock-v1')
  observed=copy.deepcopy(self.value['observed_lock_candidates'][0]);observed['schema']=lock['schema'];del observed['requires_independent_review']
  for name in observed:self.assertEqual(lock[name],observed[name])
  self.assertEqual(lock,json.loads((EVIDENCE/'reviewed-toolchain-lock.json').read_bytes()))
  self.assertFalse(review['windows_tools_rehashed_locally'])
 def test_executed_or_changed_generation_flags_refused(self):
  for name in a.FALSES:
   value=copy.deepcopy(self.value);value[name]=True
   with self.assertRaises(ValueError):a.verify_receipt(value,ROOT)
  value=copy.deepcopy(self.value);value['repository_commit']='0'*40
  with self.assertRaises(ValueError):a.verify_receipt(value,ROOT)
 def test_source_domain_and_explicit_crlf_hash_refuse_mutation(self):
  for mode in ('remove','LF','changed'):
   value=copy.deepcopy(self.value);mapping=value['input_state_before']['helper_inputs'];name=next(iter(mapping))
   if mode=='remove':mapping.pop(name)
   elif mode=='LF':mapping[name]=a.sha(a.git(ROOT,'show',a.COMMIT+':'+a.PREFIX+name.replace('\\','/')))
   else:mapping[name]='0'*64
   value['input_state_after']=copy.deepcopy(value['input_state_before'])
   with self.assertRaises(ValueError):a.verify_receipt(value,ROOT)
 def test_sdk_or_candidate_or_post_observation_mutation_refused(self):
  for mode in ('post','candidate','sdk'):
   value=copy.deepcopy(self.value)
   if mode=='post':value['observation_after']['tools']['cl']['sha256']='0'*64
   if mode=='candidate':value['observed_lock_candidates'][0]['tools']['cl']['sha256']='0'*64
   if mode=='sdk':value['observation_before']['sdks']['10.0.26100.0']['missing']=['ucrt'];value['observation_after']=copy.deepcopy(value['observation_before'])
   with self.assertRaises(ValueError):a.verify_receipt(value,ROOT)
 def test_outer_archive_exact_pin(self):
  with tempfile.TemporaryDirectory(prefix='coh-inventory-outer-') as temporary:
   path=Path(temporary)/'bad.zip';path.write_bytes(b'not the exact retained artifact')
   with self.assertRaises(ValueError):a.admit(path,ROOT)
 def test_exact_lock_tool_lock_consumer_recorded_observer_compatibility(self):
  # This validates the exact JSON/consumer shape using recorded metadata. It
  # does not claim Linux can rehash installed Windows binaries. The actual
  # future Windows build still calls the unmocked mandatory guard.
  lockpath=EVIDENCE/'reviewed-toolchain-lock.json';lock=json.loads(lockpath.read_bytes());ledger={row['path']:row for row in list(lock['tools'].values())+list(lock['sdk_representatives'].values())}
  installation=PureWindowsPath(lock['vs_installation'])
  class RecordedPath:
   def __init__(self,value):self.path=PureWindowsPath(value)
   def __str__(self):return str(self.path)
   def is_absolute(self):return self.path.is_absolute()
   def is_dir(self):return self.path==installation
   def is_symlink(self):return False
   def is_file(self):return str(self) in ledger
   def stat(self):return SimpleNamespace(st_size=ledger[str(self)]['bytes'])
   def is_relative_to(self,other):return self.path.is_relative_to(other.path)
   def resolve(self):return self
   def __eq__(self,other):return isinstance(other,RecordedPath) and self.path==other.path
  original=d.host.sha
  def hash_file(path):return ledger[str(path)]['sha256'] if isinstance(path,RecordedPath) else original(path)
  with patch.object(d,'Path',RecordedPath),patch.object(d.host,'sha',side_effect=hash_file),patch.object(d.shutil,'which',return_value=lock['tools']['git']['path']):
   result=d.tool_lock(lockpath,a.sha(lockpath.read_bytes()),{'ImageOS':lock['image_os'],'ImageVersion':lock['image_version']})
   self.assertEqual(result,lock)
   with patch.object(d.host,'sha',side_effect=lambda p:'0'*64 if isinstance(p,RecordedPath) and str(p)==lock['sdk_representatives']['ucrt']['path'] else hash_file(p)):
    with self.assertRaises(ValueError):d.tool_lock(lockpath,a.sha(lockpath.read_bytes()),{'ImageOS':lock['image_os'],'ImageVersion':lock['image_version']})
   with self.assertRaises(ValueError):d.tool_lock(lockpath,'0'*64,{'ImageOS':lock['image_os'],'ImageVersion':lock['image_version']})

if __name__=='__main__':unittest.main()
