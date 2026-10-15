"""Execute sampled pipeline clocks; qualify genuine Win32 shared TLS/clock code."""
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

HEADER = 'database/client-render-pipeline/overlay/Game/src/cohClientRenderPipeline.h'
PATCH = 'patches/client-render-pipeline/0001-render-worker-wake-and-focused-timing.patch'
OPTIONS = ['/O2', '/Oy-', '/MT', '/TC']
PREFIX = 'COH_CLIENT_RENDER_PIPELINE_V1 '


def digest(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def hostile_macros():
    return '''
#define printf coh_rp_poison_printf
#define vsnprintf(a,b,c,d) coh_rp_poison_formatter
#define fflush(a) coh_rp_poison_flush
#define FILE coh_rp_poison_file
'''


def restored_macros():
    return '''
#define RP_STRING_INNER(a) #a
#define RP_STRING(a) RP_STRING_INNER(a)
static void check_macros(void) {
    assert(!strcmp(RP_STRING(printf),"coh_rp_poison_printf"));
    assert(!strcmp(RP_STRING(vsnprintf(a,b,c,d)),"coh_rp_poison_formatter"));
    assert(!strcmp(RP_STRING(fflush(a)),"coh_rp_poison_flush"));
    assert(!strcmp(RP_STRING(FILE),"coh_rp_poison_file"));
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
void external_phase(int metric,int begin);
void external_command(int command,int begin);
'''
    if not production:
        prefix += r'''
static const char *environment;
static double wall,cpu;
static unsigned int wall_queries,cpu_queries,environment_queries,emissions;
static int fail_wall,fail_cpu,emit_lines;
static char last_line[8192];
const char *cohRpTestEnvironment(void) {++environment_queries;return environment;}
int cohRpTestWall(double *value) {++wall_queries;*value=wall;return !fail_wall;}
int cohRpTestCpu(double *value) {++cpu_queries;*value=cpu;return !fail_cpu;}
void cohRpTestEmit(const char *line) {
    assert(strlen(line)<sizeof(last_line) && !strchr(line,'\n'));
    strcpy(last_line,line);++emissions;if(emit_lines)puts(line);
}
#define COH_RENDER_PIPELINE_TEST 1
'''
    prefix += '#define COH_RP_IMPLEMENTATION 1\n'
    common = hostile_macros() + (ROOT / HEADER).read_text() + restored_macros()
    if production:
        tail = r'''
#ifdef _WIN64
#error Genuine pipeline qualification must target Win32
#endif
static volatile LONG concurrent_ready;
static HANDLE concurrent_start;
static DWORD WINAPI renderer_thread(void *unused) {
    double now;unsigned int before;
    (void)unused;
    assert(!coh_rp_stream.initialized);
    cohRpRendererBegin();assert(coh_rp_stream.renderer==1 && coh_rp_stream.sampled);
    InterlockedIncrement(&concurrent_ready);
    assert(WaitForSingleObject(concurrent_start,10000)==WAIT_OBJECT_0);
    external_command(41,1);Sleep(2);external_command(41,0);
    Sleep(2);external_command(42,1);Sleep(2);external_command(42,0);
    cohRpRendererEnd();
    assert(coh_rp_stream.metrics[COH_RP_COMMAND].count==1);
    assert(coh_rp_stream.metrics[COH_RP_COMMAND].maximum>0);
    assert(coh_rp_stream.metrics[COH_RP_GAP].maximum>0);
    before=coh_rp_stream.sampled_batches;
    cohRpRendererBegin();assert(!coh_rp_stream.sampled);
    external_command(41,1);Sleep(1);external_command(41,0);cohRpRendererEnd();
    assert(coh_rp_stream.sampled_batches==before);
    assert(cohRpWall(&now));coh_rp_stream.window_start=now-COH_RP_REPORT_MS;
    cohRpReport(now);assert(coh_rp_stream.reports==1 && coh_rp_stream.sampled_commands==0);
    return 0;
}
int main(void) {
    HANDLE threads[4];unsigned int i;double now;DWORD result;
    check_macros();
    assert(_putenv_s("COH_CLIENT_RENDER_PIPELINE","0")==0);
    cohRpMainBegin(1);assert(!coh_rp_stream.enabled);
    memset(&coh_rp_stream,0,sizeof(coh_rp_stream));
    assert(_putenv_s("COH_CLIENT_RENDER_PIPELINE","1")==0);
    cohRpMainBegin(1);cohRpPhaseBegin(COH_RP_FINISH);
    external_phase(COH_RP_FLUSH,1);Sleep(2);external_phase(COH_RP_FLUSH,0);
    cohRpPhaseEnd(COH_RP_FINISH);cohRpMainEnd(1);
    assert(coh_rp_stream.metrics[COH_RP_FLUSH].maximum>0);
    assert(coh_rp_stream.metrics[COH_RP_FINISH].maximum>=coh_rp_stream.metrics[COH_RP_FLUSH].maximum);
    assert(cohRpWall(&now));coh_rp_stream.window_start=now-COH_RP_REPORT_MS;
    cohRpReport(now);assert(coh_rp_stream.reports==1 && coh_rp_stream.renderer==0);
    concurrent_start=CreateEvent(NULL,TRUE,FALSE,NULL);assert(concurrent_start);
    for(i=0;i<4;++i) {threads[i]=CreateThread(NULL,0,renderer_thread,NULL,0,NULL);assert(threads[i]);}
    while(concurrent_ready!=4)Sleep(1);
    assert(SetEvent(concurrent_start));
    assert(WaitForMultipleObjects(4,threads,TRUE,10000)==WAIT_OBJECT_0);
    for(i=0;i<4;++i) {assert(GetExitCodeThread(threads[i],&result)&&result==0);CloseHandle(threads[i]);}
    CloseHandle(concurrent_start);
    assert(coh_rp_stream.reports==1 && coh_rp_stream.renderer==0);
    puts("WIN32_PIPELINE_QPC_THREAD_CPU_SHARED_TLS_CONCURRENT_JSON_PASS");return 0;
}
'''
    else:
        tail = r'''
static void reset(const char *flag) {
    memset(&coh_rp_stream,0,sizeof(coh_rp_stream));environment=flag;wall=cpu=0;
    wall_queries=cpu_queries=environment_queries=emissions=0;
    fail_wall=fail_cpu=emit_lines=0;last_line[0]=0;
}
static void main_frame(double start) {
    wall=start;cohRpMainBegin(1);
    wall=start+2;cohRpPhaseBegin(COH_RP_AUX);wall=start+12;cohRpPhaseEnd(COH_RP_AUX);
    wall=start+13;cohRpPhaseBegin(COH_RP_MAINVIEW);wall=start+43;cohRpPhaseEnd(COH_RP_MAINVIEW);
    wall=start+44;cohRpPhaseBegin(COH_RP_SUN);wall=start+48;cohRpPhaseEnd(COH_RP_SUN);
    wall=start+50;cohRpPhaseBegin(COH_RP_POST);wall=start+58;cohRpPhaseEnd(COH_RP_POST);
    wall=start+60;cohRpPhaseBegin(COH_RP_UI);wall=start+70;cohRpPhaseEnd(COH_RP_UI);
    wall=start+75;cohRpPhaseBegin(COH_RP_FINISH);
    wall=start+80;external_phase(COH_RP_FLUSH,1);
    wall=start+90;external_phase(COH_RP_FLUSH,0);
    wall=start+95;cohRpPhaseEnd(COH_RP_FINISH);
    wall=start+100;cpu+=4;cohRpMainEnd(1);
}
static void render_batch(double start) {
    wall=start;cohRpRendererBegin();
    external_command(0,1);wall=start+5;external_command(0,0);
    wall=start+10;external_command(17,1);wall=start+25;external_command(17,0);
    wall=start+40;external_command(999,1);wall=start+60;external_command(999,0);
    wall=start+65;cpu+=2;cohRpRendererEnd();
}
int main(void) {
    const char *flags[]={NULL,"","0","01","true","1 "};unsigned int i,j,before;
    CohRpMetricData metric;
    check_macros();
    reset("1");cohRpMainBegin(0);cohRpMainEnd(0);
    assert(!environment_queries && !wall_queries && !coh_rp_stream.initialized);
    for(i=0;i<sizeof(flags)/sizeof(flags[0]);++i) {
        reset(flags[i]);for(j=0;j<1000;++j)main_frame(j*100.0);
        assert(!wall_queries && !cpu_queries && !emissions && environment_queries==1);
        environment="1";main_frame(100000);assert(!wall_queries && environment_queries==1);
        reset(flags[i]);for(j=0;j<1000;++j)render_batch(j*100.0);
        assert(!wall_queries && !cpu_queries && !emissions && environment_queries==1);
    }
    reset("1");main_frame(0);
    assert(coh_rp_stream.metrics[COH_RP_GFX].sum==100);
    assert(coh_rp_stream.metrics[COH_RP_AUX].sum==10);
    assert(coh_rp_stream.metrics[COH_RP_MAINVIEW].sum==30);
    assert(coh_rp_stream.metrics[COH_RP_SUN].sum==4);
    assert(coh_rp_stream.metrics[COH_RP_POST].sum==8);
    assert(coh_rp_stream.metrics[COH_RP_UI].sum==10);
    assert(coh_rp_stream.metrics[COH_RP_FINISH].sum==20);
    assert(coh_rp_stream.metrics[COH_RP_FLUSH].sum==10 && cpu_queries==1 && !emissions);
    before=wall_queries;cohRpRendererBegin();external_command(1,1);external_command(1,0);
    cohRpRendererEnd();assert(wall_queries==before);
    for(i=1;i<100;++i)main_frame(i*100.0);
    assert(coh_rp_stream.reports==1 && emissions==1 && cpu_queries==2);
    assert(strstr(last_line,"\"thread_cpu_ms\":400.000"));puts(last_line);
    for(i=1;i<COH_RP_MAX_REPORTS;++i) {wall+=10000;cohRpReport(wall);}
    assert(!coh_rp_stream.enabled && coh_rp_stream.reports==COH_RP_MAX_REPORTS);
    before=wall_queries;main_frame(wall);assert(wall_queries==before);
    /* Child gfx loading/main calls share TLS but must never close or double
     * attribute an outer phase. Queue flush hooks are suppressed as well. */
    reset("1");cohRpMainBegin(1);wall=2;cohRpPhaseBegin(COH_RP_UI);
    before=wall_queries;wall=3;cohRpMainBegin(0);cohRpPhaseBegin(COH_RP_UI);
    wall=4;cohRpMainBegin(1);external_phase(COH_RP_FLUSH,1);
    wall=8;external_phase(COH_RP_FLUSH,0);cohRpMainEnd(1);
    wall=10;cohRpPhaseEnd(COH_RP_UI);cohRpMainEnd(0);
    assert(wall_queries==before && coh_rp_stream.frame_open && !coh_rp_stream.suppress_depth);
    assert(coh_rp_stream.phase_open==(1u<<COH_RP_UI));
    wall=20;cohRpPhaseEnd(COH_RP_UI);wall=30;cohRpMainEnd(1);
    assert(coh_rp_stream.metrics[COH_RP_UI].sum==18);
    assert(coh_rp_stream.metrics[COH_RP_FLUSH].sum==0);
    assert(coh_rp_stream.metrics[COH_RP_GFX].sum==30);
    reset("1");cohRpMainBegin(1);wall=2;cohRpPhaseBegin(COH_RP_MAINVIEW);
    before=wall_queries;cohRpMainBegin(1);cohRpPhaseBegin(COH_RP_MAINVIEW);
    wall=10;cohRpPhaseEnd(COH_RP_MAINVIEW);cohRpMainEnd(1);
    assert(wall_queries==before && coh_rp_stream.frame_open);
    wall=20;cohRpPhaseEnd(COH_RP_MAINVIEW);wall=30;cohRpMainEnd(1);
    assert(coh_rp_stream.metrics[COH_RP_MAINVIEW].sum==18);
    reset("1");cohRpMainBegin(1);coh_rp_stream.suppress_depth=UINT_MAX;
    cohRpMainBegin(0);assert(!coh_rp_stream.enabled && !coh_rp_stream.suppress_depth);
    reset("1");render_batch(0);
    assert(coh_rp_stream.metrics[COH_RP_BATCH].sum==65);
    assert(coh_rp_stream.metrics[COH_RP_COMMAND].sum==40);
    assert(coh_rp_stream.metrics[COH_RP_GAP].sum==25);
    assert(coh_rp_stream.sampled_batches==1 && coh_rp_stream.sampled_commands==3 && cpu_queries==1);
    for(i=1;i<16;++i) {
        before=wall_queries;render_batch(i*100.0);assert(wall_queries==before+2);
    }
    assert(coh_rp_stream.metrics[COH_RP_COMMAND].count==1);
    before=wall_queries;render_batch(1600);
    assert(wall_queries==before+8 && coh_rp_stream.sampled_batches==2);
    assert(coh_rp_stream.sampled_commands==6 && coh_rp_stream.metrics[COH_RP_BATCH].count==17);
    wall=10000;cohRpReport(wall);assert(emissions==1 && cpu_queries==2);puts(last_line);
    /* Sampling continues across report windows; zero-sample metrics are absent. */
    render_batch(10100);wall=20000;cohRpReport(wall);assert(emissions==2);
    assert(!strstr(last_line,"\"renderer_command_wall\""));puts(last_line);
    memset(&metric,0,sizeof(metric));cohRpAdd(&metric,16);cohRpAdd(&metric,16.1);
    cohRpAdd(&metric,101);cohRpAdd(&metric,120001);
    assert(cohRpQuantile(&metric,50)==33 && cohRpQuantile(&metric,95)==-1);
    assert(metric.histogram[0]==1 && metric.histogram[1]==1 && metric.histogram[6]==1
        && metric.histogram[21]==1);
    metric.count=UINT_MAX;cohRpAdd(&metric,1);assert(metric.count==UINT_MAX);
    assert(cohRpIncrement(UINT_MAX)==UINT_MAX && cohRpSum(UINT_MAX-1,4)==UINT_MAX);
    reset("1");fail_cpu=1;main_frame(0);main_frame(10000);
    assert(strstr(last_line,"\"thread_cpu_ms\":null") && coh_rp_stream.enabled);
    reset("1");fail_wall=1;main_frame(0);
    assert(!coh_rp_stream.enabled && !cpu_queries && !coh_rp_stream.frame_open);
    reset("1");main_frame(10000);main_frame(500);assert(!coh_rp_stream.enabled);
    reset("1");cohRpRendererBegin();external_command(1,1);wall=2;fail_wall=1;
    external_command(1,0);assert(!coh_rp_stream.enabled && !coh_rp_stream.command_open);
    before=wall_queries;render_batch(100);assert(wall_queries==before);
    reset("1");cohRpRendererBegin();external_command(1,1);wall=2;external_command(2,0);
    assert(!coh_rp_stream.enabled && !coh_rp_stream.frame_open);
    reset("1");cohRpRendererBegin();external_command(1,1);wall=2;external_command(1,1);
    assert(!coh_rp_stream.enabled && !coh_rp_stream.command_open);
    reset("1");cohRpMainBegin(1);cohRpPhaseBegin(COH_RP_UI);wall=2;cohRpPhaseBegin(COH_RP_UI);
    assert(!coh_rp_stream.enabled && !coh_rp_stream.phase_open);
    reset("1");cohRpMainBegin(1);cohRpPhaseBegin(COH_RP_UI);wall=2;cohRpMainEnd(1);
    assert(!coh_rp_stream.enabled && !coh_rp_stream.frame_open);
    reset("1");cohRpRendererBegin();external_command(1,1);wall=2;cohRpRendererEnd();
    assert(!coh_rp_stream.enabled && !coh_rp_stream.command_open);
    reset("1");cohRpRendererBegin();external_command(1,1);wall=2;cohRpRendererBegin();
    assert(coh_rp_stream.incomplete==1 && !coh_rp_stream.command_open);
    wall=3;cohRpRendererEnd();
    assert(coh_rp_stream.metrics[COH_RP_BATCH].count==1 && !coh_rp_stream.sampled_batches);
    reset("1");main_frame(0);
    for(i=0;i<COH_RP_METRICS;++i) {
        CohRpMetricData *m=&coh_rp_stream.metrics[i];
        m->count=UINT_MAX;m->sum=4294967295.0*120001;m->maximum=120001;
        for(j=0;j<COH_RP_BUCKETS;++j)m->histogram[j]=UINT_MAX;
    }
    wall=10000;cohRpReport(wall);
    assert(coh_rp_stream.enabled && strlen(last_line)<COH_RP_LINE_BYTES);
    puts("PIPELINE_AGGREGATION_SAMPLING_SHARED_TLS_BOUNDS_DISABLED_CLOCK_PASS");return 0;
}
'''
    return prefix + common + tail


def helper(production=False):
    prefix = '' if production else '''
const char *cohRpTestEnvironment(void);
int cohRpTestWall(double *value);
int cohRpTestCpu(double *value);
void cohRpTestEmit(const char *line);
#define COH_RENDER_PIPELINE_TEST 1
'''
    return prefix + (ROOT / HEADER).read_text() + '''
void external_phase(int metric,int begin) {if(begin)cohRpPhaseBegin(metric);else cohRpPhaseEnd(metric);}
void external_command(int command,int begin) {if(begin)cohRpCommandBegin(command);else cohRpCommandEnd(command);}
'''


def compile_harness(directory, windows=False, production=False):
    directory = Path(directory)
    source = directory / ('pipeline-production.c' if production else 'pipeline.c')
    other = directory / ('pipeline-production-helper.c' if production else 'pipeline-helper.c')
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
            raise ValueError('Formal pipeline qualification requires real Win32 MSVC')
        compiler = shutil.which('cc') or shutil.which('gcc')
        if not compiler:
            raise ValueError('C compiler required')
        binary = source.with_suffix('')
        command = [compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
            str(source), str(other), '-o', str(binary)]
    try:
        subprocess.run(command, cwd=directory, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        raise RuntimeError('Pipeline fixture compilation failed:\n' +
            (error.stdout or '') + (error.stderr or '')) from error
    if windows and file_record(binary)['pe_machine'] != 332:
        raise ValueError('Real pipeline proof compiler must target Win32')
    return binary


def records(output):
    return [json.loads(line[len(PREFIX):]) for line in output.splitlines() if line.startswith(PREFIX)]


def run_checks(binary, production=False):
    try:
        output = subprocess.check_output([str(binary)], text=True, stderr=subprocess.STDOUT, timeout=30)
    except subprocess.CalledProcessError as error:
        raise RuntimeError('Pipeline fixture execution failed:\n' + error.output) from error
    rows = records(output)
    assert all(row['scope'] == ('gameplay' if row['role'] == 'main'
        else 'all_states_independent') for row in rows)
    assert all(len(row['bucket_upper_ms']) == 22 for row in rows)
    assert all(len(metric['histogram']) == 22 for row in rows for metric in row['metrics'].values())
    if production:
        assert 'WIN32_PIPELINE_QPC_THREAD_CPU_SHARED_TLS_CONCURRENT_JSON_PASS' in output
        assert len(rows) == 5 and sum(row['role'] == 'main' for row in rows) == 1
        assert all(row['thread_cpu_ms'] is not None and row['thread_cpu_ms'] >= 0 for row in rows)
        renderers = [row for row in rows if row['role'] == 'renderer']
        assert all(row['sample_interval'] == 16 and row['sampled_batches'] == 1
            and row['sampled_command_count'] == 2 for row in renderers)
    else:
        assert 'PIPELINE_AGGREGATION_SAMPLING_SHARED_TLS_BOUNDS_DISABLED_CLOCK_PASS' in output
        assert len(rows) == 3
        main, renderer, unsampled = rows
        assert main['role'] == 'main' and main['thread_cpu_ms'] == 400
        assert main['metrics']['gfx_wall']['count'] == 100
        assert main['metrics']['gfx_wall']['mean_ms'] == 100
        assert main['metrics']['finish_wall']['mean_ms'] == 20
        assert main['metrics']['queue_flush_wall']['mean_ms'] == 10
        assert all(metric['count'] == 100 for metric in main['metrics'].values())
        assert renderer['role'] == 'renderer' and renderer['sample_interval'] == 16
        assert renderer['sampled_batches'] == 2 and renderer['sampled_command_count'] == 6
        assert renderer['metrics']['renderer_batch_wall']['count'] == 17
        assert renderer['metrics']['renderer_command_wall']['count'] == 2
        assert renderer['metrics']['renderer_command_wall']['mean_ms'] == 40
        assert renderer['metrics']['renderer_queue_gap_wall']['mean_ms'] == 25
        assert unsampled['sampled_batches'] == unsampled['sampled_command_count'] == 0
        assert set(unsampled['metrics']) == {'renderer_batch_wall'}
    return rows


def expected_checks():
    return {'format': 1, 'status': 'passed', 'platform': 'windows', 'architecture': 'Win32',
        'configuration': 'OptDebug', 'compiler_options': OPTIONS,
        'patch_sha256': digest(ROOT / PATCH), 'header_sha256': digest(ROOT / HEADER),
        'harness_sha256': hashlib.sha256(harness().encode()).hexdigest(),
        'helper_sha256': hashlib.sha256(helper().encode()).hexdigest(),
        'production_harness_sha256': hashlib.sha256(harness(True).encode()).hexdigest(),
        'production_helper_sha256': hashlib.sha256(helper(True).encode()).hexdigest(),
        'main_phase_flush_overlap_separation_verified': True,
        'main_gameplay_scope_verified': True,
        'nested_gfx_phase_and_flush_suppression_verified': True,
        'sampled_command_gap_and_batch_separation_verified': True,
        'command_clock_sampling_one_in_sixteen_verified': True,
        'shared_translation_unit_tls_and_thread_isolation_verified': True,
        'report_rate_histogram_counter_saturation_and_limits_verified': True,
        'disabled_without_clock_cpu_or_logging_verified': True,
        'clock_failure_and_incomplete_diagnostics_nonfatal_verified': True,
        'genuine_win32_qpc_thread_cpu_and_concurrent_json_verified': True,
        'native_crt_macro_isolation_and_restoration_verified': True,
        'worker_wake_handshake_source_bound_interleavings_verified': True,
        'thread_cpu_excludes_renderer_workers': True, 'physical_fps_gain_validated': False}


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
        raise ValueError('Exact source-bound genuine Win32 pipeline qualification required')
    return checks


validate_checks = validate_windows_checks


def wake_checks():
    import test_client_render_pipeline_source as source
    proof = source.wake_proof()
    if not proof:
        raise ValueError('Source-bound worker wake interleaving proof required')
    return proof


def windows_receipt(output):
    wake_checks()
    with tempfile.TemporaryDirectory(prefix='coh-win32-pipeline-') as temporary:
        run_checks(compile_harness(temporary, windows=True))
        run_checks(compile_harness(temporary, windows=True, production=True), production=True)
    document = expected_checks()
    validate_windows_checks(document)
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('Fresh pipeline Win32 proof required')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2) + '\n')
    return document


class PipelineNativeTests(unittest.TestCase):
    def test_actual_shared_tls_aggregator_separates_main_phases_sampled_dispatch_and_gap(self):
        with tempfile.TemporaryDirectory(prefix='coh-pipeline-native-') as directory:
            run_checks(compile_harness(directory))

    def test_worker_wake_handshake_source_bound_interleavings(self):
        self.assertTrue(wake_checks())

    def test_genuine_qualification_rejects_changed_source_platform_types_and_claims(self):
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
        with tempfile.TemporaryDirectory(prefix='coh-pipeline-formal-') as directory:
            path = Path(directory) / 'proof.json'
            if os.name == 'nt':
                self.assertEqual(windows_receipt(path), expected_checks())
            else:
                with self.assertRaisesRegex(ValueError, 'real Win32'):
                    windows_receipt(path)
                self.assertFalse(path.exists())


if __name__ == '__main__':
    if '--windows-qualify' in sys.argv:
        parser = argparse.ArgumentParser()
        parser.add_argument('--windows-qualify', action='store_true')
        parser.add_argument('--output', required=True, type=Path)
        args = parser.parse_args()
        windows_receipt(args.output)
    else:
        unittest.main()
