"""Execute the production frame aggregator; qualify real Win32 clocks and TLS."""
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
HEADER = 'database/client-scene-performance/overlay/Game/src/cohClientFrameTiming.h'
PATCH = 'patches/client-scene-performance/0002-native-frame-timing.patch'
OPTIONS = ['/O2', '/Oy-', '/MT', '/TC']
PREFIX = 'COH_CLIENT_FRAME_TIMING_V1 '


def hostile_macros():
    return r'''
/* Actual retained stdtypes/file headers redefine these names. */
#define printf coh_frame_poison_printf
#define vsnprintf(buffer,size,format,args) coh_frame_poison_formatter
#define fflush(file) coh_frame_poison_flush
#define FILE coh_frame_poison_file
'''


def restored_macros():
    return r'''
#define COH_FT_STRING_INNER(value) #value
#define COH_FT_STRING(value) COH_FT_STRING_INNER(value)
static void check_restored_macros(void) {
    assert(!strcmp(COH_FT_STRING(printf),"coh_frame_poison_printf"));
    assert(!strcmp(COH_FT_STRING(vsnprintf(a,b,c,d)),"coh_frame_poison_formatter"));
    assert(!strcmp(COH_FT_STRING(fflush(a)),"coh_frame_poison_flush"));
    assert(!strcmp(COH_FT_STRING(FILE),"coh_frame_poison_file"));
}
#undef printf
#undef vsnprintf
#undef fflush
#undef FILE
'''


def digest(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def harness():
    prefix = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static const char *test_environment;
static double wall,cpu;
static unsigned int wall_queries,cpu_queries,environment_queries,emissions;
static int fail_wall,fail_cpu,emit_lines;
static char last_line[12288];
static const char *cohFtTestEnvironment(void) { environment_queries++;return test_environment; }
static int cohFtTestWall(double *value) { wall_queries++;*value=wall;return !fail_wall; }
static int cohFtTestCpu(double *value) { cpu_queries++;*value=cpu;return !fail_cpu; }
static void cohFtTestEmit(const char *line) {
    assert(strlen(line)<sizeof(last_line));assert(!strchr(line,'\n'));
    strcpy(last_line,line);emissions++;if(emit_lines)puts(line);
}
#define COH_FRAME_TIMING_TEST 1
'''
    tail = r'''
static void reset(const char *flag) {
    memset(&coh_ft_stream,0,sizeof(coh_ft_stream));
    test_environment=flag;wall=cpu=0.0;
    wall_queries=cpu_queries=environment_queries=emissions=0;
    fail_wall=fail_cpu=emit_lines=0;last_line[0]=0;
}
static void frame(int state,int end_state,double start) {
    wall=start;cohFtMainBegin(state);
    wall=start+2;cohFtPhaseBegin(COH_FT_ENGINE_PHASE);
    wall=start+10;cohFtPhaseBegin(COH_FT_SUBMIT_PHASE);
    wall=start+40;cohFtPhaseEnd(COH_FT_SUBMIT_PHASE);
    wall=start+42;cohFtPhaseBegin(COH_FT_PACING_PHASE);
    wall=start+102;cohFtPhaseEnd(COH_FT_PACING_PHASE);
    cohFtPhaseEnd(COH_FT_ENGINE_PHASE);
    wall=start+104;cpu+=4;cohFtMainEnd(end_state);
}
int main(int argc,char **argv) {
    const char *flags[]={NULL,"","0","01","true","1 "};
    unsigned int i,j,before;
    CohFtMetricData metric;
    (void)argc;(void)argv;
    check_restored_macros();
    /* Disabled or inexact flags do not query clocks/CPU, print, or classify. */
    for(i=0;i<sizeof(flags)/sizeof(flags[0]);i++) {
        reset(flags[i]);
        for(j=0;j<1000;j++) {
            frame(COH_FT_GAMEPLAY,COH_FT_GAMEPLAY,j*104.0);
            cohFtPresentBegin();cohFtSwapBegin();cohFtSwapEnd();cohFtPresentEnd();
        }
        assert(!wall_queries&&!cpu_queries&&!emissions&&environment_queries==1);
        test_environment="1";frame(COH_FT_GAMEPLAY,COH_FT_GAMEPLAY,0);
        assert(!wall_queries&&environment_queries==1); /* Flag cached, not polled. */
    }
    reset("1");frame(COH_FT_GAMEPLAY,COH_FT_GAMEPLAY,0);
    assert(coh_ft_stream.data[COH_FT_GAMEPLAY][COH_FT_FRAME].sum==104);
    assert(coh_ft_stream.data[COH_FT_GAMEPLAY][COH_FT_ENGINE].sum==100);
    assert(coh_ft_stream.data[COH_FT_GAMEPLAY][COH_FT_SUBMIT].sum==30);
    assert(coh_ft_stream.data[COH_FT_GAMEPLAY][COH_FT_PACING].sum==60);
    assert(coh_ft_stream.data[COH_FT_GAMEPLAY][COH_FT_WORK].sum==44);
    assert(cpu_queries==1&&!emissions);
    frame(COH_FT_GAMEPLAY,COH_FT_GAMEPLAY,104);
    assert(coh_ft_stream.data[COH_FT_GAMEPLAY][COH_FT_INTERVAL].sum==104);
    before=wall_queries;cohFtPresentBegin();cohFtSwapBegin();cohFtSwapEnd();cohFtPresentEnd();
    assert(wall_queries==before); /* Stream roles cannot share accidental state. */
    reset("1");frame(COH_FT_MENU,COH_FT_MENU,0);
    frame(COH_FT_LOADING,COH_FT_LOADING,104);
    frame(COH_FT_LOADING,COH_FT_GAMEPLAY,208);
    frame(COH_FT_GAMEPLAY,COH_FT_GAMEPLAY,312);
    assert(coh_ft_stream.data[COH_FT_MENU][COH_FT_FRAME].count==1);
    assert(coh_ft_stream.data[COH_FT_LOADING][COH_FT_FRAME].count==1);
    assert(coh_ft_stream.data[COH_FT_MIXED][COH_FT_FRAME].count==1);
    assert(coh_ft_stream.data[COH_FT_GAMEPLAY][COH_FT_FRAME].count==1);
    assert(coh_ft_stream.data[COH_FT_MIXED][COH_FT_INTERVAL].sum==104);
    memset(&metric,0,sizeof(metric));
    cohFtAdd(&metric,100);cohFtAdd(&metric,101);cohFtAdd(&metric,200);cohFtAdd(&metric,120001);
    assert(metric.histogram[5]==1&&metric.histogram[6]==1&&metric.histogram[9]==1
        &&metric.histogram[COH_FT_BUCKETS-1]==1);
    assert(cohFtQuantile(&metric,50)==110&&cohFtQuantile(&metric,95)==-1);
    assert(metric.over125==2&&metric.over200==1);
    cohFtAdd(&metric,-1);assert(metric.count==4);
    reset("1");
    for(i=0;i<96;i++)frame(COH_FT_GAMEPLAY,COH_FT_GAMEPLAY,i*104.0);
    assert(!emissions&&cpu_queries==1);
    frame(COH_FT_GAMEPLAY,COH_FT_GAMEPLAY,96*104.0);
    assert(emissions==1&&cpu_queries==2&&coh_ft_stream.reports==1);
    assert(strstr(last_line,"\"role\":\"main\"")&&strstr(last_line,"\"mean_ms\":104.000"));
    assert(strstr(last_line,"\"thread_cpu_ms\":388.000"));
    emit_lines=1;puts(last_line); /* Python verifies the exact numeric JSON. */
    /* All four states and maximum-width histogram counts fit one fixed line. */
    for(i=0;i<COH_FT_STATES;i++)for(j=0;j<6;j++) {
        CohFtMetricData *m=&coh_ft_stream.data[i][j];
        m->count=4294967295u;m->sum=4294967295.0*120001.0;m->maximum=120001.0;
        m->over125=m->over200=4294967295u;
        for(before=0;before<COH_FT_BUCKETS;before++)m->histogram[before]=4294967295u;
    }
    /* Large impossible-in-practice counts stress bounded formatting only. */
    wall+=10000;cohFtReport(wall);assert(emissions==2&&coh_ft_stream.enabled);
    assert(strlen(last_line)<COH_FT_LINE_BYTES);
    emit_lines=0;
    for(i=2;i<COH_FT_MAX_REPORTS;i++) {
        wall+=10000;cohFtReport(wall);
    }
    assert(emissions==COH_FT_MAX_REPORTS&&!coh_ft_stream.enabled);
    before=wall_queries;frame(COH_FT_GAMEPLAY,COH_FT_GAMEPLAY,wall);
    assert(wall_queries==before&&emissions==COH_FT_MAX_REPORTS);
    reset("1");wall=100;cohFtPresentBegin();wall=103;cohFtSwapBegin();
    wall=110;cohFtSwapEnd();wall=112;cohFtPresentEnd();
    assert(coh_ft_stream.data[0][COH_FT_PRESENT].sum==12);
    assert(coh_ft_stream.data[0][COH_FT_SWAP].sum==7);
    wall=205;cohFtPresentBegin();wall=207;cohFtSwapBegin();wall=214;cohFtSwapEnd();
    wall=10100;cpu=17;emit_lines=1;cohFtPresentEnd();
    assert(emissions==1&&cpu_queries==2&&coh_ft_stream.data[0][COH_FT_PRESENT].count==0);
    assert(strstr(last_line,"\"presentation_interval\":{\"count\":1,\"mean_ms\":105.000"));
    assert(strstr(last_line,"\"swap_wall\":{\"count\":2,\"mean_ms\":7.000"));
    /* Missing CPU samples and failed/backwards wall clocks never stop gameplay. */
    reset("1");fail_cpu=1;frame(COH_FT_GAMEPLAY,COH_FT_GAMEPLAY,0);
    frame(COH_FT_GAMEPLAY,COH_FT_GAMEPLAY,10000);
    assert(strstr(last_line,"\"thread_cpu_ms\":null"));
    reset("1");fail_wall=1;frame(COH_FT_GAMEPLAY,COH_FT_GAMEPLAY,0);
    assert(!coh_ft_stream.enabled&&!emissions&&!cpu_queries);
    reset("1");frame(COH_FT_GAMEPLAY,COH_FT_GAMEPLAY,1000);
    frame(COH_FT_GAMEPLAY,COH_FT_GAMEPLAY,500);assert(!coh_ft_stream.enabled&&!emissions);
    puts("FRAME_AGGREGATION_BOUND_DISABLED_CLOCK_PASS");return 0;
}
'''
    return prefix + hostile_macros() + (ROOT / HEADER).read_text() + '\n' + restored_macros() + tail


def production_harness():
    """Use genuine production QPC/GetThreadTimes/stdio/TLS on Windows only."""
    prefix = '#include <assert.h>\n#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#include <windows.h>\n'
    return prefix + hostile_macros() + (ROOT / HEADER).read_text() + restored_macros() + r'''
#ifdef _WIN64
#error Formal frame qualification must target Win32
#endif
static __declspec(thread) volatile unsigned long observer;
static DWORD WINAPI present_thread(void *result) {
    unsigned int i;
    cohFtPresentBegin();
    assert(coh_ft_stream.enabled&&coh_ft_stream.frequency>0&&coh_ft_stream.cpu_valid);
    coh_ft_stream.window_start-=COH_FT_REPORT_MS;
    cohFtSwapBegin();for(i=0;i<100000;i++)observer+=i;cohFtSwapEnd();cohFtPresentEnd();
    assert(coh_ft_stream.reports==1&&coh_ft_stream.presentation==1);
    *(int*)result=1;return 0;
}
int main(void) {
    HANDLE threads[4];int results[4]={0,0,0,0};unsigned int i;
    check_restored_macros();
    _putenv_s("COH_CLIENT_FRAME_TIMING","0");
    cohFtMainBegin(COH_FT_MENU);assert(coh_ft_stream.initialized&&!coh_ft_stream.enabled);
    _putenv_s("COH_CLIENT_FRAME_TIMING","1");
    cohFtMainBegin(COH_FT_GAMEPLAY);assert(!coh_ft_stream.enabled);
    memset(&coh_ft_stream,0,sizeof(coh_ft_stream));
    cohFtMainBegin(COH_FT_GAMEPLAY);
    assert(coh_ft_stream.enabled&&coh_ft_stream.frequency>0&&coh_ft_stream.cpu_valid);
    coh_ft_stream.window_start-=COH_FT_REPORT_MS;
    for(i=0;i<4;i++){threads[i]=CreateThread(NULL,0,present_thread,&results[i],0,NULL);assert(threads[i]);}
    cohFtPhaseBegin(COH_FT_ENGINE_PHASE);cohFtPhaseBegin(COH_FT_SUBMIT_PHASE);
    for(i=0;i<100000;i++)observer+=i;cohFtPhaseEnd(COH_FT_SUBMIT_PHASE);
    cohFtPhaseBegin(COH_FT_PACING_PHASE);Sleep(1);cohFtPhaseEnd(COH_FT_PACING_PHASE);
    cohFtPhaseEnd(COH_FT_ENGINE_PHASE);cohFtMainEnd(COH_FT_GAMEPLAY);
    assert(WaitForMultipleObjects(4,threads,TRUE,10000)==WAIT_OBJECT_0);
    for(i=0;i<4;i++){assert(results[i]==1);CloseHandle(threads[i]);}
    assert(coh_ft_stream.reports==1&&coh_ft_stream.presentation==0);
    puts("WIN32_QPC_THREAD_CPU_TLS_CONCURRENT_JSON_PASS");return 0;
}
'''


def compile_harness(directory, windows=False, production=False):
    directory = Path(directory)
    source = directory / ('production.c' if production else 'frame.c')
    source.write_text(production_harness() if production else harness())
    if os.name == 'nt':
        compiler = shutil.which('cl')
        if not compiler:
            raise ValueError('Actual Win32 MSVC required')
        binary = source.with_suffix('.exe')
        command = [compiler, '/nologo', *OPTIONS, '/W3', str(source), '/Fe:' + str(binary)]
    else:
        if windows or production:
            raise ValueError('Formal frame clock qualification requires real Win32 MSVC')
        compiler = shutil.which('cc') or shutil.which('gcc')
        if not compiler:
            raise ValueError('C compiler required')
        binary = source.with_suffix('')
        command = [compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(binary)]
    subprocess.run(command, cwd=directory, check=True, capture_output=True, text=True)
    if windows or production:
        sys.path.insert(0, str(ROOT / 'tools'))
        from package_reference_runtime import file_record
        if file_record(binary)['pe_machine'] != 332:
            raise ValueError('Formal native frame proof compiler must target Win32')
    return binary


def records(output):
    return [json.loads(line[len(PREFIX):]) for line in output.splitlines() if line.startswith(PREFIX)]


def run_checks(binary):
    output = subprocess.check_output([str(binary)], text=True)
    assert 'FRAME_AGGREGATION_BOUND_DISABLED_CLOCK_PASS' in output
    rows = records(output)
    assert len(rows) == 3
    main = rows[0]
    assert main['role'] == 'main' and main['report'] == 1 and main['window_ms'] == 10088
    assert main['thread_cpu_ms'] == 388
    state = main['states']['gameplay']
    assert state['frame_interval']['count'] == 96 and state['frame_wall']['count'] == 97
    assert state['frame_interval']['mean_ms'] == 104 and state['frame_interval']['p95_upper_ms'] == 110
    assert state['engine_wall']['mean_ms'] == 100 and state['submit_wall']['mean_ms'] == 30
    assert state['pacing_wall']['mean_ms'] == 60 and state['work_wall']['mean_ms'] == 44
    assert state['frame_interval']['over_125ms_count'] == 0
    assert set(rows[1]['states']) == {'menu', 'loading', 'gameplay', 'mixed'}
    for group in rows[1]['states'].values():
        assert len(group) == 6
        for metric in group.values():
            assert len(metric['histogram']) == len(main['histogram_upper_ms']) == 22
    presentation = rows[2]
    assert presentation['role'] == 'presentation' and presentation['thread_cpu_ms'] == 17
    state = presentation['states']['unclassified']
    assert state['presentation_interval']['mean_ms'] == 105
    assert state['swap_wall']['mean_ms'] == 7 and state['present_wall']['max_ms'] == 9895
    return rows


def expected_receipt():
    return {'format': 1, 'status': 'passed', 'platform': 'windows', 'architecture': 'Win32',
        'configuration': 'OptDebug', 'compiler_options': OPTIONS,
        'patch_sha256': digest(ROOT / PATCH), 'header_sha256': digest(ROOT / HEADER),
        'harness_sha256': hashlib.sha256(harness().encode()).hexdigest(),
        'production_harness_sha256': hashlib.sha256(production_harness().encode()).hexdigest(),
        'wall_pacing_and_submission_separation_verified': True,
        'presentation_swap_wall_verified': True, 'histogram_upper_bounds_verified': True,
        'menu_loading_gameplay_mixed_states_verified': True,
        'report_rate_and_120_report_cap_verified': True,
        'disabled_without_clock_cpu_or_logging_verified': True,
        'clock_failure_nonfatal_verified': True, 'fixed_buffer_full_state_format_verified': True,
        'genuine_win32_qpc_and_thread_cpu_verified': True,
        'genuine_win32_tls_and_concurrent_json_verified': True,
        'retained_native_crt_macro_isolation_and_restoration_verified': True,
        'physical_frame_rate_or_gpu_latency_validated': False}


def validate_checks(checks):
    if checks != expected_receipt():
        raise ValueError('Exact source-bound real Win32 frame qualification required')
    return checks


def windows_receipt(output):
    with tempfile.TemporaryDirectory(prefix='coh-win32-frame-') as directory:
        run_checks(compile_harness(directory, windows=True))
        production = subprocess.check_output([str(compile_harness(directory, windows=True, production=True))], text=True)
        assert 'WIN32_QPC_THREAD_CPU_TLS_CONCURRENT_JSON_PASS' in production
        rows = records(production)
        assert len(rows) == 5 and sum(row['role'] == 'main' for row in rows) == 1
        assert all(row['thread_cpu_ms'] is not None and row['thread_cpu_ms'] >= 0 for row in rows)
    document = expected_receipt()
    validate_checks(document)
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(document, indent=2) + '\n')
    return document


class FrameNativeTests(unittest.TestCase):
    def test_real_aggregator_separates_wall_work_pacing_and_presentation_with_bounds(self):
        with tempfile.TemporaryDirectory(prefix='coh-frame-') as directory:
            run_checks(compile_harness(directory))

    def test_qualification_rejects_changed_source_platform_and_claims(self):
        receipt = expected_receipt()
        self.assertEqual(validate_checks(receipt), receipt)
        for key in receipt:
            wrong = dict(receipt); wrong[key] = None
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_checks(wrong)

    def test_formal_qualification_executes_on_win32_and_refuses_simulated_platform(self):
        with tempfile.TemporaryDirectory(prefix='coh-frame-production-') as directory:
            if os.name == 'nt':
                document = windows_receipt(Path(directory) / 'proof.json')
                self.assertEqual(validate_checks(document), document)
            else:
                with self.assertRaisesRegex(ValueError, 'real Win32'):
                    windows_receipt(Path(directory) / 'proof.json')
                self.assertFalse((Path(directory) / 'proof.json').exists())


if __name__ == '__main__':
    if '--windows-qualify' in sys.argv:
        parser = argparse.ArgumentParser()
        parser.add_argument('--windows-qualify', action='store_true')
        parser.add_argument('--output', type=Path, required=True)
        arguments = parser.parse_args()
        windows_receipt(arguments.output)
    else:
        unittest.main()
