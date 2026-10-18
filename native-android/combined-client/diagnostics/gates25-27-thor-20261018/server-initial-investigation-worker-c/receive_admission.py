#!/usr/bin/env python3
"""New receive-counter role admission; no native/service execution on import."""
from pathlib import Path
import ast,hashlib,json,os,re,shlex,struct,subprocess
import delivery as d
import initial_progress_admission as progress
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
RELATIVE='native-android/combined-client/diagnostics/gates25-27-thor-20261018/server-initial-investigation-worker-c/receive_admission.py'
PREFIX=RELATIVE.rsplit('/',1)[0]+'/'
SOURCE_PATHS=(RELATIVE,)
BUILD_SCHEMA='coh-initial-receive-focused-v1'
BASENAME='coh-capture-initial-receive'
SCHEMA='coh-initial-receive-counters-v1'
FALSE=('command_specific_emission_proved','server_receipt_proved','source_generation_admitted','complete_initial_character','actor_publication','ack_permitted','world_authority')
COUNTS=('udp_datagrams_received','udp_peer_rejects','udp_truncated','udp_empty','udp_malformed','udp_unsupported','udp_receive_budget_exhausted','link_received','link_duplicates','link_malformed','link_unsupported','link_queue_limits','link_fragment_expirations','link_timeouts','sample_count')
BOUNDS={'rx_pending':16,'fragment_groups':4,'max_rx_pending_sampled':16,'max_fragment_groups_sampled':4,'decode_failure_kind':4,'decode_compressed_bytes':16384,'decode_declared_raw_bytes':2**32-1,'decode_output_budget':4*1024**2}
BOOLS=('valid','observation_retired','cleanup_transport_counters_equal')
KEYS=frozenset(('schema','diagnostic_only','refusal',*FALSE,*COUNTS,*BOUNDS,*BOOLS))
def require(value,reason):d.require(value,'INITIAL_RECEIVE_'+reason)
def pin(raw):return hashlib.sha256(raw).hexdigest()
def parse(raw):
 require(type(raw)is bytes and 0<len(raw)<=2048,'SIZE');v=d.json_object(raw)
 require(set(v)==KEYS and v['schema']==SCHEMA and v['diagnostic_only']is True,'SCHEMA')
 require(all(v[k]is False for k in FALSE),'AUTHORITY')
 require(all(type(v[k])is bool for k in BOOLS),'BOOL')
 require(type(v['refusal'])is str and v['refusal']in('NONE','INPUT','LIMIT'),'REFUSAL')
 for k in COUNTS:d.uint(v[k],1000000)
 for k,limit in BOUNDS.items():d.uint(v[k],limit)
 require(v['valid']==(v['sample_count']>0 and v['refusal']=='NONE'),'VALID')
 require(v['max_rx_pending_sampled']>=v['rx_pending'] and v['max_fragment_groups_sampled']>=v['fragment_groups'],'PEAK')
 return v
def recipe(root):
 path=root/'native-android/combined-client/tools/check_local_initial_capture.py';tree=ast.parse(d.read(path,1024**2))
 values=[ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='RELATIVE'for t in n.targets)]
 require(len(values)==1 and type(values[0])is list and all(type(x)is str for x in values[0]),'RECIPE')
 return[root/'native-android'/name for name in values[0]]
def compiler_dependencies(root=ROOT):
 root=d.path(root);role=root/(PREFIX+'capture_local_initial_receive.c');unit=root/(PREFIX+'test_receive.c')
 source=[role,*recipe(root),unit,root/(PREFIX+'test_jni_receive.c'),root/'native-android/combined-client/app/src/main/cpp/interop_network.c']
 found={root/RELATIVE,root/(PREFIX+'check_receive.py'),root/(PREFIX+'QUALIFICATION.md'),root/'native-android/combined-client/tools/capture_local_initial_progress.c',root/'native-android/combined-client/tools/capture_local_initial.c',root/'native-android/combined-client/tools/check_local_initial_capture.py',root/'native-android/engine/scenecatalog-server/initial_progress_admission.py'}
 command=['cc','-std=c11','-DCOH_INTEROP_REQUEST_TX=1','-MM','-I'+str(root/'native-android/include'),'-I'+str(root/'native-android/engine/initial-capture'),'-I'+str(root/'native-android/engine/session'),'-I'+str(root/'native-android/combined-client/diagnostics/interop-adapter-20261018/test-include'),'-I'+str(root/'native-android/combined-client/tools'),*[str(p)for p in source]]
 result=subprocess.run(command,capture_output=True,timeout=60)
 require(result.returncode==0 and not result.stderr and len(result.stdout)<=1024**2,'DEPENDENCIES')
 for line in result.stdout.decode().replace('\\\n',' ').splitlines():
  words=shlex.split(line);require(words and words[0].endswith(':'),'DEPENDENCIES')
  for name in words[1:]:
   path=Path(name).resolve();require(root in path.parents,'DEPENDENCY_ROOT');found.add(path)
 return{p.relative_to(root).as_posix():pin(d.read(p,8*1024**2))for p in sorted(found)}
def preservation(root=ROOT):
 role=d.read(root/(PREFIX+'capture_local_initial_receive.c'),1024**2).decode()
 begin='/* BEGIN EXACT PROGRESS ROLE WITH FIVE REVERSIBLE IDENTIFIER EDITS */\n';end='/* END EXACT PROGRESS ROLE */\n'
 require(role.count(begin)==role.count(end)==1,'SOURCE_MARKERS');body=role.split(begin,1)[1].split(end,1)[0]
 for new,old,count in [('receive_begin(','coh_initial_capture_begin(',1),('receive_diagnostics(','coh_initial_capture_diagnostics(',4),('receive_destroy(','coh_initial_capture_destroy(',1),('receive_write_fd(out.groups.directory);','progress_write(out.groups.directory);',1),('int coh_receive_progress_main(int argc,char**argv){','int main(int argc,char**argv){',1)]:
  require(body.count(new)==count,'SOURCE_REVERSAL');body=body.replace(new,old)
 baseline=d.read(root/'native-android/combined-client/tools/capture_local_initial_progress.c',1024**2)
 require(body.encode()==baseline,'EXACT_PROGRESS_BASELINE')
 return{'exact_current_progress_body_reversal_verified':True,'five_identifier_substitutions_eight_sites':True,'baseline_progress_sha256':pin(baseline),'wire_protocol_main_loop_timeout_and_call_order_unchanged':True,'receive_file_on_original_owned_directory_FD_after_success_and_owner_destruction':True}
def native_input(binary,receipt_path,receipt_pin,root=ROOT):
 root=d.path(root);binary=d.regular(binary);raw=d.read(receipt_path,16*1024**2)
 require(pin(raw)==d.sha(receipt_pin),'RECEIPT_PIN');proof=d.json_object(raw)
 require(proof.get('schema')==BUILD_SCHEMA and proof.get('passed')is True and binary.name==BASENAME,'BUILD_ROLE')
 require(type(proof.get('source_revision'))is str and re.fullmatch('[0-9a-f]{40}',proof['source_revision'])is not None,'REVISION')
 require(proof.get('transition')==preservation(root),'PRESERVATION')
 require(all(proof.get(k)is False for k in ('old_qualifier_or_fixture_entrypoints_executed','original_server_executed','actual_source_protocol_session_executed','default_network_map_local_initial_sources_changed','complete_global_aggregate_or_RSS_fit','world_authority','leak_sanitizer_enabled')),'BUILD_AUTHORITY')
 modes=proof.get('modes',{});require(type(modes)is dict and set(modes)=={'release','asan','ubsan'},'MODES')
 for candidate in modes.values():
  unit=candidate.get('focused_unit',{});require(unit.get('passed')is True and unit.get('scenarios')==8 and unit.get('diagnostics_and_lifecycle_explicit_doubles')is True and unit.get('actual_socket_or_server_executed')is False and candidate.get('production_role_noargs_unchanged')is True,'FOCUSED_SCOPE')
 actual={'bytes':binary.stat().st_size,'sha256':pin(d.read(binary,4*1024**2))}
 require(actual=={'bytes':modes['release'].get('production_role_bytes'),'sha256':modes['release'].get('production_role_sha256')},'BINARY')
 header=d.read(binary,4*1024**2)[:20];require(header[:6]==b'\x7fELF\x02\x01'and struct.unpack_from('<H',header,18)[0]==62,'ELF')
 pins=compiler_dependencies(root);require(proof.get('source_sha256')==pins,'CURRENT_SOURCE')
 require(pin(d.read(receipt_path,16*1024**2))==receipt_pin and actual=={'bytes':binary.stat().st_size,'sha256':pin(d.read(binary,4*1024**2))},'INPUT_CHANGED')
 return{'binary':actual,'build_receipt_sha256':receipt_pin,'source_revision':proof['source_revision'],'project_dependencies':len(pins),'dependencies_sha256':pins,'build_schema':BUILD_SCHEMA,'diagnostic_role':'existing_receive_counters','historical_receiver_equivalence_established':False,'current_kernel_build_bytes_verified':True,'initial_progress_compatibility_verified':True,'current_progress_baseline_sha256':proof['transition']['baseline_progress_sha256']}
def finish(core,report,native,received,target):
 require(native.get('build_schema')==BUILD_SCHEMA and native.get('initial_progress_compatibility_verified')is True,'ACTUAL_NEW_ROLE')
 compatibility={**native,'build_schema':progress.BUILD_SCHEMA};progress.finish(core,report,compatibility,received,target)
 try:
  raw=progress.read_private(received/'receive-counters.json',2048);value=parse(raw);require(value['valid']and value['observation_retired']and value['cleanup_transport_counters_equal'],'TERMINAL_SCOPE')
  require(report.get('cleanup_verified')is True and report.get('matching_groups_transaction_captured')is True and report.get('passed')is True,'OWNED_CLEANUP')
  initial=report.get('initial_observation',{})
  require(initial.get('same_groups_owner_verified')is True and initial.get('retained_after_owned_cleanup')is True,'INITIAL_OWNER')
  out=target/'receive-counters.json'
  fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600);owned=None;ok=False
  try:
   owned=os.fstat(fd)
   with os.fdopen(fd,'wb')as stream:
    fd=None;stream.write(raw);stream.flush();os.fsync(stream.fileno())
   require(progress.read_private(out,2048)==raw and progress.read_private(received/'receive-counters.json',2048)==raw,'RETAINED_BYTES');ok=True
  finally:
   if fd is not None:os.close(fd)
   if not ok and owned is not None:
    info=out.lstat()
    if(info.st_dev,info.st_ino,info.st_uid)==(owned.st_dev,owned.st_ino,owned.st_uid):out.unlink()
  report['receive_diagnostic']=value;report['receive_private_binding']={'bytes':len(raw),'sha256':pin(raw),'retained_after_owned_cleanup':True,'public_upload_permitted':False}
 except Exception:
  report['receive_diagnostic']={'schema':SCHEMA,'state':'REFUSED',**{k:False for k in FALSE}}
def project(report,private_output):
 require(report.get('schema')=='coh-private-original-native-groups-run-v1'and report.get('passed')is True and report.get('cleanup_verified')is True and report.get('matching_groups_transaction_captured')is True and report.get('private_character_state')is True and report.get('public_upload_permitted')is False,'RUN_SCOPE')
 require(report.get('native_tool',{}).get('build_schema')==BUILD_SCHEMA and report.get('native_tool',{}).get('initial_progress_compatibility_verified')is True,'NEW_ROLE')
 require(report.get('source_sha256',{}).get(RELATIVE)==pin(Path(__file__).read_bytes()),'CONSUMED_ADAPTER_SOURCE')
 require(report.get('source_generation_admitted')is False and report.get('world_authority')is False,'RUN_AUTHORITY')
 raw=progress.read_private(Path(private_output)/'native/receive-counters.json',2048);value=parse(raw)
 require(value['valid']and value['observation_retired']and value['cleanup_transport_counters_equal'],'TERMINAL_SCOPE')
 require(report.get('receive_diagnostic')==value and report.get('receive_private_binding')=={'bytes':len(raw),'sha256':pin(raw),'retained_after_owned_cleanup':True,'public_upload_permitted':False},'PRIVATE_BINDING')
 return value
