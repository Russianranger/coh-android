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
    def test_render_queue_exact_scope_defers_all_historical_publishers(self):
        from classify_interactive_change import runtime_required
        functions=(change.task_required,change.cleanup_required,change.recovery_required,
            change.receipt_required,change.schedule_required,change.setup_required,
            change.bundle_required,change.visual_required,change.loading_required,
            change.streaming_required,change.asset_closure_required,change.startup_followup_required,
            change.levelup_ui_repair_required,change.reopen_startup_repair_required,
            change.ui_beacon_required,runtime_required)
        for names in (sorted(change.RENDER_QUEUE_ALLOWED),sorted(change.RENDER_QUEUE_DOCS)):
            self.assertTrue(change.render_queue_owned('push','a'*40,'b'*40,'a'*40,names))
            for function in functions:
                self.assertFalse(function('push','a'*40,'b'*40,'a'*40,names),function.__name__)
                for foreign in ('android/guest/client_interactive_diagnostic.py',
                        'android/guest/character_session_budget.py',change.JAVA+'ClientRuntime.java',
                        'assets/client-runtime.zip','patches/client-render-queue/new.patch',
                        'upstream/ouroboros/libs/UtilitiesLib/src/components/WorkerThread.c','unreviewed.py'):
                    self.assertTrue(function('push','a'*40,'b'*40,'a'*40,names+[foreign]),function.__name__)

    def test_render_queue_host_correction_requires_explicit_reuse_instead_of_another_Game_build(self):
        names=['tools/android/interactive/build_client_render_queue_apk.py']
        self.assertTrue(change.render_queue_push('push','a'*40,'b'*40,'a'*40,names))
        self.assertFalse(change.render_queue_native_push('push','a'*40,'b'*40,'a'*40,names))
        self.assertTrue(change.render_queue_native_push('push','a'*40,'b'*40,'a'*40,
            sorted(change.RENDER_QUEUE_ALLOWED)))
        for native in change.RENDER_QUEUE_NATIVE_INPUTS:
            self.assertTrue(change.render_queue_native_push('push','a'*40,'b'*40,'a'*40,names+[native]))
        for foreign in ('patches/client-render-queue/foreign.patch',change.JAVA+'ClientRuntime.java'):
            self.assertFalse(change.render_queue_native_push('push','a'*40,'b'*40,'a'*40,
                names+sorted(change.RENDER_QUEUE_NATIVE_INPUTS)+[foreign]))

    def test_render_queue_shared_helpers_need_marker_and_docs_need_publication_evidence(self):
        marker='tools/android/interactive/build_client_render_queue_apk.py'
        for name in change.RENDER_QUEUE_HELPERS:
            self.assertFalse(change.render_queue_push('push','a'*40,'b'*40,'a'*40,[name]))
            self.assertTrue(change.render_queue_push('push','a'*40,'b'*40,'a'*40,[name,marker]))
        names=sorted(change.RENDER_QUEUE_ALLOWED)
        for event,before,head,parent in (('workflow_dispatch','a'*40,'b'*40,'a'*40),
                ('push','c'*40,'b'*40,'a'*40),('push','0'*40,'b'*40,'0'*40),('push','a'*40,'a'*40,'a'*40)):
            self.assertFalse(change.render_queue_owned(event,before,head,parent,names))
        self.assertFalse(change.render_queue_docs('push','a'*40,'b'*40,'a'*40,['docs/HANDOFF.md']))
        self.assertFalse(change.render_queue_docs('push','a'*40,'b'*40,'a'*40,
            sorted(change.RENDER_QUEUE_DOCS)+['docs/android-evidence/render-queue-0.13.25-publication-neighbor.json']))

    def test_setup_copy_exact_scope_defers_all_historical_publishers(self):
        from classify_interactive_change import runtime_required
        functions=(change.task_required,change.cleanup_required,change.recovery_required,
            change.receipt_required,change.schedule_required,change.setup_required,
            change.bundle_required,change.visual_required,change.loading_required,
            change.streaming_required,change.asset_closure_required,change.startup_followup_required,
            change.levelup_ui_repair_required,change.reopen_startup_repair_required,
            change.ui_beacon_required,runtime_required)
        for names in (sorted(change.SETUP_COPY_ALLOWED),sorted(change.SETUP_COPY_DOCS)):
            self.assertTrue(change.setup_copy_owned('push','a'*40,'b'*40,'a'*40,names))
            for function in functions:
                self.assertFalse(function('push','a'*40,'b'*40,'a'*40,names),function.__name__)
                for foreign in ('android/guest/client_interactive_diagnostic.py',
                        'android/guest/character_session_budget.py',change.JAVA+'ClientActivity.java',
                        'assets/client-runtime.zip','patches/client-render-pipeline/new.patch','unreviewed.py'):
                    self.assertTrue(function('push','a'*40,'b'*40,'a'*40,names+[foreign]),function.__name__)

    def test_setup_copy_shared_java_and_reuse_fixture_require_new_owner_marker(self):
        marker='tools/android/interactive/build_setup_copy_repair_apk.py'
        for name in change.SETUP_COPY_SOURCES-change.SETUP_COPY_MARKERS:
            self.assertFalse(change.setup_copy_push('push','a'*40,'b'*40,'a'*40,[name]))
            self.assertTrue(change.setup_copy_push('push','a'*40,'b'*40,'a'*40,[name,marker]))
        names=sorted(change.SETUP_COPY_ALLOWED)
        for event,before,head,parent in (('workflow_dispatch','a'*40,'b'*40,'a'*40),
                ('push','c'*40,'b'*40,'a'*40),('push','0'*40,'b'*40,'0'*40),('push','a'*40,'a'*40,'a'*40)):
            self.assertFalse(change.setup_copy_owned(event,before,head,parent,names))
        self.assertFalse(change.setup_copy_docs('push','a'*40,'b'*40,'a'*40,['docs/HANDOFF.md']))
        self.assertFalse(change.setup_copy_docs('push','a'*40,'b'*40,'a'*40,
            sorted(change.SETUP_COPY_DOCS)+['docs/android-evidence/setup-copy-0.13.24-publication-neighbor.json']))

    def test_session_repair_exact_scope_defers_all_fifteen_historical_publishers(self):
        from classify_interactive_change import runtime_required
        functions = (change.task_required, change.cleanup_required, change.recovery_required,
            change.receipt_required, change.schedule_required, change.setup_required,
            change.bundle_required, change.visual_required, change.loading_required,
            change.streaming_required, change.asset_closure_required, change.startup_followup_required,
            change.levelup_ui_repair_required, change.reopen_startup_repair_required,
            change.ui_beacon_required, runtime_required)
        for names in (sorted(change.SESSION_REPAIR_ALLOWED), sorted(change.SESSION_REPAIR_DOCS)):
            self.assertTrue(change.session_repair_owned('push', 'a'*40, 'b'*40, 'a'*40, names))
            for function in functions:
                with self.subTest(function=function.__name__, names=names):
                    self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
                    for foreign in ('android/guest/client_startup_diagnostic.py',
                            'android/guest/native_responsiveness_contract.py',
                            change.JAVA+'ClientRuntime.java', 'assets/client-runtime.zip',
                            'patches/client-render-pipeline/new.patch', 'unreviewed.py'):
                        self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]))

    def test_session_repair_shared_helpers_require_marker_and_exact_immediate_parent(self):
        marker = 'tools/android/interactive/build_client_session_repair_apk.py'
        for shared in change.SESSION_REPAIR_SOURCES-change.SESSION_REPAIR_MARKERS:
            self.assertFalse(change.session_repair_push('push', 'a'*40, 'b'*40, 'a'*40, [shared]))
            self.assertTrue(change.session_repair_push('push', 'a'*40, 'b'*40, 'a'*40, [shared, marker]))
        names = sorted(change.SESSION_REPAIR_ALLOWED)
        for event, before, head, parent in (('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40),
                ('push', '0'*40, 'b'*40, '0'*40), ('push', 'c'*40, 'b'*40, 'a'*40),
                ('push', 'a'*40, 'a'*40, 'a'*40)):
            self.assertFalse(change.session_repair_owned(event, before, head, parent, names))
        self.assertFalse(change.session_repair_docs('push', 'a'*40, 'b'*40, 'a'*40, ['docs/HANDOFF.md']))
        self.assertFalse(change.session_repair_docs('push', 'a'*40, 'b'*40, 'a'*40,
            sorted(change.SESSION_REPAIR_DOCS)+['docs/android-evidence/session-repair-0.13.23-publication-neighbor.json']))

    def test_render_pipeline_exact_scope_defers_all_historical_publishers(self):
        names = sorted(change.RENDER_PIPELINE_ALLOWED)
        self.assertTrue(change.render_pipeline_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        for function in self.gameplay_historical_publishers():
            self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names), function.__name__)
        for marker in change.RENDER_PIPELINE_MARKERS:
            with self.subTest(marker=marker):
                self.assertTrue(change.render_pipeline_push('push', 'a'*40, 'b'*40, 'a'*40, [marker]))
                for function in self.gameplay_historical_publishers():
                    self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, [marker]), function.__name__)
        self.assertTrue(all(not any(character in name for character in '*?[')
            for name in change.RENDER_PIPELINE_ALLOWED))

    def test_render_pipeline_shared_helpers_and_administrative_files_require_owner_marker(self):
        marker = 'tools/android/interactive/build_client_render_pipeline_apk.py'
        shared = change.RENDER_PIPELINE_SOURCES-change.RENDER_PIPELINE_MARKERS
        administrative = {
            'tools/android/interactive/classify_storage_cleanup_change.py',
            'tools/android/interactive/classify_interactive_change.py',
            'tools/android/interactive/test_classify_storage_cleanup_change.py',
            'tools/android/interactive/test_classify_interactive_change.py',
        }
        self.assertEqual(shared, {
            'android/guest/client_gpu_profile.py',
            'android/guest/client_startup_diagnostic.py',
            'android/guest/native_responsiveness_contract.py',
            'android/guest/texture_header_index.py',
        })
        self.assertLessEqual(administrative, change.RENDER_PIPELINE_ALLOWED)
        self.assertTrue(administrative.isdisjoint(change.RENDER_PIPELINE_SOURCES))
        for path in shared | administrative:
            with self.subTest(path=path):
                self.assertFalse(change.render_pipeline_owned('push', 'a'*40, 'b'*40, 'a'*40, [path]))
                self.assertTrue(change.render_pipeline_push('push', 'a'*40, 'b'*40, 'a'*40, [path, marker]))

    def test_render_pipeline_cannot_hide_native_runtime_assets_or_neighboring_changes(self):
        names = sorted(change.RENDER_PIPELINE_ALLOWED)
        for foreign in ('android/native/client-launcher.c', 'android/runtime-lock.json',
                'upstream/ouroboros/UtilitiesLib/utils/WorkerThread.c',
                'upstream/ouroboros/Game/src/render/thread/rt_queue.c',
                'upstream/ouroboros/MapServer/src/entity/entity.c',
                'android/guest/local_character_server.py', 'android/guest/local_login_server.py',
                change.JAVA+'ClientSurface.java', 'android/interactive/src/main/AndroidManifest.xml',
                'assets/client-visual-manifest.json',
                'patches/client-render-pipeline/0002-unreviewed.patch',
                'database/client-render-pipeline/overlay/Game/src/unreviewed.h',
                'tools/android/interactive/test_client_render_pipeline_unreviewed.py',
                'tools/android/interactive/build_client_gpu_profile_apk.py', 'foreign.py'):
            with self.subTest(foreign=foreign):
                self.assertNotIn(foreign, change.RENDER_PIPELINE_ALLOWED)
                mixed = names+[foreign]
                self.assertFalse(change.render_pipeline_owned('push', 'a'*40, 'b'*40, 'a'*40, mixed))
                for function in self.gameplay_historical_publishers():
                    self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, mixed), function.__name__)

    def test_render_pipeline_requires_immediate_parent_and_nonempty_owner_scope(self):
        names = sorted(change.RENDER_PIPELINE_ALLOWED)
        for event, before, head, parent, files in (
                ('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names),
                ('pull_request', 'a'*40, 'b'*40, 'a'*40, names),
                ('push', '0'*40, 'b'*40, '0'*40, names),
                ('push', 'c'*40, 'b'*40, 'a'*40, names),
                ('push', 'invalid', 'b'*40, 'a'*40, names),
                ('push', 'a'*40, 'invalid', 'a'*40, names),
                ('push', 'a'*40, 'b'*40, None, names),
                ('push', 'a'*40, 'a'*40, 'a'*40, names),
                ('push', 'a'*40, 'b'*40, 'a'*40, [])):
            with self.subTest(event=event, before=before, head=head, files=files):
                self.assertFalse(change.render_pipeline_owned(event, before, head, parent, files))
                for function in self.gameplay_historical_publishers():
                    self.assertTrue(function(event, before, head, parent, files), function.__name__)
        self.assertFalse(change.render_pipeline_owned('push', 'a'*40, 'b'*40, 'a'*40, ['docs/HANDOFF.md']))

    def test_render_pipeline_publication_checkpoint_is_exact_docs_only(self):
        names = sorted(change.RENDER_PIPELINE_DOCS)
        self.assertTrue(change.render_pipeline_docs('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertFalse(change.render_pipeline_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        for function in self.gameplay_historical_publishers():
            self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names), function.__name__)
            for foreign in ('docs/COH-PERFORMANCE-0.13.22.md',
                    'docs/android-evidence/render-pipeline-0.13.22-publication-neighbor.json',
                    'android/guest/local_character_server.py', 'foreign.md'):
                self.assertFalse(change.render_pipeline_docs('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]))
                self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]), function.__name__)
            self.assertTrue(function('push', 'c'*40, 'b'*40, 'a'*40, names), function.__name__)
            self.assertTrue(function('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names), function.__name__)

    def test_render_pipeline_classifier_cli_defers_all_fifteen_historical_gate_outputs(self):
        for names in (sorted(change.RENDER_PIPELINE_ALLOWED), sorted(change.RENDER_PIPELINE_DOCS)):
            with self.subTest(names=names), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary)/'scope-output.txt'
                environment = {'GITHUB_EVENT_NAME': 'push', 'COH_PUSH_BEFORE': 'a'*40,
                    'GITHUB_OUTPUT': str(output)}
                values = ['a'*40+'\n', 'b'*40+'\n', ('\0'.join(names)+'\0').encode()]
                with mock.patch.dict(change.os.environ, environment), \
                        mock.patch.object(change.subprocess, 'check_output', side_effect=values), \
                        contextlib.redirect_stdout(io.StringIO()):
                    change.main()
                expected = ''.join(function.__name__+'=false\n'
                    for function in self.gameplay_historical_publishers()[:-1])
                self.assertEqual(output.read_text(), expected)

    def test_gpu_profile_exact_scope_defers_historical_publishers_without_native_mutations(self):
        names = sorted(change.GPU_PROFILE_ALLOWED)
        self.assertTrue(change.gpu_profile_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        for function in self.gameplay_historical_publishers():
            self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names), function.__name__)
        for path in ('android/guest/native_responsiveness_contract.py',
                change.JAVA+'ClientSurface.java', change.JAVA+'ClientService.java',
                'patches/client-renderer-attribution/0001-renderer-attribution-and-visible-fps.patch',
                'upstream/ouroboros/Game/src/graphics/gfx.c', 'android/runtime-lock.json',
                'tools/android/gpu-runtime/unreviewed.py', 'android/native/coh-extra-probe.c'):
            self.assertFalse(change.gpu_profile_push('push', 'a'*40, 'b'*40, 'a'*40, names+[path]), path)
            for function in self.gameplay_historical_publishers():
                self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[path]), function.__name__+': '+path)

    def test_gpu_profile_owner_requires_immediate_parent_and_explicit_source_marker(self):
        self.assertFalse(change.gpu_profile_push('push', 'a'*40, 'b'*40, 'a'*40, ['docs/HANDOFF.md']))
        for path in change.GPU_PROFILE_SOURCES-change.GPU_PROFILE_MARKERS:
            self.assertFalse(change.gpu_profile_push('push','a'*40,'b'*40,'a'*40,[path]), path)
            self.assertTrue(change.gpu_profile_push('push','a'*40,'b'*40,'a'*40,
                [path,'tools/android/interactive/build_client_gpu_profile_apk.py']), path)
        self.assertFalse(change.renderer_attribution_push('push','a'*40,'b'*40,'a'*40,
            sorted(change.GPU_PROFILE_ALLOWED)))
        for event, before, head, parent in (('workflow_dispatch','a'*40,'b'*40,'a'*40),
                ('push','0'*40,'b'*40,'0'*40), ('push','c'*40,'b'*40,'a'*40),
                ('push','a'*40,'a'*40,'a'*40)):
            self.assertFalse(change.gpu_profile_push(event,before,head,parent,sorted(change.GPU_PROFILE_ALLOWED)))
        for path in change.GPU_PROFILE_MARKERS:
            self.assertTrue(change.gpu_profile_push('push','a'*40,'b'*40,'a'*40,[path]), path)

    def test_gpu_profile_docs_are_exact_publication_checkpoint(self):
        names = sorted(change.GPU_PROFILE_DOCS)
        self.assertTrue(change.gpu_profile_docs('push','a'*40,'b'*40,'a'*40,names))
        self.assertFalse(change.gpu_profile_push('push','a'*40,'b'*40,'a'*40,names))
        for function in self.gameplay_historical_publishers():
            self.assertFalse(function('push','a'*40,'b'*40,'a'*40,names), function.__name__)
        self.assertFalse(change.gpu_profile_docs('push','a'*40,'b'*40,'a'*40,['docs/HANDOFF.md']))
        self.assertFalse(change.gpu_profile_docs('push','a'*40,'b'*40,'a'*40,names+['foreign.md']))

    def test_renderer_attribution_setup_fixture_is_only_an_exact_companion(self):
        fixture = 'tools/android/interactive/test_setup_service.py'
        names = ['tools/android/interactive/build_client_renderer_attribution_apk.py', fixture]
        self.assertIn(fixture, change.RENDERER_ATTRIBUTION_ALLOWED)
        self.assertNotIn(fixture, change.RENDERER_ATTRIBUTION_SOURCES)
        self.assertTrue(change.renderer_attribution_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertFalse(change.renderer_attribution_push('push', 'a'*40, 'b'*40, 'a'*40, [fixture]))
        self.assertTrue(change.setup_push('push', 'a'*40, 'b'*40, 'a'*40, [fixture]))
        self.assertTrue(change.setup_required('push', 'a'*40, 'b'*40, 'a'*40, [fixture]))
        for function in self.gameplay_historical_publishers():
            self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
            for foreign in ('tools/android/interactive/test_setup_service_neighbor.py',
                    'tools/android/interactive/test_setup_memory_package.py'):
                with self.subTest(function=function.__name__, foreign=foreign):
                    self.assertFalse(change.renderer_attribution_push('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]))
                    self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]))

    def test_renderer_attribution_routes_its_exact_native_capture_and_guest_lane(self):
        names = sorted(change.RENDERER_ATTRIBUTION_ALLOWED)
        self.assertTrue(change.renderer_attribution_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        for owner in (change.sidebar_push, change.gameplay_performance_push,
                change.scene_performance_push, change.performance_push):
            self.assertFalse(owner('push', 'a'*40, 'b'*40, 'a'*40, names))
        for function in self.gameplay_historical_publishers():
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))

    def test_renderer_attribution_individual_reviewed_owner_paths_route_without_broad_globs(self):
        for name in sorted(change.RENDERER_ATTRIBUTION_SOURCES):
            with self.subTest(source=name):
                self.assertTrue(change.renderer_attribution_push('push', 'a'*40, 'b'*40, 'a'*40, [name]))
                for owner in (change.sidebar_push, change.gameplay_performance_push,
                        change.scene_performance_push, change.performance_push):
                    self.assertFalse(owner('push', 'a'*40, 'b'*40, 'a'*40, [name]))
                for function in self.gameplay_historical_publishers():
                    self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, [name]))
        self.assertTrue(all(not any(character in name for character in '*?[')
            for name in change.RENDERER_ATTRIBUTION_ALLOWED))

    def test_renderer_attribution_cannot_hide_native_server_asset_or_neighbor_mutations(self):
        names = sorted(change.RENDERER_ATTRIBUTION_ALLOWED)
        forbidden = ('android/native/client-launcher.c', 'android/runtime-lock.json',
            'upstream/ouroboros/Game/src/render/thread/rt_queue.c',
            'upstream/ouroboros/MapServer/src/entity/entity.c',
            'android/guest/local_login_server.py', 'android/guest/client_interactive_diagnostic.py',
            'android/guest/native_training_save.py', 'android/guest/local_character_server_neighbor.py',
            change.JAVA+'ClientInput.java', change.JAVA+'InteractiveRfbClient.java',
            change.JAVA+'ClientSurfaceNeighbor.java', 'android/interactive/src/main/AndroidManifest.xml',
            'android/interactive/src/main/res/drawable/foreign.xml',
            'assets/client-visual-manifest.json', 'assets/atlas-beacons.zip',
            'patches/client-renderer-attribution/0002-unreviewed.patch',
            'database/client-renderer-attribution/overlay/Game/src/unreviewed.h',
            'tools/android/interactive/test_client_renderer_attribution_unreviewed.py',
            'tools/android/interactive/test_client_surface_capture_neighbor.py',
            'tools/android/interactive/test_stock_power_delta_neighbor.py',
            'tools/android/interactive/package_client_gameplay_performance_native.py',
            'tools/android/interactive/build_client_sidebar_apk.py',
            'patches/client-gameplay-performance/0001-gameplay-cap-and-texture-diagnostics.patch',
            'tools/android/interactive/test_fresh_profile_recovery.py', 'foreign.py')
        for foreign in forbidden:
            with self.subTest(foreign=foreign):
                self.assertNotIn(foreign, change.RENDERER_ATTRIBUTION_ALLOWED)
                mixed = names+[foreign]
                self.assertFalse(change.renderer_attribution_push('push', 'a'*40, 'b'*40, 'a'*40, mixed))
                for function in self.gameplay_historical_publishers():
                    self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, mixed))

    def test_renderer_attribution_requires_exact_source_marker_and_immediate_parent(self):
        names = sorted(change.RENDERER_ATTRIBUTION_ALLOWED)
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
                ('push', 'a'*40, 'b'*40, 'a'*40,
                    sorted(change.RENDERER_ATTRIBUTION_ALLOWED-change.RENDERER_ATTRIBUTION_SOURCES))):
            with self.subTest(event=event, before=before, head=head, files=files):
                self.assertFalse(change.renderer_attribution_push(event, before, head, parent, files))
                for function in self.gameplay_historical_publishers():
                    self.assertTrue(function(event, before, head, parent, files))

    def test_renderer_attribution_publication_checkpoint_is_exact_docs_only(self):
        names = sorted(change.RENDERER_ATTRIBUTION_DOCS)
        self.assertTrue(change.renderer_attribution_docs('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertFalse(change.renderer_attribution_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        for function in self.gameplay_historical_publishers():
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
                for foreign in ('docs/COH-PERFORMANCE-0.13.19.md',
                        'docs/android-evidence/renderer-attribution-0.13.19-publication-neighbor.json',
                        'android/guest/local_character_server.py', 'foreign.md'):
                    self.assertFalse(change.renderer_attribution_docs('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]))
                self.assertTrue(function('push', 'c'*40, 'b'*40, 'a'*40, names))
                self.assertTrue(function('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertFalse(change.renderer_attribution_docs('push', 'a'*40, 'b'*40, 'a'*40, ['docs/HANDOFF.md']))
        for foreign in ('foreign.md', 'android/native/client-launcher.c'):
            for function in self.gameplay_historical_publishers():
                self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]))

    def test_renderer_attribution_classifier_cli_defers_all_fifteen_historical_gate_outputs(self):
        for names in (sorted(change.RENDERER_ATTRIBUTION_ALLOWED), sorted(change.RENDERER_ATTRIBUTION_DOCS)):
            with self.subTest(names=names), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary)/'scope-output.txt'
                environment = {'GITHUB_EVENT_NAME': 'push', 'COH_PUSH_BEFORE': 'a'*40,
                    'GITHUB_OUTPUT': str(output)}
                values = ['a'*40+'\n', 'b'*40+'\n', ('\0'.join(names)+'\0').encode()]
                with mock.patch.dict(change.os.environ, environment), \
                        mock.patch.object(change.subprocess, 'check_output', side_effect=values), \
                        contextlib.redirect_stdout(io.StringIO()):
                    change.main()
                expected = ''.join(function.__name__+'=false\n'
                    for function in self.gameplay_historical_publishers()[:-1])
                self.assertEqual(output.read_text(), expected)

    def test_sidebar_retained_fresh_profile_fixture_correction_is_an_exact_companion(self):
        fixture = 'tools/android/interactive/test_fresh_profile_recovery.py'
        names = ['tools/android/interactive/build_client_sidebar_apk.py', fixture]
        self.assertTrue(change.sidebar_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertFalse(change.sidebar_push('push', 'a'*40, 'b'*40, 'a'*40, [fixture]))
        self.assertNotIn(fixture, change.SIDEBAR_SOURCES)
        for function in self.gameplay_historical_publishers():
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
                for foreign in ('tools/android/interactive/test_fresh_profile_recovery_extra.py',
                        'tools/android/interactive/test_storage_recovery_ui.py'):
                    self.assertFalse(change.sidebar_push('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]))
                    self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]))

    def test_sidebar_exact_android_scope_routes_to_its_owner_without_older_native_publication(self):
        names = sorted(change.SIDEBAR_ALLOWED)
        self.assertTrue(change.sidebar_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertFalse(change.scene_performance_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertFalse(change.gameplay_performance_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertFalse(change.performance_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        for function in self.gameplay_historical_publishers():
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))

    def test_sidebar_scope_cannot_hide_other_java_guest_native_resource_or_runtime_change(self):
        names = sorted(change.SIDEBAR_ALLOWED)
        forbidden = (change.JAVA+'ClientSurface.java', change.JAVA+'ClientAcceptance.java',
            change.JAVA+'ClientSessionBudget.java',
            'android/guest/client_interactive_diagnostic.py',
            'android/guest/native_responsiveness_contract.py', 'android/runtime-lock.json',
            'android/interactive/src/main/AndroidManifest.xml',
            'android/interactive/src/main/res/drawable/foreign.xml',
            'assets/client-ui-sweep-manifest.json', 'android/native/client-launcher.c',
            'patches/client-gameplay-performance/0001-gameplay-cap-and-texture-diagnostics.patch',
            'tools/android/interactive/test_client_sidebar_unreviewed.py', 'foreign.py')
        for foreign in forbidden:
            with self.subTest(foreign=foreign):
                mixed = names+[foreign]
                self.assertFalse(change.sidebar_push('push', 'a'*40, 'b'*40, 'a'*40, mixed))
                for function in self.gameplay_historical_publishers():
                    with self.subTest(function=function.__name__):
                        self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, mixed))

    def test_sidebar_source_marker_requires_valid_immediate_parent_push(self):
        names = sorted(change.SIDEBAR_ALLOWED)
        for event, before, head, parent, files in (
                ('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names),
                ('pull_request', 'a'*40, 'b'*40, 'a'*40, names),
                ('push', '0'*40, 'b'*40, '0'*40, names),
                ('push', 'c'*40, 'b'*40, 'a'*40, names),
                ('push', 'invalid', 'b'*40, 'a'*40, names),
                ('push', 'a'*40, 'invalid', 'a'*40, names),
                ('push', 'a'*40, 'a'*40, 'a'*40, names),
                ('push', 'a'*40, 'b'*40, 'a'*40, []),
                ('push', 'a'*40, 'b'*40, 'a'*40,
                    sorted(change.SIDEBAR_ALLOWED-change.SIDEBAR_SOURCES))):
            with self.subTest(event=event, before=before, head=head):
                self.assertFalse(change.sidebar_push(event, before, head, parent, files))
                for function in self.gameplay_historical_publishers():
                    self.assertTrue(function(event, before, head, parent, files))

    def test_sidebar_publication_checkpoint_accepts_only_named_evidence_and_handoff(self):
        names = ['docs/HANDOFF.md', 'docs/android-evidence/client-sidebar-0.13.18-publication.json']
        self.assertTrue(change.sidebar_docs('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertFalse(change.sidebar_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        for function in self.gameplay_historical_publishers():
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
                self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+['foreign.md']))
                self.assertTrue(function('push', 'c'*40, 'b'*40, 'a'*40, names))
                self.assertTrue(function('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names))
        for files in (['docs/HANDOFF.md'], names+['docs/COH-CLIENT-SIDEBAR-0.13.18.md'],
                names+[change.JAVA+'ClientActivity.java']):
            self.assertFalse(change.sidebar_docs('push', 'a'*40, 'b'*40, 'a'*40, files))

    def test_sidebar_classifier_cli_disables_every_older_owner_gate(self):
        names = sorted(change.SIDEBAR_ALLOWED)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)/'scope-output.txt'
            environment = {'GITHUB_EVENT_NAME': 'push', 'COH_PUSH_BEFORE': 'a'*40,
                'GITHUB_OUTPUT': str(output)}
            values = ['a'*40+'\n', 'b'*40+'\n', ('\0'.join(names)+'\0').encode()]
            with mock.patch.dict(change.os.environ, environment), \
                    mock.patch.object(change.subprocess, 'check_output', side_effect=values), \
                    contextlib.redirect_stdout(io.StringIO()):
                change.main()
            expected = ''.join(function.__name__+'=false\n'
                for function in self.gameplay_historical_publishers()[:-1])
            self.assertEqual(output.read_text(), expected)

    def gameplay_historical_publishers(self):
        from classify_interactive_change import runtime_required
        return (change.task_required, change.cleanup_required, change.recovery_required,
            change.receipt_required, change.schedule_required, change.setup_required,
            change.bundle_required, change.visual_required, change.loading_required,
            change.streaming_required, change.asset_closure_required,
            change.startup_followup_required, change.levelup_ui_repair_required,
            change.reopen_startup_repair_required, change.ui_beacon_required,
            runtime_required)

    def test_gameplay_performance_routes_exact_new_game_lane_away_from_older_publishers(self):
        names = sorted(change.GAMEPLAY_PERFORMANCE_ALLOWED)
        self.assertTrue(change.gameplay_performance_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertFalse(change.scene_performance_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertFalse(change.performance_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        for function in self.gameplay_historical_publishers():
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))

    def test_gameplay_performance_rejects_mixed_and_unreviewed_same_directory_changes(self):
        names = sorted(change.GAMEPLAY_PERFORMANCE_ALLOWED)
        forbidden = ('android/native/client-launcher.c', 'android/guest/local_character_server.py',
            change.JAVA+'ClientRuntime.java', 'android/interactive/src/main/AndroidManifest.xml',
            'android/runtime-lock.json', 'assets/client-ui-sweep-manifest.json',
            'upstream/ouroboros/Game/src/game.c',
            'patches/client-gameplay-performance/0002-unreviewed.patch',
            'database/client-gameplay-performance/overlay/Game/src/unreviewed.h',
            'tools/android/interactive/test_client_gameplay_performance_unreviewed.py',
            'foreign.py')
        for foreign in forbidden:
            with self.subTest(foreign=foreign):
                mixed = names+[foreign]
                self.assertFalse(change.gameplay_performance_push('push', 'a'*40, 'b'*40, 'a'*40, mixed))
                for function in self.gameplay_historical_publishers():
                    with self.subTest(function=function.__name__):
                        self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, mixed))

    def test_gameplay_performance_requires_source_marker_and_unambiguous_direct_push(self):
        names = sorted(change.GAMEPLAY_PERFORMANCE_ALLOWED)
        for event, before, head, parent, files in (
                ('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names),
                ('pull_request', 'a'*40, 'b'*40, 'a'*40, names),
                ('push', '0'*40, 'b'*40, '0'*40, names),
                ('push', 'c'*40, 'b'*40, 'a'*40, names),
                ('push', 'invalid', 'b'*40, 'a'*40, names),
                ('push', 'a'*40, 'invalid', 'a'*40, names),
                ('push', 'a'*40, 'a'*40, 'a'*40, names),
                ('push', 'a'*40, 'b'*40, 'a'*40, []),
                ('push', 'a'*40, 'b'*40, 'a'*40,
                    sorted(change.GAMEPLAY_PERFORMANCE_ALLOWED-change.GAMEPLAY_PERFORMANCE_SOURCES))):
            with self.subTest(event=event, before=before, head=head, files=files):
                self.assertFalse(change.gameplay_performance_push(event, before, head, parent, files))
                for function in self.gameplay_historical_publishers():
                    self.assertTrue(function(event, before, head, parent, files))

    def test_gameplay_publication_checkpoint_is_exact_docs_only(self):
        names = ['docs/HANDOFF.md', 'docs/android-evidence/performance-0.13.17-publication.json']
        self.assertTrue(change.gameplay_performance_docs('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertFalse(change.gameplay_performance_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        for function in self.gameplay_historical_publishers():
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
                self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+['unreviewed.md']))
                self.assertTrue(function('push', 'c'*40, 'b'*40, 'a'*40, names))
                self.assertTrue(function('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names))
        for files in (['docs/HANDOFF.md'], names+['docs/COH-PERFORMANCE-0.13.17.md'],
                names+['android/guest/client_startup_diagnostic.py']):
            self.assertFalse(change.gameplay_performance_docs('push', 'a'*40, 'b'*40, 'a'*40, files))

    def test_gameplay_classifier_cli_closes_each_historical_owner_gate(self):
        names = sorted(change.GAMEPLAY_PERFORMANCE_ALLOWED)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)/'scope-output.txt'
            environment = {'GITHUB_EVENT_NAME': 'push', 'COH_PUSH_BEFORE': 'a'*40,
                'GITHUB_OUTPUT': str(output)}
            values = ['a'*40+'\n', 'b'*40+'\n', ('\0'.join(names)+'\0').encode()]
            with mock.patch.dict(change.os.environ, environment), \
                    mock.patch.object(change.subprocess, 'check_output', side_effect=values), \
                    contextlib.redirect_stdout(io.StringIO()):
                change.main()
            expected = ''.join(function.__name__+'=false\n'
                for function in self.gameplay_historical_publishers()[:-1])
            self.assertEqual(output.read_text(), expected)

    def test_game_only_scene_performance_routes_historical_publishers_closed_and_unknowns_open(self):
        from classify_interactive_change import runtime_required
        names = sorted(change.SCENE_PERFORMANCE_ALLOWED)
        historical = (change.task_required, change.cleanup_required, change.recovery_required,
            change.receipt_required, change.schedule_required, change.setup_required, change.bundle_required,
            change.visual_required, change.loading_required, change.streaming_required,
            change.asset_closure_required, change.startup_followup_required,
            change.levelup_ui_repair_required, change.reopen_startup_repair_required,
            change.ui_beacon_required, runtime_required)
        self.assertTrue(change.scene_performance_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        for function in historical:
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
                for forbidden in ('android/native/client-launcher.c', 'android/guest/local_character_server.py',
                        'assets/client-ui-sweep-manifest.json', 'upstream/ouroboros/Game/src/game.c', 'foreign.py'):
                    self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[forbidden]))
                self.assertTrue(function('push', 'c'*40, 'b'*40, 'a'*40, names))
                self.assertTrue(function('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertFalse(change.performance_push('push', 'a'*40, 'b'*40, 'a'*40, names))

    def test_guest_only_performance_routes_all_historical_publishers_closed(self):
        from classify_interactive_change import runtime_required
        names = sorted(change.PERFORMANCE_ALLOWED-{'docs/android-evidence/performance-0.13.15-publication.json'})
        historical = (change.task_required, change.cleanup_required, change.recovery_required,
            change.receipt_required, change.schedule_required, change.setup_required, change.bundle_required,
            change.visual_required, change.loading_required, change.streaming_required,
            change.asset_closure_required, change.startup_followup_required,
            change.levelup_ui_repair_required, change.reopen_startup_repair_required,
            change.ui_beacon_required, runtime_required)
        self.assertTrue(change.performance_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        for function in historical:
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
                for forbidden in ('android/native/client-launcher.c', 'android/guest/atlas_beacon_package.py',
                        'assets/client-ui-sweep-manifest.json', 'foreign.py'):
                    self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[forbidden]))
                self.assertTrue(function('push', 'c'*40, 'b'*40, 'a'*40, names))
                self.assertTrue(function('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names))

    def test_known_host_verifier_checkpoint_skips_all_historical_builds_and_fails_closed(self):
        from classify_interactive_change import runtime_required
        names = [
            '.github/workflows/android-atlas-beacon-verification.yml',
            'tools/android/interactive/classify_storage_cleanup_change.py',
            'tools/android/interactive/test_classify_storage_cleanup_change.py',
            'docs/HANDOFF.md',
        ]
        historical = (change.task_required, change.cleanup_required, change.recovery_required,
            change.receipt_required, change.schedule_required, change.setup_required, change.bundle_required,
            change.visual_required, change.loading_required, change.streaming_required,
            change.asset_closure_required, change.startup_followup_required,
            change.levelup_ui_repair_required, change.reopen_startup_repair_required, runtime_required)
        self.assertTrue(change.ui_beacon_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        for function in historical:
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
                self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40,
                    names+['android/native/client-launcher.c']))
                self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40,
                    names+['unreviewed.py']))
                self.assertTrue(function('push', 'c'*40, 'b'*40, 'a'*40, names))

    def test_host_beacon_generation_workflow_has_no_publication_or_shipping_binary_step(self):
        root = Path(__file__).resolve().parents[3]
        source = (root/'.github/workflows/android-atlas-beacon-generation.yml').read_text()
        for required in ('C:/bcn-src', '--work C:/bcn-run', 'generate_atlas_beacons.py', '--recovery-artifact', '--recovery-metadata',
                '--original-generation-source', '--client-visual-archive', '--client-visual-manifest',
                '37377053417', '11379217768', '33296543',
                'a23fe422656874009013f56bc8a41a243a0511afb1d4fcb828196c03054731a4',
                '--timeout-seconds 5400', 'coh-ui-beacon-native', 'contents: read', 'cancel-in-progress: true',
                'Invoke-WebRequest', '1535592811', 'GH_TOKEN: ${{ github.token }}',
                '81f199d6380faa09261a85efea6fd3abca6ed58749b8cc68c75d1cd579d454a4'):
            self.assertIn(required, source)
        self.assertNotIn('cmake --build', source)
        self.assertIn("conclusion = $run.conclusion", source)
        self.assertIn("compile_conclusion = $compile[0].conclusion", source)
        self.assertEqual(source.count('contents: write'), 1)
        self.assertIn('release asset, as in the accepted server-cache workflow. No publishing step.', source)
        self.assertLess(source.index('core.autocrlf false'), source.index('actions/checkout@'))
        self.assertIn('Collect short-path host evidence on the repository drive', source)
        self.assertIn('Copy-Item -LiteralPath $source', source)
        self.assertIn('host-only-beacon-generator.pdb', source)
        self.assertIn('native-internal', source)
        self.assertIn('$count -ge 128', source)
        self.assertIn('$total + $file.Length -gt 268435456', source)
        evidence_upload = source.split('name: coh-ui-beacon-generation-evidence', 1)[1]
        self.assertNotIn('C:/', evidence_upload)
        self.assertIn('out/ui-beacon-native/evidence/', evidence_upload)
        for forbidden in ('build_ui_beacon_apk.py', 'softprops/action-gh-release', '--publish', 'COH_ATLAS_BEACON_REUSE_RUN_ID'):
            self.assertNotIn(forbidden, source)

    def test_required_geometry_cache_migration_routes_only_current_ui_beacon_work(self):
        from classify_interactive_change import runtime_required
        names = ['.github/workflows/android-atlas-beacon-generation.yml',
            'android/guest/atlas_beacon_package.py', 'android/guest/local_character_server.py',
            'tools/android/interactive/test_server_worktree_reuse.py']
        self.assertTrue(change.ui_beacon_required('push','a'*40,'b'*40,'a'*40,names))
        historical = (change.task_required, change.cleanup_required, change.recovery_required,
            change.receipt_required, change.schedule_required, change.setup_required, change.bundle_required,
            change.visual_required, change.loading_required, change.streaming_required,
            change.asset_closure_required, change.startup_followup_required, change.levelup_ui_repair_required,
            change.reopen_startup_repair_required, runtime_required)
        for function in historical:
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push','a'*40,'b'*40,'a'*40,names))
                self.assertTrue(function('push','a'*40,'b'*40,'a'*40,
                    names+['android/guest/server_data_cache.py']))

    def test_ui_beacon_scope_skips_all_historical_builds_and_fails_closed(self):
        from classify_interactive_change import runtime_required
        names = sorted(change.UI_BEACON_ALLOWED)
        historical = (change.task_required, change.cleanup_required, change.recovery_required,
            change.receipt_required, change.schedule_required, change.setup_required, change.bundle_required,
            change.visual_required, change.loading_required, change.streaming_required,
            change.asset_closure_required, change.startup_followup_required, change.levelup_ui_repair_required,
            change.reopen_startup_repair_required, runtime_required)
        self.assertTrue(change.ui_beacon_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertTrue(change.ui_beacon_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for function in historical:
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
                for foreign in ('android/native/client-launcher.c', 'android/guest/client_interactive_diagnostic.py',
                        'patches/levelup-ui-repair/0001-pg-empty-row-witness.patch', 'unreviewed.py'):
                    self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[foreign]))
                self.assertTrue(function('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40, names))
                self.assertTrue(function('push', 'c'*40, 'b'*40, 'a'*40, names))
        checkpoint = ['docs/HANDOFF.md', 'docs/android-evidence/ui-beacon-0.13.14-publication.json']
        for function in historical+(change.ui_beacon_required,):
            with self.subTest(checkpoint=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, checkpoint))
                self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, checkpoint+['unreviewed.md']))

    def test_reopen_startup_native_derivative_skips_historical_publication_and_closes_scope(self):
        from classify_interactive_change import runtime_required
        names = sorted(change.REOPEN_STARTUP_REPAIR_ALLOWED)
        historical = (change.task_required, change.cleanup_required, change.recovery_required,
            change.receipt_required, change.schedule_required, change.setup_required, change.bundle_required,
            change.visual_required, change.loading_required, change.streaming_required,
            change.asset_closure_required, change.startup_followup_required, change.levelup_ui_repair_required, runtime_required)
        self.assertTrue(change.reopen_startup_repair_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertTrue(change.reopen_startup_repair_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for function in historical:
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
                for other in ('assets/client-ui-repair-manifest.json', 'android/guest/client_interactive_diagnostic.py',
                        change.JAVA+'ClientRuntime.java', 'upstream/ouroboros/libs/UtilitiesLib/src/utils/utils.c', 'unreviewed.py'):
                    self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[other]))
        checkpoint = ['docs/HANDOFF.md', 'docs/android-evidence/reopen-startup-repair-0.13.13-publication.json']
        for function in historical+(change.reopen_startup_repair_required,):
            with self.subTest(checkpoint=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, checkpoint))
                self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, checkpoint+['docs/unreviewed.md']))

    def test_levelup_ui_repair_disables_every_historical_pipeline_with_no_unknown_file_escape(self):
        from classify_interactive_change import runtime_required
        names = sorted(change.LEVELUP_UI_REPAIR_ALLOWED)
        historical = (change.task_required, change.cleanup_required, change.recovery_required,
            change.receipt_required, change.schedule_required, change.setup_required, change.bundle_required,
            change.visual_required, change.loading_required, change.streaming_required,
            change.asset_closure_required, change.startup_followup_required, runtime_required)
        self.assertTrue(change.levelup_ui_repair_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertTrue(change.levelup_ui_repair_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        for function in historical:
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
                for other in ('android/guest/native_responsiveness_contract.py', 'android/native/client-launcher.c',
                        'assets/client-appearance-manifest.json', 'upstream/ouroboros/DBServer/src/container_sql.c',
                        change.JAVA+'ClientRuntime.java', 'unreviewed.py'):
                    self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[other]))
                for event, before, head, parent in (('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40),
                        ('push', 'c'*40, 'b'*40, 'a'*40), ('push', 'a'*40, 'a'*40, 'a'*40)):
                    self.assertTrue(function(event, before, head, parent, names))

    def test_exact_levelup_publication_checkpoint_skips_all_builds_but_other_docs_are_closed(self):
        from classify_interactive_change import runtime_required
        names = ['docs/HANDOFF.md', 'docs/android-evidence/levelup-ui-repair-0.13.12-publication.json']
        for function in (change.task_required, change.cleanup_required, change.recovery_required,
                change.receipt_required, change.schedule_required, change.setup_required, change.bundle_required,
                change.visual_required, change.loading_required, change.streaming_required,
                change.asset_closure_required, change.startup_followup_required, change.levelup_ui_repair_required,
                runtime_required):
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
                self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+['docs/unreviewed.md']))
        self.assertFalse(change.levelup_ui_repair_docs('push', 'a'*40, 'b'*40, 'a'*40, ['docs/HANDOFF.md']))

    def test_startup_followup_scope_gates_every_historical_publication_and_runtime(self):
        from classify_interactive_change import runtime_required
        names = sorted(change.CLIENT_STARTUP_FOLLOWUP_ALLOWED)
        functions = (change.task_required, change.cleanup_required, change.recovery_required,
            change.receipt_required, change.schedule_required, change.setup_required,
            change.bundle_required, change.visual_required, change.loading_required,
            change.streaming_required, change.asset_closure_required, runtime_required)
        self.assertTrue(change.client_startup_followup_push('push', 'a'*40, 'b'*40, 'a'*40, names))
        for function in functions:
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
                for other in ('assets/client-visual-manifest.json',
                        'tools/android/interactive/build_client_asset_closure_apk.py',
                        change.JAVA+'ClientRuntime.java', 'android/native/client-launcher.c',
                        'upstream/ouroboros/Game/src/render/tex.c', 'unreviewed.py'):
                    self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[other]))
                for event, before, head, parent in (('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40),
                        ('pull_request', 'a'*40, 'b'*40, 'a'*40),
                        ('push', '0'*40, 'b'*40, '0'*40), ('push', 'c'*40, 'b'*40, 'a'*40),
                        ('push', 'a'*40, 'a'*40, 'a'*40)):
                    self.assertTrue(function(event, before, head, parent, names))
        self.assertTrue(change.startup_followup_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertTrue(change.startup_followup_required('workflow_dispatch', None, None, None, []))

    def test_startup_followup_needs_a_reviewed_source_and_explicit_evidence_name(self):
        source = 'tools/android/interactive/build_client_startup_followup_apk.py'
        for names in ([], ['docs/HANDOFF.md'],
                ['docs/android-evidence/client-startup-followup-0.13.11-assets.json'],
                [source, 'docs/android-evidence/client-startup-followup-0.13.11-unreviewed.json']):
            self.assertFalse(change.client_startup_followup_push('push', 'a'*40, 'b'*40, 'a'*40, names))
            self.assertTrue(change.asset_closure_required('push', 'a'*40, 'b'*40, 'a'*40, names))
        self.assertTrue(change.asset_closure_required('push', 'a'*40, 'b'*40, 'a'*40,
            sorted(change.CLIENT_ASSET_CLOSURE_ALLOWED)))

    def test_classifier_emits_the_new_gate_and_disables_asset_closure_for_followup(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)/'outputs'
            environment = {'GITHUB_OUTPUT': str(output), 'GITHUB_EVENT_NAME': 'push', 'COH_PUSH_BEFORE': 'a'*40}
            values = ['a'*40, 'b'*40, b'tools/android/interactive/build_client_startup_followup_apk.py\0']
            with mock.patch.dict(change.os.environ, environment), \
                    mock.patch.object(change.subprocess, 'check_output', side_effect=values), \
                    contextlib.redirect_stdout(io.StringIO()):
                change.main()
            self.assertEqual(output.read_text(), 'task_required=false\ncleanup_required=false\n'
                'recovery_required=false\nreceipt_required=false\nschedule_required=false\n'
                'setup_required=false\nbundle_required=false\nvisual_required=false\n'
                'loading_required=false\nstreaming_required=false\nasset_closure_required=false\n'
                'startup_followup_required=true\nlevelup_ui_repair_required=true\nreopen_startup_repair_required=true\nui_beacon_required=true\n')

    def test_asset_closure_scope_retains_all_old_publications_and_rejects_native_startup_changes(self):
        from classify_interactive_change import runtime_required
        names = sorted(change.CLIENT_ASSET_CLOSURE_ALLOWED)
        functions = (change.task_required, change.cleanup_required, change.recovery_required,
            change.receipt_required, change.schedule_required, change.setup_required,
            change.bundle_required, change.visual_required, change.loading_required, change.streaming_required,
            runtime_required)
        for function in functions:
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
                for other in ('android/guest/texture_header_index.py', 'android/guest/client_interactive_diagnostic.py',
                        change.JAVA+'ClientRuntime.java', 'android/guest/native_responsiveness_contract.py',
                        'upstream/ouroboros/Game/src/render/tex.c', 'unreviewed.py'):
                    self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[other]))
                for event, before, head, parent in (('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40),
                        ('push', '0'*40, 'b'*40, '0'*40), ('push', 'c'*40, 'b'*40, 'a'*40)):
                    self.assertTrue(function(event, before, head, parent, names))

    def test_completed_streaming_workflow_is_gated_away_from_next_asset_closure(self):
        root = Path(__file__).resolve().parents[3]
        text = (root/'.github/workflows/android-client-streaming.yml').read_text()
        self.assertIn('streaming_required: ${{ steps.scope.outputs.streaming_required }}', text)
        self.assertEqual(text.count("needs.changes.outputs.streaming_required != 'false'"), 2)
        self.assertIn('needs: [changes, qualify]', text)

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
        allowed = change.RENDER_QUEUE_ALLOWED if change.render_queue_owned('push','a'*40,'b'*40,'a'*40,names) else change.SETUP_COPY_ALLOWED if change.setup_copy_owned('push','a'*40,'b'*40,'a'*40,names) else change.SESSION_REPAIR_ALLOWED if change.session_repair_owned('push', 'a'*40, 'b'*40, 'a'*40, names) else change.RENDER_PIPELINE_ALLOWED if change.render_pipeline_owned('push', 'a'*40, 'b'*40, 'a'*40, names) else change.GPU_PROFILE_ALLOWED if change.gpu_profile_push('push', 'a'*40, 'b'*40, 'a'*40, names) or change.gpu_profile_docs('push', 'a'*40, 'b'*40, 'a'*40, names) else change.RENDERER_ATTRIBUTION_ALLOWED if change.renderer_attribution_push('push', 'a'*40, 'b'*40, 'a'*40, names) or change.renderer_attribution_docs('push', 'a'*40, 'b'*40, 'a'*40, names) else change.SIDEBAR_ALLOWED if change.sidebar_docs('push', 'a'*40, 'b'*40, 'a'*40, names) or names & (change.SIDEBAR_SOURCES-{change.JAVA+name for name in ('ClientActivity.java', 'ClientInput.java', 'InteractiveRfbClient.java', 'ClientRuntime.java', 'ClientService.java')}) else change.GAMEPLAY_PERFORMANCE_ALLOWED if change.gameplay_performance_docs('push', 'a'*40, 'b'*40, 'a'*40, names) or names & (change.GAMEPLAY_PERFORMANCE_SOURCES-change.SCENE_PERFORMANCE_ALLOWED) else change.SCENE_PERFORMANCE_ALLOWED if names & change.SCENE_PERFORMANCE_SOURCES else change.PERFORMANCE_ALLOWED if names & change.PERFORMANCE_SOURCES else change.UI_BEACON_ALLOWED if names & (change.UI_BEACON_SOURCES - change.REOPEN_STARTUP_REPAIR_ALLOWED - change.LEVELUP_UI_REPAIR_ALLOWED) else change.REOPEN_STARTUP_REPAIR_ALLOWED if change.reopen_startup_repair_push('push', 'a'*40, 'b'*40, 'a'*40, names) else change.LEVELUP_UI_REPAIR_ALLOWED if change.levelup_ui_repair_docs('push', 'a'*40, 'b'*40, 'a'*40, names) or names & (change.LEVELUP_UI_REPAIR_SOURCES - change.CLIENT_STARTUP_FOLLOWUP_ALLOWED) else change.CLIENT_STARTUP_FOLLOWUP_ALLOWED if names & (change.CLIENT_STARTUP_FOLLOWUP_SOURCES - change.CLIENT_ASSET_CLOSURE_ALLOWED) else change.CLIENT_ASSET_CLOSURE_ALLOWED if names & (change.CLIENT_ASSET_CLOSURE_SOURCES - change.CLIENT_STREAMING_ALLOWED) else change.CLIENT_STREAMING_ALLOWED if names & (change.CLIENT_STREAMING_SOURCES - change.CLIENT_LOADING_ALLOWED) else change.CLIENT_LOADING_ALLOWED if names & (change.CLIENT_LOADING_SOURCES - change.VISUAL_ALLOWED) else change.VISUAL_ALLOWED if names & (change.VISUAL_SOURCES - change.BUNDLE_ALLOWED) else change.BUNDLE_ALLOWED
        self.assertLessEqual(names, allowed, 'Candidate contains an unclassified publication path')
        fixture = 'tools/android/interactive/test_startup_bundle_save.py'
        self.assertIn(fixture, change.BUNDLE_ALLOWED)
        for function in (change.task_required, change.cleanup_required, change.recovery_required, change.receipt_required,
                change.schedule_required, change.setup_required, change.bundle_required, change.visual_required, runtime_required):
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, sorted(names)))

    def test_client_streaming_scope_retains_all_old_releases_and_fails_closed_for_unreviewed_changes(self):
        from classify_interactive_change import runtime_required
        names = sorted(change.CLIENT_STREAMING_ALLOWED)
        functions = (change.task_required, change.cleanup_required, change.recovery_required,
            change.receipt_required, change.schedule_required, change.setup_required,
            change.bundle_required, change.visual_required, change.loading_required, runtime_required)
        for function in functions:
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
                for other in ('android/guest/local_character_server.py', change.JAVA+'ClientRuntime.java',
                        'android/guest/native_responsiveness_contract.py', 'android/native/client-launcher.c',
                        'upstream/ouroboros/Game/src/render/tex.c', 'unreviewed.py'):
                    self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[other]))
                for event, before, head, parent in (('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40),
                        ('push', '0'*40, 'b'*40, '0'*40), ('push', 'c'*40, 'b'*40, 'a'*40)):
                    self.assertTrue(function(event, before, head, parent, names))

    def test_completed_loading_publication_is_gated_away_from_new_streaming_changes(self):
        root = Path(__file__).resolve().parents[3]
        text = (root/'.github/workflows/android-client-loading.yml').read_text()
        self.assertIn('loading_required: ${{ steps.scope.outputs.loading_required }}', text)
        self.assertEqual(text.count("needs.changes.outputs.loading_required != 'false'"), 3)
        self.assertIn('COH_PUSH_BEFORE: ${{ github.event.before }}', text)

    def test_client_loading_scope_disables_all_previous_publication_and_runtime_gates(self):
        from classify_interactive_change import runtime_required
        names = sorted(change.CLIENT_LOADING_ALLOWED)
        functions = (change.task_required, change.cleanup_required, change.recovery_required,
            change.receipt_required, change.schedule_required, change.setup_required,
            change.bundle_required, change.visual_required, runtime_required)
        for function in functions:
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push', 'a'*40, 'b'*40, 'a'*40, names))
                for other in ('android/guest/local_character_server.py', change.JAVA+'SetupMemoryGuard.java',
                        'android/native/client-launcher.c', 'unreviewed.py'):
                    self.assertTrue(function('push', 'a'*40, 'b'*40, 'a'*40, names+[other]))
                for event, before, head, parent in (('workflow_dispatch', 'a'*40, 'b'*40, 'a'*40),
                        ('push', '0'*40, 'b'*40, '0'*40), ('push', 'c'*40, 'b'*40, 'a'*40)):
                    self.assertTrue(function(event, before, head, parent, names))

    def test_old_visual_workflow_is_gated_away_from_client_loading_publication(self):
        root = Path(__file__).resolve().parents[3]
        text = (root/'.github/workflows/android-client-visual.yml').read_text()
        self.assertIn('visual_required: ${{ steps.scope.outputs.visual_required }}', text)
        self.assertIn("needs.changes.outputs.visual_required != 'false'", text)
        self.assertIn('COH_PUSH_BEFORE: ${{ github.event.before }}', text)

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
                'recovery_required=false\nreceipt_required=false\nschedule_required=true\nsetup_required=true\nbundle_required=true\nvisual_required=true\nloading_required=true\nstreaming_required=true\nasset_closure_required=true\nstartup_followup_required=true\nlevelup_ui_repair_required=true\nreopen_startup_repair_required=true\nui_beacon_required=true\n')
            output.unlink()
            with mock.patch.dict(change.os.environ, environment), \
                    mock.patch.object(change.subprocess, 'check_output', side_effect=OSError('no history')), \
                    contextlib.redirect_stdout(io.StringIO()):
                change.main()
            self.assertEqual(output.read_text(), 'task_required=true\ncleanup_required=true\n'
                'recovery_required=true\nreceipt_required=true\nschedule_required=true\nsetup_required=true\nbundle_required=true\nvisual_required=true\nloading_required=true\nstreaming_required=true\nasset_closure_required=true\nstartup_followup_required=true\nlevelup_ui_repair_required=true\nreopen_startup_repair_required=true\nui_beacon_required=true\n')

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
                'recovery_required=false\nreceipt_required=false\nschedule_required=false\nsetup_required=false\nbundle_required=true\nvisual_required=true\nloading_required=true\nstreaming_required=true\nasset_closure_required=true\nstartup_followup_required=true\nlevelup_ui_repair_required=true\nreopen_startup_repair_required=true\nui_beacon_required=true\n')

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
            ('push','a'*40,'b'*40,'a'*40,[change.JAVA+'ClientSessionBudget.java']),
            ('push','a'*40,'b'*40,'a'*40,['docs/HANDOFF.md'])):
            self.assertTrue(change.task_required(event,before,head,parent,names))
