"""New EDITMSG evidence/gate mocks only; never execute loader/native/compiler."""
from contextlib import ExitStack
import ast,copy,gzip,hashlib,importlib.util,json,os
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile,unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
ROOT=next((p for p in HERE.parents if (p/'native-android/engine').is_dir()),HERE.parent/'coh-android')
SPEC=importlib.util.spec_from_file_location('editmsg_receiver_proposal',HERE/'admit_editmsg_initial_receiver.py')
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)
CASES=0
def counted():
 global CASES
 CASES+=1
class Controls(unittest.TestCase):
 def setUp(self):
  self.guard=patch.object(M.subprocess,'Popen',side_effect=AssertionError('No subprocess permitted in mocked controls'));self.guard.start();self.addCleanup(self.guard.stop)
 def metadata(self):
  return {'FOLLOWUP':M.PREFIX+'mock/source-profile.json','FOLLOWUP_SHA':'a'*64,'FOLLOWUP_BYTES':123,
          'PROFILE_SCHEMA':M.PROFILE_SCHEMA,'REVIEW_SHA':'b'*64,'REVIEW_BYTES':456,
          'OBSERVER_BUILD':M.PREFIX+'mock/observer-build.json','OBSERVER_BUILD_SHA':'d'*64,'OBSERVER_BUILD_BYTES':789}
 def patches(self,values):
  stack=ExitStack()
  for key,value in values.items():stack.enter_context(patch.object(M,key,value))
  return stack
 def test_immutable_loader_copy_import_cleanup_core_AST(self):
  before=ast.parse((ROOT/'native-android/combined-client/tools/admit_retained_initial_receiver.py').read_bytes());after=ast.parse((HERE/'admit_editmsg_initial_receiver.py').read_bytes())
  old={n.name:ast.dump(n,include_attributes=False)for n in before.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};new={n.name:ast.dump(n,include_attributes=False)for n in after.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
  self.assertEqual({n for n in old if old[n]!=new[n]},{'evidence','admit_gate','admit'})
  for name in old:
   if name not in ('evidence','admit_gate','admit'):counted();self.assertEqual(old[name],new[name])
  # Only receipt schema/count literals change in the otherwise exact admit flow.
  def normalize(function):
   node=copy.deepcopy(function)
   for part in ast.walk(node):
    if isinstance(part,ast.Constant)and part.value=='coh-editmsg-initial-receiver-reuse-v1':part.value='coh-retained-initial-receiver-reuse-v1'
    elif isinstance(part,ast.Constant)and part.value==123:part.value=151
    elif isinstance(part,ast.Constant)and part.value==15:part.value=12
   return ast.dump(node,include_attributes=False)
  counted();self.assertEqual(old['admit'],normalize(next(n for n in after.body if isinstance(n,ast.FunctionDef)and n.name=='admit')))
 def test_unfrozen_draft_refuses_before_file_or_project_execution(self):
  counted();M.frozen_metadata()
  counted()
  with patch.object(M,'FOLLOWUP_SHA',None),patch.object(M,'raw',side_effect=AssertionError('unfrozen input must not be read')),patch.object(M.importlib,'import_module',side_effect=AssertionError('no import')):
   with self.assertRaises(M.Refused)as caught:M.evidence(ROOT)
   self.assertEqual(caught.exception.code,'EVIDENCE_NOT_FROZEN')
 def test_evidence_exact_new_receipt_source8_and15_statuses(self):
  original=gzip.decompress((ROOT/(M.OLD+'build.json.gz')).read_bytes());build=json.loads(original)
  mapping=json.loads((ROOT/(M.REVIEW+'review.json')).read_bytes())['current_project_consumer_dependencies']['sha256'];self.assertEqual(len(mapping),43)
  for mode in ('good','old151','old_scope','source8_missing','source8_wrong','status','map','ELF','static'):
   counted();item=copy.deepcopy(build)
   if mode=='old151':item['modes']['release']['tests']['checks']=151
   if mode=='old_scope':item['old151_controls_reexecuted']=True
   if mode=='source8_missing':item['source_sha256'].pop('upstream/ouroboros/Game/src/edit/edit_net.c')
   if mode=='source8_wrong':item['original_editmsg_fixtures']['whole_source_sha256_lf']['Game/src/edit/edit_net.c']='f'*64
   if mode=='status':item['modes']['release']['tests']['fixed_status_stdout']['editmsg-captured']['sha256']='f'*64
   if mode=='ELF':item['modes']['release']['sha256']='f'*64
   statuses={entry['file']:{**entry,'repository_path':M.STATUS_ROOT+entry['file']}for val in build['modes'].values()for entry in val['tests']['fixed_status_stdout'].values()}
   review={'schema':M.REVIEW_SCHEMA,'passed':True,'historical_build_source_revision':M.HISTORICAL,
           'current_project_consumer_dependencies':{'sha256':mapping},
           'historical_controls':{'safe_status_files_verified':statuses},
           'static_ELF':{'interpreter':M.INTERPRETER,'needed':M.NEEDED,'required_versions':M.VERSIONS,'RPATH':False,'RUNPATH':False,'readelf_outputs':{}}}
   if mode=='map':review['current_project_consumer_dependencies']['sha256']={**mapping,next(iter(mapping)):'f'*64}
   if mode=='static':review['static_ELF']['RUNPATH']=True
   receipt=json.dumps(item).encode();zipped=gzip.compress(receipt,mtime=0);review_raw=json.dumps(review).encode();observer=b'mocked observer build';values={**self.metadata(),'BUILD_SHA':M.digest(receipt),'BUILD_BYTES':len(receipt),'GZIP_SHA':M.digest(zipped),'GZIP_BYTES':len(zipped),'REVIEW_SHA':M.digest(review_raw),'REVIEW_BYTES':len(review_raw),'OBSERVER_BUILD_SHA':M.digest(observer),'OBSERVER_BUILD_BYTES':len(observer)}
   actual=M.raw
   def read(path,*args):
    relative=path.relative_to(ROOT).as_posix()
    if relative==M.OLD+'build.json.gz':return zipped
    if relative==M.REVIEW+'review.json':return review_raw
    if relative==M.OBSERVER_BUILD:return observer
    return actual(path,*args)
   with self.patches(values),patch.object(M,'raw',side_effect=read),patch.object(M.importlib,'import_module',side_effect=AssertionError('no project import')):
    if mode=='good':
     binary,raw,got,pins=M.evidence(ROOT);self.assertEqual(raw,receipt);self.assertEqual(M.digest(binary),M.ELF_SHA);self.assertEqual(got,mapping);self.assertEqual(len([n for n in pins if n.startswith(M.STATUS_ROOT+'status-')]),15);self.assertEqual(len(item['original_editmsg_fixtures']['whole_source_sha256_lf']),8);self.assertTrue(all(pins['upstream/ouroboros/'+n]==item['source_sha256']['upstream/ouroboros/'+n]for n in item['original_editmsg_fixtures']['whole_source_sha256_lf']))
    else:
     with self.assertRaises(M.Refused):M.evidence(ROOT)
 def test_exact_gate_278_A4_new43_and_preimport_refusals(self):
  old_raw=(ROOT/M.OLD_GATE).read_bytes();old=json.loads(old_raw)['current_278_pin_map'];mapping=json.loads((ROOT/(M.REVIEW+'review.json')).read_bytes())['current_project_consumer_dependencies']['sha256']
  actual_profile=json.loads((ROOT/M.FOLLOWUP).read_bytes());updates=actual_profile['source_sha256'];candidates=list(updates);self.assertEqual(len(updates),4);self.assertTrue(actual_profile['actual_failed_observation']['runtime_executed'])
  revision='c'*40;own='native-android/combined-client/tools/admit_editmsg_initial_receiver.py';artifact='mock/artifact'
  for mode in ('good','schema','keys','revision','runtime','receiver-pin','observer-pin','profile-pin','A4-pin','old-A4','previous','new43','foreign-map-change','self','artifact','head','profile-schema','qualification-runtime','server-runtime','compiler-runtime','process-launch','A4-count','workflow-changed','workflow-missing'):
   counted();profile=copy.deepcopy(actual_profile)
   if mode=='previous':profile['previous_source_sha256'][candidates[0]]='f'*64
   if mode=='profile-schema':profile['schema']='foreign'
   if mode=='qualification-runtime':profile['runtime_executed_for_fix_qualification']=True
   if mode=='server-runtime':profile['server_executed']=True
   if mode=='compiler-runtime':profile['compiler_executed']=True
   if mode=='process-launch':profile['process_launch_not_exercised']=False
   if mode=='A4-count':profile['source_sha256'].pop(candidates[0])
   profile_raw=json.dumps(profile).encode();review={'current_project_consumer_dependencies':{'sha256':dict(mapping)}}
   if mode=='foreign-map-change':review['current_project_consumer_dependencies']['sha256'][next(n for n in mapping if n.endswith('coh_replication.c'))]='f'*64
   review_raw=json.dumps(review).encode();pins={**old,**updates,**mapping,own:'a'*64,artifact:'b'*64};gate={'schema':'coh-editmsg-fresh-groups-live-source-admission-v1','passed':True,'source_revision':revision,'source_sha256':pins,'host_controls_reexecuted':False,'historical_worker_commit_replayed_in_CI':False,'source_preflight_only':True,'runtime_executed':False,'accepted_observer_equivalence':False,'source_generation_admitted':False,'world_authority':False,'observer_compile_receipt_sha256':'d'*64,'receiver_build_receipt_sha256':M.BUILD_SHA,'source_profile_proof_sha256':M.digest(profile_raw)}
   if mode=='schema':gate['schema']='foreign'
   if mode=='keys':gate['foreign']=False
   if mode=='revision':gate['source_revision']='e'*40
   if mode=='runtime':gate['runtime_executed']=True
   if mode=='receiver-pin':gate['receiver_build_receipt_sha256']='f'*64
   if mode=='observer-pin':gate['observer_compile_receipt_sha256']='f'*64
   if mode=='profile-pin':gate['source_profile_proof_sha256']='f'*64
   if mode=='A4-pin':pins[candidates[0]]='f'*64
   if mode=='old-A4':pins[candidates[0]]=old[candidates[0]]
   if mode=='new43':pins['native-android/engine/initial-capture/coh_initial_map.c']='f'*64
   if mode=='workflow-changed':pins[M.WORKFLOW]='e'*64
   if mode=='workflow-missing':pins.pop(M.WORKFLOW)
   if mode=='self':pins.pop(own)
   if mode=='artifact':pins[artifact]='f'*64
   values={**self.metadata(),'FOLLOWUP_SHA':M.digest(profile_raw),'FOLLOWUP_BYTES':len(profile_raw),'REVIEW_SHA':M.digest(review_raw),'REVIEW_BYTES':len(review_raw)}
   gate_raw=json.dumps(gate).encode();events=[]
   def read(path,*args):
    if path==Path('/runner/fresh-groups-source-admission.json'):return gate_raw
    if path==ROOT/M.FOLLOWUP:return profile_raw
    if path==ROOT/M.OLD_GATE:return old_raw
    if path==ROOT/(M.REVIEW+'review.json'):return review_raw
    raise AssertionError('unexpected read')
   def committed(*args):
    events.append('committed')
    if mode=='head':raise M.Refused('SOURCE_HEAD')
   with self.patches(values),patch.object(M,'raw',side_effect=read),patch.object(M,'committed',side_effect=committed),patch.object(M.importlib,'import_module',side_effect=AssertionError('no import')):
    if mode in ('good','workflow-changed'):self.assertEqual(M.admit_gate(ROOT,Path('/runner'),revision,own,{artifact:'b'*64})[2],pins);self.assertEqual(events,['committed'])
    else:
     with self.assertRaises(M.Refused):M.admit_gate(ROOT,Path('/runner'),revision,own,{artifact:'b'*64})
     self.assertEqual(events,['committed']if mode=='head'else[])
 def test_full_copy_core_mock_success_and_late_rejection_cleanup(self):
  real_stat,real_fstat=M.Path.stat,M.os.fstat
  for mode in ('good','late-source'):
   counted()
   with tempfile.TemporaryDirectory()as name:
    base=Path(name);root=base/'root';root.mkdir();runner=base/'runner';runner.mkdir();parent=runner/'private';parent.mkdir(mode=0o700);out=parent/'initial';own=root/'admit.py';own.write_bytes(b'mock');gate=runner/'fresh-groups-source-admission.json';gate.write_bytes(b'mock gate');envfile=runner/'env';envfile.write_bytes(b'');mapping={str(i):'b'*64 for i in range(43)};calls=[]
    def committed(*args):
     calls.append('source')
     if mode=='late-source'and len(calls)==4:raise M.Refused('SOURCE_BYTES')
    def project_import(*args):
     self.assertGreaterEqual(len(calls),1)
     return NS(__file__=str(root/'native-android/engine/scenecatalog-server/capture_groups_transaction.py'),native_input=lambda*a:{'dependencies_sha256':mapping,'project_dependencies':43,'source_revision':M.HISTORICAL})
    def uid(info):return NS(**{key:getattr(info,key)for key in ('st_mode','st_dev','st_ino','st_size','st_mtime_ns')},st_uid=1)
    env={'GITHUB_ACTIONS':'true','RUNNER_ENVIRONMENT':'github-hosted','RUNNER_OS':'Linux','RUNNER_ARCH':'X64','GITHUB_REPOSITORY':'Russianranger/coh-android','GITHUB_REF':'refs/heads/native-android','GITHUB_SHA':'c'*40,'RUNNER_TEMP':str(runner),'GITHUB_ENV':str(envfile)}
    with ExitStack()as stack:
     stack.enter_context(patch.dict(os.environ,env,clear=True));stack.enter_context(patch.object(M,'__file__',str(own)));stack.enter_context(patch.object(M.os,'geteuid',return_value=1));stack.enter_context(patch.object(M.Path,'stat',lambda p,*a,**k:uid(real_stat(p,*a,**k))if p==parent else real_stat(p,*a,**k)));stack.enter_context(patch.object(M.os,'fstat',side_effect=lambda fd:uid(real_fstat(fd))));stack.enter_context(patch.object(M.platform,'machine',return_value='x86_64'));stack.enter_context(patch.object(M,'evidence',return_value=(b'mock ELF',b'mock receipt',mapping,{})));stack.enter_context(patch.object(M,'admit_gate',return_value=(gate,M.digest(gate.read_bytes()),{'admit.py':'a'*64})));stack.enter_context(patch.object(M,'committed',side_effect=committed));stack.enter_context(patch.object(M,'static_elf'));stack.enter_context(patch.object(M,'system_files',return_value={'mock':'stable'}));stack.enter_context(patch.object(M,'loader_checks'));stack.enter_context(patch.object(M,'imported_sources'));stack.enter_context(patch.object(M.importlib,'import_module',side_effect=project_import))
     if mode=='good':
      result=M.admit(root,out);self.assertEqual(result['historical_checks_each_mode'],123);self.assertEqual(result['historical_status_files'],15);self.assertEqual(result['schema'],'coh-editmsg-initial-receiver-reuse-v1')
     else:
      with self.assertRaises(M.Refused):M.admit(root,out)
    if mode=='good':self.assertEqual(envfile.read_text(),'INITIAL_BUILD_SHA256='+M.BUILD_SHA+'\n');self.assertEqual((out/'build.json').read_bytes(),b'mock receipt')
    else:self.assertEqual(envfile.read_bytes(),b'');self.assertFalse((out/M.BASENAME).exists());self.assertFalse((out/'build.json').exists());self.assertFalse(json.loads((out/'receiver-reuse.json').read_bytes())['passed'])
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
 if not result.wasSuccessful():raise SystemExit(1)
 proof={'schema':'coh-editmsg-receiver-specialization-mocked-controls-v1','passed':True,'methods':result.testsRun,'cases':CASES,'helper_sha256':hashlib.sha256((HERE/'admit_editmsg_initial_receiver.py').read_bytes()).hexdigest(),'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'mocked_only':True,'actual_subprocess_executed':False,'actual_native_loader_compiler_services_executed':False,'actual_capture_module_import_executed':False,'historical_64_mocks_replayed':False,'old_151_or_new_123_CLI_controls_reexecuted':False,'retained_bytes_read_without_execution':True,'missing_evidence_metadata_fails_closed':True,'source_generation_admitted':False,'world_authority':False}
 (HERE/'editmsg-receiver-mocked-controls.json').write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');print(json.dumps(proof,sort_keys=True))
