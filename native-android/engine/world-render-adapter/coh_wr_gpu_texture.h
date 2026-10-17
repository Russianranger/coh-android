#ifndef COH_WR_GPU_TEXTURE_H
#define COH_WR_GPU_TEXTURE_H
#include "coh_wr_texture.h"
#include "coh_wr_sampler.h"
#ifdef __cplusplus
extern "C" {
#endif
/* One actual render-thread/context owner. Tokens are never inferred from a GL
 * name. Backend current() must authenticate all fields against actual current
 * GLES3 context, Surface lifetime and calling thread BEFORE each operation. */
typedef struct {uint64_t surface_generation,context_generation,render_thread;} CohWrGpuToken;
typedef struct {
    void *context;
    CohStatus (*current)(void *,CohWrGpuToken);
    /* Exact old context/thread, with a recognized retired Surface permitted for
     * cleanup ONLY. Backend/caller must quarantine ALL other work in that context while
     * a journal is pending (not merely uploads using that same journal); its saved GL state may not be overwritten/interleaved. */
    CohStatus (*retire_current)(void *,CohWrGpuToken);
    CohStatus (*destroyed)(void *,CohWrGpuToken); /* OK only verified dead context */
    /* Narrow checked GLES3 calls: numeric pname/value are original GL enums.
     * Backend context/registry and callbacks outlive all owners/journals; exact
     * operation identity is retained and mismatch refuses. Each callback checks errors; no pending GL error may be silently cleared.
     * get_integer writes only on success; generate returns any partial name even
     * on failure. Calls stay synchronous; image consumes all RGBA8 bytes before
     * returning. No hidden mip generation or retained CPU pointer is permitted. */
    CohStatus (*get_integer)(void *,uint32_t,int32_t *);
    CohStatus (*generate)(void *,uint32_t *);
    CohStatus (*bind_texture)(void *,uint32_t);
    CohStatus (*bind_unpack_buffer)(void *,uint32_t);
    CohStatus (*pixel_store)(void *,uint32_t,int32_t);
    CohStatus (*image_rgba8)(void *,uint32_t,uint32_t,uint32_t,CohBytes);
    CohStatus (*parameter)(void *,uint32_t,int32_t);
    /* Ownership-aware delete: sets *name=0 iff consumption is verified, including
     * error-after-consumption. Uncertain/live names remain nonzero for retry;
     * backend must prevent reuse until disposition is known. Never delete in a
     * different context, even if that context reused the same numeric name. */
    CohStatus (*delete_texture)(void *,uint32_t *name);
} CohWrGpuOps;
/* Caller-owned zero-initialized rollback journal. Never mutate/copy a live
 * journal. Keep until retry succeeds or destroyed() verifies its exact old
 * context lifetime ended. A pending journal forbids another upload using it. */
typedef struct {
    uint32_t pending,name,restore_needed;
    CohWrGpuToken token;int32_t saved[6];CohWrGpuOps operations;
} CohWrGpuJournal;
typedef struct {
    size_t aggregate_limit,external_bytes,gpu_reservation;
    uint32_t max_dimension;
} CohWrGpuLimits;
typedef struct CohWrGpuTexture CohWrGpuTexture;
typedef struct {
    CohWrGpuToken token;CohWrTextureReport source;
    size_t gpu_reservation,aggregate_reserved_bytes;
    uint32_t uploaded_levels;
} CohWrGpuReport;
/* Off-thread CPU resource must stay alive for this synchronous call; not needed
 * afterward. Successful output owns one new name. Existing output unchanged;
 * NULL required. Failure restores bindings/unpack state and deletes candidate.
 * If cleanup cannot finish, returns COH_STATE and journal retains responsibility.
 * Caller reserves CPU/loader/all older GPU+pending journal memory externally;
 * gpu_reservation >= nominal RGBA bytes is an explicit driver reservation, NOT
 * measured GPU heap usage. Backend scratch allocations are external too.
 * No material, effective CLIENT-state, world or actor capability is granted. */
CohStatus coh_wr_gpu_upload(const CohWrTextureResource *,const CohWrSamplerSource *,
    CohWrGpuToken,const CohWrGpuOps *,const CohWrGpuLimits *,CohCancel,
    CohWrGpuTexture **out,CohWrGpuJournal *);
CohStatus coh_wr_gpu_retry_cleanup(CohWrGpuJournal *,const CohWrGpuOps *);
CohStatus coh_wr_gpu_discard_destroyed_journal(CohWrGpuJournal *,const CohWrGpuOps *);
/* View valid only through same-token flush; retain owner until all draws end.
 * This token check does not make a copied descriptor safe after context loss. */
CohStatus coh_wr_gpu_view(const CohWrGpuTexture *,CohWrGpuToken,const CohWrGpuOps *,CohRenderTexture *);
CohStatus coh_wr_gpu_report(const CohWrGpuTexture *,CohWrGpuReport *);
CohStatus coh_wr_gpu_identity(const CohWrGpuTexture *,CohAssetId *);
/* Wrong/new context refuses and preserves owner. A retired Surface may be
 * cleaned on its same surviving context through retire_current(). Retry on original context or
 * use verified-destroyed retirement. New Surface/context always needs a fresh
 * upload/name; never reassign old names to a new token. */
CohStatus coh_wr_gpu_release(CohWrGpuTexture **,const CohWrGpuOps *);
CohStatus coh_wr_gpu_discard_destroyed(CohWrGpuTexture **,const CohWrGpuOps *);
#ifdef __cplusplus
}
#endif
#endif
