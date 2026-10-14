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
    if(!p||!out||n<64||n>512u*1024u)return -1;
    unsigned v2=!memcmp(p,"COHLOCO2",8),count=v2?12:3,header=v2?128:64;
    if(!v2&&n>128u*1024u)return -1;
    if((!v2&&memcmp(p,"COHLOCO1",8))||n<header||read32(p+8)!=(v2?2u:1u)||
       read32(p+12)!=header||read32(p+16)!=count||read32(p+20)!=n)return -1;
    for(unsigned k=24+count*8;k<header;k+=4)if(read32(p+k))return -1;
    CohLocomotion l={0};l.bytes=p;l.byte_count=n;l.clip_count=count;size_t offset=header;
    static const char *names[12]={"huge/skel_ready","huge/run","huge/postrun","huge/run",
        "male/walk","male/skel_ready2","huge/runback","huge/runback",
        "huge/run_left","huge/run_left","huge/run_right","huge/run_right"};
    static const float first[12]={1,1,1,18,47,1,1,1,15,1,1,1};
    static const float last[12]={60,25,23,25,48,0,24,24,25,25,25,25};
    for(unsigned i=0;i<count;i++) {
        uint32_t start=read32(p+24+i*8),bytes=read32(p+28+i*8);
        if(start!=offset||start>n||bytes>n-start||coh_animation_parse(p+start,bytes,&l.rigs[i]))return -1;
        const CohAnimationRig *r=&l.rigs[i];
        if(!rig_name(r,names[i])||r->first_frame!=first[i]||
           (last[i]?r->last_frame!=last[i]:r->last_frame!=60.f)||
           r->ticks_per_second!=30.f||r->parent[0]!=-1)return -1;
        if(i!=4&&i!=5&&r->node_count!=60)return -1;
        if(i&&i!=4&&i!=5&&(r->base.byte_count!=l.rigs[0].base.byte_count||
               memcmp(r->base.bytes,l.rigs[0].base.bytes,r->base.byte_count)))return -1;
        offset+=(size_t)bytes;
    }
    if(offset!=n)return -1;
    if(v2)for(unsigned i=4;i<=5;i++) {
        /* ParentType male motion on the actor's unchanged Huge hierarchy.
         * animAttachBoneTracks computes selected track's frame0 minus actor
         * base position, and uses the animation backup then actor base. */
        CohAnimationRig *r=&l.rigs[i];const CohAnimationRig *actor=&l.rigs[0];
        if(!rig_name(&(CohAnimationRig){.motion=r->base},"male/skel_ready2"))return -1;
        for(unsigned j=0;j<actor->node_count;j++) {
            unsigned id=actor->order[j];
            if(r->motion.tracks[id].present)for(unsigned k=0;k<3;k++)
                r->animation_delta[id][k]+=r->base_position[id][k]-actor->base_position[id][k];
            else if(r->base.tracks[id].present) {
                r->motion.tracks[id]=r->base.tracks[id];
                for(unsigned k=0;k<3;k++)r->animation_delta[id][k]=r->base_position[id][k]-actor->base_position[id][k];
            } else for(unsigned k=0;k<3;k++)r->animation_delta[id][k]=0.f;
        }
        memcpy(r->parent,actor->parent,sizeof r->parent);memcpy(r->order,actor->order,sizeof r->order);
        memcpy(r->bind_translation,actor->bind_translation,sizeof r->bind_translation);
        memcpy(r->base_position,actor->base_position,sizeof r->base_position);
        memcpy(r->base_rotation,actor->base_rotation,sizeof r->base_rotation);r->node_count=actor->node_count;
    }
    *out=l;return 0;
}
void coh_locomotion_init(CohLocomotionState *s) {
    if(!s)return;
    memset(s,0,sizeof *s);s->frame=1.f;s->previous_frame=-1.f;s->move_rate_scale=1.f;s->ready_entries=1;s->selection_changed=1;
}
const CohAnimationRig *coh_locomotion_rig(const CohLocomotion *l,const CohLocomotionState *s) {
    return l&&s&&s->move<l->clip_count?&l->rigs[s->move]:0;
}
const char *coh_locomotion_move_name(uint32_t move) {
    static const char *names[12]={"Ready","RunCycle","RunPost","RunPre","Idle_Walk_Post","Idle_Ready",
        "Run_Back_Pre","Run_Back_Cycle","Run_Left_Pre","Run_Left_Cycle","Run_Right_Pre","Run_Right_Cycle"};
    return move<12?names[move]:"Invalid";
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
    if(!s||!(s->move==COH_LOCOMOTION_RUN||s->move==COH_LOCOMOTION_PRE||s->move>=COH_LOCOMOTION_BACK_PRE)||
       s->move>=COH_LOCOMOTION_CLIPS||s->move_rate_scale<=1.05f)return y;
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
static int is_pre(unsigned move) {return move==3||move==6||move==8||move==10;}
static int is_running(unsigned move) {return move==1||is_pre(move)||move==7||move==9||move==11;}
static int is_cycle(unsigned move) {return move==0||move==5||is_running(move);}
static unsigned requirement(unsigned move) {
    static const unsigned bit[12]={0,1,0,1,0,0,2,2,4,4,8,8};return bit[move];
}
static void set_directional_move(const CohLocomotion *l,CohLocomotionState *s,unsigned move) {
    unsigned old=s->move;
    /* seqSetMove's phase retention is disabled for a ComplexCycle source,
     * including Ready (random graph) and each authored Pre. */
    if(is_cycle(move)&&is_cycle(old)&&old!=0&&!is_pre(old)&&
       s->frame>l->rigs[move].first_frame&&s->frame<l->rigs[move].last_frame)s->phase_preservations++;
    else {s->frame=l->rigs[move].first_frame;s->previous_frame=-1.f;}
    s->move=move;s->transitions++;s->selection_changed=1;
    if(move==0||move==5)s->ready_entries++;
    if(move==1||move==7||move==9||move==11)s->run_entries++;
    if(move==2)s->post_entries++;
    if(is_pre(move))s->pre_entries++;
    if(move>=6)s->directional_entries++;
    if(move==4)s->early_stop_entries++;
    if(requirement(old)&&requirement(move)&&requirement(old)!=requirement(move))s->direction_switches++;
}
static int incoming_interrupts(unsigned incoming,unsigned current) {
    int ready=current==0||current==2;
    int move_irq=ready||current==4||current==5;
    if(incoming==3||incoming==6)return ready||move_irq;
    if(incoming==8||incoming==10)return ready||move_irq||current==3;
    if(incoming==7)return current==8||current==9||current==10||current==11;
    if(incoming==9||incoming==11)return current==3||current==1;
    return 0;
}
int coh_locomotion_step_directional(const CohLocomotion *l,CohLocomotionState *s,
                                  uint32_t mask,float dt,float distance,float geom_y) {
    if(!l||!s||l->clip_count!=12||s->move>=12||mask>15||
       ((mask&3)==3)||((mask&12)==12)||!isfinite(dt)||dt<0.f||dt>3.f||
       !isfinite(distance)||distance<0.f||distance>1000.f||!isfinite(geom_y)||
       geom_y<=0.f||geom_y>32.f||!isfinite(s->frame)||
       s->frame<l->rigs[s->move].first_frame||s->frame>l->rigs[s->move].last_frame)return -1;
    CohLocomotionState next=*s;unsigned old=next.move;float rate=1.f;
    if(is_running(old)) {
        float authored=(old==6||old==7)?.525f:.7f;
        rate=(distance/(dt?dt:1.f))/authored;
        if(rate<.25f)rate=.25f;
        if(rate>2.f)rate=2.f;
    }
    next.move_rate_scale=rate;unsigned move=old;
    if(mask!=next.input_mask||next.selection_changed) {
        /* Original ascending state-bit enumeration and authored list order.
         * Highest-priority ties use seqSearchInterrupts' anim_incrementor. */
        static const unsigned candidates[7]={3,6,7,8,9,10,11};
        unsigned eligible[7],count=0;
        for(unsigned i=0;i<7;i++) {
            unsigned candidate=candidates[i];
            if((mask&requirement(candidate))&&incoming_interrupts(candidate,old))eligible[count++]=candidate;
        }
        if(count)move=eligible[count>1?(next.anim_incrementor++%count):0];
    }
    next.input_mask=mask;next.selection_changed=0;
    /* Wretch has HUGE, not IDLE. Its forced early-stop graph visits
     * Idle_Ready, then that cyclic move's failed IDLE requirement → Ready. */
    if(move==old&&old==5)move=0;
    if(move==old&&requirement(old)&&!(mask&requirement(old)))move=is_pre(old)?4:2;
    if(move==old) {
        float size=1.f/geom_y;if(size<.5f)size=.5f;if(size>1.5f)size=1.5f;
        next.previous_frame=next.frame;next.frame+=rate*dt*size;
        float first=l->rigs[old].first_frame,last=l->rigs[old].last_frame;
        if(next.frame>last) {
            if(is_pre(old))move=old==3?1:old+1;
            else if(old==2)move=0;
            else if(old==4)move=5;
            else {next.frame-=last-first;if(next.frame>last)next.frame=first;next.previous_frame=-1.f;next.cycles++;}
        }
    }
    if(move!=old)set_directional_move(l,&next,move);
    if(!isfinite(next.frame))return -1;
    *s=next;return 0;
}
void coh_locomotion_blend_init(CohLocomotionBlend *b) {if(b)memset(b,0,sizeof *b);}
/* The qualified character composer uses these source basis scaling rules.
 * Recompose the hierarchy after blending local translations/quaternions;
 * interpolating world matrices would deform children and skip morph rules. */
static void affine_compose(const float a[12],const float b[12],float out[12]) {
    float r[12];for(unsigned i=0;i<3;i++) {
        for(unsigned j=0;j<3;j++)r[i*4+j]=a[i*4]*b[j]+a[i*4+1]*b[4+j]+a[i*4+2]*b[8+j];
        r[i*4+3]=a[i*4]*b[3]+a[i*4+1]*b[7]+a[i*4+2]*b[11]+a[i*4+3];
    }memcpy(out,r,sizeof r);
}
static void basis_scale(float a[12],const float s[3],int pre) {
    for(unsigned i=0;i<3;i++)for(unsigned j=0;j<3;j++)a[i*4+j]*=s[pre?i:j];
}
static void local_rows(const CohCharacterMorph *m,unsigned id,const float q[4],const float p[3],float r[12]) {
    float tx=2.f*q[0],ty=2.f*q[1],tz=2.f*q[2],wx=tx*q[3],wy=ty*q[3],wz=tz*q[3];
    float xx=tx*q[0],xy=ty*q[0],xz=tz*q[0],yy=ty*q[1],yz=tz*q[1],zz=tz*q[2];
    r[0]=1.f-(yy+zz);r[1]=xy+wz;r[2]=xz-wy;r[3]=p[0];
    r[4]=xy-wz;r[5]=1.f-(xx+zz);r[6]=yz+wx;r[7]=p[1];
    r[8]=xz+wy;r[9]=yz-wx;r[10]=1.f-(xx+yy);r[11]=p[2];
    float leg=1.f+m->leg_scale,arm=1.f+m->arm_scale;
    if(id==0&&m->leg_scale){float s[3]={1.f,1.f/(1.f+m->leg_scale_ratio*m->leg_scale),1.f};basis_scale(r,s,1);}
    else if(id==4){float s[3]={1.f+m->effective_head_scales[0],1.f+m->effective_head_scales[1],1.f+m->effective_head_scales[2]};basis_scale(r,s,0);}
    else if((id==23||id==24)&&m->leg_scale){float s[3]={1.f,leg,1.f};basis_scale(r,s,0);}
    else if((id==25||id==26)&&m->leg_scale){float a[3]={1.f,1.f/leg,1.f},b[3]={1.f,leg,1.f};basis_scale(r,a,1);basis_scale(r,b,0);}
    else if((id==27||id==28)&&m->leg_scale){float s[3]={1.f,1.f/leg,1.f};basis_scale(r,s,1);}
    else if((id==9||id==10)&&m->arm_scale){float s[3]={arm,arm,arm};basis_scale(r,s,0);}
    else if((id==41||id==42)&&m->arm_scale){float s[3]={1.f/arm,1.f/arm,1.f/arm};basis_scale(r,s,1);}
}
int coh_locomotion_sample_directional(const CohLocomotion *l,const CohLocomotionState *s,
                           const CohCharacterMorph *m,float dt,CohLocomotionBlend *blend,CohAnimationPose *out) {
    if(!l||!s||!m||!blend||!out||l->clip_count!=12||!isfinite(dt)||dt<0.f||dt>3.f||
       !isfinite(s->move_rate_scale)||s->move_rate_scale<.25f||s->move_rate_scale>2.f||
       !isfinite(blend->interpolation_frame)||blend->interpolation_frame<0.f||blend->valid>1)return -1;
    const CohAnimationRig *r=coh_locomotion_rig(l,s);CohAnimationPose pose;
    if(!r||s->frame<r->first_frame||s->frame>r->last_frame||coh_character_sample(r,m,s->frame,&pose))return -1;
    CohLocomotionBlend next=*blend;
    if(next.transition_serial!=s->transitions){
        next.interpolation_frame=0.f;next.transition_serial=s->transitions;
        memset(next.rotation_blend,1,sizeof next.rotation_blend);
        memset(next.translation_blend,1,sizeof next.translation_blend);
    }
    /* seqload's DEFAULT_MOVE_INTERPOLATION_RATE is5. Only RunPost overrides8. */
    next.interpolation_frame+=dt;float frames=s->move==2?8.f:5.f;
    float alpha=next.interpolation_frame<frames?1.f/(1.f+frames-next.interpolation_frame):1.f;
    for(unsigned i=0;i<r->node_count;i++) {
        unsigned id=r->order[i];
        if(!next.valid) {next.rotation_blend[id]=0;next.translation_blend[id]=0;continue;}
        /* animateGfxNodeBone skips the blend helper at percent_new>=1,
         * leaving its flags until the next skeleton change resets them. */
        if(alpha>=1.f)continue;
        if(next.rotation_blend[id]) {
            float dot=0.f,norm=0.f;
            for(unsigned j=0;j<4;j++)dot+=next.previous.rotation[id][j]*pose.rotation[id][j];
            float signed_alpha=dot<0.f?-alpha:alpha;
            for(unsigned j=0;j<4;j++) {
                pose.rotation[id][j]=(1.f-alpha)*next.previous.rotation[id][j]+signed_alpha*pose.rotation[id][j];
                norm+=pose.rotation[id][j]*pose.rotation[id][j];
            }
            if(!isfinite(norm)||norm<=0.f)return -1;
            norm=1.f/sqrtf(norm);for(unsigned j=0;j<4;j++)pose.rotation[id][j]*=norm;
            /* Original CLOSE_ENOUGH_ROT is a double literal in this compare. */
            if((double)dot>1.0-(.0003*(double)dt))next.rotation_blend[id]=0;
        }
        if(next.translation_blend[id]) {
            float delta2=0.f;
            for(unsigned j=0;j<3;j++) {
                pose.position[id][j]=(pose.position[id][j]-next.previous.position[id][j])*alpha+next.previous.position[id][j];
                float delta=pose.position[id][j]-next.previous.position[id][j];delta2+=delta*delta;
            }
            float tolerance=(float)(.001*(double)dt);
            if(delta2<=tolerance*tolerance)next.translation_blend[id]=0;
        }
    }
    /* Source stores last translations before SmoothSprint modifies hip Y. */
    next.previous=pose;next.valid=1;
    pose.position[0][1]=coh_locomotion_hip_y(s,pose.position[0][1]);
    for(unsigned i=0;i<r->node_count;i++) {
        unsigned id=r->order[i];float local[12];local_rows(m,id,pose.rotation[id],pose.position[id],local);
        int parent=r->parent[id];affine_compose(parent<0?m->actor_root_rows:pose.world_rows[parent],local,pose.world_rows[id]);
    }
    *blend=next;*out=pose;return 0;
}
