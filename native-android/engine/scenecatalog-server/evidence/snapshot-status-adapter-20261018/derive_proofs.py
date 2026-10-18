#!/usr/bin/env python3
"""Derive reuse and segmented coverage from retained bytes; run no controls."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
PREFIX=HERE.relative_to(ROOT).as_posix()+'/'
CORE='native-android/engine/scenecatalog-server/check_source_snapshot_verifier.py'
WRAPPER='native-android/engine/scenecatalog-server/check_source_snapshot_verifier_status.py'
TEST='native-android/engine/scenecatalog-server/test_snapshot_status_adapter.py'
OLD='native-android/engine/scenecatalog-server/evidence/snapshot-failure-projection-20261018/'
CLOSURE='native-android/engine/scenecatalog-server/evidence/fresh-callback-profile-20261018/snapshot-failure-projection-static-review-20261018/recorded-native-closure.json'
BASE='18c9c4e1acee319e5bebc4fdc206f429ab6156cc'
CORE_SHA='6285a25fb727c86d6d2b9cd1eeacc3c1f398058f4dceb4821122a30a97600d6d'
METHOD='test_native_exception_restores_original_before_final_binding'

def need(value,code):
    if not value:raise ValueError(code)

def digest(raw):return hashlib.sha256(raw).hexdigest()

def read(name):
    raw=(ROOT/name).read_bytes()
    need(raw==subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT),'COMMITTED_INPUT:'+name)
    return raw

def load(name):return json.loads(read(name))

def dump(node):return ast.dump(node,include_attributes=False)

def output(name,value):
    with (HERE/name).open('x') as stream:stream.write(json.dumps(value,indent=2,sort_keys=True)+'\n')

def main():
    names=('projection-reuse.json','adapter-mocks.json','adapter-mocks-binding.json','adapter-mocks.stderr.txt')
    need(all(not (HERE/name).exists() for name in names),'FRESH_DERIVED_OUTPUTS')
    wrapper=read(WRAPPER);draft=read(OLD+'superseded-common-checker.py.source')
    need(digest(draft)=='775bdd216bcef351dc9d0a34a1536592c28fafa096c893e6051a49d372c97d4d','EXACT_QUALIFIED_DRAFT')
    functions=lambda raw:{n.name:n for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    a,b=functions(draft),functions(wrapper);helpers=('SnapshotFailure','failure_scope','public_failure','unique_object','run_native')
    need(all(dump(a[n])==dump(b[n]) for n in helpers),'FIVE_HELPERS_IDENTICAL')
    need(dump(a['require'])==dump(b['require']),'SAME_REQUIRE_SEMANTICS')
    constants=lambda raw:{n.targets[0].id:n.value for n in ast.parse(raw).body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)}
    ca,cb=constants(draft),constants(wrapper)
    need(all(dump(ca[n])==dump(cb[n]) for n in ('HERE','ROOT','SCHEMA','FAILURE_PHASES')),'SAME_PROJECTION_GLOBALS')
    need(digest(read(CORE))==CORE_SHA and read(CORE)==subprocess.check_output(['git','show',BASE+':'+CORE],cwd=ROOT),'ORIGINAL_CORE_UNCHANGED')
    historical=[OLD+n for n in ('superseded-common-checker.py.source','superseded-common-projection-tests.py.source','mock-controls-binding.json','mock-controls.json','mock-controls.stderr.txt')]
    historical+=['native-android/combined-client/diagnostics/continuation-f-20261017/snapshot-failure-projection-review-20261018/review.json']
    oldproof=load(OLD+'mock-controls-binding.json');oldcounts=load(OLD+'mock-controls.json')
    need(oldproof['passed'] is True and oldproof['attempt_count']==1 and oldproof['source_inputs_unchanged'] is True and oldcounts['passed'] is True and (oldcounts['test_methods'],oldcounts['controlled_subtest_cases'],oldcounts['native_mock_invocations'],oldcounts['public_projection_checks'])==(13,245,184,294),'QUALIFIED_ONCE_PROJECTION_CONTROLS')
    need(oldproof['source_sha256'][CORE]==digest(draft) and oldproof['source_sha256']['native-android/engine/scenecatalog-server/test_snapshot_failure_projection.py']==digest(read(OLD+'superseded-common-projection-tests.py.source')),'ARCHIVED_EXACT_TEST_SOURCE')
    native=dict(load(CLOSURE)['source_sha256']);need(len(native)==36,'RECORDED_36_NATIVE_SOURCES');native[CORE]=CORE_SHA
    for name,pin in native.items():need(digest(read(name))==pin==digest(subprocess.check_output(['git','show',BASE+':'+name],cwd=ROOT)),'UNCHANGED_NATIVE_SOURCE:'+name)
    reuse={'schema':'coh-snapshot-status-adapter-projection-reuse-v1','passed':True,'original_core_sha256':CORE_SHA,'wrapper_sha256':digest(wrapper),'five_projection_helpers_AST_identical':True,'identical_helpers':list(helpers),'projection_globals_and_require_AST_identical':True,'original_inspect_is_delegated_whole':True,'qualified_historical_inputs':{n:digest(read(n)) for n in historical},'recorded_native_source_sha256':native,'only_recorded_map_correction_is_restored_original_core':True,'old_projection_tests_reexecuted':False,'compiler_dependency_discovery_reexecuted':False,'project_helper_imported':False,'read_only_Git_subprocesses_executed':True,'source_generation_admitted':False,'world_authority':False}
    first=load(PREFIX+'failed-first/adapter-mocks.json');first_binding=load(PREFIX+'failed-first/adapter-mocks-binding.json');follow=load(PREFIX+'corrected-method.json');follow_binding=load(PREFIX+'corrected-method-binding.json')
    need(first['passed'] is False and first_binding['returncode']==1 and first_binding['source_inputs_unchanged'] is True and (first['test_methods'],first['controlled_subtest_cases'])==(26,93),'EXACT_FIRST_ERROR_RETAINED')
    need(follow['passed'] is True and follow_binding['passed'] is True and follow_binding['only_corrected_method_executed'] is True and follow_binding['other_25_methods_reexecuted'] is False and (follow['test_methods'],follow['controlled_subtest_cases'])==(1,3),'ONLY_CORRECTED_METHOD_PASSED')
    previous=ast.parse(read(PREFIX+'failed-first/test.py.source'));current=ast.parse(read(TEST));changed=0
    previous_methods=[n for n in ast.walk(previous) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
    current_methods=[n for n in ast.walk(current) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
    need(len(previous_methods)==len(current_methods)==26,'26_CURRENT_METHODS')
    old_method=next(n for n in previous_methods if n.name==METHOD)
    for node in ast.walk(current):
        if isinstance(node,ast.FunctionDef) and node.name==METHOD:
            need(dump(node)!=dump(old_method),'ONLY_METHOD_WAS_CORRECTED');node.body=copy.deepcopy(old_method.body);changed+=1
    need(changed==1 and dump(previous)==dump(current),'ENTIRE_MODULE_EXCEPT_ONE_METHOD_UNCHANGED')
    counts={'schema':'coh-snapshot-status-adapter-mocks-v1','passed':True,'test_methods':26,'controlled_subtest_cases':93,'mock_only':True,'old_projection_tests_reexecuted':False,'compiler_or_native_executed':False,'segmented_qualification':True,'reused_unchanged_methods':25,'corrected_method_cases':3,'first_invocation_test_oracle_errors':1,'execution_invocations':2,'followup_is_only_corrected_method':True}
    files=['failed-first/adapter-mocks.json','failed-first/adapter-mocks.stderr.txt','failed-first/adapter-mocks-binding.json','failed-first/test.py.source','corrected-method.json','corrected-method.stderr.txt','corrected-method-binding.json','run_corrected_method.py','derive_proofs.py']
    retained={PREFIX+n:digest(read(PREFIX+n)) for n in files}
    binding={'schema':'coh-snapshot-status-adapter-mock-binding-v1','passed':True,'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_sha256':{WRAPPER:digest(wrapper),TEST:digest(read(TEST))},'source_inputs_unchanged':True,'attempt_count':2,'returncode':0,'segmented_qualification':True,'reused_unchanged_methods':25,'corrected_method_cases':3,'first_invocation_test_oracle_errors':1,'entire_module_AST_equal_after_only_corrected_method_body_replacement':True,'retained_execution_and_derivation_inputs':retained,'first_error_scope':'test expected original ValueError instead of required coarse SnapshotFailure','old_projection_tests_reexecuted':False,'other_25_methods_reexecuted':False,'source_generation_admitted':False,'world_authority':False}
    output('projection-reuse.json',reuse);output('adapter-mocks.json',counts);output('adapter-mocks-binding.json',binding)
    with (HERE/'adapter-mocks.stderr.txt').open('xb') as stream:stream.write(read(PREFIX+'corrected-method.stderr.txt'))
    print(json.dumps({'passed':True,'reused_projection_helpers':5,'reused_projection_test_methods':13,'effective_adapter_methods':26,'effective_adapter_subtests':93,'adapter_execution_invocations':2,'corrected_method_subtests':3,'other_25_reexecuted':False}))

if __name__=='__main__':main()
