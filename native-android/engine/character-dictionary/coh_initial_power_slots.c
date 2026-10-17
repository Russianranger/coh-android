#include "coh_initial_power_slots.h"
#include <string.h>
typedef struct{const void*p;size_t n;}Span;
static int valid(Span s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:!s.n;}
static int overlap(Span a,Span b){return a.n&&b.n&&(uintptr_t)a.p<(uintptr_t)b.p+b.n&&(uintptr_t)b.p<(uintptr_t)a.p+a.n;}
static CohStatus charge(size_t*used,size_t n,size_t cap){if(*used>cap||n>cap-*used)return COH_LIMIT;*used+=n;return COH_OK;}
CohStatus coh_initial_power_slots_create(const CohPowerStreamDictionary*d,const CohSchedules*s,uint32_t row,int32_t level,int32_t bought,uint32_t wire,CohInitialPowerSlots*out,CohInitialPowerSlotsWorkspace*w,size_t budget,size_t retained){
 if(!d||!s||!out||!w||!budget||budget>COH_INITIAL_POWER_SLOTS_RAM_MAX)return COH_INVALID;
 Span spans[]={{d,sizeof(*d)},{s,sizeof(*s)},{d->provider.context,d->provider.context_bytes},{out,sizeof(*out)},{w,sizeof(*w)}};
 size_t used=COH_INITIAL_POWER_SLOTS_STACK_RESERVE+COH_POWER_SLOT_STACK_RESERVE;
 for(unsigned i=0;i<5;i++){if(!valid(spans[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(overlap(spans[i],spans[j]))return COH_INVALID;CohStatus status=charge(&used,spans[i].n,budget);if(status!=COH_OK)return status;}
 CohStatus status=charge(&used,d->provider.scratch_reserve,budget);if(status!=COH_OK)return status;status=charge(&used,retained,budget);if(status!=COH_OK)return status;
 /* Nested importer charges source/context, its output/record and its own stack.
  * Add every outer live byte to its retained admission without double-counting
  * the two subobjects already inside our workspace. The outer preflight above
  * proves this addition fits the literal module cap before any callback. */
 size_t nested=retained+sizeof(*out)+sizeof(*w)-sizeof(w->candidate.source)-sizeof(w->record)+COH_INITIAL_POWER_SLOTS_STACK_RESERVE;
 memset(&w->candidate,0,sizeof(w->candidate));
 status=coh_power_boost_slots_prepare(d,s,row,level,bought,wire,&w->candidate.source,&w->record,budget,nested);if(status!=COH_OK)return status;
 CohInitialPowerSlots*c=&w->candidate;int64_t target=(int64_t)c->source.boosts_bought+c->source.free_schedule_count;
 /* Source adds signed int before MIN and before BoostsAllowed gating. Refuse
  * overflow even if a later cap or empty eligibility array would hide it. */
 if(target<INT32_MIN||target>INT32_MAX)return COH_UNSUPPORTED;
 if(target>c->source.max_boosts)target=c->source.max_boosts;
 c->level_finalize_target=(int32_t)target;
 if(c->source.boosts_allowed_count&&target>0){if((uint64_t)target>COH_INITIAL_POWER_SLOTS_MAX)return COH_LIMIT;c->slot_count=(uint32_t)target;}
 for(uint32_t i=0;i<c->slot_count;i++)c->slots[i]=COH_INITIAL_POWER_SLOT_EMPTY;
 c->fresh_slot_constructor=c->historical_state_projection=1;
 if(d->provider.cancelled&&d->provider.cancelled(d->provider.context))return COH_CANCELLED;
 *out=*c;return COH_OK;
}
