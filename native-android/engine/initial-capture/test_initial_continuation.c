/* Transport/lifetime unit: the callback completion result is a test double.
 * Actual whole-packet source qualification is a separate receiver test. */
#define COH_INITIAL_CONTINUATION_TEST 1
#define COH_INITIAL_CAPTURE_NO_MAIN 1
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "test_initial_capture.c"
#pragma GCC diagnostic pop
#include "coh_initial_send.h"
static unsigned completion_mode,release_failure,post_callbacks;
CohStatus __real_coh_net_udp_owned_release(CohNetUdp*,CohNetOwnedMessage*);
CohStatus __wrap_coh_net_udp_owned_release(CohNetUdp*u,CohNetOwnedMessage*n){CohStatus s=__real_coh_net_udp_owned_release(u,n);if(release_failure){release_failure=0;CHECK(s==COH_OK);return COH_IO;}return s;}
static CohStatus completed(void*context,const CohInitialCapture*owner,const CohInitialCaptureEvent*event){
 Observation*o=context;CohInitialCaptureLease loan;CHECK(coh_initial_capture_lease(owner,event,&loan)==COH_OK);
 if(event->kind==COH_INITIAL_CAPTURE_UPDATE){post_callbacks++;return COH_OK;}
 CHECK(event->kind==COH_INITIAL_CAPTURE_ALLENTS);CHECK(observe(context,owner,event)==COH_OK);
 CohInitialCaptureEvent copy=*event;CHECK(coh_initial_capture_finish_initial(owner,&copy,loan.reader.bits)==COH_STATE);
 CHECK(coh_initial_capture_finish_initial(owner,event,loan.reader.bits-1)==COH_STATE);
 CHECK(coh_initial_capture_finish_initial(owner,event,loan.reader.bits)==COH_OK);
 CHECK(coh_initial_capture_finish_initial(owner,event,loan.reader.bits)==COH_STATE);
 if(completion_mode==1)o->cancelled=1;
 if(completion_mode==2)release_failure=1;
 return completion_mode==3?COH_IO:COH_OK;
}
static CohStatus next(Observation*o,uint64_t now){return coh_initial_capture_service(o->owner,now,(CohCancel){cancel_now,o},completed,o,sizeof(*o));}
static void scenario_complete(unsigned mode){
 Peer db=peer_open(),map=peer_open();Observation o={0};completion_mode=mode;CohNetEndpoint to=setup(&o,&db,&map,0);
 CHECK(service(&o,115)==COH_OK);drain_ack(&map,5);ok(&o,116);CohNetPacket req=frame_read(&map,5,0);CHECK(command(&req,5,0)==COH_MAP_REQALLENTS);
 size_t bits;uint8_t*data=body(128,0,0,&bits);o.expected=data;o.bits=bits;o.bytes=(bits+7)/8;o.aligned=0;peer_message(&map,to,5,data,bits,0,req.id);
 CohStatus s=next(&o,117);CohInitialCaptureDiagnostics d=diagnostic(o.owner);drain_ack(&map,5);
 if(mode&&mode<4){CHECK(s==(mode==1?COH_CANCELLED:COH_IO));CHECK(!d.continuation.initial_complete&&!d.continuation.full_update_ack_queued&&!d.continuation.client_ready_queued&&!d.continuation.full_update_ack_sent&&!d.continuation.client_ready_sent);quiet(&map);}
 else{
  CHECK(s==COH_OK&&d.phase==COH_INITIAL_CAPTURE_WAIT_UPDATES&&d.raw_allents_observed&&d.continuation.initial_complete&&d.complete_initial_character&&d.ack_permitted);
  CHECK(d.continuation.full_update_ack_queued&&d.continuation.client_ready_queued&&!d.continuation.full_update_ack_sent&&!d.continuation.client_ready_sent&&d.continuation.waiting_for_full_update&&!d.continuation.received_character_queued);
  CHECK(next(&o,118)==COH_OK);CohNetPacket ack=frame_read(&map,5,0),ready=frame_read(&map,5,0);CohMapPacket expected;
  CHECK(ack.id!=7&&ready.id!=7&&ack.id!=123456&&ready.id!=123456);
  CHECK(coh_initial_input_serialize((CohMapProfile){0,0},7,0,&expected)==COH_OK&&ack.payload_bits==expected.bits&&!memcmp(ack.payload,expected.data,(expected.bits+7)/8));
  CHECK(command(&ready,5,0)==COH_MAP_READY);CohProtocolBits r;uint32_t value;CHECK(!coh_protocol_bits_init(&r,ready.payload,sizeof(ready.payload),ready.payload_bits,0));CHECK(coh_protocol_read_pack(&r,1,&value)==COH_OK&&value==COH_MAP_READY);CHECK(coh_protocol_read_pack(&r,1,&value)==COH_OK&&value==123456);CHECK(coh_protocol_read_pack(&r,1,&value)==COH_OK&&!value);while(r.cursor&7u)CHECK(coh_protocol_read(&r,1,&value)==COH_OK&&!value);static const uint8_t md5[16]={0xd4,0x1d,0x8c,0xd9,0x8f,0x00,0xb2,0x04,0xe9,0x80,0x09,0x98,0xec,0xf8,0x42,0x7e};for(unsigned i=0;i<16;i++)CHECK(coh_protocol_read(&r,8,&value)==COH_OK&&value==md5[i]);CHECK(coh_protocol_read(&r,2,&value)==COH_OK&&!value&&coh_protocol_read(&r,2,&value)==COH_OK&&value==1&&r.cursor==r.bit_length);
  d=diagnostic(o.owner);CHECK(d.continuation.full_update_ack_sent&&d.continuation.client_ready_sent);
  if(mode==4){
   CohNetPacket msg=application(&map,15);msg.ack_count=2;msg.acks[0]=ack.id;msg.acks[1]=ready.id;frame_send(&map,to,5,&msg);CHECK(next(&o,119)==COH_OK);drain_ack(&map,5);
   CHECK(next(&o,3000)==COH_OK&&diagnostic(o.owner).phase==COH_INITIAL_CAPTURE_WAIT_UPDATES);
   CHECK(next(&o,10117)==COH_UNSUPPORTED);d=diagnostic(o.owner);CHECK(d.phase==COH_INITIAL_CAPTURED&&d.continuation.post_window_complete&&d.continuation.post_messages==1&&d.continuation.post_end_ms-d.continuation.post_begin_ms==10000);quiet(&map);
  }else{
  for(unsigned i=0;i<COH_INITIAL_POST_MESSAGES_MAX;i++){
   CohNetPacket msg=application(&map,15);app_send(&map,to,msg,NULL,i&1?ready.id:ack.id);CHECK(next(&o,119+i)==(i+1==COH_INITIAL_POST_MESSAGES_MAX?COH_UNSUPPORTED:COH_OK));drain_ack(&map,5);
  }
  d=diagnostic(o.owner);CHECK(d.phase==COH_INITIAL_CAPTURED&&d.continuation.post_window_complete&&d.continuation.post_messages==128&&d.continuation.post_rows==1&&!d.continuation.post_row_overflow);
  CHECK(d.continuation.post[0].kind==COH_INITIAL_CAPTURE_COMMAND_SERVER_GAME_CMDS&&d.continuation.post[0].count==128&&d.continuation.post[0].total_bytes>0&&d.continuation.post[0].total_bits>0&&!d.continuation.received_character_queued);quiet(&map);
  }
 }
 free(data);coh_initial_capture_close(o.owner);CHECK(diagnostic(o.owner).local.opened_sockets==diagnostic(o.owner).local.closed_sockets);coh_initial_capture_destroy(o.owner);peer_close(&db);peer_close(&map);CHECK(!live_allocations);scenarios++;
}
int main(void){unsigned fds=descriptors();for(unsigned i=0;i<5;i++)scenario_complete(i);CHECK(fds==descriptors()&&!post_callbacks);printf("{\"passed\":true,\"checks\":%u,\"scenarios\":%u,\"synthetic_completion_double\":true,\"real_server\":false,\"post_message_bound\":128,\"post_duration_ms\":10000,\"whole_source_packet_qualification_claim\":false}\n",checks,scenarios);return 0;}
