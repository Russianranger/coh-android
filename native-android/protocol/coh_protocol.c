#include "coh_protocol.h"
#include <string.h>

static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static uint32_t mask(unsigned n) { return n==32 ? UINT32_MAX : ((UINT32_C(1)<<n)-1); }
static int state(const CohProtocolBits *b,int writing) {
    return b && b->writing==writing && b->capacity<=COH_PROTOCOL_FRAME_MAX &&
        (b->data || !b->capacity) && b->bit_length<=b->capacity*8 && b->cursor<=b->bit_length;
}
int coh_protocol_bits_init(CohProtocolBits *b,uint8_t *p,size_t n,size_t bits,int writing) {
    if(!b || (!p && n) || n>COH_PROTOCOL_FRAME_MAX || bits>n*8 || (writing!=0 && writing!=1)) return 1;
    CohProtocolBits result={p,n,bits,0,writing}; *b=result; return 0;
}
int coh_protocol_write(CohProtocolBits *b,unsigned n,uint32_t value) {
    if(!state(b,1) || n>32 || n>b->capacity*8-b->cursor) return 1;
    for(unsigned i=0;i<n;i++) {
        size_t at=b->cursor+i; uint8_t bit=(uint8_t)(1u<<(at&7));
        b->data[at>>3]=(uint8_t)((b->data[at>>3]&~bit) | (((value>>i)&1u) ? bit : 0));
    }
    b->cursor+=n; if(b->cursor>b->bit_length) b->bit_length=b->cursor; return 0;
}
int coh_protocol_read(CohProtocolBits *b,unsigned n,uint32_t *value) {
    if(!state(b,0) || !value || n>32 || n>b->bit_length-b->cursor) return 1;
    uint32_t v=0;
    for(unsigned i=0;i<n;i++) { size_t at=b->cursor+i; v |= (uint32_t)((b->data[at>>3]>>(at&7))&1u)<<i; }
    b->cursor+=n; *value=v; return 0;
}
int coh_protocol_write_pack(CohProtocolBits *b,unsigned width,uint32_t value) {
    if(!state(b,1) || !width || width>32) return 1;
    size_t needed=0; unsigned n=width; uint32_t v=value;
    for(;;) {
        needed+=n;
        if(n==32 || v<mask(n)) break;
        v-=mask(n); n=n>16 ? 32 : n*2;
    }
    if(needed>b->capacity*8-b->cursor) return 1;
    n=width; v=value;
    for(;;) {
        uint32_t m=mask(n);
        if(n==32 || v<m) return coh_protocol_write(b,n,v);
        (void)coh_protocol_write(b,n,m); v-=m; n=n>16 ? 32 : n*2;
    }
}
int coh_protocol_read_pack(CohProtocolBits *b,unsigned width,uint32_t *value) {
    if(!state(b,0) || !value || !width || width>32) return 1;
    CohProtocolBits trial=*b; uint64_t base=0; unsigned n=width;
    for(;;) {
        uint32_t v;
        if(coh_protocol_read(&trial,n,&v)) return 1;
        if(n==32 || v<mask(n)) {
            if(base+v>UINT32_MAX) return 1;
            *b=trial; *value=(uint32_t)(base+v); return 0;
        }
        base+=mask(n); n=n>16 ? 32 : n*2;
    }
}
/* CryptoPP Adler32::Final emits high-to-low digest bytes. The Win32
 * cryptAdler32/pktSendRaw U32 pair preserves those exact bytes on the wire. */
static void adler_digest(const uint8_t *p,size_t n,uint8_t digest[4]) {
    uint32_t a=1,b=0;
    for(size_t i=0;i<n;i++) { a=(a+p[i])%65521; b=(b+a)%65521; }
    digest[0]=(uint8_t)(b>>8); digest[1]=(uint8_t)b;
    digest[2]=(uint8_t)(a>>8); digest[3]=(uint8_t)a;
}
static size_t padded(size_t n) { return 4+((n-4+7)&~(size_t)7); }
int coh_protocol_encode(CohBlowfish *ctx,int encrypted,uint32_t id,const uint8_t *payload,
        uint32_t bits,uint8_t *frame,size_t capacity,size_t *frame_bytes) {
    if((encrypted!=0 && encrypted!=1) || (encrypted && !ctx) || !payload || !bits ||
        bits>COH_PROTOCOL_PAYLOAD_MAX*8 || !frame || !frame_bytes) return 1;
    size_t payload_bytes=((size_t)bits+7)/8, logical=13+payload_bytes, length=padded(logical);
    if(length>capacity || length>COH_PROTOCOL_FRAME_MAX) return 1;
    uint8_t buf[COH_PROTOCOL_FRAME_MAX]={0}; CohProtocolBits stream;
    (void)coh_protocol_bits_init(&stream,buf,sizeof(buf),0,1);
    (void)coh_protocol_write(&stream,32,104+bits);
    (void)coh_protocol_write(&stream,32,0);
    (void)coh_protocol_write(&stream,1,0);
    (void)coh_protocol_write(&stream,32,id);
    (void)coh_protocol_write_pack(&stream,1,0);
    (void)coh_protocol_write_pack(&stream,1,0);
    memcpy(buf+13,payload,payload_bytes);
    adler_digest(buf+8,length-8,buf+4);
    if(encrypted && coh_bf_crypt(ctx,buf+4,length-4,0)) return 1;
    memcpy(frame,buf,length); *frame_bytes=length; return 0;
}
int coh_protocol_decode(CohBlowfish *ctx,int encrypted,const uint8_t *frame,size_t length,
        CohProtocolPacket *packet) {
    if((encrypted!=0 && encrypted!=1) || (encrypted && !ctx) || !frame || !packet ||
        length<20 || length>COH_PROTOCOL_FRAME_MAX || ((length-4)&7)) return 1;
    uint32_t total=le32(frame);
    if(total<105 || total>104+COH_PROTOCOL_PAYLOAD_MAX*8 || padded(((size_t)total+7)/8)!=length) return 1;
    uint8_t buf[COH_PROTOCOL_FRAME_MAX]; memcpy(buf,frame,length);
    if(encrypted && coh_bf_crypt(ctx,buf+4,length-4,1)) return 1;
    uint8_t digest[4]; adler_digest(buf+8,length-8,digest);
    if(memcmp(buf+4,digest,4)) return 1;
    CohProtocolBits stream; (void)coh_protocol_bits_init(&stream,buf,length,total,0); stream.cursor=64;
    CohProtocolPacket result; memset(&result,0,sizeof(result)); uint32_t debug,siblings,acks;
    if(coh_protocol_read(&stream,1,&debug) || debug || coh_protocol_read(&stream,32,&result.packet_id) ||
        coh_protocol_read_pack(&stream,1,&siblings) || siblings || coh_protocol_read_pack(&stream,1,&acks) || acks) return 1;
    stream.cursor=(stream.cursor+7)&~(size_t)7;
    if(stream.cursor!=104 || stream.cursor>=total) return 1;
    result.payload_bits=total-104; result.payload_bytes=((size_t)result.payload_bits+7)/8;
    memcpy(result.payload,buf+13,result.payload_bytes); *packet=result; return 0;
}
