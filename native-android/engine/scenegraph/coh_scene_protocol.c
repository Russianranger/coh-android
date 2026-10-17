#include "coh_scene_protocol.h"
#include <stdlib.h>
#include <string.h>
#define TRY(x) do{CohStatus s_=(x);if(s_!=COH_OK)return s_;}while(0)
struct CohSceneProtocol {
 const CohRuntimeGraph *graph;const CohSceneProtocol *expected_previous;
 CohRuntimeGraphOwner *graph_owner;
 CohCatalogOwner *catalog;CohCatalogSnapshot *snapshot;CohRuntimeGroupsWitness *witness;
 CohBytes catalog_bytes,snapshot_bytes;CohSceneProtocolRecord *records;
 CohSceneProtocolReport report;uint32_t references,next;
 const CohCancel *cancel; /* construction-only, cleared before publication */
};
static int disjoint(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;if(!an||!bn)return 1;if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 0;return x+an<=y||y+bn<=x;}
static int safe_output(const CohSceneProtocol*,const void*,size_t);
static int same_catalog(const CohCatalogBinding*a,const CohCatalogBinding*b){return a->owner_generation==b->owner_generation&&a->catalog_generation==b->catalog_generation&&a->asset_generation==b->asset_generation&&a->map_generation==b->map_generation&&!memcmp(a->catalog_sha256,b->catalog_sha256,32)&&!memcmp(a->source_sha256,b->source_sha256,32)&&!memcmp(a->inventory_sha256,b->inventory_sha256,32)&&!memcmp(a->map_sha256,b->map_sha256,32);}
static CohStatus poll(const CohCancel*c){return c&&c->poll&&c->poll(c->context)?COH_CANCELLED:COH_OK;}
static CohStatus capture(void*ctx,const CohCatalogSeedRecord*r){
 CohSceneProtocol*t=ctx;TRY(poll(t->cancel));if(r->node!=t->next||t->next>=t->report.records)return COH_STATE;
 t->records[t->next++]=(CohSceneProtocolRecord){*r,t->report.binding.groups_compatibility_checked&&!r->external};
 if(r->external)t->report.external_records++;else{t->report.ordinary_records++;if(r->in_use)t->report.active_records++;else t->report.tombstones++;if(t->report.binding.groups_compatibility_checked){if(r->emitted)t->report.equal_wire_updates++;else t->report.verified_omissions++;}}
 return COH_OK;
}
void coh_scene_protocol_release(CohSceneProtocol*t){if(!t)return;if(--t->references)return;coh_runtime_groups_witness_release(t->witness);coh_catalog_snapshot_release(t->snapshot);coh_catalog_owner_release(t->catalog);free(t->records);coh_runtime_graph_owner_release(t->graph_owner);free(t);}
CohStatus coh_scene_protocol_retain(CohSceneProtocol*t){if(!t)return COH_INVALID;if(t->references==UINT32_MAX)return COH_LIMIT;t->references++;return COH_OK;}
CohStatus coh_scene_protocol_create(const CohSceneProtocol*old,const CohRuntimeGraph*g,CohCatalogOwner*catalog,CohCatalogSnapshot*snapshot,const CohSceneProtocolGroups*groups,uint32_t generation,const CohSceneProtocolBudget*budget,const CohCancel*cancel,CohSceneProtocol**out,CohSceneProtocolReport*report){
 if(!g||!catalog||!snapshot||!budget||!out||!report)return COH_INVALID;
 if(groups&&(!groups->witness||!groups->binding||!groups->reader))return COH_INVALID;
 CohBytes cat,snap,owned,scat,ssnap;CohCatalogBinding cb;CohCatalogSnapshotBinding sb;CohRuntimeGraphBinding gb;
 union {CohRuntimeSnapshotReport snapshot;CohRuntimeGraphReport graph;} metadata;
 TRY(coh_runtime_graph_sources(g,&cat,&snap));TRY(coh_catalog_owner_bytes(catalog,&owned));TRY(coh_catalog_owner_binding(catalog,&cb));TRY(coh_catalog_snapshot_catalog(snapshot,&scat));TRY(coh_catalog_snapshot_view(snapshot,&ssnap,&sb,&metadata.snapshot));TRY(coh_runtime_graph_binding(g,&gb));
 if(owned.data!=cat.data||owned.size!=cat.size||scat.data!=cat.data||scat.size!=cat.size||ssnap.data!=snap.data||ssnap.size!=snap.size||!same_catalog(&cb,&sb.catalog)||gb.catalog_generation!=cb.catalog_generation||gb.pins.asset_generation!=cb.asset_generation||memcmp(gb.pins.catalog_sha256,cb.catalog_sha256,32)||memcmp(gb.pins.source_sha256,cb.source_sha256,32)||memcmp(gb.pins.snapshot_sha256,sb.snapshot_sha256,32)||memcmp(gb.pins.run_sha256,sb.run_sha256,32))return COH_STATE;
 if(!metadata.snapshot.definitions_crc_verified||!metadata.snapshot.references_crc_verified||!metadata.snapshot.root_matrices_verified||!metadata.snapshot.complete_source_name_closure)return COH_STATE;
 TRY(coh_runtime_graph_report(g,&metadata.graph));
 const void*p[]={budget,out,report,cancel,groups,groups?groups->binding:NULL,groups?groups->reader:NULL,groups?groups->reader->bytes.data:NULL,cat.data,snap.data};
 size_t n[]={sizeof(*budget),sizeof(*out),sizeof(*report),cancel?sizeof(*cancel):0,groups?sizeof(*groups):0,groups?sizeof(*groups->binding):0,groups?sizeof(*groups->reader):0,groups?groups->reader->bytes.size:0,cat.size,snap.size};
 for(unsigned i=0;i<10;i++)for(unsigned j=i+1;j<10;j++)if(!disjoint(p[i],n[i],p[j],n[j]))return COH_INVALID;
 if(old)for(unsigned i=0;i<8;i++)if(!safe_output(old,p[i],n[i]))return COH_INVALID;
 if(*out)return COH_STATE;
 TRY(poll(cancel));
 if(!generation||(old&&old->report.binding.generation==UINT32_MAX)||generation!=(old?old->report.binding.generation+1:1))return COH_STATE;
 if(old){const CohSceneProtocolBinding*b=&old->report.binding;if(gb.generation<b->graph_generation||cb.catalog_generation<b->catalog_generation||cb.asset_generation<b->asset_generation||sb.generation<b->snapshot_generation)return COH_STATE;
  if(cb.catalog_generation==b->catalog_generation&&(memcmp(cb.catalog_sha256,b->catalog_sha256,32)||memcmp(sb.snapshot_sha256,b->snapshot_sha256,32)||memcmp(cb.source_sha256,b->source_sha256,32)||memcmp(sb.run_sha256,b->run_sha256,32)||(b->groups_compatibility_checked&&!groups)))return COH_STATE;
  if(cb.asset_generation==b->asset_generation&&memcmp(cb.inventory_sha256,b->inventory_sha256,32))return COH_STATE;
 }
 size_t limit=budget->aggregate_limit,own=sizeof(CohSceneProtocol)+(size_t)metadata.graph.nodes*sizeof(CohSceneProtocolRecord),snap_owned=coh_catalog_snapshot_owned_bytes(snapshot),witness_owned=groups?coh_runtime_groups_witness_owned_bytes(groups->witness):0;
 if(!limit||limit>COH_SG_TRANSACTION_MAX||!budget->owned_limit||budget->owned_limit>COH_SG_MEMORY_MAX||own>budget->owned_limit||budget->retained_bytes>limit||snap_owned<snap.size)return COH_LIMIT;
 size_t deps=metadata.graph.owned_bytes+coh_catalog_owner_owned_bytes(catalog)+snap_owned+witness_owned;
 size_t prior_own=old?old->report.owned_bytes:0,prior_deps=old?old->report.dependencies_bytes:0,total=budget->retained_bytes;
 size_t add[]={own,deps,prior_own,prior_deps,groups?metadata.graph.nodes:0,groups?groups->reader->bytes.size:0,COH_SCENE_PROTOCOL_LOCAL_SCRATCH_BYTES,COH_GROUPS_WITNESS_FIXED_SCRATCH_BYTES,groups?sizeof(CohRuntimeGroupsReport):0};for(unsigned i=0;i<sizeof(add)/sizeof(add[0]);i++){if(add[i]>limit-total)return COH_LIMIT;total+=add[i];}
 CohSceneProtocol*t=calloc(1,sizeof(*t));if(!t)return COH_LIMIT;t->references=1;t->graph=g;t->expected_previous=old;t->catalog_bytes=cat;t->snapshot_bytes=snap;t->cancel=cancel;t->report.records=metadata.graph.nodes;t->report.owned_bytes=own;t->report.dependencies_bytes=deps;t->report.prior_owned_bytes=prior_own;t->report.prior_dependencies_bytes=prior_deps;t->report.aggregate_reserved_bytes=total;t->report.protocol_wire_inputs_complete=1;
 CohSceneProtocolBinding*b=&t->report.binding;b->generation=generation;b->graph_generation=gb.generation;b->catalog_generation=gb.catalog_generation;b->asset_generation=gb.pins.asset_generation;b->snapshot_generation=sb.generation;b->groups_compatibility_checked=groups!=NULL;memcpy(b->catalog_sha256,cb.catalog_sha256,32);memcpy(b->snapshot_sha256,sb.snapshot_sha256,32);memcpy(b->source_sha256,cb.source_sha256,32);memcpy(b->run_sha256,sb.run_sha256,32);memcpy(b->inventory_sha256,cb.inventory_sha256,32);if(groups)b->groups=*groups->binding;
 if(t->report.records){t->records=calloc(t->report.records,sizeof(*t->records));if(!t->records){coh_scene_protocol_release(t);return COH_LIMIT;}}
 CohStatus status=coh_catalog_owner_retain(catalog);if(status==COH_OK)t->catalog=catalog;if(status==COH_OK){status=coh_catalog_snapshot_retain(snapshot);if(status==COH_OK)t->snapshot=snapshot;}
 if(status==COH_OK&&groups){status=coh_runtime_groups_witness_retain(groups->witness);if(status==COH_OK)t->witness=groups->witness;}
 if(status==COH_OK&&groups){uint8_t*mask=t->report.records?malloc(t->report.records):NULL;if(t->report.records&&!mask)status=COH_LIMIT;else{CohRuntimeGroupsBudget staged={limit,budget->retained_bytes+prior_own+prior_deps+own+(snap_owned-snap.size)+COH_SCENE_PROTOCOL_LOCAL_SCRATCH_BYTES};CohCatalogSeedReport seed;status=coh_catalog_seed_visit(g,catalog,groups->witness,groups->binding,groups->reader,&staged,mask,t->report.records,capture,t,&seed);if(status==COH_OK&&seed.aggregate_reserved_bytes!=total)status=COH_STATE;}free(mask);}
 if(status==COH_OK&&!groups){for(uint32_t i=0;i<t->report.records;i++){CohRuntimeGraphNode node;status=coh_runtime_graph_node(g,i,&node);if(status!=COH_OK)break;CohCatalogSeedRecord r={i,node.file,node.slot,node.external,node.in_use,0,node.wire,node.wire_bits,node.aligned};status=capture(t,&r);if(status!=COH_OK)break;}}
 if(status==COH_OK)status=poll(cancel);
 if(status==COH_OK&&t->next!=t->report.records)status=COH_STATE;
 if(status!=COH_OK){coh_scene_protocol_release(t);return status;}t->cancel=NULL;*report=t->report;*out=t;return COH_OK;
}
CohStatus coh_scene_protocol_create_owned(const CohSceneProtocol*old,CohRuntimeGraphOwner*owner,const CohSceneProtocolGroups*groups,uint32_t generation,const CohSceneProtocolBudget*budget,const CohCancel*cancel,CohSceneProtocol**out,CohSceneProtocolReport*report){
 if(!owner||!budget||!out||!report)return COH_INVALID;
 if(groups&&(!groups->witness||!groups->binding||!groups->reader))return COH_INVALID;
 const CohRuntimeGraph*g;CohCatalogOwner*catalog;CohCatalogSnapshot*snapshot;CohRuntimeGraphOwnerReport gr;CohBytes cat,snap;
 TRY(coh_runtime_graph_owner_view(owner,&g,&catalog,&snapshot,&gr));TRY(coh_runtime_graph_sources(g,&cat,&snap));
 const void*p[]={budget,out,report,cancel,groups,groups?groups->binding:NULL,groups?groups->reader:NULL,groups?groups->reader->bytes.data:NULL,cat.data,snap.data,owner};
 size_t n[]={sizeof(*budget),sizeof(*out),sizeof(*report),cancel?sizeof(*cancel):0,groups?sizeof(*groups):0,groups?sizeof(*groups->binding):0,groups?sizeof(*groups->reader):0,groups?groups->reader->bytes.size:0,cat.size,snap.size,gr.owner_bytes};
 for(unsigned i=0;i<11;i++){if(i<8&&old&&!safe_output(old,p[i],n[i]))return COH_INVALID;for(unsigned j=i+1;j<11;j++)if(!disjoint(p[i],n[i],p[j],n[j]))return COH_INVALID;}
 if(*out)return COH_STATE;
 if(budget->retained_bytes>budget->aggregate_limit||gr.owner_bytes>budget->aggregate_limit-budget->retained_bytes)return COH_LIMIT;
 CohSceneProtocolBudget inner=*budget;inner.retained_bytes+=gr.owner_bytes;
 CohSceneProtocol*t=NULL;CohSceneProtocolReport r;
 CohStatus status=coh_scene_protocol_create(old,g,catalog,snapshot,groups,generation,&inner,cancel,&t,&r);if(status!=COH_OK)return status;
 status=coh_runtime_graph_owner_retain(owner);if(status!=COH_OK){coh_scene_protocol_release(t);return status;}
 t->graph_owner=owner;t->report.dependencies_bytes+=gr.owner_bytes;t->report.owned_graph_lease=1;
 *report=t->report;*out=t;return COH_OK;
}
static int safe_output(const CohSceneProtocol*t,const void*p,size_t n){return disjoint(p,n,t,sizeof(*t))&&disjoint(p,n,t->records,(size_t)t->report.records*sizeof(*t->records))&&disjoint(p,n,t->catalog_bytes.data,t->catalog_bytes.size)&&disjoint(p,n,t->snapshot_bytes.data,t->snapshot_bytes.size);}
CohStatus coh_scene_protocol_report(const CohSceneProtocol*t,CohSceneProtocolReport*out){if(!t||!out)return COH_INVALID;if(!safe_output(t,out,sizeof(*out)))return COH_INVALID;*out=t->report;return COH_OK;}
CohStatus coh_scene_protocol_record(const CohSceneProtocol*t,uint32_t i,CohSceneProtocolRecord*out){if(!t||!out)return COH_INVALID;if(!safe_output(t,out,sizeof(*out)))return COH_INVALID;if(i>=t->report.records)return COH_NOT_FOUND;*out=t->records[i];return COH_OK;}
CohStatus coh_scene_protocol_slot(const CohSceneProtocol*t,uint32_t f,uint32_t slot,CohSceneProtocolRecord*out){if(!t||!out)return COH_INVALID;if(!safe_output(t,out,sizeof(*out)))return COH_INVALID;uint32_t i;TRY(coh_runtime_graph_slot(t->graph,f,slot,&i));if(i>=t->report.records||t->records[i].source.external||t->records[i].source.file!=f||t->records[i].source.slot!=slot)return COH_STATE;*out=t->records[i];return COH_OK;}
CohStatus coh_scene_protocol_graph(const CohSceneProtocol*t,const CohRuntimeGraph**out){if(!t||!out)return COH_INVALID;if(!safe_output(t,out,sizeof(*out)))return COH_INVALID;*out=t->graph;return COH_OK;}
CohStatus coh_scene_protocol_publish(CohSceneProtocol**current,CohSceneProtocol**candidate,CohSceneProtocol**retired){
 if(!current||!candidate||!retired||!disjoint(current,sizeof(*current),candidate,sizeof(*candidate))||!disjoint(current,sizeof(*current),retired,sizeof(*retired))||!disjoint(candidate,sizeof(*candidate),retired,sizeof(*retired)))return COH_INVALID;
 CohSceneProtocol*t=*candidate;if(!t)return COH_STATE;
 if(!safe_output(t,current,sizeof(*current))||!safe_output(t,candidate,sizeof(*candidate))||!safe_output(t,retired,sizeof(*retired)))return COH_INVALID;
 if(*current&&(!safe_output(*current,current,sizeof(*current))||!safe_output(*current,candidate,sizeof(*candidate))||!safe_output(*current,retired,sizeof(*retired))))return COH_INVALID;
 if(*retired||t==*current||t->expected_previous!=*current||t->report.binding.generation!=(*current?(*current)->report.binding.generation+1:1))return COH_STATE;
 *retired=*current;*current=t;*candidate=NULL;return COH_OK;
}
