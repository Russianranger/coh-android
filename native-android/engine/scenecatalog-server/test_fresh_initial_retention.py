#!/usr/bin/env python3
"""Offline copy/privacy/refusal controls; never produce a live admission token."""
import copy,json,os,tempfile,types,unittest
from pathlib import Path
from unittest import mock
import retain_fresh_initial_observation as r
import test_initial_observation_binding as fixture
import test_groups_public_summary as public_fixture

CANARY='PRIVATE-INITIAL-OWNER-ACCOUNT-LOG-CANARY'
class Controls(unittest.TestCase):
 def setUp(self):
  self.f=fixture.Controls('test_successful_typed_binding_retains_only_two_private_files_after_cleanup')
  self.f.setUp();self.addCleanup(self.f.doCleanups);self.root=self.f.root
  binding=r.capture.retain_initial_observation(self.f.received,self.f.target,self.f.pair)
  self.private=self.root/'private';self.private.mkdir(mode=0o700);self.f.target.rename(self.private/'native')
  self.work=self.root/'work';self.work.mkdir(mode=0o700);self.f.received.rename(self.work/'native-received')
  self.report=public_fixture.receipt();self.report['pair'].update(self.f.pair)
  self.report.update(native_tool={'build_schema':r.capture.INITIAL_BUILD_SCHEMA},initial_observation=binding)
  self.binding,self.receipt=r.observed(self.private,self.work,self.report)
  self.packet=self.private/'native/initial-update.bin';self.expected=self.binding['packet']
  self.output=self.root/'fresh-initial-observation'
  self.manifest={'schema':'explicit-offline-copy-control','passed':False,
   'fixture_only':True,'source_generation_admitted':False,'world_authority':False}
 def test_only_packet_and_commit_last_manifest_are_exported(self):
  calls=[]
  def before():
   calls.append(True);self.assertEqual(set(path.name for path in self.output.iterdir()),
    {'initial-update.bin'} if len(calls)==1 else {'initial-update.bin','manifest.json'})
  self.assertEqual(r.export_owned(self.packet,self.output,self.expected,self.manifest,before),self.manifest)
  self.assertEqual(calls,[True,True]);self.assertEqual(set(path.name for path in self.output.iterdir()),{'initial-update.bin','manifest.json'})
  self.assertEqual((self.output/'initial-update.bin').read_bytes(),self.packet.read_bytes())
  self.assertEqual(json.loads((self.output/'manifest.json').read_bytes()),self.manifest)
  self.assertEqual(self.output.stat().st_mode&0o777,0o700)
  for path in self.output.iterdir():self.assertEqual(path.stat().st_mode&0o777,0o600);self.assertEqual(path.stat().st_nlink,1)
 def test_private_observation_requires_new_role_cleaned_pair_and_same_original_loan(self):
  for name,value in (('passed',False),('cleanup_verified',False),('matching_groups_transaction_captured',False),
    ('native_tool',{}),('initial_observation',{})):
   changed=copy.deepcopy(self.report);changed[name]=value
   with self.subTest(name=name),self.assertRaises((r.Refused,r.admit.public_status.Refused)):r.observed(self.private,self.work,changed)
  path=self.work/'native-received/initial-update.bin';path.write_bytes(b'changed original loan packet')
  with self.assertRaises(r.capture.d.Refused):r.observed(self.private,self.work,self.report)
 def test_manifest_fixed_allowlist_never_exports_private_receipt_or_owner_keys(self):
  source={'source_snapshot_token_sha256':'a'*64,'private':CANARY};fresh={'database_dump_sha256':'b'*64,'account':CANARY}
  binding=dict(self.binding,private_owner=CANARY);receipt=copy.deepcopy(self.receipt)
  for name in ('selected_dbid','connection_id','message_id','groups_message_id','db_session_generation',
    'map_generation','selection_generation','account','exception','raw_log'):receipt[name]=CANARY
  manifest=r.manifest_for(source,'c'*64,fresh,'d'*64,binding,receipt,'e'*40,'f'*64)
  serialized=json.dumps(manifest);self.assertNotIn(CANARY,serialized)
  for key in ('selected_dbid','connection_id','message_id','groups_message_id','db_session_generation',
    'map_generation','selection_generation','account','exception','raw_log','groups_packet_sha256'):
   self.assertNotIn('"'+key+'"',serialized)
  self.assertEqual(set(manifest['profile']),{'payload_bits','post_command_cursor','byte_aligned','ordered','transport_version'})
  self.assertEqual(set(manifest['update_prefix']),set(r.capture.INITIAL_PREFIX))
  self.assertEqual(manifest['payload']['name'],'initial-update.bin')
  for key in ('entity_or_character_tail_semantics_admitted','source_generation_admitted','complete_initial_character',
    'actor_publication','ack_permitted','world_authority','sends_ready','sends_received_character','sends_full_update_ack'):
   self.assertIs(manifest[key],False)
 def test_fixed_destination_input_shape_and_existing_files_are_preserved(self):
  for output in (self.root/'arbitrary-name',):
   with self.assertRaises(r.Refused):r.export_owned(self.packet,output,self.expected,self.manifest,lambda:None)
  self.output.mkdir();sentinel=self.output/'existing';sentinel.write_bytes(b'preserve')
  with self.assertRaises(r.Refused):r.export_owned(self.packet,self.output,self.expected,self.manifest,lambda:None)
  self.assertEqual(sentinel.read_bytes(),b'preserve')
  for expected in ({'bytes':True,'sha256':'a'*64},{'bytes':r.capture.INITIAL_PACKET_MAX+1,'sha256':'a'*64},
    {'bytes':self.expected['bytes'],'sha256':'wrong'}):
   with self.assertRaises((r.Refused,r.admit.Refused,r.d.Refused)):
    r.export_owned(self.packet,self.root/'fresh-initial-observation',expected,self.manifest,lambda:None)
 def test_packet_copy_write_flush_fsync_close_and_hash_failures_remove_outputs(self):
  real_fdopen=os.fdopen;real_identity=r.admit.identity;before=len(os.listdir('/proc/self/fd'))
  for failure in ('write','flush','fsync','close','hash'):
   class Stream:
    def __init__(self,wrapped):self.wrapped=wrapped;self.failed=False
    def __getattr__(self,name):return getattr(self.wrapped,name)
    def write(self,raw):
     if failure=='write':raise OSError('primary write '+CANARY)
     return self.wrapped.write(raw)
    def flush(self):
     if failure=='flush':raise OSError('primary flush '+CANARY)
     return self.wrapped.flush()
    def close(self):
     self.wrapped.close()
     if failure=='close' and not self.failed:self.failed=True;raise OSError('primary close '+CANARY)
   def fail_hash(path,maximum):
    if failure=='hash' and Path(path)==self.output/'initial-update.bin':raise OSError('primary hash '+CANARY)
    return real_identity(path,maximum)
   with mock.patch.object(r.os,'fdopen',side_effect=lambda fd,mode:Stream(real_fdopen(fd,mode))),mock.patch.object(r.admit,'identity',side_effect=fail_hash):
    with mock.patch.object(r.os,'fsync',side_effect=OSError('primary fsync '+CANARY)) if failure=='fsync' else mock.patch.object(r.os,'fsync',wraps=os.fsync):
     with self.assertRaisesRegex(OSError,'primary'):r.export_owned(self.packet,self.output,self.expected,self.manifest,lambda:None)
   self.assertFalse(self.output.exists());self.assertEqual(len(os.listdir('/proc/self/fd')),before)
 def test_manifest_late_io_and_publication_failure_roll_back_packet_and_partial(self):
  real_fdopen=os.fdopen;real_link=os.link;before=len(os.listdir('/proc/self/fd'))
  for failure in ('write','flush','fsync','close','link','final_hash'):
   class Stream:
    def __init__(self,wrapped):self.wrapped=wrapped;self.failed=False
    def __getattr__(self,name):return getattr(self.wrapped,name)
    def write(self,raw):
     if failure=='write':raise OSError('manifest write '+CANARY)
     return self.wrapped.write(raw)
    def flush(self):
     if failure=='flush':raise OSError('manifest flush '+CANARY)
     return self.wrapped.flush()
    def close(self):
     self.wrapped.close()
     if failure=='close' and not self.failed:self.failed=True;raise OSError('manifest close '+CANARY)
   def fdopen(fd,mode):
    wrapped=real_fdopen(fd,mode)
    return Stream(wrapped) if Path(os.readlink('/proc/self/fd/'+str(fd))).name=='.manifest.partial' else wrapped
   real_identity=r.admit.identity
   def fail_hash(path,maximum):
    if failure=='final_hash' and Path(path)==self.output/'manifest.json':raise OSError('manifest final hash '+CANARY)
    return real_identity(path,maximum)
   real_fsync=os.fsync
   def fsync(fd):
    if failure=='fsync' and Path(os.readlink('/proc/self/fd/'+str(fd))).name=='.manifest.partial':raise OSError('manifest fsync '+CANARY)
    return real_fsync(fd)
   with mock.patch.object(r.os,'fdopen',side_effect=fdopen),mock.patch.object(r.admit,'identity',side_effect=fail_hash),mock.patch.object(r.os,'fsync',side_effect=fsync):
    with mock.patch.object(r.os,'link',side_effect=OSError('manifest link '+CANARY)) if failure=='link' else mock.patch.object(r.os,'link',wraps=real_link):
     with self.assertRaisesRegex(OSError,'manifest'):r.export_owned(self.packet,self.output,self.expected,self.manifest,lambda:None)
   self.assertFalse(self.output.exists());self.assertEqual(len(os.listdir('/proc/self/fd')),before)
 def test_rebind_or_final_target_changes_refuse_without_manifest(self):
  def changed():raise r.Refused('primary private rebind '+CANARY)
  with self.assertRaisesRegex(r.Refused,'primary private rebind'):
   r.export_owned(self.packet,self.output,self.expected,self.manifest,changed)
  self.assertFalse(self.output.exists())
  def mutate():(self.output/'initial-update.bin').write_bytes(b'changed target')
  with self.assertRaises(r.Refused):r.export_owned(self.packet,self.output,self.expected,self.manifest,mutate)
  self.assertFalse(self.output.exists())
 def test_rollback_preserves_replaced_packet_but_never_publishes_manifest(self):
  def replace():
   other=self.output/'replacement';other.write_bytes(b'preserve replacement');os.replace(other,self.output/'initial-update.bin')
  with self.assertRaises(r.Refused):r.export_owned(self.packet,self.output,self.expected,self.manifest,replace)
  self.assertEqual((self.output/'initial-update.bin').read_bytes(),b'preserve replacement')
  self.assertFalse((self.output/'manifest.json').exists())
 def test_mutation_during_manifest_and_late_provenance_refuse_every_output(self):
  real_commit=r.commit_manifest
  def changed_manifest(*args):
   result=real_commit(*args);(self.output/'initial-update.bin').write_bytes(b'changed while manifest was committed');return result
  with mock.patch.object(r,'commit_manifest',side_effect=changed_manifest):
   with self.assertRaises(r.Refused):r.export_owned(self.packet,self.output,self.expected,self.manifest,lambda:None)
  self.assertFalse(self.output.exists());calls=0
  def changed_final_manifest(*args):
   result=real_commit(*args);(self.output/'manifest.json').write_bytes(b'changed final manifest');return result
  with mock.patch.object(r,'commit_manifest',side_effect=changed_final_manifest):
   with self.assertRaises(r.Refused):r.export_owned(self.packet,self.output,self.expected,self.manifest,lambda:None)
  self.assertFalse(self.output.exists())
  def changed_provenance():
   nonlocal calls
   calls+=1
   if calls==2:raise r.Refused('primary late provenance '+CANARY)
  with self.assertRaisesRegex(r.Refused,'primary late provenance'):
   r.export_owned(self.packet,self.output,self.expected,self.manifest,changed_provenance)
  self.assertEqual(calls,2);self.assertFalse(self.output.exists())
 def test_readmission_private_workspace_cleanup_after_success_or_primary_failure(self):
  args=types.SimpleNamespace();workspace=self.work/'fresh-initial-retention-readmission'
  def fake_readmit(args,path):
   (path/'readmitted-source-snapshot.json').write_bytes(b'explicit synthetic source receipt');return {'value':'offline'}
  with mock.patch.object(r.source_retention,'readmit',side_effect=fake_readmit),mock.patch.object(r.source_retention,'scope',side_effect=lambda value:value):
   self.assertEqual(r.readmit(args,self.work),{'value':'offline'})
  self.assertFalse(workspace.exists())
  def fail_readmit(args,path):
   fake_readmit(args,path);raise r.Refused('primary readmission '+CANARY)
  with mock.patch.object(r.source_retention,'readmit',side_effect=fail_readmit):
   with self.assertRaisesRegex(r.Refused,'primary readmission'):r.readmit(args,self.work)
  self.assertFalse(workspace.exists())
 def test_host_gate_and_cli_failures_reveal_only_fixed_status(self):
  with mock.patch.object(r.admit,'hosted_revision',side_effect=r.admit.Refused(CANARY)),mock.patch.object(r.admit,'pinned_json') as read:
   with self.assertRaises(r.admit.Refused):r.retain(types.SimpleNamespace())
   read.assert_not_called()
  import contextlib,io,sys
  arguments=['retain']
  for name in (*r.PATH_ARGUMENTS,*r.PIN_ARGUMENTS,'source-admission','source-admission-sha256','output'):
   arguments+=['--'+name,CANARY]
  output=io.StringIO()
  with mock.patch.object(sys,'argv',arguments),mock.patch.object(r,'retain',side_effect=RuntimeError(CANARY)),contextlib.redirect_stdout(output):
   self.assertEqual(r.main(),2)
  self.assertNotIn(CANARY,output.getvalue());self.assertEqual(json.loads(output.getvalue())['failure_code'],'FRESH_INITIAL_RETENTION_REFUSED')

if __name__=='__main__':unittest.main()
