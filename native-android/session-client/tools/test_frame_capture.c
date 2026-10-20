#include "session_frame_capture.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,failed_allocation,live_allocations;
#define CHECK(x) do{checks++;assert(x);}while(0)
void *__real_calloc(size_t,size_t);
void __real_free(void*);
void *__wrap_calloc(size_t n,size_t s){void*p=failed_allocation?NULL:__real_calloc(n,s);if(p)live_allocations++;return p;}
void __wrap_free(void*p){if(p){assert(live_allocations);live_allocations--;}__real_free(p);}
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
int main(void){
    CHECK(!coh_frame_capture_create(UINT64_MAX));CHECK(!coh_frame_capture_create(COH_CAPTURE_SCENE_LIMIT));
    failed_allocation=1;CHECK(!coh_frame_capture_create(0));failed_allocation=0;
    CohFrameCapture*c=coh_frame_capture_create(COH_CAPTURE_SCENE_LIMIT-COH_CAPTURE_RESERVE);CHECK(c);
    CHECK(coh_frame_capture_owned_bytes(c)<COH_CAPTURE_RESERVE/2);
    CohFrameCaptureInfo m={1920,1080,125,112,3,1,100,2,1,1024,{131.453125f,.25f,-114.953125f}};
    uint8_t*p=NULL;uint32_t w=0,h=0;size_t n=0;
    CHECK(!coh_frame_capture_data(c,&n,0));
    for(unsigned field=0;field<12;field++){
        CohFrameCaptureInfo bad=m;
        switch(field){case 0:bad.viewport_width=0;break;case 1:bad.viewport_height=16385;break;case 2:bad.entity_index=0;break;case 3:bad.entity_index=10240;break;case 4:bad.pose_generation=0;break;case 5:bad.world_packets=0;break;case 6:bad.entity_draws=0;break;case 7:bad.pose[0]=NAN;break;case 8:bad.frame=111;break;case 9:bad.pose_lock_frame=UINT64_MAX;break;case 10:bad.base_charge=UINT64_MAX;break;default:bad.viewport_height=0;break;}
        CHECK(!coh_frame_capture_begin(c,&bad,&p,&w,&h));CHECK(p==NULL&&w==0&&h==0);
    }
    CHECK(!coh_frame_capture_begin(c,&m,&p,&w,&w));CHECK(!coh_frame_capture_begin(c,&m,(uint8_t**)&m,&w,&h));
    CHECK(coh_frame_capture_begin(c,&m,&p,&w,&h));CHECK(w==COH_CAPTURE_WIDTH&&h==COH_CAPTURE_HEIGHT);memset(p,123,w*h*4u);
    CHECK(!coh_frame_capture_begin(c,&m,&p,&w,&h));coh_frame_capture_publish(c,0);CHECK(!coh_frame_capture_data(c,&n,0));
    CHECK(coh_frame_capture_begin(c,&m,&p,&w,&h));memset(p,42,w*h*4u);coh_frame_capture_publish(c,1);
    const uint8_t*first=coh_frame_capture_data(c,&n,0);CHECK(first&&n==COH_CAPTURE_BYTES);CHECK(!memcmp(first,"COHFB001",8));CHECK(u32(first+12)==COH_CAPTURE_WIDTH&&u32(first+16)==COH_CAPTURE_HEIGHT);CHECK(first[128]==42);CHECK(!coh_frame_capture_data(c,&n,112));CHECK(!coh_frame_capture_begin(c,&m,&p,&w,&h));
#if COH_FULLSCREEN_DIAGNOSTIC
    m.epoch++;m.frame++;
    CHECK(coh_frame_capture_begin(c,&m,&p,&w,&h));memset(p,42,w*h*4u);coh_frame_capture_publish(c,1);
    first=coh_frame_capture_data(c,&n,0);CHECK(first&&n==COH_CAPTURE_BYTES);
    CHECK(!coh_frame_capture_begin(c,&m,&p,&w,&h));
#endif
    m.pose_generation++;m.frame++;m.viewport_width=1080;m.viewport_height=1920;
    CHECK(coh_frame_capture_begin(c,&m,&p,&w,&h));CHECK(w==(1080u*COH_CAPTURE_HEIGHT+960u)/1920u&&h==COH_CAPTURE_HEIGHT);memset(p,17,w*h*4u);CHECK(first[128]==42);coh_frame_capture_publish(c,0);CHECK(coh_frame_capture_data(c,&n,0)==first);
    CHECK(coh_frame_capture_begin(c,&m,&p,&w,&h));memset(p,99,w*h*4u);coh_frame_capture_publish(c,1);CHECK(coh_frame_capture_data(c,&n,112)[128]==99);
    for(uint32_t x=1;x<=8;x++){m.pose_generation++;m.frame++;m.viewport_width=100*x;m.viewport_height=100;CHECK(coh_frame_capture_begin(c,&m,&p,&w,&h));CHECK(w<=COH_CAPTURE_WIDTH&&h<=COH_CAPTURE_HEIGHT&&w&&h);CHECK(fabs((double)w*m.viewport_height-(double)h*m.viewport_width)<=.51*fmax(m.viewport_width,m.viewport_height));memset(p,3,w*h*4u);coh_frame_capture_publish(c,1);}
    coh_frame_capture_destroy(&c);CHECK(!c);coh_frame_capture_destroy(&c);CHECK(!coh_frame_capture_owned_bytes(c));CHECK(live_allocations==0);
    printf("{\"passed\":true,\"checks\":%u,\"capture_reserve_bytes\":%u,\"maximum_raw_bytes\":%u}\n",checks,COH_CAPTURE_RESERVE,COH_CAPTURE_BYTES);return 0;
}
