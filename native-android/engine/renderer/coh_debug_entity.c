#include "coh_debug_entity.h"
#include <math.h>
#include <string.h>
#define V(x,y,z) {{x,y,z},{0,1,0},{0,0},{0,0},{1.f,.45f,.05f,1.f}}
static const CohRenderVertex vertices[]={
 V(-1,0,-1),V(1,0,-1),V(1,6,-1),V(-1,6,-1),
 V(-1,0,1),V(1,0,1),V(1,6,1),V(-1,6,1)};
#undef V
static const uint32_t indices[]={0,1,2,0,2,3,4,6,5,4,7,6,
 0,4,5,0,5,1,3,2,6,3,6,7,0,3,7,0,7,4,1,5,6,1,6,2};
static int separate(const void*a,size_t n,const void*b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return a&&b&&n<=UINTPTR_MAX-x&&m<=UINTPTR_MAX-y&&(x+n<=y||y+m<=x);}
CohStatus coh_debug_entity_draw(const CohInitialPoseSample*sample,uint32_t index,
 const float view[16],const float projection[16],CohRenderTexture white,CohRenderDraw*out){
 if(!sample||!view||!projection||!out||!sample->valid||sample->valid!=1||!index||index>COH_ENT_INDEX_MAX||!white.handle)return COH_INVALID;
 if(!separate(sample,sizeof(*sample),out,sizeof(*out))||!separate(view,16*sizeof(float),out,sizeof(*out))||!separate(projection,16*sizeof(float),out,sizeof(*out)))return COH_INVALID;
 if(!isfinite(sample->position.x)||!isfinite(sample->position.y)||!isfinite(sample->position.z))return COH_INVALID;
 for(unsigned i=0;i<16;i++)if(!isfinite(view[i])||!isfinite(projection[i]))return COH_INVALID;
 CohRenderDraw d;memset(&d,0,sizeof(d));d.geometry=(CohRenderGeometry){vertices,8,indices,36,UINT64_C(0x434f4844424f5801),0};
 d.material=coh_renderer_default_material(COH_MAT_MULTIPLY);d.material.lighting=COH_LIGHT_VERTEX;d.material.cull_back=0;d.material.fog_params[2]=1000000.f;
 for(unsigned i=0;i<3;i++)d.material.textures[i]=white;
 memcpy(d.model_view,view,sizeof(d.model_view));memcpy(d.projection,projection,sizeof(d.projection));
 for(unsigned row=0;row<4;row++){
  d.model_view[12+row]=((view[row]*sample->position.x+view[4+row]*sample->position.y)+view[8+row]*sample->position.z)+view[12+row];
  if(!isfinite(d.model_view[12+row]))return COH_INVALID;
 }
 *out=d;return COH_OK;
}
