#include "coh_initial_sequence_probe.h"
#include <stdio.h>
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
 return x<y+bn&&y<x+an;
}
static CohStatus finish(CohInitialSequenceProbe*out,CohInitialSequenceProbe*d,
 CohStatus status,size_t bit){d->status=status;d->failure_bit=bit;*out=*d;return status;}
static CohStatus flag(CohRepReader*r,uint32_t*out){
 uint32_t value=0;CohStatus status=coh_rep_read(r,1,&value);
 if(status!=COH_OK)return status;
 if(value>1)return COH_INVALID;
 *out=value;return COH_OK;
}
CohStatus coh_initial_sequence_probe(const CohRepReader*input,CohInitialSequenceProbe*out){
 if(!input||!out||overlap(input,sizeof(*input),out,sizeof(*out)))return COH_INVALID;
 CohRepReader r=*input;uint32_t ignored;
 if(coh_rep_read(&r,0,&ignored)!=COH_OK||r.bytes.size>COH_REP_BOUNDED_MESSAGE_MAX||
    overlap(r.bytes.data,r.bytes.size,input,sizeof(*input))||
    overlap(r.bytes.data,r.bytes.size,out,sizeof(*out)))return COH_INVALID;
 CohInitialSequenceProbe d;memset(&d,0,sizeof(d));d.begin_bit=r.cursor;d.stage=COH_INITIAL_SEQUENCE_UPDATE;
 uint32_t updated=0,value=0;CohStatus status=flag(&r,&updated);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 if(!updated)return finish(out,&d,COH_UNSUPPORTED,r.cursor);
 d.update_seen=1;d.stage=COH_INITIAL_SEQUENCE_INDEX;
 status=flag(&r,&d.index_present);
 if(status==COH_OK&&d.index_present)status=coh_rep_pack(&r,8,&value);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 if(d.index_present&&value>INT32_MAX)return finish(out,&d,COH_LIMIT,r.cursor);
 d.index_end_bit=r.cursor;d.stage=COH_INITIAL_SEQUENCE_TICKS;value=0;
 status=flag(&r,&d.ticks_present);
 if(status==COH_OK&&d.ticks_present)status=coh_rep_pack(&r,4,&value);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 if(d.ticks_present&&value>65535u)return finish(out,&d,COH_LIMIT,r.cursor);
 d.ticks_end_bit=r.cursor;d.stage=COH_INITIAL_SEQUENCE_MOVE_BITS;value=0;
 status=flag(&r,&d.movement_bits_present);
 if(status==COH_OK&&d.movement_bits_present)status=coh_rep_read(&r,11,&value);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 if(d.movement_bits_present&&value>2047u)return finish(out,&d,COH_INVALID,r.cursor);
 d.sequence_validated=1;d.sequence_end_bit=r.cursor;d.stage=COH_INITIAL_SEQUENCE_TRIGGERS;
 return finish(out,&d,r.cursor<r.bits?COH_UNSUPPORTED:COH_INVALID,r.cursor);
}
int coh_initial_sequence_probe_json(const CohInitialSequenceProbe*d,char*out,size_t bytes){
 static const char*const stages[]={"NONE","INPUT","UPDATE","INDEX","TICKS","MOVEMENT_BITS",
  "FIRST_TRIGGERED_MOVES_REQUIRED"};
 if(!d||!out||!bytes||overlap(d,sizeof(*d),out,bytes))return -1;
 if(!d->stage)return snprintf(out,bytes,"null");
 return snprintf(out,bytes,"{\"schema\":\"coh-initial-first-sequence-v1\",\"diagnostic_only\":true,"
  "\"status\":%u,\"stage\":\"%s\",\"stage_id\":%u,\"begin_bit\":%llu,\"index_end_bit\":%llu,"
  "\"ticks_end_bit\":%llu,\"sequence_end_bit\":%llu,\"failure_bit\":%llu,\"update_seen\":%s,"
  "\"index_present\":%s,\"ticks_present\":%s,\"movement_bits_present\":%s,\"sequence_validated\":%s,"
  "\"selected_owner_bound\":false,\"source_generation_admitted\":false,\"complete_initial_character\":false,"
  "\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false}",
  (unsigned)d->status,(unsigned)d->stage<sizeof(stages)/sizeof(stages[0])?stages[d->stage]:"INPUT",(unsigned)d->stage,
  (unsigned long long)d->begin_bit,(unsigned long long)d->index_end_bit,(unsigned long long)d->ticks_end_bit,
  (unsigned long long)d->sequence_end_bit,(unsigned long long)d->failure_bit,
  d->update_seen?"true":"false",d->index_present?"true":"false",d->ticks_present?"true":"false",
  d->movement_bits_present?"true":"false",d->sequence_validated?"true":"false");
}
