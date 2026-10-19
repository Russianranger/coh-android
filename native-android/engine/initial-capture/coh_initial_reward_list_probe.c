#include "coh_initial_reward_list_probe.h"
#include <stdio.h>
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
 return x<y+bn&&y<x+an;
}
static CohStatus finish(CohInitialRewardListProbe*out,CohInitialRewardListProbe*d,
 CohStatus status,size_t bit){d->status=status;d->failure_bit=bit;*out=*d;return status;}
static CohStatus flag(CohRepReader*r,uint32_t*out){
 uint32_t value=0;CohStatus status=coh_rep_read(r,1,&value);
 if(status!=COH_OK)return status;
 if(value>1)return COH_INVALID;
 *out=value;return COH_OK;
}
CohStatus coh_initial_reward_list_probe(const CohRepReader*input,CohInitialRewardListProbe*out){
 if(!input||!out||overlap(input,sizeof(*input),out,sizeof(*out)))return COH_INVALID;
 CohRepReader r=*input;uint32_t value=0;
 if(coh_rep_read(&r,0,&value)!=COH_OK||r.bytes.size>COH_REP_BOUNDED_MESSAGE_MAX||
    overlap(r.bytes.data,r.bytes.size,input,sizeof(*input))||
    overlap(r.bytes.data,r.bytes.size,out,sizeof(*out)))return COH_INVALID;
 CohInitialRewardListProbe d;memset(&d,0,sizeof(d));d.begin_bit=r.cursor;
 for(unsigned g=0;g<2;g++){
  d.group=g+1;d.index=0;d.stage=COH_INITIAL_REWARD_LIST_COUNT;
  CohStatus status=coh_rep_read(&r,32,&d.counts[g]);
  if(status!=COH_OK)return finish(out,&d,status,r.cursor);
  if(d.counts[g]>COH_COSTUME_REWARDS_MAX)return finish(out,&d,COH_LIMIT,r.cursor);
  for(unsigned i=0;i<d.counts[g];i++){
   d.index=i;d.stage=COH_INITIAL_REWARD_LIST_FLAG;
   status=flag(&r,&value);if(status!=COH_OK)return finish(out,&d,status,r.cursor);
   if(value){
    d.stage=COH_INITIAL_REWARD_LIST_STRING;CohInitialRewardProbe leaf;memset(&leaf,0,sizeof(leaf));
    status=coh_initial_reward_probe(&r,&leaf);d.leaf_stage=leaf.stage;
    if(!leaf.literal_validated||leaf.stage!=COH_INITIAL_REWARD_CONTINUATION){
     if(leaf.stage==COH_INITIAL_REWARD_DICTIONARY)d.stage=COH_INITIAL_REWARD_LIST_DICTIONARY;
     return finish(out,&d,status,leaf.failure_bit);
    }
    r.cursor=leaf.end_bit;d.literals++;d.literal_bytes+=leaf.literal_bytes;d.leaf_stage=0;
   }
   d.entries[g]++;
  }
 }
 d.list_validated=1;d.end_bit=r.cursor;d.stage=COH_INITIAL_REWARD_LIST_SLOTS;
 return finish(out,&d,r.cursor<r.bits?COH_UNSUPPORTED:COH_INVALID,r.cursor);
}
int coh_initial_reward_list_probe_json(const CohInitialRewardListProbe*d,char*out,size_t bytes){
 if(!d||!out||!bytes||overlap(d,sizeof(*d),out,bytes))return -1;
 if(!d->stage)return snprintf(out,bytes,"null");
 return snprintf(out,bytes,"[%u,%u,%u,%u,%u,%u,%llu,%u,%u]",(unsigned)d->status,(unsigned)d->stage,
  d->group,d->index,d->entries[0],d->entries[1],(unsigned long long)d->failure_bit,d->list_validated,
  (unsigned)d->leaf_stage);
}
