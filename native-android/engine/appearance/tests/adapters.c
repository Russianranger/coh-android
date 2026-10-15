#include "../coh_appearance.h"
#include <assert.h>
#include <string.h>
unsigned appearance_adapter_tests(void){
 CohAppearanceDraw d={0};CohAssetGeo g={0};CohAssetGeoModel m={0},old=m;uint32_t index=99;unsigned n=0;
 strcpy(d.model_name,"missing");assert(coh_appearance_geo_model(&g,&d,1,&index,&m)==COH_NOT_FOUND&&index==99&&!memcmp(&m,&old,sizeof m));n++;
 g.model_count=2;assert(coh_appearance_geo_model(&g,&d,1,&index,&m)==COH_LIMIT);n++;
 memset(d.model_name,'a',256);assert(coh_appearance_geo_model(&g,&d,1,&index,&m)==COH_INVALID);n++;
 memset(d.model_name,0,256);strcpy(d.model_name,"test");d.flags=COH_APPEARANCE_CLEAR;assert(coh_appearance_geo_model(&g,&d,5,&index,&m)==COH_NOT_FOUND);n++;
 d.flags=0;d.socket=0;CohAnimationRig rig={0};CohAnimationPose pose={0};CohCharacterMorph morph={0};uint32_t ids[]={0};float rows[12],before[12];for(unsigned i=0;i<12;i++)rows[i]=88.f;memcpy(before,rows,sizeof rows);
 for(unsigned i=0;i<99;i++)rig.parent[i]=-2;
 rig.parent[0]=-1;rig.node_count=1;rig.order[0]=0;pose.world_rows[0][0]=pose.world_rows[0][5]=pose.world_rows[0][10]=1;
 assert(coh_appearance_palette(&d,0,&rig,NULL,&pose,ids,1,rows,11)==COH_LIMIT&&!memcmp(rows,before,sizeof rows));n++;
 assert(coh_appearance_palette(&d,1,&rig,&morph,&pose,ids,1,rows,12)==COH_UNSUPPORTED&&!memcmp(rows,before,sizeof rows));n++;
 assert(coh_appearance_palette(&d,0,&rig,NULL,&pose,ids,1,rows,12)==COH_OK&&rows[0]==1&&rows[5]==1&&rows[10]==1&&rows[3]==0);n++;
 d.socket=99;memcpy(before,rows,sizeof rows);assert(coh_appearance_palette(&d,0,&rig,NULL,&pose,ids,1,rows,12)==COH_INVALID&&!memcmp(rows,before,sizeof rows));n++;
 return n;
}
