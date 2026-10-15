#include "coh_net.h"
#include <string.h>

static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static size_t pad(size_t n) { return 4+((n-4+7)&~(size_t)7); }
static void adler(const uint8_t *p,size_t n,uint8_t out[4]) {
    uint32_t a=1,b=0;
    while(n--) { a=(a+*p++)%65521; b=(b+a)%65521; }
    out[0]=(uint8_t)(b>>8);out[1]=(uint8_t)b;
    out[2]=(uint8_t)(a>>8);out[3]=(uint8_t)a;
}
static int valid(const CohNetPacket *p,unsigned ver) {
    if(!p||ver>5||!p->payload_bits||p->payload_bits>COH_NET_PAYLOAD_MAX*8||
       p->ack_count>COH_NET_ACK_MAX||p->compressed>1||p->ordered>1||p->connect>1) return 0;
    if(p->sibling_count && (p->sibling_count<2||p->sibling_count>COH_NET_FRAGMENT_MAX||
       !p->sibling_id||p->sibling_part>=p->sibling_count)) return 0;
    if(!p->sibling_count&&(p->sibling_id||p->sibling_part)) return 0;
    if((p->connect&&(p->compressed||p->ordered||p->sibling_count))||
       (p->compressed&&(!ver||(p->payload_bits&7)))||(p->ordered&&(ver<5||!p->ordered_id))) return 0;
    for(uint32_t i=1;i<p->ack_count;i++) if(p->acks[i]<=p->acks[i-1]) return 0;
    return 1;
}
static const unsigned bins[4]={2,10,24,32};
#define W(n,v) do { if(coh_protocol_write(&b,n,v)) return COH_LIMIT; } while(0)
#define P(n,v) do { if(coh_protocol_write_pack(&b,n,v)) return COH_LIMIT; } while(0)
CohStatus coh_net_frame_encode(unsigned ver,CohBlowfish *key,int enc,const CohNetPacket *p,
        uint8_t *out,size_t capacity,size_t *bytes) {
    if(!valid(p,ver)||!out||!bytes||(enc!=0&&enc!=1)||(enc&&!key)) return COH_INVALID;
    uint8_t data[COH_PROTOCOL_FRAME_MAX]={0}; CohProtocolBits b;
    (void)coh_protocol_bits_init(&b,data,sizeof(data),0,1);
    W(32,0);W(32,0);W(1,0);W(32,p->id);P(1,p->sibling_count);
    if(p->sibling_count) { P(1,p->sibling_part);W(32,p->sibling_id); }
    P(1,p->ack_count);
    if(p->ack_count) { W(32,p->acks[0]);
        for(uint32_t i=1;i<p->ack_count;i++) P(1,p->acks[i]-p->acks[i-1]-1);
    }
    if(ver&&!p->connect) W(1,p->compressed);
    if(ver>=5&&!p->connect) {
        W(1,p->ordered);
        if(p->ordered) { unsigned bin=0;while(bin<3&&p->ordered_id>=(UINT32_C(1)<<bins[bin])) bin++;
            W(2,bin);W(bins[bin],p->ordered_id);
        }
    }
    b.cursor=(b.cursor+7)&~(size_t)7;
    if(b.cursor/8+((size_t)p->payload_bits+7)/8>sizeof(data)) return COH_LIMIT;
    memcpy(data+b.cursor/8,p->payload,((size_t)p->payload_bits+7)/8);
    size_t total=b.cursor+p->payload_bits, length=pad((total+7)/8);
    if(length>capacity||length>sizeof(data)) return COH_LIMIT;
    for(unsigned i=0;i<4;i++) data[i]=(uint8_t)(total>>(i*8));
    adler(data+8,length-8,data+4);
    if(enc&&coh_bf_crypt(key,data+4,length-4,0)) return COH_INVALID;
    memcpy(out,data,length);*bytes=length;return COH_OK;
}
#undef W
#undef P
#define R(n,v) do { if(coh_protocol_read(&b,n,&v)) return COH_INVALID; } while(0)
#define G(n,v) do { if(coh_protocol_read_pack(&b,n,&v)) return COH_INVALID; } while(0)
CohStatus coh_net_frame_decode(unsigned ver,CohBlowfish *key,int enc,int connect,
        CohBytes frame,CohNetPacket *out) {
    if(ver>5||!frame.data||!out||frame.size<20||frame.size>COH_PROTOCOL_FRAME_MAX||
       ((frame.size-4)&7)||(enc!=0&&enc!=1)||(enc&&!key)||(connect!=0&&connect!=1)) return COH_INVALID;
    uint32_t total=le32(frame.data);
    if(total<105||total>frame.size*8||pad(((size_t)total+7)/8)!=frame.size) return COH_INVALID;
    uint8_t data[COH_PROTOCOL_FRAME_MAX],digest[4];memcpy(data,frame.data,frame.size);
    if(enc&&coh_bf_crypt(key,data+4,frame.size-4,1)) return COH_INVALID;
    adler(data+8,frame.size-8,digest);
    if(memcmp(digest,data+4,4)) return COH_INVALID;
    CohNetPacket p;memset(&p,0,sizeof(p));p.connect=(uint8_t)connect;
    CohProtocolBits b;(void)coh_protocol_bits_init(&b,data,frame.size,total,0);b.cursor=64;
    uint32_t flag;R(1,flag);if(flag) return COH_UNSUPPORTED;
    R(32,p.id);G(1,p.sibling_count);
    if(p.sibling_count) { G(1,p.sibling_part);R(32,p.sibling_id); }
    G(1,p.ack_count);if(p.ack_count>COH_NET_ACK_MAX) return COH_LIMIT;
    if(p.ack_count) { R(32,p.acks[0]);
        for(uint32_t i=1;i<p.ack_count;i++) {
            uint32_t delta;G(1,delta);
            if(delta==UINT32_MAX||p.acks[i-1]>UINT32_MAX-delta-1) return COH_INVALID;
            p.acks[i]=p.acks[i-1]+delta+1;
        }
    }
    if(ver&&!connect) { R(1,flag);p.compressed=(uint8_t)flag; }
    if(ver>=5&&!connect) {
        R(1,flag);p.ordered=(uint8_t)flag;
        if(p.ordered) { uint32_t bin;R(2,bin);R(bins[bin],p.ordered_id); }
    }
    b.cursor=(b.cursor+7)&~(size_t)7;
    if(b.cursor>=total||total-b.cursor>COH_NET_PAYLOAD_MAX*8) return COH_INVALID;
    p.payload_bits=total-(uint32_t)b.cursor;
    memcpy(p.payload,data+b.cursor/8,((size_t)p.payload_bits+7)/8);
    if(!valid(&p,ver)) return COH_INVALID;
    *out=p;return COH_OK;
}
#undef R
#undef G
uint32_t coh_net_retry_ms(unsigned retries,unsigned ping,int old) {
    uint64_t n=old?(uint64_t)ping*3/2:(uint64_t)ping*4;
    n<<=(retries>2?2:retries);if(n<250) n=250;if(n>5000) n=5000;return (uint32_t)n;
}
