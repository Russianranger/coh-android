#include "coh_db_account_controls.h"
#include "../../protocol/coh_protocol.h"
#include <stdint.h>

typedef struct { CohBytes bytes; size_t bits,cursor; int aligned; } AccountBits;
typedef struct { char prefix; CohDbAccountControl value; } AccountAlignment;
static int overlaps(const void *a,size_t an,const void *b,size_t bn) {
    uintptr_t ap=(uintptr_t)a,bp=(uintptr_t)b;
    if(an>UINTPTR_MAX-ap||bn>UINTPTR_MAX-bp)return 1;
    return ap<bp+bn&&bp<ap+an;
}
static CohStatus scalar(AccountBits *b,unsigned width,int packed,uint32_t *value) {
    size_t byte=b->cursor/8,offset=b->cursor&7;
    if(byte>b->bytes.size||b->cursor>b->bits)return COH_INVALID;
    size_t capacity=b->bytes.size-byte;
    if(capacity>COH_PROTOCOL_FRAME_MAX)capacity=COH_PROTOCOL_FRAME_MAX;
    size_t bits=b->bits-byte*8;if(bits>capacity*8)bits=capacity*8;
    CohProtocolBits q;
    if(coh_protocol_bits_init(&q,(uint8_t *)(uintptr_t)b->bytes.data+byte,capacity,bits,0))return COH_INVALID;
    q.cursor=offset;
    if(packed?coh_protocol_read_pack(&q,width,value):coh_protocol_read(&q,width,value))return COH_INVALID;
    b->cursor=byte*8+q.cursor;return COH_OK;
}
static CohStatus automatic(AccountBits *b,uint32_t *value) {
    static const unsigned widths[]={2,10,24,32};uint32_t bin;
    CohStatus status=scalar(b,b->aligned?8:2,0,&bin);
    if(status!=COH_OK)return status;
    /* Byte-aligned source pktGetBits(2) reads eight bits; reject reserved bits. */
    if(bin>3)return COH_INVALID;
    return scalar(b,b->aligned?(widths[bin]+7)&~7u:widths[bin],0,value);
}
static CohStatus string(AccountBits *b) {
    for(size_t i=0;i<COH_DB_ACCOUNT_STRING_MAX;i++) {
        uint32_t c;CohStatus status=scalar(b,8,0,&c);
        if(status!=COH_OK)return status;
        if(!c)return COH_OK;
    }
    return COH_LIMIT;
}
CohStatus coh_db_account_control_parse(CohBytes bytes,size_t bits,int aligned,
    int legacy,CohDbAccountControl *out) {
    if(!out||(uintptr_t)out%offsetof(AccountAlignment,value)||!bytes.data||!bytes.size||
       bytes.size>COH_DB_MESSAGE_MAX||bits>bytes.size*8||
       (aligned!=0&&aligned!=1)||(legacy!=0&&legacy!=1)||
       overlaps(bytes.data,bytes.size,out,sizeof(*out)))return COH_INVALID;
    AccountBits b={bytes,bits,0,aligned};CohDbAccountControl v={0};
    CohStatus status=scalar(&b,aligned?32:1,!aligned,&v.command);
    if(status!=COH_OK)return status;
    if(legacy){if(v.command<5)return COH_INVALID;v.command-=5;}
    if(v.command==COH_DB_ACCOUNT_CHARCOUNT) {
        status=automatic(&b,&v.shards);if(status!=COH_OK)return status;
        if(v.shards>COH_DB_ACCOUNT_SHARDS_MAX)return COH_LIMIT;
        v.error_branch=!v.shards;
        if(!v.shards){status=string(&b);if(status!=COH_OK)return status;}
        for(uint32_t i=0;i<v.shards;i++) {
            status=string(&b);if(status!=COH_OK)return status;
            for(unsigned j=0;j<5;j++) {
                uint32_t ignored;status=automatic(&b,&ignored);if(status!=COH_OK)return status;
            }
        }
    } else if(v.command!=COH_DB_ACCOUNT_UNAVAILABLE)return COH_UNSUPPORTED;
    if(b.cursor!=bits)return COH_UNSUPPORTED;
    *out=v;return COH_OK;
}
