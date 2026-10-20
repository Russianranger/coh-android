#ifndef COH_WORLD_LIVE_H
#define COH_WORLD_LIVE_H
#include "coh_world_stream.h"
typedef struct CohWorldLive CohWorldLive;
typedef struct {size_t owned_bytes;uint32_t rows;uint64_t reads,read_bytes,queries;} CohWorldLiveStats;
/* Compact original Atlas placement rows, not a pose-pruned bundle. The caller
 * verifies the index through the same APK input manifest as its other assets.
 * A source callback keeps the full index on disk. Query copies only <=64 nearby
 * instances; misses, cancellation, malformed rows or capacity preserve output.
 * Inputs remain immutable through free. Calls use the scene owner thread. */
CohStatus coh_world_live_open(CohAssetSource,uint32_t endpoint_count,CohCancel,CohWorldLive **);
CohStatus coh_world_live_query(CohWorldLive *,const float center[3],float radius,
    CohWorldInstance *,uint32_t capacity,uint32_t *count,CohCancel);
CohWorldLiveStats coh_world_live_stats(const CohWorldLive *);
void coh_world_live_free(CohWorldLive *);
/* The exact original hierarchy matrices/tints have already been decoded by
 * live_query; retain normal dependency/cache pinning and atomic replacement. */
CohStatus coh_world_select_instances(CohWorldMap *,CohAssetLoader *,
    const CohWorldInstance *,uint32_t,size_t,CohCancel,CohWorldSelection *);
#endif
