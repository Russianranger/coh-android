#!/usr/bin/env python3
"""Stage a separate, explicit nonshipping startup snapshot role; never execute."""
import argparse
import json
from pathlib import Path
import stage_export as base

HERE = Path(__file__).resolve().parent
PRIOR = base.PRIOR
RECEIPT = 'native-runtime-snapshot-server-build-input.json'
ROLE = 'nonshipping_startup_catalog_and_runtime_snapshot'
PRODUCER = 'MapServer/src/group/coh_source_runtime_snapshot.inc'
SINK = 'MapServer/src/group/coh_source_runtime_snapshot_sink.inc'
TAIL = b'\n/* NONSHIPPING: coherent source snapshot, never client authority. */\n#include "coh_source_runtime_snapshot.inc"\n#include "coh_source_runtime_snapshot_sink.inc"\n'
OLD = b'coh_source_catalog_export_startup'
NEW = b'coh_source_runtime_snapshot_startup'
CONTRACT = dict(base.CONTRACT, role=ROLE, catalog_and_sidecar_same_owner_callback=True,
    source_snapshot_only=True, live_groups_transaction=False,
    sidecar_output_environment='COH_NATIVE_RUNTIME_SNAPSHOT_OUTPUT',
    maximum_sidecar_bytes=16*1024**2, maximum_external_objects=64,
    scratch_bounds_lookup_only=True, no_lazy_load=True, accepted_exporter_unchanged=True)


def overlays(root):
    return {**base.overlay_bytes(root), PRODUCER:base.lf((HERE/'source_snapshot.inc').read_bytes()),
            SINK:base.lf((HERE/'source_snapshot_sink.inc').read_bytes())}


def transform(original_group, original_init):
    output = base.transform(original_group, original_init)
    output[base.GROUP] += base.restore_newlines(TAIL, original_group)
    base.require(output[base.INIT].count(OLD) == 2, 'SNAPSHOT_HOOK')
    output[base.INIT] = output[base.INIT].replace(OLD, NEW)
    return output


def expected(root, prior, original, output):
    return {'schema_version':1,'build_role':ROLE,'build_targets':['MapServer'],
        'prior_build_input':prior,'prior_build_input_canonical_sha256':base.canonical(prior),
        'source_sha256':{n:base.sha(raw) for n,raw in original.items()},
        'patched_sha256':{n:base.sha(raw) for n,raw in output.items()},
        'overlay_sha256':{n:base.sha(raw) for n,raw in overlays(root).items()},
        'stager_sha256':base.sha(Path(__file__).read_bytes()),
        'reused_catalog_stager_sha256':base.sha(Path(base.__file__).read_bytes()),
        'contract':CONTRACT,'runtime_validation':'not_executed_compile_only'}


def prepare(root, stage):
    root,stage=base.private_stage(root,stage)
    prior=base.validate_prior(root,stage)
    originals={n:base.regular(stage/n).read_bytes() for n in (base.GROUP,base.INIT)}
    output=transform(originals[base.GROUP],originals[base.INIT]); extra=overlays(root)
    receipt=expected(root,prior,originals,output)
    base.require(not (stage/RECEIPT).exists(), 'SNAPSHOT_EXISTS')
    for n in extra: base.require(not (stage/n).exists(), 'SNAPSHOT_OVERLAY_EXISTS')
    created=[]; changed=[]
    try:
        for n,raw in extra.items():
            with (stage/n).open('xb') as stream: created.append(stage/n); stream.write(raw)
        for n,raw in output.items(): changed.append(n);(stage/n).write_bytes(raw)
        with (stage/RECEIPT).open('x') as stream: created.append(stage/RECEIPT);json.dump(receipt,stream,indent=2);stream.write('\n')
    except OSError:
        for n in changed:(stage/n).write_bytes(originals[n])
        for p in reversed(created):p.unlink()
        raise
    return receipt


def verify_staged(root, stage):
    root,stage=base.private_stage(root,stage)
    prior=base.read_json(stage/PRIOR)
    base.require(base.json_equal(prior,base.expected_prior(root,prior)), 'SNAPSHOT_PRIOR')
    group=base.regular(stage/base.GROUP).read_bytes(); init=base.regular(stage/base.INIT).read_bytes()
    combined=base.restore_newlines(base.TAIL+TAIL,group)
    base.require(group.endswith(combined), 'SNAPSHOT_TAIL')
    text=base.lf(init)
    base.require(text.count(NEW)==2 and OLD not in text, 'SNAPSHOT_HOOK')
    text=text.replace(NEW,OLD)
    base.require(text.count(base.HOOK)==1 and text.count(base.PROTOTYPE)==1,'SNAPSHOT_ANCHOR')
    original={base.GROUP:group[:-len(combined)],base.INIT:base.restore_newlines(text.replace(base.HOOK,b'',1).replace(base.PROTOTYPE,b'',1),init)}
    output=transform(original[base.GROUP],original[base.INIT]); receipt=expected(root,prior,original,output)
    base.require(output=={base.GROUP:group,base.INIT:init} and base.json_equal(base.read_json(stage/RECEIPT),receipt),'SNAPSHOT_RECEIPT')
    for n,sha in base.inherited_hashes(prior).items():
        raw=original[n] if n in original else base.regular(stage/n).read_bytes()
        base.require(base.sha(raw)==sha,'SNAPSHOT_INHERITED')
    for n,raw in overlays(root).items():base.require(base.regular(stage/n).read_bytes()==raw,'SNAPSHOT_OVERLAY')
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--already-staged',type=Path,required=True);p.add_argument('--verify',action='store_true');a=p.parse_args()
    receipt=(verify_staged if a.verify else prepare)(a.source_root,a.already_staged)
    print(json.dumps({'passed':True,'build_role':receipt['build_role'],'runtime_executed':False,'receipt':RECEIPT}))
if __name__=='__main__':main()
