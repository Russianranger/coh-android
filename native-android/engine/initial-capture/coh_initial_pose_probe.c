#include "coh_initial_pose_probe.h"
#include <stdio.h>
#include <string.h>
static int overlap(const void*a,size_t an,const void*b,size_t bn){
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
 return x<y+bn&&y<x+an;
}
static CohStatus finish(CohInitialPoseProbe*out,CohInitialPoseProbe*d,
 CohStatus status,size_t bit){d->status=status;d->failure_bit=bit;*out=*d;return status;}
static CohStatus flag(CohRepReader*r,uint32_t*out){
 CohStatus status=coh_rep_read(r,1,out);
 return status==COH_OK&&*out>1?COH_INVALID:status;
}
CohStatus coh_initial_pose_probe(const CohRepReader*input,uint32_t packet_id,
 CohInitialPoseProbe*out){
 if(!input||!out||!packet_id||overlap(input,sizeof(*input),out,sizeof(*out)))return COH_INVALID;
 CohRepReader r=*input;uint32_t ignored;
 if(coh_rep_read(&r,0,&ignored)!=COH_OK||r.bytes.size>COH_REP_BOUNDED_MESSAGE_MAX||
    overlap(r.bytes.data,r.bytes.size,input,sizeof(*input))||
    overlap(r.bytes.data,r.bytes.size,out,sizeof(*out)))return COH_INVALID;
 CohInitialPoseProbe d;memset(&d,0,sizeof(d));d.begin_bit=r.cursor;d.stage=COH_INITIAL_POSE_FLAGS;
 uint32_t rare=0,medium=0,very=0;CohStatus status=flag(&r,&rare);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 if(!rare)return finish(out,&d,COH_UNSUPPORTED,r.cursor);
 status=flag(&r,&medium);if(status==COH_OK)status=flag(&r,&very);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 if(!medium||!very)return finish(out,&d,COH_UNSUPPORTED,r.cursor);
 d.flags_validated=1;d.flags_end_bit=r.cursor;d.stage=COH_INITIAL_POSE_MODE;
 uint32_t updated=0,present=0,value=0;
 status=flag(&r,&updated);if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 if(!updated)return finish(out,&d,COH_UNSUPPORTED,r.cursor);
 status=flag(&r,&present);if(status==COH_OK&&present)status=coh_rep_pack(&r,3,&value);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 d.mode_validated=1;d.mode_end_bit=r.cursor;d.stage=COH_INITIAL_POSE_POSITION;
 /* Refuse a delta profile before a fresh-state decoder could require an
  * unavailable previous baseline. The real child still reads the full body. */
 CohRepReader peek=r;uint32_t mask=0;status=coh_rep_read(&peek,3,&mask);
 if(status!=COH_OK)return finish(out,&d,status,peek.cursor);
 if(mask>7)return finish(out,&d,COH_INVALID,peek.cursor);
 if(mask!=7)return finish(out,&d,COH_UNSUPPORTED,peek.cursor);
 CohRepPosition position;coh_rep_position_init(&position);
 status=coh_rep_position(&r,packet_id,&position);
 if(status!=COH_OK)return finish(out,&d,status,r.cursor);
 if(!position.valid)return finish(out,&d,COH_UNSUPPORTED,r.cursor);
 for(unsigned i=0;i<24;i++)if(position.packet_ids[i]!=packet_id)return finish(out,&d,COH_STATE,r.cursor);
 d.position_validated=1;d.position_end_bit=r.cursor;d.stage=COH_INITIAL_POSE_ORIENTATION;
 CohEntOrientation orientation;coh_ent_orientation_init(&orientation);
 status=coh_ent_orientation(&r,packet_id,&orientation,&d.entity_failure);
 if(status!=COH_OK)return finish(out,&d,status,d.entity_failure.bit);
 if(orientation.valid!=7)return finish(out,&d,COH_UNSUPPORTED,r.cursor);
 for(unsigned i=0;i<3;i++)if(orientation.packet_ids[i]!=packet_id)return finish(out,&d,COH_STATE,r.cursor);
 d.orientation_validated=d.pose_validated=1;d.pose_end_bit=r.cursor;d.stage=COH_INITIAL_POSE_SEQUENCE;
 /* No decoded scratch state or source identity is retained in this report. */
 memset(&position,0,sizeof(position));memset(&orientation,0,sizeof(orientation));value=0;
 return finish(out,&d,r.cursor<r.bits?COH_UNSUPPORTED:COH_INVALID,r.cursor);
}
int coh_initial_pose_probe_json(const CohInitialPoseProbe*d,char*out,size_t bytes){
 static const char*const stages[]={"NONE","INPUT","RARE_FLAGS","MODE","POSITION",
  "ORIENTATION","FIRST_SEQUENCE_BODY_REQUIRED"};
 if(!d||!out||!bytes||overlap(d,sizeof(*d),out,bytes))return -1;
 if(!d->stage)return snprintf(out,bytes,"null");
 return snprintf(out,bytes,"{\"schema\":\"coh-initial-first-pose-v1\",\"diagnostic_only\":true,"
  "\"status\":%u,\"stage\":\"%s\",\"stage_id\":%u,\"begin_bit\":%llu,\"flags_end_bit\":%llu,"
  "\"mode_end_bit\":%llu,\"position_end_bit\":%llu,\"pose_end_bit\":%llu,\"failure_bit\":%llu,"
  "\"flags_validated\":%s,\"mode_validated\":%s,\"position_validated\":%s,\"orientation_validated\":%s,"
  "\"pose_validated\":%s,\"entity_failure\":{\"status\":%u,\"stage\":%u,\"bit\":%llu},"
  "\"selected_owner_bound\":false,\"source_generation_admitted\":false,\"complete_initial_character\":false,"
  "\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false}",
  (unsigned)d->status,(unsigned)d->stage<sizeof(stages)/sizeof(stages[0])?stages[d->stage]:"INPUT",(unsigned)d->stage,
  (unsigned long long)d->begin_bit,(unsigned long long)d->flags_end_bit,(unsigned long long)d->mode_end_bit,
  (unsigned long long)d->position_end_bit,(unsigned long long)d->pose_end_bit,(unsigned long long)d->failure_bit,
  d->flags_validated?"true":"false",d->mode_validated?"true":"false",d->position_validated?"true":"false",
  d->orientation_validated?"true":"false",d->pose_validated?"true":"false",
  (unsigned)d->entity_failure.status,(unsigned)d->entity_failure.stage,(unsigned long long)d->entity_failure.bit);
}
