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

CohStatus coh_wr_lod_autodata(const CohWrAutoLodInput *q,CohWrAutoLodProjection *out){
 if(!q||!out)return COH_INVALID;
 uintptr_t a=(uintptr_t)q,b=(uintptr_t)out;
 if(a>UINTPTR_MAX-sizeof(*q)||b>UINTPTR_MAX-sizeof(*out)||
    (a<b+sizeof(*out)&&b<a+sizeof(*q)))return COH_INVALID;
 if(q->has_reduction_distances>1||q->source_triangle_count>2147483647u)return COH_INVALID;
 if(!isfinite(q->model_radius)||q->model_radius<0||
    !isfinite(q->shadow_distance)||q->shadow_distance<0)return COH_INVALID;
 for(unsigned i=0;i<4;i++)if(!isfinite(q->trick_lod[i])||q->trick_lod[i]<0)return COH_INVALID;
 for(unsigned i=0;i<3;i++)if(!isfinite(q->reduction_distances[i]))return COH_INVALID;
 float near=q->trick_lod[0],nearfade=q->trick_lod[1];
 float far=q->trick_lod[2],farfade=q->trick_lod[3];
 int lod_fromtrick=near||far||nearfade||farfade;
 if(!far)far=10.f*(q->model_radius*0.5f+q->shadow_distance+10.f);
 if(!farfade&&!lod_fromtrick)farfade=far*0.25f;
 if(!isfinite(far)||!isfinite(farfade))return COH_LIMIT;
 CohWrAutoLodProjection result={0};
 result.count=1;
 result.rows[0]=(CohWrAutoLodRow){0,near,nearfade,far,farfade,COH_WR_AUTOLOD_ERROR_TRICOUNT};
 int triangle_count=(int)q->source_triangle_count;
 float error=0.75f;
 for(unsigned d=0;q->has_reduction_distances&&error>0&&triangle_count>200;d++){
  /* Original while condition admits at most the three source distances because
   * the exact quarter decrement reaches zero. No source read is reordered. */
  if(d>=3)return COH_STATE;
  float distance=q->reduction_distances[d];
  CohWrAutoLodRow *previous=&result.rows[result.count-1];
  triangle_count=(int)(error*(int)q->source_triangle_count);
  if(distance>previous->lod_far-125||distance<0)break;
  if(distance>previous->lod_near+125&&(error<=0.5f||triangle_count<=2000)){
   if(result.count>=4)return COH_STATE;
   CohWrAutoLodRow *row=&result.rows[result.count++];
   row->flags=COH_WR_AUTOLOD_ERROR_TRICOUNT|COH_WR_AUTOLOD_FALLBACK_MATERIAL;
   row->max_error=100*(1-error);
   row->lod_far=previous->lod_far;row->lod_farfade=previous->lod_farfade;
   previous->lod_far=row->lod_near=distance;
   if(q->model_radius>200){previous->lod_farfade=25;row->lod_nearfade=25;}
   else if(d==0){previous->lod_farfade=5;row->lod_nearfade=5;}
   else{previous->lod_farfade=0;row->lod_nearfade=0;}
  }
  error-=0.25f;
 }
 *out=result;return COH_OK;
}
