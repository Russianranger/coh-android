/* New diagnostic suite only. Reuse the source-layout UDP fixture helpers;
 * accepted_db_fixture_main and its old scenarios are NEVER executed. */
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#define main accepted_db_fixture_main
#include "../dbclient/tests/test_db_session.c"
#undef main
#pragma GCC diagnostic pop
#include "coh_initial_capture.h"
#include "groups-fixtures.h"
#include <zlib.h>
/* Link-wrapped native allocation accounting; no LSan /proc dependency. */
static void *live_pointers[8192];static size_t live_allocations,allocation_calls,fail_allocation;
void *__real_malloc(size_t);void *__real_calloc(size_t,size_t);void __real_free(void*);
static void *record_allocation(void*p){if(p){CHECK(live_allocations<8192);live_pointers[live_allocations++]=p;}return p;}
void *__wrap_malloc(size_t n){allocation_calls++;if(fail_allocation==allocation_calls)return NULL;return record_allocation(__real_malloc(n));}
void *__wrap_calloc(size_t n,size_t bytes){allocation_calls++;if(fail_allocation==allocation_calls)return NULL;return record_allocation(__real_calloc(n,bytes));}
void __wrap_free(void*p){if(p){size_t i=0;for(;i<live_allocations;i++)if(live_pointers[i]==p)break;CHECK(i<live_allocations);live_pointers[i]=live_pointers[--live_allocations];}__real_free(p);}
typedef struct {CohInitialCapture*owner;unsigned calls,groups,allents,fail_kind,cancel_at;int cancelled;const uint8_t*expected;size_t bytes,bits;unsigned aligned;CohInitialCaptureEvent expired;} Observation;
static int cancel_now(void*p){return ((Observation*)p)->cancelled;}
static CohInitialCaptureDiagnostics diagnostic(CohInitialCapture*s){CohInitialCaptureDiagnostics d={0};coh_initial_capture_diagnostics(s,&d);return d;}
static CohStatus observe(void*opaque,const CohInitialCapture*owner,const CohInitialCaptureEvent*event){
 Observation*o=opaque;CHECK(owner==o->owner);o->calls++;CohInitialCaptureLease loan;CHECK(coh_initial_capture_lease(owner,event,&loan)==COH_OK);CHECK(loan.kind==event->kind&&loan.selected_dbid_owner_bound&&loan.selected_dbid==17&&loan.local_development_authorized);CHECK(!loan.source_generation_admitted&&!loan.complete_initial_character&&!loan.actor_publication&&!loan.ack_permitted&&!loan.world_authority);CHECK(loan.map_generation==1&&loan.selection_generation==1&&loan.selected_slot==0&&loan.map_id==5&&loan.map_link_id==17&&loan.db_session_generation==1&&loan.db_receipt_generation==1);CHECK(loan.connection_id==102&&loan.transport_version==5&&loan.reader.max_bytes==COH_NET_DECODED_MAX);CHECK(loan.message_generation&&loan.reader.cursor<loan.reader.bits);
 CohInitialCaptureEvent copied=*event;CohInitialCaptureLease old;memset(&old,0x5a,sizeof(old));CohInitialCaptureLease before=old;CHECK(coh_initial_capture_lease(owner,&copied,&old)==COH_STATE&&!memcmp(&old,&before,sizeof(old)));o->expired=copied;
 CHECK(coh_initial_capture_lease(owner,event,(CohInitialCaptureLease*)(uintptr_t)owner)==COH_INVALID);
 CHECK(coh_initial_capture_lease(owner,event,(CohInitialCaptureLease*)(uintptr_t)event)==COH_INVALID);
 CHECK(coh_initial_capture_lease(owner,event,(CohInitialCaptureLease*)(uintptr_t)loan.reader.bytes.data)==COH_INVALID);
 uint8_t beginning[16];CHECK(loan.reader.bytes.size>=sizeof(beginning));memcpy(beginning,loan.reader.bytes.data,sizeof(beginning));coh_initial_capture_diagnostics(owner,(CohInitialCaptureDiagnostics*)(uintptr_t)loan.reader.bytes.data);CHECK(!memcmp(beginning,loan.reader.bytes.data,sizeof(beginning)));
 CohInitialCaptureDiagnostics d=diagnostic(o->owner);CohLocalCharacters list;CohDbLogin policy;CHECK(coh_local_login_policy(&policy)==COH_OK);CHECK(coh_initial_capture_characters(owner,&list)==COH_STATE);CHECK(coh_initial_capture_choose_character(o->owner,0,116)==COH_STATE);CHECK(coh_initial_capture_begin(o->owner,&policy,"Fixture",201,202,116)==COH_STATE);CHECK(coh_initial_capture_service(o->owner,116,(CohCancel){0},observe,o,sizeof(*o))==COH_STATE);coh_initial_capture_close(o->owner);coh_initial_capture_cancel(o->owner);coh_initial_capture_destroy(o->owner);CohInitialCaptureDiagnostics after=diagnostic(o->owner);CHECK(!memcmp(&d,&after,sizeof(d)));
 if(event->kind==COH_INITIAL_CAPTURE_GROUPS){o->groups++;CHECK(o->groups==1&&loan.groups.consumed_bits==source_groups_minimal_world_packed_bits&&loan.reader.bits==source_groups_minimal_world_packed_bits);CHECK(loan.message_generation==loan.groups_message_generation);if(o->cancel_at==1)o->cancelled=1;}
 else{CHECK(event->kind==COH_INITIAL_CAPTURE_ALLENTS);o->allents++;CHECK(o->allents==1&&o->groups==1&&loan.message_generation>loan.groups_message_generation);CHECK(loan.reader.bytes.size==o->bytes&&loan.reader.bits==o->bits&&loan.reader.compressed==o->aligned&&!memcmp(loan.reader.bytes.data,o->expected,o->bytes));CHECK(loan.update.command==COH_REP_ALLENTS&&loan.update.full_update_id==7&&loan.update.odd_send==1);if(o->cancel_at==2)o->cancelled=1;}
 return o->fail_kind==(unsigned)event->kind?COH_IO:COH_OK;
}
static CohStatus service(Observation*o,uint64_t now){return coh_initial_capture_service(o->owner,now,(CohCancel){cancel_now,o},observe,o,sizeof(*o));}
static void ok(Observation*o,uint64_t now){CHECK(service(o,now)==COH_OK);}
static CohNetPacket read_target(Peer*p,CohNetEndpoint*target,int connecting){struct pollfd f={p->fd,POLLIN,0};CHECK(poll(&f,1,100)==1);uint8_t frame[COH_PROTOCOL_FRAME_MAX];struct sockaddr_in a;socklen_t size=sizeof(a);ssize_t n=recvfrom(p->fd,frame,sizeof(frame),0,(struct sockaddr*)&a,&size);CHECK(n>0);memcpy(target->address,&a.sin_addr.s_addr,4);target->port=ntohs(a.sin_port);CohNetPacket packet;CHECK(coh_net_frame_decode(5,NULL,0,connecting,(CohBytes){frame,(size_t)n},&packet)==COH_OK);return packet;}
static CohNetPacket application(Peer*p,unsigned cmd){CohNetPacket n={0};n.id=++p->id;CohProtocolBits b;CHECK(!coh_protocol_bits_init(&b,n.payload,sizeof(n.payload),0,1));CHECK(!coh_protocol_write_pack(&b,1,cmd));n.payload_bits=(uint32_t)b.bit_length;return n;}
static CohProtocolBits append(CohNetPacket*n){CohProtocolBits b;CHECK(!coh_protocol_bits_init(&b,n->payload,sizeof(n->payload),n->payload_bits,1));b.cursor=b.bit_length;return b;}
static void app_send(Peer*p,CohNetEndpoint to,CohNetPacket n,CohProtocolBits*b,uint32_t ack){if(b)n.payload_bits=(uint32_t)b->bit_length;n.ack_count=1;n.acks[0]=ack;frame_send(p,to,5,&n);}
static CohNetEndpoint setup(Observation*o,Peer*db,Peer*map,unsigned bad_groups){
 CohLocalConfig config=coh_local_default_config();config.db.transport.peer=db->endpoint;config.local_development_enabled=1;config.db.request_timeout_ms=2000;config.map.application_timeout_ms=2000;o->owner=coh_initial_capture_create(&config);CHECK(o->owner);CohDbLogin policy;CHECK(coh_local_login_policy(&policy)==COH_OK);CHECK(coh_initial_capture_begin(o->owner,&policy,"Fixture",101,102,100)==COH_OK);
 ok(o,100);CohNetEndpoint dbto;CohNetPacket first=read_target(db,&dbto,1);CohNetPacket reply=control(5,100,2,1,0);reply.ack_count=1;reply.acks[0]=first.id;frame_send(db,dbto,5,&reply);ok(o,101);CohNetPacket ack=frame_read(db,5,0);CHECK(command(&ack,5,1)==3);reply=control(5,101,4,0,0);reply.ack_count=1;reply.acks[0]=ack.id;frame_send(db,dbto,5,&reply);ok(o,102);drain_ack(db,5);ok(o,103);CohNetPacket request=frame_read(db,5,0);CHECK(command(&request,5,0)==COH_DB_LOGIN);
 peer_message(db,dbto,5,players0,players0_bits,0,request.id);ok(o,104);drain_ack(db,5);CohLocalCharacters list;CHECK(coh_initial_capture_characters(o->owner,&list)==COH_OK&&list.selectable_count==1);CHECK(coh_initial_capture_choose_character(o->owner,0,105)==COH_OK);ok(o,105);request=frame_read(db,5,0);CHECK(command(&request,5,0)==COH_DB_CHOOSE_PLAYER);
 reply=application(db,COH_DB_MAP_CONNECT);CohProtocolBits b=append(&reply);uint32_t fields[]={17,5,0x0100007fu,0,map->endpoint.port,7003,123456};for(unsigned i=0;i<7;i++)CHECK(!coh_protocol_write_pack(&b,1,fields[i]));app_send(db,dbto,reply,&b,request.id);ok(o,106);drain_ack(db,5);
 CohNetEndpoint mapto;first=read_target(map,&mapto,1);CHECK(first.connect);ok(o,107);CohNetPacket bye=frame_read(db,5,0);CHECK(command(&bye,5,1)==5);reply=control(5,++db->id,6,0,0);reply.ack_count=1;reply.acks[0]=bye.id;frame_send(db,dbto,5,&reply);reply=control(5,100,2,1,0);reply.ack_count=1;reply.acks[0]=first.id;frame_send(map,mapto,5,&reply);ok(o,108);ack=frame_read(map,5,0);CHECK(command(&ack,5,1)==3);reply=control(5,101,4,0,0);reply.ack_count=1;reply.acks[0]=ack.id;frame_send(map,mapto,5,&reply);ok(o,109);drain_ack(map,5);ok(o,110);request=frame_read(map,5,0);CHECK(command(&request,5,0)==COH_MAP_CONNECT);
 reply=application(map,COH_REP_CONNECT_MSG);b=append(&reply);CHECK(!coh_protocol_write_pack(&b,1,1));CHECK(!coh_protocol_write(&b,32,0));app_send(map,mapto,reply,&b,request.id);ok(o,111);drain_ack(map,5);ok(o,112);request=frame_read(map,5,0);CHECK(command(&request,5,0)==COH_MAP_REQSHORTCUTS);reply=application(map,COH_REP_SHORTCUTS);b=append(&reply);CHECK(!coh_protocol_write_pack(&b,1,UINT32_MAX));CHECK(!coh_protocol_write_pack(&b,1,0));app_send(map,mapto,reply,&b,request.id);ok(o,113);drain_ack(map,5);ok(o,114);request=frame_read(map,5,0);CHECK(command(&request,5,0)==COH_MAP_REQSCENE);
 peer_message(map,mapto,5,source_groups_minimal_world_packed,source_groups_minimal_world_packed_bits-bad_groups,0,request.id);return mapto;
}
static void fixture_scalar(CohProtocolBits*b,unsigned width,unsigned aligned,uint32_t value){CHECK(!coh_protocol_write(b,aligned?(width+7u)&~7u:width,value));}
static void fixture_packed(CohProtocolBits*b,unsigned aligned,uint32_t value){CHECK(!(aligned?coh_protocol_write(b,32,value):coh_protocol_write_pack(b,1,value)));}
static uint8_t *body(size_t bytes,unsigned aligned,unsigned bad_header,size_t*bits){
 uint8_t*data=calloc(1,bytes);CHECK(data);CohProtocolBits b;CHECK(!coh_protocol_bits_init(&b,data,bytes<128?bytes:128,0,1));fixture_packed(&b,aligned,COH_REP_ALLENTS);fixture_packed(&b,aligned,7);fixture_scalar(&b,1,aligned,bad_header?0:1);fixture_packed(&b,aligned,0);fixture_scalar(&b,32,aligned,123);fixture_scalar(&b,32,aligned,456);fixture_scalar(&b,1,aligned,1);fixture_scalar(&b,32,aligned,0x12345678);fixture_scalar(&b,32,aligned,0x23456789);*bits=aligned?bytes*8:b.bit_length;return data;
}
static void compressed_send(Peer*p,CohNetEndpoint to,const uint8_t*data,size_t bytes,uint32_t ack){
 uint8_t encoded[COH_NET_MESSAGE_MAX];uLongf size=sizeof(encoded)-8;memcpy(encoded,data,4);uint32_t tail=(uint32_t)bytes-4;for(unsigned i=0;i<4;i++)encoded[4+i]=(uint8_t)(tail>>(8*i));CHECK(compress2(encoded+8,&size,data+4,(uLong)bytes-4,9)==Z_OK);size+=8;CHECK(size<=COH_NET_MESSAGE_MAX);unsigned count=(unsigned)((size+1199)/1200);for(unsigned i=0;i<count;i++){CohNetPacket n={0};n.id=++p->id;n.compressed=1;if(count>1){n.sibling_id=++p->sibling-i;n.sibling_count=count;n.sibling_part=i;}size_t offset=(size_t)i*1200,nbytes=(size_t)size-offset;if(nbytes>1200)nbytes=1200;memcpy(n.payload,encoded+offset,nbytes);n.payload_bits=(uint32_t)nbytes*8;n.ack_count=1;n.acks[0]=ack;frame_send(p,to,5,&n);}}
static void quiet(Peer*p){struct pollfd f={p->fd,POLLIN,0};CHECK(poll(&f,1,0)==0);}
static void finish(Observation*o,Peer*db,Peer*map){CohInitialCaptureDiagnostics d=diagnostic(o->owner);CHECK(d.local.opened_sockets==2&&d.local.closed_sockets==2&&!d.source_generation_admitted&&!d.complete_initial_character&&!d.actor_publication&&!d.ack_permitted&&!d.world_authority);CohInitialCaptureLease lease;memset(&lease,0x5a,sizeof(lease));CohInitialCaptureLease before=lease;CHECK(coh_initial_capture_lease(o->owner,&o->expired,&lease)==COH_STATE&&!memcmp(&lease,&before,sizeof(lease)));CHECK(service(o,5000)==COH_STATE);coh_initial_capture_close(o->owner);coh_initial_capture_destroy(o->owner);peer_close(db);peer_close(map);CHECK(!live_allocations);scenarios++;}
static void scenario(unsigned which){
 Peer db=peer_open(),map=peer_open();Observation o={0};if(which==4)o.fail_kind=COH_INITIAL_CAPTURE_GROUPS;if(which==5)o.fail_kind=COH_INITIAL_CAPTURE_ALLENTS;if(which==6)o.cancel_at=1;if(which==12)o.cancel_at=2;CohNetEndpoint to=setup(&o,&db,&map,which==3);
 CohStatus s=service(&o,115);drain_ack(&map,5);
 if(which==3||which==4||which==6){CHECK(s==(which==3?COH_INVALID:which==4?COH_IO:COH_CANCELLED));CohInitialCaptureDiagnostics d=diagnostic(o.owner);CHECK(!d.reqallents_sent&&!d.raw_allents_observed);CHECK(d.groups_observed==(which==6));quiet(&map);finish(&o,&db,&map);return;}
 CHECK(s==COH_OK);CohInitialCaptureDiagnostics d=diagnostic(o.owner);CHECK(d.groups_observed&&d.groups_observations==1&&d.reqallents_sent==1&&d.phase==COH_INITIAL_CAPTURE_WAIT_ALLENTS);ok(&o,116);CohNetPacket request=frame_read(&map,5,0);CHECK(command(&request,5,0)==COH_MAP_REQALLENTS);quiet(&map);
 if(which==7){CHECK(service(&o,2115)==COH_STATE);d=diagnostic(o.owner);CHECK(d.failure==COH_INITIAL_CAPTURE_FAILURE_TIMEOUT&&d.groups_observed&&!d.raw_allents_observed);finish(&o,&db,&map);return;}
 if(which==8){o.cancelled=1;CHECK(service(&o,117)==COH_CANCELLED);finish(&o,&db,&map);return;}
 if(which==2){CohNetPacket unknown=application(&map,15);app_send(&map,to,unknown,NULL,request.id);CHECK(service(&o,117)==COH_UNSUPPORTED);d=diagnostic(o.owner);CHECK(d.failure==COH_INITIAL_CAPTURE_FAILURE_COMMAND&&d.groups_observed&&!d.raw_allents_observed);drain_ack(&map,5);quiet(&map);finish(&o,&db,&map);return;}
 size_t bits,bytes=which==1?65536:which==9?COH_NET_DECODED_MAX:which==10?COH_NET_DECODED_MAX+1:128;unsigned aligned=which==1||which==9||which==10;uint8_t*data=body(bytes,aligned,which==11,&bits);o.expected=data;o.bits=bits;o.bytes=(bits+7)/8;o.aligned=aligned;
 if(aligned)compressed_send(&map,to,data,bytes,request.id);else peer_message(&map,to,5,data,bits,0,request.id);
 s=service(&o,117);d=diagnostic(o.owner);
 if(which==10){CHECK(s==COH_LIMIT&&!o.allents&&d.groups_observed&&!d.raw_allents_observed);}
 else if(which==11){CHECK(s==COH_INVALID&&d.failure==COH_INITIAL_CAPTURE_FAILURE_HEADER&&!o.allents&&d.groups_observed);}
 else if(which==12){CHECK(s==COH_CANCELLED&&d.failure==COH_INITIAL_CAPTURE_FAILURE_CANCELLED&&o.allents==1&&d.groups_observed&&!d.raw_allents_observed);}
 else if(which==5){CHECK(s==COH_IO&&d.failure==COH_INITIAL_CAPTURE_FAILURE_OBSERVER&&o.allents==1&&d.groups_observed&&!d.raw_allents_observed);}
 else{CHECK(s==COH_UNSUPPORTED&&d.phase==COH_INITIAL_CAPTURED&&d.failure==COH_INITIAL_CAPTURE_FAILURE_NONE&&d.raw_allents_observed&&d.allents_observations==1&&o.allents==1&&d.allents_message_generation>d.groups_message_generation);CHECK(d.last_payload_bits==bits&&d.last_decoded_bytes==o.bytes&&d.last_byte_aligned==aligned);}
 drain_ack(&map,5);
 quiet(&map);free(data);finish(&o,&db,&map);
}
static void allocation_failure(void){CohLocalConfig c=coh_local_default_config();c.local_development_enabled=1;c.db.transport.peer=(CohNetEndpoint){{127,0,0,1},7000};for(unsigned i=1;i<=2;i++){fail_allocation=allocation_calls+i;CHECK(!coh_initial_capture_create(&c));CHECK(!live_allocations);fail_allocation=0;}}
#ifndef COH_INITIAL_CAPTURE_NO_MAIN
int main(void){unsigned before=descriptors();allocation_failure();for(unsigned i=0;i<13;i++)scenario(i);CHECK(descriptors()==before);printf("{\"passed\":true,\"checks\":%u,\"scenarios\":%u,\"actual_os_udp\":true,\"wrapped_native_allocations_balanced\":true,\"synthetic_source_layout_peers\":true,\"whole_original_allents_producer_executed\":false,\"real_server\":false,\"actor_publication\":false,\"source_generation_admitted\":false,\"ack_permitted\":false}\n",checks,scenarios);return 0;}

#endif
