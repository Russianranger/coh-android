/* Only new EDITMSG tests and directly affected capture-boundary controls run.
 * Existing helpers are reused; neither included historical main is invoked. */
#define _POSIX_C_SOURCE 200809L
#include "coh_initial_map.c"
#include "coh_initial_local.c"
#define COH_INITIAL_CAPTURE_NO_MAIN 1
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "test_initial_capture.c"
#pragma GCC diagnostic pop
#include "editmsg-fixtures.h"
static unsigned release_fault;
static Observation*release_cancel;
CohStatus __real_coh_net_udp_owned_release(CohNetUdp*,CohNetOwnedMessage*);
CohStatus __wrap_coh_net_udp_owned_release(CohNetUdp*u,CohNetOwnedMessage*n){CohStatus s=__real_coh_net_udp_owned_release(u,n);if(release_cancel){release_cancel->cancelled=1;release_cancel=NULL;}if(release_fault){release_fault=0;return COH_IO;}return s;}
static unsigned parser_cases;
static CohRepReader fixture_reader(unsigned index,size_t bits){
 CohRepReader r;CHECK(index<sizeof(editmsg_fixtures)/sizeof(editmsg_fixtures[0]));size_t full=editmsg_fixtures[index].bits;
 CHECK(coh_rep_reader_bounded(&r,(CohBytes){editmsg_fixtures[index].data,(full+7)/8},bits,editmsg_fixtures[index].aligned,COH_NET_DECODED_MAX)==COH_OK);
 uint32_t cmd;CHECK(coh_rep_pack(&r,1,&cmd)==COH_OK&&cmd==8);return r;
}
static void direct_parser(void){
 for(unsigned i=0;i<sizeof(editmsg_fixtures)/sizeof(editmsg_fixtures[0]);i++){
  CohRepReader r=fixture_reader(i,editmsg_fixtures[i].bits);IcPost out;memset(&out,0x5a,sizeof(out));IcPost before=out;
  CohStatus status=ic_editmsg(r,(CohCancel){0},&out);
  if(editmsg_fixtures[i].bytes<COH_INITIAL_EDIT_MESSAGE_BYTES_MAX)CHECK(status==COH_OK&&out.kind==IC_POST_EDITMSG&&(unsigned)out.type==editmsg_fixtures[i].type&&out.bytes==editmsg_fixtures[i].bytes);
  else CHECK(status==COH_LIMIT&&!memcmp(&out,&before,sizeof(out)));
  parser_cases++;
  if(editmsg_fixtures[i].bytes<=257){
   for(size_t bits=r.cursor;bits<r.bits;bits++){
    CohRepReader q=r;q.bits=bits;out=before;CHECK(ic_editmsg(q,(CohCancel){0},&out)==COH_INVALID&&!memcmp(&out,&before,sizeof(out)));parser_cases++;
   }
  }else for(unsigned tail=1;tail<=8;tail++){
   CohRepReader q=r;q.bits-=tail;out=before;CohStatus s=ic_editmsg(q,(CohCancel){0},&out);CHECK((s==COH_INVALID||s==COH_LIMIT)&&!memcmp(&out,&before,sizeof(out)));parser_cases++;
  }
  if(editmsg_fixtures[i].bytes<COH_INITIAL_EDIT_MESSAGE_BYTES_MAX){
   uint8_t bytes[16400];memset(bytes,0,sizeof(bytes));memcpy(bytes,r.bytes.data,r.bytes.size);r.bytes=(CohBytes){bytes,sizeof(bytes)};
   for(unsigned bit=0;bit<2;bit++){r.bits=editmsg_fixtures[i].bits+1;bytes[(r.bits-1)/8]|=(uint8_t)(bit<<((r.bits-1)&7));out=before;CHECK(ic_editmsg(r,(CohCancel){0},&out)==COH_INVALID&&!memcmp(&out,&before,sizeof(out)));parser_cases++;}
  }
 }
 /* In aligned mode a two-bit source scalar occupies a byte, but unused high
  * bits cannot introduce a new EditorMessageType. */
 uint8_t bad[8]={8,0,0,0,4,0};CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){bad,6},48,1,COH_NET_DECODED_MAX)==COH_OK);r.cursor=32;IcPost out={IC_POST_NONE,0,123},before=out;
 CHECK(ic_editmsg(r,(CohCancel){0},&out)==COH_INVALID&&!memcmp(&out,&before,sizeof(out)));parser_cases++;
}
static unsigned cancel_calls;
static int cancel_parser(void*unused){(void)unused;return ++cancel_calls==2;}
static void parser_cancel(void){IcPost out={IC_POST_NONE,0,123},before=out;CohRepReader r=fixture_reader(2,editmsg_fixtures[2].bits);cancel_calls=0;CHECK(ic_editmsg(r,(CohCancel){cancel_parser,NULL},&out)==COH_CANCELLED&&cancel_calls==2&&!memcmp(&out,&before,sizeof(out)));parser_cases++;}
static CohNetPacket wait_initial(Observation*o,Peer*db,Peer*map,CohNetEndpoint*to){
 *to=setup(o,db,map,0);ok(o,115);drain_ack(map,5);ok(o,116);CohNetPacket request=frame_read(map,5,0);CHECK(command(&request,5,0)==COH_MAP_REQALLENTS);quiet(map);return request;
}
static void edit_send(Peer*map,CohNetEndpoint to,unsigned index,uint32_t ack,unsigned truncated){
 if(editmsg_fixtures[index].aligned){CHECK(!truncated);compressed_send(map,to,editmsg_fixtures[index].data,(editmsg_fixtures[index].bits+7)/8,ack);}
 else peer_message(map,to,5,editmsg_fixtures[index].data,editmsg_fixtures[index].bits-truncated,0,ack);
}
static void assert_wait(Observation*o,unsigned count,unsigned type,unsigned bytes){CohInitialCaptureDiagnostics d=diagnostic(o->owner);CHECK(d.phase==COH_INITIAL_CAPTURE_WAIT_ALLENTS&&d.status==COH_OK&&d.failure==COH_INITIAL_CAPTURE_FAILURE_NONE&&d.groups_observed&&d.reqallents_sent==1&&!d.raw_allents_observed&&!d.allents_observations&&!d.first_failure.valid&&!d.refused_command_valid&&d.refused_command_kind==COH_INITIAL_CAPTURE_COMMAND_NONE);CHECK(d.edit_messages_handled==count&&(unsigned)d.edit_message_last_type==type&&d.edit_message_last_bytes==bytes&&o->calls==1&&!o->allents);}
static void send_allents(Observation*o,Peer*map,CohNetEndpoint to,uint32_t ack){size_t bits;uint8_t*data=body(128,0,0,&bits);o->expected=data;o->bits=bits;o->bytes=(bits+7)/8;peer_message(map,to,5,data,bits,0,ack);CHECK(service(o,119)==COH_UNSUPPORTED);CohInitialCaptureDiagnostics d=diagnostic(o->owner);CHECK(d.phase==COH_INITIAL_CAPTURED&&d.raw_allents_observed&&d.allents_observations==1&&o->allents==1&&!d.first_failure.valid&&!d.refused_command_valid);free(data);}
static void handled_then_allents(unsigned aligned,unsigned type){
 Peer db=peer_open(),map=peer_open();Observation o={0};CohNetEndpoint to;CohNetPacket request=wait_initial(&o,&db,&map,&to);unsigned index=(aligned*4+type)*5+2;uint64_t deadline=o.owner->map->request_ms;
 edit_send(&map,to,index,request.id,0);ok(&o,117);assert_wait(&o,1,type,257);CHECK(o.owner->map->request_ms==deadline);drain_ack(&map,5);quiet(&map);send_allents(&o,&map,to,request.id);CHECK(diagnostic(o.owner).edit_messages_handled==1);drain_ack(&map,5);quiet(&map);finish(&o,&db,&map);
}
static void post_edit_failure(unsigned which){
 Peer db=peer_open(),map=peer_open();Observation o={0};CohNetEndpoint to;CohNetPacket request=wait_initial(&o,&db,&map,&to);
 edit_send(&map,to,1,request.id,0);ok(&o,117);assert_wait(&o,1,0,1);drain_ack(&map,5);quiet(&map);
 CohStatus expected;CohInitialCaptureFailure why;CohInitialCaptureCommandKind kind;
 if(which==0){CohNetPacket n=application(&map,15);app_send(&map,to,n,NULL,request.id);expected=COH_UNSUPPORTED;why=COH_INITIAL_CAPTURE_FAILURE_COMMAND;kind=COH_INITIAL_CAPTURE_COMMAND_SERVER_GAME_CMDS;}
 else if(which==1){edit_send(&map,to,2,request.id,1);expected=COH_INVALID;why=COH_INITIAL_CAPTURE_FAILURE_PROTOCOL;kind=COH_INITIAL_CAPTURE_COMMAND_SERVER_EDITMSG;}
 else if(which==2){edit_send(&map,to,20+4,request.id,0);expected=COH_LIMIT;why=COH_INITIAL_CAPTURE_FAILURE_PROTOCOL;kind=COH_INITIAL_CAPTURE_COMMAND_SERVER_EDITMSG;}
 else if(which==3){edit_send(&map,to,0,request.id,0);release_fault=1;expected=COH_IO;why=COH_INITIAL_CAPTURE_FAILURE_RELEASE;kind=COH_INITIAL_CAPTURE_COMMAND_SERVER_EDITMSG;}
 else if(which==4){edit_send(&map,to,2,request.id,1);release_fault=1;expected=COH_INVALID;why=COH_INITIAL_CAPTURE_FAILURE_PROTOCOL;kind=COH_INITIAL_CAPTURE_COMMAND_SERVER_EDITMSG;}
 else if(which==5){CohNetPacket broken={0};broken.id=++map.id;broken.compressed=1;broken.payload_bits=128;broken.payload[0]=8;broken.payload[4]=12;broken.ack_count=1;broken.acks[0]=request.id;frame_send(&map,to,5,&broken);expected=COH_INVALID;why=COH_INITIAL_CAPTURE_FAILURE_PROTOCOL;kind=COH_INITIAL_CAPTURE_COMMAND_NONE;}
 else {edit_send(&map,to,0,request.id,0);release_cancel=&o;expected=COH_CANCELLED;why=COH_INITIAL_CAPTURE_FAILURE_CANCELLED;kind=COH_INITIAL_CAPTURE_COMMAND_SERVER_EDITMSG;}
 CHECK(service(&o,118)==expected);CohInitialCaptureDiagnostics d=diagnostic(o.owner);CHECK(d.edit_messages_handled==1&&d.edit_message_last_bytes==1&&d.edit_message_last_type==COH_INITIAL_EDIT_LOW_PRIORITY&&!o.allents&&!d.raw_allents_observed&&d.refused_command_kind==kind&&d.refused_command_valid==(kind!=COH_INITIAL_CAPTURE_COMMAND_NONE));first_failure(d,expected,why,COH_LOCAL_MAP_CONNECTING,COH_DB_CLOSED,COH_MAP_SCENE_INCOMPLETE);drain_ack(&map,5);quiet(&map);finish(&o,&db,&map);
}
static void queued_post_edit(unsigned which){
 Peer db=peer_open(),map=peer_open();Observation o={0};CohNetEndpoint to;CohNetPacket request=wait_initial(&o,&db,&map,&to);edit_send(&map,to,1,request.id,0);
 size_t bits=0;uint8_t*data=NULL;
 if(which==0||which==3){data=body(128,0,0,&bits);o.expected=data;o.bits=bits;o.bytes=(bits+7)/8;peer_message(&map,to,5,data,bits,0,request.id);}
 else if(which==1){CohNetPacket n=application(&map,15);app_send(&map,to,n,NULL,request.id);}
 else {CohNetPacket n={0};n.id=++map.id;n.compressed=1;n.payload_bits=128;n.payload[0]=8;n.payload[4]=12;n.ack_count=1;n.acks[0]=request.id;frame_send(&map,to,5,&n);}
 if(which==3){o.owner->local->map->config.message_budget=1;ok(&o,117);assert_wait(&o,1,0,1);}
 CohStatus expected=which==2?COH_INVALID:COH_UNSUPPORTED;CHECK(service(&o,118)==expected);CohInitialCaptureDiagnostics d=diagnostic(o.owner);CHECK(d.edit_messages_handled==1&&d.edit_message_last_bytes==1);
 if(which==0||which==3)CHECK(d.phase==COH_INITIAL_CAPTURED&&d.raw_allents_observed&&o.allents==1&&!d.refused_command_valid);
 else {CHECK(!o.allents&&!d.raw_allents_observed&&d.refused_command_valid==(which==1)&&d.refused_command_kind==(which==1?COH_INITIAL_CAPTURE_COMMAND_SERVER_GAME_CMDS:COH_INITIAL_CAPTURE_COMMAND_NONE));first_failure(d,expected,which==1?COH_INITIAL_CAPTURE_FAILURE_COMMAND:COH_INITIAL_CAPTURE_FAILURE_PROTOCOL,COH_LOCAL_MAP_CONNECTING,COH_DB_CLOSED,COH_MAP_SCENE_INCOMPLETE);}
 drain_ack(&map,5);quiet(&map);free(data);finish(&o,&db,&map);
}
static void count_and_deadline(unsigned deadline){
 Peer db=peer_open(),map=peer_open();Observation o={0};CohNetEndpoint to;CohNetPacket request=wait_initial(&o,&db,&map,&to);uint64_t begun=o.owner->map->request_ms;
 unsigned count=deadline?1:COH_INITIAL_EDIT_MESSAGES_MAX;
 for(unsigned i=0;i<count;i++){edit_send(&map,to,0,request.id,0);ok(&o,deadline?2114:117+i);assert_wait(&o,i+1,0,0);CHECK(o.owner->map->request_ms==begun);drain_ack(&map,5);quiet(&map);}
 if(!deadline)edit_send(&map,to,0,request.id,0);
 CHECK(service(&o,deadline?2115:140)==(deadline?COH_STATE:COH_LIMIT));CohInitialCaptureDiagnostics d=diagnostic(o.owner);CHECK(d.edit_messages_handled==count&&!d.raw_allents_observed);first_failure(d,deadline?COH_STATE:COH_LIMIT,deadline?COH_INITIAL_CAPTURE_FAILURE_TIMEOUT:COH_INITIAL_CAPTURE_FAILURE_PROTOCOL,COH_LOCAL_MAP_CONNECTING,COH_DB_CLOSED,COH_MAP_SCENE_INCOMPLETE);CHECK(d.refused_command_kind==(deadline?COH_INITIAL_CAPTURE_COMMAND_NONE:COH_INITIAL_CAPTURE_COMMAND_SERVER_EDITMSG));if(!deadline)drain_ack(&map,5);quiet(&map);finish(&o,&db,&map);
}
static void phase_guards(void){
 Peer db=peer_open(),map=peer_open();Observation o={0};CohNetEndpoint to;CohNetPacket request=wait_initial(&o,&db,&map,&to);(void)request;CohInitialMap*x=o.owner->map;
 CohNetOwnedMessage n={0};n.payload=(uint8_t*)editmsg_fixtures[0].data;n.payload_bytes=(editmsg_fixtures[0].bits+7)/8;n.payload_bits=(uint32_t)editmsg_fixtures[0].bits;n.generation=x->d.groups_message_generation+1;IcPost out={IC_POST_NONE,0,321},before=out;
 for(unsigned i=0;i<6;i++){
  CohInitialCapturePhase phase=x->d.phase;uint32_t requests=x->d.reqallents_sent;unsigned groups=x->d.groups_observed;uint64_t gen=n.generation;
  if(i==0)x->d.phase=COH_INITIAL_CAPTURE_WAIT_GROUPS;else if(i==1)x->d.phase=COH_INITIAL_CAPTURED;else if(i==2)x->d.reqallents_sent=0;else if(i==3)x->d.reqallents_sent=2;else if(i==4)x->d.groups_observed=0;else n.generation=x->d.groups_message_generation;
  CHECK(ic_initial(x,&n,(CohCancel){0},&out)==COH_STATE&&!memcmp(&out,&before,sizeof(out))&&!x->d.edit_messages_handled);
  x->d.phase=phase;x->d.reqallents_sent=requests;x->d.groups_observed=groups;n.generation=gen;
 }
 x->d.failure=COH_INITIAL_CAPTURE_FAILURE_NONE;coh_initial_capture_timeout(o.owner);finish(&o,&db,&map);
}
int main(void){unsigned before=descriptors();direct_parser();parser_cancel();for(unsigned a=0;a<2;a++)for(unsigned t=0;t<4;t++)handled_then_allents(a,t);for(unsigned i=0;i<7;i++)post_edit_failure(i);for(unsigned i=0;i<4;i++)queued_post_edit(i);count_and_deadline(0);count_and_deadline(1);phase_guards();CHECK(descriptors()==before&&!live_allocations&&!release_fault&&!release_cancel);printf("{\"passed\":true,\"checks\":%u,\"direct_parser_cases\":%u,\"transaction_scenarios\":%u,\"capture_owner_bytes\":%zu,\"map_wrapper_bytes\":%zu,\"diagnostics_bytes\":%zu,\"ordinary_local_bytes\":%zu,\"ordinary_map_bytes\":%zu,\"lease_bytes\":%zu,\"new_packet_or_text_allocations\":false,\"actual_os_udp_synthetic_peers\":true,\"native_allocations_balanced\":true,\"real_server\":false,\"source_generation_admitted\":false,\"actor_publication\":false,\"ack_permitted\":false}\n",checks,parser_cases,scenarios,sizeof(CohInitialCapture),sizeof(CohInitialMap),sizeof(CohInitialCaptureDiagnostics),sizeof(CohLocal),sizeof(CohMapClient),sizeof(CohInitialCaptureLease));return 0;}
