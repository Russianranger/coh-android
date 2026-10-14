#include "coh_input.h"
#include <math.h>
#include <stddef.h>
#include <string.h>
#define PI 3.14159265358979323846
#define RAD(a) (((a)*PI)*(1.0f/180.0f))
/* These scalar operations retain the original UtilitiesLib arithmetic. */
static float fix_angle(float a) {
    if(a > RAD(180.0)) a -= RAD(360.0);
    if(a <= RAD(-180.0)) a += RAD(360.0);
    return a;
}
static float add_angle(float a,float b) { return fix_angle(a+b); }
static float sub_angle(float a,float b) { return fix_angle(a-b); }
static int valid_axis(float a) { return isfinite(a) && a >= -1.0f && a <= 1.0f; }
static void clear_input(CohInputState *s) {
    memset(s->levels,0,sizeof(s->levels));
    memset(s->edges,0,sizeof(s->edges));
    memset(s->released,0,sizeof(s->released));
    memset(s->axes,0,sizeof(s->axes));
    s->pending_x=s->pending_y=0; s->touch_id=-1; s->clear_count++;
}
void coh_input_init(CohInputState *s) {
    if(!s) return;
    memset(s,0,sizeof(*s)); s->touch_id=-1; s->focused=1; s->mlook=1;
}
void coh_input_focus(CohInputState *s,int focused) {
    if(!s) return;
    if(!focused) clear_input(s);
    s->focused=(uint8_t)(focused!=0);
}
static void key_update(CohInputState *s,uint32_t key,int down) {
    if(down) {
        if(!s->levels[key]) s->edges[key]=1;
        if(s->levels[key]<127) s->levels[key]++;
    } else {
        if(s->levels[key]) s->released[key]=1;
        s->levels[key]=0;
    }
}
int coh_input_key(CohInputState *s,uint32_t key,int down) {
    if(!s) return 0;
    if(key<8 || key>=COH_INPUT_KEYS || (down!=0 && down!=1)) { s->rejected++; return 0; }
    if(s->focused) key_update(s,key,down);
    return 1;
}
int coh_input_axes(CohInputState *s,float x,float y,float z,float rz) {
    float values[4]={x,y,z,rz}; uint32_t i;
    if(!s) return 0;
    for(i=0;i<4;i++) if(!valid_axis(values[i])) { s->rejected++; return 0; }
    if(s->focused) memcpy(s->axes,values,sizeof(values));
    return 1;
}
static int32_t bounded_delta(CohInputState *s,int32_t value) {
    if(value>500) {s->clipped++;return 500;}
    if(value< -500) {s->clipped++;return -500;}
    return value;
}
int coh_input_touch(CohInputState *s,int action,int32_t id,float x,float y) {
    int32_t dx,dy;
    if(!s) return 0;
    if(action==COH_TOUCH_CANCEL) {clear_input(s);return 1;}
    if(action<COH_TOUCH_BEGIN || action>COH_TOUCH_END || id<0 || !valid_axis(x) || !valid_axis(y)) {s->rejected++;return 0;}
    if(!s->focused) return 1;
    if(action==COH_TOUCH_BEGIN) {
        if(s->touch_id>=0) return 1;
        s->touch_id=id;s->touch_x=x;s->touch_y=y;return 1;
    }
    if(id!=s->touch_id) return 1;
    dx=(int32_t)lroundf((x-s->touch_x)*250.0f);
    dy=(int32_t)lroundf((y-s->touch_y)*250.0f);
    s->pending_x=bounded_delta(s,s->pending_x+dx);
    s->pending_y=bounded_delta(s,s->pending_y+dy);
    s->touch_x=x;s->touch_y=y;
    if(action==COH_TOUCH_END) s->touch_id=-1;
    return 1;
}
static float rate_axis(float axis) {
    float magnitude=fabsf(axis);
    if(magnitude<=0.15f) return 0.0f;
    return copysignf((magnitude-0.15f)/0.85f,axis);
}
static void source_look(CohInputState *s,int32_t dx,int32_t dy) {
    float d,pyr[3];
    if(!dx && !dy) return;
    if(s->invert) dy=-dy;
    memcpy(pyr,s->pyr,sizeof(pyr));
    pyr[1]=add_angle(pyr[1],(float)dx/500.0F);
    if(s->mlook) {
        pyr[0]=add_angle(pyr[0],(float)dy/500.0F);
        if(pyr[0]< -RAD(90)) pyr[0]=(float)-RAD(90);
        if(pyr[0]> RAD(90)) pyr[0]=(float)RAD(90);
    } else {
        d=sub_angle((float)RAD(-2),pyr[0]);
        if(d>RAD(10)) d=(float)RAD(10);
        if(d< -RAD(10)) d=(float)-RAD(10);
        pyr[0]=add_angle(d,pyr[0]);
    }
    memcpy(s->pyr,pyr,sizeof(pyr));
    pyr[1]=add_angle(pyr[1],(float)RAD(180)); pyr[0]*= -1;
    memcpy(s->target_pyr,pyr,sizeof(pyr));
}
int coh_input_frame(CohInputState *s,float seconds,CohInputFrame *out) {
    uint32_t i; int32_t dx=0,dy=0;
    if(!s || !out) return 0;
    if(!isfinite(seconds) || seconds<0.0f || seconds>0.05f) {s->rejected++;return 0;}
    if(s->focused) {
        for(i=0;i<4;i++) {
            int32_t axis=(int32_t)lroundf(s->axes[i]*1000.0f);
            /* Original source uses strict boundaries at +/-500. */
            if(axis< -500) key_update(s,i*2,1);
            else if(s->levels[i*2]) key_update(s,i*2,0);
            if(axis>500) key_update(s,i*2+1,1);
            else if(s->levels[i*2+1]) key_update(s,i*2+1,0);
        }
        dx=bounded_delta(s,s->pending_x+(int32_t)lroundf(rate_axis(s->axes[2])*1000.0f*seconds));
        dy=bounded_delta(s,s->pending_y+(int32_t)lroundf(rate_axis(s->axes[3])*1000.0f*seconds));
        source_look(s,dx,dy);
    }
    s->pending_x=s->pending_y=0;s->frames++;
    memset(out,0,sizeof(*out));
    for(i=0;i<COH_INPUT_KEYS;i++) {
        if(s->levels[i]) out->held|=1u<<i;
        if(s->edges[i]) out->pressed|=1u<<i;
        if(s->released[i]) out->released|=1u<<i;
    }
    memcpy(out->levels,s->levels,sizeof(out->levels));
    memcpy(out->pyr,s->pyr,sizeof(out->pyr));
    memcpy(out->target_pyr,s->target_pyr,sizeof(out->target_pyr));
    memcpy(out->axes,s->axes,sizeof(out->axes));
    out->delta_x=dx;out->delta_y=dy;out->frames=s->frames;
    out->clear_count=s->clear_count;out->rejected=s->rejected;out->clipped=s->clipped;
    memset(s->edges,0,sizeof(s->edges));memset(s->released,0,sizeof(s->released));
    return 1;
}
#include "input_goldens.h"
int coh_input_selftest(CohInputProof *proof) {
    CohInputState s;CohInputFrame f;uint32_t i,j;
    if(!proof) return 0;
    memset(proof,0,sizeof(*proof));
#define CHECK(expr) do {proof->checks++;if(!(expr))proof->failed++;} while(0)
    for(i=0;i<COH_INPUT_GOLDEN_COUNT;i++) {
        const CohInputGolden *g=&coh_input_goldens[i];
        coh_input_init(&s);s.pyr[0]=g->pitch;s.pyr[1]=g->yaw;s.mlook=(uint8_t)g->mlook;s.invert=(uint8_t)g->invert;
        s.pending_x=g->dx;s.pending_y=g->dy;
        CHECK(coh_input_frame(&s,0,&f));
        for(j=0;j<3;j++) {
            float err=fabsf(f.pyr[j]-g->pyr[j]);
            if(err>proof->max_source_error)proof->max_source_error=err;
            CHECK(memcmp(&f.pyr[j],&g->pyr[j],sizeof(float))==0);
            err=fabsf(f.target_pyr[j]-g->target[j]);
            if(err>proof->max_source_error)proof->max_source_error=err;
            CHECK(memcmp(&f.target_pyr[j],&g->target[j],sizeof(float))==0);
        }
        proof->source_cases++;
    }
    coh_input_init(&s);
    CHECK(coh_input_key(&s,8,1));CHECK(coh_input_key(&s,8,0));CHECK(coh_input_frame(&s,0,&f));
    CHECK(f.held==0 && f.pressed==(1u<<8) && f.released==(1u<<8));
    CHECK(coh_input_frame(&s,0,&f) && f.pressed==0 && f.released==0);proof->adapter_cases++;
    for(i=0;i<200;i++)CHECK(coh_input_key(&s,8,1));
    CHECK(coh_input_frame(&s,0,&f) && f.levels[8]==127);proof->adapter_cases++;
    CHECK(coh_input_axes(&s,-0.5f,0.5f,-0.501f,0.501f));CHECK(coh_input_frame(&s,0,&f));
    CHECK((f.held&255u)==((1u<<4)|(1u<<7)));proof->adapter_cases++;
    CHECK(coh_input_touch(&s,COH_TOUCH_BEGIN,5,-1,-1));
    CHECK(coh_input_touch(&s,COH_TOUCH_MOVE,9,1,1));
    CHECK(coh_input_frame(&s,0,&f) && f.delta_x==0 && f.delta_y==0);proof->adapter_cases++;
    CHECK(coh_input_touch(&s,COH_TOUCH_MOVE,5,1,1));
    CHECK(coh_input_frame(&s,0,&f) && f.delta_x==500 && f.delta_y==500);proof->adapter_cases++;
    CHECK(coh_input_touch(&s,COH_TOUCH_CANCEL,-1,0,0));
    CHECK(coh_input_frame(&s,0,&f) && f.held==0 && f.delta_x==0 && f.delta_y==0);proof->adapter_cases++;
    CHECK(coh_input_touch(&s,COH_TOUCH_BEGIN,17,-1,0));
    CHECK(coh_input_touch(&s,COH_TOUCH_END,17,1,0));
    CHECK(coh_input_frame(&s,0,&f) && f.delta_x==500 && s.touch_id== -1);
    CHECK(coh_input_frame(&s,0,&f) && f.delta_x==0);proof->adapter_cases++;
    CHECK(coh_input_axes(&s,1,1,1,1));CHECK(coh_input_key(&s,9,1));coh_input_focus(&s,0);
    CHECK(coh_input_frame(&s,0.05f,&f) && f.held==0 && f.pressed==0 && f.delta_x==0 && f.delta_y==0);proof->adapter_cases++;
    coh_input_focus(&s,1);CHECK(coh_input_frame(&s,0.05f,&f) && f.held==0 && f.delta_x==0);proof->adapter_cases++;
    CHECK(!coh_input_axes(&s,NAN,0,0,0));CHECK(!coh_input_axes(&s,0,0,2,0));
    CHECK(!coh_input_frame(&s,-1,&f));CHECK(!coh_input_frame(&s,INFINITY,&f));
    CHECK(!coh_input_key(&s,0,1));CHECK(!coh_input_key(&s,24,1));
    CHECK(!coh_input_touch(&s,0,-1,0,0));CHECK(!coh_input_touch(&s,1,5,2,0));
    CHECK(coh_input_frame(&s,0,&f) && f.held==0 && f.rejected==8);proof->adapter_cases++;
    coh_input_init(&s);CHECK(coh_input_axes(&s,0,0,1,-1));
    CHECK(coh_input_frame(&s,0.05f,&f) && f.delta_x==50 && f.delta_y== -50);
    CHECK(coh_input_axes(&s,0,0,0,0));CHECK(coh_input_frame(&s,0.05f,&f) && f.delta_x==0 && f.delta_y==0);proof->adapter_cases++;
#undef CHECK
    return proof->failed==0;
}
