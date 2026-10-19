#include "coh_initial_create_probe.h"
#include <stdio.h>
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
 return x<y+bn&&y<x+an;
}
static CohStatus finish(CohInitialCreateProbe*out,CohInitialCreateProbe*d,
 CohStatus status,size_t bit){d->status=status;d->failure_bit=bit;*out=*d;return status;}
CohStatus coh_initial_create_probe(const CohRepReader*input,const CohRepSchema*schema,
 uint32_t selected,CohInitialCreateProbe*out){
 if(!input||!schema||!out||!selected||selected>INT32_MAX||schema->count>COH_REP_SHORTCUT_MAX||
    overlap(input,sizeof(*input),schema,sizeof(*schema))||
    overlap(input,sizeof(*input),out,sizeof(*out))||
    overlap(schema,sizeof(*schema),out,sizeof(*out)))return COH_INVALID;
 CohRepReader r=*input;uint32_t ignored;
 if(coh_rep_read(&r,0,&ignored)!=COH_OK||r.bytes.size>COH_REP_BOUNDED_MESSAGE_MAX||
    overlap(r.bytes.data,r.bytes.size,input,sizeof(*input))||
    overlap(r.bytes.data,r.bytes.size,schema,sizeof(*schema))||
    overlap(r.bytes.data,r.bytes.size,out,sizeof(*out)))return COH_INVALID;
 CohInitialCreateProbe d;memset(&d,0,sizeof(d));d.stage=COH_INITIAL_PROBE_HEADER;
 CohRepUpdatePrefix header;CohStatus status=coh_rep_update_prefix(&r,schema,COH_REP_ALLENTS,&header);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 if(!header.odd_send)return finish(out,&d,COH_INVALID,r.cursor);
 if(header.has_debug_info)return finish(out,&d,COH_UNSUPPORTED,r.cursor);
 d.header_validated=1;d.header_end_bit=r.cursor;d.stage=COH_INITIAL_PROBE_INDEX;
 uint32_t index;status=coh_ent_next_index(&r,-1,&index,&d.entity_failure);
 if(status!=COH_OK)return finish(out,&d,status,d.entity_failure.bit);
 /* Check the sentinel before treating its synthetic index as an entity. */
 CohRepReader peek=r;uint32_t create,end=0;
 status=coh_rep_read(&peek,1,&create);
 if(status==COH_OK&&create)status=coh_rep_read(&peek,1,&end);
 d.stage=COH_INITIAL_PROBE_CREATE;
 if(status!=COH_OK)return finish(out,&d,status,peek.cursor);
 if(create>1||end>1)return finish(out,&d,COH_INVALID,peek.cursor);
 if(end){d.stage=COH_INITIAL_PROBE_EMPTY_LIST;return finish(out,&d,index?COH_INVALID:COH_UNSUPPORTED,peek.cursor);}
 if(!index){d.stage=COH_INITIAL_PROBE_INDEX;return finish(out,&d,COH_INVALID,r.cursor);}
 if(!create)return finish(out,&d,COH_UNSUPPORTED,peek.cursor);
 CohEntCreate identity;memset(&identity,0,sizeof(identity));
 status=coh_ent_create(&r,selected,&identity,&d.entity_failure);
 if(status==COH_OK){
  d.create_validated=1;d.create_end_bit=r.cursor;d.entity_index=index;
  d.entity_type=identity.type;d.is_self=identity.is_self;
  d.self_dbid_matches_handoff=identity.is_self&&identity.dbid==selected;
  d.stage=COH_INITIAL_PROBE_RECORD_BODY;
 }
 /* Drop all decoded strings and raw identities before returning numerics. */
 memset(&identity,0,sizeof(identity));
 if(status!=COH_OK)return finish(out,&d,status,d.entity_failure.bit);
 return finish(out,&d,r.cursor<r.bits?COH_UNSUPPORTED:COH_INVALID,r.cursor);
}
int coh_initial_create_probe_json(const CohInitialCreateProbe*d,char*out,size_t bytes){
 static const char*const stages[]={"NONE","INPUT","HEADER","INDEX","CREATE",
  "FIRST_RECORD_BODY_REQUIRED","EMPTY_INITIAL_LIST"};
 if(!d||!out||!bytes||overlap(d,sizeof(*d),out,bytes))return -1;
 if(!d->stage)return snprintf(out,bytes,"null");
 return snprintf(out,bytes,"{\"schema\":\"coh-initial-first-create-v1\",\"diagnostic_only\":true,"
  "\"status\":%u,\"stage\":\"%s\",\"stage_id\":%u,\"header_validated\":%s,\"create_validated\":%s,"
  "\"header_end_bit\":%llu,\"create_end_bit\":%llu,\"failure_bit\":%llu,\"entity_index\":%u,\"entity_type\":%u,"
  "\"is_self\":%s,\"self_dbid_matches_handoff\":%s,\"entity_failure\":{\"status\":%u,\"stage\":%u,\"bit\":%llu},"
  "\"selected_owner_bound\":false,\"source_generation_admitted\":false,\"complete_initial_character\":false,"
  "\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false}",
  (unsigned)d->status,(unsigned)d->stage<sizeof(stages)/sizeof(stages[0])?stages[d->stage]:"INPUT",
  (unsigned)d->stage,d->header_validated?"true":"false",d->create_validated?"true":"false",
  (unsigned long long)d->header_end_bit,(unsigned long long)d->create_end_bit,(unsigned long long)d->failure_bit,
  d->entity_index,d->entity_type,d->is_self?"true":"false",d->self_dbid_matches_handoff?"true":"false",
  (unsigned)d->entity_failure.status,(unsigned)d->entity_failure.stage,(unsigned long long)d->entity_failure.bit);
}
