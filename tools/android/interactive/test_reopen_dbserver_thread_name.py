"""Compile real thread-start/quick-format code at the physical reopen overflow boundary."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import package_levelup_ui_repair_dbserver as producer
import test_startup_bundle_save as accepted
from test_levelup_ui_repair_dbserver import staged_bundle

ROOT = producer.ROOT
THREAD_SOURCE = 'libs/UtilitiesLib/src/utils/utils.c'
QUICK_SOURCE = 'libs/UtilitiesLib/src/utils/quick_sprintf.c'
ESTRING_SOURCE = 'libs/UtilitiesLib/src/components/EString.c'
ESTRING_HEADER = 'libs/UtilitiesLib/include/utilitieslib/components/EString.h'
TASK_SOURCE = 'libs/UtilitiesLib/include/utilitieslib/UtilsCXX/taskthread.hpp'
# This is the exact __FILE__ embedded in the published 0.13.12 DbServer.exe.
PUBLISHED_TASK_FILE = 'D:\\a\\coh-android\\coh-android\\out\\levelup-ui-repair-db-source\\' + TASK_SOURCE.replace('/', '\\')
THREAD_NAME_FIXTURES_RUN = set()
REQUIRED_THREAD_NAME_FIXTURES = {'published_128_assertion', 'published_128_complete',
    'old_127_complete', 'boundary_128_complete', 'boundary_129_complete',
    'deeper_complete', 'short_complete', 'fallback_tid', 'creation_failure',
    'formatter_and_asserts_retained', 'typed_sql_contract_retained'}

HEADER = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <limits.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _MSC_VER
#include <malloc.h>
#include <crtdbg.h>
#define alloca _alloca
#ifndef va_copy
#define va_copy(d,s) ((d)=(s))
#endif
#else
#include <alloca.h>
#endif
#ifndef _MSC_VER
#define __stdcall
static char *_ltoa(long n,char *s,int base){assert(base==10);snprintf(s,200,"%ld",n);return s;}
static int _vsnprintf(char *s,size_t n,const char *f,va_list a){return vsnprintf(s,n,f,a);}
static int _vscprintf(char *f,va_list a){va_list copy;int n;va_copy(copy,a);n=vsnprintf(NULL,0,f,copy);va_end(copy);return n;}
#endif
typedef float F32;
typedef void *HANDLE;
#define INLINEDBG
#define xcase break; case
#define xdefault break; default
#define _TRUNCATE ((size_t)-1)
#define SPRINT_EVERYTHING INT_MAX
#define ARRAY_SIZE_CHECKED(a) sizeof(a)
#define sprintf_s snprintf
#define strdup_alloca(d,s) d=alloca(strlen(s)+1);strcpy(d,s)
#define devassertmsg(c,m) assert(c)
#define VA_START(va,format) {va_list va,*__vaTemp__=&va;va_start(va,format)
#define VA_END() va_end(*__vaTemp__);}
static void safe_ftoa(float n,char *s){snprintf(s,200,"%f",n);}
static unsigned created_tid=77,created_calls,freeze_calls,name_calls,allocations,frees;
static unsigned captured_tid, seen_flags, seen_stack;
static int fail_create;
static void *seen_security,*seen_arg;
static unsigned (__stdcall *seen_start)(void*);
static char *captured_name;
static void check_estring_name(const char *name);
static unsigned __stdcall callback(void *arg){return arg?1:0;}
static uintptr_t _beginthreadex(void *security,unsigned stack,
 unsigned (__stdcall *start)(void*),void *arg,unsigned flags,unsigned *tid){
 created_calls++;seen_security=security;seen_stack=stack;seen_start=start;seen_arg=arg;seen_flags=flags;
 if(fail_create)return 0;*tid=created_tid;return 0x1234;
}
static void assertYouMayFreezeThisThread(HANDLE handle,unsigned tid){
 assert((uintptr_t)handle==0x1234);assert(tid==created_tid);freeze_calls++;
}
static void SetThreadName(unsigned tid,const char *name){
 assert(freeze_calls==1);name_calls++;captured_tid=tid;
 if(PATCHED_TEST)check_estring_name(name);
 captured_name=malloc(strlen(name)+1);assert(captured_name);strcpy(captured_name,name);
}
static void *tracked_malloc(size_t n){allocations++;return malloc(n);}
static void tracked_free(void *p){frees++;free(p);}
#define malloc tracked_malloc
#define free tracked_free
void estrCreateEx(char **str,int length);
int estrConcatfv(char **str,const char *fmt,va_list args);
'''

MAIN = r'''
int main(int argc,char **argv){
 unsigned caller_tid=999;unsigned *tid;uintptr_t result;int line;
 if(argc!=5)return 2;line=atoi(argv[2]);fail_create=atoi(argv[4]);
#ifdef _MSC_VER
 _set_error_mode(_OUT_TO_STDERR);
 _set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);
#endif
 tid=atoi(argv[3])?&caller_tid:NULL;
 result=x_beginthreadex((void*)0x10,0x2000,callback,(void*)0x20,4,tid,argv[1],line);
 assert(created_calls==1);assert(seen_security==(void*)0x10 && seen_stack==0x2000);
 assert(seen_start==callback && seen_arg==(void*)0x20 && seen_flags==4);
 if(fail_create){
  assert(!result && !freeze_calls && !name_calls && !allocations && !frees);
  assert(caller_tid==999);puts("FAILED_THREAD_CREATION_RETAINED");return 0;
 }
 assert(result==0x1234 && freeze_calls==1 && name_calls==1 && captured_tid==created_tid);
 if(tid)assert(caller_tid==created_tid);else assert(caller_tid==999);
 printf("NAME\t%s\n",captured_name);printf("LIFETIME\t%u,%u\n",allocations,frees);
 free(captured_name);return 0;
}
'''


class ReopenDbServerThreadNameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('cl' if os.name == 'nt' else 'cc')
        if not compiler: raise RuntimeError('Thread-start regression requires a C compiler')
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-reopen-thread-')
        cls.folder = Path(cls.temporary.name); cls.binaries = {}
        quick = (ROOT/'upstream/ouroboros'/QUICK_SOURCE).read_text()
        estring = (ROOT/'upstream/ouroboros'/ESTRING_SOURCE).read_text()
        estring_header = (ROOT/'upstream/ouroboros'/ESTRING_HEADER).read_text()
        # Win32 uses pointer va_list; host Unix uses array va_list. Adapt only
        # that ABI initialization while preserving the actual formatter body.
        if os.name != 'nt':
            quick = quick.replace('va_list        ap = ap_orig;', 'va_list ap; va_copy(ap, ap_orig);')
            quick = quick.replace('int quick_vscprintf(char *format,const char *args)',
                'int quick_vscprintf(char *format,va_list args)').replace('_vscprintf(str, (char *)args)', '_vscprintf(str, args)')
        for patched in (False, True):
            folder = cls.folder/str(patched); folder.mkdir(); staged_bundle(folder)
            if patched: producer.apply_overlay(folder)
            thread = (folder/THREAD_SOURCE).read_text()
            pieces = ['#define PATCHED_TEST '+str(int(patched)), HEADER,
                '#define ESTR_DEFAULT_SIZE'+estring_header.split('#define ESTR_DEFAULT_SIZE',1)[1].split('//---------------------------------------------------------------------------------',1)[0],
                accepted.function(quick, 'static INLINEDBG void safecopy('),
                accepted.function(quick, 'static INLINEDBG int core_vsnprintf('),
                accepted.function(quick, 'int quick_sprintf('),
                accepted.function(quick, 'int quick_vsnprintf('),
                accepted.function(quick, 'int quick_vscprintf('),
                'static INLINEDBG char* estrToStr'+estring.split('static INLINEDBG char* estrToStr',1)[1].split('void estrCreate(char** str)',1)[0],
                accepted.function(estring, 'void estrCreate('),
                accepted.function(estring, 'void estrCreateEx('),
                accepted.function(estring, 'void estrDestroy('),
                accepted.function(estring, 'void estrClear('),
                accepted.function(estring, 'unsigned int estrReserveCapacity('),
                accepted.function(estring, 'int estrConcatfv('),
                accepted.function(estring, 'int estrPrintf('),
                'static void check_estring_name(const char *name){const EString *s=cestrFromStr(name);assert(s->stringLength==strlen(name));assert(s->bufferCapacity>=s->stringLength);assert(name[s->stringLength]==0 && name[s->stringLength+1]==0);assert(allocations==1 && frees==0);}',
                '#undef malloc\n#undef free',
                '#define sprintf(a,...) quick_sprintf(a,sizeof(a),__VA_ARGS__)',
                accepted.function(thread, 'uintptr_t x_beginthreadex('), MAIN]
            harness = folder/'thread.c'; harness.write_text('\n'.join(pieces))
            binary = folder/('thread.exe' if os.name == 'nt' else 'thread')
            if os.name == 'nt':
                command = [compiler, '/nologo', '/W3', '/O2', '/MT', str(harness), f'/Fe:{binary}']
            else:
                command = [compiler, '-std=c99', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-function', '-Wno-misleading-indentation', '-Wno-sign-compare',
                    str(harness), '-o', str(binary)]
            result = subprocess.run(command, cwd=folder, capture_output=True, text=True, timeout=30)
            if result.returncode: raise RuntimeError(result.stdout+result.stderr)
            cls.binaries[patched] = binary

    @classmethod
    def tearDownClass(cls): cls.temporary.cleanup()

    def run_thread(self, filename, line=110, caller_tid=True, fail=False, patched=True):
        return subprocess.run([str(self.binaries[patched]), filename, str(line), str(int(caller_tid)), str(int(fail))],
            capture_output=True, text=True, timeout=10)

    def assert_name(self, filename, line=110, caller_tid=True):
        result = self.run_thread(filename, line, caller_tid)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(result.stdout.splitlines(), ['NAME\t%s(%d)' % (filename, line), 'LIFETIME\t1,1'])

    def test_exact_published_fifo_worker_path_reproduces_assertion_then_survives(self):
        self.assertEqual(len(PUBLISHED_TASK_FILE), 123)
        self.assertEqual(len(PUBLISHED_TASK_FILE+'(110)'), 128)
        source = (ROOT/'upstream/ouroboros'/TASK_SOURCE).read_text().splitlines()
        self.assertIn('m_thread = CreateThread(', source[109])
        result = self.run_thread(PUBLISHED_TASK_FILE, patched=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('(size_t)(tail-buf+1) <= buf_size', result.stderr)
        THREAD_NAME_FIXTURES_RUN.add('published_128_assertion')
        self.assert_name(PUBLISHED_TASK_FILE)
        THREAD_NAME_FIXTURES_RUN.add('published_128_complete')

    def test_last_old_successful_capacity_preserves_complete_name(self):
        filename = 'x'*122
        self.assertEqual(len(filename+'(110)'), 127)
        old = self.run_thread(filename, patched=False)
        self.assertEqual(old.returncode, 0, old.stderr)
        self.assert_name(filename)
        THREAD_NAME_FIXTURES_RUN.add('old_127_complete')

    def test_first_overflow_boundary_keeps_complete_name(self):
        self.assert_name('x'*123)
        THREAD_NAME_FIXTURES_RUN.add('boundary_128_complete')

    def test_next_byte_boundary_keeps_complete_name(self):
        self.assert_name('x'*124)
        THREAD_NAME_FIXTURES_RUN.add('boundary_129_complete')

    def test_deeper_build_path_and_large_line_keep_complete_name(self):
        self.assert_name('D:\\'+'deep\\'*200+'taskthread.hpp', 123456789)
        THREAD_NAME_FIXTURES_RUN.add('deeper_complete')

    def test_short_path_and_negative_line_match_previous_output(self):
        self.assert_name('worker.c', -1)
        THREAD_NAME_FIXTURES_RUN.add('short_complete')

    def test_missing_caller_thread_id_uses_retained_local_fallback(self):
        self.assert_name(PUBLISHED_TASK_FILE, caller_tid=False)
        THREAD_NAME_FIXTURES_RUN.add('fallback_tid')

    def test_creation_failure_keeps_result_and_does_not_allocate_or_name(self):
        result = self.run_thread(PUBLISHED_TASK_FILE, fail=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'FAILED_THREAD_CREATION_RETAINED')
        THREAD_NAME_FIXTURES_RUN.add('creation_failure')

    def test_global_formatter_and_assertion_policy_remain_unpatched(self):
        raw = producer.patch_bytes().decode()
        self.assertNotIn('+++ b/'+QUICK_SOURCE, raw)
        for forbidden in ('NDEBUG', 'assertIsDevelopmentMode', 'superassert', 'COH_WINE_DB_LOOPBACK_ONLY'):
            self.assertNotIn(forbidden, raw)
        old = (ROOT/'upstream/ouroboros'/THREAD_SOURCE).read_text()
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary); staged_bundle(source); producer.apply_overlay(source)
            new = (source/THREAD_SOURCE).read_text()
        begin = 'uintptr_t x_beginthreadex('; end = '\nint isHexChar('
        self.assertEqual(old.split(begin,1)[0],new.split(begin,1)[0])
        self.assertEqual(old.split(end,1)[1],new.split(end,1)[1])
        THREAD_NAME_FIXTURES_RUN.add('formatter_and_asserts_retained')

    def test_typed_contract_separates_startup_metadata_from_retained_sql(self):
        self.assertEqual(producer.save_contract()['scope'], 'physical_child_row_read_witness_and_order_only')
        self.assertEqual(producer.startup_thread_name_contract()['scope'], 'x_beginthreadex_diagnostic_name_storage_only')
        package = json.loads((ROOT/producer.retained.retained.ACCEPTED_BASE_MANIFEST).read_text())
        base = producer.retained.retained.expected_receipt(base_wine_build_input=package['wine_build_input'])
        value = producer.expected_receipt(base_startup_build_input=base)
        self.assertEqual(value['patched_sha256']['DBServer/src/container_sql.c'],
            '8eaae13bf59dbee9b76ee0c3dff447eef080eb83e943f546ba0da70d0b42c295')
        THREAD_NAME_FIXTURES_RUN.add('typed_sql_contract_retained')


if __name__ == '__main__':
    if '--require-windows' in sys.argv:
        if os.name != 'nt': raise RuntimeError('Hosted native thread-start fixture must run on Windows')
        sys.argv.remove('--require-windows')
    unittest.main(verbosity=2)
