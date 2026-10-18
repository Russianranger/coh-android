#!/usr/bin/env python3
"""Data-only successor with every old preflight/compiled source pin unchanged."""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import pprint
import subprocess
import yaml

BASE='18c9c4e1acee319e5bebc4fdc206f429ab6156cc'
WORKFLOW='.github/workflows/native-fresh-groups-observation.yml'
BASE_SHA='f0bbc00c9287e052763f9a9d9e71742b47900433d8e17c10052abe19ac1cd974'
CORE='native-android/engine/scenecatalog-server/check_source_snapshot_verifier.py'
CORE_SHA='6285a25fb727c86d6d2b9cd1eeacc3c1f398058f4dceb4821122a30a97600d6d'
WRAPPER='native-android/engine/scenecatalog-server/check_source_snapshot_verifier_status.py'
TEST='native-android/engine/scenecatalog-server/test_snapshot_status_adapter.py'
EVIDENCE='native-android/engine/scenecatalog-server/evidence/snapshot-status-adapter-20261018/'
CLOSURE='native-android/engine/scenecatalog-server/evidence/fresh-callback-profile-20261018/snapshot-failure-projection-static-review-20261018/recorded-native-closure.json'
F_REVIEW='native-android/combined-client/diagnostics/continuation-f-20261017/snapshot-status-adapter-review-20261018/review.json'

def need(ok,code):
    if not ok:raise ValueError(code)

def sha(raw):return hashlib.sha256(raw).hexdigest()

def git(root,revision,name):return subprocess.check_output(['git','show',revision+':'+name],cwd=root)

def committed(root,name):
    raw=(root/name).read_bytes();need(raw==git(root,'HEAD',name),'COMMITTED:'+name);return raw

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    root=a.root.resolve(strict=True);need(not a.output.exists() and not a.output.with_suffix('.draft.json').exists(),'FRESH_OUTPUT')
    before=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    baseline=git(root,BASE,WORKFLOW);need(sha(baseline)==BASE_SHA and committed(root,WORKFLOW)==baseline,'EXACT_18C_WORKFLOW')
    doc=yaml.safe_load(baseline);job=next(iter(doc['jobs'].values()));steps=job['steps'];need(len(steps)==17,'SAME_17_STEPS');original=copy.deepcopy(steps)
    prefix,body=steps[1]['run'].split('\n',1);body,suffix=body.rsplit('PYINVENTORYINITIALSOURCE',1)
    tree=ast.parse(body);assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='pins' for t in n.targets))
    pins=ast.literal_eval(assignment.value);old=dict(pins);need(len(old)==455 and pins[CORE]==CORE_SHA,'EXACT_455_OLD_SOURCE_MAP')
    closure=json.loads(committed(root,CLOSURE));need(closure['passed'] is True and closure['production_source_entries']==36,'RECORDED_NATIVE_CLOSURE')
    native=dict(closure['source_sha256']);native[CORE]=CORE_SHA
    for name,digest in native.items():need(sha(git(root,BASE,name))==sha(committed(root,name))==digest,'UNCHANGED_COMPLETE_RECORDED_NATIVE_CLOSURE:'+name)
    binding=json.loads(committed(root,EVIDENCE+'adapter-mocks-binding.json'));counts=json.loads(committed(root,EVIDENCE+'adapter-mocks.json'));reuse=json.loads(committed(root,EVIDENCE+'projection-reuse.json'));review=json.loads(committed(root,F_REVIEW))
    need(binding['schema']=='coh-snapshot-status-adapter-mock-binding-v1' and binding['passed'] is True and binding['attempt_count']==2 and binding['segmented_qualification'] is True and binding['reused_unchanged_methods']==25 and binding['corrected_method_cases']==3 and binding['returncode']==0 and binding['source_inputs_unchanged'] is True and binding['source_sha256']=={WRAPPER:sha(committed(root,WRAPPER)),TEST:sha(committed(root,TEST))},'EXACT_SEGMENTED_ADAPTER_MOCK_BINDING')
    need(counts['schema']=='coh-snapshot-status-adapter-mocks-v1' and counts['passed'] is True and counts['test_methods']>0 and counts['controlled_subtest_cases']>=0 and counts['mock_only'] is True and counts['old_projection_tests_reexecuted'] is False and counts['compiler_or_native_executed'] is False,'NEW_ADAPTER_CONTROLS_ONLY')
    need(reuse['schema']=='coh-snapshot-status-adapter-projection-reuse-v1' and reuse['passed'] is True and reuse['original_core_sha256']==CORE_SHA and reuse['wrapper_sha256']==sha(committed(root,WRAPPER)) and reuse['five_projection_helpers_AST_identical'] is True and reuse['old_projection_tests_reexecuted'] is False and reuse['recorded_native_source_sha256']==native,'EXACT_QUALIFIED_HELPER_REUSE')
    need(review['passed'] is True and review['wrapper_sha256']==sha(committed(root,WRAPPER)) and review['test_sha256']==sha(committed(root,TEST)) and review['reviewer_reexecuted_controls'] is False,'INDEPENDENT_ADAPTER_REVIEW')
    files=[WRAPPER,TEST,CLOSURE,F_REVIEW,EVIDENCE+'adapter-mocks-binding.json',EVIDENCE+'adapter-mocks.json',EVIDENCE+'adapter-mocks.stderr.txt',EVIDENCE+'projection-reuse.json']+list(reuse['qualified_historical_inputs'])+list(binding['retained_execution_and_derivation_inputs'])
    for name in files+list(native):
        digest=sha(committed(root,name));need(name not in pins or pins[name]==digest,'NO_OLD_PIN_SUPERSESSION:'+name);pins[name]=digest
    need(all(pins.get(k)==v for k,v in {**reuse['qualified_historical_inputs'],**binding['retained_execution_and_derivation_inputs']}.items()),'EXACT_RETAINED_REUSE_AND_EXECUTION_INPUTS')
    need(all(pins[k]==v for k,v in old.items()) and len(pins)<512,'EVERY_OLD_PIN_UNCHANGED')
    for name,digest in pins.items():need(sha(committed(root,name))==digest,'ALL_CURRENT_RAW_GIT:'+name)
    lines=body.splitlines(keepends=True);lines[assignment.lineno-1:assignment.end_lineno]=['pins='+pprint.pformat(dict(sorted(pins.items())),sort_dicts=True,width=120)+'\n'];body=''.join(lines)
    extra="""
adapter_binding=json.loads((root/'EVIDENCE_adapter-mocks-binding.json').read_bytes())
adapter_counts=json.loads((root/'EVIDENCE_adapter-mocks.json').read_bytes())
adapter_reuse=json.loads((root/'EVIDENCE_projection-reuse.json').read_bytes())
adapter_review=json.loads((root/'F_REVIEW').read_bytes())
need(adapter_binding['schema']=='coh-snapshot-status-adapter-mock-binding-v1' and adapter_binding['passed'] is True and adapter_binding['attempt_count']==2 and adapter_binding['segmented_qualification'] is True and adapter_binding['reused_unchanged_methods']==25 and adapter_binding['corrected_method_cases']==3 and adapter_binding['returncode']==0 and adapter_binding['source_inputs_unchanged'] is True and all(pins.get(k)==v for k,v in adapter_binding['source_sha256'].items()),'SEGMENTED_NEW_ADAPTER_MOCK_BINDING')
need(adapter_counts==FIXED_COUNTS,'EXACT_NEW_ADAPTER_MOCK_COUNTS')
need(adapter_reuse['schema']=='coh-snapshot-status-adapter-projection-reuse-v1' and adapter_reuse['passed'] is True and adapter_reuse['original_core_sha256']==pins['CORE'] and adapter_reuse['wrapper_sha256']==pins['WRAPPER'] and adapter_reuse['five_projection_helpers_AST_identical'] is True and adapter_reuse['old_projection_tests_reexecuted'] is False and all(pins.get(k)==v for k,v in adapter_reuse['qualified_historical_inputs'].items()) and all(pins.get(k)==v for k,v in adapter_binding['retained_execution_and_derivation_inputs'].items()) and len(adapter_reuse['recorded_native_source_sha256'])==36 and all(pins.get(k)==v for k,v in adapter_reuse['recorded_native_source_sha256'].items()),'QUALIFIED_PROJECTION_REUSE_ORIGINAL_CORE_UNCHANGED')
need(adapter_review['passed'] is True and adapter_review['wrapper_sha256']==pins['WRAPPER'] and adapter_review['test_sha256']==pins['TEST'] and adapter_review['reviewer_reexecuted_controls'] is False,'INDEPENDENT_STATUS_ADAPTER_REVIEW')
""".replace('EVIDENCE_',EVIDENCE).replace('F_REVIEW',F_REVIEW).replace('FIXED_COUNTS',repr(counts)).replace("'CORE'",repr(CORE)).replace("'WRAPPER'",repr(WRAPPER)).replace("'TEST'",repr(TEST))
    needle="need(subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==head,'SOURCE_HEAD_CHANGED')";need(body.count(needle)==1,'ONE_PREDICATE_INSERTION');body=body.replace(needle,extra+'\n'+needle);ast.parse(body)
    steps[1]['run']=prefix+'\n'+body+'PYINVENTORYINITIALSOURCE'+suffix;steps[1]['name']='Admit unchanged original Map and receiver plus separate fixed-status adapter'
    command=steps[11]['run'];boundary="python3 - <<'PYCODE'";need(command.count(boundary)==1,'ONE_CHECKER_BOUNDARY');direct,remaining=command.split(boundary,1)
    need(direct.count(CORE)==1 and direct.rstrip().endswith('verification.json"'),'EXACT_ORIGINAL_DIRECT_CHECKER_COMMAND');direct=direct.replace(CORE,WRAPPER)
    steps[11]['run']='set +e\n'+direct.rstrip()+' >out/groups-public/verifier-status.json\nverification_exit=$?\nset -e\ncat out/groups-public/verifier-status.json\nif [ "$verification_exit" -ne 0 ]; then exit "$verification_exit"; fi\n'+boundary+remaining
    steps[14]['with']['path']+='out/groups-public/verifier-status.json\n';steps[14]['with']['name']='fresh-status-adapter-groups-public-${{ github.sha }}'
    job['if']=job['if'].replace('[fresh-groups-inventory-initial-owner]','[fresh-groups-status-adapter]');doc['name']='Fresh original GROUPS with separately pinned verifier status adapter';doc['jobs']={'matching-original-status-adapter-observation':job}
    for index in range(17):
        if index not in {1,11,14}:need(steps[index]==original[index],'UNCHANGED_RUNTIME_FIXTURE_OR_EXPORT_STEP:'+str(index))
    need(subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==before,'HEAD_UNCHANGED')
    rendered=yaml.safe_dump(doc,sort_keys=False,width=120).encode();a.output.write_bytes(rendered)
    report={'schema':'coh-status-adapter-scene-workflow-draft-v1','passed':True,'source_revision':before,'workflow_sha256':sha(rendered),'workflow_bytes':len(rendered),'baseline_revision':BASE,'baseline_workflow_sha256':BASE_SHA,'baseline_nonself_pins':455,'current_nonself_pins':len(pins),'old_pins_superseded':[],'recorded_native_production_pins':36,'changed_step_indices':[1,11,14],'unchanged_original_checker_Map_PE_receiver_fixture_runtime_admitter_and_retention':True,'added_public_file_is_only_fixed_adapter_CLI_status':True,'native_compiler_loader_tests_private_capture_runtime_or_project_imports_executed':False,'read_only_Git_subprocesses_executed':True,'source_generation_admitted':False,'world_authority':False}
    a.output.with_suffix('.draft.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps(report,sort_keys=True))

if __name__=='__main__':main()
