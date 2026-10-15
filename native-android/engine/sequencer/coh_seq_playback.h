#ifndef COH_SEQ_PLAYBACK_H
#define COH_SEQ_PLAYBACK_H
#include "coh_sequencer.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_SEQ_PLAYBACK_MARKERS 256u
#define COH_SEQ_PLAYBACK_EVENTS (COH_SEQ_PLAYBACK_MARKERS + 1u)
#define COH_SEQ_PLAYBACK_NOINTERP (1u << 5)
/* Per-move immutable bindings. Raw rigs have been admitted by the existing
 * decoder; NULL means not loaded yet. Storage must outlive playback. */
typedef struct {
    uint32_t clip_id, rig_id;
    const CohAnimationRig *rig;
} CohSeqPoseBinding;
/* Local cue contract, not an original PlayFx/network packet implementation.
 * Sorted by move, then frame; equal-frame declaration order is preserved. */
typedef struct { uint32_t move, kind, token; float frame; } CohSeqMarker;
enum { COH_SEQ_EVENT_ENTER=1, COH_SEQ_EVENT_CYCLE=2, COH_SEQ_EVENT_MARKER=3 };
typedef struct {
    uint64_t tick;
    uint32_t actor_id, rig_id, move, clip_id, type, kind, token;
    float frame;
} CohSeqPlaybackEvent;
typedef struct {
    uint64_t samples, transitions, blended_bones, events;
    size_t retained_bytes, borrowed_rig_bytes;
} CohSeqPlaybackDiagnostics;
typedef struct {
    const CohSeqPoseBinding *bindings;
    const CohSeqMarker *markers;
    size_t binding_count, marker_count;
    uint32_t actor_id, rig_id, move, initialized;
    uint64_t tick, transition_generation;
    float frame, interpolation_frame;
    const CohAnimationRig *last_rig;
    uint8_t rotation_blend[COH_ANIMATION_BONES];
    uint8_t translation_blend[COH_ANIMATION_BONES];
    uint8_t stored_valid[COH_ANIMATION_BONES];
    CohAnimationPose last_pose;
    CohSeqPlaybackDiagnostics diagnostics;
} CohSeqPlayback;
/* Single simulation owner; no allocation, IO, GPU, locks or callbacks. */
CohStatus coh_seq_playback_init(CohSeqPlayback *, uint32_t actor, uint32_t rig,
    const CohSeqPoseBinding *, size_t binding_count,
    const CohSeqMarker *, size_t marker_count);
/* Clip/rig generations remain asset-owner controlled. Call only between ticks.
 * May add lazy clips; replacing a loaded current rig must retain hierarchy. */
CohStatus coh_seq_playback_rebind(CohSeqPlayback *, const CohSeqPoseBinding *, size_t);
/* selection comes from coh_seq_step. Supply sequencer.diagnostics.transitions
 * as transition_generation (also catches forced self reentry). timestep is
 * source TIMESTEP, NOT scaled clip advancement; tick must strictly increase.
 * Events use (previous,current] crossing, plus entry-at-or-before-current and
 * one-wrap source cycle ordering. Insufficient capacity fails transactionally,
 * writes no events/pose/state and returns COH_LIMIT: enlarge then retry.
 * Outputs must not alias playback or borrowed tables. No backlog on resume. */
CohStatus coh_seq_playback_sample(CohSeqPlayback *, const CohSeqSelection *,
    uint64_t transition_generation, float timestep_frames, uint64_t tick,
    CohCancel, CohAnimationPose *, CohSeqPlaybackEvent *, size_t event_capacity,
    size_t *event_count);
/* Bridge for deterministic mock/future game state: apply listed original state
 * bits to a copied bitset. Unlisted bits remain unchanged; no network schema. */
typedef struct { uint16_t bit; uint8_t on; } CohSeqStateUpdate;
CohStatus coh_seq_playback_state(const CohSeqBits *, const CohSeqStateUpdate *,
    size_t update_count, CohSeqBits *);
#ifdef __cplusplus
}
#endif
#endif
