"""Render-worker handoff with the ARM64 spin-before-sleep (patch 0116), under TSan.

Compiles the prepared WorkerThread.c on the host with the ARM64 branches
selected (atomic publication from patch 0050, polling from patch 0116) and
thin pthread shims for the Win32 calls it uses. Win32 auto-reset events are
modelled with a mutex and condition variable, and each event call is counted
as one wineserver round trip.

Two workers run concurrently, each fed by its own producer thread with bursts
of commands carrying the worker id, sequence numbers and checksums, with pauses
between bursts and wtFlush calls, while a third thread samples the counters
live through the real frame-rate-log sampler (armportWorkerSample). Every
command must reach its own worker exactly once, in order and intact, with no
data race. With polling, the workers must sleep about once per frame gap, not
per command. --no-spin removes the polling block and reports the baseline;
--plain-counters restores plain counter updates and reads and must fail TSan.
"""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--no-spin', action='store_true')
parser.add_argument('--plain-counters', action='store_true',
                    help='negative control: plain counter updates and reads must be reported by TSan')
args = parser.parse_args()
text = (args.source / 'libs/UtilitiesLib/src/components/WorkerThread.c').read_text()
assert 'ARMPORT_WT_SPIN_US' in text and 'armport_wt_spin_hits' in text, 'patch 0116 is missing'
body = re.sub(r'^#include [^\n]*\n', '', text, flags=re.M)
body = body.replace('#if defined(__aarch64__) && defined(__MINGW32__)', '#if 1')
if args.no_spin:
    body, count = re.subn(r'^#define ARMPORT_WT_SPIN_US \d+\n', '', body, flags=re.M)
    assert count == 1   # every polling block is #ifdef ARMPORT_WT_SPIN_US

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
header = (args.source / 'Game/src/graphics/armport_frame_rate_log.h').read_text()
sampler = header[header.index('typedef struct ArmportWorkerSample'):header.index('static ArmportWorkerSample armport_worker_since;')]
assert '__atomic_load_n(&armport_wt_sleeps' in sampler and '__atomic_load_n(&armport_wt_spin_hits' in sampler
assert 'static LARGE_INTEGER' not in body, 'the spin timer must not be a shared function static'
if args.plain_counters:
    # Negative control: the 0.13.42 review shape (plain ++ and plain reads).
    body = body.replace('#define ARMPORT_WT_COUNT(counter) __atomic_fetch_add(&(counter), 1, __ATOMIC_RELAXED)',
                        '#define ARMPORT_WT_COUNT(counter) ((counter)++)')
    sampler = re.sub(r'__atomic_load_n\(&(\w+), __ATOMIC_RELAXED\)', r'\1', sampler)

main = r'''
typedef struct { DWORD dwLowDateTime, dwHighDateTime; } FILETIME;
static HANDLE GetCurrentProcess(void) { return 0; }
static int GetProcessTimes(HANDLE p, FILETIME *c, FILETIME *e, FILETIME *k, FILETIME *u) {
    (void)p; memset(c, 0, sizeof(*c)); memset(e, 0, sizeof(*e)); memset(k, 0, sizeof(*k)); memset(u, 0, sizeof(*u)); return 1; }
''' + sampler + r'''
#define WORKERS 2
#define BURSTS 300
#define PER_BURST 60
typedef struct { int id; unsigned long next_expected, dispatched, bad; WorkerThread *wt; } Lane;
static Lane lanes[WORKERS];
static volatile int sampling = 1;
static long samples;
static void dispatch(void *user, int type, void *data) {
    Lane *lane = user; unsigned long *v = data;
    if (type != WT_CMD_USER_START || v[0] != (unsigned long)lane->id || v[1] != lane->next_expected
        || v[2] != v[1] * 2654435761ul + lane->id || v[3] != ~v[1]) lane->bad++;
    lane->next_expected = v[1] + 1; lane->dispatched++;
}
static void messages(void *user, int type, void *data) { (void)user; (void)type; (void)data; }
static void *producer(void *p) {           /* one producer per worker, as for the render thread */
    Lane *lane = p; unsigned long sequence = 0;
    for (int burst = 0; burst < BURSTS; burst++) {
        for (int i = 0; i < PER_BURST; i++) {
            unsigned long v[4] = {lane->id, sequence, sequence * 2654435761ul + lane->id, ~sequence}; sequence++;
            wtQueueCmd(lane->wt, WT_CMD_USER_START, v, sizeof(v));
            if (i % 7 == 0) usleep(20);
        }
        if (burst % 10 == 9) wtFlush(lane->wt);
        usleep(3000);
    }
    wtFlush(lane->wt);
    return 0;
}
static void *sampler_thread(void *p) {     /* the frame-rate log reading the totals live */
    (void)p; ArmportWorkerSample s;
    while (__atomic_load_n(&sampling, __ATOMIC_RELAXED)) { armportWorkerSample(&s); samples++; usleep(200); }
    return 0;
}
int main(void) {
    pthread_t producers[WORKERS], sampler_id;
    for (int i = 0; i < WORKERS; i++) {
        lanes[i].id = i;
        lanes[i].wt = wtCreate(dispatch, 1 << 10, messages, 0, 1 << 6, &lanes[i]);
        wtSetThreaded(lanes[i].wt, 1);
    }
    for (int i = 0; i < WORKERS; i++) wtStart(lanes[i].wt);   /* workers run concurrently */
    pthread_create(&sampler_id, 0, sampler_thread, 0);
    for (int i = 0; i < WORKERS; i++) pthread_create(&producers[i], 0, producer, &lanes[i]);
    for (int i = 0; i < WORKERS; i++) pthread_join(producers[i], 0);
    __atomic_store_n(&sampling, 0, __ATOMIC_RELAXED);
    pthread_join(sampler_id, 0);
    for (int i = 0; i < WORKERS; i++) wtDestroy(lanes[i].wt);
    long per_lane = BURSTS * PER_BURST, commands = per_lane * WORKERS; unsigned long dispatched = 0, bad = 0; int lanes_ok = 1;
    for (int i = 0; i < WORKERS; i++) {
        dispatched += lanes[i].dispatched; bad += lanes[i].bad;
        lanes_ok &= lanes[i].dispatched == (unsigned long)per_lane && !lanes[i].bad;
    }
    printf("worker: workers=%d commands=%ld dispatched=%lu bad=%lu sleeps=%ld spin_hits=%ld event_round_trips=%ld samples=%ld\n",
           WORKERS, commands, dispatched, bad, __atomic_load_n(&armport_wt_sleeps, __ATOMIC_RELAXED),
           __atomic_load_n(&armport_wt_spin_hits, __ATOMIC_RELAXED), __atomic_load_n(&round_trips, __ATOMIC_RELAXED), samples);
    return lanes_ok && samples > 0 ? 0 : 1;
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
    if args.plain_counters:
        # The report must point at a counter update: worker vs worker (lost
        # increments) or worker vs the live sampler.
        lines = source.read_text().splitlines()
        racy = [int(n) for n in re.findall(r'worker\.c:(\d+)', result.stderr)]
        reported = result.returncode == 66 and 'data race' in result.stderr and any(
            'ARMPORT_WT_COUNT' in lines[n - 1] or 'armport_wt_' in lines[n - 1] for n in racy if 0 < n <= len(lines))
        print('plain counters: TSan %s' % ('reported the counter race' if reported else 'did not report a counter race'))
        if not reported: print(result.returncode, result.stderr[-2500:])
        raise SystemExit(0 if reported else 1)
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
