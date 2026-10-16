#ifndef COH_SCENE_METADATA_H
#define COH_SCENE_METADATA_H
#include "coh_scenegraph.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Obligations for subsequent source/asset-specific adapters, never a render
 * permit. Parsing fields does not implement inherited model tricks or bounds. */
enum {
    COH_SG_META_BOUNDS_LOD=1u, COH_SG_META_GEOMETRY=2u,
    COH_SG_META_TEXTURES=4u, COH_SG_META_COMPOSITE=8u,
    COH_SG_META_PROPERTIES=16u, COH_SG_META_TYPE=32u,
    COH_SG_META_LIGHTING=64u, COH_SG_META_FOG=128u,
    COH_SG_META_CUBEMAP=256u, COH_SG_META_SOUND=512u,
    COH_SG_META_VOLUME=1024u, COH_SG_META_BEACON=2048u,
    COH_SG_META_VISIBILITY=4096u, COH_SG_META_MODEL_TRICKS=8192u
};
typedef struct {
    uint32_t scene_generation,asset_generation,file,slot,mod_time,in_use;
    uint32_t lod_present,children_present,tricks_present;
    float lod_scale,lod_near,lod_far,lod_nearfade,lod_farfade;
    uint32_t lod_fadenode,parent_fade,child_parent_fade,no_fog_clip,no_coll;
    uint32_t open_tracker,child_light,child_ambient,child_volume,child_beacon,child_no_fog_clip;
    float sound_radius,shadow_dist;
    char type_name[COH_REP_NAME_MAX];
    uint32_t lib_ungroupable,has_light,has_ambient,has_cubemap;
    float light_radius;uint8_t color[2][4];
    uint32_t cubemap_generation_size,cubemap_capture_size;
    float cubemap_blur_angle,cubemap_capture_time;
    uint32_t has_sound,sound_volume,sound_exclude;
    char sound_name[COH_REP_NAME_MAX],sound_script[COH_REP_NAME_MAX];float sound_ramp;
    uint32_t has_fog;float fog_near,fog_far,fog_radius,fog_speed;
    uint32_t has_volume;float box_scale[3];
    uint32_t has_beacon;char beacon_name[COH_REP_NAME_MAX];float beacon_radius;
    uint32_t has_tint_color,has_tex,has_alpha,has_properties;
    char textures[2][COH_REP_NAME_MAX];float alpha;
    uint32_t property_count,swap_count,has_geometry,hide_for_gameplay;
    char geometry[COH_REP_NAME_MAX];
    uint32_t unresolved_requirements;
    /* Borrowed immutable property span: valid only while owning graph remains
     * alive. Use property_begin/next; no render-thread parsing/allocation. */
    CohRepReader property_span;
} CohSgMetadata;
typedef struct {CohRepReader reader;uint32_t remaining;} CohSgPropertyCursor;
typedef struct {char name[64],value[COH_GROUPS_VALUE_MAX];uint32_t type;} CohSgProperty;
/* Input must be an immutable validated graph owned by the caller.
 * Decode the complete retained original definition body; exact consumption,
 * identity, finite numbers and explicit texture/geometry agreement required.
 * Output unchanged on error, no allocation/callback. Success preserves raw
 * receiveDef field conventions before setClientFlags/getGeo/bounds fixups.
 * No source asset generation, model/material or live renderer is authorized. */
CohStatus coh_scenegraph_metadata(const CohSceneGraph *,uint32_t index,CohSgMetadata *);
CohStatus coh_scenegraph_property_begin(const CohSgMetadata *,CohSgPropertyCursor *);
/* Sequential iteration keeps caller output/cursor unchanged on failure; returns
 * COH_NOT_FOUND at the exact validated end. Property order/duplicates retained,
 * not interpreted as the original stash table's replacement semantics. */
CohStatus coh_scenegraph_property_next(CohSgPropertyCursor *,CohSgProperty *);
#ifdef __cplusplus
}
#endif
#endif
