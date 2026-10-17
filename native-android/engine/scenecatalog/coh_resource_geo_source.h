#ifndef COH_RESOURCE_GEO_SOURCE_H
#define COH_RESOURCE_GEO_SOURCE_H
#include "../assets/coh_asset_geo.h"
/* Source-header metadata view only. Existing protected reader is tried first.
 * Narrow v8 fallback preserves ALL raw rows, explicitly admitting models whose
 * vertex/triangle/material counts are all zero. Mesh streams must be empty;
 * bounded GRID/reduction metadata is retained, never decoded/drawn implicitly.
 * Every ordinary row is validated by the protected model reader. No white-table
 * synthesis, record removal/reordering, source generation or draw authority.
 * Source/workspace remain immutable/alive while borrowed views exist. Workspace
 * may change on refusal; out/counter unchanged. Known source/workspace/control
 * aliases and overflowing endpoint spans refuse before the first write. */
CohStatus coh_resource_geo_source_open(CohBytes,uint8_t *workspace,size_t capacity,
    uint32_t maximum_models,CohAssetGeo *out,uint32_t *zero_draw_models);
/* For a view admitted above. Zero-draw metadata returns zero_draw=1 and retains
 * exact name, scale and all bounded packs; it grants no mesh/rigid resource.
 * Ordinary rows use the protected API unchanged. Outputs unchanged on failure. */
CohStatus coh_resource_geo_source_model(const CohAssetGeo *,uint32_t disk_row,
    CohAssetGeoModel *out,uint32_t *zero_draw);
#endif
