#include "coh_runtime_instances.h"
#include <math.h>
#include <string.h>
#define TRY(x) do{CohStatus s_=(x);if(s_!=COH_OK)return s_;}while(0)
static int disjoint(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;if(!an||!bn)return 1;if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 0;return x+an<=y||y+bn<=x;}
static int separate(const void**p,const size_t*n,unsigned count){for(unsigned i=0;i<count;i++)for(unsigned j=i+1;j<count;j++)if(!disjoint(p[i],n[i],p[j],n[j]))return 0;return 1;}
static int same_binding(const CohRuntimeGraphBinding*a,const CohRuntimeGraphBinding*b){return a->generation==b->generation&&a->catalog_generation==b->catalog_generation&&a->pins.asset_generation==b->pins.asset_generation&&!memcmp(a->pins.catalog_sha256,b->pins.catalog_sha256,32)&&!memcmp(a->pins.snapshot_sha256,b->pins.snapshot_sha256,32)&&!memcmp(a->pins.source_sha256,b->pins.source_sha256,32)&&!memcmp(a->pins.run_sha256,b->pins.run_sha256,32);}
static int finite_matrix(const CohSgMatrix m){for(unsigned i=0;i<4;i++)for(unsigned j=0;j<3;j++)if(!isfinite(m[i][j]))return 0;return 1;}
/* Original mulMat4Inline operation order: no added zero in basis columns. */
static CohStatus compose(const CohSgMatrix p,const CohSgMatrix child,CohSgMatrix out){
 if(!finite_matrix(p)||!finite_matrix(child))return COH_INVALID;
 CohSgMatrix result;
 for(unsigned i=0;i<4;i++)for(unsigned j=0;j<3;j++){
  float value=child[i][0]*p[0][j]+child[i][1]*p[1][j]+child[i][2]*p[2][j];
  if(i==3)value+=p[3][j];
  if(!isfinite(value))return COH_INVALID;
  result[i][j]=value;
 }
 memcpy(out,result,sizeof(result));return COH_OK;
}
CohStatus coh_runtime_instances_begin(const CohRuntimeGraph*g,const CohRuntimeInstancesConfig*config,
 const CohRuntimeInstancesBudget*budget,CohRuntimeInstances*out,CohRuntimeInstancesReport*report){
 if(!g||!config||!budget||!out||!report)return COH_INVALID;
 CohBytes catalog,snapshot;TRY(coh_runtime_graph_sources(g,&catalog,&snapshot));
 const void*p[]={config,budget,out,report,catalog.data,snapshot.data};size_t n[]={sizeof(*config),sizeof(*budget),sizeof(*out),sizeof(*report),catalog.size,snapshot.size};if(!separate(p,n,6))return COH_INVALID;
 if(!config->maximum_occurrences||config->maximum_occurrences>COH_RUNTIME_INSTANCE_COUNT_MAX||!config->maximum_work||config->maximum_work>COH_RUNTIME_INSTANCE_WORK_MAX)return COH_LIMIT;
 size_t limit=budget->aggregate_limit,total=budget->retained_bytes;if(!limit||limit>COH_SG_TRANSACTION_MAX||total>limit)return COH_LIMIT;
 CohRuntimeGraphReport topology;CohRuntimeGraphBinding binding;TRY(coh_runtime_graph_report(g,&topology));TRY(coh_runtime_graph_binding(g,&binding));
 size_t add[]={topology.owned_bytes,catalog.size,snapshot.size,sizeof(*out),COH_SG_FIXED_SCRATCH_BYTES,sizeof(*report)};
 for(unsigned i=0;i<sizeof(add)/sizeof(add[0]);i++){if(add[i]>limit-total)return COH_LIMIT;total+=add[i];}
 CohRuntimeInstances candidate;memset(&candidate,0,sizeof(candidate));candidate.graph=g;candidate.catalog=catalog;candidate.snapshot=snapshot;candidate.binding=binding;candidate.nodes=topology.nodes;candidate.root_slots=topology.source.root_slots;candidate.config=*config;candidate.aggregate_limit=limit;candidate.base_reserved_bytes=total;candidate.initialized=1;candidate.progress.graph=binding;candidate.progress.aggregate_reserved_bytes=total;
 *out=candidate;*report=candidate.progress;return COH_OK;
}
CohStatus coh_runtime_instances_next(CohRuntimeInstances*cursor,CohRuntimeInstance*rows,size_t capacity,
 uint32_t step_limit,CohCancel cancel,CohRuntimeInstancesReport*report){
 if(!cursor||!rows||!report||!capacity||capacity>COH_RUNTIME_INSTANCE_BATCH_MAX||!step_limit||step_limit>COH_RUNTIME_INSTANCE_STEP_MAX)return COH_INVALID;
 const void*p[]={cursor,rows,report,cursor->catalog.data,cursor->snapshot.data};size_t n[]={sizeof(*cursor),capacity*sizeof(*rows),sizeof(*report),cursor->catalog.size,cursor->snapshot.size};if(!separate(p,n,5))return COH_INVALID;
 if(cursor->initialized!=1||!cursor->graph||cursor->depth>COH_SG_DEPTH_MAX+1u)return COH_STATE;
 CohRuntimeGraphBinding binding;CohBytes catalog,snapshot;TRY(coh_runtime_graph_binding(cursor->graph,&binding));TRY(coh_runtime_graph_sources(cursor->graph,&catalog,&snapshot));
 if(!same_binding(&binding,&cursor->binding)||catalog.data!=cursor->catalog.data||catalog.size!=cursor->catalog.size||snapshot.data!=cursor->snapshot.data||snapshot.size!=cursor->snapshot.size)return COH_STATE;
 size_t bytes=capacity*sizeof(*rows);if(cursor->base_reserved_bytes>cursor->aggregate_limit||bytes>cursor->aggregate_limit-cursor->base_reserved_bytes)return COH_LIMIT;
 CohRuntimeInstances c=*cursor;uint32_t used=0,steps=0;
 while(steps<step_limit&&used<capacity&&!c.progress.complete){
  if(cancel.poll&&cancel.poll(cancel.context))return COH_CANCELLED;
  if(c.progress.work==c.config.maximum_work)return COH_LIMIT;
  c.progress.work++;steps++;
  if(!c.depth){
   if(c.next_root==c.root_slots){c.progress.complete=1;break;}
   CohRuntimeGraphRoot root;uint32_t slot=c.next_root++;TRY(coh_runtime_graph_root(c.graph,slot,&root));if(!root.active)continue;
   if(!finite_matrix((const float(*)[3])root.matrix))return COH_INVALID;
   CohRuntimeInstanceFrame f={0};f.node=root.node;f.incoming_edge=UINT32_MAX;f.parent_ordinal=UINT64_MAX;memcpy(f.world,root.matrix,sizeof(f.world));c.frames[0]=f;c.depth=1;c.active_root=slot;c.progress.roots_started++;continue;
  }
  CohRuntimeInstanceFrame*f=&c.frames[c.depth-1];CohRuntimeGraphNode node;TRY(coh_runtime_graph_node(c.graph,f->node,&node));if(!node.in_use)return COH_STATE;
  if(!f->emitted){
   if(c.progress.occurrences==c.config.maximum_occurrences)return COH_LIMIT;
   CohRuntimeInstance instance={0};instance.graph_generation=c.binding.generation;instance.node=f->node;instance.root_slot=c.active_root;instance.depth=c.depth-1;instance.incoming_edge=f->incoming_edge;instance.model_present=node.source_model_present;instance.external=node.external;instance.ordinal=c.progress.occurrences++;instance.parent_ordinal=f->parent_ordinal;memcpy(instance.world,f->world,sizeof(instance.world));
   f->emitted=1;f->ordinal=instance.ordinal;rows[used++]=instance;
   if(node.source_model_present)c.progress.model_occurrences++;
   if(node.external)c.progress.external_occurrences++;
   if(instance.depth>c.progress.maximum_depth)c.progress.maximum_depth=instance.depth;
   continue;
  }
  if(f->next_child==node.child_count){c.depth--;continue;}
  if(f->next_child>node.child_count||c.depth==COH_SG_DEPTH_MAX+1u)return COH_LIMIT;
  uint32_t edge=node.child_first+f->next_child++;CohRuntimeGraphChild child;TRY(coh_runtime_graph_child(c.graph,edge,&child));
  for(uint32_t i=0;i<c.depth;i++)if(c.frames[i].node==child.target)return COH_INVALID;
  CohRuntimeInstanceFrame next={0};next.node=child.target;next.incoming_edge=edge;next.parent_ordinal=f->ordinal;TRY(compose((const float(*)[3])f->world,(const float(*)[3])child.matrix,next.world));c.frames[c.depth++]=next;
 }
 if(cancel.poll&&cancel.poll(cancel.context))return COH_CANCELLED;
 c.progress.batch_count=used;c.progress.steps=steps;c.progress.aggregate_reserved_bytes=c.base_reserved_bytes+bytes;
 *cursor=c;*report=c.progress;return COH_OK;
}
CohStatus coh_runtime_instance_selection_input(const CohRuntimeInstances*c,const CohRuntimeInstance*instance,
 const CohRuntimeBoundsReport*report,const CohRuntimeBoundsRow*rows,size_t count,CohRuntimeInstanceSelectionInput*out){
 if(!c||!instance||!report||!rows||!out||count>COH_SG_DEFS_MAX+COH_RUNTIME_SNAPSHOT_EXTERNAL_MAX)return COH_INVALID;
 const void*p[]={c,instance,report,rows,out,c->catalog.data,c->snapshot.data};size_t n[]={sizeof(*c),sizeof(*instance),sizeof(*report),count*sizeof(*rows),sizeof(*out),c->catalog.size,c->snapshot.size};if(!separate(p,n,7))return COH_INVALID;
 if(c->initialized!=1||!same_binding(&c->binding,&report->graph)||instance->graph_generation!=c->binding.generation||instance->node>=count||count<c->nodes||instance->ordinal>=c->progress.occurrences)return COH_STATE;
 const CohRuntimeBoundsRow*r=&rows[instance->node];if(r->result!=COH_RB_COMPUTED&&r->result!=COH_RB_CAPTURED_FUTURE)return COH_NOT_FOUND;
 for(unsigned i=0;i<3;i++)if(!isfinite(r->bounds.min[i])||!isfinite(r->bounds.max[i])||!isfinite(r->bounds.mid[i])||r->bounds.min[i]>r->bounds.max[i])return COH_INVALID;
 if(!isfinite(r->bounds.radius)||r->bounds.radius<0||!finite_matrix(instance->world))return COH_INVALID;
 CohRuntimeInstanceSelectionInput value={*instance,r->bounds};*out=value;return COH_OK;
}
