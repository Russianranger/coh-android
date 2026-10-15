#ifndef COH_ENGINE_AUDIO_RESAMPLE_H
#define COH_ENGINE_AUDIO_RESAMPLE_H
#include "../coh_contracts.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Owner-thread streaming converter, no allocation. Linear interpolation is an
 * explicit new adapter, not a claim of original DirectSound resampler parity.
 * Integer rational phase makes output independent of input/output chunk sizes.
 * The final fractional interval holds the last sample. No antialias lowpass:
 * downsampling high-frequency content requires a later bandlimited adapter. */
typedef struct {
    uint32_t input_rate, output_rate, channels;
    uint64_t input_frames, output_frames, next_numerator;
    int16_t previous[2], latest[2];
    uint32_t initialized, ending, finished;
} CohResampler;
CohStatus coh_resample_init(CohResampler *, uint32_t input_rate,
                            uint32_t output_rate, uint32_t channels);
/* Consumes/produces partial caller spans; report counts are always initialized.
 * end=1 declares this is the last input span, but caller must resubmit any
 * unconsumed tail. Once consumed, drain with NULL/0/end=1 until finished.
 * Zero output capacity changes no state. Maximum lifetime input 2^40 frames. */
CohStatus coh_resample_process(CohResampler *, const int16_t *input,
    uint32_t input_frames, int16_t *output, uint32_t output_capacity,
    uint32_t *consumed, uint32_t *produced, int end);
#ifdef __cplusplus
}
#endif
#endif
