#ifndef COH_SESSION_STREAM_WORLD_H
#define COH_SESSION_STREAM_WORLD_H
#include <stddef.h>
#include <stdint.h>
#include "coh_asset_loader.h"
/* CPU index/cache ownership belongs to the single render worker. Session
 * snapshots copy only this diagnostic value; the pointer is never cloned. */
typedef struct CohSessionWorld CohSessionWorld;
typedef struct {
    uint64_t catalog_instances,selected_instances,resident_bytes,budget_bytes;
    uint64_t peak_resident_bytes,selection_updates,cache_hits,cache_misses,evictions;
    uint64_t draws,geo_loads,texture_loads,errors,draw_packets,tf_components;
    uint64_t tf_mismatches,visible_pixels,owned_cpu_bytes,gpu_bytes;
    uint32_t generation,material_mode_mask;
    float view_radius,tf_max_error;
} CohSessionWorldStats;
int coh_session_world_create(const void *,size_t,CohSessionWorld **,char *,size_t);
/* Runtime source handles borrow immutable imports and must outlive the world.
 * parent_retained_bytes includes actual other Session/old scene/capture storage.
 * Existing 96MiB aggregate and child caps are unchanged. This source subset is
 * the original sidewalk model; it does not imply other Atlas models are loaded. */
typedef struct {
    CohAssetSource placements,atlas_zip,client_zip;
    uint64_t parent_retained_bytes;
} CohSessionWorldSources;
typedef struct {int fd;uint64_t offset,bytes;} CohSessionWorldFd;
int coh_session_world_create_fds(const void *,size_t,const CohSessionWorldFd inputs[3],uint64_t parent_retained_bytes,CohSessionWorld **,char *,size_t);
int coh_session_world_create_archives(const void *,size_t,const CohSessionWorldSources *,CohSessionWorld **,char *,size_t);
int coh_session_world_parent_bytes(CohSessionWorld *,uint64_t,char *,size_t);
uint64_t coh_session_world_live_reservation_bytes(void);
int coh_session_world_source_io(const CohSessionWorld *,uint64_t *reads,uint64_t *bytes);
void coh_session_world_destroy(CohSessionWorld **);
/* Query on the render owner thread between draws. CPU includes concrete owned
 * allocations; input bundle bytes borrow Session assets and are counted by the
 * parent. GPU counts live buffer/texture payloads, not unknown driver overhead. */
int coh_session_world_owned_bytes(const CohSessionWorld *,uint64_t *cpu,uint64_t *gpu);
int coh_session_world_surface(CohSessionWorld *,const float view[12],
                              const float projection[16],const float center[3],
                              float radius,CohSessionWorldStats *,char *,size_t);
int coh_session_world_draw(CohSessionWorld *,const float view[12],
                           const float projection[16],const float center[3],
                           float radius,CohSessionWorldStats *,char *,size_t);
int coh_session_world_draw_observed(CohSessionWorld *,const float view[12],
 const float projection[16],const float center[3],float radius,
 CohSessionWorldStats *,char *,size_t);
int coh_session_world_observed_entity(CohSessionWorld *,const float view[12],
 const float projection[16],uint32_t index,const float position[3],
 CohSessionWorldStats *,char *,size_t);
void coh_session_world_surface_lost(CohSessionWorld *,int context_alive,
                                    CohSessionWorldStats *);
#endif
