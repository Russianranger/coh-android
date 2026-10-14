/* Narrow adaptation of pinned original control and NOCOLL kernels. See README. */
#include "coh_motion.h"
#include <math.h>
#include <stddef.h>
#include <string.h>
#include <limits.h>
#define PI 3.14159265358979323846
#define RAD(a) (((a)*PI)*(1.0f/180.0f))
static const unsigned opposite[6]={1,0,3,2,5,4};
static float fix_angle(float a) {
    if(a>RAD(180.0))a-=RAD(360.0);
    if(a<=RAD(-180.0))a+=RAD(360.0);
    return a;
}
static int valid_yaw(float yaw) {return isfinite(yaw)&&yaw>=-3.141593f&&yaw<=3.141593f;}
static int valid_state(const CohMotionState *s) {
    unsigned i;
    if(!s||!valid_yaw(s->control_yaw)||!valid_yaw(s->motion_yaw)||!valid_yaw(s->body_yaw)||
       !isfinite(s->radius)||s->radius<1||s->radius>8192||
       !isfinite(s->move_time)||s->move_time<0||s->move_time>100000000||
       s->clock_ms>UINT32_MAX-34||s->ticks>128848016||s->held>15||s->use_now>15||s->affected_last_frame>15||s->source_state_bits>15||
       s->clock_ms!=(uint32_t)((uint64_t)s->ticks*1000u/30u)||s->held_ms[4]||s->held_ms[5])return 0;
    for(i=0;i<3;i++)if(!isfinite(s->position[i])||!isfinite(s->origin[i])||fabsf(s->origin[i])>1000000||
        !isfinite(s->local_input[i])||!isfinite(s->world_input[i])||fabsf(s->local_input[i])>1.00001f||fabsf(s->world_input[i])>1.00001f)return 0;
    for(i=0;i<6;i++)if(s->held_ms[i]>1000||s->start_ms[i]>s->clock_ms)return 0;
    return fabsf(s->position[0]-s->origin[0])<=s->radius+0.001f&&
           fabsf(s->position[2]-s->origin[2])<=s->radius+0.001f&&s->position[1]==s->origin[1];
}
int coh_motion_init(CohMotionState *s,const float spawn[3],float yaw,float radius) {
    CohMotionState next;unsigned i;
    if(!s||!spawn||!valid_yaw(yaw)||!isfinite(radius)||radius<1||radius>8192)return 0;
    for(i=0;i<3;i++)if(!isfinite(spawn[i])||fabsf(spawn[i])>1000000)return 0;
    memset(&next,0,sizeof(next));memcpy(next.position,spawn,sizeof(next.position));
    memcpy(next.origin,spawn,sizeof(next.origin));next.control_yaw=fix_angle(yaw);
    next.body_yaw=next.control_yaw;next.radius=radius;*s=next;return 1;
}
static float direction_level(uint32_t ms,int down) {
    if(!ms)return 0;
    if(ms>=1000)return 1;
    if(ms<=50&&down)return 0;
    if(ms<75)return 0.2f;
    if(ms<100)return (float)(0.2+0.4*powf((ms-75)*0.04,2));
    return (float)(0.6+(ms-100)*0.004/9.0);
}
int coh_motion_step(CohMotionState *s,uint32_t dirs,float yaw) {
    CohMotionState n;unsigned i;uint32_t cur;uint8_t use_prev;int one_set=0;
    float levels[6],horizontal[3],length,speed,sin_y,cos_y;
    if(!valid_state(s)||dirs>15||!valid_yaw(yaw))return 0;
    n=*s;use_prev=n.use_now;
    /* handleBinaryStateChange, directions delivered at the start of the tick. */
    for(i=0;i<4;i++)if(!!(dirs&(1u<<i))!=!!(n.held&(1u<<i))) {
        unsigned bit=1u<<i;
        if(dirs&bit) {
            n.held|=bit;
            if(!(use_prev&bit)){n.use_now|=bit;n.affected_last_frame|=bit;}
            n.start_ms[i]=n.clock_ms;
        }else {
            n.held&=~bit;
            if(use_prev&bit){n.use_now&=~bit;n.affected_last_frame|=bit;}
            if(!(n.held&(1u<<opposite[i]))) {
                int add=(int)(n.clock_ms-n.start_ms[i]);
                if(add>0){n.held_ms[i]+=(uint32_t)add;if(n.held_ms[i]>1000)n.held_ms[i]=1000;}
                else if(!n.held_ms[i])n.held_ms[i]=1;
            }
        }
    }
    n.ticks++;cur=(uint32_t)((uint64_t)n.ticks*1000u/30u);
    /* pmotionUpdateControlsPrePhysics. */
    for(i=0;i<6&&!one_set;i++)one_set=n.held_ms[i]>=250;
    for(i=0;i<6;i++)if(n.held&(1u<<i)&&!(n.held&(1u<<opposite[i]))) {
        uint16_t add=(uint16_t)(cur-n.start_ms[i]);n.held_ms[i]+=add;
        if(one_set&&n.held_ms[i]<250)n.held_ms[i]=250;
        else if(n.held_ms[i]>1000)n.held_ms[i]=1000;
    }
    /* pmotionSetVel: speed[X/Y]=1, nocoll=1, fly/stun=0, scale=1.
     * speed_back only changes max_speed_scale, unused by entMoveNoColl. */
    for(i=0;i<6;i++)levels[i]=direction_level(n.use_now&(1u<<i)?n.held_ms[i]:0,!!(n.held&(1u<<i)));
    horizontal[0]=levels[3]-levels[2];horizontal[1]=0;horizontal[2]=levels[0]-levels[1];
    length=(float)sqrt(horizontal[0]*horizontal[0]+horizontal[2]*horizontal[2]);
    if(length){float inverse=1.f/length;horizontal[0]*=inverse;horizontal[2]*=inverse;}
    n.local_input[0]=horizontal[0]?(float)(horizontal[0]*fabs(levels[3]-levels[2])):0;
    n.local_input[1]=0;
    n.local_input[2]=horizontal[2]?(float)(horizontal[2]*fabs(levels[0]-levels[1])):0;
    n.source_state_bits=0;
    if(n.local_input[0]>0)n.source_state_bits|=COH_MOTION_STATE_STEPRIGHT;
    if(n.local_input[0]<0)n.source_state_bits|=COH_MOTION_STATE_STEPLEFT;
    if(n.local_input[2]>0)n.source_state_bits|=COH_MOTION_STATE_FORWARD;
    if(n.local_input[2]<0)n.source_state_bits|=COH_MOTION_STATE_BACKWARD;
    n.control_yaw=fix_angle(yaw);
    /* playerAdjustMotionPYR and the original CSC_ANGLE macros. */
    {uint32_t angle=(uint32_t)(0.5+(n.control_yaw+PI)*2048/(2*PI));
     n.motion_yaw=(float)((float)(angle&2047u)*(2*PI)/2048-PI);}
    /* createMat3RYP/mulVecMat3, zero pitch and roll. */
    sin_y=sinf(n.motion_yaw);cos_y=cosf(n.motion_yaw);
    n.world_input[0]=n.local_input[0]*cos_y+n.local_input[2]*sin_y;
    n.world_input[1]=0;
    n.world_input[2]=n.local_input[0]*-sin_y+n.local_input[2]*cos_y;
    /* playerAdjustBodyPYR normal strafe branch; time_to_realign=0. */
    n.body_yaw=fix_angle(n.body_yaw+(float)(fix_angle(n.control_yaw-n.body_yaw)*0.4f));
    /* entMoveNoColl: original e->timestep=1 at fixed 30 Hz. */
    n.move_time+=1;speed=(n.move_time+6)/6.f;if(speed>50.f)speed=50.f;
    n.position[0]+=n.world_input[0]*speed;n.position[2]+=n.world_input[2]*speed;
    if(n.world_input[0]*n.world_input[0]+n.world_input[2]*n.world_input[2]<=0.001f)n.move_time=0;
    if(n.local_input[0]==0&&n.local_input[2]==0&&n.stopped_steps<UINT32_MAX)n.stopped_steps++;
    /* Explicit adapter safety square; does not claim collision. */
    {int bounded=0;unsigned axis;
     for(axis=0;axis<3;axis+=2){float lo=n.origin[axis]-n.radius,hi=n.origin[axis]+n.radius;
         if(n.position[axis]<lo){n.position[axis]=lo;bounded=1;}
         if(n.position[axis]>hi){n.position[axis]=hi;bounded=1;}}
     if(bounded&&n.bounded_steps<UINT32_MAX)n.bounded_steps++;}
    /* pmotionUpdateControlsPostPhysics. */
    for(i=0;i<6;i++) {
        if(!(n.held&(1u<<i))||n.held&(1u<<opposite[i]))n.held_ms[i]=0;
        n.start_ms[i]=cur;
    }
    n.use_now|=(uint8_t)((n.held^n.use_now)&~n.affected_last_frame);
    n.affected_last_frame=0;n.clock_ms=cur;*s=n;return 1;
}
void coh_motion_clear(CohMotionState *s) {
    unsigned i;if(!s)return;s->held=s->use_now=s->affected_last_frame=s->source_state_bits=0;
    memset(s->held_ms,0,sizeof(s->held_ms));memset(s->local_input,0,sizeof(s->local_input));
    memset(s->world_input,0,sizeof(s->world_input));s->move_time=0;
    for(i=0;i<6;i++)s->start_ms[i]=s->clock_ms;
}
