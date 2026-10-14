#include "coh_decode.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void require(int ok,const char *name) { if (!ok) { fprintf(stderr,"FAILED %s\n",name);exit(1); } }
static uint8_t *load(const char *path,size_t *length) {
    FILE *f=fopen(path,"rb");require(f!=NULL,"open fixture");
    require(fseek(f,0,SEEK_END)==0,"seek fixture");long size=ftell(f);
    require(size>0 && size<=1048576,"bounded fixture");rewind(f);
    uint8_t *data=malloc((size_t)size);require(data!=NULL,"malloc fixture");
    require(fread(data,1,(size_t)size,f)==(size_t)size,"read fixture");fclose(f);
    *length=(size_t)size;return data;
}
static size_t page_size(const uint8_t *p) {
    size_t n=27u+p[26];for (unsigned i=0;i<p[26];++i)n+=p[27+i];return n;
}
static void crc_pages(uint8_t *data,size_t length) {
    size_t at=0;
    while(at<length) {
        uint8_t *p=data+at;size_t bytes=page_size(p);uint32_t crc=0;
        memset(p+22,0,4);
        for(size_t i=0;i<bytes;++i) {
            crc^=(uint32_t)p[i]<<24;
            for(unsigned b=0;b<8;++b)crc=(crc<<1)^((crc&0x80000000u)?0x04c11db7u:0u);
        }
        p[22]=(uint8_t)crc;p[23]=(uint8_t)(crc>>8);p[24]=(uint8_t)(crc>>16);p[25]=(uint8_t)(crc>>24);at+=bytes;
    }
}
int main(int argc,char **argv) {
    if (argc!=4) return 2;
    size_t length,reference_length;uint8_t *ogg=load(argv[1],&length),*reference=load(argv[2],&reference_length);
    size_t oracle_length;uint8_t *oracle=load(argv[3],&oracle_length);
    CohDecodeProof main_proof;require(coh_decode_selftest(ogg,length,reference,reference_length,&main_proof)==0,"bundled native decode checks");
    CohDecodedAudio out={0};CohDecodeProof proof;
    unsigned prefixes=0;
    for(size_t cut=0;cut<length;++cut) {
        require(coh_decode_ogg(ogg,cut,&out,&proof)!=0 && !out.data && !out.length,"all truncated prefixes rejected");
        require(!proof.opened || proof.cleared,"truncated cleanup");++prefixes;
    }
    /* Complete CRC-valid pages reach the actual decoder, rather than testing
       only the preflight scanner. Invalid identification/signature/metadata. */
    uint8_t *bad=malloc(length);require(bad!=NULL,"mutations allocation");unsigned decoder_rejections=0;
    const size_t identity=27u+ogg[26];
    const size_t fields[]={identity,identity+1,identity+7,identity+11,identity+14,identity+15};
    for(size_t i=0;i<sizeof(fields)/sizeof(fields[0]);++i) {
        memcpy(bad,ogg,length);bad[fields[i]]^=0xff;crc_pages(bad,length);
        int result=coh_decode_ogg(bad,length,&out,&proof);
        require(result!=0,"CRC-valid hostile identification rejected");
        require(proof.eos && (!proof.opened || proof.cleared),"hostile codec path cleanup");
        require(!out.data && !out.length,"rejected output empty");++decoder_rejections;
    }
    /* Remaining valid-page payload mutations need not be rejected by Vorbis,
       but every result stays bounded and releases all decoder/output state. */
    unsigned fuzz=0;size_t second=page_size(ogg),payload=second+27u+ogg[second+26];
    for(unsigned i=0;i<160;++i) {
        memcpy(bad,ogg,length);size_t pos=payload+(size_t)i*29;
        if(pos>=length)pos=length-1;
        bad[pos]^=(uint8_t)(1u<<(i%8));crc_pages(bad,length);
        int result=coh_decode_ogg(bad,length,&out,&proof);
        require(!proof.opened || proof.cleared,"mutated cleanup");
        require(result!=0 || (out.data && out.length<=1048576 && proof.close_callbacks==1),"mutated output bounds");
        coh_decode_release(&out);++fuzz;
    }
    unsigned repeats=0;
    for(unsigned i=0;i<64;++i) {
        require(coh_decode_ogg(ogg,length,&out,&proof)==0,"repeated decode");
        require(coh_decode_compare_reference(&out,reference,reference_length,&proof)==0,"repeated PCM comparison");
        require(out.length==oracle_length+64 && !memcmp(out.data+64,oracle,oracle_length),"native PCM byte exact to unchanged callback oracle");
        require(proof.cleared && proof.close_callbacks==1,"repeated lifecycle");
        coh_decode_release(&out);require(!out.data && !out.length,"idempotent empty release");coh_decode_release(&out);++repeats;
    }
    printf("{\"passed\":true,\"checks\":%u,\"failed\":%u,\"sample_rate\":%u,\"channels\":%u,\"frames\":%u,\"pcm_bytes\":%u,\"read_callbacks\":%u,\"seek_callbacks\":%u,\"tell_callbacks\":%u,\"close_callbacks\":%u,\"ov_read_calls\":%u,\"compared_samples\":%u,\"different_samples\":%u,\"maximum_sample_error\":%u,\"sample_rms_error\":%.12g,\"all_truncated_prefixes_rejected\":%u,\"CRC_valid_decoder_rejections\":%u,\"CRC_valid_payload_mutations\":%u,\"repeated_decodes\":%u,\"fixed_maximum_allowed_sample_error\":%u}\n",main_proof.checks,main_proof.failed,main_proof.sample_rate,main_proof.channels,main_proof.frames,main_proof.pcm_bytes,main_proof.read_callbacks,main_proof.seek_callbacks,main_proof.tell_callbacks,main_proof.close_callbacks,main_proof.ov_read_calls,main_proof.compared_samples,main_proof.different_samples,main_proof.maximum_sample_error,main_proof.sample_rms_error,prefixes,decoder_rejections,fuzz,repeats,COH_DECODE_MAX_SAMPLE_ERROR);
    free(bad);free(ogg);free(reference);free(oracle);return 0;
}
