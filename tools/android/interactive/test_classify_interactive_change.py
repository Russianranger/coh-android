import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('interactive_change_classifier',
    Path(__file__).with_name('classify_interactive_change.py'))
change = importlib.util.module_from_spec(spec)
spec.loader.exec_module(change)


class QualificationRoutingTests(unittest.TestCase):
    def test_only_direct_push_of_bounded_host_or_gameplay_changes_can_route_runtime(self):
        parent, head = 'a' * 40, 'b' * 40
        known = sorted(change.SHELL_ONLY)
        self.assertFalse(change.runtime_required('push', parent, head, parent, known))
        for event, before, files in (
            ('workflow_dispatch', parent, known), ('pull_request', parent, known),
            ('push', 'c' * 40, known), ('push', '0' * 40, known),
            ('push', parent, []),
            ('push', parent, known + ['android/native/client-launcher.c']),
            ('push', parent, known + ['android/guest/diagnostic.py']),
            ('push', parent, known + ['assets/reference-inputs-manifest.json']),
            ('push', parent, known + ['android/interactive/src/main/AndroidManifest.xml']),
        ):
            with self.subTest(event=event, before=before, files=files):
                self.assertTrue(change.runtime_required(event, before, head, parent, files))
