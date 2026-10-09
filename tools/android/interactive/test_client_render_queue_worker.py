"""Execute the staged worker queue with real Win32 events and race barriers.

The portable event adapter is local coverage only. Formal qualification requires
MSVC Win32 and runs the same complete staged WorkerThread implementation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT / 'tools')]
WORKER = 'libs/UtilitiesLib/src/components/WorkerThread.c'
HEADER = 'libs/UtilitiesLib/include/utilitieslib/components/WorkerThread.h'
OPTIONS = ['/O2', '/Oy-', '/MT', '/TC']
MARKER = 'ACTUAL_WORKER_QUEUE_RACES_BURST_RING_LIFECYCLE_PASS'


def staged_sources():
    import test_client_render_queue_source as source
    current = source.sources()[1]
    return current[WORKER], current[HEADER]


def normalized_digest(text):
    return hashlib.sha256(text.replace('\r\n', '\n').encode()).hexdigest()


def adapters(production=False):
    common = ('' if production else '#define _POSIX_C_SOURCE 200809L\n') + r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <malloc.h>
'''
    if production:
        common += r'''
#include <windows.h>
#ifdef _WIN64
#error Genuine worker qualification must target Win32
#endif
'''
    else:
        common += r'''
#include <pthread.h>
#include <errno.h>
#include <time.h>
#include <alloca.h>
#define _alloca alloca
#define __declspec(x)
#define __stdcall
#define WINAPI
typedef uint32_t DWORD;
typedef int32_t LONG;
typedef int BOOL;
typedef void *LPVOID;
typedef struct {long long QuadPart;} LARGE_INTEGER;
typedef pthread_mutex_t CRITICAL_SECTION;
#define INFINITE 0xffffffffu
#define WAIT_OBJECT_0 0u
#define WAIT_TIMEOUT 258u
typedef struct TestHandle {
    pthread_mutex_t mutex;
    pthread_cond_t condition;
    pthread_t thread;
    int thread_kind,manual,signaled,done;
    DWORD id,result;
    DWORD (*entry)(LPVOID);
    LPVOID argument;
} *HANDLE;
static _Thread_local DWORD test_thread_id;
static _Thread_local HANDLE test_thread_handle;
static volatile LONG test_next_id;
static LONG InterlockedExchange(volatile LONG *p,LONG value) {return __sync_lock_test_and_set(p,value);}
static LONG InterlockedCompareExchange(volatile LONG *p,LONG value,LONG expected) {return __sync_val_compare_and_swap(p,expected,value);}
static LONG InterlockedIncrement(volatile LONG *p) {return __sync_add_and_fetch(p,1);}
static DWORD GetCurrentThreadId(void) {
    if(!test_thread_id)test_thread_id=(DWORD)InterlockedIncrement(&test_next_id);
    return test_thread_id;
}
static HANDLE test_handle(void) {
    HANDLE h=calloc(1,sizeof(*h));assert(h);
    assert(!pthread_mutex_init(&h->mutex,NULL));assert(!pthread_cond_init(&h->condition,NULL));return h;
}
static HANDLE CreateEvent(void *security,BOOL manual,BOOL initial,const char *name) {
    HANDLE h=test_handle();(void)security;(void)name;h->manual=manual;h->signaled=initial;return h;
}
static BOOL SetEvent(HANDLE h) {
    assert(h);assert(!pthread_mutex_lock(&h->mutex));h->signaled=1;
    assert(!pthread_cond_broadcast(&h->condition));assert(!pthread_mutex_unlock(&h->mutex));return 1;
}
static BOOL ResetEvent(HANDLE h) {
    assert(h);assert(!pthread_mutex_lock(&h->mutex));h->signaled=0;assert(!pthread_mutex_unlock(&h->mutex));return 1;
}
static DWORD WaitForSingleObject(HANDLE h,DWORD timeout) {
    struct timespec until;int error=0;assert(h);assert(timeout!=INFINITE);
    assert(!clock_gettime(CLOCK_REALTIME,&until));until.tv_sec+=timeout/1000;
    until.tv_nsec+=(long)(timeout%1000)*1000000L;
    if(until.tv_nsec>=1000000000L){until.tv_sec++;until.tv_nsec-=1000000000L;}
    assert(!pthread_mutex_lock(&h->mutex));
    while(!(h->thread_kind?h->done:h->signaled) && !error)
        error=pthread_cond_timedwait(&h->condition,&h->mutex,&until);
    assert(error==0 || error==ETIMEDOUT);
    if(!error && !h->thread_kind && !h->manual)h->signaled=0;
    assert(!pthread_mutex_unlock(&h->mutex));return error?WAIT_TIMEOUT:WAIT_OBJECT_0;
}
static void test_thread_done(HANDLE h,DWORD result) {
    assert(h && !pthread_mutex_lock(&h->mutex));h->done=1;h->result=result;
    assert(!pthread_cond_broadcast(&h->condition));assert(!pthread_mutex_unlock(&h->mutex));
}
static void *test_thread_entry(void *argument) {
    HANDLE h=argument;DWORD result;test_thread_handle=h;test_thread_id=h->id;
    result=h->entry(h->argument);test_thread_done(h,result);return NULL;
}
static HANDLE CreateThread(void *security,size_t stack,DWORD (*entry)(LPVOID),LPVOID argument,DWORD flags,DWORD *id) {
    HANDLE h=test_handle();(void)security;(void)stack;(void)flags;h->thread_kind=1;
    h->id=(DWORD)InterlockedIncrement(&test_next_id);h->entry=entry;h->argument=argument;
    if(id)*id=h->id;
    assert(!pthread_create(&h->thread,NULL,test_thread_entry,h));return h;
}
static void ExitThread(DWORD result) {test_thread_done(test_thread_handle,result);pthread_exit(NULL);}
static BOOL CloseHandle(HANDLE h) {
    assert(h);if(h->thread_kind)assert(!pthread_join(h->thread,NULL));
    assert(!pthread_cond_destroy(&h->condition));assert(!pthread_mutex_destroy(&h->mutex));free(h);return 1;
}
static void Sleep(DWORD ms) {
    struct timespec span={(time_t)(ms/1000),(long)(ms%1000)*1000000L};
    while(nanosleep(&span,&span))assert(errno==EINTR);
}
static BOOL QueryPerformanceFrequency(LARGE_INTEGER *value) {value->QuadPart=1000000000LL;return 1;}
static BOOL QueryPerformanceCounter(LARGE_INTEGER *value) {
    struct timespec now;assert(!clock_gettime(CLOCK_MONOTONIC,&now));
    value->QuadPart=(long long)now.tv_sec*1000000000LL+now.tv_nsec;return 1;
}
static BOOL InitializeCriticalSectionAndSpinCount(CRITICAL_SECTION *p,DWORD spin) {(void)spin;assert(!pthread_mutex_init(p,NULL));return 1;}
static void DeleteCriticalSection(CRITICAL_SECTION *p) {assert(!pthread_mutex_destroy(p));}
static void EnterCriticalSection(CRITICAL_SECTION *p) {assert(!pthread_mutex_lock(p));}
static void LeaveCriticalSection(CRITICAL_SECTION *p) {assert(!pthread_mutex_unlock(p));}
'''
    return common + r'''
typedef uint8_t U8;
typedef uint32_t U32;
typedef uint64_t U64;
#ifndef __cplusplus
#define bool int
#define true 1
#define false 0
#endif
#define INLINEDBG __inline
#define ZeroStruct(p) memset((p),0,sizeof(*(p)))
#define EXCEPTION_HANDLER_BEGIN
#define EXCEPTION_HANDLER_END
static void test_failure(const char *expression,const char *file,int line) {
    fprintf(stderr,"WORKER_FIXTURE_ASSERT %s:%d: %s\n",file,line,expression);fflush(stderr);exit(91);
}
#undef assert
#define assert(expression) ((expression)?(void)0:test_failure(#expression,__FILE__,__LINE__))
'''


def interceptors():
    return r'''
/* These barriers intercept only Win32 boundaries. Queue storage, publication,
 * dispatch, coalescing and all lifecycle functions below are staged source. */
static HANDLE test_queue_event,test_arrived,test_release,test_signal_arrived,test_signal_release,test_cas_arrived,test_cas_release;
static volatile LONG test_reset_gate,test_wait_gate,test_signal_gate,test_signals,test_signal_attempts,test_fail_signal;
static volatile LONG *test_wake_target;
static volatile LONG test_wake_cas,test_wake_exchanges,test_qpc,test_qpf,test_fail_qpc;
static volatile LONG test_cas_gate;
static LONG test_InterlockedCompareExchange(volatile LONG *target,LONG value,LONG expected) {
    if(target==test_wake_target) {
        InterlockedIncrement(&test_wake_cas);
        if(InterlockedCompareExchange(&test_cas_gate,0,1)==1) {
            assert(SetEvent(test_cas_arrived));assert(WaitForSingleObject(test_cas_release,10000)==WAIT_OBJECT_0);
        }
    }
    return InterlockedCompareExchange(target,value,expected);
}
static LONG test_InterlockedExchange(volatile LONG *target,LONG value) {
    if(target==test_wake_target)InterlockedIncrement(&test_wake_exchanges);
    return InterlockedExchange(target,value);
}
static BOOL test_QueryPerformanceCounter(LARGE_INTEGER *value) {
    InterlockedIncrement(&test_qpc);
    if(InterlockedCompareExchange(&test_fail_qpc,0,1)==1)return 0;
    return QueryPerformanceCounter(value);
}
static BOOL test_QueryPerformanceFrequency(LARGE_INTEGER *value) {
    InterlockedIncrement(&test_qpf);return QueryPerformanceFrequency(value);
}
static void test_barrier(void) {
    assert(SetEvent(test_arrived));assert(WaitForSingleObject(test_release,10000)==WAIT_OBJECT_0);
}
static BOOL test_ResetEvent(HANDLE h) {
    BOOL result;
    if(h==test_queue_event && InterlockedCompareExchange(&test_reset_gate,0,1)==1)test_barrier();
    result=ResetEvent(h);
    if(h==test_queue_event && InterlockedCompareExchange(&test_reset_gate,0,2)==2)test_barrier();
    return result;
}
static BOOL test_SetEvent(HANDLE h) {
    if(h==test_queue_event) {
        InterlockedIncrement(&test_signal_attempts);
        if(InterlockedCompareExchange(&test_fail_signal,0,1)==1)return 0;
        if(InterlockedCompareExchange(&test_signal_gate,0,1)==1) {
            assert(SetEvent(test_signal_arrived));assert(WaitForSingleObject(test_signal_release,10000)==WAIT_OBJECT_0);
        }
        InterlockedIncrement(&test_signals);
    }
    return SetEvent(h);
}
static DWORD test_WaitForSingleObject(HANDLE h,DWORD timeout) {
    DWORD result;
    if(h==test_queue_event && InterlockedCompareExchange(&test_wait_gate,0,1)==1)test_barrier();
    if(timeout==INFINITE)timeout=10000;
    result=WaitForSingleObject(h,timeout);
    if(h==test_queue_event)assert(result==WAIT_OBJECT_0);
    return result;
}
#pragma push_macro("ResetEvent")
#pragma push_macro("SetEvent")
#pragma push_macro("WaitForSingleObject")
#pragma push_macro("InterlockedCompareExchange")
#pragma push_macro("InterlockedExchange")
#pragma push_macro("QueryPerformanceCounter")
#pragma push_macro("QueryPerformanceFrequency")
#undef ResetEvent
#undef SetEvent
#undef WaitForSingleObject
#undef InterlockedCompareExchange
#undef InterlockedExchange
#undef QueryPerformanceCounter
#undef QueryPerformanceFrequency
#define ResetEvent test_ResetEvent
#define SetEvent test_SetEvent
#define WaitForSingleObject test_WaitForSingleObject
#define InterlockedCompareExchange test_InterlockedCompareExchange
#define InterlockedExchange test_InterlockedExchange
#define QueryPerformanceCounter test_QueryPerformanceCounter
#define QueryPerformanceFrequency test_QueryPerformanceFrequency
'''


def scenarios():
    return r'''
#pragma pop_macro("QueryPerformanceFrequency")
#pragma pop_macro("QueryPerformanceCounter")
#pragma pop_macro("InterlockedExchange")
#pragma pop_macro("InterlockedCompareExchange")
#pragma pop_macro("WaitForSingleObject")
#pragma pop_macro("SetEvent")
#pragma pop_macro("ResetEvent")
typedef struct TestCommand {U32 sequence,checksum;} TestCommand;
static volatile LONG test_delivered,test_messages,test_debug_calls,test_stalls;
static U32 test_expected_sequence;
static void test_dispatch(void *unused,int type,void *data) {
    TestCommand *command=data;(void)unused;assert(type==WT_CMD_USER_START);
    assert(command->sequence==test_expected_sequence++);
    assert(command->checksum==(command->sequence^0x5a37c921u));InterlockedIncrement(&test_delivered);
}
static void test_message(void *unused,int type,void *data) {
    (void)unused;assert(type==WT_CMD_USER_START && *(U32*)data==0xab31u);InterlockedIncrement(&test_messages);
}
static void test_stall(void) {InterlockedIncrement(&test_stalls);}
static void test_debug(void *data) {assert(*(U32*)data==0xbb13u);InterlockedIncrement(&test_debug_calls);}
static void test_until(volatile LONG *value,LONG target) {
    unsigned i;for(i=0;i<10000 && *value!=target;++i)Sleep(1);assert(*value==target);
}
static void test_gates(void) {
    test_queue_event=NULL;test_reset_gate=test_wait_gate=test_signal_gate=test_signals=test_signal_attempts=test_fail_signal=0;
    test_wake_target=NULL;test_wake_cas=test_wake_exchanges=test_qpc=test_qpf=test_fail_qpc=test_cas_gate=0;
    test_delivered=test_messages=test_debug_calls=test_stalls=0;test_expected_sequence=0;
    test_arrived=CreateEvent(NULL,0,0,NULL);test_release=CreateEvent(NULL,0,0,NULL);
    test_signal_arrived=CreateEvent(NULL,0,0,NULL);test_signal_release=CreateEvent(NULL,0,0,NULL);
    test_cas_arrived=CreateEvent(NULL,0,0,NULL);test_cas_release=CreateEvent(NULL,0,0,NULL);
    assert(test_arrived && test_release && test_signal_arrived && test_signal_release && test_cas_arrived && test_cas_release);
}
static void test_close_gates(void) {
    test_queue_event=NULL;test_wake_target=NULL;CloseHandle(test_arrived);CloseHandle(test_release);
    CloseHandle(test_signal_arrived);CloseHandle(test_signal_release);
    CloseHandle(test_cas_arrived);CloseHandle(test_cas_release);
}
static WorkerThread *test_worker(int enabled,int diagnostics,int blocks,int threaded) {
    WorkerThread *wt=wtCreate(test_dispatch,blocks,test_message,test_stall,64,NULL);
    wtSetThreaded(wt,threaded);if(enabled)wtEnableWakeCoalescing(wt,diagnostics);
    if(threaded) {
        unsigned i;wtStart(wt);for(i=0;i<10000 && !wt->data_queued;++i)Sleep(1);assert(wt->data_queued);
        test_queue_event=wt->data_queued;
        test_wake_target=&wt->thread_asleep;
    }
    return wt;
}
static void test_enqueue(WorkerThread *wt,U32 sequence) {
    TestCommand command={sequence,sequence^0x5a37c921u};wtQueueCmd(wt,WT_CMD_USER_START,&command,sizeof(command));
}
static void test_pause(WorkerThread *wt,int gate) {
    if(gate==1 || gate==2)InterlockedExchange(&test_reset_gate,gate);
    else InterlockedExchange(&test_wait_gate,1);
    /* Control wake moves an already sleeping worker into the selected window. */
    assert(SetEvent(wt->data_queued));assert(WaitForSingleObject(test_arrived,10000)==WAIT_OBJECT_0);
}
static void test_finish(WorkerThread *wt,LONG count) {
    test_until(&test_delivered,count);wtFlush(wt);assert(wt->cmd_queue.start==wt->cmd_queue.end);
    wtDestroy(wt);test_close_gates();
}
static void test_burst(int enabled,int diagnostics) {
    WorkerThread *wt;LONG before,cas_before,exchange_before;unsigned i;WTRenderQueueStats stats;
    test_gates();wt=test_worker(enabled,diagnostics,8192,1);test_pause(wt,3);before=test_signals;
    cas_before=test_wake_cas;exchange_before=test_wake_exchanges;
    for(i=0;i<1024;++i)test_enqueue(wt,i);
    assert(test_signals-before==(enabled?1:1024));
    assert(test_wake_cas-cas_before==(enabled?1:0) && test_wake_exchanges==exchange_before);
    assert(test_qpc==0 && test_qpf==(enabled && diagnostics?1:0));
    wtGetRenderQueueStats(wt,&stats);
    if(enabled && diagnostics)assert(stats.commands==1024 && stats.wake_signals==1 && stats.pending_commands==1023);
    assert(SetEvent(test_release));test_finish(wt,1024);
}
static void test_publication_windows(void) {
    int gate;unsigned cycle;for(gate=1;gate<=3;++gate) {
        WorkerThread *wt;test_gates();wt=test_worker(1,1,128,1);
        for(cycle=0;cycle<24;++cycle) {
            test_pause(wt,gate);test_enqueue(wt,cycle);assert(SetEvent(test_release));test_until(&test_delivered,(LONG)cycle+1);
        }
        test_finish(wt,24);
    }
}
static DWORD WINAPI test_one_publisher(void *value) {test_enqueue(value,0);return 0;}
static void test_delayed_signal(void) {
    WorkerThread *wt;HANDLE producer;unsigned i;
    test_gates();wt=test_worker(1,1,128,1);test_pause(wt,2);
    /* Worker is paused after reset, before recheck. The first publisher claims
     * the armed flag then stops before native SetEvent. */
    InterlockedExchange(&test_signal_gate,1);producer=CreateThread(NULL,0,test_one_publisher,wt,0,NULL);assert(producer);
    assert(WaitForSingleObject(test_signal_arrived,10000)==WAIT_OBJECT_0);
    /* Separate release events resume only the worker; the publisher stays at
     * its signal barrier. The recheck must consume published work unaided. */
    assert(SetEvent(test_release));test_until(&test_delivered,1);
    for(i=0;i<10000 && wt->thread_asleep!=1;++i)Sleep(1);
    assert(wt->thread_asleep==1);
    assert(SetEvent(test_signal_release));assert(WaitForSingleObject(producer,10000)==WAIT_OBJECT_0);CloseHandle(producer);
    test_enqueue(wt,1);test_finish(wt,2);
}
static void test_signal_failure_retry(void) {
    WorkerThread *wt;WTRenderQueueStats stats;
    test_gates();wt=test_worker(1,1,128,1);test_pause(wt,3);
    InterlockedExchange(&test_fail_signal,1);test_enqueue(wt,0);
    assert(wt->thread_asleep==1 && test_signals==0 && test_signal_attempts==1);
    test_enqueue(wt,1);assert(test_signals==1 && test_signal_attempts==2);
    wtGetRenderQueueStats(wt,&stats);assert(stats.wake_signal_failures==1 && stats.wake_signals==1);
    assert(SetEvent(test_release));test_finish(wt,2);
}
static void test_consumed_command_late_claim_before_reset(void) {
    WorkerThread *wt;HANDLE producer;LONG before;
    test_gates();wt=test_worker(1,1,128,1);test_pause(wt,2);
    /* Publish command0, but suspend its notification CAS. The consumer sees
     * the queue directly, consumes0, and arms the next idle cycle. */
    InterlockedExchange(&test_cas_gate,1);
    producer=CreateThread(NULL,0,test_one_publisher,wt,0,NULL);assert(producer);
    assert(WaitForSingleObject(test_cas_arrived,10000)==WAIT_OBJECT_0);
    InterlockedExchange(&test_reset_gate,1);assert(SetEvent(test_release));
    test_until(&test_delivered,1);assert(WaitForSingleObject(test_arrived,10000)==WAIT_OBJECT_0);
    /* Its late claim now signals the NEXT armed cycle, before that cycle's
     * ResetEvent. That native reset erases the old event, so the post-reset
     * rearm must make the following command eligible to notify again. */
    assert(SetEvent(test_cas_release));assert(WaitForSingleObject(producer,10000)==WAIT_OBJECT_0);CloseHandle(producer);
    InterlockedExchange(&test_wait_gate,1);assert(SetEvent(test_release));
    assert(WaitForSingleObject(test_arrived,10000)==WAIT_OBJECT_0);
    assert(wt->thread_asleep==1 && "late_consumed_command_next_wake_rearm");
    before=test_signals;test_enqueue(wt,1);assert(test_signals==before+1);
    assert(SetEvent(test_release));test_finish(wt,2);
}
static void test_unthreaded(void) {
    int enabled;for(enabled=0;enabled<=1;++enabled) {
        WorkerThread *wt;unsigned i;test_gates();wt=test_worker(enabled,1,128,0);
        for(i=0;i<256;++i){test_enqueue(wt,i);assert(test_delivered==(LONG)i+1);}
        assert(!test_signals);test_finish(wt,256);
    }
}
static DWORD WINAPI test_ring_publisher(void *value) {
    WorkerThread *wt=value;U32 i;for(i=7;i<3000;++i) {
        U32 size=(U32)sizeof(QueuedCmd)*(1+i%3);TestCommand *command=wtAllocCmd(wt,WT_CMD_USER_START,(int)size);
        command->sequence=i;command->checksum=i^0x5a37c921u;wtSendCmd(wt);
    }
    return 0;
}
static void test_ring_and_lifecycle(void) {
    WorkerThread *wt;HANDLE producer;unsigned i;U32 message=0xab31u,debug=0xbb13u;WTRenderQueueStats stats;
    TestCommand *large;
    test_gates();wt=test_worker(1,1,16,1);test_pause(wt,3);
    for(i=0;i<7;++i)test_enqueue(wt,i);
    InterlockedExchange(&test_fail_qpc,1);
    producer=CreateThread(NULL,0,test_ring_publisher,wt,0,NULL);assert(producer);
    /* The consumer remains paused until a real allocation is blocked. */
    for(i=0;i<10000 && !test_stalls;++i)Sleep(1);
    assert(test_stalls);
    assert(SetEvent(test_release));assert(WaitForSingleObject(producer,10000)==WAIT_OBJECT_0);CloseHandle(producer);
    wtFlush(wt);assert(test_delivered==3000);
    /* A cancelled heap-backed allocation must not dispatch or leak ownership. */
    large=wtAllocCmd(wt,WT_CMD_USER_START,4096);assert(large);wtCancelCmd(wt);
    large=wtAllocCmd(wt,WT_CMD_USER_START,4096);assert(large);large->sequence=3000;large->checksum=3000^0x5a37c921u;wtSendCmd(wt);
    wtQueueDebugCmd(wt,test_debug,&debug,sizeof(debug));wtFlush(wt);assert(test_debug_calls==1);
    wtQueueMsg(wt,WT_CMD_USER_START,&message,sizeof(message));wtMonitor(wt);assert(test_messages==1);
    wtGetRenderQueueStats(wt,&stats);assert(stats.commands>=3002);
    assert(stats.ring_waits && stats.ring_wait_iterations>=stats.ring_waits && stats.ring_wait_wall_ms>=0);
    assert(stats.ring_wait_clock_failures==1 && (U64)test_qpc<=stats.ring_waits*2);
    test_finish(wt,3001);
    /* Destruction while idle must use its unchanged unconditional control wake. */
    test_gates();wt=test_worker(1,0,128,1);
    for(i=0;i<10000 && wt->thread_asleep!=1;++i)Sleep(1);
    assert(wt->thread_asleep==1);
    wtDestroy(wt);test_close_gates();
}
int main(void) {
    test_burst(0,0);test_burst(1,0);test_burst(1,1);
    test_publication_windows();test_delayed_signal();test_signal_failure_retry();
    test_consumed_command_late_claim_before_reset();test_unthreaded();test_ring_and_lifecycle();
    puts("ACTUAL_WORKER_QUEUE_RACES_BURST_RING_LIFECYCLE_PASS");return 0;
}
'''


def harness(production=False):
    worker, header = staged_sources()
    # Only include adapters differ. All worker statements and the actual public
    # queue API/struct declaration remain byte-for-byte staged native source.
    stripped_worker = re.sub(r'^#include[^\n]*\n', '', worker, flags=re.M)
    stripped_header = re.sub(r'^#include[^\n]*\n', '', header, flags=re.M)
    return adapters(production) + stripped_header + interceptors() + stripped_worker + scenarios()


def compile_harness(directory, windows=False, post_reset_rearm=True):
    directory = Path(directory)
    source = directory / 'worker-queue.c'
    production = os.name == 'nt'
    if windows and not production:
        raise ValueError('Formal worker qualification requires real Win32 MSVC')
    text = harness(production)
    if not post_reset_rearm:
        rearm = ('                if (wt->wake_coalescing) InterlockedExchange(&wt->thread_asleep, 1);\n'
                 '                cmd = peekStoredCmd(&wt->cmd_queue);')
        if text.count(rearm) != 1:
            raise ValueError('Exact post-reset rearm mutation required for negative control')
        text = text.replace(rearm, '                cmd = peekStoredCmd(&wt->cmd_queue);')
    source.write_text(text)
    if production:
        compiler = shutil.which('cl')
        if not compiler:
            raise ValueError('Real Win32 MSVC required')
        binary = source.with_suffix('.exe')
        command = [compiler, '/nologo', *OPTIONS, str(source), '/Fe:' + str(binary)]
    else:
        compiler = shutil.which('cc') or shutil.which('gcc')
        if not compiler:
            raise ValueError('C compiler required')
        binary = source.with_suffix('')
        command = [compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
            '-Wno-sign-compare', '-Wno-parentheses', '-Wno-unused-but-set-variable',
            '-pthread', str(source), '-o', str(binary)]
    result = subprocess.run(command, cwd=directory, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('Actual worker fixture compilation failed:\n' + result.stdout + result.stderr)
    if windows:
        from package_reference_runtime import file_record
        if file_record(binary)['pe_machine'] != 332:
            raise ValueError('Actual worker fixture must target Win32')
    return binary


def run_checks(binary):
    result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=45)
    if result.returncode or MARKER not in result.stdout:
        raise RuntimeError('Actual worker fixture failed:\n' + result.stdout + result.stderr)
    return result.stdout


def run_negative_control(binary):
    result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=45)
    if result.returncode != 91 or 'late_consumed_command_next_wake_rearm' not in result.stderr:
        raise RuntimeError('Actual worker race negative control did not fail at the expected wake:\n'
            + result.stdout + result.stderr)
    return True


def worker_checks():
    worker, header = staged_sources()
    return {'format': 1, 'status': 'passed', 'platform': 'windows', 'architecture': 'Win32',
        'configuration': 'OptDebug', 'compiler_options': OPTIONS,
        'source_sha256': normalized_digest(worker), 'header_sha256': normalized_digest(header),
        'harness_sha256': normalized_digest(harness()),
        'production_harness_sha256': normalized_digest(harness(True)),
        'actual_staged_worker_body_and_api_verified': True,
        'real_win32_auto_reset_events_and_threads_required': True,
        'publication_before_reset_after_reset_and_before_wait_verified': True,
        'repeated_idle_publication_cycles': 72,
        'burst_commands_per_case': 1024, 'legacy_burst_signal_count': 1024,
        'coalesced_burst_signal_count': 1,
        'coalesced_burst_locked_producer_operations': 1,
        'fitting_burst_no_per_command_clock_or_locked_pending_operations_verified': True,
        'diagnostics_disabled_and_enabled_same_dispatch_verified': True,
        'delayed_claim_to_signal_across_consumer_rearm_verified': True,
        'consumed_command_late_claim_before_next_reset_and_following_wake_verified': True,
        'missing_post_reset_rearm_actual_worker_negative_control_rejected': True,
        'failed_signal_rearms_pending_retry_verified': True,
        'unthreaded_immediate_ordered_dispatch_verified': True,
        'small_ring_wrap_pressure_heap_cancel_debug_messages_verified': True,
        'ring_clock_failure_nonfatal_and_at_most_two_queries_per_block_verified': True,
        'flush_monitor_idle_destruction_and_control_wakes_verified': True,
        'barriers_and_process_waits_bounded': True,
        'physical_fps_gain_validated': False}


def windows_receipt(output=None):
    with tempfile.TemporaryDirectory(prefix='coh-win32-worker-') as directory:
        run_checks(compile_harness(directory, windows=True))
        run_negative_control(compile_harness(directory, windows=True, post_reset_rearm=False))
    document = worker_checks()
    if output is not None:
        output = Path(output)
        if output.exists() or output.is_symlink():
            raise ValueError('Fresh actual worker Win32 proof required')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(document, indent=2) + '\n')
    return document


class WorkerNativeTests(unittest.TestCase):
    def test_actual_staged_worker_queue_races_bursts_and_lifecycle(self):
        with tempfile.TemporaryDirectory(prefix='coh-worker-native-') as directory:
            self.assertIn(MARKER, run_checks(compile_harness(directory)))

    def test_formal_worker_proof_refuses_portable_simulation(self):
        if os.name == 'nt':
            return
        with tempfile.TemporaryDirectory(prefix='coh-worker-formal-') as directory:
            path = Path(directory) / 'proof.json'
            with self.assertRaisesRegex(ValueError, 'real Win32'):
                windows_receipt(path)
            self.assertFalse(path.exists())

    def test_actual_worker_rejects_missing_post_reset_rearm_at_exact_cross_cycle_wake(self):
        with tempfile.TemporaryDirectory(prefix='coh-worker-regression-') as directory:
            self.assertTrue(run_negative_control(compile_harness(directory, post_reset_rearm=False)))


if __name__ == '__main__':
    if '--windows-qualify' in sys.argv:
        parser = argparse.ArgumentParser()
        parser.add_argument('--windows-qualify', action='store_true')
        parser.add_argument('--output', type=Path, required=True)
        arguments = parser.parse_args()
        windows_receipt(arguments.output)
    else:
        unittest.main()
