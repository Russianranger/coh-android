#ifndef COH_WALK_H
#define COH_WALK_H
#include "../motion/coh_motion.h"
#include <stdint.h>
enum { COH_WALK_MAX_TRIANGLES=8192, COH_WALK_NORMALTRI=1u<<11,
       COH_WALK_NOTSELECTABLE=1u<<19, COH_WALK_SLICK=1u<<20,
       COH_WALK_ICY=1u<<21, COH_WALK_BOUNCY=1u<<22 };
typedef struct { float v[3][3]; uint32_t flags; } CohWalkTriangle;
/* Immutable, bounded world-space authored triangles; cache owns its copy.
 * Zero-initialize before init; destroy before replacing a live world. */
typedef struct { void *prepared; uint32_t triangle_count, collision_count;
    float bounds_min[3], bounds_max[3]; } CohWalkWorld;
typedef struct { float traction, friction, bounce, gravity, max_speed; } CohWalkSurface;
typedef struct { float vel[3], max_speed_scale, max_jump_height;
    CohWalkSurface surf_mods[2]; uint32_t flying, no_slide_physics,
    no_ent_collision, stunned, jump_released; } CohWalkInput;
/* Fixed supported WALK subset: default grounded/air surfaces, authored CTri
 * contacts, source feet/head/wall queries, no jump/powers/entities/network. */
typedef struct {
    float vel[3], last_pos[3];
    uint32_t falling,bigfall,jumping,jump_held,jump_still_held,jump_not_landed,
        sliding,bouncing,on_poly_edge,on_surf,was_on_surf,hit_stumble,
        hit_stumble_kill_velocity_on_impact;
    int stuck,stuck_head; float move_time,surf_normal[3],jump_height,
        highest_height,heightILastTouchedTheGround; int jump_time,
        lastSurfFlags,lastGroundSurfFlags; float addedVel[3];
    uint32_t tickCounter,lastEntCollidedWith,tickOfLastEntCollision;
    int last_surf_type; float last_surf_normal[3],prev_surf_normal[3];
    int low_traction_steps_remaining; float hitStumbleTractionLoss;
    CohWalkInput input;
} CohWalkPhysics;
typedef struct {
    CohMotionState controls; float position[3]; CohWalkPhysics physics;
    uint32_t ticks, grounded_steps, blocked_steps, slide_steps, bounded_steps,
        collision_queries, triangle_tests, contact_hits, wall_hits, ground_hits;
    uint8_t grounded, blocked, sliding;
} CohWalkState;
typedef struct { uint32_t checks, failed, source_cases, collision_cases;
    float max_source_error; } CohWalkProof;
int coh_walk_world_init(CohWalkWorld *world,const CohWalkTriangle *triangles,
    uint32_t count,const float bounds_min[3],const float bounds_max[3]);
void coh_walk_world_destroy(CohWalkWorld *world);
/* Initial spawn must have actual traversable ground within source 2.5-unit
 * feet query; unsupported/no-ground scenes fail, never invent a floor. */
int coh_walk_init(CohWalkState *state,const CohWalkWorld *world,
    const float spawn[3],float yaw);
/* One 30-Hz original timestep, transactional invalid input. */
int coh_walk_step(CohWalkState *state,const CohWalkWorld *world,
    uint32_t directions,float yaw);
void coh_walk_clear(CohWalkState *state);
int coh_walk_selftest(CohWalkProof *proof);
#endif
