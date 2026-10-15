#ifndef COH_SKIN_CACHE_H
#define COH_SKIN_CACHE_H
#include "../coh_contracts.h"
#include "../../material-probe/app/src/main/cpp/coh_mesh.h"
#ifdef __cplusplus
extern "C" {
#endif
/* New optional wrapper around the unchanged accepted scalar skinning kernel.
 * Identity includes source mesh, source rig, pose AND their content generations.
 * Exact retained input comparisons defend even incorrectly reused identities. */
typedef struct {
  uint64_t mesh, rig, pose;
  uint32_t mesh_generation, rig_generation, pose_generation;
} CohSkinKey;
typedef struct {
  uint32_t entries, max_vertices, max_bones;
  size_t byte_budget; /* Includes object/metadata; excludes allocator overhead. */
} CohSkinCacheConfig;
typedef struct {
  size_t allocated_bytes;
  uint64_t hits, misses, evictions, invalidations, rejections;
  uint64_t kernel_vertices, compared_bytes, copied_bytes;
  uint32_t resident_entries;
} CohSkinCacheStats;
typedef struct CohSkinCache CohSkinCache;
CohStatus coh_skin_cache_create(const CohSkinCacheConfig *, CohSkinCache **);
void coh_skin_cache_destroy(CohSkinCache **);
/* Single owner thread. No allocations after create. vertices/palette must be
 * immutable for the call; lengths are explicit and validated. Output is borrowed
 * immutable cache storage valid ONLY until next sample/invalidate/destroy.
 * On failure *output is unchanged; partially computed victims are invalidated.
 * hit is optional, and unchanged on failure. */
CohStatus coh_skin_cache_sample(CohSkinCache *, CohSkinKey,
                               const CohMeshVertex *vertices, uint32_t count,
                               const float *palette, uint32_t bones,
                               const CohSkinnedVertex **output, int *hit);
void coh_skin_cache_invalidate(CohSkinCache *);
CohSkinCacheStats coh_skin_cache_stats(const CohSkinCache *);
#ifdef __cplusplus
}
#endif
#endif
