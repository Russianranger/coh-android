/* REQUEST_TX_HOOK_BEGIN */#include "coh_request_tx_internal.h"
/* REQUEST_TX_HOOK_END */#include "../network/coh_net.h"
#include "../network/coh_net_zip_internal.h"
#include <stdlib.h>
#include <string.h>

typedef struct { CohNetPacket packet;uint64_t last_ms;unsigned retries;uint8_t used,sent,reliable; } Tx;
typedef struct { CohNetMessage message;uint8_t used; } Rx;
typedef struct {
    CohNetPacket parts[COH_NET_FRAGMENT_MAX];uint64_t start_ms;
    uint32_t sibling_id,count,mask;uint8_t used;
} Group;
struct CohNet {
    CohNetConfig config;CohNetState state;CohNetZip *zip;
    CohNetKeyExchange key_exchange;void *key_context;CohBlowfish key;
    uint8_t decrypt_on,encrypt_on,require_encryption;
    Tx tx[COH_NET_TX_MAX];Rx rx[COH_NET_RX_MAX];Group groups[COH_NET_GROUP_MAX];
    uint32_t seen[COH_NET_WINDOW],acks[COH_NET_ACK_MAX],ack_count;
    uint32_t next_id,next_sibling,next_ordered,last_ordered;
    uint64_t start_ms,last_rx_ms,last_clock_ms;
    size_t decoded_budget,owned_bytes;uint8_t *owned;uint64_t owned_generation;
    CohNetDiagnostics diagnostics;
};
static void erase(void *data,size_t size) {volatile uint8_t *p=data;while(size--)*p++=0;}
static void forget_key(CohNet *n) {erase(&n->key,sizeof(n->key));n->decrypt_on=n->encrypt_on=0;}
static void occupancy(CohNet *n) {
    uint32_t tx=0,rx=0,g=0;size_t bytes=0;
    for(unsigned i=0;i<COH_NET_TX_MAX;i++)if(n->tx[i].used){tx++;bytes+=(n->tx[i].packet.payload_bits+7)/8;}
    for(unsigned i=0;i<COH_NET_RX_MAX;i++)if(n->rx[i].used){rx++;bytes+=(n->rx[i].message.payload_bits+7)/8;}
    for(unsigned i=0;i<COH_NET_GROUP_MAX;i++)if(n->groups[i].used){g++;
        for(unsigned j=0;j<n->groups[i].count;j++)if(n->groups[i].mask&(1u<<j))bytes+=(n->groups[i].parts[j].payload_bits+7)/8;
    }
    n->diagnostics.tx_pending=tx;n->diagnostics.rx_pending=rx;n->diagnostics.fragment_groups=g;
    n->diagnostics.storage_bytes=sizeof(*n);n->diagnostics.codec_bytes=coh_net_zip_memory(n->zip);
    n->diagnostics.owned_retained_bytes=n->owned_bytes;
    if(n->owned_bytes>n->diagnostics.owned_high_water_bytes)n->diagnostics.owned_high_water_bytes=n->owned_bytes;
    bytes+=n->owned_bytes;
    if(bytes>n->diagnostics.high_water_retained_bytes)n->diagnostics.high_water_retained_bytes=bytes;
}
CohNetConfig coh_net_default_config(void) {
    CohNetConfig c={5,100,8,10000,30000,10000};return c;
}
CohNet *coh_net_create(const CohNetConfig *config) {
    CohNetConfig c=config?*config:coh_net_default_config();
    if(c.version>5||!c.max_retries||c.max_retries>64||!c.connect_timeout_ms||
       !c.idle_timeout_ms||!c.fragment_timeout_ms)return NULL;
    CohNet *n=calloc(1,sizeof(*n));if(!n)return NULL;
    n->config=c;n->decoded_budget=COH_NET_MESSAGE_MAX;n->zip=coh_net_zip_create();
    if(!n->zip){free(n);return NULL;}occupancy(n);return n;
}
static void free_owned(CohNet *n) {
    if(n->owned){erase(n->owned,n->owned_bytes);free(n->owned);n->owned=NULL;n->owned_bytes=0;}
}
void coh_net_destroy(CohNet *n) { if(n){/* REQUEST_TX_HOOK_BEGIN */coh_request_tx_hook_retire(n,COH_REQUEST_TX_DESTROYED);/* REQUEST_TX_HOOK_END */free_owned(n);coh_net_zip_destroy(n->zip);erase(n,sizeof(*n));free(n);} }
CohStatus coh_net_set_decoded_budget(CohNet *n,size_t bytes) {
    if(!n||n->state!=COH_NET_IDLE)return COH_STATE;
    if(bytes<COH_NET_MESSAGE_MAX||bytes>COH_NET_DECODED_MAX)return COH_INVALID;
    n->decoded_budget=bytes;return COH_OK;
}
CohNetState coh_net_state(const CohNet *n) { return n?n->state:COH_NET_FAILED; }
CohStatus coh_net_set_key_exchange(CohNet *n,CohNetKeyExchange exchange,void *context,int required) {
    if(!n||n->state!=COH_NET_IDLE)return COH_STATE;
    if(required!=0&&required!=1)return COH_INVALID;
    n->key_exchange=exchange;n->key_context=context;n->require_encryption=(uint8_t)required;return COH_OK;
}
static unsigned tx_free(const CohNet *n) { unsigned c=0;for(unsigned i=0;i<COH_NET_TX_MAX;i++)c+=!n->tx[i].used;return c; }
static CohStatus queue_raw(CohNet *n,CohBytes data,uint32_t bits,int reliable,int ordered,int compressed,int connect,uint64_t now) {
    if(!data.data||!bits||bits>COH_NET_MESSAGE_MAX*8||data.size<((size_t)bits+7)/8||
       (reliable!=0&&reliable!=1)||(ordered!=0&&ordered!=1)||(compressed!=0&&compressed!=1)||
       (ordered&&(!reliable||n->config.version<5))||(compressed&&(!n->config.version||(bits&7))))return COH_INVALID;
    size_t size=((size_t)bits+7)/8;
    /* Conservatively reserve for the uncompressed maximum before advancing a
     * streaming zlib dictionary. Compression can only reduce this reservation. */
    unsigned count=(unsigned)((size+COH_PROTOCOL_PAYLOAD_MAX-1)/COH_PROTOCOL_PAYLOAD_MAX);
    unsigned reservation=compressed?(unsigned)((size+64+COH_PROTOCOL_PAYLOAD_MAX-1)/COH_PROTOCOL_PAYLOAD_MAX):count;
    if(reservation>COH_NET_FRAGMENT_MAX||tx_free(n)<reservation||
       n->next_id>UINT32_MAX-reservation||n->next_ordered==UINT32_MAX||n->next_sibling==UINT32_MAX){n->diagnostics.queue_limits++;return COH_LIMIT;}
    uint8_t packed[COH_NET_MESSAGE_MAX];const uint8_t *payload=data.data;
    if(compressed) {
        CohStatus s=coh_net_zip_encode(n->zip,ordered,(CohBytes){data.data,size},packed,sizeof(packed),&size);
        if(s!=COH_OK)return s;
        payload=packed;bits=(uint32_t)size*8;
        count=(unsigned)((size+COH_PROTOCOL_PAYLOAD_MAX-1)/COH_PROTOCOL_PAYLOAD_MAX);
    }
    uint32_t sibling=count>1?++n->next_sibling:0,order=ordered?++n->next_ordered:0;
    for(unsigned part=0;part<count;part++) {
        unsigned slot=0;while(n->tx[slot].used)slot++;
        Tx *t=&n->tx[slot];memset(t,0,sizeof(*t));t->used=1;t->reliable=(uint8_t)reliable;t->last_ms=now;
        CohNetPacket *p=&t->packet;p->id=++n->next_id;p->sibling_id=sibling;
        p->sibling_count=count>1?count:0;p->sibling_part=count>1?part:0;
        p->ordered=(uint8_t)ordered;p->ordered_id=order;p->compressed=(uint8_t)compressed;p->connect=(uint8_t)connect;
        p->payload_bits=bits-part*COH_PROTOCOL_PAYLOAD_MAX*8;
        if(p->payload_bits>COH_PROTOCOL_PAYLOAD_MAX*8)p->payload_bits=COH_PROTOCOL_PAYLOAD_MAX*8;
        memcpy(p->payload,payload+part*COH_PROTOCOL_PAYLOAD_MAX,(p->payload_bits+7)/8);
        /* REQUEST_TX_HOOK_BEGIN */coh_request_tx_hook_queue(n,p->id,count,reliable,ordered,compressed,connect,t->sent,now);/* REQUEST_TX_HOOK_END */
    }
    occupancy(n);return COH_OK;
}
static CohStatus control(CohNet *n,uint32_t cmd,int has_value,uint32_t value,uint64_t now) {
    uint8_t data[32]={0};CohProtocolBits b;(void)coh_protocol_bits_init(&b,data,sizeof(data),0,1);
    if(n->config.version>=4&&cmd!=1) {
        (void)coh_protocol_write_pack(&b,1,0);
        if(cmd)(void)coh_protocol_write_pack(&b,1,cmd);
    }else(void)coh_protocol_write_pack(&b,1,cmd);
    if(has_value)(void)coh_protocol_write_pack(&b,1,value);
    return queue_raw(n,(CohBytes){data,(b.bit_length+7)/8},(uint32_t)b.bit_length,cmd!=0&&cmd!=6,0,0,cmd==1,now);
}
CohStatus coh_net_begin(CohNet *n,uint32_t connect_id,uint64_t now) {
    if(!n||n->state!=COH_NET_IDLE)return COH_STATE;
    uint8_t data[40]={0};CohProtocolBits b;(void)coh_protocol_bits_init(&b,data,sizeof(data),0,1);
    (void)coh_protocol_write_pack(&b,1,1);(void)coh_protocol_write_pack(&b,1,connect_id);
    (void)coh_protocol_write_pack(&b,1,n->config.version);
    CohStatus s=queue_raw(n,(CohBytes){data,(b.bit_length+7)/8},(uint32_t)b.bit_length,1,0,0,1,now);
    if(s==COH_OK){n->state=COH_NET_CONNECTING;n->start_ms=n->last_rx_ms=n->last_clock_ms=now;}return s;
}
CohStatus coh_net_queue(CohNet *n,CohBytes data,uint32_t bits,int reliable,int ordered,int compressed,uint64_t now) {
    if(!n||n->state!=COH_NET_CONNECTED)return COH_STATE;
    if(now<n->last_clock_ms)return COH_INVALID;
    return queue_raw(n,data,bits,reliable,ordered,compressed,0,now);
}
static void clear_queues(CohNet *n) {
/* REQUEST_TX_HOOK_BEGIN */coh_request_tx_hook_retire(n,COH_REQUEST_TX_QUEUES_CLEARED);/* REQUEST_TX_HOOK_END */    free_owned(n);
    memset(n->tx,0,sizeof(n->tx));memset(n->rx,0,sizeof(n->rx));memset(n->groups,0,sizeof(n->groups));n->ack_count=0;occupancy(n);
}
CohStatus coh_net_disconnect(CohNet *n,uint64_t now) {
    if(!n||n->state!=COH_NET_CONNECTED)return COH_STATE;
    if(now<n->last_clock_ms)return COH_INVALID;
    /* REQUEST_TX_HOOK_BEGIN */coh_request_tx_hook_retire(n,COH_REQUEST_TX_DISCONNECTED);/* REQUEST_TX_HOOK_END */clear_queues(n);
    CohStatus s=control(n,5,0,0,now);
    if(s==COH_OK){n->state=COH_NET_DISCONNECTING;n->start_ms=n->last_clock_ms=now;}
    return s;
}
void coh_net_cancel(CohNet *n) { if(n){/* REQUEST_TX_HOOK_BEGIN */coh_request_tx_hook_retire(n,COH_REQUEST_TX_CANCELLED);/* REQUEST_TX_HOOK_END */clear_queues(n);forget_key(n);n->state=COH_NET_CANCELLED;} }
void coh_net_close(CohNet *n) { if(n){/* REQUEST_TX_HOOK_BEGIN */coh_request_tx_hook_retire(n,COH_REQUEST_TX_CLOSED);/* REQUEST_TX_HOOK_END */clear_queues(n);forget_key(n);n->state=COH_NET_CLOSED;} }
static CohStatus timeout(CohNet *n) { /* REQUEST_TX_HOOK_BEGIN */coh_request_tx_hook_retire(n,COH_REQUEST_TX_TIMED_OUT);/* REQUEST_TX_HOOK_END */clear_queues(n);forget_key(n);n->state=COH_NET_TIMED_OUT;n->diagnostics.timeouts++;return COH_STATE; }
static int cmp(const void *a,const void *b) { uint32_t x=*(const uint32_t*)a,y=*(const uint32_t*)b;return (x>y)-(x<y); }
CohStatus coh_net_pump(CohNet *n,uint64_t now,CohNetSend send,void *context,CohCancel cancel) {
    if(!n||!send)return COH_INVALID;
    if(now<n->last_clock_ms)return COH_INVALID;
    n->last_clock_ms=now;
    if(cancel.poll&&cancel.poll(cancel.context)){coh_net_cancel(n);return COH_CANCELLED;}
    if(n->state==COH_NET_CANCELLED)return COH_CANCELLED;
    if(n->state==COH_NET_TIMED_OUT||n->state==COH_NET_FAILED||n->state==COH_NET_ENCRYPTION_REQUIRED)return COH_STATE;
    if((n->state==COH_NET_CONNECTING||n->state==COH_NET_WAIT_FINAL||n->state==COH_NET_DISCONNECTING)&&now-n->start_ms>=n->config.connect_timeout_ms)return timeout(n);
    if(n->state==COH_NET_CONNECTED&&now-n->last_rx_ms>=n->config.idle_timeout_ms)return timeout(n);
    for(unsigned i=0;i<COH_NET_GROUP_MAX;i++)if(n->groups[i].used&&now-n->groups[i].start_ms>=n->config.fragment_timeout_ms) {
        /* Already-ACKed reliable fragments cannot be silently evicted: the
         * source cannot retransmit them. Require a fresh link after expiry. */
        n->diagnostics.fragment_expirations++;return timeout(n);
    }
    int ready=0;
    for(unsigned i=0;i<COH_NET_TX_MAX;i++)if(n->tx[i].used&&(!n->tx[i].sent||
        now-n->tx[i].last_ms>=coh_net_retry_ms(n->tx[i].retries,n->config.ping_ms,0)))ready=1;
    if(n->ack_count&&!ready&&tx_free(n)) {
        CohStatus s=control(n,0,0,0,now);if(s!=COH_OK)return s;
    }
    /* Stable packet-id order, even when array slots are reused. */
    uint32_t previous=0;
    for(unsigned pass=0;pass<COH_NET_TX_MAX;pass++) {
        Tx *t=NULL;for(unsigned i=0;i<COH_NET_TX_MAX;i++)if(n->tx[i].used&&n->tx[i].packet.id>previous&&(!t||n->tx[i].packet.id<t->packet.id))t=&n->tx[i];
        if(!t)break;
        previous=t->packet.id;
        if(t->sent&&now-t->last_ms<coh_net_retry_ms(t->retries,n->config.ping_ms,0))continue;
        if(t->sent&&t->retries>=n->config.max_retries)return timeout(n);
        if(cancel.poll&&cancel.poll(cancel.context)){coh_net_cancel(n);return COH_CANCELLED;}
        CohNetPacket p=t->packet;
        /* Keep the original non-debug 28-byte header allowance. pktWrap
         * reduces ACK count until the header fits; four worst-case deltas
         * plus fragmentation can exceed that allowance, so retry downward. */
        qsort(n->acks,n->ack_count,sizeof(n->acks[0]),cmp);
        p.ack_count=n->ack_count<8?n->ack_count:8;
        memcpy(p.acks,n->acks,p.ack_count*sizeof(uint32_t));
        uint8_t frame[COH_PROTOCOL_FRAME_MAX];size_t size=0;CohStatus s;
        for(;;) {
            s=coh_net_frame_encode(n->config.version,n->encrypt_on?&n->key:NULL,n->encrypt_on,&p,frame,sizeof(frame),&size);
            uint32_t total=s==COH_OK?((uint32_t)frame[0]|(uint32_t)frame[1]<<8|(uint32_t)frame[2]<<16|(uint32_t)frame[3]<<24):0;
            if(s==COH_OK&&(total-p.payload_bits<=28*8||!p.ack_count))break;
            if(!p.ack_count)return s;
            p.ack_count--;
        }
        /* REQUEST_TX_HOOK_BEGIN */uint32_t request_tx_id=t->packet.id;int request_tx_sent=t->sent;coh_request_tx_hook_send_begin(n,request_tx_id,request_tx_sent,now);/* REQUEST_TX_HOOK_END */s=send(context,(CohBytes){frame,size});/* REQUEST_TX_HOOK_BEGIN */coh_request_tx_hook_send(n,request_tx_id,request_tx_sent,s,now);/* REQUEST_TX_HOOK_END */if(s!=COH_OK)return s;
        if(p.ack_count){memmove(n->acks,n->acks+p.ack_count,(n->ack_count-p.ack_count)*sizeof(uint32_t));n->ack_count-=p.ack_count;}
        if(t->sent){n->diagnostics.retransmits++;t->retries++;}
        n->diagnostics.sent++;t->last_ms=now;t->sent=1;if(!t->reliable)t->used=0;
    }
    occupancy(n);return COH_OK;
}
static CohStatus process_control(CohNet *n,const CohNetMessage *m,uint64_t now,int *handled) {
    *handled=0;uint8_t decoded[COH_NET_MESSAGE_MAX];const uint8_t *data=m->payload;size_t bytes=(m->payload_bits+7)/8;
    if(m->compressed) {
        if(m->payload_bits&7)return COH_INVALID;
        CohStatus s=coh_net_zip_decode(n->zip,m->ordered,(CohBytes){data,bytes},decoded,sizeof(decoded),&bytes);
        if(s!=COH_OK)return s;
        data=decoded;
    }
    /* Peek only the immutable command before decompression in the caller;
     * game messages are never passed here, preserving dictionary order. */
    CohProtocolBits b;
    if(bytes>COH_PROTOCOL_FRAME_MAX)return COH_INVALID;
    (void)coh_protocol_bits_init(&b,(uint8_t*)data,bytes,m->compressed?bytes*8:m->payload_bits,0);
    uint32_t cmd;if((m->compressed?coh_protocol_read(&b,32,&cmd):coh_protocol_read_pack(&b,1,&cmd)))return COH_INVALID;
    if(n->config.version>=4&&cmd==0) {
        if(b.cursor==b.bit_length)cmd=0;
        else if(m->compressed?coh_protocol_read(&b,32,&cmd):coh_protocol_read_pack(&b,1,&cmd))return COH_INVALID;
    }
    *handled=1;
    if(cmd==0)return COH_OK;
    if(cmd==2) {
        if(n->state!=COH_NET_CONNECTING&&n->state!=COH_NET_WAIT_FINAL)return COH_STATE;
        uint32_t encrypt;
        if(m->compressed?coh_protocol_read(&b,32,&encrypt):coh_protocol_read_pack(&b,1,&encrypt))return COH_INVALID;
        if(encrypt>1)return COH_INVALID;
        if(encrypt) {
            size_t at=(b.cursor+7)&~(size_t)7;
            if(at+512>b.bit_length)return COH_INVALID;
            if(!n->key_exchange){clear_queues(n);forget_key(n);n->state=COH_NET_ENCRYPTION_REQUIRED;n->diagnostics.unsupported++;return COH_UNSUPPORTED;}
            /* Once decrypt_on is set, source retransmissions with the same
             * packet ID are deduplicated; a changed public key cannot replace
             * a live negotiation. No clear retry or crypto downgrade path. */
            if(n->decrypt_on)return COH_STATE;
            uint8_t own[64]={0};CohBlowfish key;memset(&key,0,sizeof(key));
            CohStatus s=n->key_exchange(n->key_context,data+at/8,own,&key);
            if(s!=COH_OK){erase(&key,sizeof(key));clear_queues(n);forget_key(n);n->state=COH_NET_FAILED;return s;}
            uint8_t ack[80]={0};CohProtocolBits reply;(void)coh_protocol_bits_init(&reply,ack,sizeof(ack),0,1);
            if(n->config.version>=4)(void)coh_protocol_write_pack(&reply,1,0);
            (void)coh_protocol_write_pack(&reply,1,3);(void)coh_protocol_write_pack(&reply,1,1);
            size_t key_at=(reply.cursor+7)&~(size_t)7;memcpy(ack+key_at/8,own,sizeof(own));
            uint32_t bits=(uint32_t)(key_at+512);
            s=queue_raw(n,(CohBytes){ack,(bits+7)/8},bits,1,0,0,0,now);
            if(s==COH_OK){n->key=key;n->decrypt_on=1;n->state=COH_NET_WAIT_FINAL;}
            erase(&key,sizeof(key));return s;
        }
        if(n->require_encryption||n->decrypt_on){clear_queues(n);forget_key(n);n->state=COH_NET_ENCRYPTION_REQUIRED;n->diagnostics.unsupported++;return COH_UNSUPPORTED;}
        CohStatus s=control(n,3,1,0,now);if(s==COH_OK)n->state=COH_NET_WAIT_FINAL;return s;
    }
    if(cmd==4) { if(n->state!=COH_NET_WAIT_FINAL)return COH_STATE;n->encrypt_on=n->decrypt_on;n->state=COH_NET_CONNECTED;return COH_OK; }
    if(cmd==5) {
        /* Original netAckDisconnect flushes its reply then discards the link.
         * Preserve only one reply for the caller's next nonblocking send;
         * old gameplay and reliable retry state must never survive closure. */
        clear_queues(n);
        CohStatus s=control(n,6,0,0,now);if(s==COH_OK)n->state=COH_NET_CLOSED;return s;
    }
    if(cmd==6) { coh_net_close(n);return COH_OK; }
    n->diagnostics.unsupported++;return COH_UNSUPPORTED;
}
static int is_control(CohNet *n,const CohNetMessage *m) {
    uint32_t cmd;
    if(m->compressed) { if(m->payload_bits<32)return -1;
        cmd=(uint32_t)m->payload[0]|(uint32_t)m->payload[1]<<8|(uint32_t)m->payload[2]<<16|(uint32_t)m->payload[3]<<24;
    } else {
        size_t bytes=(m->payload_bits+7)/8;if(bytes>COH_PROTOCOL_FRAME_MAX)bytes=COH_PROTOCOL_FRAME_MAX;
        size_t logical=m->payload_bits<bytes*8?m->payload_bits:bytes*8;
        CohProtocolBits b;(void)coh_protocol_bits_init(&b,(uint8_t*)m->payload,bytes,logical,0);
        if(coh_protocol_read_pack(&b,1,&cmd))return -1;
    }
    return n->config.version>=4?(cmd==0||cmd==1):cmd<7;
}
static CohStatus store_message(CohNet *n,const CohNetMessage *m,uint64_t now) {
    int ctl=is_control(n,m);if(ctl<0)return COH_INVALID;
    if(ctl) {
        /* Source-generated control messages use unordered delivery. Do not
         * permit an unsupported control to consume the gameplay dictionary. */
        if(m->ordered){n->diagnostics.unsupported++;return COH_UNSUPPORTED;}
        int handled;return process_control(n,m,now,&handled);
    }
    if(n->state!=COH_NET_CONNECTED)return COH_STATE;
    if(m->ordered&&m->ordered_id<=n->last_ordered)return COH_INVALID;
    for(unsigned i=0;i<COH_NET_RX_MAX;i++)if(n->rx[i].used&&m->ordered&&n->rx[i].message.ordered&&n->rx[i].message.ordered_id==m->ordered_id)return COH_INVALID;
    for(unsigned i=0;i<COH_NET_RX_MAX;i++)if(!n->rx[i].used){n->rx[i].message=*m;n->rx[i].used=1;return COH_OK;}
    n->diagnostics.queue_limits++;return COH_LIMIT;
}
static CohStatus retain(CohNet *n,const CohNetPacket *p,uint64_t now) {
    CohNetMessage m;memset(&m,0,sizeof(m));m.id=p->id;m.ordered_id=p->ordered_id;
    m.compressed=p->compressed;m.ordered=p->ordered;
    if(!p->sibling_count){m.payload_bits=p->payload_bits;memcpy(m.payload,p->payload,(p->payload_bits+7)/8);return store_message(n,&m,now);}
    if(p->sibling_part+1<p->sibling_count&&(p->payload_bits&7))return COH_INVALID;
    Group *g=NULL,*empty=NULL;
    for(unsigned i=0;i<COH_NET_GROUP_MAX;i++) {
        if(n->groups[i].used&&n->groups[i].sibling_id==p->sibling_id)g=&n->groups[i];
        if(!n->groups[i].used)empty=&n->groups[i];
    }
    if(!g) { if(!empty){n->diagnostics.queue_limits++;return COH_LIMIT;}g=empty;
        memset(g,0,sizeof(*g));g->used=1;g->sibling_id=p->sibling_id;g->count=p->sibling_count;g->start_ms=now;
    }
    if(g->count!=p->sibling_count||(g->mask&(1u<<p->sibling_part)))return COH_INVALID;
    for(unsigned i=0;i<g->count;i++)if(g->mask&(1u<<i)) {
        if(g->parts[i].ordered!=p->ordered||g->parts[i].compressed!=p->compressed||
           (g->parts[i].ordered_id&&p->ordered_id&&g->parts[i].ordered_id!=p->ordered_id))return COH_INVALID;
    }
    uint32_t retained_bits=p->payload_bits;
    for(unsigned i=0;i<g->count;i++)if(g->mask&(1u<<i))retained_bits+=g->parts[i].payload_bits;
    if(retained_bits>COH_NET_MESSAGE_MAX*8) {
        /* Earlier retained pieces were ACKed. Discarding them and remaining
         * connected would make a reliable message permanently unrecoverable. */
        n->diagnostics.queue_limits++;clear_queues(n);forget_key(n);n->state=COH_NET_FAILED;return COH_LIMIT;
    }
    g->parts[p->sibling_part]=*p;g->mask|=1u<<p->sibling_part;
    if(g->mask!=((1u<<g->count)-1))return COH_OK;
    /* Match original mergeSibs: delivery metadata belongs to part zero,
     * independent of arrival order and later fragments' zero ordered IDs. */
    size_t offset=0;m.id=g->parts[0].id;m.ordered_id=g->parts[0].ordered_id;
    for(unsigned i=0;i<g->count;i++) {
        size_t size=(g->parts[i].payload_bits+7)/8;
        if(offset+size>sizeof(m.payload)){n->diagnostics.queue_limits++;clear_queues(n);forget_key(n);n->state=COH_NET_FAILED;return COH_LIMIT;}
        memcpy(m.payload+offset,g->parts[i].payload,size);offset+=size;m.payload_bits+=g->parts[i].payload_bits;
    }
    CohStatus s=store_message(n,&m,now);
    if(s==COH_OK)g->used=0;
    else { /* Permit retransmitting the final fragment after RX capacity recovers. */
        g->mask&=~(1u<<p->sibling_part);memset(&g->parts[p->sibling_part],0,sizeof(g->parts[0]));
    }
    return s;
}
CohStatus coh_net_receive(CohNet *n,CohBytes frame,uint64_t now) {
    if(!n)return COH_INVALID;
    if(now<n->last_clock_ms)return COH_INVALID;
    if(n->state!=COH_NET_CONNECTING&&n->state!=COH_NET_WAIT_FINAL&&n->state!=COH_NET_CONNECTED&&n->state!=COH_NET_DISCONNECTING)return COH_STATE;
    CohNetPacket p;CohStatus s=coh_net_frame_decode(n->config.version,n->decrypt_on?&n->key:NULL,n->decrypt_on,0,frame,&p);
    if(s!=COH_OK){n->diagnostics.malformed++;return s;}
    for(uint32_t i=0;i<p.ack_count;i++)for(unsigned j=0;j<COH_NET_TX_MAX;j++)if(n->tx[j].used&&n->tx[j].sent&&n->tx[j].packet.id==p.acks[i]){
        /* REQUEST_TX_HOOK_BEGIN */coh_request_tx_hook_ack(n,n->tx[j].packet.id,now);/* REQUEST_TX_HOOK_END */n->tx[j].used=0;n->diagnostics.acknowledged++;
    }
    uint32_t slot=p.id%COH_NET_WINDOW;
    int duplicate=p.id&&n->seen[slot]==p.id;
    if(!p.id||n->seen[slot]>p.id){n->diagnostics.malformed++;occupancy(n);return COH_INVALID;}
    int ack_present=0;for(uint32_t i=0;i<n->ack_count;i++)if(n->acks[i]==p.id)ack_present=1;
    if(!ack_present&&n->ack_count==COH_NET_ACK_MAX){n->diagnostics.queue_limits++;occupancy(n);return COH_LIMIT;}
    if(!duplicate) {
        s=retain(n,&p,now);
        if(s!=COH_OK){if(s==COH_INVALID)n->diagnostics.malformed++;occupancy(n);return s;}
        n->seen[slot]=p.id;
    } else n->diagnostics.duplicates++;
    if(!ack_present&&n->state!=COH_NET_CLOSED)n->acks[n->ack_count++]=p.id;
    n->last_rx_ms=n->last_clock_ms=now;n->diagnostics.received++;occupancy(n);return COH_OK;
}
CohStatus coh_net_next(CohNet *n,CohNetMessage *out) {
    if(!n||!out)return COH_INVALID;
    if(n->owned)return COH_STATE;
    Rx *r=NULL;
    for(unsigned i=0;i<COH_NET_RX_MAX;i++)if(n->rx[i].used) {
        CohNetMessage *m=&n->rx[i].message;
        if(m->ordered&&m->ordered_id!=n->last_ordered+1)continue;
        if(!r||m->id<r->message.id)r=&n->rx[i];
    }
    if(!r)return COH_NOT_FOUND;
    CohNetMessage m=r->message;
    if(m.compressed) {
        uint8_t data[COH_NET_MESSAGE_MAX];size_t size=0;
        CohStatus s=coh_net_zip_decode(n->zip,m.ordered,(CohBytes){m.payload,(m.payload_bits+7)/8},data,sizeof(data),&size);
        if(s!=COH_OK){clear_queues(n);forget_key(n);n->state=COH_NET_FAILED;n->diagnostics.malformed++;return s;}
        memcpy(m.payload,data,size);m.payload_bits=(uint32_t)size*8;
    }
    if(m.ordered)n->last_ordered=m.ordered_id;
    r->used=0;*out=m;occupancy(n);return COH_OK;
}
CohStatus coh_net_next_owned(CohNet *n,CohNetOwnedMessage *out) {
    if(!n||!out)return COH_INVALID;
    if(n->owned)return COH_STATE;
    Rx *r=NULL;
    for(unsigned i=0;i<COH_NET_RX_MAX;i++)if(n->rx[i].used) {
        CohNetMessage *m=&n->rx[i].message;
        if(m->ordered&&m->ordered_id!=n->last_ordered+1)continue;
        if(!r||m->id<r->message.id)r=&n->rx[i];
    }
    if(!r)return COH_NOT_FOUND;
    CohNetMessage *m=&r->message;size_t bytes=(m->payload_bits+7)/8;
    CohNetDecodeReceipt receipt;memset(&receipt,0,sizeof(receipt));
    receipt.output_budget=n->decoded_budget;
    if(m->compressed&&bytes>=4) {
        uint32_t cmd=(uint32_t)m->payload[0]|(uint32_t)m->payload[1]<<8|
            (uint32_t)m->payload[2]<<16|(uint32_t)m->payload[3]<<24;
        if(n->config.version<4&&cmd>=7&&cmd<=11){receipt.command_valid=1;receipt.normalized_command=cmd-5;}
        else if(n->config.version>=4&&cmd>=2&&cmd<=6){receipt.command_valid=1;receipt.normalized_command=cmd;}
    }
    uint8_t *data=NULL;size_t decoded=bytes;CohStatus status=COH_OK;
    if(m->compressed) {
        if(m->payload_bits&7){receipt.compressed_bytes=bytes;receipt.failure_kind=COH_NET_DECODE_HEADER;status=COH_INVALID;}
        else status=coh_net_zip_decode_owned(n->zip,m->ordered,
            (CohBytes){m->payload,bytes},n->decoded_budget,&data,&decoded,&receipt);
    }
    else {
        receipt.declared_raw_bytes=bytes;
        data=malloc(bytes);
        if(!data){receipt.failure_kind=COH_NET_DECODE_ALLOCATION;status=COH_LIMIT;}
        else memcpy(data,m->payload,bytes);
    }
    n->diagnostics.decode=receipt;
    if(status!=COH_OK) {
        clear_queues(n);forget_key(n);n->state=COH_NET_FAILED;n->diagnostics.malformed++;return status;
    }
    if(n->owned_generation==UINT64_MAX) {
        free(data);clear_queues(n);forget_key(n);n->state=COH_NET_FAILED;return COH_LIMIT;
    }
    n->owned=data;n->owned_bytes=decoded;n->owned_generation++;
    CohNetOwnedMessage result={m->id,m->ordered_id,m->compressed?(uint32_t)decoded*8:m->payload_bits,
        m->compressed,m->ordered,data,decoded,n->owned_generation};
    if(m->ordered)n->last_ordered=m->ordered_id;
    r->used=0;*out=result;occupancy(n);return COH_OK;
}
CohStatus coh_net_owned_release(CohNet *n,CohNetOwnedMessage *message) {
    if(!message)return COH_INVALID;
    CohStatus status=COH_STATE;
    if(n&&n->owned&&message->payload==n->owned&&message->generation==n->owned_generation) {
        free_owned(n);occupancy(n);status=COH_OK;
    }
    memset(message,0,sizeof(*message));return status;
}
void coh_net_diagnostics(const CohNet *n,CohNetDiagnostics *out) { if(n&&out){*out=n->diagnostics;out->codec_bytes=coh_net_zip_memory(n->zip);} }
