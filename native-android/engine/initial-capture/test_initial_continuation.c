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
#include <errno.h>
#ifdef COH_BOUNDED_CONTINUATION_DIAGNOSTIC
static unsigned defer_ready,defer_ack;
#endif
ssize_t __real_sendto(int,const void*,size_t,int,const struct sockaddr*,socklen_t);
ssize_t __wrap_sendto(int fd,const void*data,size_t size,int flags,const struct sockaddr*to,socklen_t length){
#ifdef COH_BOUNDED_CONTINUATION_DIAGNOSTIC
 if(defer_ready||defer_ack){CohNetPacket p;if(coh_net_frame_decode(5,NULL,0,0,(CohBytes){data,size},&p)==COH_OK){CohProtocolBits r;uint32_t c;if(coh_protocol_bits_init(&r,p.payload,sizeof(p.payload),p.payload_bits,0)==COH_OK&&coh_protocol_read_pack(&r,1,&c)==COH_OK&&((c==COH_MAP_READY&&defer_ready)||(c==2&&defer_ack))){if(c==COH_MAP_READY)defer_ready--;else defer_ack--;errno=EAGAIN;return -1;}}}
#endif
 return __real_sendto(fd,data,size,flags,to,length);
}
static CohNetPacket read_sized(Peer*p,size_t*wire){struct pollfd pollfd={p->fd,POLLIN,0};CHECK(poll(&pollfd,1,100)==1&&(pollfd.revents&POLLIN));uint8_t frame[COH_PROTOCOL_FRAME_MAX];ssize_t size=recv(p->fd,frame,sizeof(frame),0);CHECK(size>0);*wire=(size_t)size;CohNetPacket packet;CHECK(coh_net_frame_decode(5,NULL,0,0,(CohBytes){frame,*wire},&packet)==COH_OK);return packet;}
#ifdef COH_BOUNDED_CONTINUATION_DIAGNOSTIC
static void totals(const CohInitialContinuation*c){uint64_t bytes=c->post_overflow_bytes,bits=c->post_overflow_bits;uint32_t count=c->post_row_overflow;for(unsigned i=0;i<c->post_rows;i++){count+=c->post[i].count;bytes+=c->post[i].total_bytes;bits+=c->post[i].total_bits;}CHECK(count==c->post_messages&&bytes==c->post_total_bytes&&bits==c->post_total_bits);CHECK(c->post_unclassified<=c->post_messages&&c->post_before_send+c->post_between_sends<=c->post_messages);}
static void sent_once(const CohInitialDelivery*d,uint64_t now,size_t wire,const CohNetPacket*p){CHECK(d->queued_ms==117&&d->first_sent_ms==now&&d->last_sent_ms==now&&d->accepted==1&&!d->accepted_retries&&!d->failures&&!d->counter_overflow&&d->last_status==COH_OK);CHECK(d->payload_bits==p->payload_bits&&d->payload_bytes==(p->payload_bits+7)/8&&d->accepted_wire_bytes==wire);}
#endif
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
  #ifdef COH_BOUNDED_CONTINUATION_DIAGNOSTIC
  if(mode==10){defer_ack=UINT32_MAX;CHECK(next(&o,118)==COH_OK);quiet(&map);CohNetPacket msg=application(&map,15);frame_send(&map,to,5,&msg);CHECK(next(&o,119)==COH_OK);quiet(&map);d=diagnostic(o.owner);CHECK(!d.continuation.full_update_ack_sent&&!d.continuation.client_ready_sent&&!d.continuation.post_begin_ms&&!d.continuation.ack_delivery.first_sent_ms&&d.continuation.post_before_send==1&&d.continuation.post_messages==1);defer_ack=0;CHECK(next(&o,20117)==COH_STATE);d=diagnostic(o.owner);CHECK(d.continuation.abort_reason==COH_INITIAL_ABORT_DEADLINE&&d.continuation.post_end_ms==20117&&!d.continuation.ack_delivery.accepted&&!d.continuation.ready_delivery.accepted&&d.continuation.ack_delivery.attempts==2&&!d.continuation.ready_delivery.attempts);quiet(&map);defer_ack=0;goto scenario_cleanup;}
  if(mode==8)defer_ready=2;
#endif
  CHECK(next(&o,118)==COH_OK);size_t ack_wire,ready_wire;CohNetPacket ack=read_sized(&map,&ack_wire),ready;CohMapPacket expected;
#ifdef COH_BOUNDED_CONTINUATION_DIAGNOSTIC
  if(mode==8){quiet(&map);d=diagnostic(o.owner);CHECK(d.continuation.full_update_ack_sent&&!d.continuation.client_ready_sent&&d.continuation.ready_delivery.deferred==1&&d.continuation.post_begin_ms==118);CohNetPacket msg=application(&map,15);app_send(&map,to,msg,NULL,ack.id);CHECK(next(&o,119)==COH_OK);quiet(&map);d=diagnostic(o.owner);CHECK(d.continuation.post_messages==1&&d.continuation.post_between_sends==1&&d.continuation.ready_delivery.deferred==2&&!d.continuation.client_ready_sent);CHECK(next(&o,120)==COH_OK);}
#endif
  ready=read_sized(&map,&ready_wire);
  CHECK(ack.id!=7&&ready.id!=7&&ack.id!=123456&&ready.id!=123456);
  CHECK(coh_initial_input_serialize((CohMapProfile){0,0},7,0,&expected)==COH_OK&&ack.payload_bits==expected.bits&&!memcmp(ack.payload,expected.data,(expected.bits+7)/8));
  CHECK(command(&ready,5,0)==COH_MAP_READY);CohProtocolBits r;uint32_t value;CHECK(!coh_protocol_bits_init(&r,ready.payload,sizeof(ready.payload),ready.payload_bits,0));CHECK(coh_protocol_read_pack(&r,1,&value)==COH_OK&&value==COH_MAP_READY);CHECK(coh_protocol_read_pack(&r,1,&value)==COH_OK&&value==123456);CHECK(coh_protocol_read_pack(&r,1,&value)==COH_OK&&!value);while(r.cursor&7u)CHECK(coh_protocol_read(&r,1,&value)==COH_OK&&!value);static const uint8_t md5[16]={0xd4,0x1d,0x8c,0xd9,0x8f,0x00,0xb2,0x04,0xe9,0x80,0x09,0x98,0xec,0xf8,0x42,0x7e};for(unsigned i=0;i<16;i++)CHECK(coh_protocol_read(&r,8,&value)==COH_OK&&value==md5[i]);CHECK(coh_protocol_read(&r,2,&value)==COH_OK&&!value&&coh_protocol_read(&r,2,&value)==COH_OK&&value==1&&r.cursor==r.bit_length);
  d=diagnostic(o.owner);CHECK(d.continuation.full_update_ack_sent&&d.continuation.client_ready_sent);
#ifdef COH_BOUNDED_CONTINUATION_DIAGNOSTIC
  sent_once(&d.continuation.ack_delivery,118,ack_wire,&ack);sent_once(&d.continuation.ready_delivery,mode==8?120:118,ready_wire,&ready);CHECK(d.continuation.post_begin_ms==118);CHECK(d.continuation.ack_delivery.attempts==1&&d.continuation.ready_delivery.attempts==(mode==8?3u:1u));
#endif
  if(mode==4){
   CohNetPacket msg=application(&map,15);msg.ack_count=2;msg.acks[0]=ack.id;msg.acks[1]=ready.id;frame_send(&map,to,5,&msg);CHECK(next(&o,119)==COH_OK);drain_ack(&map,5);
   CHECK(next(&o,3000)==COH_OK&&diagnostic(o.owner).phase==COH_INITIAL_CAPTURE_WAIT_UPDATES);
   #ifdef COH_BOUNDED_CONTINUATION_DIAGNOSTIC
   CHECK(next(&o,20116)==COH_OK);CHECK(next(&o,20117)==COH_STATE);d=diagnostic(o.owner);CHECK(d.phase==COH_INITIAL_CAPTURE_FAILED&&d.failure==COH_INITIAL_CAPTURE_FAILURE_TIMEOUT&&d.continuation.abort_reason==COH_INITIAL_ABORT_DEADLINE&&d.continuation.post_end_ms==20117&&d.continuation.post_begin_ms==118&&d.continuation.ack_delivery.queued_ms==117);totals(&d.continuation);
#else
   CHECK(next(&o,10117)==COH_UNSUPPORTED);d=diagnostic(o.owner);CHECK(d.phase==COH_INITIAL_CAPTURED&&d.continuation.post_end_ms-d.continuation.post_begin_ms==10000);
#endif
   CHECK(d.continuation.post_window_complete&&d.continuation.post_messages==1);quiet(&map);
  }
#ifdef COH_BOUNDED_CONTINUATION_DIAGNOSTIC
  else if(mode==5){uint64_t due=118+coh_net_retry_ms(0,coh_net_default_config().ping_ms,0);CHECK(next(&o,due-1)==COH_OK);quiet(&map);CHECK(next(&o,due)==COH_OK);size_t a_bytes,r_bytes;CohNetPacket a=read_sized(&map,&a_bytes),r=read_sized(&map,&r_bytes);CHECK(a.id==ack.id&&r.id==ready.id&&a.payload_bits==ack.payload_bits&&r.payload_bits==ready.payload_bits&&!memcmp(a.payload,ack.payload,(ack.payload_bits+7)/8)&&!memcmp(r.payload,ready.payload,(ready.payload_bits+7)/8));d=diagnostic(o.owner);CHECK(d.continuation.ack_delivery.accepted==2&&d.continuation.ready_delivery.accepted==2&&d.continuation.ack_delivery.accepted_retries==1&&d.continuation.ready_delivery.accepted_retries==1&&d.continuation.ack_delivery.accepted_wire_bytes==ack_wire+a_bytes&&d.continuation.ready_delivery.accepted_wire_bytes==ready_wire+r_bytes);uint64_t end=due+coh_net_retry_ms(1,coh_net_default_config().ping_ms,0);CHECK(next(&o,end-1)==COH_OK);quiet(&map);CHECK(next(&o,end)==COH_STATE);d=diagnostic(o.owner);CHECK(d.phase==COH_INITIAL_CAPTURE_FAILED&&d.continuation.abort_reason==COH_INITIAL_ABORT_TRANSPORT_TIMEOUT&&d.continuation.ack_delivery.accepted==2&&d.continuation.ready_delivery.accepted==2&&d.continuation.post_end_ms==end);quiet(&map);}
  else if(mode==6){uint64_t expected_bytes=0,expected_bits=0;for(unsigned i=0;i<17;i++){CohNetPacket msg=application(&map,15+i);expected_bytes+=(msg.payload_bits+7)/8;expected_bits+=msg.payload_bits;msg.ack_count=2;msg.acks[0]=ack.id;msg.acks[1]=ready.id;frame_send(&map,to,5,&msg);CHECK(next(&o,119+i)==COH_OK);drain_ack(&map,5);}d=diagnostic(o.owner);CHECK(d.continuation.post_messages==17&&d.continuation.post_rows==16&&d.continuation.post_row_overflow==1&&d.continuation.post_overflow_bytes>0&&d.continuation.post_total_bytes==expected_bytes&&d.continuation.post_total_bits==expected_bits);totals(&d.continuation);CohNetPacket unknown=application(&map,UINT32_MAX);expected_bytes+=(unknown.payload_bits+7)/8;expected_bits+=unknown.payload_bits;frame_send(&map,to,5,&unknown);CHECK(next(&o,136)==COH_OK);drain_ack(&map,5);d=diagnostic(o.owner);CHECK(d.continuation.post_messages==18&&!d.continuation.post_unclassified&&d.continuation.post_row_overflow==2&&d.continuation.post_total_bytes==expected_bytes&&d.continuation.post_total_bits==expected_bits);totals(&d.continuation);uint64_t malformed_before=d.local.map_protocol.udp.malformed;CohNetPacket malformed={0};malformed.id=++map.id;malformed.payload_bits=1;malformed.payload[0]=1;frame_send(&map,to,5,&malformed);CHECK(next(&o,137)==COH_OK);d=diagnostic(o.owner);CHECK(d.continuation.post_messages==18&&d.local.map_protocol.udp.malformed==malformed_before+1);quiet(&map);}

  else if(mode==7){CohNetPacket bye=control(5,++map.id,5,0,0);bye.ack_count=2;bye.acks[0]=ack.id;bye.acks[1]=ready.id;frame_send(&map,to,5,&bye);CHECK(next(&o,119)==COH_STATE);d=diagnostic(o.owner);CHECK(d.phase==COH_INITIAL_CAPTURE_FAILED&&d.continuation.abort_reason==COH_INITIAL_ABORT_PEER_CLOSED&&!d.continuation.post_messages&&!d.continuation.received_character_queued);}
  else if(mode==9){coh_initial_capture_cancel(o.owner);d=diagnostic(o.owner);CHECK(d.phase==COH_INITIAL_CAPTURE_CANCELLED&&d.continuation.abort_reason==COH_INITIAL_ABORT_CANCELLED&&!d.continuation.received_character_queued);quiet(&map);}
  else if(mode==8){CohNetPacket msg=application(&map,15);app_send(&map,to,msg,NULL,ready.id);CHECK(next(&o,121)==COH_OK);drain_ack(&map,5);d=diagnostic(o.owner);CHECK(d.continuation.post_messages==2&&d.continuation.post_between_sends==1&&!d.continuation.post_before_send);totals(&d.continuation);coh_initial_capture_close(o.owner);CHECK(diagnostic(o.owner).continuation.abort_reason==COH_INITIAL_ABORT_CLIENT_CLOSED);}
#endif
  else{
  for(unsigned i=0;i<COH_INITIAL_POST_MESSAGES_MAX;i++){
   CohNetPacket msg=application(&map,15);app_send(&map,to,msg,NULL,i&1?ready.id:ack.id);CHECK(next(&o,119+i)==(i+1==COH_INITIAL_POST_MESSAGES_MAX?COH_UNSUPPORTED:COH_OK));drain_ack(&map,5);
  }
  d=diagnostic(o.owner);CHECK(d.phase==COH_INITIAL_CAPTURED&&d.continuation.post_window_complete&&d.continuation.post_messages==128&&d.continuation.post_rows==1&&!d.continuation.post_row_overflow);
  CHECK(d.continuation.post[0].kind==COH_INITIAL_CAPTURE_COMMAND_SERVER_GAME_CMDS&&d.continuation.post[0].count==128&&d.continuation.post[0].total_bytes>0&&d.continuation.post[0].total_bits>0&&!d.continuation.received_character_queued);quiet(&map);
  }
 }
 #ifdef COH_BOUNDED_CONTINUATION_DIAGNOSTIC
 scenario_cleanup:
 totals(&d.continuation);if(!mode)CHECK(d.continuation.abort_reason==COH_INITIAL_ABORT_MESSAGE_LIMIT);
#endif
 free(data);coh_initial_capture_close(o.owner);CHECK(diagnostic(o.owner).local.opened_sockets==diagnostic(o.owner).local.closed_sockets);coh_initial_capture_destroy(o.owner);peer_close(&db);peer_close(&map);CHECK(!live_allocations);scenarios++;
}
int main(void){unsigned fds=descriptors();unsigned modes=5;
#ifdef COH_BOUNDED_CONTINUATION_DIAGNOSTIC
 modes=11;
#endif
 for(unsigned i=0;i<modes;i++){scenario_complete(i);}CHECK(fds==descriptors()&&!post_callbacks);printf("{\"passed\":true,\"checks\":%u,\"scenarios\":%u,\"synthetic_completion_double\":true,\"real_server\":false,\"post_message_bound\":128,\"post_duration_ms\":%u,\"whole_source_packet_qualification_claim\":false}\n",checks,scenarios,COH_INITIAL_POST_DURATION_MS);return 0;}
