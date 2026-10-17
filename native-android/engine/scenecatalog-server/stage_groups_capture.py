#!/usr/bin/env python3
"""Stage an explicit private live GROUPS observation role; never execute it.

Apply to the same qualified prepare_map_startup_source private tree used by the
existing catalog/resource build. Source PE, run, process and actual native receive
association remain required outside this source transformation.
"""
import argparse
import json
from pathlib import Path
import stage_export as base
import stage_groups_boundary as boundary
import stage_resources as resources

HERE=Path(__file__).resolve().parent
ROLE='nonshipping_actual_world_send_update_transaction_capture'
RECEIPT='native-groups-transaction-server-build-input.json'
PRIOR=base.PRIOR
GUARD=resources.GUARD
GUARD_IMPL=resources.GUARD_IMPL
SINK='MapServer/src/group/coh_source_groups_capture_sink.inc'
PATCHED=(base.GROUP,base.INIT,GUARD)
CALL=b'coh_source_groups_capture_install'
TAIL=b'\n/* NONSHIPPING opt-in actual source transaction sink. */\n#include "coh_source_catalog_sink.inc"\n#include "coh_source_groups_capture_sink.inc"\n'
CONTRACT={
 'role':ROLE,'nonshipping':True,'shipping_executable':False,
 'disabled_without_explicit_output':True,
 'output_environment':'COH_NATIVE_GROUPS_TRANSACTION_OUTPUT',
 'installation':'normal_map_startup_after_groupLoadMap_dbSetupMap_before_dbReadyForPlayers',
 'observation':'actual_same_installation_thread_worldSendUpdate_full_update_registered_owner',
 'one_open_attempt_per_process':True,
 'actual_quiet_guard_and_folder_callback_checks_required':True,
 'owner_catalog_snapshot_resources_raw_bounds_eligibility_packet_same_boundary':True,
 'streamed_envelope':'COHGTX01','maximum_envelope_bytes':160*1024**2,
 'commit_after_successful_actual_quiet_release':True,
 'create_new_partial_flush_close_rename_without_replace':True,
 'private_exclusively_owned_stable_parent_required':True,
 'source_run_pe_identity_and_actual_native_receive_admission_required':True,
 'hard_process_heap_cap_established':False,'live_groups_captured':False,
 'client_materials_available':False,'client_lods_available':False,
 'source_generation_admitted':False,'world_authority':False,
 'runtime_executed':False,'android_executed':False,'apk_changed':False,
}

def overlays(root):
 return {base.SINK:base.lf((HERE/'source_sink.inc').read_bytes()),
         SINK:base.lf((HERE/'source_groups_capture_sink.inc').read_bytes()),
         GUARD_IMPL:base.lf((HERE/'source_resource_quiescence.inc').read_bytes())}

def transform(group,init,anim):
 # Reuse exact existing init anchoring and its qualified newline preservation.
 inherited=base.transform(group,init)
 text=base.lf(inherited[base.INIT])
 base.require(text.count(b'coh_source_catalog_export_startup')==2,'GROUPS_INIT_HOOK')
 text=text.replace(b'coh_source_catalog_export_startup',CALL)
 expected=json.loads((HERE/'resource-source-pins.json').read_text())['sha256_lf'][GUARD]
 base.require(base.sha(base.lf(anim))==expected,'GROUPS_ANIM_SOURCE')
 staged=boundary.stage(base.lf(group).decode('utf-8')).encode('utf-8')
 return {base.GROUP:base.restore_newlines(staged+TAIL,group),
         base.INIT:base.restore_newlines(text,init),
         GUARD:anim+base.restore_newlines(resources.GUARD_TAIL,anim)}

def expected(root,prior,original,output):
 # All inline boundary suppliers are included in the actual staged-source hash;
 # retain their individual bytes too, so consumers can audit the producer chain.
 dependencies={str(p.relative_to(HERE.parent.parent.parent)):base.sha(base.lf(p.read_bytes()))
               for p in (*boundary.OVERLAYS,HERE/'stage_groups_boundary.py')}
 return {'schema_version':1,'build_role':ROLE,'build_targets':['MapServer'],
         'prior_build_input':prior,'prior_build_input_canonical_sha256':base.canonical(prior),
         'source_sha256':{n:base.sha(raw) for n,raw in original.items()},
         'patched_sha256':{n:base.sha(raw) for n,raw in output.items()},
         'overlay_sha256':{n:base.sha(raw) for n,raw in overlays(root).items()},
         'inline_producer_sha256':dependencies,
         'stager_sha256':base.sha(Path(__file__).read_bytes()),
         'contract':dict(CONTRACT),'runtime_validation':'not_executed_compile_only'}

def prepare(root,stage):
 root,stage=base.private_stage(root,stage);prior=base.validate_prior(root,stage)
 originals={n:base.regular(stage/n).read_bytes() for n in PATCHED}
 output=transform(originals[base.GROUP],originals[base.INIT],originals[GUARD]);extra=overlays(root)
 receipt=expected(root,prior,originals,output)
 base.require(not (stage/RECEIPT).exists(),'GROUPS_RECEIPT_EXISTS')
 for name in extra:base.require(not (stage/name).exists(),'GROUPS_OVERLAY_EXISTS')
 created=[];changed=[]
 try:
  for name,raw in extra.items():
   with (stage/name).open('xb') as stream:created.append(stage/name);stream.write(raw)
  for name,raw in output.items():changed.append(name);(stage/name).write_bytes(raw)
  with (stage/RECEIPT).open('x') as stream:created.append(stage/RECEIPT);json.dump(receipt,stream,indent=2);stream.write('\n')
 except OSError:
  for name in changed:(stage/name).write_bytes(originals[name])
  for path in reversed(created):path.unlink()
  raise
 return receipt

def verify_staged(root,stage):
 root,stage=base.private_stage(root,stage);prior=base.read_json(stage/PRIOR)
 base.require(base.json_equal(prior,base.expected_prior(root,prior)),'GROUPS_PRIOR')
 group=base.regular(stage/base.GROUP).read_bytes();init=base.regular(stage/base.INIT).read_bytes();anim=base.regular(stage/GUARD).read_bytes()
 text=base.lf(init)
 base.require(text.count(CALL)==2 and b'coh_source_catalog_export_startup' not in text,'GROUPS_INSTALL_HOOK')
 text=text.replace(CALL,b'coh_source_catalog_export_startup')
 base.require(text.count(base.HOOK)==1 and text.count(base.PROTOTYPE)==1,'GROUPS_INIT_ANCHORS')
 guard=base.restore_newlines(resources.GUARD_TAIL,anim)
 base.require(anim.endswith(guard),'GROUPS_GUARD_TAIL')
 originals={base.GROUP:base.regular(root/'upstream/ouroboros'/base.GROUP).read_bytes(),
            base.INIT:base.restore_newlines(text.replace(base.HOOK,b'',1).replace(base.PROTOTYPE,b'',1),init),GUARD:anim[:-len(guard)]}
 # A Windows working tree may use CRLF although the reference checkout uses LF.
 originals[base.GROUP]=base.restore_newlines(base.lf(originals[base.GROUP]),group)
 output=transform(originals[base.GROUP],originals[base.INIT],originals[GUARD]);receipt=expected(root,prior,originals,output)
 base.require(output=={base.GROUP:group,base.INIT:init,GUARD:anim} and base.json_equal(base.read_json(stage/RECEIPT),receipt),'GROUPS_RECEIPT')
 for name,digest in base.inherited_hashes(prior).items():
  raw=originals[name] if name in originals else base.regular(stage/name).read_bytes()
  base.require(base.sha(raw)==digest,'GROUPS_INHERITED')
 for name,raw in overlays(root).items():base.require(base.regular(stage/name).read_bytes()==raw,'GROUPS_OVERLAY')
 return receipt

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--already-staged',type=Path,required=True);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
 receipt=(verify_staged if args.verify else prepare)(args.source_root,args.already_staged)
 print(json.dumps({'passed':True,'build_role':receipt['build_role'],'runtime_executed':False,'receipt':RECEIPT}))
if __name__=='__main__':main()
