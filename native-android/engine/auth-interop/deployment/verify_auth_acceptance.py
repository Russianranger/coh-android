#!/usr/bin/env python3
"""Replay strict source/binary/receipt admission for the completed auth-only run."""
import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

import auth_readiness
import hosted_auth_login as login
import hosted_candidate_login as service
import hosted_receive_candidate as candidate

SOURCE='28fe37cc2432db4adbfe047bd07a1e738d6aa754'
ARTIFACT=12087506300
ARCHIVE_SHA='bd04a2baaee03e3d736e3419686849d4e3551770a020c0e321fe49e4d1151d3e'
CANDIDATE_PATH='native-android/combined-client/evidence/20261017/emergency-recovery/hosted-234d9c7/auth.zip'


def admit_receipt(value):
    true_flags=('passed','candidate_started','account_normal_and_capped_sends_verified','encrypted_account_login_verified',
        'no_binary_rebuilt','owned_authserver_job_stop_complete','owned_authserver_listeners_absent','owned_authserver_cleanup_complete',
        'owned_firewall_cleanup_complete','owned_localdb_cleanup_complete','private_files_removed','source_inputs_unchanged')
    false_flags=('authenticated_db_map_handoff_verified','shipping_server_modified','db_checksum_policy_modified',
        'general_tcp_segmentation_accepted','receiver_segmentation_controlled','private_service_logs_exported','private_credential_files_exported','owned_sql_in_auth_job')
    if (value.get('schema')!='coh-hosted-candidate-auth-only-v1' or value.get('repository_commit')!=SOURCE
            or value.get('github_run_id')!='38996587760' or value.get('original_source_tree')!=login.prior.ORIGINAL_TREE
            or any(value.get(k) is not True for k in true_flags) or any(value.get(k) is not False for k in false_flags)
            or value.get('positive_modes_verified')!=['normal','capped']):
        raise ValueError('completed_auth_receipt_scope')
    if set(value.get('probe_results',{}))!={'normal','capped'}:raise ValueError('completed_auth_modes')
    for mode in ('normal','capped'):
        rows=value['probe_results'][mode]
        if set(rows)!=set(login.CASES):raise ValueError('completed_auth_case_matrix')
        for case in login.CASES:
            login.admit_probe_result(rows[case],case)
            observed=value.get('probe_numeric_observations',{}).get(mode,{}).get(case)
            expected={k:rows[case][k] for k in ('state','protocol','received_frames','sent_bytes','failure_command','failure_reason','system_error','elapsed_ms')}
            if observed!=expected:raise ValueError('completed_auth_numeric_projection')
    before=value.get('owned_sql_before_start',{});after=value.get('owned_sql_after_auth_stop',{})
    if before.get('exists') is not True or before!=after or type(before.get('pid')) is not int:
        raise ValueError('completed_auth_sql_generation')
    readiness=value.get('x86_readiness_before_start',{})
    if readiness.get('healthy') is not True or auth_readiness.admit(readiness.get('observation'),before['pid'])['healthy'] is not True:
        raise ValueError('completed_auth_fresh_readiness')
    jobs=value.get('owned_job_members_before_stop')
    if not isinstance(jobs,list) or len(jobs)!=1 or type(jobs[0]) is not int or jobs[0]==before['pid']:
        raise ValueError('completed_auth_owned_job')
    rows=value.get('commands',[])
    required={'archive-original-source','localdb-create','localdb-start','localdb-version','localdb-memory-bound',
              'localdb-pid','firewall-add','firewall-remove','localdb-drop-owned-schema','localdb-stop-owned-instance','localdb-delete-owned-instance'}
    if {r.get('name') for r in rows}!=required or len(rows)!=len(required) or any(type(r.get('returncode')) is not int or r['returncode']!=0 for r in rows):
        raise ValueError('completed_auth_command_or_cleanup_result')
    if (value['candidate_admission']['binary']['sha256']!=service.BINARY_SHA
            or value['candidate_admission']['receipt_sha256']!=service.RECEIPT_SHA
            or value['normal_probe_admission']['binary']['sha256']!=service.INTACT_BINARY_SHA
            or value['capped_probe_admission']['native_probe']['sha256']!='454814a2659944cf7958d10d89f2bdf49a7e5a778ad75d941077ef8d17d672ec'
            or value['sql_memory_profile']['sql_memory_limit_mb']!=1024):
        raise ValueError('completed_auth_binary_profile_identity')
    return value


def verify(root,archive):
    if archive.stat().st_size!=6854 or login.prior.sha(archive)!=ARCHIVE_SHA:
        raise ValueError('completed_auth_archive_identity')
    with zipfile.ZipFile(archive) as zip_file:
        infos=zip_file.infolist()
        if len(infos)>32 or len({i.filename for i in infos})!=len(infos) or sum(i.file_size for i in infos)>1024*1024 or zip_file.testzip() is not None:
            raise ValueError('completed_auth_archive_bound')
        value=admit_receipt(json.loads(zip_file.read('receipt.json')))
        files={i.filename:{'bytes':i.file_size,'sha256':hashlib.sha256(zip_file.read(i)).hexdigest()} for i in infos if not i.is_dir()}
    def blob(path):
        return subprocess.check_output(['git','-C',str(root),'show',SOURCE+':'+path],timeout=30)
    tree=subprocess.check_output(['git','-C',str(root),'rev-parse',SOURCE+'^{tree}'],timeout=30).decode().strip()
    if tree!=value['repository_tree']:raise ValueError('completed_auth_source_tree')
    inputs={}
    for group in ('capped_probe_admission','normal_probe_admission'):
        for name,expected in value[group]['source_files_sha256'].items():
            if hashlib.sha256(blob(name)).hexdigest()!=expected:raise ValueError('completed_auth_native_source_identity')
            inputs[name]=expected
    for name in ('hosted_candidate_login.py','hosted_auth_login.py','candidate_sql_memory.py','auth_readiness.py','hosted_receive_candidate.py','receive_candidate.py','auth_service_profile.py','password_fixture.py'):
        path='native-android/engine/auth-interop/deployment/'+name;inputs[path]=hashlib.sha256(blob(path)).hexdigest()
    with tempfile.TemporaryDirectory(prefix='coh-auth-acceptance-') as temporary:
        temp=Path(temporary);candidate_zip=temp/'candidate.zip';candidate_zip.write_bytes(blob(CANDIDATE_PATH))
        if login.prior.sha(candidate_zip)!=service.ARCHIVE_SHA:raise ValueError('completed_auth_build_archive')
        directory=temp/'candidate';directory.mkdir()
        with zipfile.ZipFile(candidate_zip) as zipped:zipped.extractall(directory)
        admitted=candidate.admit(directory,service.RECEIPT_SHA,service.BINARY_SHA)
    return {'schema':'coh-completed-candidate-auth-source-binder-v1','passed':True,'run_id':38996587760,'artifact_id':ARTIFACT,
        'archive_sha256':ARCHIVE_SHA,'source_commit':SOURCE,'source_tree':tree,'files':files,'source_sha256':inputs,
        'candidate_build_admission':admitted,'actual_normal_and_capped_cases':8,'actual_encrypted_authserver_login':True,
        'complete_owned_cleanup':True,'source_binary_receipt_admission_replayed':True,
        'scope':'Disposable corrected original AuthServer, exact prebuilt native probes,1024MiB LocalDB; actual encrypted login+empty shard list and six negative cases. No DB/Map/shard/Android/Thor acceptance.',
        'authenticated_db_map_handoff_verified':False,'general_tcp_segmentation_accepted':False,'shipping_server_modified':False,
        'new_service_execution':False,'binaries_rebuilt':False}


@dataclass(frozen=True)
class AuthenticatedHandoffPrerequisite:
    source_commit: str
    original_source_tree: str
    protocol: int
    runtime_receipt_sha256: str
    candidate_authserver_sha256: str
    normal_probe_sha256: str
    capped_probe_sha256: str
    source_pins: tuple
    qualified_account_case_count: int = 8
    owned_cleanup_qualified: bool = True
    fresh_authentication_required: bool = True
    historical_session_reusable: bool = False
    selected_character_dbid: object = None
    authenticated_db_map_handoff_verified: bool = False
    shipping_server_modified: bool = False


def authenticated_handoff_prerequisite(root, archive):
    """Immutable source-interoperability prerequisite, never a live login token.

    This disposable service/session is stopped. A future DB/Map driver must
    perform fresh encrypted authentication, retain its own session ownership,
    register/admit an actual shard and verify the selected DBID separately.
    """
    proof=verify(root,archive)
    return AuthenticatedHandoffPrerequisite(source_commit=proof['source_commit'],
        original_source_tree=login.prior.ORIGINAL_TREE,protocol=191021,
        runtime_receipt_sha256=proof['files']['receipt.json']['sha256'],
        candidate_authserver_sha256=service.BINARY_SHA,normal_probe_sha256=service.INTACT_BINARY_SHA,
        capped_probe_sha256='454814a2659944cf7958d10d89f2bdf49a7e5a778ad75d941077ef8d17d672ec',
        source_pins=tuple(sorted(proof['source_sha256'].items())))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();proof=verify(args.source_root.resolve(),args.archive.resolve())
    args.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'actual_encrypted_authserver_login':True,'new_service_execution':False}))
