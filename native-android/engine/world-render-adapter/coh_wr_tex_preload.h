#ifndef COH_WR_TEX_PRELOAD_H
#define COH_WR_TEX_PRELOAD_H
#include "coh_wr_texture.h"
typedef struct CohWrTexPreload CohWrTexPreload;
typedef struct{size_t owned_limit,aggregate_limit,loader_reservation,external_bytes;}CohWrTexPreloadLimits;
typedef struct{uint32_t asset_generation,source_width,source_height,width,height,levels,first_DDS_level,format,cached_texopt_flags;size_t source_header_bytes,source_payload_bytes,source_preload_offset,raw_bytes,rgba_bytes,owned_bytes,aggregate_reserved_bytes,preparation_loader_reservation;uint8_t asset_sha256[32],preload_sha256[32];}CohWrTexPreloadReport;
/* Exact TX2 low-mip SOURCE owner, not BasicTexture/namespace/material admission.
 * Requires whole asset SHA/path/generation before parsing. Raw16-byte header+
 * compressed low-mip bytes must exactly equal original GetTex last-four complete
 * DDS mip suffix. Only qualified DXT1/3/5 subset; unsupported/no-preload refuses.
 * Copies raw and RGBA lowlevels, no reencoded DDS or retained provider/loader.
 * Generic BC RGBA uses existing protected decoder, not a new original nvDXT claim.
 * Configure loader.total<=reservation; historical peak checked. Whole reservation
 * +fixed owner+32KiB own preparation/control reserved BEFORE any external poll/
 * acquire/hash; external includes old resource/provider/hash/runtime/code peaks.
 * Other owners may still pin full asset. *out=NULL; every failure unchanged and
 * candidate pins retire. Borrowed views require this owner's lifetime only.
 * No GL handles, white/default/current namespace/scene/TexWord/caps/world permit. */
CohStatus coh_wr_tex_preload_acquire(CohAssetLoader*,const CohWrTextureRequest*,const CohWrTexPreloadLimits*,CohCancel,CohWrTexPreload**);
void coh_wr_tex_preload_release(CohWrTexPreload**);
CohStatus coh_wr_tex_preload_report(const CohWrTexPreload*,CohWrTexPreloadReport*);
CohStatus coh_wr_tex_preload_identity(const CohWrTexPreload*,CohAssetId*);
CohStatus coh_wr_tex_preload_name(const CohWrTexPreload*,const char**);
CohStatus coh_wr_tex_preload_raw(const CohWrTexPreload*,CohBytes*);
CohStatus coh_wr_tex_preload_mip(const CohWrTexPreload*,uint32_t,uint32_t*,uint32_t*,CohBytes*);
#endif
