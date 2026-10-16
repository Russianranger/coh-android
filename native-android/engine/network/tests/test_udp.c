#define _POSIX_C_SOURCE 200809L
#include "coh_net_udp.h"
#include <arpa/inet.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static unsigned checks,scenarios,negative;
#define CHECK(x) do {checks++;if(!(x)){fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#x);exit(1);}}while(0)
typedef struct {int fd;CohNetEndpoint endpoint;} Peer;
static struct sockaddr_in addr(CohNetEndpoint endpoint) {
    struct sockaddr_in a;memset(&a,0,sizeof(a));a.sin_family=AF_INET;a.sin_port=htons(endpoint.port);
    memcpy(&a.sin_addr.s_addr,endpoint.address,4);return a;
}
static Peer peer_open(void) {
    Peer p={-1,{{127,0,0,1},0}};p.fd=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);CHECK(p.fd>=0);
    struct sockaddr_in a=addr(p.endpoint);CHECK(bind(p.fd,(struct sockaddr*)&a,sizeof(a))==0);
    socklen_t size=sizeof(a);CHECK(getsockname(p.fd,(struct sockaddr*)&a,&size)==0&&size==sizeof(a));p.endpoint.port=ntohs(a.sin_port);
    CHECK(fcntl(p.fd,F_SETFL,O_NONBLOCK)==0);return p;
}
static void peer_close(Peer p) {CHECK(close(p.fd)==0);}
static void peer_send(Peer p,CohNetEndpoint target,const void *bytes,size_t size) {
    struct sockaddr_in a=addr(target);CHECK(sendto(p.fd,bytes,size,0,(struct sockaddr*)&a,sizeof(a))==(ssize_t)size);
}
static CohNetPacket command(unsigned ver,uint32_t id,uint32_t cmd,int value_present,uint32_t value) {
    CohNetPacket p;memset(&p,0,sizeof(p));p.id=id;CohProtocolBits b;
    CHECK(coh_protocol_bits_init(&b,p.payload,sizeof(p.payload),0,1)==COH_OK);
    if(ver>=4&&cmd!=1){CHECK(coh_protocol_write_pack(&b,1,0)==COH_OK);if(cmd)CHECK(coh_protocol_write_pack(&b,1,cmd)==COH_OK);}
    else CHECK(coh_protocol_write_pack(&b,1,cmd)==COH_OK);
    if(value_present)CHECK(coh_protocol_write_pack(&b,1,value)==COH_OK);
    p.payload_bits=(uint32_t)b.bit_length;return p;
}
static void peer_frame(Peer p,CohNetEndpoint target,unsigned ver,CohNetPacket packet) {
    uint8_t frame[COH_PROTOCOL_FRAME_MAX];size_t bytes=0;
    CHECK(coh_net_frame_encode(ver,NULL,0,&packet,frame,sizeof(frame),&bytes)==COH_OK);peer_send(p,target,frame,bytes);
}
static CohNetPacket peer_read(Peer peer,unsigned ver,int connect) {
    struct pollfd pollfd={peer.fd,POLLIN,0};CHECK(poll(&pollfd,1,100)==1&&(pollfd.revents&POLLIN));
    uint8_t frame[COH_PROTOCOL_FRAME_MAX];ssize_t size=recv(peer.fd,frame,sizeof(frame),0);CHECK(size>0);
    CohNetPacket p;CHECK(coh_net_frame_decode(ver,NULL,0,connect,(CohBytes){frame,(size_t)size},&p)==COH_OK);return p;
}
static uint32_t packet_command(CohNetPacket p,unsigned ver,int control) {
    CohProtocolBits b;uint32_t cmd;CHECK(coh_protocol_bits_init(&b,p.payload,sizeof(p.payload),p.payload_bits,0)==COH_OK);
    CHECK(coh_protocol_read_pack(&b,1,&cmd)==COH_OK);
    if(ver>=4&&control&&cmd==0&&b.cursor<b.bit_length)CHECK(coh_protocol_read_pack(&b,1,&cmd)==COH_OK);
    return cmd;
}
static CohNetUdpConfig config(Peer p,unsigned ver) {
    CohNetUdpConfig c;memset(&c,0,sizeof(c));c.link=coh_net_default_config();c.link.version=ver;
    c.peer=p.endpoint;c.local.address[0]=127;c.local.address[3]=1;c.receive_budget=8;return c;
}
static CohNetEndpoint local(CohNetUdp *u) {CohNetEndpoint e;CHECK(coh_net_udp_local_endpoint(u,&e)==COH_OK);CHECK(e.port);return e;}
static void connected_after_begin(CohNetUdp *u,Peer peer,unsigned ver,uint64_t now) {
    CHECK(coh_net_udp_service(u,now,(CohCancel){0})==COH_OK);
    CohNetPacket first=peer_read(peer,ver,1);CHECK(first.id==1&&packet_command(first,ver,1)==1);
    CohNetEndpoint target=local(u);CohNetPacket p=command(ver,100,2,1,0);p.ack_count=1;p.acks[0]=first.id;
    peer_frame(peer,target,ver,p);CHECK(coh_net_udp_service(u,now+1,(CohCancel){0})==COH_OK);
    CohNetPacket reply=peer_read(peer,ver,0);CHECK(reply.id==2&&packet_command(reply,ver,1)==3);
    p=command(ver,101,4,0,0);p.ack_count=1;p.acks[0]=reply.id;peer_frame(peer,target,ver,p);
    CHECK(coh_net_udp_service(u,now+2,(CohCancel){0})==COH_OK);reply=peer_read(peer,ver,0);CHECK(packet_command(reply,ver,1)==0);
    CohNetUdpDiagnostics d;coh_net_udp_diagnostics(u,&d);CHECK(d.state==COH_UDP_ACTIVE&&d.link_state==COH_NET_CONNECTED);scenarios++;
}
static void connected(CohNetUdp *u,Peer peer,unsigned ver,uint32_t id,uint64_t now) {
    CHECK(coh_net_udp_begin(u,id,now)==COH_OK);connected_after_begin(u,peer,ver,now);
}
static unsigned descriptor_count(void) {
    DIR *dir=opendir("/proc/self/fd");CHECK(dir);unsigned count=0;struct dirent *item;
    while((item=readdir(dir)))if(item->d_name[0]!='.')count++;
    CHECK(closedir(dir)==0);return count;
}
static void test_configuration(void) {
    Peer peer=peer_open();CohNetUdpConfig c=config(peer,5);CHECK(coh_net_udp_config_validate(&c)==COH_OK);
    CohNetUdpConfig bad=c;bad.peer.port=0;CHECK(coh_net_udp_config_validate(&bad)==COH_INVALID);negative++;
    const uint8_t invalid[][4]={{0,0,0,0},{0,1,2,3},{224,0,0,1},{239,1,2,3},{255,255,255,255}};
    for(unsigned i=0;i<sizeof(invalid)/sizeof(invalid[0]);i++){bad=c;memcpy(bad.peer.address,invalid[i],4);CHECK(!coh_net_udp_create(&bad));negative++;}
    bad=c;bad.receive_budget=0;CHECK(!coh_net_udp_create(&bad));bad.receive_budget=65;CHECK(!coh_net_udp_create(&bad));negative+=2;
    bad=c;bad.link.version=6;CHECK(!coh_net_udp_create(&bad));negative++;
    bad=c;bad.local.address[0]=224;CHECK(!coh_net_udp_create(&bad));negative++;
    CHECK(coh_net_udp_config_validate(NULL)==COH_INVALID);CHECK(coh_net_udp_service(NULL,0,(CohCancel){0})==COH_INVALID);
    CHECK(coh_net_udp_state(NULL)==COH_UDP_FAILED);coh_net_udp_destroy(NULL);peer_close(peer);scenarios++;
}
static void test_exchange(void) {
    for(unsigned ver=0;ver<=5;ver++) {
        Peer peer=peer_open(),wrong=peer_open();CohNetUdpConfig c=config(peer,ver);CohNetUdp *u=coh_net_udp_create(&c);CHECK(u);
        connected(u,peer,ver,123,100);CohNetEndpoint target=local(u);
        uint8_t too_large[COH_PROTOCOL_FRAME_MAX+1];memset(too_large,0xa5,sizeof(too_large));
        peer_send(wrong,target,too_large,sizeof(too_large));peer_send(peer,target,too_large,sizeof(too_large));
        peer_send(peer,target,"",0);uint8_t bad[4]={1,2,3,4};peer_send(peer,target,bad,sizeof(bad));
        CohNetPacket p;memset(&p,0,sizeof(p));p.id=102;
        CohProtocolBits bits;CHECK(coh_protocol_bits_init(&bits,p.payload,sizeof(p.payload),0,1)==COH_OK);
        CHECK(coh_protocol_write_pack(&bits,1,10)==COH_OK);CHECK(coh_protocol_write(&bits,32,0x12345678)==COH_OK);p.payload_bits=(uint32_t)bits.bit_length;
        peer_frame(peer,target,ver,p);CHECK(coh_net_udp_service(u,103,(CohCancel){0})==COH_OK);
        CohNetPacket ack=peer_read(peer,ver,0);CHECK(ack.ack_count==1&&ack.acks[0]==102);
        CohNetMessage m;CHECK(coh_net_udp_next(u,&m)==COH_OK&&m.id==102&&m.payload_bits==p.payload_bits&&!memcmp(m.payload,p.payload,(p.payload_bits+7)/8));
        CHECK(coh_net_udp_next(u,&m)==COH_NOT_FOUND);
        CohNetUdpDiagnostics d;coh_net_udp_diagnostics(u,&d);
        CHECK(d.peer_rejects==1&&d.truncated==1&&d.empty==1&&d.malformed==1);negative+=4;
        CHECK(d.link.received==3&&d.link.malformed==1);CHECK(coh_net_udp_service(u,102,(CohCancel){0})==COH_INVALID);negative++;
        CHECK(coh_net_udp_queue(u,(CohBytes){p.payload,(p.payload_bits+7)/8},p.payload_bits,1,0,0,104)==COH_OK);
        CHECK(coh_net_udp_service(u,104,(CohCancel){0})==COH_OK);CohNetPacket sent=peer_read(peer,ver,0);
        CHECK(sent.id==ack.id+1&&sent.payload_bits==p.payload_bits&&!memcmp(sent.payload,p.payload,(p.payload_bits+7)/8));
        /* Deliberately withhold ACK. Actual UDP retransmits identical ID/body. */
        CHECK(coh_net_udp_service(u,104+coh_net_retry_ms(0,100,0),(CohCancel){0})==COH_OK);
        CohNetPacket retry=peer_read(peer,ver,0);CHECK(retry.id==sent.id&&retry.payload_bits==sent.payload_bits&&!memcmp(retry.payload,sent.payload,(sent.payload_bits+7)/8));
        p=command(ver,103,0,0,0);p.ack_count=1;p.acks[0]=sent.id;peer_frame(peer,target,ver,p);
        uint64_t now=105+coh_net_retry_ms(0,100,0);CHECK(coh_net_udp_service(u,now,(CohCancel){0})==COH_OK);(void)peer_read(peer,ver,0);
        coh_net_udp_diagnostics(u,&d);CHECK(!d.link.tx_pending&&d.link.retransmits==1);
        /* Gameplay enqueued before disconnect must not escape after shutdown. */
        CHECK(coh_net_udp_queue(u,(CohBytes){sent.payload,(sent.payload_bits+7)/8},sent.payload_bits,1,0,0,now)==COH_OK);
        CHECK(coh_net_udp_disconnect(u,now)==COH_OK);CHECK(coh_net_udp_queue(u,(CohBytes){sent.payload,1},8,1,0,0,now)==COH_STATE);
        CHECK(coh_net_udp_service(u,now,(CohCancel){0})==COH_OK);CohNetPacket bye=peer_read(peer,ver,0);CHECK(packet_command(bye,ver,1)==5);
        p=command(ver,104,6,0,0);p.ack_count=1;p.acks[0]=bye.id;peer_frame(peer,target,ver,p);
        CHECK(coh_net_udp_service(u,now+1,(CohCancel){0})==COH_OK);CHECK(coh_net_udp_state(u)==COH_UDP_CLOSED);
        coh_net_udp_diagnostics(u,&d);CHECK(d.sockets_opened==1&&d.sockets_closed==1&&!d.link.tx_pending);
        CHECK(coh_net_udp_local_endpoint(u,&target)==COH_STATE);coh_net_udp_destroy(u);peer_close(wrong);peer_close(peer);scenarios++;
    }
}
static int cancel_poll(void *context) {unsigned *left=context;return !(*left)--;}
static void test_lifecycle(void) {
    Peer peer=peer_open();CohNetUdpConfig c=config(peer,5);CohNetUdp *u=coh_net_udp_create(&c);CHECK(u);connected(u,peer,5,321,100);
    CHECK(coh_net_udp_service(u,103,(CohCancel){0})==COH_OK);coh_net_udp_suspend(u);coh_net_udp_suspend(u);
    CohNetUdpDiagnostics d;coh_net_udp_diagnostics(u,&d);CHECK(d.state==COH_UDP_SUSPENDED&&d.sockets_opened==d.sockets_closed&&d.suspends==1);
    CHECK(coh_net_udp_service(u,10000,(CohCancel){0})==COH_STATE);CHECK(coh_net_udp_resume(u,321,104)==COH_INVALID);negative+=2;
    CHECK(coh_net_udp_resume(u,322,102)==COH_INVALID);CHECK(coh_net_udp_resume(u,322,104)==COH_OK);
    CHECK(coh_net_udp_service(u,104,(CohCancel){0})==COH_OK);CohNetPacket p=peer_read(peer,5,1);CHECK(p.id==1&&p.ack_count==0);
    coh_net_udp_diagnostics(u,&d);CHECK(d.resumes==1&&d.sockets_opened==2&&d.sockets_closed==1&&!d.link.received);
    unsigned remaining=0;CHECK(coh_net_udp_service(u,105,(CohCancel){cancel_poll,&remaining})==COH_CANCELLED);
    coh_net_udp_diagnostics(u,&d);CHECK(d.sockets_opened==d.sockets_closed&&d.cancellations==1&&d.link_state==COH_NET_CANCELLED&&!d.link.tx_pending);
    CHECK(coh_net_udp_resume(u,323,106)==COH_OK);CHECK(coh_net_udp_service(u,106+c.link.connect_timeout_ms,(CohCancel){0})==COH_STATE);
    coh_net_udp_diagnostics(u,&d);CHECK(d.state==COH_UDP_TIMED_OUT&&d.timeouts==1&&d.sockets_opened==d.sockets_closed);
    coh_net_udp_close(u);coh_net_udp_close(u);coh_net_udp_diagnostics(u,&d);CHECK(d.sockets_opened==d.sockets_closed);
    coh_net_udp_destroy(u);peer_close(peer);scenarios++;
}
static void test_rejections_cleanup(void) {
    Peer peer=peer_open();CohNetUdpConfig c=config(peer,5);c.receive_budget=2;CohNetUdp *u=coh_net_udp_create(&c);CHECK(u);
    CHECK(coh_net_udp_begin(u,10,0)==COH_OK);CHECK(coh_net_udp_service(u,0,(CohCancel){0})==COH_OK);(void)peer_read(peer,5,1);
    CohNetEndpoint target=local(u);uint8_t bad[3]={1,2,3};for(unsigned i=0;i<5;i++)peer_send(peer,target,bad,sizeof(bad));
    CHECK(coh_net_udp_service(u,1,(CohCancel){0})==COH_OK);CohNetUdpDiagnostics d;coh_net_udp_diagnostics(u,&d);
    CHECK(d.datagrams_received==2&&d.malformed==2&&d.receive_budget_exhausted==1);
    CHECK(coh_net_udp_service(u,2,(CohCancel){0})==COH_OK);CHECK(coh_net_udp_service(u,3,(CohCancel){0})==COH_OK);
    coh_net_udp_diagnostics(u,&d);CHECK(d.datagrams_received==5&&d.malformed==5&&d.receive_budget_exhausted==2);
    /* An encrypted request is rejected explicitly. No clear CLIENT_ACK is sent. */
    CohNetPacket p=command(5,100,2,1,1);p.payload_bits=(uint32_t)((p.payload_bits+7u)&~7u)+512;peer_frame(peer,target,5,p);
    CHECK(coh_net_udp_service(u,4,(CohCancel){0})==COH_UNSUPPORTED);coh_net_udp_diagnostics(u,&d);
    CHECK(d.state==COH_UDP_ENCRYPTION_REQUIRED&&d.link_state==COH_NET_ENCRYPTION_REQUIRED&&d.sockets_opened==d.sockets_closed&&d.datagrams_sent==1);
    coh_net_udp_destroy(u);negative+=6;
    /* Binding an occupied port is a deterministic socket-creation failure. */
    c=config(peer,5);c.local=peer.endpoint;u=coh_net_udp_create(&c);CHECK(u);CHECK(coh_net_udp_begin(u,11,0)==COH_IO);
    coh_net_udp_diagnostics(u,&d);CHECK(d.state==COH_UDP_FAILED&&d.io_errors==1&&d.sockets_opened==d.sockets_closed);coh_net_udp_destroy(u);negative++;
    unsigned before=descriptor_count();
    for(unsigned i=0;i<64;i++){c=config(peer,5);u=coh_net_udp_create(&c);CHECK(u);CHECK(coh_net_udp_begin(u,12,i)==COH_OK);coh_net_udp_suspend(u);coh_net_udp_destroy(u);}
    CHECK(before==descriptor_count());peer_close(peer);scenarios++;
}
static CohNetOwnedMessage owned_message(CohNetUdp *u,Peer peer,uint32_t id,uint64_t now) {
    CohNetPacket p;memset(&p,0,sizeof(p));p.id=id;CohProtocolBits bits;
    CHECK(coh_protocol_bits_init(&bits,p.payload,sizeof(p.payload),0,1)==COH_OK);
    CHECK(coh_protocol_write_pack(&bits,1,10)==COH_OK);
    CHECK(coh_protocol_write(&bits,32,0x12345678)==COH_OK);p.payload_bits=(uint32_t)bits.bit_length;
    peer_frame(peer,local(u),5,p);CHECK(coh_net_udp_service(u,now,(CohCancel){0})==COH_OK);
    CohNetPacket ack=peer_read(peer,5,0);CHECK(ack.ack_count==1&&ack.acks[0]==id);
    CohNetOwnedMessage view;memset(&view,0,sizeof(view));CHECK(coh_net_udp_next_owned(u,&view)==COH_OK);
    CHECK(view.id==id&&view.payload_bits==p.payload_bits&&view.payload_bytes==(p.payload_bits+7)/8);
    CHECK(view.payload&&view.generation&&!memcmp(view.payload,p.payload,view.payload_bytes));return view;
}
static void no_owned(CohNetUdp *u) {
    CohNetUdpDiagnostics d;coh_net_udp_diagnostics(u,&d);CHECK(!d.link.owned_retained_bytes);
}
static void test_owned_lifecycle(void) {
    Peer peer=peer_open();CohNetUdpConfig c=config(peer,5);CohNetUdp *u=coh_net_udp_create(&c);CHECK(u);
    CHECK(coh_net_udp_set_decoded_budget(u,COH_NET_MESSAGE_MAX-1)==COH_INVALID);
    CHECK(coh_net_udp_set_decoded_budget(u,COH_NET_DECODED_MAX+1)==COH_INVALID);
    CHECK(coh_net_udp_set_decoded_budget(u,COH_NET_DECODED_MAX)==COH_OK);negative+=2;
    connected(u,peer,5,400,100);CHECK(coh_net_udp_set_decoded_budget(u,COH_NET_MESSAGE_MAX)==COH_STATE);negative++;
    CohNetOwnedMessage first=owned_message(u,peer,102,103),stale=first;
    CohNetOwnedMessage untouched;memset(&untouched,0xa5,sizeof(untouched));CohNetOwnedMessage saved=untouched;
    CHECK(coh_net_udp_next_owned(u,&untouched)==COH_STATE&&!memcmp(&untouched,&saved,sizeof(saved)));
    CohNetMessage legacy;CHECK(coh_net_udp_next(u,&legacy)==COH_STATE);negative+=2;
    coh_net_udp_suspend(u);no_owned(u);
    CHECK(coh_net_udp_owned_release(u,&first)==COH_STATE&&!first.payload&&!first.generation);negative++;
    CHECK(coh_net_udp_resume(u,401,104)==COH_OK);connected_after_begin(u,peer,5,104);
    CohNetOwnedMessage current=owned_message(u,peer,102,107);
    CHECK(current.generation>stale.generation);
    /* Deliberately model allocator address reuse across the fresh NetLink.
     * Its older wrapper generation must never release the current lease. */
    stale.payload=current.payload;
    CHECK(coh_net_udp_owned_release(u,&stale)==COH_STATE&&!stale.payload&&!stale.generation);negative++;
    CohNetUdpDiagnostics d;coh_net_udp_diagnostics(u,&d);CHECK(d.link.owned_retained_bytes==current.payload_bytes);
    CHECK(current.payload[0]!=0);CHECK(coh_net_udp_owned_release(u,&current)==COH_OK);no_owned(u);
    CHECK(coh_net_udp_owned_release(u,&current)==COH_STATE);negative++;
    current=owned_message(u,peer,103,108);coh_net_udp_close(u);no_owned(u);
    CHECK(coh_net_udp_owned_release(u,&current)==COH_STATE);negative++;
    connected(u,peer,5,402,110);current=owned_message(u,peer,102,113);
    coh_net_udp_cancel(u);no_owned(u);CHECK(coh_net_udp_owned_release(u,&current)==COH_STATE);negative++;
    CHECK(coh_net_udp_resume(u,403,114)==COH_OK);connected_after_begin(u,peer,5,114);
    current=owned_message(u,peer,102,117);CHECK(coh_net_udp_disconnect(u,118)==COH_OK);no_owned(u);
    CHECK(coh_net_udp_owned_release(u,&current)==COH_STATE);negative++;
    coh_net_udp_close(u);connected(u,peer,5,404,120);current=owned_message(u,peer,102,123);
    CHECK(coh_net_udp_service(u,123+c.link.idle_timeout_ms,(CohCancel){0})==COH_STATE);
    CHECK(coh_net_udp_state(u)==COH_UDP_TIMED_OUT);no_owned(u);
    CHECK(coh_net_udp_owned_release(u,&current)==COH_STATE);negative++;
    coh_net_udp_diagnostics(u,&d);CHECK(d.sockets_opened==d.sockets_closed&&d.sockets_opened==5);
    coh_net_udp_destroy(u);peer_close(peer);scenarios++;
}
int main(void) {
    unsigned before=descriptor_count();test_configuration();test_exchange();test_lifecycle();test_rejections_cleanup();test_owned_lifecycle();CHECK(before==descriptor_count());
    printf("{\"checks\":%u,\"negative_cases\":%u,\"socket_scenarios\":%u,\"actual_os_udp\":true,\"socket_leak_check\":true,\"live_server_interoperability\":false}\n",checks,negative,scenarios);return 0;
}
