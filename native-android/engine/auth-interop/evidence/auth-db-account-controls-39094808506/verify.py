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
COMMIT='6e96fe22a567a3e252449feb37483cfea1566d8a'
TREE='8d1fb5f8e37cfa6b277ddd9f49d903fbfc703ad6'
WORKFLOW='.github/workflows/native-auth-db-development.yml'
PINS={'artifact.zip':(18245,'8d8b2518f5420a129d097b705c50406f5cbf323d1dd697c5941bb7dfa01bd4bd'),
    'receipt.json':(77676,'868fbad511f087d7cee898201054b3270499c94cac5328d37a1a6f570b332080'),
    'api.json':(3478,'b84645297bba4e8ba2c6c06666ef8120c287ab1b91ccf6216fe6d9dc20777c03')}


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
            entries[0].file_size==77676 and not entries[0].flag_bits&1,'sole_fixed_member')
        need(archive.read('receipt.json')==raw['receipt.json'] and archive.testzip() is None,'whole_member_crc_and_bytes')
    api=decode(raw['api.json']);v=decode(raw['receipt.json']);run=api['run'];job=api['jobs'][0];artifact=api['artifacts'][0]
    need(api['repository']=='Russianranger/coh-android' and len(api['jobs'])==len(api['artifacts'])==1 and
        run['id']==39094808506 and run['head_sha']==COMMIT and run['path']==WORKFLOW and
        run['head_branch']=='native-android' and run['status']=='completed' and run['conclusion']=='failure' and
        job['id']==117578922139 and job['conclusion']=='failure','exact_api_origin')
    steps={s['number']:s for s in job['steps']}
    need(all(steps[n]['conclusion']=='success' for n in (5,6,7,9)) and steps[8]['conclusion']=='failure','actual_step_outcomes')
    need(artifact['id']==12124625207 and artifact['size_in_bytes']==18245 and
        artifact['digest']=='sha256:'+PINS['artifact.zip'][1] and artifact['head_sha']==COMMIT and
        artifact['expired'] is False and api['private_logs_included'] is False,'api_artifact_pin')
    need(v['repository_commit']==COMMIT and v['repository_tree']==TREE and str(v['github_run_id'])=='39094808506'
        and subprocess.check_output(['git','-C',str(ROOT),'rev-parse',COMMIT+'^{tree}'],text=True).strip()==TREE,'actual_source_revision')
    workflow=git(WORKFLOW);need(digest(workflow)=='b2c8b2078237120dd2f42b0e421208f722182d8ab2feeaf4e39bc4e7ae26a539','workflow_identity')
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
    need(type(source) is dict and len(source)==130 and len(v['development_source_sha256'])==128 and all(source[name]==sha for name,sha in v['development_source_sha256'].items()),'runtime128_and_frozen_source130')
    need(type(extras) is dict and len(extras)==6,'six_independent_proof_inputs')
    full=dict(source,**extras);full[WORKFLOW]=digest(workflow);need(len(full)==137,'full_source_gate137')
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
    proof=decode(git(next(name for name in extras if name.endswith('/host.json'))))
    review=decode(git(next(name for name in extras if name.endswith('/review.json'))))
    runtime=v['development_source_sha256']
    common={name:sha for name,sha in source.items() if name not in runtime}
    need(set(common)=={'native-android/engine/dbclient/CMakeLists.txt','native-android/combined-client/app/src/main/cpp/CMakeLists.txt'} and
        proof['source_inputs_sha256']==runtime==review['source_inputs_sha256'] and
        review['additional_common_integration_source_sha256']==common and proof['passed'] is True and review['passed'] is True,'proof_review_source_binding')
    c_prefix='native-android/engine/dbclient/qualification/account-controls-02b54d43f'
    c_raw=gzip.decompress(git(c_prefix+'.json.gz'));need(digest(c_raw)=='8b4a16f704f53095d75c822f8f4635a707b8b965f2f1938888ff2d71c2449c1a','c99_raw_source_proof')
    c=decode(c_raw);binding=decode(git(c_prefix+'-binding.json'))
    need(c['passed'] is True and len(c['source_sha256'])==36 and c['source_sha256']==binding['source_sha256'] and
        all(source[name]==sha for name,sha in c['source_sha256'].items()),'current_c99_source36_binding')
    spans={}
    for name,offset,size,sha in (
        ('native-android/engine/dbclient/coh_db_session.c',5104,566,'8fa53f31f112930f1fc7ad477dd53437614dca85b0157d002cc9b20231270b47'),
        ('native-android/engine/dbclient/coh_db_session.c',5670,3819,'9e029c6efb55747905a801369c0700ca98b38dd11ed249720d4aa756d8711810'),
        ('native-android/engine/dbclient/coh_db_session.c',9489,2156,'007e2dab642e7f80b5dcc260df8b36bf7ad3e545ae136ec37a0c880a5a1ec041'),
        ('native-android/engine/auth-interop/deployment/windows/auth_db_development_owner.c',9013,1678,'70c1e060ea1c406298d185806107ac5f4731aa242627645a20f9cecddd618940')):
        need(digest(git(name)[offset:offset+size])==sha,'whole_function_source_span')
        spans[name+':'+str(offset)]={'offset':offset,'bytes':size,'sha256':sha}
    need(v['passed'] is False and v['failure']=='development_private_probe_refused','actual_failure_scope')
    d=v['development_probe_failure_observation'];p=d['db_received_prefix']
    need(d['json_state']=='VALID' and d['child_state']=='EXIT_ONE' and d['stage']=='OWNER_SERVICE' and
        d['phase']=='FAILED' and d['failure']=='DB' and d['status']=='UNSUPPORTED' and
        d['auth_phase']=='AUTHORIZED' and d['db_phase']=='WAIT_PLAYERS' and d['native_passed'] is False,'actual_native_phase')
    need(d['auth_frames']==4 and d['db_login_requests']==1 and d['db_player_lists']==d['db_queue_updates']==
        d['db_choices']==d['db_handoffs']==0 and d['db_unsupported']==1 and d['udp_created']==d['udp_closed']==1 and
        d['udp_active']==d['udp_close_failures']==d['udp_cleanup_failures']==0,'actual_native_counts')
    expected=['DBGAMESERVER_ACCOUNTSERVER_UNAVAILABLE','DBGAMESERVER_ACCOUNTSERVER_CHARCOUNT','DBGAMESERVER_ACCOUNTSERVER_CHARCOUNT','DBGAMESERVER_ACCOUNTSERVER_INVENTORY']
    need([e['command'] for e in p['entries']]==expected and len(p['entries'])==p['total_seen']==4 and
        p['instances']==1 and p['service_calls']==6 and p['available'] is p['context_verified'] is p['retired'] is True and
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
    build=v['development_probe_build'];need(len(build['project_sources_sha256'])==17 and
        all(project_closure[name]==sha for name,sha in build['project_sources_sha256'].items()),'new_project17_source_binding')
    need({name:len(rows) for name,rows in build['objects'].items()}=={'coh-auth-db-development':17,'chromium_zlib':21}
        and all(row['machine']=='AMD64' and row['bytes']>0 for rows in build['objects'].values() for row in rows.values()),'reported_new_x64_object_closure')
    need(build['binary']['sha256']=='1978acc1b3de864b2e658857fbdef4e427b1b58d44f2a05d269905595ea2e317' and
        build['binary']['bytes']==3299840 and build['binary']['no_unadmitted_dll_imports'] is True and
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
    return {'schema':'coh-actual-development-db-account-controls-verification-v1','passed':True,
        'repository_commit':COMMIT,'repository_tree':TREE,'github_run_id':39094808506,'job_id':117578922139,
        'artifact_id':12124625207,'evidence':{k:{'bytes':n,'sha256':h} for k,(n,h) in PINS.items()},
        'source_gate_sha256':full,'source_gate_count':137,'runtime_source_map_count':128,'common_build_source_map_count':2,
        'current_worker_source128_equal':local,'historical_source_map_counts':{k:len(x) for k,x in historical_groups.items()},
        'actual_received_header_prefix':expected,'observation_scope':'same-copy header prefix only',
        'source_derived_inventory_default_and_owner_refusal_supported':True,
        'source_derived_prior14_8_completion_supported':True,'account_control_body_values_observed':False,
        'current_c99_source_input_count':36,
        'source_derived_refusal_whole_function_spans':spans,
        'first_unsupported_attributed':False,'body_acceptance_observed':False,
        'complete_player_list_verified':False,'normal_version_or_checksum_reference_admitted':False,
        'db_or_map_handoff_verified':False,'all_cleanup_and_source_gates_verified':True,
        'reported_probe_binary':build['binary'],'probe_binary_file_available_to_this_verifier':False,
        'project_and_zlib_object_counts':[17,21],'download_or_raw_logs_performed_by_verifier':False,
        'project_helpers_or_tests_or_runtime_executed_by_verifier':False}


if __name__=='__main__':print(json.dumps(verify(),indent=2,sort_keys=True))
