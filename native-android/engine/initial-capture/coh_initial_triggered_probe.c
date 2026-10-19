#include "coh_initial_triggered_probe.h"
#include <stdio.h>
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
 return x<y+bn&&y<x+an;
}
static CohStatus finish(CohInitialTriggeredProbe*out,CohInitialTriggeredProbe*d,
 CohStatus status,size_t bit){d->status=status;d->failure_bit=bit;*out=*d;return status;}
static CohStatus flag(CohRepReader*r,uint32_t*out){
 uint32_t value=0;CohStatus status=coh_rep_read(r,1,&value);
 if(status!=COH_OK)return status;
 if(value>1)return COH_INVALID;
 *out=value;return COH_OK;
}
CohStatus coh_initial_triggered_probe(const CohRepReader*input,CohInitialTriggeredProbe*out){
 if(!input||!out||overlap(input,sizeof(*input),out,sizeof(*out)))return COH_INVALID;
 CohRepReader r=*input;uint32_t ignored;
 if(coh_rep_read(&r,0,&ignored)!=COH_OK||r.bytes.size>COH_REP_BOUNDED_MESSAGE_MAX||
    overlap(r.bytes.data,r.bytes.size,input,sizeof(*input))||
    overlap(r.bytes.data,r.bytes.size,out,sizeof(*out)))return COH_INVALID;
 CohInitialTriggeredProbe d;memset(&d,0,sizeof(d));d.begin_bit=r.cursor;d.stage=COH_INITIAL_TRIGGERED_COUNT;
 CohStatus status=coh_rep_pack(&r,1,&d.count);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 if(d.count>COH_ENT_TRIGGER_MAX)return finish(out,&d,COH_LIMIT,r.cursor);
 d.count_validated=1;d.count_end_bit=r.cursor;
 for(uint32_t i=0;i<d.count;i++){
  uint32_t value=0,present=0;d.current_entry=i;d.stage=COH_INITIAL_TRIGGERED_INDEX;
  status=coh_rep_pack(&r,10,&value);
  if(status!=COH_OK)return finish(out,&d,status,r.cursor);
  if(value>INT32_MAX)return finish(out,&d,COH_LIMIT,r.cursor);
  d.stage=COH_INITIAL_TRIGGERED_TICKS;status=coh_rep_pack(&r,6,&value);
  if(status!=COH_OK)return finish(out,&d,status,r.cursor);
  if(value>INT32_MAX)return finish(out,&d,COH_LIMIT,r.cursor);
  d.stage=COH_INITIAL_TRIGGERED_FX;status=flag(&r,&present);
  if(status==COH_OK&&present)status=coh_rep_pack(&r,16,&value);
  if(status!=COH_OK)return finish(out,&d,status,r.cursor);
  if(present)d.fx_entries++;
  d.entries_validated++;
 }
 d.current_entry=d.count;d.triggered_moves_validated=1;d.triggered_end_bit=r.cursor;
 d.stage=COH_INITIAL_TRIGGERED_AI_ANIMATION;
 return finish(out,&d,r.cursor<r.bits?COH_UNSUPPORTED:COH_INVALID,r.cursor);
}
int coh_initial_triggered_probe_json(const CohInitialTriggeredProbe*d,char*out,size_t bytes){
 static const char*const stages[]={"NONE","INPUT","COUNT","INDEX","TICKS","FX","FIRST_AI_ANIMATION_REQUIRED"};
 if(!d||!out||!bytes||overlap(d,sizeof(*d),out,bytes))return -1;
 if(!d->stage)return snprintf(out,bytes,"null");
 return snprintf(out,bytes,"{\"schema\":\"coh-initial-first-triggered-v1\",\"diagnostic_only\":true,"
  "\"status\":%u,\"stage\":\"%s\",\"stage_id\":%u,\"begin_bit\":%llu,\"count_end_bit\":%llu,"
  "\"triggered_end_bit\":%llu,\"failure_bit\":%llu,\"local_trigger_limit\":%u,\"count\":%u,"
  "\"count_validated\":%s,\"entries_validated\":%u,\"current_entry\":%u,\"fx_entries\":%u,"
  "\"triggered_moves_validated\":%s,\"selected_owner_bound\":false,\"source_generation_admitted\":false,"
  "\"complete_initial_character\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false}",
  (unsigned)d->status,(unsigned)d->stage<sizeof(stages)/sizeof(stages[0])?stages[d->stage]:"INPUT",(unsigned)d->stage,
  (unsigned long long)d->begin_bit,(unsigned long long)d->count_end_bit,(unsigned long long)d->triggered_end_bit,
  (unsigned long long)d->failure_bit,COH_ENT_TRIGGER_MAX,d->count,d->count_validated?"true":"false",
  d->entries_validated,d->current_entry,d->fx_entries,d->triggered_moves_validated?"true":"false");
}
