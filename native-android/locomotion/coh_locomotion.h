#ifndef COH_LOCOMOTION_H
#define COH_LOCOMOTION_H
#include "../animation/coh_animation.h"
#include "../character/coh_character.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Bounded offline adapter over authored Ready, RunCycle and RunPost moves.
 * It is NOT the full source sequencer: complex idle variants, RunPre,
 * early-RunPre Idle_Walk_Post, combat/weapon/swim and PlayFx are excluded. */
enum { COH_LOCOMOTION_READY=0, COH_LOCOMOTION_RUN=1, COH_LOCOMOTION_POST=2,
       COH_LOCOMOTION_CLIPS=3 };
typedef struct {
    const uint8_t *bytes;
    size_t byte_count;
    CohAnimationRig rigs[COH_LOCOMOTION_CLIPS];
} CohLocomotion;
typedef struct {
    uint32_t move;
    float frame, previous_frame, move_rate_scale;
    uint32_t transitions, ready_entries, run_entries, post_entries, cycles;
} CohLocomotionState;
/* COHLOCO1 canonical envelope contains unchanged original encoded .anim keys
 * in three accepted COHRIG01 views. Storage must outlive parsed views. */
int coh_locomotion_parse(const uint8_t *,size_t,CohLocomotion *);
void coh_locomotion_init(CohLocomotionState *);
/* timestep is engine frames (seconds*30), displacement the length of actual
 * world motion this tick, and geom_y_scale the source character root Y scale.
 * Source MoveScale cap [.25,2], strict-end looping, source frame preservation.
 * Return0 success; invalid values return-1 without modifying state. */
int coh_locomotion_step(const CohLocomotion *,CohLocomotionState *,int forward,
                        float timestep_frames,float displacement,float geom_y_scale);
const CohAnimationRig *coh_locomotion_rig(const CohLocomotion *,const CohLocomotionState *);
const char *coh_locomotion_move_name(uint32_t move);
/* Apply source SmoothSprint hip-local Y correction before composing hierarchy.
 * Used only by caller sampling the raw local pose (HIPS bone0), at rate>1.05. */
float coh_locomotion_hip_y(const CohLocomotionState *,float hip_y);
/* Accepted full-character morphology and keys, plus original SmoothSprint
 * hip adjustment propagated through the already composed hierarchy. */
int coh_locomotion_sample(const CohLocomotion *,const CohLocomotionState *,
                          const CohCharacterMorph *,CohAnimationPose *);
#ifdef __cplusplus
}
#endif
#endif
