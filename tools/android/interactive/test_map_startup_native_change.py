"""Real temporary Git history exercises the fail-closed native workflow guard."""
import importlib.util
import ast
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('map_native_change',
    ROOT/'tools/android/interactive/classify_map_startup_native_change.py')
guard = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(guard)
WORKFLOW = (ROOT/guard.WORKFLOW).read_bytes()
LEGACY = subprocess.check_output(['git','show',guard.BASELINE+':'+guard.WORKFLOW],cwd=ROOT)
PREVIOUS_POLICY = {path: subprocess.check_output(['git','show',guard.POLICY_CORRECTION_PARENT+':'+path],cwd=ROOT)
    for path in (guard.HELPER,guard.TEST)}
PREVIOUS_FIXTURE_POLICY = {path: subprocess.check_output(['git','show',guard.FIXTURE_POLICY_PARENT+':'+path],cwd=ROOT)
    for path in (guard.HELPER,guard.TEST)}
PREVIOUS_FIXTURE_WORKFLOW = subprocess.check_output(['git','show',guard.FIXTURE_POLICY_PARENT+':'+guard.FIXTURE_WORKFLOW],cwd=ROOT)
FIXTURE_WORKFLOW = (ROOT/guard.FIXTURE_WORKFLOW).read_bytes()
FIXTURE_STAGE = (
    'tools/android/interactive/build_client_zone_startup_apk.py',
    'tools/android/interactive/classify_client_zone_startup_change.py',
    'tools/android/interactive/qualify_client_zone_startup.py',
    'tools/android/interactive/test_native_metadata_map_activation.py',
    'tools/android/interactive/prepare_native_metadata_qualification_fixtures.py',
    'tools/android/interactive/test_native_metadata_qualification_fixtures.py')
FACTUAL_DOC = 'docs/android-evidence/native-startup-material-facts-0.13.37.json'
GUEST = 'android/guest/native_map_startup_contract.py'
NATIVE = 'tools/prepare_map_startup_source.py'


class NativeWorkflowScopeTests(unittest.TestCase):
    def setUp(self):
        self.repo = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.git('init','-q')
        self.git('config','user.email','controlled-test@example.invalid')
        self.git('config','user.name','Controlled Git Fixture')
        self.write(guard.WORKFLOW,LEGACY)
        self.write(GUEST,b'BASELINE_GUEST')
        self.write(NATIVE,b'BASELINE_UNEXECUTED_PRODUCER')
        self.write(guard.FIXTURE_WORKFLOW,PREVIOUS_FIXTURE_WORKFLOW)
        self.baseline=self.commit('baseline')
        self.enterContext(patch.object(guard,'BASELINE',self.baseline))

    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.repo),*args],stderr=subprocess.DEVNULL).decode().strip()

    def write(self,path,value):
        target=self.repo/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(value)

    def commit(self,message):
        self.git('add','-A');self.git('commit','-q','-m',message)
        return self.git('rev-parse','HEAD')

    def install_guard(self):
        self.write(guard.WORKFLOW,WORKFLOW)
        self.write(guard.HELPER,(ROOT/guard.HELPER).read_bytes())
        self.write(guard.TEST,(ROOT/guard.TEST).read_bytes())
        return self.commit('reviewed guard introduction')

    def classification(self,before,head,event='push'):
        return guard.classify(self.repo,event,before,head)

    def install_previous_policy(self):
        self.write(guard.WORKFLOW,WORKFLOW)
        for path,raw in PREVIOUS_POLICY.items():self.write(path,raw)
        head=self.commit('actual prior reviewed guard bytes')
        self.enterContext(patch.object(guard,'POLICY_CORRECTION_PARENT',head))
        return head

    def update_policy(self):
        for path in (guard.HELPER,guard.TEST):self.write(path,(ROOT/path).read_bytes())

    def install_previous_fixture_policy(self):
        self.write(guard.WORKFLOW,WORKFLOW)
        for path,raw in PREVIOUS_FIXTURE_POLICY.items():self.write(path,raw)
        head=self.commit('actual prior fixture-routing policy bytes')
        self.enterContext(patch.object(guard,'FIXTURE_POLICY_PARENT',head))
        return head

    def update_fixture_policy(self):
        self.update_policy()
        self.write(guard.FIXTURE_WORKFLOW,FIXTURE_WORKFLOW)
        for path in FIXTURE_STAGE:self.write(path,b'CONTROLLED_UNEXECUTED_HOST_FIXTURE_SOURCE')

    def test_exact_current_fixture_handover_and_credential_workflow_admit_no_native_changes(self):
        before=self.install_previous_fixture_policy();self.update_fixture_policy();head=self.commit('finite host fixture recovery')
        row=self.classification(before,head)
        self.assertFalse(row['native_required'],row)
        self.assertTrue(row['original_fixture_scope_policy_correction'])
        self.assertFalse(row['source_only_scope_policy_correction']);self.assertFalse(row['control_introduction'])
        self.assertEqual(row['retained_native_body_sha256'],guard.NATIVE_BODY_SHA256)
        previous=head
        self.write(FIXTURE_STAGE[0],b'LATER_KNOWN_HOST_SOURCE');head=self.commit('later known host source')
        self.assertFalse(self.classification(previous,head)['native_required'])

    def test_fixture_handover_requires_exact_parent_controls_and_both_actual_old_source_pins(self):
        before=self.install_previous_fixture_policy();self.update_fixture_policy();head=self.commit('fixture handover')
        with patch.object(guard,'FIXTURE_POLICY_PARENT','1'*40):
            self.assertTrue(self.classification(before,head)['native_required'])
        for path in (guard.HELPER,guard.TEST):
            self.assertEqual(guard.sha(PREVIOUS_FIXTURE_POLICY[path]),guard.FIXTURE_POLICY_PREDECESSOR_PINS[path])
            with self.subTest(path=path):
                self.git('checkout','-q',before)
                self.write(path,(ROOT/path).read_bytes());partial=self.commit('partial fixture control')
                self.assertTrue(self.classification(before,partial)['native_required'])
                self.git('checkout','-q',before)
                self.write(path,PREVIOUS_FIXTURE_POLICY[path]+b'\nUNREVIEWED_PREDECESSOR\n')
                altered=self.commit('altered predecessor');self.update_fixture_policy();head=self.commit('subsequent fixture handover')
                with patch.object(guard,'FIXTURE_POLICY_PARENT',altered):
                    self.assertTrue(self.classification(altered,head)['native_required'])

    def test_fixture_handover_and_later_push_reject_unknown_workflows_native_and_future_guard_edits(self):
        before=self.install_previous_fixture_policy()
        for path in (NATIVE,'docs/android-evidence/unknown-fixture.json',guard.WORKFLOW,guard.FIXTURE_WORKFLOW):
            with self.subTest(path=path):
                self.git('checkout','-q',before);self.update_fixture_policy()
                self.write(path,b'UNREVIEWED_CHANGED_SCOPE');head=self.commit('foreign scope')
                self.assertTrue(self.classification(before,head)['native_required'])
        self.git('checkout','-q',before);self.update_fixture_policy();previous=self.commit('reviewed fixture handover')
        for path in (guard.HELPER,guard.TEST,guard.FIXTURE_WORKFLOW):
            with self.subTest(later=path):
                self.git('checkout','-q',previous);self.write(path,b'UNREVIEWED_FUTURE_POLICY')
                head=self.commit('future guard/workflow mutation')
                self.assertTrue(self.classification(previous,head)['native_required'])

    def test_exact_f6_policy_handover_admits_only_unchanged_native_source_closure(self):
        before=self.install_previous_policy();self.update_policy();head=self.commit('one reviewed host-doc routing handover')
        row=self.classification(before,head)
        self.assertFalse(row['native_required'],row)
        self.assertTrue(row['source_only_scope_policy_correction'])
        self.assertFalse(row['control_introduction'])
        self.assertEqual(row['retained_native_body_sha256'],guard.NATIVE_BODY_SHA256)

    def test_handover_can_include_exact_eight_source_only_stage_paths(self):
        before=self.install_previous_policy();self.update_policy()
        for path in ('android/guest/native_map_startup_contract.py',
            'tools/android/interactive/build_client_zone_startup_apk.py',
            'tools/android/interactive/classify_client_zone_startup_change.py',
            'tools/android/interactive/native_startup_metadata_admission.py',
            'tools/android/interactive/test_derive_native_metadata_cache_proof.py',
            'tools/android/interactive/test_native_metadata_map_activation.py',
            'tools/android/interactive/test_native_startup_metadata_admission.py',FACTUAL_DOC):
            self.write(path,b'CONTROLLED_UNEXECUTED_SOURCE_ONLY_STAGE')
        head=self.commit('host evidence plus exact handover')
        self.assertFalse(self.classification(before,head)['native_required'])

    def test_factual_doc_then_remains_an_exact_host_only_path(self):
        before=self.install_previous_policy();self.update_policy();previous=self.commit('handover')
        self.write(FACTUAL_DOC,b'CONTROLLED_INACTIVE_MATERIAL_FACTS');head=self.commit('exact evidence path')
        row=self.classification(previous,head)
        self.assertFalse(row['native_required'],row)
        self.assertFalse(row['source_only_scope_policy_correction'])

    def test_policy_handover_wrong_parent_or_partial_controls_require_native(self):
        before=self.install_previous_policy();self.update_policy();head=self.commit('handover')
        with patch.object(guard,'POLICY_CORRECTION_PARENT','1'*40):
            self.assertTrue(self.classification(before,head)['native_required'])
        for path in (guard.HELPER,guard.TEST):
            with self.subTest(path=path):
                self.git('checkout','-q',before)
                self.write(path,(ROOT/path).read_bytes());partial=self.commit('one policy control only')
                self.assertTrue(self.classification(before,partial)['native_required'])

    def test_policy_handover_authenticates_both_actual_predecessor_source_pins(self):
        before=self.install_previous_policy()
        for path in (guard.HELPER,guard.TEST):
            self.assertEqual(guard.sha(PREVIOUS_POLICY[path]),guard.POLICY_PREDECESSOR_PINS[path])
            with self.subTest(path=path):
                self.git('checkout','-q',before)
                self.write(path,PREVIOUS_POLICY[path]+b'\nUNREVIEWED_PREDECESSOR\n')
                changed=self.commit('alter prior policy');self.update_policy();head=self.commit('handover after altered policy')
                with patch.object(guard,'POLICY_CORRECTION_PARENT',changed):
                    self.assertTrue(self.classification(changed,head)['native_required'])

    def test_later_helper_or_test_edits_do_not_inherit_one_time_policy_exception(self):
        before=self.install_previous_policy();self.update_policy();previous=self.commit('handover')
        for path in (guard.HELPER,guard.TEST):
            with self.subTest(path=path):
                self.git('checkout','-q',previous)
                self.write(path,b'UNREVIEWED_FUTURE_POLICY');head=self.commit('future policy change')
                self.assertTrue(self.classification(previous,head)['native_required'])

    def test_policy_handover_never_admits_unknown_docs_native_or_workflow_changes(self):
        before=self.install_previous_policy()
        for path in ('docs/android-evidence/unreviewed-material-facts.json',NATIVE,
            'database/map-startup/tests/unreviewed.c','upstream/ouroboros/CMakeLists.txt',guard.WORKFLOW):
            with self.subTest(path=path):
                self.git('checkout','-q',before);self.update_policy()
                self.write(path,WORKFLOW.replace(b'--target MapServer',b'--target Game',1)
                    if path==guard.WORKFLOW else b'UNREVIEWED_OTHER_SCOPE')
                head=self.commit('foreign scope with policy handover')
                self.assertTrue(self.classification(before,head)['native_required'])

    def test_exact_first_wrapper_introduction_skips_unchanged_native_body(self):
        head=self.install_guard();row=self.classification(self.baseline,head)
        self.assertFalse(row['native_required'],row)
        self.assertTrue(row['control_introduction'])
        self.assertEqual(row['retained_native_body_sha256'],guard.NATIVE_BODY_SHA256)

    def test_guest_only_push_skips_with_complete_cumulative_known_scope(self):
        previous=self.install_guard();self.write(GUEST,b'CHANGED_GUEST_METADATA')
        head=self.commit('guest only');row=self.classification(previous,head)
        self.assertFalse(row['native_required'],row)
        self.assertFalse(row['control_introduction'])
        self.assertIn(guard.HELPER,row['cumulative_paths'])
        self.assertFalse(row['inherited_native_execution_claimed_fresh'])

    def test_exact_other_known_host_metadata_paths_are_admitted(self):
        previous=self.install_guard()
        for path in ('android/guest/server_animation_package.py',
            'tools/android/interactive/build_client_zone_startup_apk.py',
            'docs/android-evidence/native-map-metadata-adapter-0.13.37-review.json'):
            self.write(path,b'CONTROLLED_UNEXECUTED_HOST_PATH')
        head=self.commit('known host metadata')
        self.assertFalse(self.classification(previous,head)['native_required'])

    def test_manual_dispatch_and_unknown_events_always_require_full_native_gate(self):
        head=self.install_guard()
        for event in ('workflow_dispatch','pull_request','schedule',None):
            with self.subTest(event=event):
                self.assertTrue(self.classification(self.baseline,head,event)['native_required'])

    def test_missing_zero_malformed_or_wrong_head_requires_full_gate(self):
        head=self.install_guard()
        for before,actual in ((None,head),('0'*40,head),('BAD',head),
            (self.baseline,'0'*40),(self.baseline,self.baseline),('1'*40,head)):
            with self.subTest(before=before,head=actual):
                self.assertTrue(self.classification(before,actual)['native_required'])

    def test_multi_commit_push_cannot_skip(self):
        self.install_guard();self.write(GUEST,b'ONE_MORE_COMMIT')
        head=self.commit('next')
        self.assertTrue(self.classification(self.baseline,head)['native_required'])

    def test_merge_commit_cannot_skip(self):
        previous=self.install_guard();current=self.git('branch','--show-current')
        self.git('checkout','-q','-b','side')
        self.write(GUEST,b'SIDE_GUEST');self.commit('side')
        self.git('checkout','-q',current)
        self.write('android/guest/server_animation_package.py',b'OTHER_HOST_CHANGE');self.commit('main')
        self.git('merge','-q','--no-ff','side','-m','merge')
        head=self.git('rev-parse','HEAD')
        self.assertTrue(self.classification(previous,head)['native_required'])

    def test_actual_native_producer_build_fixture_and_unknown_changes_require_gate(self):
        previous=self.install_guard()
        for path in (NATIVE,'database/map-startup/tests/new_contract.c',
            'upstream/ouroboros/CMakeLists.txt','unknown.txt'):
            with self.subTest(path=path):
                self.git('checkout','-q',previous)
                self.write(path,b'ACTUAL_UNEXECUTED_CHANGE');head=self.commit('native or unknown')
                self.assertTrue(self.classification(previous,head)['native_required'])

    def test_prior_unqualified_native_change_is_not_hidden_by_later_guest_push(self):
        self.install_guard();self.write(NATIVE,b'UNQUALIFIED_PRODUCER')
        previous=self.commit('native changed earlier')
        self.write(GUEST,b'LATER_GUEST_CHANGE');head=self.commit('guest after native')
        row=self.classification(previous,head)
        self.assertTrue(row['native_required'])
        self.assertIn(NATIVE,row['cumulative_paths'])

    def test_missing_baseline_history_falls_back_to_native_gate(self):
        head=self.install_guard()
        with patch.object(guard,'BASELINE','1'*40):
            self.assertTrue(self.classification(self.baseline,head)['native_required'])

    def test_compiler_runner_native_step_and_fx_step_changes_all_require_gate(self):
        previous=self.install_guard()
        replacements=((b'windows-2025-vs2026',b'windows-unknown'),
            (b'-DCOH_PG_PERSISTENCE_TESTS=OFF',b'-DCOH_PG_PERSISTENCE_TESTS=ON'),
            (b'--target MapServer',b'--target Game'),
            (b'timeout-minutes: 120',b'timeout-minutes: 1'))
        for old,new in replacements:
            with self.subTest(old=old):
                self.git('checkout','-q',previous)
                self.write(guard.WORKFLOW,WORKFLOW.replace(old,new,1));head=self.commit('alter native body')
                self.assertTrue(self.classification(previous,head)['native_required'])

    def test_non_native_workflow_policy_change_is_unknown_and_requires_gate(self):
        previous=self.install_guard()
        self.write(guard.WORKFLOW,WORKFLOW.replace(b"github.event_name == 'push'",b"github.event_name == 'schedule'",1))
        head=self.commit('alter workflow policy')
        self.assertTrue(self.classification(previous,head)['native_required'])

    def test_routing_helper_or_test_changes_cannot_use_first_introduction_exception(self):
        previous=self.install_guard()
        for path in (guard.HELPER,guard.TEST):
            with self.subTest(path=path):
                self.git('checkout','-q',previous)
                self.write(path,b'CHANGED_ROUTING_SOURCE');head=self.commit('routing change')
                self.assertTrue(self.classification(previous,head)['native_required'])

    def test_deleted_renamed_or_symlinked_host_file_requires_native_gate(self):
        previous=self.install_guard();target=self.repo/GUEST
        target.unlink();head=self.commit('deleted known host source')
        self.assertTrue(self.classification(previous,head)['native_required'])
        self.git('checkout','-q',previous)
        target.rename(target.with_name('server_animation_package.py'));head=self.commit('rename')
        self.assertTrue(self.classification(previous,head)['native_required'])
        self.git('checkout','-q',previous)
        target.unlink();target.symlink_to('../../../tools/prepare_map_startup_source.py');head=self.commit('source alias')
        self.assertTrue(self.classification(previous,head)['native_required'])

    def test_empty_push_scope_or_git_failure_never_reports_successful_native_reuse(self):
        previous=self.install_guard()
        self.git('commit','-q','--allow-empty','-m','actual empty fixture commit')
        head=self.git('rev-parse','HEAD')
        self.assertTrue(self.classification(previous,head)['native_required'])
        with patch.object(guard,'git',side_effect=OSError('fixture unavailable')):
            self.assertTrue(self.classification(self.baseline,head)['native_required'])

    def test_actual_workflow_keeps_full_native_and_fx_bodies_and_fail_closed_wrapper(self):
        self.assertEqual(guard.sha(LEGACY),guard.LEGACY_WORKFLOW_SHA256)
        self.assertEqual(guard.sha(WORKFLOW),guard.GUARDED_WORKFLOW_SHA256)
        self.assertEqual(guard.sha(guard.native_body(LEGACY)),guard.NATIVE_BODY_SHA256)
        self.assertEqual(guard.native_body(LEGACY),guard.native_body(WORKFLOW))
        text=WORKFLOW.decode()
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'push' }}",text)
        self.assertIn("if: ${{ always() && (needs.change-scope.result != 'success' || needs.change-scope.outputs.native_required != 'false') }}",text)
        self.assertIn('fetch-depth: 0',text)
        self.assertLess(text.index('Host change-scope'),text.index('id: scope'))

    def test_finite_037_owner_and_fresh_suite_inventory_include_the_guard(self):
        path=ROOT/'tools/android/interactive/classify_client_zone_startup_change.py'
        spec=importlib.util.spec_from_file_location('finite_guard_owner',path)
        owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
        names=[owner.CLIENT_ZONE_STARTUP_MARKER,*guard.CONTROL,
            'tools/android/interactive/build_client_zone_startup_apk.py',
            'tools/android/interactive/qualify_client_zone_startup.py',
            'tools/android/interactive/classify_client_zone_startup_change.py']
        self.assertTrue(owner.client_zone_startup_owned('push','1'*40,'2'*40,'1'*40,names))
        self.assertFalse(owner.client_zone_startup_owned('push','1'*40,'2'*40,'1'*40,names+[NATIVE]))
        tree=ast.parse((ROOT/'tools/android/interactive/qualify_client_zone_startup.py').read_text())
        values={node.targets[0].id:ast.literal_eval(node.value) for node in tree.body
            if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)
            and node.targets[0].id=='NEW_TEST_MODULES'}
        self.assertEqual(values['NEW_TEST_MODULES'].count('test_map_startup_native_change'),1)
        builder=(ROOT/'tools/android/interactive/build_client_zone_startup_apk.py').read_text()
        for path in guard.CONTROL:self.assertIn(repr(path),builder)

    def test_actual_native_predicate_requires_success_even_when_false_output_survives_failure(self):
        native=WORKFLOW.decode().split('  native:\n',1)[1]
        expression=native.split('    if: ${{ ',1)[1].split(' }}',1)[0]
        expression=expression.replace('always()','True').replace('&&','and').replace('||','or')
        expression=expression.replace('needs.change-scope.outputs.native_required','scope_output')
        expression=expression.replace('needs.change-scope.result','scope_result')
        parsed=ast.parse(expression,mode='eval')
        allowed=(ast.Expression,ast.BoolOp,ast.And,ast.Or,ast.Compare,ast.NotEq,ast.Name,ast.Load,ast.Constant)
        self.assertTrue(all(isinstance(node,allowed) for node in ast.walk(parsed)))
        predicate=compile(parsed,'actual-native-workflow-predicate','eval')
        cases=(('success','false',False),('success','true',True),('success','',True),
            ('failure','false',True),('cancelled','false',True),('skipped','false',True),
            (None,'false',True),('success',None,True))
        for result,output,expected in cases:
            with self.subTest(result=result,output=output):
                actual=eval(predicate,{'__builtins__':{}},{'scope_result':result,'scope_output':output})
                self.assertIs(actual,expected)

    def test_actual_concurrency_preserves_push_group_and_isolates_every_manual_run(self):
        text=WORKFLOW.decode().split('concurrency:\n',1)[1].split('jobs:\n',1)[0]
        expression=text.split('group: ${{ ',1)[1].split(' }}',1)[0]
        expression=expression.replace('github.event_name','event').replace('github.run_id','run_id')
        expression=expression.replace('&&','and').replace('||','or').replace('format(','group_format(')
        parsed=ast.parse(expression,mode='eval')
        allowed=(ast.Expression,ast.BoolOp,ast.And,ast.Or,ast.Compare,ast.Eq,ast.Name,ast.Load,ast.Constant,ast.Call)
        self.assertTrue(all(isinstance(node,allowed) for node in ast.walk(parsed)))
        for node in ast.walk(parsed):
            if isinstance(node,ast.Call):
                self.assertIsInstance(node.func,ast.Name);self.assertEqual(node.func.id,'group_format')
                self.assertEqual(ast.literal_eval(node.args[0]),'android-map-startup-native-manual-{0}')
        predicate=compile(parsed,'actual-concurrency-group','eval')
        def group(event,run_id):
            return eval(predicate,{'__builtins__':{}},{'event':event,'run_id':run_id,
                'group_format':lambda template,identifier:template.format(identifier)})
        self.assertEqual(group('push',123),'android-map-startup-native')
        self.assertEqual(group('workflow_dispatch',123),'android-map-startup-native-manual-123')
        self.assertNotEqual(group('workflow_dispatch',123),group('workflow_dispatch',124))
        self.assertNotEqual(group('push',123),group('workflow_dispatch',123))
        cancel=text.split('cancel-in-progress: ${{ ',1)[1].split(' }}',1)[0]
        self.assertEqual(cancel,"github.event_name == 'push'")


if __name__ == '__main__':unittest.main()
