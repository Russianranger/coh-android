#ifndef COH_SEQ_ACTOR_H
#define COH_SEQ_ACTOR_H
#include "coh_seq_playback.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_SEQ_ACTOR_ROUTES COH_SEQ_PLAYBACK_MARKERS
#define COH_SEQ_SOCKET_ROOT UINT32_MAX
/* Typed local presentation requests. They are not original PlayFx commands,
 * damage/combat events, network actions or an authorization to create an FX. */
enum { COH_SEQ_CUE_NONE=0, COH_SEQ_CUE_AUDIO=1, COH_SEQ_CUE_EFFECT=2,
       COH_SEQ_CUE_ATTACHMENT=3 };
typedef struct {
    uint32_t marker_kind, marker_token, kind, resource_id, socket_bone;
} CohSeqCueRoute;
/* All tables and original raw-key bytes are immutable and caller retained.
 * Generations identify resource lifetime, not GL context lifetime. */
typedef struct {
    uint32_t actor_id, rig_id;
    uint64_t appearance_generation, rig_generation, resource_generation;
    const CohSeqGraph *graph;
    const CohSeqClip *clips;
    const CohSeqPoseBinding *poses;
    size_t move_count;
    const CohSeqMarker *markers;
    size_t marker_count;
    const CohSeqCueRoute *routes;
    size_t route_count;
} CohSeqActorResources;
typedef struct {
    CohSeqPlaybackEvent animation;
    uint64_t appearance_generation, rig_generation, resource_generation;
    uint32_t kind, resource_id, socket_bone;
    /* Rig-space rows at delivery, after recursive pose blending. Morph and
     * actor-root composition belong to the appearance/render owner. */
    float socket_rows[12];
} CohSeqActorCue;
typedef struct {
    CohSeqActorResources resources;
    CohSequencer sequencer;
    CohSeqPlayback playback;
    CohSeqSelection selection;
    uint64_t successful_ticks, cue_count;
} CohSeqActor;
typedef struct {
    uint32_t actor_id, rig_id, move, clip_id;
    uint64_t appearance_generation, rig_generation, resource_generation;
    uint64_t tick, successful_ticks, transitions, blended_bones, cue_count;
    float frame;
    size_t retained_bytes, borrowed_active_rig_bytes;
} CohSeqActorSnapshot;
/* Source graph priorities, ranges and interruption rules remain unchanged.
 * No allocation, IO, GL, locks or callbacks except input.cancel's initial poll.
 * Callers own one actor per simulation owner and iterate actors in stable order.
 * Different actors may use different authentic skeletons and clip families. */
CohStatus coh_seq_actor_init(CohSeqActor *, const CohSeqActorResources *,
    uint32_t initial_move, uint32_t seed);
/* Atomically selects, samples, composes hierarchy and stages presentation cues.
 * On any failure actor, pose, cues and count are unchanged: load a missing clip
 * or enlarge capacity, then retry the SAME tick. No animation time is consumed.
 * Output spans must not alias actor/resources/each other. Capacity can be zero.
 * Caller dispatches only successful outputs; no callbacks occur during staging.
 * Source timestep stays bounded [0,3]; discard lifecycle wall-clock backlog. */
CohStatus coh_seq_actor_step(CohSeqActor *, const CohSeqInput *, uint64_t tick,
    CohAnimationPose *, CohSeqActorCue *, size_t capacity, size_t *cue_count);
/* Between ticks only. Same actor/appearance/rig generation and graph; strictly
 * newer resource generation. Preserves current pose, clock and transition.
 * Loaded clips may be replaced only with the same active clip/topology/range.
 * Old storage is releasable once EVERY borrower has rebound. New topology or
 * morphology requires explicit actor reinitialization with a new generation. */
CohStatus coh_seq_actor_rebind(CohSeqActor *, const CohSeqActorResources *);
const CohAnimationRig *coh_seq_actor_active_rig(const CohSeqActor *);
CohStatus coh_seq_actor_snapshot(const CohSeqActor *, CohSeqActorSnapshot *);
#ifdef __cplusplus
}
#endif
#endif
