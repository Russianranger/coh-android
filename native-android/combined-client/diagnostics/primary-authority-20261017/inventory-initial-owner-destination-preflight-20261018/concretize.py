#!/usr/bin/env python3
"""Bind two metadata constants and existing evidence maps; execute no helper."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('/workspace/scratch/7ed1da2a7e55/coh-android')
D = 'native-android/combined-client/diagnostics/primary-authority-20261017/inventory-initial-owner-destination-preflight-20261018/'
H = 'native-android/combined-client/tools/admit_initial_inventory_receiver.py'
T = 'native-android/combined-client/tools/test_admit_initial_inventory_receiver.py'
M = 'native-android/engine/scenecatalog-server/evidence/fresh-callback-profile-20261018/compile-initial-owner-20261018/'
RECEIPT_SHA = '28d61fc30718391fc5dd1a269f468b0f2aa83c33abe5d60413104dafd0b28f91'
PENDING_SHA = '99f47dd7d3e6e9a0475a83d498a7c3318bcfc1e40c9140d89948c28942e4c553'
TEST_SHA = '897488f2cdfbb4614966c344fb9dde562c6093dc0c9d31e8616534925d849336'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def need(ok, code):
    if not ok:
        raise ValueError(code)

def pinned(name, digest=None):
    p = ROOT / name
    b = p.read_bytes()
    need(p.resolve() == p and not p.is_symlink() and p.is_file(), 'CANONICAL_INPUT')
    need(subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+name]) == b, 'CURRENT_GIT_INPUT:'+name)
    need(digest is None or sha(b) == digest, 'FIXED_INPUT:'+name)
    return b

def main():
    before = subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip()
    source = pinned(H, PENDING_SHA)
    need(source == pinned(D+'source/admit_initial_inventory_receiver.py', PENDING_SHA), 'PENDING_SOURCE_COPY')
    pinned(T, TEST_SHA)
    mock_raw = pinned(D+'mocked-controls-pending-source.json','26aea5a5d5177b572d33ed49eef12d7eb7d18b456b020a68faa3df93e7d59324')
    data_raw = pinned(D+'pending-source-data.json','168dfaf9295d31c8f732a3598ee91945797d55275d94b11bb0cb367377cba059')
    data = json.loads(data_raw)
    receipt_raw = pinned(M+'compile-only-receipt.json', RECEIPT_SHA)
    need(len(receipt_raw) == 3796, 'ACTUAL_RECEIPT_BYTES')
    a_raw = pinned(M+'admission.json','2569696ad525cdf2e5eefc5b896152795a21b06145e0251aecc4aba694df9b06')
    a = json.loads(a_raw)
    need(a['schema'] == 'coh-fresh-initial-owner-map-compile-admission-v1' and a['passed'] is True and
         a['strict_cli_invocations'] == 1 and a['strict_cli_passed'] is True and a['strict_cli_stderr_empty'] is True and
         a['strict_linux_admission_passed'] is True and a['run_id'] == 39099315295 and a['job_id'] == 117592138887 and
         a['artifact_id'] == 12125997958 and a['source_revision'] == 'd9adf2b431a039357f8bfe878d3d0da991a81b19' and
         a['runtime_executed'] is False and a['world_authority'] is False and
         set(a['changed_local6']) == {'stage.py','source_group_profile.inc','source_group_profile_api.h'}, 'ACTUAL_MAP_ADMISSION')
    pins = dict(data['evidence_artifact_sha256'])
    mapping = data['current_receiver_dependencies_sha256']
    need(len(pins) == 143 and len(mapping) == 46 and
         pins[M+'compile-only-receipt.json'] == data['mock_observer_receipt_sha256'], 'ONE_MOCK_PIN')
    pins[M+'compile-only-receipt.json'] = RECEIPT_SHA
    for name, digest in {**pins, **mapping, **data['admit_gate_additional_artifact_sha256']}.items():
        pinned(name, digest)
    replacements = {'OBSERVER_BUILD_SHA':RECEIPT_SHA,'OBSERVER_BUILD_BYTES':len(receipt_raw)}
    old_tree = ast.parse(source)
    lines = source.decode().splitlines(keepends=True)
    changed = []
    for node in old_tree.body:
        if isinstance(node,ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in replacements:
            name = node.targets[0].id
            need(node.lineno == node.end_lineno, 'SINGLE_LINE_CONSTANT')
            lines[node.lineno-1] = name+' = '+repr(replacements[name])+'\n'
            changed.append(name)
    final = ''.join(lines).encode()
    expected = copy.deepcopy(old_tree)
    for node in expected.body:
        if isinstance(node,ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in replacements:
            node.value = ast.Constant(replacements[node.targets[0].id])
    need(changed == list(replacements) and ast.dump(expected,include_attributes=False) == ast.dump(ast.parse(final),include_attributes=False), 'ONLY_TWO_AST_CONSTANTS')
    need(subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip() == before, 'HEAD_CHANGED')
    output = ROOT / D / 'binding.json'
    need(not output.exists(), 'FRESH_BINDING')
    binding = {'schema':'coh-inventory-initial-owner-destination-preflight-actual-metadata-binding-v1','passed':True,
      'source_revision_before_binding':before,'pending_helper_sha256':PENDING_SHA,'pending_helper_bytes':len(source),
      'final_helper':H,'final_helper_sha256':sha(final),'final_helper_bytes':len(final),
      'test_file':T,'test_sha256':TEST_SHA,'mocked_proof_sha256':sha(mock_raw),'mocked_proof_path':D+'mocked-controls-pending-source.json',
      'pending_data_path':D+'pending-source-data.json','pending_data_sha256':sha(data_raw),
      'exact_AST_changes':list(replacements),'other_AST_equal':True,
      'current_receiver_dependency_count':46,'current_receiver_dependencies_sha256':mapping,
      'evidence_artifact_pin_count':143,'evidence_artifact_sha256':pins,
      'admit_gate_additional_artifact_sha256':data['admit_gate_additional_artifact_sha256'],
      'actual_Map_compile_receipt':{'path':M+'compile-only-receipt.json','bytes':len(receipt_raw),'sha256':RECEIPT_SHA},
      'actual_Map_independent_admission':{'path':M+'admission.json','bytes':len(a_raw),'sha256':sha(a_raw)},
      'original_mock_execution_reused':True,'supplemental_maps_are_data_derivation_not_serialized_positive_returns':True,
      'all_current_artifact_and_consumer_pins_rehashed_and_Git_equal':True,
      'destination_platform_qualified':False,'destination_helper_or_loader_or_native_executed':False,
      'Git_read_only_subprocesses_executed':True,'mock_controls_reexecuted':False,'runtime_executed':False,
      'source_generation_admitted':False,'world_authority':False}
    (ROOT/H).write_bytes(final)
    output.write_text(json.dumps(binding,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'final_helper_sha256':sha(final),'final_helper_bytes':len(final),'binding_bytes':output.stat().st_size,'binding_sha256':sha(output.read_bytes()),'current46':len(mapping),'artifact143':len(pins)}))

if __name__ == '__main__':
    main()
