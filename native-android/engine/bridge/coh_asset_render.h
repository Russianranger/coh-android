#ifndef COH_ASSET_RENDER_H
#define COH_ASSET_RENDER_H
#include "../assets/coh_asset_geo.h"
#include "../renderer/coh_renderer.h"
#ifdef __cplusplus
extern "C" {
#endif
/* A material resolver belongs to the source map/trick frontend. It must resolve
 * original GEO names (including aliases and explicit source defaults), never
 * infer an asset by a renderer mesh ID. Returned paths must remain valid until
 * the next resolver call; the bridge copies them before source-read callbacks. */
typedef struct {
    CohRenderMaterial material; /* texture handles must be zero */
    CohAssetId textures[3]; /* 2 for MULTIPLY/DUAL, 3 for ADDGLOW */
    float uv_scale[2][2]; /* applied after exactly one source V=1-V */
} CohBridgeMaterial;
typedef CohStatus (*CohBridgeResolveMaterial)(void *,const char *geo_texture,
                                             CohBridgeMaterial *);
/* Upload consumes immutable RGBA mip zero synchronously, retains no CPU pointer.
 * Release gets context_alive=0 after loss; it must then issue no GL calls. */
typedef struct {
    CohStatus (*upload)(void *,CohAssetId,uint32_t width,uint32_t height,
                        CohBytes rgba,uint32_t surface_generation,uint32_t *handle);
    void (*release)(void *,uint32_t handle,int context_alive);
    void *context;
} CohBridgeTextureBackend;
typedef struct {
    size_t total_bytes,max_workspace_bytes,max_stream_bytes;
    uint32_t meshes,textures,max_models,max_vertices,max_triangles,max_materials;
} CohBridgeLimits;
typedef struct {
    size_t allocated_bytes,peak_allocated_bytes;
    uint32_t meshes,textures,pins,surface_generation;
    uint64_t mesh_hits,mesh_loads,texture_hits,texture_loads,uploads,evictions,rejections;
} CohBridgeStats;
typedef struct CohAssetRenderBridge CohAssetRenderBridge;
typedef struct CohBridgeMesh CohBridgeMesh;
CohBridgeLimits coh_bridge_default_limits(void);
/* Explicit new native adapter for the already qualified offline ARGB8888 DDS
 * profile: exact BGRA masks, 2D, full bounded mip envelope; mip zero only.
 * NULL rgba/zero capacity validates and returns dimensions. Outputs remain
 * unchanged on malformed/unsupported input. No name-based texture fallback. */
CohStatus coh_bridge_argb8888(CohBytes dds,uint8_t *rgba,size_t capacity,
                              uint32_t *width,uint32_t *height);
/* Loader must outlive bridge. One owner thread, including all callbacks. */
CohStatus coh_bridge_create(CohAssetLoader *,const CohBridgeLimits *,
                            const CohBridgeTextureBackend *,CohAssetRenderBridge **);
/* Live mesh pins reject destroy without changing the object. */
CohStatus coh_bridge_destroy(CohAssetRenderBridge **,int context_alive);
/* Resolver is called for each source partition. resolver_generation is an
 * explicit semantic identity; changing aliases/tricks/effective tint requires
 * a new value (or caller-applied per-instance material copies after part()).
 * Acquired mesh owns all CPU geometry/material/texture bytes independent of
 * asset cache trims. Output unchanged on failure. Rigid v0/v7 only; skinned
 * admission remains the separately accepted character/rig path. */
CohStatus coh_bridge_acquire(CohAssetRenderBridge *,CohAssetId geo,
                             const char *model_name,uint32_t resolver_generation,
                             CohBridgeResolveMaterial,void *,CohCancel,
                             const CohBridgeMesh **);
/* Explicit bounded source subset. Bit p selects original material partition p;
 * UINT32_MAX retains the existing all-partition behavior. Zero/out-of-range
 * masks refuse. The mask is part of the immutable mesh cache identity; retained
 * source vertices/indices are unchanged and output partitions keep source order.
 * Unselected material bodies are neither resolved nor acquired. */
CohStatus coh_bridge_acquire_parts(CohAssetRenderBridge *,CohAssetId geo,
                                   const char *model_name,uint32_t resolver_generation,
                                   uint32_t source_part_mask,
                                   CohBridgeResolveMaterial,void *,CohCancel,
                                   const CohBridgeMesh **);
void coh_bridge_release(CohAssetRenderBridge *,const CohBridgeMesh *);
/* Packet pointers remain immutable while mesh is pinned. One packet per source
 * material partition; positions/normals remain model local (no hidden scale or
 * matrix rewrite). No GPU calls. Texture handles are filled by prepare. */
uint32_t coh_bridge_mesh_parts(const CohBridgeMesh *);
CohStatus coh_bridge_mesh_part(const CohBridgeMesh *,uint32_t,CohRenderGeometry *,
                               CohRenderMaterial *);
const char *coh_bridge_mesh_name(const CohBridgeMesh *);
/* Explicit GL-owner phase, upload once per texture/Surface. May populate some
 * handles before failure; mesh is still valid, caller must skip that frame. */
CohStatus coh_bridge_prepare(CohAssetRenderBridge *,const CohBridgeMesh *,CohCancel);
/* Matrices are already source-composed column major and copied unchanged.
 * Caller keeps this mesh pinned until renderer flush or surface_lost returns.
 * Partial submit failure leaves previous submissions queued per renderer API. */
CohStatus coh_bridge_submit(CohAssetRenderBridge *,const CohBridgeMesh *,
                            CohRenderer *,const float model_view[16],
                            const float projection[16]);
/* First drop renderer pending spans via renderer_surface_lost, then invalidate
 * bridge handles. CPU geometry/texture bytes and mesh pins remain intact. */
CohStatus coh_bridge_surface_lost(CohAssetRenderBridge *,uint32_t generation,
                                  int context_alive);
void coh_bridge_trim(CohAssetRenderBridge *,int context_alive);
CohBridgeStats coh_bridge_stats(const CohAssetRenderBridge *);
#ifdef __cplusplus
}
#endif
#endif
