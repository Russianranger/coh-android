#!/usr/bin/env python3
"""Synthetic admission controls only; no native executable or service is run."""
import hashlib,json,struct,tempfile,unittest
from pathlib import Path
from unittest import mock
import capture_groups_transaction as capture

class Controls(unittest.TestCase):
 def setUp(self):
  self.temporary=tempfile.TemporaryDirectory(prefix='coh-initial-build-input-')
  self.addCleanup(self.temporary.cleanup);self.root=Path(self.temporary.name)
  self.tools=self.root/'native-android/combined-client/tools';self.tools.mkdir(parents=True)
  (self.root/'native-android/include').mkdir();(self.root/'native-android/engine').mkdir()
  (self.root/'native-android/include/synthetic.h').write_text('#define EXPLICIT_SYNTHETIC_INPUT 1\n')
  (self.root/'native-android/engine/synthetic.c').write_text('#include "synthetic.h"\nint synthetic_source;\n')
  for driver,tool,_ in capture.NATIVE_BUILDS.values():
   (self.tools/driver).write_text("RELATIVE = ['engine/synthetic.c']\n")
   (self.tools/tool).write_text('#include "synthetic.h"\nint synthetic_tool;\n')
  # Header shape is deliberately synthetic, never executable and never run.
  header=bytearray(20);header[:6]=b'\x7fELF\x02\x01';struct.pack_into('<H',header,18,62)
  self.binary=self.root/'coh-capture-local-initial';self.binary.write_bytes(header)
  self.receipt_path=self.root/'build.json'
 def receipt(self,schema=capture.INITIAL_BUILD_SCHEMA):
  return {'schema':schema,'passed':True,'source_hashes_authoritative_for_build_bytes':True,
   **(capture.INITIAL_BUILD_FLAGS if schema==capture.INITIAL_BUILD_SCHEMA else {}),
   'source_revision':'0'*40,'modes':{'release':{'built':True,'binary':self.binary.name,
    'sha256':hashlib.sha256(self.binary.read_bytes()).hexdigest()}},
   'source_sha256':{path.relative_to(self.root).as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
    for path in (self.root/'native-android').rglob('*') if path.is_file()}}
 def admit(self,receipt):
  self.receipt_path.write_text(json.dumps(receipt));pin=hashlib.sha256(self.receipt_path.read_bytes()).hexdigest()
  return capture.native_input(self.binary,self.receipt_path,pin,self.root)
 def refuse_before_compiler(self,receipt):
  with mock.patch.object(capture.subprocess,'run') as compiler:
   with self.assertRaises(capture.d.Refused):self.admit(receipt)
   self.assertFalse(compiler.called)
 def test_fixed_initial_driver_and_complete_project_dependencies(self):
  result=self.admit(self.receipt())
  self.assertEqual(result['build_schema'],capture.INITIAL_BUILD_SCHEMA)
  self.assertEqual(result['project_dependencies'],4)
  self.assertEqual(set(result['dependencies_sha256']),{
   'native-android/combined-client/tools/check_local_initial_capture.py',
   'native-android/combined-client/tools/capture_local_initial.c',
   'native-android/engine/synthetic.c','native-android/include/synthetic.h'})
 def test_legacy_result_shape_and_fixed_driver_remain_unchanged(self):
  self.binary=self.binary.with_name('coh-capture-local-scene')
  self.binary.write_bytes(b'\x7fELF\x02\x01'+b'\0'*12+b'\x3e\0')
  result=self.admit(self.receipt('coh-local-scene-capture-build-v1'))
  self.assertEqual(set(result),{'binary','build_receipt_sha256','source_revision',
   'project_dependencies','dependencies_sha256'})
  self.assertIn('native-android/combined-client/tools/check_local_scene_capture.py',result['dependencies_sha256'])
  self.assertNotIn('native-android/combined-client/tools/check_local_initial_capture.py',result['dependencies_sha256'])
 def test_initial_flags_strict_and_required_before_compiler(self):
  for name,expected in capture.INITIAL_BUILD_FLAGS.items():
   for value in (not expected,int(expected),None,'true'):
    with self.subTest(name=name,value=value):
     receipt=self.receipt();receipt[name]=value;self.refuse_before_compiler(receipt)
   receipt=self.receipt();del receipt[name];self.refuse_before_compiler(receipt)
  for name in ('passed','source_hashes_authoritative_for_build_bytes'):
   receipt=self.receipt();receipt[name]=1;self.refuse_before_compiler(receipt)
 def test_fixed_basename_and_schema_before_compiler(self):
  receipt=self.receipt();self.binary=self.binary.with_name('caller-selected-tool')
  self.binary.write_bytes(b'\x7fELF\x02\x01'+b'\0'*12+b'\x3e\0')
  receipt['modes']['release']['binary']=self.binary.name;self.refuse_before_compiler(receipt)
  for schema in ('caller-selected-build-v1',None,False,[]):
   receipt=self.receipt();receipt['schema']=schema;self.refuse_before_compiler(receipt)
 def test_caller_driver_selector_cannot_override_fixed_driver(self):
  receipt=self.receipt();receipt['driver']='caller.py';receipt['relative_sources']=[]
  (self.tools/'caller.py').write_text("raise RuntimeError('never loaded')\n")
  result=self.admit(receipt)
  self.assertNotIn('native-android/combined-client/tools/caller.py',result['dependencies_sha256'])
  (self.tools/'check_local_initial_capture.py').write_text('RELATIVE = []\nRELATIVE = []\n')
  with self.assertRaises(capture.d.Refused):self.admit(receipt)
 def test_transitive_header_and_tool_source_bytes_required(self):
  for name in ('native-android/include/synthetic.h',
    'native-android/combined-client/tools/capture_local_initial.c'):
   receipt=self.receipt();del receipt['source_sha256'][name]
   with self.subTest(omitted=name),self.assertRaises(capture.d.Refused):self.admit(receipt)
   receipt=self.receipt();receipt['source_sha256'][name]='0'*64
   with self.subTest(changed=name),self.assertRaises(capture.d.Refused):self.admit(receipt)
 def test_binary_receipt_and_architecture_binding(self):
  receipt=self.receipt();receipt['modes']['release']['sha256']='0'*64
  with self.assertRaises(capture.d.Refused):self.admit(receipt)
  self.binary.write_bytes(b'\x7fELF\x02\x01'+b'\0'*14)
  with self.assertRaises(capture.d.Refused):self.admit(self.receipt())
 def test_ast_dynamic_source_list_refused_without_execution(self):
  receipt=self.receipt();(self.tools/'check_local_initial_capture.py').write_text("RELATIVE = eval('[]')\n")
  with mock.patch.object(capture.subprocess,'run') as compiler:
   with self.assertRaises(ValueError):self.admit(receipt)
   self.assertFalse(compiler.called)

if __name__=='__main__':unittest.main()
