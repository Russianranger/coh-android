/* New focused controls only. Outer capture service/request bracket are explicit
 * doubles. UDP/net/codec/queue/pump/ACK and loopback sockets below are real. */
#include "coh_request_tx_internal.h"
#include "coh_request_tx_udp.c" /* test-only access to this real UDP's link/fd */
#include <stdio.h>
#include <sys/time.h>
static unsigned checks,real_request_datagrams,real_io_errors,services;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"request-tx:%d\n",__LINE__);exit(1);}}while(0)
typedef enum { NOOP,QUEUE,PUMP,SELECTIVE,LIMIT_HOOKS,DIRECT_UDP_PUMP } Action;
typedef struct {CohNetUdp*u;Action action;int other;CohStatus status;uint32_t request_id,other_id;uint64_t now;} Control;
static Control *closing;
static CohStatus observer(void*c,const CohInitialCapture*o,const CohInitialCaptureEvent*e){(void)c;(void)o;(void)e;return COH_OK;}
static uint32_t command(CohNetPacket*p){CohProtocolBits b;uint32_t cmd=999;CHECK(!coh_protocol_bits_init(&b,p->payload,sizeof(p->payload),p->payload_bits,0));CHECK(!coh_protocol_read_pack(&b,1,&cmd));return cmd;}
static CohStatus selective(void*opaque,CohBytes bytes){
 Control*c=opaque;CohNetPacket p;CHECK(coh_net_frame_decode(5,NULL,0,0,bytes,&p)==COH_OK);
 if(command(&p)==COH_MAP_REQALLENTS){c->request_id=p.id;return c->status;}c->other_id=p.id;return COH_OK;
}
static void payload(uint32_t cmd,uint8_t data[8],uint32_t*bits){CohProtocolBits b;memset(data,0,8);CHECK(!coh_protocol_bits_init(&b,data,8,0,1));CHECK(!coh_protocol_write_pack(&b,1,cmd));*bits=(uint32_t)b.bit_length;}
CohStatus coh_initial_capture_service(CohInitialCapture*owner,uint64_t now,CohCancel cancel,CohInitialCaptureObserver fn,void*context,size_t size){
 Control*c=context;(void)cancel;CHECK(fn==observer&&size==sizeof(*c));services++;c->now=now;
 if(c->action==NOOP)return c->status;
 if(c->action==QUEUE){uint8_t data[8];uint32_t bits;payload(COH_MAP_REQSCENE,data,&bits);if(c->other)CHECK(coh_net_udp_queue(c->u,(CohBytes){data,(bits+7)/8},bits,1,0,0,now)==COH_OK);
  payload(COH_MAP_REQALLENTS,data,&bits);coh_request_tx_hook_begin(owner,c->u,now);CohStatus s=coh_net_udp_queue(c->u,(CohBytes){data,(bits+7)/8},bits,1,0,0,now);coh_request_tx_hook_end(s);return s;}
 if(c->action==DIRECT_UDP_PUMP)return coh_net_pump(c->u->link,now,send_frame,c->u,(CohCancel){0});
 if(c->action==PUMP)return coh_net_udp_service(c->u,now,(CohCancel){0});
 if(c->action==SELECTIVE)return coh_net_pump(c->u->link,now,selective,c,(CohCancel){0});
 if(c->action==LIMIT_HOOKS){for(unsigned i=0;i<COH_REQUEST_TX_EVENT_MAX;i++){coh_request_tx_hook_send_begin(c->u->link,c->request_id,0,now);coh_request_tx_hook_send(c->u->link,c->request_id,0,COH_NOT_FOUND,now);}return COH_OK;}
 return COH_INVALID;
}
void coh_initial_capture_close(CohInitialCapture*owner){(void)owner;if(closing)coh_net_udp_close(closing->u);}
void coh_initial_capture_cancel(CohInitialCapture*owner){(void)owner;if(closing)coh_net_udp_cancel(closing->u);}
void coh_initial_capture_timeout(CohInitialCapture*owner){(void)owner;if(closing)coh_net_udp_close(closing->u);}
static CohNetPacket peer_command(uint32_t id,uint32_t cmd,int value){
 CohNetPacket p;memset(&p,0,sizeof(p));p.id=id;CohProtocolBits b;CHECK(!coh_protocol_bits_init(&b,p.payload,sizeof(p.payload),0,1));
 CHECK(!coh_protocol_write_pack(&b,1,0));if(cmd)CHECK(!coh_protocol_write_pack(&b,1,cmd));if(value)CHECK(!coh_protocol_write_pack(&b,1,0));p.payload_bits=(uint32_t)b.bit_length;return p;
}
static void peer_send(int peer,CohNetUdp*u,CohNetPacket*p,int corrupt){
 uint8_t raw[COH_PROTOCOL_FRAME_MAX];size_t size=0;CHECK(coh_net_frame_encode(5,NULL,0,p,raw,sizeof(raw),&size)==COH_OK);if(corrupt)raw[4]^=128;
 CohNetEndpoint endpoint;CHECK(coh_net_udp_local_endpoint(u,&endpoint)==COH_OK);struct sockaddr_in target=address(endpoint);CHECK(sendto(peer,raw,size,0,(struct sockaddr*)&target,sizeof(target))==(ssize_t)size);
}
static CohNetPacket peer_receive(int peer,int connect){uint8_t raw[COH_PROTOCOL_FRAME_MAX];ssize_t size=recv(peer,raw,sizeof(raw),0);CHECK(size>0);CohNetPacket p;CHECK(coh_net_frame_decode(5,NULL,0,connect,(CohBytes){raw,(size_t)size},&p)==COH_OK);return p;}
static unsigned drain(int peer,uint32_t*request_id){
 unsigned requests=0;for(;;){uint8_t raw[COH_PROTOCOL_FRAME_MAX];ssize_t size=recv(peer,raw,sizeof(raw),MSG_DONTWAIT);if(size<0){CHECK(errno==EAGAIN||errno==EWOULDBLOCK);break;}
  CohNetPacket p;CHECK(coh_net_frame_decode(5,NULL,0,0,(CohBytes){raw,(size_t)size},&p)==COH_OK);if(command(&p)==COH_MAP_REQALLENTS){requests++;*request_id=p.id;}}
 real_request_datagrams+=requests;return requests;
}
static CohNetUdp *connected(int*peer){
 *peer=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);CHECK(*peer>=0);struct sockaddr_in bind_to=address((CohNetEndpoint){{127,0,0,1},0});CHECK(!bind(*peer,(struct sockaddr*)&bind_to,sizeof(bind_to)));socklen_t length=sizeof(bind_to);CHECK(!getsockname(*peer,(struct sockaddr*)&bind_to,&length));struct timeval timeout_={1,0};CHECK(!setsockopt(*peer,SOL_SOCKET,SO_RCVTIMEO,&timeout_,sizeof(timeout_)));
 CohNetUdpConfig config={0};config.link=coh_net_default_config();config.receive_budget=8;config.peer=(CohNetEndpoint){{127,0,0,1},ntohs(bind_to.sin_port)};config.local=(CohNetEndpoint){{127,0,0,1},0};CohNetUdp*u=coh_net_udp_create(&config);CHECK(u);CHECK(coh_net_udp_begin(u,42,100)==COH_OK);CHECK(coh_net_udp_service(u,100,(CohCancel){0})==COH_OK);CohNetPacket sent=peer_receive(*peer,1);
 CohNetPacket p=peer_command(100,2,1);p.ack_count=1;p.acks[0]=sent.id;peer_send(*peer,u,&p,0);CHECK(coh_net_udp_service(u,101,(CohCancel){0})==COH_OK);sent=peer_receive(*peer,0);p=peer_command(101,4,0);p.ack_count=1;p.acks[0]=sent.id;peer_send(*peer,u,&p,0);CHECK(coh_net_udp_service(u,102,(CohCancel){0})==COH_OK);(void)peer_receive(*peer,0);CHECK(coh_net_state(u->link)==COH_NET_CONNECTED);return u;
}
static CohStatus tick(CohRequestTxWitness*w,CohInitialCapture*owner,Control*c,Action action,uint64_t now){c->action=action;return coh_request_tx_service(w,owner,now,(CohCancel){0},observer,c,sizeof(*c));}
static CohRequestTxDiagnostics diagnostic_snapshot(CohRequestTxWitness*w){CohRequestTxDiagnostics d;memset(&d,0,sizeof(d));coh_request_tx_diagnostics(w,&d);CHECK(d.diagnostic_only&&!d.server_receipt_proved&&!d.source_generation_admitted&&!d.complete_initial_character&&!d.actor_publication&&!d.ack_permitted&&!d.world_authority);return d;}
static void dispose(CohRequestTxWitness*w,CohInitialCapture*owner,Control*c,int peer){closing=c;coh_request_tx_close(w,owner);coh_request_tx_retire(w);CohRequestTxDiagnostics d=diagnostic_snapshot(w);CHECK(d.witness_retired);coh_request_tx_destroy(w);coh_net_udp_destroy(c->u);close(peer);closing=NULL;}
static void test_specific(void){
 int peer;Control c={0};c.u=connected(&peer);c.other=1;int key=0;CohInitialCapture*owner=(CohInitialCapture*)&key;CohRequestTxWitness*w=coh_request_tx_create(owner,100);CHECK(w);CHECK(tick(w,owner,&c,QUEUE,103)==COH_OK);CohRequestTxDiagnostics d=diagnostic_snapshot(w);CHECK(d.queue_attempted&&d.queue_succeeded&&!d.first_send_accepted&&!d.first_send_attempts&&!d.peer_transport_ack_observed);
 c.status=COH_NOT_FOUND;CHECK(tick(w,owner,&c,SELECTIVE,104)==COH_NOT_FOUND);d=diagnostic_snapshot(w);CHECK(d.first_send_attempts==1&&d.deferred_send_callbacks==1&&!d.first_send_accepted&&c.request_id&&c.other_id&&c.request_id!=c.other_id);
 /* A decoded ACK for this allocated but UNSENT request must not retire it. */
 CohNetPacket p=peer_command(200,0,0);p.ack_count=1;p.acks[0]=c.request_id;peer_send(peer,c.u,&p,0);CHECK(tick(w,owner,&c,PUMP,105)==COH_OK);uint32_t wire_id=0;CHECK(drain(peer,&wire_id)==1&&wire_id==c.request_id);d=diagnostic_snapshot(w);CHECK(d.first_send_accepted&&d.first_send_attempts==2&&!d.peer_transport_ack_observed);
 uint64_t retry=105+coh_net_retry_ms(0,c.u->config.link.ping_ms,0);CHECK(tick(w,owner,&c,PUMP,retry)==COH_OK);CHECK(drain(peer,&wire_id)==1&&wire_id==c.request_id);d=diagnostic_snapshot(w);CHECK(d.retry_send_attempts==1&&d.successful_retries==1);
 p=peer_command(201,0,0);p.ack_count=1;p.acks[0]=c.other_id;peer_send(peer,c.u,&p,0);CHECK(tick(w,owner,&c,PUMP,retry+1)==COH_OK);(void)drain(peer,&wire_id);CHECK(!diagnostic_snapshot(w).peer_transport_ack_observed);
 p=peer_command(202,0,0);p.ack_count=1;p.acks[0]=c.request_id;peer_send(peer,c.u,&p,1);CHECK(tick(w,owner,&c,PUMP,retry+2)==COH_OK);(void)drain(peer,&wire_id);CHECK(!diagnostic_snapshot(w).peer_transport_ack_observed);
 peer_send(peer,c.u,&p,0);CHECK(tick(w,owner,&c,PUMP,retry+3)==COH_OK);(void)drain(peer,&wire_id);d=diagnostic_snapshot(w);CHECK(d.peer_transport_ack_observed&&d.retirement==COH_REQUEST_TX_PEER_ACK&&!d.failed_send_callbacks);
 closing=&c;coh_request_tx_close(w,owner);coh_request_tx_retire(w);d=diagnostic_snapshot(w);CHECK(d.valid&&d.retirement==COH_REQUEST_TX_PEER_ACK);coh_request_tx_destroy(w);coh_net_udp_destroy(c.u);close(peer);closing=NULL;
}
static void test_callback_status(CohStatus status,int actual_io){
 int peer;Control c={0};c.u=connected(&peer);int key=0;CohInitialCapture*owner=(CohInitialCapture*)&key;CohRequestTxWitness*w=coh_request_tx_create(owner,100);CHECK(w);CHECK(tick(w,owner,&c,QUEUE,103)==COH_OK);c.status=status;
 if(actual_io){CHECK(!close(c.u->fd));CHECK(tick(w,owner,&c,DIRECT_UDP_PUMP,104)==COH_IO);real_io_errors++;}else CHECK(tick(w,owner,&c,SELECTIVE,104)==status);
 CohRequestTxDiagnostics d=diagnostic_snapshot(w);if((unsigned)status<=COH_STATE){CHECK(!d.refusal&&d.first_send_attempts==1&&d.failed_send_callbacks==1&&!d.first_send_accepted);if(actual_io)CHECK(d.retirement==COH_REQUEST_TX_CLOSED);}else CHECK(d.refusal==COH_REQUEST_TX_CALLBACK);
 dispose(w,owner,&c,peer);
}
static void test_queue_limit(void){
 int peer;Control c={0};c.u=connected(&peer);uint8_t data[8];uint32_t bits;payload(3,data,&bits);for(unsigned i=0;i<COH_NET_TX_MAX;i++)CHECK(coh_net_udp_queue(c.u,(CohBytes){data,(bits+7)/8},bits,1,0,0,103)==COH_OK);
 int key=0;CohInitialCapture*owner=(CohInitialCapture*)&key;CohRequestTxWitness*w=coh_request_tx_create(owner,100);CHECK(w);CHECK(tick(w,owner,&c,QUEUE,103)==COH_LIMIT);CohRequestTxDiagnostics d=diagnostic_snapshot(w);CHECK(d.queue_attempted&&!d.queue_succeeded&&d.queue_status==COH_LIMIT&&!d.refusal);dispose(w,owner,&c,peer);
}
static void test_retirement(int kind){
 int peer;Control c={0};c.u=connected(&peer);int key=0;CohInitialCapture*owner=(CohInitialCapture*)&key;CohRequestTxWitness*w=coh_request_tx_create(owner,100);CHECK(w);CHECK(tick(w,owner,&c,QUEUE,103)==COH_OK);closing=&c;
 if(kind==0)coh_request_tx_close(w,owner);else if(kind==1)coh_request_tx_cancel(w,owner);else if(kind==2)coh_request_tx_timeout(w,owner);else CHECK(tick(w,owner,&c,PUMP,102+c.u->config.link.idle_timeout_ms)==COH_STATE);
 coh_request_tx_retire(w);CohRequestTxDiagnostics d=diagnostic_snapshot(w);CHECK(d.valid&&!d.first_send_accepted&&!d.peer_transport_ack_observed);CHECK(d.retirement==(kind==1?COH_REQUEST_TX_CANCELLED:kind==3?COH_REQUEST_TX_TIMED_OUT:COH_REQUEST_TX_CLOSED));coh_request_tx_destroy(w);coh_net_udp_destroy(c.u);close(peer);closing=NULL;
}
static void test_refusals(void){
 int key=0,other=0;CohInitialCapture*owner=(CohInitialCapture*)&key;Control c={.status=COH_IO};CohRequestTxWitness*w=coh_request_tx_create(owner,100);CHECK(w);unsigned before=services;CHECK(tick(w,(CohInitialCapture*)&other,&c,NOOP,101)==COH_IO&&services==before+1);coh_request_tx_retire(w);CHECK(diagnostic_snapshot(w).refusal==COH_REQUEST_TX_OWNER);coh_request_tx_destroy(w);
 w=coh_request_tx_create(owner,100);CHECK(w);CHECK(tick(w,owner,&c,NOOP,99)==COH_IO);coh_request_tx_retire(w);CHECK(diagnostic_snapshot(w).refusal==COH_REQUEST_TX_CLOCK);coh_request_tx_destroy(w);CHECK(tick(NULL,owner,&c,NOOP,100)==COH_IO);
 int peer;c.u=connected(&peer);w=coh_request_tx_create(owner,100);CHECK(w);CHECK(tick(w,owner,&c,QUEUE,103)==COH_OK);c.status=COH_NOT_FOUND;CHECK(tick(w,owner,&c,SELECTIVE,104)==COH_NOT_FOUND);CHECK(tick(w,owner,&c,LIMIT_HOOKS,105)==COH_OK);CHECK(diagnostic_snapshot(w).refusal==COH_REQUEST_TX_LIMIT);dispose(w,owner,&c,peer);
}
int main(void){test_specific();test_callback_status(COH_IO,1);test_callback_status(COH_LIMIT,0);test_callback_status(COH_STATE,0);test_callback_status((CohStatus)8,0);test_queue_limit();for(int i=0;i<4;i++)test_retirement(i);test_refusals();printf("{\"passed\":true,\"checks\":%u,\"real_request_datagrams\":%u,\"actual_sendto_io_failures\":%u,\"outer_capture_and_request_bracket_doubled\":true,\"original_server_executed\":false,\"source_generation_admitted\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false}\n",checks,real_request_datagrams,real_io_errors);return 0;}
