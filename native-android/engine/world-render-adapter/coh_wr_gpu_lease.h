#ifndef COH_WR_GPU_LEASE_H
#define COH_WR_GPU_LEASE_H
#include "coh_wr_gpu_texture.h"
#include "coh_wr_presentation.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_WR_GPU_LEASE_MAX_TEXTURES 4096u
#define COH_WR_GPU_LEASE_CONTROL_RESERVE 65536u
typedef struct CohWrGpuLease CohWrGpuLease;
typedef struct {
    uint64_t texture_id;
    CohAssetId asset;
    uint8_t source_sha256[32];
    CohWrGpuTexture **take;
} CohWrGpuLeaseInput;
/* These are actual registry operations, not generation attestations. retain and
 * release pin its immutable operations/context registry; they perform no GL.
 * begin_retirement obtains the exact token's whole-context cleanup gate. Normal
 * GL work in that context must then refuse, while retire_current/destroyed and
 * cleanup remain usable. A failed begin acquires NO gate; a failed end retains
 * its already acquired gate. The registry and its
 * root lease outlive adoption; every acquired pin outlives GPU disposition.
 * Failed retain acquires no pin. Calls are synchronous, nonreentrant, and
 * callbacks never retain inputs. */
typedef struct {
    CohWrGpuOps gpu;
    CohStatus (*retain_registry)(void *);
    void (*release_registry)(void *);
    CohStatus (*begin_retirement)(void *, CohWrGpuToken);
    CohStatus (*end_retirement)(void *, CohWrGpuToken);
} CohWrGpuLeaseBackend;
typedef struct {
    size_t aggregate_limit, external_bytes;
    size_t gpu_owner_cpu_reservation, registry_reservation;
} CohWrGpuLeaseLimits;
typedef struct {
    CohWrGpuToken token;
    uint32_t asset_generation, textures, remaining_textures, leases;
    uint32_t attached, retired, drained, cleanup_gate, callback_faults;
    size_t owned_bytes, gpu_reservation, aggregate_reserved_bytes;
} CohWrGpuLeaseReport;
/* GL owner before presentation. Strictly increasing nonzero logical IDs bind
 * exact full asset path + generation + whole-source SHA to successful genuine
 * opaque upload owners, their common token and the identical GPU operations.
 * A numeric ID is an immutable local binding, never source/current authority.
 * All input pointer slots are distinct and exclusively owned; opaque GPU owner
 * storage must not alias writable caller slots. No concurrent owner use/transfer
 * is permitted. All takes and *out remain unchanged on EVERY failure; *out must
 * be NULL. All transfer writes occur only after complete validation/cancellation.
 * No texture upload, name substitution, material or scene interpretation occurs.
 *
 * external_bytes must book ALL old/new GPU reservations, opaque GPU CPU owners,
 * registry/provider/context/driver storage, input arrays/paths and other parent
 * peaks. Explicit GPU-owner/registry reservations establish required minima,
 * not allocator/RSS measurement. This module adds its allocation +64KiB reserve;
 * its <=96MiB check is the same parent allowance, never extra capacity. */
CohStatus coh_wr_gpu_lease_adopt(const CohWrGpuLeaseInput *, size_t,
    const CohWrGpuLeaseBackend *, const CohWrGpuLeaseLimits *, CohCancel,
    CohWrGpuLease **);
/* Control thread attaches once; that same actual pthread owns hold/drop,
 * retire and collect. Callbacks borrow this owner. Join their users before
 * collect. hold/drop never allocate, delete, free, upload or invoke registry GL.
 * Wrong-thread/underflow drops preserve leases and increment a fixed fault count.
 * Resolve is GL-only, bounded numeric lookup + existing exact gpu_view; returned
 * names remain owned through the frame's final flush/abandonment and drop. */
CohStatus coh_wr_gpu_lease_resources(CohWrGpuLease *, CohWrPresentationResources *);
/* Retire stops new holds; existing leases can still resolve until their drops.
 * A paused frame is still a lease. Retirement does not delete anything. */
CohStatus coh_wr_gpu_lease_retire(CohWrGpuLease *);
/* Separate GL maintenance, never the presentation render callback. Refuses
 * while leases remain. GPU release may free its existing small CPU owner here.
 * Partial/error-after-consumption owners and a cleanup gate remain for retry.
 * Old Surface cleanup is allowed only in its same surviving context. A dead
 * context disposes only through existing verified-destroyed retirement. */
CohStatus coh_wr_gpu_lease_drain(CohWrGpuLease *);
/* Control metadata/registry-pin release only after complete GL disposition and
 * gate release; STATE preserves owner otherwise. No automatic budget reduction. */
CohStatus coh_wr_gpu_lease_collect(CohWrGpuLease **);
CohStatus coh_wr_gpu_lease_report(const CohWrGpuLease *, CohWrGpuLeaseReport *);
#ifdef __cplusplus
}
#endif
#endif
