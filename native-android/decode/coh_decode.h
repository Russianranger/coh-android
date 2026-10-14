#ifndef COH_NATIVE_DECODE_H
#define COH_NATIVE_DECODE_H
#include <stddef.h>
#include <stdint.h>

/* The owned COHAUD11 result feeds the accepted coh_audio_play sink unchanged.
 * Start with {0}; release every successful result. No cache/reference fallback. */
typedef struct { uint8_t *data; size_t length; } CohDecodedAudio;
typedef struct {
    int result, codec_result, opened, cleared, eos, streams;
    uint32_t sample_rate, channels, frames, pcm_bytes, pages;
    uint32_t read_callbacks, seek_callbacks, tell_callbacks, close_callbacks;
    uint32_t ov_read_calls, maximum_sample_error, different_samples;
    uint32_t compared_samples, checks, failed, rejected_inputs, repeated_decodes;
    uint64_t callback_bytes, absolute_sample_error, squared_sample_error;
    double sample_rms_error;
    int reference_compared, reference_passed, callback_limit;
} CohDecodeProof;
enum {
    COH_DECODE_OK=0, COH_DECODE_INVALID=-1, COH_DECODE_LIMIT=-2,
    COH_DECODE_CODEC=-3, COH_DECODE_MEMORY=-4, COH_DECODE_REFERENCE=-5
};
#define COH_DECODE_MAX_COMPRESSED (1024u*1024u)
#define COH_DECODE_MAX_PCM (1024u*1024u-64u)
#define COH_DECODE_MAX_SAMPLE_ERROR 1u

int coh_decode_ogg(const uint8_t *data, size_t length,
                   CohDecodedAudio *out, CohDecodeProof *proof);
void coh_decode_release(CohDecodedAudio *out);
/* Fixed signed16 maximum error <=1 LSB permits native libm rounding at a
 * quantization boundary; metadata, sample count and header remain exact. */
int coh_decode_compare_reference(const CohDecodedAudio *out,
                   const uint8_t *reference, size_t length, CohDecodeProof *proof);
int coh_decode_selftest(const uint8_t *ogg, size_t ogg_length,
                   const uint8_t *reference, size_t reference_length,
                   CohDecodeProof *proof);
#endif
