#include "coh_initial_costume_slots_probe.h"
#include <stdio.h>
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
 return x<y+bn&&y<x+an;
}
static CohStatus finish(CohInitialCostumeSlotsProbe*out,CohInitialCostumeSlotsProbe*d,
 CohStatus status,size_t bit){d->status=status;d->failure_bit=bit;*out=*d;return status;}
static CohStatus scalar(CohRepReader*r,unsigned width,uint32_t*out){
 uint32_t value=0;CohStatus status=coh_rep_read(r,width,&value);
 if(status!=COH_OK)return status;
 if(value>=(UINT32_C(1)<<width))return COH_INVALID;
 *out=value;return COH_OK;
}
CohStatus coh_initial_costume_slots_probe(const CohRepReader*input,CohInitialCostumeSlotsProbe*out){
 if(!input||!out||overlap(input,sizeof(*input),out,sizeof(*out)))return COH_INVALID;
 CohRepReader r=*input;uint32_t value=0;
 if(coh_rep_read(&r,0,&value)!=COH_OK||r.bytes.size>COH_REP_BOUNDED_MESSAGE_MAX||
    overlap(r.bytes.data,r.bytes.size,input,sizeof(*input))||
    overlap(r.bytes.data,r.bytes.size,out,sizeof(*out)))return COH_INVALID;
 CohInitialCostumeSlotsProbe d;memset(&d,0,sizeof(d));d.begin_bit=r.cursor;
 d.stage=COH_INITIAL_COSTUME_SLOTS_DEFERRED;CohStatus status=scalar(&r,1,&d.deferred);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 d.stage=COH_INITIAL_COSTUME_SLOTS_CURRENT;status=scalar(&r,8,&d.current);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 if(d.current>=COH_COSTUME_STORED_MAX)return finish(out,&d,COH_LIMIT,r.cursor);
 d.stage=COH_INITIAL_COSTUME_SLOTS_ADDITIONAL;status=scalar(&r,8,&d.additional);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 d.stage=COH_INITIAL_COSTUME_SLOTS_MULTIPLE;status=scalar(&r,1,&d.multiple);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 if(!d.multiple)return finish(out,&d,COH_UNSUPPORTED,r.cursor);
 d.stage=COH_INITIAL_COSTUME_SLOTS_COUNT;status=scalar(&r,4,&d.body_count);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 if(!d.body_count||d.body_count>COH_COSTUME_STORED_MAX||d.current>=d.body_count)
  return finish(out,&d,COH_LIMIT,r.cursor);
 d.stage=COH_INITIAL_COSTUME_SLOTS_BODY;d.end_bit=r.cursor;d.framing_validated=1;
 return finish(out,&d,r.cursor<r.bits?COH_UNSUPPORTED:COH_INVALID,r.cursor);
}
static int valid(const CohInitialCostumeSlotsProbe*d){
 return (d->status==COH_INVALID||d->status==COH_UNSUPPORTED||d->status==COH_LIMIT)&&
  d->stage>=COH_INITIAL_COSTUME_SLOTS_DEFERRED&&d->stage<=COH_INITIAL_COSTUME_SLOTS_BODY&&
  d->begin_bit<=COH_REP_BOUNDED_MESSAGE_MAX*8u&&d->failure_bit>=d->begin_bit&&
  d->failure_bit<=COH_REP_BOUNDED_MESSAGE_MAX*8u&&
  d->failure_bit-d->begin_bit<=40u&&d->deferred<=1&&d->current<=255&&d->additional<=255&&
  d->multiple<=1&&d->body_count<=15&&d->framing_validated<=1;
}
static uint32_t metadata(const CohInitialCostumeSlotsProbe*d){
 return d->deferred|(d->current<<1)|(d->additional<<9)|(d->multiple<<17)|
  (d->body_count<<18)|(d->framing_validated<<22);
}
int coh_initial_costume_slots_probe_json(const CohInitialCostumeSlotsProbe*d,char*out,size_t bytes){
 if(!d||!out||!bytes||overlap(d,sizeof(*d),out,bytes))return -1;
 if(!d->stage)return snprintf(out,bytes,"null");
 if(!valid(d))return -1;
 return snprintf(out,bytes,"[%u,%u,%llu,%llu,%u]",(unsigned)d->status,(unsigned)d->stage,
  (unsigned long long)d->begin_bit,(unsigned long long)(d->failure_bit-d->begin_bit),metadata(d));
}
int coh_initial_costume_slots_progress_json(const CohInitialRewardListProbe*l,
 const CohInitialCostumeSlotsProbe*d,char*out,size_t bytes){
 if(!l||!d||!out||!bytes||overlap(l,sizeof(*l),out,bytes)||overlap(d,sizeof(*d),out,bytes)||
    !valid(d)||!l->list_validated||l->stage!=COH_INITIAL_REWARD_LIST_SLOTS||
    l->end_bit!=d->begin_bit||l->entries[0]>COH_COSTUME_REWARDS_MAX||l->entries[1]>COH_COSTUME_REWARDS_MAX||
    l->entries[0]!=l->counts[0]||l->entries[1]!=l->counts[1])return -1;
 return snprintf(out,bytes,"[%u,%u,%u,%u,%llu,%llu,%u]",(unsigned)d->status,6u+(unsigned)d->stage,
  l->entries[0],l->entries[1],(unsigned long long)l->end_bit,
  (unsigned long long)(d->failure_bit-d->begin_bit),metadata(d));
}
