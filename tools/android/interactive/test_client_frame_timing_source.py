"""Prove frame hooks retain every native operation and compose after scene patch."""
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT / 'tools')]
import package_client_loading_native as loading
import test_client_scene_performance_native as scene
import test_client_frame_timing_native as frame
from prepare_resume_client_source import apply_patch

FILES = ('Game/src/game.c', 'Game/src/render/thread/rt_win_init.c')


def sources(after_scene=False):
    original = {name: (ROOT / 'upstream/ouroboros' / name).read_bytes().replace(b'\r\n', b'\n').decode('utf-8')
                for name in FILES}
    if after_scene:
        original['Game/src/game.c'] = scene.sources()[1]['Game/src/game.c']
    with tempfile.TemporaryDirectory(prefix='coh-frame-source-') as directory:
        source = Path(directory)
        for name, value in original.items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value.encode('utf-8'))
        patch = (ROOT / frame.PATCH).read_bytes().replace(b'\r\n', b'\n')
        names = tuple(line[6:] for line in patch.decode().splitlines() if line.startswith('+++ b/'))
        if names != FILES:
            raise ValueError('Frame patch changes an unexpected native source')
        try:
            apply_patch(source, patch)
        except subprocess.CalledProcessError as error:
            raise RuntimeError('Frame fixture patch failed: ' +
                (error.stderr or b'').decode('utf-8', errors='replace')) from error
        current = {name: (source / name).read_bytes().decode('utf-8') for name in FILES}
        loading.reverse_patch(source, patch)
        if any((source / name).read_bytes() != value.encode('utf-8') for name, value in original.items()):
            raise ValueError('Frame reverse proof did not reproduce the complete input')
        return original, current


def strip_hooks(text):
    text = text.replace('#include "cohClientFrameTiming.h"\n', '')
    for name in ('Begin', 'End'):
        text = text.replace('        if (cohFtActive(0))\n'
            '            cohFtMain' + name + '(loadingScreenVisible() ? COH_FT_LOADING :\n'
            '                (isMenu(MENU_GAME) ? COH_FT_GAMEPLAY : COH_FT_MENU));\n', '')
    # These blank lines belong to the inserted hook, not to the native function.
    text = text.replace('        cohFtPhaseEnd(COH_FT_PACING_PHASE);\n\n', '')
    text = text.replace('\n    cohFtPresentBegin();\n', '')
    return re.sub(r'^[ \t]*cohFt(?:PhaseBegin|PhaseEnd|SwapBegin|SwapEnd|PresentEnd)\([^\n]*\);\n',
        '', text, flags=re.M)


class FrameSourceTests(unittest.TestCase):
    def test_scene_and_frame_fixtures_keep_exact_bytes_under_windows_text_translation(self):
        ordinary_write = Path.write_text
        def windows_write(path, text, *args, **kwargs):
            kwargs.setdefault('newline', '\r\n')
            return ordinary_write(path, text, *args, **kwargs)
        # Reproduce Windows's native text mode even when the host is Linux.
        # Scene and frame apply/reverse proofs must survive without text-mode
        # reads silently normalizing a different physical byte stream.
        with mock.patch.object(Path, 'write_text', windows_write):
            self.assertTrue(scene.source_proof())
            for after_scene in (False, True):
                old, current = sources(after_scene)
                for name in FILES:
                    self.assertEqual(strip_hooks(current[name]), old[name])

    def test_complete_sources_keep_native_behavior_with_and_without_scene_layer(self):
        for after_scene in (False, True):
            old, current = sources(after_scene)
            for name in FILES:
                with self.subTest(after_scene=after_scene, name=name):
                    self.assertEqual(strip_hooks(current[name]), old[name])

    def test_actual_pacing_submit_swap_and_main_boundaries_are_correctly_nested(self):
        _, current = sources(after_scene=True)
        engine = loading.function(current[FILES[0]], 'void engine_update(')
        order = ('cohFtPhaseBegin(COH_FT_SUBMIT_PHASE)', 'gfxUpdateFrame(0, 0, 0)',
                 'cohFtPhaseEnd(COH_FT_SUBMIT_PHASE)', 'cohFtPhaseBegin(COH_FT_PACING_PHASE)',
                 'waitFps( game_state.maxfps)', 'cohFtPhaseEnd(COH_FT_PACING_PHASE)', 'doMapXfer()')
        self.assertEqual([engine.index(value) for value in order], sorted(engine.index(value) for value in order))
        main = loading.function(current[FILES[0]], 'int game_mainLoop(')
        order = ('autoTimerTickBegin()', 'cohFtMainBegin(', 'cohFtPhaseBegin(COH_FT_ENGINE_PHASE)',
                 'engine_update()', 'cohFtPhaseEnd(COH_FT_ENGINE_PHASE)', 'LWC_Tick()',
                 'cohFtMainEnd(', 'endProfilingCPU()', 'autoTimerTickEnd();')
        positions = [main.index(value) for value in order]
        self.assertEqual(positions, sorted(positions))
        presentation = loading.function(current[FILES[1]], 'void windowUpdateDirect(')
        order = ('cohFtPresentBegin()', 'cohFtSwapBegin()', 'SwapBuffers(hDC)', 'cohFtSwapEnd()',
                 'InterlockedDecrement(&frames_buffered)', 'SetEvent(frame_done_signal)', 'cohFtPresentEnd()')
        positions = [presentation.index(value) for value in order]
        self.assertEqual(positions, sorted(positions))
        # No new render synchronization, heap allocation, sleep, or GPU query.
        patch = (ROOT / frame.PATCH).read_text()
        added = '\n'.join(line[1:] for line in patch.splitlines() if line.startswith('+') and not line.startswith('+++'))
        self.assertNotRegex(added, r'\b(?:Sleep|WaitFor|malloc|calloc|realloc|glFinish|glFlush|glGetQuery)\b')

    def test_recipe_binds_source_implementation_and_records_measurement_limits(self):
        expected = frame.expected_receipt()
        self.assertEqual(expected['header_sha256'], frame.digest(ROOT / frame.HEADER))
        self.assertEqual(expected['harness_sha256'], hashlib.sha256(frame.harness().encode()).hexdigest())
        self.assertFalse(expected['physical_frame_rate_or_gpu_latency_validated'])
        self.assertTrue(expected['disabled_without_clock_cpu_or_logging_verified'])
        header = (ROOT / frame.HEADER).read_text()
        self.assertIn('strcmp(flag,"1")==0', header)
        self.assertIn('#define COH_FT_MAX_REPORTS 120u', header)
        self.assertIn('#define COH_FT_REPORT_MS 10000.0', header)
        self.assertIn('static COH_FT_TLS CohFtStream coh_ft_stream;', header)
        self.assertIn('printf("%s\\n", line); fflush(stdout);', header)
        self.assertNotRegex(header, r'\b(?:malloc|calloc|realloc|Sleep|glFlush|glFinish)\s*\(')


if __name__ == '__main__':
    unittest.main()
