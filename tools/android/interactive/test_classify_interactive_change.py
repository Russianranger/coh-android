import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('interactive_change_classifier',
    Path(__file__).with_name('classify_interactive_change.py'))
change = importlib.util.module_from_spec(spec)
spec.loader.exec_module(change)


class QualificationRoutingTests(unittest.TestCase):
    def test_exact_startup_derivative_routes_to_its_native_and_apk_pipeline(self):
        names = sorted(change.STARTUP_ALLOWED)
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40,
            names+['upstream/ouroboros/DBServer/src/dbinit.c']))

    def test_only_direct_push_of_bounded_host_or_gameplay_changes_can_route_runtime(self):
        parent, head = 'a' * 40, 'b' * 40
        known = sorted(change.SHELL_ONLY)
        self.assertFalse(change.runtime_required('push', parent, head, parent, known))
        candidate = sorted(change.SHELL_ONLY | change.RESPONSIVENESS_ONLY)
        self.assertFalse(change.runtime_required('push', parent, head, parent, candidate))
        for event, before, files in (
            ('workflow_dispatch', parent, known), ('pull_request', parent, known),
            ('push', 'c' * 40, known), ('push', '0' * 40, known),
            ('push', parent, []),
            ('push', parent, candidate + ['android/native/unreviewed-renderer.c']),
            ('push', parent, known + ['android/guest/diagnostic.py']),
            ('push', parent, known + ['assets/reference-inputs-manifest.json']),
            ('push', parent, known + ['android/interactive/src/main/AndroidManifest.xml']),
        ):
            with self.subTest(event=event, before=before, files=files):
                self.assertTrue(change.runtime_required(event, before, head, parent, files))


    def test_task_derivative_routes_to_its_own_workflow_but_unknown_native_edits_do_not(self):
        paths = ['.github/workflows/android-task-gate.yml',
            'android/guest/task_gate_evidence.py', 'android/guest/server_animation_package.py',
            'android/guest/task-gate.json',
            'tools/android/atlasgame/prepare_server_animations.py',
            'tools/android/interactive/test_task_gate_integration.py']
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, paths))
        self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40,
            paths+['upstream/ouroboros/MapServer/src/svr/svrinit.c']))
