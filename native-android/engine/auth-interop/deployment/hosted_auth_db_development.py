#!/usr/bin/env python3
"""New private real-Auth -> provisional development DB-list experiment.

Normal version/reference-checksum and character/Map authority remain blocked.
This driver is separate from the accepted selected-grant/default paths.
"""
import argparse
import ast
import copy
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import time

import db_received_prefix as received_prefix
import hosted_db_threadname_readiness as readiness
import hosted_selected_shard_play as selected

HERE=Path(__file__).resolve().parent
activation=readiness.activation
login=selected.login
PREFIX=readiness.candidate.PREFIX
ZLIB_EVIDENCE=PREFIX+'evidence/exact-zlib-cf333892-20261018/'
ZLIB_ADMIT_SHA='acb28d1cbf5f7eb8d1484face6ea3b18925679eda6c72344a1e134c2b00c934b'
ZLIB_CMAKE_SHA='646bf5e3c3b1787daeec7334b937ad5593e4f4a69a81ad59ffc5e686c326d00b'
SUSPENDED_HELPER_SHA='5c5306850d5c1abeab5f70682ce54f35240127f67a54f90393598421caef5a11'
SUSPENDED_PROOF_SHA='2a94e518de3e53a55123012a73c5b7eaed4482cf9fe4cad336cfae0b4c724267'
ACCOUNT_REVISION='02b54d43ffd2add91b32a5651aa31ebf6b170fdd'
ACCOUNT_BASE='native-android/engine/dbclient/qualification/account-controls-02b54d43f'
ACCOUNT_GZIP_SHA='d04dda6ac635ced869f0a86e4f4801ec732d12e69dc8ab10575056fa9c00513f'
ACCOUNT_RAW_SHA='8b4a16f704f53095d75c822f8f4635a707b8b965f2f1938888ff2d71c2449c1a'
ACCOUNT_BINDING_SHA='53767d18c4edd2b10964a6a2d4b8bff1ed40490789f6bb316d44c26cb3b18acb'
ACCOUNT_HISTORICAL_REVISION='b321a3dd883031072f26c63d4f2d9f4866b63d9d'
ACCOUNT_OLD_CORE={
    'native-android/engine/dbclient/coh_db_session.c':'ca8ee6130ebdccb3072f0ec0c279e4c044fac88f463144db7ef1caa7202f36b9',
    'native-android/engine/dbclient/coh_db_session.h':'9fe7adf5261a4c871e571b7a6e4df81513116dd978f4344e42d9c407234a80d4'}
ACCOUNT_CURRENT_CORE={
    'native-android/engine/dbclient/coh_db_session.c':'394a94e436d52963fbe2667b0b3cf977554d3b6ffe69c8c858da42ded697bc06',
    'native-android/engine/dbclient/coh_db_session.h':'d9993e341349cac614fe862481b1a3fb21e7239900ca1d3d6c8c1e8043b92c87'}

ACCOUNT_TOOL=PREFIX+'deployment/qualify_auth_db_development_owner.py'
ACCOUNT_TOOL_OLD_SHA='aa58020f335e60553e06941c7adb9a0b905c81c5ba84c5f0c3207b295e738637'
ACCOUNT_TOOL_NEW_SHA='3ac893e35650c89a59273bac096bc60053a1bfc1d3e036501170b102e7185a18'
ACCOUNT_TOOL_REVIEW='native-android/engine/dbclient/qualification/account-control-owned-link-lists.json'
ACCOUNT_TOOL_REVIEW_SHA='67578035a171f6f0fe0d5bf549f5658b2737d6f10c16a04090fa1b70cb43c50c'
ACCOUNT_DEPENDENCY='engine/dbclient/coh_db_account_controls.c'
LAUNCH_STATES=('NOT_STARTED','SPAWNING_SUSPENDED','SPAWN_REFUSED','CREATED_SUSPENDED',
    'ASSIGNING','ASSIGNMENT_REFUSED','RESUMING','RESUME_REFUSED','RESUMED')
RESUME_FLAGS={'passed','process_identity_verified','single_owned_thread_verified','thread_identity_verified',
    'generation_recheck_verified','resume_attempted','previous_suspend_count_one','resume_observed',
    'snapshots_closed','thread_handle_closed','cleanup_verified'}
RESUME_KEYS=RESUME_FLAGS|{'schema','snapshot_passes','snapshot_entries_examined','secondary_close_failures','failure'}
RESUME_FAILURES={'NONE','INPUT','PLATFORM','PROCESS_QUERY','PROCESS_IDENTITY','PROCESS_EXITED',
    'SNAPSHOT_CREATE','SNAPSHOT_ENUM','SNAPSHOT_ENTRY','SNAPSHOT_LIMIT','SINGLE_THREAD','THREAD_OPEN',
    'THREAD_QUERY','THREAD_IDENTITY','GENERATION_CHANGED','RESUME_API','RESUME_COUNT','HANDLE_CLOSE','API_FAILED'}
PLATFORM_DLLS={'kernel32.dll','user32.dll','advapi32.dll','bcrypt.dll','crypt32.dll','ws2_32.dll','gdi32.dll','secur32.dll','ncrypt.dll'}
PHASES=('IDLE','AUTH','DB','COMPLETE','FAILED','CANCELLED','CLOSED')
FAILURES=('NONE','INPUT','AUTH','SHARD','GRANT','DB_BEGIN','DB','LIST','TIMEOUT','CANCEL')
# Failure enum is indexed from the exact owner header (NONE plus nine causes).
STATUSES=('OK','INVALID','UNSUPPORTED','NOT_FOUND','LIMIT','CANCELLED','IO','STATE')
DB_PHASES=('IDLE','CONNECTING','WAIT_PLAYERS','QUEUED','CHARACTERS','WAIT_MAP','HANDOFF_READY',
    'DISCONNECTING','SUSPENDED','CLOSED','FAILED','CANCELLED','TIMED_OUT')
STAGES=('INPUT','TCP_INITIALIZE','TCP_LIMITS','UDP_INITIALIZE','ENTROPY','SELF_FILE_MD5',
    'OWNER_CREATE','OWNER_BEGIN','OWNER_SERVICE','OWNER_COMPLETE','PLATFORM_READY')
INTEGER_BOUNDS={'probe_stage':10,'phase':6,'failure':9,'status':7,'auth_phase':13,'db_phase':12,
    'auth_final_phase':13,'db_final_phase':12,'slots':64,'base_slots':0xffffffff,
    'bonus_slots':0xffffffff,'auth_frames':64,'db_login_requests':64,'db_player_lists':64,
    'db_queue_updates':64,'db_unsupported':64,'db_choices':64,'db_handoffs':64,'elapsed_ms':35000,
    'udp_created':4,'udp_closed':4,'udp_active':4,'udp_close_failures':16,'udp_cleanup_failures':16}
ONE_FLAGS={'begun','grant_consumed','selected_shard_verified','complete_matching_list',
    'all_slots_empty_unlocked','cleanup_cancel_close_used','controllers_destroyed',
    'development_skip_requested','udp_cleanup_complete'}
ZERO_FLAGS={'normal_version_admitted','checksum_reference_admitted','character_selected',
    'map_handoff_verified','current_world_verified'}
TRUE_FLAGS={'passed','checksum_measured_from_actual_probe','local_sensitive_buffers_wiped',
    'owner_cleanup_complete','socket_cleanup_complete','development_skip_source_inference_only'}
FALSE_FLAGS={'server_development_skip_observed','graceful_peer_disconnect_acknowledged',
    'real_server_provenance_verified_by_probe'}
NATIVE_KEYS=set(INTEGER_BOUNDS)|ONE_FLAGS|ZERO_FLAGS|TRUE_FLAGS|FALSE_FLAGS|{'schema'}


def private_json(raw):
    if type(raw) is not bytes or not 0<len(raw)<=8192:raise ValueError('development_native_json_extent')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('development_native_duplicate_key')
            result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('development_native_nonfinite')))


def native_shape(value,preflight=False):
    expected='coh-auth-db-development-'+('platform-preflight' if preflight else 'list-probe')+'-v1'
    if (type(preflight) is not bool or type(value) is not dict or set(value)!=NATIVE_KEYS or value['schema']!=expected
            or any(type(value[k]) is not int or not 0<=value[k]<=bound for k,bound in INTEGER_BOUNDS.items())
            or any(type(value[k]) is not int or value[k] not in (0,1) for k in ONE_FLAGS|ZERO_FLAGS)
            or any(value[k]!=0 for k in ZERO_FLAGS)
            or any(type(value[k]) is not bool for k in TRUE_FLAGS|FALSE_FLAGS)
            or any(value[k] is not False for k in FALSE_FLAGS)
            or value['development_skip_source_inference_only'] is not True):
        raise ValueError('development_native_fixed_scope')
    return value


def admit_probe(value,preflight=False):
    native_shape(value,preflight)
    if any(value[k] is not True for k in TRUE_FLAGS):raise ValueError('development_native_cleanup_or_policy')
    if preflight:
        nonzero={'probe_stage':10,'udp_cleanup_complete':1}
        # Elapsed time is a measurement, not an owner/socket count.
        if any(value[k]!=nonzero.get(k,0) for k in (set(INTEGER_BOUNDS)|ONE_FLAGS)-{'elapsed_ms'}):
            raise ValueError('development_platform_preflight_scope')
        return value
    expected={'probe_stage':9,'phase':3,'failure':0,'status':0,'auth_phase':7,'db_phase':4,
        'auth_final_phase':8,'db_final_phase':11,'auth_frames':4,'db_login_requests':1,
        'db_player_lists':1,'db_queue_updates':0,'db_unsupported':0,'db_choices':0,
        'db_handoffs':0,'udp_created':1,'udp_closed':1,'udp_active':0,
        'udp_close_failures':0,'udp_cleanup_failures':0}
    if (any(value[k]!=v for k,v in expected.items()) or any(value[k]!=1 for k in ONE_FLAGS)
            or not 0<value['base_slots']<=value['slots']<=64 or value['bonus_slots']>value['slots']):
        raise ValueError('development_native_complete_list_scope')
    return value


def observation(child,output,preflight=False,*,received=False):
    result={'schema':'coh-auth-db-development-fixed-observation-v1','child_state':'NOT_STARTED',
        'json_state':'UNAVAILABLE','stdout_bytes_bounded':0,'stage':'UNAVAILABLE','phase':'UNAVAILABLE',
        'failure':'UNAVAILABLE','status':'UNAVAILABLE','auth_phase':'UNAVAILABLE','db_phase':'UNAVAILABLE',
        'native_passed':False,'db_request_state':'UNAVAILABLE','complete_matching_list':False,
        'local_sensitive_buffers_wiped':False,'socket_cleanup_complete':False,
        'raw_private_output_exported':False,'owned_child_cleanup_complete':False,
        'owned_child_cleanup_outcome':'NOT_COMPLETED'}
    counters=('auth_frames','db_login_requests','db_player_lists','db_queue_updates','db_unsupported',
        'db_choices','db_handoffs','udp_created','udp_closed','udp_active','udp_close_failures','udp_cleanup_failures')
    result.update({k:0 for k in counters})
    if child is None:return result
    try:
        code=child.poll();result['child_state']=('RUNNING' if code is None else 'EXIT_ZERO' if type(code) is int and code==0
            else 'EXIT_ONE' if type(code) is int and code==1 else 'OTHER_EXIT')
        size=os.fstat(output.fileno()).st_size;result['stdout_bytes_bounded']=min(size,8193)
        if size>8192:result['json_state']='OVERSIZE';return result
        if code is None:return result
        result['json_state']='REFUSED'
        if type(code) is not int or code not in (0,1):return result
        output.seek(0);value=private_json(output.read(8193))
        if received:
            value,prefix=received_prefix.native(value,preflight)
        value=native_shape(value,preflight)
        if value['passed'] is not (code==0):return result
        result.update(json_state='VALID',stage=STAGES[value['probe_stage']],phase=PHASES[value['phase']],
            failure=FAILURES[value['failure']],status=STATUSES[value['status']],
            auth_phase=selected.PROBE_STATES[value['auth_phase']],db_phase=DB_PHASES[value['db_phase']],
            native_passed=value['passed'],db_request_state='QUEUED' if value['db_login_requests'] else 'NOT_QUEUED',
            complete_matching_list=value['complete_matching_list']==1,
            local_sensitive_buffers_wiped=value['local_sensitive_buffers_wiped'],socket_cleanup_complete=value['socket_cleanup_complete'])
        result.update({k:value[k] for k in counters})
        if received:
            result['native_producer_schema']=value['schema'][:-1]+'2'
            result['db_received_prefix']=prefix
    except Exception:pass
    return result


def _committed_file(root,name,expected=None):
    path=root/name
    try:raw=subprocess.check_output(['git','-C',str(root),'show','HEAD:'+name],stderr=subprocess.DEVNULL,timeout=30)
    except subprocess.SubprocessError:raise ValueError('development_input_not_owned_by_head') from None
    if (path.resolve()!=path or path.is_symlink() or not path.is_file() or len(raw)>2*1024*1024 or path.read_bytes()!=raw
            or (expected is not None and hashlib.sha256(raw).hexdigest()!=expected)):
        raise ValueError('development_input_not_owned_by_head')
    return raw


def deployment_import_inputs(root,starts):
    """Admit the finite local Python source graph without executing helpers."""
    base=PREFIX+'deployment/'
    names=subprocess.check_output(['git','-C',str(root),'ls-tree','-r','--name-only','HEAD','--',base],
        timeout=30,text=True).splitlines()
    owned={Path(name).stem:name for name in names if Path(name).parent.as_posix()==base.rstrip('/') and name.endswith('.py')}
    pending=list(starts);pins={};total=0
    while pending:
        name=pending.pop()
        if name in pins:continue
        raw=_committed_file(root,name);total+=len(raw)
        if len(pins)>=128 or total>16*1024*1024:raise ValueError('development_local_import_graph_bound')
        pins[name]=hashlib.sha256(raw).hexdigest()
        module_name=Path(name).stem;loaded=sys.modules.get(module_name)
        if loaded is not None and Path(getattr(loaded,'__file__','')).resolve()!=root/name:
            raise ValueError('development_executed_dependency_identity')
        for node in ast.walk(ast.parse(raw)):
            imported=([item.name for item in node.names] if isinstance(node,ast.Import)
                else [node.module] if isinstance(node,ast.ImportFrom) and node.level==0 else [])
            for module in imported:
                if module and re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',module):
                    candidate=base+module+'.py'
                    if module in owned or (root/candidate).exists():pending.append(owned.get(module,candidate))
    return pins


def account_controls_inputs(root):
    """Current typed-parser admission, separately from immutable old proofs."""
    compressed=_committed_file(root,ACCOUNT_BASE+'.json.gz',ACCOUNT_GZIP_SHA)
    binding_raw=_committed_file(root,ACCOUNT_BASE+'-binding.json',ACCOUNT_BINDING_SHA)
    if len(compressed)!=5180:raise ValueError('development_account_source_proof_extent')
    raw=gzip.decompress(compressed)
    if len(raw)!=25073 or hashlib.sha256(raw).hexdigest()!=ACCOUNT_RAW_SHA:
        raise ValueError('development_account_source_proof_identity')
    proof=json.loads(raw);binding=json.loads(binding_raw)
    if (proof.get('schema')!='coh-db-account-controls-focused-tests-v1' or proof.get('passed') is not True
            or proof.get('source_revision')!=ACCOUNT_REVISION or proof.get('all_inputs_equal_committed_HEAD') is not True
            or binding.get('schema')!='coh-db-account-controls-source-proof-binding-v1' or binding.get('passed') is not True
            or binding.get('qualified_source_revision')!=ACCOUNT_REVISION or binding.get('proof')!=ACCOUNT_BASE+'.json.gz'
            or binding.get('proof_sha256')!=ACCOUNT_RAW_SHA or binding.get('gzip_sha256')!=ACCOUNT_GZIP_SHA
            or binding.get('source_sha256')!=proof.get('source_sha256')
            or binding.get('previous_ordinary_sha256')!=ACCOUNT_OLD_CORE):
        raise ValueError('development_account_source_proof_scope')
    for name in ('historical_suites_executed','real_auth_or_db','sockets_executed','actual_witness_body_inferred',
            'source_generation_admitted','world_authority','global_aggregate_budget_admitted'):
        if proof.get(name) is not False:raise ValueError('development_account_source_proof_authority')
    for name in ('owner_implementation_changed','strict_owner_success_predicate_changed','historical_suites_replayed',
            'actual_header_witness_body_inferred','current_generation_or_world_authority'):
        if binding.get(name) is not False:raise ValueError('development_account_source_binding_authority')
    if (type(proof.get('source_sha256')) is not dict or len(proof['source_sha256'])!=36
            or any(proof['source_sha256'].get(name)!=sha for name,sha in ACCOUNT_CURRENT_CORE.items())
            or set(proof.get('modes',{}))!={'release','asan','ubsan'}
            or any(row.get('passed') is not True or row.get('checks')!=8822 or row.get('parser_cases')!=7226
                or row.get('session_transactions')!=52 for row in proof['modes'].values())):
        raise ValueError('development_account_source_qualification')
    pins={ACCOUNT_BASE+'.json.gz':ACCOUNT_GZIP_SHA,ACCOUNT_BASE+'-binding.json':ACCOUNT_BINDING_SHA}
    for name,sha in proof['source_sha256'].items():
        pins[name]=hashlib.sha256(_committed_file(root,name,sha)).hexdigest()
    return pins


def dependency_only_ast(old,current):
    """Require exactly the one parser dependency literal and no other AST edit."""
    class RemoveDependency(ast.NodeTransformer):
        count=0
        def visit_Tuple(self,node):
            self.generic_visit(node);kept=[]
            for item in node.elts:
                if isinstance(item,ast.Constant) and item.value==ACCOUNT_DEPENDENCY:self.count+=1
                else:kept.append(item)
            node.elts=kept;return node
    try:
        previous=ast.parse(old);current_tree=ast.parse(current);remove=RemoveDependency()
        changed=remove.visit(current_tree)
        if remove.count!=1 or ast.dump(previous,include_attributes=False)!=ast.dump(changed,include_attributes=False):
            raise ValueError('development_qualifier_dependency_ast_refused')
    except SyntaxError:raise ValueError('development_qualifier_dependency_ast_refused') from None


def account_controls_tool_inputs(root):
    review=json.loads(_committed_file(root,ACCOUNT_TOOL_REVIEW,ACCOUNT_TOOL_REVIEW_SHA))
    row=review.get('files',{}).get(ACCOUNT_TOOL,{})
    if (review.get('schema')!='coh-account-control-owned-link-list-review-v1' or review.get('passed') is not True
            or review.get('source_only') is not True or review.get('qualifier_or_tests_executed') is not False
            or review.get('new_parser_dependency')!=ACCOUNT_DEPENDENCY
            or row!={'before_sha256':ACCOUNT_TOOL_OLD_SHA,'after_sha256':ACCOUNT_TOOL_NEW_SHA,
                'ast_equals_previous_after_removing_only_new_dependency_literal':True}):
        raise ValueError('development_qualifier_dependency_review_scope')
    current=_committed_file(root,ACCOUNT_TOOL,ACCOUNT_TOOL_NEW_SHA)
    try:old=subprocess.check_output(['git','-C',str(root),'show',ACCOUNT_HISTORICAL_REVISION+':'+ACCOUNT_TOOL],
        stderr=subprocess.DEVNULL,timeout=30)
    except subprocess.SubprocessError:raise ValueError('development_historical_qualifier_unavailable') from None
    if len(old)>2*1024*1024 or hashlib.sha256(old).hexdigest()!=ACCOUNT_TOOL_OLD_SHA:
        raise ValueError('development_historical_qualifier_identity')
    dependency_only_ast(old,current)
    return {ACCOUNT_TOOL_REVIEW:ACCOUNT_TOOL_REVIEW_SHA,ACCOUNT_TOOL:ACCOUNT_TOOL_NEW_SHA}


def qualified_prior_input(root,path,expected,account):
    """Two compiled core inputs and one separate qualifier dependency transition."""
    if path==ACCOUNT_TOOL:
        if expected!=ACCOUNT_TOOL_OLD_SHA or account.get(path)!=ACCOUNT_TOOL_NEW_SHA:
            raise ValueError('development_historical_qualifier_transition_refused')
        account_controls_tool_inputs(root)
        return _committed_file(root,path,ACCOUNT_TOOL_NEW_SHA)
    if path not in ACCOUNT_OLD_CORE:return _committed_file(root,path,expected)
    if expected!=ACCOUNT_OLD_CORE[path] or account.get(path)!=ACCOUNT_CURRENT_CORE[path]:
        raise ValueError('development_historical_core_transition_refused')
    try:
        old=subprocess.check_output(['git','-C',str(root),'show',ACCOUNT_HISTORICAL_REVISION+':'+path],
            stderr=subprocess.DEVNULL,timeout=30)
    except subprocess.SubprocessError:raise ValueError('development_historical_core_unavailable') from None
    if len(old)>2*1024*1024 or hashlib.sha256(old).hexdigest()!=expected:
        raise ValueError('development_historical_core_identity')
    return _committed_file(root,path,ACCOUNT_CURRENT_CORE[path])


def account_controls_summary():
    return {'schema':'coh-development-account-controls-source-composition-v1',
        'source_proof':ACCOUNT_BASE+'.json.gz','source_proof_sha256':ACCOUNT_GZIP_SHA,
        'source_binding':ACCOUNT_BASE+'-binding.json','source_binding_sha256':ACCOUNT_BINDING_SHA,
        'historical_qualifier_dependency_transition':{'path':ACCOUNT_TOOL,'before_sha256':ACCOUNT_TOOL_OLD_SHA,
            'after_sha256':ACCOUNT_TOOL_NEW_SHA,'review':ACCOUNT_TOOL_REVIEW,'review_sha256':ACCOUNT_TOOL_REVIEW_SHA,
            'only_parser_dependency_literal_added':True},
        'historical_core_source_revision':ACCOUNT_HISTORICAL_REVISION,
        'historical_core_sha256':ACCOUNT_OLD_CORE,'current_core_sha256':ACCOUNT_CURRENT_CORE,
        'old_proofs_reused_for_unchanged_inputs_only':True,'new_parser_source_qualified':True,
        'old_qualifiers_reexecuted':False,'actual_account_control_bodies_inferred':False,
        'unknown_command_policy_relaxed':False,'owner_success_predicate_changed':False}


def committed_inputs(root,commit):
    if (Path(__file__).resolve()!=root/(PREFIX+'deployment/hosted_auth_db_development.py')
            or subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()!=commit):
        raise ValueError('development_executed_source_identity')
    result=readiness.committed_runtime_inputs(root,commit)
    account=account_controls_inputs(root)
    account.update(account_controls_tool_inputs(root))
    proofs=[
        ('native-android/engine/auth-interop/evidence/auth-db-development-owner-20261018/host-1642051b3.json.gz',
         'b3c0b382202be509748fe5a70b289b35a02e5069f136e779f16358df5ddfe066',True),
        ('native-android/engine/auth-interop/qualification/db-udp-windows-source-20261018/host.json',
         'dc3018ebc0e853ddfd8ffc2071c6d30b05f115edbfde01d3b8d9e736a0c8e419',False),
        ('native-android/engine/auth-interop/qualification/db-development-probe-source-20261018/host.json',
         '6325c41dd124f5c97ba91897ab33117ed347aeb1c8545f25e80f04336ef25223',False)]
    for name,digest,zipped in proofs:
        raw=_committed_file(root,name,digest);value=json.loads(gzip.decompress(raw) if zipped else raw)
        if value.get('passed') is not True:raise ValueError('development_prior_source_proof_scope')
        result[name]=digest
        if zipped:pins=value['source_sha256']
        else:
            groups=(('source_files','unchanged_ordinary_udp_private_wrapper_host_compile_project_closure')
                if 'source_files' in value else ('new_source_inputs','synthetic_probe_host_compile_project_closure'))
            pins={path:row['sha256'] for group in groups for path,row in value[group].items()}
        for path,expected in pins.items():
            raw=qualified_prior_input(root,path,expected,account);actual=hashlib.sha256(raw).hexdigest()
            if path in result and result[path]!=actual:raise ValueError('development_source_pin_conflict')
            result[path]=actual
    for name,sha in account.items():
        if name in result and result[name]!=sha:raise ValueError('development_account_source_pin_conflict')
        result[name]=sha
    own=['hosted_auth_db_development.py','hosted_auth_db_development_stage.py','test_auth_db_development_driver.py',
        'AUTH-DB-DEVELOPMENT-DRIVER.md','db_received_prefix.py','test_db_received_prefix.py',
        'DB-RECEIVED-PREFIX.md','test_account_controls_tool_admission.py','test_account_controls_admission.py','ACCOUNT-CONTROLS-ADMISSION.md','windows/db_received_prefix.h','windows/wrapped_db_received_prefix.c',
        'windows/db_development_received_probe.c','windows/test_db_received_prefix.c','windows_registry_lease.py','test_windows_registry_lease.py',
        'hosted_selected_shard_play.py','password_fixture.py','auth_service_profile.py']
    for name in own:
        path=PREFIX+'deployment/'+name;raw=_committed_file(root,path)
        digest=hashlib.sha256(raw).hexdigest()
        if path in result and result[path]!=digest:raise ValueError('development_source_pin_conflict')
        result[path]=digest
    for name,digest in (('auth_service_profile.py','6261d5e328df028dfc1332d5e00e94d5d23710dc35587db01e0b3f46f9c033c4'),
            ('password_fixture.py','0518446903dbcb16f78399871139db871a535f3e85995373a163502401605cdd')):
        if result[PREFIX+'deployment/'+name]!=digest:raise ValueError('development_qualified_fixture_or_profile_changed')
    if result[PREFIX+'deployment/windows_registry_lease.py']!='4f7bcbdb79dc3dc8cbe0d4744810bea0b18a56655b26a89b9e6bb32701f5636b':
        raise ValueError('development_qualified_registry_module_changed')
    for name in ('admit.py','admission.json','source.tar.gz','commit.json','tree.json','Zlib.cmake','chromium-zlib-cmake.patch'):
        path=ZLIB_EVIDENCE+name;result[path]=hashlib.sha256(_committed_file(root,path)).hexdigest()
    suspended=PREFIX+'deployment/qualification/windows-suspended-thread-20261018/'
    proof=json.loads(_committed_file(root,suspended+'mock.json',SUSPENDED_PROOF_SHA))
    if (proof.get('passed') is not True or proof.get('actual_windows_or_native_api_executed') is not False
            or proof.get('driver_integration_qualified') is not False):
        raise ValueError('development_suspended_helper_source_scope')
    result[suspended+'mock.json']=SUSPENDED_PROOF_SHA
    result[suspended+'HANDOFF.md']=hashlib.sha256(_committed_file(root,suspended+'HANDOFF.md')).hexdigest()
    for name,digest in proof['source_sha256'].items():
        result[name]=hashlib.sha256(_committed_file(root,name,digest)).hexdigest()
    if result.get(PREFIX+'deployment/windows_suspended_thread.py')!=SUSPENDED_HELPER_SHA:
        raise ValueError('development_suspended_helper_source_identity')
    for name,digest in deployment_import_inputs(root,[PREFIX+'deployment/hosted_auth_db_development.py',
            PREFIX+'deployment/windows_suspended_thread.py']).items():
        if name in result and result[name]!=digest:raise ValueError('development_local_import_pin_conflict')
        result[name]=digest
    for name,digest in received_prefix.SOURCE_PINS.items():
        if name in result and result[name]!=digest:raise ValueError('development_received_source_pin_conflict')
        result[name]=hashlib.sha256(_committed_file(root,name,digest)).hexdigest()
    return result


def _registry_module(root):
    name=PREFIX+'deployment/windows_registry_lease.py'
    code=_committed_file(root,name,'4f7bcbdb79dc3dc8cbe0d4744810bea0b18a56655b26a89b9e6bb32701f5636b')
    spec=importlib.util.spec_from_file_location('coh_development_registry_lease',root/name)
    module=importlib.util.module_from_spec(spec)
    # Dataclass type metadata resolves through this private canonical module.
    sys.modules[spec.name]=module
    exec(compile(code,str(root/name),'exec'),module.__dict__)
    return module


def _resume_primary(process):
    root=HERE.parents[3];name=PREFIX+'deployment/windows_suspended_thread.py'
    if type(SUSPENDED_HELPER_SHA) is not str or not re.fullmatch('[a-f0-9]{64}',SUSPENDED_HELPER_SHA):
        raise ValueError('development_suspended_helper_unqualified')
    code=_committed_file(root,name,SUSPENDED_HELPER_SHA)
    spec=importlib.util.spec_from_file_location('coh_development_suspended_thread',root/name)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
    exec(compile(code,str(root/name),'exec'),module.__dict__)
    return module.resume_primary(process)


def admit_resume(value):
    if (type(value) is not dict or set(value)!=RESUME_KEYS
            or value['schema']!='coh-owned-suspended-primary-thread-v1'
            or any(value[key] is not True for key in RESUME_FLAGS)
            or type(value['snapshot_passes']) is not int or value['snapshot_passes']!=2
            or type(value['snapshot_entries_examined']) is not int or not 2<=value['snapshot_entries_examined']<=131072
            or type(value['secondary_close_failures']) is not int or value['secondary_close_failures']!=0
            or value['failure']!='NONE'):
        raise ValueError('development_primary_resume_refused')
    return value


def resume_projection(value):
    result={name:False for name in RESUME_FLAGS}
    result.update(schema='coh-owned-suspended-primary-thread-v1',snapshot_passes=0,
        snapshot_entries_examined=0,secondary_close_failures=0,failure='UNAVAILABLE')
    if value is None or value=={}:return result
    if (type(value) is not dict or set(value)!=RESUME_KEYS
            or value['schema']!=result['schema'] or any(type(value[name]) is not bool for name in RESUME_FLAGS)
            or any(type(value[name]) is not int or not 0<=value[name]<=bound for name,bound in (
                ('snapshot_passes',2),('snapshot_entries_examined',131072),('secondary_close_failures',65535)))
            or type(value['failure']) is not str or value['failure'] not in RESUME_FAILURES):
        result['failure']='PROJECTION_REFUSED';return result
    return dict(value)


def recover_zlib(root,destination):
    """Recover only the already admitted source; apply existing exact patch."""
    code=_committed_file(root,ZLIB_EVIDENCE+'admit.py',ZLIB_ADMIT_SHA)
    spec=importlib.util.spec_from_file_location('coh_development_exact_zlib',root/ZLIB_EVIDENCE/'admit.py')
    module=importlib.util.module_from_spec(spec)
    exec(compile(code,str(root/ZLIB_EVIDENCE/'admit.py'),'exec'),module.__dict__)
    admission=module.admit()
    if destination.exists() or destination.is_symlink():raise ValueError('development_new_zlib_directory_required')
    destination.mkdir()
    manifest=module.decode(module.exact(root/ZLIB_EVIDENCE/'admission.json',*module.PINS['admission.json']))
    archive_raw=module.exact(root/ZLIB_EVIDENCE/'source.tar.gz',*module.PINS['source.tar.gz'])
    with tarfile.open(fileobj=io.BytesIO(archive_raw),mode='r:gz') as archive:
        for member in archive:
            if member.isdir():continue
            if member.name not in manifest['files']:raise ValueError('development_zlib_member_not_admitted')
            path=destination/member.name;path.parent.mkdir(parents=True,exist_ok=True)
            with archive.extractfile(member) as source,path.open('xb') as target:shutil.copyfileobj(source,target,1024*1024)
            path.chmod(0o755 if manifest['files'][member.name]['git_mode']=='100755' else 0o644)
    # The archive's Git mode bits were independently admitted above. Windows
    # does not represent POSIX executable modes in stat(); byte/inventory
    # admission must not substitute its physical mode for that Git evidence.
    for name,row in manifest['files'].items():
        path=destination/name
        if path.is_symlink() or path.stat().st_size!=row['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError('development_zlib_original_copy_identity')
    if {p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()}!=set(manifest['files']):
        raise ValueError('development_zlib_original_copy_inventory')
    # This existing patch adds only the CMake recipe. Recover its exact content,
    # rather than duplicate or alter any zlib algorithm or compiler policy.
    patch=module.exact(root/ZLIB_EVIDENCE/'chromium-zlib-cmake.patch',*module.PINS['chromium-zlib-cmake.patch'])
    lines=patch.splitlines(keepends=True);derived=b''.join(line[1:] for line in lines if line.startswith(b'+') and not line.startswith(b'+++'))
    if len(derived)!=2133 or hashlib.sha256(derived).hexdigest()!=ZLIB_CMAKE_SHA:
        raise ValueError('development_existing_zlib_patch_body')
    (destination/'CMakeLists.txt').write_bytes(derived)
    for name,row in manifest['files'].items():
        path=destination/name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError('development_zlib_source_changed')
    if {p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()}!=set(manifest['files'])|{'CMakeLists.txt'}:
        raise ValueError('development_zlib_patched_inventory')
    if _committed_file(root,ZLIB_EVIDENCE+'admit.py',ZLIB_ADMIT_SHA)!=code:raise ValueError('development_zlib_admitter_changed')
    module.admit()
    return dict(source_admission=admission,existing_patch_sha256=hashlib.sha256(patch).hexdigest(),
        existing_patch_applied_to_private_copy=True,original_111_files_unchanged=True,
        derived_cmake_sha256=ZLIB_CMAKE_SHA,patched_source_files=112,compiler_executed=False)


def prepare_project(root,project,crypto,zlib):
    project.mkdir();native=root/'native-android';windows=HERE/'windows'
    sources=[windows/p for p in ('db_development_received_probe.c','auth_db_development_owner.c','winsock_compat.c',
        'wrapped_login.c','db_udp_winsock.c','wrapped_db_udp.c','wrapped_db_received_prefix.c')]
    sources += [native/p for p in ('engine/dbclient/coh_dbclient.c','engine/dbclient/coh_db_account_controls.c',
        'engine/auth/coh_auth.c','engine/auth/coh_auth_openssl.c','engine/session/coh_session_crypto.c',
        'engine/network/coh_net.c','engine/network/coh_net_frame.c','engine/network/coh_net_zip.c',
        'protocol/coh_protocol.c','src/coh_blowfish.c')]
    def quote(path):
        if any(c in str(path) for c in ('"','\n','\r',';','$','\0')):raise ValueError('development_project_path')
        return '"'+path.as_posix()+'"'
    text=('cmake_minimum_required(VERSION 3.24)\nproject(CohAuthDbDevelopment C)\n'
        'set(CMAKE_C_STANDARD 11)\nset(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreaded)\n'
        'if(NOT WIN32 OR NOT MSVC OR NOT CMAKE_SIZEOF_VOID_P EQUAL 8)\nmessage(FATAL_ERROR "New x64 MSVC probe only")\nendif()\n'
        'add_subdirectory('+quote(zlib)+' zlib-owned)\nadd_executable(coh-auth-db-development\n'
        +'\n'.join(quote(path) for path in sources)+')\n'
        'target_compile_definitions(coh-auth-db-development PRIVATE _CRT_SECURE_NO_WARNINGS WIN32_LEAN_AND_MEAN _WIN32_WINNT=0x0601 WINVER=0x0601)\n'
        'target_include_directories(coh-auth-db-development PRIVATE '
        +' '.join(quote(p) for p in (windows/'compat',crypto/'include',native/'include'))+')\n'
        'target_link_libraries(coh-auth-db-development PRIVATE ZLIB::ZLIB '+quote(crypto/'libcrypto.lib')
        +' ws2_32 gdi32 crypt32 bcrypt advapi32 user32)\n')
    (project/'CMakeLists.txt').write_text(text,encoding='utf-8')
    return sources


def verify_zlib(root,directory):
    code=_committed_file(root,ZLIB_EVIDENCE+'admit.py',ZLIB_ADMIT_SHA)
    spec=importlib.util.spec_from_file_location('coh_development_verify_zlib',root/ZLIB_EVIDENCE/'admit.py')
    module=importlib.util.module_from_spec(spec)
    exec(compile(code,str(root/ZLIB_EVIDENCE/'admit.py'),'exec'),module.__dict__)
    source=module.admit()
    manifest=module.decode(module.exact(root/ZLIB_EVIDENCE/'admission.json',*module.PINS['admission.json']))
    if directory.is_symlink() or not directory.is_dir():raise ValueError('development_zlib_private_directory')
    for name,row in manifest['files'].items():
        path=directory/name
        if (path.is_symlink() or not path.is_file() or path.stat().st_size!=row['bytes']
                or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']):
            raise ValueError('development_zlib_private_identity')
    cmake=directory/'CMakeLists.txt'
    if (cmake.is_symlink() or not cmake.is_file() or cmake.stat().st_size!=2133
            or hashlib.sha256(cmake.read_bytes()).hexdigest()!=ZLIB_CMAKE_SHA
            or any(p.is_symlink() for p in directory.rglob('*'))
            or {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
                !=set(manifest['files'])|{'CMakeLists.txt'}):
        raise ValueError('development_zlib_private_inventory')
    return {'original_tree':source['tree'],'original_files':111,'private_files':112,
        'existing_cmake_sha256':ZLIB_CMAKE_SHA,'physical_posix_modes_claimed_on_windows':False,
        'original_git_modes_admitted_from_archive':True}


class DevelopmentJob(login.OwnedJob):
    """New-scope completion proof, while retaining the assigned job handle."""
    def __init__(self):
        self.empty_before_close=False;self.assignment_attempted=False
        self._attempted_process=None;self._assigned_process=None;self.pending_empty_before_close=False
        self.launch_attempted=False;self._launched_process=None;self.launch_state='NOT_STARTED';self.resume_metadata={}
        super().__init__()

    def popen(self,*args,**kwargs):
        if self.launch_attempted or self.assignment_attempted or not self.handle or 'creationflags' in kwargs:
            raise ValueError('development_suspended_launch_consumed_or_overridden')
        self.launch_attempted=True;self.launch_state='SPAWNING_SUSPENDED'
        try:self._launched_process=subprocess.Popen(*args,**kwargs,creationflags=0x00000004)
        except BaseException:self.launch_state='SPAWN_REFUSED';raise
        self.launch_state='CREATED_SUSPENDED'
        return self._launched_process

    def assign(self,process):
        if (self.assignment_attempted or not self.handle or process is not self._launched_process
                or self.launch_state!='CREATED_SUSPENDED'):
            raise ValueError('development_job_assignment_consumed_or_not_owned_suspended')
        self.assignment_attempted=True;self._attempted_process=process
        self.launch_state='ASSIGNING'
        try:super().assign(process)
        except BaseException:self.launch_state='ASSIGNMENT_REFUSED';raise
        self._assigned_process=process
        self.launch_state='RESUMING'
        try:
            value=_resume_primary(process);self.resume_metadata=resume_projection(value)
            admit_resume(value)
        except BaseException:self.launch_state='RESUME_REFUSED';raise
        self.launch_state='RESUMED'

    @property
    def assignment_verified(self):return self._assigned_process is not None

    @property
    def scope_closed_verified(self):
        return (self.handle is None and self.empty_before_close is True
            and (self.assignment_verified or self.pending_empty_before_close is True))

    def stop(self,process):
        # TerminateJobObject alone is asynchronous.  Query the retained job,
        # including all descendants, until its exact member inventory is empty.
        primary=None;terminated=False;root_clean=False;closed=False
        direct_owned=self._launched_process is process
        assigned=direct_owned and self._assigned_process is process
        try:
            terminated=bool(self.kernel.TerminateJobObject(self.handle,0))
            deadline=time.monotonic()+15
            while True:
                if self.process_ids()==[]:
                    self.empty_before_close=True;break
                if time.monotonic()>=deadline:break
                time.sleep(.05)
        except BaseException as error:primary=error
        finally:
            # A refused assignment leaves a suspended direct child outside the
            # job. Its independent kill/wait must run even if job APIs fail.
            if direct_owned:
                if not assigned or not terminated:
                    try:process.kill()
                    except BaseException as error:
                        if primary is None:primary=error
                try:
                    try:process.wait(timeout=5)
                    except subprocess.TimeoutExpired as error:
                        if primary is None:primary=error
                        process.kill();process.wait(timeout=5)
                    root_clean=process.poll() is not None
                except BaseException as error:
                    if primary is None:primary=error
            try:
                if self.handle:
                    closed=bool(self.kernel.CloseHandle(self.handle))
                    if closed:self.handle=None
            except BaseException as error:
                if primary is None:primary=error
        if primary is not None:raise primary
        return assigned and terminated and self.empty_before_close and root_clean and closed

    def close_unassigned(self):
        """A fresh pending job has no child, but still observe its inventory."""
        primary=None;closed=False
        try:
            if self.assignment_attempted or self._launched_process is not None:
                raise ValueError('development_pending_job_assignment_attempted')
            self.empty_before_close=self.process_ids()==[]
            self.pending_empty_before_close=self.empty_before_close
        except BaseException as error:primary=error;raise
        finally:
            try:
                closed=bool(self.kernel.CloseHandle(self.handle))
                if closed:self.handle=None
            except BaseException:
                if primary is None:raise
        return self.empty_before_close and closed


def job_projection(job):
    state=getattr(job,'launch_state',None)
    return {'launch_state':state if type(state) is str and state in LAUNCH_STATES else 'UNAVAILABLE',
        'assignment_verified':getattr(job,'assignment_verified',None) is True,
        'resume_verified':state=='RESUMED',
        'empty_before_close':getattr(job,'empty_before_close',None) is True,
        'scope_closed_verified':getattr(job,'scope_closed_verified',None) is True,
        'primary_resume':resume_projection(getattr(job,'resume_metadata',None))}


def finish_private_job(job,child):
    """Try fallback closure without losing a handle or the first stop error."""
    if job is None:return False
    primary=None;clean=False
    try:clean=(job.stop(child) if child is not None else job.close_unassigned()) is True
    except BaseException as error:primary=error
    finally:
        if job.handle:
            try:
                closed=bool(job.kernel.CloseHandle(job.handle))
                if closed:job.handle=None
                clean=closed and clean
            except BaseException as error:
                clean=False
                if primary is None:primary=error
    if primary is not None:raise primary
    return clean


def private_probe(binary,port,temporary,preflight=False,failure_observation=None):
    """One owned child; retain only a strict fixed projection before teardown."""
    if type(preflight) is not bool or (not preflight and (type(port) is not int or not 20000<=port<=59999)):
        raise ValueError('development_private_probe_arguments')
    if failure_observation is not None and (type(failure_observation) is not dict or failure_observation):
        raise ValueError('development_observation_sink')
    if failure_observation is not None:failure_observation.update(observation(None,None,preflight,received=True))
    credentials=bytearray() if preflight else bytearray((selected.password_fixture.ACCOUNT+'\n'+selected.password_fixture.PASSWORD+'\n').encode('ascii'))
    child=None;job=None;clean=False;primary=None;result=None
    try:
        job=DevelopmentJob()
        with tempfile.TemporaryFile(dir=temporary) as output:
            try:
                child=job.popen([str(binary),'--platform-preflight' if preflight else str(port)],
                    cwd=temporary,stdin=subprocess.PIPE,stdout=output,stderr=subprocess.DEVNULL)
                job.assign(child);child.communicate(input=credentials,timeout=12 if preflight else 37)
                if child.returncode!=0 or os.fstat(output.fileno()).st_size>8192:
                    raise ValueError('development_private_probe_refused')
                output.seek(0);base,prefix=received_prefix.native(private_json(output.read(8193)),preflight)
                result=admit_probe(base,preflight)
                result['normalized_policy_schema']=result['schema']
                result['native_producer_schema']=result['schema'][:-1]+'2'
                result['schema']='coh-auth-db-development-policy-result-projection-v2'
                result['db_received_prefix']=received_prefix.completion(prefix,preflight)
            finally:
                if failure_observation is not None:failure_observation.update(observation(child,output,preflight,received=True))
    except BaseException as error:
        primary=error;raise
    finally:
        for i in range(len(credentials)):credentials[i]=0
        cleanup_exception=False
        try:
            if child is not None and job is not None:
                pipe_clean=activation.close_streams([child.stdin]) if child.stdin is not None else True
                clean=finish_private_job(job,child) and pipe_clean
            elif job is not None:clean=finish_private_job(job,None)
        except BaseException:
            clean=False;cleanup_exception=True
            if primary is None:raise
        finally:
            if failure_observation is not None:
                failure_observation['owned_child_cleanup_complete']=clean
                failure_observation['owned_child_cleanup_outcome']=('EXCEPTION' if cleanup_exception else 'COMPLETE' if clean else 'REFUSED')
                failure_observation['owned_child_job_empty_before_close']=(job is not None and job.empty_before_close is True)
                failure_observation['owned_child_job_assignment_verified']=(job is not None and job.assignment_verified is True)
                failure_observation['owned_child_launch_state']=job_projection(job)['launch_state']
    if not clean:raise ValueError('development_private_child_cleanup')
    return result


class PrivateBuildCommands:
    """Owned compile/configure descendants and private fixed log metadata."""
    def __init__(self,directory):self.directory=directory;self.records=[]
    def run(self,name,command,timeout):
        if name not in ('configure-new-db-probe','build-new-db-probe'):raise ValueError('development_build_command_kind')
        child=None;job=None;clean=False;primary=None
        log=self.directory/(name+'.private.log');record={'name':name,'succeeded':False,'owned_cleanup_complete':False}
        self.records.append(record)
        try:
            job=DevelopmentJob()
            with log.open('xb') as output:
                child=job.popen(list(map(str,command)),cwd=self.directory,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT)
                job.assign(child);child.wait(timeout=timeout)
                record['succeeded']=child.returncode==0
                if not record['succeeded']:raise ValueError('development_new_probe_build_refused')
        except BaseException as error:
            primary=error;raise
        finally:
            try:
                clean=finish_private_job(job,child)
            except BaseException:
                clean=False
                if primary is None:raise
            finally:
                record['owned_cleanup_complete']=clean
                record['owned_job_empty_before_close']=(job is not None and job.empty_before_close is True)
                record['owned_job_assignment_verified']=(job is not None and job.assignment_verified is True)
                record['launch']=job_projection(job)
                record['private_log_exported']=False
        if not clean:raise ValueError('development_new_probe_build_cleanup')


def _coff_identity(path):
    with path.open('rb') as stream:header=stream.read(56)
    if len(header)<20:raise ValueError('development_coff_header_required')
    machine=int.from_bytes(header[:2],'little')
    if header[:4]==b'\0\0\xff\xff':
        if len(header)<56 or int.from_bytes(header[4:6],'little')!=2:
            raise ValueError('development_bigobj_header_required')
        machine=int.from_bytes(header[6:8],'little')
    if machine!=0x8664:raise ValueError('development_x64_coff_required')
    return {'bytes':path.stat().st_size,'sha256':selected.prior.sha(path),'machine':'AMD64','admission':'header_machine_and_whole_file_hash'}


def probe_identity(path):
    """Header and bounded static platform import admission; no loader claim."""
    identity=login.probe_identity(path);raw=path.read_bytes()
    def need(condition):
        if not condition:raise ValueError('development_x64_platform_imports_refused')
    def take(at,size):
        need(type(at) is int and type(size) is int and 0<=at<=len(raw) and 0<=size<=len(raw)-at)
        return raw[at:at+size]
    def u32(at):return struct.unpack('<I',take(at,4))[0]
    need(len(raw)<=16*1024*1024 and identity['sha256']==hashlib.sha256(raw).hexdigest())
    pe=u32(60);need(pe>=64 and take(0,2)==b'MZ' and take(pe,4)==b'PE\0\0')
    count=struct.unpack('<H',take(pe+6,2))[0];optional=struct.unpack('<H',take(pe+20,2))[0];op=pe+24
    need(struct.unpack('<H',take(pe+4,2))[0]==0x8664 and struct.unpack('<H',take(op,2))[0]==0x20b
        and struct.unpack('<H',take(op+68,2))[0]==3 and 1<=count<=96 and optional==240 and u32(op+108)==16)
    sections=[]
    for index in range(count):
        virtual,address,size,offset=struct.unpack('<IIII',take(op+optional+index*40+8,16))
        need(offset+size<=len(raw) and address+max(virtual,size)<=u32(op+56))
        sections.append((address,size,offset))
    def rva(address,size):
        owners=[offset+address-base for base,length,offset in sections if base<=address and address+size<=base+length]
        need(len(owners)==1);return take(owners[0],size)
    def text(address,limit):
        chars=bytearray()
        for offset in range(limit):
            value=rva(address+offset,1)[0]
            if value==0:return chars.decode('ascii')
            need(32<=value<127);chars.append(value)
        need(False)
    need(take(op+112+13*8,8)==bytes(8))
    address,size=struct.unpack('<II',take(op+120,8));need(address>0 and 40<=size<=20*128)
    names=[];terminated=False
    for index in range(size//20):
        fields=struct.unpack('<IIIII',rva(address+index*20,20))
        if not any(fields):terminated=True;break
        lookup,stamp,chain,name,iat=fields;dll=text(name,129).lower()
        need(dll in PLATFORM_DLLS and dll not in names and bool(lookup or iat));names.append(dll)
        for symbol in range(4097):
            value=struct.unpack('<Q',rva((lookup or iat)+symbol*8,8))[0]
            if value==0:break
            need(symbol<4096)
            if value>>63:need(value&0x7fffffffffff0000==0 and value&65535!=0)
            else:need(value<=0xffffffff);rva(value,2);text(value+2,513)
        else:need(False)
    need(terminated and {'kernel32.dll','ws2_32.dll'}<=set(names))
    return dict(identity,platform_imports=sorted(names),delay_imports_absent=True,
        no_unadmitted_dll_imports=True,platform_loader_or_export_resolution_claimed=False)


def build_probe(root,temporary,retained,build_observation=None):
    if build_observation is not None and (type(build_observation) is not dict or build_observation):
        raise ValueError('development_build_observation_sink')
    trace={} if build_observation is None else build_observation
    trace.update(stage='ADMIT_CRYPTO',commands=[],raw_build_logs_exported=False)
    crypto,crypto_admission=selected.admit_crypto(retained,root)
    trace['stage']='RECOVER_EXACT_ZLIB'
    zlib=temporary/'zlib-private';zlib_admission=recover_zlib(root,zlib);zlib_before=verify_zlib(root,zlib)
    project,build=temporary/'project',temporary/'build';sources=prepare_project(root,project,crypto,zlib)
    source_before={p.relative_to(root).as_posix():selected.prior.sha(p) for p in sources}
    runner=PrivateBuildCommands(temporary);policy=login.PROBE_BUILD_POLICY
    trace['commands']=runner.records;trace['stage']='CONFIGURE'
    runner.run('configure-new-db-probe',['cmake','-S',project,'-B',build,'-G',policy['cmake_generator'],'-A',policy['architecture']],180)
    trace['stage']='COMPILE'
    runner.run('build-new-db-probe',['cmake','--build',build,'--config',policy['configuration'],
        '--target','coh-auth-db-development','--parallel',policy['parallel']],240)
    trace['stage']='ADMIT_NEW_OBJECTS_AND_PE'
    import xml.etree.ElementTree as xml
    manifest=json.loads((root/ZLIB_EVIDENCE/'admission.json').read_bytes())
    expected_zlib=[zlib/name for name in manifest['x64_recipe_translation_units']]
    object_groups={}
    for name,expected in (('coh-auth-db-development',sources),('chromium_zlib',expected_zlib)):
        projects=list(build.rglob(name+'.vcxproj'))
        if len(projects)!=1:raise ValueError('development_exact_project_required')
        tree=xml.parse(projects[0]);ns={'m':'http://schemas.microsoft.com/developer/msbuild/2003'}
        if any('COH_TEST' in (node.text or '') for node in tree.iter()):
            raise ValueError('development_synthetic_build_define_refused')
        actual={Path(node.attrib['Include']).resolve() for node in tree.findall('.//m:ClCompile[@Include]',ns)}
        if actual!={p.resolve() for p in expected}:raise ValueError('development_project_source_closure')
        release=[n for n in tree.findall('.//m:ItemDefinitionGroup',ns) if "Release|x64" in n.attrib.get('Condition','')]
        if len(release)!=1:raise ValueError('development_release_project')
        runtime=release[0].find('m:ClCompile/m:RuntimeLibrary',ns)
        definitions=release[0].find('m:ClCompile/m:PreprocessorDefinitions',ns)
        if runtime is None or runtime.text!='MultiThreaded' or definitions is None or 'CHROMIUM_ZLIB_NO_CHROMECONF' not in definitions.text.split(';'):
            raise ValueError('development_static_runtime_or_zlib_interface')
        objects=[p for p in build.rglob('*.obj') if any(part==name+'.dir' for part in p.parts) and 'Release' in p.parts]
        if len(objects)!=len(expected) or {p.stem.casefold() for p in objects}!={p.stem.casefold() for p in expected}:
            raise ValueError('development_exact_object_inventory')
        object_groups[name]={p.name:_coff_identity(p) for p in sorted(objects)}
    binary=build/'Release/coh-auth-db-development.exe';identity=probe_identity(binary)
    static=build/'zlib-owned/Release/chromium_zlib.lib'
    if not static.is_file() or not static.read_bytes().startswith(b'!<arch>\n'):raise ValueError('development_static_zlib_archive')
    if verify_zlib(root,zlib)!=zlib_before or selected.admit_crypto(retained,root)[1]!=crypto_admission:
        raise ValueError('development_dependency_changed_during_link')
    if any(selected.prior.sha(root/name)!=digest for name,digest in source_before.items()):raise ValueError('development_source_changed_during_link')
    trace['stage']='COMPLETE'
    return binary,{'binary':identity,'retained_crypto':crypto_admission,'zlib_source':zlib_admission,
        'zlib_private_source':zlib_before,'static_zlib':{'bytes':static.stat().st_size,'sha256':selected.prior.sha(static)},
        'project_sources_sha256':source_before,'objects':object_groups,'build_policy':policy,
        'generated_project_sha256':selected.prior.sha(project/'CMakeLists.txt'),'commands':runner.records,
        'server_rebuilt':False,'crypto_rebuilt':False,'ordinary_core_modified':False,
        'map_client_linked':False,'approved_reference_checksum_admitted':False,'normal_version_admitted':False}


class DevelopmentScope:
    """Distinct one-attempt owner; never a selected-scope subclass or grant API."""
    def __init__(self,retained,db_candidate_generation,*,provisional_development_policy=False):
        if provisional_development_policy is not True:raise ValueError('development_policy_must_be_explicit')
        if type(db_candidate_generation) is not activation.DbCandidateGeneration:
            raise ValueError('development_candidate_generation_type')
        self.retained=Path(retained);self._generation=db_candidate_generation
        self.binary=None;self.registry=None;self._build_attempted=False;self._exercise_attempted=False;self._native_attempted=False;self._prepared=False
        self.build_observation={};self.build_metadata={};self.preflight_observation={};self.preflight={}
        self.native_observation={};self.registry_metadata={}
        self._service_jobs=[]

    def new_service_job(self):
        job=DevelopmentJob();self._service_jobs.append(job);return job

    def service_jobs_stopped(self):
        return all(job.scope_closed_verified is True for job in self._service_jobs)

    @property
    def db_candidate_generation(self):return self._generation

    def build(self,root,temporary):
        if self._build_attempted:raise ValueError('development_probe_build_consumed')
        self._build_attempted=True
        self.binary,self.build_metadata=build_probe(root,temporary,self.retained,self.build_observation)
        if probe_identity(self.binary)!=self.build_metadata['binary']:raise ValueError('development_new_probe_changed')
        self.preflight=private_probe(self.binary,None,temporary,True,self.preflight_observation)
        if probe_identity(self.binary)!=self.build_metadata['binary']:raise ValueError('development_new_probe_changed')

    def prepare(self,root,temporary,output,runner,proof,sql,sql_runner):
        if self._prepared or self.registry is not None or not self.preflight or self.preflight.get('passed') is not True:
            raise ValueError('development_scope_not_fresh_or_platform_unqualified')
        if 'owned_service_generations_start' in proof:raise ValueError('development_services_already_started')
        try:
            if sql.count('-S')!=1:raise ValueError()
            match=re.fullmatch(r'\(localdb\)\\(cohauth-ci-[a-f0-9]{24})',str(sql[sql.index('-S')+1]))
            if match is None:raise ValueError()
            instance=match[1]
        except (ValueError,IndexError):raise ValueError('development_owned_instance_required') from None
        module=_registry_module(root);self.registry=module.RegistryLease(instance)
        proof.update(development_scope='fresh_real_auth_original_development_db_complete_empty_list_then_cancel_destroy',
            development_probe_build=self.build_metadata,development_platform_preflight=self.preflight,
            development_platform_preflight_observation=self.preflight_observation,
            auth_only_negative_cases_repeated=False,grant_values_exported=False,private_credentials_exported=False,
            normal_version_admitted=False,checksum_reference_admitted=False,character_selected=False,
            map_handoff_verified=False,current_world_verified=False,
            server_development_skip_observed=False,development_db_request_state='UNAVAILABLE')
        try:self.registry_metadata=self.registry.prepare(owned_services_not_started=True)
        except Exception:
            try:proof['owned_empty_registry_prepare']=self.registry.snapshot()
            except Exception:proof['owned_empty_registry_prepare']={'prepared':False,'failure':'REGISTRY_OWNER_REFUSED'}
            raise
        else:proof['owned_empty_registry_prepare']=self.registry_metadata
        if self.registry.client_project!='coh-ci-'+instance.removeprefix('cohauth-ci-'):
            raise ValueError('development_owned_client_project')
        selected.password_fixture.write_private_fixture(temporary/'private-development-credentials')
        account=temporary/'private-development-account.sql';account.write_text(selected.account_sql(),encoding='ascii')
        sql_runner.run('seed-private-development-password',[*sql,'-i',temporary/'private-development-credentials/credential.sql'],timeout=150)
        sql_runner.run('seed-private-development-account',[*sql,'-i',account],timeout=150)
        if activation.scalar(sql,selected.USERDATA_QUERY,temporary)!=1:raise ValueError('development_userdata_not_complete')
        selected.require_group_membership(sql,temporary)
        proof.update(complete_userdata_preflight_verified=True,selected_group_membership_preflight_verified=True)
        self._prepared=True

    def exercise(self,temporary,proof,sql,ports,auth_child,db_child,auth,db,auth_start,db_start,sql_pid,sql_start):
        if not self._prepared or self._exercise_attempted:raise ValueError('development_scope_attempt_consumed_or_unprepared')
        self._exercise_attempted=True
        def observe():
            result={'auth':activation.service_process_snapshot(auth_child,auth,auth_start),
                'db':activation.service_process_snapshot(db_child,db,db_start,expected_binary_sha256=self._generation.binary_sha256),
                'sql':login.owned_process_snapshot(sql_pid),'channel':activation.owned_channel(auth_child.pid,db_child.pid,ports[0]),
                'game_listener':activation.game_listener(db_child.pid)}
            if (result['sql']!=sql_start or login.inspect_listeners(auth_child.pid)!=set(ports)
                    or activation.scalar(sql,'SET NOCOUNT ON;SELECT COUNT(*) FROM cohauth.dbo.worldstatus WHERE idx=1 AND status=1;',temporary)!=1):
                raise ValueError('development_owned_runtime_unavailable')
            if (selected.prior.sha(db.parent/'data/server/db/servers.cfg')!=proof['runtime_config_sha256']['db']
                    or selected.prior.sha(auth.parent/'etc/config.txt')!=proof['runtime_config_sha256']['auth']):
                raise ValueError('development_owned_runtime_profile_changed')
            lines=(db.parent/'data/server/db/servers.cfg').read_text(encoding='ascii').splitlines()
            if [line for line in lines if line.startswith('ClientProject ')]!=['ClientProject '+self.registry.client_project]:
                raise ValueError('development_owned_client_project')
            if activation.scalar(sql,selected.USERDATA_QUERY,temporary)!=1:raise ValueError('development_userdata_not_complete')
            selected.require_group_membership(sql,temporary)
            result['registered_group_membership_verified']=True
            return result
        proof['development_runtime_before_probe']=observe()
        if probe_identity(self.binary)!=self.build_metadata['binary']:raise ValueError('development_private_binary_changed')
        proof['client_login_attempted']=True;failed=False
        self._native_attempted=True
        try:
            proof['development_probe_result']=private_probe(self.binary,ports[1],temporary,False,self.native_observation)
            proof['db_login_attempted']=True;proof['development_db_request_state']='QUEUED'
        except Exception:
            failed=True;proof['development_probe_failure_observation']=self.native_observation
            if self.native_observation.get('json_state')=='VALID':
                state=self.native_observation['db_request_state'];proof['development_db_request_state']=state
                proof['db_login_attempted']=state=='QUEUED'
            raise
        finally:
            try:
                proof['development_runtime_after_probe']=observe()
                if probe_identity(self.binary)!=self.build_metadata['binary']:raise ValueError('development_private_binary_changed')
                proof['development_runtime_after_probe_verified']=True
            except Exception:
                proof['development_runtime_after_probe_verified']=False
                proof['development_runtime_after_probe_failure']='OWNED_RUNTIME_OBSERVER_REFUSED'
                if not failed:
                    proof['development_probe_failure_observation']=self.native_observation
                    raise
        return True


def failure_kind(error):
    if isinstance(error,subprocess.TimeoutExpired):return 'OWNED_CHILD_DEADLINE'
    if isinstance(error,ValueError):return 'SCOPE_REFUSED'
    if isinstance(error,OSError):return 'OWNED_IO_REFUSED'
    return 'UNEXPECTED_SOURCE_FAILURE'


def run(args):
    root,output=args.source_root.resolve(),args.output.resolve()
    if getattr(args,'allow_provisional_development_policy',None) is not True:
        raise ValueError('development_policy_must_be_explicit')
    identity=selected.prior.require_hosted(root,output,args.expected_commit)
    inputs=committed_inputs(root,args.expected_commit)
    db=readiness.DbCandidate(root,args.db_candidate_stage,args.expected_db_receipt_sha256,args.expected_db_binary_sha256)
    generation=activation.DbCandidateGeneration(db.binary_sha256,db.receipt_pin)
    scope=DevelopmentScope(args.retained_intact_stage.resolve(),generation,provisional_development_policy=True)
    activation.admit_development_candidate(scope,db)
    temporary=Path(tempfile.mkdtemp(prefix='coh-development-client-',dir=os.environ['RUNNER_TEMP']))
    value=dict(identity,account_controls_source_qualification=account_controls_summary(),schema='coh-owned-mssql-db-threadname-development-player-list-v1',passed=False,
        provisional_development_db_player_list_verified=False,selected_shard_play_verified=False,
        authenticated_db_map_handoff_verified=False,normal_version_admitted=False,
        checksum_reference_admitted=False,nondevelopment_version_admitted=False,
        checksum_reference_installed=False,checksum_policy_relaxed=False,shipping_profiles_modified=False,
        accepted_runtime_replaced=False,server_development_skip_observed=False,
        source_inferred_development_exception_used=False,grant_values_exported=False,private_credentials_exported=False,
        auth_only_login_repeated=False,owned_service_cleanup_complete=True,
        owned_firewall_cleanup_complete=True,owned_localdb_cleanup_complete=True,private_files_removed=True)
    try:
        scope.build(root,temporary)
        if committed_inputs(root,args.expected_commit)!=inputs:raise ValueError('development_source_changed_before_services')
        # Until the ordinary owner returns its receipt, its teardown is unknown.
        # A late common-owner exception cannot inherit the pre-service defaults.
        value.update(owned_service_cleanup_complete=False,owned_firewall_cleanup_complete=False,
            owned_localdb_cleanup_complete=False,private_files_removed=False)
        private_args=copy.copy(args);private_args.output=temporary/'private-service-receipt'
        value=activation.run(private_args,db_candidate=db,development_scope=scope)
    except Exception as error:
        value['passed']=False;value.setdefault('failure',failure_kind(error))
    finally:
        value['development_probe_build_observation']=scope.build_observation
        value['development_probe_build']=scope.build_metadata
        value['development_platform_preflight_observation']=scope.preflight_observation
        if scope.preflight:value['development_platform_preflight']=scope.preflight
        value['development_service_job_launches']=[job_projection(job) for job in scope._service_jobs]
        registry_clean=True
        if scope.registry is not None:
            stopped=(value.get('owned_service_cleanup_complete') is True
                and scope.service_jobs_stopped()
                and (not scope._native_attempted or (scope.native_observation.get('owned_child_cleanup_complete') is True
                    and scope.native_observation.get('owned_child_job_empty_before_close') is True)))
            value['development_all_owned_service_jobs_empty_before_close']=scope.service_jobs_stopped()
            try:
                result=scope.registry.cleanup(services_stopped=stopped)
                value['owned_empty_registry_cleanup']=result
                registry_clean=stopped and result.get('cleanup_verified') is True
            except Exception:
                registry_clean=False;value['owned_empty_registry_cleanup']={'cleanup_verified':False,'failure':'REGISTRY_OWNER_REFUSED'}
        value['owned_registry_cleanup_complete']=registry_clean
        try:
            stable=db.verify()==db.admission and committed_inputs(root,args.expected_commit)==inputs
        except Exception:stable=False
        value['development_candidate_and_source_inputs_unchanged']=stable
        value['development_source_sha256']=inputs
        try:shutil.rmtree(temporary);removed=not temporary.exists()
        except Exception:removed=False
        value['private_probe_build_removed']=removed
        value['passed']=(value.get('passed') is True and registry_clean and stable and removed)
        if not value['passed']:
            value.update(provisional_development_db_player_list_verified=False,selected_shard_play_verified=False,
                source_inferred_development_exception_used=False)
            value.setdefault('failure','DEVELOPMENT_CLEANUP_OR_ADMISSION_REFUSED')
        if not output.exists():output.mkdir()
        (output/'receipt.json').write_text(json.dumps(value,indent=2)+'\n')
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source-root','output','auth-success-archive','auth-candidate-stage','db-candidate-stage','retained-intact-stage'):
        parser.add_argument('--'+name,type=Path,required=True)
    for name in ('expected-commit','expected-db-receipt-sha256','expected-db-binary-sha256'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--allow-provisional-development-policy',action='store_true',required=True)
    value=run(parser.parse_args())
    print(json.dumps({key:value.get(key) for key in ('passed','failure','selected_shard_play_verified',
        'provisional_development_db_player_list_verified','authenticated_db_map_handoff_verified')}))
    return 0 if value['passed'] else 1
