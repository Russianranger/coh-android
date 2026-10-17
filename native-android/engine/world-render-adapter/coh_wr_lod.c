#include "coh_wr_lod.h"
#include <math.h>
#include <stdint.h>
static int bit(uint32_t flags,uint32_t mask){return (flags&mask)!=0;}
CohStatus coh_wr_lod_project(const CohWrLodInput *q,CohWrLodProjection *out){
 if(!q||!out)return COH_INVALID;
 uintptr_t a=(uintptr_t)q,b=(uintptr_t)out;
 if(a>UINTPTR_MAX-sizeof(*q)||b>UINTPTR_MAX-sizeof(*out)||
    (a<b+sizeof(*out)&&b<a+sizeof(*q)))return COH_INVALID;
 if(q->flags>16383u||q->lod_fadenode>2||q->lamp_alpha>255)return COH_INVALID;
 const float values[]={q->distance,q->scale,q->client_lod_scale,q->client_fade_range,
 q->definition_radius,q->node_radius,q->fog_far,q->draw_alpha};
 for(unsigned i=0;i<8;i++)if(!isfinite(values[i])||values[i]<0)return COH_INVALID;
 if(q->scale==0||q->client_lod_scale==0||q->client_fade_range>1||q->draw_alpha>1)return COH_INVALID;
 for(unsigned i=0;i<4;i++)if(!isfinite(q->definition_lod[i])||q->definition_lod[i]<0||
    !isfinite(q->selected_lod[i])||q->selected_lod[i]<0)return COH_INVALID;
 const float *lod=bit(q->flags,COH_WR_LOD_SELECTED)?q->selected_lod:q->definition_lod;
 if(lod[0]>lod[2]||(bit(q->flags,COH_WR_LOD_WINDOW)&&lod[2]==0))return COH_INVALID;
 float scale=q->scale*q->client_lod_scale;
 float near=lod[0]*scale,nearfade=lod[1]*scale,far=lod[2]*scale,farfade=lod[3]*scale;
 if(scale==0||!isfinite(scale)||!isfinite(near)||!isfinite(nearfade)||!isfinite(far)||!isfinite(farfade))return COH_LIMIT;
 if(bit(q->flags,COH_WR_LOD_DEBUG_FADE)&&q->client_fade_range!=1.f){
  near-=nearfade*(1-q->client_fade_range);far+=farfade*(1-q->client_fade_range);
  nearfade*=q->client_fade_range;farfade*=q->client_fade_range;
 }
 float radius=q->lod_fadenode&&(bit(q->flags,COH_WR_LOD_PARENT_FADE)||q->lod_fadenode==2)?q->node_radius:q->definition_radius;
 float fog=q->fog_far+radius;
 if(!isfinite(far)||!isfinite(fog)||(bit(q->flags,COH_WR_LOD_WINDOW)&&far==0))return COH_LIMIT;
 CohWrLodProjection result={0,0,0};
 int trick=bit(q->flags,COH_WR_LOD_MODEL_TRICK);
 result.beyond_fog=!(trick&&bit(q->flags,COH_WR_LOD_NOFOG))&&!bit(q->flags,COH_WR_LOD_DRAW_ALL)&&q->distance>fog;
 float alpha=1.f,alpha2=1.f,dist=q->distance;unsigned alpha3=255;
 if(result.beyond_fog&&!bit(q->flags,COH_WR_LOD_NO_FOG_CLIP)&&bit(q->flags,COH_WR_LOD_FOG_CLIP)){
  alpha2=1-((dist-fog)/100.f);if(alpha2>1)alpha2=1;if(alpha2<0)alpha2=0;
 }
 if(dist<near){dist=near-dist;if(dist>=nearfade){*out=result;return COH_OK;}alpha=1.f-dist/nearfade;}
 else if(dist>far){if(bit(q->flags,COH_WR_LOD_WINDOW)){result.alpha=255;*out=result;return COH_OK;}
  dist-=far;if(dist>=farfade){*out=result;return COH_OK;}alpha=1.f-dist/farfade;
 }else if(bit(q->flags,COH_WR_LOD_WINDOW)){alpha=dist/far;if(alpha<0.31f)alpha=0.31f;}
 if(trick&&bit(q->flags,COH_WR_LOD_NIGHTLIGHT)&&!bit(q->flags,COH_WR_LOD_ADDGLOW))alpha3=q->lamp_alpha;
 if(q->draw_alpha){
  if(bit(q->flags,COH_WR_LOD_DRAW_TRICK)&&(q->flags&(COH_WR_LOD_STIPPLE1|COH_WR_LOD_STIPPLE2))){
   result.stipple_alpha=(uint32_t)round(q->draw_alpha*255);if(result.stipple_alpha==255)result.stipple_alpha=254;
   if(q->draw_alpha<0.0001){*out=result;return COH_OK;}
  }else{alpha*=q->draw_alpha;result.stipple_alpha=255;}
 }else result.stipple_alpha=255;
 result.alpha=(uint32_t)(alpha*alpha2*alpha3);*out=result;return COH_OK;
}
