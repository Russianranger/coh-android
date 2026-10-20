/* Public NetLink API regression. Send deferral is an explicit callback double;
 * there are no sockets, application requeues, servers, or Android builds here. */
#include "coh_net.h"
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned checks,scenarios;
#define CHECK(x) do {checks++;if(!(x)){fprintf(stderr,"retry-limit:%d: %s\n",__LINE__,#x);exit(1);}} while(0)
typedef struct {
    uint8_t wire[COH_NET_TX_MAX+1][COH_PROTOCOL_FRAME_MAX];
    size_t size[COH_NET_TX_MAX+1];
    unsigned attempts,accepted;
    CohStatus result;
} Capture;
static void reset(Capture *c,CohStatus result) {memset(c,0,sizeof(*c));c->result=result;}
static CohStatus capture(void *context,CohBytes frame) {
    Capture *c=context;CHECK(c->attempts<COH_NET_TX_MAX+1);CHECK(frame.size<=COH_PROTOCOL_FRAME_MAX);
    memcpy(c->wire[c->attempts],frame.data,frame.size);c->size[c->attempts++]=frame.size;
    if(c->result==COH_OK)c->accepted++;
    return c->result;
}
static CohNetPacket decoded(const Capture *c,unsigned at,int connect) {
    CohNetPacket p;CHECK(at<c->attempts);
    CHECK(coh_net_frame_decode(5,NULL,0,connect,(CohBytes){c->wire[at],c->size[at]},&p)==COH_OK);
    return p;
}
static CohNetDiagnostics diagnostics(CohNet *n) {CohNetDiagnostics d;coh_net_diagnostics(n,&d);return d;}
static CohStatus pump(CohNet *n,uint64_t now,Capture *c) {return coh_net_pump(n,now,capture,c,(CohCancel){0});}
static CohNetPacket control(uint32_t id,uint32_t cmd,int has_value,uint32_t value) {
    CohNetPacket p;CohProtocolBits b;memset(&p,0,sizeof(p));p.id=id;
    CHECK(coh_protocol_bits_init(&b,p.payload,sizeof(p.payload),0,1)==COH_OK);
    CHECK(coh_protocol_write_pack(&b,1,0)==COH_OK);
    if(cmd)CHECK(coh_protocol_write_pack(&b,1,cmd)==COH_OK);
    if(has_value)CHECK(coh_protocol_write_pack(&b,1,value)==COH_OK);
    p.payload_bits=(uint32_t)b.bit_length;return p;
}
static CohStatus receive(CohNet *n,CohNetPacket *p,uint64_t now) {
    uint8_t wire[COH_PROTOCOL_FRAME_MAX];size_t size=0;
    CHECK(coh_net_frame_encode(5,NULL,0,p,wire,sizeof(wire),&size)==COH_OK);
    return coh_net_receive(n,(CohBytes){wire,size},now);
}
static void ack(CohNet *n,uint32_t peer_id,uint32_t tx_id,uint64_t now) {
    CohNetPacket p=control(peer_id,0,0,0);p.acks[0]=tx_id;p.ack_count=1;CHECK(receive(n,&p,now)==COH_OK);
}
static CohNet *connected(void) {
    CohNetConfig cfg=coh_net_default_config();CHECK(cfg.version==5&&cfg.max_retries==8);
    CohNet *n=coh_net_create(&cfg);CHECK(n);CHECK(coh_net_begin(n,42,100)==COH_OK);
    Capture c;reset(&c,COH_OK);CHECK(pump(n,100,&c)==COH_OK&&c.accepted==1);
    CohNetPacket sent=decoded(&c,0,1),p=control(100,2,1,0);p.acks[0]=sent.id;p.ack_count=1;
    CHECK(receive(n,&p,101)==COH_OK&&coh_net_state(n)==COH_NET_WAIT_FINAL);
    reset(&c,COH_OK);CHECK(pump(n,101,&c)==COH_OK&&c.accepted==1);sent=decoded(&c,0,0);
    p=control(101,4,0,0);p.acks[0]=sent.id;p.ack_count=1;
    CHECK(receive(n,&p,102)==COH_OK&&coh_net_state(n)==COH_NET_CONNECTED);
    /* Flush the handshake's remaining ACK-only control before each scenario. */
    reset(&c,COH_OK);CHECK(pump(n,102,&c)==COH_OK&&c.accepted==1);
    CHECK(diagnostics(n).tx_pending==0);return n;
}
static void same_payload(const CohNetPacket *a,const CohNetPacket *b) {
    CHECK(a->id==b->id&&a->payload_bits==b->payload_bits);
    CHECK(a->sibling_id==b->sibling_id&&a->sibling_count==b->sibling_count&&a->sibling_part==b->sibling_part);
    CHECK(a->ordered==b->ordered&&a->ordered_id==b->ordered_id&&a->compressed==b->compressed&&a->connect==b->connect);
    CHECK(!memcmp(a->payload,b->payload,(a->payload_bits+7u)/8u));
}
static const uint8_t payload[]={0x57,0xa5,0x7b};
static CohStatus queue(CohNet *n,unsigned limit,uint64_t now) {
    return coh_net_queue_retries(n,(CohBytes){payload,sizeof(payload)},sizeof(payload)*8,1,0,0,limit,now);
}
static void test_one_retry_and_deferral(void) {
    CohNet *n=connected();Capture c;CohNetDiagnostics before=diagnostics(n);
    CHECK(queue(n,1,103)==COH_OK);reset(&c,COH_NOT_FOUND);
    CHECK(pump(n,103,&c)==COH_NOT_FOUND&&c.attempts==1&&!c.accepted);
    CohNetPacket first=decoded(&c,0,0);CohNetDiagnostics d=diagnostics(n);
    CHECK(d.sent==before.sent&&d.retransmits==before.retransmits&&d.tx_pending==1);
    /* An allocated but unaccepted Tx cannot be retired by a guessed peer ACK. */
    ack(n,200,first.id,104);CHECK(diagnostics(n).tx_pending==1);
    reset(&c,COH_OK);CHECK(pump(n,104,&c)==COH_OK&&c.accepted==1);
    CohNetPacket accepted=decoded(&c,0,0);same_payload(&first,&accepted);CHECK(accepted.ack_count==1&&accepted.acks[0]==200);
    uint64_t due=104+coh_net_retry_ms(0,100,0);
    reset(&c,COH_OK);CHECK(pump(n,due-1,&c)==COH_OK&&!c.attempts);
    CohNetPacket peer=control(201,0,0,0);CHECK(receive(n,&peer,due)==COH_OK);
    reset(&c,COH_NOT_FOUND);CHECK(pump(n,due,&c)==COH_NOT_FOUND&&c.attempts==1&&!c.accepted);
    CohNetPacket deferred=decoded(&c,0,0);same_payload(&first,&deferred);CHECK(deferred.ack_count==1&&deferred.acks[0]==201);
    d=diagnostics(n);CHECK(d.sent==before.sent+1&&d.retransmits==before.retransmits&&d.tx_pending==1);
    reset(&c,COH_NOT_FOUND);CHECK(pump(n,due+1,&c)==COH_NOT_FOUND&&c.attempts==1);
    reset(&c,COH_OK);CHECK(pump(n,due+2,&c)==COH_OK&&c.accepted==1);
    CohNetPacket retried=decoded(&c,0,0);same_payload(&first,&retried);CHECK(retried.ack_count==1&&retried.acks[0]==201);
    d=diagnostics(n);CHECK(d.sent==before.sent+2&&d.retransmits==before.retransmits+1&&d.tx_pending==1);
    uint64_t exhausted=due+2+coh_net_retry_ms(1,100,0);
    reset(&c,COH_OK);CHECK(pump(n,exhausted-1,&c)==COH_OK&&!c.attempts);
    CHECK(pump(n,exhausted,&c)==COH_STATE&&!c.attempts);
    d=diagnostics(n);CHECK(coh_net_state(n)==COH_NET_TIMED_OUT&&d.timeouts==1&&!d.tx_pending&&!d.rx_pending&&!d.fragment_groups);
    CHECK(queue(n,1,exhausted)==COH_STATE);coh_net_destroy(n);scenarios++;
}
static void test_ack_suppresses_retry(void) {
    CohNet *n=connected();Capture c;CHECK(queue(n,1,103)==COH_OK);
    reset(&c,COH_OK);CHECK(pump(n,103,&c)==COH_OK&&c.accepted==1);CohNetPacket original=decoded(&c,0,0);
    ack(n,200,original.id+1,104);CHECK(diagnostics(n).tx_pending==1);
    CohNetPacket p=control(201,0,0,0);p.acks[0]=original.id;p.ack_count=1;
    uint8_t wire[COH_PROTOCOL_FRAME_MAX];size_t size=0;
    CHECK(coh_net_frame_encode(5,NULL,0,&p,wire,sizeof(wire),&size)==COH_OK);wire[4]^=0x80;
    CHECK(coh_net_receive(n,(CohBytes){wire,size},105)==COH_INVALID&&diagnostics(n).tx_pending==1);
    ack(n,201,original.id,106);CohNetDiagnostics d=diagnostics(n);CHECK(!d.tx_pending&&d.acknowledged==3);
    reset(&c,COH_OK);CHECK(pump(n,103+coh_net_retry_ms(0,100,0),&c)==COH_OK);
    for(unsigned i=0;i<c.attempts;i++){CohNetPacket emitted=decoded(&c,i,0);CHECK(emitted.id!=original.id);}
    CHECK(diagnostics(n).retransmits==d.retransmits&&coh_net_state(n)==COH_NET_CONNECTED);
    coh_net_destroy(n);scenarios++;
}
static void test_invalid_caps_before_compression(void) {
    CohNet *n=connected(),*reference=connected();uint8_t data[512];Capture a,b;
    memset(data,'q',sizeof(data));data[0]=10;data[1]=data[2]=data[3]=0;
    const unsigned invalid[]={9,256,UINT_MAX};CohNetDiagnostics before=diagnostics(n);
    for(unsigned i=0;i<sizeof(invalid)/sizeof(invalid[0]);i++) {
        CHECK(coh_net_queue_retries(n,(CohBytes){data,sizeof(data)},sizeof(data)*8,1,1,1,invalid[i],103)==COH_INVALID);
        CohNetDiagnostics d=diagnostics(n);CHECK(!d.tx_pending&&d.queue_limits==before.queue_limits&&d.sent==before.sent&&d.codec_bytes==before.codec_bytes);
    }
    for(unsigned i=0;i<2;i++) {
        data[17]=(uint8_t)i;
        CHECK(coh_net_queue_retries(n,(CohBytes){data,sizeof(data)},sizeof(data)*8,1,1,1,1,103)==COH_OK);
        CHECK(coh_net_queue_retries(reference,(CohBytes){data,sizeof(data)},sizeof(data)*8,1,1,1,1,103)==COH_OK);
    }
    reset(&a,COH_OK);reset(&b,COH_OK);CHECK(pump(n,103,&a)==COH_OK&&pump(reference,103,&b)==COH_OK);
    CHECK(a.accepted==2&&b.accepted==2);
    for(unsigned i=0;i<a.attempts;i++){CHECK(a.size[i]==b.size[i]&&!memcmp(a.wire[i],b.wire[i],a.size[i]));CohNetPacket p=decoded(&a,i,0);CHECK(p.ordered&&p.compressed&&p.ordered_id==i+1);}
    coh_net_destroy(n);coh_net_destroy(reference);scenarios++;
}
static void test_older_default_budget(void) {
    CohNet *n=connected();Capture c;
    CHECK(coh_net_queue(n,(CohBytes){payload,sizeof(payload)},sizeof(payload)*8,1,0,0,103)==COH_OK);
    CHECK(queue(n,1,103)==COH_OK);reset(&c,COH_OK);CHECK(pump(n,103,&c)==COH_OK&&c.accepted==2);
    CohNetPacket older=decoded(&c,0,0),capped=decoded(&c,1,0);CHECK(older.id<capped.id);
    ack(n,200,capped.id,104);CHECK(diagnostics(n).tx_pending==1);
    uint64_t now=103;
    for(unsigned i=0;i<8;i++) {
        now+=coh_net_retry_ms(i,100,0);reset(&c,COH_OK);CHECK(pump(n,now,&c)==COH_OK&&c.accepted==1);
        CohNetPacket retried=decoded(&c,0,0);same_payload(&older,&retried);
        CHECK(diagnostics(n).retransmits==i+1&&diagnostics(n).tx_pending==1);
    }
    reset(&c,COH_OK);CHECK(pump(n,now+coh_net_retry_ms(8,100,0),&c)==COH_STATE&&!c.attempts);
    CHECK(!diagnostics(n).tx_pending&&diagnostics(n).timeouts==1);coh_net_destroy(n);scenarios++;
}
static void test_cap_boundaries_and_fragments(void) {
    CohNet *n=connected();Capture c;CHECK(queue(n,0,103)==COH_OK);
    reset(&c,COH_OK);CHECK(pump(n,103,&c)==COH_OK&&c.accepted==1);
    reset(&c,COH_OK);CHECK(pump(n,103+coh_net_retry_ms(0,100,0),&c)==COH_STATE&&!c.attempts);
    CHECK(!diagnostics(n).retransmits&&!diagnostics(n).tx_pending);coh_net_destroy(n);scenarios++;
    n=connected();CHECK(queue(n,8,103)==COH_OK);coh_net_close(n);CHECK(!diagnostics(n).tx_pending);coh_net_destroy(n);scenarios++;
    n=connected();uint8_t data[COH_PROTOCOL_PAYLOAD_MAX*2+1];memset(data,0xa5,sizeof(data));data[0]=0x57;
    CHECK(coh_net_queue_retries(n,(CohBytes){data,sizeof(data)},sizeof(data)*8,1,0,0,1,103)==COH_OK);
    reset(&c,COH_OK);CHECK(pump(n,103,&c)==COH_OK&&c.accepted==3);CohNetPacket original[3];
    for(unsigned i=0;i<3;i++){original[i]=decoded(&c,i,0);CHECK(original[i].sibling_count==3&&original[i].sibling_part==i);}
    uint64_t due=103+coh_net_retry_ms(0,100,0);reset(&c,COH_OK);CHECK(pump(n,due,&c)==COH_OK&&c.accepted==3);
    for(unsigned i=0;i<3;i++){CohNetPacket p=decoded(&c,i,0);same_payload(&original[i],&p);}
    reset(&c,COH_OK);CHECK(pump(n,due+coh_net_retry_ms(1,100,0),&c)==COH_STATE&&!c.attempts);
    CHECK(diagnostics(n).retransmits==3&&!diagnostics(n).tx_pending);coh_net_destroy(n);scenarios++;
}
static void test_capacity_reuse_and_cleanup(void) {
    CohNet *n=connected();Capture c;
    for(unsigned i=0;i<COH_NET_TX_MAX;i++)CHECK(queue(n,1,103)==COH_OK);
    CHECK(queue(n,1,103)==COH_LIMIT&&diagnostics(n).queue_limits==1&&diagnostics(n).tx_pending==COH_NET_TX_MAX);
    CHECK(queue(n,UINT_MAX,103)==COH_INVALID&&diagnostics(n).queue_limits==1);
    reset(&c,COH_OK);CHECK(pump(n,103,&c)==COH_OK&&c.accepted==COH_NET_TX_MAX);
    CohNetPacket first=decoded(&c,0,0);ack(n,200,first.id,104);
    CHECK(coh_net_queue(n,(CohBytes){payload,sizeof(payload)},sizeof(payload)*8,1,0,0,104)==COH_OK);
    CohNetPacket p=control(201,0,0,0);p.ack_count=COH_NET_TX_MAX-1;
    for(unsigned i=1;i<COH_NET_TX_MAX;i++){CohNetPacket old=decoded(&c,i,0);p.acks[i-1]=old.id;}
    CHECK(receive(n,&p,105)==COH_OK&&diagnostics(n).tx_pending==1);
    reset(&c,COH_OK);CHECK(pump(n,105,&c)==COH_OK&&c.accepted==1);CohNetPacket reused=decoded(&c,0,0);
    CHECK(reused.id>first.id+COH_NET_TX_MAX-1);uint64_t now=105;
    for(unsigned i=0;i<2;i++){now+=coh_net_retry_ms(i,100,0);reset(&c,COH_OK);CHECK(pump(n,now,&c)==COH_OK&&c.accepted==1);CohNetPacket retry=decoded(&c,0,0);same_payload(&reused,&retry);}
    /* Reusing a previously capped slot must restore the legacy queue budget. */
    CHECK(diagnostics(n).retransmits==2);coh_net_cancel(n);
    CHECK(coh_net_state(n)==COH_NET_CANCELLED&&!diagnostics(n).tx_pending&&!diagnostics(n).rx_pending&&!diagnostics(n).fragment_groups);
    reset(&c,COH_OK);CHECK(pump(n,now+1,&c)==COH_CANCELLED&&!c.attempts&&queue(n,1,now+1)==COH_STATE);
    coh_net_destroy(n);scenarios++;
    n=connected();CHECK(queue(n,1,103)==COH_OK);coh_net_close(n);
    CHECK(coh_net_state(n)==COH_NET_CLOSED&&!diagnostics(n).tx_pending);reset(&c,COH_OK);
    CHECK(pump(n,104,&c)==COH_OK&&!c.attempts&&queue(n,1,104)==COH_STATE);coh_net_destroy(n);scenarios++;
}
int main(void) {
    test_one_retry_and_deferral();test_ack_suppresses_retry();test_invalid_caps_before_compression();
    test_older_default_budget();test_cap_boundaries_and_fragments();test_capacity_reuse_and_cleanup();
    printf("{\"passed\":true,\"checks\":%u,\"scenarios\":%u,\"public_net_api\":true,\"send_deferral_double\":true,\"socket_or_android_execution\":false}\n",checks,scenarios);
    return 0;
}
