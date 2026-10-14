#include "../../walk/coh_walk.h"
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#define CHECK(c) do { checks++;if(!(c)){failed++;fprintf(stderr,"check failed line %d: %s\n",__LINE__,#c);} }while(0)
/* Synthetic query witnesses exercise adapter boundaries; actual authored scene
 * qualification is additional and identified separately by its manifest. */
int main(void) {
 unsigned checks=0,failed=0;CohWalkProof proof;CHECK(coh_walk_selftest(&proof));CHECK(proof.failed==0);CohWalkWorld world={0};CohWalkState state,before;float lo[3]={-20,0,-20},hi[3]={20,8,20},spawn[3]={0,0,-5};
 CohWalkTriangle tri[]={
  {{{-20,0,-20},{-20,0,20},{20,0,-20}},COH_WALK_NORMALTRI},
  {{{20,0,-20},{-20,0,20},{20,0,20}},COH_WALK_NORMALTRI},
  {{{-10,0,0},{10,8,0},{10,0,0}},COH_WALK_NORMALTRI},
  {{{-10,0,0},{-10,8,0},{10,8,0}},COH_WALK_NORMALTRI}
 };
 CHECK(coh_walk_world_init(&world,tri,4,lo,hi));CHECK(coh_walk_init(&state,&world,spawn,0));
 CHECK(state.grounded&&fabsf(state.position[1])<.00001f);
 for(unsigned i=0;i<60;i++)CHECK(coh_walk_step(&state,&world,COH_MOTION_FORWARD,0));
 CHECK(state.position[2]<-1.f&&state.position[2]>-1.2f);CHECK(state.blocked_steps>0);CHECK(state.grounded);
 float x=state.position[0];for(unsigned i=0;i<10;i++)CHECK(coh_walk_step(&state,&world,COH_MOTION_FORWARD|COH_MOTION_RIGHT,0));
 CHECK(state.position[0]>x+.1f);CHECK(state.position[2]<-1.f);CHECK(state.slide_steps>0);
 coh_walk_clear(&state);for(unsigned i=0;i<6;i++)CHECK(coh_walk_step(&state,&world,0,0));CHECK(state.physics.vel[0]==0&&state.physics.vel[2]==0);
 before=state;CHECK(!coh_walk_step(&state,&world,16,0));CHECK(!memcmp(&state,&before,sizeof(state)));
 CHECK(!coh_walk_step(&state,&world,0,NAN));CHECK(!memcmp(&state,&before,sizeof(state)));
 state.physics.vel[0]=NAN;before=state;CHECK(!coh_walk_step(&state,&world,0,0));CHECK(!memcmp(&state,&before,sizeof(state)));state=before;state.physics.vel[0]=0;
 CHECK(!coh_walk_init(&state,&world,(float[]){19,6,19},0));
 CohWalkWorld invalid={0};tri[0].v[0][0]=NAN;CHECK(!coh_walk_world_init(&invalid,tri,4,lo,hi));CHECK(invalid.prepared==NULL);
 tri[0].v[0][0]=-20;CHECK(!coh_walk_world_init(&invalid,tri,8193,lo,hi));CHECK(!coh_walk_world_init(&invalid,tri,4,hi,lo));
 coh_walk_world_destroy(&world);CHECK(world.prepared==NULL);
 printf("{\"passed\":%s,\"checks\":%u,\"failed\":%u}\n",failed?"false":"true",checks,failed);return failed?1:0;
}
