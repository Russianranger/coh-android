/* Direct internal fault controls supplement the public scripted UDP suite.
 * No test hook or caller-populated admission API is compiled into production. */
#define _POSIX_C_SOURCE 200809L
#include "coh_initial_map.c"
#include "coh_initial_local.c"
#define COH_INITIAL_CAPTURE_NO_MAIN 1
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "test_initial_capture.c"
#pragma GCC diagnostic pop
static CohStatus never_observe(void*opaque,const CohInitialCaptureEvent*event){(void)event;(*(unsigned*)opaque)++;return COH_OK;}
static void alias_controls(void){
 CohLocalConfig c=coh_local_default_config();c.local_development_enabled=1;c.db.transport.peer=(CohNetEndpoint){{127,0,0,1},7000};CohInitialCapture*x=coh_initial_capture_create(&c);CHECK(x);
 CohInitialCapture old=*x;CohLocal local_before=*x->local;
 CHECK(coh_initial_capture_characters(x,(CohLocalCharacters*)(void*)x)==COH_INVALID);
 CHECK(coh_initial_capture_characters(x,(CohLocalCharacters*)(void*)x->local)==COH_INVALID);
 CHECK(!memcmp(x,&old,sizeof(old))&&!memcmp(x->local,&local_before,sizeof(local_before)));
 coh_initial_capture_destroy(x);CHECK(!live_allocations);
 CohMapClient map={0};map.diag.phase=COH_MAP_NET_CONNECTING;map.last_connect_id=1;fail_allocation=allocation_calls+1;CHECK(!coh_initial_map_create(&map));fail_allocation=0;CHECK(!live_allocations);CohInitialMap state={0};uint8_t payload[64]={0};CohNetOwnedMessage n={0};unsigned calls=0,owner=0;n.payload=payload;n.payload_bytes=sizeof(payload);state.map=&map;state.message=&n;state.owner=&owner;state.owner_bytes=sizeof(owner);state.context=&n;state.context_bytes=sizeof(n);state.observer=never_observe;state.observer_context=&calls;
 CHECK(ic_observe(&state,COH_INITIAL_CAPTURE_ALLENTS)==COH_INVALID&&!calls);
 state.context=&calls;state.context_bytes=sizeof(calls);state.owner=&n;state.owner_bytes=sizeof(n);CHECK(ic_observe(&state,COH_INITIAL_CAPTURE_ALLENTS)==COH_INVALID&&!calls);
}
static void owner_fault(unsigned which){
 Peer db=peer_open(),map=peer_open();Observation o={0};setup(&o,&db,&map,0);
 CohMapClient*m=o.owner->local->map;
 if(which==0)m->diag.scene_structures=1;else if(which==1)m->diag.generation++;
 CohStatus status=service(&o,115);
 if(which<2){CHECK(status==COH_STATE&&!o.groups&&!diagnostic(o.owner).reqallents_sent);if(which==0)drain_ack(&map,5);finish(&o,&db,&map);return;}
 CHECK(status==COH_OK);drain_ack(&map,5);CHECK(diagnostic(o.owner).groups_observed);
 if(which==2)coh_db_handoff_owner_retire(m->handoff_owner);
 else if(which==3)m->diag.selection_generation++;
 else m->config.udp.peer.address[0]=10;
 CHECK(service(&o,116)==COH_STATE);CohInitialCaptureDiagnostics d=diagnostic(o.owner);CHECK(d.groups_observed&&!d.raw_allents_observed&&d.failure==COH_INITIAL_CAPTURE_FAILURE_OWNER&&d.reqallents_sent==1);finish(&o,&db,&map);
}
int main(void){unsigned before=descriptors();alias_controls();for(unsigned i=0;i<5;i++)owner_fault(i);CHECK(descriptors()==before&&!live_allocations);printf("{\"passed\":true,\"checks\":%u,\"owner_fault_scenarios\":%u,\"native_allocations_balanced\":true,\"capture_owner_bytes\":%zu,\"map_wrapper_bytes\":%zu,\"ordinary_local_bytes\":%zu,\"ordinary_map_bytes\":%zu,\"lease_bytes\":%zu,\"real_server\":false,\"actor_publication\":false,\"ack_permitted\":false}\n",checks,scenarios,sizeof(CohInitialCapture),sizeof(CohInitialMap),sizeof(CohLocal),sizeof(CohMapClient),sizeof(CohInitialCaptureLease));return 0;}
