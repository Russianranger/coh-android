#include "coh_power_ids.h"
#include <string.h>
typedef struct {const void*p;size_t n;}Span;
static int valid(Span s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:!s.n;}
static int overlap(Span a,Span b){return a.n&&b.n&&(uintptr_t)a.p<(uintptr_t)b.p+b.n&&(uintptr_t)b.p<(uintptr_t)a.p+a.n;}
static CohStatus charge(size_t*used,size_t n,size_t budget){if(*used>budget||n>budget-*used)return COH_LIMIT;*used+=n;return COH_OK;}
static CohStatus category_name(const CohPowerCategoryDictionary*c,uint32_t row,CohBytes*out){if(row>=c->count)return COH_STATE;CohOriginText span=c->entries[row].fields[1];if(span.offset>c->text_bytes||span.size>c->text_bytes-span.offset||span.size>=260)return COH_STATE;*out=(CohBytes){(const uint8_t*)c->text+span.offset,span.size};for(size_t i=0;i<out->size;i++)if(!out->data[i]||out->data[i]>127)return COH_UNSUPPORTED;return COH_OK;}
static CohStatus compare(const CohPowerCategoryDictionary*c,uint32_t a,uint32_t b,int*order,size_t*work){/* Precharge both full ASCII scans, comparison bytes and control. */if(3u*260u>*work)return COH_LIMIT;*work-=3u*260u;CohBytes x,y;CohStatus status=category_name(c,a,&x);if(status!=COH_OK)return status;status=category_name(c,b,&y);if(status!=COH_OK)return status;size_t n=x.size<y.size?x.size:y.size;int value=memcmp(x.data,y.data,n);*order=value?value:(x.size>y.size)-(x.size<y.size);return COH_OK;}
CohStatus coh_power_ids_prepare(const CohPowerJoin*j,CohPowerIDs*out,CohPowerIDsWorkspace*w,size_t budget,size_t retained){
 if(!j||!out||!w||!budget||budget>COH_POWER_IDS_RAM_MAX)return COH_INVALID;
 if(!j->categories||!j->sets||!j->powers)return COH_STATE;
 const CohPowerCategoryDictionary*c=j->categories;const CohPowerSetDictionary*s=j->sets;const CohPowerStreamDictionary*p=j->powers;
 Span spans[]={{j,sizeof(*j)},{c,sizeof(*c)},{s,sizeof(*s)},{p,sizeof(*p)},{s->input.data,s->input.size},{p->provider.context,p->provider.context_bytes},{out,sizeof(*out)},{w,sizeof(*w)}};size_t used=COH_POWER_IDS_STACK_RESERVE;
 for(unsigned i=0;i<sizeof(spans)/sizeof(spans[0]);i++){if(!valid(spans[i]))return COH_INVALID;for(unsigned k=0;k<i;k++)if(overlap(spans[i],spans[k]))return COH_INVALID;CohStatus status=charge(&used,spans[i].n,budget);if(status!=COH_OK)return status;}
 CohStatus status=charge(&used,p->provider.scratch_reserve,budget);if(status!=COH_OK)return status;status=charge(&used,retained,budget);if(status!=COH_OK)return status;
 if(!j->complete_forward_join||!j->parent_projection||j->category_count!=c->count||j->set_count!=s->count||j->power_count!=p->count||c->count>COH_CATEGORY_MAX||c->text_bytes>COH_CATEGORY_TEXT_MAX||s->count>COH_POWER_SET_MAX||p->count>COH_POWER_STREAM_RECORD_MAX||j->category_reference_count!=c->set_count||c->set_count>COH_CATEGORY_REFS_MAX||j->power_reference_count>COH_POWER_JOIN_REF_MAX||!c->raw_schema_validated||!c->source_lease||!s->raw_schema_validated||!s->input_lease||!s->input.data||s->input.size>COH_POWER_SET_INPUT_MAX||!p->raw_schema_validated||!p->provider.lease||!p->provider.context||!p->provider.context_bytes)return COH_STATE;
 size_t work=COH_POWER_IDS_WORK_MAX;uint32_t next=0;
 for(uint32_t ci=0;ci<c->count;ci++){const CohPowerCategoryEntry*cat=&c->entries[ci];CohBytes name;status=category_name(c,ci,&name);if(status!=COH_OK)return status;if(name.size>work)return COH_LIMIT;work-=name.size;if(cat->set_first!=next||cat->set_count>c->set_count-next)return COH_STATE;next+=cat->set_count;}
 if(next!=c->set_count)return COH_STATE;
 /* Validate and precharge BOTH source assignment passes before touching scratch. */
 for(uint32_t ri=0;ri<j->category_reference_count;ri++){uint32_t row=j->category_sets[ri];if(row>=s->count)return COH_STATE;const CohPowerJoinSet*set=&j->set_links[row];if(set->first>j->power_reference_count||set->count>j->power_reference_count-set->first)return COH_STATE;size_t cost=((size_t)set->count+1)*4;if(cost>work)return COH_LIMIT;work-=cost;for(uint32_t pi=0;pi<set->count;pi++)if(j->power_links[set->first+pi].resolved_power>=p->count)return COH_STATE;}
 CohPowerIDs*candidate=&w->candidate;memset(candidate,0,sizeof(*candidate));candidate->join=j;candidate->category_count=c->count;candidate->set_count=s->count;candidate->power_count=p->count;
 for(uint32_t i=0;i<COH_POWER_SET_MAX;i++)candidate->set_parent_categories[i]=COH_POWER_JOIN_NONE;
 for(uint32_t i=0;i<COH_POWER_STREAM_RECORD_MAX;i++)candidate->power_parent_sets[i]=COH_POWER_JOIN_NONE;
 /* Unique admitted category names make equal comparator keys impossible; stable
  * bounded insertion order therefore agrees with source qsort's unique order. */
 for(uint32_t i=0;i<c->count;i++){uint32_t at=i;while(at){int order;status=compare(c,candidate->sorted_categories[at-1],i,&order,&work);if(status!=COH_OK)return status;if(!order)return COH_STATE;if(order<0)break;candidate->sorted_categories[at]=candidate->sorted_categories[at-1];at--;}candidate->sorted_categories[at]=i;}
 for(uint32_t ci=0;ci<c->count;ci++){const CohPowerCategoryEntry*cat=&c->entries[candidate->sorted_categories[ci]];for(uint32_t si=0;si<cat->set_count;si++){uint32_t row=j->category_sets[cat->set_first+si];const CohPowerJoinSet*set=&j->set_links[row];for(uint32_t pi=0;pi<set->count;pi++){uint32_t power=j->power_links[set->first+pi].resolved_power;CohPowerRuntimeID*id=&candidate->ids[power];if(!id->assigned)candidate->assigned_power_count++;*id=(CohPowerRuntimeID){ci,si,pi,1};}}}
 for(uint32_t ci=c->count;ci>0;ci--){const CohPowerCategoryEntry*cat=&c->entries[candidate->sorted_categories[ci-1]];for(uint32_t si=cat->set_count;si>0;si--){uint32_t row=j->category_sets[cat->set_first+si-1];const CohPowerJoinSet*set=&j->set_links[row];candidate->set_parent_categories[row]=ci-1;for(uint32_t pi=set->count;pi>0;pi--)candidate->power_parent_sets[j->power_links[set->first+pi-1].resolved_power]=row;}}
 candidate->source_id_projection=1;*out=*candidate;return COH_OK;
}
CohStatus coh_power_ids_find(const CohPowerIDs*d,uint32_t category,uint32_t set,uint32_t power,uint32_t*out){
 if(!d||!out)return COH_INVALID;
 if(!valid((Span){d,sizeof(*d)})||!valid((Span){out,sizeof(*out)})||overlap((Span){d,sizeof(*d)},(Span){out,sizeof(*out)}))return COH_INVALID;
 const CohPowerJoin*j=d->join;if(!d->source_id_projection||!j||!j->categories||!j->sets||!j->powers||d->category_count>COH_CATEGORY_MAX||d->set_count>COH_POWER_SET_MAX||d->power_count>COH_POWER_STREAM_RECORD_MAX||!j->complete_forward_join||j->category_count!=d->category_count||j->set_count!=d->set_count||j->power_count!=d->power_count||j->category_reference_count>COH_CATEGORY_REFS_MAX||j->power_reference_count>COH_POWER_JOIN_REF_MAX||j->categories->count>COH_CATEGORY_MAX)return COH_STATE;
 Span immutable[]={{j,sizeof(*j)},{j->categories,sizeof(*j->categories)},{j->sets,sizeof(*j->sets)},{j->powers,sizeof(*j->powers)},{j->sets->input.data,j->sets->input.size},{j->powers->provider.context,j->powers->provider.context_bytes}};
 for(unsigned i=0;i<sizeof(immutable)/sizeof(immutable[0]);i++)if(!valid(immutable[i])||overlap(immutable[i],(Span){out,sizeof(*out)}))return COH_INVALID;
 if(category>=d->category_count)return COH_NOT_FOUND;
 uint32_t raw=d->sorted_categories[category];if(raw>=j->categories->count)return COH_STATE;const CohPowerCategoryEntry*cat=&j->categories->entries[raw];if(set>=cat->set_count)return COH_NOT_FOUND;if(cat->set_first>j->category_reference_count||set>=j->category_reference_count-cat->set_first)return COH_STATE;uint32_t row=j->category_sets[cat->set_first+set];if(row>=d->set_count)return COH_STATE;const CohPowerJoinSet*link=&j->set_links[row];if(power>=link->count)return COH_NOT_FOUND;if(link->first>j->power_reference_count||power>=j->power_reference_count-link->first)return COH_STATE;uint32_t resolved=j->power_links[link->first+power].resolved_power;if(resolved>=d->power_count)return COH_STATE;*out=resolved;return COH_OK;
}
