import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('interactive_change_classifier',
    Path(__file__).with_name('classify_interactive_change.py'))
change = importlib.util.module_from_spec(spec)
spec.loader.exec_module(change)


class QualificationRoutingTests(unittest.TestCase):
    def test_startup_followup_marker_has_priority_and_cannot_hide_historical_scope(self):
        names = sorted(change.CLIENT_STARTUP_FOLLOWUP_ALLOWED)
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for other in ('assets/client-visual-manifest.json',
                'tools/android/interactive/build_client_asset_closure_apk.py',
                'tools/android/interactive/package_client_loading_native.py',
                'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientRuntime.java',
                'android/native/client-launcher.c', 'unknown.py'):
            with self.subTest(other=other):
                self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[other]))

    def test_startup_followup_dispatch_and_ambiguous_history_require_full_runtime(self):
        names = sorted(change.CLIENT_STARTUP_FOLLOWUP_ALLOWED)
        for event, before, head, parent in (
                ('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40),
                ('pull_request', 'a'*40, 'b'*40, 'a'*40),
                ('push', '0'*40, 'b'*40, '0'*40),
                ('push', 'c'*40, 'b'*40, 'a'*40),
                ('push', 'invalid', 'b'*40, 'a'*40),
                ('push', 'a'*40, 'invalid', 'a'*40),
                ('push', 'a'*40, 'a'*40, 'a'*40)):
            with self.subTest(event=event, before=before, head=head):
                self.assertTrue(change.runtime_required(event, before, head, parent, names))

    def test_exact_asset_closure_scope_cannot_hide_native_renderer_startup_or_java_edits(self):
        names = sorted(change.CLIENT_ASSET_CLOSURE_ALLOWED)
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for other in ('android/guest/texture_header_index.py', 'android/guest/client_interactive_diagnostic.py',
                'android/guest/native_responsiveness_contract.py',
                'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientRuntime.java',
                'upstream/ouroboros/Game/src/render/tex.c', 'unknown.py'):
            self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[other]))

    def test_streaming_pass_retains_exact_native_server_dex_and_limits_reviewed_helper_asset_scope(self):
        names = sorted(change.CLIENT_STREAMING_ALLOWED)
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for other in ('android/guest/local_character_server.py', 'android/guest/native_responsiveness_contract.py',
                'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientRuntime.java',
                'patches/client-loading/0001-known-length-string-copy-and-profile.patch', 'unknown.py'):
            self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[other]))

    def test_visual_pass_routes_only_its_explicit_client_assets_without_native_or_java_changes(self):
        names = sorted(change.VISUAL_ALLOWED)
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for other in ('android/guest/character_server_data_cache.py', 'android/guest/local_character_server.py',
                'android/guest/client_startup_diagnostic.py', 'android/guest/native_responsiveness_contract.py',
                'patches/startup-bundle-client/0001-verified-texture-root.patch',
                'tools/android/interactive/package_startup_bundle_client.py',
                'assets/atlas-world-supplement-manifest.json',
                'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientRuntime.java',
                'upstream/ouroboros/Game/src/render/tex.c', 'unknown.py'):
            with self.subTest(other=other):
                self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[other]))

    def test_bundle_routes_only_exact_explicit_native_and_guest_paths_to_its_own_pipeline(self):
        names = sorted(change.BUNDLE_ALLOWED)
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for other in ('upstream/ouroboros/DBServer/src/container_sql.c',
                'upstream/ouroboros/Game/src/render/tex.c', 'android/guest/local_login_server.py',
                'patches/startup-bundle/unreviewed.patch', 'android/native/client-launcher.c',
                'assets/server-cache-manifest.json', 'android/interactive/src/main/AndroidManifest.xml',
                'unreviewed.py'):
            with self.subTest(other=other):
                self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[other]))

    def test_bundle_dispatch_and_invalid_or_ambiguous_history_request_full_runtime(self):
        names = sorted(change.BUNDLE_ALLOWED)
        for event, before, head, parent in (
                ('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40),
                ('pull_request', 'a'*40, 'b'*40, 'a'*40),
                ('push', '0'*40, 'b'*40, '0'*40),
                ('push', 'c'*40, 'b'*40, 'a'*40),
                ('push', 'invalid', 'b'*40, 'a'*40),
                ('push', 'a'*40, 'invalid', 'a'*40),
                ('push', 'a'*40, None, 'a'*40),
                ('push', 'a'*40, 'a'*40, 'a'*40)):
            with self.subTest(event=event, before=before, head=head):
                self.assertTrue(change.runtime_required(event, before, head, parent, names))

    def test_setup_wrapper_reuses_runtime_for_its_exact_known_scope(self):
        names = sorted(change.SETUP_ALLOWED)
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for other in ('android/native/unreviewed-setup.c',
                'upstream/ouroboros/DBServer/src/dbinit.c', 'android/guest/diagnostic.py',
                'android/interactive/src/main/AndroidManifest.xml', 'unreviewed.py'):
            with self.subTest(other=other):
                self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[other]))

    def test_setup_dispatch_and_ambiguous_history_request_runtime(self):
        names = sorted(change.SETUP_ALLOWED)
        for event, before, head, parent in (
                ('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40),
                ('pull_request', 'a'*40, 'b'*40, 'a'*40),
                ('push', '0'*40, 'b'*40, '0'*40),
                ('push', 'c'*40, 'b'*40, 'a'*40),
                ('push', 'invalid', 'b'*40, 'a'*40),
                ('push', 'a'*40, 'a'*40, 'a'*40)):
            with self.subTest(event=event, before=before):
                self.assertTrue(change.runtime_required(event, before, head, parent, names))

    def test_receipt_cleanup_reuses_native_build_and_unknown_changes_remain_closed(self):
        names = sorted(change.RECEIPT_ALLOWED)
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40,
            names+['android/native/unreviewed-startup.c']))

    def test_exact_startup_derivative_routes_to_its_native_and_apk_pipeline(self):
        names = sorted(change.STARTUP_ALLOWED)
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40,
            names+['upstream/ouroboros/DBServer/src/dbinit.c']))

    def test_levelup_route_has_precedence_and_cannot_hide_retained_game_or_native_changes(self):
        names = sorted(change.LEVELUP_UI_REPAIR_ALLOWED)
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for other in ('upstream/ouroboros/Game/src/render/tex.c', 'android/guest/diagnostic.py',
                'patches/startup-bundle/0001-pg-cancelled-child-insert.patch', 'unknown.py'):
            with self.subTest(other=other):
                self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[other]))

    def test_only_direct_push_of_bounded_host_or_gameplay_changes_can_route_runtime(self):
        parent, head = 'a' * 40, 'b' * 40
        known = sorted(change.SHELL_ONLY)
        self.assertFalse(change.runtime_required('push', parent, head, parent, known))
        candidate = sorted((change.SHELL_ONLY | change.RESPONSIVENESS_ONLY) - change.BUNDLE_MARKERS - change.VISUAL_MARKERS - change.CLIENT_LOADING_MARKERS - change.CLIENT_STREAMING_MARKERS - change.CLIENT_ASSET_CLOSURE_MARKERS - change.CLIENT_STARTUP_FOLLOWUP_MARKERS - change.LEVELUP_UI_REPAIR_MARKERS - change.REOPEN_STARTUP_REPAIR_MARKERS - change.UI_BEACON_MARKERS)
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

    def test_client_loading_reuses_server_donor_only_for_its_exact_game_and_acceptance_scope(self):
        names = sorted(change.CLIENT_LOADING_ALLOWED)
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for other in ('upstream/ouroboros/DBServer/src/container_sql.c',
                'upstream/ouroboros/libs/UtilitiesLib/src/utils/textparser.c',
                'android/app/src/main/java/io/github/russianranger/cohdiagnostic/SetupMemoryGuard.java',
                'android/guest/local_character_server.py', 'unreviewed.py'):
            with self.subTest(other=other):
                self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[other]))


    def test_task_derivative_routes_to_its_own_workflow_but_unknown_native_edits_do_not(self):
        paths = ['.github/workflows/android-task-gate.yml',
            'android/guest/task_gate_evidence.py', 'android/guest/server_animation_package.py',
            'android/guest/task-gate.json',
            'tools/android/atlasgame/prepare_server_animations.py',
            'tools/android/interactive/test_task_gate_integration.py']
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, paths))
        self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40,
            paths+['upstream/ouroboros/MapServer/src/svr/svrinit.c']))
