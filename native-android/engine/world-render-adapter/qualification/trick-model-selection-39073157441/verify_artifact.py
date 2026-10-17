#!/usr/bin/env python3
"""Read-only review of retained CI bytes against the exact published git tree.

This checks proof/source bindings; it never executes any module or qualifier.
"""
import argparse,gzip,hashlib,io,json,pathlib,posixpath,re,subprocess,zipfile,stat

REVISION='91cacafa4451cf7504b5dd105f2790ae1c41739b'
TREE='499e397a7bc3eaf0d01a8b404317b94a2b97384b'
ZIP_SHA='54be63d80829412fb83cccf2f587f3bc8edb81d778261cd01bf1c13aa49462dd'
HERE=pathlib.Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
 assert not a.output.exists(),'fresh output required'
 def blob(path):
  # Some historical receipt entries contain an internal ../assets component.
  # Normalize only within the same exact published tree; never escape its root.
  path=posixpath.normpath(path)
  assert not pathlib.PurePosixPath(path).is_absolute() and '..' not in pathlib.PurePosixPath(path).parts,path
  return subprocess.check_output(['git','-C',a.source_root,'show',REVISION+':'+path])
 def decode(path):
  b=path.read_bytes()
  if path.suffix=='.gz':
   with gzip.GzipFile(fileobj=io.BytesIO(b))as stream:b=stream.read(1_048_577)
  assert len(b)<=1_048_576
  return json.loads(b)
 archive=(HERE/'artifact.zip').read_bytes();assert len(archive)==21884 and sha(archive)==ZIP_SHA
 with zipfile.ZipFile(io.BytesIO(archive))as z:
  assert len(z.infolist())==3 and set(z.namelist())=={'trick-model.json','power-boost-slots.json.gz','latest-owner-overlap.json'}
  assert sum(i.file_size for i in z.infolist())<1<<20 and z.testzip()is None
  for i in z.infolist():assert stat.S_ISREG(i.external_attr>>16)and not i.flag_bits&1 and z.read(i)==(HERE/i.filename).read_bytes()
 proofs={role:decode(HERE/name)for role,name in [('B','trick-model.json'),('C','power-boost-slots.json.gz'),('F','latest-owner-overlap.json')]};pins={};counts={}
 def pin(path,h,role):
  assert sha(blob(path))==h,(path,role)
  normalized=posixpath.normpath(path)
  assert normalized not in pins or pins[normalized]['sha256']==h,path
  pins.setdefault(normalized,{'sha256':h,'roles':[]})['roles'].append(role)
 for role,proof in proofs.items():
  assert proof['passed']is True and proof['source_revision']==REVISION
  for path,h in proof['source_sha256'].items():pin(path,h,role)
  counts[role]=len(proof['source_sha256'])
 b,c,f=(proofs[role]for role in ['B','C','F'])
 base='native-android/engine/world-render-adapter/qualification/trick-model-selection-20261017/host.json'
 old_b=json.loads(blob(base));assert b['source_sha256']==old_b['source_sha256']and b['input_sha256']==old_b['input_sha256']
 assert b['modes']==old_b['modes']and b['original_function_sha256_lf']==old_b['original_function_sha256_lf']
 assert b['production_mutations_refused']==old_b['production_mutations_refused']and len(b['production_mutations_refused'])==6
 cpp=b['actual_C_object_CPP_link_test'];assert cpp['passed']and cpp['executed']
 assert cpp['actual_whole_C_object_sha256']==b['standalone_public_exports']['release']['whole']['object_sha256']
 assert cpp['actual_detached_C_object_sha256']==b['standalone_public_exports']['release']['detached']['object_sha256']
 for name in ['SERVER_CLIENT_generation_equality','current_CLIENT_material_selection','material_or_GPU_owner_created','world_authority','android_execution']:assert b[name]is False,name
 old_c=json.loads(gzip.decompress(blob('native-android/engine/character-dictionary/qualification/power-boost-slots-20261017-final.json.gz')))
 assert c['source_sha256']==old_c['source_sha256']and c['cases']==old_c['cases']and len(c['cases'])==11
 assert c['modes'].keys()=={'release','asan','ubsan'}
 for mode,value in c['modes'].items():assert value['checks']==old_c['modes'][mode]['checks']and sum(x['checks']for x in value['checks'])==375012
 assert c['cpp_link_passed']is True
 for name in ['runtime_generation','actor_authority','whole_character_ReceivePowers_executed','power_LevelFinalize_executed','current_cache_loader_branch_executed','android_executed','original_win32_abi_executed']:assert c[name]is False,name
 base='native-android/combined-client/diagnostics/continuation-f-20261017/latest-owner-overlap/'
 pin(base+'qualify.py',f['audit_source_sha256'],'F_audit_script');pin(base+'HANDOFF.md',f['audit_handoff_sha256'],'F_audit_handoff')
 references={}
 for role,identity in f['qualified_receipts'].items():
  raw=blob(identity['path']);assert len(raw)==identity['bytes']and sha(raw)==identity['sha256']
  pin(identity['path'],identity['sha256'],'F_historical_receipt_'+role)
  prior=json.loads(gzip.decompress(raw)if identity['path'].endswith('.gz')else raw);assert prior['passed']is True;changes={}
  for name,h in prior.get('source_sha256',{}).items():
   path=identity['historical_absolute_path_comparison_only_remapping'].get(name,name);current=sha(blob(path))
   if current!=h:changes[path]={'historical_sha256':h,'current_sha256':current}
  assert len(prior.get('source_sha256',{}))==identity['source_hash_entries_checked']
  assert changes==identity['historical_source_changes_no_current_execution_requalification']
  references[role]={'receipt_sha256':identity['sha256'],'source_entries_compared':len(prior.get('source_sha256',{})),'historical_source_changes':len(changes)}
 assert sum(f['new_named_owner_bytes'].values())==f['new_named_owner_total']==3824536
 for phase in f['reference_phase_comparisons']:
  assert phase['reference_bytes']+phase['additional_named_owners']==phase['total_named_lower_bound']
  assert f['cap_bytes']-phase['total_named_lower_bound']==phase['allowance']
 assert f['reference_phase_comparisons'][0]['allowance']==-3235921
 assert f['host_layout_build']['matching_size_and_alignment']is True and f['host_layout_build']['module_functions_or_captures_executed']is False
 for name in ['current_parent_module_adapter_exists','actual_owner_retirement_observed_by_this_audit','Android_ABI_checked','RSS_measured','startup_improvement_measured','world_authority']:assert f[name]is False,name
 assert f['old_world_phase_numbers_are_historical_reference_not_current_pipeline_measurements']is True
 assert f['retirement_boundary']['arithmetic_credit_taken']is False and f['retirement_boundary']['production_handoff_executed']is False
 workflow='.github/workflows/native-source-selection.yml';pin(workflow,sha(blob(workflow)),'workflow')
 server='native-android/engine/scenecatalog-server/'
 for name in ['test_groups_public_summary.py','summarize_groups_capture.py','groups_capture_stages.py']:pin(server+name,sha(blob(server+name)),'A8_public_status_control_source')
 logs=(HERE/'job.log').read_text();tests=re.findall(r'(test_\w+) \(__main__\.Controls\.\1\) \.\.\. ok',logs)
 assert len(tests)==8 and len(set(tests))==8 and re.search(r'Ran 8 tests in [0-9.]+s',logs)and re.search(r'Z OK\n',logs)
 run=decode(HERE/'run.json');jobs=decode(HERE/'jobs.json')['jobs'];art=decode(HERE/'artifacts.json')['artifacts']
 assert run['head_sha']==REVISION and run['head_commit']['tree_id']==TREE and run['status']=='completed'and run['conclusion']=='success'and run['run_attempt']==1
 assert len(jobs)==1 and jobs[0]['id']==117514794401 and jobs[0]['conclusion']=='success'and all(s['conclusion']=='success'for s in jobs[0]['steps'])
 assert len(art)==1 and art[0]['id']==12115756974 and art[0]['workflow_run']['head_sha']==REVISION and art[0]['digest']=='sha256:'+ZIP_SHA
 result={'schema':'coh-focused-source-selection-artifact-review-v1','passed':True,'run_id':39073157441,'run_attempt':1,'job_id':117514794401,'source_revision':REVISION,'source_tree':TREE,'artifact_id':12115756974,'artifact_zip_bytes':21884,'artifact_zip_sha256':ZIP_SHA,'review_method':'Downloaded completed artifact; verified ZIP size/digest/CRC/member types, three proof revisions, every current source hash and eight historical receipt/difference maps against exact published git bytes; no qualifiers reexecuted.','verification_script_sha256':sha(pathlib.Path(__file__).read_bytes()),'distinct_source_receipt_workflow_pins_verified':len(pins),'source_role_counts':counts,'source_pins':dict(sorted(pins.items())),'F_historical_receipt_reference_verification':references,'B_actual_root_models_per_owner':3083,'B_historical_matches':1959,'B_historical_misses':1124,'B_distinct_selected_rows':528,'B_actual_name_file_disagreements':0,'B_checks_per_mode':301210,'B_original_comparisons_per_mode':28046,'B_semantic_mutations_refused':b['production_mutations_refused'],'B_actual_C_CPP_object_binding_verified':True,'C_checks_per_mode':375012,'C_profiles':11,'C_actual_C_CPP_link_reported':True,'F_C_CPP_layout_match':True,'F_new_named_owners_bytes':3824536,'F_historical_reference_old_candidate_named_overage_bytes':3235921,'F_historical_reference_only_not_current_fit':True,'A8_tests_passed':tests,'A8_result_is_log_bound_no_separate_artifact_member':True,'A8_public_status_control_only_not_capture':True,'current_CLIENT_generation_admitted':False,'SERVER_CLIENT_generation_equality':False,'current_material_or_GPU_owner_created':False,'actor_or_ACK_authority':False,'complete_parent_aggregate_budget_admitted':False,'Android_or_Thor_acceptance':False,'world_authority':False,'qualifiers_rerun_for_review':False}
 with a.output.open('x')as stream:json.dump(result,stream,indent=2);stream.write('\n')
 print(json.dumps({'passed':True,'distinct_pins':len(pins),'source_role_counts':counts,'A8_tests':len(tests),'report_sha256':sha(a.output.read_bytes())}))
if __name__=='__main__':main()
