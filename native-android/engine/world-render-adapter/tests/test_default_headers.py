"""Controlled staging/layout tests; these are NOT the seven authentic bodies."""
import gzip,hashlib,importlib.util,io,json,os,shutil,stat,struct,subprocess,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fixed_default_admitter',HERE/'inspect_default_headers.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
HELPER_FIXTURE=HERE/'qualification/default-header-admission-20261017/pinned-031-read-only-helpers.json.gz'
def zipped(name,body):
 out=io.BytesIO()
 with zipfile.ZipFile(out,'w') as z:z.writestr(name,body)
 return out.getvalue()
def texture(name,unsupported=False):
 dds=bytearray(136);dds[:4]=b'DDS ';struct.pack_into('<I',dds,4,124);struct.pack_into('<I',dds,12,4);struct.pack_into('<I',dds,16,4);struct.pack_into('<I',dds,28,1);struct.pack_into('<I',dds,76,32);struct.pack_into('<I',dds,80,4);dds[84:88]=b'DX10' if unsupported else b'DXT1'
 extra=(name[:-8]+'.dds').encode()+b'\0';header=bytearray(32);struct.pack_into('<IIII',header,0,32+len(extra),len(dds),4,4);header[29:32]=b'TEX';return bytes(header)+extra+dds
class Fixture:
 def __init__(self,root,unsupported=False):
  self.root=root;self.staging=root/'staging';self.payloads=root/'payloads';self.imported=root/'full-original-import-fixture-v1/data'
  for p in (self.staging,self.payloads,self.imported,self.staging/'assets',self.staging/'apk-runtime',self.staging/'owned'):p.mkdir(parents=True,mode=0o700,exist_ok=True)
  raw=HELPER_FIXTURE.read_bytes();assert m.sha(raw)=='8a62c21674d020ad73eed9e340a740133b9eb167ee05a0a3a45c0f15ca76e172';helpers={k:v.encode() for k,v in json.loads(gzip.decompress(raw)).items()}
  for name,body in helpers.items():(self.staging/'apk-runtime'/name).write_bytes(body)
  properties=b'generation=generation-'+b'0'*32+b'\ncontract.sha256='+b'a'*64+b'\ncount=173011\nbytes=2977730517\n';(self.imported.parent/'complete.properties').write_bytes(properties)
  identity={'generation':'generation-'+'0'*32,'receipt_sha256':m.sha(properties),'contract_sha256':'a'*64,'file_count':m.COUNT,'total_bytes':m.BYTES}
  package={'source_commit':'0b75ade0c801735e10c5798f641948a45cc50488','data_commit':'d51533ec8e6a9cf726b9214968077a05fdcf19f3','files':{'CityOfHeroes.exe':{'size':1,'sha256':'b'*64},**{f'{i}.dll':{'size':1,'sha256':'b'*64} for i in range(20)}}}
  prerequisite=m.canonical({'fixture_only':True});archives={'client-runtime.zip':zipped('client-package.json',m.canonical(package)),'client-prerequisites.zip':zipped('client-prerequisites-manifest.json',prerequisite),'client-caches.zip':zipped('client-cache-manifest.json',m.canonical({'prerequisites_manifest_sha256':m.sha(prerequisite)}))}
  for name,body in archives.items():(self.staging/'assets'/name).write_bytes(body)
  expected={'format':1,'source_data':str(self.imported),'import':identity,'package_sha256':m.sha(archives['client-runtime.zip']),'cache_archive_sha256':m.sha(archives['client-caches.zip']),'prerequisites_archive_sha256':m.sha(archives['client-prerequisites.zip']),'prerequisites_manifest_sha256':m.sha(prerequisite),'normalized_mtime_epoch':m.EPOCH}
  data={k:v for k,v in expected.items() if k!='package_sha256'};self.content=m.sha(m.canonical({'data':data,'native':package}));self.work=self.staging/'owned'/('client-work-'+self.content[:24]);(self.work/'data').mkdir(parents=True,mode=0o700)
  marker=dict(expected,content_identity_sha256=self.content,worktree_key=self.work.name,input_files=m.COUNT,input_bytes=m.BYTES,imported_inputs_readonly=True);(self.work/'client-work.json').write_bytes(m.canonical(marker))
  allow=json.loads(m.DEFAULTS.read_bytes());self.paths=[];self.bodies=[]
  for i,entry in enumerate(allow['required_defaults']):
   logical=entry['required_virtual_asset_path'][5:];mixed=logical.replace('/world/','/WORLD/').replace('/filler/','/Filler/');body=texture(mixed,unsupported and i==0);target=self.imported/mixed;target.parent.mkdir(parents=True,mode=0o700,exist_ok=True);target.write_bytes(body);target.chmod(0o444);link=self.work/'data'/mixed;link.parent.mkdir(parents=True,mode=0o700,exist_ok=True);link.symlink_to(target);self.paths.append(link);self.bodies.append(body);entry['whole_body_bytes']=len(body);entry['whole_body_sha256']=m.sha(body)
  self.allow=root/'controlled-allowlist.json';self.allow.write_bytes(m.canonical(allow));self.allow_sha=m.sha(self.allow.read_bytes())
  control={'format':1,'role':'complete_prepared_public_031_native_fx_control','status':'prepared','source_commit':'74fe247be85173e618f1af2c8af71b1316de4cd8','donor_apk':m.DONOR,'native_processes_started':False,'live_sql_started':False,'player_database_used':False,'source_script':{'bytes':m.STAGING_SOURCE.stat().st_size,'sha256':m.sha(m.STAGING_SOURCE.read_bytes())},'packaged_guest_sources':{name:{'bytes':len(body),'sha256':m.sha(body)} for name,body in helpers.items()},'original_import':{'files':m.COUNT,'bytes':m.BYTES,'all_leaf_sha256_checked':True,'contract_sha256':'a'*64},'client_asset_hashes':{name:m.sha(body) for name,body in archives.items()}}
  self.control=self.staging/'control-fixture.json';self.control.write_bytes(m.canonical(control));self.control_sha=m.sha(self.control.read_bytes())
class Admission(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='controlled-default-admission-');self.root=Path(self.temp.name);self.fixture=Fixture(self.root);self.output=self.root/'result.json';self.retain=self.root/'seven';self.patches=[]
  self.adjust(self.fixture)
 def adjust(self,f):
  self.fixture=f;self.patch('DEFAULTS',f.allow);self.patch('DEFAULTS_SHA',f.allow_sha);original=m.source_pins;self.patch('source_pins',lambda committed=True:original(False))
 def patch(self,name,value):
  p=patch.object(m,name,value);p.start();self.patches.append(p)
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def inspect(self,retain=True):return m.inspect(self.fixture.staging,self.fixture.payloads,self.fixture.control_sha,self.output,self.retain if retain else None)
 def unchanged_outputs(self):self.assertFalse(self.output.exists());self.assertFalse(self.retain.exists())
 def test_complete_and_fixed_only_retention(self):
  value=self.inspect();self.assertTrue(value['native_inspection']['seven_header_owner_created']);self.assertFalse(value['current_provider_generation']);self.assertFalse(value['default_identity']);self.assertEqual(set(p.name for p in self.retain.iterdir()),{n+'.texture' for n in m.NAMES}|{'manifest.json'});self.assertEqual([p.read_bytes() for p in (self.retain/(n+'.texture') for n in m.NAMES)],self.fixture.bodies)
  raw=self.output.read_text();self.assertNotIn(str(self.root),raw);self.assertEqual(m.sha((self.retain/'manifest.json').read_bytes()),value['retained_fixed_seven']['manifest_sha256'])
 def test_no_retention_by_default(self):
  value=self.inspect(False);self.assertIsNone(value['retained_fixed_seven']);self.assertFalse(self.retain.exists())
 def test_unsupported_exact_source_can_be_retained(self):
  root=self.root/'unsupported';root.mkdir();self.adjust(Fixture(root,True));value=self.inspect();self.assertEqual(value['native_inspection']['rows'][0]['protected_parser_status'],2);self.assertFalse(value['native_inspection']['seven_header_owner_attempted']);self.assertFalse(value['native_inspection']['seven_header_owner_created']);self.assertEqual((self.retain/'white.texture').read_bytes(),self.fixture.bodies[0])
 def test_wrong_seventh_body_never_publishes(self):
  target=self.fixture.paths[-1].resolve();target.chmod(0o644);target.write_bytes(b'bad');target.chmod(0o444)
  with self.assertRaises(m.Refused):self.inspect()
  self.unchanged_outputs()
 def test_wrong_or_replaced_receipts_and_helpers_refuse(self):
  for target in (self.fixture.control,self.fixture.work/'client-work.json',self.fixture.staging/'apk-runtime/texture_header_index.py'):
   old=target.read_bytes()
   if target.name=='client-work.json':changed=json.loads(old);changed['content_identity_sha256']='0'*64;target.write_bytes(m.canonical(changed))
   else:target.write_bytes(old+b' ')
   with self.assertRaises((m.Refused,ValueError)):self.inspect()
   self.unchanged_outputs();target.write_bytes(old)
 def test_no_glob_or_other_owner_fallback(self):
  renamed=self.fixture.work.with_name('client-work-'+'0'*24);self.fixture.work.rename(renamed)
  with self.assertRaises((m.Refused,OSError)):self.inspect()
  self.unchanged_outputs()
 def test_body_link_escape_and_writable_body_refuse(self):
  target=self.fixture.paths[0].resolve();outside=self.root/'outside.texture';outside.write_bytes(target.read_bytes());outside.chmod(0o444);link=self.fixture.paths[0];link.unlink();link.symlink_to(outside)
  with self.assertRaises(m.Refused):self.inspect()
  self.unchanged_outputs();link.unlink();link.symlink_to(target);target.chmod(0o644)
  with self.assertRaises(m.Refused):self.inspect()
  self.unchanged_outputs()
 def test_output_overlap_and_existing_outputs_refuse(self):
  self.output.write_bytes(b'preserve')
  with self.assertRaises(m.Refused):self.inspect()
  self.assertEqual(self.output.read_bytes(),b'preserve');self.output.unlink();self.output=self.fixture.staging/'result.json'
  with self.assertRaises(m.Refused):self.inspect()
  self.unchanged_outputs()
 def test_late_native_source_mutation_refuses(self):
  original=m.native_inspection
  def changed(bodies,temp,pins):
   value=original(bodies,temp,pins);target=self.fixture.paths[0].resolve();target.chmod(0o644);target.write_bytes(bodies[0]);target.chmod(0o444);return value
  self.patch('native_inspection',changed)
  with self.assertRaises(m.Refused):self.inspect()
  self.unchanged_outputs()
 def test_every_retention_and_receipt_write_rolls_back(self):
  original=m.write_new
  for fail in range(1,10):
   calls=[0]
   def write(path,body,created):
    calls[0]+=1
    if calls[0]==fail:
     with path.open('xb') as stream:created.append((path,m.stamp(os.fstat(stream.fileno()))[:3]));stream.write(body[:3])
     raise OSError('controlled late I/O')
    original(path,body,created)
   with patch.object(m,'write_new',write),self.assertRaises(OSError):self.inspect()
   self.unchanged_outputs()
 def test_source_recheck_after_manifest_and_after_result_rolls_back(self):
  for fail in (2,3,4):
   entries,bodies,proof,verify,_=m.resolve_inputs(self.fixture.staging,self.fixture.payloads,self.fixture.control_sha);calls=[0]
   def refuse():
    calls[0]+=1;verify()
    if calls[0]==fail:raise m.Refused('CONTROLLED_FINAL_SOURCE_CHANGE')
   admission={k:proof[k] for k in ('control_fixture_sha256','client_work_receipt_sha256','client_content_identity_sha256')}
   with self.assertRaises(m.Refused):m.publish(self.output,self.retain,entries,bodies,admission,refuse)
   self.unchanged_outputs()
 def test_write_or_flush_failure_survives_close_failure(self):
  opened=Path.open
  for stage in ('write','flush'):
   closed=[];created=[]
   class Broken:
    def __init__(self,stream):self.stream=stream
    def fileno(self):return self.stream.fileno()
    def write(self,body):
     self.stream.write(body[:3])
     if stage=='write':raise OSError('controlled primary write')
    def flush(self):raise OSError('controlled primary flush')
    def close(self):self.stream.close();closed.append(True);raise OSError('controlled secondary close')
   def opening(path,*args,**kwargs):
    stream=opened(path,*args,**kwargs);return Broken(stream) if path==self.output else stream
   with patch.object(Path,'open',opening),self.assertRaisesRegex(OSError,'controlled primary '+stage) as caught:m.write_new(self.output,b'abcdef',created)
   self.assertEqual(closed,[True]);self.assertEqual(len(created),1);self.assertIn('OUTPUT_CLOSE_SECONDARY_FAILURES=1',caught.exception.__notes__);caught.exception.add_note(str(self.root));self.assertEqual(m.failure_result(caught.exception),{'passed':False,'failure_code':'DEPENDENCY_OR_SOURCE_FAILURE','secondary_failure_counts':{'OUTPUT_CLOSE_SECONDARY_FAILURES':1}});self.output.unlink()
 def test_rollback_continues_after_unlink_failure(self):
  entries,bodies,proof,verify,_=m.resolve_inputs(self.fixture.staging,self.fixture.payloads,self.fixture.control_sha)
  admission={k:proof[k] for k in ('control_fixture_sha256','client_work_receipt_sha256','client_content_identity_sha256')};unlink=Path.unlink;rmdir=Path.rmdir
  for blocked,failures in ((self.output,1),(self.retain/'manifest.json',2)):
   calls=[0];removed=[];directories=[]
   def refuse():
    calls[0]+=1;verify()
    if calls[0]==4:raise m.Refused('CONTROLLED_PRIMARY_FINAL_SOURCE_CHANGE')
   def removing(path,*args,**kwargs):
    removed.append(path)
    if path==blocked:raise OSError('controlled secondary unlink')
    return unlink(path,*args,**kwargs)
   def removing_directory(path,*args,**kwargs):directories.append(path);return rmdir(path,*args,**kwargs)
   with patch.object(Path,'unlink',removing),patch.object(Path,'rmdir',removing_directory),self.assertRaisesRegex(m.Refused,'CONTROLLED_PRIMARY_FINAL_SOURCE_CHANGE') as caught:m.publish(self.output,self.retain,entries,bodies,admission,refuse)
   self.assertEqual(len(removed),9);self.assertEqual(directories,[self.retain]);self.assertIn('ROLLBACK_SECONDARY_FAILURES='+str(failures),caught.exception.__notes__);self.assertEqual(m.failure_result(caught.exception),{'passed':False,'failure_code':'CONTROLLED_PRIMARY_FINAL_SOURCE_CHANGE','secondary_failure_counts':{'ROLLBACK_SECONDARY_FAILURES':failures}})
   self.assertEqual([p for p in removed if p.exists()],[blocked]);blocked.unlink()
   if self.retain.exists():self.retain.rmdir()
   self.unchanged_outputs()
 def test_directory_fsync_failure_survives_close_failure(self):
  entries,bodies,proof,verify,_=m.resolve_inputs(self.fixture.staging,self.fixture.payloads,self.fixture.control_sha);admission={k:proof[k] for k in ('control_fixture_sha256','client_work_receipt_sha256','client_content_identity_sha256')};fsync=os.fsync;close=os.close;failed=[]
  def syncing(fd):
   if stat.S_ISDIR(os.fstat(fd).st_mode):failed.append(fd);raise OSError('controlled primary directory fsync')
   return fsync(fd)
  def closing(fd):
   close(fd)
   if fd in failed:raise OSError('controlled secondary directory close')
  with patch.object(m.os,'fsync',syncing),patch.object(m.os,'close',closing),self.assertRaisesRegex(OSError,'controlled primary directory fsync') as caught:m.publish(self.output,self.retain,entries,bodies,admission,verify)
  self.assertEqual(len(failed),1);self.assertIn('DIRECTORY_CLOSE_SECONDARY_FAILURES=1',caught.exception.__notes__);self.unchanged_outputs()
 def test_native_source_and_executable_brackets_refuse(self):
  pins=m.source_pins(False);changed=dict(pins,controlled_change={'bytes':1,'sha256':'0'*64});run=m.subprocess.run
  for index in (0,1):
   directory=self.root/('source-bracket-'+str(index));directory.mkdir();observed=[];answers=iter([changed] if index==0 else [pins,changed])
   def running(*args,**kwargs):observed.append(args[0]);return run(*args,**kwargs)
   with patch.object(m,'source_pins',lambda committed=True:next(answers)),patch.object(m.subprocess,'run',running),self.assertRaisesRegex(m.Refused,'ADMITTER_SOURCE_CHANGED'):m.native_inspection(self.fixture.bodies,directory,pins)
   self.assertEqual(len(observed),index)
  directory=self.root/'executable-bracket';directory.mkdir()
  def changed_binary(command,*args,**kwargs):
   result=run(command,*args,**kwargs)
   if command[0]==str(directory/'inspect-default-headers'):
    with (directory/'inspect-default-headers').open('ab') as stream:stream.write(b'controlled post-execution change')
   return result
  with patch.object(m.subprocess,'run',changed_binary),self.assertRaisesRegex(m.Refused,'NATIVE_EXECUTABLE_CHANGED'):m.native_inspection(self.fixture.bodies,directory,pins)
if __name__=='__main__':unittest.main()
