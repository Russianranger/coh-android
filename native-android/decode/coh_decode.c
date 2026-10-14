#define OV_EXCLUDE_STATIC_CALLBACKS
#include <vorbis/vorbisfile.h>
#include "coh_decode.h"
#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { char *mem; int curr, length; } MemFile;
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-parameter"
#include "source_callbacks.inc"
#pragma GCC diagnostic pop

typedef struct { MemFile file; CohDecodeProof *proof; uint32_t calls; } BoundedSource;
static int allow_call(BoundedSource *source) {
    if (++source->calls > 8192) { source->proof->callback_limit=1; return 0; }
    return 1;
}
static size_t bounded_read(void *dst,size_t item,size_t count,void *opaque) {
    BoundedSource *source=opaque; ++source->proof->read_callbacks;
    if (!allow_call(source)) return 0;
    size_t n=readbytes(dst,item,count,&source->file);
    source->proof->callback_bytes+=(uint64_t)n*item;
    return n;
}
static int bounded_seek(void *opaque,ogg_int64_t offset,int whence) {
    BoundedSource *source=opaque; ++source->proof->seek_callbacks;
    if (!allow_call(source)) return -1;
    return seekbytes(&source->file,offset,whence);
}
static int bounded_close(void *opaque) {
    BoundedSource *source=opaque; ++source->proof->close_callbacks;
    return closebytes(&source->file);
}
static long bounded_tell(void *opaque) {
    BoundedSource *source=opaque; ++source->proof->tell_callbacks;
    if (!allow_call(source)) return -1;
    return tellbytes(&source->file);
}
static uint32_t u32(const uint8_t *p) {
    return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static uint64_t u64(const uint8_t *p) { return (uint64_t)u32(p)|(uint64_t)u32(p+4)<<32; }
static void put32(uint8_t *p,uint32_t n) {
    p[0]=(uint8_t)n;p[1]=(uint8_t)(n>>8);p[2]=(uint8_t)(n>>16);p[3]=(uint8_t)(n>>24);
}
/* Ogg page validation is intentionally stricter than ov_open: a decoder may
 * otherwise treat a truncated tail as normal EOF. CRC includes a zeroed CRC
 * field. No resynchronization, chained stream, skipped byte or missing EOS. */
static int preflight(const uint8_t *data,size_t length,CohDecodeProof *proof,
                     uint64_t *last_granule) {
    size_t at=0; uint32_t serial=0, sequence=0; int end=0;
    while (at<length) {
        if (end || length-at<27 || memcmp(data+at,"OggS",4) || data[at+4]!=0)
            return COH_DECODE_INVALID;
        const uint8_t *p=data+at; uint8_t flags=p[5];
        size_t segments=p[26], page=27+segments;
        if ((flags & ~7u) || length-at<page) return COH_DECODE_INVALID;
        for (size_t i=0;i<segments;++i) page+=p[27+i];
        if (page>length-at || ++proof->pages>4096) return COH_DECODE_INVALID;
        if (proof->pages==1) {
            if (!(flags&2) || (flags&1) || u32(p+18)!=0) return COH_DECODE_INVALID;
            serial=u32(p+14);
        } else if ((flags&2) || u32(p+14)!=serial || u32(p+18)!=sequence)
            return COH_DECODE_INVALID;
        ++sequence;
        uint32_t crc=0;
        for (size_t i=0;i<page;++i) {
            uint8_t value=(i>=22 && i<26)?0:p[i]; crc^=(uint32_t)value<<24;
            for (unsigned b=0;b<8;++b)
                crc=(crc<<1)^((crc&0x80000000u)?0x04c11db7u:0u);
        }
        if (crc!=u32(p+22)) return COH_DECODE_INVALID;
        if (flags&4) { end=1;*last_granule=u64(p+6); }
        at+=page;
    }
    if (!end || proof->pages<3 || *last_granule>COH_DECODE_MAX_PCM/2)
        return COH_DECODE_INVALID;
    proof->eos=1;return COH_DECODE_OK;
}
void coh_decode_release(CohDecodedAudio *out) {
    if (out) { free(out->data);out->data=NULL;out->length=0; }
}
int coh_decode_ogg(const uint8_t *data,size_t length,CohDecodedAudio *out,
                   CohDecodeProof *proof) {
    CohDecodeProof local; if (!proof) proof=&local;memset(proof,0,sizeof(*proof));
    int result=COH_DECODE_INVALID; uint8_t *decoded=NULL;
    uint64_t granule=0; OggVorbis_File state;memset(&state,0,sizeof(state));
    BoundedSource source={{(char *)data,0,0},proof,0};
    if (!data || !out || out->data || out->length || !length) goto done;
    if (length>COH_DECODE_MAX_COMPRESSED || length>INT_MAX) { result=COH_DECODE_LIMIT;goto done; }
    result=preflight(data,length,proof,&granule);if (result) goto done;
    source.file.length=(int)length;
    ov_callbacks callbacks={bounded_read,bounded_seek,bounded_close,bounded_tell};
    proof->codec_result=ov_open_callbacks(&source,&state,NULL,0,callbacks);
    if (proof->codec_result<0) { result=COH_DECODE_CODEC;goto done; }
    proof->opened=1;proof->streams=(int)ov_streams(&state);
    vorbis_info *info=ov_info(&state,-1);ogg_int64_t frames=ov_pcm_total(&state,-1);
    if (proof->streams!=1 || !info || info->rate<8000 || info->rate>96000 ||
        info->channels<1 || info->channels>2 || frames<=0 || (uint64_t)frames!=granule ||
        (uint64_t)frames>COH_DECODE_MAX_PCM/(2u*(unsigned)info->channels)) {
        result=COH_DECODE_INVALID;goto done;
    }
    proof->sample_rate=(uint32_t)info->rate;proof->channels=(uint32_t)info->channels;
    proof->frames=(uint32_t)frames;proof->pcm_bytes=proof->frames*proof->channels*2u;
    decoded=calloc(1,64u+proof->pcm_bytes);if (!decoded) { result=COH_DECODE_MEMORY;goto done; }
    memcpy(decoded,"COHAUD11",8);put32(decoded+8,1);put32(decoded+12,64);
    put32(decoded+16,proof->sample_rate);put32(decoded+20,proof->channels);
    put32(decoded+24,proof->frames);put32(decoded+28,proof->pcm_bytes);put32(decoded+32,16);
    size_t wrote=0;int section=0;char buffer[4096];
    for (;;) {
        if (++proof->ov_read_calls>8192 || proof->callback_limit) { result=COH_DECODE_LIMIT;goto done; }
        /* Original oggDecode signed16 little-endian conversion contract. */
        long n=ov_read(&state,buffer,sizeof(buffer),0,2,1,&section);
        if (n<0 || section!=0) { proof->codec_result=(int)n;result=COH_DECODE_CODEC;goto done; }
        if (n==0) break;
        if ((size_t)n>proof->pcm_bytes-wrote) { result=COH_DECODE_LIMIT;goto done; }
        memcpy(decoded+64+wrote,buffer,(size_t)n);wrote+=(size_t)n;
    }
    if (wrote!=proof->pcm_bytes || ov_pcm_tell(&state)!=frames || proof->callback_limit) {
        result=COH_DECODE_INVALID;goto done;
    }
    result=COH_DECODE_OK;
done:
    if (proof->opened) { ov_clear(&state);proof->cleared=1; }
    if (result==COH_DECODE_OK) { out->data=decoded;out->length=64u+proof->pcm_bytes; }
    else free(decoded);
    proof->result=result;return result;
}
static int sample16(const uint8_t *p) {
    unsigned v=(unsigned)p[0]|(unsigned)p[1]<<8;return v<32768?(int)v:(int)v-65536;
}
int coh_decode_compare_reference(const CohDecodedAudio *out,
                   const uint8_t *reference,size_t length,CohDecodeProof *proof) {
    if (!proof) return COH_DECODE_INVALID;
    proof->reference_compared=1;proof->reference_passed=0;
    proof->maximum_sample_error=0;proof->different_samples=0;
    proof->compared_samples=0;proof->absolute_sample_error=0;proof->squared_sample_error=0;proof->sample_rms_error=0;
    if (!out || !out->data || !reference || length<64 || out->length!=length ||
        length!=64u+proof->pcm_bytes || memcmp(out->data,reference,64))
        return COH_DECODE_REFERENCE;
    for (size_t i=64;i<length;i+=2) {
        int d=sample16(out->data+i)-sample16(reference+i);
        unsigned error=(unsigned)(d<0?-d:d);++proof->compared_samples;
        proof->absolute_sample_error+=error;proof->squared_sample_error+=(uint64_t)error*error;
        proof->different_samples+=error!=0;
        if (error>proof->maximum_sample_error) proof->maximum_sample_error=error;
    }
    if (proof->compared_samples)
        proof->sample_rms_error=sqrt((double)proof->squared_sample_error/proof->compared_samples);
    proof->reference_passed=proof->maximum_sample_error<=COH_DECODE_MAX_SAMPLE_ERROR;
    return proof->reference_passed?COH_DECODE_OK:COH_DECODE_REFERENCE;
}
static void check(CohDecodeProof *p,int ok) { ++p->checks;p->failed+=!ok; }
int coh_decode_selftest(const uint8_t *ogg,size_t ogg_length,
                   const uint8_t *reference,size_t reference_length,
                   CohDecodeProof *proof) {
    if (!proof) return COH_DECODE_INVALID;
    CohDecodedAudio audio={0};int result=coh_decode_ogg(ogg,ogg_length,&audio,proof);
    check(proof,result==0);if (result) return result;
    check(proof,proof->sample_rate==44100 && proof->channels==2 && proof->frames==18168 && proof->pcm_bytes==72672);
    check(proof,proof->opened && proof->cleared && proof->close_callbacks==1 && proof->eos && proof->streams==1);
    check(proof,coh_decode_compare_reference(&audio,reference,reference_length,proof)==0);
    coh_decode_release(&audio);check(proof,!audio.data && !audio.length);
    for (unsigned i=0;i<8;++i) {
        CohDecodeProof test;
        result=coh_decode_ogg(ogg,ogg_length,&audio,&test);
        check(proof,result==0 && test.cleared && test.close_callbacks==1);
        coh_decode_release(&audio);++proof->repeated_decodes;
    }
    const size_t cuts[]={0,1,4,26,27,58,128,4096};
    for (size_t i=0;i<sizeof(cuts)/sizeof(cuts[0])+2;++i) {
        size_t n=i<sizeof(cuts)/sizeof(cuts[0])?cuts[i]:(i==8?ogg_length/2:ogg_length-1);
        CohDecodeProof test;result=coh_decode_ogg(ogg,n,&audio,&test);
        int rejected=result!=0 && !audio.data && !audio.length;
        check(proof,rejected);proof->rejected_inputs+=(unsigned)rejected;coh_decode_release(&audio);
    }
    uint8_t *bad=malloc(ogg_length);
    check(proof,bad!=NULL);
    if (bad) {
        memcpy(bad,ogg,ogg_length);bad[ogg_length/2]^=0x40;
        CohDecodeProof test;result=coh_decode_ogg(bad,ogg_length,&audio,&test);
        int rejected=result!=0 && !audio.data && !audio.length;
        check(proof,rejected);proof->rejected_inputs+=(unsigned)rejected;coh_decode_release(&audio);
        /* Reach libvorbis with CRC-valid but invalid identification magic. */
        memcpy(bad,ogg,ogg_length);size_t first_page=27u+bad[26];
        for (unsigned j=0;j<bad[26];++j) first_page+=bad[27+j];
        bad[27u+bad[26]+1u]^=0x01;
        uint32_t crc=0;memset(bad+22,0,4);
        for (size_t j=0;j<first_page;++j) {
            crc^=(uint32_t)bad[j]<<24;
            for (unsigned b=0;b<8;++b) crc=(crc<<1)^((crc&0x80000000u)?0x04c11db7u:0u);
        }
        put32(bad+22,crc);result=coh_decode_ogg(bad,ogg_length,&audio,&test);
        rejected=result!=0 && test.eos && !audio.data && !audio.length && (!test.opened || test.cleared);
        check(proof,rejected);proof->rejected_inputs+=(unsigned)rejected;coh_decode_release(&audio);free(bad);
    }
    { CohDecodeProof test;result=coh_decode_ogg(ogg,COH_DECODE_MAX_COMPRESSED+1u,&audio,&test);
      int rejected=result==COH_DECODE_LIMIT && !audio.data && !audio.length;
      check(proof,rejected);proof->rejected_inputs+=(unsigned)rejected; }
    proof->result=proof->failed?COH_DECODE_INVALID:COH_DECODE_OK;
    return proof->result;
}
