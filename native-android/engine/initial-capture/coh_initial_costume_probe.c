#include "coh_initial_costume_probe.h"
#include <stdio.h>
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
 return x<y+bn&&y<x+an;
}
static CohStatus finish(CohInitialCostumeProbe*out,CohInitialCostumeProbe*d,
 CohStatus status,size_t bit){d->status=status;d->failure_bit=bit;*out=*d;return status;}
static CohStatus scalar(CohRepReader*r,unsigned width,uint32_t*out){
 uint32_t value=0;CohStatus status=coh_rep_read(r,width,&value);
 if(status!=COH_OK)return status;
 if(width<32&&value>=(UINT32_C(1)<<width))return COH_INVALID;
 *out=value;return COH_OK;
}
static CohStatus boundary(CohRepReader*r,CohInitialCostumeProbe*out,
 CohInitialCostumeProbe*d,CohInitialCostumeStage stage){
 d->stage=stage;d->prefix_end_bit=r->cursor;
 return finish(out,d,r->cursor<r->bits?COH_UNSUPPORTED:COH_INVALID,r->cursor);
}
CohStatus coh_initial_costume_probe(const CohRepReader*input,uint32_t create_is_self,
 CohInitialCostumeProbe*out){
 if(!input||!out||create_is_self>1||overlap(input,sizeof(*input),out,sizeof(*out)))return COH_INVALID;
 CohRepReader r=*input;uint32_t value=0;
 if(coh_rep_read(&r,0,&value)!=COH_OK||r.bytes.size>COH_REP_BOUNDED_MESSAGE_MAX||
    overlap(r.bytes.data,r.bytes.size,input,sizeof(*input))||
    overlap(r.bytes.data,r.bytes.size,out,sizeof(*out)))return COH_INVALID;
 CohInitialCostumeProbe d;memset(&d,0,sizeof(d));d.begin_bit=r.cursor;d.stage=COH_INITIAL_COSTUME_SELECTOR_FLAG;
 CohStatus status=scalar(&r,1,&value);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 d.stage=COH_INITIAL_COSTUME_SELECTOR;
 if(value){status=coh_rep_pack(&r,2,&d.type);if(status!=COH_OK)return finish(out,&d,status,r.cursor);}
 if(!d.type||d.type>4)return finish(out,&d,COH_UNSUPPORTED,r.cursor);
 d.selector_validated=1;d.selector_end_bit=r.cursor;
 if(d.type==3)return boundary(&r,out,&d,COH_INITIAL_COSTUME_NPC_BODY);
 if(d.type==4)return boundary(&r,out,&d,COH_INITIAL_COSTUME_SEQUENCE_BODY);
 if(d.type==2){d.body_count=1;d.framing_validated=1;return boundary(&r,out,&d,COH_INITIAL_COSTUME_BODY_DICTIONARY);}
 d.stage=COH_INITIAL_COSTUME_SELF;status=scalar(&r,1,&value);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 d.self_seen=1;if(value!=create_is_self)return finish(out,&d,COH_STATE,r.cursor);
 d.self_wire_consistent=1;
 if(value){
  for(unsigned i=0;i<2;i++){
   d.reward_list=i+1;d.reward_index=0;d.stage=COH_INITIAL_COSTUME_REWARD_COUNT;
   status=scalar(&r,32,&d.reward_count[i]);if(status!=COH_OK)return finish(out,&d,status,r.cursor);
   if(d.reward_count[i]>COH_COSTUME_REWARDS_MAX)return finish(out,&d,COH_LIMIT,r.cursor);
   for(unsigned j=0;j<d.reward_count[i];j++){
    d.reward_index=j;d.stage=COH_INITIAL_COSTUME_REWARD_FLAG;status=scalar(&r,1,&value);
    if(status!=COH_OK)return finish(out,&d,status,r.cursor);
    if(value)return boundary(&r,out,&d,COH_INITIAL_COSTUME_REWARD_STRING);
    d.absent_rewards[i]++;
   }
  }
 }
 d.stage=COH_INITIAL_COSTUME_SLOTS;status=scalar(&r,1,&value); /* deferred, never applied */
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 uint32_t current=0;
 if(create_is_self){
  status=scalar(&r,8,&current);if(status==COH_OK)status=scalar(&r,8,&value); /* additional slots */
  if(status!=COH_OK)return finish(out,&d,status,r.cursor);
  if(current>=COH_COSTUME_STORED_MAX)return finish(out,&d,COH_LIMIT,r.cursor);
 }
 d.stage=COH_INITIAL_COSTUME_MULTIPLE;uint32_t multiple=0;status=scalar(&r,1,&multiple);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 if(multiple&&!create_is_self)return finish(out,&d,COH_INVALID,r.cursor);
 if(!multiple&&create_is_self)return finish(out,&d,COH_UNSUPPORTED,r.cursor);
 d.body_count=1;
 if(multiple){
  d.stage=COH_INITIAL_COSTUME_STORED_COUNT;status=scalar(&r,4,&d.body_count);
  if(status!=COH_OK)return finish(out,&d,status,r.cursor);
  if(!d.body_count||d.body_count>COH_COSTUME_STORED_MAX||current>=d.body_count)return finish(out,&d,COH_LIMIT,r.cursor);
 }
 d.framing_validated=1;
 return boundary(&r,out,&d,COH_INITIAL_COSTUME_BODY_DICTIONARY);
}
int coh_initial_costume_probe_json(const CohInitialCostumeProbe*d,char*out,size_t bytes){
 static const char*const stages[]={"NONE","INPUT","SELECTOR_FLAG","SELECTOR","SELF","REWARD_COUNT","REWARD_FLAG",
  "SLOTS","MULTIPLE","STORED_COUNT","FIRST_COSTUME_REWARD_STRING_REQUIRED","FIRST_COSTUME_DICTIONARY_REQUIRED",
  "FIRST_NPC_COSTUME_BODY_REQUIRED","FIRST_SEQUENCE_COSTUME_BODY_REQUIRED"};
 if(!d||!out||!bytes||overlap(d,sizeof(*d),out,bytes))return -1;
 if(!d->stage)return snprintf(out,bytes,"null");
 return snprintf(out,bytes,"{\"schema\":\"coh-initial-costume-prefix-v1\",\"status\":%u,\"stage\":\"%s\","
  "\"begin_bit\":%llu,\"prefix_end_bit\":%llu,\"failure_bit\":%llu,\"type\":%u,"
  "\"selector_validated\":%s,\"self_wire_consistent\":%s,\"reward_list\":%u,\"reward_index\":%u,"
  "\"reward_counts\":[%u,%u],\"absent_rewards\":[%u,%u],\"body_count\":%u,\"framing_validated\":%s,"
  "\"source_generation_admitted\":false,\"ack_permitted\":false,\"world_authority\":false}",
  (unsigned)d->status,(unsigned)d->stage<sizeof(stages)/sizeof(stages[0])?stages[d->stage]:"INPUT",
  (unsigned long long)d->begin_bit,(unsigned long long)d->prefix_end_bit,(unsigned long long)d->failure_bit,d->type,
  d->selector_validated?"true":"false",d->self_wire_consistent?"true":"false",d->reward_list,d->reward_index,
  d->reward_count[0],d->reward_count[1],d->absent_rewards[0],d->absent_rewards[1],d->body_count,
  d->framing_validated?"true":"false");
}
