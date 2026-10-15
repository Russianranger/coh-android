#ifndef COH_ENGINE_PHYSICS_SNAPSHOT_H
#define COH_ENGINE_PHYSICS_SNAPSHOT_H
#include "coh_physics.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Optional loader admission around the unchanged static-world/WALK adapter.
 * A cell describes completeness, not the shape of a collidable floor. */
#define COH_PHYSICS_MAX_COVERAGE_CELLS 65536u
enum { COH_PHYSICS_CELL_MISSING=0, COH_PHYSICS_CELL_EMPTY=1,
       COH_PHYSICS_CELL_LOADED=2 };
typedef struct {
    uint64_t segment;
    uint32_t generation, state;
} CohPhysicsCoverageCell;
typedef struct {
    float origin_x, origin_z, cell_size, min_y, max_y;
    uint32_t columns, rows;
    /* Row-major Z then X. LOADED references an exact supplied segment;
     * EMPTY/MISSING must have zero identity. Loader attests completeness. */
    const CohPhysicsCoverageCell *cells;
} CohPhysicsCoverageGrid;
typedef struct CohPhysicsSnapshot CohPhysicsSnapshot;
typedef struct {
    CohPhysicsSceneInfo scene;
    uint32_t columns, rows, loaded_cells, empty_cells, missing_cells;
    size_t owned_bytes;
} CohPhysicsSnapshotInfo;
typedef struct { uint32_t cells_checked, missing_cells; } CohPhysicsAdmission;
/* Off tick; deep copies geometry and manifest transactionally. Limit covers
 * every retained allocation payload. Generation must never identify new data. */
CohStatus coh_physics_snapshot_create(CohPhysicsSnapshot **out,
    const CohPhysicsSegment *segments,uint32_t count,uint32_t generation,
    const CohPhysicsCoverageGrid *grid,size_t byte_limit,const CohCancel *cancel);
/* Retain only while already owning a live reference. Transfer one owned ref
 * per reader before publication; release after its last synchronous operation.
 * Do not race retain against release of the only reference. */
CohStatus coh_physics_snapshot_retain(CohPhysicsSnapshot *snapshot);
void coh_physics_snapshot_release(CohPhysicsSnapshot *snapshot);
CohStatus coh_physics_snapshot_info(const CohPhysicsSnapshot *snapshot,
    CohPhysicsSnapshotInfo *out);
/* Closed AABBs touching a cell edge require both neighbors. Missing, outside,
 * or uncovered Y returns NOT_FOUND, never a collision miss or invented floor.
 * Query budgets, original CTri behavior and stable ties remain unchanged. */
CohStatus coh_physics_snapshot_query(const CohPhysicsSnapshot *snapshot,
    const float start[3],const float end[3],float radius,uint32_t flags,
    CohPhysicsBudget budget,CohPhysicsContact *out,CohPhysicsQueryStats *stats,
    CohPhysicsAdmission *admission);
/* Off tick. Checks the whole requested neighborhood before existing source
 * WALK admission. Failed preparation retains the old world and exact state.
 * A prepared walker retains no snapshot pointer; its lifetime is independent. */
CohStatus coh_physics_snapshot_walker_prepare(CohPhysicsWalker *walker,
    const CohPhysicsSnapshot *snapshot,const float center[3],const float extents[3],
    const float spawn[3],float yaw,CohPhysicsBudget budget,const CohCancel *cancel,
    CohPhysicsAdmission *admission);
#ifdef __cplusplus
}
#endif
#endif
