#!/usr/bin/env python3
"""New account-receiver evidence/gate mocks only; no loader or native execution."""
from pathlib import Path
import argparse,ast,copy,gzip,hashlib,importlib.util,json,sys,tempfile,unittest
from unittest.mock import patch
ROOT=None;M=None;HELPER=None;FROZEN=None;CASES=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def js(b):return json.loads(b)
CORE=['Refused','need','digest','raw','child','git','committed','fixed','static_elf','system_files','loader_checks','imported_sources','write_new','unlink_owned','export_env','main']
class Controls(unittest.TestCase):
 def setUp(self):
  self.no_process=patch.object(M.subprocess,'Popen',side_effect=AssertionError('mock-only process prohibition'));self.no_process.start();self.addCleanup(self.no_process.stop)
  self.no_import=patch.object(M.importlib,'import_module',side_effect=AssertionError('project import prohibited'));self.no_import.start();self.addCleanup(self.no_import.stop)
 def check(self,ok,label):
  self.assertTrue(ok,label);CASES.append(label)
 def refused(self,call,label,code=None):
  with self.assertRaises(M.Refused)as got:call()
  if code:self.assertEqual(got.exception.code,code)
  CASES.append(label)
 def fake_observer(self,mutate=None):
  focused=js((ROOT/M.FOLLOWUP).read_bytes());fp=focused['compiled_source_fingerprint']['current']
  value=js((ROOT/'native-android/engine/scenecatalog-server/evidence/fresh-callback-profile-20261018/compile-39086864926/compile-only-receipt.json').read_bytes())
  names={'source/Common/seq/coh_fresh_folder_profile_api.h':'source_folder_profile_api.h','source/libs/UtilitiesLib/src/utils/coh_fresh_folder_profile_api.h':'source_folder_profile_api.h','source/libs/UtilitiesLib/src/utils/coh_fresh_folder_profile.inc':'source_folder_profile.inc','source/MapServer/src/group/coh_fresh_source_profile.inc':'source_group_profile.inc','source/libs/UtilitiesLib/src/utils/coh_fresh_source_profile_api.h':'source_group_profile_api.h','source/Common/seq/coh_resource_quiescence.inc':'source_sealed_quiescence.inc'}
  for path,key in names.items():value['artifacts'][path]['sha256']=fp[key]
  if mutate:mutate(value)
  return (json.dumps(value,sort_keys=True)+'\n').encode()
 def observer_scope(self,raw=None,extra=None):
  raw=self.fake_observer()if raw is None else raw;original=M.fixed
  def fixed(root,name,size,pin):
   if name==M.OBSERVER_BUILD:return raw
   if extra and name in extra:return extra[name]
   return original(root,name,size,pin)
  from contextlib import ExitStack
  stack=ExitStack();stack.enter_context(patch.object(M,'OBSERVER_BUILD_SHA',sha(raw)));stack.enter_context(patch.object(M,'OBSERVER_BUILD_BYTES',len(raw)));stack.enter_context(patch.object(M,'fixed',side_effect=fixed));return stack
 def test_core_ast_and_pending(self):
  base=(ROOT/'native-android/combined-client/tools/admit_editmsg_initial_receiver.py').read_bytes();self.assertEqual(sha(base),'7bcafe470fde547f497fced3605704eaf277715866045824b5407ef56da641d4')
  def nodes(raw):return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
  old,new=nodes(base),nodes(FROZEN)
  for name in CORE:self.check(old[name]==new[name],'unchanged-core-'+name)
  with patch.object(M,'OBSERVER_BUILD_SHA','PENDING'),patch.object(M,'OBSERVER_BUILD_BYTES',0):self.refused(M.frozen_metadata,'pending-actual-map-refuses','EVIDENCE_NOT_FROZEN')
 def test_complete_new_evidence(self):
  with self.observer_scope():
   binary,raw,mapping,pins=M.evidence(ROOT)
   self.check(len(binary)==180616 and sha(binary)==M.ELF_SHA,'new-elf-bytes-read-only')
   self.check(len(raw)==254894 and sha(raw)==M.BUILD_SHA,'new-build-receipt')
   self.check(len(mapping)==45 and sha(json.dumps(mapping,sort_keys=True,separators=(',',':')).encode())==M.MAP_SHA,'new-current45-map')
   self.check(all(pins.get(k)==v for k,v in mapping.items()if k in pins),'current-qualified-overlaps')
   self.check(M.ACCOUNT_PROOF in pins and M.OWN_LINKS in pins and M.ROOT_LINKS in pins,'separate-c99-and-link-evidence')
   self.check('native-android/engine/initial-capture/test_initial_account_peer.c'in pins,'new-selected-peer-pinned')
   self.check(sum(n.startswith(M.STATUS_ROOT+'status-')for n in pins)==3,'three-new-fixed-status-files')
 def test_observer_source_and_scope_refusals(self):
  for field,value in [('compile_only',False),('runtime_executed',True),('source_stage_verified',False)]:
   raw=self.fake_observer(lambda d:d.__setitem__(field,value))
   with self.observer_scope(raw):self.refused(lambda:M.evidence(ROOT),'observer-'+field,'QUALIFIED_SCOPE')
  for path in ['source/MapServer/src/group/coh_fresh_source_profile.inc','source/libs/UtilitiesLib/src/utils/coh_fresh_source_profile_api.h']:
   raw=self.fake_observer(lambda d:d['artifacts'][path].__setitem__('sha256','0'*64))
   with self.observer_scope(raw):self.refused(lambda:M.evidence(ROOT),'observer-old-member-'+path,'OBSERVER_SOURCE')
  raw=(ROOT/'native-android/engine/scenecatalog-server/evidence/fresh-callback-profile-20261018/compile-39086864926/compile-only-receipt.json').read_bytes()
  with self.observer_scope(raw):self.refused(lambda:M.evidence(ROOT),'historical-map-cannot-admit-new-owner-code','OBSERVER_SOURCE')
 def test_exact_c79_transitions(self):
  build=js(gzip.decompress((ROOT/(M.OLD+'build.json.gz')).read_bytes()))
  changes=[(M.ROOT_LINKS,'files','native-android/engine/dbclient/check.py','previous_sha256'),(M.OWN_LINKS,'files','native-android/engine/initial-capture/check_initial_editmsg.py','before_sha256')]
  for path,group,name,field in changes:
   d=js((ROOT/path).read_bytes());d[group][name][field]='0'*64
   with self.observer_scope(extra={path:json.dumps(d).encode()}):self.refused(lambda:M.qualified_sources(ROOT,build,{}),'c79-refuses-unqualified-tool-transition-'+name,'QUALIFIED_SCOPE')
  d=js((ROOT/M.ACCOUNT_BINDING).read_bytes());d['previous_ordinary_sha256']['native-android/engine/dbclient/coh_db_session.c']='0'*64
  with self.observer_scope(extra={M.ACCOUNT_BINDING:json.dumps(d).encode()}):self.refused(lambda:M.qualified_sources(ROOT,build,{}),'c79-refuses-unqualified-core-transition','QUALIFIED_SCOPE')
 def test_current_gate_positive_and_refusals(self):
  with self.observer_scope():
   _,_,mapping,artifacts=M.evidence(ROOT)
   old=js((ROOT/M.OLD_GATE).read_bytes())['current_278_pin_map'];earlier=js((ROOT/M.EARLIER_PROFILE).read_bytes());focused=js((ROOT/M.FOLLOWUP).read_bytes());own='native-android/combined-client/tools/admit_account_controls_initial_receiver.py'
   pins={k:v for k,v in old.items()if k!=M.WORKFLOW};pins.update(earlier['source_sha256']);pins.update(focused['source_sha256']);pins.update(mapping);pins.update(artifacts);pins.update({M.EARLIER_PROFILE:M.EARLIER_PROFILE_SHA,M.OWNER_REVIEW:M.OWNER_REVIEW_SHA,own:sha(FROZEN),M.WORKFLOW:sha((ROOT/M.WORKFLOW).read_bytes())})
   revision='a'*40;gate={key:False for key in M.GATE_KEYS};gate.update(schema='coh-account-controls-fresh-groups-live-source-admission-v1',passed=True,source_revision=revision,source_sha256=pins,source_preflight_only=True,observer_compile_receipt_sha256=M.OBSERVER_BUILD_SHA,receiver_build_receipt_sha256=M.BUILD_SHA,source_profile_proof_sha256=M.FOLLOWUP_SHA)
   calls=[]
   def committed(root,values,rev):self.assertEqual((root,rev),(ROOT,revision));calls.append(copy.deepcopy(values))
   with tempfile.TemporaryDirectory(prefix='account-receiver-gate-mocks-')as tmp,patch.object(M,'committed',side_effect=committed):
    runner=Path(tmp).resolve();path=runner/'fresh-groups-source-admission.json';path.write_text(json.dumps(gate));result=M.admit_gate(ROOT,runner,revision,own,artifacts)
    self.check(result[2]==pins and len(calls)==1,'new-gate-current-closure-before-any-import')
    mutations=[('old-schema',lambda d:d.__setitem__('schema','coh-editmsg-fresh-groups-live-source-admission-v1')),('stale-head',lambda d:d.__setitem__('source_revision','b'*40)),('extra-key',lambda d:d.__setitem__('extra',False)),('runtime-claim',lambda d:d.__setitem__('runtime_executed',True)),('old-build',lambda d:d.__setitem__('receiver_build_receipt_sha256','0'*64)),('old-map',lambda d:d.__setitem__('observer_compile_receipt_sha256','0'*64)),('old-profile',lambda d:d.__setitem__('source_profile_proof_sha256',M.EARLIER_PROFILE_SHA)),('missing-self',lambda d:d['source_sha256'].pop(own)),('missing-current-workflow',lambda d:d['source_sha256'].pop(M.WORKFLOW))]
    for name in ['native-android/engine/dbclient/coh_db_session.c','native-android/engine/dbclient/check.py','native-android/engine/initial-capture/check_initial_editmsg.py','native-android/engine/initial-capture/test_initial_peer.c','native-android/engine/initial-capture/test_initial_account_peer.c','native-android/engine/scenecatalog-server/fresh_callback_observer/stage.py']:
     mutations.append(('old-source-'+name,lambda d,n=name:d['source_sha256'].__setitem__(n,'0'*64)))
    for label,mutate in mutations:
     candidate=copy.deepcopy(gate);mutate(candidate);path.write_text(json.dumps(candidate));calls.clear();self.refused(lambda:M.admit_gate(ROOT,runner,revision,own,artifacts),label,'SOURCE_GATE');self.assertEqual(calls,[])

def main():
 global ROOT,M,HELPER,FROZEN
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--helper',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();ROOT=a.source_root.resolve();HELPER=a.helper.resolve();FROZEN=HELPER.read_bytes()
 if a.output.exists():raise ValueError('fresh output required')
 sys.dont_write_bytecode=True;spec=importlib.util.spec_from_file_location('account_receiver_mocked',HELPER);M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controls);result=unittest.TextTestRunner(verbosity=2).run(suite)
 if HELPER.read_bytes()!=FROZEN:raise ValueError('helper changed during mock controls')
 if not result.wasSuccessful():return 1
 proof={'schema':'coh-account-controls-receiver-mocked-controls-v1','passed':True,'helper_sha256':sha(FROZEN),'test_sha256':sha(Path(__file__).read_bytes()),'methods':result.testsRun,'cases':len(CASES),'case_names':CASES,'new_evidence_and_gate_only':True,'old_mock_suites_reexecuted':False,'actual_map_compile_receipt_admitted':False,'observer_receipt_is_explicit_mock':True,'actual_destination_preflight_executed':False,'loader_native_compiler_services_executed':False,'retained_elf_read_for_hash_only':True,'source_generation_admitted':False,'world_authority':False}
 with a.output.open('x')as f:f.write(json.dumps(proof,indent=2)+'\n')
 print(json.dumps({'passed':True,'methods':result.testsRun,'cases':len(CASES)}));return 0
if __name__=='__main__':raise SystemExit(main())
