#ifndef COH_ENGINE_PHYSICS_H
#define COH_ENGINE_PHYSICS_H
#include "../coh_contracts.h"
#include "../../walk/coh_walk.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Additive, offline static-world adapter. No network or prediction semantics. */
#define COH_PHYSICS_MAX_SEGMENTS 1024u
#define COH_PHYSICS_MAX_TRIANGLES 262144u
typedef struct CohPhysicsScene CohPhysicsScene;
typedef struct {
    uint64_t id; uint32_t generation;
    const CohWalkTriangle *triangles; uint32_t count;
} CohPhysicsSegment;
typedef struct { uint32_t nodes, triangles, candidates; } CohPhysicsQueryStats;
typedef struct { uint32_t max_nodes, max_triangles; } CohPhysicsBudget;
typedef struct {
    uint32_t generation, segment_count, triangle_count, node_count;
    size_t owned_bytes;
} CohPhysicsSceneInfo;
/* Same flags as pinned gridcoll.h; unsupported flag combinations reject. */
enum { COH_PHYSICS_FROM_START=1u, COH_PHYSICS_FROM_CENTER=2u,
       COH_PHYSICS_HIT_ANY=4u, COH_PHYSICS_BOTH_SIDES=1u<<7,
       COH_PHYSICS_CYLINDER=1u<<8, COH_PHYSICS_FROM_START_EXACT=1u<<16 };
typedef struct {
    uint64_t segment; uint32_t generation, triangle;
    uint32_t hit, flags; float position[3], normal[3], squared_distance;
} CohPhysicsContact;
/* Single owner builds/deletes scenes outside the tick. Geometry is deep copied,
 * immutable afterward, concurrently readable. Identity must be unique per scene.
 * Generation is caller assigned, uniquely identifies immutable scene contents,
 * and is checked before every window step. Never reuse it for changed geometry. */
CohStatus coh_physics_scene_create(CohPhysicsScene **out,
    const CohPhysicsSegment *segments,uint32_t count,uint32_t generation,
    size_t byte_limit,const CohCancel *cancel);
void coh_physics_scene_destroy(CohPhysicsScene *scene);
CohStatus coh_physics_scene_info(const CohPhysicsScene *scene,CohPhysicsSceneInfo *out);
/* No allocation. Budgets are hard caps; COH_LIMIT never means no collision.
 * Output/contact is transactional, stats describes attempted work on failure.
 * Stable nearest-contact ties choose original input segment/triangle order. */
CohStatus coh_physics_query(const CohPhysicsScene *scene,const float start[3],
    const float end[3],float radius,uint32_t flags,CohPhysicsBudget budget,
    CohPhysicsContact *out,CohPhysicsQueryStats *stats);
/* Caller-owned window: initialize to zero. Prepare/refresh only off tick;
 * accepted WALK owns one bounded prepared copy. Scene may be freed after
 * preparation; step uses generation only and does not retain a scene pointer. */
typedef struct {
    CohWalkWorld world; CohWalkState state;
    uint32_t generation, ready;
    float query_min[3], query_max[3];
    uint64_t steps, refresh_requests;
    size_t owned_triangle_bytes;
} CohPhysicsWalker;
/* Refresh retains exact accepted WALK state. A changed scene generation must
 * pass fresh source ground admission; same-generation refresh supports airborne
 * state. New spawn uses the accepted source ground admission test. Extents
 * are 32..4096 source units; a 16-unit query closure is required before step. */
CohStatus coh_physics_walker_prepare(CohPhysicsWalker *walker,
    const CohPhysicsScene *scene,const float center[3],const float extents[3],
    const float spawn[3],float yaw,CohPhysicsBudget budget,const CohCancel *cancel);
/* COH_NOT_FOUND: refresh neighborhood off tick before retrying, never invent a
 * floor or advance into an unloaded region. Every successful call is one 30Hz tick. */
CohStatus coh_physics_walker_step(CohPhysicsWalker *walker,uint32_t generation,
    uint32_t directions,float yaw);
void coh_physics_walker_clear(CohPhysicsWalker *walker);
void coh_physics_walker_destroy(CohPhysicsWalker *walker);
#ifdef __cplusplus
}
#endif
#endif
