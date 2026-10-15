#ifndef COH_APPEARANCE_RENDER_H
#define COH_APPEARANCE_RENDER_H
#include "coh_appearance.h"
#include "../renderer/coh_renderer.h"
#include "../../material-probe/app/src/main/cpp/coh_mesh.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Asset/control-thread conversion, not a render callback. Uses the existing
 * bounded GEO/delta readers and canonical mesh validator. No heap or GL calls.
 * Supports the same GEO versions as coh_asset_geo_open (0,2..8). Model index is
 * the already resolved authentic identity; no alternate model is selected.
 * A rigid model uses the original source socket as its one-bone fallback.
 * Multi-material ranges remain in the pinned GEO; no material is discarded. */
typedef struct {
 size_t canonical_bytes,workspace_bytes;
 uint32_t vertices,indices,bones,materials,rigid_socket_fallback;
} CohAppearanceMeshRequirements;
CohStatus coh_appearance_mesh_requirements(const CohAssetGeo *,uint32_t model_index,
 uint32_t socket_id,CohAppearanceMeshRequirements *);
/* workspace may change on failure. dst, *out and diagnostics are transactional.
 * All buffers must be disjoint from one another and from pinned GEO bytes. */
CohStatus coh_appearance_mesh_build(const CohAssetGeo *,uint32_t model_index,
 uint32_t socket_id,void *workspace,size_t workspace_bytes,uint8_t *dst,
 size_t dst_bytes,CohMeshView *out,CohAppearanceMeshRequirements *diagnostics);

/* Caller authenticates and pins source IDs/resources. This API checks exact
 * logical identity and generation agreement; it is not a digest authenticator.
 * Pose is an already composed world pose from the sequencer owner. Neutral
 * morph=NULL is admitted only when that rig is independently neutral-qualified.
 * A non-NULL morph uses the existing Huge-only qualified kernel. */
typedef struct {
 uint64_t actor_id,rig_id;
 uint32_t body_type,appearance_generation,rig_generation,pose_generation;
 const CohAnimationRig *rig;
 const CohCharacterMorph *morph;
 const CohAnimationPose *pose;
} CohAppearanceActorPose;
typedef struct {
 uint64_t actor_id,rig_id,geometry_id;
 uint32_t appearance_generation,rig_generation,body_type;
 uint32_t first_index,index_count; /* explicit source material range, multiples of 3 */
 const char *source_geometry_path,*source_model_name;
 const CohMeshView *mesh;
} CohAppearanceRenderResource;
typedef struct {
 CohRenderMaterial material;
 uint32_t surface_generation;
 const char *source_texture[2];
} CohAppearanceMaterialBinding;
typedef struct { uint32_t vertices,indices,palette_bones;size_t vertex_bytes,index_bytes; } CohAppearanceRenderDiagnostics;
/* Portable CPU-skin bridge to the existing rigid renderer, for integration and
 * comparison. This is not a GPU skinning/cache/performance qualification.
 * Caller-owned vertex/index arenas may change on failure; *out and diagnostics
 * do not. Arrays must outlive renderer flush. Each call evaluates all vertices
 * and the selected source material's index range; call once per material range.
 * Cache prepared immutable index arrays in a later optimized path.
 * Only the source-qualified COLORBLEND_DUAL material is admitted here. Original
 * effective costume colors populate const0/const1. Texture bindings must name
 * both source logical identities (including the explicit "none" marker).
 * Surface generation affects texture handles; pose generation invalidates
 * CPU-skinned geometry. A Surface loss never invalidates immutable asset IDs. */
CohStatus coh_appearance_render_part(const CohAppearanceDraw *,
 const CohAppearanceRenderResource *,const CohAppearanceActorPose *,
 const CohAppearanceMaterialBinding *,uint32_t surface_generation,
 const float model_view[16],const float projection[16],
 CohRenderVertex *vertices,size_t vertex_capacity,uint32_t *indices,
 size_t index_capacity,CohRenderDraw *out,CohAppearanceRenderDiagnostics *);
#ifdef __cplusplus
}
#endif
#endif
