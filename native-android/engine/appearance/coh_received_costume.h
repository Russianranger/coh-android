#ifndef COH_RECEIVED_COSTUME_H
#define COH_RECEIVED_COSTUME_H
#include "coh_appearance_actor.h"
#include "coh_appearance_scales.h"
#include "../assets/coh_asset_zip.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_RECEIVED_COSTUME_LIMIT (96u<<20)
#define COH_RECEIVED_COSTUME_STACK (32u<<10)
#define COH_RECEIVED_COSTUME_TEXTURES 64u
typedef struct CohReceivedCostume CohReceivedCostume;
typedef struct {
 const CohOriginalCostumeSnapshot *snapshot;
 const CohAnimationRig *rig; /* authentic Huge hierarchy; immutable lifetime */
 CohAssetSource archives[2]; /* actual CLIENT, optional zones supplement */
 uint64_t parent_bytes,source_epoch;uint32_t entity_index;CohCancel cancel;
} CohReceivedCostumeInputs;
typedef struct {
 uint64_t cpu_bytes,texture_bytes,gpu_reserve_bytes,renderer_cpu_reserve_bytes,prepare_peak_bytes,source_reads,source_bytes,frames,draws;
 uint64_t source_epoch;uint32_t entity_index,bodytype,parts,vertices,indices,textures,material_fallbacks;
 float height_scale;char missing[256];
} CohReceivedCostumeStats;
/* Off-GL, before mutation: caller supplies actual old/world/source/borrowed
 * charges. Entire staging and planned GPU storage are preflighted under96MiB.
 * No full catalog is copied; only requested ZIP identities and original bodies
 * are streamed. Missing inputs name their real path/texture, never a substitute.
 * out must beNULL. Failure preservesout and cleans every private candidate.
 * Input FD/source spans outlive this call; only the original rig is borrowed
 * after return. The snapshot is copied into source-selected colors/morphology. */
CohStatus coh_received_costume_prepare(const CohReceivedCostumeInputs *,
 CohReceivedCostume **out,CohReceivedCostumeStats *);
void coh_received_costume_destroy(CohReceivedCostume **);
CohReceivedCostumeStats coh_received_costume_stats(const CohReceivedCostume *);
/* Borrowed immutable pixels, logical source name and dimensions. Explicit
 * source "none" uses the original engine white binding, not a missing asset. */
CohStatus coh_received_costume_texture(const CohReceivedCostume *,uint32_t,
 CohBytes *,uint32_t *,uint32_t *,const char **);
CohStatus coh_received_costume_bind(CohReceivedCostume *,uint32_t,
 const uint32_t *,uint32_t);
/* CPU skin original Huge Ready/base inspection with actual packet morphology.
 * No animation/movement authority is inferred. Caller supplies real observed
 * pose translation and view. Returns owned packets valid until nextcall. */
CohStatus coh_received_costume_draws(CohReceivedCostume *,const float view[12],
 const float projection[16],const float position[3],const CohRenderDraw **,size_t *);
#ifdef __cplusplus
}
#endif
#endif
