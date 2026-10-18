#!/usr/bin/env python3
"""Scratch-only successor of the reviewed owner-reason scene generator.

All inputs are committed bytes or JSON. No project module is imported. Final
rendering requires the actual admitted new Map metadata and concretized helper.

Required map-metadata schema: coh-inventory-initial-owner-scene-map-input-v1.
Fields: passed, actual_source_and_PE_admitted, runtime_executed, run_id,
artifact_id, source_revision, artifact_name, canonical_directory, archive_path,
archive_bytes, archive_sha256, receipt_path, receipt_bytes, receipt_sha256,
source_admission_path, strict_admission_path, retained_files,
independent_review_files. The last two maps use repository paths and
{bytes,sha256}; retained_files contains exactly ten files, including the archive.

Required helper-review fields: passed, helper_sha256, binding_sha256,
test_sha256, current_receiver_dependencies_sha256, evidence_artifact_sha256.
The coordinator supplies its committed path; the review is not its own input.
"""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import pprint
import re
import subprocess
import yaml

BASE_REVISION = '2b5dac5ac81d49359b47fd7027747b2c86f2d0db'
WORKFLOW = '.github/workflows/native-fresh-groups-observation.yml'
BASE_SHA = '919934db659c237f3af4e1679edc880052927fa03c70c9ec763dfb9046c4a71a'
BASE_GENERATOR = 'native-android/combined-client/diagnostics/primary-authority-20261017/owner-reason-scene-workflow-20261018/generate.py'
BASE_GENERATOR_SHA = '8cab092c82639097cd116c8abafa3e2ecfd62c1c1705b17ad36c42112c2b7ca7'
HELPER = 'native-android/combined-client/tools/admit_initial_inventory_receiver.py'
TEST = 'native-android/combined-client/tools/test_admit_initial_inventory_receiver.py'
PENDING_HELPER_SHA = '99f47dd7d3e6e9a0475a83d498a7c3318bcfc1e40c9140d89948c28942e4c553'
PENDING_REVISION = '271b70d935eea41d7243d941fa9adfe04949d7fd'
PROFILE = 'native-android/engine/scenecatalog-server/evidence/fresh-callback-profile-20261018/'
FOLLOWUP = PROFILE + 'initial-owner-followup.json'
FOLLOWUP_SHA = '550d600596e2939f73de076fac5fce859ce18248a0866e1b1d19795393dc03fb'
F_INITIAL = 'native-android/combined-client/diagnostics/continuation-f-20261017/fresh-initial-owner-source-review-20261018/review.json'
F_INITIAL_SHA = 'e68610a2a511db9171572a5d0b05bca1b74f2bf3c488dee4a17ff2a2c5471f7e'
BUILD_WORKFLOW = '.github/workflows/native-fresh-groups-build.yml'
BUILD_OLD_SHA = 'a2adda1b06a824fa58bf5d36335fa060e360edbf25d6860a8e2148e10a87e851'
BUILD_NEW_SHA = 'fb80fc0e14001056888e951eb378d71d56efa24058439e832076234bbed9b7b3'
CURRENT_MAP_SHA = '0c144dbb754959267b73902832b988468f34b4324393803450c3b9d28dce39b3'
RECEIVER_RAW_SHA = '09320ce3c78ccbf9af46de9b09c7bd1f551375fad39dc4e2b44eb3e962779216'
RECEIVER_ELF_SHA = '66f92ff8574c538ad221e1bcbbff834b80eddb54aa270b95ed607e7049a6dccc'
MAP_SCHEMA = 'coh-inventory-initial-owner-scene-map-input-v1'
BINDING_SCHEMA = 'coh-inventory-initial-owner-destination-preflight-actual-metadata-binding-v1'
HELPER_REVIEW_SCHEMA = 'coh-f-inventory-initial-owner-receiver-actual-binding-review-v1'


def need(ok, code):
    if not ok:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(root, revision, name):
    return subprocess.check_output(['git', '-C', root, 'show', revision + ':' + name])


def admitted(root, name, expected=None):
    relative = Path(name)
    need(isinstance(name, str) and not relative.is_absolute() and
         relative.as_posix() == name and all(p not in ('', '.', '..') for p in name.split('/')) and
         chr(92) not in name and ':' not in name, 'RELATIVE_INPUT')
    path = root / name
    need(path.resolve() == path and path.is_file() and not path.is_symlink(), 'CANONICAL_INPUT:' + name)
    raw = path.read_bytes()
    need(git(root, 'HEAD', name) == raw, 'COMMITTED_INPUT:' + name)
    need(expected is None or sha(raw) == expected, 'FIXED_INPUT:' + name)
    return raw


def load(root, name, expected=None):
    return json.loads(admitted(root, name, expected))


def merge(pins, more, label):
    for name, digest in more.items():
        need(name not in pins or pins[name] == digest, 'UNQUALIFIED_CONFLICT:' + label + ':' + name)
        pins[name] = digest


def literals(raw):
    result = {}
    def value(node):
        try:
            return ast.literal_eval(node)
        except (ValueError, TypeError):
            if isinstance(node, ast.Name) and node.id in result:
                return result[node.id]
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                left, right = value(node.left), value(node.right)
                if isinstance(left, str) and isinstance(right, str):
                    return left + right
            raise ValueError('NONLITERAL_CONSTANT')
    for node in ast.parse(raw).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                result[node.targets[0].id] = value(node.value)
            except (ValueError, TypeError):
                pass
    return result


def prior_pins(raw):
    workflow = yaml.safe_load(raw)
    code = '\n'.join(next(iter(workflow['jobs'].values()))['steps'][1]['run'].splitlines()[1:-1])
    pins = literals(code)['pins']
    need(len(pins) == 394 and WORKFLOW not in pins, 'EXACT_394_BASELINE')
    return workflow, pins


def replace_pin(pins, changes, name, old, new, proof):
    need(pins.get(name) == old and old != new, 'EXACT_QUALIFIED_PREDECESSOR:' + name)
    pins[name] = new
    changes[name] = {'previous_sha256': old, 'sha256': new, 'proof': proof}


def exact_two_constants(pending, final):
    old, new = ast.parse(pending), ast.parse(final)
    names = ('OBSERVER_BUILD_SHA', 'OBSERVER_BUILD_BYTES')
    for tree in (old, new):
        found = []
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if node.targets[0].id in names:
                    found.append(node.targets[0].id)
                    node.value = ast.Constant(value=None)
        need(sorted(found) == sorted(names), 'EXACT_TWO_OBSERVER_CONSTANTS')
    need(ast.dump(old, include_attributes=False) == ast.dump(new, include_attributes=False),
         'ALL_OTHER_PENDING_HELPER_AST_UNCHANGED')


def compose(root, args):
    baseline = git(root, BASE_REVISION, WORKFLOW)
    need(sha(baseline) == BASE_SHA and admitted(root, WORKFLOW) == baseline, 'ACTUAL_2B5_WORKFLOW')
    admitted(root, BASE_GENERATOR, BASE_GENERATOR_SHA)
    workflow, pins = prior_pins(baseline)
    old_pins = dict(pins)
    binding = load(root, args.helper_binding)
    mock = load(root, args.mock_proof)
    helper_review = load(root, args.helper_review)
    meta = load(root, args.map_metadata)
    helper_raw = admitted(root, HELPER, binding['final_helper_sha256'])
    pending_helper = git(root, PENDING_REVISION, HELPER)
    need(sha(pending_helper) == PENDING_HELPER_SHA, 'EXACT_PUBLISHED_PENDING_HELPER')
    exact_two_constants(pending_helper, helper_raw)
    admitted(root, TEST, binding['test_sha256'])
    helper = literals(helper_raw)
    need(binding['schema'] == BINDING_SCHEMA and binding['passed'] is True and binding['other_AST_equal'] is True and
         binding['pending_helper_sha256'] == PENDING_HELPER_SHA and
         binding['mocked_proof_sha256'] == sha(admitted(root, args.mock_proof)) and
         type(binding['current_receiver_dependency_count']) is int and binding['current_receiver_dependency_count'] == 46 and
         binding['current_receiver_dependencies_sha256'] and
         type(binding['evidence_artifact_pin_count']) is int and
         binding['evidence_artifact_pin_count'] == len(binding['evidence_artifact_sha256']) == 143,
         'ACTUAL_CONCRETIZATION_BINDING')
    need(binding['exact_AST_changes'] == ['OBSERVER_BUILD_SHA', 'OBSERVER_BUILD_BYTES'] and
         binding['final_helper'] == HELPER and binding['test_file'] == TEST and
         binding['destination_platform_qualified'] is False and
         binding['destination_helper_or_loader_or_native_executed'] is False and
         binding['Git_read_only_subprocesses_executed'] is True and
         binding['mock_controls_reexecuted'] is False and binding['runtime_executed'] is False and
         binding['source_generation_admitted'] is False and binding['world_authority'] is False,
         'ONLY_TWO_CONSTANTS_SOURCE_BINDING')
    need(re.fullmatch('[0-9a-f]{64}', helper['OBSERVER_BUILD_SHA']) is not None and
         type(helper['OBSERVER_BUILD_BYTES']) is int and helper['OBSERVER_BUILD_BYTES'] > 0,
         'ACTUAL_MAP_METADATA_REQUIRED')
    mapping = binding['current_receiver_dependencies_sha256']
    artifacts = binding['evidence_artifact_sha256']
    need(len(mapping) == 46 and sha(json.dumps(mapping, sort_keys=True, separators=(',', ':')).encode()) == CURRENT_MAP_SHA,
         'EXACT_CURRENT_46')
    need(helper['ELF_SHA'] == RECEIVER_ELF_SHA and helper['BUILD_SHA'] == RECEIVER_RAW_SHA and
         helper['MAP_SHA'] == CURRENT_MAP_SHA and helper['FOLLOWUP_SHA'] == FOLLOWUP_SHA, 'EXACT_NEW_RECEIVER')
    focused = load(root, FOLLOWUP, FOLLOWUP_SHA)
    independent = load(root, F_INITIAL, F_INITIAL_SHA)
    need(focused['passed'] is independent['passed'] is True and len(focused['source_sha256']) == 13 and
         len(focused['original_sha256_raw']) == 15 and len(independent['source_inputs_sha256']) == 253,
         'QUALIFIED_A13_ORIGINAL15_F253')
    changes = {}
    need(len(focused['superseded_source_pins']) == 6, 'EXACT_A_SIX')
    for name, item in focused['superseded_source_pins'].items():
        replace_pin(pins, changes, name, item['previous_sha256'], item['sha256'], FOLLOWUP)
    merge(pins, focused['source_sha256'], 'A13')
    merge(pins, focused['added_source_paths'], 'A_THREE_ADDED')
    merge(pins, {'upstream/ouroboros/' + k: v for k, v in focused['original_sha256_raw'].items()}, 'ORIGINAL15')
    # Current46 is source-derived by F from the retained release receipt. Its
    # exact four45->46 changes and single added header remain separately bound.
    reuse = load(root, helper['REVIEW'] + 'review.json', helper['REVIEW_SHA'])
    previous = load(root, helper['PREVIOUS_RECEIVER_REVIEW'], helper['PREVIOUS_RECEIVER_REVIEW_SHA'])
    old_map = previous['current_project_consumer_dependencies']['sha256']
    transition = reuse['current_project_consumer_dependencies']['previous_account_controls45_transition']
    need(len(old_map) == 45 and reuse['current_project_consumer_dependencies']['sha256'] == mapping and
         transition['removed'] == [] and len(transition['changed']) == 4 and
         set(transition['added']) == {'native-android/engine/dbclient/coh_db_account_inventory.h'} and
         all(mapping[k] == v for k, v in transition['added'].items()), 'QUALIFIED_45_TO_46')
    for name, item in transition['changed'].items():
        need(old_map[name] == item['previous_sha256'] and mapping[name] == item['sha256'], 'CURRENT_46_TRANSITION')
        replace_pin(pins, changes, name, item['previous_sha256'], item['sha256'], helper['REVIEW'] + 'review.json')
    peer_proof = load(root, helper['PEER_PROOF'], helper['PEER_PROOF_SHA'])
    peer = 'native-android/engine/initial-capture/test_initial_peer.c'
    need(peer_proof['passed'] is True and peer_proof['all_old_bytes_equal_after_removing_new_guard_blocks'] is True and
         peer_proof['C50_all_50_source_hashes_unchanged'] is True, 'QUALIFIED_PEER_EXTENSION')
    replace_pin(pins, changes, peer, 'aa20f0e7d9cecbff6770a33905ce0768f4e32c248a29af3a9a588209f538f721',
                peer_proof['source_sha256'][peer], helper['PEER_PROOF'])
    merge(pins, mapping, 'CURRENT46')
    # The retained old compile workflow is historical. Its only replacement is
    # the reviewed current recipe whose actual255 closure is checked below.
    replace_pin(pins, changes, BUILD_WORKFLOW, BUILD_OLD_SHA, BUILD_NEW_SHA, args.map_metadata)
    merge(pins, independent['source_inputs_sha256'], 'F253')
    merge(pins, artifacts, 'QUALIFIED_RECEIVER_EVIDENCE')
    need(meta['schema'] == MAP_SCHEMA and meta['passed'] is True and
         meta['actual_source_and_PE_admitted'] is True and meta['runtime_executed'] is False and
         all(meta[k] is False for k in ('actor_authority', 'actual_sleeping_state_established',
                                        'source_generation_admitted', 'world_authority')) and
         type(meta['run_id']) is int and meta['run_id'] > 0 and
         type(meta['artifact_id']) is int and meta['artifact_id'] > 0 and
         re.fullmatch('[0-9a-f]{40}', meta['source_revision']) is not None and
         meta['artifact_name'] == 'fresh-groups-initial-owner-build-' + meta['source_revision'],
         'ACTUAL_ADMITTED_MAP_METADATA')
    folder = PROFILE + 'compile-initial-owner-20261018/'
    need(meta['canonical_directory'] == folder and meta['receipt_path'] == helper['OBSERVER_BUILD'] ==
         folder + 'compile-only-receipt.json' and meta['receipt_sha256'] == helper['OBSERVER_BUILD_SHA'] and
         meta['receipt_bytes'] == helper['OBSERVER_BUILD_BYTES'] and
         type(meta['archive_bytes']) is int and 0 < meta['archive_bytes'] < 8 * 1024**2 and
         meta['archive_path'].startswith(folder) and meta['archive_path'].endswith('.zip'),
         'ACTUAL_MAP_PATHS_AND_RECEIPT')
    files = meta['retained_files']
    need(len(files) == 10 and meta['archive_path'] in files and
         meta['source_admission_path'] in files and meta['strict_admission_path'] in files and
         meta['receipt_path'] in files and 1 <= len(meta['independent_review_files']) <= 4,
         'EXACT_RETAINED_MAP_FILES')
    need(not set(files).intersection(meta['independent_review_files']) and
         args.map_metadata not in files and not args.map_metadata.startswith(folder) and
         all(name.startswith(folder) for name in files), 'DISJOINT_MAP_EVIDENCE')
    for name, item in {**files, **meta['independent_review_files']}.items():
        value = admitted(root, name, item['sha256'])
        need(len(value) == item['bytes'], 'MAP_EVIDENCE_BYTES')
        merge(pins, {name: item['sha256']}, 'ACTUAL_MAP_EVIDENCE')
    need(files[meta['archive_path']] == {'bytes': meta['archive_bytes'], 'sha256': meta['archive_sha256']} and
         files[meta['receipt_path']] == {'bytes': meta['receipt_bytes'], 'sha256': meta['receipt_sha256']},
         'EXACT_MAP_ARCHIVE_AND_RECEIPT')
    receipt = load(root, meta['receipt_path'], meta['receipt_sha256'])
    need(receipt['schema'] == 'coh-fresh-groups-observer-compile-v1' and receipt['passed'] is True and
         receipt['compile_only'] is True and receipt['runtime_executed'] is False and
         receipt['source_revision'] == meta['source_revision'] and receipt['pe_machine'] == 'i386' and
         receipt['source_stage_verified'] is True and receipt['inherited_source_closure_reverified'] is True,
         'ACTUAL_STRICT_MAP_RECEIPT')
    actual = load(root, meta['source_admission_path'])
    need(actual['schema'] == 'coh-fresh-initial-owner-build-source-admission-v1' and actual['passed'] is True and
         actual['compile_only'] is True and actual['runtime_executed'] is False and
         actual['source_revision'] == meta['source_revision'] and len(actual['source_sha256']) == 255,
         'ACTUAL_MAP_255')
    merge(pins, actual['source_sha256'], 'ACTUAL_MAP255')
    strict = load(root, meta['strict_admission_path'])
    need(strict['schema'] == 'coh-fresh-initial-owner-map-compile-admission-v1' and strict['passed'] is True and
         strict['strict_linux_admission_passed'] is True and strict['strict_cli_passed'] is True and
         strict['compile_only'] is True and strict['runtime_executed'] is False and
         strict['source_revision'] == meta['source_revision'] and strict['run_id'] == meta['run_id'] and
         strict['artifact_id'] == meta['artifact_id'], 'INDEPENDENT_STRICT_MAP_ADMISSION')
    need(helper_review['schema'] == HELPER_REVIEW_SCHEMA and helper_review['passed'] is True and
         helper_review['helper_sha256'] == binding['final_helper_sha256'] and
         helper_review['binding_sha256'] == sha(admitted(root, args.helper_binding)) and
         helper_review['test_sha256'] == binding['test_sha256'] and
         helper_review['current_receiver_dependencies_sha256'] == mapping and
         helper_review['evidence_artifact_sha256'] == artifacts, 'INDEPENDENT_HELPER_BINDING_REVIEW')
    need(mock['schema'] == 'coh-inventory-initial-owner-receiver-focused-mocks-v1' and mock['passed'] is True and
         mock['helper_sha256'] == PENDING_HELPER_SHA and mock['test_sha256'] == binding['test_sha256'] and
         type(mock['methods']) is int and mock['methods'] == 5 and
         type(mock['cases']) is int and mock['cases'] == 73 and
         isinstance(mock['case_names'], list) and len(mock['case_names']) == 73 and
         len(set(mock['case_names'])) == 73 and all(type(k) is str for k in mock['case_names']) and
         all(type(mock[k]) is int and mock[k] == 0 for k in ('errors', 'failures', 'skipped')) and
         mock['source_inputs_unchanged'] is True and mock['retained_elf_read_for_hash_only'] is True and
         mock['new_inventory_a13_metadata_controls_only'] is True and
         mock['observer_receipt_is_explicit_mock'] is True and mock['actual_new_map_receipt_admitted'] is False and
         mock['old49_or54_mock_suites_reexecuted'] is False and
         mock['actual_destination_preflight_executed'] is False and
         mock['project_imports_compiler_loader_native_registry_services_or_network_executed'] is False and
         mock['source_generation_admitted'] is False and mock['actor_publication'] is False and
         mock['world_authority'] is False,
         'ONLY_NEW_MOCK_CONTROLS')
    for name in (HELPER, TEST, args.helper_binding, args.mock_proof, args.helper_review, args.map_metadata, F_INITIAL):
        merge(pins, {name: sha(admitted(root, name))}, 'CURRENT_METADATA')
    need(set(changes) == {k for k, v in old_pins.items() if pins[k] != v} and len(changes) == 12,
         'ONLY_TWELVE_QUALIFIED_BASELINE_SUPERSESSIONS')
    for name, digest in pins.items():
        admitted(root, name, digest)
    need(0 < len(pins) < 512, 'BOUNDED_CURRENT_SOURCE_MAP')
    return workflow, dict(sorted(pins.items())), binding, meta, changes


GATE_TAIL = r'''
workflow='.github/workflows/native-fresh-groups-observation.yml'
p=root/workflow
need(p.resolve()==p and p.is_file() and not p.is_symlink() and p.stat().st_size<1024**2,'WORKFLOW_REGULAR_SOURCE')
pins[workflow]=hashlib.sha256(p.read_bytes()).hexdigest()
need(0<len(pins)<=512,'BOUNDED_SOURCE_CLOSURE')
tree=subprocess.check_output(['git','ls-tree','-r','-z','HEAD','--',*sorted(pins)]);blobs={}
for row in tree.split(b'\0'):
    if not row:continue
    meta,name=row.split(b'\t',1);mode,kind,digest=meta.split()
    need(kind==b'blob' and mode in (b'100644',b'100755'),'TRACKED_SOURCE_MODE');blobs[name.decode()]=digest.decode()
need(set(blobs)==set(pins),'ALL_FROZEN_SOURCES_COMMITTED')
for name,digest in pins.items():
    rel=pathlib.PurePosixPath(name)
    need(not rel.is_absolute() and all(part not in ('','.','..') for part in rel.parts) and chr(92) not in name and ':' not in name,'RELATIVE_SOURCE_NAME')
    p=root/name
    need(p.resolve()==p and p.is_file() and not p.is_symlink() and 0<p.stat().st_size<8*1024**2,'BOUNDED_CANONICAL_SOURCE')
    raw=p.read_bytes()
    need(hashlib.sha256(raw).hexdigest()==digest and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blobs[name],'EXACT_REVIEWED_SOURCE_AND_ARTIFACT')
binding=json.loads((root/BINDING).read_bytes());mock=json.loads((root/MOCK).read_bytes());meta=json.loads((root/MAP_METADATA).read_bytes())
need(binding['schema']=='coh-inventory-initial-owner-destination-preflight-actual-metadata-binding-v1' and binding['passed'] is True and binding['final_helper_sha256']==pins[HELPER] and binding['test_sha256']==pins[TEST] and binding['mocked_proof_sha256']==pins[MOCK] and binding['other_AST_equal'] is True and binding['pending_helper_sha256']=='99f47dd7d3e6e9a0475a83d498a7c3318bcfc1e40c9140d89948c28942e4c553' and binding['exact_AST_changes']==['OBSERVER_BUILD_SHA','OBSERVER_BUILD_BYTES'] and binding['final_helper']==HELPER and binding['test_file']==TEST,'ACTUAL_METADATA_BINDING')
need(all(binding[k] is False for k in ('destination_platform_qualified','destination_helper_or_loader_or_native_executed','mock_controls_reexecuted','runtime_executed','source_generation_admitted','world_authority')),'SOURCE_ONLY_TWO_CONSTANT_BINDING')
need(binding['Git_read_only_subprocesses_executed'] is True,'READ_ONLY_GIT_BINDING_SCOPE')
need(type(binding['current_receiver_dependency_count']) is int and binding['current_receiver_dependency_count']==46 and len(binding['current_receiver_dependencies_sha256'])==46 and all(pins.get(k)==v for k,v in binding['current_receiver_dependencies_sha256'].items()) and type(binding['evidence_artifact_pin_count']) is int and binding['evidence_artifact_pin_count']==len(binding['evidence_artifact_sha256'])==143 and all(pins.get(k)==v for k,v in binding['evidence_artifact_sha256'].items()),'CURRENT46_AND_QUALIFIED_EVIDENCE')
need(mock['schema']=='coh-inventory-initial-owner-receiver-focused-mocks-v1' and mock['passed'] is True and mock['helper_sha256']==binding['pending_helper_sha256'] and mock['test_sha256']==pins[TEST] and type(mock['methods']) is int and mock['methods']==5 and type(mock['cases']) is int and mock['cases']==73 and isinstance(mock['case_names'],list) and len(mock['case_names'])==len(set(mock['case_names']))==73 and all(type(k) is str for k in mock['case_names']) and all(type(mock[k]) is int and mock[k]==0 for k in ('errors','failures','skipped')) and mock['source_inputs_unchanged'] is True and mock['retained_elf_read_for_hash_only'] is True and mock['new_inventory_a13_metadata_controls_only'] is True and mock['old49_or54_mock_suites_reexecuted'] is False and mock['observer_receipt_is_explicit_mock'] is True and mock['actual_new_map_receipt_admitted'] is False and mock['actual_destination_preflight_executed'] is False and mock['project_imports_compiler_loader_native_registry_services_or_network_executed'] is False and mock['source_generation_admitted'] is False and mock['actor_publication'] is False and mock['world_authority'] is False,'NEW_MOCK_CONTROLS_ONLY')
actual=json.loads((root/meta['source_admission_path']).read_bytes())
need(meta['schema']=='coh-inventory-initial-owner-scene-map-input-v1' and meta['passed'] is True and meta['actual_source_and_PE_admitted'] is True and meta['runtime_executed'] is False and all(meta[k] is False for k in ('actor_authority','actual_sleeping_state_established','source_generation_admitted','world_authority')) and actual['schema']=='coh-fresh-initial-owner-build-source-admission-v1' and actual['passed'] is True and actual['source_revision']==meta['source_revision'] and actual['compile_only'] is True and actual['runtime_executed'] is False and len(actual['source_sha256'])==255 and all(pins.get(k)==v for k,v in actual['source_sha256'].items()),'ACTUAL_NEW_MAP255_SUBSET')
review=json.loads((root/HELPER_REVIEW).read_bytes())
need(review['schema']=='coh-f-inventory-initial-owner-receiver-actual-binding-review-v1' and review['passed'] is True and review['helper_sha256']==pins[HELPER] and review['binding_sha256']==pins[BINDING] and review['test_sha256']==pins[TEST] and review['current_receiver_dependencies_sha256']==binding['current_receiver_dependencies_sha256'] and review['evidence_artifact_sha256']==binding['evidence_artifact_sha256'],'INDEPENDENT_HELPER_REVIEW')
need(subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==head,'SOURCE_HEAD_CHANGED')
receipt={'schema':'coh-inventory-initial-owner-fresh-groups-live-source-admission-v1','passed':True,'source_revision':head,'source_sha256':pins,'host_controls_reexecuted':False,'historical_worker_commit_replayed_in_CI':False,'source_preflight_only':True,'runtime_executed':False,'accepted_observer_equivalence':False,'source_generation_admitted':False,'world_authority':False,'observer_compile_receipt_sha256':meta['receipt_sha256'],'receiver_build_receipt_sha256':'09320ce3c78ccbf9af46de9b09c7bd1f551375fad39dc4e2b44eb3e962779216','source_profile_proof_sha256':'550d600596e2939f73de076fac5fce859ce18248a0866e1b1d19795393dc03fb'}
need(set(receipt)==GATE_KEYS,'EXACT_FOURTEEN_KEY_GATE')
path=pathlib.Path(os.environ['RUNNER_TEMP'])/'fresh-groups-source-admission.json'
with path.open('xb') as stream:stream.write((json.dumps(receipt,indent=2,sort_keys=True)+'\n').encode())
print(json.dumps({'source_admission_passed':True,'frozen_pins':len(pins),'host_controls_reexecuted':False,'runtime_executed':False}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--helper-binding', required=True)
    parser.add_argument('--mock-proof', required=True)
    parser.add_argument('--helper-review', required=True)
    parser.add_argument('--map-metadata', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve(strict=True)
    need(not args.output.exists() and not args.output.with_suffix('.draft.json').exists(), 'FRESH_OUTPUT')
    before = subprocess.check_output(['git', '-C', root, 'rev-parse', 'HEAD'], text=True).strip()
    previous, pins, binding, meta, changes = compose(root, args)
    draft = copy.deepcopy(previous)
    draft['name'] = 'Fresh original GROUPS with pre-entry owner and complete DB inventory controls'
    job = next(iter(draft['jobs'].values()))
    draft['jobs'] = {'matching-original-inventory-initial-owner-observation': job}
    job['if'] = job['if'].replace('[fresh-groups-owner-reason]', '[fresh-groups-inventory-initial-owner]')
    job['env'].update(FRESH_OBSERVER_ARTIFACT_ID=str(meta['artifact_id']), FRESH_OBSERVER_RUN_ID=str(meta['run_id']),
        FRESH_OBSERVER_REVISION=meta['source_revision'], FRESH_OBSERVER_ZIP_BYTES=str(meta['archive_bytes']),
        FRESH_OBSERVER_ZIP_SHA256=meta['archive_sha256'], FRESH_OBSERVER_RECEIPT_SHA256=meta['receipt_sha256'])
    steps = job['steps']
    gate = """import hashlib,json,os,pathlib,subprocess
def need(ok,code):
    if not ok:raise ValueError(code)
need(__debug__ and not os.environ.get('PYTHONOPTIMIZE'),'ASSERTIONS_REQUIRED')
need(os.name=='posix' and os.environ['RUNNER_ENVIRONMENT']=='github-hosted' and os.environ['RUNNER_OS']=='Linux' and os.environ['RUNNER_ARCH']=='X64','HOSTED_LINUX_X64_ONLY')
need(os.environ['GITHUB_REPOSITORY']=='Russianranger/coh-android' and os.environ['GITHUB_REF']=='refs/heads/native-android','OWNED_NATIVE_BRANCH_ONLY')
root=pathlib.Path.cwd().resolve();head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
need(head==os.environ['GITHUB_SHA'],'EXACT_HEAD')
"""
    for name, value in [('HELPER', HELPER), ('TEST', TEST), ('BINDING', args.helper_binding), ('MOCK', args.mock_proof),
                        ('HELPER_REVIEW', args.helper_review), ('MAP_METADATA', args.map_metadata)]:
        gate += name + '=' + repr(value) + '\n'
    gate += 'GATE_KEYS=set(' + repr(sorted(literals(admitted(root, HELPER))['GATE_KEYS'])) + ')\n'
    gate += 'pins=' + pprint.pformat(pins, sort_dicts=True, width=120) + '\n' + GATE_TAIL
    ast.parse(gate)
    steps[1]['name'] = 'Admit exact current Inventory receiver and initial-owner Map before project imports or runtime'
    steps[1]['run'] = "python3 - <<'PYINVENTORYINITIALSOURCE'\n" + gate + 'PYINVENTORYINITIALSOURCE\n'
    old_receipt = '478bea524f7d8a5ed016ae43ea54f50401bff2c714d75275002d1f8d5b6e9034'
    for index, step in enumerate(steps):
        if index != 1 and 'run' in step:
            step['run'] = step['run'].replace(old_receipt, meta['receipt_sha256'])
    steps[4]['run'] = steps[4]['run'].replace("'fresh-groups-owner-reason-build-'+os.environ['FRESH_OBSERVER_REVISION']",
        "'fresh-groups-initial-owner-build-'+os.environ['FRESH_OBSERVER_REVISION']").replace(
        PROFILE + 'compile-owner-predicates-20261018/fresh-map-owner-build-39094808520.zip', meta['archive_path'])
    steps[8]['name'] = 'Admit exact Inventory receiver without rebuild or historical test replay'
    steps[8]['run'] = steps[8]['run'].replace('admit_account_controls_initial_receiver.py', 'admit_initial_inventory_receiver.py')
    steps[14]['with']['name'] = 'fresh-inventory-initial-owner-groups-public-status-$' + '{{ github.sha }}'
    need(len(steps) == 17 and steps[1]['id'] == 'source_admission' and
         steps[13]['if'] == "always() && steps.source_admission.outcome == 'success'", 'EXACT_17_STEP_BOUNDARIES')
    oldsteps = next(iter(previous['jobs'].values()))['steps']
    for index in (0, 2, 3, 5, 6, 7, 9, 10, 11, 12, 13, 15, 16):
        expected = copy.deepcopy(oldsteps[index])
        if 'run' in expected:
            expected['run'] = expected['run'].replace(old_receipt, meta['receipt_sha256'])
        need(steps[index] == expected, 'UNCHANGED_FIXTURE_RUNTIME_OR_EXPORT_STEP:' + str(index))
    need(subprocess.check_output(['git', '-C', root, 'rev-parse', 'HEAD'], text=True).strip() == before, 'HEAD_CHANGED')
    for name, digest in pins.items():
        need(sha((root / name).read_bytes()) == digest, 'FINAL_SOURCE_CHANGED')
    rendered = yaml.safe_dump(draft, sort_keys=False, width=120).encode()
    with args.output.open('xb') as stream:
        stream.write(rendered)
    report = {'schema': 'coh-inventory-initial-owner-scene-workflow-draft-v1', 'passed': True, 'source_revision': before,
        'workflow_bytes': len(rendered), 'workflow_sha256': sha(rendered), 'generator_sha256': sha(Path(__file__).read_bytes()),
        'current_nonself_pins': len(pins), 'dynamic_workflow_self_pin': True, 'current_receiver_dependencies': 46,
        'qualified_evidence_pins': len(binding['evidence_artifact_sha256']), 'actual_map_source_pins': 255,
        'baseline_workflow_sha256': BASE_SHA, 'qualified_supersessions': changes,
        'project_helpers_imported': False, 'qualifiers_tests_compiler_loader_native_services_or_download_executed': False,
        'root_repository_mutated': False, 'same_fixture_unchanged': True}
    with args.output.with_suffix('.draft.json').open('x') as stream:
        stream.write(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
