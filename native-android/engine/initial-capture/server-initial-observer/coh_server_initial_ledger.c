#include "coh_server_initial_ledger.h"
#include <stdio.h>
#include <string.h>
static void coh_sio_core_clear_keys(CohSIOLedger*s){memset(&s->key,0,sizeof(s->key));s->packet=0;s->send_pending=0;s->report.owner_retired=1;}
void coh_sio_init(CohSIOLedger*s){if(s){memset(s,0,sizeof(*s));s->report.diagnostic_only=s->report.valid=1;s->report.pkt_send_result=-1;}}
void coh_sio_refuse(CohSIOLedger*s,CohSIORefusal reason){if(s&&s->report.stop==COH_SIO_ACTIVE&&reason>COH_SIO_NONE&&reason<=COH_SIO_SINK){s->report.refusal=reason;s->report.valid=0;s->report.stop=COH_SIO_REFUSED;if(s->report.groups_owner_bound)coh_sio_core_clear_keys(s);}}
static int coh_sio_core_key_ok(const CohSIOKey*k){return k&&k->link&&k->client&&k->entity&&k->character&&k->entity_id&&k->dbid&&k->server_index&&k->protocol<=5;}
static int coh_sio_core_same(const CohSIOKey*a,const CohSIOKey*b){return a->link==b->link&&a->client==b->client&&a->entity==b->entity&&a->character==b->character&&a->uid==b->uid&&a->connection_id==b->connection_id&&a->connect_id==b->connect_id&&a->entity_id==b->entity_id&&a->dbid==b->dbid&&a->server_index==b->server_index&&a->auth_id==b->auth_id&&a->protocol==b->protocol;}
void coh_sio_bind(CohSIOLedger*s,const CohSIOKey*k,uint32_t thread){if(!s||s->report.stop!=COH_SIO_ACTIVE)return;if(s->report.groups_owner_bound||!coh_sio_core_key_ok(k)||!thread){coh_sio_refuse(s,COH_SIO_OWNER);return;}s->key=*k;s->thread=thread;s->report.groups_owner_bound=1;s->report.stage=COH_SIO_GROUPS_BOUND;s->report.reached_mask=1u<<COH_SIO_GROUPS_BOUND;}
static int coh_sio_core_enter(CohSIOLedger*s,const CohSIOKey*k,uint32_t thread){
 if(!s||s->report.stop!=COH_SIO_ACTIVE||!s->report.groups_owner_bound||!k||k->link!=s->key.link)return 0;
 if(thread!=s->thread){coh_sio_refuse(s,COH_SIO_THREAD);return 0;}
 if(!coh_sio_core_key_ok(k)||!coh_sio_core_same(&s->key,k)){coh_sio_refuse(s,COH_SIO_OWNER);return 0;}
 if(s->events==COH_SIO_MAX_EVENTS){coh_sio_refuse(s,COH_SIO_LIMIT);return 0;}s->events++;return 1;
}
static int coh_sio_core_packet(CohSIOLedger*s,const void*p){if(!p||(uintptr_t)p!=s->packet){coh_sio_refuse(s,COH_SIO_PACKET);return 0;}return 1;}
static int coh_sio_core_require(CohSIOLedger*s,int condition){if(!condition)coh_sio_refuse(s,COH_SIO_ORDER);return condition;}
void coh_sio_record(CohSIOLedger*s,const CohSIOKey*k,uint32_t thread,CohSIOEvent event,const void*p,uint32_t a,uint32_t b,uint32_t c){
 CohSIOReport*r;if(!coh_sio_core_enter(s,k,thread))return;r=&s->report;
 if(event<=COH_SIO_UNUSED||event>=COH_SIO_GROUPS_BOUND){coh_sio_refuse(s,COH_SIO_VALUE);return;}
 if(event==COH_SIO_TICK||event==COH_SIO_REQUEST_STATE){if(a>7||b>1){coh_sio_refuse(s,COH_SIO_VALUE);return;}r->last_ready=a;r->last_sent_self=b;r->ready_seen_mask|=1u<<a;}
 switch(event){
 case COH_SIO_DISPATCH:r->dispatch_entered=1;break;
 case COH_SIO_REQUEST_STATE:if(!coh_sio_core_require(s,r->dispatch_entered&&a==1&&!b))return;r->dispatch_state_written=1;break;
 case COH_SIO_TICK:r->tick_seen++;break;
 case COH_SIO_BACKPRESSURE_ENTER:r->backpressure_entered++;break;
 case COH_SIO_BACKPRESSURE_PASS:r->backpressure_passed++;break;
 case COH_SIO_BACKPRESSURE_BLOCK:r->backpressure_blocked++;break;
 case COH_SIO_MAPXFER_ENTER:r->mapxfer_entered++;break;
 case COH_SIO_MAPXFER_RETURN:r->mapxfer_returned++;break;
 case COH_SIO_SELECTED:if(!coh_sio_core_require(s,r->dispatch_state_written))return;r->tick_selected++;break;
 case COH_SIO_FULL_ENTER:if(a>1||b>1||c>1){coh_sio_refuse(s,COH_SIO_VALUE);return;}r->full_sender_entered=1;r->full_update_argument=a;r->viewed_entity_matches_owner=b;if(!coh_sio_core_require(s,r->tick_selected&&a&&b))return;break;
 case COH_SIO_ALLENTS_HEADER:if(!coh_sio_core_require(s,r->full_sender_entered&&r->full_update_argument&&r->viewed_entity_matches_owner&&!s->packet))return;if(!p){coh_sio_refuse(s,COH_SIO_PACKET);return;}s->packet=(uintptr_t)p;r->allents_header_written=1;break;
 case COH_SIO_CHARACTER_ENTER:if(!coh_sio_core_packet(s,p)||!coh_sio_core_require(s,r->allents_header_written))return;r->character_entered=1;break;
 case COH_SIO_CHARACTER_CORE_ENTER:if(!coh_sio_core_packet(s,p)||!coh_sio_core_require(s,r->character_entered))return;r->character_core_entered=1;break;
 case COH_SIO_CHARACTER_CORE_RETURN:if(!coh_sio_core_packet(s,p)||!coh_sio_core_require(s,r->character_core_entered))return;r->character_core_returned=1;break;
 case COH_SIO_CHARACTER_RETURN:if(!coh_sio_core_packet(s,p)||!coh_sio_core_require(s,r->character_core_returned))return;r->character_returned=1;break;
 case COH_SIO_ATTACHED:if(!coh_sio_core_packet(s,p)||!coh_sio_core_require(s,r->character_returned))return;r->packet_attached=1;break;
 case COH_SIO_FINISH_ENTITY:r->finish_entity_seen=1;if(r->packet_attached&&p&&!coh_sio_core_packet(s,p))return;break;
 case COH_SIO_SEND_BEGIN:if(b>7){coh_sio_refuse(s,COH_SIO_VALUE);return;}if(!coh_sio_core_packet(s,p)||!coh_sio_core_require(s,r->packet_attached&&r->finish_entity_seen&&!s->send_pending&&a))return;s->send_pending=1;r->final_packet_same=r->pkt_send_called=1;r->final_packet_bits=a;r->final_packet_reliable=!!(b&1);r->final_packet_compress=!!(b&2);r->final_packet_ordered=!!(b&4);break;
 default:coh_sio_refuse(s,COH_SIO_VALUE);return;
 }r->stage=(uint32_t)event;r->reached_mask|=1u<<event;
}
void coh_sio_send_return(CohSIOLedger*s,uint32_t thread,int result){
 CohSIOReport*r;if(!s||s->report.stop!=COH_SIO_ACTIVE||!s->send_pending)return;
 if(thread!=s->thread){coh_sio_refuse(s,COH_SIO_THREAD);return;}if(result!=0&&result!=1){coh_sio_refuse(s,COH_SIO_VALUE);return;}
 r=&s->report;r->pkt_send_returned=1;r->pkt_send_result=result;r->stop=COH_SIO_FINAL_RETURN;r->stage=COH_SIO_SEND_RETURN;r->reached_mask|=1u<<COH_SIO_SEND_RETURN;coh_sio_core_clear_keys(s);
}
void coh_sio_snapshot(const CohSIOLedger*s,CohSIOReport*out){if(s&&out)*out=s->report;}
static const char*coh_sio_core_boolean(unsigned v){return v?"true":"false";}
int coh_sio_json(const CohSIOReport*r,char*out,size_t cap){
 static const char*refusals[]={"NONE","OWNER","THREAD","ORDER","LIMIT","VALUE","PACKET","SINK"};static const char*stops[]={"ACTIVE","FINAL_RETURN","REFUSED"};int n;
 if(!r||!out||cap<COH_SIO_MAX_JSON||(unsigned)r->refusal>COH_SIO_SINK||(unsigned)r->stop>COH_SIO_REFUSED)return 0;
 /* Original stdtypes.h wraps snprintf with an array-only size check. This
  * API has an explicit pointer/capacity pair, so call the C99 CRT function
  * without expanding that function-like macro in the containing server TU. */
 n=(snprintf)(out,cap,"{\"schema\":\"coh-server-initial-ledger-v1\",\"refusal\":\"%s\",\"stop\":\"%s\",\"stage\":%u,\"reached_mask\":%u,\"last_ready\":%u,\"ready_seen_mask\":%u,\"pkt_send_result\":%d,\"final_packet_bits\":%u,"
 "\"diagnostic_only\":true,\"valid\":%s,\"groups_owner_bound\":%s,\"owner_retired\":%s,\"dispatch_entered\":%s,\"dispatch_state_written\":%s,\"full_sender_entered\":%s,\"full_update_argument\":%s,\"viewed_entity_matches_owner\":%s,\"allents_header_written\":%s,\"character_entered\":%s,\"character_core_entered\":%s,\"character_core_returned\":%s,\"character_returned\":%s,\"packet_attached\":%s,\"finish_entity_seen\":%s,\"final_packet_same\":%s,\"pkt_send_called\":%s,\"pkt_send_returned\":%s,\"last_sent_self\":%s,\"final_packet_compress\":%s,\"final_packet_ordered\":%s,\"final_packet_reliable\":%s,"
 "\"tick_seen\":%u,\"tick_selected\":%u,\"backpressure_entered\":%u,\"backpressure_passed\":%u,\"backpressure_blocked\":%u,\"mapxfer_entered\":%u,\"mapxfer_returned\":%u,"
 "\"packet_queue_acceptance_established\":false,\"socket_send_established\":false,\"source_generation_admitted\":false,\"complete_initial_character\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false}\n",
 refusals[r->refusal],stops[r->stop],r->stage,r->reached_mask,r->last_ready,r->ready_seen_mask,r->pkt_send_result,r->final_packet_bits,
 coh_sio_core_boolean(r->valid),coh_sio_core_boolean(r->groups_owner_bound),coh_sio_core_boolean(r->owner_retired),coh_sio_core_boolean(r->dispatch_entered),coh_sio_core_boolean(r->dispatch_state_written),coh_sio_core_boolean(r->full_sender_entered),coh_sio_core_boolean(r->full_update_argument),coh_sio_core_boolean(r->viewed_entity_matches_owner),coh_sio_core_boolean(r->allents_header_written),coh_sio_core_boolean(r->character_entered),coh_sio_core_boolean(r->character_core_entered),coh_sio_core_boolean(r->character_core_returned),coh_sio_core_boolean(r->character_returned),coh_sio_core_boolean(r->packet_attached),coh_sio_core_boolean(r->finish_entity_seen),coh_sio_core_boolean(r->final_packet_same),coh_sio_core_boolean(r->pkt_send_called),coh_sio_core_boolean(r->pkt_send_returned),coh_sio_core_boolean(r->last_sent_self),coh_sio_core_boolean(r->final_packet_compress),coh_sio_core_boolean(r->final_packet_ordered),coh_sio_core_boolean(r->final_packet_reliable),r->tick_seen,r->tick_selected,r->backpressure_entered,r->backpressure_passed,r->backpressure_blocked,r->mapxfer_entered,r->mapxfer_returned);
 return n>0&&(size_t)n<cap&&(unsigned)n<COH_SIO_MAX_JSON?n:0;
}
