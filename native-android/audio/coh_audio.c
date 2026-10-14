#include "coh_audio.h"
#include <limits.h>
#include <math.h>
#include <string.h>
#include "source_gain_golden.h"

static uint32_t u32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
int coh_audio_ratio_to_db(float ratio, int *db) {
    if (!db || !isfinite(ratio)) return COH_AUDIO_INVALID;
    float minimum=powf(10, -10000 / 2000.0);
    if (ratio<=minimum) *db=-10000;
    else {
        ratio=fminf(1.f,fmaxf(0.f,ratio));
        *db=(int)(2000.0 * log10(ratio));
        if (*db < -10000) *db=-10000;
        if (*db > 0) *db=0;
    }
    return COH_AUDIO_OK;
}
float coh_audio_db_to_ratio(int db) {
    if (db < -10000) db=-10000;
    if (db > 0) db=0;
    return powf(10, db / 2000.0);
}
int coh_audio_parse(const uint8_t *data, size_t length, CohAudioFixture *out) {
    if (!out) return COH_AUDIO_INVALID;
    memset(out,0,sizeof *out);
    if (!data || length<64 || length>(1u<<20) || memcmp(data,"COHAUD11",8)) return COH_AUDIO_INVALID;
    uint32_t version=u32(data+8), header=u32(data+12),rate=u32(data+16),channels=u32(data+20);
    uint32_t frames=u32(data+24),bytes=u32(data+28),format=u32(data+32);
    if (version!=1 || header!=64 || format!=16 || rate<8000 || rate>192000 ||
        (channels!=1 && channels!=2) || !frames || frames>rate*2 ||
        bytes!=frames*channels*2 || length!=(size_t)64+bytes) return COH_AUDIO_INVALID;
    for (unsigned i=36;i<64;i++) if (data[i]) return COH_AUDIO_INVALID;
    out->sample_rate=rate;out->channels=channels;out->frames=frames;
    out->pcm_bytes=bytes;out->pcm=data+64;
    return COH_AUDIO_OK;
}
int coh_audio_scale(const CohAudioFixture *f,uint32_t offset,uint32_t frames,int db,int16_t *out) {
    if (!f || !f->pcm || !out || !frames || offset>f->frames || frames>f->frames-offset ||
        (f->channels!=1 && f->channels!=2)) return COH_AUDIO_INVALID;
    float gain=coh_audio_db_to_ratio(db);
    for (uint32_t i=0;i<frames*f->channels;i++) {
        const uint8_t *p=f->pcm+((size_t)offset*f->channels+i)*2;
        uint16_t bits=(uint16_t)p[0] | (uint16_t)p[1]<<8;
        int sample=bits<32768 ? bits : (int)bits-65536;
        /* This PCM adapter uses nearest rounding. DirectSound's undocumented
         * sample rounding is outside the source-volume qualification. */
        long scaled=lrintf((float)sample*gain);
        if (scaled<INT16_MIN || scaled>INT16_MAX) return COH_AUDIO_INVALID;
        out[i]=(int16_t)scaled;
    }
    return COH_AUDIO_OK;
}
int coh_audio_selftest(CohAudioProof *out) {
    if (!out) return COH_AUDIO_INVALID;
    memset(out,0,sizeof *out);
    for (unsigned i=0;i<sizeof audio_golden/sizeof audio_golden[0];i++) {
        int db=0;int status=coh_audio_ratio_to_db(audio_golden[i].input,&db);
        float gain=coh_audio_db_to_ratio(audio_golden[i].db);
        double error=fabs((double)gain-audio_golden[i].gain);
        out->checks+=2;out->source_cases++;
        if (status || db!=audio_golden[i].db) out->failed++;
        if (error>out->maximum_source_error) out->maximum_source_error=error;
        /* Independent libm implementations can differ at the final float ULP. */
        if (!isfinite(gain) || error>1e-6) out->failed++;
    }
    int db=0;out->checks+=3;
    if (coh_audio_ratio_to_db(NAN,&db)!=COH_AUDIO_INVALID) out->failed++;
    if (coh_audio_ratio_to_db(INFINITY,&db)!=COH_AUDIO_INVALID) out->failed++;
    if (coh_audio_ratio_to_db(.6f,0)!=COH_AUDIO_INVALID) out->failed++;
    return out->failed ? COH_AUDIO_INVALID : COH_AUDIO_OK;
}
