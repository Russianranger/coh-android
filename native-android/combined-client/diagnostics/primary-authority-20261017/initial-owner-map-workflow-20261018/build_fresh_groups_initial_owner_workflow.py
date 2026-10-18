#!/usr/bin/env python3
"""Draft only the new Map observer build workflow from committed data.

No project helper, qualifier, compiler, native program or service is executed.
The coordinator owns the actual workflow copy and publication.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import yaml

WORKFLOW = '.github/workflows/native-fresh-groups-build.yml'
BASE_REVISION = '6e96fe22a567a3e252449feb37483cfea1566d8a'
BASE_WORKFLOW_SHA = 'a2adda1b06a824fa58bf5d36335fa060e360edbf25d6860a8e2148e10a87e851'
FOLDER = 'native-android/engine/scenecatalog-server/fresh_callback_observer/'
EVIDENCE = 'native-android/engine/scenecatalog-server/evidence/fresh-callback-profile-20261018/'
FOLLOWUP = EVIDENCE + 'initial-owner-followup.json'
QUALIFICATION = EVIDENCE + 'initial-owner-qualification.json'
FOLLOWUP_SHA = '550d600596e2939f73de076fac5fce859ce18248a0866e1b1d19795393dc03fb'
QUALIFICATION_SHA = '198176ce653c7ec267a12efd8c92bd2f890e6589fd65d1030026874d4953991c'
REVIEW_SCHEMA = 'coh-f-fresh-initial-owner-source-review-v1'
LOCAL = ('source_folder_profile.inc', 'source_folder_profile_api.h',
         'source_group_profile.inc', 'source_group_profile_api.h',
         'source_sealed_quiescence.inc', 'stage.py')
COMPILED_CHANGES = {'source_group_profile.inc', 'source_group_profile_api.h', 'stage.py'}
REASONS = ['INITIAL_SLOT_OUTSIDE_TABLE', 'INITIAL_STATE', 'INITIAL_OUTPUT_ENTINFO_ALIAS',
           'INITIAL_NOT_PLAYER', 'INITIAL_NOT_OWNED', 'INITIAL_PLAYER_ABSENT',
           'INITIAL_CLIENT_STATE', 'INITIAL_ENTITY_READY', 'INITIAL_RELAY',
           'INITIAL_TRANSFER_LOGIN', 'INITIAL_TRANSFER_ACTIVE',
           'INITIAL_TRANSFER_WAITING', 'INITIAL_TRANSFER_STEP']
MUTATIONS = {'missing_live_range', 'mixed_sleeping_bits', 'missing_entinfo_alias',
             'missing_owned', 'missing_client_phase', 'missing_transfer_step'}


def need(ok, code):
    if not ok:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(root, revision, path):
    return subprocess.check_output(['git', '-C', root, 'show', revision + ':' + path])


def maps(raw):
    """Read only the two literal dictionaries in the historical source gate."""
    document = yaml.safe_load(raw)
    steps = next(iter(document['jobs'].values()))['steps']
    code = '\n'.join(steps[3]['run'].splitlines()[1:-1])
    values = {}
    for node in ast.parse(code).body:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            continue
        name = node.targets[0].id
        if name == 'source':
            values[name] = ast.literal_eval(node.value)
        elif name == 'pins':
            need(isinstance(node.value, ast.Dict), 'HISTORICAL_PIN_LITERAL')
            pins = {}
            for key, value in zip(node.value.keys, node.value.values):
                if key is None:
                    group = values[value.id] if isinstance(value, ast.Name) else ast.literal_eval(value)
                    for path, digest in group.items():
                        need(path not in pins or pins[path] == digest, 'HISTORICAL_PIN_CONFLICT')
                        pins[path] = digest
                else:
                    path, digest = ast.literal_eval(key), ast.literal_eval(value)
                    need(path not in pins or pins[path] == digest, 'HISTORICAL_PIN_CONFLICT')
                    pins[path] = digest
            values[name] = pins
    need(len(values['source']) == 230 and len(values['pins']) == 240
         and WORKFLOW not in values['pins'], 'HISTORICAL_241_SCOPE')
    return document, values['pins']


GATE = r'''import hashlib,json,os,pathlib,subprocess

def need(ok,code):
    if not ok:raise ValueError(code)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pairs(rows):
    value={}
    for name,item in rows:
        need(name not in value,'DUPLICATE_JSON_FIELD');value[name]=item
    return value
def load(name):return json.loads((root/name).read_bytes(),object_pairs_hook=pairs)
def merge(target,group):
    for name,digest in group.items():
        need(name not in target or target[name]==digest,'SOURCE_PIN_CONFLICT');target[name]=digest

need(__debug__ and not os.environ.get('PYTHONOPTIMIZE'),'ASSERTIONS_REQUIRED')
need(os.name=='nt' and os.environ['RUNNER_ENVIRONMENT']=='github-hosted' and os.environ['RUNNER_OS']=='Windows' and os.environ['RUNNER_ARCH']=='X64','HOSTED_WINDOWS_X64_ONLY')
need(os.environ['GITHUB_REPOSITORY']=='Russianranger/coh-android' and os.environ['GITHUB_REF']=='refs/heads/native-android','OWNED_NATIVE_BRANCH_ONLY')
root=pathlib.Path.cwd().resolve();head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
need(head==os.environ['GITHUB_SHA'],'EXACT_HEAD')
source=__SOURCE__
prior=__PRIOR__
pins=dict(source);pins[__REVIEW_PATH__]=__REVIEW_SHA__
workflow=__WORKFLOW__
p=root/workflow
need(p.resolve()==p and p.is_file() and not p.is_symlink() and p.stat().st_size<1024**2,'WORKFLOW_REGULAR_SOURCE')
pins[workflow]=sha(p.read_bytes())
need(len(prior)==240 and len(source)==253 and len(pins)==255,'EXACT_CURRENT_AND_HISTORICAL_SOURCE_COUNTS')
tree=subprocess.check_output(['git','ls-tree','-r','-z','HEAD','--',*sorted(pins)]);blobs={}
for row in tree.split(b'\0'):
    if not row:continue
    meta,name=row.split(b'	',1);mode,kind,digest=meta.split()
    need(kind==b'blob' and mode in (b'100644',b'100755'),'TRACKED_SOURCE_MODE');blobs[name.decode()]=digest.decode()
need(set(blobs)==set(pins),'ALL_FROZEN_SOURCES_COMMITTED')
for name,digest in pins.items():
    rel=pathlib.PurePosixPath(name)
    need(not rel.is_absolute() and all(part not in ('','.','..') for part in rel.parts) and chr(92) not in name and ':' not in name,'RELATIVE_SOURCE_NAME')
    p=root/name
    need(p.resolve()==p and p.is_file() and not p.is_symlink() and 0<p.stat().st_size<2*1024**2,'BOUNDED_CANONICAL_SOURCE')
    raw=p.read_bytes()
    need(sha(raw)==digest and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blobs[name],'EXACT_REVIEWED_SOURCE_AND_PROOF')

# The old 241-pin build is immutable history. Its workflow self pin is removed;
# only the separately qualified six source replacements are permitted below.
historical=subprocess.check_output(['git','show',__BASE_REVISION__+':'+workflow])
need(sha(historical)==__BASE_WORKFLOW_SHA__,'HISTORICAL_WORKFLOW_BLOB')
# The reviewed generator parsed that exact blob's two literal maps. The hosted
# gate uses their frozen compact identity; it needs only standard-library JSON.
need(sha(json.dumps(prior,sort_keys=True,separators=(',',':')).encode())==__PRIOR_COMPACT_SHA__,'HISTORICAL_240_LITERAL_MAP')
followup=load(__FOLLOWUP__);qualification=load(__QUALIFICATION__);review=load(__REVIEW_PATH__)
need(followup['schema']=='coh-fresh-initial-owner-followup-v1' and followup['passed'] is True and qualification['schema']=='coh-fresh-initial-owner-host-v1' and qualification['passed'] is True,'EXACT_NEW_FOCUSED_PROOF_SCHEMAS')
need(followup['source_revision']==qualification['source_revision']==__QUALIFIED_REVISION__,'QUALIFIED_SOURCE_REVISION')
need(followup['qualification']['path']==__QUALIFICATION__ and followup['qualification']['bytes']==14859 and followup['qualification']['sha256']==pins[__QUALIFICATION__] and pins[__QUALIFICATION__]==__QUALIFICATION_SHA__,'QUALIFICATION_BYTE_BINDING')
need(len(followup['source_sha256'])==13 and qualification['source_sha256']==followup['source_sha256'] and len(followup['original_sha256_raw'])==15 and qualification['original_sha256_raw']==followup['original_sha256_raw'] and qualification['original_sha256_lf']==followup['original_sha256_lf'],'FULL_NEW_LOCAL_AND_ORIGINAL_CLOSURE')
changes={name for name,digest in prior.items() if source.get(name)!=digest}
need(changes==set(followup['superseded_source_pins']) and len(changes)==6,'ONLY_SIX_QUALIFIED_SUPERSESSIONS')
effective=dict(prior)
for name in changes:
    item=followup['superseded_source_pins'][name]
    need(prior[name]==item['previous_sha256'] and source[name]==item['sha256'],'EXACT_OLD_AND_NEW_SOURCE_BYTES');effective[name]=item['sha256']
need(set(followup['added_source_paths'])=={__FOLDER__+'INITIAL_OWNER_ELIGIBILITY.md',__FOLDER__+'check_initial_owner.py',__FOLDER__+'test_initial_owner.c'},'EXACT_THREE_NEW_LOCAL_PATHS')
for group in (followup['added_source_paths'],followup['source_sha256'],{'upstream/ouroboros/'+name:digest for name,digest in followup['original_sha256_raw'].items()},followup['unchanged_original_or_core_source_sha256']):merge(effective,group)
need(len(effective)==251 and len(followup['unchanged_original_or_core_source_sha256'])==9,'CURRENT_OWNER_AND_UNCHANGED_CORE_CLOSURE')
merge(effective,{__FOLLOWUP__:__FOLLOWUP_SHA__,__QUALIFICATION__:__QUALIFICATION_SHA__})
need(effective==source and review['schema']==__REVIEW_SCHEMA__ and review['passed'] is True and review['source_inputs_sha256']==source,'INDEPENDENT_CURRENT_EFFECTIVE_SOURCE_MAP')
need(followup['fresh_only_eligibility_extended'] is True and followup['original_entInUse_success_semantics_preserved'] is True,'EXPLICIT_FRESH_ONLY_ELIGIBILITY_POLICY')
for name in ('accepted_shared_owner_changed','entity_or_client_state_mutated','READY_or_ACK_behavior_changed','owner_record_schema_or_candidate_bytes_changed','actual_windows_pe_compiled_for_refinement','runtime_executed_for_qualification','native_receiver_reexecuted','source_generation_admitted','actor_authority','world_authority'):need(followup[name] is False,'SOURCE_ONLY_NO_STATE_OR_PROTOCOL_MUTATION')
for name in ('actual_sleeping_state_established','runtime_executed','whole_lifecycle_executed','original_win32_layout_qualified','leak_sanitizer_qualified','old_47_atom_oracle_replayed','old_folder_or_83_qualification_replayed','native_qualification_replayed','source_generation_admitted','world_authority'):need(qualification[name] is False,'PRECISE_HOST_QUALIFICATION_SCOPE')
need(qualification['one_gate_exact_reverse'] is True and qualification['specializer_refusal_controls']==3 and qualification['host_member_subset_storage_only'] is True and qualification['host_type_access_counter'] is True,'ONE_GATE_SPECIALIZATION_AND_HOST_STORAGE_SCOPE')
need(set(qualification['modes'])=={'release','address','undefined'},'EXACT_THREE_NEW_MODES')
for name,mode in qualification['modes'].items():
    c=mode['controls']
    need(c['passed'] is True and c['checks']==8398 and c['scenarios']==208 and c['refusals']==176 and c['fallback_guard_refusals']==13 and c['unchanged_active_successes']==30 and c['sleeping_successes']==1 and c['reason_names']==__REASONS__ and c['runtime_executed'] is False and c['world_authority'] is False,'NEW_FOCUSED_CONTROLS')
    need(followup['host_controls']['modes'][name]==c,'WRAPPER_MODE_BINDING')
need(set(qualification['mutations'])==__MUTATIONS__ and all(value['refused'] is True for value in qualification['mutations'].values()) and followup['host_controls']['mutations']==qualification['mutations'],'SIX_NEW_MUTATIONS_REFUSED')
need(qualification['parser']['checks']==31 and qualification['parser']['fixed_additional_reasons']==__REASONS__ and qualification['parser']['file_or_child_collection_replayed'] is False and followup['host_controls']['parser']==qualification['parser'],'FIXED_PURE_PARSER_SCOPE')
protocol=followup['protocol'];fingerprint=followup['compiled_source_fingerprint']
need(protocol['source_probe_schema']=='coh-fresh-source-profile-probe-v2' and protocol['source_keys']==36 and protocol['public_schema']=='coh-fresh-source-profile-diagnostic-v2' and protocol['public_keys']==43 and protocol['additional_fixed_owner_failure_names']==__REASONS__ and protocol['raw_values_or_identity_exported'] is False,'UNCHANGED_SCHEMA_FIXED_REFUSAL_ENUM_ONLY')
need(fingerprint['build_role']=='nonshipping_fresh_callback_sealed_groups_observer' and fingerprint['compile_schema']=='coh-fresh-groups-observer-compile-v1' and fingerprint['compile_cli_changed'] is False and fingerprint['declared_compile_artifact_count']==19 and fingerprint['new_map_only_compile_required'] is True and fingerprint['new_map_PE_compiled'] is False,'NEW_MAP_ONLY_COMPILE_REQUIRED')
need(fingerprint['keys']==__LOCAL__ and set(fingerprint['changed'])==__COMPILED_CHANGES__ and len(fingerprint['previous'])==len(fingerprint['current'])==6,'SAME_SIX_COMPILED_NAMES_EXACT_THREE_CHANGES')
for name in __LOCAL__:
    need(source[__FOLDER__+name]==fingerprint['current'][name],'CURRENT_COMPILED_SOURCE_PIN')
    if name in __COMPILED_CHANGES__:need(fingerprint['changed'][name]=={'previous_sha256':fingerprint['previous'][name],'sha256':fingerprint['current'][name]},'DECLARED_COMPILED_SUPERSESSION')
    else:need(fingerprint['previous'][name]==fingerprint['current'][name],'UNCHANGED_OTHER_COMPILED_SLOTS')
missing=followup['actual_missing_witness']
need(missing['owner_failure']=='ENTITY_NOT_IN_USE' and missing['literal_failed_atom']=='!entInUse(entity->owner)' and missing['entInUse_includes_live_range_and_state'] is True and missing['actual_sleeping_state_established'] is False and missing['native_timeout_cause_established'] is False,'ACTUAL_OLD_FAILURE_REMAINS_CONDITIONAL')
need(subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==head,'SOURCE_HEAD_CHANGED')
result={'schema':'coh-fresh-initial-owner-build-source-admission-v1','passed':True,'source_revision':head,'source_sha256':pins,'frozen_independent_review_sha256':pins[__REVIEW_PATH__],'host_controls_reexecuted':False,'historical_worker_commit_replayed_in_CI':False,'compile_only':True,'runtime_executed':False,'accepted_observer_equivalence':False,'actual_sleeping_state_established':False,'source_generation_admitted':False,'world_authority':False}
out=pathlib.Path(os.environ['RUNNER_TEMP'])/'fresh-groups-source-admission.json'
with out.open('xb') as stream:stream.write((json.dumps(result,indent=2,sort_keys=True)+'\n').encode())
print(json.dumps({'source_admission_passed':True,'frozen_pins':len(pins),'old_tests_replayed':False,'runtime_executed':False}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--review', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve(strict=True)
    need(not args.output.exists() and not args.output.is_symlink()
         and not args.output.with_suffix('.draft.json').exists(), 'FRESH_OUTPUT_REQUIRED')
    historical = git(root, BASE_REVISION, WORKFLOW)
    need(sha(historical) == BASE_WORKFLOW_SHA, 'EXACT_HISTORICAL_WORKFLOW')
    need((root / WORKFLOW).read_bytes() == historical, 'CURRENT_BASE_WORKFLOW_CHANGED')
    document, prior = maps(historical)
    old_steps = next(iter(document['jobs'].values()))['steps']
    before_steps = json.loads(json.dumps(old_steps))
    followup = json.loads((root / FOLLOWUP).read_bytes())
    qualification = json.loads((root / QUALIFICATION).read_bytes())
    need(sha((root / FOLLOWUP).read_bytes()) == FOLLOWUP_SHA and
         sha((root / QUALIFICATION).read_bytes()) == QUALIFICATION_SHA, 'FROZEN_NEW_PROOF_BYTES')
    need(followup['passed'] is qualification['passed'] is True, 'NEW_PROOFS_PASSED')
    source = dict(prior)
    supersessions = followup['superseded_source_pins']
    need(len(supersessions) == 6 and set(supersessions) <= set(source), 'SIX_PRIOR_PATHS_ONLY')
    for name, item in supersessions.items():
        need(source[name] == item['previous_sha256'], 'QUALIFIED_PREDECESSOR_PIN')
        source[name] = item['sha256']
    for group in (followup['added_source_paths'], followup['source_sha256'],
                  {'upstream/ouroboros/' + name: digest for name, digest in followup['original_sha256_raw'].items()},
                  followup['unchanged_original_or_core_source_sha256'],
                  {FOLLOWUP: FOLLOWUP_SHA, QUALIFICATION: QUALIFICATION_SHA}):
        for name, digest in group.items():
            need(name not in source or source[name] == digest, 'UNQUALIFIED_SOURCE_CONFLICT')
            source[name] = digest
    review_bytes = (root / args.review).read_bytes()
    review = json.loads(review_bytes)
    need(review['schema'] == REVIEW_SCHEMA and review['passed'] is True and
         review['source_inputs_sha256'] == source and len(source) == 253, 'INDEPENDENT_EXACT_CURRENT_REVIEW')
    frozen = {**source, args.review: sha(review_bytes)}
    revision = subprocess.check_output(['git', '-C', root, 'rev-parse', 'HEAD'], text=True).strip()
    for name, digest in frozen.items():
        path = root / name
        need(path.resolve() == path and path.is_file() and not path.is_symlink(), 'CANONICAL_SOURCE')
        raw = path.read_bytes()
        need(sha(raw) == digest and git(root, revision, name) == raw, 'CURRENT_COMMITTED_SOURCE')
    replacements = {'SOURCE': source, 'PRIOR': prior, 'REVIEW_PATH': args.review,
                    'REVIEW_SHA': sha(review_bytes), 'WORKFLOW': WORKFLOW,
                    'BASE_REVISION': BASE_REVISION, 'BASE_WORKFLOW_SHA': BASE_WORKFLOW_SHA,
                    'PRIOR_COMPACT_SHA': sha(json.dumps(prior, sort_keys=True, separators=(',', ':')).encode()),
                    'FOLLOWUP': FOLLOWUP, 'QUALIFICATION': QUALIFICATION,
                    'QUALIFICATION_SHA': QUALIFICATION_SHA, 'FOLLOWUP_SHA': FOLLOWUP_SHA,
                    'REVIEW_SCHEMA': REVIEW_SCHEMA, 'QUALIFIED_REVISION': followup['source_revision'],
                    'FOLDER': FOLDER, 'LOCAL': list(LOCAL), 'COMPILED_CHANGES': COMPILED_CHANGES,
                    'REASONS': REASONS, 'MUTATIONS': MUTATIONS}
    code = GATE
    for key, value in replacements.items():
        literal = 'set(' + repr(sorted(value)) + ')' if isinstance(value, set) else repr(value)
        code = code.replace('__' + key + '__', literal)
    ast.parse(code)
    document['name'] = 'Build original MapServer observer with fresh pre-entry owner eligibility'
    job = next(iter(document['jobs'].values()))
    document['jobs'] = {'fresh-original-initial-owner-compile': job}
    job['if'] = job['if'].replace('[fresh-groups-owner-reason-build]', '[fresh-groups-initial-owner-build]')
    job['steps'][3] = {'id': 'source_admission', 'name': 'Admit the new initial-owner proof and exact current build closure before project imports',
                       'shell': 'bash', 'run': "python - <<'PYINITIALOWNERSOURCE'\n" + code + 'PYINITIALOWNERSOURCE\n'}
    job['steps'][-1]['with']['name'] = 'fresh-groups-initial-owner-build-${{ github.sha }}'
    for index in range(len(before_steps)):
        if index not in (3, 10):
            need(job['steps'][index] == before_steps[index], 'UNCHANGED_BUILD_AND_RECOVERY_STEPS')
    before_upload = dict(before_steps[10]['with']); before_upload.pop('name')
    after_upload = dict(job['steps'][10]['with']); after_upload.pop('name')
    need(before_upload == after_upload and job['steps'][9]['if'] == "always() && steps.source_admission.outcome == 'success'", 'UNCHANGED_BOUNDED_RECOVERY_AND_UPLOAD')
    raw = yaml.safe_dump(document, sort_keys=False, width=120).encode()
    draft = {'schema': 'coh-fresh-initial-owner-build-workflow-draft-v1', 'passed': True,
             'source_revision': revision, 'workflow_bytes': len(raw), 'workflow_sha256': sha(raw),
             'generator_sha256': sha(Path(__file__).read_bytes()), 'source_inputs': len(source),
             'nonself_pins': len(frozen), 'self_inclusive_pins': len(frozen) + 1,
             'baseline_workflow_sha256': BASE_WORKFLOW_SHA, 'historical_241_preserved': True,
             'supersessions': supersessions, 'unchanged_step_indices': [0, 1, 2, 4, 5, 6, 7, 8, 9],
             'new_qualifier_or_project_imports_executed': False, 'compiler_native_or_runtime_executed': False,
             'root_repository_mutated': False}
    need(subprocess.check_output(['git', '-C', root, 'rev-parse', 'HEAD'], text=True).strip() == revision, 'SOURCE_HEAD_CHANGED')
    for name, digest in frozen.items():
        need(sha((root / name).read_bytes()) == digest, 'FINAL_SOURCE_CHANGED')
    with args.output.open('xb') as stream:
        stream.write(raw)
    with args.output.with_suffix('.draft.json').open('x') as stream:
        stream.write(json.dumps(draft, indent=2, sort_keys=True) + '\n')
    print(json.dumps(draft, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
