"""New optional wiring/privacy controls, no source server or runtime capture."""
import copy,json,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from fresh_callback_observer import runtime,probe,admit_compile
import admit_groups_capture as admission
import capture_groups_transaction as capture
import summarize_groups_capture as summary

class Controls(unittest.TestCase):
 def receipt(self):
  return {'schema':'coh-private-original-native-groups-run-v1','passed':True,'private_character_state':True,
   'public_upload_permitted':False,'local_development_auth':True,'authserver_authenticated':False,
   'source_generation_admitted':False,'world_authority':False,'capture_stage':'COMPLETE','failure_stage':'NONE',
   **{name:True for name in summary.STATUS},'pair':{'schema':'coh-original-native-groups-pair-v1','passed':True,
   'source_run_provenance_verified':False,'cache_equivalence_verified':False,'source_generation_admitted':False,
   'actor_identity_verified':False,'world_authority':False,**{name:True for name in summary.PAIR}}}
 def test_only_fixed_schema_selects_fresh_admission(self):
  with tempfile.TemporaryDirectory() as t:
   directory=Path(t);path=directory/'compile-only-receipt.json'
   raw=json.dumps({'schema':admit_compile.SCHEMA}).encode();path.write_bytes(raw)
   with patch.object(admit_compile,'inspect',return_value=('fresh','declared')) as selected:
    self.assertEqual(admission.inspect(directory,capture.ROOT,capture.d.digest(raw)),('fresh','declared'))
    selected.assert_called_once_with(directory,capture.ROOT,capture.d.digest(raw))
   for schema in ('arbitrary-driver-path','coh-fresh-groups-observer-compile-v2'):
    raw=json.dumps({'schema':schema}).encode();path.write_bytes(raw)
    with patch.object(admit_compile,'inspect') as selected,self.assertRaises(ValueError):admission.inspect(directory,capture.ROOT,capture.d.digest(raw))
    selected.assert_not_called()
 def test_old_role_keeps_original_source_map_new_role_adds_bound_helpers(self):
  legacy=capture.orchestration_source_paths()
  for compiled in (None,{}, {'build_role':capture.stage.ROLE},{'build_role':'arbitrary'}):self.assertEqual(capture.orchestration_source_paths(compiled),legacy)
  with patch.object(runtime,'source_paths',return_value={'fixed-new-helper.py'}) as selected:
   self.assertEqual(capture.orchestration_source_paths({'build_role':runtime.ROLE}),legacy|{'fixed-new-helper.py'})
   selected.assert_called_once_with(capture.ROOT)
  with patch.object(runtime,'source_paths',side_effect=ValueError('PRIVATE_CANARY')),self.assertRaises(ValueError):capture.orchestration_source_paths({'build_role':runtime.ROLE})
 def test_optional_prepare_bind_errors_never_start_or_change_groups(self):
  with patch.object(probe,'precreate') as make:
   self.assertIsNone(runtime.precreate({'build_role':capture.stage.ROLE},Path('/not-used')));make.assert_not_called()
  with patch.object(probe,'precreate',side_effect=ValueError('PRIVATE_CANARY')):
   self.assertIsNone(runtime.precreate({'build_role':runtime.ROLE},Path('/not-used')))
  owner,child,streams,children,handles=object(),object(),[object(),object()],[],[]
  with patch.object(probe,'bind',side_effect=ValueError('PRIVATE_CANARY')) as bind:
   runtime.bind(owner,child,streams,children,handles);bind.assert_called_once_with(owner,child,streams,children,handles)
 def test_late_collection_refusal_clears_private_binding_preserves_groups(self):
  report=self.receipt();report['source_profile_private_binding']={'canary':'PRIVATE_CANARY'}
  for failure in ('collect','public'):
   value=copy.deepcopy(report)
   context=patch.object(probe,'collect',side_effect=OSError('PRIVATE_CANARY')) if failure=='collect' else patch.object(probe,'collect',return_value=({'bad':'PRIVATE_CANARY'},None))
   with context:runtime.record(value,object(),object(),cleanup_attempted=True)
   self.assertTrue(value['passed']);self.assertTrue(value['cleanup_verified']);self.assertTrue(value['matching_groups_transaction_captured'])
   self.assertNotIn('source_profile_private_binding',value);self.assertEqual(value['source_profile_diagnostic']['probe_state'],'REFUSED')
   self.assertNotIn('PRIVATE_CANARY',json.dumps(summary.summarize(value)))
 def test_outer_optional_failure_never_unwinds_cleanup_or_pair(self):
  report=self.receipt();report['source_profile_private_binding']={'private':'PRIVATE_CANARY'};report['source_profile_diagnostic']={'bad':'PRIVATE_CANARY'}
  with patch.object(runtime,'record',side_effect=OSError('PRIVATE_CANARY')):capture.record_source_profile(report,runtime,object(),object())
  self.assertTrue(report['passed']);self.assertTrue(report['cleanup_verified']);self.assertTrue(report['matching_groups_transaction_captured'])
  self.assertNotIn('source_profile_diagnostic',report);self.assertNotIn('source_profile_private_binding',report)
  self.assertNotIn('PRIVATE_CANARY',json.dumps(summary.summarize(report)))

 def test_public_summary_optional_malformed_diagnostic_keeps_pair(self):
  for diagnostic in ({'arbitrary':'PRIVATE_CANARY'},None,'PRIVATE_CANARY'):
   value=self.receipt();value['source_profile_diagnostic']=diagnostic;value['source_profile_private_binding']={'private':'PRIVATE_CANARY'}
   result=summary.summarize(value);self.assertTrue(result['passed']);self.assertTrue(result['matching_groups_transaction_captured'])
   self.assertEqual(result['source_profile_diagnostic']['probe_state'],'REFUSED');self.assertNotIn('PRIVATE_CANARY',json.dumps(result))
  value=self.receipt();value['source_profile_diagnostic']=probe.empty();self.assertTrue(summary.summarize(value)['passed'])
 def test_private_identity_never_projected(self):
  value=self.receipt();private={'private':'PRIVATE_CANARY','public_upload_permitted':False}
  with patch.object(probe,'collect',return_value=(probe.empty(),private)):runtime.record(value,object(),object(),cleanup_attempted=True)
  self.assertIs(value['source_profile_private_binding'],private)
  self.assertNotIn('PRIVATE_CANARY',json.dumps(summary.summarize(value)))
 def test_source_and_retention_role_imports_precede_source_freeze(self):
  import admit_source_snapshot as source_admission
  import retain_fresh_source_snapshot as source_retention
  import retain_fresh_initial_observation as initial_retention
  class StopAtFreeze(Exception):pass
  for module in (source_admission,source_retention,initial_retention):
   events=[];compiled={'build_role':runtime.ROLE}
   args=types.SimpleNamespace(compile_directory=Path('/not-used'),compile_receipt_sha256='a'*64)
   with patch.object(source_admission,'hosted_revision',return_value='a'*40),patch.object(capture.base,'fixture_modules',return_value=(None,None,None,None)),patch.object(source_admission.compiled_admission,'inspect',side_effect=lambda *a:(events.append('compiled') or compiled,{})),patch.object(capture,'orchestration_source_paths',side_effect=lambda value:events.append(('role',value)) or set()),patch.object(source_admission,'admission_source_pins',side_effect=lambda **kw:events.append(('pins',kw.get('compiled'))) or {'synthetic':'a'*64}),patch.object(source_admission,'committed_source_closure',side_effect=StopAtFreeze):
    with self.assertRaises(StopAtFreeze):(module.admit if module is source_admission else module.retain)(args)
   self.assertEqual(events,['compiled',('role',compiled),('pins',compiled)])

 def test_bounded_wiring_order_source_guard(self):
  # The actual supervisor is reviewed, never executed by these controls. Protect
  # the cross-process ordering that a thin helper cannot infer on its own.
  text=(HERE.parent/'capture_groups_transaction.py').read_text()
  self.assertLess(text.index('source_probe_owner=fresh_runtime.precreate'),text.index("advance(report,'MAPSERVER_START')"))
  self.assertLess(text.index("advance(report,'MAPSERVER_START')"),text.index('fresh_runtime.bind(source_probe_owner,map_process,handles[-2:],children,handles)'))
  self.assertLess(text.index('for handle in handles:'),text.index('record_source_profile(report,fresh_runtime,source_probe_owner,map_process)'))
  self.assertIn("map_env['COH_NATIVE_GROUPS_PROFILE_PROBE_OUTPUT']=base.windows_path(source_probe_owner.path)",text)

if __name__=='__main__':unittest.main()
