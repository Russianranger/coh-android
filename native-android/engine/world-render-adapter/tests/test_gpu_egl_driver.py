"""Mock admission/device controls only; these tests never claim Android execution."""
import copy,hashlib,importlib.util,json,struct,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE))
import gpu_egl_contract as contract
import run_gpu_egl_android as driver

def result(platform='android'):
 return {'passed':True,'checks':183,'failure_line':0,'cleanup_verified':True,'gles_major':3,'contexts_created':2,'contexts_destroyed':2,'surfaces_created':3,'surfaces_destroyed':3,'readbacks':27,'levels_per_upload':9,'rgba_bytes_per_upload':349524,'generation_fixture_only':True,'sampler_fixture_only':True,'material_authority':False,'world_authority':False,'platform':platform,'context_name_reused':False,'gl_version':'OpenGL ES 3.0 explicit mock','gl_renderer':'explicit mocked driver'}

def elf(machine):
 raw=bytearray(512);raw[:7]=b'\x7fELF\x02\x01\x01';struct.pack_into('<HHI',raw,16,3,machine,1);struct.pack_into('<Q',raw,32,64);struct.pack_into('<HHH',raw,52,64,56,3)
 interp=b'/system/bin/linker64\0';raw[256:256+len(interp)]=interp
 for i,(kind,offset,size,mem) in enumerate([(1,0,512,512),(2,300,16,16),(3,256,len(interp),len(interp))]):
  at=64+i*56;struct.pack_into('<I',raw,at,kind);struct.pack_into('<Q',raw,at+8,offset);struct.pack_into('<QQ',raw,at+32,size,mem)
 return bytes(raw)

class FakeAdb:
 def __init__(self,mode='success'):self.mode,self.calls=mode,[]
 def run(self,args,timeout=45):
  self.calls.append(args)
  if args[:3]==['shell','getprop','ro.build.version.sdk']:return '33'
  if args[:3]==['shell','getprop','ro.product.cpu.abi']:return 'x86_64'
  if args[:2]==['shell','sha256sum']:
   path=args[2];digest=contract.FIXTURE_SHA if path.endswith('box-1.texture') else contract.WHOLE_PACKET_SHA if path.endswith('readback.rgba') else 'a'*64
   return digest+'  '+path
  if args[:2]==['shell','timeout']:
   if self.mode=='native_failure':raise ValueError('explicit mock native failure')
   value=result()
   if self.mode=='bad_json':value['cleanup_verified']=False
   return json.dumps(value)
  if args[:3]==['shell','stat','-c']:return str(3*349524)
  if args[0]=='pull':Path(args[2]).write_bytes(b'\0'*(3*349524) if self.mode!='bad_packet' else b'bad');return ''
  if args[:2]==['shell','rm'] and self.mode=='cleanup_failure':raise ValueError('explicit mock cleanup failure')
  return ''

class EglDriverTests(unittest.TestCase):
 def test_every_native_field_type_scope_and_missing_field(self):
  contract.native(result(),'android')
  for key in result():
   value=result();value.pop(key)
   with self.assertRaises(ValueError):contract.native(value,'android')
  for key,value in result().items():
   if type(value)is int:
    changed=result();changed[key]=True
    with self.assertRaises(ValueError):contract.native(changed,'android')
   if type(value)is bool:
    changed=result();changed[key]=int(value)
    with self.assertRaises(ValueError):contract.native(changed,'android')
  changed=result();changed['world_authority']=True
  with self.assertRaises(ValueError):contract.native(changed,'android')
  with self.assertRaises(ValueError):contract.native(result('host-linux'),'android')

 def test_elf_both_abis_interpreter_segments_and_truncation(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)/'binary'
   for machine in (62,183):p.write_bytes(elf(machine));self.assertTrue(contract.elf(p,machine))
   for raw in (elf(183)[:100],elf(62).replace(b'/system/bin/linker64',b'/system/bin/linker32'),b'bad',elf(183)):
    p.write_bytes(raw)
    with self.assertRaises(ValueError):contract.elf(p,62)

 def test_execute_success_failure_flags_packet_and_owned_cleanup(self):
  packet=b'\0'*(3*349524);digest=hashlib.sha256(packet).hexdigest()
  for mode in ('success','native_failure','bad_json','bad_packet','cleanup_failure'):
   with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temp,patch.object(contract,'WHOLE_PACKET_SHA',digest):
    output=Path(temp);(output/'qualification.json').write_text('{}')
    args=SimpleNamespace(artifacts=output,abi='x86_64');q={'source_commit':'a'*40,'source_tree':'b'*40,'android':{'x86_64':{'binary_sha256':'a'*64}}};adb=FakeAdb(mode)
    value=driver.execute(q,args,output,adb)
    self.assertEqual(value['passed'],mode=='success');self.assertTrue(value['native_execution_attempted'])
    self.assertEqual(value['android_executed'],mode not in ('native_failure','bad_json'))
    self.assertEqual(value['device_cleanup_verified'],mode!='cleanup_failure')
    self.assertTrue(any(call[:2]==['shell','rm'] for call in adb.calls))
    for call in adb.calls:
     if call[:2]==['shell','rm']:self.assertRegex(call[-1],r'^/data/local/tmp/coh-egl-[0-9a-f]{24}$')

 def test_full_admission_own_source_modes_binary_and_fixture_bindings(self):
  # Explicitly mocked build declarations/ELFs; no actual build/execution claim.
  root=contract.ROOT;packet=b'\0'*(3*349524);fixture=b'\0'*43990
  packet_sha=hashlib.sha256(packet).hexdigest();fixture_sha=hashlib.sha256(fixture).hexdigest()
  with tempfile.TemporaryDirectory() as temp,patch.object(contract,'WHOLE_PACKET_SHA',packet_sha),patch.object(contract,'FIXTURE_SHA',fixture_sha),patch.object(driver,'git',side_effect=lambda root,*args:'\n'.join(contract.source_paths(root)) if args[0]=='ls-files' else '' if args[0]=='status' else 'b'*40 if args[-1]=='HEAD^{tree}' else 'a'*40):
   out=Path(temp);(out/'box-1.texture').write_bytes(fixture);(out/'egl_fixture_digest.h').write_bytes(contract.fixture_header(fixture));headers=json.loads((HERE/'egl-host-header-pins.json').read_text())
   prior=json.loads((HERE/'qualification/gpu-texture-model-20261017/host.json').read_text())
   q={'schema':'coh-standalone-egl-v1','passed':True,'source_commit':'a'*40,'source_tree':'b'*40,'source_sha256':contract.source_hashes(root),'prior_gpu_model_sha256':contract.PRIOR_SHA,'fixture_sha256':fixture_sha,'fixture_bytes':43990,'fixture_header_sha256':contract.sha(out/'egl_fixture_digest.h'),'readback_sha256':packet_sha,'host_actual_gles':True,'android_executed':False,'material_authority':False,'world_authority':False,'shipping_renderer_modified':False,'host_library_files_before':{'egl':'1'*64,'gles':'2'*64},'host_library_files_after':{'egl':'1'*64,'gles':'2'*64},'host_loaded_mapping_verified':False,'system_driver_sanitized':False,'host_headers':headers,'pillow':prior['texture_oracle'],'host':{},'ndk':{'revision':'28.2.13676358','source_properties_sha256':'d'*64,'clang_sha256':'c'*64,'headers_sha256':{name:'e'*64 for name in headers}},'android':{}}
   for mode in ('release','address','undefined','finite-fixture'):
    (out/('host-'+mode)).write_bytes(b'explicit mock host binary');(out/(mode+'.rgba')).write_bytes(packet)
    q['host'][mode]={'native':result('host-linux'),'binary_sha256':contract.sha(out/('host-'+mode)),'packet_sha256':packet_sha}
   for abi,(_,machine) in contract.ABI.items():
    (out/abi).mkdir();p=out/abi/'coh_gpu_egl_test';p.write_bytes(elf(machine));q['android'][abi]={'binary':abi+'/coh_gpu_egl_test','binary_sha256':contract.sha(p),'bytes':p.stat().st_size,'elf_machine':machine,'compiler_sha256':'f'*64,'built':True,'executed':False}
   def admit(value):
    (out/'qualification.json').write_text(json.dumps(value));return driver.admit(root,out)
   self.assertTrue(admit(q)['passed'])
   for key in ('source_commit','source_tree','source_sha256','pillow','android','host'):
    changed=copy.deepcopy(q);changed[key]={} if isinstance(changed[key],dict) else 'bad'
    with self.assertRaises(ValueError):admit(changed)
   changed=copy.deepcopy(q);name='native-android/engine/world-render-adapter/run_gpu_egl_android.py';changed['source_sha256'][name]='0'*64
   with self.assertRaises(ValueError):admit(changed)
   (out/'x86_64/coh_gpu_egl_test').write_bytes(elf(183))
   with self.assertRaises(ValueError):admit(q)

 def test_artifact_symlink_and_escape_rejection(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp);(p/'target').write_bytes(b'bytes');(p/'link').symlink_to(p/'target')
   with self.assertRaises(ValueError):driver.checked_file(p,'link',20)
   with self.assertRaises(ValueError):driver.checked_file(p,'../outside',20)

 def test_fixture_admission_refuses_unpinned_and_native_extra(self):
  with self.assertRaises(ValueError):contract.fixture_header(b'\0'*43990)
  value=result();value['extra']=True
  with self.assertRaises(ValueError):contract.native(value,'android')

if __name__=='__main__':unittest.main()
