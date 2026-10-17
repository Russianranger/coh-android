#include "coh_source_sealed.h"
#include <stdlib.h>
#include <string.h>
#define PREPARATION (16u*1024u)
typedef struct {CohSourceSealedEntry view;CohRenderVertex*vertices;uint32_t*indices;CohAssetGeoMaterial*parts;}Entry;
struct CohSourceSealed {CohSourceSealedReport report;CohSourceSelection*selection;CohSourceSealedIdentity identity;Entry entries[];};
static int separate(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return (!an||a)&&(!bn||b)&&an<=UINTPTR_MAX-x&&bn<=UINTPTR_MAX-y&&(x+an<=y||y+bn<=x);}
static CohStatus add(size_t*n,size_t x,size_t cap){if(*n>cap||x>cap-*n)return COH_LIMIT;*n+=x;return COH_OK;}
static CohStatus region(size_t*n,size_t x,size_t cap,size_t*offset){size_t padding=(8-*n%8)%8;CohStatus s=add(n,padding,cap);if(s!=COH_OK)return s;*offset=*n;return add(n,x,cap);}
static CohStatus tick(CohCancel c){return c.poll&&c.poll(c.context)?COH_CANCELLED:COH_OK;}
#define TRY(x) do{CohStatus s_=(x);if(s_!=COH_OK)return s_;}while(0)
static CohStatus name_offset(const char*s,CohBytes bytes,size_t*offset){uintptr_t start=(uintptr_t)bytes.data,p=(uintptr_t)s;if(!s||!bytes.data||bytes.size>UINTPTR_MAX-start||p<start||p-start>=bytes.size)return COH_STATE;size_t n=(size_t)(p-start),limit=bytes.size-n;if(limit>COH_ASSET_PATH_MAX)limit=COH_ASSET_PATH_MAX;if(!memchr(bytes.data+n,0,limit))return COH_STATE;*offset=n;return COH_OK;}
static CohStatus path_size(const char*s,size_t*out){if(!s)return COH_STATE;for(size_t n=0;n<COH_ASSET_PATH_MAX;n++)if(!s[n]){*out=n+1;return COH_OK;}return COH_LIMIT;}
static CohStatus source_control(const CohSourceMeshBatch*b,uint32_t slot,const void*p,size_t n){CohSourceMeshDependencies d;CohSourceMeshReport m;uint32_t first;TRY(coh_source_mesh_batch_dependencies(b,slot,&d));TRY(coh_source_mesh_batch_entry(b,slot,&m,&first));CohBytes spans[]={d.mesh_storage,d.body.join.catalog_bytes,d.body.join.snapshot_bytes,d.body.join.resource_bytes,m.source.actual_sources.record,m.source.actual_sources.header,m.source.actual_sources.blob};for(unsigned k=0;k<7;k++)if(!separate(p,n,spans[k].data,spans[k].size))return COH_INVALID;return COH_OK;}
static CohStatus safe(const CohSourceSealed*s,const void*p,size_t n){if(!s||!p||!separate(s,s->report.owned_bytes,p,n))return COH_INVALID;CohBytes spans[]={s->identity.join.catalog_bytes,s->identity.join.snapshot_bytes,s->identity.join.resource_bytes};for(unsigned k=0;k<3;k++)if(!separate(p,n,spans[k].data,spans[k].size))return COH_INVALID;return COH_OK;}
void coh_source_sealed_free(CohSourceSealed*s){if(!s)return;CohSourceSelection*selection=s->selection;free(s);coh_source_selection_free(selection);}
CohStatus coh_source_sealed_report(const CohSourceSealed*s,CohSourceSealedReport*out){TRY(safe(s,out,sizeof(*out)));*out=s->report;return COH_OK;}
CohStatus coh_source_sealed_identity(const CohSourceSealed*s,CohSourceSealedIdentity*out){TRY(safe(s,out,sizeof(*out)));*out=s->identity;return COH_OK;}
CohStatus coh_source_sealed_entry(const CohSourceSealed*s,uint32_t slot,CohSourceSealedEntry*out){TRY(safe(s,out,sizeof(*out)));if(slot>=s->report.meshes)return COH_NOT_FOUND;*out=s->entries[slot].view;return COH_OK;}
CohStatus coh_source_sealed_find(const CohSourceSealed*s,uint32_t ordinal,uint32_t*out){TRY(safe(s,out,sizeof(*out)));uint32_t lo=0,hi=s->report.meshes;while(lo<hi){uint32_t at=lo+(hi-lo)/2,n=s->entries[at].view.source_ordinal;if(n==ordinal){*out=at;return COH_OK;}if(n<ordinal)lo=at+1;else hi=at;}return COH_NOT_FOUND;}
CohStatus coh_source_sealed_part(const CohSourceSealed*s,uint32_t slot,uint32_t part,CohSourceMeshPart*out){TRY(safe(s,out,sizeof(*out)));if(slot>=s->report.meshes||part>=s->entries[slot].view.parts)return COH_NOT_FOUND;const Entry*e=s->entries+slot;CohAssetGeoMaterial m=e->parts[part];*out=(CohSourceMeshPart){e->vertices,e->view.vertices,e->indices+(size_t)m.first_triangle*3,m.triangle_count*3,m};return COH_OK;}
CohStatus coh_source_sealed_create(CohSourceMeshBatch**batch,const CohSourceSealedBudget*b,CohCancel cancel,CohSourceSealed**out,CohSourceSealedReport*report){
 if(!batch||!*batch||!b||!out||!report)return COH_INVALID;
 const void*p[]={batch,b,out,report};size_t sizes[]={sizeof(*batch),sizeof(*b),sizeof(*out),sizeof(*report)};for(unsigned i=0;i<4;i++)for(unsigned j=i+1;j<4;j++)if(!separate(p[i],sizes[i],p[j],sizes[j]))return COH_INVALID;
 if(!b->owned_limit||b->owned_limit>COH_RESOURCE_INPUT_MAX||!b->aggregate_limit||b->aggregate_limit>COH_SG_TRANSACTION_MAX)return COH_LIMIT;
 if(*out)return COH_STATE;
 size_t minimum=b->retained_bytes;TRY(add(&minimum,PREPARATION,b->aggregate_limit));
 CohSourceMeshBatchReport old;TRY(coh_source_mesh_batch_report(*batch,&old));
 for(unsigned k=0;k<4;k++)if(!separate(*batch,old.owned_bytes,p[k],sizes[k]))return COH_INVALID;
 CohSourceMeshDependencies base;TRY(coh_source_mesh_batch_dependencies(*batch,0,&base));
 CohSourceSealedReport r={0};r.meshes=old.meshes;r.parts=old.parts;r.preparation_reserve=PREPARATION;r.inherited_loader_reservations=old.loader_reservations;r.owned_bytes=sizeof(CohSourceSealed)+(size_t)old.meshes*sizeof(Entry);
 if(r.owned_bytes>b->owned_limit)return COH_LIMIT;
 for(uint32_t n=0;n<old.meshes;n++){
  for(unsigned k=0;k<4;k++)TRY(source_control(*batch,n,p[k],sizes[k]));
  CohSourceMeshReport m;uint32_t first;TRY(coh_source_mesh_batch_entry(*batch,n,&m,&first));size_t offset,path;
  TRY(path_size(m.source.geo.id.path,&path));
  TRY(region(&r.owned_bytes,(size_t)m.vertices*sizeof(CohRenderVertex),b->owned_limit,&offset));TRY(region(&r.owned_bytes,(size_t)m.triangles*3*sizeof(uint32_t),b->owned_limit,&offset));TRY(region(&r.owned_bytes,(size_t)m.parts*sizeof(CohAssetGeoMaterial),b->owned_limit,&offset));TRY(region(&r.owned_bytes,m.source.actual_sources.record.size,b->owned_limit,&offset));TRY(region(&r.owned_bytes,m.source.actual_sources.header.size,b->owned_limit,&offset));TRY(region(&r.owned_bytes,path,b->owned_limit,&offset));
 }
 r.shared_source_bytes=base.body.selection_owned_bytes;TRY(add(&r.shared_source_bytes,base.body.profile_bytes,b->aggregate_limit));TRY(add(&r.shared_source_bytes,base.body.join.report.owned_bytes,b->aggregate_limit));TRY(add(&r.shared_source_bytes,base.body.join.catalog_owned_bytes,b->aggregate_limit));TRY(add(&r.shared_source_bytes,base.body.join.snapshot_owned_bytes,b->aggregate_limit));TRY(add(&r.shared_source_bytes,base.body.join.graph_owned_bytes,b->aggregate_limit));
 size_t peak=b->retained_bytes;TRY(add(&peak,old.owned_bytes,b->aggregate_limit));TRY(add(&peak,old.mesh_owned_bytes,b->aggregate_limit));TRY(add(&peak,old.source_owner_bytes,b->aggregate_limit));TRY(add(&peak,old.loader_reservations,b->aggregate_limit));TRY(add(&peak,r.owned_bytes,b->aggregate_limit));TRY(add(&peak,PREPARATION,b->aggregate_limit));r.retirement_peak_bytes=peak;
 CohSourceSelection*selection=(CohSourceSelection*)base.body.selection_identity;CohSourceSelectionReport selection_report;TRY(coh_source_selection_report(selection,&selection_report));r.evidence_kind=selection_report.evidence_kind;r.profile_id=selection_report.profile_id;
 TRY(tick(cancel));CohSourceSealed*candidate=calloc(1,r.owned_bytes);if(!candidate)return COH_LIMIT;
 size_t at=sizeof(CohSourceSealed)+(size_t)old.meshes*sizeof(Entry);CohStatus status=COH_OK;
 for(uint32_t n=0;n<old.meshes;n++){
  status=tick(cancel);if(status!=COH_OK)goto fail;
  CohSourceMeshReport m;uint32_t first;status=coh_source_mesh_batch_entry(*batch,n,&m,&first);if(status!=COH_OK)goto fail;Entry*e=candidate->entries+n;size_t offset,path;status=path_size(m.source.geo.id.path,&path);if(status!=COH_OK)goto fail;
#define AREA(field,bytes) do{status=region(&at,(bytes),r.owned_bytes,&offset);if(status!=COH_OK)goto fail;(field)=(void*)((uint8_t*)candidate+offset);}while(0)
  AREA(e->vertices,(size_t)m.vertices*sizeof(*e->vertices));AREA(e->indices,(size_t)m.triangles*3*sizeof(*e->indices));AREA(e->parts,(size_t)m.parts*sizeof(*e->parts));uint8_t*record;uint8_t*header;char*assetpath;AREA(record,m.source.actual_sources.record.size);AREA(header,m.source.actual_sources.header.size);AREA(assetpath,path);
#undef AREA
  memcpy(record,m.source.actual_sources.record.data,m.source.actual_sources.record.size);memcpy(header,m.source.actual_sources.header.data,m.source.actual_sources.header.size);memcpy(assetpath,m.source.geo.id.path,path);
  e->view.source_ordinal=m.source.source_ordinal;e->view.graph_node=m.source.graph_node;e->view.graph_generation=m.source.graph_generation;e->view.catalog_generation=m.source.catalog_generation;e->view.first_part=first;e->view.vertices=m.vertices;e->view.triangles=m.triangles;e->view.parts=m.parts;e->view.binding=m.source.binding;e->view.geo=m.source.geo;e->view.geo.id.path=assetpath;e->view.model=m.source.model;e->view.resource_record=(CohBytes){record,m.source.actual_sources.record.size};e->view.original_header=(CohBytes){header,m.source.actual_sources.header.size};memcpy(e->view.resource_record_sha256,m.source.resource_record_sha256,32);memcpy(e->view.resources_sha256,m.source.resources_sha256,32);e->view.unscaled_base_uv=1;e->view.material_binding_required=1;
  const char**names[]={&e->view.model.definition_name,&e->view.model.model_name,&e->view.model.geo_name,&e->view.model.trick_name,&e->view.model.trick_file,&e->view.model.library_name};
  for(unsigned k=0;k<6;k++)if(*names[k]){status=name_offset(*names[k],m.source.actual_sources.record,&offset);if(status!=COH_OK)goto fail;*names[k]=(const char*)record+offset;}
  status=name_offset(m.source.model.model.name,m.source.actual_sources.header,&offset);if(status!=COH_OK)goto fail;e->view.model.model.name=(const char*)header+offset;
  if(strcmp(m.source.geo.source_geo_name,e->view.model.geo_name)){status=COH_STATE;goto fail;}e->view.geo.source_geo_name=e->view.model.geo_name;
  uint32_t triangles=0;const CohRenderVertex*vertices=NULL;
  for(uint32_t k=0;k<m.parts;k++){status=tick(cancel);if(status!=COH_OK)goto fail;CohSourceMeshPart part;status=coh_source_mesh_batch_part(*batch,n,k,&part);if(status!=COH_OK)goto fail;if(part.vertex_count!=m.vertices||part.source_material.first_triangle!=triangles||part.source_material.triangle_count>m.triangles-triangles||part.index_count!=part.source_material.triangle_count*3){status=COH_STATE;goto fail;}if(!k){vertices=part.vertices;memcpy(e->vertices,vertices,(size_t)m.vertices*sizeof(*vertices));}else if(vertices!=part.vertices){status=COH_STATE;goto fail;}memcpy(e->indices+(size_t)triangles*3,part.indices,(size_t)part.index_count*sizeof(*part.indices));e->parts[k]=part.source_material;status=name_offset(part.source_material.texture_name,m.source.actual_sources.header,&offset);if(status!=COH_OK)goto fail;e->parts[k].texture_name=(const char*)header+offset;triangles+=part.source_material.triangle_count;}
  if(triangles!=m.triangles){status=COH_STATE;goto fail;}
 }
 if(at!=r.owned_bytes){status=COH_STATE;goto fail;}status=tick(cancel);if(status!=COH_OK)goto fail;status=coh_source_selection_retain(selection);if(status!=COH_OK)goto fail;
 candidate->selection=selection;candidate->identity=(CohSourceSealedIdentity){selection,base.body.join_identity,base.body.join};candidate->report=r;CohSourceMeshBatch*retired=*batch;*batch=NULL;coh_source_mesh_batch_free(retired);*out=candidate;*report=r;return COH_OK;
 fail:coh_source_sealed_free(candidate);return status;
}
