#ifndef COH_PHYSICS_NEIGHBORHOOD_H
#define COH_PHYSICS_NEIGHBORHOOD_H
#include "coh_physics_snapshot.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Copied on the simulation owner, then immutable until the loader completes.
 * owner_generation uniquely identifies this actor lifetime; do not reuse it for
 * another actor or a reset. No live walker/world/snapshot pointer is borrowed. */
typedef struct {
    uint64_t owner_generation;
    uint32_t scene_generation, ready;
    CohWalkState state;
    uint64_t steps;
} CohPhysicsNeighborhoodRequest;
typedef struct CohPhysicsPreparedNeighborhood CohPhysicsPreparedNeighborhood;
typedef struct {
    uint64_t owner_generation;
    uint32_t source_generation, target_generation, committed;
    size_t owned_triangle_bytes;
} CohPhysicsNeighborhoodInfo;
/* Simulation owner only. Bounded copy, no allocation or lock. Walker must be
 * initialized through accepted WALK. Only requests produced here are supported. */
CohStatus coh_physics_neighborhood_capture(const CohPhysicsWalker *walker,
    uint64_t owner_generation,CohPhysicsNeighborhoodRequest *out);
/* Loader only. Copies the request and prepares a separate accepted WALK cache.
 * Caller owns one live snapshot reference for this entire synchronous call.
 * Output is unchanged on failure. Missing coverage remains NOT_FOUND. */
CohStatus coh_physics_neighborhood_build(CohPhysicsPreparedNeighborhood **out,
    const CohPhysicsNeighborhoodRequest *request,const CohPhysicsSnapshot *snapshot,
    const float center[3],const float extents[3],CohPhysicsBudget budget,
    const CohCancel *cancel,CohPhysicsAdmission *admission);
/* Publish the completed handle using a caller-owned synchronized queue. Then
 * call only on the simulation owner, with the matching actor lifetime ID.
 * Same-scene movement may continue during preparation: commit preserves the
 * latest exact state, provided it remains inside the prepared safety margin.
 * Changed-scene admission is valid only for the exact captured state; a moved
 * actor returns STATE, requiring another build. No tick is consumed on failure.
 * Commit swaps ownership without allocation/free. The handle then owns the old
 * cache; return it to the loader for destroy. Never destroy it on the tick. */
CohStatus coh_physics_neighborhood_commit(CohPhysicsWalker *walker,
    uint64_t owner_generation,CohPhysicsPreparedNeighborhood *prepared);
CohStatus coh_physics_neighborhood_info(const CohPhysicsPreparedNeighborhood *,
    CohPhysicsNeighborhoodInfo *out);
/* Loader only. Safe for an uncommitted, rejected, cancelled or committed handle.
 * Never race build, commit, info, or destruction of the same handle. */
void coh_physics_neighborhood_destroy(CohPhysicsPreparedNeighborhood *prepared);
#ifdef __cplusplus
}
#endif
#endif
