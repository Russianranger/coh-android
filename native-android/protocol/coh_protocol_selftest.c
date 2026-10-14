#include "coh_protocol.h"
#include "protocol_goldens.h"
#include <stdlib.h>
#include <string.h>

#define CHECK(x) do { proof.checks++; if(!(x)) goto failed; } while(0)
static int unchanged(const void *p,size_t n,uint8_t value) {
    const uint8_t *b=p; for(size_t i=0;i<n;i++) if(b[i]!=value) return 0; return 1;
}
int coh_protocol_selftest(CohProtocolProof *out) {
    if(!out) return 1;
    CohProtocolProof proof={0}; CohBlowfish context;
    CHECK(sizeof(context)==4168);
    CHECK(coh_bf_init(&context,protocol_key,sizeof(protocol_key))==0);
    for(size_t i=0;i<sizeof(protocol_goldens)/sizeof(protocol_goldens[0]);i++) {
        const ProtocolGolden *g=protocol_goldens+i;
        for(unsigned offset=0;offset<8;offset++) {
            uint8_t buf[COH_PROTOCOL_FRAME_MAX+16]; memset(buf,0xa5,sizeof(buf)); size_t n=SIZE_MAX;
            CHECK(coh_protocol_encode(&context,g->encrypted,g->id,g->payload,g->bits,buf+offset,g->wire_bytes,&n)==0);
            CHECK(n==g->wire_bytes && memcmp(buf+offset,g->wire,n)==0);
            CHECK(unchanged(buf,offset,0xa5) && unchanged(buf+offset+n,sizeof(buf)-offset-n,0xa5));
            CohProtocolPacket packet; memset(&packet,0xa5,sizeof(packet));
            CHECK(coh_protocol_decode(&context,g->encrypted,buf+offset,n,&packet)==0);
            CHECK(packet.packet_id==g->id && packet.payload_bits==g->bits && packet.payload_bytes==(g->bits+7u)/8u);
            CHECK(memcmp(packet.payload,g->payload,packet.payload_bytes)==0);
            proof.unaligned_cases++;
        }
        proof.wire_cases++;
        for(size_t cut=0;cut<g->wire_bytes;cut++) {
            uint8_t *bytes=cut ? malloc(cut) : NULL; CohProtocolPacket packet; memset(&packet,0xa5,sizeof(packet));
            CHECK(!cut || bytes);
            if(cut) memcpy(bytes,g->wire,cut);
            int result=coh_protocol_decode(&context,g->encrypted,bytes,cut,&packet); free(bytes);
            CHECK(result!=0 && unchanged(&packet,sizeof(packet),0xa5)); proof.malformed_cases++;
        }
        for(size_t at=4;at<g->wire_bytes;at++) {
            uint8_t buf[COH_PROTOCOL_FRAME_MAX]; memcpy(buf,g->wire,g->wire_bytes); buf[at]^=1;
            CohProtocolPacket packet; memset(&packet,0xa5,sizeof(packet));
            CHECK(coh_protocol_decode(&context,g->encrypted,buf,g->wire_bytes,&packet)!=0);
            CHECK(unchanged(&packet,sizeof(packet),0xa5)); proof.malformed_cases++;
        }
        uint8_t short_buffer[COH_PROTOCOL_FRAME_MAX]; memset(short_buffer,0xa5,sizeof(short_buffer));size_t n=0x1234;
        CHECK(coh_protocol_encode(&context,g->encrypted,g->id,g->payload,g->bits,short_buffer,g->wire_bytes-1,&n)!=0);
        CHECK(n==0x1234 && unchanged(short_buffer,sizeof(short_buffer),0xa5));proof.malformed_cases++;
    }
    /* Valid independent checksum/cipher envelopes reach policy and overflow
     * rejection branches instead of failing at checksum validation. */
    for(size_t i=0;i<sizeof(protocol_negatives)/sizeof(protocol_negatives[0]);i++) {
        const ProtocolNegative *g=protocol_negatives+i;CohProtocolPacket packet;memset(&packet,0xa5,sizeof(packet));
        CHECK(coh_protocol_decode(&context,g->encrypted,g->wire,g->wire_bytes,&packet)!=0);
        CHECK(unchanged(&packet,sizeof(packet),0xa5));proof.malformed_cases++;
    }
    for(size_t i=0;i<sizeof(protocol_bit_goldens)/sizeof(protocol_bit_goldens[0]);i++) {
        const ProtocolBitGolden *g=protocol_bit_goldens+i;
        for(unsigned offset=0;offset<8;offset++) {
            uint8_t memory[24]; memset(memory,0,sizeof(memory)); CohProtocolBits writer;
            CHECK(coh_protocol_bits_init(&writer,memory+offset,16,0,1)==0);
            CHECK(coh_protocol_write_pack(&writer,g->width,g->value)==0);
            CHECK(writer.bit_length==g->bits && writer.cursor==g->bits && memcmp(memory+offset,g->bytes,(g->bits+7)/8)==0);
            CohProtocolBits reader; uint32_t value=0;
            CHECK(coh_protocol_bits_init(&reader,memory+offset,16,g->bits,0)==0);
            CHECK(coh_protocol_read_pack(&reader,g->width,&value)==0 && value==g->value && reader.cursor==g->bits);
        }
        for(size_t bits=0;bits<g->bits;bits++) {
            uint8_t memory[16]; memcpy(memory,g->bytes,16); CohProtocolBits reader; uint32_t value=0x12345678;
            CHECK(coh_protocol_bits_init(&reader,memory,sizeof(memory),bits,0)==0);
            CHECK(coh_protocol_read_pack(&reader,g->width,&value)!=0 && reader.cursor==0 && value==0x12345678);
            proof.malformed_cases++;
        }
        proof.bit_cases++;
    }
    /* Direct fields exercise all 0..32 widths at all possible bit offsets. */
    for(unsigned start=0;start<8;start++) for(unsigned width=0;width<=32;width++) {
        uint8_t memory[8]={0}; CohProtocolBits w,r; uint32_t value=UINT32_MAX;
        CHECK(coh_protocol_bits_init(&w,memory,sizeof(memory),0,1)==0);
        CHECK(coh_protocol_write(&w,start,0x55)==0 && coh_protocol_write(&w,width,0xc3a59687)==0);
        CHECK(coh_protocol_bits_init(&r,memory,sizeof(memory),w.bit_length,0)==0);r.cursor=start;
        CHECK(coh_protocol_read(&r,width,&value)==0);
        CHECK(value==(width==32 ? UINT32_C(0xc3a59687) : (UINT32_C(0xc3a59687)&((UINT32_C(1)<<width)-1))));
        proof.bit_cases++;
    }
    /* The source could wrap packed overflows; this bounded parser rejects them. */
    { uint8_t memory[8];memset(memory,0xff,sizeof(memory)); CohProtocolBits r;uint32_t value=99;
      CHECK(coh_protocol_bits_init(&r,memory,sizeof(memory),64,0)==0);
      CHECK(coh_protocol_read_pack(&r,1,&value)!=0 && r.cursor==0 && value==99);proof.malformed_cases++;
    }
    { uint8_t memory[8];memset(memory,0xa5,sizeof(memory));CohProtocolBits w;uint32_t value=99;
      CHECK(coh_protocol_bits_init(&w,memory,1,0,1)==0);
      CHECK(coh_protocol_write(&w,9,0)!=0 && w.cursor==0 && unchanged(memory,sizeof(memory),0xa5));
      CHECK(coh_protocol_write_pack(&w,1,UINT32_MAX)!=0 && w.cursor==0 && unchanged(memory,sizeof(memory),0xa5));
      CHECK(coh_protocol_write_pack(&w,0,0)!=0 && coh_protocol_write_pack(&w,33,0)!=0);
      CHECK(coh_protocol_read(&w,1,&value)!=0 && value==99);
      CHECK(coh_protocol_bits_init(&w,memory,COH_PROTOCOL_FRAME_MAX+1,0,0)!=0);
      CHECK(coh_protocol_bits_init(&w,NULL,1,0,0)!=0);proof.malformed_cases+=6;
    }
    { uint8_t bytes[COH_PROTOCOL_FRAME_MAX];CohProtocolPacket packet;const ProtocolGolden *g=protocol_goldens;
      for(unsigned mode=0;mode<2;mode++){
        memcpy(bytes,g->wire,g->wire_bytes);uint32_t bad=mode ? UINT32_MAX : 104;
        for(unsigned i=0;i<4;i++) bytes[i]=(uint8_t)(bad>>(8*i));
        memset(&packet,0xa5,sizeof(packet));
        CHECK(coh_protocol_decode(&context,g->encrypted,bytes,g->wire_bytes,&packet)!=0 && unchanged(&packet,sizeof(packet),0xa5));proof.malformed_cases++;
      }
      memset(&packet,0xa5,sizeof(packet));CHECK(coh_protocol_decode(NULL,1,g->wire,g->wire_bytes,&packet)!=0);
      CHECK(coh_protocol_decode(&context,2,g->wire,g->wire_bytes,&packet)!=0 && unchanged(&packet,sizeof(packet),0xa5));proof.malformed_cases+=2;
    }
    proof.passed=1;*out=proof;return 0;
failed:
    *out=proof;return 1;
}
