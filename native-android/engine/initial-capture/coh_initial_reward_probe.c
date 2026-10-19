#include "coh_initial_reward_probe.h"
#include <stdio.h>
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
 return x<y+bn&&y<x+an;
}
static CohStatus finish(CohInitialRewardProbe*out,CohInitialRewardProbe*d,
 CohStatus status,size_t bit){d->status=status;d->failure_bit=bit;*out=*d;return status;}
static CohStatus flag(CohRepReader*r,uint32_t*out){
 uint32_t value=0;CohStatus status=coh_rep_read(r,1,&value);
 if(status!=COH_OK)return status;
 if(value>1)return COH_INVALID;
 *out=value;return COH_OK;
}
CohStatus coh_initial_reward_probe(const CohRepReader*input,CohInitialRewardProbe*out){
 if(!input||!out||overlap(input,sizeof(*input),out,sizeof(*out)))return COH_INVALID;
 CohRepReader r=*input;uint32_t value=0;
 if(coh_rep_read(&r,0,&value)!=COH_OK||r.bytes.size>COH_REP_BOUNDED_MESSAGE_MAX||
    overlap(r.bytes.data,r.bytes.size,input,sizeof(*input))||
    overlap(r.bytes.data,r.bytes.size,out,sizeof(*out)))return COH_INVALID;
 CohInitialRewardProbe d;memset(&d,0,sizeof(d));d.begin_bit=r.cursor;d.stage=COH_INITIAL_REWARD_PRESENCE;
 CohStatus status=flag(&r,&value);if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 if(!value)return finish(out,&d,COH_INVALID,r.cursor);
 d.presence_seen=1;d.stage=COH_INITIAL_REWARD_STORAGE;
 status=flag(&r,&d.in_table);if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 if(d.in_table){
  d.stage=COH_INITIAL_REWARD_DICTIONARY;
  return finish(out,&d,r.cursor<r.bits?COH_UNSUPPORTED:COH_INVALID,r.cursor);
 }
 d.stage=COH_INITIAL_REWARD_TEXT;unsigned terminated=0;
 for(unsigned i=0;i<COH_INITIAL_REWARD_TEXT_MAX;i++){
  status=coh_rep_read(&r,8,&value);if(status!=COH_OK)return finish(out,&d,status,r.cursor);
  if(!value){terminated=1;break;}
  d.literal_bytes++;
 }
 if(!terminated)return finish(out,&d,COH_LIMIT,r.cursor);
 d.literal_validated=1;d.end_bit=r.cursor;d.stage=COH_INITIAL_REWARD_CONTINUATION;
 return finish(out,&d,r.cursor<r.bits?COH_UNSUPPORTED:COH_INVALID,r.cursor);
}
int coh_initial_reward_probe_json(const CohInitialRewardProbe*d,char*out,size_t bytes){
 static const char*const stages[]={"NONE","INPUT","PRESENCE","STORAGE","TEXT",
  "FIRST_REWARD_DICTIONARY_REQUIRED","FIRST_REWARD_CONTINUATION_REQUIRED"};
 if(!d||!out||!bytes||overlap(d,sizeof(*d),out,bytes))return -1;
 if(!d->stage)return snprintf(out,bytes,"null");
 return snprintf(out,bytes,"{\"status\":%u,\"stage\":\"%s\",\"bit\":%llu,\"bytes\":%u,\"literal_validated\":%s}",
  (unsigned)d->status,(unsigned)d->stage<sizeof(stages)/sizeof(stages[0])?stages[d->stage]:"INPUT",
  (unsigned long long)d->failure_bit,d->literal_bytes,d->literal_validated?"true":"false");
}
