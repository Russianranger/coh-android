/* Reuse complete DB socket lifecycle tests with newly source-qualified packets. */
#define main coh_db_existing_session_main
#include "../dbclient/tests/test_db_session.c"
#undef main
static void identity_refusal(unsigned which){
 Peer peer=peer_open();CohDbSessionConfig c=configuration(&peer,5,0);CohDbSession*s=coh_db_session_create(&c);CHECK(s);CohNetPacket request=handshake(s,&peer,5,2001+which,100);CohNetEndpoint target=local(s);
 peer_message(&peer,target,5,players0,players0_bits,0,request.id);CHECK(coh_db_session_service(s,105,(CohCancel){0})==COH_OK);drain_ack(&peer,5);CHECK(coh_db_session_phase(s)==COH_DB_CHARACTERS);
 if(which!=2){CHECK(coh_db_session_choose(s,0,0x0100007f,0,106)==COH_OK);CHECK(coh_db_session_service(s,106,(CohCancel){0})==COH_OK);request=frame_read(&peer,5,0);}
 const uint8_t*wire=which==0?identity_zero:which==1?identity_high:map0;unsigned bits=which==0?identity_zero_bits:which==1?identity_high_bits:map0_bits;
 peer_message(&peer,target,5,wire,bits,0,request.id);CHECK(coh_db_session_service(s,107,(CohCancel){0})==COH_STATE);CHECK(coh_db_session_phase(s)==COH_DB_FAILED);
 CohDbSessionHandoff out,prior;memset(&out,0xa5,sizeof(out));prior=out;CHECK(coh_db_session_take_handoff(s,&out)==COH_STATE);CHECK(!memcmp(&out,&prior,sizeof(out)));
 CohDbSessionDiagnostics d;coh_db_session_diagnostics(s,&d);CHECK(d.handoffs==0&&d.malformed==1&&d.transport.sockets_opened==d.transport.sockets_closed);coh_db_session_destroy(s);peer_close(&peer);scenarios++;
}
static void identity_positive(unsigned maximum){
 Peer peer=peer_open();CohDbSessionConfig c=configuration(&peer,5,0);CohDbSession*s=coh_db_session_create(&c);CHECK(s);CohNetPacket request=handshake(s,&peer,5,3001+maximum,100);CohNetEndpoint target=local(s);
 peer_message(&peer,target,5,players0,players0_bits,0,request.id);CHECK(coh_db_session_service(s,105,(CohCancel){0})==COH_OK);drain_ack(&peer,5);CHECK(coh_db_session_choose(s,0,0,0,106)==COH_OK);CHECK(coh_db_session_service(s,106,(CohCancel){0})==COH_OK);request=frame_read(&peer,5,0);
 peer_message(&peer,target,5,maximum?identity_max:identity_one,maximum?identity_max_bits:identity_one_bits,0,request.id);CHECK(coh_db_session_service(s,107,(CohCancel){0})==COH_OK);drain_ack(&peer,5);CohDbSessionHandoff h;CHECK(coh_db_session_take_handoff(s,&h)==COH_OK);CHECK(h.selected_dbid==(maximum?INT32_MAX:1u)&&h.selected_slot==0&&h.selection_generation==1);CohDbSessionHandoff prior=h;CHECK(coh_db_session_take_handoff(s,&h)==COH_STATE&&!memcmp(&prior,&h,sizeof(h)));coh_db_session_suspend(s);coh_db_session_destroy(s);peer_close(&peer);scenarios++;
}
int main(void){CHECK(coh_db_existing_session_main()==0);unsigned before=descriptors();for(unsigned i=0;i<3;i++)identity_refusal(i);identity_positive(0);identity_positive(1);CHECK(before==descriptors());printf("{\"passed\":true,\"checks\":%u,\"socket_scenarios\":%u,\"new_identity_refusals\":3,\"boundary_identity_successes\":2,\"opaque_owner_selected_dbid\":true,\"real_server\":false,\"actor_or_ack\":false}\n",checks,scenarios);return 0;}
