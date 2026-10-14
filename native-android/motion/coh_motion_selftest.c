#include "coh_motion.h"
#include "motion_goldens.h"
#include <math.h>
#include <string.h>
#include <stdint.h>
static void check(CohMotionProof*p,int ok){p->checks++;if(!ok)p->failed++;}
int coh_motion_selftest(CohMotionProof *p) {
    CohMotionState state,before;unsigned row,j;const float spawn[3]={0,0,0};
    if(!p)return 0;
    memset(p,0,sizeof(*p));memset(&state,0,sizeof(state));
    for(row=0;row<COH_MOTION_GOLDEN_COUNT;row++) {
        const CohMotionGolden*g=&coh_motion_goldens[row];float got[12];
        if(g->reset)check(p,coh_motion_init(&state,spawn,g->yaw,8192));
        check(p,coh_motion_step(&state,g->dirs,g->yaw));
        memcpy(got,state.position,3*sizeof(float));memcpy(got+3,state.local_input,3*sizeof(float));
        memcpy(got+6,state.world_input,3*sizeof(float));got[9]=state.motion_yaw;got[10]=state.body_yaw;got[11]=state.move_time;
        for(j=0;j<12;j++) {float e=fabsf(got[j]-g->values[j]);if(e>p->max_source_error)p->max_source_error=e;
            check(p,isfinite(got[j])&&e<=0.002f+fabsf(g->values[j])*0.000001f);}
        for(j=0;j<6;j++)check(p,state.held_ms[j]==g->integers[j]);
        check(p,state.use_now==g->integers[6]);check(p,state.source_state_bits==g->integers[7]);p->source_cases++;
    }
    check(p,coh_motion_init(&state,spawn,0,1));
    for(j=0;j<200;j++)check(p,coh_motion_step(&state,COH_MOTION_FORWARD,0));
    check(p,state.position[2]==1&&state.bounded_steps>0);p->adapter_cases++;
    check(p,coh_motion_step(&state,0,0));before=state;
    for(j=0;j<20;j++)check(p,coh_motion_step(&state,0,0));
    check(p,state.position[0]==before.position[0]&&state.position[2]==before.position[2]&&state.move_time==0);p->adapter_cases++;
    /* Invalid commands and init leave the complete state unchanged. */
    before=state;check(p,!coh_motion_step(&state,16,0));check(p,!memcmp(&state,&before,sizeof(state)));p->adapter_cases++;
    check(p,!coh_motion_step(&state,1,NAN));check(p,!memcmp(&state,&before,sizeof(state)));p->adapter_cases++;
    check(p,!coh_motion_step(&state,1,INFINITY));check(p,!memcmp(&state,&before,sizeof(state)));p->adapter_cases++;
    check(p,!coh_motion_step(&state,1,4));check(p,!memcmp(&state,&before,sizeof(state)));p->adapter_cases++;
    check(p,!coh_motion_init(&state,spawn,0,0));check(p,!memcmp(&state,&before,sizeof(state)));p->adapter_cases++;
    {float bad[3]={0,NAN,0};check(p,!coh_motion_init(&state,bad,0,96));check(p,!memcmp(&state,&before,sizeof(state)));p->adapter_cases++;}
    state.held_ms[0]=1001;before=state;check(p,!coh_motion_step(&state,1,0));check(p,!memcmp(&state,&before,sizeof(state)));p->adapter_cases++;
    check(p,coh_motion_init(&state,spawn,0,96));state.clock_ms=1;before=state;
    check(p,!coh_motion_step(&state,1,0));check(p,!memcmp(&state,&before,sizeof(state)));p->adapter_cases++;
    check(p,coh_motion_init(&state,spawn,0,96));
    for(j=0;j<12;j++)check(p,coh_motion_step(&state,COH_MOTION_RIGHT,0));
    before=state;coh_motion_clear(&state);check(p,state.held==0&&state.use_now==0&&state.move_time==0&&state.source_state_bits==0);
    check(p,state.position[0]==before.position[0]&&state.position[2]==before.position[2]);
    check(p,coh_motion_step(&state,0,0));check(p,state.position[0]==before.position[0]&&state.position[2]==before.position[2]);p->adapter_cases++;
    return p->failed==0;
}
