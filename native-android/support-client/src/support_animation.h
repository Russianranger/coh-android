#ifndef COH_SUPPORT_ANIMATION_H
#define COH_SUPPORT_ANIMATION_H
#include "../../engine/sequencer/coh_seq_playback.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct CohSupportAnimation CohSupportAnimation;
enum { COH_SUPPORT_ANIMATION_PUNCH=0, COH_SUPPORT_ANIMATION_JUMP_SMASH=1,
       COH_SUPPORT_ANIMATION_FALLOUT=2, COH_SUPPORT_ANIMATION_CLIPS=3 };
typedef struct {
    uint64_t samples, triggers, transitions, cycles, blended_bones, last_tick;
    uint32_t kind;
    float frame;
    size_t retained_bytes, borrowed_bytes;
} CohSupportAnimationSnapshot;
/* One control/render owner. Parse the three canonical borrowed COHRIG01 spans
 * in kind order above. They must share the same authentic Huge base skeleton.
 * Caller retains every span until destroy. Allocation is only in create/destroy.
 * This is an offline mock-event adapter, not the full source player graph. */
CohStatus coh_support_animation_create(const CohBytes clips[COH_SUPPORT_ANIMATION_CLIPS],
    uint32_t actor_id, CohSupportAnimation **out);
void coh_support_animation_destroy(CohSupportAnimation *);
/* Each trigger restarts the selected clip; the latest pending trigger wins.
 * Tick may equal the next sample tick but cannot precede the last sample. */
CohStatus coh_support_animation_trigger(CohSupportAnimation *, uint32_t kind, uint64_t tick);
/* Unscaled source timestep [0,3] at 30 Hz. Strictly increasing sample ticks.
 * Neutral rig pose: root transforms/morph hierarchy composition remain caller
 * responsibilities. No GL, JNI, file IO, locks, allocations or network calls. */
CohStatus coh_support_animation_sample(CohSupportAnimation *, float timestep_frames,
    uint64_t tick, CohAnimationPose *);
const CohAnimationRig *coh_support_animation_active_rig(const CohSupportAnimation *);
CohStatus coh_support_animation_snapshot(const CohSupportAnimation *, CohSupportAnimationSnapshot *);
#ifdef __cplusplus
}
#endif
#endif
