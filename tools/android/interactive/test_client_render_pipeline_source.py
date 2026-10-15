"""Bind focused observations and the worker handshake to exact staged ancestry."""
from __future__ import annotations
from functools import lru_cache
from itertools import combinations
from pathlib import Path
import hashlib
import re
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools')]
from prepare_resume_client_source import apply_patch
from package_client_loading_native import function, reverse_patch

FILES = ('Game/src/graphics/gfx.c', 'Game/src/render/thread/rt_queue.c',
    'Game/src/render/thread/rt_queue.h', 'libs/UtilitiesLib/src/components/WorkerThread.c')
PATCH = 'patches/client-render-pipeline/0001-render-worker-wake-and-focused-timing.patch'
OLD_WAKE = '''                ResetEvent(wt->data_queued);
                cmd = peekStoredCmd(&wt->cmd_queue);
                if (!cmd) {
                    wt->thread_asleep = 1;
                    WaitForSingleObject(wt->data_queued, INFINITE);
                    wt->thread_asleep = 0;
                }
'''
NEW_WAKE = '''                /* Arm the producer's wake handshake before resetting and
                 * checking the queue. A publication before ResetEvent is seen
                 * by the recheck; one after the recheck signals an armed event.
                 * Win32/x86 volatile publication and event ordering are retained. */
                wt->thread_asleep = 1;
                ResetEvent(wt->data_queued);
                cmd = peekStoredCmd(&wt->cmd_queue);
                if (!cmd) {
                    WaitForSingleObject(wt->data_queued, INFINITE);
                }
                wt->thread_asleep = 0;
'''
GLUE = '''#define COH_RP_IMPLEMENTATION
#include "cohClientRenderPipeline.h"

/* The queue header is also included before Windows initialization headers.
 * Keep these external adapters free of Win32/CRT headers at its callsites. */
void cohRpQueueFlushBegin(void) { cohRpPhaseBegin(COH_RP_FLUSH); }
void cohRpQueueFlushEnd(void) { cohRpPhaseEnd(COH_RP_FLUSH); }
'''


def wake_sources():
    original = (ROOT/'upstream/ouroboros'/FILES[3]).read_bytes().replace(b'\r\n', b'\n')
    patch = (ROOT/PATCH).read_bytes().replace(b'\r\n', b'\n')
    wake = patch[patch.index(('--- a/'+FILES[3]+'\n').encode()):]
    with tempfile.TemporaryDirectory(prefix='coh-worker-wake-') as temporary:
        source = Path(temporary)
        path = source/FILES[3]
        path.parent.mkdir(parents=True)
        path.write_bytes(original)
        apply_patch(source, wake)
        current = path.read_bytes()
        reverse_patch(source, wake)
        if path.read_bytes() != original:
            raise ValueError('Worker wake reverse proof did not reproduce the accepted source')
    return original.decode(), current.decode()


def interleaving_proof(order, spurious=False):
    """Enumerate every ordered consumer/publisher schedule, including notify late.

    Win32 events are remembered until ResetEvent/Wait; volatile command
    publication is visible to the final queue recheck. The two producer steps
    remain exactly publish-then-notify. The test explicitly treats notifications
    occurring after the wait begins as successful wakes.
    """
    failures = []
    for positions in combinations(range(6), 2):
        producer = iter(('publish', 'notify'))
        consumer = iter(order)
        schedule = [next(producer) if i in positions else next(consumer) for i in range(6)]
        queued = asleep = waiting = False
        event = spurious
        should_wait = None
        for step in schedule:
            if step == 'arm':
                asleep = True
            elif step == 'reset':
                event = False
            elif step == 'peek':
                should_wait = not queued
            elif step == 'wait':
                if should_wait:
                    waiting = not event
                    event = False
                else:
                    asleep = False
            elif step == 'publish':
                queued = True
            elif step == 'notify' and asleep:
                event = True
                waiting = False
        if waiting:
            failures.append(schedule)
    return failures


def wake_proof():
    original, current = wake_sources()
    if original.count(OLD_WAKE) != 1 or current.count(NEW_WAKE) != 1 or current.replace(NEW_WAKE, OLD_WAKE) != original:
        raise ValueError('Worker wake repair changed behavior beyond the exact wait handshake')
    for signature in ('void wtSendCmd(', 'static INLINEDBG void *allocStoredCmd(',
            'void wtSetThreaded(', 'static INLINEDBG void wtReqFlush('):
        if function(original, signature) != function(current, signature):
            raise ValueError('Unthreaded, full-queue, debug or shutdown producer policy changed')
    old = interleaving_proof(('reset', 'peek', 'arm', 'wait'))
    new = interleaving_proof(('arm', 'reset', 'peek', 'wait'))
    if old != [['reset', 'peek', 'publish', 'notify', 'arm', 'wait']] or new:
        raise ValueError('Exhaustive worker wake schedules did not expose the old loss and repair all schedules')
    if interleaving_proof(('arm', 'reset', 'peek', 'wait'), spurious=True):
        raise ValueError('Spurious event state reintroduced a lost worker wake')
    return {'schedules_per_policy': 15, 'old_lost_wakes': 1, 'repaired_lost_wakes': 0,
        'spurious_signal_schedules': 15, 'producer_and_full_queue_and_unthreaded_unchanged': True,
        'volatile_win32_x86_publication_assumption': True}


@lru_cache(maxsize=1)
def sources():
    import package_client_render_pipeline_native as producer
    if producer.FILES != FILES:
        raise ValueError('Render pipeline source inventory differs')
    with tempfile.TemporaryDirectory(prefix='coh-pipeline-source-') as temporary:
        source = Path(temporary)/'accepted'
        producer.base.stage(SimpleNamespace(output=source))
        producer.base.validate_source(source)
        original = {name: (source/name).read_bytes().decode() for name in FILES}
        apply_patch(source, (ROOT/PATCH).read_bytes().replace(b'\r\n', b'\n'))
        current = {name: (source/name).read_bytes().decode() for name in FILES}
        reverse_patch(source, (ROOT/PATCH).read_bytes().replace(b'\r\n', b'\n'))
        if any((source/name).read_bytes() != text.encode() for name, text in original.items()):
            raise ValueError('Render pipeline reverse proof did not reproduce exact accepted sources')
    return original, current


def strip_hooks(text):
    text = text.replace(GLUE, '')
    text = text.replace('    int coh_rp_gameplay_frame = !force_render_world && !headShot && !no_drawing &&\n        game_state.game_mode == SHOW_GAME && !shellMode() && !loadingScreenVisible();\n', '')
    text = text.replace('#include "cohClientRenderPipeline.h"\n', '')
    text = re.sub(r'^[ \t]*cohRp(?:MainBegin|MainEnd|PhaseBegin|PhaseEnd|CommandBegin|CommandEnd)\([^\n]*\);\n', '', text, flags=re.M)
    text = text.replace('    if (type == DRAWCMD_INITTOPOFFRAME) cohRpRendererBegin();\n', '')
    text = text.replace('    if (type == DRAWCMD_SWAPBUFFER) cohRpRendererEnd();\n', '')
    text = text.replace('void cohRpQueueFlushBegin(void);\nvoid cohRpQueueFlushEnd(void);\n', '')
    text = text.replace('cohRpQueueFlushBegin(); ', '').replace(' cohRpQueueFlushEnd();', '')
    return text.replace(NEW_WAKE, OLD_WAKE)


def source_proof():
    import package_client_render_pipeline_native as producer
    original, current = sources()
    expected = producer.expected_receipt()
    for field, values in (('source_sha256', original), ('patched_sha256', current)):
        if {name: hashlib.sha256(text.encode()).hexdigest() for name, text in values.items()} != expected[field]:
            raise ValueError('Render pipeline actual source bytes differ from the package receipt')
    for name in FILES:
        if strip_hooks(current[name]) != original[name]:
            raise ValueError('Render pipeline changed drawing/loading/gameplay beyond timing and wake repair: '+name)
    return wake_proof()


class RenderPipelineSourceTests(unittest.TestCase):
    def test_exact_source_and_reverse_ancestry_and_fidelity(self):
        self.assertTrue(source_proof())

    def test_worker_wake_all_adversarial_interleavings_and_spurious_events(self):
        self.assertEqual(wake_proof()['repaired_lost_wakes'], 0)

    def test_worker_arms_before_reset_and_recheck_and_clears_after_both_paths(self):
        _, current = wake_sources()
        order = ('wt->thread_asleep = 1;', 'ResetEvent(wt->data_queued)',
            'cmd = peekStoredCmd(&wt->cmd_queue)', 'if (!cmd)',
            'WaitForSingleObject(wt->data_queued, INFINITE)', 'wt->thread_asleep = 0;')
        start = current.index(NEW_WAKE)
        positions = [current.index(value, start) for value in order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('if (!cmd) {\n                    WaitForSingleObject(wt->data_queued, INFINITE);\n                }\n                wt->thread_asleep = 0;', current)
        self.assertEqual(function(wake_sources()[0], 'void wtSendCmd('), function(current, 'void wtSendCmd('))

    def test_phase_hooks_bracket_accepted_main_operations_without_changing_commands(self):
        _, current = sources()
        gfx = function(current[FILES[0]], 'void gfxUpdateFrame(')
        for metric, target in (
            ('AUX', 'viewport_RenderAll();'), ('MAINVIEW', 'gfxRenderViewport(&s_mainviewport);'),
            ('SUN', 'sunVisible();'), ('POST', 'rdrPostprocessing(&pbRenderTexture);'),
            ('UI', 'gfxDraw2DStuffPost3D(!no_drawing, headShot);'),
            ('FINISH', 'gfxDrawFinishFrame(!headShot && !no_drawing && !gfx_state.screenshot, headShot, s_mainviewport.renderPass);')):
            order = (f'cohRpPhaseBegin(COH_RP_{metric});', target, f'cohRpPhaseEnd(COH_RP_{metric});')
            positions = [gfx.index(value) for value in order]
            self.assertEqual(positions, sorted(positions), metric)
        self.assertLess(gfx.index('cohRpMainBegin('), gfx.index('rdrInitTopOfFrame();'))
        self.assertGreater(gfx.index('cohRpMainEnd('), gfx.index('cohRpPhaseEnd(COH_RP_FINISH);'))

    def test_main_scope_is_captured_gameplay_and_end_restores_same_invocation(self):
        _, current = sources()
        gfx = function(current[FILES[0]], 'void gfxUpdateFrame(')
        self.assertIn('int coh_rp_gameplay_frame = !force_render_world && !headShot && !no_drawing &&\n        game_state.game_mode == SHOW_GAME && !shellMode() && !loadingScreenVisible();', gfx)
        self.assertIn('cohRpMainBegin(coh_rp_gameplay_frame);', gfx)
        self.assertIn('cohRpMainEnd(coh_rp_gameplay_frame);', gfx)

    def test_dispatcher_active_span_and_batch_boundary_capture_queue_gaps(self):
        original, current = sources()
        callback = function(current[FILES[1]], 'static void cmdDispatchCallback(')
        order = ('if (type == DRAWCMD_INITTOPOFFRAME) cohRpRendererBegin();',
            'cohRpCommandBegin(type);', 'cmdDispatch(unused, (DrawType)type, data);',
            'cohRpCommandEnd(type);', 'if (type == DRAWCMD_SWAPBUFFER) cohRpRendererEnd();')
        positions = [callback.index(value) for value in order]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(strip_hooks(callback), function(original[FILES[1]], 'static void cmdDispatchCallback('))
        self.assertEqual(function(original[FILES[1]], 'static void cmdDispatch('), function(current[FILES[1]], 'static void cmdDispatch('))

    def test_flush_observation_preserves_wtFlush_and_safe_header_include_order(self):
        original, current = sources()
        queue = current[FILES[2]]
        self.assertNotIn('cohClientRenderPipeline.h', queue)
        self.assertNotIn('windows.h', queue)
        self.assertEqual(strip_hooks(queue), original[FILES[2]])
        self.assertIn('cohRpQueueFlushBegin(); wtFlush(render_thread); cohRpQueueFlushEnd();', queue)
        self.assertLess(current[FILES[0]].index('#include "win/win_init.h"'), current[FILES[0]].index(GLUE))
        self.assertLess(current[FILES[1]].index('#include "win/win_init.h"'), current[FILES[1]].index('#include "cohClientRenderPipeline.h"'))


if __name__ == '__main__':
    unittest.main()
