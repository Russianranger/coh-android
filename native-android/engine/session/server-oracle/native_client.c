#define _POSIX_C_SOURCE 200809L
#include "coh_net_udp.h"
#include "coh_session_crypto.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"FAILED %s:%d %s\n",__FILE__,__LINE__,#x);exit(1);}}while(0)
static uint64_t clock_ms(void){struct timespec ts;CHECK(clock_gettime(CLOCK_MONOTONIC,&ts)==0);return (uint64_t)ts.tv_sec*1000+(uint64_t)ts.tv_nsec/1000000;}
static void tick(CohNetUdp *u){CHECK(coh_net_udp_service(u,clock_ms(),(CohCancel){0})==COH_OK);struct timespec t={0,1000000};while(nanosleep(&t,&t)&&errno==EINTR){}}
int main(int argc,char **argv){
 CHECK(argc==4);unsigned port=(unsigned)strtoul(argv[1],NULL,10),version=(unsigned)strtoul(argv[2],NULL,10),encrypted=(unsigned)strtoul(argv[3],NULL,10);CHECK(port&&port<65536&&version<=5&&version!=1&&version!=3&&encrypted<=1);
 CohNetUdpConfig c;memset(&c,0,sizeof(c));c.link=coh_net_default_config();c.link.version=version;c.link.connect_timeout_ms=2500;c.peer=(CohNetEndpoint){{127,0,0,1},(uint16_t)port};c.local=(CohNetEndpoint){{127,0,0,1},0};c.receive_budget=8;
 c.key_exchange=coh_session_key_exchange;c.key_context=(void*)coh_auth_openssl_provider();c.encryption_required=(int)encrypted;CohNetUdp *u=coh_net_udp_create(&c);CHECK(u);CHECK(coh_net_udp_begin(u,0x484F4354,clock_ms())==COH_OK);
 uint64_t end=clock_ms()+3000;CohNetUdpDiagnostics d;
 do{tick(u);coh_net_udp_diagnostics(u,&d);}while(d.link_state!=COH_NET_CONNECTED&&clock_ms()<end);CHECK(d.link_state==COH_NET_CONNECTED);
 uint8_t bytes[32]={0};CohProtocolBits b;CHECK(coh_protocol_bits_init(&b,bytes,sizeof(bytes),0,1)==COH_OK);CHECK(coh_protocol_write_pack(&b,1,10)==COH_OK);CHECK(coh_protocol_write(&b,32,0x12345678)==COH_OK);
 CHECK(coh_net_udp_queue(u,(CohBytes){bytes,(b.bit_length+7)/8},(uint32_t)b.bit_length,1,0,0,clock_ms())==COH_OK);CohNetMessage m;CohStatus s;
 do{tick(u);s=coh_net_udp_next(u,&m);}while(s==COH_NOT_FOUND&&clock_ms()<end);CHECK(s==COH_OK);uint32_t cmd=0,value=0;CHECK(coh_protocol_bits_init(&b,m.payload,(m.payload_bits+7)/8,m.payload_bits,0)==COH_OK);CHECK(coh_protocol_read_pack(&b,1,&cmd)==COH_OK&&cmd==11);CHECK(coh_protocol_read(&b,32,&value)==COH_OK&&value==0x12345678);
 CHECK(coh_net_udp_disconnect(u,clock_ms())==COH_OK);do{tick(u);}while(coh_net_udp_state(u)==COH_UDP_ACTIVE&&clock_ms()<end);CHECK(coh_net_udp_state(u)==COH_UDP_CLOSED);coh_net_udp_diagnostics(u,&d);CHECK(d.sockets_opened==1&&d.sockets_closed==1&&d.link.tx_pending==0);CHECK(d.malformed==2&&d.empty==1);
 coh_net_udp_destroy(u);printf("{\"checks\":%u,\"connected\":true,\"payload_exchange\":true,\"closed\":true,\"retransmits\":%llu,\"acknowledged\":%llu,\"sockets_opened\":%llu,\"sockets_closed\":%llu}\n",checks,(unsigned long long)d.link.retransmits,(unsigned long long)d.link.acknowledged,(unsigned long long)d.sockets_opened,(unsigned long long)d.sockets_closed);return 0;
}
