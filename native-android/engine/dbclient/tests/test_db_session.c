#define _POSIX_C_SOURCE 200809L
#include "../coh_db_session.h"
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
static unsigned checks,scenarios;
#define CHECK(x) do {checks++;if(!(x)){fprintf(stderr,"DB session check line %d: %s\n",__LINE__,#x);exit(1);}} while(0)
typedef struct {int fd;CohNetEndpoint endpoint;uint32_t id,sibling;CohNetZip *zip;} Peer;
static struct sockaddr_in addr(CohNetEndpoint endpoint) {
    struct sockaddr_in a;memset(&a,0,sizeof(a));a.sin_family=AF_INET;a.sin_port=htons(endpoint.port);memcpy(&a.sin_addr.s_addr,endpoint.address,4);return a;
}
static Peer peer_open(void) {
    Peer p={-1,{{127,0,0,1},0},101,50,NULL};p.fd=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);CHECK(p.fd>=0);
    struct sockaddr_in a=addr(p.endpoint);CHECK(!bind(p.fd,(struct sockaddr*)&a,sizeof(a)));socklen_t size=sizeof(a);
    CHECK(!getsockname(p.fd,(struct sockaddr*)&a,&size));p.endpoint.port=ntohs(a.sin_port);CHECK(!fcntl(p.fd,F_SETFL,O_NONBLOCK));
    p.zip=coh_net_zip_create();CHECK(p.zip);return p;
}
static void peer_close(Peer *p){CHECK(!close(p->fd));coh_net_zip_destroy(p->zip);}
static void frame_send(Peer *p,CohNetEndpoint target,unsigned version,const CohNetPacket *packet) {
    uint8_t frame[COH_PROTOCOL_FRAME_MAX];size_t size=0;
    CHECK(coh_net_frame_encode(version,NULL,0,packet,frame,sizeof(frame),&size)==COH_OK);
    struct sockaddr_in a=addr(target);CHECK(sendto(p->fd,frame,size,0,(struct sockaddr*)&a,sizeof(a))==(ssize_t)size);
}
static CohNetPacket frame_read(Peer *p,unsigned version,int connecting) {
    struct pollfd pollfd={p->fd,POLLIN,0};CHECK(poll(&pollfd,1,100)==1&&(pollfd.revents&POLLIN));
    uint8_t frame[COH_PROTOCOL_FRAME_MAX];ssize_t size=recv(p->fd,frame,sizeof(frame),0);CHECK(size>0);
    CohNetPacket packet;CHECK(coh_net_frame_decode(version,NULL,0,connecting,(CohBytes){frame,(size_t)size},&packet)==COH_OK);return packet;
}
static CohNetPacket control(unsigned version,uint32_t id,uint32_t command,int has_value,uint32_t value) {
    CohNetPacket p;memset(&p,0,sizeof(p));p.id=id;CohProtocolBits b;CHECK(!coh_protocol_bits_init(&b,p.payload,sizeof(p.payload),0,1));
    if(version>=4&&command!=1){CHECK(!coh_protocol_write_pack(&b,1,0));if(command)CHECK(!coh_protocol_write_pack(&b,1,command));}
    else CHECK(!coh_protocol_write_pack(&b,1,command));
    if(has_value)CHECK(!coh_protocol_write_pack(&b,1,value));
    p.payload_bits=(uint32_t)b.bit_length;return p;
}
static uint32_t command(const CohNetPacket *p,unsigned version,int is_control) {
    CohProtocolBits b;uint32_t c;CHECK(!coh_protocol_bits_init(&b,(uint8_t *)(uintptr_t)p->payload,sizeof(p->payload),p->payload_bits,0));
    CHECK(!(p->compressed?coh_protocol_read(&b,32,&c):coh_protocol_read_pack(&b,1,&c)));
    if(version>=4&&is_control&&!c&&b.cursor<b.bit_length)CHECK(!coh_protocol_read_pack(&b,1,&c));
    return c;
}
static CohDbSessionConfig configuration(Peer *p,unsigned version,int compressed) {
    CohDbSessionConfig c;memset(&c,0,sizeof(c));c.transport.link=coh_net_default_config();c.transport.link.version=version;
    c.transport.peer=p->endpoint;c.transport.local.address[0]=127;c.transport.local.address[3]=1;c.transport.receive_budget=16;
    c.request_timeout_ms=2000;c.outbound_compressed=compressed;return c;
}
static void login_configuration(CohDbLogin *v,CohDbAuthReceipt *auth,uint32_t generation) {
    memset(v,0,sizeof(*v));strcpy(v->account,"fixture");strcpy(v->patch_version,"disposable-native-test");strcpy(v->system_spec,"Disabled");
    v->user_id=12345;v->protocol_version=COH_DB_PROTOCOL_VERSION;v->cookie=0x89abcdef;
    memset(auth,0,sizeof(*auth));auth->user_id=v->user_id;auth->game_cookie=v->cookie;auth->generation=generation;auth->verified=1;strcpy(auth->account,v->account);
}
static CohNetEndpoint local(CohDbSession *s){CohNetEndpoint e;CHECK(coh_db_session_local_endpoint(s,&e)==COH_OK);return e;}
static CohNetPacket handshake_uid(CohDbSession *s,Peer *peer,unsigned version,uint32_t connect_id,uint64_t now,uint32_t uid) {
    CohDbLogin login;CohDbAuthReceipt auth;login_configuration(&login,&auth,1);
    login.user_id=auth.user_id=uid;
    if(uid)CHECK(coh_db_session_begin(s,&login,&auth,connect_id,now)==COH_OK);
    else {login.cookie=0;login.no_version_check=1;CHECK(coh_db_session_begin_local(s,&login,1,connect_id,now)==COH_OK);}
    CHECK(coh_db_session_service(s,now,(CohCancel){0})==COH_OK);
    CohNetPacket first=frame_read(peer,version,1);CHECK(command(&first,version,1)==1);
    CohNetEndpoint target=local(s);CohNetPacket reply=control(version,100,2,1,0);reply.ack_count=1;reply.acks[0]=first.id;frame_send(peer,target,version,&reply);
    CHECK(coh_db_session_service(s,now+1,(CohCancel){0})==COH_OK);CohNetPacket ack=frame_read(peer,version,0);CHECK(command(&ack,version,1)==3);
    reply=control(version,101,4,0,0);reply.ack_count=1;reply.acks[0]=ack.id;frame_send(peer,target,version,&reply);
    CHECK(coh_db_session_service(s,now+2,(CohCancel){0})==COH_OK);ack=frame_read(peer,version,0);CHECK(command(&ack,version,1)==0);
    CHECK(coh_db_session_phase(s)==COH_DB_WAIT_PLAYERS);CHECK(coh_db_session_service(s,now+3,(CohCancel){0})==COH_OK);
    CohNetPacket request=frame_read(peer,version,0);CHECK(!request.sibling_count);
    uint8_t decoded[COH_NET_MESSAGE_MAX];const uint8_t *data=request.payload;size_t bytes=(request.payload_bits+7)/8;
    if(request.compressed){CHECK(coh_net_zip_decode(peer->zip,0,(CohBytes){data,bytes},decoded,sizeof(decoded),&bytes)==COH_OK);data=decoded;}
    uint8_t expected[COH_DB_LOGIN_MAX];size_t expected_bits=0;
    CHECK((uid?coh_db_login_encode:coh_db_local_login_encode)(&login,request.compressed,version<4,expected,sizeof(expected),&expected_bits)==COH_OK);
    CHECK(expected_bits==(request.compressed?bytes*8:request.payload_bits)&&!memcmp(data,expected,(expected_bits+7)/8));
    coh_db_wipe(&login,sizeof(login));coh_db_wipe(&auth,sizeof(auth));return request;
}
static CohNetPacket handshake(CohDbSession *s,Peer *peer,unsigned version,uint32_t connect_id,uint64_t now) {
    return handshake_uid(s,peer,version,connect_id,now,12345);
}
static void peer_message(Peer *p,CohNetEndpoint target,unsigned version,const uint8_t *data,size_t bits,int compressed,uint32_t ack) {
    uint8_t zipped[COH_NET_MESSAGE_MAX];size_t bytes=(bits+7)/8;
    if(compressed){CHECK(!(bits&7));CHECK(coh_net_zip_encode(p->zip,0,(CohBytes){data,bytes},zipped,sizeof(zipped),&bytes)==COH_OK);data=zipped;bits=bytes*8;}
    size_t count=(bytes+1199)/1200;uint32_t sibling=count>1?++p->sibling:0;
    for(size_t part=0;part<count;part++) {
        CohNetPacket m;memset(&m,0,sizeof(m));m.id=++p->id;m.compressed=(uint8_t)compressed;
        if(sibling){m.sibling_id=sibling;m.sibling_count=(uint32_t)count;m.sibling_part=(uint32_t)part;}
        m.payload_bits=(uint32_t)(bits-part*1200*8);if(m.payload_bits>1200*8)m.payload_bits=1200*8;
        memcpy(m.payload,data+part*1200,(m.payload_bits+7)/8);if(ack){m.ack_count=1;m.acks[0]=ack;}
        frame_send(p,target,version,&m);
    }
}
static void drain_ack(Peer *peer,unsigned version){CohNetPacket ack=frame_read(peer,version,0);CHECK(command(&ack,version,1)==0);}
static void happy(unsigned version,int compressed) {
    Peer peer=peer_open();CohDbSessionConfig c=configuration(&peer,version,compressed);CohDbSession *s=coh_db_session_create(&c);CHECK(s);
    CohNetPacket request=handshake(s,&peer,version,1001,100);CohNetEndpoint target=local(s);
    if(version>=4){peer_message(&peer,target,version,compressed?queue1:queue0,compressed?queue1_bits:queue0_bits,compressed,request.id);
      CHECK(coh_db_session_service(s,104,(CohCancel){0})==COH_OK);drain_ack(&peer,version);CHECK(coh_db_session_phase(s)==COH_DB_QUEUED);}
    const uint8_t *players=version<4?players_old0:(compressed?players1:players0);size_t player_bits=version<4?players_old0_bits:(compressed?players1_bits:players0_bits);
    peer_message(&peer,target,version,players,player_bits,compressed,request.id);CHECK(coh_db_session_service(s,105,(CohCancel){0})==COH_OK);drain_ack(&peer,version);
    CHECK(coh_db_session_phase(s)==COH_DB_CHARACTERS);CohDbPlayers list;CHECK(coh_db_session_players(s,&list)==COH_OK&&list.user_id==12345&&list.selectable_count==1);
    for(unsigned i=1;i<5;i++)CHECK(coh_db_session_choose(s,i,0,0,106)==COH_STATE);
    CHECK(coh_db_session_choose(s,0,0x0100007f,0,106)==COH_OK);CHECK(coh_db_session_choose(s,0,0,0,106)==COH_STATE);
    CHECK(coh_db_session_players(s,&list)==COH_STATE);CHECK(coh_db_session_service(s,106,(CohCancel){0})==COH_OK);request=frame_read(&peer,version,0);
    CHECK(command(&request,version,0)==COH_DB_CHOOSE_PLAYER+(version<4?5:0));
    const uint8_t *map=version<4?map_old0:(compressed?map1:map0);size_t map_bits=version<4?map_old0_bits:(compressed?map1_bits:map0_bits);
    peer_message(&peer,target,version,map,map_bits,compressed,request.id);CHECK(coh_db_session_service(s,107,(CohCancel){0})==COH_OK);drain_ack(&peer,version);
    CHECK(coh_db_session_phase(s)==COH_DB_HANDOFF_READY);CohDbSessionHandoff h;CHECK(coh_db_session_take_handoff(s,&h)==COH_OK);
    CHECK(h.map.cookie==123456&&h.map.udp_port==7002&&h.map.address[0]==0x0100007f&&h.selected_slot==0&&h.selection_generation==1&&h.selected_dbid==17);
    CHECK(coh_db_session_take_handoff(s,&h)==COH_STATE);CHECK(coh_db_session_service(s,108,(CohCancel){0})==COH_OK);request=frame_read(&peer,version,0);
    CHECK(command(&request,version,1)==5);CohNetPacket ack=control(version,++peer.id,6,0,0);ack.ack_count=1;ack.acks[0]=request.id;frame_send(&peer,target,version,&ack);
    CHECK(coh_db_session_service(s,109,(CohCancel){0})==COH_OK&&coh_db_session_phase(s)==COH_DB_CLOSED);
    CohDbSessionDiagnostics d;coh_db_session_diagnostics(s,&d);CHECK(d.login_requests==1&&d.player_lists==1&&d.choices==1&&d.handoffs==1&&d.disconnects==1);
    CHECK(d.transport.sockets_opened==d.transport.sockets_closed);
    coh_db_session_destroy(s);peer_close(&peer);scenarios++;
}
static int cancelled(void *context){(void)context;return 1;}
static void receipt_and_lifecycle(void) {
    Peer peer=peer_open();CohDbSessionConfig c=configuration(&peer,5,0);CohDbSession *s=coh_db_session_create(&c);CHECK(s);
    CohDbLogin login;CohDbAuthReceipt auth;login_configuration(&login,&auth,1);CohDbAuthReceipt bad=auth;bad.verified=0;
    CHECK(coh_db_session_begin(s,&login,&bad,1,100)==COH_STATE);bad=auth;bad.user_id++;CHECK(coh_db_session_begin(s,&login,&bad,1,100)==COH_STATE);
    bad=auth;bad.game_cookie++;CHECK(coh_db_session_begin(s,&login,&bad,1,100)==COH_STATE);bad=auth;strcpy(bad.account,"other");CHECK(coh_db_session_begin(s,&login,&bad,1,100)==COH_STATE);
    CHECK(coh_db_session_begin(s,&login,&auth,1,100)==COH_OK);CHECK(coh_db_session_disconnect(s,100)==COH_OK&&coh_db_session_phase(s)==COH_DB_CLOSED);
    CHECK(coh_db_session_begin(s,&login,&auth,2,101)==COH_STATE);auth.generation=2;CHECK(coh_db_session_begin(s,&login,&auth,2,101)==COH_OK);
    coh_db_session_suspend(s);CHECK(coh_db_session_phase(s)==COH_DB_SUSPENDED);CohDbPlayers p;CHECK(coh_db_session_players(s,&p)==COH_STATE);
    CHECK(coh_db_session_begin(s,&login,&auth,3,102)==COH_STATE);auth.generation=3;CHECK(coh_db_session_begin(s,&login,&auth,3,102)==COH_OK);
    CHECK(coh_db_session_service(s,101,(CohCancel){0})==COH_INVALID);CHECK(coh_db_session_service(s,103,(CohCancel){cancelled,NULL})==COH_CANCELLED);
    CHECK(coh_db_session_phase(s)==COH_DB_CANCELLED);auth.generation=4;CHECK(coh_db_session_begin(s,&login,&auth,4,104)==COH_OK);
    CHECK(coh_db_session_service(s,104+c.request_timeout_ms,(CohCancel){0})==COH_STATE);CHECK(coh_db_session_phase(s)==COH_DB_TIMED_OUT);
    CohDbSessionDiagnostics d;coh_db_session_diagnostics(s,&d);CHECK(d.receipt_rejections==6&&d.suspends==1&&d.cancellations==1&&d.timeouts==1);
    CHECK(d.transport.sockets_opened==d.transport.sockets_closed);coh_db_session_destroy(s);peer_close(&peer);scenarios++;
}
static void rejection(unsigned which) {
    Peer peer=peer_open();CohDbSessionConfig c=configuration(&peer,5,0);CohDbSession *s=coh_db_session_create(&c);CHECK(s);
    CohNetPacket request=handshake_uid(s,&peer,5,1001,100,which==3?12346:12345);CohNetEndpoint target=local(s);
    const uint8_t *data=which==0?error0:(which==1?map0:(which==2?overslots0:players0));size_t bits=which==0?error0_bits:(which==1?map0_bits:(which==2?overslots0_bits:players0_bits));
    peer_message(&peer,target,5,data,bits,0,request.id);CHECK(coh_db_session_service(s,104,(CohCancel){0})!=COH_OK);drain_ack(&peer,5);
    CHECK(coh_db_session_phase(s)==COH_DB_FAILED);CohDbSessionHandoff h;CHECK(coh_db_session_take_handoff(s,&h)==COH_STATE);
    CohDbSessionDiagnostics d;coh_db_session_diagnostics(s,&d);CHECK(d.transport.sockets_opened==d.transport.sockets_closed);
    CHECK(which?d.malformed==1:d.server_rejections==1);coh_db_session_destroy(s);peer_close(&peer);scenarios++;
}
static void encryption_policy(void) {
    Peer peer=peer_open();CohDbSessionConfig c=configuration(&peer,5,0);c.transport.encryption_required=1;CohDbSession *s=coh_db_session_create(&c);CHECK(s);
    CohDbLogin login;CohDbAuthReceipt auth;login_configuration(&login,&auth,1);
    CHECK(coh_db_session_begin(s,&login,&auth,9,100)==COH_OK);CHECK(coh_db_session_service(s,100,(CohCancel){0})==COH_OK);
    CohNetPacket first=frame_read(&peer,5,1),reply=control(5,100,2,1,0);reply.ack_count=1;reply.acks[0]=first.id;
    frame_send(&peer,local(s),5,&reply);CHECK(coh_db_session_service(s,101,(CohCancel){0})==COH_UNSUPPORTED);
    CHECK(coh_db_session_phase(s)==COH_DB_FAILED);CohDbSessionDiagnostics d;coh_db_session_diagnostics(s,&d);
    CHECK(!d.login_requests&&d.transport.datagrams_sent==1&&d.transport.sockets_opened==d.transport.sockets_closed);
    coh_db_session_destroy(s);peer_close(&peer);scenarios++;
}
static void reliable_retry(void) {
    Peer peer=peer_open();CohDbSessionConfig c=configuration(&peer,5,0);CohDbSession *s=coh_db_session_create(&c);CHECK(s);
    CohNetPacket login=handshake(s,&peer,5,444,100);uint64_t now=103+coh_net_retry_ms(0,c.transport.link.ping_ms,0);
    CHECK(coh_db_session_service(s,now,(CohCancel){0})==COH_OK);CohNetPacket retry=frame_read(&peer,5,0);
    CHECK(retry.id==login.id&&retry.payload_bits==login.payload_bits&&!memcmp(retry.payload,login.payload,(login.payload_bits+7)/8));
    peer_message(&peer,local(s),5,queue0,queue0_bits,0,login.id);CHECK(coh_db_session_service(s,now+1,(CohCancel){0})==COH_OK);drain_ack(&peer,5);
    CohDbSessionDiagnostics d;coh_db_session_diagnostics(s,&d);CHECK(d.login_requests==1&&d.transport.link.retransmits==1&&d.phase==COH_DB_QUEUED);
    CHECK(coh_db_session_service(s,102+c.request_timeout_ms,(CohCancel){0})==COH_STATE);CHECK(coh_db_session_phase(s)==COH_DB_TIMED_OUT);
    coh_db_session_destroy(s);peer_close(&peer);scenarios++;
}
static void local_development(unsigned which) {
    Peer peer=peer_open();CohDbSessionConfig c=configuration(&peer,5,0);CohDbSession *s=coh_db_session_create(&c);CHECK(s);
    CohNetPacket request=handshake_uid(s,&peer,5,555,100,0);CohNetEndpoint target=local(s);
    const uint8_t *data=which==1?players_zero0:players0;size_t bits=which==1?players_zero0_bits:players0_bits;
    peer_message(&peer,target,5,data,bits,0,request.id);CohStatus status=coh_db_session_service(s,104,(CohCancel){0});drain_ack(&peer,5);
    CohDbSessionDiagnostics d;coh_db_session_diagnostics(s,&d);CHECK(d.local_development_auth==1);
    if(which==1){CHECK(status==COH_INVALID&&d.phase==COH_DB_FAILED&&!d.server_identity_bound);}
    else {
        CHECK(status==COH_OK&&d.phase==COH_DB_CHARACTERS&&d.server_identity_bound);
        CohDbPlayers p;CHECK(coh_db_session_players(s,&p)==COH_OK&&p.user_id==12345);
        if(which==2){peer_message(&peer,target,5,players_rebound0,players_rebound0_bits,0,0);CHECK(coh_db_session_service(s,105,(CohCancel){0})==COH_INVALID);drain_ack(&peer,5);CHECK(coh_db_session_phase(s)==COH_DB_FAILED);}
        else {
            peer_message(&peer,target,5,players0,players0_bits,0,0);CHECK(coh_db_session_service(s,105,(CohCancel){0})==COH_OK);drain_ack(&peer,5);
            CHECK(coh_db_session_choose(s,0,0,0,106)==COH_OK);CHECK(coh_db_session_service(s,106,(CohCancel){0})==COH_OK);request=frame_read(&peer,5,0);
            peer_message(&peer,target,5,map0,map0_bits,0,request.id);CHECK(coh_db_session_service(s,107,(CohCancel){0})==COH_OK);drain_ack(&peer,5);
            CohDbSessionHandoff h;CHECK(coh_db_session_take_handoff(s,&h)==COH_OK&&h.map.cookie==123456&&h.selected_slot==0&&h.selected_dbid==17);
        }
    }
    coh_db_session_suspend(s);CohDbLogin login;CohDbAuthReceipt auth;login_configuration(&login,&auth,1);login.user_id=login.cookie=0;
    CHECK(coh_db_session_begin(s,&login,&auth,556,108)==COH_STATE);
    CHECK(coh_db_session_begin_local(s,&login,1,556,108)==COH_STATE);
    CHECK(coh_db_session_begin_local(s,&login,2,556,108)==COH_OK);coh_db_session_cancel(s);
    coh_db_session_diagnostics(s,&d);CHECK(d.transport.sockets_opened==d.transport.sockets_closed);
    coh_db_session_destroy(s);peer_close(&peer);scenarios++;
}
static void local_policy_rejections(void) {
    Peer peer=peer_open();CohDbSessionConfig c=configuration(&peer,5,0);CohDbLogin login;CohDbAuthReceipt auth;login_configuration(&login,&auth,1);login.user_id=login.cookie=0;
    for(unsigned i=0;i<2;i++){
        if(i==0)c.transport.peer.address[0]=10;else {c.transport.peer=peer.endpoint;c.transport.local.address[0]=0;c.transport.local.address[3]=0;}
        CohDbSession *s=coh_db_session_create(&c);CHECK(s);
        CHECK(coh_db_session_begin_local(s,&login,1,1,100)==COH_STATE);
        CohDbSessionDiagnostics d;coh_db_session_diagnostics(s,&d);CHECK(!d.transport.sockets_opened);
        coh_db_session_destroy(s);
    }
    peer_close(&peer);scenarios++;
}
static unsigned descriptors(void) {
    DIR *d=opendir("/proc/self/fd");CHECK(d);unsigned n=0;struct dirent *e;while((e=readdir(d)))if(e->d_name[0]!='.')n++;CHECK(!closedir(d));return n;
}
int main(void) {
    unsigned before=descriptors();local_development(0);local_development(1);local_development(2);local_policy_rejections();happy(0,0);happy(5,0);happy(5,1);receipt_and_lifecycle();rejection(0);rejection(1);rejection(2);rejection(3);encryption_policy();reliable_retry();CHECK(before==descriptors());
    printf("{\"passed\":true,\"checks\":%u,\"socket_scenarios\":%u,\"actual_os_udp\":true,\"source_layout_peer\":true,\"real_authenticated_server\":false,\"socket_leak_check\":true}\n",checks,scenarios);return 0;
}
