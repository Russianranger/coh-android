#include "coh_asset_audio.h"
CohStatus coh_asset_sound_decode(CohBytes bytes,CohDecodedAudio *out,CohDecodeProof *proof) {
    int r=coh_decode_ogg(bytes.data,bytes.size,out,proof);
    if(r==COH_DECODE_OK)return COH_OK;
    if(r==COH_DECODE_LIMIT||r==COH_DECODE_MEMORY)return COH_LIMIT;
    return COH_INVALID;
}
