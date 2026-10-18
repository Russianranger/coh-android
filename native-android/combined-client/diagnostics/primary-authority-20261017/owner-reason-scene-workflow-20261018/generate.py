#!/usr/bin/env python3
"""Draft the new scene recipe from qualified source supersessions, data only.

Writes scratch outputs only. No helper CLI, loader, compiler, server, capture,
qualification suite or remote download is run. Root owns repository publication.
"""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import pprint
import subprocess
from unittest.mock import patch

import yaml

HELPER = 'native-android/combined-client/tools/admit_account_controls_initial_receiver.py'
HELPER_SHA = 'c5a49d446423ac76ab2977a75a5e8bcb3a817daeb55c1d2dd30092933238c01e'
TEST = 'native-android/combined-client/tools/test_admit_account_controls_initial_receiver.py'
TEST_SHA = '48a3de4349dee2b3f3fe3a3144197f5b39373ff273918e4dcfadf86b7a29c376'
WORKFLOW = '.github/workflows/native-fresh-groups-observation.yml'
OLD_WORKFLOW_SHA = '0261d1a4404f51186986181805f16295f7b48bd732b3a0a4a138707d0935c262'
PROFILE = 'native-android/engine/scenecatalog-server/evidence/fresh-callback-profile-20261018/'
MAP_FOLDER = PROFILE + 'compile-owner-predicates-20261018/'
MAP_ZIP = MAP_FOLDER + 'fresh-map-owner-build-39094808520.zip'
MAP_ZIP_SHA = 'b3a82a5265322685e035e3b86f44862a59d8fc561852288e3d3ea8bb8371eed6'
MAP_RECEIPT_SHA = '478bea524f7d8a5ed016ae43ea54f50401bff2c714d75275002d1f8d5b6e9034'
MAP_REVISION = '6e96fe22a567a3e252449feb37483cfea1566d8a'
PREFLIGHT = 'native-android/combined-client/diagnostics/primary-authority-20261017/account-controls-destination-preflight-20261018/'
MOCK = PREFLIGHT + 'mocked-controls-pending-source.json'
BINDING = PREFLIGHT + 'binding.json'
MAP_REVIEW = 'native-android/combined-client/diagnostics/continuation-f-20261017/owner-reason-map-build-39094808520-review/'
A_HELPER_REVIEW = PROFILE + 'account-controls-preflight-binding-review.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, code):
    if not ok:
        raise ValueError(code)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def admitted(root, name, expected=None):
    path = root / name
    raw = path.read_bytes()
    require(path.resolve() == path and not path.is_symlink() and path.is_file(), 'CANONICAL_INPUT')
    require(git(root, 'show', 'HEAD:' + name) == raw, 'INPUT_EQUALS_COMMITTED_HEAD:' + name)
    require(expected is None or sha(raw) == expected, 'FIXED_INPUT:' + name)
    return raw


def merge(pins, more, label):
    for name, digest in more.items():
        require(name not in pins or pins[name] == digest, 'SOURCE_CONFLICT:' + label + ':' + name)
        pins[name] = digest


def compose(root):
    helper_raw = admitted(root, HELPER, HELPER_SHA)
    admitted(root, TEST, TEST_SHA)
    spec = importlib.util.spec_from_file_location('draft_account_receiver_data', root / HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    # The exact admitted helper has only stdlib imports and declarations at
    # module scope. Its evidence functions read fixed bytes; these sentinels
    # make an accidental future process/import path fail during drafting.
    with patch.object(helper.subprocess, 'Popen', side_effect=AssertionError('DATA_ONLY_NO_PROCESS')), \
         patch.object(helper.importlib, 'import_module', side_effect=AssertionError('DATA_ONLY_NO_PROJECT_IMPORT')):
        _, _, mapping, artifacts = helper.evidence(root)
    require(len(mapping) == 45 and len(artifacts) == 115, 'FROZEN_45_AND_115')
    load = lambda name: json.loads(admitted(root, name))
    previous = load(helper.OLD_GATE)['current_278_pin_map']
    require(len(previous) == 278 and WORKFLOW in previous, 'OLD_278')
    base = {k: v for k, v in previous.items() if k != WORKFLOW}
    earlier = load(helper.EARLIER_PROFILE)
    require(len(earlier['source_sha256']) == 4 and
            all(base[k] == v for k, v in earlier['previous_source_sha256'].items()), 'A4_PREDECESSOR')
    base.update(earlier['source_sha256'])
    focused = load(helper.FOLLOWUP)
    updates, changed = focused['source_sha256'], focused['superseded_source_pins']
    require(len(updates) == 40 and len(changed) == 9 and
            all(base.get(k) == row['previous_sha256'] and updates[k] == row['sha256']
                for k, row in changed.items()) and
            {k for k, v in updates.items() if k in base and base[k] != v} == set(changed) and
            set(updates).difference(base) == set(focused['added_source_paths']) |
            {'native-android/engine/scenecatalog-server/groups_owner_oracle_shim.h'}, 'QUALIFIED_A40')
    base.update(updates)
    allowed = {'native-android/combined-client/tools/check_local_initial_capture.py',
        'native-android/engine/initial-capture/coh_initial_capture.h',
        'native-android/engine/initial-capture/coh_initial_map.c',
        'native-android/engine/dbclient/coh_db_session.c', 'native-android/engine/dbclient/coh_db_session.h',
        'native-android/engine/dbclient/coh_db_account_controls.c', 'native-android/engine/dbclient/coh_db_account_controls.h'}
    require({k for k, v in mapping.items() if base.get(k) != v} == allowed, 'QUALIFIED_45_TRANSITIONS')
    base.update(mapping)
    merge(base, artifacts, 'QUALIFIED_EVIDENCE')
    merge(base, {helper.EARLIER_PROFILE: helper.EARLIER_PROFILE_SHA,
                 helper.OWNER_REVIEW: helper.OWNER_REVIEW_SHA}, 'PROFILE_PROOFS')
    actual_map = load(MAP_FOLDER + 'fresh-groups-source-admission.json')
    require(actual_map['schema'] == 'coh-fresh-owner-reason-build-source-admission-v1' and
            actual_map['passed'] is True and actual_map['compile_only'] is True and
            actual_map['runtime_executed'] is False and len(actual_map['source_sha256']) == 241,
            'ACTUAL_MAP_241_SOURCE_CLOSURE')
    merge(base, actual_map['source_sha256'], 'ACTUAL_MAP_241')
    extra = [HELPER, TEST, MOCK, BINDING, A_HELPER_REVIEW]
    extra += [p.relative_to(root).as_posix() for folder in (MAP_FOLDER, MAP_REVIEW)
              for p in sorted((root / folder).iterdir()) if p.is_file()]
    require(len([n for n in extra if n.startswith(MAP_FOLDER)]) == 10, 'ACTUAL_MAP_TEN_FILES')
    for name in extra:
        merge(base, {name: sha(admitted(root, name))}, 'CURRENT_EVIDENCE')
    for name, digest in base.items():
        admitted(root, name, digest)
    binding = load(BINDING)
    require(binding['passed'] is True and binding['final_helper_sha256'] == HELPER_SHA and
            binding['test_sha256'] == TEST_SHA and binding['other_AST_equal'] is True and
            binding['current_receiver_dependencies_sha256'] == mapping and
            binding['evidence_artifact_sha256'] == artifacts, 'CONCRETIZATION_BINDING')
    require(sha(admitted(root, MAP_ZIP)) == MAP_ZIP_SHA, 'RETAINED_MAP_ZIP')
    require(sha(admitted(root, MAP_FOLDER + 'compile-only-receipt.json')) == MAP_RECEIPT_SHA,
            'NEW_MAP_RECEIPT')
    require((root / HELPER).read_bytes() == helper_raw, 'HELPER_UNCHANGED')
    require(0 < len(base) < 512, 'SOURCE_CLOSURE_BOUND')
    return helper, dict(sorted(base.items()))


GATE_TAIL = r'''
workflow='.github/workflows/native-fresh-groups-observation.yml'
p=root/workflow
need(p.resolve()==p and p.is_file() and not p.is_symlink() and p.stat().st_size<1024**2,'WORKFLOW_REGULAR_SOURCE')
pins[workflow]=hashlib.sha256(p.read_bytes()).hexdigest()
need(0<len(pins)<=512,'BOUNDED_SOURCE_CLOSURE')
tree=subprocess.check_output(['git','ls-tree','-r','-z','HEAD','--',*sorted(pins)])
blobs={}
for row in tree.split(b'\0'):
    if not row:continue
    meta,name=row.split(b'\t',1);mode,kind,digest=meta.split()
    need(kind==b'blob' and mode in (b'100644',b'100755'),'TRACKED_SOURCE_MODE')
    blobs[name.decode()]=digest.decode()
need(set(blobs)==set(pins),'ALL_FROZEN_SOURCES_COMMITTED')
for name,digest in pins.items():
    rel=pathlib.PurePosixPath(name)
    need(not rel.is_absolute() and all(part not in ('','.','..') for part in rel.parts) and chr(92) not in name and ':' not in name,'RELATIVE_SOURCE_NAME')
    p=root/name
    need(p.resolve()==p and p.is_file() and not p.is_symlink() and 0<p.stat().st_size<8*1024**2,'BOUNDED_CANONICAL_SOURCE')
    raw=p.read_bytes()
    need(hashlib.sha256(raw).hexdigest()==digest and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blobs[name],'EXACT_REVIEWED_SOURCE_AND_ARTIFACT')
binding=json.loads((root/BINDING).read_bytes())
mock=json.loads((root/MOCK).read_bytes())
need(binding['schema']=='coh-account-controls-destination-preflight-actual-metadata-binding-v1' and binding['passed'] is True and binding['final_helper_sha256']==pins[HELPER] and binding['test_sha256']==pins[TEST] and binding['mocked_proof_sha256']==pins[MOCK] and binding['other_AST_equal'] is True,'ACTUAL_METADATA_BINDING')
need(binding['current_receiver_dependency_count']==45 and len(binding['current_receiver_dependencies_sha256'])==45 and all(pins.get(k)==v for k,v in binding['current_receiver_dependencies_sha256'].items()) and binding['evidence_artifact_pin_count']==115 and all(pins.get(k)==v for k,v in binding['evidence_artifact_sha256'].items()),'CURRENT_45_AND_QUALIFIED_115')
need(binding['destination_platform_qualified'] is False and binding['loader_or_native_or_subprocess_executed'] is False and binding['mock_controls_reexecuted'] is False and binding['runtime_executed'] is False and binding['source_generation_admitted'] is False and binding['world_authority'] is False,'NO_DESTINATION_OR_RUNTIME_AUTHORITY')
need(mock['schema']=='coh-account-controls-receiver-mocked-controls-v1' and mock['passed'] is True and mock['helper_sha256']==binding['pending_helper_sha256'] and mock['test_sha256']==pins[TEST] and type(mock['methods']) is int and mock['methods']==5 and mock['new_evidence_and_gate_only'] is True and mock['old_mock_suites_reexecuted'] is False and mock['observer_receipt_is_explicit_mock'] is True and mock['actual_map_compile_receipt_admitted'] is False and mock['actual_destination_preflight_executed'] is False and mock['loader_native_compiler_services_executed'] is False,'MOCKED_NEW_CONTROLS_SCOPE')
actual_map=json.loads((root/ACTUAL_MAP_GATE).read_bytes())
need(actual_map['schema']=='coh-fresh-owner-reason-build-source-admission-v1' and actual_map['passed'] is True and actual_map['compile_only'] is True and actual_map['runtime_executed'] is False and actual_map['source_generation_admitted'] is False and actual_map['world_authority'] is False and len(actual_map['source_sha256'])==241 and all(pins.get(k)==v for k,v in actual_map['source_sha256'].items()),'ACTUAL_COMPILED_MAP_241_SUBSET')
a_review=json.loads((root/A_HELPER_REVIEW).read_bytes())
need(a_review['schema']=='coh-a-account-controls-preflight-metadata-review-v1' and a_review['passed'] is True and a_review['helper']['path']==HELPER and a_review['helper']['sha256']==pins[HELPER] and a_review['retained_root_binding']['sha256']==pins[BINDING] and a_review['unchanged_test']['sha256']==pins[TEST] and a_review['actual_Map_receipt']['sha256']=='478bea524f7d8a5ed016ae43ea54f50401bff2c714d75275002d1f8d5b6e9034' and a_review['compiled_slots_verified']==6 and a_review['current_receiver_dependencies_rehashed']==45 and a_review['evidence_artifact_pins_rehashed']==115 and a_review['other_whole_module_AST_equal'] is True and a_review['native_loader_or_ELF_executed'] is False and a_review['runtime_executed'] is False,'INDEPENDENT_HELPER_METADATA_REVIEW')
need(subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==head,'SOURCE_HEAD_CHANGED')
receipt={'schema':'coh-account-controls-fresh-groups-live-source-admission-v1','passed':True,'source_revision':head,'source_sha256':pins,'host_controls_reexecuted':False,'historical_worker_commit_replayed_in_CI':False,'source_preflight_only':True,'runtime_executed':False,'accepted_observer_equivalence':False,'source_generation_admitted':False,'world_authority':False,'observer_compile_receipt_sha256':'478bea524f7d8a5ed016ae43ea54f50401bff2c714d75275002d1f8d5b6e9034','receiver_build_receipt_sha256':'821ebfd2f84c60e8da23333476b9d1f8baadaf815c506933ee2b41572ef137d6','source_profile_proof_sha256':'d16e9260ef07a3d64e46014037e2433d96f9a2b94905a8b7fd7e1e4970d4aa22'}
path=pathlib.Path(os.environ['RUNNER_TEMP'])/'fresh-groups-source-admission.json'
with path.open('xb') as stream:stream.write((json.dumps(receipt,indent=2,sort_keys=True)+'\n').encode())
print(json.dumps({'source_admission_passed':True,'frozen_pins':len(pins),'host_controls_reexecuted':False,'runtime_executed':False}))
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    root = args.source_root.resolve()
    before = git(root, 'rev-parse', 'HEAD')
    old_raw = admitted(root, WORKFLOW, OLD_WORKFLOW_SHA)
    helper, pins = compose(root)
    previous = yaml.safe_load(old_raw)
    draft = copy.deepcopy(previous)
    draft['name'] = 'Fresh original GROUPS with fixed owner reason and complete DB account controls'
    draft['jobs'] = {'matching-original-owner-reason-observation': next(iter(draft['jobs'].values()))}
    job = next(iter(draft['jobs'].values()))
    job['if'] = job['if'].replace('[fresh-groups-editmsg]', '[fresh-groups-owner-reason]')
    env = job['env']
    env.update(FRESH_OBSERVER_ARTIFACT_ID='12124306842', FRESH_OBSERVER_RUN_ID='39094808520',
        FRESH_OBSERVER_REVISION=MAP_REVISION, FRESH_OBSERVER_ZIP_BYTES='6781758',
        FRESH_OBSERVER_ZIP_SHA256=MAP_ZIP_SHA, FRESH_OBSERVER_RECEIPT_SHA256=MAP_RECEIPT_SHA)
    steps = job['steps']
    gate = '''import hashlib,json,os,pathlib,subprocess
def need(ok,code):
    if not ok:raise ValueError(code)
need(__debug__ and not os.environ.get('PYTHONOPTIMIZE'),'ASSERTIONS_REQUIRED')
need(os.name=='posix' and os.environ['RUNNER_ENVIRONMENT']=='github-hosted' and os.environ['RUNNER_OS']=='Linux' and os.environ['RUNNER_ARCH']=='X64','HOSTED_LINUX_X64_ONLY')
need(os.environ['GITHUB_REPOSITORY']=='Russianranger/coh-android' and os.environ['GITHUB_REF']=='refs/heads/native-android','OWNED_NATIVE_BRANCH_ONLY')
root=pathlib.Path.cwd().resolve()
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
need(head==os.environ['GITHUB_SHA'],'EXACT_HEAD')
'''
    for name, value in [('HELPER', HELPER), ('TEST', TEST), ('BINDING', BINDING), ('MOCK', MOCK),
                        ('ACTUAL_MAP_GATE', MAP_FOLDER + 'fresh-groups-source-admission.json'),
                        ('A_HELPER_REVIEW', A_HELPER_REVIEW)]:
        gate += name + '=' + repr(value) + '\n'
    gate += 'pins=' + pprint.pformat(pins, sort_dicts=True, width=120) + '\n' + GATE_TAIL
    ast.parse(gate)
    steps[1]['name'] = 'Admit exact current owner-reason source and account-control receiver before project imports or runtime'
    steps[1]['run'] = "python3 - <<'PYOWNERREASONSOURCE'\n" + gate + 'PYOWNERREASONSOURCE\n'
    old_receipt = '0daf56e8dcae5d40ab9d5ef08bc09d022eba0a9a609170ce6d1ce867b2ca18c5'
    for step in steps:
        if 'run' in step:
            step['run'] = step['run'].replace(old_receipt, MAP_RECEIPT_SHA)
    steps[4]['run'] = steps[4]['run'].replace(
        "'original-fresh-groups-observer-compile-'+os.environ['FRESH_OBSERVER_REVISION']",
        "'fresh-groups-owner-reason-build-'+os.environ['FRESH_OBSERVER_REVISION']").replace(
        'native-android/engine/scenecatalog-server/evidence/fresh-callback-profile-20261018/compile-39086864926/fresh-map-build-39086864926.zip', MAP_ZIP)
    steps[8]['name'] = 'Admit exact account-control receiver without rebuild or test replay'
    steps[8]['run'] = steps[8]['run'].replace('admit_editmsg_initial_receiver.py', 'admit_account_controls_initial_receiver.py')
    steps[14]['with']['name'] = 'fresh-owner-reason-groups-public-status-${{ github.sha }}'
    require(len(steps) == 17 and steps[1]['id'] == 'source_admission' and
            steps[13]['if'] == "always() && steps.source_admission.outcome == 'success'", 'UNCHANGED_17_STEP_BOUNDARIES')
    for index in (2, 3, 6, 7, 9, 11, 12, 13, 15, 16):
        expected = copy.deepcopy(next(iter(previous['jobs'].values()))['steps'][index])
        if 'run' in expected:
            expected['run'] = expected['run'].replace(old_receipt, MAP_RECEIPT_SHA)
        require(steps[index] == expected, 'RUNTIME_STEP_CHANGED:' + str(index + 1))
    require(git(root, 'rev-parse', 'HEAD') == before, 'SOURCE_HEAD_CHANGED_DURING_DRAFT')
    rendered = yaml.safe_dump(draft, sort_keys=False, width=120)
    args.output.write_text(rendered)
    proof = {'schema': 'coh-owner-reason-scene-workflow-draft-v1', 'passed': True,
        'source_revision': before.decode().strip(), 'generator_sha256': sha(Path(__file__).read_bytes()),
        'workflow_sha256': sha(rendered.encode()), 'workflow_bytes': len(rendered.encode()),
        'current_nonself_pins': len(pins), 'dynamic_workflow_self_pin': True,
        'helper_sha256': HELPER_SHA, 'current_receiver_dependencies': 45,
        'qualified_evidence_pins': 115, 'same_fixture_unchanged': True,
        'actual_compiled_map_source_pins': 241,
        'unchanged_runtime_retention_steps': [3, 4, 7, 8, 10, 12, 13, 14, 16, 17],
        'pure_helper_evidence_read': True, 'helper_cli_executed': False,
        'qualifiers_tests_compiler_loader_native_services_or_download_executed': False}
    args.output.with_suffix('.draft.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps(proof))


if __name__ == '__main__':
    main()
