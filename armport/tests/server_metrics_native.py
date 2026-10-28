#!/usr/bin/env python3
"""Execute the prepared MapServer loop, fileAlloc bodies and metric producer.

Adapters supply deterministic Windows clocks and file I/O, not a second copy of
the measurement logic. --original executes the upstream loop/file functions
with the same assertions and must fail because no metrics are produced. This
does not qualify the actual Windows binary or a packaged server producer.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

CASES = ['window', 'disabled', 'files', 'thread', 'slow', 'clock', 'saturation']
NEGATIVE_ASSERTION = 's->ticks == 4 && s->file_calls == 4 && s->window_start == 0'


def test_cases(source):
    text = (source / 'MapServer/src/svr/svr_init.c').read_text()
    return CASES + (['progress_markers'] if 'cohMapProgressMark(COH_MAP_STAGE_LOOP_PRE_TICK);' in text else [])


def function(text, signature):
    start = text.index(signature)
    return text[start:text.index('\n}\n', start) + 3]


def fixture(source, original=None):
    root = original or source
    files = (root / 'libs/UtilitiesLib/src/utils/file.c').read_text()
    svr = (root / 'MapServer/src/svr/svr_init.c').read_text()
    marker = svr.index('    if (coll_test)\n        gridCollPerfTest();')
    start = svr.index('    for(;;)\n    {', marker)
    end = svr.index('\n    }\n    EXCEPTION_HANDLER_END', start)
    loop = svr[start + len('    for(;;)\n    {'):end]
    if original:
        bodies = function(files, 'void *fileAlloc_dbg(') + function(files, 'void *fileAllocEx_dbg(')
    else:
        bodies = ''.join(function(files, sig) for sig in (
            'static void *fileAllocInternal_dbg(', 'void *fileAlloc_dbg(',
            'static void *fileAllocExInternal_dbg(', 'void *fileAllocEx_dbg('))
        assert '#include "armport_server_metrics_impl.h"' in files
        assert 'armportServerMetricsInit(db_state.map_id);' in svr[marker:start]
        assert loop.index('armportServerMetricsTickBegin();') < loop.index('svrTick();')
        assert loop.index('svrTick();') < loop.index('armportServerMetricsTickEnd();') < loop.index('sleepAndCalcTimers();')
        assert loop.index('sleepAndCalcTimers();') < loop.index('armportServerMetricsLoopEnd();')
        assert loop.strip().startswith('armportServerMetricsTickBegin();')
        assert loop.strip().endswith('armportServerMetricsLoopEnd();')
    return r'''
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <pthread.h>
#define __declspec(x) __thread
static __thread long long fake_now;
static __thread int clock_calls, clock_ok = 1;
static int frequency_ok = 1;
static int progress_marker_ms;
#include "utilitieslib/utils/wininclude.h"
static int QueryPerformanceCounter(LARGE_INTEGER *p) { ++clock_calls; p->QuadPart = fake_now; return clock_ok; }
static int QueryPerformanceFrequency(LARGE_INTEGER *p) { p->QuadPart = 1000; return frequency_ok; }
static DWORD GetCurrentProcessId(void) { return 42; }
/* Poison the same CRT names file.h replaces. The producer must isolate them. */
#define snprintf forbidden_snprintf
#define fputs forbidden_fputs
#define fflush forbidden_fflush
#define FILE ForbiddenFileWrapper
#include "armport_server_metrics_impl.h"
#undef snprintf
#undef fputs
#undef fflush
#undef FILE
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); return 1; } } while (0)
#define MEM_DBG_PARMS
#define MEM_DBG_PARMS_CALL
#define MAX_PATH 1024
#define PERFINFO_AUTO_START(a,b)
#define PERFINFO_AUTO_STOP()
#define PERFINFO_AUTO_STOP_START(a,b)
#define PERFINFO_AUTO_STOP_CHECKED(a)
#define cohMapProgressMark(a) (fake_now += progress_marker_ms)
#define assert(x) ((void)0)
typedef int (*FileProcessCallback)(int, int);
static int filealloc_failure_spot;
static int io_failure, nested_once;
static char *fileLocateRead(const char *name, char *buffer) {
    fake_now += 5; if (io_failure == 1) return NULL; strcpy(buffer, name); return buffer;
}
static intptr_t fileSize(const char *name) { (void)name; fake_now += 5; return io_failure == 2 ? -1 : 3; }
static int is_pigged_path(const char *name) { (void)name; return 0; }
static FILE *fake_open(const char *name, const char *mode) { (void)name; (void)mode; fake_now += 10; return io_failure == 3 ? NULL : (FILE *)(uintptr_t)1; }
static size_t fake_read(void *buffer, size_t size, size_t count, FILE *file) {
    (void)size; (void)file; fake_now += 20; memcpy(buffer, "abc", count); return count;
}
static int fake_close(FILE *file) { (void)file; fake_now += 10; return 0; }
static void *fake_malloc(size_t n) { return io_failure == 4 ? NULL : malloc(n); }
#define fopen fake_open
#define fread fake_read
#define fclose fake_close
#define smalloc fake_malloc
#define srealloc realloc
''' + bodies + r'''
#undef fopen
#undef fread
#undef fclose
static int nested(int done, int total) {
    (void)done; (void)total;
    if (!nested_once++) { void *p = fileAlloc_dbg("nested", NULL); free(p); }
    return 1;
}
static void timerTickBegin(void) {}
static void timerTickEnd(void) {}
static void startProfilingCPU(void) {}
static void endProfilingCPU(void) {}
static void svrTick(void) { void *p = fileAlloc_dbg("file", NULL); free(p); fake_now += 200; }
static void sleepAndCalcTimers(void) { fake_now += 750; }
static void one_actual_loop(void) {
''' + loop + r'''
}
static void *background(void *unused) {
    void *p;
    (void)unused;
    /* Main thread opt-in must not enable another thread or share counters. */
    p = fileAlloc_dbg("worker", NULL); free(p);
    return (void *)(uintptr_t)(clock_calls != 0 || armport_server_metrics.enabled != 0);
}
int main(int argc, char **argv) {
    ArmportServerMetrics *s = &armport_server_metrics;
    const char *mode = argc > 1 ? argv[1] : "window";
    int i;
    /* Keep helpers referenced in the original-code negative control. */
    (void)armportServerMetricsFileBegin; (void)armportServerMetricsFileEnd;
    setenv("ARMPORT_SERVER_METRICS", "1", 1);
    if (!strcmp(mode, "disabled")) {
        const char *options[] = {"0", "", "10", "true"};
        for (i = 0; i < 4; ++i) {
            setenv("ARMPORT_SERVER_METRICS", options[i], 1);
            armportServerMetricsInit(2);
            one_actual_loop();
        }
        unsetenv("ARMPORT_SERVER_METRICS"); armportServerMetricsInit(2); one_actual_loop();
        CHECK(clock_calls == 0 && s->ticks == 0);
        puts("disabled: clocks=0"); return 0;
    }
    armportServerMetricsInit(2);
    if (!strcmp(mode, "progress_markers")) {
        progress_marker_ms = 10;
        one_actual_loop();
        CHECK(s->ticks == 1 && s->file_calls == 1);
        CHECK(s->max_tick_ms == 280 && s->max_loop_ms == 1040 && s->file_ms == 50);
        puts("progress markers: work_ms=280 loop_ms=1040 file_ms=50"); return 0;
    }
    if (!strcmp(mode, "window")) {
        for (i = 0; i < 4; ++i) one_actual_loop();
        CHECK(s->ticks == 4 && s->file_calls == 4 && s->window_start == 0);
        CHECK(s->max_tick_ms == 250 && s->max_loop_ms == 1000 && s->file_ms == 200);
        one_actual_loop(); /* Exactly five seconds, not strictly greater. */
        CHECK(s->ticks == 0 && s->file_ms == 0 && s->window_start == 5000);
        for (i = 0; i < 5; ++i) one_actual_loop();
        CHECK(s->window_start == 10000); return 0;
    }
    if (!strcmp(mode, "files")) {
        int len = 0, before = clock_calls;
        void *p = fileAlloc_dbg("outside_tick", &len);
        CHECK(p && len == 3 && !memcmp(p, "abc", 4)); free(p);
        CHECK(clock_calls == before && s->file_calls == 0);
        armportServerMetricsTickBegin();
        for (io_failure = 1; io_failure <= 4; ++io_failure) {
            p = fileAlloc_dbg("failed", NULL); CHECK(!p);
        }
        io_failure = 0;
        p = fileAllocEx_dbg("outer", &len, "rb", nested);
        CHECK(p && len == 3 && !memcmp(p, "abc", 4)); free(p);
        /* 5+10+20+30 failed; outer50+nested50; nested is counted once. */
        CHECK(s->file_calls == 5 && s->file_failures == 4 && s->file_ms == 165 && s->file_depth == 0);
        armportServerMetricsTickEnd();
        puts("files: failures=4 outer_calls=5 wall_ms=165"); return 0;
    }
    if (!strcmp(mode, "thread")) {
        pthread_t thread; void *result;
        CHECK(pthread_create(&thread, NULL, background, NULL) == 0);
        CHECK(pthread_join(thread, &result) == 0 && result == NULL);
        CHECK(s->enabled == 1 && s->file_calls == 0);
        puts("thread: uninitialized TLS stays disabled"); return 0;
    }
    if (!strcmp(mode, "slow")) {
        armportServerMetricsTickBegin();
        fake_now = 7000; armportServerMetricsTickEnd();
        fake_now = 7500; armportServerMetricsLoopEnd();
        CHECK(s->window_start == 7500 && s->ticks == 0);
        return 0;
    }
    if (!strcmp(mode, "clock")) {
        clock_ok = 0; armportServerMetricsTickBegin();
        CHECK(!s->enabled && s->ticks == 0);
        i = clock_calls; one_actual_loop(); CHECK(clock_calls == i);
        clock_ok = 1; fake_now = 20; armportServerMetricsInit(2);
        fake_now = 19; armportServerMetricsTickBegin(); CHECK(!s->enabled);
        frequency_ok = 0; armportServerMetricsInit(2); CHECK(!s->enabled);
        return 0;
    }
    if (!strcmp(mode, "saturation")) {
        s->ticks = ULLONG_MAX;
        one_actual_loop(); CHECK(s->ticks == ULLONG_MAX && s->saturated);
        puts("saturation: no counter wrap"); return 0;
    }
    return 2;
}
'''


def run(source, original=None, expect_control_failure=False):
    with tempfile.TemporaryDirectory(prefix='armport-server-metrics-') as directory:
        work = Path(directory)
        inc = work / 'utilitieslib/utils'
        inc.mkdir(parents=True)
        (inc / 'wininclude.h').write_text('#ifndef TEST_WINDOWS\n#define TEST_WINDOWS\ntypedef uint32_t DWORD; typedef long long LONGLONG; typedef struct { LONGLONG QuadPart; } LARGE_INTEGER;\n#endif\n')
        (inc / 'armport_server_metrics.h').write_bytes((source / 'libs/UtilitiesLib/include/utilitieslib/utils/armport_server_metrics.h').read_bytes())
        (work / 'armport_server_metrics_impl.h').write_bytes((source / 'libs/UtilitiesLib/src/utils/armport_server_metrics_impl.h').read_bytes())
        control = fixture(source, original)
        (work / 'control.c').write_text(control)
        exe = work / 'control'
        subprocess.run(['cc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-but-set-variable',  # upstream fileAllocEx original_total
                        '-fsanitize=address,undefined', '-pthread', '-I', str(work),
                        str(work / 'control.c'), '-o', str(exe)], check=True)
        for mode in (['window'] if original else test_cases(source)):
            result = subprocess.run([str(exe), mode], capture_output=True, text=True,
                                    env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'})
            print(mode + ': ' + ' | '.join(result.stdout.splitlines()))
            if expect_control_failure:
                assert result.returncode != 0 and 'FAIL line ' in result.stderr and NEGATIVE_ASSERTION in result.stderr, result.stderr
                print('unpatched negative control: expected missing-metrics assertion')
                return hashlib.sha256(control.encode()).hexdigest()
            if result.returncode:
                print(result.stderr)
                raise SystemExit(result.returncode)
            if mode == 'window':
                rows = result.stdout.splitlines()
                assert len(rows) == 2, rows
                expected = {'status': 'ok', 'map_id': '2', 'pid': '42', 'seconds': '5.000000',
                            'ticks': '5', 'max_tick_ms': '250.000', 'max_loop_ms': '1000.000',
                            'filealloc_ms': '250.000', 'filealloc_calls': '5', 'filealloc_failures': '0',
                            'counter_saturated': '0', 'scope': 'post_ready_main_thread_outer_filealloc'}
                for row in rows:
                    assert row.startswith('ARMPORT_SERVER_METRICS_V1 '), row
                    assert dict(field.split('=', 1) for field in row.split()[1:]) == expected, row
            if mode == 'disabled':
                assert 'ARMPORT_SERVER_METRICS_V1' not in result.stdout
            if mode == 'slow':
                fields = dict(field.split('=', 1) for field in result.stdout.split()[1:])
                assert fields['ticks'] == '1' and fields['seconds'] == '7.500000'
                assert fields['max_tick_ms'] == '7000.000' and fields['max_loop_ms'] == '7500.000'
        print('server metrics extracted-source controls passed')
        return hashlib.sha256(control.encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--original', type=Path,
                        help='Legacy negative invocation: expected assertion exits nonzero')
    parser.add_argument('--negative-control', type=Path,
                        help='Require the original-source missing-metrics assertion after positive checks')
    parser.add_argument('--report', type=Path,
                        help='Write passed host evidence bound to a prepared server source receipt')
    parser.add_argument('--upstream-root', type=Path,
                        default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    if args.original and (args.report or args.negative_control):
        parser.error('--original cannot be combined with --report or --negative-control')
    if args.report and not args.negative_control:
        parser.error('--report requires --negative-control')
    source = args.source.resolve()
    receipt = None
    if args.report:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
        import prepare_server_metrics_source as staging
        receipt = staging.verify_prepared(source, args.upstream_root)
        assert args.negative_control.resolve() == (args.upstream_root / 'upstream/ouroboros').resolve()
    positive = run(source, args.original)
    if args.negative_control:
        negative = run(source, args.negative_control.resolve(), expect_control_failure=True)
    if args.report:
        document = {'format': 1, 'role': 'armport_server_metrics_source_checks',
                    'status': 'passed', 'variant': receipt['variant'],
                    'build_input_sha256': staging.digest(staging.canonical(receipt)),
                    'source_sha256': receipt['patched_sha256'],
                    'original_sha256': {name: staging.digest((args.negative_control / name).read_bytes())
                                        for name in (staging.SVR, staging.FILE)},
                    'fixture_sha256': {'positive': positive, 'negative': negative},
                    'test_script_sha256': staging.digest(Path(__file__).read_bytes()),
                    'compiler': subprocess.check_output(['cc', '--version'], text=True).splitlines()[0],
                    'execution_environment': 'posix_host_with_windows_clock_and_file_io_shims',
                    'positive_cases': test_cases(source), 'unpatched_control_failed': True,
                    'unpatched_control_failure': 'runtime_missing_metrics_assertion',
                    'shipping_binary_executed': False}
        staging.validate_test_report(document, receipt, args.upstream_root)
        args.report.write_text(json.dumps(document, indent=2) + '\n')


if __name__ == '__main__':
    main()
