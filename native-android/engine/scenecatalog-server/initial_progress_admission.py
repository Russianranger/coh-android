#!/usr/bin/env python3
"""Explicit current-source progress-role admission; no original runtime starts."""
from pathlib import Path
import argparse,ast,hashlib,json,os,re,shlex,stat,struct,subprocess
import delivery as d
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
BUILD_SCHEMA='coh-initial-progress-focused-v1'
SCHEMA='coh-initial-post-queue-progress-v1'
BASENAME='coh-capture-initial-progress'
RELATIVE='native-android/engine/scenecatalog-server/initial_progress_admission.py'
SOURCE_PATHS=(RELATIVE,)
FALSE=('command_specific_emission_proved','server_receipt_proved','source_generation_admitted','actor_publication','ack_permitted','world_authority')
COUNTS=('post_queue_services','post_queue_send_callbacks','post_queue_datagrams_emitted','post_queue_would_block','post_queue_interrupted','post_queue_send_errors','post_queue_partial_sends')
OFFSETS=('queue_service_offset_ms','last_post_queue_service_offset_ms')
KEYS=frozenset(('schema','diagnostic_only','valid','queue_observed','witness_owner_retired','refusal',*FALSE,*COUNTS,*OFFSETS))
REFUSALS=frozenset(('NONE','OWNER','CLOCK','STATE','LIMIT','CALLBACK'))
BUILD_FALSE=('old_qualifier_or_fixture_entrypoints_executed','original_server_executed','actual_source_protocol_session_executed','default_network_map_local_initial_sources_changed','complete_global_aggregate_or_RSS_fit','command_specific_emission_proved','server_receipt_proved','source_generation_admitted','actor_publication','ack_permitted','world_authority','leak_sanitizer_enabled')
def require(value,code='REFUSED'):d.require(value,'INITIAL_PROGRESS_'+code)
def pin(raw):return hashlib.sha256(raw).hexdigest()
def identity(path,maximum):
 size,digest=d.hash_file(path,maximum);return{'bytes':size,'sha256':digest}
def compiler_dependencies(root):
 recipe=root/'native-android/combined-client/tools/check_local_initial_capture.py';tree=ast.parse(d.read(recipe,1024**2));nodes=[n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='RELATIVE'for t in n.targets)]
 require(len(nodes)==1,'RECIPE');relative=ast.literal_eval(nodes[0]);require(type(relative)is list and all(type(x)is str for x in relative),'RECIPE')
 role=root/'native-android/combined-client/tools/capture_local_initial_progress.c';test=root/'native-android/engine/initial-capture/test_initial_progress.c'
 sources=[role,*[root/'native-android'/name for name in relative],test]
 found={role,recipe,root/'native-android/combined-client/tools/capture_local_initial.c',root/'native-android/engine/initial-capture/check_initial_progress.py',root/'native-android/engine/initial-capture/INITIAL_PROGRESS.md'}
 result=subprocess.run(['cc','-std=c11','-MM','-I'+str(root/'native-android/include'),*[str(p)for p in sources]],capture_output=True,timeout=60)
 require(result.returncode==0 and not result.stderr and len(result.stdout)<=1024**2,'DEPENDENCIES')
 for line in result.stdout.decode('utf8').replace('\\\n',' ').splitlines():
  words=shlex.split(line);require(words and words[0].endswith(':'),'DEPENDENCIES')
  for name in words[1:]:
   p=Path(name).resolve();require(root in p.parents,'DEPENDENCY_ROOT');found.add(p)
 return{p.relative_to(root).as_posix():pin(d.read(p,8*1024**2))for p in sorted(found)}
def native_input(binary,receipt_path,receipt_pin,root=ROOT):
 root=d.path(root);binary=d.regular(binary);raw=d.read(receipt_path,16*1024**2);require(pin(raw)==d.sha(receipt_pin),'RECEIPT_PIN');receipt=d.json_object(raw)
 require(receipt.get('schema')==BUILD_SCHEMA and receipt.get('passed')is True and binary.name==BASENAME,'BUILD_SCOPE')
 require(type(receipt.get('source_revision'))is str and re.fullmatch('[0-9a-f]{40}',receipt['source_revision'])is not None,'BUILD_REVISION')
 require(all(receipt.get(name)is False for name in BUILD_FALSE),'BUILD_AUTHORITY')
 require(receipt.get('link_wrapped_actual_sendto_executed')is True and receipt.get('unit_service_begin_and_diagnostics_explicit_doubles')is True and receipt.get('new_observer_static_bytes')==112 and receipt.get('fixed_report_max_bytes')==1024,'BUILD_ROLE')
 transition=receipt.get('transition',{});require(transition.get('five_reversible_identifier_or_call_edits_only')is True and transition.get('protocol_deadline_main_loop_and_original_call_order_unchanged')is True and transition.get('extra_private_report_written_only_after_legacy_capture_success_before_owned_FD_close')is True,'SOURCE_TRANSITION')
 modes=receipt.get('modes',{});require(type(modes)is dict and set(modes)=={'release','asan','ubsan'},'MODES')
 for candidate in modes.values():
  result=candidate.get('focused_unit',{});require(result.get('passed')is True and result.get('checks')==129 and result.get('observer_bytes')==112 and result.get('actual_loopback_datagrams')==2 and result.get('service_protocol_doubled')is True and result.get('original_server_executed')is False and result.get('command_specific_emission_proved')is False and result.get('world_authority')is False and candidate.get('production_role_noargs_unchanged')is True,'FOCUSED_SCOPE')
 mode=modes['release'];actual=identity(binary,4*1024**2)
 require(actual=={'bytes':mode.get('production_role_bytes'),'sha256':mode.get('production_role_sha256')} and mode.get('production_role_noargs_unchanged')is True,'BINARY')
 header=d.read(binary,4*1024**2)[:20];require(len(header)==20 and header[:6]==b'\x7fELF\x02\x01'and struct.unpack_from('<H',header,18)[0]==62,'ELF')
 dependencies=compiler_dependencies(root);require(receipt.get('source_sha256')==dependencies,'CURRENT_SOURCE_BYTES')
 require(transition.get('legacy_sha256')==dependencies['native-android/combined-client/tools/capture_local_initial.c'] and transition.get('current_role_sha256')==dependencies['native-android/combined-client/tools/capture_local_initial_progress.c'],'TRANSITION_BYTES')
 require(identity(binary,4*1024**2)==actual and pin(d.read(receipt_path,16*1024**2))==receipt_pin,'INPUT_CHANGED')
 return{'binary':actual,'build_receipt_sha256':receipt_pin,'source_revision':receipt.get('source_revision'),'project_dependencies':len(dependencies),'dependencies_sha256':dependencies,'build_schema':BUILD_SCHEMA,'diagnostic_role':'command_unattributed_post_queue_progress','historical_receiver_equivalence_established':False,'current_kernel_build_bytes_verified':True}
def parse(raw):
 require(type(raw)is bytes and 0<len(raw)<=1024,'RECEIPT_SIZE');value=d.json_object(raw);require(set(value)==KEYS and value.get('schema')==SCHEMA and value.get('diagnostic_only')is True,'RECEIPT_SCHEMA')
 require(all(value.get(name)is False for name in FALSE),'RECEIPT_AUTHORITY')
 for name in('valid','queue_observed','witness_owner_retired'):require(type(value.get(name))is bool,'BOOL')
 require(type(value.get('refusal'))is str and value['refusal']in REFUSALS,'REFUSAL_ENUM')
 for name in COUNTS:d.uint(value[name],1000000)
 for name in OFFSETS:d.uint(value[name],600000)
 require(value['post_queue_send_callbacks']==sum(value[name]for name in COUNTS[2:]),'CALLBACK_COUNTS')
 require((value['valid']and value['witness_owner_retired']and value['refusal']=='NONE')or(not value['valid']and value['refusal']!='NONE'),'VALID_SCOPE')
 if not value['queue_observed']:require(all(value[name]==0 for name in(*COUNTS,*OFFSETS)),'NO_QUEUE')
 if not value['post_queue_services']:require(not value['post_queue_send_callbacks']and not value['last_post_queue_service_offset_ms'],'NO_SERVICE')
 else:require(value['queue_observed']and value['last_post_queue_service_offset_ms']>=value['queue_service_offset_ms'],'SERVICE_OFFSETS')
 return{'schema':SCHEMA,'diagnostic_only':True,**{name:value[name]for name in('valid','queue_observed',*COUNTS,*OFFSETS,'witness_owner_retired','refusal')},**{name:False for name in FALSE}}
def read_private(path,maximum=1024):
 path=d.regular(path);before=path.stat();require(before.st_uid==os.geteuid()and not before.st_mode&0o077 and 0<before.st_size<=maximum,'PRIVATE_FILE')
 def key(s):return(s.st_dev,s.st_ino,s.st_uid,s.st_nlink,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
 fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
 with os.fdopen(fd,'rb')as stream:
  require(key(os.fstat(stream.fileno()))==key(before),'FILE_REPLACED');raw=stream.read(maximum+1);require(len(raw)==before.st_size and key(os.fstat(stream.fileno()))==key(before),'FILE_CHANGED')
 require(key(path.stat())==key(before),'PATH_CHANGED');return raw

def finish(core,report,native,received,target):
 # Optional diagnostics never unwind owned cleanup or promote GROUPS acceptance.
 report['request_progress_diagnostic']={'schema':'coh-initial-progress-admission-v1','state':'UNAVAILABLE',**{name:False for name in FALSE}}
 if native.get('build_schema')!=BUILD_SCHEMA:return
 if report.get('matching_groups_transaction_captured')is not True:report['initial_observation']=core.initial_status('GROUPS_NOT_PAIRED');return
 if report.get('cleanup_verified')is not True or report.get('passed')is not True:report['initial_observation']=core.initial_status('CLEANUP_NOT_VERIFIED');return
 try:report['initial_observation']=core.retain_initial_observation(received,target,report['pair'])
 except Exception:
  report['initial_observation']=core.initial_status('REFUSED');return
 try:
  initial=report['initial_observation'];diagnostic=report.get('native_diagnostic',{})
  require(initial.get('same_groups_owner_verified')is True and initial.get('retained_after_owned_cleanup')is True,'INITIAL_OWNER')
  require(diagnostic.get('process_started')is True and diagnostic.get('stdout_validated')is True and diagnostic.get('native_sockets_closed')is True,'OWNED_STDOUT')
  path=received/'request-progress.json';raw=read_private(path);value=parse(raw);require(value['queue_observed']==(diagnostic.get('reqallents_sent')==1),'QUEUE_BINDING')
  name='request-progress.json';out=target/name;fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600);owned=os.fstat(fd);ok=False
  try:
   with os.fdopen(fd,'wb')as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
   require(read_private(path)==raw and read_private(out)==raw,'RETAINED_BYTES');ok=True
  finally:
   if not ok:
    info=out.lstat()
    if (info.st_dev,info.st_ino,info.st_uid)==(owned.st_dev,owned.st_ino,owned.st_uid):out.unlink()
  report['request_progress_diagnostic']=value;report['request_progress_private_binding']={'bytes':len(raw),'sha256':pin(raw),'retained_after_owned_cleanup':True,'public_upload_permitted':False}
 except Exception:
  report['request_progress_diagnostic']={'schema':'coh-initial-progress-admission-v1','state':'REFUSED',**{name:False for name in FALSE}}

def emit(directory,output):
 directory=d.path(directory);output=d.path(output)
 report=d.json_object(read_private(directory/'capture-receipt.json',8*1024**2))
 require(report.get('schema')=='coh-private-original-native-groups-run-v1' and report.get('passed')is True and report.get('matching_groups_transaction_captured')is True and report.get('cleanup_verified')is True and report.get('private_character_state')is True and report.get('public_upload_permitted')is False and report.get('source_generation_admitted')is False and report.get('world_authority')is False,'RUN_SCOPE')
 require(report.get('native_tool',{}).get('build_schema')==BUILD_SCHEMA and report.get('source_sha256',{}).get(RELATIVE)==pin(Path(__file__).read_bytes()),'NEW_ROLE_SOURCE')
 raw=read_private(directory/'native/request-progress.json');value=parse(raw);binding=report.get('request_progress_private_binding',{})
 require(binding=={'bytes':len(raw),'sha256':pin(raw),'retained_after_owned_cleanup':True,'public_upload_permitted':False}and report.get('request_progress_diagnostic')==value,'PRIVATE_BINDING')
 require(not output.exists()and output.parent.is_dir(),'NEW_OUTPUT');fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
 with os.fdopen(fd,'w')as stream:json.dump(value,stream,sort_keys=True,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
 return value

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--private-output',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 try:emit(args.private_output,args.output)
 except Exception:print(json.dumps({'schema':'coh-initial-progress-projection-status-v1','passed':False,'failure':'PROJECTION_REFUSED','world_authority':False}));return 2
 print(json.dumps({'schema':'coh-initial-progress-projection-status-v1','passed':True,'world_authority':False}));return 0
if __name__=='__main__':raise SystemExit(main())
