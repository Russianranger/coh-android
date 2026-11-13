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
import re
from pathlib import Path
import subprocess
import sys
import tempfile

CASES = ['window', 'disabled', 'files', 'thread', 'slow', 'clock', 'saturation',
         'startup', 'startup_disabled', 'startup_clock']
NEGATIVE_ASSERTION = 's->ticks == 4 && s->file_calls == 4 && s->window_start == 0'
STARTUP_NEGATIVE_ASSERTION = 'startup->enabled && startup->sequence == 17'
TRUSTED_NEGATIVE_ASSERTION = 'scans == 0 && list_reads == 0'
TEXTPARSER = 'libs/UtilitiesLib/src/utils/textparser.c'
TRUSTED_CASES = ['trusted_bins', 'trusted_bins_disabled']
SPARE_HEADER = 'MapServer/src/svr/armport_spare_server.h'
SPARE_NEGATIVE_ASSERTION = 'reads == 3 && sleeps == 2 && db_state.map_id == 5001'
SPARE_CASES = ['spare_server', 'spare_server_disabled', 'spare_server_invalid']


def test_cases(source):
    text = (source / 'MapServer/src/svr/svr_init.c').read_text()
    parser = (source / TEXTPARSER).read_text()
    return (CASES + (['progress_markers'] if 'cohMapProgressMark(COH_MAP_STAGE_LOOP_PRE_TICK);' in text else [])
            + (TRUSTED_CASES if 'static int armportTrustedBin(' in parser else [])
            + (SPARE_CASES if (source / SPARE_HEADER).is_file() else []))


def spare_fixture(source):
    """Run the shipping spare-server header over recorded Win32 file, clock and map-list shims."""
    svr = (source / 'MapServer/src/svr/svr_init.c').read_text()
    header = source / SPARE_HEADER
    if header.is_file():
        # The shipping call site: after every shared load, before any DbServer traffic.
        main = svr[svr.index('int __cdecl main(int argc,char **argv)'):]
        order = [main.index(text) for text in ('    checkTsr();', '        cmdCfgLoad();\n        armportSpareWait();\n',
                                               '        connectToDbserver(NO_TIMEOUT);')]
        assert order == sorted(order) and svr.count('armportSpareWait();') == 1, order
        assert svr.index('#include <utilitieslib/utils/wininclude.h>') < svr.index('#include "armport_spare_server.h"')
        body = header.read_text()
    else:
        assert 'armportSpare' not in svr
        body = 'static void armportSpareWait(void) {}\n'
    return r'''
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint32_t DWORD; typedef void *HANDLE;
#define INVALID_HANDLE_VALUE ((HANDLE)-1)
#define GENERIC_READ 1
#define FILE_SHARE_READ 1
#define FILE_SHARE_WRITE 2
#define FILE_SHARE_DELETE 4
#define OPEN_EXISTING 3
#define FILE_ATTRIBUTE_NORMAL 0
typedef struct StaticMapInfo { int mapID, baseMapID, instanceID; } StaticMapInfo;
static struct { int map_id, base_map_id, instance_id, cookie, local_server; } db_state;
static const char *contents[8]; static const char *opened; static int reads, sleeps, ticks;
static HANDLE CreateFileA(const char *path, int access, int share, void *security, int disposition, int flags, void *template) {
    (void)access; (void)share; (void)security; (void)disposition; (void)flags; (void)template;
    opened = path; return contents[reads] ? (HANDLE)1 : (++reads, INVALID_HANDLE_VALUE); }
static int ReadFile(HANDLE handle, char *buffer, DWORD wanted, DWORD *got, void *overlapped) {
    const char *text = contents[reads++]; size_t length = strlen(text);
    (void)handle; (void)overlapped;
    if (length > wanted) length = wanted;
    memcpy(buffer, text, length); *got = (DWORD)length; return 1; }
static void CloseHandle(HANDLE handle) { (void)handle; }
static void Sleep(int milliseconds) { sleeps += milliseconds == 100; }
static DWORD GetTickCount(void) { return (DWORD)(ticks += 250); }
static DWORD GetCurrentProcessId(void) { return 42; }
static StaticMapInfo clone = {5001, 50, 2};
static StaticMapInfo *staticMapInfoFind(int id) { return id == 5001 ? &clone : NULL; }
#define fileGetStdout() stdout      /* svr_init.c flushes its console this way */
''' + body + r'''
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); return 1; } } while (0)
int main(int argc, char **argv) {
    const char *mode = argc > 1 ? argv[1] : "";
    (void)contents; (void)opened; (void)clone; (void)staticMapInfoFind; (void)CreateFileA; (void)ReadFile;
    (void)CloseHandle; (void)Sleep; (void)GetTickCount; (void)GetCurrentProcessId;
    db_state.map_id = 71; db_state.base_map_id = 71;
    if (!strcmp(mode, "spare_server")) {
        CHECK(setenv("ARMPORT_SPARE_FILE", "Z:\\state\\spare-assign", 1) == 0);
        contents[2] = "ARMPORT_SPARE_ASSIGN_V1 map_id=5001 cookie=7\n";      /* absent twice, then published */
        armportSpareWait();
        CHECK(reads == 3 && sleeps == 2 && db_state.map_id == 5001);
        CHECK(db_state.base_map_id == 50 && db_state.instance_id == 2 && db_state.cookie == 7);
        CHECK(opened && !strcmp(opened, "Z:\\state\\spare-assign"));
        reads = 0; contents[0] = "ARMPORT_SPARE_ASSIGN_V1 map_id=71 cookie=2147483647\n"; contents[2] = NULL;
        armportSpareWait();                                                  /* a zone without a base map */
        CHECK(db_state.map_id == 71 && db_state.base_map_id == 71 && db_state.instance_id == 0);
        CHECK(db_state.cookie == 2147483647);
        return 0;
    }
    if (!strcmp(mode, "spare_server_disabled")) {
        unsetenv("ARMPORT_SPARE_FILE");
        armportSpareWait();
        CHECK(setenv("ARMPORT_SPARE_FILE", "", 1) == 0);
        armportSpareWait();
        CHECK(reads == 0 && sleeps == 0 && db_state.map_id == 71 && db_state.cookie == 0);
        return 0;
    }
    if (!strcmp(mode, "spare_server_invalid")) {
        CHECK(setenv("ARMPORT_SPARE_FILE", "assign", 1) == 0);
        contents[0] = argc > 2 ? argv[2] : "";
        db_state.local_server = argc > 3;
        armportSpareWait();                                                  /* must exit(3) itself */
        return 0;
    }
    return 2;
}
'''


def trusted_fixture(source):
    """Run the shipping ParserIsPersistNewer body over recorded parser shims."""
    text = (source / TEXTPARSER).read_text()
    helper = function(text, 'static int armportTrustedBin(') if 'static int armportTrustedBin(' in text else ''
    body = function(text, 'SimpleBufHandle ParserIsPersistNewer(')
    return r'''
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef int __time32_t;
typedef struct SimpleBuf { int pos; } *SimpleBufHandle;
typedef struct ParseTable { int unused; } ParseTable;
typedef struct DefineContext DefineContext;
typedef struct FileEntry { const char *path; __time32_t date; int seen; } FileEntry;
typedef FileEntry **FileList;
struct _finddata32_t { unsigned attrib; char name[260]; __time32_t time_write; };
typedef int FileScanAction;
#define PARSE_SIG "Parse6"
#define verbose_printf(...) ((void)0)
static struct SimpleBuf bin_buffer;
static FileList lf_filedates;
static int scans, list_reads, closes, production, crc_matches = 1;
static const char *g_StdAdditionalFilePrefixes[] = {""};
static int ParseTableCRC(ParseTable pti[], DefineContext *defines) { (void)pti; (void)defines; return 7; }
static SimpleBufHandle SerializeReadOpen(const char *name, const char *type, int crc, int ignore_crc) {
    (void)name; (void)type; return (crc_matches && (crc == 7 || ignore_crc)) ? &bin_buffer : NULL; }
static int isProductionMode(void) { return production; }
static int SimpleBufTell(SimpleBufHandle h) { return h->pos; }
static void SimpleBufSeek(SimpleBufHandle h, int pos, int whence) { (void)whence; h->pos = pos; }
static void SerializeClose(SimpleBufHandle h) { (void)h; ++closes; }
static int FileListRead(FileList *list, SimpleBufHandle h) { (void)h; ++list_reads; *list = NULL; return 1; }
static void FileListCreate(FileList *list) { *list = NULL; }
static void FileListDestroy(FileList *list) { *list = NULL; }
static void FileListInsert(FileList *list, const char *path, __time32_t date) { (void)list; (void)path; (void)date; }
static FileEntry *FileListFind(FileList *list, const char *path) { (void)list; (void)path; return NULL; }
static int eaSize(FileList *list) { (void)list; return 0; }
static char *addFilePrefix(const char *mask, const char *prefix) { (void)prefix; return (char *)mask; }
static FileScanAction DateCheckCallback(char *dir, struct _finddata32_t *data) { (void)dir; (void)data; return 0; }
static void fileScanAllDataDirs(const char *dir, FileScanAction (*callback)(char *, struct _finddata32_t *)) {
    (void)dir; (void)callback; ++scans; }
static int fileDatesEqual(__time32_t a, __time32_t b, bool exact) { (void)exact; return a == b; }
static __time32_t fileLastChanged(const char *path) { (void)path; return 0; }
static int fileExists(const char *path) { (void)path; return 0; }
''' + helper + body + r'''
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); return 1; } } while (0)
int main(int argc, char **argv) {
    ParseTable pti[1] = {{0}};
    int i;
    const char *mode = argc > 1 ? argv[1] : "";
    if (!strcmp(mode, "trusted_bins")) {
        CHECK(setenv("ARMPORT_TRUSTED_BINS", "1", 1) == 0);
        CHECK(ParserIsPersistNewer("fx", NULL, "bin/fxinfo.bin", pti, NULL) == &bin_buffer);
        CHECK(scans == 0 && list_reads == 0);
        crc_matches = 0;
        CHECK(ParserIsPersistNewer("fx", NULL, "bin/fxinfo.bin", pti, NULL) == NULL);
        crc_matches = 1;
        for (i = 0; i < 300; ++i)
            CHECK(ParserIsPersistNewer("maps", NULL, "bin/minimap.bin", pti, NULL) == &bin_buffer);
        CHECK(scans == 0 && list_reads == 0 && closes == 0);
        return 0;
    }
    if (!strcmp(mode, "trusted_bins_disabled")) {
        unsetenv("ARMPORT_TRUSTED_BINS");
        CHECK(ParserIsPersistNewer("fx", NULL, "bin/fxinfo.bin", pti, NULL) == &bin_buffer);
        CHECK(scans == 1 && list_reads == 1);
        return 0;
    }
    return 2;
}
'''


def function(text, signature):
    start = text.index(signature)
    return text[start:text.index('\n}\n', start) + 3]


def startup_calls(svr, original=False):
    """Use the shipping call sites, expanding sysInit at its real main call."""
    main = svr[svr.index('int __cdecl main(int argc,char **argv)'):]
    pattern = r'^\s*(armportServerStartup(?:Begin\(\)|Phase\("[a-z_]+", db_state.map_id\));|sysInit\(\);)'
    calls = []
    for call in re.findall(pattern, main, re.MULTILINE):
        if call == 'sysInit();':
            calls.extend(re.findall(pattern, function(svr, 'static void sysInit()'), re.MULTILINE))
        else:
            calls.append(call)
    if not original:
        assert calls[0] == 'armportServerStartupBegin();'
        assert main.index(calls[0]) < main.index('memCheckInit();')
        # Early diagnostic commands can exit in parseArgs1. Their stdout
        # stays quiet even when telemetry was requested.
        assert main.index('parseArgs1(argc,argv);') < main.index(calls[1])
        assert main.index('dbReadyForPlayers();') < main.index('armportServerStartupPhase("ready_published"')
        assert main.index('armportServerStartupPhase("main_loop_begin"') < main.index('armportServerMetricsInit(')
        assert len(calls) == 18, calls
    return '\n'.join(('    ' if i == 0 else '    fake_now += 100; ') + call.replace('db_state.map_id', '2')
                     for i, call in enumerate(calls))


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
static void actual_startup_observations(void) {
''' + startup_calls(svr, original is not None) + r'''
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
    if (!strcmp(mode, "startup")) {
        ArmportServerStartup *startup = &armport_server_startup;
        actual_startup_observations();
        CHECK(startup->enabled && startup->sequence == 17);
        CHECK(startup->begin == 0 && startup->previous == 1700);
        CHECK(s->enabled == 0 && s->file_calls == 0 && s->ticks == 0);
        return 0;
    }
    if (!strcmp(mode, "startup_disabled")) {
        const char *options[] = {"0", "", "10", "true"};
        for (i = 0; i < 4; ++i) {
            setenv("ARMPORT_SERVER_METRICS", options[i], 1);
            actual_startup_observations();
        }
        unsetenv("ARMPORT_SERVER_METRICS"); actual_startup_observations();
        CHECK(clock_calls == 0 && armport_server_startup.sequence == 0);
        puts("startup disabled: clocks=0"); return 0;
    }
    if (!strcmp(mode, "startup_clock")) {
        ArmportServerStartup *startup = &armport_server_startup;
        frequency_ok = 0; armportServerStartupBegin();
        CHECK(startup->clock_error && !startup->enabled);
        armportServerStartupPhase("args_parsed", 2);
        CHECK(!startup->clock_error && !startup->enabled && startup->sequence == 0);
        i = clock_calls; armportServerStartupPhase("ignored", 2); CHECK(clock_calls == i);
        frequency_ok = 1; fake_now = 20; armportServerStartupBegin();
        CHECK(startup->enabled && startup->sequence == 0);
        fake_now = 19; armportServerStartupPhase("args_parsed", 2);
        CHECK(!startup->enabled && startup->sequence == 0);
        fake_now = 30; armportServerStartupBegin(); clock_ok = 0;
        armportServerStartupPhase("args_parsed", 2); CHECK(!startup->enabled);
        return 0;
    }
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
        trusted_root = original or source
        trusted = work / 'trusted'
        (work / 'trusted.c').write_text(trusted_fixture(trusted_root))
        subprocess.run(['cc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-label', '-fsanitize=address,undefined',
                        str(work / 'trusted.c'), '-o', str(trusted)], check=True)
        control += trusted_fixture(trusted_root)
        spare = work / 'spare'
        (work / 'spare.c').write_text(spare_fixture(trusted_root))
        subprocess.run(['cc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-function', '-fsanitize=address,undefined',
                        str(work / 'spare.c'), '-o', str(spare)], check=True)
        control += spare_fixture(trusted_root)
        environment = {**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0'}
        for mode in (['window', 'startup', 'trusted_bins', 'spare_server'] if original and expect_control_failure else
                     (['window'] if original else test_cases(source))):
            if mode == 'spare_server_invalid':
                # Every malformed assignment, and a server in local mode, ends the process with
                # status 3 before it has touched its map id or the DbServer.
                invalid = ['ARMPORT_SPARE_ASSIGN_V1 map_id=71 cookie=1', 'ARMPORT_SPARE_ASSIGN_V1 map_id=0 cookie=1\n',
                           'ARMPORT_SPARE_ASSIGN_V1 map_id=071 cookie=1\n', 'ARMPORT_SPARE_ASSIGN_V1 map_id=100000 cookie=1\n',
                           'ARMPORT_SPARE_ASSIGN_V1 map_id=71 cookie=2147483648\n', 'ARMPORT_SPARE_ASSIGN_V1 map_id=71  cookie=1\n',
                           'ARMPORT_SPARE_ASSIGN_V1 map_id=71 cookie=1 \n', 'ARMPORT_SPARE_ASSIGN_V2 map_id=71 cookie=1\n',
                           'ARMPORT_SPARE_ASSIGN_V1 map_id=-1 cookie=1\n', 'ARMPORT_SPARE_ASSIGN_V1 map_id=71 cookie=\n',
                           'ARMPORT_SPARE_ASSIGN_V1 map_id=71 cookie=1\nmore\n', '\n', 'x' * 200 + '\n']
                for text in invalid:
                    result = subprocess.run([str(spare), mode, text], capture_output=True, text=True, env=environment)
                    assert result.returncode == 3 and result.stdout.splitlines() == [
                        'ARMPORT_SPARE_V1 status=waiting pid=42 placeholder_map_id=71',
                        'ARMPORT_SPARE_V1 status=refused pid=42 reason=invalid_assignment'], (text, result)
                result = subprocess.run([str(spare), mode, 'ARMPORT_SPARE_ASSIGN_V1 map_id=71 cookie=1\n', 'local'],
                                        capture_output=True, text=True, env=environment)
                assert result.returncode == 3 and result.stdout.splitlines()[-1] == \
                    'ARMPORT_SPARE_V1 status=refused pid=42 reason=local_server', result
                print(mode + ': %d malformed assignments and local mode refused' % len(invalid))
                continue
            program = trusted if mode in TRUSTED_CASES else spare if mode in SPARE_CASES else exe
            result = subprocess.run([str(program), mode], capture_output=True, text=True, env=environment)
            print(mode + ': ' + ' | '.join(result.stdout.splitlines()))
            if expect_control_failure:
                assertion = {'window': NEGATIVE_ASSERTION, 'trusted_bins': TRUSTED_NEGATIVE_ASSERTION,
                             'spare_server': SPARE_NEGATIVE_ASSERTION}.get(mode, STARTUP_NEGATIVE_ASSERTION)
                assert result.returncode != 0 and 'FAIL line ' in result.stderr and assertion in result.stderr, result.stderr
                print('unpatched negative control: expected missing-' + mode + ' assertion')
                continue
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
            if mode == 'startup':
                rows = result.stdout.splitlines()
                assert len(rows) == 17, rows
                phases = ['args_parsed', 'directory_cache_begin', 'directory_cache_done', 'sys_init_done',
                          'server_state_done', 'map_metadata_done', 'sequencer_info_done', 'definitions_done',
                          'encounter_scripts_done', 'player_animations_done', 'db_connect_begin', 'db_connected',
                          'group_load_begin', 'group_load_done', 'db_setup_done', 'ready_published', 'main_loop_begin']
                for i, (row, phase) in enumerate(zip(rows, phases), 1):
                    assert row.startswith('ARMPORT_SERVER_STARTUP_V1 '), row
                    fields = dict(field.split('=', 1) for field in row.split()[1:])
                    assert fields == {'status': 'ok', 'map_id': '2', 'pid': '42', 'sequence': str(i),
                                      'phase': phase, 'elapsed_ms': f'{i * 100:.3f}', 'phase_ms': '100.000',
                                      'scope': 'main_entry_to_checkpoint'}, row
            if mode == 'startup_disabled':
                assert 'ARMPORT_SERVER_STARTUP_V1' not in result.stdout
            if mode == 'trusted_bins':
                rows = result.stdout.splitlines()
                assert len(rows) == 256, len(rows)
                assert rows[0] == 'ARMPORT_TRUSTED_BINS_V1 status=trusted ordinal=1 bin=bin/fxinfo.bin', rows[0]
                assert rows[1] == 'ARMPORT_TRUSTED_BINS_V1 status=trusted ordinal=2 bin=bin/minimap.bin', rows[1]
                assert rows[-1].endswith('ordinal=256 bin=bin/minimap.bin'), rows[-1]
            if mode == 'trusted_bins_disabled':
                assert 'ARMPORT_TRUSTED_BINS_V1' not in result.stdout
            if mode == 'spare_server':
                assert result.stdout.splitlines() == [
                    'ARMPORT_SPARE_V1 status=waiting pid=42 placeholder_map_id=71',
                    'ARMPORT_SPARE_V1 status=assigned pid=42 map_id=5001 base_map_id=50 instance_id=2 waited_ms=250',
                    'ARMPORT_SPARE_V1 status=waiting pid=42 placeholder_map_id=5001',
                    'ARMPORT_SPARE_V1 status=assigned pid=42 map_id=71 base_map_id=71 instance_id=0 waited_ms=250'], result.stdout
            if mode == 'spare_server_disabled':
                assert 'ARMPORT_SPARE_V1' not in result.stdout
            if mode == 'startup_clock':
                rows = result.stdout.splitlines()
                assert len(rows) == 3 and all('status=clock_error' in row for row in rows), rows
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
                                        for name in (staging.SVR, staging.FILE, staging.TEXTPARSER)},
                    'fixture_sha256': {'positive': positive, 'negative': negative},
                    'test_script_sha256': staging.digest(Path(__file__).read_bytes()),
                    'compiler': subprocess.check_output(['cc', '--version'], text=True).splitlines()[0],
                    'execution_environment': 'posix_host_with_windows_clock_and_file_io_shims',
                    'positive_cases': test_cases(source), 'unpatched_control_failed': True,
                    'unpatched_control_failure': 'runtime_missing_metrics_startup_trusted_bin_and_spare_assertions',
                    'shipping_binary_executed': False}
        staging.validate_test_report(document, receipt, args.upstream_root)
        args.report.write_text(json.dumps(document, indent=2) + '\n')


if __name__ == '__main__':
    main()
