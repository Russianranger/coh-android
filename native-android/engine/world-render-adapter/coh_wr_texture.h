#ifndef COH_WR_TEXTURE_H
#define COH_WR_TEXTURE_H
#include "../assets/coh_asset_loader.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Immutable CPU resource only, no material semantics, GL name or world permit.
 * Single off-thread owner; loader/source outlive all borrowed views.
 * Caller MUST configure opaque loader total_bytes<=loader_reservation. That
 * entire reservation is charged BEFORE acquire and its historical peak checked.
 * external_bytes reserves all other resource/source/digest/temporary/GPU memory,
 * including older textures during replacement. This is not a process RSS cap. */
typedef struct {
    size_t aggregate_limit,external_bytes,loader_reservation,max_rgba_bytes;
    uint32_t max_dimension,max_levels;
} CohWrTextureLimits;
typedef CohStatus (*CohWrTextureDigest)(void *,CohBytes,uint8_t sha256[32]);
typedef struct {
    CohAssetId asset;uint8_t sha256[32];
    CohWrTextureDigest digest;void *digest_context;
} CohWrTextureRequest;
typedef struct CohWrTextureResource CohWrTextureResource;
typedef struct {
    uint32_t asset_generation,width,height,levels,format,cached_texopt_flags;
    size_t owned_bytes,rgba_bytes,loader_reservation,external_bytes,aggregate_peak_bytes;
    uint8_t sha256[32];
} CohWrTextureReport;
/* Exact source hash precedes parsing. Protected DXT1/3/5 legacy DDS API validates
 * the complete declared chain; every declared level is retained as RGBA8.
 * Cached .texture TexOptFlags are SOURCE ONLY, not effective CLIENT sampling.
 * *out must be NULL. All failures roll back; existing output is unchanged. */
CohStatus coh_wr_texture_acquire(CohAssetLoader *,const CohWrTextureRequest *,
    const CohWrTextureLimits *,CohCancel,CohWrTextureResource **out);
CohStatus coh_wr_texture_identity(const CohWrTextureResource *,CohAssetId *);
CohStatus coh_wr_texture_report(const CohWrTextureResource *,CohWrTextureReport *);
/* Borrowed immutable view, valid until release, including after loader trim. */
CohStatus coh_wr_texture_mip(const CohWrTextureResource *,uint32_t level,
    uint32_t *width,uint32_t *height,CohBytes *rgba);
/* Retire only after all CPU borrowers and prospective GPU upload callbacks end. */
void coh_wr_texture_release(CohWrTextureResource **);
#ifdef __cplusplus
}
#endif
#endif
