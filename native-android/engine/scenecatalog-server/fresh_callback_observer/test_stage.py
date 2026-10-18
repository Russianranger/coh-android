"""New private-role source controls. Synthetic metadata never runtime authority."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import stage
ROOT=HERE.parents[3]

class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.original={n:(ROOT/'upstream/ouroboros'/n).read_bytes() for n in stage.old.PATCHED}
  cls.old_output=stage.old.transform(cls.original[stage.base.GROUP],cls.original[stage.base.INIT],cls.original[stage.old.GUARD])
  cls.inputs={**cls.old_output,stage.FOLDER:(ROOT/'upstream/ouroboros'/stage.FOLDER).read_bytes()}
 def test_exact_hook_positions_and_preserved_old_group(self):
  out=stage.transform(self.inputs);folder=stage.base.lf(out[stage.FOLDER]);group=stage.base.lf(out[stage.base.GROUP])
  self.assertIn(b'coh_fresh_folder_queue_added();\n            newitem = listAddNewMember',folder)
  self.assertIn(b'newitem->when = whathappened;\n            coh_fresh_folder_queue_add_finished();',folder)
  self.assertIn(b'listFreeMember(walk, &queued_callbacks);\n        coh_fresh_folder_queue_removed();',folder)
  self.assertIn(b'FolderCacheEnableCallbacks(1);\n'+stage.SEAL,stage.base.lf(out[stage.base.INIT]))
  # Strip only the fixed new prefix/tail and stage statements. The old complete
  # boundary/exporters/predicate must then be byte-exact, not approximate.
  prefix=b'#include "../../../libs/UtilitiesLib/src/utils/coh_fresh_source_profile_api.h"\n'
  group=group.removeprefix(prefix).removesuffix(stage.GROUP_TAIL)
  import re
  group=re.sub(rb' coh_fresh_source_probe_step\(COH_FRESH_STAGE_[A-Z_]+\);\n',b'',group)
  owner=(HERE.parent/'source_groups_owner.inc').read_bytes()
  group=group.replace(stage.specialize_initial_owner(stage.instrument_owner(owner)),owner,1)
  self.assertEqual(group,stage.base.lf(self.old_output[stage.base.GROUP]))
  self.assertEqual(out[stage.old.GUARD],self.old_output[stage.old.GUARD])
  self.assertEqual(stage.overlays(ROOT)[stage.ORIGINAL_GUARD],stage.base.lf((HERE.parent/'source_resource_quiescence.inc').read_bytes()))
 def test_every_anchor_and_source_mutation_refused(self):
  for name in stage.PATCHED:
   changed=dict(self.inputs);changed[name]=changed[name].replace(b'FolderCacheEnableCallbacks(1);',b'FolderCacheEnableCallbacks(0);',1) if name==stage.base.INIT else changed[name]+b'\n'
   if name in (stage.FOLDER,stage.base.INIT):
    with self.subTest(name=name),self.assertRaises(ValueError):stage.transform(changed)
  changed=dict(self.inputs);changed[stage.base.GROUP]=changed[stage.base.GROUP].replace(b' status=coh_source_catalog_export(',b' status=other_export(',1)
  with self.assertRaises(ValueError):stage.transform(changed)
  changed=dict(self.inputs);changed[stage.base.INIT]=changed[stage.base.INIT]+stage.old.CALL
  with self.assertRaises(ValueError):stage.transform(changed)
 def test_crlf_staged_sources_preserve_raw_line_endings(self):
  inputs={n:stage.base.lf(raw).replace(b'\n',b'\r\n') for n,raw in self.inputs.items()}
  out=stage.transform(inputs);reference=stage.transform(self.inputs)
  for n,raw in out.items():
   self.assertEqual(raw.count(b'\r\n'),raw.count(b'\n'))
   self.assertEqual(stage.base.lf(raw),stage.base.lf(reference[n]))
 def test_portable_old_inline_keys_exact_and_duplicate_refusal(self):
  self.assertEqual(stage.portable({'inline_producer_sha256':{'a\\b':'c'}}),{'inline_producer_sha256':{'a/b':'c'}})
  with self.assertRaises(ValueError):stage.portable({'inline_producer_sha256':{'a\\b':'c','a/b':'c'}})
  with self.assertRaises(ValueError):stage.decode(b'{"a":1,"a":1}')
  with self.assertRaises(ValueError):stage.decode(b'{"a":NaN}')
 def test_synthetic_source_reconstruction_and_every_final_byte(self):
  # Metadata suppliers are explicitly synthetic here. Production admission
  # reconstructs original prerequisite certificates; this control checks the new
  # deterministic layer without forging any prior certificate or PE provenance.
  prior={'inline_producer_sha256':{},'synthetic_source_control':True}
  output=stage.transform(self.inputs)
  values={**stage.old.overlays(ROOT),**stage.overlays(ROOT),**output,
   stage.old.PRIOR:b'{}',stage.old.RECEIPT:json.dumps(prior).encode()}
  receipt=stage.expected(ROOT,prior,self.inputs,output);values[stage.RECEIPT]=json.dumps(receipt).encode()
  with patch.object(stage.base,'expected_prior',return_value={}),patch.object(stage.base,'inherited_hashes',return_value={}),patch.object(stage.old,'expected',return_value=prior):
   stage.verify_bytes(ROOT,values.__getitem__)
   # Real startup receipts retain ORIGINAL FolderCache.c. Full staged verify
   # must substitute that original before checking its inherited digest, while
   # independently checking the transformed FolderCache output below.
   with patch.object(stage.base,'inherited_hashes',return_value={stage.FOLDER:stage.base.sha(self.inputs[stage.FOLDER])}):
    stage.verify_bytes(ROOT,values.__getitem__,all_inherited=True)
   with patch.object(stage.base,'inherited_hashes',return_value={stage.FOLDER:'0'*64}),self.assertRaises(ValueError):stage.verify_bytes(ROOT,values.__getitem__,all_inherited=True)
   for n in (*stage.PATCHED,*stage.overlays(ROOT)):
    modified=dict(values);modified[n]=modified[n]+b'\n'
    with self.subTest(name=n),self.assertRaises(ValueError):stage.verify_bytes(ROOT,modified.__getitem__)
   modified=dict(values);wrong=copy.deepcopy(receipt);wrong['contract']['accepted_cache_watch_policy_equivalent']=True;modified[stage.RECEIPT]=json.dumps(wrong).encode()
   with self.assertRaises(ValueError):stage.verify_bytes(ROOT,modified.__getitem__)
 def test_checkout_closure_refuses_foreign_root_and_changed_blob(self):
  with tempfile.TemporaryDirectory() as temp,self.assertRaises(ValueError):stage.checkout_closure(Path(temp))
  # Actual admission executes only committed own-checkout helpers. Simulate a
  # late changed helper read without writing any protected/common source.
  pins=stage.checkout_closure(ROOT)
  self.assertIn((HERE/'stage.py').relative_to(ROOT).as_posix(),pins)
  original=stage.base.regular
  def changed(path,*args,**kwargs):
   result=original(path,*args,**kwargs)
   if Path(path)==HERE/'stage.py':
    from unittest.mock import Mock
    return Mock(read_bytes=lambda:result.read_bytes()+b'changed')
   return result
  with patch.object(stage.base,'regular',side_effect=changed),self.assertRaises(ValueError):stage.checkout_closure(ROOT)

 def test_old_source_files_never_written(self):
  # New overlays are separate; accepted old suppliers and stagers are imported
  # read-only. No source-dependent real process invocation belongs to this CLI.
  out=stage.transform(self.inputs)
  self.assertEqual(set(out),set(stage.PATCHED))
  self.assertNotEqual(stage.ROLE,stage.old.ROLE)
  self.assertNotEqual(stage.RECEIPT,stage.old.RECEIPT)
  self.assertFalse(stage.CONTRACT['accepted_cache_watch_policy_equivalent'])
  self.assertFalse(stage.CONTRACT['runtime_executed'])

 def test_owner_atom_order_reversibility_and_changed_table_refusal(self):
  owner=(HERE.parent/'source_groups_owner.inc').read_bytes();rows=stage.owner_predicates()
  instrumented=stage.instrument_owner(owner);restored=instrumented
  self.assertEqual(len(rows),47)
  self.assertEqual(instrumented.count(b'coh_fresh_source_owner_failed('),47)
  previous=-1
  for name,atom in rows:
   wrapper=b'coh_fresh_source_owner_failed(('+atom+b'),COH_FRESH_OWNER_'+name.encode()+b')'
   self.assertEqual(instrumented.count(wrapper),1)
   at=instrumented.index(wrapper);self.assertGreater(at,previous);previous=at
   restored=restored.replace(wrapper,atom,1)
  self.assertEqual(restored,owner)
  self.assertIn(b'*out=candidate;return 1;',instrumented)
  with self.assertRaises(ValueError):stage.instrument_owner(owner+b'\n')
  with patch.object(stage,'owner_predicates',return_value=rows[::-1]),self.assertRaises(ValueError):stage.instrument_owner(owner)
  with patch.object(stage,'owner_predicates',return_value=rows[:-1]),self.assertRaises(ValueError):stage.instrument_owner(owner)

if __name__=='__main__':unittest.main()
