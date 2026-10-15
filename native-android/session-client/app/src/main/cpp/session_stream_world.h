#ifndef COH_SESSION_STREAM_WORLD_H
#define COH_SESSION_STREAM_WORLD_H
#include <stddef.h>
#include <stdint.h>
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
void coh_session_world_destroy(CohSessionWorld **);
int coh_session_world_surface(CohSessionWorld *,const float view[12],
                              const float projection[16],const float center[3],
                              float radius,CohSessionWorldStats *,char *,size_t);
int coh_session_world_draw(CohSessionWorld *,const float view[12],
                           const float projection[16],const float center[3],
                           float radius,CohSessionWorldStats *,char *,size_t);
void coh_session_world_surface_lost(CohSessionWorld *,int context_alive,
                                    CohSessionWorldStats *);
#endif
