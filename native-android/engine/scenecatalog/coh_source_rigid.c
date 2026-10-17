#include "coh_source_rigid_internal.h"
#include <stdlib.h>
#include <string.h>
struct CohSourceRigid {CohSourceBody *body;CohWrRigidResource *rigid;CohSourceRigidReport report;};
static int disjoint(const void *a,size_t an,const void *b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;if(!an||!bn)return 1;if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 0;return x+an<=y||y+bn<=x;}
static CohStatus add(size_t *n,size_t x,size_t cap){if(*n>cap||x>cap-*n)return COH_LIMIT;*n+=x;return COH_OK;}
#define TRY(x) do{CohStatus st_=(x);if(st_!=COH_OK)return st_;}while(0)
static CohStatus tick(CohCancel c){return c.poll&&c.poll(c.context)?COH_CANCELLED:COH_OK;}
void coh_source_rigid_free(CohSourceRigid *r){if(!r)return;coh_wr_rigid_release(&r->rigid);coh_source_body_free(r->body);free(r);}
CohStatus coh_source_rigid_create_using(CohSourceBody **body,const CohSourceRigidRequest *q,const CohSourceRigidLimits *b,CohCancel cancel,CohSourceRigid **out,CohSourceRigidReport *report,uint32_t exact_version,CohSourceRigidAcquire acquire_cpu){
 if(!acquire_cpu||(exact_version!=0&&exact_version!=7&&exact_version!=5))return COH_INVALID;
 if(!body||!*body||!q||!b||!out||!report||!q->digest||!q->acquire||!q->release||!q->material_generation)return COH_INVALID;
 const void *p[]={body,q,b,out,report};size_t sizes[]={sizeof(*body),sizeof(*q),sizeof(*b),sizeof(*out),sizeof(*report)};
 for(unsigned n=0;n<5;n++)for(unsigned k=n+1;k<5;k++)if(!disjoint(p[n],sizes[n],p[k],sizes[k]))return COH_INVALID;
 if(!b->aggregate_limit||b->aggregate_limit>COH_WR_MAX_MEMORY)return COH_LIMIT;
 TRY(tick(cancel));CohSourceBodyLease lease;TRY(coh_source_body_lease(*body,q->source_ordinal,&lease));
 CohBytes spans[]={lease.actual_sources.record,lease.actual_sources.header,lease.actual_sources.blob};
 for(unsigned k=0;k<3;k++)for(unsigned n=0;n<5;n++)if(!disjoint(p[n],sizes[n],spans[k].data,spans[k].size))return COH_INVALID;
 const void *sp[]={lease.model.definition_name,lease.model.model_name,lease.model.geo_name,lease.geo.id.path};
 for(unsigned k=0;k<4;k++)for(unsigned n=0;n<5;n++)if(!disjoint(p[n],sizes[n],sp[k],strlen(sp[k])+1))return COH_INVALID;
 if(*out)return COH_STATE;
 if(lease.model.zero_draw_model||(exact_version&&lease.model.geo_version!=exact_version))return COH_UNSUPPORTED;
 size_t external=b->retained_bytes;TRY(add(&external,lease.retained_owner_bytes,b->aggregate_limit));TRY(add(&external,sizeof(CohSourceRigid)+8192u,b->aggregate_limit));size_t preflight=external;TRY(add(&preflight,lease.loader_reservation,b->aggregate_limit));
 if(coh_asset_stats(lease.loader).peak_allocated_bytes>lease.loader_reservation)return COH_LIMIT;
 CohSourceRigid *r=calloc(1,sizeof(*r));if(!r)return COH_LIMIT;
 CohWrRigidRequest request={0};request.geo=lease.geo.id;request.model=lease.model.model_name;memcpy(request.geo_sha256,lease.geo.sha256,32);request.material_generation=q->material_generation;request.digest=q->digest;request.digest_context=q->digest_context;request.acquire=q->acquire;request.release=q->release;request.material_context=q->material_context;
 CohWrRigidLimits limits={b->aggregate_limit,external,lease.loader_reservation,b->max_workspace_bytes,b->max_stream_bytes,b->max_models,b->max_vertices,b->max_triangles,b->max_parts};
 CohStatus status=acquire_cpu(lease.loader,&request,&limits,cancel,&r->rigid);if(status!=COH_OK)goto fail;
 CohAssetId id;const char *model;status=coh_wr_rigid_identity(r->rigid,&id,&model);if(status!=COH_OK)goto fail;status=coh_wr_rigid_report(r->rigid,&r->report.rigid);if(status!=COH_OK)goto fail;
 if(id.generation!=lease.binding.asset_generation||strcmp(id.path,lease.geo.id.path)||strcmp(model,lease.model.model_name)||memcmp(r->report.rigid.geo_sha256,lease.geo.sha256,32)||r->report.rigid.material_generation!=q->material_generation||r->report.rigid.geo_version!=lease.model.geo_version||r->report.rigid.vertices!=lease.model.model.vertex_count||r->report.rigid.triangles!=lease.model.model.triangle_count||r->report.rigid.parts!=lease.model.model.material_count){status=COH_STATE;goto fail;}
 status=tick(cancel);if(status!=COH_OK)goto fail;
 r->report.source_ordinal=lease.source_ordinal;r->report.graph_node=lease.graph_node;r->report.owner_kind=lease.model.owner_kind;r->report.file=lease.model.file;r->report.slot=lease.model.slot;r->report.original_id=lease.model.original_id;
 r->report.evidence_kind=COH_SOURCE_PROCEDURAL_EXACT_COLD_CAPTURE;r->report.profile_id=1;r->report.asset_generation=lease.binding.asset_generation;r->report.resource_owner_generation=lease.binding.generation;r->report.graph_generation=lease.graph_generation;r->report.catalog_generation=lease.catalog_generation;r->report.material_generation=q->material_generation;r->report.derived_file_origin_verified=1;r->report.unresolved_client_semantics=1;
 r->report.retained_source_bytes=lease.retained_owner_bytes;r->report.aggregate_reserved_bytes=r->report.rigid.aggregate_peak_bytes;
 memcpy(r->report.source_sha256,lease.binding.source_sha256,32);memcpy(r->report.run_sha256,lease.binding.run_sha256,32);memcpy(r->report.resource_record_sha256,lease.resource_record_sha256,32);memcpy(r->report.resources_sha256,lease.resources_sha256,32);
 r->body=*body;*body=NULL;*report=r->report;*out=r;return COH_OK;
 fail:coh_source_rigid_free(r);return status;
}
CohStatus coh_source_rigid_report(const CohSourceRigid *r,CohSourceRigidReport *out){if(!r||!out)return COH_INVALID;if(!disjoint(r,sizeof(*r),out,sizeof(*out)))return COH_INVALID;*out=r->report;return COH_OK;}
CohStatus coh_source_rigid_part(const CohSourceRigid *r,uint32_t i,CohRenderGeometry *g,CohWrRigidMaterial *m){if(!r||!g||!m)return COH_INVALID;if(!disjoint(g,sizeof(*g),m,sizeof(*m))||!disjoint(r,sizeof(*r),g,sizeof(*g))||!disjoint(r,sizeof(*r),m,sizeof(*m)))return COH_INVALID;return coh_wr_rigid_part(r->rigid,i,g,m);}

CohStatus coh_source_rigid_create(CohSourceBody **body,const CohSourceRigidRequest *q,
 const CohSourceRigidLimits *b,CohCancel cancel,CohSourceRigid **out,CohSourceRigidReport *report){
 return coh_source_rigid_create_using(body,q,b,cancel,out,report,0,coh_wr_rigid_source_acquire);
}
