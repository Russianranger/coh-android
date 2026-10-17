"""Admit the exact nonshipping 1024-MiB host SQL prerequisite; no auth inheritance."""
import json
from pathlib import Path

import auth_readiness
import hosted_auth_stage as prior

HERE=Path(__file__).resolve().parent
RECEIPT_SHA='4c06409b977495d9db6dc42fcd1c0148005487fd3086c97a9fc1d45bf63a5e86'
DRIVER_SHA='319b6c3b0ab08dd92dc1e5ee6daf3def82503ebbc85944fc1c614cd7a1c7b729'
PHASES=('default_memory_before_schema','configured_memory_before_schema','after_original_schema','after_original_public_seed')


def admit_receipt(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>1024*1024 or prior.sha(path)!=RECEIPT_SHA:
        raise ValueError('candidate_1024_receipt_identity')
    value=json.loads(path.read_text())
    if (value.get('schema')!='coh-sql-readiness-transport-only-v1' or value.get('passed') is not True
            or value.get('experiment_completed') is not True or type(value.get('memory_limit_mb')) is not int or value['memory_limit_mb']!=1024
            or value.get('original_source_tree')!=prior.ORIGINAL_TREE or value.get('localdb_version')!='17.0.4025.3'
            or value.get('x86_odbc_driver',{}).get('sha256')!=DRIVER_SHA
            or any(value.get(k) is not True for k in ('owned_localdb_cleanup_complete','private_files_removed','source_inputs_unchanged'))
            or any(value.get(k) is not False for k in ('authserver_started','encrypted_account_login_verified','shipping_server_modified','service_guard_disabled','connectivity_qualified'))):
        raise ValueError('candidate_1024_receipt_scope')
    initial=value.get('owned_sql_initial',{});pid=initial.get('pid');generation=initial.get('started_utc_ticks')
    if type(pid) is not int or not 1<=pid<=0xffffffff or type(generation) is not int or generation<=0:
        raise ValueError('candidate_1024_sql_generation')
    phases=value.get('observations')
    if not isinstance(phases,list) or len(phases)!=4 or tuple(p.get('phase') for p in phases)!=PHASES:
        raise ValueError('candidate_1024_phases')
    for phase in phases:
        for key in ('process_before','process_after'):
            p=phase.get(key,{})
            if p.get('exists') is not True or p.get('pid')!=pid or p.get('started_utc_ticks')!=generation:
                raise ValueError('candidate_1024_phase_generation')
        log=phase.get('sql_errorlog',{})
        if (log.get('ready_marker') is not True or any(log.get(k) is not False for k in ('termination_marker','insufficient_memory_marker','content_exported'))
                or log.get('numeric_errors')!=[]):
            raise ValueError('candidate_1024_sql_errorlog')
        transports=phase.get('transports')
        if not isinstance(transports,list) or len(transports)!=4 or {(p.get('architecture_bits'),p.get('transport')) for p in transports}!={(a,t) for a in (32,64) for t in ('named_instance','owned_named_pipe')}:
            raise ValueError('candidate_1024_transport_matrix')
        for observation in transports:
            raw=observation.get('observation',{});bits=observation['architecture_bits']
            if type(bits) is not int or type(raw.get('pointer_bytes')) is not int or raw['pointer_bytes']!=bits//8:
                raise ValueError('candidate_1024_architecture')
            expected_database='master' if phase['phase'] in PHASES[:2] else 'cohauth'
            if observation.get('healthy') is not True or observation.get('database')!=expected_database:
                raise ValueError('candidate_1024_health')
            if auth_readiness.admit(dict(raw,pointer_bytes=4),pid)['healthy'] is not True:
                raise ValueError('candidate_1024_actual_odbc_health')
    required=('original-schema-private','public-seed-private-credential','public-seed-private-account','localdb-drop-owned-schema','localdb-stop-owned-instance','localdb-delete-owned-instance')
    for name in required:
        rows=[c for c in value.get('commands',[]) if c.get('name')==name]
        if len(rows)!=1 or type(rows[0].get('returncode')) is not int or rows[0]['returncode']!=0 or rows[0].get('console_output_suppressed') is not True:
            raise ValueError('candidate_1024_seed_or_cleanup')
    return {'sql_memory_limit_mb':1024,'readiness_run_id':38995104446,'readiness_artifact_id':12086284710,
            'receipt_sha256':RECEIPT_SHA,'healthy_transport_observations':16,'public_fixture_seed_qualified':True,
            'prior_authentication_inherited':False,'fresh_x86_readiness_still_required':True}


def select(memory_limit_mb):
    if type(memory_limit_mb) is not int or memory_limit_mb not in (256,1024):
        raise ValueError('candidate_sql_memory_profile')
    if memory_limit_mb==256:
        return {'sql_memory_limit_mb':256,'profile':'existing_default','prior_authentication_inherited':False}
    return admit_receipt(HERE.parent/'evidence/sql-readiness-1024-38995104446/receipt.json')
