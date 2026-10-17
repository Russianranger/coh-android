#include "../coh_wr_lod.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"LOD line%d %s\n",__LINE__,#x);exit(1);}}while(0)
extern CohWrLodProjection original_project(const CohWrLodInput *);
int main(void){
 CohWrLodInput q={0,1,1,1,{10,5,40,10},{20,0,50,0},3,8,60,0,0,0,200};
 static const float distances[]={0,5,9,10,11,15,20,25,39,40,41,45,49,50,51,100,199,200,201};
 static const float alpha[]={0,0.00001f,0.0001f,0x1.a36e2cp-14f,0x1.a36e30p-14f,0.25f,0.5f,0.999f,1};
 for(unsigned flags=0;flags<16384;flags++)for(unsigned d=0;d<19;d++){
  q.flags=flags;q.distance=distances[d];q.draw_alpha=alpha[(flags+d)%9];q.lod_fadenode=(flags+d)%3;
  q.client_lod_scale=(flags%3)+1;q.client_fade_range=(flags%3)*0.5f;q.lamp_alpha=(flags+d)%256;
  CohWrLodProjection expected=original_project(&q),actual={999,998,997};
  CHECK(coh_wr_lod_project(&q,&actual)==COH_OK);CHECK(!memcmp(&actual,&expected,sizeof(actual)));
 }
 q=(CohWrLodInput){20,1,1,1,{10,5,40,10},{20,0,50,0},3,8,60,0,0,0,200};
 CohWrLodProjection sentinel={111,222,333},out=sentinel;
 for(unsigned which=0;which<16;which++)for(unsigned kind=0;kind<3;kind++){
  CohWrLodInput bad=q;float *fields[]={&bad.distance,&bad.scale,&bad.client_lod_scale,&bad.client_fade_range,&bad.definition_radius,&bad.node_radius,&bad.fog_far,&bad.draw_alpha,&bad.definition_lod[0],&bad.definition_lod[1],&bad.definition_lod[2],&bad.definition_lod[3],&bad.selected_lod[0],&bad.selected_lod[1],&bad.selected_lod[2],&bad.selected_lod[3]};
  *fields[which]=kind==0?NAN:kind==1?INFINITY:-1.f;CHECK(coh_wr_lod_project(&bad,&out)==COH_INVALID);CHECK(!memcmp(&out,&sentinel,sizeof(out)));
 }
 CohWrLodInput bad=q;
 for(unsigned which=0;which<8;which++){
  bad=q;
  if(which==0)bad.flags=16384;
  if(which==1)bad.lod_fadenode=3;
  if(which==2)bad.lamp_alpha=256;
  if(which==3)bad.draw_alpha=1.001f;
  if(which==4)bad.client_fade_range=1.001f;
  if(which==5)bad.definition_lod[0]=41;
  if(which==6){bad.flags=COH_WR_LOD_WINDOW;bad.definition_lod[0]=0;bad.definition_lod[2]=0;}
  if(which==7)bad.scale=0;
  CHECK(coh_wr_lod_project(&bad,&out)==COH_INVALID);CHECK(!memcmp(&out,&sentinel,sizeof(out)));
 }
 bad=q;bad.scale=0x1p-149f;bad.client_lod_scale=0x1p-149f;
 CHECK(coh_wr_lod_project(&bad,&out)==COH_LIMIT);CHECK(!memcmp(&out,&sentinel,sizeof(out)));
 bad=q;bad.flags=COH_WR_LOD_WINDOW;bad.scale=0x1p-149f;bad.definition_lod[0]=0;bad.definition_lod[2]=0x1p-149f;
 CHECK(coh_wr_lod_project(&bad,&out)==COH_LIMIT);CHECK(!memcmp(&out,&sentinel,sizeof(out)));
 q.scale=3.402823466e38f;q.client_lod_scale=2;CHECK(coh_wr_lod_project(&q,&out)==COH_LIMIT);CHECK(!memcmp(&out,&sentinel,sizeof(out)));
 CHECK(coh_wr_lod_project(&q,(CohWrLodProjection*)&q)==COH_INVALID);CHECK(coh_wr_lod_project(NULL,&out)==COH_INVALID);CHECK(coh_wr_lod_project(&q,NULL)==COH_INVALID);
 printf("{\"passed\":true,\"checks\":%u,\"source_combinations\":311296,\"client_semantic_authority\":false,\"world_authority\":false}\n",checks);
}
