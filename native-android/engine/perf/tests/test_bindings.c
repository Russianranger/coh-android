#include "coh_perf_bridge.h"
#include "../../audio/coh_audio_listener.h"
#include "../../../world/coh_world.h"
#include <assert.h>
#include <float.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks,guard,guard_calls;
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void *__real_realloc(void *,size_t);void __real_free(void *);
void *__wrap_malloc(size_t n){if(guard)guard_calls++;return __real_malloc(n);}
void *__wrap_calloc(size_t n,size_t m){if(guard)guard_calls++;return __real_calloc(n,m);}
void *__wrap_realloc(void *p,size_t n){if(guard)guard_calls++;return __real_realloc(p,n);}
void __wrap_free(void *p){if(guard)guard_calls++;__real_free(p);}
#define CHECK(c) do {checks++;if(!(c)){fprintf(stderr,"check %u failed line %u: %s\n",checks,__LINE__,#c);abort();}}while(0)
static void near(float a,float b,float tol){CHECK(isfinite(a)&&isfinite(b)&&fabsf(a-b)<=tol);}
extern void oracle_right(const float degrees[3],float right[3]);
extern float oracle_moving_spatial(const CohAudioEvent *,CohVec3,CohVec3,float *);
extern int oracle_db(float);
extern float oracle_gain(int);
static void listener(void){
    guard=1;
    for(unsigned i=0;i<5000;i++){
        CohWorldInputs in={0};CohWorldCamera *c=&in.cameras[0];
        for(unsigned j=0;j<3;j++){
            c->position[j]=(float)((int)((i*(13+j*7))%65000)-32500);
            c->pyr_degrees[j]=(float)((int)((i*(7+j*11))%720)-360);
        }
        c->fovy=70;c->aspect=1.777f;c->znear=.1f;c->zfar=10000;c->flip_x=i&1;c->flip_y=(i>>1)&1;
        float v[12],projection[16],expected[3];CohAudioListenerPose pose;
        CHECK(coh_world_camera(&in,0,0,v,projection)==0);
        CHECK(coh_audio_listener_source_view(v,&pose)==COH_OK);
        oracle_right(c->pyr_degrees,expected);
        near(pose.position.x,c->position[0],.025f);near(pose.position.y,c->position[1],.025f);near(pose.position.z,c->position[2],.025f);
        near(pose.right.x,expected[0],2e-6f);near(pose.right.y,expected[1],2e-6f);near(pose.right.z,expected[2],2e-6f);
        /* Use exact original position for the spatial comparison to isolate
         * head-right math from world-coordinate binary32 inverse rounding. */
        pose.position=(CohVec3){c->position[0],c->position[1],c->position[2]};
        CohAudioEvent e={0};e.gain=(i%9+1)*.1f;e.spatial=1;e.inner_radius=2;e.outer_radius=40;e.ignore_ramp=i&1;
        e.position=(CohVec3){pose.position.x+(float)((int)(i%25)-12),pose.position.y+(float)(i%19),pose.position.z+(float)(i%13)};
        float pan=0,vol=oracle_moving_spatial(&e,pose.position,(CohVec3){expected[0],expected[1],expected[2]},&pan);
        float l,r;coh_mixer_spatial_gains(&e,pose.position,pose.right,.6f,&l,&r);
        float gain=oracle_gain(oracle_db(vol*.6f));int db=(int)(pan*2000);
        near(l,gain*oracle_gain(db>0?-db:0),2e-4f);near(r,gain*oracle_gain(db<0?db:0),2e-4f);
    }
    CohAudioListenerPose p={{7,8,9},{1,0,0}},saved=p;
    float identity[12]={1,0,0,0,1,0,0,0,1,0,0,0};
    CHECK(coh_audio_listener_source_view(identity,&p)==COH_INVALID);CHECK(!memcmp(&p,&saved,sizeof p));
    identity[0]=-1;
    CHECK(coh_audio_listener_source_view(identity,&p)==COH_OK);near(p.right.x,1,0);
    saved=p;
    for(unsigned j=0;j<12;j++){
        float v[12];memcpy(v,identity,sizeof v);v[j]=NAN;
        CHECK(coh_audio_listener_source_view(v,&p)==COH_INVALID);CHECK(!memcmp(&p,&saved,sizeof p));
    }
    identity[1]=.01f;CHECK(coh_audio_listener_source_view(identity,&p)==COH_INVALID);
    identity[1]=0;identity[4]=.999f;identity[9]=FLT_MAX;identity[10]=FLT_MAX;
    CHECK(coh_audio_listener_source_view(identity,&p)==COH_OK);
    CHECK(coh_audio_listener_pose((CohVec3){0,0,0},(CohVec3){FLT_MAX,FLT_MAX,FLT_MAX},&p)==COH_OK);
    near(p.right.x,1/sqrtf(3),1e-7f);
    CHECK(coh_audio_listener_pose((CohVec3){0,0,0},(CohVec3){FLT_TRUE_MIN,0,0},&p)==COH_OK);near(p.right.x,1,0);
    CHECK(coh_audio_listener_pose((CohVec3){INFINITY,0,0},(CohVec3){1,0,0},&p)==COH_INVALID);
    CHECK(coh_audio_listener_pose((CohVec3){0,0,0},(CohVec3){0,0,0},&p)==COH_INVALID);
    CHECK(coh_audio_listener_source_view(NULL,&p)==COH_INVALID);CHECK(coh_audio_listener_source_view(identity,NULL)==COH_INVALID);
    CHECK(coh_audio_listener_apply(NULL,&p)==COH_INVALID);
    guard=0;
    CohMixer *m=NULL;CohMixerConfig config={48000,2,2,1,32,0};CHECK(coh_mixer_create(&config,&m)==COH_OK);
    int16_t pcm[2]={8192,8192};CohAudioResource h;
    CHECK(coh_mixer_cache_pcm16(m,(CohAssetId){"mock/constant.pcm",1},pcm,2,1,48000,&h)==COH_OK);
    CohAudioEvent event={0};event.resource=h;event.gain=1;event.inner_radius=10;event.outer_radius=20;event.spatial=1;event.loop=1;event.position.x=5;
    CHECK(coh_mixer_play(m,&event)==COH_OK);float output[2];CHECK(coh_mixer_render(m,output,1)==COH_OK);
    guard=1;
    CHECK(coh_audio_listener_pose((CohVec3){0,0,0},(CohVec3){1,0,0},&p)==COH_OK);CHECK(coh_audio_listener_apply(m,&p)==COH_OK);
    CHECK(coh_mixer_render(m,output,1)==COH_OK);CHECK(output[1]>output[0]);
    p.right.x=-1;CHECK(coh_audio_listener_apply(m,&p)==COH_OK);CHECK(coh_mixer_render(m,output,1)==COH_OK);CHECK(output[0]>output[1]);
    CHECK(coh_audio_listener_apply(m,&p)==COH_OK);CHECK(coh_audio_listener_apply(m,&p)==COH_OK);
    CHECK(coh_audio_listener_apply(m,&p)==COH_LIMIT); /* Caller can retry latest pose. */
    CHECK(coh_mixer_render(m,NULL,0)==COH_OK);
    guard=0;coh_mixer_destroy(m);
}
static void performance(CohPerf *p,CohPerfBridge *b){
    CohPerfConfig c=coh_perf_default_config();CHECK(coh_perf_init(p,&c)==COH_OK);coh_perf_bridge_init(b);
    guard=1;uint64_t total=0;
    CHECK(coh_perf_bridge_total(b,p,COH_PERF_DRAW_CALLS,1,0)==COH_OK);
    for(unsigned i=1;i<=1000;i++){
        coh_perf_set_paused(p,i%13==0);c.enabled=i%17!=0;CHECK(coh_perf_configure(p,&c)==COH_OK);
        total+=i%7;CHECK(coh_perf_bridge_total(b,p,COH_PERF_DRAW_CALLS,1,total)==COH_OK);
        CHECK(coh_perf_bridge_total(b,p,COH_PERF_DRAW_CALLS,1,total)==COH_OK);
    }
    coh_perf_set_paused(p,0);c.enabled=1;CHECK(coh_perf_configure(p,&c)==COH_OK);
    uint64_t original=p->snapshot.counters[COH_PERF_DRAW_CALLS];
    CHECK(coh_perf_bridge_total(b,p,COH_PERF_DRAW_CALLS,1,total-1)==COH_STATE);
    CHECK(coh_perf_bridge_total(b,p,COH_PERF_DRAW_CALLS,1,total+5)==COH_OK);
    CHECK(coh_perf_bridge_total(b,p,COH_PERF_DRAW_CALLS,2,500)==COH_OK);
    CHECK(coh_perf_bridge_total(b,p,COH_PERF_DRAW_CALLS,2,507)==COH_OK);
    CHECK(p->snapshot.counters[COH_PERF_DRAW_CALLS]==original+12);
    CHECK(coh_perf_bridge_delta(b,p,COH_PERF_DRAW_CALLS,5)==COH_STATE);
    CHECK(coh_perf_bridge_delta(b,p,COH_PERF_READBACKS,0)==COH_OK);
    CHECK(coh_perf_bridge_total(b,p,COH_PERF_READBACKS,1,0)==COH_STATE);
    CHECK(coh_perf_bridge_delta(b,p,COH_PERF_UPLOAD_BYTES,UINT64_MAX)==COH_OK);
    CHECK(coh_perf_bridge_delta(b,p,COH_PERF_UPLOAD_BYTES,5)==COH_OK);
    CHECK(p->snapshot.counters[COH_PERF_UPLOAD_BYTES]==UINT64_MAX);
    CHECK(coh_perf_bridge_total(b,p,COH_PERF_ASSET_HITS,0,1)==COH_INVALID);
    CHECK(!b->counters[COH_PERF_ASSET_HITS].known);
    CHECK(coh_perf_bridge_memory(b,COH_PERF_MEMORY_ACCOUNTED,600)==COH_OK);
    CHECK(coh_perf_bridge_memory(b,COH_PERF_MEMORY_ACCOUNTED,400)==COH_OK);
    CHECK(coh_perf_bridge_memory(b,COH_PERF_MEMORY_RSS,0)==COH_OK);
    CHECK(coh_perf_bridge_memory(b,COH_PERF_MEMORY_COUNT,0)==COH_INVALID);
    CHECK(coh_perf_bridge_delta(NULL,p,COH_PERF_DRAW_CALLS,0)==COH_INVALID);
    CHECK(coh_perf_bridge_delta(b,NULL,COH_PERF_DRAW_CALLS,0)==COH_INVALID);
    CHECK(coh_perf_bridge_total(b,p,COH_PERF_COUNTER_COUNT,1,0)==COH_INVALID);
    guard=0;
    char json[8192],one[1];size_t needed=0,again=0;
    CHECK(coh_perf_bridge_json(b,NULL,0,&needed)==COH_LIMIT);CHECK(needed>2&&needed<=sizeof json);
    CHECK(coh_perf_bridge_json(b,one,1,&again)==COH_LIMIT);CHECK(needed==again&&one[0]==0);
    CHECK(coh_perf_bridge_json(b,json,needed-1,&again)==COH_LIMIT);CHECK(json[0]==0);
    CHECK(coh_perf_bridge_json(b,json,needed,&again)==COH_OK);CHECK(strlen(json)+1==needed);
    CHECK(coh_perf_bridge_json(b,NULL,1,&needed)==COH_INVALID);
    CHECK(coh_perf_bridge_json(b,json,sizeof json,NULL)==COH_INVALID);
}
int main(void){
    listener();CohPerf p;CohPerfBridge b;performance(&p,&b);
    CHECK(guard_calls==0);char bindings[8192],perf[8192];size_t needed;
    CHECK(coh_perf_bridge_json(&b,bindings,sizeof bindings,&needed)==COH_OK);
    CHECK(coh_perf_json(&p,perf,sizeof perf,&needed)==COH_OK);
    printf("{\"status\":\"passed\",\"checks\":%u,\"cameras\":5000,\"spatial_source_comparisons\":10000,\"hot_path_allocator_calls\":%u,\"bridge_bytes\":%zu,\"listener_pose_bytes\":%zu,\"perf\":%s,\"bindings\":%s}\n",checks,guard_calls,sizeof b,sizeof(CohAudioListenerPose),perf,bindings);return 0;
}
