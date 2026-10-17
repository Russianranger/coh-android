#include "coh_source_mesh.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#define PREPARATION (16u*1024u)
#define STREAM_MAX (2u*1024u*1024u)
struct CohSourceMesh {CohSourceBody*body;CohSourceMeshReport report;CohRenderVertex*vertices;uint32_t*indices;CohAssetGeoMaterial*parts;};
static uint32_t u32(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int separate(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return (!an||a)&&(!bn||b)&&an<=UINTPTR_MAX-x&&bn<=UINTPTR_MAX-y&&(x+an<=y||y+bn<=x);}
static int add(size_t*n,size_t v,size_t cap){if(*n>cap||v>cap-*n)return 0;*n+=v;return 1;}
static CohStatus tick(CohCancel c){return c.poll&&c.poll(c.context)?COH_CANCELLED:COH_OK;}
static int safe(const CohSourceMesh*m,const void*p,size_t n){if(!separate(m,m->report.owned_bytes,p,n))return 0;CohBytes spans[]={m->report.source.actual_sources.record,m->report.source.actual_sources.header,m->report.source.actual_sources.blob};for(unsigned k=0;k<3;k++)if(!separate(spans[k].data,spans[k].size,p,n))return 0;return 1;}
void coh_source_mesh_free(CohSourceMesh*m){if(!m)return;CohSourceBody*b=m->body;free(m);coh_source_body_free(b);}
CohStatus coh_source_mesh_report(const CohSourceMesh*m,CohSourceMeshReport*out){if(!m||!out||!safe(m,out,sizeof(*out)))return COH_INVALID;*out=m->report;return COH_OK;}
CohStatus coh_source_mesh_part(const CohSourceMesh*m,uint32_t n,CohSourceMeshPart*out){if(!m||!out||!safe(m,out,sizeof(*out)))return COH_INVALID;if(n>=m->report.parts)return COH_NOT_FOUND;CohAssetGeoMaterial p=m->parts[n];*out=(CohSourceMeshPart){m->vertices,m->report.vertices,m->indices+(size_t)p.first_triangle*3,p.triangle_count*3,p};return COH_OK;}
CohStatus coh_source_mesh_v8_create(CohSourceBody**body,const CohSourceMeshRequest*q,const CohSourceMeshBudget*b,CohCancel cancel,CohSourceMesh**out,CohSourceMeshReport*report){
 if(!body||!*body||!q||!q->digest||!b||!out||!report)return COH_INVALID;
 const void*p[]={body,q,b,out,report};size_t pn[]={sizeof(*body),sizeof(*q),sizeof(*b),sizeof(*out),sizeof(*report)};
 for(unsigned i=0;i<5;i++)for(unsigned j=i+1;j<5;j++)if(!separate(p[i],pn[i],p[j],pn[j]))return COH_INVALID;
 CohSourceBodyLease lease;CohStatus s=coh_source_body_lease(*body,q->source_ordinal,&lease);if(s!=COH_OK)return s;
 CohBytes spans[]={lease.actual_sources.record,lease.actual_sources.header,lease.actual_sources.blob};for(unsigned k=0;k<3;k++)for(unsigned i=0;i<5;i++)if(!separate(p[i],pn[i],spans[k].data,spans[k].size))return COH_INVALID;
 if(*out)return COH_STATE;
 if(!b->aggregate_limit||b->aggregate_limit>COH_SG_TRANSACTION_MAX||!b->max_stream_bytes||b->max_stream_bytes>STREAM_MAX)return COH_LIMIT;
 if(lease.model.geo_version!=8||lease.model.zero_draw_model)return COH_UNSUPPORTED;
 size_t base=PREPARATION;if(!add(&base,lease.retained_owner_bytes,b->aggregate_limit)||!add(&base,lease.loader_reservation,b->aggregate_limit)||!add(&base,b->retained_bytes,b->aggregate_limit))return COH_LIMIT;
 if((s=tick(cancel))!=COH_OK)return s;
 const CohAssetGeoModel*m=&lease.model.model;uint32_t verts=m->vertex_count,tris=m->triangle_count,parts=m->material_count;
 if(!verts||!tris||!parts)return COH_INVALID;
 if(verts>65536||tris>65536||parts>512)return COH_LIMIT;
 if(m->bone_info_offset||m->scale[0]!=1.f||m->scale[1]!=1.f||m->scale[2]!=1.f||m->packs[4].unpacked_bytes||m->packs[5].unpacked_bytes||m->packs[6].unpacked_bytes||m->packs[9].unpacked_bytes)return COH_UNSUPPORTED;
 size_t at=16;CohBytes header=lease.actual_sources.header,blob=lease.actual_sources.blob;if(header.size<16||blob.size<16)return COH_INVALID;
 for(unsigned k=0;k<3;k++)if(!add(&at,u32(header.data+4+k*4),header.size))return COH_INVALID;
 if(!add(&at,140,header.size))return COH_INVALID;
 for(uint32_t n=0;n<lease.model.geo_disk_row;n++){if((s=tick(cancel))!=COH_OK)return s;if(at>header.size||header.size-at<4)return COH_INVALID;uint32_t bytes=u32(header.data+at);if(bytes<4||!add(&at,bytes,header.size))return COH_INVALID;}
 CohGeoModel metadata;if(at>header.size||coh_geo_model(header.data+at,header.size-at,8,&metadata))return COH_INVALID;
 if(metadata.vertex_count!=verts||metadata.triangle_count!=tris||metadata.texture_count!=parts||metadata.bone_info_offset!=m->bone_info_offset||metadata.pack_count!=m->pack_count)return COH_STATE;
 if(metadata.reflection_count||metadata.alternate_pivot_offset)return COH_UNSUPPORTED;
 size_t payload=(size_t)u32(blob.data);if(!add(&payload,4,blob.size))return COH_INVALID;
 CohAssetGeo geo;memset(&geo,0,sizeof(geo));geo.payload=(CohBytes){blob.data+payload,blob.size-payload};
 size_t encoded_size=0;for(unsigned k=0;k<4;k++){if(!m->packs[k].unpacked_bytes)return COH_UNSUPPORTED;if(m->packs[k].unpacked_bytes>encoded_size)encoded_size=m->packs[k].unpacked_bytes;}
 if(encoded_size>b->max_stream_bytes)return COH_LIMIT;
 size_t own=sizeof(CohSourceMesh),temporary=0;
 if(!add(&own,(size_t)parts*sizeof(CohAssetGeoMaterial),COH_RESOURCE_INPUT_MAX)||!add(&own,(size_t)verts*sizeof(CohRenderVertex),COH_RESOURCE_INPUT_MAX)||!add(&own,(size_t)tris*3*sizeof(uint32_t),COH_RESOURCE_INPUT_MAX)||!add(&temporary,encoded_size,b->aggregate_limit)||!add(&temporary,65536,b->aggregate_limit)||!add(&temporary,(size_t)verts*3*sizeof(float),b->aggregate_limit))return COH_LIMIT;
 size_t peak=base;if(!add(&peak,own,b->aggregate_limit)||!add(&peak,temporary,b->aggregate_limit))return COH_LIMIT;
 if(coh_asset_stats(lease.loader).peak_allocated_bytes>lease.loader_reservation)return COH_LIMIT;
 uint8_t hash[32];s=q->digest(q->digest_context,blob,hash);if(s!=COH_OK)return s;if(memcmp(hash,lease.geo.sha256,32))return COH_STATE;
 if((s=tick(cancel))!=COH_OK)return s;
 CohSourceMesh*candidate=calloc(1,own);if(!candidate)return COH_LIMIT;
 uint8_t*encoded=malloc(encoded_size+65536);float*values=malloc((size_t)verts*3*sizeof(float));
 if(!encoded||!values){s=COH_LIMIT;goto fail;}
 candidate->parts=(CohAssetGeoMaterial*)(candidate+1);candidate->vertices=(CohRenderVertex*)(candidate->parts+parts);candidate->indices=(uint32_t*)(candidate->vertices+verts);
 /* Material source descriptors already admitted by the immutable file index. */
 const CohResourceIndex*index;CohSourceBodyReport ignored;s=coh_source_body_view(*body,&index,&ignored);if(s!=COH_OK)goto fail;
 uint32_t first=0;for(uint32_t n=0;n<parts;n++){s=coh_resource_index_material(index,lease.model.owner_kind,lease.model.file,lease.model.slot,n,candidate->parts+n);if(s!=COH_OK)goto fail;CohAssetGeoMaterial part=candidate->parts[n];if(part.first_triangle!=first||!part.triangle_count||part.triangle_count>tris-first){s=COH_INVALID;goto fail;}first+=part.triangle_count;}if(first!=tris){s=COH_INVALID;goto fail;}
 for(unsigned pack=0;pack<4;pack++){
  if((s=tick(cancel))!=COH_OK)goto fail;
  size_t count=0;s=coh_asset_geo_stream(&geo,m,pack,encoded,encoded_size,encoded+encoded_size,65536,&count);if(s!=COH_OK)goto fail;
  if(!pack){s=coh_asset_delta_indices((CohBytes){encoded,count},tris,candidate->indices,(size_t)tris*3);if(s!=COH_OK)goto fail;for(size_t n=0;n<(size_t)tris*3;n++)if(candidate->indices[n]>=verts){s=COH_INVALID;goto fail;}}
  else{
   s=coh_asset_delta_floats((CohBytes){encoded,count},verts,pack==3?2:3,values,(size_t)verts*3);if(s!=COH_OK)goto fail;
   for(uint32_t n=0;n<verts;n++){CohRenderVertex*v=candidate->vertices+n;if(pack==1)memcpy(v->position,values+(size_t)n*3,12);else if(pack==2)memcpy(v->normal,values+(size_t)n*3,12);else{float flip=1.f-values[(size_t)n*2+1];if(!isfinite(flip)){s=COH_INVALID;goto fail;}v->uv0[0]=v->uv1[0]=values[(size_t)n*2];v->uv0[1]=v->uv1[1]=flip;for(unsigned c=0;c<4;c++)v->color[c]=1;}}
  }
 }
 if((s=tick(cancel))!=COH_OK)goto fail;
 candidate->report=(CohSourceMeshReport){lease,verts,tris,parts,1,1,own,temporary,PREPARATION,peak,0,0,0};candidate->body=*body;*body=NULL;*report=candidate->report;*out=candidate;free(values);free(encoded);return COH_OK;
 fail:free(values);free(encoded);coh_source_mesh_free(candidate);return s;
}
