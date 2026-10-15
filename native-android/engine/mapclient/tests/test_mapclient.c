#define _POSIX_C_SOURCE 200809L
#include "coh_mapclient.h"
#include "fixtures.h"
#include <arpa/inet.h>
#include <dirent.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static unsigned checks,negative,scenarios;
#define CHECK(x) do {checks++;if(!(x)){fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#x);exit(1);}}while(0)
typedef struct {int fd;CohNetEndpoint endpoint;} Peer;
static struct sockaddr_in address(CohNetEndpoint e) {
    struct sockaddr_in a;memset(&a,0,sizeof(a));a.sin_family=AF_INET;
    memcpy(&a.sin_addr.s_addr,e.address,4);a.sin_port=htons(e.port);return a;
}
static Peer peer_open(void) {
    Peer p={-1,{{127,0,0,1},0}};p.fd=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);CHECK(p.fd>=0);
    struct sockaddr_in a=address(p.endpoint);CHECK(bind(p.fd,(struct sockaddr*)&a,sizeof(a))==0);
    socklen_t n=sizeof(a);CHECK(getsockname(p.fd,(struct sockaddr*)&a,&n)==0);p.endpoint.port=ntohs(a.sin_port);
    CHECK(fcntl(p.fd,F_SETFL,O_NONBLOCK)==0);return p;
}
static void peer_close(Peer p){CHECK(close(p.fd)==0);}
static CohMapConfig configuration(Peer p,unsigned version) {
    CohMapConfig c;memset(&c,0,sizeof(c));c.udp.link=coh_net_default_config();c.udp.link.version=version;
    c.udp.peer=p.endpoint;c.udp.local.address[0]=127;c.udp.local.address[3]=1;c.udp.receive_budget=16;
    c.message_budget=16;c.application_timeout_ms=10000;c.cod=1;return c;
}
static CohMapAuthorization authorized(Peer p) {
    CohMapAuthorization a;memset(&a,0,sizeof(a));a.authenticated=1;a.endpoint_authorized=1;
    a.selected_slot=7;a.selection_generation=9; /* DB list carries no DBID. */
    a.handoff.link_id=23;a.handoff.map_id=19;a.handoff.cookie=77;
    a.handoff.address[0]=0x0100007fu;a.handoff.address[1]=0x0200007fu;a.handoff.udp_port=p.endpoint.port;return a;
}
static CohMapDiagnostics diagnostics(CohMapClient *m){CohMapDiagnostics d;coh_map_client_diagnostics(m,&d);return d;}
static CohNetEndpoint local(CohMapClient *m){CohNetEndpoint e;CHECK(coh_map_client_local_endpoint(m,&e)==COH_OK);return e;}
static CohNetPacket packet(uint32_t id,unsigned cmd,unsigned legacy) {
    CohNetPacket p;memset(&p,0,sizeof(p));p.id=id;CohProtocolBits b;
    CHECK(coh_protocol_bits_init(&b,p.payload,sizeof(p.payload),0,1)==COH_OK);
    CHECK(coh_protocol_write_pack(&b,1,cmd+(legacy?5u:0u))==COH_OK);p.payload_bits=(uint32_t)b.bit_length;return p;
}
static CohNetPacket profile_packet(uint32_t id,unsigned cmd,unsigned legacy,unsigned aligned) {
    if(!aligned)return packet(id,cmd,legacy);
    CohNetPacket p;memset(&p,0,sizeof(p));p.id=id;p.compressed=1;CohProtocolBits b;
    CHECK(coh_protocol_bits_init(&b,p.payload,sizeof(p.payload),0,1)==COH_OK);
    CHECK(coh_protocol_write(&b,32,cmd+(legacy?5u:0u))==COH_OK);p.payload_bits=(uint32_t)b.bit_length;return p;
}
static void pack_value(CohProtocolBits *b,unsigned aligned,uint32_t value) {
    CHECK((aligned?coh_protocol_write(b,32,value):coh_protocol_write_pack(b,1,value))==COH_OK);
}
static void scalar_value(CohProtocolBits *b,unsigned aligned,unsigned width,uint32_t value) {
    CHECK(coh_protocol_write(b,aligned?(width+7u)&~7u:width,value)==COH_OK);
}
static CohProtocolBits append(CohNetPacket *p) {
    CohProtocolBits b;CHECK(coh_protocol_bits_init(&b,p->payload,sizeof(p->payload),p->payload_bits,1)==COH_OK);
    b.cursor=b.bit_length;return b;
}
static CohNetPacket control(unsigned version,uint32_t id,uint32_t cmd,int value,uint32_t v) {
    CohNetPacket p=packet(id,version>=4?0:cmd,0);CohProtocolBits b=append(&p);
    if(version>=4)CHECK(coh_protocol_write_pack(&b,1,cmd)==COH_OK);
    if(value)CHECK(coh_protocol_write_pack(&b,1,v)==COH_OK);
    p.payload_bits=(uint32_t)b.bit_length;return p;
}
static void send_packet(Peer p,CohNetEndpoint to,unsigned version,CohNetPacket body) {
    uint8_t data[COH_PROTOCOL_FRAME_MAX];size_t n;
    if(body.compressed) {
        uint8_t encoded[COH_NET_MESSAGE_MAX];size_t bytes;CohNetZip *z=coh_net_zip_create();CHECK(z);
        CHECK(coh_net_zip_encode(z,0,(CohBytes){body.payload,(body.payload_bits+7)/8},encoded,sizeof(encoded),&bytes)==COH_OK);
        CHECK(bytes<=sizeof(body.payload));memcpy(body.payload,encoded,bytes);body.payload_bits=(uint32_t)bytes*8;coh_net_zip_destroy(z);
    }
    CHECK(coh_net_frame_encode(version,NULL,0,&body,data,sizeof(data),&n)==COH_OK);
    struct sockaddr_in a=address(to);CHECK(sendto(p.fd,data,n,0,(struct sockaddr*)&a,sizeof(a))==(ssize_t)n);
}
static CohNetPacket receive_packet(Peer p,unsigned version,int connect) {
    struct pollfd pollfd={p.fd,POLLIN,0};CHECK(poll(&pollfd,1,100)==1);
    uint8_t data[COH_PROTOCOL_FRAME_MAX];ssize_t n=recv(p.fd,data,sizeof(data),0);CHECK(n>0);
    CohNetPacket body;CHECK(coh_net_frame_decode(version,NULL,0,connect,(CohBytes){data,(size_t)n},&body)==COH_OK);return body;
}
static unsigned command(CohNetPacket p,unsigned legacy) {
    CohProtocolBits b;uint32_t cmd;CHECK(coh_protocol_bits_init(&b,p.payload,sizeof(p.payload),p.payload_bits,0)==COH_OK);
    CHECK(coh_protocol_read_pack(&b,1,&cmd)==COH_OK);return legacy?cmd-5:cmd;
}
static CohNetPacket receive_command(Peer p,unsigned version,unsigned wanted) {
    for(unsigned i=0;i<16;i++){
        CohNetPacket body=receive_packet(p,version,0);unsigned cmd=command(body,0);
        if(cmd==(wanted+(version<4?5u:0u)))return body;
        CHECK(cmd==0); /* source transport ACK, not an application ACK */
    }
    CHECK(0);return packet(0,0,0);
}
static void drain_idle(Peer p,unsigned version) {
    struct pollfd pollfd={p.fd,POLLIN,0};
    while(poll(&pollfd,1,0)==1)CHECK(command(receive_packet(p,version,0),0)==0);
}
static uint64_t handshake(CohMapClient *m,Peer p,unsigned version,unsigned aligned,uint32_t known_dbid,uint32_t connect_id,uint64_t now) {
    CohMapAuthorization a=authorized(p);a.selected_dbid=known_dbid;
    CHECK(coh_map_client_begin(m,&a,connect_id,now)==COH_OK);
    CHECK(coh_map_client_service(m,now,(CohCancel){0})==COH_OK);
    CohNetPacket first=receive_packet(p,version,1);CHECK(first.connect&&command(first,0)==1);
    CohNetPacket ack=control(version,100,2,1,0);ack.ack_count=1;ack.acks[0]=first.id;
    send_packet(p,local(m),version,ack);CHECK(coh_map_client_service(m,now+1,(CohCancel){0})==COH_OK);
    CohNetPacket reply=receive_packet(p,version,0);
    ack=control(version,101,4,0,0);ack.ack_count=1;ack.acks[0]=reply.id;send_packet(p,local(m),version,ack);
    CHECK(coh_map_client_service(m,now+2,(CohCancel){0})==COH_OK);drain_idle(p,version);
    CHECK(diagnostics(m).phase==COH_MAP_WAIT_CONNECT);
    CHECK(coh_map_client_service(m,now+3,(CohCancel){0})==COH_OK);
    CohNetPacket connect=receive_command(p,version,COH_MAP_CONNECT);
    CohProtocolBits b;uint32_t cmd,cookie,cod,new_character;
    CHECK(coh_protocol_bits_init(&b,connect.payload,sizeof(connect.payload),connect.payload_bits,0)==COH_OK);
    CHECK(coh_protocol_read_pack(&b,1,&cmd)==COH_OK&&cmd==COH_MAP_CONNECT+(version<4?5u:0u));
    CHECK(coh_protocol_read_pack(&b,1,&cookie)==COH_OK&&cookie==77);
    CHECK(coh_protocol_read(&b,1,&cod)==COH_OK&&cod==1);
    CHECK(coh_protocol_read(&b,1,&new_character)==COH_OK&&!new_character&&b.cursor==b.bit_length);
    /* The three distinct request IDs survive independently, while no DBID is invented. */
    CohMapDiagnostics d=diagnostics(m);CHECK(d.selected_slot==7&&d.selection_generation==9&&d.selected_dbid==known_dbid);
    CHECK(d.map_link_id==23&&d.map_id==19&&!d.character_identity_verified);
    CHECK(d.inspector_phase==(known_dbid?COH_REP_WAIT_MAP:COH_REP_DISCONNECTED));
    ack=profile_packet(102,COH_REP_CONNECT_MSG,version<4,aligned);b=append(&ack);
    pack_value(&b,aligned,1);float timezone=-6;uint32_t u;memcpy(&u,&timezone,4);
    CHECK(coh_protocol_write(&b,32,u)==COH_OK);ack.payload_bits=(uint32_t)b.bit_length;ack.ack_count=1;ack.acks[0]=connect.id;
    send_packet(p,local(m),version,ack);CHECK(coh_map_client_service(m,now+4,(CohCancel){0})==COH_OK);
    CHECK(diagnostics(m).phase==COH_MAP_WAIT_SHORTCUTS);drain_idle(p,version);
    CHECK(coh_map_client_service(m,now+5,(CohCancel){0})==COH_OK);CohNetPacket shortcuts=receive_command(p,version,COH_MAP_REQSHORTCUTS);
    ack=profile_packet(103,COH_REP_SHORTCUTS,version<4,aligned);b=append(&ack);
    pack_value(&b,aligned,UINT32_MAX);pack_value(&b,aligned,0);
    ack.payload_bits=(uint32_t)b.bit_length;ack.ack_count=1;ack.acks[0]=shortcuts.id;
    send_packet(p,local(m),version,ack);CHECK(coh_map_client_service(m,now+6,(CohCancel){0})==COH_OK);drain_idle(p,version);
    CHECK(diagnostics(m).phase==COH_MAP_WAIT_SCENE);
    CHECK(coh_map_client_service(m,now+7,(CohCancel){0})==COH_OK);CohNetPacket scene=receive_command(p,version,COH_MAP_REQSCENE);
    CHECK(scene.payload_bits>0);return now+8;
}
static void serializers(void) {
    uint8_t md5[16];for(unsigned i=0;i<16;i++)md5[i]=(uint8_t)i;
    for(unsigned i=0;i<sizeof(goldens)/sizeof(goldens[0]);i++){
        const MapGolden *g=&goldens[i];CohMapFields f={g->cookie,g->cod,g->console,g->initial,md5};CohMapPacket p;
        CHECK(coh_map_serialize(g->cmd,(CohMapProfile){g->legacy,g->aligned},&f,&p)==COH_OK);
        CHECK(p.bits==g->bits&&!memcmp(p.data,g->bytes,(p.bits+7)/8));
        coh_map_packet_wipe(&p);CohMapPacket zero;memset(&zero,0,sizeof(zero));CHECK(!memcmp(&p,&zero,sizeof(p)));
    }
    CohMapPacket sentinel;memset(&sentinel,0xa5,sizeof(sentinel));CohMapPacket out=sentinel;
    CohMapFields fields={77,1,0,0,md5};
    CHECK(coh_map_serialize(COH_MAP_CONNECT,(CohMapProfile){2,0},&fields,&out)==COH_INVALID&&!memcmp(&out,&sentinel,sizeof(out)));
    CHECK(coh_map_serialize(COH_MAP_CONNECT,(CohMapProfile){0,2},&fields,&out)==COH_INVALID);
    CHECK(coh_map_serialize(COH_MAP_CONNECT,(CohMapProfile){0,0},NULL,&out)==COH_INVALID);
    CHECK(coh_map_serialize(COH_MAP_INPUT,(CohMapProfile){0,0},&fields,&out)==COH_UNSUPPORTED);
    fields.cookie=1;CHECK(coh_map_serialize(COH_MAP_READY,(CohMapProfile){0,0},&fields,&out)==COH_INVALID);
    fields.cookie=77;fields.password_md5=NULL;CHECK(coh_map_serialize(COH_MAP_READY,(CohMapProfile){0,0},&fields,&out)==COH_INVALID);
    fields.password_md5=md5;fields.initial_login=2;CHECK(coh_map_serialize(COH_MAP_READY,(CohMapProfile){0,0},&fields,&out)==COH_INVALID);
    fields.initial_login=0;fields.console_open=2;CHECK(coh_map_serialize(COH_MAP_READY,(CohMapProfile){0,0},&fields,&out)==COH_INVALID);
    fields.console_open=0;fields.cod=2;CHECK(coh_map_serialize(COH_MAP_CONNECT,(CohMapProfile){0,0},&fields,&out)==COH_INVALID);
    CHECK(!memcmp(&out,&sentinel,sizeof(out)));negative+=9;
    uint32_t rng=0x1234fedc;
    for(unsigned i=0;i<10000;i++){
        rng=rng*1664525u+1013904223u;fields.cod=rng|2u;
        CHECK(coh_map_serialize(COH_MAP_CONNECT,(CohMapProfile){i&1,(i>>1)&1},&fields,&out)==COH_INVALID);
        CHECK(!memcmp(&out,&sentinel,sizeof(out)));negative++;
    }
    scenarios++;
}
static void configuration_tests(void) {
    Peer p=peer_open();CohMapConfig c=configuration(p,5);CohMapClient *m=coh_map_client_create(&c);CHECK(m);
    CohMapAuthorization a=authorized(p);a.authenticated=0;CHECK(coh_map_client_begin(m,&a,7,0)==COH_STATE);
    a=authorized(p);a.endpoint_authorized=0;CHECK(coh_map_client_begin(m,&a,7,0)==COH_STATE);
    a=authorized(p);a.selected_slot=64;CHECK(coh_map_client_begin(m,&a,7,0)==COH_INVALID);
    a=authorized(p);a.selection_generation=0;CHECK(coh_map_client_begin(m,&a,7,0)==COH_INVALID);
    a=authorized(p);a.handoff.cookie=1;CHECK(coh_map_client_begin(m,&a,7,0)==COH_INVALID);
    a=authorized(p);a.handoff.address[0]++;CHECK(coh_map_client_begin(m,&a,7,0)==COH_INVALID);
    a=authorized(p);a.address_index=1;CHECK(coh_map_client_begin(m,&a,7,0)==COH_INVALID);
    a=authorized(p);a.handoff.udp_port++;CHECK(coh_map_client_begin(m,&a,7,0)==COH_INVALID);
    a=authorized(p);CHECK(coh_map_client_begin(m,&a,0,0)==COH_INVALID);
    CHECK(coh_map_client_service(m,0,(CohCancel){0})==COH_STATE);CHECK(!diagnostics(m).udp.sockets_opened);
    CohMapConfig bad=c;bad.message_budget=0;CHECK(!coh_map_client_create(&bad));bad=c;bad.message_budget=17;CHECK(!coh_map_client_create(&bad));
    bad=c;bad.application_timeout_ms=0;CHECK(!coh_map_client_create(&bad));bad=c;bad.cod=2;CHECK(!coh_map_client_create(&bad));
    bad=c;bad.udp.peer.port=0;CHECK(!coh_map_client_create(&bad));
    CHECK(coh_map_config_validate(NULL)==COH_INVALID);coh_map_client_destroy(m);peer_close(p);negative+=15;scenarios++;
}
static void local_authorization_tests(void) {
    Peer p=peer_open();CohMapConfig c=configuration(p,5);CohMapClient *m=coh_map_client_create(&c);CHECK(m);
    CohMapAuthorization a=authorized(p);a.local_development_authorized=1;
    CHECK(coh_map_client_begin(m,&a,61,0)==COH_INVALID);negative++;
    a.authenticated=0;a.local_development_authorized=2;CHECK(coh_map_client_begin(m,&a,61,0)==COH_INVALID);negative++;
    a.local_development_authorized=1;a.selected_dbid=123;CHECK(coh_map_client_begin(m,&a,61,0)==COH_INVALID);negative++;
    a.selected_dbid=0;a.endpoint_authorized=0;CHECK(coh_map_client_begin(m,&a,61,0)==COH_STATE);negative++;
    a.endpoint_authorized=1;CHECK(coh_map_client_begin(m,&a,61,0)==COH_OK);
    CHECK(diagnostics(m).local_development_authorized==1&&!diagnostics(m).character_identity_verified);
    CHECK(coh_map_client_service(m,0,(CohCancel){0})==COH_OK);
    CohNetPacket first=receive_packet(p,5,1);CHECK(first.connect&&command(first,0)==1);
    coh_map_client_suspend(m);CHECK(!diagnostics(m).local_development_authorized);
    coh_map_client_destroy(m);
    c.udp.peer.address[0]=192;a.handoff.address[0]=(a.handoff.address[0]&~255u)|192u;
    m=coh_map_client_create(&c);CHECK(m);CHECK(coh_map_client_begin(m,&a,62,1)==COH_INVALID);negative++;
    CHECK(!diagnostics(m).udp.sockets_opened);coh_map_client_destroy(m);peer_close(p);scenarios++;
}
static CohNetPacket scene_prefix(unsigned version,unsigned aligned,uint32_t id) {
    CohNetPacket p=profile_packet(id,COH_REP_GROUPS,version<4,aligned);CohProtocolBits b=append(&p);
    pack_value(&b,aligned,0);pack_value(&b,aligned,0);
    scalar_value(&b,aligned,1,0);scalar_value(&b,aligned,1,1);p.payload_bits=(uint32_t)b.bit_length;return p;
}
static CohNetPacket entity_prefix(unsigned version,unsigned aligned,uint32_t id) {
    CohNetPacket p=profile_packet(id,COH_REP_ALLENTS,version<4,aligned);CohProtocolBits b=append(&p);
    pack_value(&b,aligned,17);scalar_value(&b,aligned,1,1);
    pack_value(&b,aligned,0);scalar_value(&b,aligned,32,123456);
    scalar_value(&b,aligned,32,87654321);scalar_value(&b,aligned,1,1);
    p.payload_bits=(uint32_t)b.bit_length;return p;
}
static void actual_socket_inspection(void) {
    for(unsigned profile=0;profile<12;profile++){
        unsigned version=profile<6?profile:(profile<11?profile-5:5),aligned=profile>=6;
        Peer p=peer_open();CohMapConfig c=configuration(p,version);CohMapClient *m=coh_map_client_create(&c);CHECK(m);
        uint64_t now=handshake(m,p,version,aligned,profile==11?12345:0,41,100);
        CohNetPacket scene=scene_prefix(version,aligned,104);send_packet(p,local(m),version,scene);
        CHECK(coh_map_client_service(m,now++,(CohCancel){0})==COH_UNSUPPORTED);drain_idle(p,version);
        CohMapDiagnostics d=diagnostics(m);CHECK(d.phase==COH_MAP_SCENE_INCOMPLETE&&d.scene_prefixes==1&&!d.character_identity_verified);
        CohNetPacket ent=entity_prefix(version,aligned,105);send_packet(p,local(m),version,ent);
        CHECK(coh_map_client_service(m,now++,(CohCancel){0})==COH_UNSUPPORTED);drain_idle(p,version);
        d=diagnostics(m);CHECK(d.phase==COH_MAP_SCENE_INCOMPLETE&&d.entity_prefixes==1&&d.accepted_messages==2&&!d.character_identity_verified);
        /* Every truncation is rejected and cannot create a READY/ACK/own spawn. */
        unsigned id=106;
        for(uint32_t bits=aligned?32:1;bits<ent.payload_bits;bits+=aligned?8:1){
            CohNetPacket truncated=ent;truncated.id=id++;truncated.payload_bits=bits;send_packet(p,local(m),version,truncated);
            /* A truncated command may be discarded by NetLink before the
             * application queue. Either rejection layer must preserve flow. */
            CohStatus status=coh_map_client_service(m,now++,(CohCancel){0});
            CHECK(status==COH_OK||status==COH_UNSUPPORTED||status==COH_INVALID||status==COH_LIMIT);
            drain_idle(p,version);negative++;
            CHECK(diagnostics(m).phase==COH_MAP_SCENE_INCOMPLETE&&!diagnostics(m).character_identity_verified&&diagnostics(m).accepted_messages==2);
        }
        CHECK(coh_map_client_service(m,now-2,(CohCancel){0})==COH_INVALID);negative++;
        CHECK(coh_map_client_disconnect(m,now)==COH_OK);CHECK(!diagnostics(m).selected_dbid&&!diagnostics(m).selection_generation);
        CHECK(coh_map_client_service(m,now++,(CohCancel){0})==COH_OK);CohNetPacket bye=receive_packet(p,version,0);
        CohNetPacket ack=control(version,id++,6,0,0);ack.ack_count=1;ack.acks[0]=bye.id;send_packet(p,local(m),version,ack);
        CHECK(coh_map_client_service(m,now++,(CohCancel){0})==COH_OK);d=diagnostics(m);
        CHECK(d.phase==COH_MAP_CLOSED&&d.udp.sockets_opened==d.udp.sockets_closed&&!d.udp.link.tx_pending);
        CohMapAuthorization a=authorized(p);CHECK(coh_map_client_begin(m,&a,41,now)==COH_INVALID);negative++;
        CHECK(coh_map_client_begin(m,&a,42,now)==COH_OK);coh_map_client_suspend(m);d=diagnostics(m);
        CHECK(d.phase==COH_MAP_SUSPENDED&&!d.selection_generation&&d.udp.sockets_opened==d.udp.sockets_closed);
        CHECK(coh_map_client_begin(m,&a,42,now)==COH_INVALID);negative++;
        a.authenticated=0;CHECK(coh_map_client_begin(m,&a,43,now)==COH_STATE);negative++;
        coh_map_client_destroy(m);peer_close(p);scenarios++;
    }
}
static unsigned fd_count(void) {
    DIR *d=opendir("/proc/self/fd");CHECK(d);unsigned n=0;struct dirent *e;
    while((e=readdir(d)))if(e->d_name[0]!='.')n++;
    CHECK(closedir(d)==0);return n;
}
static int cancelled(void *context){(void)context;return 1;}
static void timeout_and_cancel(void) {
    Peer p=peer_open();CohMapConfig c=configuration(p,5);c.application_timeout_ms=10;
    CohMapClient *m=coh_map_client_create(&c);CHECK(m);uint64_t now=handshake(m,p,5,0,0,51,100);
    CHECK(coh_map_client_service(m,now+20,(CohCancel){0})==COH_STATE);
    CohMapDiagnostics d=diagnostics(m);CHECK(d.phase==COH_MAP_TIMED_OUT&&d.timeouts==1&&!d.selection_generation&&d.udp.sockets_opened==d.udp.sockets_closed);
    coh_map_client_destroy(m);peer_close(p);scenarios++;
    p=peer_open();c=configuration(p,5);m=coh_map_client_create(&c);CHECK(m);
    CohMapAuthorization a=authorized(p);CHECK(coh_map_client_begin(m,&a,52,0)==COH_OK);
    CHECK(coh_map_client_service(m,0,(CohCancel){cancelled,NULL})==COH_CANCELLED);d=diagnostics(m);
    CHECK(d.phase==COH_MAP_FAILED&&!d.selection_generation&&d.udp.state==COH_UDP_CANCELLED&&d.udp.sockets_opened==d.udp.sockets_closed);
    coh_map_client_destroy(m);peer_close(p);scenarios++;
    p=peer_open();c=configuration(p,5);m=coh_map_client_create(&c);CHECK(m);now=handshake(m,p,5,0,0,53,100);
    CohNetPacket refusal=packet(104,COH_REP_CONNECT_MSG,0);CohProtocolBits b=append(&refusal);
    CHECK(coh_protocol_write_pack(&b,1,0)==COH_OK);
    static const char remote_text[]="Synthetic refusal; remote text discarded";
    for(unsigned i=0;i<sizeof(remote_text);i++)CHECK(coh_protocol_write(&b,8,(unsigned char)remote_text[i])==COH_OK);
    refusal.payload_bits=(uint32_t)b.bit_length;send_packet(p,local(m),5,refusal);
    CHECK(coh_map_client_service(m,now,(CohCancel){0})==COH_STATE);d=diagnostics(m);
    CHECK(d.phase==COH_MAP_CLOSED&&!d.selection_generation&&!d.character_identity_verified&&d.udp.sockets_opened==d.udp.sockets_closed);
    coh_map_client_destroy(m);peer_close(p);scenarios++;
}
int main(void) {
    unsigned fds=fd_count();serializers();configuration_tests();local_authorization_tests();actual_socket_inspection();timeout_and_cancel();CHECK(fd_count()==fds);
    printf("{\"checks\":%u,\"negative_cases\":%u,\"scenarios\":%u,\"actual_os_udp\":true,\"scripted_peer_only\":true,\"socket_leak_check\":true,\"actual_authentication\":false,\"live_world\":false}\n",checks,negative,scenarios);return 0;
}
