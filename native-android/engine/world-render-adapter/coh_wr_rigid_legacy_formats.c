#include "coh_wr_rigid_legacy_formats.h"
#include "coh_wr_rigid_internal.h"
#include "../scenecatalog/coh_resource_geo_source.h"
#include <math.h>
#include <string.h>
static uint32_t u32(const uint8_t*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static CohStatus legacy_open(CohBytes bytes,uint8_t*workspace,size_t capacity,uint32_t maximum,CohAssetGeo*out,uint32_t version){
 uint32_t zero=0;CohAssetGeo g;CohStatus s=coh_resource_geo_source_open(bytes,workspace,capacity,maximum,&g,&zero);if(s!=COH_OK)return s;if(g.version!=version)return COH_UNSUPPORTED;
 /* The original <=5 branch reads ModelLODInfoOnDisk_v5 rows regardless of
  * model-record family. Preserve raw trailing/unused cells; validate only
  * bounded active inputs. No effective CLIENT LOD selection is performed. */
 if(g.header.size<20||(g.model_count&&148u>SIZE_MAX/g.model_count))return COH_INVALID;
 size_t at=20,blocks[3]={g.texture_names.size,g.model_names.size,g.material_ids.size};for(unsigned i=0;i<3;i++){if(blocks[i]>g.header.size-at)return COH_INVALID;at+=blocks[i];}
 size_t lod=u32(g.header.data+16);if(lod>g.header.size-at||(size_t)g.model_count*148u>lod||g.records_offset<140||at+lod!=g.records_offset-140)return COH_INVALID;
 for(uint32_t row=0;row<g.model_count;row++){const uint8_t*p=g.header.data+at+(size_t)row*148u;uint32_t count=u32(p);if(count>6)return COH_INVALID;for(uint32_t j=0;j<count;j++)for(unsigned k=0;k<5;k++){uint32_t bits=u32(p+4+(size_t)j*24u+k*4u);float value;memcpy(&value,&bits,4);if(!isfinite(value))return COH_UNSUPPORTED;}}
 *out=g;return COH_OK;
}
#define ENTRY(version) \
static CohStatus open_v##version(CohBytes bytes,uint8_t*w,size_t n,uint32_t max,CohAssetGeo*out){return legacy_open(bytes,w,n,max,out,version);} \
CohStatus coh_wr_rigid_v##version##_acquire(CohAssetLoader*l,const CohWrRigidRequest*q,const CohWrRigidLimits*b,CohCancel c,CohWrRigidResource**out){return coh_wr_rigid_acquire_policy(l,q,b,c,out,open_v##version,coh_resource_geo_source_model,COH_WR_RIGID_EXACT_SOURCE_##version);}
ENTRY(2)
ENTRY(3)
ENTRY(4)
#undef ENTRY
