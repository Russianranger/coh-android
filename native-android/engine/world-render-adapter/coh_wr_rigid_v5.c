#include "coh_wr_rigid_v5.h"
#include "coh_wr_rigid_internal.h"
#include "../scenecatalog/coh_resource_geo_source.h"
#include <math.h>
#include <string.h>
static uint32_t u32(const uint8_t*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static CohStatus source_open(CohBytes bytes,uint8_t *workspace,size_t capacity,
 uint32_t maximum,CohAssetGeo *out){
 uint32_t zero=0;CohAssetGeo g;CohStatus s=coh_resource_geo_source_open(bytes,workspace,capacity,maximum,&g,&zero);if(s!=COH_OK)return s;
 if(g.version!=5)return COH_UNSUPPORTED;
 /* Original geoLoadStubs reads five header sizes, then the three name/partition
  * blocks, then ModelLODInfoOnDisk_v5[model_count] before ModelHeader. Raw
  * trailing LOD bytes remain preserved: original unpackLODInfo checks <=size. */
 if(g.header.size<20||(g.model_count&&148u>SIZE_MAX/g.model_count))return COH_INVALID;
 size_t at=20,blocks[3]={g.texture_names.size,g.model_names.size,g.material_ids.size};for(unsigned i=0;i<3;i++){if(blocks[i]>g.header.size-at)return COH_INVALID;at+=blocks[i];}
 size_t lod=u32(g.header.data+16);if(lod>g.header.size-at||(size_t)g.model_count*148u>lod||g.records_offset<140||at+lod!=g.records_offset-140)return COH_INVALID;
 for(uint32_t row=0;row<g.model_count;row++){
  const uint8_t*p=g.header.data+at+(size_t)row*148u;uint32_t n=u32(p);if(n>6)return COH_INVALID;
  for(uint32_t j=0;j<n;j++)for(unsigned k=0;k<5;k++){uint32_t bits=u32(p+4+(size_t)j*24u+k*4u);float v;memcpy(&v,&bits,4);if(!isfinite(v))return COH_UNSUPPORTED;}
 }
 *out=g;return COH_OK;
}
CohStatus coh_wr_rigid_v5_acquire(CohAssetLoader*l,const CohWrRigidRequest*q,
 const CohWrRigidLimits*b,CohCancel cancel,CohWrRigidResource**out){
 return coh_wr_rigid_acquire_policy(l,q,b,cancel,out,source_open,coh_resource_geo_source_model,COH_WR_RIGID_EXACT_SOURCE_5);
}
