import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('storage_change',Path(__file__).with_name('classify_storage_cleanup_change.py'))
change=importlib.util.module_from_spec(spec);spec.loader.exec_module(change)


class StorageRoutingTests(unittest.TestCase):
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
            ('push','a'*40,'b'*40,'a'*40,[change.JAVA+'ClientActivity.java']),
            ('push','a'*40,'b'*40,'a'*40,['docs/HANDOFF.md'])):
            self.assertTrue(change.task_required(event,before,head,parent,names))
