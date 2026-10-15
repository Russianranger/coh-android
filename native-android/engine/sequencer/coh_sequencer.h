#ifndef COH_ENGINE_SEQUENCER_H
#define COH_ENGINE_SEQUENCER_H
#include "../coh_contracts.h"
#include "../../animation/coh_animation.h"
#ifdef __cplusplus
extern "C" {
#endif
/* These are the original seq/TriggeredMove.h and seq.h bounds. No serialized
 * pointer is admitted; tables and strings borrow validated immutable storage. */
#define COH_SEQ_STATES 876u
#define COH_SEQ_WORDS 28u
#define COH_SEQ_IRQ_WORDS 14u
#define COH_SEQ_REQUIRES 12u
#define COH_SEQ_CYCLES 5u
#define COH_SEQ_MAX_MOVES 4096u
#define COH_SEQ_MAX_TIES 100u
#define COH_SEQ_NONE UINT32_MAX
enum {
    COH_SEQ_CYCLE=1u, COH_SEQ_FINISH_CYCLE=4u, COH_SEQ_REQ_INPUTS=8u,
    COH_SEQ_COMPLEX_CYCLE=16u, COH_SEQ_PICK_RANDOMLY=4096u
};
enum {
    COH_SEQ_CAUSE_INTERRUPT=1u, COH_SEQ_CAUSE_RELEASE=2u,
    COH_SEQ_CAUSE_ENDED=4u, COH_SEQ_CAUSE_COMPLEX=8u,
    COH_SEQ_CAUSE_CYCLE=16u
};
typedef struct { uint32_t words[COH_SEQ_WORDS]; } CohSeqBits;
typedef struct {
    const char *name;
    uint32_t flags;
    int32_t priority;
    /* Original declaration order, deduplicated; the first bit is the source
     * cached-search anchor. Sorting this array changes equal-priority choices. */
    uint16_t required[COH_SEQ_REQUIRES], required_count;
    uint32_t members[COH_SEQ_IRQ_WORDS], interrupts[COH_SEQ_IRQ_WORDS];
    uint32_t next_move; /* COH_SEQ_NONE explicitly means unimported dependency. */
    uint32_t cycle_moves[COH_SEQ_CYCLES], cycle_count;
    float scale, interpolate;
} CohSeqMove;
typedef struct { const CohSeqMove *moves; uint32_t move_count; } CohSeqGraph;
/* One actor-specific binding per move, resolved by the asset owner. Different
 * skeletons use the same graph; no male/huge/fem branch exists in the engine.
 * ready=0 prevents invented durations when source Anim omits its last frame. */
typedef struct {
    CohAssetId asset;
    uint32_t clip_id, ready;
    float first_frame, last_frame, type_scale;
} CohSeqClip;
typedef struct {
    uint64_t steps, searches, candidate_checks, transitions, cycles;
    size_t retained_bytes; /* Actor only; graph/clip bytes stay caller-owned. */
} CohSeqDiagnostics;
typedef struct {
    const CohSeqGraph *graph;
    const CohSeqClip *clips;
    uint32_t actor_id, rig_id, move, previous_move, searched_move;
    uint32_t incrementor, predict_seed;
    CohSeqBits last_state;
    float frame, previous_frame;
    CohSeqDiagnostics diagnostics;
} CohSequencer;
typedef struct {
    CohSeqBits state;
    float timestep_frames; /* source 30 Hz frames; bounded [0,3], no backlog */
    float animation_scale; /* explicit source actor-size / MoveScale result */
    uint32_t force_interrupt;
    /* Source qrand value supplied by session for PICKRANDOMLY; other source
     * complex-cycle choices use the per-actor Windows wrapping LCG seed. */
    uint32_t random_choice;
    CohCancel cancel;
} CohSeqInput;
typedef struct {
    uint32_t actor_id, rig_id, move, previous_move, clip_id, flags, cause;
    float frame, previous_frame, interpolate_frames;
} CohSeqSelection;
/* A graph is admitted once, never revalidated on the hot step path. Owners
 * must not modify graph/bindings while actors consume them. */
CohStatus coh_seq_validate(const CohSeqGraph *, const CohSeqClip *, size_t);
CohStatus coh_seq_init(CohSequencer *, const CohSeqGraph *, const CohSeqClip *,
                       size_t clip_count, uint32_t actor_id, uint32_t rig_id,
                       uint32_t initial_move, uint32_t seed);
/* Between steps, replace the complete immutable binding table after loading a
 * missing clip. Prior backing storage may be released only after all borrowing
 * actors have rebound. Current selection/frame are preserved on success. */
CohStatus coh_seq_rebind_clips(CohSequencer *, const CohSeqClip *, size_t);
CohStatus coh_seq_set_bit(CohSeqBits *, uint32_t bit, int on);
int coh_seq_requires(const CohSeqMove *, const CohSeqBits *);
int coh_seq_interrupts(const CohSeqMove *, const CohSeqMove *);
/* Single simulation-owner thread. No allocation, locks, IO, renderer calls or
 * callbacks except the optional initial cancellation poll. Actor/output remain
 * unchanged on failure. NOT_FOUND requests a missing original animation;
 * UNSUPPORTED requests an unimported next-move. Caller loads then retries. */
CohStatus coh_seq_step(CohSequencer *, const CohSeqInput *, CohSeqSelection *);
/* Thin adapter to the accepted encoded-key sampler; no new decoder or baked
 * pose data. Caller owns output; no GPU state, root-motion or blend mutation. */
CohStatus coh_seq_sample(const CohSequencer *, const CohAnimationRig *const *,
                         size_t rig_count, CohAnimationPose *);
#ifdef __cplusplus
}
#endif
#endif
