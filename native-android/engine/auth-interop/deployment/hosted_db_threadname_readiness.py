#!/usr/bin/env python3
"""Disposable registration-only runner for an independently admitted new DB PE."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import hosted_db_shard_activation as activation
import hosted_db_threadname_candidate as candidate

HERE=Path(__file__).resolve().parent
RUNTIME_INPUTS=(candidate.PREFIX+'deployment/hosted_db_threadname_readiness.py',
 candidate.PREFIX+'deployment/test_db_threadname_readiness.py',
 candidate.PREFIX+'deployment/hosted_db_shard_activation.py')
GENERATED_TEXT={'candidate-manifest.json','threadname-manifest.json','checksum-failclosed.patch'}


def raw_artifact(directory,receipt_pin,binary_pin):
    raw=candidate.read_pinned(directory/'receipt.json',receipt_pin,1024*1024)
    value=json.loads(raw)
    if (not isinstance(value,dict) or not isinstance(value.get('files'),dict)
            or set(value['files'])!=candidate.FILES
            or {p.name for p in directory.iterdir()}!=candidate.FILES|{'receipt.json'}):
        raise ValueError('threadname_readiness_raw_artifact_inventory')
    total=0
    for name,record in value['files'].items():
        if not isinstance(record,dict) or set(record)!={'bytes','sha256'} or type(record['bytes']) is not int:
            raise ValueError('threadname_readiness_raw_artifact_record')
        body=candidate.read_pinned(directory/name,record['sha256'],8*1024*1024 if name==candidate.BINARY else candidate.base.prior.LOG_LIMIT)
        if len(body)!=record['bytes']:raise ValueError('threadname_readiness_raw_artifact_record')
        total+=len(body)
        if total>32*1024*1024:raise ValueError('threadname_readiness_raw_artifact_total')
    candidate.read_pinned(directory/candidate.BINARY,binary_pin,8*1024*1024)
    return value


def native_generated_text(raw):
    lf=raw.replace(b'\r\n',b'\n')
    if b'\r' in lf or raw not in (lf,lf.replace(b'\n',b'\r\n')):
        raise ValueError('threadname_readiness_generated_text_line_endings')
    return lf.replace(b'\n',os.linesep.encode('ascii'))


def admit_candidate(root,directory,receipt_pin,binary_pin):
    """Preserve raw identities; only regenerate a bounded metadata read view."""
    directory=Path(directory).resolve()
    value=raw_artifact(directory,receipt_pin,binary_pin)
    try:
        admitted=candidate.admit(root,directory,receipt_pin,binary_pin)
    except ValueError as error:
        if str(error)!='threadname_prepared_artifact_identity':raise
    else:
        return dict(admitted,generated_metadata_admission={'mode':'strict_native_artifact',
            'original_receipt_sha256':receipt_pin,'view_receipt_sha256':None,'changed_files':[],
            'original_build_receipt_replaced':False,'original_pe_sha256':binary_pin})
    # The unchanged builder writes exactly these three files with write_text.
    # A whole-file LF or CRLF representation is allowed; mixed/bare CR refuses.
    originals={name:candidate.read_pinned(directory/name,value['files'][name]['sha256'],1024*1024) for name in GENERATED_TEXT}
    replacements={name:native_generated_text(raw) for name,raw in originals.items()}
    changed=sorted(name for name,body in replacements.items() if body!=originals[name])
    if not changed:raise ValueError('threadname_readiness_no_generated_text_conversion')
    with tempfile.TemporaryDirectory(prefix='coh-threadname-metadata-admission-') as temporary:
        view=Path(temporary)
        # Recheck every original raw byte before constructing the view. No source,
        # source map, PE, policy proof, log or build input is transformed.
        if raw_artifact(directory,receipt_pin,binary_pin)!=value:raise ValueError('threadname_readiness_raw_artifact_changed')
        normalized=json.loads(json.dumps(value))
        for name in candidate.FILES:
            if name in replacements:
                body=replacements[name];(view/name).write_bytes(body)
                normalized['files'][name]={'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
            else:shutil.copyfile(directory/name,view/name)
        receipt=(json.dumps(normalized,indent=2)+'\n').encode()
        (view/'receipt.json').write_bytes(receipt);view_pin=hashlib.sha256(receipt).hexdigest()
        admitted=candidate.admit(root,view,view_pin,binary_pin)
    if view.exists():raise ValueError('threadname_readiness_metadata_view_cleanup')
    if raw_artifact(directory,receipt_pin,binary_pin)!=value:raise ValueError('threadname_readiness_raw_artifact_changed')
    # The normalized receipt is only a verification view, never a claim about
    # what the actual Windows build emitted. Always return the raw build pin.
    return dict(admitted,receipt_sha256=receipt_pin,generated_metadata_admission={
        'mode':'native_generated_metadata_view','original_receipt_sha256':receipt_pin,
        'view_receipt_sha256':view_pin,'changed_files':changed,'temporary_view_removed':True,
        'content_changes_other_than_line_endings':False,'original_build_receipt_replaced':False,
        'original_pe_sha256':binary_pin})


def committed_runtime_inputs(root,commit):
    if not isinstance(commit,str) or not re.fullmatch('[a-f0-9]{40}',commit):
        raise ValueError('threadname_readiness_expected_commit')
    if (Path(__file__).resolve()!=root/candidate.PREFIX/'deployment/hosted_db_threadname_readiness.py'
            or Path(activation.__file__).resolve()!=root/candidate.PREFIX/'deployment/hosted_db_shard_activation.py'):
        raise ValueError('threadname_readiness_executed_checkout')
    result={}
    for name in RUNTIME_INPUTS:
        try:raw=subprocess.check_output(['git','-C',str(root),'show',commit+':'+name],timeout=30,stderr=subprocess.PIPE)
        except subprocess.SubprocessError:raise ValueError('threadname_readiness_source_not_owned_by_head') from None
        path=root/name
        if path.is_symlink() or path.read_bytes()!=raw:raise ValueError('threadname_readiness_source_not_owned_by_head')
        result[name]=hashlib.sha256(raw).hexdigest()
    return result


class DbCandidate:
    binary_name=candidate.BINARY
    receipt_schema='coh-owned-mssql-db-threadname-readiness-v1'

    def __init__(self,root,directory,receipt_pin,binary_pin):
        if (not isinstance(receipt_pin,str) or not re.fullmatch('[a-f0-9]{64}',receipt_pin)
                or not isinstance(binary_pin,str) or not re.fullmatch('[a-f0-9]{64}',binary_pin)
                or binary_pin==candidate.OLD_BINARY_SHA):
            raise ValueError('threadname_readiness_new_candidate_pins')
        self.root,self.directory=root,Path(directory).resolve()
        self.receipt_pin,self.binary_sha256=receipt_pin,binary_pin
        self.admission=self.verify()

    def verify(self):
        value=admit_candidate(self.root,self.directory,self.receipt_pin,self.binary_sha256)
        receipt=json.loads(candidate.read_pinned(self.directory/'receipt.json',self.receipt_pin,1024*1024))
        return dict(value,build_repository_commit=receipt['repository_commit'],
                    build_source_map_sha256=receipt['source_file_map_sha256'])

    def recover(self,root,destination):
        if root!=self.root or destination.exists() or destination.is_symlink():
            raise ValueError('threadname_readiness_recovery_destination')
        if self.verify()!=self.admission:raise ValueError('threadname_readiness_candidate_changed')
        destination.mkdir()
        source=self.directory/self.binary_name
        shutil.copy2(source,destination/self.binary_name)
        candidate.read_pinned(destination/self.binary_name,self.binary_sha256,8*1024*1024)
        return dict(self.admission,separate_runtime_dlls_required=False,
                    platform_imports=sorted(candidate.PLATFORM_DLLS))


def run(args):
    root,output=args.source_root.resolve(),args.output.resolve()
    # Refuse local/uncommitted execution before any artifact staging or service.
    activation.prior.require_hosted(root,output,args.expected_commit)
    inputs=committed_runtime_inputs(root,args.expected_commit)
    scope=DbCandidate(root,args.db_candidate_stage,args.expected_db_receipt_sha256,args.expected_db_binary_sha256)
    value=activation.run(args,db_candidate=scope)
    # Candidate source/binary and wrapper ownership are checked again after all
    # common owned-service/SQL/firewall/private-file teardown has completed.
    stable=False
    try:stable=scope.verify()==scope.admission and inputs==committed_runtime_inputs(root,args.expected_commit)
    except Exception:pass
    value['new_candidate_and_readiness_inputs_unchanged']=stable
    value['readiness_source_sha256']=inputs
    value['passed']=value['passed'] and stable
    if not stable:value['failure']='threadname_readiness_candidate_or_source_changed'
    (output/'receipt.json').write_text(json.dumps(value,indent=2)+'\n')
    return value


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source-root','output','auth-success-archive','auth-candidate-stage','db-candidate-stage'):
        parser.add_argument('--'+name,type=Path,required=True)
    for name in ('expected-commit','expected-db-receipt-sha256','expected-db-binary-sha256'):
        parser.add_argument('--'+name,required=True)
    value=run(parser.parse_args())
    print(json.dumps({key:value.get(key) for key in ('passed','failure','original_interserver_shard_activation_verified',
        'selected_shard_play_verified','authenticated_db_map_handoff_verified')}))
    raise SystemExit(0 if value['passed'] else 1)
