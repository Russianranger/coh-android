"""Synthetic probe values and tiny actual host children only; never Map evidence."""
import hashlib,json,os,re,stat,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
if __package__:
 from . import probe as p
else:
 import probe as p

def value():
 out={'schema':p.SCHEMA,**{name:False for name in p.SOURCE_BOOLS},
  'stage':'INSTALL','refusal':'NONE','folder_failure':'NONE','owner_failure':'NONE','loader_status':0,
  **{name:0 for name in p.COUNTERS}}
 out.update(diagnostic_only=True,queue_empty=True,queue_writers_idle=True,
  update_idle=True,callbacks_idle=True,setters_idle=True)
 return out
def raw(item=None):return (json.dumps(value() if item is None else item,separators=(',',':'))+'\n').encode('ascii')
def fd_count():
 path=Path('/proc/self/fd');return len(tuple(path.iterdir())) if path.is_dir() else None
class Host:
 def __init__(self,data=None,*,sleep=0,bind=True):
  self.temp=tempfile.TemporaryDirectory(prefix='coh-synthetic-probe-');self.root=Path(self.temp.name)
  self.path=self.root/'probe.json';self.owner=p.precreate(self.path)
  self.streams=[os.fdopen(os.open(self.root/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') for name in ('stdout','stderr')]
  script=('import os,stat,sys,time;from pathlib import Path\n'
   'q=Path(sys.argv[1]);s=q.stat()\n'
   'if not (stat.S_ISREG(s.st_mode) and stat.S_IMODE(s.st_mode)==0o600 and s.st_nlink==1 and s.st_size==0):raise SystemExit(3)\n'
   'q.write_bytes(sys.argv[2].encode("ascii"));time.sleep(float(sys.argv[3]))')
  self.child=subprocess.Popen([sys.executable,'-c',script,str(self.path),(raw() if data is None else data).decode('ascii'),str(sleep)],stdout=self.streams[0],stderr=self.streams[1])
  self.children=[self.child];self.handles=list(self.streams)
  if bind:p.bind(self.owner,self.child,self.streams,self.children,self.handles)
 def finish(self):
  code=self.child.wait(timeout=5)
  for stream in self.streams:stream.close()
  return code
 def collect(self,**kwargs):return p.collect(self.owner,self.child,cleanup_attempted=True,**kwargs)
 def close(self):
  if self.child.poll() is None:self.child.kill()
  self.child.wait(timeout=5)
  for stream in self.streams:stream.close()
  self.temp.cleanup()
 def __enter__(self):return self
 def __exit__(self,*_):self.close()

class ProbeTests(unittest.TestCase):
 def test_exact_source_emitter_schema_and_fixed_names(self):
  text=Path(__file__).with_name('source_group_profile.inc').read_text()
  for name,expected in [('coh_fp_stages',p.STAGES),('coh_fp_refusals',p.REFUSALS),('coh_fp_failures',p.FOLDER_FAILURES)]:
   matches=re.findall(r'\b'+name+r'\[\]\s*=\s*\{([^}]+)\}',text)
   self.assertEqual(len(matches),1);self.assertEqual(tuple(re.findall(r'"([A-Z_]+)"',matches[0])),expected)
  fields=re.findall(r'\\"([a-z_]+)\\":',text)
  self.assertEqual(len(fields),36);self.assertEqual(set(fields),p.SOURCE_KEYS)
  self.assertIn('COH_FRESH_PROBE_MAX 8192u',text)
  header=Path(__file__).with_name('source_group_profile_api.h').read_text()
  self.assertEqual(('NONE',*re.findall(r'^ X\(([A-Z_]+),',header,re.M)),p.OWNER_FAILURES)

 def test_strict_parser_types_keys_enums_and_source_bounds(self):
  good=value();self.assertEqual(p.parse(raw(good)),good)
  bad=[]
  for name in good:
   item=dict(good);del item[name];bad.append(item)
  for name in p.SOURCE_BOOLS:
   item=dict(good);item[name]=1;bad.append(item)
  for name in p.COUNTERS:
   for number in (-1,True,65536,1.0):
    item=dict(good);item[name]=number;bad.append(item)
  for name in p.ENUMS:
   item=dict(good);item[name]='PRIVATE_ACCOUNT_PATH_CANARY';bad.append(item)
  for field in ('source_generation_admitted','world_authority'):
   item=dict(good);item[field]=True;bad.append(item)
  for number in (-1,True,9,1.0):
   item=dict(good);item['loader_status']=number;bad.append(item)
  item=dict(good);item['diagnostic_only']=False;bad.append(item)
  item=dict(good);item['queue_count']=1;bad.append(item)
  for item in bad:
   with self.subTest(item=item),self.assertRaisesRegex(p.ProbeRefused,'^PROBE_PARSE_REFUSED$'):p.parse(raw(item))
  for data in (b'{}',b'[]',raw()[:-2]+b',"stage":"INSTALL"}\n',b'\xff',b'x'*8192,b'{"schema":NaN}'):
   with self.subTest(data=data[:20]),self.assertRaises(p.ProbeRefused):p.parse(data)

 def test_owner_reason_v2_fixed_vocabulary_and_no_legacy_normalization(self):
  for reason in p.OWNER_FAILURES:
   candidate=value();candidate['owner_failure']=reason
   self.assertEqual(p.parse(raw(candidate))['owner_failure'],reason)
  for reason in (0,True,None,{},'PRIVATE_OWNER_ID_PATH_CANARY','COH_FRESH_OWNER_LINK_PENDING'):
   candidate=value();candidate['owner_failure']=reason
   with self.assertRaises(p.ProbeRefused):p.parse(raw(candidate))
  old=value();old['schema']='coh-fresh-source-profile-probe-v1';del old['owner_failure']
  with self.assertRaises(p.ProbeRefused):p.parse(raw(old))
  old_public=p.empty();old_public['schema']='coh-fresh-source-profile-diagnostic-v1'
  with self.assertRaises(p.ProbeRefused):p.public(old_public)

 def test_actual_owned_child_owner_reason_projection_excludes_private_binding(self):
  candidate=value();candidate['owner_failure']='LINK_PENDING';candidate['stage']='OWNER'
  candidate['refusal']='BOUNDARY_REFUSED';candidate['complete']=True
  with Host(raw(candidate)) as host:
   self.assertEqual(host.finish(),0);public,private=host.collect()
   self.assertEqual(public['schema'],'coh-fresh-source-profile-diagnostic-v2')
   self.assertEqual(public['probe_state'],'VALID');self.assertEqual(public['owner_failure'],'LINK_PENDING')
   self.assertEqual(public['stage'],'OWNER');self.assertFalse(public['source_generation_admitted'] or public['world_authority'])
   self.assertTrue(private['same_owned_closed_child_and_streams_verified'])
   self.assertNotIn(str(host.path),json.dumps(public));self.assertNotIn('owned_child_pid',public)

 def test_actual_child_preexisting_file_and_private_public_separation(self):
  with Host() as host:
   self.assertEqual(host.finish(),0);public,private=host.collect()
   self.assertEqual(public['probe_state'],'VALID');self.assertTrue(public['probe_validated'])
   self.assertTrue(public['process_closed'] and public['handles_closed'] and public['cleanup_attempted'])
   self.assertFalse(public['world_authority'] or public['source_generation_admitted'])
   self.assertEqual(private['owned_child_pid'],host.child.pid)
   self.assertEqual(private['probe_sha256'],hashlib.sha256(host.path.read_bytes()).hexdigest())
   self.assertIs(private['public_upload_permitted'],False)
   self.assertEqual(p.public(public),public)
   self.assertFalse(set(private)&{'owned_child_pid','file_device','file_inode','file_uid','probe_sha256'} & set(public))

 def test_optional_unavailable_empty_and_not_launched(self):
  public,private=p.collect(None,None);self.assertEqual(public,p.empty());self.assertIsNone(private)
  with tempfile.TemporaryDirectory() as temp:
   owner=p.precreate(Path(temp)/'probe');public,private=p.collect(owner,None,cleanup_attempted=True)
   self.assertEqual(public['probe_state'],'UNAVAILABLE');self.assertFalse(public['process_started']);self.assertIsNone(private)
  with Host(b'') as host:
   self.assertEqual(host.finish(),0);public,private=host.collect()
   self.assertEqual(public['probe_state'],'UNAVAILABLE');self.assertTrue(public['process_closed']);self.assertIsNone(private)

 def test_closure_and_cleanup_gates_precede_read(self):
  with Host(sleep=1) as host:
   with patch.object(p,'_read_owned',side_effect=AssertionError('MUST_NOT_READ')) as read:
    public,private=host.collect();self.assertEqual(public['probe_state'],'REFUSED');read.assert_not_called()
   self.assertEqual(host.finish(),0)
   for attempted in (False,1,None):
    with patch.object(p,'_read_owned',side_effect=AssertionError('MUST_NOT_READ')) as read:
     public,private=p.collect(host.owner,host.child,cleanup_attempted=attempted)
     self.assertEqual(public['probe_state'],'REFUSED');self.assertIsNone(private);read.assert_not_called()
   public,private=host.collect();self.assertEqual(public['probe_state'],'VALID')

 def test_binding_requires_actual_registered_objects_and_atomic_publication(self):
  with Host(bind=False) as host:
   for children,streams,handles in [([],host.streams,host.handles),(host.children,host.streams,[]),
     (host.children,[host.streams[0],host.streams[0]],host.handles),(host.children,host.streams[:1],host.handles)]:
    with self.assertRaisesRegex(p.ProbeRefused,'^PROBE_BIND_REFUSED$'):p.bind(host.owner,host.child,streams,children,handles)
    self.assertIsNone(host.owner.binding)
   p.bind(host.owner,host.child,host.streams,host.children,host.handles)
   with self.assertRaises(p.ProbeRefused):p.bind(host.owner,host.child,host.streams,host.children,host.handles)
   self.assertEqual(host.finish(),0)
   host.children.clear();public,private=host.collect();self.assertEqual(public['probe_state'],'REFUSED');self.assertIsNone(private)

 def test_file_ownership_replacements_and_parent_privacy_refuse(self):
  for kind in ('mode','link','replacement','symlink','fifo','parent_mode','missing','wrong_uid'):
   with self.subTest(kind=kind),Host() as host:
    self.assertEqual(host.finish(),0)
    if kind=='mode':host.path.chmod(0o644)
    elif kind=='link':os.link(host.path,host.root/'extra')
    elif kind in ('replacement','symlink','fifo'):
     host.path.rename(host.root/'original')
     if kind=='replacement':host.path.write_bytes(raw());host.path.chmod(0o600)
     elif kind=='symlink':host.path.symlink_to(host.root/'original')
     else:os.mkfifo(host.path,0o600)
    elif kind=='parent_mode':host.root.chmod(0o755)
    elif kind=='missing':host.path.unlink()
    if kind=='wrong_uid':
     with patch.object(p.os,'geteuid',return_value=os.geteuid()+1):public,private=host.collect()
    else:public,private=host.collect()
    self.assertEqual(public['probe_state'],'REFUSED');self.assertIsNone(private)
    host.root.chmod(0o700)

 def test_precreate_refuses_existing_and_rolls_back_owned_failures(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);path=root/'probe';path.write_bytes(b'PRIVATE_PRESERVE');path.chmod(0o600)
   with self.assertRaises(p.ProbeRefused):p.precreate(path)
   self.assertEqual(path.read_bytes(),b'PRIVATE_PRESERVE');path.unlink()
   before=fd_count()
   with patch.object(p.os,'fsync',side_effect=OSError('PRIVATE_IO_CANARY')):
    with self.assertRaisesRegex(p.ProbeRefused,'^PROBE_PRECREATE_REFUSED$'):p.precreate(path)
   self.assertFalse(path.exists());self.assertEqual(fd_count(),before)
   original=p.os.close;calls=0
   def fail_after_close(descriptor):
    nonlocal calls
    original(descriptor);calls+=1
    if calls==1:raise OSError('PRIVATE_CLOSE_CANARY')
   with patch.object(p.os,'close',side_effect=fail_after_close):
    with self.assertRaises(p.ProbeRefused):p.precreate(path)
   self.assertFalse(path.exists());self.assertEqual(fd_count(),before)

 def test_failed_precreate_preserves_foreign_replacement(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);path=root/'probe'
   def replace(_):
    path.rename(root/'original');path.write_bytes(b'FOREIGN_REPLACEMENT_CANARY');path.chmod(0o600)
    raise OSError('CONTROLLED_FAILURE')
   with patch.object(p.os,'fsync',side_effect=replace),self.assertRaises(p.ProbeRefused):p.precreate(path)
   self.assertEqual(path.read_bytes(),b'FOREIGN_REPLACEMENT_CANARY');self.assertTrue((root/'original').exists())

 def test_mutation_and_same_bytes_inode_swap_during_read_refuse(self):
  for replace in (False,True):
   with self.subTest(replace=replace),Host() as host:
    self.assertEqual(host.finish(),0);original=p._read_fd;calls=0
    def changed(descriptor):
     nonlocal calls
     data=original(descriptor);calls+=1
     if calls==1:
      if replace:host.path.rename(host.root/'original');host.path.write_bytes(data);host.path.chmod(0o600)
      else:host.path.write_bytes(data.replace(b'INSTALL',b'INSTXLL'))
     return data
    with patch.object(p,'_read_fd',side_effect=changed):public,private=host.collect()
    self.assertEqual(public['probe_state'],'REFUSED');self.assertIsNone(private)

 def test_privacy_canaries_unknown_fields_and_public_reconstruction(self):
  canary='PRIVATE_ACCOUNT_PATH_HASH_PAYLOAD_PID_CANARY'
  for field,item in [('account',canary),('path',canary),('sha256',canary),('payload',{'nested':canary}),('pid',1234567)]:
   data=value();data[field]=item
   with self.subTest(field=field),Host(raw(data)) as host:
    self.assertEqual(host.finish(),0);public,private=host.collect()
    self.assertEqual(public['probe_state'],'REFUSED');self.assertIsNone(private)
    self.assertNotIn(canary,json.dumps(public));self.assertNotIn(field,public)
  item=p.empty();item['private_canary']=canary
  with self.assertRaisesRegex(p.ProbeRefused,'^PROBE_PUBLIC_REFUSED$'):p.public(item)
  class PretendsUnavailable:
   def __eq__(self,other):return other=='UNAVAILABLE'
  for name in p.ENUMS:
   item=p.empty();item[name]=PretendsUnavailable()
   with self.assertRaises(p.ProbeRefused):p.public(item)

 def test_final_path_reopen_detects_late_same_inode_write(self):
  with Host() as host:
   self.assertEqual(host.finish(),0);original=p._path_info
   def changed(owner):
    host.path.write_bytes(host.path.read_bytes().replace(b'INSTALL',b'INSTXLL'))
    return original(owner)
   with patch.object(p,'_path_info',side_effect=changed):public,private=host.collect()
   self.assertEqual(public['probe_state'],'REFUSED');self.assertIsNone(private)

 def test_mutation_during_parse_and_late_closed_poll_refuses(self):
  for phase in ('parse','poll'):
   with self.subTest(phase=phase),Host() as host:
    self.assertEqual(host.finish(),0)
    def change():host.path.write_bytes(host.path.read_bytes().replace(b'INSTALL',b'CATALOG'))
    if phase=='parse':
     original=p.parse
     def changed(data):
      result=original(data);change();return result
     target=patch.object(p,'parse',side_effect=changed)
    else:
     original=host.child.poll;calls=0
     def changed():
      nonlocal calls
      result=original();calls+=1
      if calls==3:change()
      return result
     target=patch.object(host.child,'poll',side_effect=changed)
    with target:public,private=host.collect()
    self.assertEqual(public['probe_state'],'REFUSED');self.assertIsNone(private)

 def test_public_saturation_retains_exact_private_source_counts(self):
  data=value();data.update({name:65535 for name in p.COUNTERS})
  data.update(queue_empty=False,queue_writers_idle=False,update_idle=False,callbacks_idle=False,setters_idle=False)
  with Host(raw(data)) as host:
   self.assertEqual(host.finish(),0);public,private=host.collect()
   self.assertEqual(public['probe_state'],'VALID');self.assertTrue(public['counter_saturated'])
   self.assertTrue(all(public[name]==255 for name in p.COUNTERS));self.assertTrue(all(private['source_counters'][name]==65535 for name in p.COUNTERS))

 def test_read_failure_and_repeated_collection_close_all_descriptors(self):
  with Host() as host:
   self.assertEqual(host.finish(),0);before=fd_count()
   with patch.object(p.os,'read',side_effect=OSError('PRIVATE_READ_CANARY')):
    public,private=host.collect();self.assertEqual(public['probe_state'],'REFUSED');self.assertIsNone(private)
   self.assertEqual(fd_count(),before)
   for _ in range(20):self.assertEqual(host.collect()[0]['probe_state'],'VALID')
   self.assertEqual(fd_count(),before)
if __name__=='__main__':unittest.main()
