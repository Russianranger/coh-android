#ifndef COH_WR_TEXOPT_H
#define COH_WR_TEXOPT_H
#include "../assets/coh_asset_loader.h"
#include "coh_wr_surface_states.h"
#define COH_WR_TEXOPT_LAYERS 13u
typedef enum{COH_WR_TEXOPT_OLD_BASE,COH_WR_TEXOPT_OLD_BLEND,COH_WR_TEXOPT_BASE1,COH_WR_TEXOPT_MULTIPLY1,COH_WR_TEXOPT_BUMPMAP1,COH_WR_TEXOPT_DUALCOLOR1,COH_WR_TEXOPT_MASK,COH_WR_TEXOPT_BASE2,COH_WR_TEXOPT_MULTIPLY2,COH_WR_TEXOPT_BUMPMAP2,COH_WR_TEXOPT_DUALCOLOR2,COH_WR_TEXOPT_ADDGLOW1,COH_WR_TEXOPT_CUBEMAP}CohWrTexOptLayerIndex;
typedef struct CohWrTexOptCache CohWrTexOptCache;
typedef struct CohWrTexOptRecord CohWrTexOptRecord;
typedef CohStatus(*CohWrTexOptDigest)(void*,CohBytes,uint8_t[32]);
typedef struct{size_t owned_limit,aggregate_limit,loader_reservation,external_bytes;}CohWrTexOptLimits;
typedef struct{uint32_t historical_input_generation,count;size_t owned_bytes,loader_reservation,aggregate_reserved_bytes;uint8_t cache_sha256[32];uint32_t observed_schema_crc;}CohWrTexOptCacheReport;
typedef struct{const char*name;float scale[2],scroll[2];uint32_t scroll_type;uint8_t swappable;}CohWrTexOptLayer;
typedef struct{const char*base,*blend,*bumpmap;uint32_t blend_mode;float scale[2][2],diffuse[3],ambient[3],ambient_min[3];uint8_t use_fallback;}CohWrTexOptFallbackView;
typedef struct{
 uint8_t cache_sha256[32];size_t owned_bytes,aggregate_reserved_bytes;
 uint32_t historical_input_generation,source_ordinal,table_owner_ordinal,is_table_owner,unresolved_client_semantics,original_CLIENT_postprocessed,diagnostics;
 const char*name,*source_file,*table_owner_source_file,*surface_name,*df_name;uint32_t flags,model_flags,blend_mode,surface,source_age;
 float fade[2],gloss;CohWrTexOptLayer layers[COH_WR_TEXOPT_LAYERS];
 uint8_t alpha_mask,has_rgb34,multiply1_reflect,multiply2_reflect,base_add_glow,min_add_glow,max_add_glow,add_glow_mat2,tint_glow,tint_reflection,desaturate_reflection,alpha_water;
 uint8_t rgba3[4],rgba4[4],specular_rgba1[4],specular_rgba2[4];
 float parsed_specular_exponent1,parsed_specular_exponent2,specular_exponent1,specular_exponent2,reflectivity,reflectivity_base,reflectivity_scale,reflectivity_power,mask_weight;
 float diffuse_scale[3],ambient_scale[3],diffuse_trick[3],ambient_trick[3],ambient_min[3];CohWrTexOptFallbackView fallback;
}CohWrTexOptView;
/* Exact historical CLIENT input cache ONLY, not active Basic/composite/material
 * authority. Loader configured total<=reservation; loader outlives cache. Source
 * row ordering retained, case-fold duplicates owned by highest ordinal (original
 * reverse-order nonoverwriting setup). Every raw row remains inspectable; unsafe
 * high-byte original postprocess names refuse explicitly. No rows are dropped.
 * Whole loader reservation +32KiB native stack/static +external peaks charged
 * before acquire/allocate. Digest/provider/compiler/runtime closure is external. */
CohStatus coh_wr_texopt_cache_open(CohAssetLoader*,CohAssetId,CohWrTexOptDigest,void*,const CohWrTexOptLimits*,CohCancel,CohWrTexOptCache**);
void coh_wr_texopt_cache_release(CohWrTexOptCache**);
CohStatus coh_wr_texopt_cache_report(const CohWrTexOptCache*,CohWrTexOptCacheReport*);
CohStatus coh_wr_texopt_cache_find(const CohWrTexOptCache*,const char*,uint32_t*);
/* Immutable compact single-record owner; source cache/Surface needed only during
 * prepare. Same historical import label required; fixed full-cache identities
 * bind the retained producing archive, not a current CLIENT or Map generation.
 * external_bytes must include cache owned+whole loader+Surface owned/static and
 * ALL old records/provider/runtime peaks. No render/material permission minted. */
CohStatus coh_wr_texopt_record_create(const CohWrTexOptCache*,uint32_t,const CohWrSurfaceStates*,const CohWrTexOptLimits*,CohCancel,CohWrTexOptRecord**);
void coh_wr_texopt_record_release(CohWrTexOptRecord**);
CohStatus coh_wr_texopt_record_view(const CohWrTexOptRecord*,CohWrTexOptView*);
/* Original stored source values before setupTexOpt; keeps source-defined cleanup
 * auditable. Earlier alias tokens remain in the retained exact raw cache. */
CohStatus coh_wr_texopt_record_source_view(const CohWrTexOptRecord*,CohWrTexOptView*);
#endif
