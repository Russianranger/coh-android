#ifndef COH_WR_TEX_INPUTS_H
#define COH_WR_TEX_INPUTS_H
#include "../assets/coh_asset_loader.h"
#define COH_WR_TEX_INPUTS_MAX 256u
#define COH_WR_TEX_INPUTS_PREPARATION_RESERVE 16384u
typedef struct CohWrTexInputs CohWrTexInputs;
typedef CohStatus(*CohWrTexInputsDigest)(void*,CohBytes,uint8_t[32]);
typedef struct{CohAssetId asset;uint8_t sha256[32];}CohWrTexInputPin;
typedef struct{
 const CohWrTexInputPin *textures,*raw_tricks;uint32_t texture_count,raw_trick_count,input_generation;
 CohWrTexInputsDigest digest;void*digest_context;
}CohWrTexInputsRequest;
typedef struct{size_t owned_limit,aggregate_limit,loader_reservation,external_bytes;}CohWrTexInputsLimits;
typedef struct{
 CohAssetId asset;uint8_t sha256[32];uint32_t input_ordinal,unresolved_client_semantics;
 const char *original_name,*directory,*basic_key;
 uint32_t cached_flags,width,height;float cached_fade[2];uint8_t cached_alpha;
}CohWrTexHeaderInput;
typedef struct{
 CohAssetId asset;uint8_t sha256[32];uint32_t input_ordinal,parsed;CohBytes raw;
}CohWrRawTrickInput;
typedef struct{
 uint32_t texture_count,raw_trick_count,input_generation,unresolved_client_semantics;
 size_t owned_bytes,input_bytes,aggregate_reserved_bytes,loader_reservation,preparation_reserved_bytes;
}CohWrTexInputsReport;
/* Immutable SOURCE INPUTS ONLY. Creates no BasicTexture/TexBind/composite seed,
 * no effective TexOpt/default material, and no global absence/overlay/generation
 * proof. Exact cached bodies/raw .txt files are hashed and pinned. Header names
 * follow original texFillInBind+texFixName's bounded safe subset, NOT model-table
 * last-extension projection. Case-insensitive basic-key collisions refuse rather
 * than guessing source enumeration order. Input ordering is preserved; original CLIENT enumeration order is unknown.
 * Loader configured total <=loader_reservation; loader outlives owner/views.
 * Fixed 16KiB preparation stack/control reserve is charged before allocation.
 * It covers this module frames/limits/output/control, not compiler/sanitizer,
 * loader/libc or callback stack/runtime closure; those remain external_bytes.
 * Whole loader reservation is charged before acquisition plus old/material/source/hash
 * callback peak bytes in external_bytes. Input arrays/paths are charged locally.
 * *out must be NULL. Every refusal preserves out and balances all acquired pins.
 * Source/digest context and input spans stay immutable throughout preparation. */
CohStatus coh_wr_tex_inputs_build(CohAssetLoader*,const CohWrTexInputsRequest*,const CohWrTexInputsLimits*,CohCancel,CohWrTexInputs**);
void coh_wr_tex_inputs_release(CohWrTexInputs**);
CohStatus coh_wr_tex_inputs_report(const CohWrTexInputs*,CohWrTexInputsReport*);
CohStatus coh_wr_tex_inputs_header(const CohWrTexInputs*,uint32_t,CohWrTexHeaderInput*);
/* Search ONLY the imported cached-header namespace; missing is not proof that
 * the original CLIENT table lacks the key. No composite lookup is performed. */
CohStatus coh_wr_tex_inputs_find_basic(const CohWrTexInputs*,const char*,CohWrTexHeaderInput*);
CohStatus coh_wr_tex_inputs_raw_trick(const CohWrTexInputs*,uint32_t,CohWrRawTrickInput*);
#endif
