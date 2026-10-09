"""Bind queue coalescing and sparse observations to the retained native ancestry."""
from __future__ import annotations
from collections import deque
from functools import lru_cache
import hashlib
from pathlib import Path
import re
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools')]
from prepare_resume_client_source import apply_patch
from package_client_loading_native import function, reverse_patch
FILES = ('Game/src/graphics/gfx.c', 'Game/src/render/thread/rt_queue.c',
    'libs/UtilitiesLib/src/components/WorkerThread.c',
    'libs/UtilitiesLib/include/utilitieslib/components/WorkerThread.h')
PATCH = 'patches/client-render-queue/0001-coalesce-render-worker-wake-and-sparse-queue-timing.patch'
WORKER, WORKER_HEADER = FILES[2:]


@lru_cache(maxsize=1)
def sources():
    import package_client_render_queue_native as producer
    if producer.FILES != FILES: raise ValueError('Render queue source inventory differs')
    with tempfile.TemporaryDirectory(prefix='coh-render-queue-source-') as temporary:
        source = Path(temporary)/'parent'
        producer.base.stage(SimpleNamespace(output=source))
        producer.base.validate_source(source)
        original = {name: (source/name).read_bytes().replace(b'\r\n', b'\n').decode() for name in FILES}
        for name, text in original.items(): (source/name).write_bytes(text.encode())
        patch = (ROOT/PATCH).read_bytes().replace(b'\r\n', b'\n')
        apply_patch(source, patch)
        current = {name: (source/name).read_text() for name in FILES}
        reverse_patch(source, patch)
        if any((source/name).read_bytes() != text.encode() for name, text in original.items()):
            raise ValueError('Render queue reverse patch did not reproduce the complete retained source')
    return original, current


def wake_model(commands=2, spurious=False, post_reset_rearm=True):
    """Explore complete single-producer/two-cycle schedules with atomic claims.

    Publish/load/CAS/signal are distinct producer steps. Consumer empty check,
    arm/reset/recheck/wait/clear are distinct steps; signals may land after a
    rearm or while waiting. Queue work is conserved until dispatch consumes it.
    """
    initial = (0, 0, 0, 0, bool(spurious), 0, 0, 0)  # queue, producer, consumer, state, event, read, claim, consumed
    pending, visited, failures = deque([initial]), {initial}, []
    transitions = 0
    while pending:
        q, p, c, state, event, read, claim, consumed = value = pending.popleft()
        if p == commands*4 and q == 0: continue
        next_states = []
        if p < commands*4:
            step = p % 4
            if step == 0: next_states.append((q+1,p+1,c,state,event,read,0,consumed))
            elif step == 1: next_states.append((q,p+1,c,state,event,state,0,consumed))
            elif step == 2:
                won = read == 1 and state == 1
                next_states.append((q,p+1,c,2 if won else state,event,read,int(won),consumed))
            else: next_states.append((q,p+1,c,state,event or bool(claim),read,0,consumed))
        if c == 0: next_states.append((q,p,6 if q else 1,state,event,read,claim,consumed))
        elif c == 1: next_states.append((q,p,2,1,event,read,claim,consumed))
        elif c == 2: next_states.append((q,p,8 if post_reset_rearm else 3,state,False,read,claim,consumed))
        elif c == 8: next_states.append((q,p,3,1,event,read,claim,consumed))
        elif c == 3: next_states.append((q,p,5 if q else 4,state,event,read,claim,consumed))
        elif c == 4 and event: next_states.append((q,p,5,state,False,read,claim,consumed))
        elif c == 5: next_states.append((q,p,0,0,event,read,claim,consumed))
        elif c == 6 and q: next_states.append((q-1,p,0,state,event,read,claim,consumed+1))
        if not next_states and q:
            failures.append(value)
        for next_state in next_states:
            transitions += 1
            if next_state[0] + next_state[7] != (next_state[1]+3)//4:
                raise ValueError('Queue model lost or duplicated a command')
            if next_state not in visited:
                visited.add(next_state);pending.append(next_state)
    if failures and post_reset_rearm: raise ValueError('Atomic first-wake acknowledgement lost a queue wake')
    return {'commands': commands, 'spurious_initial_event': spurious,
        'post_reset_rearm': post_reset_rearm, 'states': len(visited),
        'transitions': transitions, 'lost_wakes': len(failures)}


def source_proof():
    import package_client_render_queue_native as producer
    original, current = sources()
    receipt = producer.expected_receipt()
    for field, values in (('source_sha256', original), ('patched_sha256', current)):
        if {name: hashlib.sha256(text.encode()).hexdigest() for name, text in values.items()} != receipt[field]:
            raise ValueError('Actual queue source differs from the native recipe')
    worker = current[WORKER]
    gfx = current[FILES[0]]
    gfx = gfx.replace('#define COH_RQ_IMPLEMENTATION\n#include "cohClientRenderQueue.h"\n', '')
    gfx = gfx.replace('    cohRqMainBegin(coh_rp_gameplay_frame);\n', '')
    gfx = re.sub(r'^[ \t]*if \(viewport == &s_mainviewport\) cohRqPhase(?:Begin|End)\(COH_RQ_\w+\);\n', '', gfx, flags=re.M)
    snapshot_block = function(gfx, '    if (cohRqEnabled())')
    gfx = gfx.replace(snapshot_block+'\n    else cohRqMainEnd(coh_rp_gameplay_frame, NULL);\n', '')
    if gfx != original[FILES[0]]: raise ValueError('Rendering/gameplay changed beyond sparse main-owned hooks')
    queue_stripped = current[FILES[1]].replace('#include "cohClientRenderQueue.h"\n', '')
    queue_stripped = queue_stripped.replace('    wtEnableWakeCoalescing(render_thread, cohRqEnabled());\n', '')
    if queue_stripped != original[FILES[1]]: raise ValueError('Render dispatch changed beyond the instance opt-in')
    normalized_worker = worker
    for signature in ('static INLINEDBG void wtQueueCounter(', 'static int wtQueueWall(',
            'void wtEnableWakeCoalescing(', 'void wtGetRenderQueueStats('):
        normalized_worker = normalized_worker.replace(function(normalized_worker, signature)+'\n\n', '')
    normalized_worker = normalized_worker.replace('/* Must be selected by the render-instance owner before the worker starts.\n * Other workers retain the accepted handshake and notification behavior. */\n', '')
    normalized_worker = normalized_worker.replace('    volatile LONG thread_asleep; // legacy 0/1; render opt-in: awake/armed/notified\n    int wake_coalescing, queue_diagnostics;\n    double queue_clock_frequency;\n    WTRenderQueueStats queue_stats; // producer-owned, process-cumulative\n',
        '    volatile int    thread_asleep; // thread sleeps when it has no data queued\n')
    normalized_worker = normalized_worker.replace('    int queue_waiting = 0, queue_wait_clock = 0;\n    double queue_wait_start = 0.0;\n', '')
    normalized_worker = re.sub(r'        // Measure only a real producer ring-capacity block, never each command\.\n.*?        // wait for worker thread to free some blocks\n',
        '        // wait for worker thread to free some blocks\n', normalized_worker, flags=re.S)
    wait_block = function(normalized_worker, '    if (queue_waiting && queue_wait_clock)')
    normalized_worker = normalized_worker.replace(wait_block+'\n', '')
    normalized_worker = normalized_worker.replace('                if (wt->wake_coalescing) InterlockedExchange(&wt->thread_asleep, 1);\n                else wt->thread_asleep = 1;\n', '                wt->thread_asleep = 1;\n')
    normalized_worker = normalized_worker.replace('                /* A consumed command can claim the next arm late. Reset may\n                 * erase its signal, so restore armed state before the final\n                 * recheck. A new command is then caught by peek or signals.\n                 * This atomic occurs only on the empty-queue transition. */\n                if (wt->wake_coalescing) InterlockedExchange(&wt->thread_asleep, 1);\n', '')
    normalized_worker = normalized_worker.replace('                if (wt->wake_coalescing) InterlockedExchange(&wt->thread_asleep, 0);\n                else wt->thread_asleep = 0;\n', '                wt->thread_asleep = 0;\n')
    producer_branch = function(normalized_worker, '    if (wt->wake_coalescing)')
    normalized_worker = normalized_worker.replace(producer_branch+'\n    else if (wt->thread_asleep', '    if (wt->thread_asleep')
    if normalized_worker != original[WORKER]: raise ValueError('Worker changed beyond the explicit coalescing and blocked-ring diagnostics')
    normalized_header = re.sub(r'// Optional render-instance first-wake acknowledgement and producer diagnostics\.\n.*?// set threading and start worker thread',
        '// set threading and start worker thread', current[WORKER_HEADER], flags=re.S)
    if normalized_header != original[WORKER_HEADER]: raise ValueError('Retained worker public API changed')
    preserved = ('static INLINEDBG void wtReqFlush(', 'static INLINEDBG void getStoredCmd(',
        'static INLINEDBG QueuedCmd *peekStoredCmd(', 'static INLINEDBG void handleQueuedCmd(',
        'static void wtDispatchMessages(', 'void wtFlushMessages(', 'void wtFlush(', 'void wtMonitor(',
        'static INLINEDBG void initCmdQueue(', 'WorkerThread *wtCreate(', 'void wtSetProcessor(',
        'void wtDestroy(', 'void wtSetThreaded(', 'int wtIsThreaded(', 'void wtStart(',
        'void wtQueueDebugCmd(', 'void *wtAllocCmd(', 'void wtCancelCmd(', 'void wtQueueCmd(', 'void wtQueueMsg(')
    for signature in preserved:
        if function(original[WORKER], signature) != function(worker, signature):
            raise ValueError('Retained worker control or payload behavior changed: '+signature)
    old_send, new_send = function(original[WORKER], 'void wtSendCmd('), function(worker, 'void wtSendCmd(')
    if old_send[:old_send.index('    if (wt->thread_asleep')] != new_send[:new_send.index('    if (wt->wake_coalescing)')]:
        raise ValueError('Immediate dispatch or queue publication changed')
    if '    else if (wt->thread_asleep && wt->data_queued)\n        SetEvent(wt->data_queued);' not in new_send:
        raise ValueError('Other-worker notification policy changed')
    if new_send.index('wt->cmd_queue.end = wt->cmd_queue.next_end;') > new_send.index('InterlockedCompareExchange'):
        raise ValueError('Wake claim occurs before command publication')
    thread = function(worker, 'static unsigned __stdcall wtThread(')
    order = ('InterlockedExchange(&wt->thread_asleep, 1)', 'ResetEvent(wt->data_queued)',
        'cmd = peekStoredCmd(&wt->cmd_queue);', 'WaitForSingleObject(wt->data_queued, INFINITE)',
        'InterlockedExchange(&wt->thread_asleep, 0)')
    start = thread.index('if (wt->data_queued)')
    positions = [thread.index(token, start) for token in order]
    if positions != sorted(positions): raise ValueError('Retained arm/reset/recheck ordering changed')
    reset = thread.index('ResetEvent(wt->data_queued)', start)
    rearm = thread.index('InterlockedExchange(&wt->thread_asleep, 1)', reset)
    recheck = thread.index('cmd = peekStoredCmd(&wt->cmd_queue);', reset)
    if not reset < rearm < recheck: raise ValueError('Late consumed-command notification can suppress the next wake')
    queue = current[FILES[1]]
    if function(original[FILES[1]], 'static void cmdDispatchCallback(') != function(queue, 'static void cmdDispatchCallback('):
        raise ValueError('Render command callback or inactive pipeline sampling changed')
    if function(original[FILES[1]], 'static void cmdDispatch(') != function(queue, 'static void cmdDispatch('):
        raise ValueError('Drawing callbacks changed')
    if '#define CMD_QUEUE_SIZE    (1<<20)' not in queue or '#define MSG_QUEUE_SIZE    (1<<6)' not in queue:
        raise ValueError('Queue capacities changed')
    for name in FILES:
        added = set(current[name].splitlines()) - set(original[name].splitlines())
        if any(re.search(r'\b(?:glFinish|glFlush|glGetQueryObject|glReadPixels|Sleep|WaitForSingleObject)\s*\(', line) for line in added):
            raise ValueError('Queue continuation introduced a completion wait or rendering policy')
    unsafe = wake_model(post_reset_rearm=False)
    if not unsafe['lost_wakes']: raise ValueError('Regression model did not expose the stale-claim wake loss')
    return {'retained_worker_functions': len(preserved), 'two_command_model': wake_model(),
        'without_post_reset_rearm_model': unsafe,
        'spurious_model': wake_model(spurious=True), 'three_command_model': wake_model(commands=3),
        'reverse_exact_ancestry': True, 'command_payloads_and_callbacks_preserved': True,
        'queue_capacity_and_control_wakes_preserved': True, 'unthreaded_dispatch_preserved': True}


class RenderQueueSourceTests(unittest.TestCase):
    def test_complete_staged_chain_and_parent_receipts_reject_source_mutation(self):
        import package_client_render_queue_native as producer
        with tempfile.TemporaryDirectory(prefix='coh-render-queue-ancestry-') as temporary:
            source=Path(temporary)/'source'
            expected=producer.stage(SimpleNamespace(output=source))
            actual,frozen=producer.validate_source(source)
            self.assertEqual(actual,expected)
            self.assertEqual(actual['base_client_render_pipeline_build_input'],producer.base.expected_receipt())
            self.assertEqual(set(frozen),set(producer.baseline.INPUTS))
            for name in (WORKER, 'Game/src/cohClientRenderPipeline.h'):
                path=source/name;original=path.read_bytes();path.write_bytes(original+b'\n/* foreign mutation */\n')
                with self.subTest(name=name),self.assertRaises(ValueError): producer.validate_source(source)
                path.write_bytes(original)

    def test_source_reverse_ancestry_payload_and_fidelity_conservation(self):
        self.assertTrue(source_proof())

    def test_atomic_wake_adversarial_schedules_conserve_every_command(self):
        self.assertGreater(wake_model(post_reset_rearm=False)['lost_wakes'],0)
        for count in (1,2,3):
            for spurious in (False,True):
                self.assertEqual(wake_model(count,spurious)['lost_wakes'],0)

    def test_real_blocked_allocation_only_has_two_clock_sites(self):
        original,current=sources()
        alloc=function(current[WORKER], 'static INLINEDBG void *allocStoredCmd(')
        self.assertEqual(alloc.count('wtQueueWall('),2)
        self.assertLess(alloc.index('if (num_blocks+filler_blocks <= free_blocks)'),alloc.index('queue_wait_clock = wtQueueWall'))
        self.assertIn('if (queue_waiting && queue_wait_clock)',alloc)
        self.assertEqual(function(original[WORKER], 'static INLINEDBG void wtReqFlush('),function(current[WORKER], 'static INLINEDBG void wtReqFlush('))

    def test_render_owner_is_the_only_opted_in_worker_before_start(self):
        _,current=sources()
        queue=current[FILES[1]]
        self.assertEqual(queue.count('wtEnableWakeCoalescing('),1)
        begin=function(queue,'void renderThreadStart(')
        self.assertLess(begin.index('wtEnableWakeCoalescing(render_thread, cohRqEnabled());'),begin.index('wtStart(render_thread);'))
        self.assertNotIn('cohRqCommand',queue)

    def test_sparse_scene_hooks_retain_main_viewport_calls_and_nested_scope(self):
        original,current=sources()
        gfx=current[FILES[0]]
        for target,phase in (('gfxSetupStuffToDraw(viewport);','SETUP'),
                ('sortModels(viewport->renderOpaquePass, viewport->renderAlphaPass);','SORT')):
            order=(f'if (viewport == &s_mainviewport) cohRqPhaseBegin(COH_RQ_{phase});',target,
                f'if (viewport == &s_mainviewport) cohRqPhaseEnd(COH_RQ_{phase});')
            positions=[gfx.index(token) for token in order]
            self.assertEqual(positions,sorted(positions))
        old_calls=re.findall(r'drawSortedModels_ex\([^\n]+\);',original[FILES[0]])
        self.assertEqual(old_calls,re.findall(r'drawSortedModels_ex\([^\n]+\);',gfx))
        self.assertEqual(gfx.count('cohRqPhaseBegin(COH_RQ_DRAW)'),len(old_calls))
        self.assertIn('cohRqMainBegin(coh_rp_gameplay_frame);',gfx)
        self.assertIn('cohRqMainEnd(coh_rp_gameplay_frame, &snapshot);',gfx)


if __name__ == '__main__': unittest.main()
