#!/usr/bin/env python3
"""Read-only same-copy fixed receipt/Git-source admission; no project imports."""
import ast
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
COMMIT='b321a3dd883031072f26c63d4f2d9f4866b63d9d'
TREE='ff2d168a643b3751965caf6e67d283ceb71c3bad'
WORKFLOW='.github/workflows/native-auth-db-development.yml'
PINS={'artifact.zip':(17000,'dfa3341369b6659e9be3451d8b99cd6adc2d3fa7d1d1ebacd2f051894c448b8e'),
    'receipt.json':(73968,'44c6eeb9eaa391c550e3534e925d0dcc05eb2954e9bdd186bb7c5526e5604ef0'),
    'api.json':(3485,'7945c30037835cf92c8d102c9be7ccfb2e23f93b4a96f67e5edf1c6e4cefd6ca')}


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
            entries[0].file_size==73968 and not entries[0].flag_bits&1,'sole_fixed_member')
        need(archive.read('receipt.json')==raw['receipt.json'] and archive.testzip() is None,'whole_member_crc_and_bytes')
    api=decode(raw['api.json']);v=decode(raw['receipt.json']);run=api['run'];job=api['jobs'][0];artifact=api['artifacts'][0]
    need(api['repository']=='Russianranger/coh-android' and len(api['jobs'])==len(api['artifacts'])==1 and
        run['id']==39092477566 and run['head_sha']==COMMIT and run['path']==WORKFLOW and
        run['head_branch']=='native-android' and run['status']=='completed' and run['conclusion']=='failure' and
        job['id']==117571944787 and job['conclusion']=='failure','exact_api_origin')
    steps={s['number']:s for s in job['steps']}
    need(all(steps[n]['conclusion']=='success' for n in (5,6,7,9)) and steps[8]['conclusion']=='failure','actual_step_outcomes')
    need(artifact['id']==12123094046 and artifact['size_in_bytes']==17000 and
        artifact['digest']=='sha256:'+PINS['artifact.zip'][1] and artifact['head_sha']==COMMIT and
        artifact['expired'] is False and api['private_logs_included'] is False,'api_artifact_pin')
    need(v['repository_commit']==COMMIT and v['repository_tree']==TREE and str(v['github_run_id'])=='39092477566'
        and subprocess.check_output(['git','-C',str(ROOT),'rev-parse',COMMIT+'^{tree}'],text=True).strip()==TREE,'actual_source_revision')
    workflow=git(WORKFLOW);need(digest(workflow)=='2c0d46c3b5a30f47ea8e191df7e606b0a6023adb05f2dc01ee7907551dda33d6','workflow_identity')
    # Parse the fixed quoted Bash Python body from YAML without executing it.
    import yaml
    data=yaml.safe_load(workflow);steps_yaml=next(iter(data['jobs'].values()))['steps']
    shell=next(s['run'] for s in steps_yaml if s.get('id')=='source_admission')
    body=shell.split('\n',1)[1].rsplit('\n',1)[0];tree=ast.parse(body);source=None;extras=None
    for node in tree.body:
        if isinstance(node,ast.Assign):
            names=[t.id for t in node.targets if isinstance(t,ast.Name)]
            if 'source' in names:source=ast.literal_eval(node.value)
            if 'pins' in names:extras=ast.literal_eval(node.value.values[1])
    need(type(source) is dict and len(source)==106 and v['development_source_sha256']==source,'runtime_and_frozen_source106')
    need(type(extras) is dict and len(extras)==2,'two_independent_proof_inputs')
    full=dict(source,**extras);full[WORKFLOW]=digest(workflow);need(len(full)==109,'full_source_gate109')
    for name,sha in full.items():need(digest(git(name))==sha,'published_source_git_bytes')
    local=all((ROOT/name).is_file() and digest((ROOT/name).read_bytes())==sha for name,sha in source.items())
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
    proof=decode(git(next(name for name in extras if name.endswith('/host.json'))))
    review=decode(git(next(name for name in extras if name.endswith('/review.json'))))
    need(proof['source_inputs_sha256']==source==review['source_inputs_sha256'] and proof['passed'] is True and review['passed'] is True,'proof_review_source_binding')
    spans={}
    for name,offset,size,sha in (
        ('native-android/engine/dbclient/coh_db_session.c',5067,565,'389994ca84d5166da707cdf15e295d9fce5542a80babedff2acbaf4fc3379303'),
        ('native-android/engine/dbclient/coh_db_session.c',5633,3002,'f4f451d01e659370897d1d1643b911412b7f355c10366bd2c1d28ee9d6e57bba'),
        ('native-android/engine/dbclient/coh_db_session.c',8636,2155,'e7d81733678de55659918014e5eac62e07760842f546932a1adeb02975a13c61'),
        ('native-android/engine/auth-interop/deployment/windows/auth_db_development_owner.c',9013,1678,'70c1e060ea1c406298d185806107ac5f4731aa242627645a20f9cecddd618940')):
        need(digest(git(name)[offset:offset+size])==sha,'whole_function_source_span')
        spans[name+':'+str(offset)]={'offset':offset,'bytes':size,'sha256':sha}
    need(v['passed'] is False and v['failure']=='development_private_probe_refused','actual_failure_scope')
    d=v['development_probe_failure_observation'];p=d['db_received_prefix']
    need(d['json_state']=='VALID' and d['child_state']=='EXIT_ONE' and d['stage']=='OWNER_SERVICE' and
        d['phase']=='FAILED' and d['failure']=='DB' and d['status']=='UNSUPPORTED' and
        d['auth_phase']=='AUTHORIZED' and d['db_phase']=='WAIT_PLAYERS' and d['native_passed'] is False,'actual_native_phase')
    need(d['auth_frames']==4 and d['db_login_requests']==1 and d['db_player_lists']==d['db_queue_updates']==
        d['db_choices']==d['db_handoffs']==0 and d['db_unsupported']==3 and d['udp_created']==d['udp_closed']==1 and
        d['udp_active']==d['udp_close_failures']==d['udp_cleanup_failures']==0,'actual_native_counts')
    expected=['DBGAMESERVER_ACCOUNTSERVER_UNAVAILABLE','DBGAMESERVER_ACCOUNTSERVER_CHARCOUNT','DBGAMESERVER_ACCOUNTSERVER_CHARCOUNT']
    need([e['command'] for e in p['entries']]==expected and len(p['entries'])==p['total_seen']==3 and
        p['instances']==1 and p['service_calls']==5 and p['available'] is p['context_verified'] is p['retired'] is True and
        p['truncated'] is p['first_unsupported_attributed'] is p['body_acceptance_observed'] is False and
        all(e==dict(command=name,header_decoded=True,phase='WAIT_PLAYERS',legacy=False,compressed=False)
            for e,name in zip(p['entries'],expected)),'actual_fixed_received_header_prefix')
    before=v['development_runtime_before_probe'];after=v['development_runtime_after_probe'];start=v['owned_service_generations_start']
    for name in ('auth','db','sql'):need(start[name]==before[name]==after[name],'service_generation_stability')
    need(before==after and v['development_runtime_after_probe_verified'] is True and
        before['registered_group_membership_verified'] is True and v['actual_game_database_user_tables']==99 and
        before['channel']['loopback_pair_verified'] is True and before['game_listener']['udp_port']==7000,'runtime_channel_schema_group_stability')
    project_closure=dict(source)
    for group in historical_groups.values():
        for name,sha in group.items():
            need(name not in project_closure or project_closure[name]==sha,'source_group_conflict')
            project_closure[name]=sha
    build=v['development_probe_build'];need(len(build['project_sources_sha256'])==16 and
        all(project_closure[name]==sha for name,sha in build['project_sources_sha256'].items()),'new_project16_source_binding')
    need({name:len(rows) for name,rows in build['objects'].items()}=={'coh-auth-db-development':16,'chromium_zlib':21}
        and all(row['machine']=='AMD64' and row['bytes']>0 for rows in build['objects'].values() for row in rows.values()),'reported_new_x64_object_closure')
    need(build['binary']['sha256']=='8442838e2c8b19a68115e8797b6cefd8e6f784e6649c12a08b0db148989dcfaa' and
        build['binary']['bytes']==3298304 and build['binary']['no_unadmitted_dll_imports'] is True and
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
    need(all(v[k] is True for k in cleanup) and all(d[k] is True for k in ('local_sensitive_buffers_wiped',
        'socket_cleanup_complete','owned_child_cleanup_complete','owned_child_job_empty_before_close','owned_child_job_assignment_verified')),'actual_cleanup_intersection')
    registry=v['owned_empty_registry_cleanup'];need(all(registry[k] is True for k in
        ('services_stopped_confirmed','nonce_absent_both_views','owned_parent_absent_both_views','handles_closed','cleanup_verified')) and
        registry['failure'] is registry['cleanup_failure'] is None and registry['registry_atomicity_claimed'] is False,'actual_empty_registry_retirement')
    false=('provisional_development_db_player_list_verified','source_inferred_development_exception_used',
        'server_development_skip_observed','normal_version_admitted','checksum_reference_admitted','character_selected',
        'map_handoff_verified','current_world_verified','auth_only_negative_cases_repeated','grant_values_exported',
        'private_credentials_exported','accepted_runtime_replaced','shipping_profiles_modified','checksum_policy_relaxed','private_console_exported')
    need(all(v[k] is False for k in false),'unclosed_claims_remain_false')
    return {'schema':'coh-actual-development-db-received-prefix-verification-v1','passed':True,
        'repository_commit':COMMIT,'repository_tree':TREE,'github_run_id':39092477566,'job_id':117571944787,
        'artifact_id':12123094046,'evidence':{k:{'bytes':n,'sha256':h} for k,(n,h) in PINS.items()},
        'source_gate_sha256':full,'source_gate_count':109,'runtime_source_map_count':106,
        'current_worker_source106_equal':local,'historical_source_map_counts':{k:len(x) for k,x in historical_groups.items()},
        'actual_received_header_prefix':expected,'observation_scope':'same-copy header prefix only',
        'source_derived_owner_zero_unsupported_refusal_supported':True,
        'source_derived_refusal_whole_function_spans':spans,
        'first_unsupported_attributed':False,'body_acceptance_observed':False,
        'complete_player_list_verified':False,'normal_version_or_checksum_reference_admitted':False,
        'db_or_map_handoff_verified':False,'all_cleanup_and_source_gates_verified':True,
        'reported_probe_binary':build['binary'],'probe_binary_file_available_to_this_verifier':False,
        'project_and_zlib_object_counts':[16,21],'download_or_raw_logs_performed_by_verifier':False,
        'project_helpers_or_tests_or_runtime_executed_by_verifier':False}


if __name__=='__main__':print(json.dumps(verify(),indent=2,sort_keys=True))
