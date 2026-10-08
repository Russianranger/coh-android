"""Prove renderer observations preserve the complete accepted native sources."""
from pathlib import Path
import hashlib
import re
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools')]
import package_client_renderer_attribution_native as producer
import package_client_loading_native as loading
from prepare_resume_client_source import apply_patch

FILES = ('Game/src/graphics/gfx.c', 'Game/src/win/win_init.c',
    'Game/src/render/thread/rt_queue.c', 'Game/src/render/thread/rt_win_init.c')
FPS_ORIGINAL = ('           xyprintf(38 + TEXT_JUSTIFY,line++,"% 2.2f (%0.1fm/fm)", '
    'game_state.fps, 1000.f/game_state.fps);\n')
FPS_REPLACEMENT = ('           xyprintf(COH_RA_FPS_COLUMN,COH_RA_FPS_ROW,'
    '"FPS %.2f | %.1f ms/frame", game_state.fps, 1000.f/game_state.fps);\n'
    '           line++;\n')
HOOKS = (
    'cohRaMainBegin(!force_render_world && !headShot && !no_drawing, '
        'game_state.allow_frames_buffered, rdrIsThreaded(), game_state.sliLimit, '
        'game_state.frame_delay, game_state.maxfps, game_state.showfps);',
    'cohRaMainEnd(!force_render_world && !headShot && !no_drawing);', 'cohRaWaitIteration();',
    'cohRaRendererBegin();', 'cohRaRendererEnd();',
    *(f'cohRaPhase{boundary}(COH_RA_{metric});'
        for metric in ('WAIT', 'SWAP', 'TEXCOPY', 'TEXSUBCOPY', 'VBO', 'READBACK')
        for boundary in ('Begin', 'End')))
HOOK_COUNTS = {
    FILES[0]: {HOOKS[0]: 1, HOOKS[1]: 1},
    FILES[1]: {'cohRaWaitIteration();': 1,
        'cohRaPhaseBegin(COH_RA_WAIT);': 1, 'cohRaPhaseEnd(COH_RA_WAIT);': 1},
    FILES[2]: {'cohRaRendererBegin();': 1, 'cohRaRendererEnd();': 1,
        **{f'cohRaPhase{boundary}(COH_RA_{metric});': count
            for metric, count in (('TEXCOPY', 1), ('TEXSUBCOPY', 1), ('VBO', 1), ('READBACK', 2))
            for boundary in ('Begin', 'End')}},
    FILES[3]: {'cohRaPhaseBegin(COH_RA_SWAP);': 1, 'cohRaPhaseEnd(COH_RA_SWAP);': 1}}


def sources():
    """Rebuild the accepted gameplay parent independently, apply and reverse."""
    if producer.FILES != FILES:
        raise ValueError('Renderer attribution changes an unexpected native file inventory')
    with tempfile.TemporaryDirectory(prefix='coh-renderer-source-') as temporary:
        source = Path(temporary)/'accepted'
        producer.base.stage(SimpleNamespace(output=source))
        producer.base.validate_source(source)
        original = {name: (source/name).read_bytes().decode('utf-8') for name in FILES}
        touched = []
        for name in producer.PATCHES:
            patch, paths = producer.normalized_patch(name)
            touched.extend(paths)
            apply_patch(source, patch)
        if tuple(touched) != FILES:
            raise ValueError('Renderer patch changes an unexpected native file inventory')
        current = {name: (source/name).read_bytes().decode('utf-8') for name in FILES}
        for name in reversed(producer.PATCHES):
            loading.reverse_patch(source, producer.normalized_patch(name)[0])
        if any((source/name).read_bytes() != text.encode('utf-8') for name, text in original.items()):
            raise ValueError('Renderer reverse proof did not reproduce the complete accepted source')
    return original, current


def strip_hooks(text):
    text = text.replace('#define COH_RA_IMPLEMENTATION\n', '')
    text = text.replace('#include "cohClientRendererAttribution.h"\n', '')
    for hook in HOOKS:
        text = re.sub(r'^[ \t]*'+re.escape(hook)+r'\n', '', text, flags=re.M)
    return text.replace(FPS_REPLACEMENT, FPS_ORIGINAL)


def source_proof():
    original, current = sources()
    expected = producer.expected_receipt()
    for field, values in (('source_sha256', original), ('patched_sha256', current)):
        hashes = {name: hashlib.sha256(text.encode('utf-8')).hexdigest()
            for name, text in values.items()}
        if hashes != expected[field]:
            raise ValueError('Renderer fixture differs from the actual staged native ancestry')
    for name in FILES:
        if current[name].count('#include "cohClientRendererAttribution.h"\n') != 1:
            raise ValueError('Renderer header include differs: '+name)
        if current[name].count('#define COH_RA_IMPLEMENTATION\n') != int(name == FILES[0]):
            raise ValueError('Renderer shared TLS definition inventory differs: '+name)
        for hook in HOOKS:
            if current[name].count(hook) != HOOK_COUNTS[name].get(hook, 0):
                raise ValueError('Renderer diagnostic hook count differs: '+name+' '+hook)
        if strip_hooks(current[name]) != original[name]:
            raise ValueError('Renderer layer changes accepted native behavior outside its exact hooks: '+name)
    return True


def command_case(dispatch, command):
    begin = dispatch.index('xcase '+command+':')
    match = re.search(r'\n\s*x(?:case|default)\b', dispatch[begin+1:])
    return dispatch[begin:begin+1+match.start()] if match else dispatch[begin:]


class RendererSourceTests(unittest.TestCase):
    def test_complete_accepted_sources_remain_exact_except_observations_and_fps_placement(self):
        self.assertTrue(source_proof())

    def test_windows_text_translation_cannot_change_apply_reverse_proofs(self):
        ordinary = Path.write_text
        def translated(path, text, *args, **kwargs):
            kwargs.setdefault('newline', '\r\n')
            return ordinary(path, text, *args, **kwargs)
        with mock.patch.object(Path, 'write_text', translated):
            self.assertTrue(source_proof())

    def test_backpressure_brackets_existing_wait_and_keeps_queue_policy(self):
        original, current = sources()
        wait = loading.function(current[FILES[1]], 'void windowUpdate(')
        order = ('cohRaPhaseBegin(COH_RA_WAIT)',
            'while(frames_buffered > game_state.allow_frames_buffered)',
            'rdrQueueMonitor()', 'cohRaWaitIteration()',
            'WaitForSingleObject( frame_done_signal, 10 )',
            'if (!first && frames_buffered)', 'Sleep(1)',
            'cohRaPhaseEnd(COH_RA_WAIT)', 'InterlockedIncrement(&frames_buffered)',
            'rdrQueueCmd(DRAWCMD_SWAPBUFFER)')
        positions = [wait.index(value) for value in order]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(strip_hooks(wait), loading.function(original[FILES[1]], 'void windowUpdate('))

    def test_render_batch_upload_readback_and_swap_hooks_bracket_actual_native_operations(self):
        _, current = sources()
        graphics = loading.function(current[FILES[0]], 'void gfxUpdateFrame(')
        order = ('cohRaMainBegin(', 'rdrBeginMarker(__FUNCTION__)',
            'rdrInitTopOfFrame()',
            'gfxDrawFinishFrame(!headShot && !no_drawing && !gfx_state.screenshot, headShot, s_mainviewport.renderPass)',
            'cohRaMainEnd(!force_render_world && !headShot && !no_drawing)')
        positions = [graphics.index(value) for value in order]
        self.assertEqual(positions, sorted(positions))
        self.assertLess(graphics.rindex('rdrEndMarker()'), graphics.index('cohRaMainEnd('))
        dispatch = loading.function(current[FILES[2]], 'static void cmdDispatch(')
        first = command_case(dispatch, 'DRAWCMD_INITTOPOFFRAME')
        self.assertLess(first.index('cohRaRendererBegin()'), first.index('rdrInitTopOfFrameDirect(data)'))
        last = command_case(dispatch, 'DRAWCMD_SWAPBUFFER')
        order = ('wtSetFlushRequested(render_thread, 0)', 'windowUpdateDirect()', 'cohRaRendererEnd()')
        positions = [last.index(value) for value in order]
        self.assertEqual(positions, sorted(positions))
        for command, metric, call in (
            ('DRAWCMD_TEXCOPY', 'TEXCOPY', 'texCopyDirect(data)'),
            ('DRAWCMD_TEXSUBCOPY', 'TEXSUBCOPY', 'texSubCopyDirect(data)'),
            ('DRAWCMD_CREATEVBO', 'VBO', 'createVboDirect(data)'),
            ('DRAWCMD_GETFRAMEBUFFER', 'READBACK', 'rdrGetFrameBufferDirect(data)'),
            ('DRAWCMD_FRAMEGRAB', 'READBACK', 'rdrFrameGrabDirect(data)')):
            case = command_case(dispatch, command)
            with self.subTest(command=command):
                order = ('cohRaPhaseBegin(COH_RA_'+metric+')', call,
                    'cohRaPhaseEnd(COH_RA_'+metric+')')
                positions = [case.index(value) for value in order]
                self.assertEqual(positions, sorted(positions))
                self.assertEqual(case.count(call), 1)
        presentation = loading.function(current[FILES[3]], 'void windowUpdateDirect(')
        order = ('cohFtSwapBegin()', 'cohRaPhaseBegin(COH_RA_SWAP)', 'SwapBuffers(hDC)',
            'cohRaPhaseEnd(COH_RA_SWAP)', 'cohFtSwapEnd()',
            'InterlockedDecrement(&frames_buffered)', 'SetEvent(frame_done_signal)', 'cohFtPresentEnd()')
        positions = [presentation.index(value) for value in order]
        self.assertEqual(positions, sorted(positions))

    def test_fps_sampling_timestep_and_existing_line_state_are_preserved(self):
        original, current = sources()
        old = loading.function(original[FILES[0]], 'void showFrameRate(')
        new = loading.function(current[FILES[0]], 'void showFrameRate(')
        self.assertEqual(new.count(FPS_REPLACEMENT), 1)
        self.assertEqual(new.replace(FPS_REPLACEMENT, FPS_ORIGINAL), old)
        self.assertEqual(loading.function(original[FILES[0]], 'void    waitFps('),
            loading.function(current[FILES[0]], 'void    waitFps('))

    def test_receipt_binds_exact_gameplay_parent_and_retains_native_policy(self):
        document = producer.expected_receipt()
        self.assertEqual(document['base_client_gameplay_performance_build_input'], producer.base.expected_receipt())
        self.assertEqual(set(document['source_sha256']), set(FILES))
        self.assertEqual(set(document['patched_sha256']), set(FILES))
        self.assertEqual(set(document['overlay_sha256']), {'Game/src/cohClientRendererAttribution.h'})
        self.assertTrue(document['reverse_patch_exact_base_verified'])
        self.assertTrue(document['native_fps_display_changed'])
        for name in ('cache_encoding_changed', 'parse6_schema_changes', 'source_freshness_changed',
            'graphics_profile_changes', 'renderer_changed', 'gameplay_validation_changes',
            'gameplay_frame_cap_changed', 'runtime_execution_validated'):
            with self.subTest(field=name):
                self.assertIs(document[name], False)
        self.assertEqual(document['build_targets'], ['Game'])
        controls = document['controls']['renderer_attribution']
        self.assertTrue(controls['queue_pacing_rendering_loading_unchanged'])
        self.assertTrue(controls['worker_configuration_unchanged'])

    def test_staged_source_rejects_changed_prior_headers_hooks_and_cache_schema(self):
        with tempfile.TemporaryDirectory(prefix='coh-renderer-stage-proof-') as temporary:
            source = Path(temporary)/'source'
            producer.stage(SimpleNamespace(output=source))
            self.assertEqual(producer.validate_source(source)[0], producer.expected_receipt())
            targets = (*FILES, 'Game/src/cohClientSceneTiming.h', 'Game/src/cohClientFrameTiming.h',
                'Game/src/cohClientGameplayPerformance.h', 'Game/src/cohClientRendererAttribution.h',
                'Game/src/entity/entclient.c', next(iter(producer.baseline.schema_pins())))
            for name in targets:
                path = source/name
                original = path.read_bytes()
                path.write_bytes(original+b'\n/* unexpected native change */\n')
                try:
                    with self.subTest(name=name), self.assertRaises(ValueError):
                        producer.validate_source(source)
                finally:
                    path.write_bytes(original)

    def test_shared_tls_header_is_bounded_opt_in_and_has_no_native_policy_operations(self):
        header = (ROOT/next(iter(producer.OVERLAYS.values()))).read_text()
        self.assertIn('#define COH_RA_MAX_REPORTS 120u', header)
        self.assertIn('#define COH_RA_MAX_STATE_REPORTS 64u', header)
        self.assertIn('#define COH_RA_REPORT_MS 10000.0', header)
        self.assertIn('strcmp(flag,"1")==0', header)
        self.assertIn('extern COH_RA_TLS CohRaStream coh_ra_stream;', header)
        self.assertIn('\nCOH_RA_TLS CohRaStream coh_ra_stream;', header)
        self.assertIn('#define COH_RA_FPS_COLUMN 1', header)
        self.assertIn('#define COH_RA_FPS_ROW 14', header)
        self.assertNotRegex(header, r'\b(?:malloc|calloc|realloc|Sleep|WaitFor\w*|waitFps|'
            r'glFinish|glFlush|glGetQuery\w*|texLoad\w*|rdrQueue\w*)\s*\(')
        patch = b'\n'.join(producer.normalized_patch(name)[0] for name in producer.PATCHES).decode()
        added = '\n'.join(line[1:] for line in patch.splitlines()
            if line.startswith('+') and not line.startswith('+++'))
        self.assertEqual(added.count('#define COH_RA_IMPLEMENTATION'), 1)
        self.assertNotRegex(added, r'\b(?:Sleep|WaitFor\w*|malloc|calloc|realloc|'
            r'glFinish|glFlush|glGetQuery\w*|rdrQueue\w*|wtSet\w*|texLoad\w*)\s*\(')


if __name__ == '__main__':
    unittest.main()
