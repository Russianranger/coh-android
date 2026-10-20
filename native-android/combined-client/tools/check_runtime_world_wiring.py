#!/usr/bin/env python3
"""Extract the shipped private-init JNI hook with explicit owner/JNI doubles.

Serialize externally with flock /tmp/coh-next-build.lock. Does not execute Android
or prove imported archive identity; the FD reader and Java resolver have separate
real-file tests. Exercises this hook's accounting, atomic replacement and refusal.
"""
import argparse, hashlib, importlib.util, json, os
from pathlib import Path
import subprocess, tempfile

HARNESS=r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#define SIZE 512
#define COH_CAPTURE_SCENE_LIMIT (96u*1024u*1024u)
#define COH_CAPTURE_RESERVE 5667858u
#define JNIEXPORT
#define JNICALL
typedef int64_t jlong;typedef int32_t jint;typedef void*jclass;
typedef struct {int count;int32_t values[3];} Ints;
typedef struct {int count;int64_t values[3];} Longs;
typedef Ints*jintArray;typedef Longs*jlongArray;
struct Api;typedef const struct Api*JNIEnv;
struct Api {int(*GetArrayLength)(JNIEnv*,void*);void(*GetIntArrayRegion)(JNIEnv*,Ints*,int,int,int32_t*);void(*GetLongArrayRegion)(JNIEnv*,Longs*,int,int,int64_t*);int(*ExceptionCheck)(JNIEnv*);};
typedef struct {int fd;uint64_t offset,bytes;} CohSessionWorldFd;
typedef struct {int id;} CohSessionWorld;
typedef struct {uint32_t count;} Geometry;
typedef struct {unsigned part_count;} Scene;
typedef struct {int mutex,running,failed;uint64_t frames,contexts_started;int runtime_world_status;uint64_t runtime_world_parent_bytes,runtime_world_reads,runtime_world_bytes;char runtime_world_failure[128];Scene world,actor,walkable;Geometry world_geometry[3],actor_geometry[3],walkable_geometry[3];struct {unsigned char*p;size_t n;}assets[7];CohSessionWorld*stream_world;struct {int value;}stream_stats;} Session;
typedef struct {size_t tf_bytes;} Graphics;
static unsigned checks,calls,closed,locked;static int exception,create_ok=1,charge_ok=1;static uint64_t expected_parent;
static CohSessionWorld original={1},replacement={2};
static void check(int value){checks++;assert(value);}
static int test_lock(int*p){(void)p;assert(!locked);locked=1;return 0;}
static int test_unlock(int*p){(void)p;assert(locked);locked=0;return 0;}
#define pthread_mutex_lock test_lock
#define pthread_mutex_unlock test_unlock
static int capture_scene_charge(const Session*s,const Graphics*g,uint64_t*out){assert(s->running&&!locked);assert(g->tf_bytes==20u*13u*sizeof(float));*out=10000;return charge_ok;}
static int capture_add(uint64_t*sum,uint64_t bytes){if(*sum>COH_CAPTURE_SCENE_LIMIT||bytes>COH_CAPTURE_SCENE_LIMIT-*sum)return 0;*sum+=bytes;return 1;}
static int coh_session_world_create_fds(const void*p,size_t n,const CohSessionWorldFd f[3],uint64_t parent,CohSessionWorld**out,char*error,size_t cap){assert(!locked&&p&&n==1);calls++;assert(parent==expected_parent);assert(f[0].fd==3&&f[0].offset==11&&f[0].bytes==10144);assert(f[1].fd==4&&f[2].fd==5);if(!create_ok){snprintf(error,cap,"Known import identity mismatch");return 0;}*out=&replacement;return 1;}
static int coh_session_world_source_io(const CohSessionWorld*w,uint64_t*reads,uint64_t*bytes){assert(w==&replacement&&!locked);*reads=7;*bytes=10144;return 1;}
static void coh_session_world_destroy(CohSessionWorld**w){assert(!locked);if(*w){closed++;*w=NULL;}}
static int length(JNIEnv*e,void*a){(void)e;return *(int*)a;}
static void ints(JNIEnv*e,Ints*a,int start,int count,int32_t*out){(void)e;assert(!start&&count==3);memcpy(out,a->values,12);}
static void longs(JNIEnv*e,Longs*a,int start,int count,int64_t*out){(void)e;assert(!start&&count==3);memcpy(out,a->values,24);}
static int exceptions(JNIEnv*e){(void)e;return exception;}
/* SHIPPED */
static Session fresh(void){Session s={0};s.world.part_count=1;s.world_geometry[0].count=20;s.actor.part_count=1;s.actor_geometry[0].count=10;s.assets[6].p=(unsigned char*)"x";s.assets[6].n=1;s.stream_world=&original;return s;}
int main(void){struct Api api={length,ints,longs,exceptions};JNIEnv env=&api;Session s=fresh();Ints fd={3,{3,4,5}};Longs offsets={3,{11,0,0}},sizes={3,{10144,100000,200000}};expected_parent=10000+12345+SIZE*SIZE*4u*4u+COH_CAPTURE_RESERVE;
#define RUN() Java_org_coh_sessionclient_SessionNative_runtimeWorld(&env,NULL,(jlong)(intptr_t)&s,&fd,&offsets,&sizes,12345)
check(!Java_org_coh_sessionclient_SessionNative_runtimeWorld(&env,NULL,0,&fd,&offsets,&sizes,0));
fd.count=2;check(!RUN());fd.count=3;fd.values[1]=-1;check(!RUN());fd.values[1]=4;
offsets.values[0]=-1;check(!RUN());offsets.values[0]=11;sizes.values[0]=0;check(!RUN());sizes.values[0]=10144;
offsets.values[0]=INT64_MAX;check(!RUN());offsets.values[0]=11;exception=1;check(!RUN());exception=0;
s.running=1;check(!RUN());s.running=0;s.failed=1;check(!RUN());s.failed=0;s.frames=1;check(!RUN());s.frames=0;s.contexts_started=1;check(!RUN());s.contexts_started=0;check(calls==0&&closed==0);
charge_ok=0;check(!RUN());check(s.stream_world==&original&&!s.running&&s.runtime_world_status==-1&&strstr(s.runtime_world_failure,"inventory"));check(!RUN());charge_ok=1;
s=fresh();create_ok=0;check(!RUN());check(s.stream_world==&original&&!s.running&&s.runtime_world_status==-1&&strstr(s.runtime_world_failure,"identity"));check(closed==0&&calls==1);
s=fresh();create_ok=1;check(RUN());check(s.stream_world==&replacement&&!s.running&&s.runtime_world_status==1&&s.runtime_world_parent_bytes==expected_parent&&closed==1&&s.runtime_world_reads==7&&s.runtime_world_bytes==10144);check(!RUN());check(calls==2);
s=fresh();check(!Java_org_coh_sessionclient_SessionNative_runtimeWorld(&env,NULL,(jlong)(intptr_t)&s,&fd,&offsets,&sizes,INT64_MAX));check(s.stream_world==&original&&calls==2&&s.runtime_world_status==-1);
printf("{\"checks\":%u,\"candidate_calls\":%u,\"retired_old_owners\":%u}\n",checks,calls,closed);return 0;}
'''

def run(root,work):
    renderer=root/'native-android/session-client/app/src/main/cpp/session_renderer.c'
    activity=root/'native-android/combined-client/app/src/main/java/org/coh/nativecombined/NativeClientActivity.java'
    spec=importlib.util.spec_from_file_location('runtime_hook_extract',root/'native-android/session-client/tools/lifecycle_host_check.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    raw=renderer.read_text();body=mod.method(raw,'JNIEXPORT jint JNICALL Java_org_coh_sessionclient_SessionNative_runtimeWorld(')
    java=activity.read_text();attach=java.index('SessionNative.runtimeWorld(')
    assert java.index('RuntimeWorldInputs.open(')<attach<java.index('handle = result;',attach)
    assert 'new ImportContract.Control()' in java and 'Math.addExact(javaPayload,source.length)' in java
    assert 'finally{if(result!=0)SessionNative.destroy(result);}' in java
    assert 'runtime_world_optional_failure' in java and 'runtime_world_import_unavailable' in java
    assert body.index('coh_session_world_create_fds(')<body.index('s->stream_world=candidate')<body.index('coh_session_world_destroy(&old)')
    source=work/'runtime-hook.c';source.write_text(HARNESS.replace('/* SHIPPED */',body));results={}
    for mode,flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
        binary=work/mode;subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic',*flags,str(source),'-o',str(binary)],check=True,timeout=60)
        result=subprocess.run([str(binary)],check=True,capture_output=True,text=True,timeout=30,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'));results[mode]=json.loads(result.stdout)
    return {'passed':True,'modes':results,'source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (renderer,activity)},'leak_sanitizer_executed':False,'scope':'Actual extracted JNI body with explicit owner/JNI doubles; no Android ABI, EGL or archive identity claim'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[3]);a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='coh-runtime-hook-') as temp:result=run(a.source_root,Path(temp))
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
