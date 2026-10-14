#ifndef COH_LOCOMOTION_H
#define COH_LOCOMOTION_H
#include "../animation/coh_animation.h"
#include "../character/coh_character.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Bounded offline selection adapter; full random idle, combat/weapon/swim,
 * PlayFx and authoritative server sequencing remain excluded. COHLOCO1 retains
 * its qualified forward-only behavior; COHLOCO2 adds authored directional moves. */
enum { COH_LOCOMOTION_READY=0, COH_LOCOMOTION_RUN=1, COH_LOCOMOTION_POST=2,
       COH_LOCOMOTION_PRE=3, COH_LOCOMOTION_EARLY_POST=4,
       COH_LOCOMOTION_IDLE_READY=5, COH_LOCOMOTION_BACK_PRE=6,
       COH_LOCOMOTION_BACK=7, COH_LOCOMOTION_LEFT_PRE=8,
       COH_LOCOMOTION_LEFT=9, COH_LOCOMOTION_RIGHT_PRE=10,
       COH_LOCOMOTION_RIGHT=11, COH_LOCOMOTION_CLIPS=12 };
enum { COH_LOCOMOTION_FORWARD=1, COH_LOCOMOTION_BACKWARD=2,
       COH_LOCOMOTION_STEPLEFT=4, COH_LOCOMOTION_STEPRIGHT=8 };
typedef struct {
    const uint8_t *bytes;
    size_t byte_count;
    CohAnimationRig rigs[COH_LOCOMOTION_CLIPS];
    uint32_t clip_count;
} CohLocomotion;
typedef struct {
    uint32_t move;
    float frame, previous_frame, move_rate_scale;
    uint32_t transitions, ready_entries, run_entries, post_entries, cycles;
    uint32_t pre_entries, directional_entries, early_stop_entries;
    uint32_t phase_preservations, direction_switches, anim_incrementor;
    uint32_t input_mask, selection_changed;
} CohLocomotionState;
typedef struct {
    CohAnimationPose previous;
    uint32_t valid,transition_serial;
    float interpolation_frame;
    uint8_t rotation_blend[COH_ANIMATION_BONES],translation_blend[COH_ANIMATION_BONES];
} CohLocomotionBlend;
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
/* Desired local velocity flags remain set while blocked. Actual achieved
 * distance controls source MoveScale [.25,2]; it never clears a held flag.
 * Invalid/opposed masks are rejected. Source interruption groups, priorities,
 * phase retention and strict completion govern this bounded ground graph. */
int coh_locomotion_step_directional(const CohLocomotion *,CohLocomotionState *,
                        uint32_t input_mask,float timestep_frames,
                        float actual_displacement,float geom_y_scale);
const CohAnimationRig *coh_locomotion_rig(const CohLocomotion *,const CohLocomotionState *);
const char *coh_locomotion_move_name(uint32_t move);
/* Apply source SmoothSprint hip-local Y correction before composing hierarchy.
 * Used only by caller sampling the raw local pose (HIPS bone0), at rate>1.05. */
float coh_locomotion_hip_y(const CohLocomotionState *,float hip_y);
/* Accepted full-character morphology and keys, plus original SmoothSprint
 * hip adjustment propagated through the already composed hierarchy. */
int coh_locomotion_sample(const CohLocomotion *,const CohLocomotionState *,
                          const CohCharacterMorph *,CohAnimationPose *);
void coh_locomotion_blend_init(CohLocomotionBlend *);
/* Source recursive last-displayed-pose interpolation (default5, RunPost8).
 * dt is render unscaled TIMESTEP, seconds*30. Clear cache for Reset
 * or process restoration; cache is display state, never authoritative motion. */
int coh_locomotion_sample_directional(const CohLocomotion *,const CohLocomotionState *,
                           const CohCharacterMorph *,float timestep_frames,
                           CohLocomotionBlend *,CohAnimationPose *);
#ifdef __cplusplus
}
#endif
#endif
