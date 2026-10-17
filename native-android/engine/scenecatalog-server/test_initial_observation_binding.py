#!/usr/bin/env python3
"""Typed synthetic initial/GROUPS byte closure; no server or native capture."""
import copy,hashlib,json,os,tempfile,unittest
from pathlib import Path
from unittest import mock
import capture_groups_transaction as c

class Controls(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='coh-initial-binding-');self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.received=self.root/'received';self.target=self.root/'retained'
  self.received.mkdir(mode=0o700);self.target.mkdir(mode=0o700)
  self.group_bytes=b'explicit synthetic GROUPS bytes';self.packet=b'explicit synthetic ALLENTS bytes'
  self.group_pin={'bytes':len(self.group_bytes),'sha256':hashlib.sha256(self.group_bytes).hexdigest()}
  self.pair={'passed':True,'exact_logical_packet_verified':True,'native_packet':self.group_pin}
  self.groups={'schema':'coh-local-scene-capture-v1','passed':True,'packet_sha256':self.group_pin['sha256'],
   'message_id':11,**{name:1 for name in c.INITIAL_OWNER}}
  self.groups.update(transport_version=5,selected_slot=0,opened_sockets=2,closed_sockets=2)
  self.receipt={'schema':'coh-private-initial-observation-v1','passed':True,
   **{name:True for name in c.INITIAL_TRUE},**{name:False for name in c.INITIAL_FALSE},
   **{name:self.groups[name] for name in c.INITIAL_OWNER},'reqallents_sent':1,'failure_code':'NONE','status':2,
   'groups_packet_sha256':self.group_pin['sha256'],'groups_message_generation':4,'groups_message_id':11,
   'raw_allents_loan_verified':True,'bytes':len(self.packet),'payload_bits':len(self.packet)*8,
   'post_command_cursor':6,'byte_aligned':0,'ordered':1,'message_id':12,'ordered_id':2,'message_generation':5,
   'packet_sha256':hashlib.sha256(self.packet).hexdigest(),'accessible_commands':17,'shortcuts':[[1,1],[9,0]],
   'update_prefix':{name:0 for name in c.INITIAL_PREFIX}}
  self.receipt['update_prefix'].update(command=3,full_update_id=1,odd_send=1,interp_level=2,interp_precision=1,entity_tail_bit=96)
  for directory in (self.received,self.target):
   self.write(directory/'groups.bin',self.group_bytes);self.write(directory/'capture.json',json.dumps(self.groups).encode())
  self.emit(self.receipt);self.write(self.received/'initial-update.bin',self.packet)
 def write(self,path,raw):path.write_bytes(raw);path.chmod(0o600)
 def emit(self,value):self.write(self.received/'initial-observation.json',json.dumps(value).encode())
 def bind(self):return c.initial_input(self.received,self.pair)
 def refused(self,receipt):
  self.emit(receipt)
  with self.assertRaises((c.d.Refused,OSError)):self.bind()
 def test_successful_typed_binding_retains_only_two_private_files_after_cleanup(self):
  binding=self.bind();self.assertEqual(binding['status'],'OBSERVED');self.assertTrue(binding['same_groups_owner_verified'])
  self.assertEqual(binding['packet'],{'bytes':len(self.packet),'sha256':hashlib.sha256(self.packet).hexdigest()})
  report={'passed':True,'matching_groups_transaction_captured':True,'cleanup_verified':True,'pair':self.pair}
  c.finish_initial_observation(report,{'build_schema':c.INITIAL_BUILD_SCHEMA},self.received,self.target)
  self.assertTrue(report['passed']);self.assertTrue(report['initial_observation']['retained_after_owned_cleanup'])
  self.assertEqual(set(p.name for p in self.target.iterdir()),{'capture.json','groups.bin','initial-observation.json','initial-update.bin'})
  for name in ('initial-observation.json','initial-update.bin'):
   self.assertEqual((self.target/name).read_bytes(),(self.received/name).read_bytes());self.assertEqual((self.target/name).stat().st_mode&0o777,0o600)
  for key in ('source_generation_admitted','complete_initial_character','actor_publication','ack_permitted','world_authority'):
   self.assertIs(report['initial_observation'][key],False)
 def test_cleanup_and_groups_gate_precede_every_optional_read_or_copy(self):
  native={'build_schema':c.INITIAL_BUILD_SCHEMA}
  for change,status in (({'passed':False},'CLEANUP_NOT_VERIFIED'),({'cleanup_verified':False},'CLEANUP_NOT_VERIFIED'),
    ({'cleanup_verified':1},'CLEANUP_NOT_VERIFIED'),({'matching_groups_transaction_captured':False},'GROUPS_NOT_PAIRED')):
   report={'passed':True,'cleanup_verified':True,'matching_groups_transaction_captured':True,'pair':self.pair,**change};before=copy.deepcopy(report)
   with mock.patch.object(c,'retain_initial_observation') as retain:c.finish_initial_observation(report,native,self.received,self.target);retain.assert_not_called()
   self.assertEqual(report['initial_observation']['status'],status)
   for name,value in before.items():self.assertEqual(report[name],value)
  report={'passed':True}
  with mock.patch.object(c,'retain_initial_observation') as retain:c.finish_initial_observation(report,{},self.received,self.target);retain.assert_not_called()
  self.assertEqual(report,{'passed':True})
 def test_missing_invalid_or_failed_initial_does_not_discard_groups(self):
  report={'passed':True,'cleanup_verified':True,'matching_groups_transaction_captured':True,'pair':self.pair}
  path=self.received/'initial-observation.json';path.unlink()
  for status in ('ABSENT','REFUSED'):
   c.finish_initial_observation(report,{'build_schema':c.INITIAL_BUILD_SCHEMA},self.received,self.target)
   self.assertTrue(report['passed']);self.assertEqual(report['initial_observation']['status'],status)
   self.write(path,b'{"schema":"invalid"}')
  failed=copy.deepcopy(self.receipt);failed.update(passed=False,raw_allents_loan_verified=False,failure_code='HEADER',packet_sha256='',shortcuts=[])
  for name in c.INITIAL_VALUES:failed[name]=0
  failed['update_prefix']={name:0 for name in c.INITIAL_PREFIX};self.emit(failed);(self.received/'initial-update.bin').unlink()
  c.finish_initial_observation(report,{'build_schema':c.INITIAL_BUILD_SCHEMA},self.received,self.target)
  self.assertTrue(report['passed']);self.assertEqual(report['initial_observation']['status'],'DIAGNOSTIC_REFUSED')
  self.assertFalse((self.target/'initial-update.bin').exists());self.assertTrue((self.target/'initial-observation.json').is_file())
 def test_exact_schema_boolean_integer_and_failure_shape_refusals(self):
  for name in self.receipt:
   value=copy.deepcopy(self.receipt);del value[name]
   with self.subTest(omitted=name):self.refused(value)
  value=copy.deepcopy(self.receipt);value['private_canary']='must not be exported';self.refused(value)
  for name,value in self.receipt.items():
   if type(value) is int:
    changed=copy.deepcopy(self.receipt);changed[name]=bool(value)
    with self.subTest(boolean_integer=name):self.refused(changed)
  for name in (*c.INITIAL_TRUE,*c.INITIAL_FALSE,'passed','raw_allents_loan_verified'):
   changed=copy.deepcopy(self.receipt);changed[name]=int(changed[name]);self.refused(changed)
  for name,value in (('failure_code','caller-error-canary'),('status',0),('reqallents_sent',0),('message_generation',4)):
   changed=copy.deepcopy(self.receipt);changed[name]=value;self.refused(changed)
  self.emit(self.receipt);path=self.received/'initial-observation.json';raw=path.read_bytes();self.write(path,raw[:-1]+b',"passed":true}')
  with self.assertRaises(c.d.Refused):self.bind()
 def test_every_groups_owner_and_exact_packet_binding(self):
  for name in (*c.INITIAL_OWNER,'groups_message_id'):
   value=copy.deepcopy(self.receipt);value[name]+=1
   with self.subTest(owner=name):self.refused(value)
  value=copy.deepcopy(self.receipt);value['groups_packet_sha256']='0'*64;self.refused(value)
  self.emit(self.receipt);self.write(self.received/'groups.bin',b'different groups')
  with self.assertRaises(c.d.Refused):self.bind()
  self.write(self.received/'groups.bin',self.group_bytes);self.write(self.received/'initial-update.bin',b'different initial')
  with self.assertRaises(c.d.Refused):self.bind()
 def test_bounded_profile_shortcut_and_prefix_refusals(self):
  for name,value in (('bytes',c.INITIAL_PACKET_MAX+1),('payload_bits',len(self.packet)*8+1),('post_command_cursor',len(self.packet)*8),
    ('payload_bits',len(self.packet)*8-8),('byte_aligned',2),('ordered',2),('accessible_commands',1025),('packet_sha256','0'*64),('shortcuts',[[1,1],[1,0]]),
    ('shortcuts',[[0,1]]),('shortcuts',[[1,11]]),('shortcuts',[[True,1]]),('shortcuts',[[1,True]]),('shortcuts',[[1,1]]*257)):
   changed=copy.deepcopy(self.receipt);changed[name]=value;self.refused(changed)
  changed=copy.deepcopy(self.receipt);changed.update(byte_aligned=1,payload_bits=len(self.packet)*8-1);self.refused(changed)
  for name,value in (('command',2),('odd_send',0),('odd_send',2),('has_debug_info',2),('interp_level',4),('interp_precision',4),('command_count',257),('entity_tail_bit',0),('entity_tail_bit',self.receipt['payload_bits'])):
   changed=copy.deepcopy(self.receipt);changed['update_prefix'][name]=value;self.refused(changed)
  for name in c.INITIAL_PREFIX:
   changed=copy.deepcopy(self.receipt);changed['update_prefix'][name]=True;self.refused(changed)
 def test_private_regular_receipt_and_packet_ownership(self):
  for name in ('initial-observation.json','initial-update.bin'):
   path=self.received/name;raw=path.read_bytes();path.chmod(0o644)
   with self.subTest(public=name),self.assertRaises(c.d.Refused):self.bind()
   path.chmod(0o600);link=self.root/('link-'+name);os.link(path,link)
   with self.subTest(hardlink=name),self.assertRaises(c.d.Refused):self.bind()
   link.unlink();path.unlink();link.write_bytes(raw);link.chmod(0o600);path.symlink_to(link)
   with self.subTest(symlink=name),self.assertRaises(c.d.Refused):self.bind()
   path.unlink();link.unlink();self.write(path,raw)
 def test_failed_shape_cannot_smuggle_payload_or_unknown_failure(self):
  failed=copy.deepcopy(self.receipt);failed.update(passed=False,raw_allents_loan_verified=False,
   failure_code='TIMEOUT',status=5,packet_sha256='',shortcuts=[])
  for name in c.INITIAL_VALUES:failed[name]=0
  failed['update_prefix']={name:0 for name in c.INITIAL_PREFIX}
  (self.received/'initial-update.bin').unlink();self.emit(failed)
  self.assertEqual(self.bind()['status'],'DIAGNOSTIC_REFUSED')
  for name,value in (('packet_sha256','0'*64),('bytes',1),('raw_allents_loan_verified',True),
    ('failure_code','NONE'),('failure_code','private exception canary'),('reqallents_sent',2),('status',0)):
   changed=copy.deepcopy(failed);changed[name]=value;self.refused(changed)
  self.emit(failed);self.write(self.received/'initial-update.bin',b'unexpected failed packet')
  with self.assertRaises(c.d.Refused):self.bind()
 def test_final_recheck_mutation_rolls_back_only_optional_files(self):
  real_input=c.initial_input;calls=0
  def changing_input(*args):
   nonlocal calls
   calls+=1
   if calls==2:self.write(self.received/'initial-update.bin',b'changed after private copy')
   return real_input(*args)
  with mock.patch.object(c,'initial_input',side_effect=changing_input):result=c.retain_initial_observation(self.received,self.target,self.pair)
  self.assertEqual(result['status'],'RETENTION_FAILED');self.assertTrue(result['retention_rollback_complete'])
  self.assertEqual(set(p.name for p in self.target.iterdir()),{'capture.json','groups.bin'})
 def test_final_target_rechecks_cover_groups_and_earlier_initial_file(self):
  real_input=c.initial_input
  for name in ('groups.bin','capture.json','initial-observation.json'):
   calls=0;original=(self.target/name).read_bytes() if (self.target/name).exists() else None
   def changing_input(*args):
    nonlocal calls
    calls+=1
    if calls==2:self.write(self.target/name,b'changed retained target after copies')
    return real_input(*args)
   with mock.patch.object(c,'initial_input',side_effect=changing_input):result=c.retain_initial_observation(self.received,self.target,self.pair)
   self.assertEqual(result['status'],'RETENTION_FAILED');self.assertTrue(result['retention_rollback_complete'])
   self.assertFalse((self.target/'initial-observation.json').exists());self.assertFalse((self.target/'initial-update.bin').exists())
   if original is not None:self.write(self.target/name,original)
 def test_replaced_target_is_preserved_during_owned_rollback(self):
  real_input=c.initial_input;calls=0
  def replacing_input(*args):
   nonlocal calls
   calls+=1
   if calls==2:
    replacement=self.target/'replacement';self.write(replacement,b'existing replacement must survive')
    os.replace(replacement,self.target/'initial-observation.json')
   return real_input(*args)
  with mock.patch.object(c,'initial_input',side_effect=replacing_input):result=c.retain_initial_observation(self.received,self.target,self.pair)
  self.assertEqual(result['status'],'RETENTION_FAILED');self.assertFalse(result['retention_rollback_complete'])
  self.assertEqual((self.target/'initial-observation.json').read_bytes(),b'existing replacement must survive')
  self.assertFalse((self.target/'initial-update.bin').exists());self.assertEqual((self.target/'groups.bin').read_bytes(),self.group_bytes)
 def test_rollback_refusal_is_visible_and_never_claims_retention(self):
  real_unlink=Path.unlink
  def denied_unlink(path,*args,**kwargs):
   if path==self.target/'initial-observation.json':raise OSError('private unlink canary')
   return real_unlink(path,*args,**kwargs)
  with mock.patch.object(c.os,'fsync',side_effect=OSError('private primary canary')),mock.patch.object(Path,'unlink',denied_unlink):
   result=c.retain_initial_observation(self.received,self.target,self.pair)
  self.assertEqual(result['status'],'RETENTION_FAILED');self.assertFalse(result['retention_rollback_complete'])
  self.assertNotIn('retained_after_owned_cleanup',result);self.assertFalse(result['bounded_raw_allents_observed'])
  self.assertEqual((self.target/'groups.bin').read_bytes(),self.group_bytes)
 def test_existing_output_and_late_copy_refusals_preserve_groups(self):
  collision=self.target/'initial-observation.json';self.write(collision,b'preexisting')
  result=c.retain_initial_observation(self.received,self.target,self.pair)
  self.assertEqual(result['status'],'RETENTION_FAILED');self.assertEqual(collision.read_bytes(),b'preexisting');collision.unlink()
  before=len(os.listdir('/proc/self/fd'));real_fdopen=c.os.fdopen
  for failure in ('write','flush','close','fsync','hash'):
   class Stream:
    def __init__(self,wrapped):self.wrapped=wrapped;self.failed=False
    def __getattr__(self,name):return getattr(self.wrapped,name)
    def write(self,raw):
     if failure=='write':raise OSError('private write canary')
     return self.wrapped.write(raw)
    def flush(self):
     if failure=='flush':raise OSError('private flush canary')
     return self.wrapped.flush()
    def close(self):
     self.wrapped.close()
     if failure=='close' and not self.failed:self.failed=True;raise OSError('private close canary')
   real_identity=c.identity
   def bad_hash(path,maximum):
    if failure=='hash' and Path(path).parent==self.target and Path(path).name=='initial-update.bin':raise OSError('private hash canary')
    return real_identity(path,maximum)
   with mock.patch.object(c.os,'fdopen',side_effect=lambda fd,mode:Stream(real_fdopen(fd,mode))),mock.patch.object(c,'identity',side_effect=bad_hash):
    with mock.patch.object(c.os,'fsync',side_effect=OSError('private fsync canary')) if failure=='fsync' else mock.patch.object(c.os,'fsync',wraps=os.fsync):
     result=c.retain_initial_observation(self.received,self.target,self.pair)
   self.assertEqual(result['status'],'RETENTION_FAILED');self.assertFalse((self.target/'initial-observation.json').exists());self.assertFalse((self.target/'initial-update.bin').exists())
   self.assertEqual((self.target/'groups.bin').read_bytes(),self.group_bytes);self.assertEqual(len(os.listdir('/proc/self/fd')),before)

if __name__=='__main__':unittest.main()
