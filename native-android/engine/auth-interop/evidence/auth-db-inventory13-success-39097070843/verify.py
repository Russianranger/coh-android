#!/usr/bin/env python3
"""Read-only same-copy fixed receipt/Git-source admission; no project imports."""
import ast
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
COMMIT='f3ee9db6bc8a323c896769f0952dd242fc79e2f4'
TREE='e6495d4fd3958a65537f38e7369d36e2f852f74d'
WORKFLOW='.github/workflows/native-auth-db-development.yml'
PINS={'artifact.zip':(19695,'6135be6a09d9f014c010278ab8f93168a7207800de3a25899024f675aaca854b'),
    'receipt.json':(82930,'3741c777e645b38b97e9ee87df8a9b7e26db4b038dd97f2290d5f81bea722a24'),
    'api.json':(4050,'25124e3d38ef5ba5d11ea2ed41066ca6bcc771674448a7a568fd9c77aef7f7e6')}


def need(ok,code):
    if not ok:raise ValueError(code)


def digest(raw):return hashlib.sha256(raw).hexdigest()


def decode(raw):
    def pairs(items):
        out={}
        for key,value in items:
            need(key not in out,'duplicate_json_key');out[key]=value
        return out
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:need(False,'nonfinite_json'))


def git(name):return subprocess.check_output(['git','-C',str(ROOT),'show',COMMIT+':'+name],stderr=subprocess.DEVNULL)


def verify():
    raw={}
    for name,(size,sha) in PINS.items():
        body=(HERE/name).read_bytes();need(len(body)==size and digest(body)==sha,'fixed_evidence_identity');raw[name]=body
    with zipfile.ZipFile(io.BytesIO(raw['artifact.zip'])) as archive:
        entries=archive.infolist();need(len(entries)==1 and entries[0].filename=='receipt.json' and
            entries[0].file_size==82930 and not entries[0].flag_bits&1,'sole_fixed_member')
        need(archive.read('receipt.json')==raw['receipt.json'] and archive.testzip() is None,'whole_member_crc_and_bytes')
    api=decode(raw['api.json']);v=decode(raw['receipt.json']);run=api['run'];job=api['jobs'][0];artifact=api['artifacts'][0]
    need(api['repository']=='Russianranger/coh-android' and len(api['jobs'])==len(api['artifacts'])==1 and
        run['id']==39097070843 and run['head_sha']==COMMIT and run['path']==WORKFLOW and
        run['head_branch']=='native-android' and run['status']=='completed' and run['conclusion']=='success' and
        job['id']==117585620683 and job['conclusion']=='success','exact_api_origin')
    steps={s['number']:s for s in job['steps']}
    need(all(step['conclusion']=='success' for step in steps.values()) and set(steps)=={1,2,3,4,5,6,7,8,9,17,18,19},'actual_step_outcomes')
    need(artifact['id']==12125401436 and artifact['size_in_bytes']==19695 and
        artifact['digest']=='sha256:'+PINS['artifact.zip'][1] and artifact['workflow_run']['head_sha']==COMMIT and
        artifact['expired'] is False and api['private_runtime_logs_included'] is False,'api_artifact_pin')
    need(v['repository_commit']==COMMIT and v['repository_tree']==TREE and str(v['github_run_id'])=='39097070843'
        and subprocess.check_output(['git','-C',str(ROOT),'rev-parse',COMMIT+'^{tree}'],text=True).strip()==TREE,'actual_source_revision')
    workflow=git(WORKFLOW);need(digest(workflow)=='c16f7ac6ee655e811e8fe3650aacd961af898bd4ad329490a6283f9bfe9bd89c','workflow_identity')
    # Parse the fixed quoted Bash Python body from YAML without executing it.
    import yaml
    data=yaml.safe_load(workflow);steps_yaml=next(iter(data['jobs'].values()))['steps']
    shell=next(s['run'] for s in steps_yaml if s.get('id')=='source_admission')
    body=shell.split('\n',1)[1].rsplit('\n',1)[0];tree=ast.parse(body);literals={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name):
            try:literals[node.targets[0].id]=ast.literal_eval(node.value)
            except (ValueError,TypeError):pass
    source=literals['current148'];common=literals['COMMON'];full=literals['pins']
    need(type(source) is dict and len(source)==148 and source==v['development_source_sha256'],'runtime148_exact_frozen_source')
    need(len(common)==2 and len(full)==156 and all(full[k]==h for k,h in dict(source,**common).items()),'source_gate156_nonself')
    extras={k:h for k,h in full.items() if k not in source and k not in common};need(len(extras)==6,'six_independent_proof_inputs')
    full[WORKFLOW]=digest(workflow);need(len(full)==157,'source_gate157_with_self')
    for name,sha in full.items():need(digest(git(name))==sha,'published_source_git_bytes')
    local=all((ROOT/name).is_file() and digest((ROOT/name).read_bytes())==sha for name,sha in v['development_source_sha256'].items())
    builder_archive=git('native-android/engine/auth-interop/evidence/threadname-db-build-39080037562/artifact.zip')
    with zipfile.ZipFile(io.BytesIO(builder_archive)) as z:builder_raw=z.read('receipt.json')
    need(digest(builder_raw)==v['new_db_candidate_admission']['receipt_sha256'],'original_db_build_receipt_pin')
    builder=decode(builder_raw)
    need(builder['source_file_map_sha256']==v['new_db_candidate_admission']['build_source_map_sha256'],'original_db_build_source_map_pin')
    historical_groups={'accepted_auth':dict(v['prior_auth_qualification']['source_pins']),
        'db_builder':builder['input_state_before']['project_inputs_sha256'],
        'retained_crypto_reference':v['development_probe_build']['retained_crypto']['qualified_core_source_sha256']}
    for group in historical_groups.values():
        for name,sha in group.items():need(digest(git(name))==sha,'historical_source_git_bytes')
    proof=decode(git(literals['PROOF']));review=decode(git(literals['REVIEW']))
    kernel=decode(git(literals['KERNEL_REVIEW']));runtime=v['development_source_sha256']
    need(proof['source_inputs_sha256']==runtime==review['source_inputs_sha256'] and
        review['additional_common_integration_source_sha256']==common and proof['passed'] is True and review['passed'] is True,
        'current_proof_review_source_binding')
    c_prefix=literals['C50'];c_raw=gzip.decompress(git(c_prefix+'.json.gz'))
    need(digest(c_raw)=='bf6c7a0730dd912cbb6fa1c18e61d6fcc1c34689a121aa18cf3fa3745c523376','c50_raw_source_proof')
    c=decode(c_raw);binding=decode(git(c_prefix+'-binding.json'))
    need(c['passed'] is True and len(c['source_sha256'])==50 and c['source_sha256']==binding['source_sha256'] and
        all(source[name]==sha for name,sha in c['source_sha256'].items()) and
        all(kernel['source_inputs_sha256'][name]==sha for name,sha in c['source_sha256'].items()),'current_c50_source_binding')
    c36=decode(gzip.decompress(git(literals['C36']+'.json.gz')))['source_sha256']
    old=binding['previous_changed_source_sha256'];need(len(c36)==36 and len(old)==3 and
        {k for k,h in c36.items() if source[k]!=h}==set(old) and all(c36[k]==h for k,h in old.items()),'exact_three_c36_transitions')
    predecessor='6e96fe22a567a3e252449feb37483cfea1566d8a'
    for name,sha in old.items():
        previous=subprocess.check_output(['git','-C',str(ROOT),'show',predecessor+':'+name],stderr=subprocess.DEVNULL)
        need(digest(previous)==sha and source[name]==c['source_sha256'][name],'historical_precursor_current_successor_binding')
    summary=v['account_controls_source_qualification']
    need(summary['inventory_previous_sha256']==old and summary['inventory_current_sha256']=={k:source[k] for k in old} and
        summary['inventory_predecessor_revision']==predecessor and summary['old_proofs_reused_for_unchanged_inputs_only'] is True and
        summary['old_qualifiers_reexecuted'] is False and summary['actual_account_control_bodies_inferred'] is False and
        summary['unknown_command_policy_relaxed'] is False and summary['owner_success_predicate_changed'] is False,'receipt_composition_roles')
    need(v['passed'] is True and 'failure' not in v and 'development_probe_failure_observation' not in v,'actual_success_scope')
    d=v['development_probe_result'];p=d['db_received_prefix']
    need(d['schema']=='coh-auth-db-development-policy-result-projection-v2' and d['passed'] is True and
        d['native_producer_schema']=='coh-auth-db-development-list-probe-v2' and
        d['normalized_policy_schema']=='coh-auth-db-development-list-probe-v1' and
        (d['probe_stage'],d['phase'],d['failure'],d['status'],d['auth_phase'],d['db_phase'],d['auth_final_phase'],d['db_final_phase'])==
        (9,3,0,0,7,4,8,11),'actual_native_completion_phase')
    need(all(type(d[k]) is int and d[k]==1 for k in ('begun','grant_consumed','selected_shard_verified','complete_matching_list',
        'all_slots_empty_unlocked','cleanup_cancel_close_used','controllers_destroyed','development_skip_requested','udp_cleanup_complete')) and
        (d['slots'],d['base_slots'],d['bonus_slots'])==(48,12,0),'actual_complete_empty_list')
    need(d['auth_frames']==4 and d['db_login_requests']==d['db_player_lists']==1 and d['db_queue_updates']==
        d['db_unsupported']==d['db_choices']==d['db_handoffs']==0 and d['udp_created']==d['udp_closed']==1 and
        d['udp_active']==d['udp_close_failures']==d['udp_cleanup_failures']==0,'actual_native_counts')
    need(all(d[k] is True for k in ('checksum_measured_from_actual_probe','local_sensitive_buffers_wiped','owner_cleanup_complete',
        'socket_cleanup_complete','development_skip_source_inference_only')) and all(d[k] is False for k in
        ('server_development_skip_observed','graceful_peer_disconnect_acknowledged','real_server_provenance_verified_by_probe')) and
        all(type(d[k]) is int and d[k]==0 for k in ('normal_version_admitted','checksum_reference_admitted','character_selected',
        'map_handoff_verified','current_world_verified')),'native_cleanup_and_explicit_policy_limit')
    expected=['DBGAMESERVER_ACCOUNTSERVER_UNAVAILABLE','DBGAMESERVER_ACCOUNTSERVER_CHARCOUNT',
        'DBGAMESERVER_ACCOUNTSERVER_CHARCOUNT','DBGAMESERVER_ACCOUNTSERVER_INVENTORY','DBGAMESERVER_SEND_PLAYERS']
    need([e['command'] for e in p['entries']]==expected and len(p['entries'])==p['total_seen']==5 and
        p['instances']==1 and p['service_calls']==8 and p['available'] is p['context_verified'] is p['retired'] is True and
        p['truncated'] is p['first_unsupported_attributed'] is p['body_acceptance_observed'] is False and
        all(e==dict(command=name,header_decoded=True,phase='WAIT_PLAYERS',legacy=False,compressed=False)
            for e,name in zip(p['entries'],expected)),'actual_fixed_received_header_prefix')
    before=v['development_runtime_before_probe'];after=v['development_runtime_after_probe'];start=v['owned_service_generations_start']
    for name in ('auth','db','sql'):need(start[name]==before[name]==after[name],'service_generation_stability')
    need(before==after and v['development_runtime_after_probe_verified'] is True and
        before['registered_group_membership_verified'] is True and v['actual_game_database_user_tables']==99 and
        before['channel']['loopback_pair_verified'] is True and before['game_listener']['udp_port']==7000,'runtime_channel_schema_group_stability')
    project_closure=dict(source,**common)
    for group in historical_groups.values():
        for name,sha in group.items():
            need(name not in project_closure or project_closure[name]==sha,'source_group_conflict')
            project_closure[name]=sha
    build=v['development_probe_build'];need(len(build['project_sources_sha256'])==17 and
        all(project_closure[name]==sha for name,sha in build['project_sources_sha256'].items()),'new_project17_source_binding')
    need({name:len(rows) for name,rows in build['objects'].items()}=={'coh-auth-db-development':17,'chromium_zlib':21}
        and all(row['machine']=='AMD64' and row['bytes']>0 for rows in build['objects'].values() for row in rows.values()),'reported_new_x64_object_closure')
    need(build['binary']['sha256']=='d3b649a3555e3809a6c4f1f44e9d05614dff7634d96b9cea3a01b15789c4fb35' and
        build['binary']['bytes']==3300864 and build['binary']['no_unadmitted_dll_imports'] is True and
        build['binary']['delay_imports_absent'] is True,'reported_new_pe_identity')
    need(v['development_platform_preflight']['passed'] is True and
        v['development_platform_preflight']['native_producer_schema']=='coh-auth-db-development-platform-preflight-v2' and
        v['development_platform_preflight']['udp_created']==0,'actual_platform_preflight')
    def launch(x):
        r=x['primary_resume'];resume_flags=('passed','process_identity_verified','single_owned_thread_verified',
            'thread_identity_verified','generation_recheck_verified','resume_attempted','previous_suspend_count_one',
            'resume_observed','snapshots_closed','thread_handle_closed','cleanup_verified')
        return (all(r[k] is True for k in resume_flags) and r['snapshot_passes']==2 and
            2<=r['snapshot_entries_examined']<=131072 and r['secondary_close_failures']==0 and all(x[k] is True for k in ('assignment_verified','resume_verified','empty_before_close','scope_closed_verified'))
            and x['launch_state']=='RESUMED' and r['passed'] is True and r['previous_suspend_count_one'] is True
            and r['resume_observed'] is True and r['cleanup_verified'] is True and r['failure']=='NONE')
    need(all(launch(x) for x in v['development_service_job_launches']) and len(v['development_service_job_launches'])==2 and
        all(c['succeeded'] is c['owned_cleanup_complete'] is c['owned_job_empty_before_close'] is c['owned_job_assignment_verified'] is True
            and launch(c['launch']) for c in build['commands']),'actual_owned_launch_and_job_cleanup')
    cleanup=('owned_service_cleanup_complete','owned_firewall_cleanup_complete','owned_localdb_cleanup_complete',
        'private_files_removed','source_inputs_unchanged','development_all_owned_service_jobs_empty_before_close',
        'owned_registry_cleanup_complete','development_candidate_and_source_inputs_unchanged','private_probe_build_removed')
    need(all(v[k] is True for k in cleanup) and all(d[k] is True for k in ('local_sensitive_buffers_wiped','socket_cleanup_complete','owner_cleanup_complete')),'actual_cleanup_intersection')
    registry=v['owned_empty_registry_cleanup'];need(all(registry[k] is True for k in
        ('services_stopped_confirmed','nonce_absent_both_views','owned_parent_absent_both_views','handles_closed','cleanup_verified')) and
        registry['failure'] is registry['cleanup_failure'] is None and registry['registry_atomicity_claimed'] is False,'actual_empty_registry_retirement')
    need(v['provisional_development_db_player_list_verified'] is v['source_inferred_development_exception_used'] is True,'provisional_success_label')
    preflight=v['development_platform_preflight_observation']
    need(all(preflight[k] is True for k in ('owned_child_cleanup_complete','owned_child_job_empty_before_close','owned_child_job_assignment_verified')) and
        preflight['owned_child_launch_state']=='RESUMED','actual_preflight_job_cleanup')
    false=('server_development_skip_observed','normal_version_admitted','checksum_reference_admitted','character_selected',
        'map_handoff_verified','current_world_verified','auth_only_negative_cases_repeated','grant_values_exported',
        'private_credentials_exported','accepted_runtime_replaced','shipping_profiles_modified','checksum_policy_relaxed','private_console_exported')
    need(all(v[k] is False for k in false),'unclosed_claims_remain_false')
    return {'schema':'coh-actual-provisional-development-empty-list-success-verification-v1','passed':True,
        'repository_commit':COMMIT,'repository_tree':TREE,'github_run_id':39097070843,'job_id':117585620683,
        'artifact_id':12125401436,'evidence':{k:{'bytes':n,'sha256':h} for k,(n,h) in PINS.items()},
        'source_gate_sha256':full,'source_gate_count':157,'runtime_source_map_count':148,'common_build_source_map_count':2,
        'preservation_worker_source148_equal':local,'historical_source_map_counts':{k:len(x) for k,x in historical_groups.items()},
        'current_c50_source_input_count':50,'historical_c36_inputs':36,'c36_changed_inputs':3,'c36_current_unchanged_inputs':33,
        'actual_received_header_prefix':expected,'observation_scope':'same-copy header prefix only',
        'first_unsupported_attributed':False,'prefix_body_acceptance_observed':False,'account_control_body_values_observed':False,
        'complete_matching_empty_unlocked_list_verified':True,'slots':48,'base_slots':12,'bonus_slots':0,
        'actual_internal_server_development_skip_observed':False,'provisional_development_policy':True,
        'normal_version_or_checksum_reference_admitted':False,'character_creation_or_selection_verified':False,
        'db_or_map_handoff_verified':False,'all_cleanup_and_source_gates_verified':True,
        'reported_probe_binary':build['binary'],'probe_binary_file_available_to_this_verifier':False,
        'project_and_zlib_object_counts':[17,21],'download_or_raw_logs_performed_by_verifier':False,
        'project_helpers_or_tests_or_runtime_executed_by_verifier':False}



if __name__=='__main__':print(json.dumps(verify(),indent=2,sort_keys=True))
