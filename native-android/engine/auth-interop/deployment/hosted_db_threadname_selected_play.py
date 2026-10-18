#!/usr/bin/env python3
"""Fresh selected-shard grant on the separately admitted thread-name Db PE.

Reuse the unchanged encrypted probe and accepted Auth PE. Stop and wipe before
DB client login; this scope grants no version/checksum/character/Map admission.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import hosted_db_threadname_readiness as readiness
import hosted_selected_shard_play as selected

activation=readiness.activation
PREFIX=readiness.candidate.PREFIX
OWN_INPUTS=(PREFIX+'deployment/hosted_db_threadname_selected_play.py',
            PREFIX+'deployment/test_db_threadname_selected_play.py',
            PREFIX+'deployment/hosted_selected_shard_play.py',
            PREFIX+'deployment/windows/shard_play_probe.c')


def committed_inputs(root,commit):
    result=readiness.committed_runtime_inputs(root,commit)
    if (Path(__file__).resolve()!=root/OWN_INPUTS[0]
            or Path(selected.__file__).resolve()!=root/OWN_INPUTS[2]):
        raise ValueError('threadname_selected_executed_checkout')
    for name in OWN_INPUTS:
        try:raw=subprocess.check_output(['git','-C',str(root),'show',commit+':'+name],timeout=30,stderr=subprocess.PIPE)
        except subprocess.SubprocessError:raise ValueError('threadname_selected_source_not_owned_by_head') from None
        path=root/name
        if path.is_symlink() or path.read_bytes()!=raw:raise ValueError('threadname_selected_source_not_owned_by_head')
        result[name]=hashlib.sha256(raw).hexdigest()
    return result


def run(args):
    root,output=args.source_root.resolve(),args.output.resolve()
    activation.prior.require_hosted(root,output,args.expected_commit)
    inputs=committed_inputs(root,args.expected_commit)
    db=readiness.DbCandidate(root,args.db_candidate_stage,args.expected_db_receipt_sha256,args.expected_db_binary_sha256)
    generation=activation.DbCandidateGeneration(db.binary_sha256,db.receipt_pin)
    scope=selected.SelectedScope(args.retained_intact_stage.resolve(),args.send_cap,generation)
    activation.admit_selected_candidate(scope,db)
    value=activation.run(args,selected_scope=scope,db_candidate=db)
    # Common teardown has completed. Preserve independent original artifact
    # identity and exact current source ownership even on a protocol refusal.
    stable=False
    try:stable=db.verify()==db.admission and inputs==committed_inputs(root,args.expected_commit)
    except Exception:pass
    value['selected_candidate_and_source_inputs_unchanged']=stable
    value['selected_candidate_source_sha256']=inputs
    value['passed']=value['passed'] and stable
    if not stable:value['failure']='threadname_selected_candidate_or_source_changed'
    (output/'receipt.json').write_text(json.dumps(value,indent=2)+'\n')
    return value


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source-root','output','auth-success-archive','auth-candidate-stage','db-candidate-stage','retained-intact-stage'):
        parser.add_argument('--'+name,type=Path,required=True)
    for name in ('expected-commit','expected-db-receipt-sha256','expected-db-binary-sha256'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--send-cap',type=int,choices=(7,1024),default=1024)
    value=run(parser.parse_args())
    print(json.dumps({key:value.get(key) for key in ('passed','failure','original_interserver_shard_activation_verified',
        'selected_shard_play_verified','authenticated_db_map_handoff_verified')}))
    raise SystemExit(0 if value['passed'] else 1)
