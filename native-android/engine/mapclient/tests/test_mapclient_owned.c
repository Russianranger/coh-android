#define main db_session_regression_main
#include "../../dbclient/tests/test_db_session.c"
#undef main
#include "coh_mapclient_owned_private.h"
#include "groups-fixtures.h"
static unsigned fail_map_allocation;
void *__real_calloc(size_t,size_t);
void *__wrap_calloc(size_t n,size_t size){if(fail_map_allocation){fail_map_allocation=0;return NULL;}return __real_calloc(n,size);}
static CohDbHandoffOwner*make_owner(OwnerMemory*memory,unsigned development){
 Peer peer=peer_open();CohDbSessionConfig c=configuration(&peer,5,0);CohDbSession*s=coh_db_session_create(&c);CHECK(s);CohNetPacket request=handshake_uid(s,&peer,5,500,100,development?0:12345);CohNetEndpoint target=local(s);
 peer_message(&peer,target,5,players0,players0_bits,0,request.id);CHECK(coh_db_session_service(s,104,(CohCancel){0})==COH_OK);drain_ack(&peer,5);CHECK(coh_db_session_choose(s,0,0x0100007f,0,105)==COH_OK);CHECK(coh_db_session_service(s,105,(CohCancel){0})==COH_OK);request=frame_read(&peer,5,0);
 peer_message(&peer,target,5,map0,map0_bits,0,request.id);CHECK(coh_db_session_service(s,106,(CohCancel){0})==COH_OK);drain_ack(&peer,5);
 CohDbHandoffAllocator allocator={memory,owner_test_allocate,owner_test_free};CohDbHandoffOwner*owner=NULL;CHECK(coh_db_session_take_handoff_owner_alloc(s,&allocator,&owner)==COH_OK&&owner);coh_db_session_destroy(s);peer_close(&peer);return owner;
}
static CohMapConfig map_config(Peer*p){CohMapConfig c;memset(&c,0,sizeof(c));c.udp=configuration(p,5,0).transport;c.application_timeout_ms=2000;c.message_budget=16;return c;}
static Peer map_peer(void){Peer p=peer_open();CHECK(!close(p.fd));p.fd=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);CHECK(p.fd>=0);p.endpoint.port=7002;struct sockaddr_in a=addr(p.endpoint);CHECK(!bind(p.fd,(struct sockaddr*)&a,sizeof(a)));CHECK(!fcntl(p.fd,F_SETFL,O_NONBLOCK));return p;}
static CohMapDiagnostics map_diag(CohMapClient*m){CohMapDiagnostics d;memset(&d,0,sizeof(d));coh_map_client_diagnostics(m,&d);return d;}
static CohNetEndpoint map_local(CohMapClient*m){CohNetEndpoint e;CHECK(coh_map_client_local_endpoint(m,&e)==COH_OK);return e;}
static void map_drain(Peer*p){struct pollfd f={p->fd,POLLIN,0};while(poll(&f,1,0)==1){CohNetPacket a=frame_read(p,5,0);CHECK(command(&a,5,1)==0);}}
static CohNetPacket map_command(Peer*p,unsigned wanted){for(unsigned i=0;i<16;i++){CohNetPacket a=frame_read(p,5,0);unsigned v=command(&a,5,0);if(v==wanted)return a;CHECK(v==0);}CHECK(0);return(CohNetPacket){0};}
static unsigned callback_count;
static void map_observe(void*ctx,const CohMapSceneObservation*e){CohMapClient*m=ctx;callback_count++;CohMapSceneLease lease;CHECK(coh_map_client_scene_lease(m,e,&lease)==COH_OK);CHECK(lease.selected_dbid==17&&lease.selected_dbid_owner_bound&&lease.db_session_generation==1&&lease.db_receipt_generation==1&&!lease.source_generation_admitted&&!lease.world_authority);CHECK(lease.message_id==104&&lease.connection_id==900);}
static void complete_map(CohMapClient*m,Peer*p){
 uint64_t now=200;CHECK(coh_map_client_service(m,now,(CohCancel){0})==COH_OK);CohNetPacket first=frame_read(p,5,1),reply=control(5,100,2,1,0);reply.ack_count=1;reply.acks[0]=first.id;frame_send(p,map_local(m),5,&reply);CHECK(coh_map_client_service(m,++now,(CohCancel){0})==COH_OK);CohNetPacket ack=frame_read(p,5,0);reply=control(5,101,4,0,0);reply.ack_count=1;reply.acks[0]=ack.id;frame_send(p,map_local(m),5,&reply);CHECK(coh_map_client_service(m,++now,(CohCancel){0})==COH_OK);map_drain(p);CHECK(coh_map_client_service(m,++now,(CohCancel){0})==COH_OK);CohNetPacket connect=map_command(p,COH_MAP_CONNECT);
 CohProtocolBits b;uint32_t v;CHECK(coh_protocol_bits_init(&b,connect.payload,sizeof(connect.payload),connect.payload_bits,0)==COH_OK);CHECK(coh_protocol_read_pack(&b,1,&v)==COH_OK&&v==COH_MAP_CONNECT);CHECK(coh_protocol_read_pack(&b,1,&v)==COH_OK&&v==123456);
 memset(&reply,0,sizeof(reply));reply.id=102;CHECK(coh_protocol_bits_init(&b,reply.payload,sizeof(reply.payload),0,1)==COH_OK);CHECK(coh_protocol_write_pack(&b,1,COH_REP_CONNECT_MSG)==COH_OK);CHECK(coh_protocol_write_pack(&b,1,1)==COH_OK);CHECK(coh_protocol_write(&b,32,0)==COH_OK);reply.payload_bits=(uint32_t)b.bit_length;reply.ack_count=1;reply.acks[0]=connect.id;frame_send(p,map_local(m),5,&reply);CHECK(coh_map_client_service(m,++now,(CohCancel){0})==COH_OK);map_drain(p);CHECK(coh_map_client_service(m,++now,(CohCancel){0})==COH_OK);CohNetPacket request=map_command(p,COH_MAP_REQSHORTCUTS);
 memset(&reply,0,sizeof(reply));reply.id=103;CHECK(coh_protocol_bits_init(&b,reply.payload,sizeof(reply.payload),0,1)==COH_OK);CHECK(coh_protocol_write_pack(&b,1,COH_REP_SHORTCUTS)==COH_OK);CHECK(coh_protocol_write_pack(&b,1,UINT32_MAX)==COH_OK);CHECK(coh_protocol_write_pack(&b,1,0)==COH_OK);reply.payload_bits=(uint32_t)b.bit_length;reply.ack_count=1;reply.acks[0]=request.id;frame_send(p,map_local(m),5,&reply);CHECK(coh_map_client_service(m,++now,(CohCancel){0})==COH_OK);map_drain(p);CHECK(coh_map_client_service(m,++now,(CohCancel){0})==COH_OK);request=map_command(p,COH_MAP_REQSCENE);
 memset(&reply,0,sizeof(reply));reply.id=104;reply.payload_bits=source_groups_minimal_world_packed_bits;memcpy(reply.payload,source_groups_minimal_world_packed,(reply.payload_bits+7)/8);reply.ack_count=1;reply.acks[0]=request.id;frame_send(p,map_local(m),5,&reply);CHECK(coh_map_client_service_observed(m,++now,(CohCancel){0},map_observe,m)==COH_UNSUPPORTED);map_drain(p);CHECK(callback_count&&map_diag(m).phase==COH_MAP_SCENE_INCOMPLETE&&!map_diag(m).character_identity_verified&&map_diag(m).udp.link.owned_retained_bytes==0);
}
typedef struct {unsigned calls,at;} Stop;
static int stop_at(void*ctx){Stop*s=ctx;return ++s->calls==s->at;}
int main(void){
 unsigned before=descriptors();
 for(unsigned which=0;which<12;which++){
  OwnerMemory memory={0};CohDbHandoffOwner*owner=make_owner(&memory,which==1);CohDbHandoffMetadata md;CHECK(coh_db_handoff_owner_metadata(owner,&md)==COH_OK&&!md.claimed&&!md.retired);
  Peer peer=map_peer();CohMapConfig c=map_config(&peer);CohMapClient*m=coh_map_client_create(&c);CHECK(m);CohMapOwnedBegin o={1,1,900,0,200,1};CHECK(coh_map_client_begin_owned(m,owner,(const CohMapOwnedBegin*)m,NULL)==COH_INVALID);CHECK(coh_map_client_begin_owned(m,owner,&o,(const CohCancel*)&o)==COH_INVALID);CohMapOwnedBegin wrong=o;wrong.expected_db_session_generation=2;CHECK(coh_map_client_begin_owned(m,owner,&wrong,NULL)==COH_STATE);wrong=o;wrong.expected_selection_generation=2;CHECK(coh_map_client_begin_owned(m,owner,&wrong,NULL)==COH_STATE);wrong=o;wrong.endpoint_authorized=0;CHECK(coh_map_client_begin_owned(m,owner,&wrong,NULL)==COH_STATE);CHECK(coh_db_handoff_owner_metadata(owner,&md)==COH_OK&&!md.claimed&&!md.retired);
  if(which==2||which==3){Stop stop={0,which==2?1u:2u};CohCancel cancel={.poll=stop_at,.context=&stop};CHECK(coh_map_client_begin_owned(m,owner,&o,&cancel)==COH_CANCELLED);CHECK(coh_db_handoff_owner_metadata(owner,&md)==COH_OK&&md.retired&&md.claimed==(which==3));CHECK(!map_diag(m).selected_dbid_owner_bound);}
  else if(which==4){c.udp.peer.port=7001;coh_map_client_destroy(m);m=coh_map_client_create(&c);CHECK(m);CHECK(coh_map_client_begin_owned(m,owner,&o,NULL)==COH_INVALID);CHECK(coh_db_handoff_owner_metadata(owner,&md)==COH_OK&&md.claimed&&md.retired);}
  else if(which==10){fail_map_allocation=1;CHECK(coh_map_client_begin_owned(m,owner,&o,NULL)==COH_LIMIT&&!fail_map_allocation);CHECK(coh_db_handoff_owner_metadata(owner,&md)==COH_OK&&md.claimed&&md.retired&&!map_diag(m).selected_dbid_owner_bound);}
  else{
   CHECK(coh_map_client_begin_owned(m,owner,&o,NULL)==COH_OK);CHECK(coh_db_handoff_owner_metadata(owner,&md)==COH_OK&&md.claimed&&!md.retired);CHECK(map_diag(m).selected_dbid_owner_bound&&map_diag(m).selected_dbid==17&&!map_diag(m).character_identity_verified);CohDbHandoffMetadata bound;CHECK(coh_map_client_handoff_metadata(m,&bound)==COH_OK&&bound.selected_dbid==17&&bound.session_generation==1&&bound.local_development_auth==(which==1));CHECK(coh_map_client_handoff_metadata(m,(CohDbHandoffMetadata*)m)==COH_INVALID);CHECK(coh_map_client_begin_owned(m,owner,&o,NULL)==COH_STATE);
   if(which<2){coh_db_handoff_owner_release(owner);owner=NULL;CHECK(!memory.freed);complete_map(m,&peer);coh_map_client_close(m);CHECK(memory.freed==1);}
   else if(which==5){coh_map_client_suspend(m);}
   else if(which==6){complete_map(m,&peer);CHECK(coh_map_client_disconnect(m,209)==COH_OK);}
   else if(which==7){coh_db_handoff_owner_retire(owner);CHECK(!map_diag(m).selected_dbid_owner_bound);CHECK(coh_map_client_service(m,200,(CohCancel){0})==COH_STATE&&map_diag(m).phase==COH_MAP_FAILED);}
   else if(which==8){CHECK(coh_map_client_service(m,2201,(CohCancel){0})==COH_STATE);}
   else if(which==11){CHECK(coh_map_client_service(m,200,(CohCancel){.poll=cancelled})==COH_CANCELLED&&!map_diag(m).selected_dbid_owner_bound);}
   else{coh_map_client_destroy(m);m=NULL;}
  }
  if(m){coh_map_client_close(m);CHECK(!map_diag(m).selected_dbid_owner_bound);coh_map_client_destroy(m);}if(owner){CHECK(coh_db_handoff_owner_metadata(owner,&md)==COH_OK&&md.retired);CHECK(!memory.freed);coh_db_handoff_owner_release(owner);}CHECK(memory.freed==1);peer_close(&peer);CHECK(descriptors()==before);
 }
 printf("{\"passed\":true,\"checks\":%u,\"actual_os_udp\":true,\"scripted_peer_only\":true,\"owned_callbacks\":%u,\"character_identity_verified\":false,\"world_authority\":false,\"crypto_auth_verified\":false}\n",checks,callback_count);return 0;
}
