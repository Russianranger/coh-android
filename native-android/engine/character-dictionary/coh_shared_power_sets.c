#include "coh_shared_power_sets.h"
#include <string.h>
typedef struct{const void*p;size_t n;}Span;
static int valid(Span s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:!s.n;}
static int overlap(Span a,Span b){return a.n&&b.n&&(uintptr_t)a.p<(uintptr_t)b.p+b.n&&(uintptr_t)b.p<(uintptr_t)a.p+a.n;}
static CohStatus charge(size_t*used,size_t n,size_t budget){if(*used>budget||n>budget-*used)return COH_LIMIT;*used+=n;return COH_OK;}
CohStatus coh_shared_power_sets_prepare(const CohPowerIDs*ids,const CohSharedPowerSets*prior,CohSharedPowerSets*out,CohSharedPowerSetsWorkspace*w,size_t budget,size_t retained){
 if(!ids||!out||!w||!budget||budget>COH_SHARED_SETS_RAM_MAX)return COH_INVALID;
 const CohPowerJoin*j=ids->join;if(!j||!j->categories||!j->sets||!j->powers)return COH_STATE;
 const CohPowerCategoryDictionary*c=j->categories;const CohPowerSetDictionary*s=j->sets;const CohPowerStreamDictionary*p=j->powers;
 Span spans[]={{ids,sizeof(*ids)},{j,sizeof(*j)},{c,sizeof(*c)},{s,sizeof(*s)},{p,sizeof(*p)},{s->input.data,s->input.size},{p->provider.context,p->provider.context_bytes},{prior,prior?sizeof(*prior):0},{out,sizeof(*out)},{w,sizeof(*w)}};size_t used=COH_SHARED_SETS_STACK_RESERVE;
 for(unsigned i=0;i<sizeof(spans)/sizeof(spans[0]);i++){if(!valid(spans[i]))return COH_INVALID;for(unsigned k=0;k<i;k++)if(overlap(spans[i],spans[k]))return COH_INVALID;CohStatus status=charge(&used,spans[i].n,budget);if(status!=COH_OK)return status;}
 CohStatus status=charge(&used,p->provider.scratch_reserve,budget);if(status!=COH_OK)return status;status=charge(&used,retained,budget);if(status!=COH_OK)return status;
 if(!ids->source_id_projection||!j->complete_forward_join||ids->category_count!=j->category_count||ids->set_count!=j->set_count||ids->power_count!=j->power_count||ids->category_count!=c->count||ids->set_count!=s->count||ids->power_count!=p->count||c->count>COH_CATEGORY_MAX||s->count>COH_POWER_SET_MAX||p->count>COH_POWER_STREAM_RECORD_MAX||j->category_reference_count!=c->set_count||c->set_count>COH_CATEGORY_REFS_MAX||!c->raw_schema_validated||!c->source_lease||!s->raw_schema_validated||!s->input_lease||!s->input.data||s->input.size>COH_POWER_SET_INPUT_MAX||!p->raw_schema_validated||!p->provider.lease||!p->provider.context||!p->provider.context_bytes)return COH_STATE;
 if(prior&&(!prior->source_layout_projection||prior->ids!=ids||prior->count>COH_SHARED_SETS_MAX||prior->source_calls==0))return COH_STATE;
 if(prior&&prior->source_calls==UINT32_MAX)return COH_LIMIT;
 /* Any retained list must remain a prefix of this same source traversal. This
  * rejects forged/unreachable rows instead of trusting count/flags from prior. */
 uint32_t selected[COH_CATEGORY_MAX/32]={0};size_t work=COH_SHARED_SETS_WORK_MAX;uint32_t expected_refs=0;
 for(uint32_t ci=0;ci<c->count;ci++){
  uint32_t raw=ids->sorted_categories[ci];if(raw>=c->count||selected[raw/32]&(UINT32_C(1)<<(raw%32)))return COH_STATE;selected[raw/32]|=UINT32_C(1)<<(raw%32);
  const CohPowerCategoryEntry*cat=&c->entries[raw];if(cat->set_first>j->category_reference_count||cat->set_count>j->category_reference_count-cat->set_first)return COH_STATE;if(cat->set_count>j->category_reference_count-expected_refs)return COH_STATE;expected_refs+=cat->set_count;
 }
 if(expected_refs!=j->category_reference_count)return COH_STATE;
 CohSharedPowerSets*candidate=&w->candidate;memset(candidate,0,sizeof(*candidate));candidate->ids=ids;candidate->initial_from_empty=prior==NULL;candidate->source_calls=prior?prior->source_calls+1:1;
 for(uint32_t ci=0;ci<c->count;ci++){
  const CohPowerCategoryEntry*cat=&c->entries[ids->sorted_categories[ci]];
  for(uint32_t si=0;si<cat->set_count;si++){
   if(work<1024)return COH_LIMIT;
   work-=1024;/* All four preceding bounded text/scalar fields + getter control. */
   uint32_t row=j->category_sets[cat->set_first+si];if(row>=s->count)return COH_STATE;CohBytes field;status=coh_power_sets_field(s,row,4,&field);if(status!=COH_OK)return status;if(field.size!=4)return COH_STATE;
   /* Original u8_readbin casts the persisted U32 to U8 before bool storage. */
   if(field.data[0]){if(candidate->appended_count==COH_SHARED_SETS_MAX)return COH_LIMIT;candidate->sets[candidate->appended_count++]=row;}
  }
 }
 uint32_t added=candidate->appended_count;
 if(prior){
  if(prior->appended_count!=added)return COH_STATE;
  if(added){if(prior->source_calls>COH_SHARED_SETS_MAX/added||prior->count!=prior->source_calls*added)return COH_STATE;for(uint32_t i=0;i<prior->count;i++){if(!work)return COH_LIMIT;work--;if(prior->sets[i]!=candidate->sets[i%added])return COH_STATE;}}
  else if(prior->count)return COH_STATE;
  if(added>COH_SHARED_SETS_MAX-prior->count)return COH_LIMIT;
  memmove(candidate->sets+prior->count,candidate->sets,(size_t)added*sizeof(*candidate->sets));memcpy(candidate->sets,prior->sets,(size_t)prior->count*sizeof(*candidate->sets));candidate->count=prior->count+added;
 }else candidate->count=added;
 candidate->source_layout_projection=1;*out=*candidate;return COH_OK;
}
