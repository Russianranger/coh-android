import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import stage_resources as stage
ROOT=Path(__file__).resolve().parents[3]
class ResourceStageTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.target=Path(self.temp.name)/'private';self.target.mkdir()
  self.prior={'schema_version':1,'build_role':'map_startup_certified_animation','build_targets':['MapServer'],'animation_certificate':{},'monorail_build_input':{},'patched_sha256':{},'overlay_sha256':{},'retained_sources_sha256':{}}
  self.original={n:(ROOT/'upstream/ouroboros'/n).read_bytes() for n in stage.PATCHED}
  for n,b in self.original.items():p=self.target/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  (self.target/stage.PRIOR).write_text(json.dumps(self.prior))
 def prepare(self):
  with mock.patch.object(stage.base,'validate_prior',return_value=self.prior):return stage.prepare(ROOT,self.target)
 def verify(self):
  with mock.patch.object(stage.base,'expected_prior',return_value=self.prior):return stage.verify_staged(ROOT,self.target)
 def test_exact_original_preserved_and_single_owner_hook(self):
  receipt=self.prepare();self.assertEqual(self.verify(),receipt)
  out=(self.target/stage.base.GROUP).read_bytes();self.assertTrue(out.startswith(self.original[stage.base.GROUP]))
  init=(self.target/stage.base.INIT).read_bytes();self.assertEqual(init.count(stage.NEW),2)
  self.assertIn(b'dbSetupMap();\n        coh_source_resource_snapshot_startup();\n        dbReadyForPlayers();',init)
  self.assertFalse(receipt['contract']['client_materials_available']);self.assertFalse(receipt['contract']['live_groups_transaction'])
 def test_only_new_private_role_and_frozen_existing_payload(self):
  r=self.prepare();self.assertNotEqual(r['build_role'],stage.snapshot.ROLE)
  self.assertEqual((self.target/stage.PRODUCER).read_bytes(),(stage.HERE/'source_snapshot.inc').read_bytes())
  self.assertNotIn(stage.snapshot.SINK,stage.overlays(ROOT))
 def test_repeated_stage_refused_without_overwrite(self):
  self.prepare();before={str(p):p.read_bytes() for p in self.target.rglob('*') if p.is_file()}
  with self.assertRaises(ValueError):self.prepare()
  self.assertEqual(before,{str(p):p.read_bytes() for p in self.target.rglob('*') if p.is_file()})
 def test_each_overlay_drift_refused(self):
  self.prepare()
  for name in stage.overlays(ROOT):
   path=self.target/name;raw=path.read_bytes();path.write_bytes(raw+b'tamper')
   with self.assertRaises(ValueError):self.verify()
   path.write_bytes(raw)
 def test_receipt_role_tamper_refused(self):
  r=self.prepare();r['contract']['client_materials_available']=True;(self.target/stage.RECEIPT).write_text(json.dumps(r))
  with self.assertRaises(ValueError):self.verify()
 def test_unchanged_original_input_required(self):
  p=self.target/stage.base.GROUP;p.write_bytes(p.read_bytes()+b'drift')
  with self.assertRaises(ValueError):self.prepare()
 def test_newline_identity_preserved(self):
  for n,b in self.original.items():(self.target/n).write_bytes(b.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
  self.prepare();self.verify();out=(self.target/stage.base.INIT).read_bytes();self.assertEqual(out.count(b'\r\n'),out.count(b'\n'))
if __name__=='__main__':unittest.main()
