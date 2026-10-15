#ifndef COH_SUPPORT_CLIENT_PHYSICS_H
#define COH_SUPPORT_CLIENT_PHYSICS_H
#include "../../engine/physics/coh_physics.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct CohSupportPhysics CohSupportPhysics;
typedef struct {
    CohPhysicsSceneInfo scene;
    CohPhysicsQueryStats query;
    CohPhysicsContact diagnostic_ground;
    uint64_t steps, refreshes, refresh_requests;
    uint32_t neighborhood_triangles;
} CohSupportPhysicsSnapshot;
/* Offline support-client only. Input is deep copied into up to three immutable
 * contiguous segments; accepted scene WALK ordering/semantics are preserved.
 * This control-thread operation requires <=8192 finite world-space triangles. */
CohStatus coh_support_physics_create(CohSupportPhysics **out,
    const CohWalkTriangle *triangles,uint32_t count,const float spawn[3],float yaw);
/* One allocation-free accepted WALK tick. COH_NOT_FOUND requests an off-tick
 * refresh; do not advance an accumulator on failure. */
CohStatus coh_support_physics_step(CohSupportPhysics *physics,uint32_t directions,float yaw);
/* Borrowed read-only state valid until the next step/clear/refresh/destroy. */
const CohWalkState *coh_support_physics_state(const CohSupportPhysics *physics);
/* Snapshot performs a bounded source-CTri ground diagnostic, without changing
 * WALK state. Ground diagnostic is separate from the accepted grounded flag. */
CohStatus coh_support_physics_snapshot(const CohSupportPhysics *physics,CohSupportPhysicsSnapshot *out);
/* Off-tick only; retains exact WALK state. Surface recreation needs no refresh. */
CohStatus coh_support_physics_refresh(CohSupportPhysics *physics);
void coh_support_physics_clear(CohSupportPhysics *physics);
void coh_support_physics_destroy(CohSupportPhysics *physics);
#ifdef __cplusplus
}
#endif
#endif
