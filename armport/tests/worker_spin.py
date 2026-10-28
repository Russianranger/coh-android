"""Render-worker handoff with the ARM64 spin-before-sleep (patch 0116), under TSan.

Compiles the prepared WorkerThread.c on the host with the ARM64 branches
selected (atomic publication from patch 0050, polling from patch 0116) and
thin pthread shims for the Win32 calls it uses. Win32 auto-reset events are
modelled with a mutex and condition variable, and each event call is counted
as one wineserver round trip.

The producer queues bursts of commands carrying sequence numbers and payload
checksums, with pauses between bursts and wtFlush calls. Every command must be
dispatched exactly once, in order and intact, with no data race. With polling,
almost every in-burst command must be picked up without a sleep. --no-spin
removes the polling block and reports the baseline counts for comparison.
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--no-spin', action='store_true')
args = parser.parse_args()
text = (args.source / 'libs/UtilitiesLib/src/components/WorkerThread.c').read_text()
assert 'ARMPORT_WT_SPIN_US' in text and 'armport_wt_spin_hits' in text, 'patch 0116 is missing'
body = re.sub(r'^#include [^\n]*\n', '', text, flags=re.M)
body = body.replace('#if defined(__aarch64__) && defined(__MINGW32__)', '#if 1')
if args.no_spin:
    body, count = re.subn(r'#ifdef ARMPORT_WT_SPIN_US\n.*?\n#endif\n', '', body, count=1, flags=re.S)
    assert count == 1

shim = r'''
#define _GNU_SOURCE
#include <assert.h>
#include <pthread.h>
#include <sched.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
typedef uint32_t U32; typedef uint8_t U8; typedef unsigned long DWORD; typedef void *LPVOID;
typedef void *HANDLE; typedef DWORD *LPDWORD;
typedef struct { long long QuadPart; } LARGE_INTEGER;
#define __stdcall
#define __declspec(x) __attribute__((aligned(16)))
#define INLINEDBG inline
#define EXCEPTION_HANDLER_BEGIN
#define EXCEPTION_HANDLER_END
#define INFINITE 0xffffffffu
typedef pthread_mutex_t CRITICAL_SECTION;
static void InitializeCriticalSectionAndSpinCount(CRITICAL_SECTION *c, int n) { (void)n; pthread_mutex_init(c, 0); }
static void EnterCriticalSection(CRITICAL_SECTION *c) { pthread_mutex_lock(c); }
static void LeaveCriticalSection(CRITICAL_SECTION *c) { pthread_mutex_unlock(c); }
static void DeleteCriticalSection(CRITICAL_SECTION *c) { pthread_mutex_destroy(c); }
#include <alloca.h>
#define _alloca alloca
#define ZeroStruct(p) memset((p), 0, sizeof(*(p)))
typedef struct { pthread_mutex_t m; pthread_cond_t c; int set; } Event;
static long round_trips;            /* event calls: one wineserver request each */
static HANDLE CreateEvent(void *a, int manual, int initial, void *n) {
    (void)a; (void)manual; (void)n; Event *e = calloc(1, sizeof(*e));
    pthread_mutex_init(&e->m, 0); pthread_cond_init(&e->c, 0); e->set = initial; return e; }
static int SetEvent(HANDLE h) { Event *e = h; __atomic_add_fetch(&round_trips, 1, __ATOMIC_RELAXED);
    pthread_mutex_lock(&e->m); e->set = 1; pthread_cond_signal(&e->c); pthread_mutex_unlock(&e->m); return 1; }
static int ResetEvent(HANDLE h) { Event *e = h; __atomic_add_fetch(&round_trips, 1, __ATOMIC_RELAXED);
    pthread_mutex_lock(&e->m); e->set = 0; pthread_mutex_unlock(&e->m); return 1; }
static DWORD WaitForSingleObject(HANDLE h, DWORD ms) { Event *e = h; (void)ms;
    __atomic_add_fetch(&round_trips, 1, __ATOMIC_RELAXED);
    pthread_mutex_lock(&e->m); while (!e->set) pthread_cond_wait(&e->c, &e->m); e->set = 0;
    pthread_mutex_unlock(&e->m); return 0; }
static int CloseHandle(HANDLE h) { (void)h; return 1; }
static void Sleep(DWORD ms) { usleep(ms * 1000); }
static void YieldProcessor(void) { sched_yield(); }
static int QueryPerformanceFrequency(LARGE_INTEGER *f) { f->QuadPart = 1000000000ll; return 1; }
static int QueryPerformanceCounter(LARGE_INTEGER *c) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
    c->QuadPart = t.tv_sec * 1000000000ll + t.tv_nsec; return 1; }
static DWORD GetCurrentThreadId(void) { return (DWORD)(uintptr_t)pthread_self(); }
static void ExitThread(DWORD code) { (void)code; pthread_exit(0); }
typedef unsigned (__stdcall *ThreadProc)(LPVOID);
typedef struct { ThreadProc proc; LPVOID arg; } Start;
static void *trampoline(void *p) { Start s = *(Start *)p; free(p); s.proc(s.arg); return 0; }
static HANDLE CreateThread(void *a, int stack, ThreadProc proc, LPVOID arg, int flags, unsigned *id) {
    (void)a; (void)stack; (void)flags; pthread_t *t = malloc(sizeof(*t)); Start *s = malloc(sizeof(*s));
    s->proc = proc; s->arg = arg; pthread_create(t, 0, trampoline, s); pthread_detach(*t); *id = 1; return t; }
static void XSetThreadProcessor(HANDLE h, int p) { (void)h; (void)p; }
typedef struct WorkerThread WorkerThread;
typedef void (*WTDebugCallback)(void *data);
typedef void (*WTDispatchCallback)(void *user_data, int type, void *data);
typedef void (*WTStallCallback)(void);
enum { WT_CMD_NOP=1, WT_CMD_DEBUGCALLBACK, WT_CMD_USER_START };
'''
main = r'''
#define BURSTS 400
#define PER_BURST 60
static unsigned long next_expected, dispatched, bad;
static void dispatch(void *user, int type, void *data) {
    (void)user; unsigned long *v = data;
    if (type != WT_CMD_USER_START || v[0] != next_expected || v[1] != v[0] * 2654435761ul || v[2] != ~v[0]) bad++;
    next_expected = v[0] + 1; dispatched++;
}
static void messages(void *user, int type, void *data) { (void)user; (void)type; (void)data; }
int main(void) {
    WorkerThread *wt = wtCreate(dispatch, 1 << 10, messages, 0, 1 << 6, 0);
    wtSetThreaded(wt, 1); wtStart(wt);
    unsigned long sequence = 0;
    for (int burst = 0; burst < BURSTS; burst++) {
        for (int i = 0; i < PER_BURST; i++) {
            unsigned long v[3] = {sequence, sequence * 2654435761ul, ~sequence}; sequence++;
            wtQueueCmd(wt, WT_CMD_USER_START, v, sizeof(v));
            if (i % 7 == 0) usleep(20);        /* main-thread work between draw commands */
        }
        if (burst % 10 == 9) wtFlush(wt);
        usleep(3000);                          /* frame gap: the worker sleeps on the event */
    }
    wtFlush(wt);
    wtDestroy(wt);
    long commands = BURSTS * PER_BURST;
    printf("worker: commands=%ld dispatched=%lu bad=%lu sleeps=%ld spin_hits=%ld event_round_trips=%ld\n",
           commands, dispatched, bad, armport_wt_sleeps, armport_wt_spin_hits, round_trips);
    return dispatched == (unsigned long)commands && !bad ? 0 : 1;
}
'''
with tempfile.TemporaryDirectory() as temporary:
    source = Path(temporary) / 'worker.c'
    exe = Path(temporary) / 'worker'
    source.write_text(shim + body + main)
    subprocess.run(['cc', '-std=gnu11', '-O1', '-g', '-w', '-fsanitize=thread', '-pthread',
                    str(source), '-o', str(exe)], check=True)
    # Two upstream races present with and without patch 0116 (see --no-spin):
    # wtStart and the new thread both store thread_id (the same value on
    # Windows) before any command is queued; wtReqFlush writes the
    # flush_requested bit of a bitfield the worker reads only for debug mode.
    # Every other report, including any on the queue indices or command
    # contents, still fails the run.
    suppressions = Path(temporary) / 'tsan.supp'
    suppressions.write_text('race:wtStart\nrace:wtReqFlush\n')
    result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=300,
        env={'TSAN_OPTIONS': 'halt_on_error=1 exitcode=66 suppressions=%s' % suppressions})
    line = result.stdout.strip()
    print(line)
    if result.returncode != 0:
        print(result.stderr[-3000:])
        raise SystemExit(result.returncode)
    counts = dict(item.split('=') for item in line.split()[1:])
    commands, sleeps = int(counts['commands']), int(counts['sleeps'])
    if not args.no_spin:
        # Bursts arrive faster than the spin bound; the worker should sleep
        # about once per frame gap, not once per command.
        assert sleeps <= commands // 10, 'worker still sleeps per command: %s' % line
