"""Execute sparse queue metrics and require genuine Win32 production clocks."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT / 'tools')]
from package_reference_runtime import file_record

HEADER = 'database/client-render-queue/overlay/Game/src/cohClientRenderQueue.h'
PATCH = 'patches/client-render-queue/0001-coalesce-render-worker-wake-and-sparse-queue-timing.patch'
OPTIONS = ['/O2', '/Oy-', '/MT', '/TC']
PREFIX = 'COH_CLIENT_RENDER_QUEUE_V1 '


def digest(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def hostile_macros():
    return '''
#define printf coh_rq_poison_printf
#define vsnprintf(a,b,c,d) coh_rq_poison_formatter
#define fflush(a) coh_rq_poison_flush
#define FILE coh_rq_poison_file
'''


def restored_macros():
    return '''
#define RQ_STRING_INNER(a) #a
#define RQ_STRING(a) RQ_STRING_INNER(a)
static void check_macros(void) {
    assert(!strcmp(RQ_STRING(printf),"coh_rq_poison_printf"));
    assert(!strcmp(RQ_STRING(vsnprintf(a,b,c,d)),"coh_rq_poison_formatter"));
    assert(!strcmp(RQ_STRING(fflush(a)),"coh_rq_poison_flush"));
    assert(!strcmp(RQ_STRING(FILE),"coh_rq_poison_file"));
}
#undef printf
#undef vsnprintf
#undef fflush
#undef FILE
'''


def harness(production=False):
    prefix = '''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
void external_phase(int phase,int begin);
'''
    if not production:
        prefix += r'''
static const char *environment;
static double wall;
static unsigned int wall_queries,environment_queries,emissions;
static int fail_wall;
static char last_line[8192];
const char *cohRqTestEnvironment(void) {++environment_queries;return environment;}
int cohRqTestWall(double *value) {++wall_queries;*value=wall;return !fail_wall;}
void cohRqTestEmit(const char *line) {
    assert(strlen(line)<sizeof(last_line) && !strchr(line,'\n'));
    strcpy(last_line,line);++emissions;
}
#define COH_RENDER_QUEUE_TEST 1
'''
    prefix += '#define COH_RQ_IMPLEMENTATION 1\n'
    common = hostile_macros() + (ROOT / HEADER).read_text() + restored_macros()
    if production:
        tail = r'''
#ifdef _WIN64
#error Genuine queue qualification must target Win32
#endif
static volatile LONG concurrent_ready;
static HANDLE concurrent_start;
static CohRqQueueSnapshot queue_snapshot={100,20,20,0,80,0,0,0,0,0};
static void production_frame(void) {
    cohRqMainBegin(1);
    external_phase(COH_RQ_SETUP,1);Sleep(2);external_phase(COH_RQ_SETUP,0);
    external_phase(COH_RQ_SORT,1);Sleep(2);external_phase(COH_RQ_SORT,0);
    external_phase(COH_RQ_DRAW,1);Sleep(2);external_phase(COH_RQ_DRAW,0);
    external_phase(COH_RQ_DRAW,1);Sleep(2);external_phase(COH_RQ_DRAW,0);
    cohRqMainEnd(1,&queue_snapshot);
}
static DWORD WINAPI observer_thread(void *unused) {
    double now;
    (void)unused;assert(!coh_rq_stream.initialized);
    InterlockedIncrement(&concurrent_ready);
    assert(WaitForSingleObject(concurrent_start,10000)==WAIT_OBJECT_0);
    production_frame();
    assert(coh_rq_stream.sampled_frames==1 && coh_rq_stream.gameplay_frames==1);
    assert(coh_rq_stream.metrics[COH_RQ_SETUP].maximum>0);
    assert(coh_rq_stream.metrics[COH_RQ_DRAW].maximum>0);
    assert(cohRqWall(&now));coh_rq_stream.window_start=now-COH_RQ_REPORT_MS;
    cohRqReport(now,&queue_snapshot);assert(coh_rq_stream.reports==1);
    return 0;
}
int main(void) {
    HANDLE threads[4];unsigned int i;double now;DWORD result;
    check_macros();
    assert(_putenv_s("COH_CLIENT_RENDER_QUEUE","0")==0);
    production_frame();assert(!coh_rq_stream.enabled && !coh_rq_stream.window_open);
    assert(_putenv_s("COH_CLIENT_RENDER_QUEUE","1")==0);
    production_frame();assert(!coh_rq_stream.enabled);
    memset(&coh_rq_stream,0,sizeof(coh_rq_stream));production_frame();
    assert(coh_rq_stream.metrics[COH_RQ_SETUP].maximum>0);
    assert(coh_rq_stream.metrics[COH_RQ_SORT].maximum>0);
    assert(coh_rq_stream.metrics[COH_RQ_DRAW].maximum>0);
    for(i=1;i<32;++i) production_frame();
    assert(coh_rq_stream.sampled_frames==1 && coh_rq_stream.gameplay_frames==32);
    assert(cohRqWall(&now));coh_rq_stream.window_start=now-COH_RQ_REPORT_MS;
    cohRqReport(now,&queue_snapshot);assert(coh_rq_stream.reports==1);
    concurrent_start=CreateEvent(NULL,TRUE,FALSE,NULL);assert(concurrent_start);
    for(i=0;i<4;++i) {threads[i]=CreateThread(NULL,0,observer_thread,NULL,0,NULL);assert(threads[i]);}
    while(concurrent_ready!=4) Sleep(1);
    assert(SetEvent(concurrent_start));
    assert(WaitForMultipleObjects(4,threads,TRUE,10000)==WAIT_OBJECT_0);
    for(i=0;i<4;++i) {assert(GetExitCodeThread(threads[i],&result)&&result==0);CloseHandle(threads[i]);}
    CloseHandle(concurrent_start);assert(coh_rq_stream.reports==1);
    puts("WIN32_QUEUE_REAL_QPC_SHARED_TLS_SPARSE_PHASE_JSON_PASS");return 0;
}
'''
    else:
        tail = r'''
static CohRqQueueSnapshot queue_snapshot={123,20,19,1,103,2,7,1,9.5,6.5};
static void reset(const char *flag) {
    memset(&coh_rq_stream,0,sizeof(coh_rq_stream));environment=flag;wall=0;
    wall_queries=environment_queries=emissions=0;fail_wall=0;last_line[0]=0;
}
static void main_frame(double start) {
    wall=start;cohRqMainBegin(1);
    wall=start+2;external_phase(COH_RQ_SETUP,1);wall=start+12;external_phase(COH_RQ_SETUP,0);
    wall=start+15;external_phase(COH_RQ_SORT,1);wall=start+35;external_phase(COH_RQ_SORT,0);
    wall=start+40;external_phase(COH_RQ_DRAW,1);wall=start+50;external_phase(COH_RQ_DRAW,0);
    wall=start+55;external_phase(COH_RQ_DRAW,1);wall=start+85;external_phase(COH_RQ_DRAW,0);
    wall=start+100;cohRqMainEnd(1,&queue_snapshot);
}
int main(void) {
    const char *flags[]={NULL,"","0","01","true","1 "};unsigned int i,j,before;
    CohRqQueueSnapshot q;CohRqMetricData metric;char line[COH_RQ_LINE_BYTES];size_t length;
    check_macros();
    reset("1");cohRqMainBegin(0);cohRqMainEnd(0,NULL);
    assert(!environment_queries && !wall_queries && !coh_rq_stream.initialized);
    for(i=0;i<sizeof(flags)/sizeof(flags[0]);++i) {
        reset(flags[i]);for(j=0;j<1000;++j) main_frame(j*100.0);
        assert(!wall_queries && !emissions && environment_queries==1);
        environment="1";main_frame(100000);assert(!wall_queries && environment_queries==1);
    }
    reset("1");main_frame(0);
    assert(wall_queries==10 && coh_rq_stream.gameplay_frames==1 && coh_rq_stream.sampled_frames==1);
    assert(coh_rq_stream.metrics[COH_RQ_SETUP].sum==10);
    assert(coh_rq_stream.metrics[COH_RQ_SORT].sum==20);
    assert(coh_rq_stream.metrics[COH_RQ_DRAW].sum==40);
    for(i=1;i<64;++i) {
        before=wall_queries;main_frame(i*100.0);
        assert(wall_queries==before+(i==32?10:0));
    }
    assert(!emissions && coh_rq_stream.sampled_frames==2);
    before=wall_queries;main_frame(10000);assert(wall_queries==before+10);
    assert(emissions==1 && coh_rq_stream.reports==1);puts(last_line);
    for(i=1;i<COH_RQ_MAX_REPORTS;++i) {wall+=10000;cohRqReport(wall,&queue_snapshot);}
    assert(!coh_rq_stream.enabled && coh_rq_stream.reports==COH_RQ_MAX_REPORTS);
    before=wall_queries;main_frame(wall);assert(wall_queries==before && emissions==120);
    /* Nested loading/ordinary calls cannot overwrite an outer sample. */
    reset("1");cohRqMainBegin(1);wall=2;external_phase(COH_RQ_SETUP,1);before=wall_queries;
    wall=3;cohRqMainBegin(0);external_phase(COH_RQ_DRAW,1);
    wall=4;cohRqMainBegin(1);external_phase(COH_RQ_SORT,1);
    wall=8;external_phase(COH_RQ_SORT,0);cohRqMainEnd(1,NULL);
    wall=10;external_phase(COH_RQ_DRAW,0);cohRqMainEnd(0,NULL);
    assert(wall_queries==before && coh_rq_stream.frame_open && !coh_rq_stream.suppress_depth);
    wall=20;external_phase(COH_RQ_SETUP,0);wall=30;cohRqMainEnd(1,&queue_snapshot);
    assert(coh_rq_stream.metrics[COH_RQ_SETUP].sum==18);
    assert(coh_rq_stream.metrics[COH_RQ_SORT].sum==0 && coh_rq_stream.metrics[COH_RQ_DRAW].sum==0);
    /* An incomplete sampled frame contributes no phase or gameplay count. */
    reset("1");cohRqMainBegin(1);wall=1;external_phase(COH_RQ_SETUP,1);
    wall=10000;cohRqMainEnd(1,&queue_snapshot);
    assert(emissions==1 && coh_rq_stream.enabled && !coh_rq_stream.metrics[0].count);
    assert(strstr(last_line,"\"incomplete_frames\":1") && strstr(last_line,"\"metrics\":{}"));puts(last_line);
    reset("1");cohRqMainBegin(1);external_phase(COH_RQ_SETUP,1);
    external_phase(COH_RQ_SORT,1);wall=10;cohRqMainEnd(1,&queue_snapshot);
    assert(coh_rq_stream.incomplete_frames==1 && !coh_rq_stream.sampled_frames);
    for(i=1;i<32;++i) main_frame(10+i*100.0);
    assert(coh_rq_stream.gameplay_frames==31 && !coh_rq_stream.sampled_frames);
    main_frame(5000);assert(coh_rq_stream.sampled_frames==1 && coh_rq_stream.metrics[0].count==1);
    reset("1");cohRqMainBegin(1);external_phase(COH_RQ_DRAW,0);
    wall=10;cohRqMainEnd(1,&queue_snapshot);assert(coh_rq_stream.incomplete_frames==1);
    reset("1");cohRqMainBegin(1);external_phase(-1,1);
    wall=10;cohRqMainEnd(1,&queue_snapshot);assert(coh_rq_stream.incomplete_frames==1);
    /* Clock failures and overflow stop only diagnostics. */
    reset("1");fail_wall=1;main_frame(0);assert(!coh_rq_stream.enabled && !emissions);
    reset("1");main_frame(10000);main_frame(500);assert(coh_rq_stream.enabled);
    for(i=2;i<32;++i) main_frame(500+i*100.0);
    main_frame(1);assert(!coh_rq_stream.enabled && !emissions);
    reset("1");wall=NAN;cohRqMainBegin(1);assert(!coh_rq_stream.enabled);
    reset("1");wall=INFINITY;cohRqMainBegin(1);assert(!coh_rq_stream.enabled);
    reset("1");wall=-1;cohRqMainBegin(1);assert(!coh_rq_stream.enabled);
    reset("1");cohRqMainBegin(1);coh_rq_stream.suppress_depth=UINT_MAX;
    cohRqMainBegin(0);assert(!coh_rq_stream.enabled && !coh_rq_stream.suppress_depth);
    reset("1");main_frame(0);coh_rq_stream.gameplay_frames=UINT_MAX;
    main_frame(100);assert(!coh_rq_stream.enabled && !emissions);
    reset("1");main_frame(0);coh_rq_stream.metrics[0].count=UINT_MAX;
    for(i=1;i<32;++i) main_frame(i*100.0);
    main_frame(4000);assert(!coh_rq_stream.enabled && !emissions);
    memset(&metric,0,sizeof(metric));cohRqAdd(&metric,16);cohRqAdd(&metric,16.1);
    cohRqAdd(&metric,101);cohRqAdd(&metric,120001);
    assert(cohRqQuantile(&metric,50)==33 && cohRqQuantile(&metric,95)==-1);
    assert(metric.histogram[0]==1 && metric.histogram[1]==1 && metric.histogram[6]==1
        && metric.histogram[21]==1);
    length=COH_RQ_LINE_BYTES-1;assert(!cohRqAppend(line,&length,"overflow"));
    /* Snapshot types are fixed C fields; enforce finite clocks, conservation
     * and monotonic cumulative ownership before an emitted JSON row. */
    reset("1");assert(cohRqSnapshotValid(&queue_snapshot));
    q=queue_snapshot;q.wake_signal_failures=2;assert(!cohRqSnapshotValid(&q));
    q=queue_snapshot;q.pending_commands=124;assert(!cohRqSnapshotValid(&q));
    q=queue_snapshot;q.ring_waits=8;assert(!cohRqSnapshotValid(&q));
    q=queue_snapshot;q.ring_wait_clock_failures=3;assert(!cohRqSnapshotValid(&q));
    q=queue_snapshot;q.ring_wait_wall_ms=NAN;assert(!cohRqSnapshotValid(&q));
    q=queue_snapshot;q.ring_wait_max_ms=10;assert(!cohRqSnapshotValid(&q));
    coh_rq_stream.last_snapshot=queue_snapshot;coh_rq_stream.have_snapshot=1;
    q=queue_snapshot;--q.commands;assert(!cohRqSnapshotValid(&q));
    reset("1");main_frame(0);wall=10000;cohRqReport(wall,NULL);
    assert(!coh_rq_stream.enabled && !emissions);
    reset("1");main_frame(0);q=queue_snapshot;q.commands=UINT64_MAX;
    q.armed_observations=q.wake_signals=q.wake_signal_failures=UINT64_MAX;
    wall=10000;cohRqReport(wall,&q);assert(emissions==1 && coh_rq_stream.enabled);
    assert(strstr(last_line,"\"queue_counters_saturated\":true"));puts(last_line);
    puts("QUEUE_SPARSE_PHASES_COUNTER_CONSERVATION_BOUNDS_DISABLED_CLOCK_PASS");return 0;
}
'''
    return prefix + common + tail


def helper(production=False):
    prefix = '' if production else '''
const char *cohRqTestEnvironment(void);
int cohRqTestWall(double *value);
void cohRqTestEmit(const char *line);
#define COH_RENDER_QUEUE_TEST 1
'''
    return prefix + (ROOT / HEADER).read_text() + '''
void external_phase(int phase,int begin) {if(begin)cohRqPhaseBegin(phase);else cohRqPhaseEnd(phase);}
'''


def compile_harness(directory, windows=False, production=False):
    directory = Path(directory)
    source = directory / ('queue-production.c' if production else 'queue.c')
    other = directory / ('queue-production-helper.c' if production else 'queue-helper.c')
    source.write_bytes(harness(production).encode())
    other.write_bytes(helper(production).encode())
    if os.name == 'nt':
        compiler = shutil.which('cl')
        if not compiler:
            raise ValueError('Real Win32 MSVC required')
        binary = source.with_suffix('.exe')
        command = [compiler, *OPTIONS, '/nologo', str(source), str(other), '/Fe:' + str(binary)]
    else:
        if windows or production:
            raise ValueError('Formal queue qualification requires real Win32 MSVC')
        compiler = shutil.which('cc') or shutil.which('gcc')
        if not compiler:
            raise ValueError('C compiler required')
        binary = source.with_suffix('')
        command = [compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
            str(source), str(other), '-o', str(binary)]
    try:
        subprocess.run(command, cwd=directory, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        raise RuntimeError('Queue fixture compilation failed:\n' +
            (error.stdout or '') + (error.stderr or '')) from error
    if windows and file_record(binary)['pe_machine'] != 332:
        raise ValueError('Real queue proof compiler must target Win32')
    return binary


def records(output):
    return [json.loads(line[len(PREFIX):]) for line in output.splitlines() if line.startswith(PREFIX)]


def run_checks(binary, production=False):
    try:
        output = subprocess.check_output([str(binary)], text=True, stderr=subprocess.STDOUT, timeout=30)
    except subprocess.CalledProcessError as error:
        raise RuntimeError('Queue fixture execution failed:\n' + error.output) from error
    rows = records(output)
    for row in rows:
        assert type(row['format']) is int and row['format'] == 1
        assert row['event'] == 'window' and row['scope'] == 'gameplay'
        assert row['queue_scope'] == 'process_cumulative' and row['sample_interval'] == 32
        assert row['window_ms'] >= 10000 and len(row['bucket_upper_ms']) == 22
        assert type(row['queue_counters_saturated']) is bool
        assert all(type(row['queue_counters'][name]) is int for name in (
            'commands', 'armed_observations', 'wake_signals', 'wake_signal_failures',
            'pending_commands', 'ring_waits', 'ring_wait_iterations', 'ring_wait_clock_failures'))
        for metric in row['metrics'].values():
            assert metric['count'] == row['sampled_frames']
            assert len(metric['histogram']) == 22 and sum(metric['histogram']) == metric['count']
    if production:
        assert 'WIN32_QUEUE_REAL_QPC_SHARED_TLS_SPARSE_PHASE_JSON_PASS' in output
        assert len(rows) == 5
        assert sorted(row['gameplay_frames'] for row in rows) == [1, 1, 1, 1, 32]
        assert all(row['sampled_frames'] == 1 and row['incomplete_frames'] == 0 for row in rows)
        assert all(metric['mean_ms'] > 0 for row in rows for metric in row['metrics'].values())
    else:
        assert 'QUEUE_SPARSE_PHASES_COUNTER_CONSERVATION_BOUNDS_DISABLED_CLOCK_PASS' in output
        assert len(rows) == 3
        ordinary, partial, saturated = rows
        assert ordinary['gameplay_frames'] == 65 and ordinary['sampled_frames'] == 3
        assert ordinary['incomplete_frames'] == 0 and not ordinary['queue_counters_saturated']
        assert ordinary['metrics']['setup_wall']['mean_ms'] == 10
        assert ordinary['metrics']['sort_wall']['mean_ms'] == 20
        assert ordinary['metrics']['draw_wall']['mean_ms'] == 40
        assert ordinary['queue_counters']['ring_wait_wall_ms'] == 9.5
        assert partial['gameplay_frames'] == partial['sampled_frames'] == 0
        assert partial['incomplete_frames'] == 1 and partial['metrics'] == {}
        assert saturated['queue_counters_saturated']
        assert saturated['queue_counters']['commands'] == 2**64-1
    return rows


def expected_checks():
    import test_client_render_queue_worker as worker
    return {'format': 1, 'status': 'passed', 'platform': 'windows', 'architecture': 'Win32',
        'configuration': 'OptDebug', 'compiler_options': OPTIONS,
        'patch_sha256': digest(ROOT / PATCH), 'header_sha256': digest(ROOT / HEADER),
        'harness_sha256': hashlib.sha256(harness().encode()).hexdigest(),
        'helper_sha256': hashlib.sha256(helper().encode()).hexdigest(),
        'production_harness_sha256': hashlib.sha256(harness(True).encode()).hexdigest(),
        'production_helper_sha256': hashlib.sha256(helper(True).encode()).hexdigest(),
        'worker_source_proof_sha256': hashlib.sha256(json.dumps(source_checks(),
            sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        'worker_source_bound_interleavings_verified': True,
        'worker_queue_fixture': worker.worker_checks(),
        'main_gameplay_setup_sort_and_repeated_draw_aggregation_verified': True,
        'phase_clocks_one_in_thirty_two_frames_verified': True,
        'unsampled_and_disabled_without_wall_clocks_verified': True,
        'nested_gfx_suppression_and_partial_frame_discard_verified': True,
        'producer_snapshot_conservation_monotonicity_and_saturation_verified': True,
        'bounded_ten_second_windows_and_120_report_limit_verified': True,
        'invalid_clock_overflow_and_logging_bounds_nonfatal_verified': True,
        'shared_translation_unit_tls_isolation_verified': True,
        'genuine_win32_qpc_and_concurrent_json_verified': True,
        'native_crt_macro_isolation_and_restoration_verified': True,
        'queue_counters_include_non_gameplay_work': True,
        'phase_wall_is_not_gpu_time': True, 'physical_fps_gain_validated': False}


def typed_equal(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(typed_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(typed_equal(a, b) for a, b in zip(left, right))
    return left == right


def validate_windows_checks(checks):
    if not typed_equal(checks, expected_checks()):
        raise ValueError('Exact source-bound genuine Win32 render queue qualification required')
    return checks


validate_checks = validate_windows_checks


def source_checks():
    import test_client_render_queue_source as source
    proof = source.source_proof()
    if not proof:
        raise ValueError('Source-bound render queue worker interleaving proof required')
    return proof


def windows_receipt(output):
    import test_client_render_queue_worker as worker
    if os.name != 'nt':
        raise ValueError('Formal queue qualification requires real Win32 MSVC')
    source_checks()
    with tempfile.TemporaryDirectory(prefix='coh-win32-queue-') as temporary:
        run_checks(compile_harness(temporary, windows=True))
        run_checks(compile_harness(temporary, windows=True, production=True), production=True)
    worker.windows_receipt()
    document = expected_checks()
    validate_windows_checks(document)
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('Fresh queue Win32 proof required')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2) + '\n')
    return document


class QueueNativeTests(unittest.TestCase):
    def test_actual_shared_tls_sparse_phases_and_producer_snapshots(self):
        with tempfile.TemporaryDirectory(prefix='coh-queue-native-') as directory:
            run_checks(compile_harness(directory))

    def test_genuine_qualification_rejects_source_platform_types_and_claims(self):
        good = expected_checks()
        self.assertEqual(validate_windows_checks(good), good)
        for name, value in good.items():
            wrong = dict(good);wrong[name] = None
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_windows_checks(wrong)
            if type(value) in (int, bool):
                wrong = dict(good);wrong[name] = float(value) if type(value) is int else int(value)
                with self.subTest(name=name, mutation='JSON_type'), self.assertRaises(ValueError):
                    validate_windows_checks(wrong)

    def test_formal_qualification_refuses_host_simulation(self):
        with tempfile.TemporaryDirectory(prefix='coh-queue-formal-') as directory:
            path = Path(directory) / 'proof.json'
            if os.name == 'nt':
                self.assertEqual(windows_receipt(path), expected_checks())
            else:
                with self.assertRaisesRegex(ValueError, 'real Win32'):
                    windows_receipt(path)
                self.assertFalse(path.exists())

    def test_nested_actual_worker_proof_cannot_use_python_numeric_type_equivalence(self):
        good = expected_checks()
        for name, value in good['worker_queue_fixture'].items():
            if type(value) not in (int, bool):
                continue
            wrong = dict(good)
            wrong['worker_queue_fixture'] = dict(good['worker_queue_fixture'])
            wrong['worker_queue_fixture'][name] = float(value) if type(value) is int else int(value)
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_windows_checks(wrong)


if __name__ == '__main__':
    if '--windows-qualify' in sys.argv:
        parser = argparse.ArgumentParser()
        parser.add_argument('--windows-qualify', action='store_true')
        parser.add_argument('--output', required=True, type=Path)
        args = parser.parse_args()
        windows_receipt(args.output)
    else:
        unittest.main()
