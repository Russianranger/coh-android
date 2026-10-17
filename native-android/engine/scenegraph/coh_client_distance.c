#include "coh_client_distance.h"
#include <math.h>
#include <string.h>
static int disjoint(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;if(an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 0;return x+an<=y||y+bn<=x;}
CohStatus coh_client_distance_project(const CohClientDistanceInput*in,CohClientDistanceProjection*out){
 if(!in||!out||!disjoint(in,sizeof(*in),out,sizeof(*out)))return COH_INVALID;
 CohClientDistanceProjection result={0};result.used_parent_mid=in->lod_fadenode&&((in->client_flags_cache&1u)||in->lod_fadenode==2);
 const float*p=result.used_parent_mid?in->parent_node_mid:in->view_mid;
 for(unsigned i=0;i<3;i++)if(!isfinite(p[i]))return COH_INVALID;
 float d=p[0]*p[0]+p[1]*p[1]+p[2]*p[2];if(!isfinite(d))return COH_INVALID;
 result.squared_distance=d;result.source_return=d;result.exception_flags=in->client_flags_cache&(16u|2u|4u);
 if(!result.exception_flags){
  if(!isfinite(in->game_lod_scale)||!isfinite(in->client_vis_dist_scaled_cache)||!isfinite(in->client_vis_def_radius_cache))return COH_INVALID;
  float distance=in->game_lod_scale*in->client_vis_dist_scaled_cache+in->client_vis_def_radius_cache;
  float square=distance*distance;if(!isfinite(distance)||!isfinite(square))return COH_INVALID;
  if(d>square){result.far_rejected=1;result.source_return=0;}
 }
 result.source_return_nonzero=result.source_return!=0;*out=result;return COH_OK;
}
