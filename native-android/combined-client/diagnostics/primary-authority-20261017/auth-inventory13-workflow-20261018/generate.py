#!/usr/bin/env python3
"""Draft only the new Auth/DB Inventory recipe from fixed JSON/source inputs.

No project modules, qualifiers, compilers, native programs or services execute.
The generator refuses until root has committed the reviewed Inventory inputs.
"""
import argparse
import ast
import copy
import gzip
import hashlib
import json
from pathlib import Path
import pprint
import subprocess

import yaml

WORKFLOW = '.github/workflows/native-auth-db-development.yml'
BASE_SHA = 'b2c8b2078237120dd2f42b0e421208f722182d8ab2feeaf4e39bc4e7ae26a539'
DEPLOYMENT = 'native-android/engine/auth-interop/deployment/'
PROOF = DEPLOYMENT + 'qualification/account-inventory-admission-20261018/host.json'
PROOF_SHA = 'e5e7839cbe99100d6cf4e25e1fd4bc83bbb908923d401d7a6b795a8e628147e6'
C50 = 'native-android/engine/dbclient/qualification/account-inventory-396621362'
C50_GZIP_SHA = '53d6b32dd97f2ff9bd0489097640193a6d66211b9fd1d50b7808c472ed9d219f'
C50_RAW_SHA = 'bf6c7a0730dd912cbb6fa1c18e61d6fcc1c34689a121aa18cf3fa3745c523376'
C50_BINDING_SHA = 'eeadd942e687e00c7967e73968dc02d60618fce6c9ded6bf4a585da6ce84c475'
C36 = 'native-android/engine/dbclient/qualification/account-controls-02b54d43f'
HISTORICAL = {
    DEPLOYMENT + 'qualification/account-controls-tool-admission-20261018/host.json':
        '45a525496b2307605addb416e07e5772c2a06da43e3f9291eeb405c051c626b2',
    DEPLOYMENT + 'qualification/account-controls-admission-20261018/host.json':
        'f6e8b60dfd96193a98b0ae00c9794385c27c589ebef3649d7f7d78b291aa9e5d',
    DEPLOYMENT + 'qualification/db-received-prefix-20261018/host.json':
        '5635322a560af7a73901a13ae8f18f25c2be60ce5f228ab58687999a4fe29985',
}
COMMON = {
    'native-android/combined-client/app/src/main/cpp/CMakeLists.txt':
        '9663fa7ed680d02a440789af7509239b4aafa2fa247ab90386f87502be9457f0',
    'native-android/engine/dbclient/CMakeLists.txt':
        'bd1249f3e43d0aa0bdd2ba7abab8c44ca75dfb87b6e07f62a37742556154a0f0',
}
METHODS = [
    'test_account_inventory_admission.InventoryAdmissionTests.test_c36_predecessor_has_only_three_exact_historical_changes_and_other_inputs_stay_current',
    'test_account_inventory_admission.InventoryAdmissionTests.test_current_c50_proof_and_every_current_input_reject_source_and_proof_drift',
    'test_account_inventory_admission.InventoryAdmissionTests.test_whole_current_map_same17tu_and_original_policy_lifetime_and_history_roles',
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def need(ok, code):
    if not ok:
        raise ValueError(code)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def admitted(root, name, expected=None):
    path = root / name
    raw = path.read_bytes()
    need(path.resolve() == path and not path.is_symlink() and path.is_file(), 'CANONICAL_INPUT')
    need(git(root, 'show', 'HEAD:' + name) == raw, 'CURRENT_COMMITTED_INPUT:' + name)
    need(expected is None or sha(raw) == expected, 'FIXED_INPUT:' + name)
    return raw


def source_field(review, subset):
    # Only the new C50 qualified map/subset is authoritative for this draft.
    # A review's unrelated tool snapshot is never promoted to current inputs.
    for field in ('qualified_source_sha256', 'source_sha256', 'source_inputs_sha256'):
        value = review.get(field)
        if isinstance(value, dict) and all(value.get(k) == v for k, v in subset.items()):
            return field
    raise ValueError('REVIEW_HAS_NO_QUALIFIED_C50_SUBSET')


GATE = r'''
workflow='.github/workflows/native-auth-db-development.yml'
p=root/workflow
need(p.resolve()==p and p.is_file() and not p.is_symlink() and p.stat().st_size<1024**2,'WORKFLOW_REGULAR_SOURCE')
pins[workflow]=hashlib.sha256(p.read_bytes()).hexdigest()
need(0<len(pins)<=512,'SOURCE_CLOSURE_BOUND')
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
    need(p.resolve()==p and p.is_file() and not p.is_symlink() and 0<p.stat().st_size<2*1024**2,'BOUNDED_CANONICAL_SOURCE')
    raw=p.read_bytes()
    need(hashlib.sha256(raw).hexdigest()==digest and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blobs[name],'EXACT_REVIEWED_SOURCE_AND_PROOF')
proof=json.loads((root/PROOF).read_bytes())
review=json.loads((root/REVIEW).read_bytes())
kernel_review=json.loads((root/KERNEL_REVIEW).read_bytes())
need(proof['schema']=='coh-development-account-inventory-admission-host-v1' and proof['passed'] is True and proof['source_inputs_sha256']==current148 and len(current148)==148,'CURRENT_D148')
need(type(proof['methods']) is list and proof['methods']==METHODS and len(proof['methods'])==proof['tests_run']==3 and proof['errors']==proof['failures']==proof['skipped']==0,'EXACT_NEW_THREE_CONTROLS')
need(proof['current_c50_source_inputs']==50 and proof['historical_c36_other_inputs_strictly_current']==33 and proof['project_translation_units']==17 and proof['unchanged_original_two_core_and_qualifier_boundaries'] is True,'C50_AND_UNCHANGED_LINK_POLICY')
for flag in ('old_qualifiers_or_deployment_suites_reexecuted','c50_qualifier_reexecuted','C_compiler_or_project_native_program_executed','actual_windows_api_executed','sockets_or_services_executed','new_runtime_qualified','root_source_integration_performed','owner_positive_policy_or_private_child_changed','server_crypto_profile_protocol_timeout_changed','inventory_body_values_observed_or_inferred','normal_version_or_checksum_reference_admitted'):
    need(proof[flag] is False,'SOURCE_CONTROLS_NOT_RUNTIME_OR_AUTHORITY')
need(review['schema']==REVIEW_SCHEMA and review['passed'] is True and review['source_inputs_sha256']==current148 and review['additional_common_integration_source_sha256']==COMMON,'INDEPENDENT_CURRENT_D148_REVIEW')
composition=proof['source_composition']
need(composition['source_proof_role']=='historical C36 precursor; unchanged current inputs revalidated' and composition['inventory_predecessor_revision']=='6e96fe22a567a3e252449feb37483cfea1566d8a' and composition['owner_success_predicate_changed'] is False and composition['unknown_command_policy_relaxed'] is False and composition['old_qualifiers_reexecuted'] is False and composition['actual_account_control_bodies_inferred'] is False,'EXPLICIT_HISTORICAL_AND_CURRENT_ROLES')
craw=gzip.decompress((root/(C50+'.json.gz')).read_bytes())
need(len(craw)==35544 and hashlib.sha256(craw).hexdigest()=='bf6c7a0730dd912cbb6fa1c18e61d6fcc1c34689a121aa18cf3fa3745c523376','EXACT_C50_RAW_PROOF')
cproof=json.loads(craw)
binding=json.loads((root/(C50+'-binding.json')).read_bytes())
need(cproof['schema']=='coh-db-account-inventory-focused-tests-v1' and cproof['passed'] is True and cproof['source_revision']==binding['qualified_source_revision']=='396621362fb55ef5a424f86d8d0e4fad549e58a2' and len(cproof['source_sha256'])==50 and cproof['source_sha256']==binding['source_sha256'] and all(current148.get(k)==v for k,v in cproof['source_sha256'].items()),'CURRENT_C50_SUBSET')
need(kernel_review['schema']==KERNEL_REVIEW_SCHEMA and kernel_review['passed'] is True and all(kernel_review[KERNEL_FIELD].get(k)==v for k,v in cproof['source_sha256'].items()),'INDEPENDENT_C50_REVIEW_SUBSET_ONLY')
need(binding['owner_implementation_changed'] is False and binding['strict_owner_success_predicate_changed'] is False and binding['new_translation_unit_required'] is False and binding['actual_packet_body_values_inferred'] is False,'UNCHANGED_OWNER_AND_NO_NEW_TU')
need(set(cproof['modes'])=={'release','asan','ubsan'} and all(row['passed'] is True and row['checks']==38748 and row['inventory_parser_cases']==37060 and row['session_transactions']==52 for row in cproof['modes'].values()),'NEW_INVENTORY_FOCUSED_CONTROLS')
for flag in ('historical_suites_executed','old8822_main_executed','real_auth_or_db','sockets_executed','actual_witness_body_inferred','source_generation_admitted','world_authority','global_aggregate_budget_admitted'):
    need(cproof[flag] is False,'C50_SOURCE_FIXTURE_ONLY')
oldraw=gzip.decompress((root/(C36+'.json.gz')).read_bytes())
need(len(oldraw)==25073 and hashlib.sha256(oldraw).hexdigest()=='8b4a16f704f53095d75c822f8f4635a707b8b965f2f1938888ff2d71c2449c1a','EXACT_HISTORICAL_C36')
old=json.loads(oldraw)['source_sha256']
changed={k for k,v in old.items() if current148.get(k)!=v}
need(changed==set(composition['inventory_previous_sha256'])==set(composition['inventory_current_sha256'])=={'native-android/engine/dbclient/coh_db_account_controls.c','native-android/engine/dbclient/coh_db_session.c','native-android/engine/dbclient/coh_db_session.h'} and all(old[k]==v for k,v in composition['inventory_previous_sha256'].items()) and all(current148[k]==v for k,v in composition['inventory_current_sha256'].items()) and len(old)-len(changed)==33,'EXACT_THREE_C36_PREDECESSORS_ONLY')
for name,expected in composition['inventory_previous_sha256'].items():
    prior=subprocess.check_output(['git','show',composition['inventory_predecessor_revision']+':'+name])
    need(len(prior)<2*1024**2 and hashlib.sha256(prior).hexdigest()==expected,'EXACT_ACCEPTED_HISTORICAL_BYTES')
need(subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==head,'SOURCE_HEAD_CHANGED')
result={'schema':'coh-fresh-auth-db-inventory13-source-admission-v1','passed':True,'source_revision':head,'source_sha256':pins,'host_controls_reexecuted':False,'historical_worker_commit_replayed_in_CI':False,'historical_C36_D128_D126_prefix106_used_as_current_maps':False,'runtime_executed':False,'normal_version_or_checksum_reference_admitted':False,'db_or_map_interoperability_verified':False,'first_unsupported_command_attributed':False,'body_acceptance_verified':False}
out=pathlib.Path(os.environ['RUNNER_TEMP'])/'auth-db-development-source-admission.json'
with out.open('xb') as stream:stream.write((json.dumps(result,indent=2,sort_keys=True)+'\n').encode())
print(json.dumps({'source_admission_passed':True,'frozen_pins':len(pins),'old_tests_replayed':False,'runtime_executed':False}))
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--pipeline-review', required=True)
    p.add_argument('--kernel-review', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    root = a.source_root.resolve()
    head = git(root, 'rev-parse', 'HEAD')
    old = yaml.safe_load(admitted(root, WORKFLOW, BASE_SHA))
    proof = json.loads(admitted(root, PROOF, PROOF_SHA))
    need(len(proof['source_inputs_sha256']) == 148, 'D148')
    current = proof['source_inputs_sha256']
    pins = {**current, **COMMON, **HISTORICAL, PROOF: PROOF_SHA}
    for name in (a.pipeline_review, a.kernel_review):
        pins[name] = sha(admitted(root, name))
    for name, digest in pins.items():
        admitted(root, name, digest)
    cproof = json.loads(gzip.decompress(admitted(root, C50+'.json.gz', C50_GZIP_SHA)))
    need(sha(gzip.decompress((root/(C50+'.json.gz')).read_bytes())) == C50_RAW_SHA, 'C50_RAW')
    admitted(root, C50+'-binding.json', C50_BINDING_SHA)
    review = json.loads((root/a.pipeline_review).read_bytes())
    kernel = json.loads((root/a.kernel_review).read_bytes())
    need(review['passed'] is True and review['source_inputs_sha256'] == current and
         review['additional_common_integration_source_sha256'] == COMMON, 'D148_REVIEW')
    field = source_field(kernel, cproof['source_sha256'])
    draft = copy.deepcopy(old)
    draft['name'] = 'Fresh original Auth to DB after complete bounded Inventory envelope validation'
    draft['jobs'] = {'matching-original-inventory13': next(iter(draft['jobs'].values()))}
    job = next(iter(draft['jobs'].values()))
    job['if'] = job['if'].replace('[auth-db-account-controls]', '[auth-db-inventory13]')
    code = '''import gzip,hashlib,json,os,pathlib,subprocess
def need(ok,code):
    if not ok:raise ValueError(code)
need(__debug__ and not os.environ.get('PYTHONOPTIMIZE'),'ASSERTIONS_REQUIRED')
need(os.name=='nt' and os.environ['RUNNER_ENVIRONMENT']=='github-hosted' and os.environ['RUNNER_OS']=='Windows' and os.environ['RUNNER_ARCH']=='X64','HOSTED_WINDOWS_X64_ONLY')
need(os.environ['GITHUB_REPOSITORY']=='Russianranger/coh-android' and os.environ['GITHUB_REF']=='refs/heads/native-android','OWNED_NATIVE_BRANCH_ONLY')
root=pathlib.Path.cwd().resolve()
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
need(head==os.environ['GITHUB_SHA'],'EXACT_HEAD')
'''
    values = {'PROOF': PROOF, 'REVIEW': a.pipeline_review, 'REVIEW_SCHEMA': review['schema'],
              'KERNEL_REVIEW': a.kernel_review, 'KERNEL_REVIEW_SCHEMA': kernel['schema'],
              'KERNEL_FIELD': field, 'C50': C50, 'C36': C36, 'METHODS': METHODS,
              'COMMON': COMMON, 'current148': current, 'pins': dict(sorted(pins.items()))}
    for name, value in values.items():
        code += name + '=' + pprint.pformat(value, sort_dicts=True, width=120) + '\n'
    code += GATE
    ast.parse(code)
    steps = job['steps']
    steps[3]['name'] = 'Admit current C50 Inventory and exact historical C36 source transitions before imports or recovery'
    steps[3]['run'] = "python - <<'PYINVENTORYSOURCE'\n" + code + 'PYINVENTORYSOURCE\n'
    steps[6]['name'] = 'Observe one fresh original Auth to DB after complete bounded Inventory validation'
    steps[7]['with']['name'] = 'auth-db-inventory13-${{ github.sha }}'
    previous = next(iter(old['jobs'].values()))['steps']
    need(len(steps) == 8 and all(steps[i].get('run') == previous[i].get('run')
         for i in (0, 1, 2, 4, 5, 6, 7)), 'UNCHANGED_RECOVERY_AND_RUNTIME_COMMANDS')
    need(steps[7]['with']['path'] == previous[7]['with']['path'], 'FIXED_PUBLIC_RECEIPT_ONLY')
    need(git(root, 'rev-parse', 'HEAD') == head, 'HEAD_CHANGED_DURING_DRAFT')
    a.output.write_text(yaml.safe_dump(draft, sort_keys=False, width=120))
    print(json.dumps({'passed': True, 'workflow_sha256': sha(a.output.read_bytes()),
        'workflow_bytes': a.output.stat().st_size, 'nonself_pins': len(pins), 'dynamic_self': True,
        'source_revision': head.decode().strip(), 'generator_sha256': sha(Path(__file__).read_bytes()),
        'project_imports_tests_compilers_native_services_downloads_executed': False}))


if __name__ == '__main__':
    main()
