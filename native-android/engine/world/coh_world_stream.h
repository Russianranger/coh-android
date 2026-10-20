#ifndef COH_WORLD_STREAM_H
#define COH_WORLD_STREAM_H
#include "../assets/coh_asset_loader.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_WORLD_MAX_NODES 512u
#define COH_WORLD_MAX_ENDPOINTS 16u
#define COH_WORLD_MAX_ASSETS 64u
#define COH_WORLD_MAX_INSTANCES 64u
#define COH_WORLD_NO_PARENT UINT32_MAX
/* Immutable COHMAP01 semantic index is generated from source Def/Group/Ref,
 * PYR, Pos, inherited TintColor and explicitly admitted asset endpoints.
 * All indices/strings are copied and validated. No hidden I/O or GL work. */
typedef struct CohWorldMap CohWorldMap;
/* COHWB001 is an app packaging envelope, not an original PIGG archive. Raw
 * original asset payloads have no format conversion. Bundle borrows immutable
 * bytes through loader destruction; entry callbacks never allocate. */
typedef struct { CohAssetId id; CohBytes bytes; } CohWorldBundleEntry;
#define COH_WORLD_MAX_MATERIALS 16u
typedef struct {
    const char *name; CohAssetId textures[2]; uint32_t family,wrap[2],cull_back;
    float uv_scale[2][2],const0[4],const1[4],alpha_ref,diffuse[4],ambient[4];
} CohWorldMaterial;
typedef struct {
    CohBytes index; uint32_t count,material_count;
    CohWorldMaterial materials[COH_WORLD_MAX_MATERIALS];
    CohWorldBundleEntry entries[COH_WORLD_MAX_ASSETS];
} CohWorldBundle;
CohStatus coh_world_bundle_open(CohBytes,CohWorldBundle *out);
/* Mount into a fresh loader. On failure destroy that loader before retry: an
 * already completed mount is indexed, while malformed bundles publish none. */
CohStatus coh_world_bundle_mount(CohWorldBundle *,CohAssetLoader *,CohCancel);
CohStatus coh_world_material(const CohWorldBundle *,const char *exact_geo_texture,CohWorldMaterial *);
typedef struct {
    uint32_t parent,endpoint; const char *name;
    float world[12],tint[6]; /* source Mat4 column-major 4x3, normalized RGB */
} CohWorldNode;
typedef struct {
    CohAssetId geometry; const char *model;
    float center[3],radius; uint32_t dependency_count;
} CohWorldEndpoint;
typedef struct { uint32_t node,endpoint; float world[12],tint[6]; } CohWorldInstance;
typedef struct {
    uint32_t count,pin_count; size_t resident_bytes;
    CohWorldInstance instances[COH_WORLD_MAX_INSTANCES];
    /* Private ownership: initialize to all zero, release before storage dies. */
    CohWorldMap *owner; CohAssetLoader *loader;
    const CohAssetBlob *pins[COH_WORLD_MAX_ASSETS];
} CohWorldSelection;
typedef struct {
    uint32_t nodes,endpoints,assets,live_selections;
    size_t allocated_bytes; uint64_t selections,cancellations,rejections;
} CohWorldStats;
CohStatus coh_world_map_create(CohBytes,CohWorldMap **out);
CohStatus coh_world_map_destroy(CohWorldMap **); /* refuses live selections */
CohWorldStats coh_world_map_stats(const CohWorldMap *);
size_t coh_world_map_allocation_bytes(void);
CohStatus coh_world_node(const CohWorldMap *,uint32_t,CohWorldNode *);
CohStatus coh_world_endpoint(const CohWorldMap *,uint32_t,CohWorldEndpoint *);
/* Version-1 indices retain all original parts. Version 2 can explicitly select
 * a bounded subset without changing the original model identity or vertices. */
CohStatus coh_world_endpoint_part_mask(const CohWorldMap *,uint32_t,uint32_t *);
CohStatus coh_world_dependency(const CohWorldMap *,uint32_t endpoint,uint32_t,CohAssetId *);
/* Explicit, bounded instance selection. Duplicate node IDs are rejected. Radius
 * helper produces IDs; caller may retain/pin a support region independently.
 * Acquire every unique dependency exactly once; summed decoded bytes are bounded
 * before acquisition. On any failure old selection/pins/output remain unchanged.
 * On success old selection is released and atomically replaced. Cache warming
 * can occur on failure; trim remains an explicit owner-thread decision. */
CohStatus coh_world_select(CohWorldMap *,CohAssetLoader *,const uint32_t *nodes,
                          uint32_t count,size_t byte_budget,CohCancel,
                          CohWorldSelection *inout);
CohStatus coh_world_query(const CohWorldMap *,const float center[3],float radius,
                         uint32_t *nodes,uint32_t capacity,uint32_t *count);
void coh_world_release(CohWorldSelection *);
#ifdef __cplusplus
}
#endif
#endif
