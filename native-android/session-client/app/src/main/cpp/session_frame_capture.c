#include "session_frame_capture.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
struct CohFrameCapture {
    uint8_t data[2][COH_CAPTURE_BYTES];
    CohFrameCaptureInfo pending;
    uint64_t published_frame,published_generation;
    size_t published_size;
    uint32_t width,height;
    unsigned published,candidate,writing;
};
static int alias(const void *a,size_t n,const void *b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return n>UINTPTR_MAX-x||m>UINTPTR_MAX-y||(x<y+m&&y<x+n);}
static void u32(uint8_t *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(i*8));}
static void u64(uint8_t *p,uint64_t v){for(unsigned i=0;i<8;i++)p[i]=(uint8_t)(v>>(i*8));}
CohFrameCapture *coh_frame_capture_create(uint64_t base){
    if(base>COH_CAPTURE_SCENE_LIMIT-COH_CAPTURE_RESERVE)return NULL;
    return calloc(1,sizeof(CohFrameCapture));
}
void coh_frame_capture_destroy(CohFrameCapture **out){if(out&&*out){free(*out);*out=NULL;}}
size_t coh_frame_capture_owned_bytes(const CohFrameCapture *c){return c?sizeof *c:0;}
int coh_frame_capture_begin(CohFrameCapture *c,const CohFrameCaptureInfo *m,uint8_t **pixels,uint32_t *width,uint32_t *height){
    if(!c||!m||!pixels||!width||!height||alias(c,sizeof *c,m,sizeof *m)||alias(c,sizeof *c,pixels,sizeof *pixels)||alias(c,sizeof *c,width,sizeof *width)||alias(c,sizeof *c,height,sizeof *height)||alias(m,sizeof *m,pixels,sizeof *pixels)||alias(m,sizeof *m,width,sizeof *width)||alias(m,sizeof *m,height,sizeof *height)||alias(pixels,sizeof *pixels,width,sizeof *width)||alias(pixels,sizeof *pixels,height,sizeof *height)||alias(width,sizeof *width,height,sizeof *height)||c->writing||!m->entity_index||m->entity_index>10239||
       !m->pose_generation||!m->world_packets||!m->entity_draws||!m->viewport_width||!m->viewport_height||
       m->viewport_width>16384||m->viewport_height>16384||m->pose_lock_frame>UINT64_MAX-COH_CAPTURE_WAIT||
       m->frame<m->pose_lock_frame+COH_CAPTURE_WAIT||m->pose_generation==c->published_generation||
       m->base_charge>COH_CAPTURE_SCENE_LIMIT-COH_CAPTURE_RESERVE)return 0;
    for(unsigned i=0;i<3;i++)if(!isfinite(m->pose[i]))return 0;
    uint32_t w=COH_CAPTURE_WIDTH,h=(uint32_t)(((uint64_t)m->viewport_height*w+m->viewport_width/2)/m->viewport_width);
    if(h>COH_CAPTURE_HEIGHT){h=COH_CAPTURE_HEIGHT;w=(uint32_t)(((uint64_t)m->viewport_width*h+m->viewport_height/2)/m->viewport_height);}
    if(!w)w=1;
    if(!h)h=1;
    if(w>COH_CAPTURE_WIDTH||h>COH_CAPTURE_HEIGHT)return 0;
    c->pending=*m;c->width=w;c->height=h;c->candidate=c->published^1u;c->writing=1;
    *pixels=c->data[c->candidate]+COH_CAPTURE_HEADER;*width=w;*height=h;return 1;
}
void coh_frame_capture_publish(CohFrameCapture *c,int presented){
    if(!c||!c->writing)return;
    c->writing=0;
    if(!presented)return;
    uint8_t *p=c->data[c->candidate];const CohFrameCaptureInfo *m=&c->pending;
    memset(p,0,COH_CAPTURE_HEADER);memcpy(p,"COHFB001",8);u32(p+8,COH_CAPTURE_HEADER);
    u32(p+12,c->width);u32(p+16,c->height);u32(p+20,m->viewport_width);u32(p+24,m->viewport_height);
    u32(p+28,c->width*c->height*4u);u32(p+32,m->entity_index);
    u64(p+40,m->frame);u64(p+48,m->epoch);u64(p+56,m->pose_generation);u64(p+64,m->pose_lock_frame);
    u64(p+72,m->world_packets);u64(p+80,m->entity_draws);
    for(unsigned i=0;i<3;i++){uint32_t v;memcpy(&v,m->pose+i,4);u32(p+88+i*4,v);}
    u64(p+104,m->base_charge+COH_CAPTURE_RESERVE);u64(p+112,COH_CAPTURE_SCENE_LIMIT);u32(p+120,COH_CAPTURE_WAIT);u32(p+124,1);
    c->published=c->candidate;c->published_size=COH_CAPTURE_HEADER+(size_t)c->width*c->height*4u;
    c->published_frame=m->frame;c->published_generation=m->pose_generation;
}
const uint8_t *coh_frame_capture_data(const CohFrameCapture *c,size_t *size,uint64_t after){
    if(!c||!size||alias(c,sizeof *c,size,sizeof *size)||!c->published_size||c->published_frame<=after)return NULL;
    *size=c->published_size;return c->data[c->published];
}
