from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from contextlib import ExitStack
import json,os,tempfile,unittest
import windows_tool_inventory as w

class InventoryControls(unittest.TestCase):
 def setUp(self):
  self.owned=tempfile.TemporaryDirectory(prefix='coh-readonly-tools-');self.root=Path(self.owned.name);self.addCleanup(self.owned.cleanup)
  self.program=self.root/'ProgramFiles';self.parent=self.program/'Microsoft Visual Studio/18';self.vs=self.parent/'Enterprise'
  self.marker=self.vs/'VC/Auxiliary/Build/Microsoft.VCToolsVersion.default.txt';self.write(self.marker,b'14.51.36231\r\n')
  self.git=self.program/'Git/cmd/git.exe';self.write(self.git,b'fixture git');self.write(self.program/'Git/usr/bin/patch.exe',b'fixture patch')
  self.cmake=self.program/'CMake/bin/cmake.exe';self.write(self.cmake,b'fixture cmake')
  for name in ('cl','link','ml'):self.write(self.vs/('VC/Tools/MSVC/14.51.36231/bin/Hostx64/x86/'+name+'.exe'),('fixture '+name).encode())
  self.write(self.vs/'MSBuild/Current/Bin/MSBuild.exe',b'fixture msbuild');self.kits=self.root/'WindowsKits/10';self.version='10.0.26100.0'
  for name in ('bin/'+self.version+'/x64/rc.exe','Lib/'+self.version+'/um/x86/kernel32.lib','Lib/'+self.version+'/ucrt/x86/ucrt.lib','Include/'+self.version+'/um/Windows.h'):
   self.write(self.kits/name,('fixture '+name).encode())
  self.state={'commit':'1'*40,'tracked_dirty':'','helper_inputs':{'fixture':'a'*64}}
 def write(self,p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 def metadata(self,p):return '19.51.36260.0' if p.name=='cl.exe' else '4.4.4.0' if p.name=='cmake.exe' else None
 def discover(self):return w.discover(self.parent,self.git,self.kits)
 def test_all_eight_tools_and_explicit_versions_no_review_permit(self):
  vs,toolset,marker,common,sdks=self.discover();common['cmake']=self.cmake
  proof=w.observe(common,sdks,self.metadata);self.assertEqual(len(proof['tools']),7)
  locks=w.observed_locks(proof,vs,toolset,{'ImageOS':'fixture','ImageVersion':'fixture1'})
  self.assertEqual(len(locks),1);lock=locks[0];self.assertEqual(lock['windows_sdk_version'],self.version);self.assertEqual(len(lock['tools']),8)
  self.assertEqual(lock['compiler_version'],'19.51.36260.0');self.assertEqual(lock['cmake_version'],'4.4.4')
  self.assertEqual(lock['schema'],'coh-observed-windows-build-tool-lock-v1');self.assertTrue(lock['requires_independent_review'])
 def test_changed_tool_or_sdk_input_detected_by_second_observation(self):
  _,_,_,common,sdks=self.discover();common['cmake']=self.cmake;before=w.observe(common,sdks,self.metadata)
  for p in list(common.values())+[row['paths']['rc'] for row in sdks.values()]:
   data=p.read_bytes();p.write_bytes(data+b'changed')
   try:self.assertNotEqual(before,w.observe(common,sdks,self.metadata))
   finally:p.write_bytes(data)
 def test_ambiguous_vs_requires_explicit_instance(self):
  other=self.parent/'Professional/VC/Auxiliary/Build/Microsoft.VCToolsVersion.default.txt';self.write(other,b'14.51.36231')
  with self.assertRaises(ValueError):self.discover()
  self.assertEqual(w.discover(self.parent,self.git,self.kits,self.vs)[0],self.vs)
 def test_partial_sdk_and_missing_version_produce_no_lock(self):
  path=self.kits/('Lib/'+self.version+'/ucrt/x86/ucrt.lib');path.unlink();vs,toolset,_,common,sdks=self.discover();common['cmake']=self.cmake
  proof=w.observe(common,sdks,self.metadata);self.assertEqual(proof['sdks'][self.version]['missing'],['ucrt'])
  self.assertEqual(w.observed_locks(proof,vs,toolset,{}),[])
  proof['sdks'][self.version]['missing']=[];proof['file_versions']['cmake']=None
  self.assertEqual(w.observed_locks(proof,vs,toolset,{}),[])
 def test_tool_marker_symlink_size_and_version_bounds(self):
  self.marker.write_bytes(b'latest')
  with self.assertRaises(ValueError):self.discover()
  link=self.root/'link.exe';link.symlink_to(self.cmake)
  with self.assertRaises(ValueError):w.file_record(link)
  large=self.root/'large.exe'
  with large.open('wb') as f:f.truncate(256*1024*1024+1)
  with self.assertRaises(ValueError):w.file_record(large)
 def run_collect(self,states=None,metadata=None):
  args=SimpleNamespace(source_root=self.root,output=self.root/'out',expected_commit='1'*40,vs_installation=None)
  with ExitStack() as stack:
   stack.enter_context(patch.object(w.host,'require_hosted',return_value={'repository_commit':'1'*40,'image_os':'fixture','image_version':'fixture1'}))
   stack.enter_context(patch.object(w,'input_state',side_effect=states or [self.state,self.state]))
   stack.enter_context(patch.object(w,'sdk_root',return_value=self.kits))
   stack.enter_context(patch.object(w.shutil,'which',side_effect=lambda name:str(self.git if name=='git' else self.cmake)))
   stack.enter_context(patch.object(w,'fixed_file_version',side_effect=metadata or self.metadata))
   stack.enter_context(patch.dict(os.environ,{'ProgramFiles':str(self.program),'ImageOS':'fixture','ImageVersion':'fixture1'}))
   stack.enter_context(patch('subprocess.Popen',side_effect=AssertionError('tool process forbidden in collector')))
   result=w.collect(args)
  return result,json.loads((args.output/'receipt.json').read_bytes())
 def test_collector_without_tool_process_and_no_source_writes(self):
  before={p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
  result,retained=self.run_collect();self.assertTrue(result['passed']);self.assertEqual(result,retained)
  for name in ('compiler_executed','cmake_executed','source_patched','dependencies_fetched','service_executed','toolchain_reviewed','compile_permit','shipping_runtime_replacement_permit'):self.assertIs(result[name],False)
  self.assertEqual(result['observation_before'],result['observation_after'])
  for name,data in before.items():self.assertEqual((self.root/name).read_bytes(),data)
 def test_private_metadata_error_is_symbolic_failure_receipt(self):
  def fail(p):raise OSError('private Windows user/driver detail')
  result,retained=self.run_collect(metadata=fail);self.assertFalse(result['passed']);self.assertEqual(result['failure'],'OSError')
  self.assertNotIn('private Windows',json.dumps(retained))
 def test_source_generation_change_refuses_success(self):
  changed=dict(self.state,commit='2'*40);result,_=self.run_collect(states=[self.state,changed])
  self.assertFalse(result['passed']);self.assertFalse(result['source_inputs_unchanged'])
 def test_linux_rejected_before_receipt_or_tool_execution(self):
  args=SimpleNamespace(source_root=self.root,output=self.root/'out',expected_commit='1'*40)
  with self.assertRaises(ValueError):w.collect(args)
  self.assertFalse(args.output.exists())

if __name__=='__main__':unittest.main()
