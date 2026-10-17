#!/usr/bin/env python3
"""Pure restore-supervisor input/pairing controls; no PG/Wine/server startup."""
from pathlib import Path
import argparse,copy,hashlib,json,os,struct,subprocess,sys,tempfile,types
from unittest import mock
import capture_groups_transaction as capture

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--fixture',type=Path,required=True);parser.add_argument('--native-directory',type=Path);parser.add_argument('--native-source-root',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();checks=refusals=0
 with tempfile.TemporaryDirectory(prefix='coh-private-groups-supervisor-') as temporary:
  work=Path(temporary);dump=work/'database.dump';account=work/'account';dump.write_bytes(b'PGDMP-explicit-unit-fixture');dump.chmod(0o600);account.write_bytes(b'Existing\n');account.chmod(0o600)
  basic=types.SimpleNamespace(database_dump=dump,database_dump_sha256=hashlib.sha256(dump.read_bytes()).hexdigest(),account_file=account,wire_slot=0)
  def preflight_refused(change):
   nonlocal checks,refusals
   values=copy.copy(basic)
   for key,value in change.items():setattr(values,key,value)
   with mock.patch.object(capture.subprocess,'Popen') as process,mock.patch.object(capture.subprocess,'run') as run,mock.patch.object(capture.subprocess,'check_output') as output:
    try:capture.preflight(values)
    except (ValueError,OSError):refusals+=1
    else:raise AssertionError('unqualified private invocation accepted')
    assert not process.called and not run.called and not output.called;checks+=1
  preflight_refused({'database_dump':work/'absent'})
  preflight_refused({'database_dump_sha256':'0'*64})
  preflight_refused({'account_file':work/'absent-account'})
  for slot in (-1,64,True,'0'):preflight_refused({'wire_slot':slot})
  for data in (b'',b'a'*15,b'bad name',b'a\x00b',b'\n'):
   account.write_bytes(data);preflight_refused({})
  account.write_bytes(b'Existing\n');account.chmod(0o644);preflight_refused({});account.chmod(0o600)
  dump.chmod(0o644);preflight_refused({});dump.chmod(0o600)
  linked=work/'linked';linked.symlink_to(dump);preflight_refused({'database_dump':linked})
  previous=dump.read_bytes();dump.write_bytes(b'NOTPG-dump');preflight_refused({'database_dump_sha256':hashlib.sha256(dump.read_bytes()).hexdigest()});dump.write_bytes(previous)
  class ExistingCluster:
   meta={'database':'existing_private'}
   def sql(self,query,**options):
    assert query.startswith('SELECT ') and 'LIMIT 65' in query and 'INSERT ' not in query and 'UPDATE ' not in query
    self.query=query;return json.dumps(self.rows)
  cluster=ExistingCluster();cluster.rows=[{'containerid':99,'staticmapid':1,'mapid':None}]
  assert capture.character_membership(cluster,"Existing'Account")==cluster.rows and "Existing''Account" in cluster.query;checks+=1
  for rows in ([],[{'containerid':0,'staticmapid':1,'mapid':None}],[{'containerid':99,'staticmapid':5,'mapid':None}],cluster.rows*65):
   cluster.rows=rows
   try:capture.character_membership(cluster,'Existing')
   except ValueError:refusals+=1;checks+=1
   else:raise AssertionError('missing/unsupported membership accepted')
  raw=bytearray(args.fixture.read_bytes());at=64;packets=[]
  while at<len(raw):
   kind,_,n,_=struct.unpack_from('<4I',raw,at);at+=16
   if kind==1:struct.pack_into('<I',raw,at+48,5) # explicit source-profile unit fixture
   if kind==8:packets.append(bytes(raw[at:at+n]))
   at+=n
  source=work/'source.cohgtx';source.write_bytes(raw);inspection=capture.envelope.inspect(source);received=work/'native';received.mkdir();(received/'groups.bin').write_bytes(packets[0])
  state={'schema':'coh-local-scene-capture-v1','passed':True,'local_development_auth':True,'actual_client_loan_verified':True,'selected_dbid_owner_bound':True,'cleanup_verified':True,'packet_written_synchronously':True,
         'authserver_authenticated':False,'source_generation_admitted':False,'actor_identity_verified':False,'world_authority':False,'packet_copy_retained':False,'selected_slot':0,'selected_dbid':99,'map_id':1,'bytes':len(packets[0]),'packet_sha256':hashlib.sha256(packets[0]).hexdigest(),'payload_bits':inspection['packet']['bits'],'byte_aligned':inspection['packet']['byte_aligned'],'transport_version':5,'footer_file_count':inspection['source_catalog']['files'],'footer_defs_crc':inspection['source_snapshot']['definitions_crc'],'footer_refs_crc':inspection['source_snapshot']['references_crc'],'footer_active_roots':inspection['source_snapshot']['active_roots'],'groups_consumed_bits':inspection['packet']['bits'],'opened_sockets':2,'closed_sockets':2}
  def emit(value):(received/'capture.json').write_text(json.dumps(value))
  membership=[{'containerid':99,'staticmapid':1,'mapid':None}];emit(state);paired=capture.pair(source,received,membership,0)
  assert paired['passed'] and paired['exact_logical_packet_verified'] and not paired['source_generation_admitted'] and not paired['world_authority'] and not paired['source_run_provenance_verified'];checks+=1
  changes={'passed':False,'local_development_auth':False,'actual_client_loan_verified':False,'selected_dbid_owner_bound':False,'cleanup_verified':False,'packet_written_synchronously':False,'authserver_authenticated':True,'source_generation_admitted':True,'actor_identity_verified':True,'world_authority':True,'packet_copy_retained':True,'selected_slot':1,'selected_dbid':100,'map_id':5,'bytes':state['bytes']+1,'packet_sha256':'0'*64,'payload_bits':state['payload_bits']-1,'byte_aligned':0,'transport_version':3,'footer_file_count':state['footer_file_count']+1,'footer_defs_crc':state['footer_defs_crc']^1,'footer_refs_crc':state['footer_refs_crc']^1,'footer_active_roots':state['footer_active_roots']+1,'groups_consumed_bits':state['payload_bits']-1,'opened_sockets':3,'closed_sockets':1}
  for key,value in changes.items():
   changed=dict(state);changed[key]=value;emit(changed)
   try:capture.pair(source,received,membership,0)
   except ValueError:refusals+=1;checks+=1
   else:raise AssertionError('contradictory pair accepted: '+key)
  for key in state:
   changed=dict(state);del changed[key];emit(changed)
   try:capture.pair(source,received,membership,0)
   except ValueError:refusals+=1;checks+=1
   else:raise AssertionError('omitted pair field accepted: '+key)
  for key,value in state.items():
   if type(value) is not int:continue
   changed=dict(state);changed[key]=bool(value);emit(changed)
   try:capture.pair(source,received,membership,0)
   except ValueError:refusals+=1;checks+=1
   else:raise AssertionError('boolean numeric pair field accepted: '+key)
  changed=dict(state);changed['schema']='unrelated-capture-v1';emit(changed)
  try:capture.pair(source,received,membership,0)
  except ValueError:refusals+=1;checks+=1
  else:raise AssertionError('wrong capture schema accepted')
  altered=bytearray(packets[0]);altered[-1]^=1;(received/'groups.bin').write_bytes(altered);changed=dict(state);changed['packet_sha256']=hashlib.sha256(altered).hexdigest();emit(changed)
  try:capture.pair(source,received,membership,0)
  except ValueError:refusals+=1;checks+=1
  else:raise AssertionError('different exact original/native payload accepted')
  before=len(os.listdir('/proc/self/fd'));children=[];handles=[];logs=[];original_open=Path.open
  def refused_stderr(path,*values,**keywords):
   if path.name=='fault-stderr.log':raise OSError('stderr-refusal')
   return original_open(path,*values,**keywords)
  with mock.patch.object(Path,'open',refused_stderr),mock.patch.object(capture.subprocess,'Popen') as process:
   try:capture.start_owned(children,handles,logs,work,'fault',['unused'],work,os.environ.copy())
   except OSError:refusals+=1;checks+=1
   else:raise AssertionError('stderr refusal lost')
   assert not process.called and not children and len(handles)==1
  for handle in handles:handle.close()
  assert len(os.listdir('/proc/self/fd'))==before;checks+=1
  repository=work/'source-fixture';repository.mkdir();subprocess.run(['git','init','-q'],cwd=repository,check=True)
  helper=repository/'helper.py';helper.write_bytes(b'explicit source fixture\n');subprocess.run(['git','add','helper.py'],cwd=repository,check=True);subprocess.run(['git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','Explicit source fixture'],cwd=repository,check=True)
  revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repository,text=True).strip();source_pins={'helper.py':hashlib.sha256(helper.read_bytes()).hexdigest()};assert capture.verify_orchestration(repository,source_pins,revision)==revision;checks+=1
  untracked=repository/'untracked.py';untracked.write_bytes(b'untracked source\n')
  for pins,expected in (({**source_pins,'untracked.py':hashlib.sha256(untracked.read_bytes()).hexdigest()},revision),(source_pins,'0'*40)):
   try:capture.verify_orchestration(repository,pins,expected)
   except ValueError:checks+=1;refusals+=1
   else:raise AssertionError('uncommitted/unmatched source admitted')
  helper.write_bytes(b'changed source\n')
  try:capture.verify_orchestration(repository,{'helper.py':hashlib.sha256(helper.read_bytes()).hexdigest()},revision)
  except ValueError:checks+=1;refusals+=1
  else:raise AssertionError('changed source claimed under old HEAD')
  children=[];handles=[];logs=[]
  with mock.patch.object(capture.subprocess,'Popen',side_effect=OSError('popen-refusal')):
   try:capture.start_owned(children,handles,logs,work,'popen',['unused'],work,os.environ.copy())
   except OSError:refusals+=1;checks+=1
   else:raise AssertionError('Popen refusal lost')
  assert not children and len(handles)==2
  for handle in handles:handle.close()
  assert len(os.listdir('/proc/self/fd'))==before;checks+=1
  children=[];handles=[];logs=[]
  child,_,_=capture.start_owned(children,handles,logs,work,'owned',[sys.executable,'-c','import time;time.sleep(20)'],work,os.environ.copy())
  try:assert len(children)==1 and child.pid==os.getpgid(child.pid) and capture.base.stop_owned(child) and capture.base.process_group_absent(child);checks+=1
  finally:
   if child.poll() is None:capture.base.stop_owned(child)
   for handle in handles:handle.close()
  assert len(os.listdir('/proc/self/fd'))==before;checks+=1
 native=None
 if args.native_directory:
  assert args.native_source_root
  native=capture.native_input(args.native_directory/'coh-capture-local-scene',args.native_directory/'build.json',hashlib.sha256((args.native_directory/'build.json').read_bytes()).hexdigest(),args.native_source_root);checks+=1
 report={'schema':'coh-private-groups-supervisor-host-v1','passed':True,'checks':checks,'refusals':refusals,'source_sha256':{path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in (Path(capture.__file__),Path(__file__),Path(capture.admit.__file__))},'existing_membership_and_pairing_unit_fixtures_only':True,'private_input_refusals_before_process_creation':True,'actual_linux_child_group_cleanup':True,'actual_native_binary_admission':native,'postgres_executed':False,'wine_executed':False,'real_server_capture':False,'source_generation_admitted':False,'world_authority':False}
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'refusals':refusals,'real_server_capture':False}))
if __name__=='__main__':main()
