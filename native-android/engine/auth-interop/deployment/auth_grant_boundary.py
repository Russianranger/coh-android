#!/usr/bin/env python3
"""Historical auth-only evidence diagnostic; exposes no credential/grant factory."""
import argparse,hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
RECEIPT_SHA='1b1bea257b8e29f73543cffc4c2148071f738036ee2cd5adc122417160106c94'
BINDER_SHA='8226b673b4143a1525296abc5d879f8a948f0cd57a5c6ccc5f5297452e51af40'
SOURCE='28fe37cc2432db4adbfe047bd07a1e738d6aa754'
TREE='f634e21e230009fa8edc91d15429cd4da69eee8c'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def checked(raw,digest,limit):
 if type(raw)is not bytes or len(raw)>limit or sha(raw)!=digest:raise ValueError('historical_input_identity')
 return json.loads(raw)
def diagnose(receipt_raw,binder_raw,root):
 q=checked(receipt_raw,RECEIPT_SHA,65536);binder=checked(binder_raw,BINDER_SHA,128*1024)
 if q['repository_commit']!=SOURCE or binder['source_commit']!=SOURCE or q['github_run_id']!='38996587760':raise ValueError('historical_source_run')
 if q['original_source_tree']!=TREE or binder['run_id']!=38996587760:raise ValueError('historical_original_tree')
 git=lambda *args:subprocess.check_output(['git','--no-replace-objects','-C',str(root),*args],timeout=30)
 if git('rev-parse',SOURCE+':upstream/ouroboros').decode().strip()!=TREE:raise ValueError('historical_original_git_tree')
 for name,digest in binder['source_sha256'].items():
  if sha(git('show',SOURCE+':'+name))!=digest:raise ValueError('historical_helper_source_identity')
 for name,digest in q['profile']['source_files_sha256'].items():
  if sha(git('show',SOURCE+':upstream/ouroboros/'+name))!=digest:raise ValueError('historical_server_source_identity')
 profile=git('show',SOURCE+':native-android/engine/auth-interop/deployment/auth_service_profile.py')
 if b"'UserData': False" not in profile or b'auth-only server table must remain empty' not in profile:raise ValueError('historical_auth_only_profile')
 if q['passed'] is not True or q['encrypted_account_login_verified'] is not True or q['authenticated_db_map_handoff_verified'] is not False:raise ValueError('historical_auth_scope')
 for mode in ('normal','capped'):
  valid=q['probe_results'][mode]['valid']
  if valid['state']!=5 or valid['shards']!=0 or valid['received_frames']!=3 or valid['protocol']!=191021 or valid['db_handoff_attempted'] is not False:raise ValueError('historical_no_play_authorization')
  for result in q['probe_results'][mode].values():
   if result['socket_cleanup_complete'] is not True or result['password_retained_after_close'] is not False:raise ValueError('historical_probe_lifecycle')
 for name in ('owned_authserver_job_stop_complete','owned_authserver_listeners_absent','owned_authserver_cleanup_complete','owned_localdb_cleanup_complete','private_files_removed','source_inputs_unchanged'):
  if q[name] is not True:raise ValueError('historical_closed_generation_required')
 if q['general_tcp_segmentation_accepted'] is not False or q['receiver_segmentation_controlled'] is not False:raise ValueError('historical_transport_scope')
 required=[
  {'gate':'fresh_authorized_client_session','missing':'Actual selected nonempty registered shard and AC_PLAY_OK opcode7 ten-byte body: gamekeyU32,UIDU32,shardU8 from the owned decrypted TCP session. Historical SHARDS_READY is insufficient.'},
  {'gate':'full_auth_db_channel','missing':'UserData=true, nonqueue profile; owned shard registration and live AuthServer-to-DB channel plus exact SQ_ABOUT_TO_PLAY body159..172 bytes/opcode0/full128authbytes and SQ_GAME_DATA body133/opcode7.'},
  {'gate':'matching_one_shot_cookie','missing':'Actual DB-to-Auth PLAY_OK nine-byte body/opcode0/UIDU32/cookieU32 matched to client AC_PLAY_OK and the fresh account/shard/channel generation. Source matching U32 cookie may be zero; no fabricated nonzero rule or consumer TTL.'},
  {'gate':'actual_normal_version_checksum','missing':'Actual nondevelopment original version-provider observation, authorized reference16-byte executable MD5, full fail-closed DB checksum policy, correct and wrong-version/checksum/reference controls. Auth frame XOR is not game executable checksum.'},
  {'gate':'fresh_owned_readiness','missing':'New owned LocalDB process generation and x86 ODBC healthy observation before AuthServer start plus owned listener/PID binding. Reuse exact accepted1024MiB profile and qualified binaries; historical readiness/PID is stale after verified cleanup.'},
  {'gate':'lifecycle_owned_transfer','missing':'Validated CohLogin AUTHORIZED state and fresh private handoff consumption through existing noninjectable coordinator; DB and Map opaque owner bridges preserve subsequent selection provenance but cannot authenticate an absent ticket.'}]
 return {'schema':'coh-historical-auth-grant-boundary-v1','historical_run_id':38996587760,'receipt_sha256':RECEIPT_SHA,'binder_sha256':BINDER_SHA,'source_commit':SOURCE,'source_helper_pins_verified':len(binder['source_sha256']),'server_source_pins_verified':len(q['profile']['source_files_sha256']),'encrypted_account_login_accepted':True,'historical_valid_modes':['normal','capped'],'historical_client_state':'SHARDS_READY','historical_shards':0,'historical_user_data_profile':False,'historical_generation_closed':True,'fresh_authentication_grant_available':False,'ticket_bytes_retained':False,'account_uid_or_run_id_used_as_live_generation':False,'missing_prerequisites':required,'sql_memory_limit_mb':q['sql_memory_profile']['sql_memory_limit_mb'],'historical_x86_odbc_healthy':q['x86_readiness_before_start']['healthy'],'fresh_readiness_required':True,'general_tcp_segmentation_accepted':False,'complete_encrypted_db_map_or_world_accepted':False,'service_executed_by_diagnostic':False}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--expected-commit',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 root=a.source_root.resolve();git=lambda *v:subprocess.check_output(['git','--no-replace-objects','-C',str(root),*v],timeout=30);script=Path(__file__).resolve();raw=script.read_bytes()
 if git('rev-parse','HEAD').decode().strip()!=a.expected_commit or raw!=git('show',a.expected_commit+':'+script.relative_to(root).as_posix()) or a.output.exists():raise ValueError('current_checked_source_and_new_output_required')
 directory=HERE.parent/'evidence/auth-success-38996587760';result=diagnose((directory/'receipt.json').read_bytes(),(directory/'source-binder.json').read_bytes(),root)
 if script.read_bytes()!=raw or git('rev-parse','HEAD').decode().strip()!=a.expected_commit:raise ValueError('current_source_changed')
 result.update(diagnostic_source_commit=a.expected_commit,diagnostic_sha256=sha(raw));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'historical_encrypted_account_login_accepted':True,'fresh_grant_available':False,'missing_gates':len(result['missing_prerequisites'])}))
