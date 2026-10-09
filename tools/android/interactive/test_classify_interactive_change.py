import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('interactive_change_classifier',
    Path(__file__).with_name('classify_interactive_change.py'))
change = importlib.util.module_from_spec(spec)
spec.loader.exec_module(change)


class QualificationRoutingTests(unittest.TestCase):
    def test_session_repair_exact_scope_retains_runtime_and_rejects_unknown_neighbors(self):
        from classify_storage_cleanup_change import SESSION_REPAIR_ALLOWED, SESSION_REPAIR_DOCS
        for names in (sorted(SESSION_REPAIR_ALLOWED), sorted(SESSION_REPAIR_DOCS)):
            self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
            for foreign in ('android/guest/client_gpu_profile.py',
                    'android/guest/native_responsiveness_contract.py', 'assets/client-runtime.zip',
                    'upstream/ouroboros/libs/UtilitiesLib/src/components/WorkerThread.c', 'foreign.py'):
                self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]))
            self.assertTrue(change.runtime_required('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names))
            self.assertTrue(change.runtime_required('push', 'c'*40, 'b'*40, 'a'*40, names))

    def test_render_pipeline_exact_sources_and_publication_docs_reuse_owned_runtime(self):
        from classify_storage_cleanup_change import RENDER_PIPELINE_ALLOWED, RENDER_PIPELINE_DOCS, RENDER_PIPELINE_MARKERS
        for names in (sorted(RENDER_PIPELINE_ALLOWED), sorted(RENDER_PIPELINE_DOCS)):
            self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for marker in RENDER_PIPELINE_MARKERS:
            self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, [marker]), marker)
        names = sorted(RENDER_PIPELINE_ALLOWED)
        for foreign in ('android/native/client-launcher.c', 'android/runtime-lock.json',
                'upstream/ouroboros/Game/src/render/thread/rt_queue.c',
                'android/guest/local_character_server.py', 'assets/client-visual-manifest.json',
                'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientSurface.java',
                'patches/client-render-pipeline/unreviewed.patch',
                'database/client-render-pipeline/overlay/Game/src/unreviewed.h',
                'tools/android/interactive/test_client_render_pipeline_unreviewed.py', 'foreign.py'):
            self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]), foreign)

    def test_render_pipeline_scope_cannot_mask_ambiguous_history_or_docs_neighbors(self):
        from classify_storage_cleanup_change import RENDER_PIPELINE_ALLOWED, RENDER_PIPELINE_DOCS
        names = sorted(RENDER_PIPELINE_ALLOWED)
        for event, before, head, parent in (
                ('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40),
                ('pull_request', 'a'*40, 'b'*40, 'a'*40),
                ('push', '0'*40, 'b'*40, '0'*40),
                ('push', 'c'*40, 'b'*40, 'a'*40),
                ('push', 'invalid', 'b'*40, 'a'*40),
                ('push', 'a'*40, 'invalid', 'a'*40),
                ('push', 'a'*40, 'b'*40, None),
                ('push', 'a'*40, 'a'*40, 'a'*40)):
            with self.subTest(event=event, before=before, head=head):
                self.assertTrue(change.runtime_required(event, before, head, parent, names))
        names = sorted(RENDER_PIPELINE_DOCS)
        for foreign in ('docs/COH-PERFORMANCE-0.13.22.md',
                'docs/android-evidence/render-pipeline-0.13.22-publication-neighbor.json',
                'android/guest/local_character_server.py', 'foreign.md'):
            self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]), foreign)
        self.assertTrue(change.runtime_required('push', 'c'*40, 'b'*40, 'a'*40, names))
        self.assertTrue(change.runtime_required('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names))

    def test_gpu_profile_reuses_owned_runtime_and_rejects_unreviewed_neighbor_paths(self):
        from classify_storage_cleanup_change import GPU_PROFILE_ALLOWED, GPU_PROFILE_DOCS, gpu_profile_push
        for names in (sorted(GPU_PROFILE_ALLOWED), sorted(GPU_PROFILE_DOCS)):
            self.assertFalse(change.runtime_required('push','a'*40,'b'*40,'a'*40,names))
            for foreign in ('android/guest/native_responsiveness_contract.py',
                    'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientSurface.java',
                    'android/runtime-lock.json', 'unreviewed.py'):
                self.assertFalse(gpu_profile_push('push','a'*40,'b'*40,'a'*40,names+[foreign]))
                self.assertTrue(change.runtime_required('push','a'*40,'b'*40,'a'*40,names+[foreign]))

    def test_renderer_attribution_setup_fixture_companion_retains_standalone_setup_owner(self):
        from classify_storage_cleanup_change import renderer_attribution_push, setup_push, setup_required
        fixture = 'tools/android/interactive/test_setup_service.py'
        names = ['tools/android/interactive/build_client_renderer_attribution_apk.py', fixture]
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertFalse(renderer_attribution_push('push', 'a'*40, 'b'*40, 'a'*40, [fixture]))
        self.assertTrue(setup_push('push', 'a'*40, 'b'*40, 'a'*40, [fixture]))
        self.assertTrue(setup_required('push', 'a'*40, 'b'*40, 'a'*40, [fixture]))
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, [fixture]))
        for foreign in ('tools/android/interactive/test_setup_service_neighbor.py',
                'tools/android/interactive/test_setup_memory_package.py'):
            self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]))

    def test_renderer_attribution_finite_game_guest_and_capture_scope_reuses_owned_runtime(self):
        from classify_storage_cleanup_change import RENDERER_ATTRIBUTION_ALLOWED, RENDERER_ATTRIBUTION_SOURCES
        names = sorted(RENDERER_ATTRIBUTION_ALLOWED)
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for name in sorted(RENDERER_ATTRIBUTION_SOURCES):
            with self.subTest(source=name):
                self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, [name]))
        for foreign in ('android/guest/client_interactive_diagnostic.py', 'android/guest/local_login_server.py',
                'android/native/client-launcher.c', 'upstream/ouroboros/Game/src/render/thread/rt_queue.c',
                'upstream/ouroboros/DBServer/src/container_sql.c', 'assets/client-visual-manifest.json',
                'android/interactive/src/main/AndroidManifest.xml',
                'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientInput.java',
                'patches/client-renderer-attribution/unreviewed.patch',
                'database/client-renderer-attribution/overlay/Game/src/unreviewed.h',
                'tools/android/interactive/test_client_renderer_attribution_unreviewed.py',
                'tools/android/interactive/build_client_sidebar_apk.py', 'foreign.py'):
            with self.subTest(foreign=foreign):
                self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]))

    def test_renderer_attribution_owner_marker_cannot_mask_ambiguous_history_or_docs_only(self):
        from classify_storage_cleanup_change import RENDERER_ATTRIBUTION_ALLOWED, RENDERER_ATTRIBUTION_SOURCES
        names = sorted(RENDERER_ATTRIBUTION_ALLOWED)
        for event, before, head, parent, files in (
                ('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names),
                ('pull_request', 'a'*40, 'b'*40, 'a'*40, names),
                ('push', '0'*40, 'b'*40, '0'*40, names),
                ('push', 'c'*40, 'b'*40, 'a'*40, names),
                ('push', 'invalid', 'b'*40, 'a'*40, names),
                ('push', 'a'*40, 'invalid', 'a'*40, names),
                ('push', 'a'*40, 'b'*40, None, names),
                ('push', 'a'*40, 'a'*40, 'a'*40, names),
                ('push', 'a'*40, 'b'*40, 'a'*40, []),
                ('push', 'a'*40, 'b'*40, 'a'*40, sorted(RENDERER_ATTRIBUTION_ALLOWED-RENDERER_ATTRIBUTION_SOURCES))):
            with self.subTest(event=event, before=before, head=head):
                self.assertTrue(change.runtime_required(event, before, head, parent, files))

    def test_renderer_attribution_publication_docs_cannot_hide_neighbors(self):
        from classify_storage_cleanup_change import RENDERER_ATTRIBUTION_DOCS
        names = sorted(RENDERER_ATTRIBUTION_DOCS)
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for foreign in ('foreign.md', 'docs/COH-PERFORMANCE-0.13.19.md',
                'android/native/client-launcher.c', 'android/guest/local_login_server.py'):
            with self.subTest(foreign=foreign):
                self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]))
        self.assertTrue(change.runtime_required('push', 'c'*40, 'b'*40, 'a'*40, names))
        self.assertTrue(change.runtime_required('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names))

    def test_sidebar_fixture_qualification_correction_does_not_admit_neighboring_tests(self):
        names = ['tools/android/interactive/build_client_sidebar_apk.py',
            'tools/android/interactive/test_fresh_profile_recovery.py']
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for foreign in ('tools/android/interactive/test_fresh_profile_recovery_extra.py',
                'tools/android/interactive/test_storage_recovery_ui.py'):
            self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]))
        self.assertTrue(change.runtime_required('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names))

    def test_sidebar_android_scope_bypasses_full_runtime_only_for_exact_direct_push(self):
        from classify_storage_cleanup_change import SIDEBAR_ALLOWED
        names = sorted(SIDEBAR_ALLOWED)
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for foreign in ('android/guest/client_startup_diagnostic.py', 'android/native/client-launcher.c',
                'upstream/ouroboros/Game/src/game.c', 'assets/client-ui-sweep-manifest.json',
                'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientSurface.java',
                'tools/android/interactive/test_client_sidebar_foreign.py',
                'android/interactive/src/main/AndroidManifest.xml', 'foreign.py'):
            with self.subTest(foreign=foreign):
                self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]))
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

    def test_sidebar_publication_checkpoint_cannot_mask_unrelated_changes(self):
        names = ['docs/HANDOFF.md', 'docs/android-evidence/client-sidebar-0.13.18-publication.json']
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for foreign in ('foreign.md', 'android/guest/local_character_server.py',
                'android/native/client-launcher.c'):
            self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]))
        self.assertTrue(change.runtime_required('push', 'c'*40, 'b'*40, 'a'*40, names))
        self.assertTrue(change.runtime_required('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names))

    def test_gameplay_performance_only_bypasses_full_runtime_for_exact_reviewed_scope(self):
        from classify_storage_cleanup_change import GAMEPLAY_PERFORMANCE_ALLOWED
        names = sorted(GAMEPLAY_PERFORMANCE_ALLOWED)
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for foreign in ('android/guest/local_character_server.py', 'android/native/client-launcher.c',
                'upstream/ouroboros/Game/src/game.c', 'assets/client-ui-sweep-manifest.json',
                'patches/client-gameplay-performance/foreign.patch',
                'database/client-gameplay-performance/overlay/Game/src/foreign.h',
                'tools/android/interactive/test_client_gameplay_performance_foreign.py',
                'android/interactive/src/main/AndroidManifest.xml', 'foreign.py'):
            with self.subTest(foreign=foreign):
                self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]))
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

    def test_gameplay_publication_docs_skip_runtime_without_hiding_foreign_edit(self):
        names = ['docs/HANDOFF.md', 'docs/android-evidence/performance-0.13.17-publication.json']
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for foreign in ('foreign.md', 'android/guest/local_character_server.py',
                'android/native/client-launcher.c'):
            with self.subTest(foreign=foreign):
                self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]))
        self.assertTrue(change.runtime_required('push', 'c'*40, 'b'*40, 'a'*40, names))
        self.assertTrue(change.runtime_required('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names))

    def test_scene_performance_is_finite_game_only_and_requires_immediate_parent(self):
        from classify_storage_cleanup_change import SCENE_PERFORMANCE_ALLOWED
        names = sorted(SCENE_PERFORMANCE_ALLOWED)
        self.assertFalse(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for foreign in ('android/guest/local_character_server.py', 'android/native/client-launcher.c',
                'upstream/ouroboros/Game/src/game.c', 'foreign.py'):
            self.assertTrue(change.runtime_required('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]))
        self.assertTrue(change.runtime_required('push', 'c'*40, 'b'*40, 'a'*40, names))
        self.assertTrue(change.runtime_required('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names))

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
