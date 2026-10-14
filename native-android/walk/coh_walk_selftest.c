#include "coh_walk.h"
#include "walk_goldens.h"
#include <math.h>
#include <string.h>
extern void coh_walk_velocity_probe(float,unsigned,unsigned,const float[3],const float[3],const float[3],float[3]);
static void verify(CohWalkProof *p,int ok){p->checks++;if(!ok)p->failed++;}
int coh_walk_selftest(CohWalkProof *proof){
 CohWalkProof p={0};unsigned i,j;CohWalkWorld world={0};CohWalkState s,before;float lo[3]={-20,0,-20},hi[3]={20,8,20},spawn[3]={0,0,-5};
 CohWalkTriangle tris[]={
  {{{-20,0,-20},{-20,0,20},{20,0,-20}},COH_WALK_NORMALTRI},
  {{{20,0,-20},{-20,0,20},{20,0,20}},COH_WALK_NORMALTRI},
  {{{-10,0,0},{10,8,0},{10,0,0}},COH_WALK_NORMALTRI},
  {{{-10,0,0},{-10,8,0},{10,8,0}},COH_WALK_NORMALTRI}
 };
 for(i=0;i<sizeof(walk_goldens)/sizeof(walk_goldens[0]);i++){
  const CohWalkGolden *g=&walk_goldens[i];float out[3],error=0;
  coh_walk_velocity_probe(g->timestep,g->flags,g->state,g->input,g->vel,g->normal,out);
  for(j=0;j<3;j++){float e=fabsf(out[j]-g->out[j]);if(!isfinite(out[j]))error=INFINITY;else if(e>error)error=e;}
  if(error>p.max_source_error)p.max_source_error=error;
  verify(&p,error<=.00001f);p.source_cases++;
 }
 int ok=coh_walk_world_init(&world,tris,4,lo,hi);verify(&p,ok);
 if(ok){ok=coh_walk_init(&s,&world,spawn,0);verify(&p,ok);
  if(ok){verify(&p,s.grounded&&fabsf(s.position[1])<.00001f);
   for(i=0;i<60;i++)verify(&p,coh_walk_step(&s,&world,COH_MOTION_FORWARD,0));
   verify(&p,s.position[2]<-1.f&&s.position[2]>-1.2f&&s.blocked_steps>0);p.collision_cases++;
   float x=s.position[0];for(i=0;i<10;i++)verify(&p,coh_walk_step(&s,&world,COH_MOTION_FORWARD|COH_MOTION_RIGHT,0));
   verify(&p,s.position[0]>x+.1f&&s.position[2]<-1.f&&s.slide_steps>0);p.collision_cases++;
   coh_walk_clear(&s);verify(&p,s.physics.vel[0]==0&&s.physics.vel[2]==0);
   before=s;verify(&p,!coh_walk_step(&s,&world,16,0));verify(&p,!memcmp(&s,&before,sizeof(s)));
   verify(&p,!coh_walk_step(&s,&world,0,NAN));verify(&p,!memcmp(&s,&before,sizeof(s)));
   verify(&p,!coh_walk_init(&s,&world,(float[]){19,6,19},0));p.collision_cases++;
  }
  coh_walk_world_destroy(&world);verify(&p,world.prepared==NULL);
 }
 if(proof)*proof=p;
 return p.failed?0:1;
}
