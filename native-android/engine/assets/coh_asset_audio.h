#ifndef COH_ASSET_AUDIO_H
#define COH_ASSET_AUDIO_H
#include "coh_asset_loader.h"
#include "../../decode/coh_decode.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Optional adapter, compiled only with the existing qualified native decoder.
 * Call off the audio thread. Input is borrowed for the call; *out must start at
 * {0}. Successful PCM belongs to caller; use coh_decode_release(out).
 * Decoder limits/accounting are independent of the loader's cache budget.
 * No implicit resampling, streaming, codec fallback or fixture substitution. */
CohStatus coh_asset_sound_decode(CohBytes,CohDecodedAudio *,CohDecodeProof *);
#ifdef __cplusplus
}
#endif
#endif
