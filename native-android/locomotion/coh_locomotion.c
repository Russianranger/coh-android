#include "coh_locomotion.h"
#include <math.h>
#include <string.h>
static uint32_t read32(const uint8_t *p) {
    return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static int rig_name(const CohAnimationRig *r,const char *name) {
    const uint8_t *p=r->motion.bytes+4;
    for(size_t i=0;i<256;i++) {
        unsigned a=p[i],b=(unsigned char)name[i];
        if(a=='\\')a='/';
        if(a>='A'&&a<='Z')a+='a'-'A';
        if(a!=b)return 0;
        if(!a)return 1;
    }
    return 0;
}
int coh_locomotion_parse(const uint8_t *p,size_t n,CohLocomotion *out) {
    if(!p||!out||n<64||n>128u*1024u||memcmp(p,"COHLOCO1",8)||
       read32(p+8)!=1||read32(p+12)!=64||read32(p+16)!=3||read32(p+20)!=n)return -1;
    for(unsigned k=48;k<64;k+=4)if(read32(p+k))return -1;
    CohLocomotion l={0};l.bytes=p;l.byte_count=n;size_t offset=64;
    static const char *names[3]={"huge/skel_ready","huge/run","huge/postrun"};
    static const float last[3]={60.f,25.f,23.f};
    for(unsigned i=0;i<3;i++) {
        uint32_t start=read32(p+24+i*8),bytes=read32(p+28+i*8);
        if(start!=offset||start>n||bytes>n-start||coh_animation_parse(p+start,bytes,&l.rigs[i]))return -1;
        const CohAnimationRig *r=&l.rigs[i];
        if(!rig_name(r,names[i])||r->first_frame!=1.f||r->last_frame!=last[i]||
           r->ticks_per_second!=30.f||r->node_count!=60||r->parent[0]!=-1)return -1;
        if(i&&(r->base.byte_count!=l.rigs[0].base.byte_count||
               memcmp(r->base.bytes,l.rigs[0].base.bytes,r->base.byte_count)))return -1;
        offset+=(size_t)bytes;
    }
    if(offset!=n)return -1;
    *out=l;return 0;
}
void coh_locomotion_init(CohLocomotionState *s) {
    if(!s)return;
    memset(s,0,sizeof *s);s->frame=1.f;s->previous_frame=-1.f;s->move_rate_scale=1.f;s->ready_entries=1;
}
const CohAnimationRig *coh_locomotion_rig(const CohLocomotion *l,const CohLocomotionState *s) {
    return l&&s&&s->move<3?&l->rigs[s->move]:0;
}
const char *coh_locomotion_move_name(uint32_t move) {
    static const char *names[3]={"Ready","RunCycle","RunPost"};
    return move<3?names[move]:"Invalid";
}
static void set_move(CohLocomotionState *s,unsigned move) {
    /* These selected transitions always reset in source seqSetMove:
     * Ready is complex-cycle; RunPost is not cyclic. */
    s->move=move;s->frame=1.f;s->previous_frame=-1.f;s->transitions++;
    if(move==COH_LOCOMOTION_READY)s->ready_entries++;
    else if(move==COH_LOCOMOTION_RUN)s->run_entries++;
    else s->post_entries++;
}
int coh_locomotion_step(const CohLocomotion *l,CohLocomotionState *s,int forward,
                        float dt,float distance,float geom_y) {
    if(!l||!s||s->move>=3||(forward!=0&&forward!=1)||!isfinite(dt)||dt<0.f||dt>3.f||
       !isfinite(distance)||distance<0.f||distance>1000.f||!isfinite(geom_y)||geom_y<=0.f||geom_y>32.f||
       !isfinite(s->frame)||s->frame<1.f||s->frame>l->rigs[s->move].last_frame)return -1;
    CohLocomotionState next=*s;
    /* entclient.c takes actual displacement per engine TIMESTEP and compares
     * against MoveRate (feet/engine frame), not a frame clock multiplier .7. */
    float rate=1.f;
    if(next.move==COH_LOCOMOTION_RUN) {
        rate=(distance/(dt?dt:1.f))/.7f;
        if(rate<.25f)rate=.25f;
        if(rate>2.f)rate=2.f;
    }
    next.move_rate_scale=rate;
    if(forward&&next.move!=COH_LOCOMOTION_RUN)set_move(&next,COH_LOCOMOTION_RUN);
    else if(!forward&&next.move==COH_LOCOMOTION_RUN)set_move(&next,COH_LOCOMOTION_POST);
    else {
        /* Source seqGetAnimScale default predictable capped size scaling. */
        float size=1.f/geom_y;if(size<.5f)size=.5f;if(size>1.5f)size=1.5f;
        next.previous_frame=next.frame;next.frame+=(rate*dt)*size;
        float last=l->rigs[next.move].last_frame;
        if(next.frame>last) {
            if(next.move==COH_LOCOMOTION_POST)set_move(&next,COH_LOCOMOTION_READY);
            else {
                /* seqCycleFrame preserves strict >end and single subtraction. */
                next.frame-=last-1.f;if(next.frame>last)next.frame=1.f;
                next.previous_frame=-1.f;next.cycles++;
            }
        }
    }
    if(!isfinite(next.frame))return -1;
    *s=next;return 0;
}
float coh_locomotion_hip_y(const CohLocomotionState *s,float y) {
    if(!s||s->move!=COH_LOCOMOTION_RUN||s->move_rate_scale<=1.05f)return y;
    float modifier=s->move_rate_scale*s->move_rate_scale;
    return 3.3f+((y-3.3f)/modifier);
}
int coh_locomotion_sample(const CohLocomotion *l,const CohLocomotionState *s,
                          const CohCharacterMorph *m,CohAnimationPose *out) {
    const CohAnimationRig *r=coh_locomotion_rig(l,s);
    if(!r||!out||!m||!isfinite(s->move_rate_scale)||s->move_rate_scale<.25f||
       s->move_rate_scale>2.f)return -1;
    CohAnimationPose pose;
    if(coh_character_sample(r,m,s->frame,&pose))return -1;
    /* gfxTreeFindBoneInAnimation(0,...,1) selects HIPS bone0; the final1
     * controls recursive lookup, not the bone ID. */
    float hip=coh_locomotion_hip_y(s,pose.position[0][1]);
    float delta=hip-pose.position[0][1];
    pose.position[0][1]=hip;
    if(delta) {
        float shift[3];for(unsigned j=0;j<3;j++)shift[j]=m->actor_root_rows[j*4+1]*delta;
        for(unsigned i=0;i<r->node_count;i++) {
            unsigned id=r->order[i];int ancestor=(int)id;unsigned depth=0;
            while(ancestor>=0&&ancestor!=0&&depth++<COH_ANIMATION_BONES)ancestor=r->parent[ancestor];
            if(ancestor==0)for(unsigned j=0;j<3;j++)pose.world_rows[id][j*4+3]+=shift[j];
        }
    }
    *out=pose;return 0;
}
