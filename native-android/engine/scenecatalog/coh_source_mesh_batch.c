#include "coh_source_mesh_batch.h"
#include <stdlib.h>
#include <string.h>
#define PREPARATION (16u*1024u)
typedef struct {CohSourceMesh*mesh;CohSourceMeshReport report;uint32_t first_part;}Entry;
struct CohSourceMeshBatch {CohSourceMeshBatchReport report;Entry entries[];};
static int separate(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return (!an||a)&&(!bn||b)&&an<=UINTPTR_MAX-x&&bn<=UINTPTR_MAX-y&&(x+an<=y||y+bn<=x);}
static CohStatus add(size_t*n,size_t x,size_t cap){if(*n>cap||x>cap-*n)return COH_LIMIT;*n+=x;return COH_OK;}
static CohStatus tick(CohCancel c){return c.poll&&c.poll(c.context)?COH_CANCELLED:COH_OK;}
#define TRY(x) do{CohStatus s_=(x);if(s_!=COH_OK)return s_;}while(0)
static CohStatus known(const CohSourceMesh*m,const void*out,size_t size){
 CohSourceMeshDependencies d;CohSourceMeshReport r;TRY(coh_source_mesh_dependencies(m,&d));TRY(coh_source_mesh_report(m,&r));
 CohBytes spans[]={d.mesh_storage,d.body.join.catalog_bytes,d.body.join.snapshot_bytes,d.body.join.resource_bytes,r.source.actual_sources.record,r.source.actual_sources.header,r.source.actual_sources.blob};
 for(unsigned n=0;n<7;n++)if(!separate(out,size,spans[n].data,spans[n].size))return COH_INVALID;
 return COH_OK;
}
static CohStatus safe(const CohSourceMeshBatch*b,const void*out,size_t n){if(!b||!out||!separate(b,b->report.owned_bytes,out,n))return COH_INVALID;for(uint32_t k=0;k<b->report.meshes;k++)TRY(known(b->entries[k].mesh,out,n));return COH_OK;}
void coh_source_mesh_batch_free(CohSourceMeshBatch*b){if(!b)return;for(uint32_t n=0;n<b->report.meshes;n++)coh_source_mesh_free(b->entries[n].mesh);free(b);}
CohStatus coh_source_mesh_batch_report(const CohSourceMeshBatch*b,CohSourceMeshBatchReport*out){TRY(safe(b,out,sizeof(*out)));*out=b->report;return COH_OK;}
CohStatus coh_source_mesh_batch_find(const CohSourceMeshBatch*b,uint32_t ordinal,uint32_t*out){TRY(safe(b,out,sizeof(*out)));uint32_t lo=0,hi=b->report.meshes;while(lo<hi){uint32_t at=lo+(hi-lo)/2,v=b->entries[at].report.source.source_ordinal;if(v==ordinal){*out=at;return COH_OK;}if(v<ordinal)lo=at+1;else hi=at;}return COH_NOT_FOUND;}
CohStatus coh_source_mesh_batch_entry(const CohSourceMeshBatch*b,uint32_t slot,CohSourceMeshReport*out,uint32_t*first){TRY(safe(b,out,sizeof(*out)));TRY(safe(b,first,sizeof(*first)));if(!separate(out,sizeof(*out),first,sizeof(*first)))return COH_INVALID;if(slot>=b->report.meshes)return COH_NOT_FOUND;*out=b->entries[slot].report;*first=b->entries[slot].first_part;return COH_OK;}
CohStatus coh_source_mesh_batch_part(const CohSourceMeshBatch*b,uint32_t slot,uint32_t part,CohSourceMeshPart*out){TRY(safe(b,out,sizeof(*out)));if(slot>=b->report.meshes)return COH_NOT_FOUND;return coh_source_mesh_part(b->entries[slot].mesh,part,out);}
CohStatus coh_source_mesh_batch_create(CohSourceMesh**meshes,uint32_t count,const CohSourceMeshBatchBudget*b,CohCancel cancel,CohSourceMeshBatch**out,CohSourceMeshBatchReport*report){
 if(!meshes||!b||!out||!report)return COH_INVALID;
 if(!count||count>COH_SOURCE_MESH_BATCH_MAX)return COH_LIMIT;
 const void*p[]={meshes,b,out,report};size_t sizes[]={(size_t)count*sizeof(*meshes),sizeof(*b),sizeof(*out),sizeof(*report)};
 for(unsigned i=0;i<4;i++)for(unsigned j=i+1;j<4;j++)if(!separate(p[i],sizes[i],p[j],sizes[j]))return COH_INVALID;
 if(!b->aggregate_limit||b->aggregate_limit>COH_SG_TRANSACTION_MAX)return COH_LIMIT;
 if(*out)return COH_STATE;
 CohSourceMeshBatchReport r={0};r.meshes=count;r.owned_bytes=sizeof(CohSourceMeshBatch)+(size_t)count*sizeof(Entry);r.preparation_reserve=PREPARATION;
 size_t minimum=b->retained_bytes;TRY(add(&minimum,r.owned_bytes,b->aggregate_limit));TRY(add(&minimum,PREPARATION,b->aggregate_limit));
 CohSourceMeshDependencies base={0};uint32_t previous=0;
 for(uint32_t i=0;i<count;i++){
  if(!meshes[i])return COH_INVALID;
  for(unsigned k=0;k<4;k++)TRY(known(meshes[i],p[k],sizes[k]));
  CohSourceMeshDependencies d;CohSourceMeshReport m;TRY(coh_source_mesh_dependencies(meshes[i],&d));TRY(coh_source_mesh_report(meshes[i],&m));
  if(i&&m.source.source_ordinal<=previous)return COH_STATE;
  previous=m.source.source_ordinal;
  if(!i){base=d;TRY(add(&r.source_owner_bytes,d.body.selection_owned_bytes,b->aggregate_limit));TRY(add(&r.source_owner_bytes,d.body.profile_bytes,b->aggregate_limit));TRY(add(&r.source_owner_bytes,d.body.join.report.owned_bytes,b->aggregate_limit));TRY(add(&r.source_owner_bytes,d.body.join.catalog_owned_bytes,b->aggregate_limit));TRY(add(&r.source_owner_bytes,d.body.join.snapshot_owned_bytes,b->aggregate_limit));TRY(add(&r.source_owner_bytes,d.body.join.graph_owned_bytes,b->aggregate_limit));}
  else if(d.body.selection_identity!=base.body.selection_identity||d.body.join_identity!=base.body.join_identity||d.body.profile_identity!=base.body.profile_identity||d.body.join.catalog_identity!=base.body.join.catalog_identity||d.body.join.snapshot_identity!=base.body.join.snapshot_identity||d.body.join.graph_identity!=base.body.join.graph_identity)return COH_STATE;
  if(m.render_ready||m.client_materials_available||m.world_authority)return COH_STATE;
  if(m.parts>COH_SOURCE_MESH_BATCH_PARTS_MAX-r.parts)return COH_LIMIT;
  r.parts+=m.parts;TRY(add(&r.mesh_owned_bytes,m.owned_bytes,b->aggregate_limit));TRY(add(&r.source_owner_bytes,d.body.body_owned_bytes,b->aggregate_limit));
  size_t prior_reservation=0;
  for(uint32_t j=0;j<i;j++){CohSourceMeshDependencies prior;TRY(coh_source_mesh_dependencies(meshes[j],&prior));if(meshes[i]==meshes[j]||d.body.body_identity==prior.body.body_identity||d.body.index_identity==prior.body.index_identity)return COH_STATE;if(d.body.loader==prior.body.loader&&prior.body.loader_reservation>prior_reservation)prior_reservation=prior.body.loader_reservation;}
  if(coh_asset_stats(d.body.loader).peak_allocated_bytes>d.body.loader_reservation)return COH_LIMIT;
  if(d.body.loader_reservation>prior_reservation)TRY(add(&r.loader_reservations,d.body.loader_reservation-prior_reservation,b->aggregate_limit));
 }
 size_t peak=b->retained_bytes;TRY(add(&peak,r.owned_bytes,b->aggregate_limit));TRY(add(&peak,r.mesh_owned_bytes,b->aggregate_limit));TRY(add(&peak,r.source_owner_bytes,b->aggregate_limit));TRY(add(&peak,r.loader_reservations,b->aggregate_limit));TRY(add(&peak,PREPARATION,b->aggregate_limit));r.aggregate_reserved_bytes=peak;
 TRY(tick(cancel));CohSourceMeshBatch*candidate=calloc(1,r.owned_bytes);if(!candidate)return COH_LIMIT;
 uint32_t first=0;for(uint32_t i=0;i<count;i++){CohStatus s=tick(cancel);if(s==COH_OK)s=coh_source_mesh_report(meshes[i],&candidate->entries[i].report);if(s!=COH_OK){free(candidate);return s;}candidate->entries[i].mesh=meshes[i];candidate->entries[i].first_part=first;first+=candidate->entries[i].report.parts;}
 CohStatus final=tick(cancel);if(final!=COH_OK){free(candidate);return final;}candidate->report=r;for(uint32_t i=0;i<count;i++)meshes[i]=NULL;*report=r;*out=candidate;return COH_OK;
}
