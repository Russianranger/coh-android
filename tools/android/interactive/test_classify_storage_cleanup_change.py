import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('storage_change',Path(__file__).with_name('classify_storage_cleanup_change.py'))
change=importlib.util.module_from_spec(spec);spec.loader.exec_module(change)


class StorageRoutingTests(unittest.TestCase):
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
