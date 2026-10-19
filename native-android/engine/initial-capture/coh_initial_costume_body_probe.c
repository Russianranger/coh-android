#include "coh_initial_costume_body_probe.h"
#include <stdio.h>
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
 return x<y+bn&&y<x+an;
}
static CohStatus finish(CohInitialCostumeBodyProbe*out,CohInitialCostumeBodyProbe*d,
 CohStatus status,size_t bit){d->status=status;d->failure_bit=bit;*out=*d;return status;}
static CohStatus flag(CohRepReader*r,uint32_t*out){
 uint32_t value=0;CohStatus status=coh_rep_read(r,1,&value);
 if(status!=COH_OK)return status;
 if(value>1)return COH_INVALID;
 *out=value;return COH_OK;
}
CohStatus coh_initial_costume_body_probe(const CohRepReader*input,CohInitialCostumeBodyProbe*out){
 if(!input||!out||overlap(input,sizeof(*input),out,sizeof(*out)))return COH_INVALID;
 CohRepReader r=*input;uint32_t value=0;
 if(coh_rep_read(&r,0,&value)!=COH_OK||r.bytes.size>COH_REP_BOUNDED_MESSAGE_MAX||
    overlap(r.bytes.data,r.bytes.size,input,sizeof(*input))||
    overlap(r.bytes.data,r.bytes.size,out,sizeof(*out)))return COH_INVALID;
 CohInitialCostumeBodyProbe d;memset(&d,0,sizeof(d));d.begin_bit=r.cursor;d.compressed=r.compressed;
 for(unsigned i=0;i<2;i++){
  uint32_t mask=1u<<i;d.field=i+1;d.stage=COH_INITIAL_COSTUME_BODY_FLAG;
  CohStatus status=flag(&r,&value);if(status!=COH_OK)return finish(out,&d,status,r.cursor);
  d.seen_mask|=mask;
  if(!value){d.complete_mask|=mask;continue;}
  d.present_mask|=mask;d.stage=COH_INITIAL_COSTUME_BODY_CACHE;
  status=flag(&r,&value);if(status!=COH_OK)return finish(out,&d,status,r.cursor);
  if(value){
   d.cached_mask|=mask;
   if(d.cache_count!=1)return finish(out,&d,COH_INVALID,r.cursor);
  }else{
   CohInitialRewardProbe leaf;memset(&leaf,0,sizeof(leaf));
   status=coh_initial_reward_probe(&r,&leaf);
   if(!leaf.literal_validated||leaf.stage!=COH_INITIAL_REWARD_CONTINUATION){
    d.stage=(CohInitialCostumeBodyStage)((unsigned)leaf.stage+2u);
    return finish(out,&d,status,leaf.failure_bit);
   }
   r.cursor=leaf.end_bit;d.cache_count++;d.literals++;d.literal_bytes+=leaf.literal_bytes;
  }
  d.complete_mask|=mask;
 }
 d.stage=COH_INITIAL_COSTUME_BODY_BODYTYPE;d.prefix_validated=1;d.end_bit=r.cursor;
 return finish(out,&d,r.cursor<r.bits?COH_UNSUPPORTED:COH_INVALID,r.cursor);
}
static int valid(const CohInitialCostumeBodyProbe*d){
 return (d->status==COH_INVALID||d->status==COH_UNSUPPORTED||d->status==COH_LIMIT)&&
  d->stage>=COH_INITIAL_COSTUME_BODY_FLAG&&d->stage<=COH_INITIAL_COSTUME_BODY_BODYTYPE&&
  d->field>=1&&d->field<=2&&d->compressed<=1&&d->begin_bit<=d->failure_bit&&
  d->failure_bit<=COH_REP_BOUNDED_MESSAGE_MAX*8u&&
  d->failure_bit-d->begin_bit<=(d->compressed?4224u:4168u)&&
  d->seen_mask<=3&&d->present_mask<=3&&d->complete_mask<=3&&d->cached_mask<=3&&
  d->prefix_validated<=1&&d->cache_count<=2&&d->literals<=2&&d->literal_bytes<=518;
}
int coh_initial_costume_body_probe_json(const CohInitialCostumeBodyProbe*d,char*out,size_t bytes){
 if(!d||!out||!bytes||overlap(d,sizeof(*d),out,bytes))return -1;
 if(!d->stage)return snprintf(out,bytes,"null");
 if(!valid(d))return -1;
 uint32_t m=d->present_mask|(d->complete_mask<<2)|(d->cached_mask<<4)|
  (d->prefix_validated<<6)|(d->seen_mask<<7)|(d->compressed<<9);
 return snprintf(out,bytes,"[%u,%u,%u,%llu,%llu,%u]",(unsigned)d->status,(unsigned)d->stage,d->field,
  (unsigned long long)d->begin_bit,(unsigned long long)(d->failure_bit-d->begin_bit),m);
}
int coh_initial_costume_body_progress_json(const CohInitialRewardListProbe*l,
 const CohInitialCostumeSlotsProbe*s,const CohInitialCostumeBodyProbe*d,char*out,size_t bytes){
 if(!l||!s||!d||!out||!bytes||overlap(l,sizeof(*l),out,bytes)||overlap(s,sizeof(*s),out,bytes)||
    overlap(d,sizeof(*d),out,bytes)||!valid(d)||l->list_validated!=1||l->stage!=COH_INITIAL_REWARD_LIST_SLOTS||
    (l->status!=COH_INVALID&&l->status!=COH_UNSUPPORTED)||
    l->entries[0]>COH_COSTUME_REWARDS_MAX||l->entries[1]>COH_COSTUME_REWARDS_MAX||
    l->entries[0]!=l->counts[0]||l->entries[1]!=l->counts[1]||
    s->stage!=COH_INITIAL_COSTUME_SLOTS_BODY||s->framing_validated!=1||s->multiple!=1||
    (s->status!=COH_INVALID&&s->status!=COH_UNSUPPORTED)||
    s->current>=COH_COSTUME_STORED_MAX||s->additional>255||s->deferred>1||
    !s->body_count||s->body_count>COH_COSTUME_STORED_MAX||s->current>=s->body_count||
    s->begin_bit!=l->end_bit||s->end_bit!=d->begin_bit||s->failure_bit!=s->end_bit||
    s->end_bit<s->begin_bit||s->end_bit-s->begin_bit!=(d->compressed?40u:22u))return -1;
 uint32_t stage=d->stage==COH_INITIAL_COSTUME_BODY_BODYTYPE?26u:
  14u+(d->field-1u)*6u+(unsigned)d->stage-2u;
 uint32_t m=s->current|(s->additional<<4)|(s->deferred<<12)|(s->body_count<<13)|
  (d->present_mask<<17)|(d->complete_mask<<19)|(d->cached_mask<<21)|
  (d->prefix_validated<<23)|(d->seen_mask<<24)|(d->compressed<<26);
 return snprintf(out,bytes,"[%u,%u,%u,%u,%llu,%llu,%u]",(unsigned)d->status,stage,
  l->entries[0],l->entries[1],(unsigned long long)l->end_bit,
  (unsigned long long)(d->failure_bit-l->end_bit),m);
}
