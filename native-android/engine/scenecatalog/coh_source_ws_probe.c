#include "coh_source_ws_probe.h"
static int separate(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return (!an||a)&&(!bn||b)&&an<=UINTPTR_MAX-x&&bn<=UINTPTR_MAX-y&&(x+an<=y||y+bn<=x);}
#define TRY(x) do{CohStatus s_=(x);if(s_!=COH_OK)return s_;}while(0)
CohStatus coh_source_ws_probe(const CohWorkingSet*parent,const CohSourceMeshBatch*batch,const CohSourceSealedBudget*budget,CohSourceWsProbe*out){
 if(!parent||!batch||!budget||!out)return COH_INVALID;
 if(!separate(budget,sizeof(*budget),out,sizeof(*out))||!separate(parent,1,out,sizeof(*out)))return COH_INVALID;
 CohSourceMeshBatchReport r;TRY(coh_source_mesh_batch_report(batch,&r));if(!separate(batch,r.owned_bytes,out,sizeof(*out)))return COH_INVALID;
 for(uint32_t n=0;n<r.meshes;n++){CohSourceMeshDependencies d;CohSourceMeshReport m;uint32_t first;TRY(coh_source_mesh_batch_dependencies(batch,n,&d));TRY(coh_source_mesh_batch_entry(batch,n,&m,&first));CohBytes spans[]={d.mesh_storage,d.body.join.catalog_bytes,d.body.join.snapshot_bytes,d.body.join.resource_bytes,m.source.actual_sources.record,m.source.actual_sources.header,m.source.actual_sources.blob};for(unsigned k=0;k<7;k++)if(!separate(out,sizeof(*out),spans[k].data,spans[k].size))return COH_INVALID;}
 CohSourceWsProbe value={0};TRY(coh_ws_report(parent,&value.parent));CohSourceSealedBudget full=*budget;
 if(value.parent.booked>full.aggregate_limit||full.retained_bytes>full.aggregate_limit-value.parent.booked)return COH_LIMIT;
 full.retained_bytes+=value.parent.booked;TRY(coh_source_sealed_measure(batch,&full,&value.source));
 value.parent_booked_added_to_retained=value.parent.booked;
 value.candidate_copy_only=(CohWsPlan){value.source.prepared.owned_bytes,0,value.source.prepared.preparation_reserve,budget->aggregate_limit};
 *out=value;return COH_OK;
}
