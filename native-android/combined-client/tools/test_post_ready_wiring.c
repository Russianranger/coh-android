/* Explicit capture/JNI context doubles around unchanged shipped FD callback and
 * configure method; real FD/hash sink is included. No Android ABI/server claim. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "../app/src/main/cpp/post_ready_replay.h"
#define JNIEXPORT
#define JNICALL
typedef int JNIEnv;typedef void*jclass;typedef int64_t jlong;typedef int32_t jint;
enum{COH_OK=0,COH_IO=6,COH_STATE=7};
enum{COH_INITIAL_CAPTURE_RAW_POST=4,COH_INITIAL_CAPTURE_UPDATE=3};
typedef struct{struct{struct{const uint8_t*data;size_t size;}bytes;uint64_t bits,cursor;uint32_t compressed;}reader;uint64_t message_generation,message_id;struct{uint32_t command;}update;uint32_t ordered,ordered_id,kind;}CohInitialCaptureLease;
typedef struct{CohPostReplay post_replay;uint64_t service_now;unsigned busy,suspended,disconnected,terminal,groups_callbacks,allents_callbacks;void*capture;}Interop;
static Interop object;
static Interop*owner(jlong token){return token==17?&object:NULL;}
static size_t initial_retained(const Interop*h){(void)h;return 7000000;}
/* SHIPPED_METHODS */
int main(void){
 unsigned checks=0;
#define CHECK(v) do{checks++;assert(v);}while(0)
 char path[]="/tmp/coh-wiring-post-XXXXXX";int fd=mkstemp(path);CHECK(fd>=0);post_replay_init(&object.post_replay);object.capture=&object;object.service_now=1000;
 CHECK(Java_org_coh_nativecombined_InteropNative_configurePostReadyReplay(NULL,NULL,1,fd)==COH_STATE);
 object.busy=1;CHECK(Java_org_coh_nativecombined_InteropNative_configurePostReadyReplay(NULL,NULL,17,fd)==COH_STATE);object.busy=0;
 object.suspended=1;CHECK(Java_org_coh_nativecombined_InteropNative_configurePostReadyReplay(NULL,NULL,17,fd)==COH_STATE);object.suspended=0;
 object.groups_callbacks=1;CHECK(Java_org_coh_nativecombined_InteropNative_configurePostReadyReplay(NULL,NULL,17,fd)==COH_STATE);object.groups_callbacks=0;
 CHECK(Java_org_coh_nativecombined_InteropNative_configurePostReadyReplay(NULL,NULL,17,-1)==COH_IO);CHECK(!object.busy&&!object.suspended&&!object.terminal);
 CHECK(Java_org_coh_nativecombined_InteropNative_configurePostReadyReplay(NULL,NULL,17,fd)==COH_OK);CHECK(Java_org_coh_nativecombined_InteropNative_configurePostReadyReplay(NULL,NULL,17,fd)==COH_IO);
 uint8_t payload[]={0xde,0xad,0xbe,0xef,0x13,0x37,0,1,2,3};CohInitialCaptureLease loan={0};loan.reader.bytes.data=payload;loan.reader.bytes.size=sizeof(payload);loan.reader.bits=77;loan.reader.cursor=32;loan.reader.compressed=1;loan.message_generation=2;loan.message_id=100;loan.update.command=3;loan.ordered=1;loan.ordered_id=4;
 save_post_ready_message(&object,&loan);CHECK(!object.post_replay.records&&!object.post_replay.seen);
 loan.kind=COH_INITIAL_CAPTURE_RAW_POST;save_post_ready_message(&object,&loan);CHECK(object.post_replay.records==1&&object.post_replay.seen==1&&object.post_replay.bits==77);
 object.service_now=1100;loan.message_generation=3;loan.update.command=2;save_post_ready_message(&object,&loan);CHECK(object.post_replay.records==2&&object.post_replay.bits==154);
 post_replay_finish(&object.post_replay,1);save_post_ready_message(&object,&loan);CHECK(object.post_replay.records==2&&!object.post_replay.reasons);
 CHECK(lseek(fd,64+112,SEEK_SET)==176);uint8_t copy[10];CHECK(read(fd,copy,sizeof(copy))==10&&!memcmp(payload,copy,sizeof(payload)));close(fd);unlink(path);
 printf("{\"passed\":true,\"checks\":%u,\"READY_before_capture\":true,\"body_decoded\":false,\"actual_packet_source\":false}\n",checks);return 0;
}
