#include "coh_source_special.h"
#include <math.h>
#include <stdint.h>
#include <string.h>
static uint32_t u32(const uint8_t*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float f32(const uint8_t*p){uint32_t u=u32(p);float f;memcpy(&f,&u,4);return f;}
static int disjoint(const void*a,size_t n,const void*b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return (!n||a)&&(!m||b)&&n<=UINTPTR_MAX-x&&m<=UINTPTR_MAX-y&&(x+n<=y||y+m<=x);}
static CohStatus poll(CohCancel c){return c.poll&&c.poll(c.context)?COH_CANCELLED:COH_OK;}
static int add(size_t*n,size_t v,size_t cap){if(*n>cap||v>cap-*n)return 0;*n+=v;return 1;}
CohStatus coh_source_special_prepare(const CohSourceBody*body,uint32_t ordinal,void*workspace,size_t capacity,const CohSourceSpecialBudget*b,CohCancel cancel,CohSourceSpecial*out){
 if(!body||!workspace||!b||!out||((uintptr_t)workspace%sizeof(float)))return COH_INVALID;
 if(capacity>(1u<<20))return COH_LIMIT;
 if(!disjoint(workspace,capacity,b,sizeof(*b))||!disjoint(workspace,capacity,out,sizeof(*out))||!disjoint(b,sizeof(*b),out,sizeof(*out)))return COH_INVALID;
 CohSourceSpecial v;memset(&v,0,sizeof(v));CohStatus s=coh_source_body_lease(body,ordinal,&v.source);if(s!=COH_OK)return s;
 CohBytes spans[]={v.source.actual_sources.record,v.source.actual_sources.header,v.source.actual_sources.blob};
 for(unsigned k=0;k<3;k++)if(!disjoint(spans[k].data,spans[k].size,workspace,capacity)||!disjoint(spans[k].data,spans[k].size,b,sizeof(*b))||!disjoint(spans[k].data,spans[k].size,out,sizeof(*out)))return COH_INVALID;
 size_t reserved=0;if(!add(&reserved,COH_SOURCE_SPECIAL_PREPARATION_RESERVE,b->aggregate_limit)||!add(&reserved,v.source.retained_owner_bytes,b->aggregate_limit)||!add(&reserved,v.source.loader_reservation,b->aggregate_limit)||!add(&reserved,capacity,b->aggregate_limit)||!add(&reserved,b->retained_bytes,b->aggregate_limit))return COH_LIMIT;
 if((s=poll(cancel))!=COH_OK)return s;
 const CohAssetGeoModel*m=&v.source.model.model;CohBytes header=v.source.actual_sources.header,blob=v.source.actual_sources.blob;uint32_t version=v.source.model.geo_version;
 if(version!=0&&version!=8)return COH_UNSUPPORTED;
 /* Source index already validated complete records. Re-find exact raw disk row,
  * bounded by the admitted row and header extent; never sorted runtime row. */
 if(header.size<16||blob.size<4)return COH_INVALID;
 size_t at=16u;
 if(!add(&at,u32(header.data+4),header.size)||!add(&at,u32(header.data+8),header.size)||!add(&at,u32(header.data+12),header.size)||!add(&at,140,header.size))return COH_INVALID;
 for(uint32_t k=0;k<v.source.model.geo_disk_row;k++){
  if((s=poll(cancel))!=COH_OK)return s;
  if(at>header.size||header.size-at<(version?4u:216u))return COH_INVALID;
  size_t n=version?u32(header.data+at):216u;if(n<4||!add(&at,n,header.size))return COH_INVALID;
 }
 if(at>header.size||header.size-at<(version?4u:216u))return COH_INVALID;
 uint32_t pivot=0;
 if(version){CohGeoModel metadata;if(coh_geo_model(header.data+at,header.size-at,version,&metadata))return COH_INVALID;v.reflection_quads=metadata.reflection_count;pivot=metadata.alternate_pivot_offset;}
 else pivot=u32(header.data+at+84);
 size_t payload_offset=(size_t)u32(blob.data);if(!add(&payload_offset,version?4u:8u,blob.size))return COH_INVALID;
 CohBytes payload={blob.data+payload_offset,blob.size-payload_offset};
 if(!v.reflection_quads&&m->packs[9].unpacked_bytes)return COH_INVALID;
 if(v.reflection_quads){
  if(v.reflection_quads>COH_SOURCE_SPECIAL_MAX_QUADS)return COH_LIMIT;
  if(m->pack_count<10||!m->packs[9].unpacked_bytes)return COH_INVALID;
  size_t bytes=m->packs[9].unpacked_bytes;if(bytes>COH_SOURCE_SPECIAL_MAX_STREAM)return COH_LIMIT;
  size_t aligned=(bytes+3u)&~(size_t)3u,scalars=(size_t)v.reflection_quads*12u;
  if(aligned>capacity||65536u>capacity-aligned||scalars*sizeof(float)>capacity-aligned-65536u)return COH_LIMIT;
  CohAssetGeo g;memset(&g,0,sizeof(g));g.payload=payload;
  uint8_t*w=workspace;size_t decoded=0;s=coh_asset_geo_stream(&g,m,9,w,bytes,w+aligned,65536,&decoded);if(s!=COH_OK)return s;
  float*points=(float*)(w+aligned+65536);s=coh_asset_delta_floats((CohBytes){w,decoded},v.reflection_quads*4,3,points,scalars);if(s!=COH_OK)return s;
  for(size_t n=0;n<scalars;n++)if(!isfinite(points[n]))return COH_INVALID;
  v.kinds|=COH_SOURCE_SPECIAL_REFLECTION;v.reflection_delta=(CohBytes){w,decoded};v.reflection_vertices=points;
 }
 if(pivot){
  if(pivot>payload.size||724u>payload.size-pivot)return COH_INVALID;
  const uint8_t*p=payload.data+pivot;uint32_t count=u32(p);if(count>15)return COH_INVALID;
  v.alternate_pivots=count;v.alternate_pivot_wire=(CohBytes){p,724};
  for(uint32_t k=0;k<count;k++)for(unsigned n=0;n<12;n++){float f=f32(p+4+(size_t)k*48+n*4);if(!isfinite(f))return COH_INVALID;v.alternate_pivot[k][n]=f;}
  v.kinds|=COH_SOURCE_SPECIAL_ALT_PIVOT;
 }
 if(!m->packs[3].unpacked_bytes)v.kinds|=COH_SOURCE_SPECIAL_MISSING_UV;
 v.observed_cast_shadow=!!(v.source.model.trick_flags[1]&(1u<<22));
 if(!v.kinds)return COH_NOT_FOUND;
 if((s=poll(cancel))!=COH_OK)return s;
 v.workspace_bytes=capacity;v.aggregate_reserved_bytes=reserved;*out=v;return COH_OK;
}
