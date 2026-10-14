#ifndef COH_MOTION_H
#define COH_MOTION_H
#include <stdint.h>
/* Same ordinal direction IDs as pinned Common/cmdparse/cmdcommon.h. */
enum { COH_MOTION_FORWARD=1u, COH_MOTION_BACKWARD=2u,
       COH_MOTION_LEFT=4u, COH_MOTION_RIGHT=8u };
/* Named source states encoded locally, not original sequencer bit indices. */
enum { COH_MOTION_STATE_FORWARD=1u, COH_MOTION_STATE_BACKWARD=2u,
       COH_MOTION_STATE_STEPLEFT=4u, COH_MOTION_STATE_STEPRIGHT=8u };
typedef struct {
    float position[3], origin[3], local_input[3], world_input[3];
    float control_yaw, motion_yaw, body_yaw, move_time, radius;
    uint32_t held_ms[6], start_ms[6], clock_ms, ticks;
    uint32_t held, source_state_bits, stopped_steps, bounded_steps;
    uint8_t use_now, affected_last_frame;
} CohMotionState;
typedef struct {
    uint32_t checks, failed, source_cases, adapter_cases;
    float max_source_error;
} CohMotionProof;
/* Horizontal offline source NOCOLL path. No WALK/collision/server prediction.
 * yaw is the source control/body yaw in radians (-pi..pi); source camera yaw
 * is control yaw + pi. Source direction inputs are binary, already mapped by
 * the authentic input kernel. Radius is an explicit X/Z safety square in source
 * units, 1..8192, relative to spawn; it is not authored-world collision.
 * Invalid input is transactional: state bytes remain unchanged. */
int coh_motion_init(CohMotionState *state, const float spawn[3], float yaw, float radius);
/* Exactly one original physics timestep (1/30 second); no background backlog.
 * NOCOLL has the original accelerating debug speed, not normal WALK speed. */
int coh_motion_step(CohMotionState *state, uint32_t directions, float control_yaw);
/* Clear latched controls and accumulated speed on focus loss, retain pose. */
void coh_motion_clear(CohMotionState *state);
int coh_motion_selftest(CohMotionProof *proof);
#endif
