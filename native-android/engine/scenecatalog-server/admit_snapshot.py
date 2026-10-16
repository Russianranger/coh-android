#!/usr/bin/env python3
"""Admit the same-workflow snapshot compile artifact, never an installed runtime."""
import argparse
import json
from pathlib import Path
import re
import delivery as d
import stage_snapshot as stage


def inspect(source,root,revision):
    source=d.path(source);root=d.path(root)
    d.require(re.fullmatch('[0-9a-f]{40}',revision),'SOURCE_REVISION')
    receipt=d.json_object(d.read(source/'compile-only-receipt.json',8*1024**2))
    d.require(receipt.get('schema')=='coh-runtime-snapshot-compile-v1' and receipt.get('passed') is True and
        receipt.get('source_revision')==revision and receipt.get('source_git_status_porcelain')==[] and
        receipt.get('build_role')==stage.ROLE and receipt.get('compile_only') is True and
        receipt.get('runtime_executed') is False and receipt.get('source_stage_verified') is True and
        receipt.get('published_inputs_reverified') is True,'COMPILE_SCOPE')
    expected={'MapServer.exe','CMakeCache.txt',stage.RECEIPT,stage.PRIOR,'map-startup-inputs.json',
        *('source/'+n for n in (stage.base.GROUP,stage.base.INIT,*stage.overlays(root)))}
    d.require(set(receipt['artifacts'])==expected,'ARTIFACT_NAMES')
    d.require({p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}==expected|{'compile-only-receipt.json'},'EXTRA_FILES')
    for name,record in receipt['artifacts'].items():
        size,digest=d.hash_file(source/name,16*1024**2)
        d.require(record=={'bytes':size,'sha256':digest},'ARTIFACT_HASH')
    declared=d.json_object(d.read(source/stage.RECEIPT,8*1024**2))
    prior=d.json_object(d.read(source/stage.PRIOR,8*1024**2))
    d.require(stage.base.json_equal(prior,stage.base.expected_prior(root,prior)),'PRIOR_SOURCE')
    group=d.read(source/('source/'+stage.base.GROUP),2*1024**2)
    init=d.read(source/('source/'+stage.base.INIT),2*1024**2)
    tail=stage.base.restore_newlines(stage.base.TAIL+stage.TAIL,group)
    d.require(group.endswith(tail),'STAGED_TAIL')
    text=stage.base.lf(init)
    d.require(text.count(stage.NEW)==2 and stage.OLD not in text,'STAGED_HOOK')
    text=text.replace(stage.NEW,stage.OLD)
    original={stage.base.GROUP:group[:-len(tail)],stage.base.INIT:stage.base.restore_newlines(text.replace(stage.base.HOOK,b'',1).replace(stage.base.PROTOTYPE,b'',1),init)}
    output=stage.transform(original[stage.base.GROUP],original[stage.base.INIT])
    d.require(output=={stage.base.GROUP:group,stage.base.INIT:init} and
        stage.base.json_equal(declared,stage.expected(root,prior,original,output)),'STAGED_SOURCE')
    inherited=stage.base.inherited_hashes(prior)
    for name,raw in original.items():
        if name in inherited:d.require(stage.base.sha(raw)==inherited[name],'INHERITED_SOURCE')
    for name,raw in stage.overlays(root).items():d.require(d.read(source/('source/'+name),1024**2)==raw,'OVERLAY_SOURCE')
    return receipt,declared


def admit(source,root,revision,output):
    receipt,stage_receipt=inspect(source,root,revision)
    output=d.absent_directory(output);output.mkdir(mode=0o700)
    d.copy_verified(Path(source)/'MapServer.exe',output/'MapServer.exe',receipt['artifacts']['MapServer.exe']['sha256'],16*1024**2)
    for name in ('compile-only-receipt.json',stage.RECEIPT):
        size,digest=d.hash_file(Path(source)/name,8*1024**2);d.copy_verified(Path(source)/name,output/name,digest,size)
    plan={'schema':'coh-runtime-snapshot-candidate-v1','source_revision':revision,
        'binary':receipt['artifacts']['MapServer.exe'],'compile_receipt_sha256':d.hash_file(output/'compile-only-receipt.json',8*1024**2)[1],
        'stage_receipt_sha256':d.hash_file(output/stage.RECEIPT,8*1024**2)[1],
        'source_snapshot_only':True,'runtime_executed':False,'accepted_runtime_modified':False,
        'catalog_producer_sha256':stage_receipt['overlay_sha256'][stage.base.EXPORT]}
    d.emit_json(output/'deployment-plan.json',plan);return plan


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('compile-directory','source-root','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--source-revision',required=True);a=p.parse_args()
    print(json.dumps(admit(a.compile_directory,a.source_root,a.source_revision,a.output)))
if __name__=='__main__':main()
