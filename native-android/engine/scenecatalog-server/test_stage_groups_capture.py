import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import stage_groups_capture as stage
ROOT=Path(__file__).resolve().parents[3]
class GroupsCaptureStageTests(unittest.TestCase):
 def setUp(self):
  self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup);self.target=Path(self.temporary.name)/'private';self.target.mkdir()
  self.original={name:(ROOT/'upstream/ouroboros'/name).read_bytes() for name in stage.PATCHED}
  self.prior={'schema_version':1,'build_role':'map_startup_certified_animation','build_targets':['MapServer'],'animation_certificate':{},'monorail_build_input':{},'patched_sha256':{},'overlay_sha256':{},'retained_sources_sha256':{name:hashlib.sha256(raw).hexdigest() for name,raw in self.original.items()}}
  for name,raw in self.original.items():target=self.target/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
  (self.target/stage.PRIOR).write_text(json.dumps(self.prior))
 def prepare(self):
  # Independent inherited-startup admission retains its existing tests. These
  # explicit substitutions exercise only this added private role/rollback.
  with mock.patch.object(stage.base,'validate_prior',return_value=self.prior):return stage.prepare(ROOT,self.target)
 def verify(self):
  with mock.patch.object(stage.base,'expected_prior',return_value=self.prior):return stage.verify_staged(ROOT,self.target)
 def test_exact_roundtrip_and_actual_owner_hook(self):
  receipt=self.prepare();self.assertEqual(self.verify(),receipt)
  group=(self.target/stage.base.GROUP).read_bytes();init=(self.target/stage.base.INIT).read_bytes()
  self.assertEqual(group.count(b'coh_groups_transaction_begin(link,full_update);'),1);self.assertEqual(group.count(b'coh_groups_transaction_finish(pak);'),1)
  self.assertEqual(init.count(stage.CALL),2);self.assertIn(b'dbSetupMap();\n        coh_source_groups_capture_install();\n        dbReadyForPlayers();',init)
  self.assertFalse(receipt['contract']['source_generation_admitted']);self.assertFalse(receipt['contract']['world_authority'])
 def test_repeat_refuses_without_overwrite(self):
  self.prepare();before={str(p):p.read_bytes() for p in self.target.rglob('*') if p.is_file()}
  with self.assertRaises(ValueError):self.prepare()
  self.assertEqual(before,{str(p):p.read_bytes() for p in self.target.rglob('*') if p.is_file()})
 def test_each_overlay_drift_refuses(self):
  self.prepare()
  for name in stage.overlays(ROOT):
   target=self.target/name;raw=target.read_bytes();target.write_bytes(raw+b'drift')
   with self.assertRaises(ValueError):self.verify()
   target.write_bytes(raw)
 def test_each_patched_source_drift_refuses(self):
  self.prepare()
  for name in stage.PATCHED:
   target=self.target/name;raw=target.read_bytes();target.write_bytes(raw+b'drift')
   with self.assertRaises(ValueError):self.verify()
   target.write_bytes(raw)
 def test_receipt_admission_cannot_be_forged(self):
  receipt=self.prepare();receipt['contract']['source_generation_admitted']=True;(self.target/stage.RECEIPT).write_text(json.dumps(receipt))
  with self.assertRaises(ValueError):self.verify()
 def test_foreign_group_and_anim_refuse(self):
  for name in (stage.base.GROUP,stage.GUARD):
   target=self.target/name;raw=target.read_bytes();target.write_bytes(raw+b'drift')
   with self.assertRaises(ValueError):self.prepare()
   target.write_bytes(raw)
 def test_newline_identity_roundtrip(self):
  for name,raw in self.original.items():
   raw=stage.base.lf(raw).replace(b'\n',b'\r\n');(self.target/name).write_bytes(raw);self.prior['retained_sources_sha256'][name]=hashlib.sha256(raw).hexdigest()
  (self.target/stage.PRIOR).write_text(json.dumps(self.prior));self.prepare();self.verify();raw=(self.target/stage.base.GROUP).read_bytes();self.assertEqual(raw.count(b'\r\n'),raw.count(b'\n'))
 def test_failed_overlay_creation_rolls_back(self):
  before={str(p):p.read_bytes() for p in self.target.rglob('*') if p.is_file()};original_open=Path.open
  def refused_open(path,*args,**kwargs):
   if path==self.target/stage.SINK and args and args[0]=='xb':raise OSError('fixture create refusal')
   return original_open(path,*args,**kwargs)
  with mock.patch.object(Path,'open',refused_open):
   with self.assertRaises(OSError):self.prepare()
  self.assertEqual(before,{str(p):p.read_bytes() for p in self.target.rglob('*') if p.is_file()})
if __name__=='__main__':unittest.main()
