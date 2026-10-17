"""Source-shaped compile-artifact tests; inherited startup is substituted.

No actual PE build, runtime, generation or character is established by fixtures.
"""
import hashlib,json
from pathlib import Path
import tempfile,unittest
from unittest import mock
import admit_groups_capture as admit
import stage_groups_capture as stage
ROOT=Path(__file__).resolve().parents[3]
class GroupsCompileAdmissionTests(unittest.TestCase):
 def setUp(self):
  self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup);self.output=Path(self.temporary.name)/'compile';self.output.mkdir()
  original={name:(ROOT/'upstream/ouroboros'/name).read_bytes() for name in stage.PATCHED}
  self.prior={'schema_version':1,'build_role':'map_startup_certified_animation','build_targets':['MapServer'],'animation_certificate':{},'monorail_build_input':{},'patched_sha256':{},'overlay_sha256':{},'retained_sources_sha256':{name:hashlib.sha256(raw).hexdigest() for name,raw in original.items()}}
  output=stage.transform(original[stage.base.GROUP],original[stage.base.INIT],original[stage.GUARD]);declared=stage.expected(ROOT,self.prior,original,output)
  files={'MapServer.exe':b'explicit-nonexecuted-compile-artifact-fixture','CMakeCache.txt':b'explicit-unused-cache-fixture',stage.RECEIPT:json.dumps(declared).encode(),stage.PRIOR:json.dumps(self.prior).encode(),'map-startup-inputs.json':b'{}'}
  files.update({'source/'+name:raw for name,raw in {**output,**stage.overlays(ROOT)}.items()})
  for name,raw in files.items():path=self.output/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
  self.receipt={'schema':'coh-groups-transaction-compile-v1','passed':True,'source_revision':'0'*40,'source_git_status_porcelain':[],'build_role':stage.ROLE,'compile_only':True,'runtime_executed':False,'source_stage_verified':True,'published_inputs_reverified':True,'platform':'Win32','pe_machine':'i386','artifacts':{name:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for name,raw in files.items()}}
  self.write()
 def write(self):
  raw=json.dumps(self.receipt).encode();(self.output/'compile-only-receipt.json').write_bytes(raw);self.pin=hashlib.sha256(raw).hexdigest()
 def inspect(self,pin=None):
  with mock.patch.object(stage.base,'expected_prior',return_value=self.prior):return admit.inspect(self.output,ROOT,pin or self.pin)
 def test_exact_independently_pinned_artifact(self):self.assertEqual(self.inspect()[0],self.receipt)
 def test_independent_pin_is_required(self):
  with self.assertRaises(ValueError):self.inspect('f'*64)
 def test_scope_refusals(self):
  for field,value in {'schema':'wrong','passed':False,'source_git_status_porcelain':['dirty'],'build_role':'wrong','compile_only':False,'runtime_executed':True,'source_stage_verified':False,'published_inputs_reverified':False,'platform':'x64','pe_machine':'amd64'}.items():
   prior=self.receipt[field];self.receipt[field]=value;self.write()
   with self.assertRaises(ValueError):self.inspect()
   self.receipt[field]=prior
  self.write()
 def test_missing_artifact_refused(self):
  del self.receipt['artifacts']['CMakeCache.txt'];self.write()
  with self.assertRaises(ValueError):self.inspect()
 def test_every_artifact_byte_drift_refused(self):
  for name in self.receipt['artifacts']:
   path=self.output/name;raw=path.read_bytes();path.write_bytes(raw+b'drift')
   with self.assertRaises(ValueError):self.inspect()
   path.write_bytes(raw)
 def test_self_described_changed_source_cannot_pass(self):
  name='source/'+stage.base.GROUP;path=self.output/name;path.write_bytes(path.read_bytes()+b'drift');raw=path.read_bytes();self.receipt['artifacts'][name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()};self.write()
  with self.assertRaises(ValueError):self.inspect()
 def test_actual_windows_inline_manifest_keys(self):
  path=self.output/stage.RECEIPT;declared=json.loads(path.read_bytes());declared['inline_producer_sha256']={name.replace('/','\\'):digest for name,digest in declared['inline_producer_sha256'].items()};path.write_text(json.dumps(declared));raw=path.read_bytes();self.receipt['artifacts'][stage.RECEIPT]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()};self.write();self.assertEqual(self.inspect()[0],self.receipt)
 def test_inline_duplicate_and_mixed_separator_aliases_refused(self):
  path=self.output/stage.RECEIPT;declared=json.loads(path.read_bytes());name=next(iter(declared['inline_producer_sha256']))
  for alias in (name.replace('/','\\'),name.replace('/','\\',1)):
   changed=json.loads(json.dumps(declared));changed['inline_producer_sha256'][alias]=declared['inline_producer_sha256'][name];path.write_text(json.dumps(changed));raw=path.read_bytes();self.receipt['artifacts'][stage.RECEIPT]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()};self.write()
   with self.assertRaises(ValueError):self.inspect()
if __name__=='__main__':unittest.main()
