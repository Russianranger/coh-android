#include "coh_initial_aianim_probe.h"
#include <stdio.h>
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
 return x<y+bn&&y<x+an;
}
static CohStatus finish(CohInitialAiAnimProbe*out,CohInitialAiAnimProbe*d,
 CohStatus status,size_t bit){d->status=status;d->failure_bit=bit;*out=*d;return status;}
static CohStatus flag(CohRepReader*r,uint32_t*out){
 uint32_t value=0;CohStatus status=coh_rep_read(r,1,&value);
 if(status!=COH_OK)return status;
 if(value>1)return COH_INVALID;
 *out=value;return COH_OK;
}
CohStatus coh_initial_aianim_probe(const CohRepReader*input,CohInitialAiAnimProbe*out){
 if(!input||!out||overlap(input,sizeof(*input),out,sizeof(*out)))return COH_INVALID;
 CohRepReader r=*input;uint32_t ignored;
 if(coh_rep_read(&r,0,&ignored)!=COH_OK||r.bytes.size>COH_REP_BOUNDED_MESSAGE_MAX||
    overlap(r.bytes.data,r.bytes.size,input,sizeof(*input))||
    overlap(r.bytes.data,r.bytes.size,out,sizeof(*out)))return COH_INVALID;
 CohInitialAiAnimProbe d;memset(&d,0,sizeof(d));d.begin_bit=r.cursor;d.stage=COH_INITIAL_AIANIM_UPDATE;
 uint32_t update=0;CohStatus status=flag(&r,&update);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 if(!update)return finish(out,&d,COH_UNSUPPORTED,r.cursor);
 d.update_seen=1;d.stage=COH_INITIAL_AIANIM_STRING_FLAG;
 status=flag(&r,&d.string_present);if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 if(d.string_present){
  d.stage=COH_INITIAL_AIANIM_STRING;unsigned terminated=0;
  for(unsigned i=0;i<COH_INITIAL_AIANIM_TEXT_MAX;i++){
   uint32_t byte=0;status=coh_rep_read(&r,8,&byte);
   if(status!=COH_OK)return finish(out,&d,status,r.cursor);
   if(!byte){terminated=1;break;}
   d.string_bytes++;
  }
  if(!terminated)return finish(out,&d,COH_LIMIT,r.cursor);
 }
 d.ai_animation_validated=1;d.ai_end_bit=r.cursor;d.stage=COH_INITIAL_AIANIM_NETFX;
 return finish(out,&d,r.cursor<r.bits?COH_UNSUPPORTED:COH_INVALID,r.cursor);
}
int coh_initial_aianim_probe_json(const CohInitialAiAnimProbe*d,char*out,size_t bytes){
 static const char*const stages[]={"NONE","INPUT","UPDATE","STRING_FLAG","STRING","FIRST_NETFX_REQUIRED"};
 if(!d||!out||!bytes||overlap(d,sizeof(*d),out,bytes))return -1;
 if(!d->stage)return snprintf(out,bytes,"null");
 return snprintf(out,bytes,"{\"schema\":\"coh-initial-first-aianim-v1\",\"diagnostic_only\":true,"
  "\"status\":%u,\"stage\":\"%s\",\"stage_id\":%u,\"begin_bit\":%llu,\"ai_end_bit\":%llu,"
  "\"failure_bit\":%llu,\"update_seen\":%s,\"string_present\":%s,\"string_bytes\":%u,"
  "\"text_limit_including_nul\":%u,\"ai_animation_validated\":%s,\"selected_owner_bound\":false,"
  "\"source_generation_admitted\":false,\"complete_initial_character\":false,\"actor_publication\":false,"
  "\"ack_permitted\":false,\"world_authority\":false}",
  (unsigned)d->status,(unsigned)d->stage<sizeof(stages)/sizeof(stages[0])?stages[d->stage]:"INPUT",(unsigned)d->stage,
  (unsigned long long)d->begin_bit,(unsigned long long)d->ai_end_bit,(unsigned long long)d->failure_bit,
  d->update_seen?"true":"false",d->string_present?"true":"false",d->string_bytes,COH_INITIAL_AIANIM_TEXT_MAX,
  d->ai_animation_validated?"true":"false");
}
