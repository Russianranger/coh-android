#!/usr/bin/env python3
"""Execute production memory JNI and reused observer in release/ASan/UBSan."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
NATIVE = PROJECT.parent
JNI = PROJECT / 'app/src/main/cpp/process_memory_jni.c'
PERF = NATIVE / 'engine/perf'
HEADER = r'''
#include <stddef.h>
#define JNIEXPORT
#define JNICALL
typedef void *jclass;typedef const char *jstring;
struct JNINativeInterface_;typedef const struct JNINativeInterface_ *JNIEnv;
struct JNINativeInterface_ {jstring (*NewStringUTF)(JNIEnv *,const char *);};
'''
HARNESS = r'''
#include <jni.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "coh_process_memory.h"
static unsigned checks,mode,strings;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"JNI check %u line %u\n",checks,__LINE__);abort();}}while(0)
CohStatus __real_coh_process_memory_sample(CohProcessMemorySnapshot *);
CohStatus __real_coh_process_memory_json(const CohProcessMemorySnapshot *,char *,size_t,size_t *);
CohStatus __wrap_coh_process_memory_sample(CohProcessMemorySnapshot *s){
 if(mode==1){memset(s,0,sizeof(*s));s->rss.status=s->pss.status=s->rollup_status=s->status_file_status=COH_IO;return COH_IO;}
 return __real_coh_process_memory_sample(s);
}
CohStatus __wrap_coh_process_memory_json(const CohProcessMemorySnapshot *s,char *out,size_t cap,size_t *needed){
 if(mode==2)return COH_LIMIT;
 return __real_coh_process_memory_json(s,out,cap,needed);
}
static char saved[1024];
static jstring string(JNIEnv *env,const char *text){(void)env;strings++;CHECK(strlen(text)<sizeof(saved));memcpy(saved,text,strlen(text)+1);return mode==3?NULL:saved;}
jstring Java_org_coh_nativecombined_LocalNative_processMemory(JNIEnv *,jclass);
int main(void){
 const struct JNINativeInterface_ table={string};JNIEnv env=&table;
 CHECK(Java_org_coh_nativecombined_LocalNative_processMemory(&env,NULL)==saved);CHECK(strstr(saved,"\"scope\":\"process_memory_sample\"")!=NULL);
 mode=1;CHECK(Java_org_coh_nativecombined_LocalNative_processMemory(&env,NULL)==saved);CHECK(strstr(saved,"\"known\":false")!=NULL);CHECK(strstr(saved,"\"source\":\"unavailable\"")!=NULL);
 unsigned before=strings;mode=2;CHECK(Java_org_coh_nativecombined_LocalNative_processMemory(&env,NULL)==NULL);CHECK(strings==before);
 mode=3;CHECK(Java_org_coh_nativecombined_LocalNative_processMemory(&env,NULL)==NULL);
 for(unsigned i=0;i<100;i++){mode=i%4;jstring value=Java_org_coh_nativecombined_LocalNative_processMemory(&env,NULL);CHECK((value==NULL)==(mode>=2));}
 printf("{\"status\":\"passed\",\"checks\":%u,\"repeated_calls\":100,\"JSON_capacity\":1024,\"JNI_allocation_refusal_checked\":true}\n",checks);
 return 0;
}
'''

def run(command, **kwargs):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, **kwargs)
    if result.returncode:
        raise RuntimeError(f'{command[0]} exited {result.returncode}: {result.stdout[-2000:]}{result.stderr[-4000:]}')
    return result.stdout

def main():
    sources = [JNI, *(PERF / name for name in ('coh_process_memory.c', 'coh_perf_bridge.c', 'coh_perf.c'))]
    results = []
    leak_sanitizer = True
    with tempfile.TemporaryDirectory(prefix='coh-memory-jni-') as tmp:
        root = Path(tmp)
        (root / 'jni.h').write_text(HEADER)
        test = root / 'test.c'
        test.write_text(HARNESS)
        for mode, flags in [('release', ['-O2']), ('asan', ['-O1', '-g', '-fsanitize=address']), ('ubsan', ['-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]:
            binary = root / mode
            run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-fno-omit-frame-pointer', *flags, '-I', root, '-I', PERF, test, *sources, '-Wl,--wrap=coh_process_memory_sample,--wrap=coh_process_memory_json', '-o', binary])
            env = dict(os.environ, ASAN_OPTIONS='detect_leaks=1:abort_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
            attempt = subprocess.run([binary], capture_output=True, text=True, env=env)
            if mode == 'asan' and attempt.returncode and "Can't open /proc/" in attempt.stderr and '/task for reading' in attempt.stderr and 'LeakSanitizer has encountered a fatal error' in attempt.stderr and 'ERROR: AddressSanitizer' not in attempt.stderr:
                leak_sanitizer = False
                env['ASAN_OPTIONS'] = 'detect_leaks=0:abort_on_error=1'
                result = json.loads(run([binary], env=env))
            else:
                if attempt.returncode: raise RuntimeError(f'{mode} exited {attempt.returncode}: {attempt.stderr[-4000:]}')
                result = json.loads(attempt.stdout)
            result['mode']=mode;results.append(result)
    print(json.dumps({'schema':'coh-combined-memory-jni-host-v1','passed':True,'modes':results,
                     'sources_sha256':{str(path.relative_to(NATIVE.parent)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
                     'JNI_table':'host minimal shim; actual Android ABI/build/execution are separate gates',
                     'leak_sanitizer_enabled':leak_sanitizer,
                     'leak_sanitizer_blocker':None if leak_sanitizer else 'Host denies LeakSanitizer /proc/PID/task inspection; AddressSanitizer passed with leak detection disabled',
                     'physical_Thor_qualified':False,'world_authority':False}))

if __name__ == '__main__':
    main()
