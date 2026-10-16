#include "coh_net.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <zlib.h>

static unsigned checks,negative,wire_cases,session_cases;
#define CHECK(x) do { checks++;if(!(x)){fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#x);exit(1);} }while(0)
typedef struct { unsigned version;CohNetPacket packet;const uint8_t *payload,*wire;size_t bytes; } Golden;
#include "goldens.h"
#include "retry_goldens.h"
typedef struct { int streaming;const uint8_t *input;size_t input_bytes;const uint8_t *wire;size_t wire_bytes; } ZipGolden;
#include "zip_goldens.h"
typedef struct { int streaming;unsigned pattern;size_t raw_bytes;const uint8_t *wire;size_t wire_bytes; } LargeGolden;
#include "large_zip_goldens.h"
typedef struct { uint8_t frames[COH_NET_TX_MAX][COH_PROTOCOL_FRAME_MAX];size_t sizes[COH_NET_TX_MAX];unsigned count;CohStatus status; } Captured;
static CohStatus capture(void *context,CohBytes b) {
    Captured *c=context;if(c->status!=COH_OK)return c->status;
    CHECK(c->count<COH_NET_TX_MAX);CHECK(b.size<=COH_PROTOCOL_FRAME_MAX);
    memcpy(c->frames[c->count],b.data,b.size);c->sizes[c->count++]=b.size;return COH_OK;
}
static CohBytes frame(unsigned version,CohNetPacket *p,uint8_t out[COH_PROTOCOL_FRAME_MAX]) {
    size_t size=0;CHECK(coh_net_frame_encode(version,NULL,0,p,out,COH_PROTOCOL_FRAME_MAX,&size)==COH_OK);return (CohBytes){out,size};
}
static CohNetPacket command(unsigned ver,uint32_t id,uint32_t cmd,uint32_t value,int has_value) {
    CohNetPacket p;memset(&p,0,sizeof(p));p.id=id;
    CohProtocolBits b;CHECK(!coh_protocol_bits_init(&b,p.payload,sizeof(p.payload),0,1));
    if(ver>=4&&cmd!=1){CHECK(!coh_protocol_write_pack(&b,1,0));if(cmd)CHECK(!coh_protocol_write_pack(&b,1,cmd));}
    else CHECK(!coh_protocol_write_pack(&b,1,cmd));
    if(has_value)CHECK(!coh_protocol_write_pack(&b,1,value));
    p.payload_bits=(uint32_t)b.bit_length;return p;
}
static CohNet *connected_budget(unsigned ver,size_t budget) {
    CohNetConfig config=coh_net_default_config();config.version=ver;CohNet *n=coh_net_create(&config);CHECK(n);
    if(budget)CHECK(coh_net_set_decoded_budget(n,budget)==COH_OK);
    CHECK(coh_net_begin(n,0x12345678,100)==COH_OK);CHECK(coh_net_begin(n,1,100)==COH_STATE);
    Captured c={0};CHECK(coh_net_pump(n,100,capture,&c,(CohCancel){0})==COH_OK);CHECK(c.count==1);
    CohNetPacket p;CHECK(coh_net_frame_decode(ver,NULL,0,1,(CohBytes){c.frames[0],c.sizes[0]},&p)==COH_OK);CHECK(p.connect&&p.id==1);
    CohProtocolBits b;uint32_t cmd,key,version;
    CHECK(!coh_protocol_bits_init(&b,p.payload,sizeof(p.payload),p.payload_bits,0));
    CHECK(!coh_protocol_read_pack(&b,1,&cmd)&&cmd==1);CHECK(!coh_protocol_read_pack(&b,1,&key)&&key==0x12345678);
    CHECK(!coh_protocol_read_pack(&b,1,&version)&&version==ver);
    uint8_t raw[COH_PROTOCOL_FRAME_MAX];p=command(ver,100,2,0,1);p.ack_count=1;p.acks[0]=1;
    CHECK(coh_net_receive(n,frame(ver,&p,raw),101)==COH_OK);CHECK(coh_net_state(n)==COH_NET_WAIT_FINAL);
    c.count=0;CHECK(coh_net_pump(n,101,capture,&c,(CohCancel){0})==COH_OK);CHECK(c.count==1);
    CHECK(coh_net_frame_decode(ver,NULL,0,0,(CohBytes){c.frames[0],c.sizes[0]},&p)==COH_OK);CHECK(p.id==2&&p.ack_count==1&&p.acks[0]==100);
    p=command(ver,101,4,0,0);p.ack_count=1;p.acks[0]=2;
    CHECK(coh_net_receive(n,frame(ver,&p,raw),102)==COH_OK);CHECK(coh_net_state(n)==COH_NET_CONNECTED);session_cases++;
    return n;
}
static CohNet *connected(unsigned ver) {return connected_budget(ver,0);}
static void test_frames(void) {
    uint8_t key_data[16];for(unsigned i=0;i<16;i++)key_data[i]=(uint8_t)i;CohBlowfish key;CHECK(!coh_bf_init(&key,key_data,16));
    for(size_t i=0;i<sizeof(goldens)/sizeof(goldens[0]);i++) {
        const Golden *g=&goldens[i];CohNetPacket p=g->packet;memcpy(p.payload,g->payload,(p.payload_bits+7)/8);
        for(unsigned alignment=0;alignment<8;alignment++) {
            uint8_t space[COH_PROTOCOL_FRAME_MAX+8];size_t size=0;
            CHECK(coh_net_frame_encode(g->version,NULL,0,&p,space+alignment,sizeof(space)-alignment,&size)==COH_OK);
            CHECK(size==g->bytes&&!memcmp(space+alignment,g->wire,size));wire_cases++;
            CohNetPacket decoded;CHECK(coh_net_frame_decode(g->version,NULL,0,p.connect,(CohBytes){space+alignment,size},&decoded)==COH_OK);
            CHECK(decoded.id==p.id&&decoded.sibling_id==p.sibling_id&&decoded.sibling_count==p.sibling_count&&decoded.sibling_part==p.sibling_part);
            CHECK(decoded.ordered_id==p.ordered_id&&decoded.ack_count==p.ack_count&&decoded.payload_bits==p.payload_bits);
            CHECK(decoded.compressed==p.compressed&&!memcmp(decoded.acks,p.acks,p.ack_count*4)&&!memcmp(decoded.payload,p.payload,(p.payload_bits+7)/8));
            uint8_t encrypted[COH_PROTOCOL_FRAME_MAX];size_t enc_size=0;
            CHECK(coh_net_frame_encode(g->version,&key,1,&p,encrypted,sizeof(encrypted),&enc_size)==COH_OK);
            CHECK(enc_size==size);CHECK(coh_net_frame_decode(g->version,&key,1,p.connect,(CohBytes){encrypted,enc_size},&decoded)==COH_OK);
            CHECK(!memcmp(decoded.payload,p.payload,(p.payload_bits+7)/8));
        }
        for(size_t cut=0;cut<g->bytes;cut++) {
            uint8_t *exact=malloc(cut?cut:1);memcpy(exact,g->wire,cut);
            CohNetPacket before,after;memset(&before,0xa5,sizeof(before));after=before;
            CHECK(coh_net_frame_decode(g->version,NULL,0,p.connect,(CohBytes){exact,cut},&after)!=COH_OK);
            CHECK(!memcmp(&before,&after,sizeof(before)));free(exact);negative++;
        }
    }
    for(size_t i=0;i<sizeof(retry_goldens)/sizeof(retry_goldens[0]);i++) {
        const uint32_t *g=retry_goldens[i];CHECK(coh_net_retry_ms(g[0],g[1],(int)g[2])==g[3]);
    }
    CohNetPacket p;memset(&p,0,sizeof(p));p.id=1;p.payload_bits=8;
    uint8_t out[COH_PROTOCOL_FRAME_MAX];memset(out,0xaa,sizeof(out));size_t size=999;
    p.ack_count=32;CHECK(coh_net_frame_encode(5,NULL,0,&p,out,sizeof(out),&size)==COH_INVALID);CHECK(size==999&&out[0]==0xaa);negative++;
    p.ack_count=2;p.acks[0]=2;p.acks[1]=1;CHECK(coh_net_frame_encode(5,NULL,0,&p,out,sizeof(out),&size)==COH_INVALID);negative++;
    p.ack_count=0;p.sibling_count=16;p.sibling_part=16;p.sibling_id=1;CHECK(coh_net_frame_encode(5,NULL,0,&p,out,sizeof(out),&size)==COH_INVALID);negative++;
    p.sibling_count=p.sibling_part=p.sibling_id=0;p.ordered=1;p.ordered_id=0;CHECK(coh_net_frame_encode(5,NULL,0,&p,out,sizeof(out),&size)==COH_INVALID);negative++;
    p.ordered=0;p.compressed=1;p.payload_bits=32;CohBytes f=frame(5,&p,out);
    uint32_t total=(uint32_t)out[0]|(uint32_t)out[1]<<8|(uint32_t)out[2]<<16|(uint32_t)out[3]<<24;
    total--;for(unsigned i=0;i<4;i++)out[i]=(uint8_t)(total>>(i*8));
    CohNetPacket decoded;CHECK(coh_net_frame_decode(5,NULL,0,0,f,&decoded)==COH_INVALID);negative++;
}
static void test_zip(void) {
    CohNetZip *enc=coh_net_zip_create(),*dec=coh_net_zip_create();CHECK(enc&&dec);
    uint8_t input[5000],packed[COH_NET_MESSAGE_MAX],output[COH_NET_MESSAGE_MAX];memset(input,'x',sizeof(input));input[0]=10;input[1]=input[2]=input[3]=0;
    for(size_t i=0;i<sizeof(zip_goldens)/sizeof(zip_goldens[0]);i++) {
        const ZipGolden *g=&zip_goldens[i];size_t size=0,decoded=0;
        CHECK(coh_net_zip_encode(enc,g->streaming,(CohBytes){g->input,g->input_bytes},packed,sizeof(packed),&size)==COH_OK);
        CHECK(size==g->wire_bytes&&!memcmp(packed,g->wire,size));
        CHECK(coh_net_zip_decode(dec,g->streaming,(CohBytes){g->wire,g->wire_bytes},output,sizeof(output),&decoded)==COH_OK);
        CHECK(decoded==g->input_bytes&&!memcmp(output,g->input,decoded));
    }
    coh_net_zip_destroy(enc);coh_net_zip_destroy(dec);
    enc=coh_net_zip_create();dec=coh_net_zip_create();CHECK(enc&&dec);
    for(unsigned repeat=0;repeat<500;repeat++) {
        input[40]=(uint8_t)repeat;size_t n=0,decoded=0;
        int stream=repeat%3!=0;
        CHECK(coh_net_zip_encode(enc,stream,(CohBytes){input,sizeof(input)},packed,sizeof(packed),&n)==COH_OK);
        CHECK(coh_net_zip_decode(dec,stream,(CohBytes){packed,n},output,sizeof(output),&decoded)==COH_OK);
        CHECK(decoded==sizeof(input)&&!memcmp(input,output,decoded));
    }
    CHECK(coh_net_zip_memory(enc)<768*1024);CHECK(coh_net_zip_memory(dec)<768*1024);
    size_t n=999;memset(output,0x55,sizeof(output));
    CHECK(coh_net_zip_encode(enc,1,(CohBytes){input,sizeof(input)},output,10,&n)==COH_LIMIT);CHECK(n==999&&output[0]==0x55);negative++;
    /* Independent zlib compress2 oracle for original command/length/tail. */
    size_t native_n=0;CHECK(coh_net_zip_encode(enc,0,(CohBytes){input,sizeof(input)},packed,sizeof(packed),&native_n)==COH_OK);
    uint8_t reference[COH_NET_MESSAGE_MAX];memcpy(reference,input,4);uint32_t tail=sizeof(input)-4;
    for(unsigned i=0;i<4;i++)reference[4+i]=(uint8_t)(tail>>(i*8));
    uLongf reference_n=sizeof(reference)-8;
    CHECK(compress2(reference+8,&reference_n,input+4,tail,Z_DEFAULT_COMPRESSION)==Z_OK);
    CHECK(native_n==reference_n+8&&!memcmp(packed,reference,native_n));
    packed[4]=packed[5]=packed[6]=packed[7]=0xff;
    CHECK(coh_net_zip_decode(dec,0,(CohBytes){packed,native_n},output,sizeof(output),&n)==COH_LIMIT);negative++;
    input[0]=7;CHECK(coh_net_zip_encode(enc,0,(CohBytes){input,15},packed,sizeof(packed),&n)==COH_OK);CHECK(n==15&&!memcmp(input,packed,n));
    CHECK(coh_net_zip_decode(dec,0,(CohBytes){packed,n},output,sizeof(output),&n)==COH_OK);CHECK(n==15&&!memcmp(input,output,n));
    coh_net_zip_destroy(enc);coh_net_zip_destroy(dec);
}
static CohNetPacket game(uint32_t id,uint32_t order,uint8_t value) {
    CohNetPacket p;memset(&p,0,sizeof(p));p.id=id;p.ordered=(uint8_t)!!order;p.ordered_id=order;
    p.payload[0]=0x57; /* BitsPack(1,14), then data. */
    p.payload[1]=value;p.payload_bits=16;return p;
}
static void test_session(void) {
    for(unsigned ver=0;ver<=5;ver++) { CohNet *n=connected(ver);coh_net_destroy(n); }
    CohNet *n=connected(5);uint8_t data[5000];memset(data,0xa5,sizeof(data));data[0]=0x57;
    CHECK(coh_net_queue(n,(CohBytes){data,sizeof(data)},sizeof(data)*8,1,1,0,103)==COH_OK);
    Captured c={0};CHECK(coh_net_pump(n,103,capture,&c,(CohCancel){0})==COH_OK);CHECK(c.count==5);
    CohNetDiagnostics diagnostics;coh_net_diagnostics(n,&diagnostics);CHECK(diagnostics.tx_pending==5);
    c.count=0;CHECK(coh_net_pump(n,200,capture,&c,(CohCancel){0})==COH_OK);CHECK(c.count==0);
    CHECK(coh_net_pump(n,503,capture,&c,(CohCancel){0})==COH_OK);CHECK(c.count==5);
    coh_net_diagnostics(n,&diagnostics);CHECK(diagnostics.retransmits==5);
    /* Independent receiving link: complete source-compatible fragments in
     * reverse transport order, then ordered delivery after assembly. */
    CohNet *receiver=connected(5);
    for(unsigned i=c.count;i>0;i--)CHECK(coh_net_receive(receiver,(CohBytes){c.frames[i-1],c.sizes[i-1]},504)==COH_OK);
    CohNetMessage message;CHECK(coh_net_next(receiver,&message)==COH_OK);CHECK(message.payload_bits==sizeof(data)*8&&message.ordered_id==1&&!memcmp(message.payload,data,sizeof(data)));
    CHECK(coh_net_next(receiver,&message)==COH_NOT_FOUND);
    CHECK(coh_net_receive(receiver,(CohBytes){c.frames[0],c.sizes[0]},505)==COH_OK);
    coh_net_diagnostics(receiver,&diagnostics);CHECK(diagnostics.duplicates==1);
    Captured response={0};CHECK(coh_net_pump(receiver,505,capture,&response,(CohCancel){0})==COH_OK);CHECK(response.count==1);
    CHECK(coh_net_receive(n,(CohBytes){response.frames[0],response.sizes[0]},506)==COH_OK);
    coh_net_diagnostics(n,&diagnostics);CHECK(diagnostics.tx_pending==0&&diagnostics.acknowledged==7);
    coh_net_destroy(receiver);coh_net_destroy(n);session_cases++;
    n=connected(5);uint8_t raw[COH_PROTOCOL_FRAME_MAX];CohNetPacket p=game(103,2,22);
    CHECK(coh_net_receive(n,frame(5,&p,raw),103)==COH_OK);CHECK(coh_net_next(n,&message)==COH_NOT_FOUND);
    p=game(102,1,11);CHECK(coh_net_receive(n,frame(5,&p,raw),104)==COH_OK);
    CHECK(coh_net_next(n,&message)==COH_OK&&message.ordered_id==1&&message.payload[1]==11);
    CHECK(coh_net_next(n,&message)==COH_OK&&message.ordered_id==2&&message.payload[1]==22);
    p=game(104,1,99);CHECK(coh_net_receive(n,frame(5,&p,raw),105)==COH_INVALID);negative++;
    coh_net_destroy(n);
}
static void test_compressed_session(void) {
    CohNet *sender=connected(5),*receiver=connected(5);uint8_t input[4000];memset(input,'z',sizeof(input));input[0]=10;input[1]=input[2]=input[3]=0;
    Captured c={0};
    for(unsigned i=0;i<3;i++){input[50]=(uint8_t)i;CHECK(coh_net_queue(sender,(CohBytes){input,sizeof(input)},sizeof(input)*8,1,1,1,103)==COH_OK);}
    CHECK(coh_net_pump(sender,103,capture,&c,(CohCancel){0})==COH_OK);CHECK(c.count==3);
    for(unsigned i=c.count;i>0;i--)CHECK(coh_net_receive(receiver,(CohBytes){c.frames[i-1],c.sizes[i-1]},104)==COH_OK);
    for(unsigned i=0;i<3;i++) { CohNetMessage m;CHECK(coh_net_next(receiver,&m)==COH_OK);CHECK(m.payload_bits==sizeof(input)*8&&m.payload[50]==i&&m.ordered_id==i+1); }
    coh_net_destroy(sender);coh_net_destroy(receiver);session_cases++;
}

/* Linker-local test allocator seam; production builds do not expose hooks. */
static int refuse_owned_allocation;
void *__real_malloc(size_t bytes);
void *__wrap_malloc(size_t bytes) {
    if(refuse_owned_allocation&&bytes>COH_NET_MESSAGE_MAX)return NULL;
    return __real_malloc(bytes);
}
static void deliver_zip(CohNet *n,CohBytes body,unsigned order,uint32_t *id,uint64_t now) {
    CHECK(body.size&&body.size<=COH_NET_MESSAGE_MAX);
    unsigned count=(unsigned)((body.size+COH_PROTOCOL_PAYLOAD_MAX-1)/COH_PROTOCOL_PAYLOAD_MAX);
    uint32_t first=*id;*id+=count;
    for(unsigned part=count;part>0;part--) {
        unsigned i=part-1;size_t offset=i*COH_PROTOCOL_PAYLOAD_MAX;
        size_t bytes=body.size-offset;if(bytes>COH_PROTOCOL_PAYLOAD_MAX)bytes=COH_PROTOCOL_PAYLOAD_MAX;
        CohNetPacket p;memset(&p,0,sizeof(p));p.id=first+i;p.ordered=(uint8_t)!!order;p.ordered_id=order;p.compressed=1;
        if(count>1){p.sibling_id=first;p.sibling_count=count;p.sibling_part=i;}
        p.payload_bits=(uint32_t)bytes*8;memcpy(p.payload,body.data+offset,bytes);
        uint8_t raw[COH_PROTOCOL_FRAME_MAX];CHECK(coh_net_receive(n,frame(5,&p,raw),now)==COH_OK);
    }
}
static void assert_large(const CohNetOwnedMessage *m,const LargeGolden *g) {
    CHECK(m->payload_bytes==g->raw_bytes&&m->payload_bits==g->raw_bytes*8);
    CHECK(m->payload[0]==6&&!m->payload[1]&&!m->payload[2]&&!m->payload[3]);
    int valid=1;for(size_t i=4;i<g->raw_bytes;i++)if(m->payload[i]!=(uint8_t)(65+((i-4+g->pattern)%16))){valid=0;break;}
    CHECK(valid);
}
static void test_owned_large(void) {
    CohNet *n=coh_net_create(NULL);CHECK(n);
    CHECK(coh_net_set_decoded_budget(n,COH_NET_MESSAGE_MAX-1)==COH_INVALID);
    CHECK(coh_net_set_decoded_budget(n,COH_NET_DECODED_MAX+1)==COH_INVALID);
    coh_net_destroy(n);n=connected_budget(5,COH_NET_DECODED_MAX);
    CHECK(coh_net_set_decoded_budget(n,COH_NET_DECODED_MAX)==COH_STATE);
    uint32_t id=102,order=0;size_t max=0;
    for(size_t i=0;i<sizeof(large_goldens)/sizeof(large_goldens[0]);i++) {
        const LargeGolden *g=&large_goldens[i];if(g->streaming)order++;
        deliver_zip(n,(CohBytes){g->wire,g->wire_bytes},g->streaming?order:0,&id,103+i);
        CohNetOwnedMessage m,before,empty;memset(&empty,0xa5,sizeof(empty));before=empty;
        CHECK(coh_net_next_owned(n,&m)==COH_OK);assert_large(&m,g);
        CHECK(coh_net_next_owned(n,&empty)==COH_STATE&&!memcmp(&empty,&before,sizeof(empty)));
        CohNetMessage legacy;CHECK(coh_net_next(n,&legacy)==COH_STATE);
        CohNetDiagnostics d;coh_net_diagnostics(n,&d);
        if(g->raw_bytes>max)max=g->raw_bytes;
        CHECK(d.owned_retained_bytes==g->raw_bytes&&d.owned_high_water_bytes==max);
        CHECK(d.decode.failure_kind==COH_NET_DECODE_NONE&&d.decode.compressed_bytes==g->wire_bytes);
        CHECK(d.decode.declared_raw_bytes==g->raw_bytes&&d.decode.output_budget==COH_NET_DECODED_MAX);
        CHECK(d.decode.command_valid&&d.decode.normalized_command==6);
        CHECK(coh_net_owned_release(n,&m)==COH_OK&&!m.payload&&!m.payload_bytes&&!m.generation);
        coh_net_diagnostics(n,&d);CHECK(!d.owned_retained_bytes&&d.owned_high_water_bytes==max);
        CHECK(coh_net_next_owned(n,&empty)==COH_NOT_FOUND&&!memcmp(&empty,&before,sizeof(empty)));
    }
    CohNetDiagnostics d;coh_net_diagnostics(n,&d);CHECK(!d.queue_limits&&d.owned_high_water_bytes==COH_NET_DECODED_MAX);
    coh_net_destroy(n);session_cases++;
    /* Ordered dictionary consumers cannot inflate order2 before order1. */
    n=connected_budget(5,COH_NET_DECODED_MAX);id=102;
    const LargeGolden *one=&large_goldens[1],*two=&large_goldens[3];
    deliver_zip(n,(CohBytes){two->wire,two->wire_bytes},2,&id,103);
    CohNetOwnedMessage m,before;memset(&m,0xa5,sizeof(m));before=m;
    CHECK(coh_net_next_owned(n,&m)==COH_NOT_FOUND&&!memcmp(&m,&before,sizeof(m)));
    deliver_zip(n,(CohBytes){one->wire,one->wire_bytes},1,&id,104);
    CHECK(coh_net_next_owned(n,&m)==COH_OK);assert_large(&m,one);CHECK(coh_net_owned_release(n,&m)==COH_OK);
    CHECK(coh_net_next_owned(n,&m)==COH_OK);assert_large(&m,two);CHECK(coh_net_owned_release(n,&m)==COH_OK);
    coh_net_destroy(n);session_cases++;
}
static void owned_failure(CohBytes body,size_t budget,CohNetDecodeFailure why,CohStatus expected,int stream) {
    CohNet *n=connected_budget(5,budget);uint32_t id=102;
    deliver_zip(n,body,stream?1:0,&id,103);
    CohNetOwnedMessage m,before;memset(&m,0xa5,sizeof(m));before=m;
    CHECK(coh_net_next_owned(n,&m)==expected&&!memcmp(&m,&before,sizeof(m)));
    CohNetDiagnostics d;coh_net_diagnostics(n,&d);
    CHECK(coh_net_state(n)==COH_NET_FAILED&&d.decode.failure_kind==why);
    CHECK(!d.owned_retained_bytes&&!d.owned_high_water_bytes&&!d.rx_pending&&!d.tx_pending&&!d.fragment_groups);
    coh_net_destroy(n);negative++;
}
static void test_owned_failures(void) {
    const LargeGolden *g=&large_goldens[0];
    owned_failure((CohBytes){g->wire,g->wire_bytes},COH_NET_MESSAGE_MAX,COH_NET_DECODE_BUDGET,COH_LIMIT,0);
    /* Opting in never changes legacy next's accepted16KiB output contract. */
    CohNet *n=connected_budget(5,COH_NET_DECODED_MAX);uint32_t id=102;
    deliver_zip(n,(CohBytes){g->wire,g->wire_bytes},0,&id,103);
    CohNetMessage legacy,before;memset(&legacy,0xa5,sizeof(legacy));before=legacy;
    CHECK(coh_net_next(n,&legacy)==COH_LIMIT&&!memcmp(&legacy,&before,sizeof(legacy)));
    CHECK(coh_net_state(n)==COH_NET_FAILED);coh_net_destroy(n);negative++;
    uint8_t invalid[COH_NET_MESSAGE_MAX];memcpy(invalid,g->wire,g->wire_bytes);
    memset(invalid+4,0xff,4);
    n=connected_budget(5,COH_NET_DECODED_MAX);id=102;
    deliver_zip(n,(CohBytes){invalid,g->wire_bytes},0,&id,103);CohNetOwnedMessage m;
    CHECK(coh_net_next_owned(n,&m)==COH_LIMIT);CohNetDiagnostics d;coh_net_diagnostics(n,&d);
    CHECK(d.decode.declared_raw_bytes==UINT64_C(4294967299)&&d.decode.failure_kind==COH_NET_DECODE_BUDGET);
    CHECK(!d.owned_retained_bytes&&!d.owned_high_water_bytes);coh_net_destroy(n);negative++;
    memcpy(invalid,g->wire,g->wire_bytes);memset(invalid+4,0,4);
    owned_failure((CohBytes){invalid,g->wire_bytes},COH_NET_DECODED_MAX,COH_NET_DECODE_HEADER,COH_INVALID,0);
    memcpy(invalid,g->wire,g->wire_bytes);invalid[8]^=0x55;
    owned_failure((CohBytes){invalid,g->wire_bytes},COH_NET_DECODED_MAX,COH_NET_DECODE_STREAM,COH_INVALID,0);
    memcpy(invalid,g->wire,g->wire_bytes);invalid[g->wire_bytes]=0x7f;
    owned_failure((CohBytes){invalid,g->wire_bytes+1},COH_NET_DECODED_MAX,COH_NET_DECODE_STREAM,COH_INVALID,0);
    for(size_t cut=16;cut<g->wire_bytes;cut++)owned_failure((CohBytes){g->wire,cut},COH_NET_DECODED_MAX,COH_NET_DECODE_STREAM,COH_INVALID,0);
    g=&large_goldens[1];
    for(size_t cut=16;cut<g->wire_bytes;cut++)owned_failure((CohBytes){g->wire,cut},COH_NET_DECODED_MAX,COH_NET_DECODE_STREAM,COH_INVALID,1);
    /* Exact allocation failure leaves dictionary unpublished and fails closed. */
    g=&large_goldens[0];n=connected_budget(5,COH_NET_DECODED_MAX);id=102;
    deliver_zip(n,(CohBytes){g->wire,g->wire_bytes},0,&id,103);
    refuse_owned_allocation=1;CHECK(coh_net_next_owned(n,&m)==COH_LIMIT);refuse_owned_allocation=0;
    coh_net_diagnostics(n,&d);CHECK(d.decode.failure_kind==COH_NET_DECODE_ALLOCATION&&!d.owned_retained_bytes&&!d.owned_high_water_bytes);
    coh_net_destroy(n);negative++;
    /* No decoded secret-looking command word becomes a public command receipt. */
    uint8_t tiny[4]={0xef,0xbe,0xad,0xde};n=connected_budget(5,COH_NET_DECODED_MAX);id=102;
    deliver_zip(n,(CohBytes){tiny,4},0,&id,103);CHECK(coh_net_next_owned(n,&m)==COH_OK);
    coh_net_diagnostics(n,&d);CHECK(!d.decode.command_valid&&!d.decode.normalized_command);
    CHECK(coh_net_owned_release(n,&m)==COH_OK);coh_net_destroy(n);negative++;
    n=connected_budget(1,COH_NET_DECODED_MAX);CohNetPacket normalized;memset(&normalized,0,sizeof(normalized));
    normalized.id=102;normalized.compressed=1;normalized.payload_bits=32;normalized.payload[0]=11;
    uint8_t encoded[COH_PROTOCOL_FRAME_MAX];CHECK(coh_net_receive(n,frame(1,&normalized,encoded),103)==COH_OK);
    CHECK(coh_net_next_owned(n,&m)==COH_OK);coh_net_diagnostics(n,&d);
    CHECK(d.decode.command_valid&&d.decode.normalized_command==6);
    CHECK(coh_net_owned_release(n,&m)==COH_OK);coh_net_destroy(n);negative++;
    /* Cleanup invalidates all aliases; an old generation cannot release a new one. */
    for(unsigned method=0;method<5;method++) {
        n=connected_budget(5,COH_NET_DECODED_MAX);id=102;g=&large_goldens[0];
        deliver_zip(n,(CohBytes){g->wire,g->wire_bytes},0,&id,103);CHECK(coh_net_next_owned(n,&m)==COH_OK);
        CohNetOwnedMessage stale=m;
        if(method==0)coh_net_close(n);
        else if(method==1)coh_net_cancel(n);
        else if(method==2)CHECK(coh_net_disconnect(n,104)==COH_OK);
        else if(method==3){Captured captured={0};CHECK(coh_net_pump(n,30103,capture,&captured,(CohCancel){0})==COH_STATE);}
        else {coh_net_destroy(n);n=NULL;}
        if(n){coh_net_diagnostics(n,&d);CHECK(!d.owned_retained_bytes&&d.owned_high_water_bytes==g->raw_bytes);}
        CHECK(coh_net_owned_release(n,&stale)==COH_STATE&&!stale.payload&&!stale.generation);
        coh_net_destroy(n);
    }
    session_cases++;
}
static int cancelled(void *context) { return *(int*)context; }
static void test_negative_lifecycle(void) {
    CohNet *n=connected(5);int cancel=1;Captured c={0};
    CHECK(coh_net_pump(n,103,capture,&c,(CohCancel){cancelled,&cancel})==COH_CANCELLED);CHECK(coh_net_state(n)==COH_NET_CANCELLED);
    CohNetDiagnostics d;coh_net_diagnostics(n,&d);CHECK(!d.rx_pending&&!d.tx_pending&&!d.fragment_groups);coh_net_close(n);coh_net_close(n);coh_net_destroy(n);negative++;
    n=coh_net_create(NULL);CHECK(n);CHECK(coh_net_begin(n,7,0)==COH_OK);
    CHECK(coh_net_pump(n,10000,capture,&c,(CohCancel){0})==COH_STATE);CHECK(coh_net_state(n)==COH_NET_TIMED_OUT);coh_net_destroy(n);negative++;
    n=connected(5);uint8_t raw[COH_PROTOCOL_FRAME_MAX];CohNetPacket p=game(102,0,1);p.sibling_id=10;p.sibling_count=2;
    CHECK(coh_net_receive(n,frame(5,&p,raw),103)==COH_OK);CHECK(coh_net_pump(n,10103,capture,&c,(CohCancel){0})==COH_STATE);
    coh_net_diagnostics(n,&d);CHECK(d.fragment_expirations==1&&coh_net_state(n)==COH_NET_TIMED_OUT);coh_net_destroy(n);negative++;
    n=connected(5);p=game(102,0,1);p.sibling_id=10;p.sibling_count=2;p.sibling_part=0;
    CHECK(coh_net_receive(n,frame(5,&p,raw),103)==COH_OK);
    p.id=103;p.sibling_part=1;p.ordered=1;p.ordered_id=1;
    CHECK(coh_net_receive(n,frame(5,&p,raw),104)==COH_INVALID);coh_net_destroy(n);negative++;
    n=coh_net_create(NULL);CHECK(n);CHECK(coh_net_begin(n,1,0)==COH_OK);
    p=command(5,9,2,0,1);CHECK(coh_net_receive(n,frame(5,&p,raw),0)==COH_OK);CHECK(coh_net_state(n)==COH_NET_WAIT_FINAL);
    memset(&p,0,sizeof(p));p.id=10;p.payload_bits=3;p.payload[0]=7;
    CHECK(coh_net_receive(n,frame(5,&p,raw),1)==COH_INVALID);CHECK(coh_net_state(n)==COH_NET_WAIT_FINAL);coh_net_destroy(n);negative++;
    n=coh_net_create(NULL);CHECK(n);CHECK(coh_net_begin(n,1,0)==COH_OK);
    p=command(5,10,2,1,1);p.payload_bits=(p.payload_bits+7)&~7u;
    CHECK(coh_net_receive(n,frame(5,&p,raw),1)==COH_INVALID);CHECK(coh_net_state(n)==COH_NET_CONNECTING);
    p.payload_bits+=512;memset(p.payload+(p.payload_bits-512)/8,0x22,64);
    CHECK(coh_net_receive(n,frame(5,&p,raw),2)==COH_UNSUPPORTED);CHECK(coh_net_state(n)==COH_NET_ENCRYPTION_REQUIRED);coh_net_destroy(n);negative++;
    /* RX limit rejection does not acknowledge or mark the rejected reliable
     * message received; delivery can be retried after capacity is released. */
    n=connected(5);
    for(unsigned i=0;i<COH_NET_RX_MAX;i++){p=game(102+i,0,(uint8_t)i);CHECK(coh_net_receive(n,frame(5,&p,raw),103)==COH_OK);}
    p=game(118,0,99);CohBytes b=frame(5,&p,raw);CHECK(coh_net_receive(n,b,104)==COH_LIMIT);CohNetMessage m;
    CHECK(coh_net_next(n,&m)==COH_OK);CHECK(coh_net_receive(n,b,105)==COH_OK);coh_net_destroy(n);negative++;
    n=connected(5);uint8_t data[1]={0x57};
    for(unsigned i=0;i<COH_NET_TX_MAX;i++)CHECK(coh_net_queue(n,(CohBytes){data,1},8,1,0,0,103)==COH_OK);
    CHECK(coh_net_queue(n,(CohBytes){data,1},8,1,0,0,103)==COH_LIMIT);
    c.count=0;c.status=COH_IO;CHECK(coh_net_pump(n,103,capture,&c,(CohCancel){0})==COH_IO);
    coh_net_diagnostics(n,&d);CHECK(d.tx_pending==COH_NET_TX_MAX&&d.sent==2);coh_net_destroy(n);negative++;
    /* A cap violation after ACKed siblings must fail the whole link, never
     * discard ACKed bytes and leave an unrecoverable reliable message live. */
    n=connected(5);p=game(102,0,1);p.sibling_id=20;p.sibling_count=16;p.payload_bits=COH_NET_PAYLOAD_MAX*8;
    for(unsigned i=0;i<11;i++){p.id=102+i;p.sibling_part=i;CHECK(coh_net_receive(n,frame(5,&p,raw),103)==COH_OK);}
    p.id=113;p.sibling_part=11;CHECK(coh_net_receive(n,frame(5,&p,raw),104)==COH_LIMIT);CHECK(coh_net_state(n)==COH_NET_FAILED);
    coh_net_diagnostics(n,&d);CHECK(!d.fragment_groups&&!d.tx_pending&&!d.rx_pending);coh_net_destroy(n);negative++;
    /* Remote disconnect discards every gameplay queue and sends exactly one
     * close response; CLOSED cannot retransmit the old pending application. */
    n=connected(5);CHECK(coh_net_queue(n,(CohBytes){data,1},8,1,0,0,103)==COH_OK);
    p=game(102,0,5);CHECK(coh_net_receive(n,frame(5,&p,raw),103)==COH_OK);
    p=command(5,103,5,0,0);CHECK(coh_net_receive(n,frame(5,&p,raw),104)==COH_OK);CHECK(coh_net_state(n)==COH_NET_CLOSED);
    coh_net_diagnostics(n,&d);CHECK(d.tx_pending==1&&!d.rx_pending&&!d.fragment_groups);
    c.count=0;c.status=COH_OK;CHECK(coh_net_pump(n,104,capture,&c,(CohCancel){0})==COH_OK);CHECK(c.count==1);
    coh_net_diagnostics(n,&d);CHECK(!d.tx_pending);CHECK(coh_net_pump(n,10000,capture,&c,(CohCancel){0})==COH_OK);CHECK(c.count==1);
    coh_net_destroy(n);negative++;
    n=connected(5);p=command(5,102,0,0,0);p.ordered=1;p.ordered_id=1;
    CHECK(coh_net_receive(n,frame(5,&p,raw),103)==COH_UNSUPPORTED);CHECK(coh_net_state(n)==COH_NET_CONNECTED);negative++;
    memset(&p,0,sizeof(p));p.id=103;p.compressed=1;p.ordered=1;p.ordered_id=1;p.payload_bits=24*8;
    p.payload[0]=10;p.payload[4]=16;
    CHECK(coh_net_receive(n,frame(5,&p,raw),104)==COH_OK);CHECK(coh_net_next(n,&m)==COH_INVALID);CHECK(coh_net_state(n)==COH_NET_FAILED);
    coh_net_diagnostics(n,&d);CHECK(!d.tx_pending&&!d.rx_pending&&!d.fragment_groups);coh_net_destroy(n);negative++;
}
typedef struct {unsigned calls;CohStatus result;} Exchange;
static CohStatus fixed_exchange(void *context,const uint8_t peer[64],uint8_t own[64],CohBlowfish *key) {
    Exchange *e=context;e->calls++;
    for(unsigned i=0;i<64;i++){CHECK(peer[i]==i+1);own[i]=(uint8_t)(128+i);}
    if(e->result!=COH_OK)return e->result;
    uint8_t raw[16];memset(raw,0x5a,sizeof(raw));CHECK(coh_bf_init(key,raw,sizeof(raw))==0);return COH_OK;
}
static CohNetPacket encrypted_ack(unsigned ver) {
    CohNetPacket p=command(ver,100,2,1,1);
    size_t at=(p.payload_bits+7u)&~(size_t)7;
    for(unsigned i=0;i<64;i++)p.payload[at/8+i]=(uint8_t)(i+1);
    p.payload_bits=(uint32_t)at+512;p.ack_count=1;p.acks[0]=1;return p;
}
static void test_key_exchange(void) {
    for(unsigned ver=0;ver<=5;ver++) {
        CohNetConfig config=coh_net_default_config();config.version=ver;CohNet *n=coh_net_create(&config);CHECK(n);
        Exchange exchange={0,COH_OK};CHECK(coh_net_set_key_exchange(n,fixed_exchange,&exchange,1)==COH_OK);
        CHECK(coh_net_begin(n,999,0)==COH_OK);CHECK(coh_net_set_key_exchange(n,fixed_exchange,&exchange,1)==COH_STATE);
        Captured sent={0};CHECK(coh_net_pump(n,0,capture,&sent,(CohCancel){0})==COH_OK);CHECK(sent.count==1);
        uint8_t raw[COH_PROTOCOL_FRAME_MAX];CohNetPacket p=encrypted_ack(ver);CHECK(coh_net_receive(n,frame(ver,&p,raw),1)==COH_OK);
        CHECK(exchange.calls==1&&coh_net_state(n)==COH_NET_WAIT_FINAL);
        sent.count=0;CHECK(coh_net_pump(n,1,capture,&sent,(CohCancel){0})==COH_OK);CHECK(sent.count==1);
        CHECK(coh_net_frame_decode(ver,NULL,0,0,(CohBytes){sent.frames[0],sent.sizes[0]},&p)==COH_OK);
        CohProtocolBits b;uint32_t cmd,value;CHECK(coh_protocol_bits_init(&b,p.payload,sizeof(p.payload),p.payload_bits,0)==COH_OK);
        CHECK(coh_protocol_read_pack(&b,1,&cmd)==COH_OK);
        if(ver>=4){CHECK(cmd==0);CHECK(coh_protocol_read_pack(&b,1,&cmd)==COH_OK);}
        CHECK(cmd==3&&coh_protocol_read_pack(&b,1,&value)==COH_OK&&value==1);
        size_t at=(b.cursor+7)&~(size_t)7;CHECK(at+512==p.payload_bits);
        for(unsigned i=0;i<64;i++)CHECK(p.payload[at/8+i]==128+i);
        CohBlowfish key;uint8_t key_bytes[16];memset(key_bytes,0x5a,sizeof(key_bytes));CHECK(coh_bf_init(&key,key_bytes,16)==0);
        p=command(ver,101,4,0,0);p.ack_count=1;p.acks[0]=2;size_t size=0;
        CHECK(coh_net_frame_encode(ver,&key,1,&p,raw,sizeof(raw),&size)==COH_OK);
        CHECK(coh_net_receive(n,(CohBytes){raw,size},2)==COH_OK&&coh_net_state(n)==COH_NET_CONNECTED);
        uint8_t data[1]={10};CHECK(coh_net_queue(n,(CohBytes){data,1},8,1,0,0,3)==COH_OK);
        sent.count=0;CHECK(coh_net_pump(n,3,capture,&sent,(CohCancel){0})==COH_OK);CHECK(sent.count==1);
        CHECK(coh_net_frame_decode(ver,&key,1,0,(CohBytes){sent.frames[0],sent.sizes[0]},&p)==COH_OK&&p.payload_bits==8&&p.payload[0]==10);
        CHECK(coh_net_frame_decode(ver,NULL,0,0,(CohBytes){sent.frames[0],sent.sizes[0]},&p)==COH_INVALID);negative++;
        CHECK(coh_net_disconnect(n,4)==COH_OK);sent.count=0;CHECK(coh_net_pump(n,4,capture,&sent,(CohCancel){0})==COH_OK);
        CHECK(coh_net_frame_decode(ver,&key,1,0,(CohBytes){sent.frames[0],sent.sizes[0]},&p)==COH_OK);
        coh_net_destroy(n);session_cases++;
    }
    CohNet *n=coh_net_create(NULL);CHECK(n);CHECK(coh_net_set_key_exchange(n,NULL,NULL,1)==COH_OK);CHECK(coh_net_begin(n,1,0)==COH_OK);
    uint8_t raw[COH_PROTOCOL_FRAME_MAX];CohNetPacket p=command(5,100,2,0,1);
    CHECK(coh_net_receive(n,frame(5,&p,raw),1)==COH_UNSUPPORTED&&coh_net_state(n)==COH_NET_ENCRYPTION_REQUIRED);coh_net_destroy(n);negative++;
    n=coh_net_create(NULL);CHECK(n);Exchange failed={0,COH_INVALID};CHECK(coh_net_set_key_exchange(n,fixed_exchange,&failed,1)==COH_OK);
    CHECK(coh_net_begin(n,1,0)==COH_OK);p=encrypted_ack(5);CHECK(coh_net_receive(n,frame(5,&p,raw),1)==COH_INVALID&&coh_net_state(n)==COH_NET_FAILED);
    CohNetDiagnostics d;coh_net_diagnostics(n,&d);CHECK(!d.tx_pending);coh_net_destroy(n);negative++;
}
static uint32_t random_state=0x250143;
static uint32_t random32(void) { random_state^=random_state<<13;random_state^=random_state>>17;random_state^=random_state<<5;return random_state; }
static void test_fuzz(void) {
    for(unsigned i=0;i<12000;i++) {
        size_t size=20+(random32()%181)*8;uint8_t *data=malloc(size);CHECK(data);
        for(size_t j=0;j<size;j++)data[j]=(uint8_t)random32();
        uint32_t total=(uint32_t)((size-7)*8+(random32()%55));for(unsigned j=0;j<4;j++)data[j]=(uint8_t)(total>>(8*j));
        uLong digest=adler32(1,data+8,(uInt)size-8);for(unsigned j=0;j<4;j++)data[4+j]=(uint8_t)(digest>>(24-j*8));
        CohNetPacket before,after;memset(&before,0xa5,sizeof(before));after=before;
        CohStatus s=coh_net_frame_decode(random32()%6,NULL,0,0,(CohBytes){data,size},&after);
        if(s!=COH_OK)CHECK(!memcmp(&before,&after,sizeof(before)));
        free(data);negative++;
    }
}
int main(void) {
    clock_t start=clock();test_frames();test_zip();test_session();test_compressed_session();test_owned_large();test_owned_failures();test_negative_lifecycle();test_key_exchange();test_fuzz();
    CohNet *n=coh_net_create(NULL);CHECK(n);CohNetDiagnostics d;coh_net_diagnostics(n,&d);coh_net_destroy(n);
    printf("{\"checks\":%u,\"negative_cases\":%u,\"wire_cases\":%u,\"session_scenarios\":%u,\"fixed_link_bytes\":%zu,\"codec_initial_bytes\":%zu,\"cpu_test_ms\":%.3f,\"server_interoperability\":false}\n",checks,negative,wire_cases,session_cases,d.storage_bytes,d.codec_bytes,1000.0*(clock()-start)/CLOCKS_PER_SEC);return 0;
}
