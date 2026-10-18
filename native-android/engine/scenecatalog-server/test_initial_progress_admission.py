#!/usr/bin/env python3
"""Focused new role/data admission only; no original/native test is replayed."""
from pathlib import Path
import argparse,copy,gzip,hashlib,json,os,subprocess,tempfile,types
from unittest import mock
import capture_groups_transaction as core
import initial_progress_admission as p
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];checks=0;refusals=0
LEGACY_REVISION='0c8d7e064a9d7360a0a4be68d7a38b975f1c1b37'
CANARY='PRIVATE-PACKET-ACCOUNT-DBID-ENDPOINT-DO-NOT-EXPORT'
def need(ok,reason):
 global checks
 checks+=1
 if not ok:raise ValueError('PROGRESS_ADMISSION_TEST_'+reason)
def refused(call):
 global refusals
 try:call()
 except(core.d.Refused,OSError):refusals+=1;return
 raise ValueError('PROGRESS_ADMISSION_EXPECTED_REFUSAL')
def wire():
 return{'schema':p.SCHEMA,'diagnostic_only':True,'valid':True,'queue_observed':True,'post_queue_services':3,'post_queue_send_callbacks':2,'post_queue_datagrams_emitted':1,'post_queue_would_block':1,'post_queue_interrupted':0,'post_queue_send_errors':0,'post_queue_partial_sends':0,'queue_service_offset_ms':10,'last_post_queue_service_offset_ms':12,'witness_owner_retired':True,'refusal':'NONE',**{name:False for name in p.FALSE}}
def blob(value):return json.dumps(value).encode()
def emit(path,value):path.write_bytes(blob(value));path.chmod(0o600)
def restoration():
 file=HERE/'capture_groups_transaction.py';text=file.read_text()
 new="receipt=d.json_object(d.read(receipt_path,16*1024**2));build_schema=receipt.get('schema')\n if build_schema=='coh-initial-progress-focused-v1':\n  from initial_progress_admission import native_input as progress_input\n  return progress_input(binary,receipt_path,receipt_pin,root)\n d.require"
 text=text.replace(new,"receipt=d.json_object(d.read(receipt_path,16*1024**2));build_schema=receipt.get('schema');d.require")
 text=text.replace('def orchestration_source_paths(compiled=None,native=None):','def orchestration_source_paths(compiled=None):')
 text=text.replace(" if type(native)is dict and native.get('build_schema')=='coh-initial-progress-focused-v1':\n  from initial_progress_admission import SOURCE_PATHS\n  paths.update(SOURCE_PATHS);paths.update(native['dependencies_sha256'])\n",'')
 text=text.replace('source_paths=orchestration_source_paths(compiled,native)','source_paths=orchestration_source_paths(compiled)')
 text=text.replace(" if native.get('build_schema')=='coh-initial-progress-focused-v1':\n  import initial_progress_admission as progress_admission\n  progress_admission.finish(sys.modules[__name__],report,native,received,target);return\n",'')
 text=text.replace("native.get('build_schema')in (INITIAL_BUILD_SCHEMA,'coh-initial-progress-focused-v1'),ROOT)","native.get('build_schema')==INITIAL_BUILD_SCHEMA,ROOT)")
 committed=subprocess.run(['git','show',LEGACY_REVISION+':native-android/engine/scenecatalog-server/capture_groups_transaction.py'],cwd=ROOT,capture_output=True,check=True).stdout
 need(text.encode()==committed,'EXACT_OLD_CAPTURE_REVERSAL')
 return{'legacy_revision':LEGACY_REVISION,'old_capture_sha256':p.pin(committed),'new_capture_sha256':p.pin(file.read_bytes()),'six_reversible_source_edits_only':True,'legacy_native_input_and_NativeBuilds_unchanged':True}
def qualify(output):
 global checks,refusals
 output.mkdir(parents=True,exist_ok=False);source=restoration();proofdir=ROOT/'native-android/engine/initial-capture/qualification/post-queue-progress-20261018';build=json.loads((proofdir/'qualification.json').read_bytes())
 with tempfile.TemporaryDirectory(prefix='coh-progress-admission-')as temp:
  root=Path(temp);binary=root/p.BASENAME;binary.write_bytes(gzip.decompress((proofdir/'coh-capture-initial-progress.gz').read_bytes()));binary.chmod(0o700);receipt=root/'build.json';emit(receipt,build)
  admitted=core.native_input(binary,receipt,p.pin(receipt.read_bytes()));need(admitted['build_schema']==p.BUILD_SCHEMA and admitted['current_kernel_build_bytes_verified']and not admitted['historical_receiver_equivalence_established'],'ACTUAL_NEW_ROLE');need(admitted['project_dependencies']==51 and admitted['binary']['sha256']==build['modes']['release']['production_role_sha256'],'ACTUAL_BINARY_CLOSURE')
  for key,value in(('schema',core.INITIAL_BUILD_SCHEMA),('passed',False),('actor_publication',True),('original_server_executed',True),('new_observer_static_bytes',113),('source_revision',CANARY)):
   bad=copy.deepcopy(build);bad[key]=value;emit(receipt,bad);refused(lambda:core.native_input(binary,receipt,p.pin(receipt.read_bytes())))
  for change in('source','missing-source','extra-source','binary','transition','mode'):
   bad=copy.deepcopy(build)
   if change=='source':bad['source_sha256'][next(iter(bad['source_sha256']))]='0'*64
   if change=='missing-source':bad['source_sha256'].pop(next(iter(bad['source_sha256'])))
   if change=='extra-source':bad['source_sha256'][CANARY]='0'*64
   if change=='binary':bad['modes']['release']['production_role_sha256']='0'*64
   if change=='transition':bad['transition']['five_reversible_identifier_or_call_edits_only']=False
   if change=='mode':bad['modes']['release']['focused_unit']['world_authority']=True
   emit(receipt,bad);refused(lambda:p.native_input(binary,receipt,p.pin(receipt.read_bytes())))
  emit(receipt,build);refused(lambda:p.native_input(binary,receipt,'0'*64));wrong=root/'old-receiver-name';wrong.write_bytes(binary.read_bytes());refused(lambda:p.native_input(wrong,receipt,p.pin(receipt.read_bytes())))
  need(set(core.NATIVE_BUILDS)=={'coh-local-scene-capture-build-v1',core.INITIAL_BUILD_SCHEMA},'OLD_SCHEMA_TABLE_UNCHANGED')
  old=core.orchestration_source_paths();new=core.orchestration_source_paths(native=admitted);need(new==old|set(p.SOURCE_PATHS)|set(admitted['dependencies_sha256']),'NEW_ORCHESTRATION_GIT_CLOSURE')
  baseline=wire();need(p.parse(blob(baseline))==baseline,'FIXED_PROJECTION')
  for key in baseline:
   changed=copy.deepcopy(baseline);changed.pop(key);refused(lambda:p.parse(blob(changed)))
   changed=copy.deepcopy(baseline)
   if type(changed[key])is bool:changed[key]=int(changed[key])
   elif type(changed[key])is int:changed[key]=bool(changed[key])
   else:changed[key]=CANARY
   refused(lambda:p.parse(blob(changed)))
  for key,value in(('extra',CANARY),('post_queue_services',1000001),('queue_service_offset_ms',600001),('refusal',CANARY),('post_queue_datagrams_emitted',2),('post_queue_services',0),('queue_observed',False),('witness_owner_retired',False),('valid',False)):
   changed=copy.deepcopy(baseline);changed[key]=value;refused(lambda:p.parse(blob(changed)))
  for key in p.FALSE:
   changed=copy.deepcopy(baseline);changed[key]=True;refused(lambda:p.parse(blob(changed)))
  for raw in(b'',b'[]',blob(baseline)[:-1]+b',"valid":true}',b'x'*1025,blob(baseline)+CANARY.encode()):refused(lambda:p.parse(raw))
  noqueue=wire();noqueue.update(queue_observed=False,**{name:0 for name in(*p.COUNTS,*p.OFFSETS)});need(p.parse(blob(noqueue))==noqueue,'NO_LATER_SERVICE_WITNESS')
  refused_value=wire();refused_value.update(valid=False,refusal='LIMIT');need(p.parse(blob(refused_value))==refused_value,'FIXED_REFUSED_WITNESS')
  received=root/'received';target=root/'retained';received.mkdir(mode=0o700);target.mkdir(mode=0o700);emit(received/'request-progress.json',baseline)
  report={'passed':True,'matching_groups_transaction_captured':True,'cleanup_verified':True,'pair':{'explicit_synthetic_owner_binding':True},'native_diagnostic':{'process_started':True,'stdout_validated':True,'native_sockets_closed':True,'reqallents_sent':1}}
  binding={'same_groups_owner_verified':True,'retained_after_owned_cleanup':True}
  with mock.patch.object(core,'retain_initial_observation',return_value=binding)as retained:
   core.finish_initial_observation(report,admitted,received,target);need(retained.call_count==1 and report['request_progress_diagnostic']==baseline and (target/'request-progress.json').read_bytes()==blob(baseline),'NEW_ROLE_RETAINS_FIXED_ONLY')
  need(report['passed']and not report['request_progress_private_binding']['public_upload_permitted'],'NO_GROUPS_PROMOTION')
  for field in('passed','matching_groups_transaction_captured','cleanup_verified'):
   bad=dict(report);bad[field]=False
   with mock.patch.object(core,'retain_initial_observation')as retained,mock.patch.object(p,'read_private')as read:
    core.finish_initial_observation(bad,admitted,received,target);need(not retained.called and not read.called,'CLEANUP_BEFORE_PRIVATE_READ')
  for change in('mode','symlink','hardlink'):
   path=root/('private-'+change);emit(path,baseline)
   if change=='mode':path.chmod(0o644)
   if change=='symlink':path.unlink();path.symlink_to(received/'request-progress.json')
   if change=='hardlink':os.link(path,root/'same-inode')
   refused(lambda:p.read_private(path))
  # Positive public projection uses a synthetic fixed run receipt; no packet,
  # service, process or original source-generation authority is invented.
  directory=root/'projection';(directory/'native').mkdir(parents=True,mode=0o700);emit(directory/'native/request-progress.json',baseline)
  private=dict(report,schema='coh-private-original-native-groups-run-v1',private_character_state=True,public_upload_permitted=False,source_generation_admitted=False,world_authority=False,native_tool=admitted,source_sha256={p.RELATIVE:p.pin(Path(p.__file__).read_bytes())})
  emit(directory/'capture-receipt.json',private);public=root/'public.json';need(p.emit(directory,public)==baseline and CANARY not in public.read_text(),'PUBLIC_PROJECTION')
  bad=dict(private);bad['request_progress_diagnostic']=dict(baseline,extra=CANARY);emit(directory/'capture-receipt.json',bad);refused(lambda:p.emit(directory,root/'refused.json'))
 sources={str(path.relative_to(ROOT)):p.pin(path.read_bytes())for path in(HERE/'capture_groups_transaction.py',HERE/'initial_progress_admission.py',Path(__file__).resolve(),HERE/'PROGRESS_ROLE_ADMISSION.md')}
 result={'schema':'coh-initial-progress-admission-focused-v1','passed':True,'checks':checks,'refusals':refusals,'source_sha256':sources,'native_build_receipt_sha256':p.pin((proofdir/'qualification.json').read_bytes()),'real_retained_native_ELF_admitted_read_only':True,'real51_current_source_pins_and_compiler_dependency_closure_checked':True,'legacy_capture_source_restoration':source,'new_retention_owner_predicate_explicit_double':True,'new_private_file_and_public_projection_IO_executed':True,'old_suites_or_native_qualifier_replayed':False,'original_server_or_native_binary_executed':False,'current_orchestration_required':'all51nativeinputs+newadapter enter existing committed Git source check before runtime','historical9c29_receiver_equivalence_claimed':False,'source_generation_admitted':False,'actor_publication':False,'ack_permitted':False,'world_authority':False}
 (output/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'refusals':refusals,'actual_source_pins':51}))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();qualify(args.output)
