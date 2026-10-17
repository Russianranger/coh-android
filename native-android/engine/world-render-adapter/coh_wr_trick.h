#ifndef COH_WR_TRICK_H
#define COH_WR_TRICK_H
#include "coh_wr_texopt.h"
typedef struct CohWrTrickCache CohWrTrickCache;
typedef struct{size_t owned_limit,aggregate_limit,loader_reservation,external_bytes;}CohWrTrickLimits;
typedef struct{uint8_t cache_sha256[32];uint32_t historical_input_generation,count,stanim_children,autolod_children;size_t owned_bytes,aggregate_reserved_bytes,loader_reservation;}CohWrTrickReport;
typedef struct{
 CohBytes name,source_file;uint32_t ordinal,table_owner_ordinal,is_table_owner,source_age,historical_input_generation;uint8_t cache_sha256[32];
 float lod_near,lod_far,lod_nearfade,lod_farfade,lod_scale,shadow_dist,alpha_ref,alpha_ref_parser,tex_bias,nightglow[2],sway[2],sway_random[2],sway_pitch[2],sway_roll[2],scroll[2][3],tighten_up,sort_bias,water_skew,water_strength;
 uint32_t flags1,flags2,model_flags,group_flags,stanim_count,autolod_count;uint8_t rgba[4],rgba2[4];
 uint32_t numeric_group_projection,animation_binding_unresolved,dictionary_registration_executed,unresolved_client_semantics;
}CohWrTrickView;
typedef struct{float speed_scale,st_scale;CohBytes name;uint32_t flags,track_binding_unresolved;}CohWrTrickStAnim;
typedef struct{float max_error,lod_near,lod_far,lod_nearfade,lod_farfade;uint32_t flags,modelname_specified;CohBytes model_name,filename;uint32_t geometry_lod_resolution_unresolved;}CohWrTrickAutoLOD;
/* Full persisted historical TrickInfo/StAnim/AutoLOD wire owner. Requires the
 * already-qualified opaque TexOpt owner for the SAME exact cache/import label.
 * Acquires its own immutable loader pin (same loader reuses the existing blob).
 * Whole loader reservation +32KiB preparation/static +external peaks charged
 * before acquisition/allocation. external must cover TexOpt metadata and its
 * whole loader reservation and16KiB static data as well (conservative double
 * charge if shared), old
 * owners and provider/code/runtime/compiler peaks. Loader outlives owner/views;
 * TexOpt owner is needed only during admission. No eager child/runtime trees.
 * Raw source ordering/empty values/unknown bits retained; no live/material permit.
 * All failures preserve output and retire candidate pins. */
CohStatus coh_wr_trick_open(CohAssetLoader*,const CohWrTexOptCache*,CohWrTexOptDigest,void*,const CohWrTrickLimits*,CohCancel,CohWrTrickCache**);
void coh_wr_trick_release(CohWrTrickCache**);
CohStatus coh_wr_trick_report(const CohWrTrickCache*,CohWrTrickReport*);
CohStatus coh_wr_trick_find(const CohWrTrickCache*,const char*,uint32_t*);
/* All strings are borrowed byte spans, NOT NUL-terminated C strings; empty means
 * data=NULL,size=0. Every view requires owner lifetime. Child indices retain the
 * original array hierarchy/order, including multiple StAnim entries if present. */
CohStatus coh_wr_trick_view(const CohWrTrickCache*,uint32_t,CohWrTrickView*);
/* Only original numeric prefix before setStAnim and independent GROUP_VIS_TRAY
 * flag projection. Original animation tracks/setStAnim and dictionary insertion
 * are NOT performed; this never claims complete CLIENT postprocess. */
CohStatus coh_wr_trick_numeric_projection(const CohWrTrickCache*,uint32_t,CohWrTrickView*);
CohStatus coh_wr_trick_stanim(const CohWrTrickCache*,uint32_t,uint32_t,CohWrTrickStAnim*);
CohStatus coh_wr_trick_autolod(const CohWrTrickCache*,uint32_t,uint32_t,CohWrTrickAutoLOD*);
#endif
