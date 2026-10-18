#!/usr/bin/env python3
"""Verify exact independently pinned original GROUPS observer compile output.

No installation, process or source-generation authority follows from this check.
"""
from pathlib import Path
import argparse,json
import delivery as d
import stage_groups_capture as stage

def portable_declared(value):
 # The original producer stager serializes str(Path), hence actual Win32 keys
 # use backslashes. Canonicalize this one metadata field for byte-equivalent
 # cross-host reconstruction; preserve actual receipt bytes and digest untouched.
 result=dict(value);inline=value.get('inline_producer_sha256');d.require(type(inline) is dict,'INLINE_SOURCE_FIELDS');normalized={}
 for name,digest in inline.items():
  d.require(type(name) is str and ('\\' not in name or '/' not in name),'INLINE_SOURCE_PATH');name=name.replace('\\','/')
  d.require(name not in normalized,'INLINE_SOURCE_DUPLICATE');normalized[name]=digest
 result['inline_producer_sha256']=normalized;return result

def inspect(source,root,receipt_sha256):
 source=d.path(source);root=d.path(root);d.sha(receipt_sha256)
 d.require(d.hash_file(source/'compile-only-receipt.json',8*1024**2)[1]==receipt_sha256,'COMPILE_RECEIPT_PIN')
 receipt=d.json_object(d.read(source/'compile-only-receipt.json',8*1024**2))
 # Exactly one separately identified fresh diagnostic role is admitted by its
 # own validator. The independently pinned old role retains its unchanged path.
 if receipt.get('schema')=='coh-fresh-groups-observer-compile-v1':
  from fresh_callback_observer import admit_compile as fresh
  return fresh.inspect(source,root,receipt_sha256)
 d.require(receipt.get('schema')=='coh-groups-transaction-compile-v1' and receipt.get('passed') is True and
           receipt.get('source_git_status_porcelain')==[] and receipt.get('build_role')==stage.ROLE and
           receipt.get('compile_only') is True and receipt.get('runtime_executed') is False and
           receipt.get('source_stage_verified') is True and receipt.get('published_inputs_reverified') is True and
           receipt.get('platform')=='Win32' and receipt.get('pe_machine')=='i386','COMPILE_SCOPE')
 expected={'MapServer.exe','CMakeCache.txt',stage.RECEIPT,stage.PRIOR,'map-startup-inputs.json',*('source/'+name for name in (*stage.PATCHED,*stage.overlays(root)))}
 d.require(set(receipt.get('artifacts',{}))==expected,'ARTIFACT_NAMES')
 for name,record in receipt['artifacts'].items():
  size,digest=d.hash_file(source/name,16*1024**2);d.require(record=={'bytes':size,'sha256':digest},'ARTIFACT_HASH')
 declared=d.json_object(d.read(source/stage.RECEIPT,8*1024**2));prior=d.json_object(d.read(source/stage.PRIOR,8*1024**2))
 d.require(stage.base.json_equal(prior,stage.base.expected_prior(root,prior)),'PRIOR_SOURCE')
 group=d.read(source/('source/'+stage.base.GROUP),2*1024**2);init=d.read(source/('source/'+stage.base.INIT),2*1024**2);anim=d.read(source/('source/'+stage.GUARD),2*1024**2)
 text=stage.base.lf(init);d.require(text.count(stage.CALL)==2 and b'coh_source_catalog_export_startup' not in text,'INSTALL_HOOK');text=text.replace(stage.CALL,b'coh_source_catalog_export_startup')
 d.require(text.count(stage.base.HOOK)==1 and text.count(stage.base.PROTOTYPE)==1,'INIT_ANCHORS')
 guard=stage.base.restore_newlines(stage.resources.GUARD_TAIL,anim);d.require(anim.endswith(guard),'QUIET_GUARD')
 original={stage.base.GROUP:stage.base.restore_newlines(stage.base.lf(d.read(root/'upstream/ouroboros'/stage.base.GROUP,2*1024**2)),group),
           stage.base.INIT:stage.base.restore_newlines(text.replace(stage.base.HOOK,b'',1).replace(stage.base.PROTOTYPE,b'',1),init),stage.GUARD:anim[:-len(guard)]}
 output=stage.transform(original[stage.base.GROUP],original[stage.base.INIT],original[stage.GUARD])
 d.require(output=={stage.base.GROUP:group,stage.base.INIT:init,stage.GUARD:anim} and stage.base.json_equal(portable_declared(declared),portable_declared(stage.expected(root,prior,original,output))),'STAGED_SOURCE')
 for name,digest in stage.base.inherited_hashes(prior).items():
  if name in original:d.require(stage.base.sha(original[name])==digest,'INHERITED_SOURCE')
 for name,raw in stage.overlays(root).items():d.require(d.read(source/('source/'+name),1024**2)==raw,'OVERLAY_SOURCE')
 return receipt,declared

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--compile-directory',type=Path,required=True);parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--compile-receipt-sha256',required=True);args=parser.parse_args()
 receipt,_=inspect(args.compile_directory,args.source_root,args.compile_receipt_sha256)
 print(json.dumps({'passed':True,'source_revision':receipt['source_revision'],'binary':receipt['artifacts']['MapServer.exe'],'runtime_executed':False}))
if __name__=='__main__':main()
