#include "coh_appearance_render.h"
#include <math.h>
#include <string.h>
#define INFLATE_BYTES 65536u
#define MAX_STREAM_BYTES (16u*1024u*1024u)
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void put32(uint8_t *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(8u*i));}
static void putf(uint8_t *p,float f){uint32_t v;memcpy(&v,&f,4);put32(p,v);}
static int span(size_t n,size_t o,size_t s){return o<=n&&s<=n-o;}
static int overlaps(const void *a,size_t an,const void *b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return an&&bn&&(x<=y?y-x<an:x-y<bn);}
static CohStatus inspect(const CohAssetGeo *g,uint32_t index,uint32_t socket,CohAssetGeoModel *m,CohAppearanceMeshRequirements *r,size_t *stream_bytes){
 if(!g||!m||!r||!stream_bytes||socket>=COH_MESH_GLOBAL_BONE_COUNT)return COH_INVALID;
 CohStatus s=coh_asset_geo_model(g,index,m);if(s)return s;
 if(m->vertex_count>COH_MESH_MAX_VERTICES||m->triangle_count>COH_MESH_MAX_INDICES/3u)return COH_LIMIT;
 uint32_t bones=1u,rigid=m->bone_info_offset==0;
 if(!rigid){
  if(!span(g->payload.size,m->bone_info_offset,72u))return COH_INVALID;
  const uint8_t *p=g->payload.data+m->bone_info_offset;bones=u32(p);
  if(!bones||bones>COH_MESH_MAX_BONES)return COH_LIMIT;
  if(u32(p+64)||u32(p+68))return COH_UNSUPPORTED;
  for(uint32_t i=0;i<bones;i++){uint32_t id=u32(p+4+i*4);if(id>=COH_MESH_GLOBAL_BONE_COUNT)return COH_INVALID;for(uint32_t j=0;j<i;j++)if(id==u32(p+4+j*4))return COH_INVALID;}
 }
 size_t maximum=0;for(unsigned i=0;i<7;i++){if(i==4)continue;if(m->packs[i].unpacked_bytes>MAX_STREAM_BYTES)return COH_LIMIT;if(m->packs[i].unpacked_bytes>maximum)maximum=m->packs[i].unpacked_bytes;}
 if(!m->packs[0].unpacked_bytes||!m->packs[1].unpacked_bytes||!m->packs[2].unpacked_bytes||!m->packs[3].unpacked_bytes)return COH_INVALID;
 if(rigid&&(m->packs[5].unpacked_bytes||m->packs[6].unpacked_bytes))return COH_INVALID;
 if(!rigid&&(m->packs[5].unpacked_bytes!=m->vertex_count||m->packs[6].unpacked_bytes!=(size_t)m->vertex_count*2u))return COH_INVALID;
 CohAppearanceMeshRequirements q={0};q.vertices=m->vertex_count;q.indices=m->triangle_count*3u;q.bones=bones;q.materials=m->material_count;q.rigid_socket_fallback=rigid;
 q.canonical_bytes=64u+(size_t)q.vertices*48u+(size_t)q.indices*4u+(size_t)q.bones*4u;
 size_t scalar_count=q.indices>(size_t)q.vertices*3u?q.indices:(size_t)q.vertices*3u;
 q.workspace_bytes=q.canonical_bytes+maximum+scalar_count*4u+INFLATE_BYTES+15u;
 *r=q;*stream_bytes=maximum;return COH_OK;
}
CohStatus coh_appearance_mesh_requirements(const CohAssetGeo *g,uint32_t index,uint32_t socket,CohAppearanceMeshRequirements *out){
 if(!out)return COH_INVALID;
 CohAssetGeoModel m;CohAppearanceMeshRequirements r;size_t bytes;
 CohStatus s=inspect(g,index,socket,&m,&r,&bytes);if(!s)*out=r;return s;
}
CohStatus coh_appearance_mesh_build(const CohAssetGeo *g,uint32_t index,uint32_t socket,void *workspace,size_t capacity,uint8_t *dst,size_t dstcap,CohMeshView *out,CohAppearanceMeshRequirements *diagnostics){
 if(!workspace||!dst||!out)return COH_INVALID;
 CohAssetGeoModel m;CohAppearanceMeshRequirements r;size_t maxstream;CohStatus s=inspect(g,index,socket,&m,&r,&maxstream);if(s)return s;
 if(capacity<r.workspace_bytes||dstcap<r.canonical_bytes)return COH_LIMIT;
 if(overlaps(workspace,capacity,dst,dstcap)||overlaps(workspace,capacity,g->header.data,g->header.size)||overlaps(workspace,capacity,g->payload.data,g->payload.size)||overlaps(dst,dstcap,g->header.data,g->header.size)||overlaps(dst,dstcap,g->payload.data,g->payload.size))return COH_INVALID;
 uint8_t *staged=workspace,*stream=staged+r.canonical_bytes;
 uintptr_t aligned=((uintptr_t)(stream+maxstream)+15u)&~(uintptr_t)15u;float *values=(float*)aligned;
 size_t scalar_count=r.indices>(size_t)r.vertices*3u?r.indices:(size_t)r.vertices*3u;
 uint8_t *inflate=(uint8_t*)values+scalar_count*4u;
 memset(staged,0,r.canonical_bytes);memcpy(staged,"COHMESH1",8);
 put32(staged+8,1);put32(staged+12,64);put32(staged+16,r.vertices);put32(staged+20,r.indices);put32(staged+24,r.bones);put32(staged+28,48);put32(staged+32,64);
 uint32_t io=64u+r.vertices*48u,bo=io+r.indices*4u;put32(staged+36,io);put32(staged+40,bo);put32(staged+44,(uint32_t)r.canonical_bytes);
 size_t bytes=0;
 for(unsigned channel=0;channel<4;channel++){
  s=coh_asset_geo_stream(g,&m,channel,stream,maxstream,inflate,INFLATE_BYTES,&bytes);if(s)return s;
  if(channel==0){s=coh_asset_delta_indices((CohBytes){stream,bytes},m.triangle_count,(uint32_t*)values,scalar_count);if(s)return s;for(uint32_t i=0;i<r.indices;i++){uint32_t v;memcpy(&v,(uint8_t*)values+i*4u,4);if(v>=r.vertices)return COH_INVALID;put32(staged+io+i*4u,v);}}
  else {uint32_t stride=channel==3?2u:3u;s=coh_asset_delta_floats((CohBytes){stream,bytes},r.vertices,stride,values,scalar_count);if(s)return s;
   for(uint32_t i=0;i<r.vertices;i++)for(uint32_t j=0;j<stride;j++){float f=values[(size_t)i*stride+j];if(channel==3&&j==1)f=1.f-f;if(!isfinite(f))return COH_INVALID;putf(staged+64u+(size_t)i*48u+(channel==1?0u:channel==2?12u:24u)+j*4u,f);}}
 }
 if(r.rigid_socket_fallback){put32(staged+bo,socket);for(uint32_t i=0;i<r.vertices;i++)putf(staged+64u+(size_t)i*48u+32u,1.f);}
 else {
  const uint8_t *ids=g->payload.data+m.bone_info_offset+4u;for(uint32_t i=0;i<r.bones;i++)put32(staged+bo+i*4u,u32(ids+i*4u));
  s=coh_asset_geo_stream(g,&m,5,stream,maxstream,inflate,INFLATE_BYTES,&bytes);if(s||bytes!=r.vertices)return s?s:COH_INVALID;
  for(uint32_t i=0;i<r.vertices;i++){float w=(float)stream[i]/255.f;putf(staged+64u+(size_t)i*48u+32u,w);putf(staged+64u+(size_t)i*48u+36u,1.f-w);}
  s=coh_asset_geo_stream(g,&m,6,stream,maxstream,inflate,INFLATE_BYTES,&bytes);if(s||bytes!=(size_t)r.vertices*2u)return s?s:COH_INVALID;
  for(uint32_t i=0;i<r.vertices;i++)for(unsigned j=0;j<2;j++){uint32_t row=stream[i*2u+j];if(row%3u||row/3u>=r.bones)return COH_INVALID;put32(staged+64u+(size_t)i*48u+40u+j*4u,row/3u);}
 }
 CohMeshView parsed;if(coh_mesh_parse(staged,r.canonical_bytes,&parsed))return COH_INVALID;
 memcpy(dst,staged,r.canonical_bytes);parsed.bytes=dst;*out=parsed;if(diagnostics)*diagnostics=r;return COH_OK;
}
