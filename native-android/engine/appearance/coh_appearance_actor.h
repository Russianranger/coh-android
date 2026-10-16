#ifndef COH_APPEARANCE_ACTOR_H
#define COH_APPEARANCE_ACTOR_H
#include "coh_appearance_render.h"
#ifdef __cplusplus
extern "C" {
#endif
/* A complete, immutable snapshot is required here, not an appearance delta.
 * Every non-clear draw must have exactly one resource with a full mesh range.
 * Multi-material meshes must first be split into independent canonical meshes
 * by their asset owner; this adapter never silently omits material ranges.
 * One draw per source socket; paired limbs remain independent source parts.
 * geometry_id identifies actor/part rendered storage, not merely a source GEO;
 * shared source meshes across actors need distinct rendered identities.
 * Wider external generations must be range-checked, never truncated to u32. */
typedef struct {
 const CohAppearanceDraw *draws;
 const CohAppearanceRenderResource *resources;
 const CohAppearanceMaterialBinding *materials;
 const uint32_t *source_material_counts;
 uint32_t count,snapshot_complete;
 CohAppearanceActorPose actor;
 uint32_t surface_generation;
 CohCancel cancel;
} CohAppearanceActorRequest;
typedef struct {
 uint32_t rendered_parts,cleared_parts,vertices,indices;
 size_t vertex_bytes,index_bytes;
} CohAppearanceActorDiagnostics;
/* Caller-owned fixed transaction workspace. No allocation, GL or callbacks
 * other than explicit cancellation; borrowed arrays survive renderer flush.
 * Public draws/count/diagnostics remain unchanged on every error; vertex/index
 * arenas and workspace can change: use staging, never a published arena.
 * Arrays and inputs must not alias.
 * Missing source geometry/materials are errors, never placeholder admission.
 * This bounds resource ownership/publication, not provenance authentication. */
typedef struct {CohRenderDraw draws[COH_APPEARANCE_DRAWS];} CohAppearanceActorWorkspace;
CohStatus coh_appearance_actor_requirements(const CohAppearanceActorRequest *,
 CohAppearanceActorDiagnostics *);
CohStatus coh_appearance_actor_render(const CohAppearanceActorRequest *,
 const float model_view[16],const float projection[16],
 CohAppearanceActorWorkspace *,CohRenderVertex *,size_t vertex_capacity,
 uint32_t *,size_t index_capacity,CohRenderDraw *,size_t draw_capacity,
 size_t *draw_count,CohAppearanceActorDiagnostics *);
#ifdef __cplusplus
}
#endif
#endif
