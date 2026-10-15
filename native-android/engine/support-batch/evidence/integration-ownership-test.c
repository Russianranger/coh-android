
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <pthread.h>
#include <assert.h>
typedef void AAssetManager;typedef struct{const uint8_t*data;size_t size;} CohBytes;
typedef struct {int live;} CohSupportAnimation;typedef struct {int live;} SupportAudio;
typedef struct SupportBridge {pthread_mutex_t mutex;void *physics,*ui,*cache;CohSupportAnimation *animation;SupportAudio *audio;CohBytes clips[3];int configured,foreground;uint64_t failures;} SupportBridge;
static unsigned outstanding,allocation_index,fail_index,fail_animation,fail_audio,close_failure;
static void *alloc(size_t n){allocation_index++;if(fail_index&&allocation_index==fail_index)return NULL;void*p=malloc(n);if(p)outstanding++;return p;}
static void release(void*p){if(p){assert(outstanding);outstanding--;free(p);}}
static int coh_support_animation_create(CohBytes*b,unsigned actor,CohSupportAnimation**out){(void)actor;assert(b[0].data&&b[1].data&&b[2].data);if(fail_animation)return 1;*out=alloc(sizeof **out);return *out?0:1;}
static void coh_support_animation_destroy(CohSupportAnimation*p){release(p);}
static SupportAudio *support_audio_create(AAssetManager*m){(void)m;return fail_audio?NULL:alloc(sizeof(SupportAudio));}
static int support_audio_destroy(SupportAudio**p){if(close_failure){close_failure--;return 1;}release(*p);*p=NULL;return 0;}
static void support_audio_resume(SupportAudio*p){assert(p);}
static void coh_support_physics_destroy(void*p){release(p);}
static void support_ui_destroy(void*p){release(p);}
static void coh_skin_cache_destroy(void**p){release(*p);*p=NULL;}
#define malloc alloc
#define free release
int support_bridge_destroy(SupportBridge **owner){if(!owner)return 0;SupportBridge *b=*owner;if(!b)return 1;
 /* Caller has stopped render/input users and serializes destruction. No other
  * dependency is released until the backend has joined every callback. */
 if(b->audio&&support_audio_destroy(&b->audio)){b->failures++;return 0;}
 coh_support_animation_destroy(b->animation);for(unsigned i=0;i<3;i++)free((void*)b->clips[i].data);
 coh_support_physics_destroy(b->physics);support_ui_destroy(b->ui);coh_skin_cache_destroy(&b->cache);pthread_mutex_destroy(&b->mutex);free(b);*owner=NULL;return 1;
}
int support_bridge_configure(SupportBridge *b,AAssetManager *manager,const void *clips[3],const size_t sizes[3]){
 if(!b||!manager||!clips||!sizes)return 0;pthread_mutex_lock(&b->mutex);
 int ok=0;CohBytes staged[3]={{0}};CohSupportAnimation *animation=NULL;SupportAudio *audio=NULL;
 if(b->configured){ok=1;goto done;}
 /* Stage owned clips/animation before starting the asynchronous audio worker.
  * No failure path overwrites an existing owner or leaves partial state. */
 for(unsigned i=0;i<3;i++){if(!clips[i]||!sizes[i]||sizes[i]>(1u<<20))goto done;uint8_t *p=malloc(sizes[i]);if(!p)goto done;memcpy(p,clips[i],sizes[i]);staged[i]=(CohBytes){p,sizes[i]};}
 if(coh_support_animation_create(staged,1,&animation))goto done;
 audio=support_audio_create(manager);if(!audio)goto done;
 memcpy(b->clips,staged,sizeof staged);memset(staged,0,sizeof staged);
 b->animation=animation;animation=NULL;b->audio=audio;b->configured=1;
 if(b->foreground)support_audio_resume(b->audio);ok=1;
 done:coh_support_animation_destroy(animation);for(unsigned i=0;i<3;i++)free((void*)staged[i].data);
 if(!ok)b->failures++;pthread_mutex_unlock(&b->mutex);return ok;
}

int main(void){unsigned checks=0;unsigned char bytes[3][16]={{1},{2},{3}};const void*clips[3]={bytes[0],bytes[1],bytes[2]};size_t sizes[3]={16,16,16};
 for(unsigned scenario=0;scenario<6;scenario++){
  SupportBridge*b=alloc(sizeof *b);memset(b,0,sizeof *b);pthread_mutex_init(&b->mutex,NULL);b->ui=alloc(1);b->physics=alloc(1);b->cache=alloc(1);assert(outstanding==4);
  allocation_index=0;fail_index=scenario<4?scenario+1:0;fail_animation=scenario==4;fail_audio=scenario==5;
  assert(!support_bridge_configure(b,(AAssetManager*)1,clips,sizes));assert(outstanding==4);assert(!b->configured&&!b->audio&&!b->animation);for(unsigned i=0;i<3;i++)assert(!b->clips[i].data);checks+=7;
  fail_index=fail_animation=fail_audio=0;allocation_index=0;assert(support_bridge_configure(b,(AAssetManager*)1,clips,sizes));assert(outstanding==9&&b->configured);checks+=2;
  unsigned before=allocation_index;assert(support_bridge_configure(b,(AAssetManager*)1,clips,sizes));assert(allocation_index==before);checks+=2;
  SupportBridge*saved=b;close_failure=1;assert(!support_bridge_destroy(&b));assert(b==saved&&b->audio&&b->animation&&b->clips[0].data&&b->physics&&b->ui&&b->cache);assert(outstanding==9);checks+=3;
  assert(support_bridge_destroy(&b));assert(!b&&!outstanding);assert(support_bridge_destroy(&b));checks+=3;
 }
 printf("{\"checks\":%u,\"fault_scenarios\":6,\"retained_close_failure_owners\":1,\"outstanding_allocations\":%u}\n",checks,outstanding);return 0;}
