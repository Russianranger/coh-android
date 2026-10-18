#!/usr/bin/env python3
"""Emit only fixed public status fields from the private GROUPS supervisor.

Never export a private receipt, packet, source envelope, identity, path, hash,
account, dump, log, exception text or caller-provided failure string.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,stat,subprocess
from pathlib import Path
from groups_capture_stages import CAPTURE_STAGES,FAILURE_STAGES
import groups_native_status as native_status
from fresh_callback_observer import probe as source_probe
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
STATUS=('runtime_executed','matching_groups_transaction_captured','cleanup_verified',
        'owned_process_groups_absent','private_input_bytes_unchanged','restored_private_copy_unchanged',
        'source_runtime_unchanged','compiled_inputs_unchanged')
PAIR=('exact_logical_packet_verified','same_source_selected_dbid_verified','actual_native_owned_receive_verified')
FAILURES=frozenset(('NONE','SOURCE_CAPTURE_NOT_ACCEPTED','PRIVATE_RECEIPT_ABSENT','PRIVATE_RECEIPT_INVALID'))
class Refused(ValueError):pass
def require(value):
    if not value:raise Refused('PUBLIC_SUMMARY_REFUSED')
def empty(code):
    require(code in FAILURES)
    # This fixed construction is the complete public field allowlist.
    return {'schema':'coh-source-native-groups-public-summary-v1','passed':False,
        'failure_code':code,**{name:False for name in STATUS},**{name:False for name in PAIR},
        'capture_stage':'PREFLIGHT' if code=='PRIVATE_RECEIPT_ABSENT' else 'RECEIPT_INVALID',
        'failure_stage':'PREFLIGHT' if code=='PRIVATE_RECEIPT_ABSENT' else 'RECEIPT_INVALID',
        'local_development_auth':True,'authserver_authenticated':False,'source_generation_admitted':False,
        'actor_identity_verified':False,'world_authority':False,'private_source_output_exported':False,
        'native_diagnostic':native_status.empty(),'source_profile_diagnostic':source_probe.empty()}
def summarize(value):
    require(type(value) is dict and value.get('schema')=='coh-private-original-native-groups-run-v1'
            and value.get('private_character_state') is True and value.get('public_upload_permitted') is False
            and value.get('local_development_auth') is True and value.get('authserver_authenticated') is False
            and value.get('source_generation_admitted') is False and value.get('world_authority') is False
            and type(value.get('passed')) is bool)
    result=empty('NONE' if value['passed'] else 'SOURCE_CAPTURE_NOT_ACCEPTED')
    require(value.get('capture_stage') in CAPTURE_STAGES and value.get('failure_stage') in FAILURE_STAGES)
    require((value['capture_stage']=='COMPLETE' and value['failure_stage']=='NONE') if value['passed'] else value['failure_stage'] not in ('NONE','PREFLIGHT','RECEIPT_INVALID'))
    result['capture_stage']=value['capture_stage'];result['failure_stage']=value['failure_stage']
    if 'native_diagnostic' in value:result['native_diagnostic']=native_status.public(value['native_diagnostic'])
    if 'source_profile_diagnostic' in value:
        try:result['source_profile_diagnostic']=source_probe.public(value['source_profile_diagnostic'])
        except Exception:
            refused=source_probe.empty();refused['probe_state']='REFUSED';result['source_profile_diagnostic']=source_probe.public(refused)
    for name in STATUS:
        flag=value.get(name,False);require(type(flag) is bool);result[name]=flag
    if result['matching_groups_transaction_captured']:
        pair=value.get('pair')
        require(type(pair) is dict and pair.get('schema')=='coh-original-native-groups-pair-v1'
                and pair.get('passed') is True and pair.get('source_run_provenance_verified') is False
                and pair.get('cache_equivalence_verified') is False and pair.get('source_generation_admitted') is False
                and pair.get('actor_identity_verified') is False and pair.get('world_authority') is False)
        for name in PAIR:require(pair.get(name) is True);result[name]=True
    if value['passed']:require(all(result[name] for name in (*STATUS,*PAIR)))
    result['passed']=value['passed'];return result
def private_receipt(directory):
    # The source supervisor writes only to its fresh0700 private output. This
    # helper reads one exact filename; it never scans or serializes that tree.
    if not directory.exists():raise FileNotFoundError
    require(directory.is_dir() and not directory.is_symlink())
    owned=directory.stat();require(owned.st_uid==os.geteuid() and not owned.st_mode&0o077)
    path=directory/'capture-receipt.json';info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_uid==os.geteuid()
            and not info.st_mode&0o077 and 0<info.st_size<=8*1024**2)
    def pairs(rows):
        value={}
        for key,item in rows:require(key not in value);value[key]=item
        return value
    return json.loads(path.read_bytes(),object_pairs_hook=pairs,parse_constant=lambda _:require(False))
def committed_helper():
    revision=os.environ.get('GITHUB_SHA','');require(re.fullmatch('[0-9a-f]{40}',revision) is not None)
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==revision)
    relative=Path(__file__).resolve().relative_to(ROOT).as_posix()
    expected=subprocess.check_output(['git','show',revision+':'+relative],cwd=ROOT,stderr=subprocess.DEVNULL)
    actual=Path(__file__).read_bytes();require(actual==expected)
    stages=HERE/'groups_capture_stages.py';require(stages.read_bytes()==subprocess.check_output(
        ['git','show',revision+':'+stages.relative_to(ROOT).as_posix()],cwd=ROOT,stderr=subprocess.DEVNULL))
    diagnostic=HERE/'groups_native_status.py';require(diagnostic.read_bytes()==subprocess.check_output(
        ['git','show',revision+':'+diagnostic.relative_to(ROOT).as_posix()],cwd=ROOT,stderr=subprocess.DEVNULL))
    for relative in native_status.ENUM_SOURCE_PATHS:
        require((ROOT/relative).read_bytes()==subprocess.check_output(
            ['git','show',revision+':'+relative],cwd=ROOT,stderr=subprocess.DEVNULL))
    for relative in ('fresh_callback_observer/probe.py','fresh_callback_observer/source_group_profile.inc','fresh_callback_observer/source_group_profile_api.h','fresh_callback_observer/source_folder_profile_api.h'):
        path=HERE/relative;require(path.read_bytes()==subprocess.check_output(
            ['git','show',revision+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT,stderr=subprocess.DEVNULL))
    return revision,hashlib.sha256(actual).hexdigest()
def emit(directory,output):
    revision,source=committed_helper()
    try:value=private_receipt(directory);result=summarize(value)
    except FileNotFoundError:result=empty('PRIVATE_RECEIPT_ABSENT')
    except Exception:result=empty('PRIVATE_RECEIPT_INVALID')
    result['orchestration_revision']=revision;result['summary_source_sha256']=source
    require(output.parent.is_dir() and not output.exists() and not output.is_symlink())
    with output.open('x') as stream:
        os.chmod(output,0o600);json.dump(result,stream,sort_keys=True,indent=2);stream.write('\n')
        stream.flush();os.fsync(stream.fileno())
    return result
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--private-output',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();os.umask(0o077)
    try:
        value=emit(args.private_output,args.output)
        print(json.dumps({'summary_written':True,'passed':value['passed'],'failure_code':value['failure_code'],'world_authority':False}));return 0
    except Exception:
        print(json.dumps({'summary_written':False,'passed':False,'failure_code':'PUBLIC_SUMMARY_REFUSED','world_authority':False}));return 2
if __name__=='__main__':raise SystemExit(main())
