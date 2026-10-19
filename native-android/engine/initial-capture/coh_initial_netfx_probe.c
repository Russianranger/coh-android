#include "coh_initial_netfx_probe.h"
#include <stdio.h>
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
 return x<y+bn&&y<x+an;
}
static CohStatus finish(CohInitialNetFxProbe*out,CohInitialNetFxProbe*d,
 CohStatus status,size_t bit){d->status=status;d->failure_bit=bit;*out=*d;return status;}
static CohStatus flag(CohRepReader*r,uint32_t*out){
 uint32_t value=0;CohStatus status=coh_rep_read(r,1,&value);
 if(status!=COH_OK)return status;
 if(value>1)return COH_INVALID;
 *out=value;return COH_OK;
}
CohStatus coh_initial_netfx_probe(const CohRepReader*input,CohInitialNetFxProbe*out){
 if(!input||!out||overlap(input,sizeof(*input),out,sizeof(*out)))return COH_INVALID;
 CohRepReader r=*input;uint32_t ignored;
 if(coh_rep_read(&r,0,&ignored)!=COH_OK||r.bytes.size>COH_REP_BOUNDED_MESSAGE_MAX||
    overlap(r.bytes.data,r.bytes.size,input,sizeof(*input))||
    overlap(r.bytes.data,r.bytes.size,out,sizeof(*out)))return COH_INVALID;
 CohInitialNetFxProbe d;memset(&d,0,sizeof(d));d.begin_bit=r.cursor;d.stage=COH_INITIAL_NETFX_FLAGS;
 CohStatus status=flag(&r,&d.pchar_things);
 if(status==COH_OK)status=flag(&r,&d.in_phase);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 d.flags_end_bit=r.cursor;d.body_present=d.pchar_things&&d.in_phase;
 if(d.body_present){
  d.stage=COH_INITIAL_NETFX_BODY;CohEntNetFxList effects;memset(&effects,0,sizeof(effects));
  status=coh_ent_netfx(&r,&effects,&d.entity_failure);
  if(status==COH_OK)d.effect_count=effects.count;
  memset(&effects,0,sizeof(effects));
  if(status!=COH_OK)return finish(out,&d,status,d.entity_failure.bit);
 }
 d.netfx_validated=1;d.netfx_end_bit=r.cursor;d.stage=COH_INITIAL_NETFX_COSTUME;
 return finish(out,&d,r.cursor<r.bits?COH_UNSUPPORTED:COH_INVALID,r.cursor);
}
int coh_initial_netfx_probe_json(const CohInitialNetFxProbe*d,char*out,size_t bytes){
 static const char*const stages[]={"NONE","INPUT","FLAGS","BODY","FIRST_COSTUME_BODY_REQUIRED"};
 if(!d||!out||!bytes||overlap(d,sizeof(*d),out,bytes))return -1;
 if(!d->stage)return snprintf(out,bytes,"null");
 return snprintf(out,bytes,"{\"schema\":\"coh-initial-first-netfx-v1\",\"diagnostic_only\":true,"
  "\"status\":%u,\"stage\":\"%s\",\"stage_id\":%u,\"begin_bit\":%llu,\"flags_end_bit\":%llu,"
  "\"netfx_end_bit\":%llu,\"failure_bit\":%llu,\"pchar_things\":%s,\"in_phase\":%s,"
  "\"body_present\":%s,\"effect_count\":%u,\"netfx_validated\":%s,"
  "\"entity_failure\":{\"status\":%u,\"stage\":%u,\"bit\":%llu},"
  "\"cross_prefix_in_phase_verified\":false,\"selected_owner_bound\":false,"
  "\"source_generation_admitted\":false,\"complete_initial_character\":false,"
  "\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false}",
  (unsigned)d->status,(unsigned)d->stage<sizeof(stages)/sizeof(stages[0])?stages[d->stage]:"INPUT",(unsigned)d->stage,
  (unsigned long long)d->begin_bit,(unsigned long long)d->flags_end_bit,
  (unsigned long long)d->netfx_end_bit,(unsigned long long)d->failure_bit,
  d->pchar_things?"true":"false",d->in_phase?"true":"false",d->body_present?"true":"false",
  d->effect_count,d->netfx_validated?"true":"false",(unsigned)d->entity_failure.status,
  (unsigned)d->entity_failure.stage,(unsigned long long)d->entity_failure.bit);
}
