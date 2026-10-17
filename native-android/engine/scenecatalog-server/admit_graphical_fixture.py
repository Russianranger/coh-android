#!/usr/bin/env python3
"""Admit exact fresh graphical fixture bytes for the existing private supervisor.

The successful capture receipt SHA must be pinned independently to the owned
CI artifact. This checks retained byte/receipt closure; it is not world authority.
"""
from __future__ import annotations
import argparse,json,os,re
from pathlib import Path
import capture_graphical_fixture as capture
require=capture.require
def inspect(directory,receipt_sha256):
    directory=directory.resolve();receipt_path=directory/'fixture-capture.json'
    require(re.fullmatch('[0-9a-f]{64}',receipt_sha256 or '') is not None
            and capture.pin(receipt_path,16*1024**2)['sha256']==receipt_sha256,'FIXTURE_RECEIPT_PIN')
    receipt=json.loads(receipt_path.read_bytes())
    require(type(receipt) is dict and receipt.get('schema')=='coh-fresh-graphical-fixture-capture-v1','FIXTURE_SCHEMA')
    for name in ('passed','fixture_only','inputs_unchanged','owned_process_group_absent',
                 'original_guest_cleanup_verified','committed_original_logout_verified',
                 'fresh_profile_source_creation_verified','public_fixture_dump_retention_permitted',
                 'fresh_role_secret_export_scan_passed','regular_publication_preflight_verified'):
        require(receipt.get(name) is True,'FIXTURE_SUCCESS_'+name.upper())
    for name in ('private_user_input_accepted','apk_rebuilt','client_or_server_recompiled','synthetic_character_rows',
                 'source_generation_admitted','world_authority','android_execution_validated'):
        require(receipt.get(name) is False,'FIXTURE_SCOPE_'+name.upper())
    require(receipt.get('input_scope')=='new_disposable_original_graphical_COHLOCAL_THORHERO'
            and receipt.get('failure') is None and receipt.get('repository')=='Russianranger/coh-android'
            and receipt.get('runner_environment')=='github-hosted'
            and all(type(receipt.get(name)) is int and receipt[name]>0 for name in ('workflow_run_id','workflow_run_attempt'))
            and receipt.get('apk')==capture.APK and receipt.get('build_report')==capture.BUILD
            and receipt.get('game_archive')==capture.ARCHIVE and receipt.get('donor',{}).get('revision')==capture.DONOR
            and receipt.get('ocr_overlay_sha256')==capture.OCR_SHA,'FIXTURE_ORIGIN')
    require(type(receipt.get('fixture_wire_slot')) is int and receipt['fixture_wire_slot']==0,'FIXTURE_WIRE_SLOT')
    probe=receipt.get('publication_preflight_observation')
    require(receipt.get('capture_stage')=='COMPLETE' and receipt.get('failure_stage')=='NONE'
            and type(probe) is dict and set(probe)==set(capture.publication_observation())
            and all(value is True for value in probe.values()),
            'FIXTURE_REAL_REGULAR_PUBLICATION')
    helper=receipt.get('backup_observation')
    require(type(helper) is dict and set(helper)==set(capture.backup_observation())
            and all(helper[name] is True for name in capture.backup_observation()
                    if name not in ('helper_stage','helper_failure_code'))
            and helper['helper_stage']=='COMPLETE' and helper['helper_failure_code']=='NONE','FIXTURE_HELPER_CLOSURE')
    session=receipt.get('session_id');require(type(session) is str and re.fullmatch('[0-9a-f]{32}',session),'FIXTURE_SESSION')
    pins=receipt.get('retained_creation_evidence')
    names={'original-guest-report.json','external-observer.json','backup-request.json','backup-receipt.json'}
    require(type(pins) is dict and set(pins)==names,'FIXTURE_EVIDENCE_SET')
    objects={}
    for name in sorted(names):
        path=directory/name;require(capture.pin(path,16*1024**2)==pins[name],'FIXTURE_EVIDENCE_BYTES')
        objects[name]=json.loads(path.read_bytes());require(type(objects[name]) is dict,'FIXTURE_EVIDENCE_OBJECT')
    backup=objects['backup-receipt.json'];request=objects['backup-request.json']
    dump=capture.pin(directory/'fixture.pgdump',capture.MAX_DUMP)
    with (directory/'fixture.pgdump').open('rb') as source:require(source.read(5)==b'PGDMP','FIXTURE_CUSTOM_ARCHIVE')
    capture.validate_backup(backup,request,dump)
    require(receipt.get('full_backup')==backup and request['session_id']==session,'FIXTURE_BACKUP_CLOSURE')
    require(capture.regular(directory/'account.txt',15).read_bytes()==b'COHLOCAL\n','FIXTURE_ACCOUNT_BYTES')
    require(receipt.get('original_guest_report')==pins['original-guest-report.json'],'FIXTURE_GUEST_REPORT_PIN')
    observer=objects['external-observer.json'];guest=objects['original-guest-report.json']
    require(observer.get('session_id')==session and observer.get('failure') is None
            and observer.get('terminal_event_observed') is True and type(observer.get('client_pid')) is int
            and observer['client_pid']==request['client_pid'] and observer.get('interaction_script',{}).get('full_backup')==backup,
            'FIXTURE_OBSERVER_CLOSURE')
    saved=guest.get('character_creation',{});local=guest.get('local_login',{})
    require(guest.get('passed') is True and guest.get('status')=='passed' and guest.get('failures')==[]
            and guest.get('session_id')==session and guest.get('scope')=='actual_character_creation_guest'
            and guest.get('cleanup_complete') is True and local.get('profile_reused') is False
            and local.get('profile_initialized') is True and type(local.get('character_count')) is int
            and local['character_count']==0 and local.get('account')=='COHLOCAL'
            and all(saved.get(name) is True for name in ('verified','committed_sql_verified',
                 'requested_logout_observed','logout_timer_observed','disconnected_before_sql'))
            and saved.get('forced_stop_before_save') is False and saved.get('name')=='THORHERO'
            and saved.get('account')=='COHLOCAL' and type(saved.get('character_id')) is int
            and saved['character_id']==request['character_id'] and type(saved.get('auth_id')) is int
            and saved['auth_id']==backup['fixture_identity']['auth_id'],'FIXTURE_GUEST_CLOSURE')
    # Independent artifact/run provenance remains the caller's responsibility;
    # receipt bytes are never accepted by a caller-asserted fixture boolean.
    return {'schema':'coh-graphical-fixture-admission-v1','passed':True,'fixture_only':True,
            'capture_receipt_sha256':receipt_sha256,'database_dump':str(directory/'fixture.pgdump'),
            'database_dump_sha256':dump['sha256'],'account_file':str(directory/'account.txt'),'wire_slot':0,
            'required_postgresql_major_minimum':18,'source_generation_admitted':False,'world_authority':False}
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,required=True)
    parser.add_argument('--receipt-sha256',required=True);args=parser.parse_args()
    try:print(json.dumps(inspect(args.fixture,args.receipt_sha256),indent=2));return 0
    except Exception as error:
        print(json.dumps({'passed':False,'failure_code':str(error) if isinstance(error,capture.Refused) else 'FIXTURE_ADMISSION_FAILED','world_authority':False}));return 2
if __name__=='__main__':raise SystemExit(main())
