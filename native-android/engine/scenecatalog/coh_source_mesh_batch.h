#ifndef COH_SOURCE_MESH_BATCH_H
#define COH_SOURCE_MESH_BATCH_H
#include "coh_source_mesh.h"
#define COH_SOURCE_MESH_BATCH_MAX 64u
#define COH_SOURCE_MESH_BATCH_PARTS_MAX 4096u
typedef struct CohSourceMeshBatch CohSourceMeshBatch;
typedef struct {size_t aggregate_limit,retained_bytes;}CohSourceMeshBatchBudget;
typedef struct {
 uint32_t meshes,parts;
 size_t owned_bytes,mesh_owned_bytes,source_owner_bytes,loader_reservations,preparation_reserve,aggregate_reserved_bytes;
 uint32_t renderer_ready,client_materials_available,actor_available,world_authority;
}CohSourceMeshBatchReport;
/* SOURCE-only immutable ownership/lookup, not a renderer draw batch.
 * meshes is an actual mutable array of opaque prepared mesh pointers, strictly
 * increasing wholejoin ordinal. All must share actual selection/join/catalog/
 * snapshot/graph/profile identities; equal labels/hashes alone do not suffice.
 * Duplicate mesh/body/ordinal, mixed owners, descending order and caps refuse.
 * Each Body/index and mesh is charged, shared actual source dependencies once;
 * each actual loader once at maximum supplied reservation. Whole<=96MiB, <=64
 * meshes/4096 parts. All OTHER owners/provider/runtime/old batches/temporary peaks
 * belong in retained_bytes. Graph+loaders remain externally owned and MUST stay
 * live+immutable until batch retirement; retaining meshes cannot retain them.
 * Transfers ALL meshes (sets all input slots NULL) only after complete success.
 * Read-only owner preflight (<=64 squared comparisons, no I/O/allocation) runs
 * before the first cancellation callback; whole budget is admitted first.
 * Failure preserves slots/out/report. *outNULL. Serialized access; caller
 * supplies disjoint controls/opaque owners, known storage/endpoints checked.
 * Lookup/view outputs borrow batch lifetime, with source order unchanged. */
CohStatus coh_source_mesh_batch_create(CohSourceMesh **meshes,uint32_t count,
 const CohSourceMeshBatchBudget*,CohCancel,CohSourceMeshBatch**,CohSourceMeshBatchReport*);
void coh_source_mesh_batch_free(CohSourceMeshBatch*);
CohStatus coh_source_mesh_batch_report(const CohSourceMeshBatch*,CohSourceMeshBatchReport*);
/* No path aliases, guessed names, generations or renderer IDs. Binary search
 * ordinal; known-output-alias validation additionally visits<=64 mesh owners. */
CohStatus coh_source_mesh_batch_find(const CohSourceMeshBatch*,uint32_t ordinal,uint32_t*slot);
CohStatus coh_source_mesh_batch_entry(const CohSourceMeshBatch*,uint32_t slot,CohSourceMeshReport*,uint32_t*first_part);
CohStatus coh_source_mesh_batch_part(const CohSourceMeshBatch*,uint32_t slot,uint32_t part,CohSourceMeshPart*);
/* Actual borrowed entry dependencies, no references or authority added. */
CohStatus coh_source_mesh_batch_dependencies(const CohSourceMeshBatch*,uint32_t slot,CohSourceMeshDependencies*);
#endif
