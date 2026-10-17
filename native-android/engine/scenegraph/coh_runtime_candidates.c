#include "coh_runtime_candidates.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#define RESERVE COH_SG_FIXED_SCRATCH_BYTES
#define TRY(x) do{CohStatus s_=(x);if(s_!=COH_OK)return s_;}while(0)
struct CohRuntimeCandidates {uint32_t refs,roots,edges;const CohRuntimeGraph*graph;CohResourceJoin*join;CohResourceJoinIdentity identity;CohRuntimeGraphBinding binding;const CohResourceSource*sources;size_t count;uint32_t*map;CohRuntimeCandidateOwnerReport report;};
static int disjoint(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;if(!an||!bn)return 1;if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 0;return x+an<=y||y+bn<=x;}
static int separate(const void**p,const size_t*n,unsigned count){for(unsigned i=0;i<count;i++)for(unsigned j=i+1;j<count;j++)if(!disjoint(p[i],n[i],p[j],n[j]))return 0;return 1;}
static int binding_equal(const CohRuntimeGraphBinding*a,const CohRuntimeGraphBinding*b){return a->generation==b->generation&&a->catalog_generation==b->catalog_generation&&a->pins.asset_generation==b->pins.asset_generation&&!memcmp(a->pins.catalog_sha256,b->pins.catalog_sha256,32)&&!memcmp(a->pins.snapshot_sha256,b->pins.snapshot_sha256,32)&&!memcmp(a->pins.source_sha256,b->pins.source_sha256,32)&&!memcmp(a->pins.run_sha256,b->pins.run_sha256,32);}
static int matrix_ok(const CohSgMatrix m){for(unsigned i=0;i<4;i++)for(unsigned j=0;j<3;j++)if(!isfinite(m[i][j]))return 0;return 1;}
static int output_disjoint(const CohRuntimeCandidates*c,const void*out,size_t bytes){return disjoint(c,sizeof(*c),out,bytes)&&disjoint(c->map,(size_t)c->report.nodes*sizeof(*c->map),out,bytes)&&disjoint(c->sources,c->count*sizeof(*c->sources),out,bytes)&&disjoint(c->identity.catalog_bytes.data,c->identity.catalog_bytes.size,out,bytes)&&disjoint(c->identity.snapshot_bytes.data,c->identity.snapshot_bytes.size,out,bytes)&&disjoint(c->identity.resource_bytes.data,c->identity.resource_bytes.size,out,bytes);}
CohStatus coh_runtime_candidates_retain(CohRuntimeCandidates*c){if(!c||!c->refs)return COH_INVALID;if(c->refs==UINT32_MAX)return COH_LIMIT;c->refs++;return COH_OK;}
void coh_runtime_candidates_free(CohRuntimeCandidates*c){if(!c)return;if(--c->refs)return;coh_resource_join_free(c->join);free(c->map);free(c);}
CohStatus coh_runtime_candidates_create(const CohRuntimeGraph*g,CohResourceJoin*j,
 const CohRuntimeCandidateBudget*budget,CohCancel cancel,CohRuntimeCandidates**out,CohRuntimeCandidateOwnerReport*report){
 if(!g||!j||!budget||!out||!report)return COH_INVALID;
 CohResourceJoinIdentity id;TRY(coh_resource_join_identity(j,&id));CohBytes catalog,snapshot;TRY(coh_runtime_graph_sources(g,&catalog,&snapshot));
 const CohResourceSource*sources;size_t count;CohResourceBinding resource;TRY(coh_resource_join_sources(j,&sources,&count,&resource));if(count>COH_RESOURCE_ROWS_MAX)return COH_LIMIT;
 const void*p[]={budget,out,report,id.catalog_bytes.data,id.snapshot_bytes.data,id.resource_bytes.data,sources};size_t n[]={sizeof(*budget),sizeof(*out),sizeof(*report),id.catalog_bytes.size,id.snapshot_bytes.size,id.resource_bytes.size,count*sizeof(*sources)};if(!separate(p,n,7))return COH_INVALID;
 if(*out)return COH_STATE;
 if(count>COH_RESOURCE_ROWS_MAX||id.report.rows!=count||id.graph_identity!=g||!id.report.source_association_verified||catalog.data!=id.catalog_bytes.data||catalog.size!=id.catalog_bytes.size||snapshot.data!=id.snapshot_bytes.data||snapshot.size!=id.snapshot_bytes.size)return COH_STATE;
 CohRuntimeGraphBinding binding;CohRuntimeGraphReport gr;TRY(coh_runtime_graph_binding(g,&binding));TRY(coh_runtime_graph_report(g,&gr));
 if(gr.nodes>COH_SG_DEFS_MAX+COH_RUNTIME_SNAPSHOT_EXTERNAL_MAX||gr.owned_bytes!=id.graph_owned_bytes||binding.generation!=id.report.graph_generation||binding.catalog_generation!=id.report.catalog_generation||resource.generation!=id.pins.resource.generation||resource.asset_generation!=binding.pins.asset_generation||memcmp(resource.source_sha256,binding.pins.source_sha256,32)||memcmp(resource.run_sha256,binding.pins.run_sha256,32)||memcmp(resource.manifest_sha256,id.pins.resource.manifest_sha256,32))return COH_STATE;
 size_t owned=sizeof(CohRuntimeCandidates)+(size_t)gr.nodes*sizeof(uint32_t),limit=budget->aggregate_limit,total=budget->retained_bytes,deps=0;
 if(budget->owned_limit>COH_SG_MEMORY_MAX||owned>budget->owned_limit||!limit||limit>COH_SG_TRANSACTION_MAX||total>limit)return COH_LIMIT;
 size_t add[]={id.report.owned_bytes,id.catalog_owned_bytes,id.snapshot_owned_bytes,id.graph_owned_bytes};for(unsigned i=0;i<4;i++){if(add[i]>limit-total)return COH_LIMIT;total+=add[i];deps+=add[i];}
 if(owned>limit-total)return COH_LIMIT;
 total+=owned;if(RESERVE>limit-total)return COH_LIMIT;total+=RESERVE;
 CohRuntimeCandidates*c=calloc(1,sizeof(*c));if(!c)return COH_LIMIT;
 c->map=gr.nodes?malloc((size_t)gr.nodes*sizeof(*c->map)):NULL;if(gr.nodes&&!c->map){free(c);return COH_LIMIT;}
 c->graph=g;c->binding=binding;c->identity=id;c->sources=sources;c->count=count;c->roots=gr.source.root_slots;c->edges=gr.edges;c->report=(CohRuntimeCandidateOwnerReport){gr.nodes,(uint32_t)count,binding.generation,binding.catalog_generation,owned,deps,total,0,0,0};
 CohStatus status=COH_OK;
 for(uint32_t node=0;node<gr.nodes;node++)c->map[node]=UINT32_MAX;
 for(uint32_t row=0;row<count;row++){if(cancel.poll&&cancel.poll(cancel.context)){status=COH_CANCELLED;goto failure;}uint32_t node;status=coh_resource_join_node(j,row,&node);if(status!=COH_OK)goto failure;if(node>=gr.nodes||c->map[node]!=UINT32_MAX){status=COH_STATE;goto failure;}c->map[node]=row;}
 for(uint32_t node=0;node<gr.nodes;node++){if(cancel.poll&&cancel.poll(cancel.context)){status=COH_CANCELLED;goto failure;}CohRuntimeGraphNode v;status=coh_runtime_graph_node(g,node,&v);if(status!=COH_OK)goto failure;if((c->map[node]!=UINT32_MAX)!=!!v.in_use){status=COH_STATE;goto failure;}}
 if(cancel.poll&&cancel.poll(cancel.context)){status=COH_CANCELLED;goto failure;}
 status=coh_resource_join_retain(j);if(status!=COH_OK)goto failure;c->join=j;c->refs=1;*report=c->report;*out=c;return COH_OK;
 failure:free(c->map);free(c);return status;
}
CohStatus coh_runtime_candidates_report(const CohRuntimeCandidates*c,CohRuntimeCandidateOwnerReport*out){if(!c||!out||!output_disjoint(c,out,sizeof(*out)))return COH_INVALID;*out=c->report;return COH_OK;}
CohStatus coh_runtime_candidates_node(const CohRuntimeCandidates*c,uint32_t node,uint32_t*out){if(!c||!out||!output_disjoint(c,out,sizeof(*out)))return COH_INVALID;if(node>=c->report.nodes||c->map[node]==UINT32_MAX)return COH_NOT_FOUND;*out=c->map[node];return COH_OK;}
CohStatus coh_runtime_candidates_source(const CohRuntimeCandidates*c,uint32_t ordinal,CohResourceSource*out){if(!c||!out||!output_disjoint(c,out,sizeof(*out)))return COH_INVALID;if(ordinal>=c->count)return COH_NOT_FOUND;*out=c->sources[ordinal];return COH_OK;}
CohStatus coh_runtime_candidates_begin(CohRuntimeCandidates*c,const CohRuntimeInstances*walk,
 const CohRuntimeInstance*batch,size_t count,const CohRuntimeBoundsReport*bounds_report,
 const CohRuntimeBoundsRow*bounds,size_t bounds_rows,const CohRuntimeCandidateBudget*budget,
 CohCancel cancel,CohRuntimeCandidatePager*out,CohRuntimeCandidatePageReport*report){
 if(!c||!walk||!budget||!out||!report||count>COH_RUNTIME_INSTANCE_BATCH_MAX||(count&&!batch)||bounds_rows>COH_SG_DEFS_MAX+COH_RUNTIME_SNAPSHOT_EXTERNAL_MAX||(!bounds_report&&(bounds||bounds_rows))||(bounds_report&&(!bounds||bounds_rows<c->report.nodes)))return COH_INVALID;
 const void*p[]={walk,batch,bounds_report,bounds,budget,out,report};size_t n[]={sizeof(*walk),count*sizeof(*batch),bounds_report?sizeof(*bounds_report):0,bounds_rows*sizeof(*bounds),sizeof(*budget),sizeof(*out),sizeof(*report)};if(!separate(p,n,7))return COH_INVALID;for(unsigned i=0;i<7;i++)if(!output_disjoint(c,p[i],n[i]))return COH_INVALID;
 if(out->active||walk->initialized!=1||walk->graph!=c->graph||!binding_equal(&walk->binding,&c->binding)||walk->catalog.data!=c->identity.catalog_bytes.data||walk->catalog.size!=c->identity.catalog_bytes.size||walk->snapshot.data!=c->identity.snapshot_bytes.data||walk->snapshot.size!=c->identity.snapshot_bytes.size||count!=walk->progress.batch_count||count>walk->progress.occurrences||(bounds_report&&!binding_equal(&bounds_report->graph,&c->binding)))return COH_STATE;
 size_t limit=budget->aggregate_limit,total=budget->retained_bytes;if(!limit||limit>COH_SG_TRANSACTION_MAX||total>limit)return COH_LIMIT;
 size_t add[]={c->report.owned_bytes,c->report.dependency_bytes,count*sizeof(*batch),bounds_rows*sizeof(*bounds),bounds_report?sizeof(*bounds_report):0,sizeof(*out),sizeof(*report),RESERVE};for(unsigned i=0;i<sizeof(add)/sizeof(add[0]);i++){if(add[i]>limit-total)return COH_LIMIT;total+=add[i];}
 for(size_t i=0;i<count;i++){if(cancel.poll&&cancel.poll(cancel.context))return COH_CANCELLED;const CohRuntimeInstance*r=&batch[i];if(r->ordinal!=walk->progress.occurrences-count+i||r->graph_generation!=c->binding.generation||r->node>=c->report.nodes||c->map[r->node]==UINT32_MAX||r->root_slot>=c->roots||r->depth>COH_SG_DEPTH_MAX||((r->depth==0)!=(r->parent_ordinal==UINT64_MAX))||(r->depth&&r->parent_ordinal>=r->ordinal)||!matrix_ok(r->world))return COH_STATE;CohRuntimeGraphNode node;TRY(coh_runtime_graph_node(c->graph,r->node,&node));if(r->model_present!=node.source_model_present||r->external!=node.external)return COH_STATE;}
 if(cancel.poll&&cancel.poll(cancel.context))return COH_CANCELLED;
 CohRuntimeCandidatePager pager={0};pager.owner=c;pager.batch=batch;pager.bounds=bounds;pager.bounds_rows=bounds_rows;pager.active=1;pager.count=(uint32_t)count;pager.base_reserved_bytes=total;pager.aggregate_limit=limit;pager.progress.total=(uint32_t)count;pager.progress.complete=count==0;pager.progress.aggregate_reserved_bytes=total;
 TRY(coh_runtime_candidates_retain(c));*out=pager;*report=pager.progress;return COH_OK;
}
CohStatus coh_runtime_candidates_next(CohRuntimeCandidatePager*cursor,CohRuntimeCandidate*out,
 size_t capacity,uint32_t step_limit,CohCancel cancel,CohRuntimeCandidatePageReport*report){
 if(!cursor||cursor->active!=1||!cursor->owner||!out||!report||!capacity||capacity>COH_RUNTIME_INSTANCE_BATCH_MAX||!step_limit||step_limit>COH_RUNTIME_INSTANCE_STEP_MAX)return COH_INVALID;
 const void*p[]={cursor,out,report,cursor->batch,cursor->bounds};size_t n[]={sizeof(*cursor),capacity*sizeof(*out),sizeof(*report),(size_t)cursor->count*sizeof(*cursor->batch),cursor->bounds_rows*sizeof(*cursor->bounds)};if(!separate(p,n,5))return COH_INVALID;for(unsigned i=0;i<3;i++)if(!output_disjoint(cursor->owner,p[i],n[i]))return COH_INVALID;
 size_t extra=capacity*sizeof(*out)+sizeof(*report);if(cursor->base_reserved_bytes>cursor->aggregate_limit||extra>cursor->aggregate_limit-cursor->base_reserved_bytes)return COH_LIMIT;
 CohRuntimeCandidatePager c=*cursor;uint32_t used=0;
 while(c.offset<c.count&&used<capacity&&used<step_limit){
  if(cancel.poll&&cancel.poll(cancel.context))return COH_CANCELLED;
  const CohRuntimeInstance*r=&c.batch[c.offset];CohRuntimeCandidate v={0};v.instance=*r;v.source_ordinal=c.owner->map[r->node];v.source_model_present=r->model_present;memcpy(v.source_record_sha256,c.owner->sources[v.source_ordinal].sha256,32);v.unresolved=COH_CANDIDATE_CLIENT_UNKNOWN_MASK;if(r->model_present)v.unresolved|=COH_CANDIDATE_SOURCE_BODY;
  if(c.bounds){const CohRuntimeBoundsRow*b=&c.bounds[r->node];if(b->result>COH_RB_CAPTURED_FUTURE)return COH_INVALID;v.bounds_result=b->result;if(b->result==COH_RB_COMPUTED||b->result==COH_RB_CAPTURED_FUTURE){for(unsigned i=0;i<3;i++)if(!isfinite(b->bounds.min[i])||!isfinite(b->bounds.max[i])||!isfinite(b->bounds.mid[i])||b->bounds.min[i]>b->bounds.max[i])return COH_INVALID;if(!isfinite(b->bounds.radius)||b->bounds.radius<0)return COH_INVALID;v.local_source_bounds=b->bounds;v.has_source_bounds=1;}}
  if(!v.has_source_bounds)v.unresolved|=COH_CANDIDATE_SOURCE_BOUNDS;
  if(v.has_source_bounds)c.progress.with_source_bounds++;else c.progress.without_source_bounds++;
  if(r->model_present)c.progress.model_candidates++;else c.progress.no_model_candidates++;
  out[used++]=v;c.offset++;
 }
 if(cancel.poll&&cancel.poll(cancel.context))return COH_CANCELLED;
 c.progress.processed=c.offset;c.progress.emitted=used;c.progress.steps=used;c.progress.complete=c.offset==c.count;c.progress.aggregate_reserved_bytes=c.base_reserved_bytes+extra;
 *cursor=c;*report=c.progress;return COH_OK;
}
void coh_runtime_candidates_close(CohRuntimeCandidatePager*c){if(!c||!c->active)return;CohRuntimeCandidates*owner=c->owner;memset(c,0,sizeof(*c));coh_runtime_candidates_free(owner);}
