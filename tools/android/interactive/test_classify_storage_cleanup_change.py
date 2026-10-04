import importlib.util
import contextlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

spec=importlib.util.spec_from_file_location('storage_change',Path(__file__).with_name('classify_storage_cleanup_change.py'))
change=importlib.util.module_from_spec(spec);spec.loader.exec_module(change)


class StorageRoutingTests(unittest.TestCase):
    def test_actual_candidate_change_set_routes_only_to_its_dedicated_workflow(self):
        from classify_interactive_change import runtime_required
        root = Path(__file__).resolve().parents[3]
        names = set(subprocess.check_output(['git', 'diff', '--name-only', '-z', 'HEAD'], cwd=root).decode().split('\0'))
        names.update(subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=root).decode().split('\0'))
        names.discard('')
        if not names:
            names.update(subprocess.check_output(['git', 'diff', '--name-only', '-z', 'HEAD^', 'HEAD'], cwd=root).decode().split('\0'))
            names.discard('')
        self.assertTrue(names, 'Candidate source change evidence required')
        allowed = change.VISUAL_ALLOWED if names & (change.VISUAL_SOURCES - change.BUNDLE_ALLOWED) else change.BUNDLE_ALLOWED
        self.assertLessEqual(names, allowed, 'Candidate contains an unclassified publication path')
        fixture = 'tools/android/interactive/test_startup_bundle_save.py'
        self.assertIn(fixture, change.BUNDLE_ALLOWED)
        for function in (change.task_required, change.cleanup_required, change.recovery_required, change.receipt_required,
                change.schedule_required, change.setup_required, runtime_required):
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, sorted(names)))

    def test_client_visual_scope_disables_all_seven_old_publication_gates(self):
        from classify_interactive_change import runtime_required
        names = sorted(change.VISUAL_ALLOWED)
        functions = (change.task_required, change.cleanup_required, change.recovery_required,
            change.receipt_required, change.schedule_required, change.setup_required,
            change.bundle_required, runtime_required)
        for function in functions:
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
                for marker in change.VISUAL_SOURCES:
                    self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, [marker]))
                for other in ('android/guest/character_server_data_cache.py',
                        'android/guest/local_character_server.py', 'android/guest/client_startup_diagnostic.py',
                        'android/guest/native_responsiveness_contract.py', change.JAVA+'ClientRuntime.java',
                        'tools/android/interactive/package_startup_bundle_client.py',
                        'assets/atlas-world-supplement-manifest.json', 'unreviewed.py'):
                    self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[other]))
                for event, before, head, parent in (
                        ('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40),
                        ('pull_request', 'a'*40, 'b'*40, 'a'*40),
                        ('push', '0'*40, 'b'*40, '0'*40),
                        ('push', 'c'*40, 'b'*40, 'a'*40),
                        ('push', 'a'*40, 'a'*40, 'a'*40)):
                    self.assertTrue(function(event, before, head, parent, names))

    def test_startup_bundle_workflow_obeys_client_scope_and_keeps_dispatch(self):
        root = Path(__file__).resolve().parents[3]
        text = (root/'.github/workflows/android-startup-bundle.yml').read_text()
        self.assertIn('bundle_required: ${{ steps.scope.outputs.bundle_required }}', text)
        self.assertEqual(text.count("needs.changes.outputs.bundle_required != 'false'"), 4)
        self.assertIn('needs: [changes, dbserver, client]', text)
        self.assertIn('needs: [changes, dbserver, client, qualify]', text)
        self.assertIn('COH_PUSH_BEFORE: ${{ github.event.before }}', text)
        self.assertIn('fetch-depth: 2', text)
        self.assertIn('workflow_dispatch:', text)

    def test_bundle_routes_exact_native_and_guest_scope_away_from_six_old_releases(self):
        names = sorted(change.BUNDLE_ALLOWED)
        for function in (change.task_required, change.cleanup_required, change.recovery_required,
                change.receipt_required, change.schedule_required, change.setup_required):
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
                for marker in change.BUNDLE_SOURCES:
                    self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, [marker]))

    def test_bundle_unknown_native_manifest_asset_or_unrelated_java_changes_remain_closed(self):
        names = sorted(change.BUNDLE_ALLOWED)
        for other in ('upstream/ouroboros/DBServer/src/container_sql.c',
                'android/native/client-launcher.c', 'android/guest/local_login_server.py',
                'patches/startup-bundle/unreviewed.patch',
                'android/interactive/src/main/AndroidManifest.xml',
                'assets/server-cache-manifest.json', change.JAVA+'ClientRuntime.java', 'unreviewed.py'):
            for function in (change.task_required, change.cleanup_required, change.recovery_required,
                    change.receipt_required, change.schedule_required, change.setup_required):
                with self.subTest(other=other, function=function.__name__):
                    self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[other]))

    def test_bundle_requires_valid_direct_parent_push_and_a_bundle_source(self):
        names = sorted(change.BUNDLE_ALLOWED)
        for event, before, head, parent, files in (
                ('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names),
                ('pull_request', 'a'*40, 'b'*40, 'a'*40, names),
                ('push', '0'*40, 'b'*40, '0'*40, names),
                ('push', 'c'*40, 'b'*40, 'a'*40, names),
                ('push', 'invalid', 'b'*40, 'a'*40, names),
                ('push', 'a'*40, 'invalid', 'a'*40, names),
                ('push', 'a'*40, None, 'a'*40, names),
                ('push', 'a'*40, 'a'*40, 'a'*40, names),
                ('push', 'a'*40, 'b'*40, 'a'*40, []),
                ('push', 'a'*40, 'b'*40, 'a'*40, ['docs/HANDOFF.md']),
                ('push', 'a'*40, 'b'*40, 'a'*40,
                    ['tools/android/interactive/classify_storage_cleanup_change.py'])):
            for function in (change.task_required, change.cleanup_required, change.recovery_required,
                    change.receipt_required, change.schedule_required, change.setup_required):
                with self.subTest(event=event, before=before, head=head, function=function.__name__):
                    self.assertTrue(function(event, before, head, parent, files))

    def test_setup_and_schedule_workflows_obey_bundle_routing_and_keep_dispatch(self):
        root = Path(__file__).resolve().parents[3]
        for filename, gate in (('android-setup-memory.yml', 'setup_required'),
                ('android-startup-schedule.yml', 'schedule_required')):
            with self.subTest(filename=filename):
                text = (root/'.github/workflows'/filename).read_text()
                self.assertIn(gate+': ${{ steps.scope.outputs.'+gate+' }}', text)
                self.assertIn('needs: changes', text)
                if gate == 'schedule_required':
                    self.assertIn('needs: [changes, native]', text)
                    self.assertIn('needs: [changes, native, qualify]', text)
                    count = 3
                else:
                    self.assertIn('needs: [changes, qualify]', text)
                    count = 2
                self.assertEqual(text.count("needs.changes.outputs."+gate+" != 'false'"), count)
                self.assertIn('fetch-depth: 2', text)
                self.assertIn('COH_PUSH_BEFORE: ${{ github.event.before }}', text)
                self.assertIn('workflow_dispatch:', text)

    def test_setup_wrapper_routes_its_exact_scope_away_from_all_four_old_releases(self):
        names = sorted(change.SETUP_ALLOWED)
        for function in (change.task_required, change.cleanup_required, change.recovery_required, change.receipt_required):
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
                for marker in change.SETUP_SOURCES:
                    self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, [marker]))

    def test_setup_scope_cannot_hide_guest_native_manifest_or_unrelated_java_edits(self):
        names = sorted(change.SETUP_ALLOWED)
        for other in ('android/guest/character_reopen_diagnostic.py', 'android/guest/local_character_server.py',
                'upstream/ouroboros/DBServer/src/dbinit.c', 'android/native/client-launcher.c',
                'android/interactive/src/main/AndroidManifest.xml', change.JAVA+'ClientInput.java',
                'tools/android/interactive/build_task_receipt_cleanup_apk.py', 'unreviewed.py'):
            for function in (change.task_required, change.cleanup_required, change.recovery_required, change.receipt_required):
                with self.subTest(other=other, function=function.__name__):
                    self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[other]))

    def test_setup_requires_direct_parent_push_and_a_setup_source(self):
        names = sorted(change.SETUP_ALLOWED)
        for event, before, head, parent, files in (
                ('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names),
                ('pull_request', 'a'*40, 'b'*40, 'a'*40, names),
                ('push', '0'*40, 'b'*40, '0'*40, names),
                ('push', 'c'*40, 'b'*40, 'a'*40, names),
                ('push', 'invalid', 'b'*40, 'a'*40, names),
                ('push', 'a'*40, 'a'*40, 'a'*40, names),
                ('push', 'a'*40, 'b'*40, 'a'*40, []),
                ('push', 'a'*40, 'b'*40, 'a'*40, ['docs/HANDOFF.md']),
                ('push', 'a'*40, 'b'*40, 'a'*40,
                    ['tools/android/interactive/classify_storage_cleanup_change.py'])):
            for function in (change.task_required, change.cleanup_required, change.recovery_required, change.receipt_required):
                with self.subTest(event=event, before=before, files=files, function=function.__name__):
                    self.assertTrue(function(event, before, head, parent, files))
        for historical in (change.ALLOWED, change.STARTUP_ALLOWED, change.RECEIPT_ALLOWED):
            self.assertTrue(change.receipt_required('push', 'a'*40, 'b'*40, 'a'*40, sorted(historical)))

    def test_setup_scope_has_only_the_six_changed_java_sources_and_one_addition(self):
        diagnostic = 'android/app/src/main/java/io/github/russianranger/cohdiagnostic/'
        self.assertEqual({name for name in change.SETUP_ALLOWED if name.startswith('android/') and name.endswith('.java')}, {
            change.JAVA+'ClientRuntime.java', change.JAVA+'ClientService.java',
            change.JAVA+'ClientActivity.java', change.JAVA+'ClientSurface.java',
            diagnostic+'DiagnosticRuntime.java', diagnostic+'TarExtractor.java', diagnostic+'SetupMemoryGuard.java'})

    def test_receipt_workflow_obeys_setup_routing_and_keeps_manual_dispatch(self):
        root = Path(__file__).resolve().parents[3]
        text = (root/'.github/workflows/android-task-receipt-cleanup.yml').read_text()
        self.assertIn('receipt_required: ${{ steps.scope.outputs.receipt_required }}', text)
        self.assertIn('needs: changes', text)
        self.assertIn('needs: [changes, qualify]', text)
        self.assertEqual(text.count("needs.changes.outputs.receipt_required != 'false'"), 2)
        self.assertIn('fetch-depth: 2', text)
        self.assertIn('COH_PUSH_BEFORE: ${{ github.event.before }}', text)
        self.assertIn('workflow_dispatch:', text)

    def test_classifier_emits_receipt_gate_and_defaults_to_required_without_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)/'outputs'
            environment = {'GITHUB_OUTPUT': str(output), 'GITHUB_EVENT_NAME': 'push', 'COH_PUSH_BEFORE': 'a'*40}
            values = ['a'*40, 'b'*40, b'tools/android/interactive/build_setup_memory_apk.py\0']
            with mock.patch.dict(change.os.environ, environment), \
                    mock.patch.object(change.subprocess, 'check_output', side_effect=values), \
                    contextlib.redirect_stdout(io.StringIO()):
                change.main()
            self.assertEqual(output.read_text(), 'task_required=false\ncleanup_required=false\n'
                'recovery_required=false\nreceipt_required=false\nschedule_required=true\nsetup_required=true\nbundle_required=true\n')
            output.unlink()
            with mock.patch.dict(change.os.environ, environment), \
                    mock.patch.object(change.subprocess, 'check_output', side_effect=OSError('no history')), \
                    contextlib.redirect_stdout(io.StringIO()):
                change.main()
            self.assertEqual(output.read_text(), 'task_required=true\ncleanup_required=true\n'
                'recovery_required=true\nreceipt_required=true\nschedule_required=true\nsetup_required=true\nbundle_required=true\n')

    def test_classifier_emits_all_six_disabled_gates_for_exact_bundle_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)/'outputs'
            environment = {'GITHUB_OUTPUT': str(output), 'GITHUB_EVENT_NAME': 'push', 'COH_PUSH_BEFORE': 'a'*40}
            values = ['a'*40, 'b'*40, b'tools/android/interactive/test_startup_bundle_save.py\0']
            with mock.patch.dict(change.os.environ, environment), \
                    mock.patch.object(change.subprocess, 'check_output', side_effect=values), \
                    contextlib.redirect_stdout(io.StringIO()):
                change.main()
            self.assertEqual(output.read_text(), 'task_required=false\ncleanup_required=false\n'
                'recovery_required=false\nreceipt_required=false\nschedule_required=false\nsetup_required=false\nbundle_required=true\n')

    def test_receipt_cleanup_routes_only_its_same_profile_scope_away_from_old_releases(self):
        names = sorted(change.RECEIPT_ALLOWED)
        for function in (change.task_required, change.cleanup_required, change.recovery_required):
            self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
            for other in ('android/guest/local_character_server.py',
                    change.JAVA+'ClientActivity.java', 'upstream/ouroboros/DBServer/src/dbinit.c'):
                with self.subTest(function=function.__name__, other=other):
                    self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[other]))
            self.assertTrue(function('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names))

    def test_startup_routes_away_from_all_three_historical_publications(self):
        names = sorted(change.STARTUP_ALLOWED)
        for function in (change.task_required, change.cleanup_required, change.recovery_required):
            self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
            for other in ('upstream/ouroboros/DBServer/src/dbinit.c',
                    'android/native/unreviewed.c', 'android/guest/dbserver_diagnostic.py'):
                with self.subTest(function=function.__name__, other=other):
                    self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[other]))

    def test_startup_dispatch_ambiguous_history_or_document_only_edit_cannot_skip(self):
        names = sorted(change.STARTUP_ALLOWED)
        for event, before, head, parent, files in (
                ('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names),
                ('push', 'c'*40, 'b'*40, 'a'*40, names),
                ('push', 'a'*40, 'a'*40, 'a'*40, names),
                ('push', 'a'*40, 'b'*40, 'a'*40, ['docs/HANDOFF.md'])):
            for function in (change.task_required, change.cleanup_required, change.recovery_required):
                with self.subTest(function=function.__name__, event=event):
                    self.assertTrue(function(event, before, head, parent, files))

    def test_recovery_workflow_obeys_startup_routing_before_qualification(self):
        workflow = Path(__file__).resolve().parents[3]/'.github/workflows/android-storage-recovery.yml'
        text = workflow.read_text()
        self.assertIn('recovery_required: ${{ steps.scope.outputs.recovery_required }}', text)
        self.assertIn('needs: [changes, qualify]', text)
        self.assertEqual(text.count("needs.changes.outputs.recovery_required != 'false'"), 2)
        self.assertIn('fetch-depth: 2', text)

    def test_recovery_routes_away_from_historical_task_and_cleanup_publications(self):
        for marker in change.RECOVERY_SOURCES:
            with self.subTest(marker=marker):
                names = [marker, change.JAVA+'StorageAudit.java',
                    change.JAVA+'ClientService.java',
                    'android/app/src/main/java/io/github/russianranger/cohdiagnostic/DiagnosticRuntime.java']
                self.assertFalse(change.task_required('push','a'*40,'b'*40,'a'*40,names))
                self.assertFalse(change.cleanup_required('push','a'*40,'b'*40,'a'*40,names))

    def test_historical_storage_change_still_qualifies_its_own_publication(self):
        names = [change.JAVA+'StorageAudit.java', change.JAVA+'ClientActivity.java']
        self.assertFalse(change.task_required('push','a'*40,'b'*40,'a'*40,names))
        self.assertTrue(change.cleanup_required('push','a'*40,'b'*40,'a'*40,names))

    def test_recovery_cannot_hide_native_or_unknown_changes(self):
        known = sorted(change.RECOVERY_SOURCES)
        for other in ('android/guest/local_character_server.py',
                'upstream/ouroboros/Common/seq/animtrack.c',
                'android/interactive/src/main/AndroidManifest.xml', 'unknown.txt'):
            with self.subTest(other=other):
                names = known+[other]
                self.assertTrue(change.task_required('push','a'*40,'b'*40,'a'*40,names))
                self.assertTrue(change.cleanup_required('push','a'*40,'b'*40,'a'*40,names))

    def test_recovery_ambiguous_history_and_dispatch_cannot_skip_historical_checks(self):
        known = sorted(change.RECOVERY_SOURCES)
        for event,before,head,parent in (
                ('workflow_dispatch','a'*40,'b'*40,'a'*40),
                ('push','0'*40,'b'*40,'0'*40),
                ('push','c'*40,'b'*40,'a'*40),
                ('push','a'*40,'a'*40,'a'*40)):
            self.assertTrue(change.task_required(event,before,head,parent,known))
            self.assertTrue(change.cleanup_required(event,before,head,parent,known))

    def test_cleanup_workflow_obeys_recovery_routing_before_qualification(self):
        workflow = Path(__file__).resolve().parents[3]/'.github/workflows/android-storage-cleanup.yml'
        text = workflow.read_text()
        self.assertIn('cleanup_required: ${{ steps.scope.outputs.cleanup_required }}', text)
        self.assertIn('needs: [changes, qualify]', text)
        self.assertEqual(text.count("needs.changes.outputs.cleanup_required != 'false'"), 2)
        self.assertIn('fetch-depth: 2', text)

    def test_direct_storage_commit_uses_exact_retained_runtime_workflow(self):
        self.assertFalse(change.task_required('push','a'*40,'b'*40,'a'*40,sorted(change.ALLOWED)))
        self.assertFalse(change.task_required('push','a'*40,'b'*40,'a'*40,
            [change.JAVA+'StorageAudit.java',change.JAVA+'ClientActivity.java']))

    def test_native_guest_task_or_unknown_changes_cannot_skip_qualification(self):
        known=[change.JAVA+'StorageAudit.java']
        for other in ('android/guest/local_character_server.py',
            'android/guest/task_gate_evidence.py','android/guest/server_animation_package.py',
            'tools/android/atlasgame/prepare_server_animations.py',
            change.JAVA+'ClientAcceptance.java','assets/reference-inputs-manifest.json',
            'android/interactive/src/main/AndroidManifest.xml',
            'upstream/ouroboros/Common/seq/animtrack.c'):
            with self.subTest(other=other):
                self.assertTrue(change.task_required('push','a'*40,'b'*40,'a'*40,known+[other]))

    def test_ambiguous_history_dispatch_and_unmarked_java_edits_remain_fail_closed(self):
        known=[change.JAVA+'StorageAudit.java']
        for event,before,head,parent,names in (
            ('workflow_dispatch','a'*40,'b'*40,'a'*40,known),
            ('pull_request','a'*40,'b'*40,'a'*40,known),
            ('push','0'*40,'b'*40,'0'*40,known),
            ('push','c'*40,'b'*40,'a'*40,known),
            ('push','a'*40,'a'*40,'a'*40,known),
            ('push','a'*40,'b'*40,'a'*40,[]),
            ('push','a'*40,'b'*40,'a'*40,[change.JAVA+'ClientInput.java']),
            ('push','a'*40,'b'*40,'a'*40,['docs/HANDOFF.md'])):
            self.assertTrue(change.task_required(event,before,head,parent,names))
