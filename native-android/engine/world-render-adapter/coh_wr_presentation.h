#ifndef COH_WR_PRESENTATION_H
#define COH_WR_PRESENTATION_H
#include "coh_world_render.h"
#ifdef __cplusplus
extern "C" {
#endif

typedef struct CohWrPresentation CohWrPresentation;
typedef struct CohWrPreparedFrame CohWrPreparedFrame;
/* One immutable resource-owner lease per prepared frame, including its exact
 * old/new GPU Surface lifetimes. hold/drop run on the control thread; resolve
 * runs on the GL owner, never decodes/uploads/allocates. A missing exact resource
 * returns refusal. Callbacks/context outlive the lease. Actual resource storage,
 * provider/driver overhead and renderer arenas are reserved externally once.
 * These operations preserve ownership; they do not establish source authority. */
typedef struct {
    void *context;
    CohStatus (*hold)(void *);
    void (*drop)(void *);
    CohWrTextureFn resolve;
} CohWrPresentationResources;
typedef struct {
    uint64_t publication, snapshot, transaction;
    CohWrSource source;
    uint32_t surface_generation;
    size_t draws, batches;
    CohStatus candidate_status;
    uint32_t adopted, fallback;
} CohWrPresentationResult;

/* Production consumes ONLY existing immutable coh_wr_prepare results. No
 * receipt/authority minting, ACK or network completion exists here. Fixture
 * owners permanently refuse production snapshots, and production owners refuse
 * fixture snapshots. The immutable config MUST match the exclusively owned
 * renderer. All adapter allocations share the snapshot's budget. */
CohStatus coh_wr_presentation_create(CohWrBudget *, const CohRendererConfig *, CohWrPresentation **);
CohStatus coh_wr_presentation_create_fixture(CohWrBudget *, const CohRendererConfig *, CohWrPresentation **);
/* Control-thread only. Immutable snapshot + source-selected visibility/camera
 * become one frame/binding/resource bundle. No source data is reinterpreted.
 * Publication counter is distinct from packet IDs: the identical immutable
 * snapshot can receive a new camera/visibility frame. Output unchanged on error. */
CohStatus coh_wr_presentation_prepare(CohWrPresentation *, CohWrSnapshot *,
    uint64_t publication, const size_t *indices, size_t count,
    const float view[16], const float projection[16],
    const CohWrPresentationResources *, CohCancel, CohWrPreparedFrame **);
/* Single control publisher, concurrently with one GL consumer. Retains bundle;
 * counter must increase. New snapshots obey existing mailbox source/session/
 * player/generation rules. Replacing pending work never invalidates GL leases. */
CohStatus coh_wr_presentation_publish(CohWrPresentation *, CohWrPreparedFrame *);
void coh_wr_presentation_release(CohWrPreparedFrame *);
/* GL thread. Resume requires the actual renderer's matching nonzero Surface
 * generation and no outstanding queue. Home pause preserves CPU/GPU owners.
 * Surface loss abandons the renderer before invalidating bindings; resume with
 * the new exact generation before presenting again. All GL methods serialized.
 * Neither method uploads GPU resources or certifies the GLES context/thread. */
CohStatus coh_wr_presentation_resume(CohWrPresentation *, CohRenderer *, uint32_t);
CohStatus coh_wr_presentation_pause(CohWrPresentation *, CohRenderer *);
CohStatus coh_wr_presentation_surface_lost(CohWrPresentation *, CohRenderer *, uint32_t new_generation, int context_alive);
/* No adapter heap allocation/free/IO/resource decode or upload. Renderer shader
 * cache callbacks may compile/evict programs; actual backend/driver ownership
 * remains external and unmeasured. Candidate resources bind before any submit.
 * Missing/cancelled candidate bind renders old active frame, reporting refusal.
 * Candidate becomes active ONLY after every bounded batch flush succeeds.
 * A draw/backend failure abandons outstanding spans and keeps old active frame;
 * already drawn pixels cannot be rolled back. Callback draws retain source
 * opaque-run batching/translucent ordering; framebuffer atomicity is not claimed.
 * result is set for attempted frames; malformed/lifecycle refusals preserve it. */
CohStatus coh_wr_presentation_render(CohWrPresentation *, CohRenderer *, CohCancel, CohWrPresentationResult *);
/* GL thread after publisher is stopped/joined. Permanently closes this session,
 * abandons draws and releases active/pending publication. New session creates a
 * new owner. Leases queue retirement; only control collect invokes drop/free. */
CohStatus coh_wr_presentation_stop(CohWrPresentation *, CohRenderer *, int context_alive);
void coh_wr_presentation_collect(CohWrPresentation *);
/* Control thread after GL/publisher joined and all caller bundles released.
 * STATE preserves owner while outstanding prepared/retired objects exist. */
CohStatus coh_wr_presentation_destroy(CohWrPresentation **);
#ifdef __cplusplus
}
#endif
#endif
