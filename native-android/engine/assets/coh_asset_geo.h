#ifndef COH_ASSET_GEO_H
#define COH_ASSET_GEO_H
#include "coh_asset_loader.h"
#ifdef __cplusplus
extern "C" {
#endif
/* GEO v0,2..8 readers; no native pointer casts. Header workspace is caller-owned
 * and must outlive the view, source bytes must remain pinned. Model limit bounds
 * all record walks. No fixture IDs/names are part of these APIs. */
typedef struct {
    CohBytes header,payload,texture_names,model_names,material_ids;
    uint32_t version,model_count,texture_count; size_t records_offset;
} CohAssetGeo;
typedef struct {
    const char *name; uint32_t vertex_count,triangle_count,material_count;
    uint32_t material_offset,bone_info_offset,pack_count; float scale[3];
    CohPack32 packs[10];
} CohAssetGeoModel;
typedef struct { const char *texture_name; uint32_t texture_id,first_triangle,triangle_count; } CohAssetGeoMaterial;
/* Includes a bounded 64 KiB temporary inflate arena. Caller workspace may change
 * on failure; public *out remains unchanged. The arena tail is reusable after open. */
CohStatus coh_asset_geo_workspace(CohBytes,size_t *required);
CohStatus coh_asset_geo_open(CohBytes,uint8_t *workspace,size_t capacity,
                             uint32_t maximum_models,CohAssetGeo *out);
/* Original v0 bone-scale GEOs contain legitimate zero-geometry records. This
 * explicit metadata view admits those records without weakening mesh admission.
 * Material IDs, record/string/pack spans and exact header end remain validated. */
CohStatus coh_asset_geo_open_scales(CohBytes,uint8_t *,size_t,uint32_t,CohAssetGeo *);
CohStatus coh_asset_geo_scale_model(const CohAssetGeo *,uint32_t,CohAssetGeoModel *);
CohStatus coh_asset_geo_model(const CohAssetGeo *,uint32_t index,CohAssetGeoModel *);
CohStatus coh_asset_geo_material(const CohAssetGeo *,const CohAssetGeoModel *,uint32_t index,CohAssetGeoMaterial *);
/* Caller supplies decoded stream and scratch; no heap allocations. Empty packs
 * return zero bytes. Strict zlib termination rejects trailing compressed bytes. */
CohStatus coh_asset_geo_stream(const CohAssetGeo *,const CohAssetGeoModel *,uint32_t pack,
                              uint8_t *decoded,size_t capacity,void *scratch,size_t scratch_bytes,size_t *bytes);
/* Two-pass validated original delta scheme. Output unchanged on malformed data;
 * caller capacity is in scalar elements. Indices apply original +1 convention.
 * Floats retain source binary32 accumulation, no implicit UV V flip here. */
CohStatus coh_asset_delta_floats(CohBytes,uint32_t count,uint32_t stride,float *,size_t capacity);
CohStatus coh_asset_delta_indices(CohBytes,uint32_t triangles,uint32_t *,size_t capacity);
#ifdef __cplusplus
}
#endif
#endif
