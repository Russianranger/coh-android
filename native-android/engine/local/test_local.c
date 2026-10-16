/* Exercise real DB/Map owners over actual UDP, using the independently
 * pinned original bit writer's source-layout player list. No shard/login
 * success claim is inferred from this controlled scripted peer. */
#define main accepted_db_test_main
#include "../dbclient/tests/test_db_session.c"
#undef main
#include "coh_local.h"
#include "groups-fixtures.h"
static CohLocalDiagnostics diag(CohLocal *s){CohLocalDiagnostics d={0};coh_local_diagnostics(s,&d);return d;}
static CohNetPacket read_target(Peer *p,CohNetEndpoint *target,int connecting){
    struct pollfd f={p->fd,POLLIN,0};CHECK(poll(&f,1,100)==1);
    uint8_t frame[COH_PROTOCOL_FRAME_MAX];struct sockaddr_in a;socklen_t length=sizeof(a);
    ssize_t n=recvfrom(p->fd,frame,sizeof(frame),0,(struct sockaddr*)&a,&length);CHECK(n>0);
    memcpy(target->address,&a.sin_addr.s_addr,4);target->port=ntohs(a.sin_port);
    CohNetPacket packet;CHECK(coh_net_frame_decode(5,NULL,0,connecting,(CohBytes){frame,(size_t)n},&packet)==COH_OK);return packet;
}
static void service_ok(CohLocal *s,uint64_t now){CHECK(coh_local_service(s,now,(CohCancel){0})==COH_OK);}
static CohNetPacket connect_peer(CohLocal *s,Peer *p,CohNetEndpoint *target,uint64_t now,int already_started){
    if(!already_started)service_ok(s,now);
    CohNetPacket first=read_target(p,target,1);CHECK(first.connect&&command(&first,5,1)==1);
    CohNetPacket reply=control(5,100,2,1,0);reply.ack_count=1;reply.acks[0]=first.id;frame_send(p,*target,5,&reply);
    service_ok(s,now+1);CohNetPacket ack=frame_read(p,5,0);CHECK(command(&ack,5,1)==3);
    reply=control(5,101,4,0,0);reply.ack_count=1;reply.acks[0]=ack.id;frame_send(p,*target,5,&reply);
    service_ok(s,now+2);drain_ack(p,5);service_ok(s,now+3);return frame_read(p,5,0);
}
static CohNetPacket application(Peer *p,unsigned cmd){
    CohNetPacket v;memset(&v,0,sizeof(v));v.id=++p->id;
    CohProtocolBits b;CHECK(!coh_protocol_bits_init(&b,v.payload,sizeof(v.payload),0,1));
    CHECK(!coh_protocol_write_pack(&b,1,cmd));v.payload_bits=(uint32_t)b.bit_length;return v;
}
static CohProtocolBits append_packet(CohNetPacket *p){
    CohProtocolBits b;CHECK(!coh_protocol_bits_init(&b,p->payload,sizeof(p->payload),p->payload_bits,1));b.cursor=b.bit_length;return b;
}
static void application_send(Peer *p,CohNetEndpoint to,CohNetPacket packet,CohProtocolBits *bits,uint32_t ack){
    if(bits)packet.payload_bits=(uint32_t)bits->bit_length;
    packet.ack_count=1;packet.acks[0]=ack;frame_send(p,to,5,&packet);
}
static CohLocal *start(Peer *db,uint32_t dbid,uint32_t mapid,uint64_t now){
    CohLocalConfig c=coh_local_default_config();c.db.transport.peer=db->endpoint;c.local_development_enabled=1;c.db.request_timeout_ms=2000;c.map.application_timeout_ms=2000;
    CohLocal *s=coh_local_create(&c);CHECK(s);CohDbLogin p;CHECK(coh_local_login_policy(&p)==COH_OK);
    CHECK(p.no_version_check==1&&p.protocol_version==20110614&&!p.user_id&&!p.cookie&&!p.no_timeout);
    CHECK(coh_local_begin(s,&p,"Fixture",dbid,mapid,now)==COH_OK);return s;
}
static CohNetEndpoint list_characters(CohLocal *s,Peer *db,uint64_t now){
    CohNetEndpoint target;CohNetPacket request=connect_peer(s,db,&target,now,0);
    CohDbLogin p;coh_local_login_policy(&p);strcpy(p.account,"Fixture");uint8_t expected[4096];size_t bits=0;
    CHECK(coh_db_local_login_encode(&p,0,0,expected,sizeof(expected),&bits)==COH_OK);
    CHECK(request.payload_bits==bits&&!memcmp(request.payload,expected,(bits+7)/8));
    peer_message(db,target,5,players0,players0_bits,0,request.id);service_ok(s,now+4);drain_ack(db,5);
    CHECK(diag(s).phase==COH_LOCAL_CHARACTERS_READY&&diag(s).server_identity_bound);
    CohLocalCharacters c;CHECK(coh_local_characters(s,&c)==COH_OK&&c.count==5&&c.selectable_count==1&&!strcmp(c.players[0].name,"Native Fixture"));
    CHECK(coh_local_choose_character(s,1,now+5)==COH_STATE);CHECK(coh_local_choose_character(s,0,now+5)==COH_OK);
    CHECK(coh_local_choose_character(s,0,now+5)==COH_STATE);service_ok(s,now+5);request=frame_read(db,5,0);
    CohProtocolBits r;uint32_t command_id,slot,local_ip;
    CHECK(!coh_protocol_bits_init(&r,request.payload,sizeof(request.payload),request.payload_bits,0));
    CHECK(!coh_protocol_read_pack(&r,1,&command_id)&&command_id==3);
    CHECK(!coh_protocol_read_pack(&r,1,&slot)&&slot==0);
    CHECK(!coh_protocol_read_pack(&r,1,&local_ip)&&local_ip==0); /* preserve saved destination */
    return target;
}
static void send_handoff(Peer *db,CohNetEndpoint target,Peer *map,int remote){
    CohNetPacket p=application(db,COH_DB_MAP_CONNECT);CohProtocolBits b=append_packet(&p);
    uint32_t fields[]={17,5,remote?0x0100000au:0x0100007fu,0,map->endpoint.port,7003,123456};
    for(unsigned i=0;i<7;i++)CHECK(!coh_protocol_write_pack(&b,1,fields[i]));
    application_send(db,target,p,&b,0);
}
static void happy_chain(unsigned malformed_catalog){
    Peer db=peer_open(),map=peer_open();CohLocal *s=start(&db,101,102,100);CohNetEndpoint db_target=list_characters(s,&db,100);
    send_handoff(&db,db_target,&map,0);service_ok(s,106);drain_ack(&db,5);CHECK(diag(s).phase==COH_LOCAL_MAP_CONNECTING&&diag(s).map_handoffs==1&&diag(s).server_identity_bound);
    /* Finish genuine DB graceful disconnect while Map connects. */
    CohNetEndpoint map_target;CohNetPacket first=read_target(&map,&map_target,1);CHECK(first.connect);
    service_ok(s,107);CohNetPacket bye=frame_read(&db,5,0);CHECK(command(&bye,5,1)==5);
    CohNetPacket close_ack=control(5,++db.id,6,0,0);close_ack.ack_count=1;close_ack.acks[0]=bye.id;frame_send(&db,db_target,5,&close_ack);
    CohNetPacket reply=control(5,100,2,1,0);reply.ack_count=1;reply.acks[0]=first.id;frame_send(&map,map_target,5,&reply);
    service_ok(s,108);CohNetPacket ack=frame_read(&map,5,0);CHECK(command(&ack,5,1)==3);
    reply=control(5,101,4,0,0);reply.ack_count=1;reply.acks[0]=ack.id;frame_send(&map,map_target,5,&reply);
    service_ok(s,109);drain_ack(&map,5);service_ok(s,110);CohNetPacket request=frame_read(&map,5,0);CHECK(command(&request,5,0)==COH_MAP_CONNECT);
    CohProtocolBits r;uint32_t cmd,cookie,cod,new_character;CHECK(!coh_protocol_bits_init(&r,request.payload,sizeof(request.payload),request.payload_bits,0));
    CHECK(!coh_protocol_read_pack(&r,1,&cmd));CHECK(!coh_protocol_read_pack(&r,1,&cookie)&&cookie==123456);
    CHECK(!coh_protocol_read(&r,1,&cod)&&cod==0);CHECK(!coh_protocol_read(&r,1,&new_character)&&new_character==0&&r.cursor==r.bit_length);
    reply=application(&map,COH_REP_CONNECT_MSG);CohProtocolBits b=append_packet(&reply);CHECK(!coh_protocol_write_pack(&b,1,1));CHECK(!coh_protocol_write(&b,32,0));application_send(&map,map_target,reply,&b,request.id);
    service_ok(s,111);drain_ack(&map,5);service_ok(s,112);request=frame_read(&map,5,0);CHECK(command(&request,5,0)==COH_MAP_REQSHORTCUTS);
    reply=application(&map,COH_REP_SHORTCUTS);b=append_packet(&reply);CHECK(!coh_protocol_write_pack(&b,1,UINT32_MAX));
    CHECK(!coh_protocol_write_pack(&b,1,malformed_catalog==1?COH_REP_ACCESSIBLE_COMMAND_MAX+1:0));
    application_send(&map,map_target,reply,&b,request.id);
    if(malformed_catalog==1) {
        CHECK(coh_local_service(s,113,(CohCancel){0})==COH_LIMIT);drain_ack(&map,5);
        CohLocalDiagnostics d=diag(s);CHECK(d.phase==COH_LOCAL_FAILED&&d.last_status==COH_LIMIT);
        CHECK(d.terminal_failure&&d.terminal_map_phase==COH_MAP_WAIT_SHORTCUTS&&d.map_phase==COH_MAP_CLOSED);
        CHECK(d.map_protocol.stage==COH_MAP_STAGE_SHORTCUTS&&d.map_protocol.last_status==COH_LIMIT);
        CHECK(d.map_protocol.last_command_valid&&d.map_protocol.last_command==COH_REP_SHORTCUTS);
        CHECK(d.map_protocol.accepted_messages==1&&d.map_protocol.rejected_messages==1&&d.map_protocol.malformed==1);
        CHECK(d.opened_sockets==2&&d.closed_sockets==2);
        coh_local_suspend(s);d=diag(s);
        CHECK(d.terminal_failure&&d.terminal_map_phase==COH_MAP_WAIT_SHORTCUTS&&d.last_status==COH_LIMIT);
        CHECK(d.map_protocol.stage==COH_MAP_STAGE_SHORTCUTS&&d.map_protocol.last_status==COH_LIMIT);
        coh_local_destroy(s);peer_close(&map);peer_close(&db);scenarios++;return;
    }
    service_ok(s,113);drain_ack(&map,5);service_ok(s,114);request=frame_read(&map,5,0);CHECK(command(&request,5,0)==COH_MAP_REQSCENE);
    if(malformed_catalog==3)peer_message(&map,map_target,5,source_groups_unsupported_base_byte_aligned,source_groups_unsupported_base_byte_aligned_bits,1,request.id);
    else peer_message(&map,map_target,5,source_groups_minimal_world_packed,source_groups_minimal_world_packed_bits-(malformed_catalog==2?1:0),0,request.id);
    if(malformed_catalog==2) {
        CHECK(coh_local_service(s,115,(CohCancel){0})==COH_INVALID);drain_ack(&map,5);
        CohLocalDiagnostics d=diag(s);CHECK(d.phase==COH_LOCAL_FAILED&&d.last_status==COH_INVALID);
        CHECK(d.terminal_failure&&d.terminal_map_phase==COH_MAP_SCENE_INCOMPLETE&&d.map_phase==COH_MAP_CLOSED);
        CHECK(d.map_protocol.stage==COH_MAP_STAGE_SCENE_STRUCTURE&&d.map_protocol.scene_prefixes==1&&!d.map_protocol.scene_structures);
        CHECK(d.map_protocol.scene_failure.stage==COH_GROUPS_STAGE_FOOTER&&d.map_protocol.scene_failure.status==COH_INVALID);
        CHECK(!d.map_protocol.scene_inspection.consumed_bits&&!d.map_protocol.udp.link.owned_retained_bytes);
        CHECK(d.opened_sockets==2&&d.closed_sockets==2&&!d.map_protocol.character_identity_verified);
        coh_local_suspend(s);CHECK(diag(s).map_protocol.scene_failure.status==COH_INVALID);
        coh_local_destroy(s);peer_close(&map);peer_close(&db);scenarios++;return;
    }
    CHECK(coh_local_service(s,115,(CohCancel){0})==COH_UNSUPPORTED);drain_ack(&map,5);
    CHECK(diag(s).phase==COH_LOCAL_SCENE_INCOMPLETE&&diag(s).local_development_auth&&diag(s).map_phase==COH_MAP_SCENE_INCOMPLETE);
    if(malformed_catalog==3)CHECK(!diag(s).map_protocol.scene_structures&&diag(s).map_protocol.scene_failure.stage==COH_GROUPS_STAGE_FILE&&diag(s).map_protocol.scene_failure.status==COH_UNSUPPORTED);
    else CHECK(diag(s).map_protocol.scene_structures==1&&diag(s).map_protocol.scene_inspection.consumed_bits==source_groups_minimal_world_packed_bits&&!diag(s).map_protocol.scene_failure.status);
    CHECK(!diag(s).map_protocol.udp.link.owned_retained_bytes&&!diag(s).map_protocol.character_identity_verified);
    struct pollfd f={map.fd,POLLIN,0};CHECK(poll(&f,1,0)==0); /* no READY/full entities/spawn */
    coh_local_suspend(s);CHECK(diag(s).phase==COH_LOCAL_SUSPENDED&&diag(s).opened_sockets==2&&diag(s).closed_sockets==2&&!diag(s).server_identity_bound);
    CohDbLogin p;coh_local_login_policy(&p);CHECK(coh_local_begin(s,&p,"Fixture",101,102,116)==COH_INVALID);
    CHECK(coh_local_begin(s,&p,"Fixture",103,104,116)==COH_OK);coh_local_close(s);CHECK(diag(s).opened_sockets==3&&diag(s).closed_sockets==3);
    CHECK(coh_local_begin(s,&p,"Fixture",101,102,117)==COH_INVALID);coh_local_destroy(s);peer_close(&map);peer_close(&db);scenarios++;
}
static void failures(void){
    for(unsigned which=0;which<5;which++){
        Peer db=peer_open(),map=peer_open();CohLocal *s=start(&db,101,102,100);
        if(which==0){coh_local_cancel(s);CHECK(diag(s).phase==COH_LOCAL_CANCELLED&&coh_local_service(s,100,(CohCancel){0})==COH_CANCELLED);}
        else if(which==1){coh_local_suspend(s);CHECK(diag(s).phase==COH_LOCAL_SUSPENDED);}
        else if(which==2){service_ok(s,100);CHECK(coh_local_service(s,2101,(CohCancel){0})!=COH_OK&&diag(s).phase==COH_LOCAL_TIMED_OUT);}
        else {CohNetEndpoint target=list_characters(s,&db,100);
            if(which==3){send_handoff(&db,target,&map,1);CHECK(coh_local_service(s,106,(CohCancel){0})==COH_INVALID&&diag(s).policy_rejections==1);drain_ack(&db,5);}
            else {peer_message(&db,target,5,map0,map0_bits-1,0,0);CHECK(coh_local_service(s,106,(CohCancel){0})!=COH_OK);drain_ack(&db,5);}
        }
        CHECK(diag(s).opened_sockets==diag(s).closed_sockets);coh_local_destroy(s);peer_close(&db);peer_close(&map);scenarios++;
    }
}
int main(void){
    unsigned before=descriptors();CohLocalConfig c=coh_local_default_config();c.db.transport.peer=(CohNetEndpoint){{127,0,0,1},7000};
    CHECK(!coh_local_create(&c));c.local_development_enabled=1;c.db.transport.peer.address[0]=10;CHECK(!coh_local_create(&c));
    c.db.transport.peer.address[0]=127;c.map.udp.local.address[0]=0;CHECK(!coh_local_create(&c));
    happy_chain(0);happy_chain(1);happy_chain(2);happy_chain(3);failures();CHECK(descriptors()==before);
    printf("{\"passed\":true,\"checks\":%u,\"socket_scenarios\":%u,\"actual_os_udp\":true,\"full_scripted_db_map_chain\":true,\"source_layout_peer\":true,\"real_server_interoperability\":false,\"real_authenticated_session\":false,\"native_live_world\":false,\"socket_leak_check\":true}\n",checks,scenarios);return 0;
}
