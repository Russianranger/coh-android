#include "coh_net.h"
#include "coh_net_zip_internal.h"
#include <stdlib.h>
#include <string.h>
#include <zlib.h>

/* zlib allocation accounting is bounded separately from payload and queue
 * storage. zlib defaults request <400 KiB for one encoder + one decoder. */
#define ZIP_BUDGET (768u*1024u)
typedef union { size_t n; long double alignment; void *pointer; } Allocation;
struct CohNetZip { z_stream encode,decode;size_t allocated;int enc_ready,dec_ready,poison; };
static voidpf alloc_z(voidpf opaque,uInt items,uInt size) {
    CohNetZip *z=opaque;if(size&&items>SIZE_MAX/size) return NULL;
    size_t n=(size_t)items*size;
    if(n>ZIP_BUDGET-z->allocated||n>SIZE_MAX-sizeof(Allocation)) return NULL;
    Allocation *p=calloc(1,n+sizeof(*p));if(!p) return NULL;
    p->n=n;z->allocated+=n;return p+1;
}
static void free_z(voidpf opaque,voidpf pointer) {
    if(pointer) { CohNetZip *z=opaque;Allocation *p=(Allocation*)pointer-1;
        z->allocated-=p->n;free(p); }
}
static uint32_t le32(const uint8_t *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static void put32(uint8_t *p,uint32_t v) { for(unsigned i=0;i<4;i++) p[i]=(uint8_t)(v>>(i*8)); }
CohNetZip *coh_net_zip_create(void) {
    CohNetZip *z=calloc(1,sizeof(*z));if(!z) return NULL;
    z->encode.zalloc=z->decode.zalloc=alloc_z;z->encode.zfree=z->decode.zfree=free_z;
    z->encode.opaque=z->decode.opaque=z;
    if(deflateInit(&z->encode,Z_DEFAULT_COMPRESSION)!=Z_OK) { coh_net_zip_destroy(z);return NULL; }
    z->enc_ready=1;
    if(inflateInit(&z->decode)!=Z_OK) { coh_net_zip_destroy(z);return NULL; }
    z->dec_ready=1;return z;
}
void coh_net_zip_destroy(CohNetZip *z) {
    if(!z)return;
    if(z->enc_ready)deflateEnd(&z->encode);
    if(z->dec_ready)inflateEnd(&z->decode);
    free(z);
}
size_t coh_net_zip_memory(const CohNetZip *z) { return z?sizeof(*z)+z->allocated:0; }
CohStatus coh_net_zip_encode(CohNetZip *z,int stream,CohBytes in,uint8_t *out,size_t cap,size_t *bytes) {
    if(!z||z->poison||!in.data||in.size<4||in.size>COH_NET_MESSAGE_MAX||!out||!bytes||cap>COH_NET_MESSAGE_MAX||(stream!=0&&stream!=1))return COH_INVALID;
    /* Preflight worst-case size before changing a persistent dictionary. */
    size_t need=in.size-4<12?in.size:8+(size_t)compressBound(in.size-4)+8;
    if(need>cap)return COH_LIMIT;
    uint8_t scratch[COH_NET_MESSAGE_MAX];size_t n;
    if(in.size-4<12) { memcpy(scratch,in.data,in.size);n=in.size; }
    else {
        memcpy(scratch,in.data,4);put32(scratch+4,(uint32_t)in.size-4);
        z_stream temporary;memset(&temporary,0,sizeof(temporary));
        temporary.zalloc=alloc_z;temporary.zfree=free_z;temporary.opaque=z;
        z_stream *s=stream?&z->encode:&temporary;
        if(!stream&&deflateInit(s,Z_DEFAULT_COMPRESSION)!=Z_OK)return COH_LIMIT;
        s->next_in=(Bytef*)in.data+4;s->avail_in=(uInt)in.size-4;
        s->next_out=scratch+8;s->avail_out=(uInt)sizeof(scratch)-8;
        int r=deflate(s,stream?Z_SYNC_FLUSH:Z_FINISH);
        int good=(stream?r==Z_OK:r==Z_STREAM_END)&&!s->avail_in&&s->avail_out;
        n=sizeof(scratch)-s->avail_out;
        if(!stream)deflateEnd(s);
        if(!good) { if(stream)z->poison=1;return COH_INVALID; }
    }
    memcpy(out,scratch,n);*bytes=n;return COH_OK;
}
CohStatus coh_net_zip_decode(CohNetZip *z,int stream,CohBytes in,uint8_t *out,size_t cap,size_t *bytes) {
    if(!z||z->poison||!in.data||in.size<4||in.size>COH_NET_MESSAGE_MAX||!out||!bytes||cap>COH_NET_MESSAGE_MAX||(stream!=0&&stream!=1))return COH_INVALID;
    if(in.size-4<12) { if(cap<in.size)return COH_LIMIT;memcpy(out,in.data,in.size);*bytes=in.size;return COH_OK; }
    uint32_t tail=le32(in.data+4);
    if(tail<12||tail>COH_NET_MESSAGE_MAX-4)return COH_LIMIT;
    if(cap<(size_t)tail+4)return COH_LIMIT;
    uint8_t scratch[COH_NET_MESSAGE_MAX];memcpy(scratch,in.data,4);
    z_stream temporary;memset(&temporary,0,sizeof(temporary));
    temporary.zalloc=alloc_z;temporary.zfree=free_z;temporary.opaque=z;
    z_stream *s=stream?&z->decode:&temporary;
    if(!stream&&inflateInit(s)!=Z_OK)return COH_LIMIT;
    s->next_in=(Bytef*)in.data+8;s->avail_in=(uInt)in.size-8;
    s->next_out=scratch+4;s->avail_out=tail;
    int r=inflate(s,stream?Z_SYNC_FLUSH:Z_FINISH);
    int good=(stream?r==Z_OK:r==Z_STREAM_END)&&!s->avail_in&&!s->avail_out;
    if(!stream)inflateEnd(s);
    if(!good) { if(stream)z->poison=1;return COH_INVALID; }
    memcpy(out,scratch,(size_t)tail+4);*bytes=(size_t)tail+4;return COH_OK;
}

CohStatus coh_net_zip_decode_owned(CohNetZip *z,int stream,CohBytes in,size_t budget,
    uint8_t **out,size_t *bytes,CohNetDecodeReceipt *receipt) {
    if(!receipt)return COH_INVALID;
    receipt->compressed_bytes=in.size;receipt->output_budget=budget;
    receipt->declared_raw_bytes=0;receipt->failure_kind=COH_NET_DECODE_HEADER;
    if(!z||z->poison||!in.data||in.size<4||in.size>COH_NET_MESSAGE_MAX||
       !out||!bytes||budget<COH_NET_MESSAGE_MAX||budget>COH_NET_DECODED_MAX||
       (stream!=0&&stream!=1))return COH_INVALID;
    size_t total=in.size;uint32_t tail=0;
    if(in.size-4>=12) {
        tail=le32(in.data+4);
        if(tail<12)return COH_INVALID;
        uint64_t declared=(uint64_t)tail+4;
        receipt->declared_raw_bytes=declared;
        /* Compare in 64 bits before size_t conversion or allocation. */
        if(declared>budget){receipt->failure_kind=COH_NET_DECODE_BUDGET;return COH_LIMIT;}
        total=(size_t)declared;
    }
    receipt->declared_raw_bytes=total;
    if(total>budget){receipt->failure_kind=COH_NET_DECODE_BUDGET;return COH_LIMIT;}
    /* Source bsCompress uses Z_SYNC_FLUSH for persistent streams. Requiring
     * its completed empty stored-block suffix also detects a truncated flush
     * that otherwise yields all declared output before the final marker. */
    if(tail&&stream&&(in.data[in.size-4]||in.data[in.size-3]||
       in.data[in.size-2]!=0xff||in.data[in.size-1]!=0xff)) {
        z->poison=1;receipt->failure_kind=COH_NET_DECODE_STREAM;return COH_INVALID;
    }
    uint8_t *data=malloc(total);
    if(!data){receipt->failure_kind=COH_NET_DECODE_ALLOCATION;return COH_LIMIT;}
    memcpy(data,in.data,4);
    if(!tail)memcpy(data,in.data,total);
    else {
        z_stream temporary;memset(&temporary,0,sizeof(temporary));
        temporary.zalloc=alloc_z;temporary.zfree=free_z;temporary.opaque=z;
        z_stream *s=stream?&z->decode:&temporary;
        if(!stream&&inflateInit(s)!=Z_OK) {
            free(data);receipt->failure_kind=COH_NET_DECODE_ALLOCATION;return COH_LIMIT;
        }
        s->next_in=(Bytef*)in.data+8;s->avail_in=(uInt)in.size-8;
        s->next_out=data+4;s->avail_out=tail;
        int r=inflate(s,stream?Z_SYNC_FLUSH:Z_FINISH);
        int good=(stream?r==Z_OK:r==Z_STREAM_END)&&!s->avail_in&&!s->avail_out;
        if(!stream)inflateEnd(s);
        if(!good) {
            if(stream)z->poison=1;
            free(data);receipt->failure_kind=r==Z_MEM_ERROR?COH_NET_DECODE_ALLOCATION:COH_NET_DECODE_STREAM;
            return r==Z_MEM_ERROR?COH_LIMIT:COH_INVALID;
        }
    }
    receipt->failure_kind=COH_NET_DECODE_NONE;*out=data;*bytes=total;return COH_OK;
}
