#include "coh_source_placement.h"
#include <math.h>
#include <string.h>
#define RESERVE (16u*1024u)
#define TRY(x) do{CohStatus s_=(x);if(s_!=COH_OK)return s_;}while(0)
static int separate(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return (!an||a)&&(!bn||b)&&an<=UINTPTR_MAX-x&&bn<=UINTPTR_MAX-y&&(x+an<=y||y+bn<=x);}
static CohStatus add(size_t*n,size_t v,size_t limit){if(*n>limit||v>limit-*n)return COH_LIMIT;*n+=v;return COH_OK;}
CohStatus coh_source_placement_prepare(const CohSourceSealed*s,const CohRuntimeCandidates*c,
 const CohRuntimeCandidate*input,const CohSourcePlacementBudget*b,CohSourcePlacement*out){
 if(!s||!c||!input||!b||!out)return COH_INVALID;
 const void*p[]={input,b,out};size_t sizes[]={sizeof(*input),sizeof(*b),sizeof(*out)};
 for(unsigned i=0;i<3;i++)for(unsigned j=i+1;j<3;j++)if(!separate(p[i],sizes[i],p[j],sizes[j]))return COH_INVALID;
 CohSourceSealedReport sr;CohSourceSealedIdentity sid;CohRuntimeCandidateIdentity cid;CohRuntimeCandidateOwnerReport cr;
 TRY(coh_source_sealed_report(s,&sr));TRY(coh_source_sealed_identity(s,&sid));TRY(coh_runtime_candidates_identity(c,&cid));TRY(coh_runtime_candidates_report(c,&cr));
 CohBytes spans[]={sid.join.catalog_bytes,sid.join.snapshot_bytes,sid.join.resource_bytes};
 for(unsigned i=0;i<3;i++){
  if(!separate(s,sr.owned_bytes,p[i],sizes[i]))return COH_INVALID;
  TRY(coh_runtime_candidates_check_span(c,p[i],sizes[i]));
  for(unsigned j=0;j<3;j++)if(!separate(spans[j].data,spans[j].size,p[i],sizes[i]))return COH_INVALID;
 }
 if(sid.join_identity!=cid.join_identity||sid.join.catalog_identity!=cid.join.catalog_identity||sid.join.snapshot_identity!=cid.join.snapshot_identity||sid.join.graph_identity!=cid.join.graph_identity||sid.join.catalog_bytes.data!=cid.join.catalog_bytes.data||sid.join.snapshot_bytes.data!=cid.join.snapshot_bytes.data||sid.join.resource_bytes.data!=cid.join.resource_bytes.data)return COH_STATE;
 if(!b->aggregate_limit||b->aggregate_limit>COH_SG_TRANSACTION_MAX)return COH_LIMIT;
 size_t total=b->retained_bytes;TRY(add(&total,sr.owned_bytes,b->aggregate_limit));TRY(add(&total,sr.shared_source_bytes,b->aggregate_limit));TRY(add(&total,cr.owned_bytes,b->aggregate_limit));TRY(add(&total,sizeof(*input),b->aggregate_limit));TRY(add(&total,sizeof(*b),b->aggregate_limit));TRY(add(&total,sizeof(*out),b->aggregate_limit));TRY(add(&total,RESERVE,b->aggregate_limit));
 CohRuntimeGraphRoot root;CohRuntimeGraphNode node;
 /* Indexed root access avoids copying the full 64-entry graph diagnostic. */
 TRY(coh_runtime_graph_root((const CohRuntimeGraph*)cid.join.graph_identity,input->instance.root_slot,&root));
 if(!root.active)return COH_STATE;
 if(input->instance.graph_generation!=cr.graph_generation||input->source_model_present!=input->instance.model_present||input->source_model_present>1||input->instance.external>1||input->instance.depth>COH_SG_DEPTH_MAX||((input->instance.depth==0)!=(input->instance.parent_ordinal==UINT64_MAX))||(input->instance.depth&&input->instance.parent_ordinal>=input->instance.ordinal))return COH_STATE;
 for(unsigned i=0;i<4;i++)for(unsigned j=0;j<3;j++)if(!isfinite(input->instance.world[i][j]))return COH_STATE;
 if(!input->instance.depth&&(input->instance.node!=root.node||memcmp(input->instance.world,root.matrix,sizeof(root.matrix))))return COH_STATE;
 uint32_t ordinal;TRY(coh_runtime_candidates_node(c,input->instance.node,&ordinal));if(ordinal!=input->source_ordinal)return COH_STATE;
 TRY(coh_runtime_graph_node((const CohRuntimeGraph*)cid.join.graph_identity,input->instance.node,&node));
 if(node.source_model_present!=input->instance.model_present||node.external!=input->instance.external)return COH_STATE;
 CohResourceSource source;TRY(coh_runtime_candidates_source(c,ordinal,&source));if(memcmp(input->source_record_sha256,source.sha256,32))return COH_STATE;
 CohResourceView view;TRY(coh_resource_source_view(source.record,sid.join.pins.resource.asset_generation,&view));if(view.model_present!=input->source_model_present)return COH_STATE;
 uint32_t required=COH_CANDIDATE_CLIENT_UNKNOWN_MASK|(input->source_model_present?COH_CANDIDATE_SOURCE_BODY:0)|(input->has_source_bounds?0:COH_CANDIDATE_SOURCE_BOUNDS);
 if(input->unresolved!=required||input->has_source_bounds>1)return COH_STATE;
 if(input->has_source_bounds){
  if(input->bounds_result!=COH_RB_COMPUTED&&input->bounds_result!=COH_RB_CAPTURED_FUTURE)return COH_STATE;
  for(unsigned i=0;i<3;i++)if(!isfinite(input->local_source_bounds.min[i])||!isfinite(input->local_source_bounds.max[i])||!isfinite(input->local_source_bounds.mid[i])||input->local_source_bounds.min[i]>input->local_source_bounds.max[i])return COH_STATE;
  if(!isfinite(input->local_source_bounds.radius)||input->local_source_bounds.radius<0)return COH_STATE;
 }
 CohSourcePlacement value={0};value.candidate=*input;value.unresolved=input->unresolved;value.sealed_slot=UINT32_MAX;value.preparation_reserve=RESERVE;value.aggregate_reserved_bytes=total;
 if(!input->source_model_present)value.result=COH_SOURCE_PLACEMENT_NO_MODEL;
 else {
  uint32_t slot;CohStatus status=coh_source_sealed_find(s,ordinal,&slot);
  if(status==COH_NOT_FOUND)value.result=COH_SOURCE_PLACEMENT_NOT_PREPARED;
  else {
   if(status!=COH_OK)return status;
   CohSourceSealedEntry entry;TRY(coh_source_sealed_entry(s,slot,&entry));
   if(entry.source_ordinal!=ordinal||entry.graph_node!=input->instance.node||entry.graph_generation!=cr.graph_generation||entry.catalog_generation!=cr.catalog_generation||entry.resource_record.size!=source.record.size||memcmp(entry.resource_record_sha256,source.sha256,32)||memcmp(entry.resource_record.data,source.record.data,source.record.size)||!entry.parts||!entry.vertices||!entry.triangles||!entry.unscaled_base_uv||!entry.material_binding_required)return COH_STATE;
   value.result=COH_SOURCE_PLACEMENT_GEOMETRY;value.geometry=entry;value.sealed_slot=slot;value.source_geometry_available=1;value.unresolved&=~COH_CANDIDATE_SOURCE_BODY;
  }
 }
 *out=value;return COH_OK;
}
