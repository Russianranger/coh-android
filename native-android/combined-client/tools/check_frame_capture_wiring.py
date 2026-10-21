#!/usr/bin/env python3
"""Exercise shipped capture accounting/JNI bodies with explicit host doubles.

Run externally under /tmp/coh-next-build.lock. This checker does not acquire a
lock, build an Android ABI, execute EGL/GL, or measure application memory peaks.
Source assertions cover the surrounding render/activity wiring separately.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


HARNESS = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "session_frame_capture.h"
#define SIZE 512
/* Deliberately thin host storage types: sizeof values are not Android ABI facts. */
typedef struct { float fields[10]; } Vertex;
typedef struct { float fields[9]; } CohMeshVertex;
typedef struct { uint32_t count,index_count; } Geometry;
typedef struct { uint64_t bytes; } Texture;
typedef struct { unsigned part_count,texture_count; Texture textures[3]; } Scene;
typedef struct { uint64_t cpu,gpu; int candidate; } CohSessionWorld;
typedef struct { uint64_t owned; } WalkWorld;
struct CohFrameCapture { const uint8_t *bytes; size_t size; uint64_t frame; };
typedef struct {
 int mutex; uint64_t epoch,frames,capture_view_epoch,capture_lock_frame,capture_draws; uint32_t capture_view_width,capture_view_height; struct { size_t n; } assets[7];
 Scene world,actor,walkable; Geometry world_geometry[3],actor_geometry[3],walkable_geometry[3];
 CohSessionWorld *stream_world; WalkWorld walk_world; CohFrameCapture *frame_capture;
} Session;
typedef struct { size_t tf_bytes; } Graphics;
static unsigned checks,world_calls,lock_depth,locks,unlocks,allocations,frees,new_calls,set_calls;
static int source_ok=1,malloc_fails,new_fails,mutate_on_new;
static void *outstanding;
static uint64_t requested_after;
static uint8_t raw_bytes[COH_CAPTURE_BYTES],java_bytes[COH_CAPTURE_BYTES];
static void check(int condition){checks++;assert(condition);}
/* Explicit source-owner refusal double, including candidate-in-progress. */
static int coh_session_world_owned_bytes(const CohSessionWorld*w,uint64_t*cpu,uint64_t*gpu){
 world_calls++;if(!source_ok||!w||w->candidate)return 0;*cpu=w->cpu;*gpu=w->gpu;return 1;
}
static size_t coh_walk_world_owned_bytes(const WalkWorld*w){return (size_t)w->owned;}
static int test_lock(int*m){(void)m;assert(lock_depth==0);lock_depth=1;locks++;return 0;}
static int test_unlock(int*m){(void)m;assert(lock_depth==1);lock_depth=0;unlocks++;return 0;}
static void *test_malloc(size_t n){
 assert(n==COH_CAPTURE_BYTES&&!outstanding);allocations++;
 if(malloc_fails)return NULL;
 outstanding=malloc(n);assert(outstanding);return outstanding;
}
static void test_free(void*p){assert(p&&p==outstanding);frees++;free(p);outstanding=NULL;}
const uint8_t *coh_frame_capture_data(const CohFrameCapture*c,size_t*size,uint64_t after){
 assert(lock_depth==1);requested_after=after;
 if(!c||c->frame<=after)return NULL;
 *size=c->size;return c->bytes;
}
typedef int64_t jlong;
typedef int32_t jsize;
typedef int32_t jint;
typedef signed char jbyte;
typedef void *jclass;
typedef uint8_t *jbyteArray;
struct JNINativeInterface_;
typedef const struct JNINativeInterface_ *JNIEnv;
struct JNINativeInterface_ {
 jbyteArray (*NewByteArray)(JNIEnv*,jsize);
 void (*SetByteArrayRegion)(JNIEnv*,jbyteArray,jsize,jsize,const jbyte*);
};
static jbyteArray new_array(JNIEnv*e,jsize n){
 (void)e;assert(lock_depth==0);assert(n>0&&n<=(jsize)COH_CAPTURE_BYTES);new_calls++;
 if(mutate_on_new)memset(raw_bytes,0xee,sizeof raw_bytes);
 return new_fails?NULL:java_bytes;
}
static void set_array(JNIEnv*e,jbyteArray out,jsize start,jsize n,const jbyte*copy){
 (void)e;assert(lock_depth==0&&out==java_bytes&&start==0);assert((const void*)copy==outstanding);
 set_calls++;memcpy(out,copy,(size_t)n);
}
#define JNIEXPORT
#define JNICALL
#define pthread_mutex_lock test_lock
#define pthread_mutex_unlock test_unlock
#define malloc test_malloc
#define free test_free
/* SHIPPED_METHODS */
#undef malloc
#undef free

static uint64_t expected_charge(const Session*s,const Graphics*g){
 uint64_t total=s->stream_world->cpu+s->stream_world->gpu+2u*sizeof(Session)+sizeof(Graphics)+s->walk_world.owned;
 for(unsigned i=0;i<7;i++)total+=s->assets[i].n;
 const Scene*scenes[]={&s->world,&s->actor,&s->walkable};
 const Geometry*sets[]={s->world_geometry,s->actor_geometry,s->walkable_geometry};
 for(unsigned set=0;set<3;set++){
  for(unsigned i=0;i<scenes[set]->part_count;i++){
   const Geometry*m=sets[set]+i;
   total+=(uint64_t)m->count*(2u*sizeof(Vertex)+sizeof(CohMeshVertex))+(uint64_t)m->index_count*8u;
  }
  for(unsigned i=0;i<scenes[set]->texture_count;i++)total+=scenes[set]->textures[i].bytes;
 }
 return total+(uint64_t)SIZE*SIZE*8u+4u+g->tf_bytes;
}
static void accounting(void){
 uint64_t sum=COH_CAPTURE_SCENE_LIMIT-1;
 check(capture_add(&sum,1)&&sum==COH_CAPTURE_SCENE_LIMIT);
 check(!capture_add(&sum,1)&&sum==COH_CAPTURE_SCENE_LIMIT);
 check(capture_add(&sum,0));
 sum=COH_CAPTURE_SCENE_LIMIT+1u;check(!capture_add(&sum,0)&&sum==COH_CAPTURE_SCENE_LIMIT+1u);
 sum=UINT64_MAX;check(!capture_add(&sum,1)&&sum==UINT64_MAX);
 sum=1;check(!capture_add(&sum,UINT64_MAX)&&sum==1);
 CohSessionWorld world={101,202,0};Session s={0};Graphics g={1234};s.stream_world=&world;s.walk_world.owned=303;
 s.world.part_count=2;s.actor.part_count=1;s.walkable.part_count=1;
 s.world.texture_count=2;s.actor.texture_count=1;s.walkable.texture_count=1;
 for(unsigned i=0;i<7;i++)s.assets[i].n=i+11;
 s.world_geometry[0]=(Geometry){2,3};s.world_geometry[1]=(Geometry){5,7};
 s.actor_geometry[0]=(Geometry){11,13};s.walkable_geometry[0]=(Geometry){17,19};
 s.world.textures[0].bytes=23;s.world.textures[1].bytes=29;
 s.actor.textures[0].bytes=31;s.walkable.textures[0].bytes=37;
 uint64_t out=0;check(capture_scene_charge(&s,&g,&out)&&out==expected_charge(&s,&g));
 check(world_calls==1);
 const uint64_t baseline=out;
 world.cpu+=41;check(capture_scene_charge(&s,&g,&out)&&out==baseline+41);world.cpu-=41;
 world.gpu+=43;check(capture_scene_charge(&s,&g,&out)&&out==baseline+43);world.gpu-=43;
 s.walk_world.owned+=47;check(capture_scene_charge(&s,&g,&out)&&out==baseline+47);s.walk_world.owned-=47;
 for(unsigned i=0;i<7;i++){s.assets[i].n+=53;check(capture_scene_charge(&s,&g,&out)&&out==baseline+53);s.assets[i].n-=53;}
 g.tf_bytes+=59;check(capture_scene_charge(&s,&g,&out)&&out==baseline+59);g.tf_bytes-=59;
 world.candidate=1;out=71;check(!capture_scene_charge(&s,&g,&out)&&out==71);world.candidate=0;
 source_ok=0;check(!capture_scene_charge(&s,&g,&out)&&out==71);source_ok=1;
 uint64_t non_cpu=baseline-world.cpu;
 world.cpu=COH_CAPTURE_SCENE_LIMIT-COH_CAPTURE_RESERVE-non_cpu;
 check(capture_scene_charge(&s,&g,&out)&&out==COH_CAPTURE_SCENE_LIMIT-COH_CAPTURE_RESERVE);
 world.cpu++;check(!capture_scene_charge(&s,&g,&out)&&out==COH_CAPTURE_SCENE_LIMIT-COH_CAPTURE_RESERVE+1u);
 world.cpu=UINT64_MAX;out=79;check(!capture_scene_charge(&s,&g,&out)&&out==79);world.cpu=101;
 s.assets[6].n=COH_CAPTURE_SCENE_LIMIT;check(!capture_scene_charge(&s,&g,&out));s.assets[6].n=17;
 s.actor_geometry[0].count=UINT32_MAX;check(!capture_scene_charge(&s,&g,&out));s.actor_geometry[0].count=11;
 s.walkable.textures[0].bytes=COH_CAPTURE_SCENE_LIMIT;check(!capture_scene_charge(&s,&g,&out));s.walkable.textures[0].bytes=37;
 g.tf_bytes=COH_CAPTURE_SCENE_LIMIT;check(!capture_scene_charge(&s,&g,&out));
}
static void reset_jni(void){
 assert(!outstanding&&!lock_depth);locks=unlocks=allocations=frees=new_calls=set_calls=0;
 requested_after=UINT64_MAX;malloc_fails=new_fails=mutate_on_new=0;
 memset(raw_bytes,0x5a,sizeof raw_bytes);memset(java_bytes,0,sizeof java_bytes);
}
static void jni(void){
 const struct JNINativeInterface_ functions={new_array,set_array};JNIEnv env=&functions;
 CohFrameCapture owner={raw_bytes,COH_CAPTURE_BYTES,40};Session s={0};s.frame_capture=&owner;
 jlong handle=(jlong)(intptr_t)&s;
 reset_jni();check(!Java_org_coh_sessionclient_SessionNative_frameCapture(&env,NULL,0,0));check(!allocations&&!locks);
 reset_jni();check(!Java_org_coh_sessionclient_SessionNative_frameCapture(&env,NULL,handle,-1));check(!allocations&&!locks);
 reset_jni();malloc_fails=1;check(!Java_org_coh_sessionclient_SessionNative_frameCapture(&env,NULL,handle,0));check(allocations==1&&!frees&&!locks);
 reset_jni();s.frame_capture=NULL;check(!Java_org_coh_sessionclient_SessionNative_frameCapture(&env,NULL,handle,0));
 check(allocations==1&&frees==1&&locks==1&&unlocks==1&&!new_calls&&!set_calls);s.frame_capture=&owner;
 for(uint64_t after=40;after<42;after++){
  reset_jni();check(!Java_org_coh_sessionclient_SessionNative_frameCapture(&env,NULL,handle,(jlong)after));
  check(requested_after==after&&allocations==1&&frees==1&&locks==1&&unlocks==1&&!new_calls);
 }
 reset_jni();mutate_on_new=1;
 check(Java_org_coh_sessionclient_SessionNative_frameCapture(&env,NULL,handle,39)==java_bytes);
 check(requested_after==39&&new_calls==1&&set_calls==1&&frees==1&&locks==1&&unlocks==1);
 for(size_t i=0;i<sizeof java_bytes;i++)assert(java_bytes[i]==0x5a);
 check(raw_bytes[0]==0xee); /* NewByteArray ran after unlock; original bytes were copied first. */
 reset_jni();new_fails=1;check(!Java_org_coh_sessionclient_SessionNative_frameCapture(&env,NULL,handle,39));
 check(new_calls==1&&!set_calls&&frees==1&&!outstanding);
 for(unsigned mode=0;mode<2;mode++){
  reset_jni();owner.size=mode?COH_CAPTURE_BYTES+1u:0;
  check(!Java_org_coh_sessionclient_SessionNative_frameCapture(&env,NULL,handle,0));
  check(allocations==1&&frees==1&&!new_calls&&!set_calls&&locks==1&&unlocks==1);
 }
 check(!outstanding&&!lock_depth);
}
static void viewport(void){
 reset_jni();Session s={0};s.epoch=3;s.frames=70;s.capture_draws=11;jlong h=(jlong)(intptr_t)&s;
 Java_org_coh_sessionclient_SessionNative_captureViewport(NULL,NULL,0,3,640,360);check(!locks);
 Java_org_coh_sessionclient_SessionNative_captureViewport(NULL,NULL,h,-1,640,360);check(!locks);
 Java_org_coh_sessionclient_SessionNative_captureViewport(NULL,NULL,h,3,16385,360);check(!locks);
 Java_org_coh_sessionclient_SessionNative_captureViewport(NULL,NULL,h,2,640,360);check(!s.capture_view_epoch&&s.capture_draws==11);
 Java_org_coh_sessionclient_SessionNative_captureViewport(NULL,NULL,h,3,640,360);
 check(s.capture_view_epoch==3&&s.capture_view_width==640&&s.capture_view_height==360&&s.capture_draws==0&&s.capture_lock_frame==70);
 s.capture_draws=5;s.frames=75;
 Java_org_coh_sessionclient_SessionNative_captureViewport(NULL,NULL,h,3,640,360);check(s.capture_draws==5&&s.capture_lock_frame==70);
 Java_org_coh_sessionclient_SessionNative_captureViewport(NULL,NULL,h,3,0,0);check(s.capture_draws==0&&s.capture_lock_frame==75&&!s.capture_view_width&&!s.capture_view_height);
 check(!lock_depth&&locks==unlocks&&!outstanding);
}
int main(void){accounting();jni();viewport();printf("{\"checks\":%u,\"thin_host_types\":true}\n",checks);return 0;}
'''


def compact(value):
    return re.sub(r"\s+", "", value)


def source_checks(sources, method):
    renderer = sources["renderer"]
    render = compact(method(renderer, "JNIEXPORT jint JNICALL Java_org_coh_sessionclient_SessionNative_render("))
    assert "COH_FRAME_CAPTURE_DIAGNOSTIC&&startup->observed_entity_index&&packets&&entities" in render
    assert "startup->capture_view_epoch==startup->epoch" in render
    assert "startup->capture_view_width==(uint32_t)width&&startup->capture_view_height==(uint32_t)height" in render
    assert render.index("startup->capture_view_epoch==startup->epoch")<render.index("++startup->capture_draws==COH_CAPTURE_WAIT")
    assert "packets_before=startup->stream_stats.draw_packets,entity_before=startup->observed_entity_draws" in render
    assert "startup->stream_stats.draw_packets-packets_before" in render
    assert "startup->observed_entity_draws-entity_before" in render
    assert render.index("coh_frame_capture_readback(") < render.index("eglSwapBuffers(") < render.index("coh_frame_capture_publish(")
    assert "capture_read&&capture_presented&&!s->cancel&&s->epoch==(uint64_t)epoch&&s->observed_entity_updates==startup->observed_entity_updates&&s->observed_entity_index==startup->observed_entity_index" in render
    assert "startup->capture_charge=charge+COH_CAPTURE_RESERVE" in render
    pose = compact(method(renderer, "JNIEXPORT void JNICALL Java_org_coh_sessionclient_SessionNative_observedEntity("))
    assert pose.index("s->observed_entity_updates++;") < pose.index("s->capture_lock_frame=s->frames;") < pose.index("s->capture_draws=0")
    assert '\\"startup_witness\\":false' in renderer
    assert "#define COH_CAPTURE_WAIT 12u" in sources["header"]
    assert "#define COH_CAPTURE_RESERVE (1024u*1024u)" in sources["header"]
    assert "#define COH_CAPTURE_SCENE_LIMIT (96u*1024u*1024u)" in sources["header"]
    owner = compact(sources["owner"])
    assert "m->frame<m->pose_lock_frame+COH_CAPTURE_WAIT" in owner
    assert "m->base_charge>COH_CAPTURE_SCENE_LIMIT-COH_CAPTURE_RESERVE" in owner
    assert "public static native byte[] frameCapture(long handle, long afterFrame);" in sources["native_java"]
    activity = sources["activity"]
    queue = compact(method(activity, "private void queueSceneCapture(JSONObject report)"))
    assert queue.index("reportWorker.execute(") < queue.index("SessionNative.frameCapture(")
    assert "synchronized(captureLife){if(destroying||handle==0)return;raw=SessionNative.frameCapture(handle,captureSavedFrame);}" in queue
    assert "finally{captureQueued.set(false);}" in queue
    assert activity.count("SessionNative.frameCapture(") == 1
    destroy = compact(method(activity, "@Override protected void onDestroy()"))
    assert "synchronized(captureLife){longprevious=handle;handle=0;if(previous!=0)SessionNative.destroy(previous);}" in destroy
    assert "SceneFrameCapture.writeZip(getFilesDir(),output)" in compact(activity)
    assert "SceneFrameCapture.append(getFilesDir(),zip)" in compact(sources["main"])
    assert "buildConfigField 'boolean', 'FRAME_CAPTURE_DIAGNOSTIC'" in sources["gradle"]
    assert "buildConfigField'boolean','FULLSCREEN_DIAGNOSTIC',(candidateProfilein['fullscreen-diagnostic','continuation-diagnostic']).toString()" in compact(sources["gradle"])
    assert "-DCOH_FRAME_CAPTURE_DIAGNOSTIC=" in sources["gradle"]
    assert "if(COH_FRAME_CAPTURE_DIAGNOSTIC)" in sources["cmake"]
    assert "COH_FRAME_CAPTURE_DIAGNOSTIC=1" in sources["cmake"]
    return 30


def run(root, work):
    paths = {
        "renderer": "native-android/session-client/app/src/main/cpp/session_renderer.c",
        "header": "native-android/session-client/app/src/main/cpp/session_frame_capture.h",
        "owner": "native-android/session-client/app/src/main/cpp/session_frame_capture.c",
        "native_java": "native-android/session-client/app/src/main/java/org/coh/sessionclient/SessionNative.java",
        "activity": "native-android/combined-client/app/src/main/java/org/coh/nativecombined/NativeClientActivity.java",
        "main": "native-android/combined-client/app/src/main/java/org/coh/nativecombined/MainActivity.java",
        "gradle": "native-android/combined-client/app/build.gradle",
        "cmake": "native-android/combined-client/app/src/main/cpp/CMakeLists.txt",
        "extractor": "native-android/session-client/tools/lifecycle_host_check.py",
    }
    pins = {name: hashlib.sha256((root / path).read_bytes()).hexdigest() for name, path in paths.items()}
    sources = {name: (root / path).read_text() for name, path in paths.items()}
    spec = importlib.util.spec_from_file_location("capture_lifecycle_host_check", root / paths["extractor"])
    extractor = importlib.util.module_from_spec(spec)
    previous_bytecode = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(extractor)
    finally:
        sys.dont_write_bytecode = previous_bytecode
    assertions = source_checks(sources, extractor.method)
    bodies = [extractor.method(sources["renderer"], signature) for signature in (
        "static int capture_add(", "static int capture_scene_charge(",
        "JNIEXPORT jbyteArray JNICALL Java_org_coh_sessionclient_SessionNative_frameCapture(",
        "JNIEXPORT void JNICALL Java_org_coh_sessionclient_SessionNative_captureViewport(")]
    source = work / "capture-wiring.c"
    source.write_text(HARNESS.replace("/* SHIPPED_METHODS */", "\n".join(bodies)))
    include = root / "native-android/session-client/app/src/main/cpp"
    modes = {}
    variants = [("release", ["-O2"]),
                ("asan", ["-O1", "-g", "-fsanitize=address", "-fno-omit-frame-pointer", "-no-pie"]),
                ("ubsan", ["-O1", "-g", "-fsanitize=undefined", "-fno-sanitize-recover=all"])]
    for mode, flags in variants:
        binary = work / mode
        subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic", *flags,
                        "-I", str(include), str(source), "-o", str(binary)], check=True, timeout=60)
        result = subprocess.run([str(binary)], capture_output=True, text=True, check=True, timeout=60,
                                env=dict(os.environ, ASAN_OPTIONS="detect_leaks=0:halt_on_error=1", UBSAN_OPTIONS="halt_on_error=1"))
        modes[mode] = json.loads(result.stdout)
    assert pins == {name: hashlib.sha256((root / path).read_bytes()).hexdigest() for name, path in paths.items()}, "Source changed during controls"
    return {"passed": True, "source_assertions": assertions, "modes": modes, "source_sha256": pins,
            "actual_framebuffer_readback": False, "android_abi_executed": False,
            "application_memory_peak_measured": False, "leak_sanitizer_executed": False,
            "scope": "Extracted accounting/JNI bodies with explicit thin host storage/JNI/mutex doubles; surrounding wiring is source-asserted."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="coh-capture-wiring-") as directory:
        result = run(args.source_root.resolve(), Path(directory))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
