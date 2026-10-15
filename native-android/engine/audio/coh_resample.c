#include "coh_resample.h"
#include <string.h>

CohStatus coh_resample_init(CohResampler *s,uint32_t in,uint32_t out,uint32_t ch) {
    if (!s || in<8000 || in>192000 || out<8000 || out>192000 || (ch!=1&&ch!=2)) return COH_INVALID;
    memset(s,0,sizeof *s);s->input_rate=in;s->output_rate=out;s->channels=ch;s->initialized=1;return COH_OK;
}
static int16_t interpolate(int16_t a,int16_t b,uint64_t fraction,uint32_t rate) {
    int64_t value=(int64_t)a*(rate-fraction)+(int64_t)b*fraction;
    /* Symmetric nearest rounding, including negative values. */
    value=value>=0 ? (value+rate/2)/rate : -((-value+rate/2)/rate);
    return (int16_t)value;
}
CohStatus coh_resample_process(CohResampler *s,const int16_t *in,uint32_t frames,
    int16_t *out,uint32_t capacity,uint32_t *used,uint32_t *made,int end) {
    if (used) *used=0;
    if (made) *made=0;
    if (!s||!used||!made||!s->initialized||(!in&&frames)||(!out&&capacity)||(end!=0&&end!=1)) return COH_INVALID;
    if ((s->ending||s->finished)&&frames) return COH_STATE;
    if (s->input_frames+frames>(UINT64_C(1)<<40)) return COH_LIMIT;
    if (!capacity||s->finished) return COH_OK;
    while (*made<capacity) {
        uint64_t last=s->input_frames ? (s->input_frames-1)*s->output_rate : 0;
        if (s->input_frames && s->next_numerator<=last) {
            uint64_t fraction=s->next_numerator%s->output_rate;
            for (uint32_t c=0;c<s->channels;c++)
                out[(size_t)*made*s->channels+c]=fraction ? interpolate(s->previous[c],s->latest[c],fraction,s->output_rate) : s->latest[c];
            ++*made;++s->output_frames;s->next_numerator+=s->input_rate;
            continue;
        }
        if (*used<frames) {
            for (uint32_t c=0;c<s->channels;c++) {
                s->previous[c]=s->latest[c];s->latest[c]=in[(size_t)*used*s->channels+c];
            }
            ++*used;++s->input_frames;continue;
        }
        if (end) s->ending=1;
        if (!s->ending) break;
        if (s->input_frames && s->next_numerator<s->input_frames*s->output_rate) {
            for (uint32_t c=0;c<s->channels;c++) out[(size_t)*made*s->channels+c]=s->latest[c];
            ++*made;++s->output_frames;s->next_numerator+=s->input_rate;continue;
        }
        s->finished=1;break;
    }
    return COH_OK;
}
