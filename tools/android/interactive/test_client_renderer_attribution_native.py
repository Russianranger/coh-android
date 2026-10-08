"""Execute bounded renderer attribution and qualify real Win32 shared TLS/clock code."""
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
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools')]
import package_client_renderer_attribution_native as producer
import package_client_loading_native as loading
from package_reference_runtime import file_record

HEADER = next(iter(producer.OVERLAYS.values()))
PATCH = producer.PATCHES[0]
OPTIONS = ['/O2', '/Oy-', '/MT', '/TC']
PREFIX = 'COH_CLIENT_RENDERER_ATTRIBUTION_V1 '


def font_fixture():
    """Exercise the actual stock coordinate conversion and default-font scaling."""
    source=(ROOT/'upstream/ouroboros/Game/src/graphics/font.c').read_text()
    return r'''
typedef float F32;
typedef unsigned char U8;
typedef struct FontState {U8 rgba[4];F32 scaleX,scaleY;void *font;} FontState;
static FontState curr_state, saved_state;
static FontState default_state={{255,255,255,255},1,1,0};
static void *fonts[1];
static int state_stack_critical_section, font_lock;
static F32 observed_x,observed_y;
static char observed_text[1024];
static void cohRaFontEnterCriticalSection(int *lock) {(void)lock;assert(!font_lock);font_lock=1;}
static void cohRaFontLeaveCriticalSection(int *lock) {(void)lock;assert(font_lock);font_lock=0;}
static void fontPushState(void) {saved_state=curr_state;}
static void fontPopState(void) {curr_state=saved_state;}
static void fontText(F32 x,F32 y,const char *text) {
    assert(font_lock);observed_x=x*curr_state.scaleX;observed_y=y*curr_state.scaleY;
    assert(strlen(text)<sizeof(observed_text));strcpy(observed_text,text);
}
#define PERFINFO_AUTO_START(a,b) ((void)0)
#define PERFINFO_AUTO_STOP() ((void)0)
#define _vsnprintf vsnprintf
#define TEXT_JUSTIFY 8192.f
#define EnterCriticalSection cohRaFontEnterCriticalSection
#define LeaveCriticalSection cohRaFontLeaveCriticalSection
''' + loading.function(source,'void fontSysText(') + '\n' + loading.function(source,'void xyprintf(') + r'''
static void hud_position_checks(void) {
    curr_state.scaleX=3;curr_state.scaleY=7;
    xyprintf(COH_RA_FPS_COLUMN,COH_RA_FPS_ROW,"FPS %.2f | %.1f ms/frame",10.0,100.0);
    assert(observed_x==8 && observed_y==112);
    assert(curr_state.scaleX==3 && curr_state.scaleY==7 && !font_lock);
    assert(!strcmp(observed_text,"FPS 10.00 | 100.0 ms/frame"));
    assert(observed_x+strlen(observed_text)*8<640 && observed_y+8<480);
    xyprintf(COH_RA_FPS_COLUMN,COH_RA_FPS_ROW,"FPS %.2f | %.1f ms/frame",30.0,1000.0/30.0);
    assert(observed_x==8 && observed_y==112);
    assert(observed_x+strlen(observed_text)*8<800 && observed_y+8<600);
}
#undef EnterCriticalSection
#undef LeaveCriticalSection
'''


def macros():
    return '''\n#define printf coh_ra_poison_printf
#define vsnprintf(a,b,c,d) coh_ra_poison_formatter
#define fflush(a) coh_ra_poison_flush
#define FILE coh_ra_poison_file
'''


def restore():
    return '''
#define RA_STRING_INNER(a) #a
#define RA_STRING(a) RA_STRING_INNER(a)
static void check_macros(void) {
    assert(!strcmp(RA_STRING(printf),"coh_ra_poison_printf"));
    assert(!strcmp(RA_STRING(vsnprintf(a,b,c,d)),"coh_ra_poison_formatter"));
    assert(!strcmp(RA_STRING(fflush(a)),"coh_ra_poison_flush"));
    assert(!strcmp(RA_STRING(FILE),"coh_ra_poison_file"));
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
void external_wait(int begin);
void external_swap(int begin);
'''
    if not production:
        prefix += '''
static const char *environment;
static double wall,cpu;
static unsigned int wall_queries,cpu_queries,environment_queries,emissions;
static int fail_wall,fail_cpu,emit_lines;
static char last_line[8192];
const char *cohRaTestEnvironment(void) {++environment_queries;return environment;}
int cohRaTestWall(double *value) {++wall_queries;*value=wall;return !fail_wall;}
int cohRaTestCpu(double *value) {++cpu_queries;*value=cpu;return !fail_cpu;}
void cohRaTestEmit(const char *line) {
    assert(strlen(line)<sizeof(last_line) && !strchr(line,'\\n'));
    strcpy(last_line,line);++emissions;if(emit_lines)puts(line);
}
#define COH_RENDERER_ATTRIBUTION_TEST 1
'''
    prefix += '#define COH_RA_IMPLEMENTATION 1\n'
    common = macros() + (ROOT/HEADER).read_text() + restore() + font_fixture()
    if production:
        tail = r'''
#ifdef _WIN64
#error Genuine qualification must target Win32
#endif
static volatile LONG concurrent_ready;
static HANDLE concurrent_start;
static DWORD WINAPI renderer_thread(void *unused) {
    unsigned int i;double now;
    volatile unsigned int busy=0;
    (void)unused;
    assert(coh_ra_stream.initialized==0);
    cohRaRendererBegin();assert(coh_ra_stream.renderer==1);
    InterlockedIncrement(&concurrent_ready);
    assert(WaitForSingleObject(concurrent_start,10000)==WAIT_OBJECT_0);
    for(i=0;i<1000000;++i)busy+=i;
    external_swap(1);Sleep(2);external_swap(0);cohRaRendererEnd();
    assert(coh_ra_stream.metrics[COH_RA_SWAP].count==1);
    assert(coh_ra_stream.metrics[COH_RA_SWAP].maximum>0);
    assert(cohRaWall(&now));coh_ra_stream.window_start=now-COH_RA_REPORT_MS;
    cohRaReport(now);assert(coh_ra_stream.reports==1);
    return busy?0:1;
}
int main(void) {
    HANDLE threads[4];unsigned int i;double now;DWORD result;
    check_macros();
    hud_position_checks();
    assert(_putenv_s("COH_CLIENT_RENDERER_ATTRIBUTION","0")==0);
    cohRaMainBegin(1,0,1,0,0,30,1);assert(!coh_ra_stream.enabled);
    memset(&coh_ra_stream,0,sizeof(coh_ra_stream));
    assert(_putenv_s("COH_CLIENT_RENDERER_ATTRIBUTION","1")==0);
    cohRaMainBegin(1,0,1,0,0,30,1);external_wait(1);Sleep(2);external_wait(0);cohRaMainEnd(1);
    assert(coh_ra_stream.metrics[COH_RA_WAIT].maximum>0);
    assert(cohRaWall(&now));coh_ra_stream.window_start=now-COH_RA_REPORT_MS;
    cohRaReport(now);assert(coh_ra_stream.reports==1 && coh_ra_stream.renderer==0);
    concurrent_start=CreateEvent(NULL,TRUE,FALSE,NULL);assert(concurrent_start);
    for(i=0;i<4;++i) {threads[i]=CreateThread(NULL,0,renderer_thread,NULL,0,NULL);assert(threads[i]);}
    while(concurrent_ready!=4)Sleep(1);
    assert(SetEvent(concurrent_start));
    assert(WaitForMultipleObjects(4,threads,TRUE,10000)==WAIT_OBJECT_0);
    for(i=0;i<4;++i) {assert(GetExitCodeThread(threads[i],&result)&&result==0);CloseHandle(threads[i]);}
    CloseHandle(concurrent_start);
    assert(coh_ra_stream.reports==1 && coh_ra_stream.renderer==0);
    puts("WIN32_QPC_THREAD_CPU_SHARED_TLS_CONCURRENT_JSON_PASS");return 0;
}
'''
    else:
        tail = r'''
static void reset(const char *flag) {
    memset(&coh_ra_stream,0,sizeof(coh_ra_stream));environment=flag;wall=cpu=0;
    wall_queries=cpu_queries=environment_queries=emissions=0;
    fail_wall=fail_cpu=emit_lines=0;last_line[0]=0;
}
static void main_frame(double start,int cap,double showfps) {
    wall=start;cohRaMainBegin(1,0,1,0,0,cap,showfps);
    wall=start+10;external_wait(1);cohRaWaitIteration();cohRaWaitIteration();
    wall=start+40;external_wait(0);wall=start+100;cpu+=4;cohRaMainEnd(1);
}
int main(void) {
    const char *flags[]={NULL,"","0","01","true","1 "};unsigned int i,j,before;
    CohRaMetricData metric;
    check_macros();
    hud_position_checks();
    assert(COH_RA_FPS_COLUMN*8==8 && COH_RA_FPS_ROW*8==112);
    for(i=0;i<sizeof(flags)/sizeof(flags[0]);++i) {
        reset(flags[i]);for(j=0;j<1000;++j)main_frame(j*100.0,30,1);
        assert(!wall_queries && !cpu_queries && !emissions && environment_queries==1);
    }
    reset("1");main_frame(0,30,1);
    assert(coh_ra_stream.metrics[COH_RA_GFX].sum==100);
    assert(coh_ra_stream.metrics[COH_RA_WAIT].sum==30);
    assert(coh_ra_stream.metrics[COH_RA_GFX_OTHER].sum==70);
    assert(coh_ra_stream.waits==2 && cpu_queries==1 && emissions==1);
    wall=101;cohRaMainBegin(1,0,1,0,0,30,1);
    cohRaMainBegin(0,0,1,0,0,30,1);cohRaMainEnd(0);
    assert(coh_ra_stream.frame_open && coh_ra_stream.frame_start==101);
    wall=102;cohRaMainEnd(1);
    before=wall_queries;cohRaRendererBegin();cohRaRendererEnd();assert(wall_queries==before);
    main_frame(200,30,1);assert(emissions==1);
    main_frame(300,10,1);assert(emissions==2 && strstr(last_line,"\"maxfps\":10"));
    main_frame(400,10,0);assert(emissions==3 && strstr(last_line,"\"showfps\":0.000"));
    for(i=0;i<100;++i) {cohRaState(i,1);}
    assert(coh_ra_stream.state_reports==COH_RA_MAX_STATE_REPORTS && emissions==64);
    reset("1");for(i=0;i<100;++i)main_frame(i*100.0,30,1);
    assert(coh_ra_stream.reports==1 && cpu_queries==2 && emissions==2);
    assert(strstr(last_line,"\"thread_cpu_ms\":400.000"));
    puts(last_line);
    assert(strstr(last_line,"\"backpressure_wall\":{\"count\":100,\"mean_ms\":30.000"));
    for(i=1;i<COH_RA_MAX_REPORTS;++i) {wall+=10000;cohRaReport(wall);}
    assert(!coh_ra_stream.enabled && coh_ra_stream.reports==COH_RA_MAX_REPORTS);
    before=wall_queries;main_frame(wall,30,1);assert(wall_queries==before);
    reset("1");wall=0;cohRaRendererBegin();
    wall=10;cohRaPhaseBegin(COH_RA_TEXCOPY);wall=15;cohRaPhaseEnd(COH_RA_TEXCOPY);
    wall=20;cohRaPhaseBegin(COH_RA_TEXSUBCOPY);wall=27;cohRaPhaseEnd(COH_RA_TEXSUBCOPY);
    wall=30;cohRaPhaseBegin(COH_RA_VBO);wall=35;cohRaPhaseEnd(COH_RA_VBO);
    wall=40;cohRaPhaseBegin(COH_RA_READBACK);wall=48;cohRaPhaseEnd(COH_RA_READBACK);
    wall=80;external_swap(1);wall=100;external_swap(0);wall=105;cohRaRendererEnd();
    assert(coh_ra_stream.metrics[COH_RA_BATCH].sum==105);
    assert(coh_ra_stream.metrics[COH_RA_SWAP].sum==20);
    assert(coh_ra_stream.metrics[COH_RA_BATCH_OTHER].sum==85);
    for(i=0;i<4;++i)assert(coh_ra_stream.callbacks[i]==1);
    assert(coh_ra_stream.metrics[COH_RA_READBACK].sum==8 && cpu_queries==1);
    wall=10000;cohRaReport(wall);puts(last_line);
    memset(&metric,0,sizeof(metric));cohRaAdd(&metric,101);cohRaAdd(&metric,120001);
    assert(cohRaQuantile(&metric,95)==-1 && metric.histogram[6]==1 && metric.histogram[21]==1);
    metric.count=UINT_MAX;cohRaAdd(&metric,1);assert(metric.count==UINT_MAX);
    assert(cohRaIncrement(UINT_MAX)==UINT_MAX);
    reset("1");fail_cpu=1;main_frame(0,30,1);main_frame(10000,30,1);
    assert(strstr(last_line,"\"thread_cpu_ms\":null"));
    reset("1");fail_wall=1;main_frame(0,30,1);assert(!coh_ra_stream.enabled && !cpu_queries);
    reset("1");main_frame(10000,30,1);main_frame(500,30,1);assert(!coh_ra_stream.enabled);
    reset("1");main_frame(0,30,1);main_frame(500,30,1);main_frame(400,30,1);
    assert(!coh_ra_stream.enabled); /* backwards between completed frames inside one window */
    reset("1");main_frame(0,30,1);
    for(i=0;i<COH_RA_METRICS;++i) {
        CohRaMetricData *m=&coh_ra_stream.metrics[i];
        m->count=UINT_MAX;m->sum=4294967295.0*120001;m->maximum=120001;
        for(j=0;j<COH_RA_BUCKETS;++j)m->histogram[j]=UINT_MAX;
    }
    wall=10000;cohRaReport(wall);assert(coh_ra_stream.enabled && strlen(last_line)<COH_RA_LINE_BYTES);
    puts("RENDERER_ATTRIBUTION_AGGREGATION_SHARED_TLS_BOUNDS_DISABLED_CLOCK_PASS");return 0;
}
'''
    return prefix + common + tail


def helper(production=False):
    prefix = '' if production else '''
const char *cohRaTestEnvironment(void);
int cohRaTestWall(double *value);
int cohRaTestCpu(double *value);
void cohRaTestEmit(const char *line);
#define COH_RENDERER_ATTRIBUTION_TEST 1
'''
    return prefix + (ROOT/HEADER).read_text() + '''
void external_wait(int begin) {if(begin)cohRaPhaseBegin(COH_RA_WAIT);else cohRaPhaseEnd(COH_RA_WAIT);}
void external_swap(int begin) {if(begin)cohRaPhaseBegin(COH_RA_SWAP);else cohRaPhaseEnd(COH_RA_SWAP);}
'''


def compile_harness(directory, windows=False, production=False):
    directory=Path(directory)
    source=directory/('renderer-production.c' if production else 'renderer.c')
    other=directory/('renderer-production-helper.c' if production else 'renderer-helper.c')
    source.write_bytes(harness(production).encode());other.write_bytes(helper(production).encode())
    if os.name=='nt':
        compiler=shutil.which('cl')
        if not compiler: raise ValueError('Real Win32 MSVC required')
        binary=source.with_suffix('.exe')
        command=[compiler,*OPTIONS,'/nologo',str(source),str(other),'/Fe:'+str(binary)]
    else:
        if windows or production: raise ValueError('Formal renderer qualification requires real Win32 MSVC')
        compiler=shutil.which('cc') or shutil.which('gcc')
        if not compiler: raise ValueError('C compiler required')
        binary=source.with_suffix('')
        command=[compiler,'-std=c11','-O2','-Wall','-Wextra','-Werror',str(source),str(other),'-o',str(binary)]
    try:
        subprocess.run(command,cwd=directory,check=True,capture_output=True,text=True)
    except subprocess.CalledProcessError as error:
        raise RuntimeError('Renderer fixture compilation failed:\n'+(error.stdout or '')+(error.stderr or '')) from error
    if windows and file_record(binary)['pe_machine']!=332: raise ValueError('Real Win32 proof compiler must target Win32')
    return binary


def records(output):
    return [json.loads(line[len(PREFIX):]) for line in output.splitlines() if line.startswith(PREFIX)]


def run_checks(binary, production=False):
    try:
        output=subprocess.check_output([str(binary)],text=True,stderr=subprocess.STDOUT,timeout=30)
    except subprocess.CalledProcessError as error:
        raise RuntimeError('Renderer fixture execution failed:\n'+error.output) from error
    rows=records(output);windows=[row for row in rows if row['event']=='window']
    assert all(len(row['bucket_upper_ms'])==22 for row in windows)
    assert all(len(m['histogram'])==22 for row in windows for m in row['metrics'].values())
    if production:
        assert 'WIN32_QPC_THREAD_CPU_SHARED_TLS_CONCURRENT_JSON_PASS' in output
        assert len(windows)==5 and sum(row['role']=='main' for row in windows)==1
        assert all(row['thread_cpu_ms'] is not None and row['thread_cpu_ms']>=0 for row in windows)
    else:
        assert 'RENDERER_ATTRIBUTION_AGGREGATION_SHARED_TLS_BOUNDS_DISABLED_CLOCK_PASS' in output
        assert len(windows)==2 and windows[0]['metrics']['gfx_other_wall']['mean_ms']==70
        assert windows[1]['metrics']['renderer_batch_non_swap_wall']['mean_ms']==85
    return rows


def expected_checks():
    return {'format':1,'status':'passed','platform':'windows','architecture':'Win32',
        'configuration':'OptDebug','compiler_options':OPTIONS,
        'patch_sha256':producer.digest(ROOT/PATCH),'header_sha256':producer.digest(ROOT/HEADER),
        'harness_sha256':hashlib.sha256(harness().encode()).hexdigest(),
        'helper_sha256':hashlib.sha256(helper().encode()).hexdigest(),
        'production_harness_sha256':hashlib.sha256(harness(True).encode()).hexdigest(),
        'production_helper_sha256':hashlib.sha256(helper(True).encode()).hexdigest(),
        'gfx_backpressure_and_remainder_separation_verified':True,
        'renderer_batch_swap_and_selected_callback_separation_verified':True,
        'numeric_cap_showfps_state_changes_bounded_verified':True,
        'unchanged_native_fps_sampling_and_bounded_position_verified':True,
        'shared_translation_unit_tls_and_thread_isolation_verified':True,
        'report_rate_histogram_counter_saturation_and_limits_verified':True,
        'disabled_without_clock_cpu_or_logging_verified':True,
        'clock_failure_nonfatal_verified':True,
        'genuine_win32_qpc_thread_cpu_and_concurrent_json_verified':True,
        'native_crt_macro_isolation_and_restoration_verified':True,
        'thread_cpu_excludes_renderer_workers':True,'physical_fps_gain_validated':False}


def validate_windows_checks(checks):
    if not producer.typed_equal(checks,expected_checks()):
        raise ValueError('Exact source-bound genuine Win32 renderer qualification required')
    return checks


def windows_receipt(output):
    with tempfile.TemporaryDirectory(prefix='coh-win32-renderer-') as temporary:
        run_checks(compile_harness(temporary,windows=True))
        run_checks(compile_harness(temporary,windows=True,production=True),production=True)
    document=expected_checks();validate_windows_checks(document);output=Path(output)
    if output.exists() or output.is_symlink(): raise ValueError('Fresh renderer Win32 proof required')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(document,indent=2)+'\n')
    return document


class RendererNativeTests(unittest.TestCase):
    def test_actual_shared_tls_aggregator_separates_wait_swap_callbacks_and_bounds(self):
        with tempfile.TemporaryDirectory(prefix='coh-renderer-native-') as directory:
            run_checks(compile_harness(directory))

    def test_genuine_qualification_rejects_changed_source_platform_types_and_claims(self):
        good=expected_checks();self.assertEqual(validate_windows_checks(good),good)
        for name,value in good.items():
            wrong=dict(good);wrong[name]=None
            with self.subTest(name=name),self.assertRaises(ValueError):validate_windows_checks(wrong)
            if type(value) in (int,bool):
                wrong=dict(good);wrong[name]=float(value) if type(value) is int else int(value)
                with self.subTest(name=name,mutation='JSON_type'),self.assertRaises(ValueError):validate_windows_checks(wrong)

    def test_formal_qualification_refuses_host_simulation(self):
        with tempfile.TemporaryDirectory(prefix='coh-renderer-formal-') as directory:
            path=Path(directory)/'proof.json'
            if os.name=='nt':self.assertEqual(windows_receipt(path),expected_checks())
            else:
                with self.assertRaisesRegex(ValueError,'real Win32'):windows_receipt(path)
                self.assertFalse(path.exists())


if __name__=='__main__':
    if '--windows-qualify' in sys.argv:
        parser=argparse.ArgumentParser();parser.add_argument('--windows-qualify',action='store_true')
        parser.add_argument('--output',required=True,type=Path);args=parser.parse_args();windows_receipt(args.output)
    else:unittest.main()
