#ifndef COH_OFFLINE_WORLD_H
#define COH_OFFLINE_WORLD_H
#include "../assets/coh_asset_loader.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_OFFLINE_SELECTION_CAP 256u
#define COH_OFFLINE_DEPENDENCY_CAP 256u
#define COH_OFFLINE_INSTANCE_DEPENDENCIES 16u
/* Prepared on loader owner thread. All arrays borrowed immutable until destroy;
 * no hidden global/filesystem/GL/network dependencies. Instances must have
 * independently qualified GEO/model/material dependencies before ready=1. */
typedef struct {
    uint32_t source_id, cell, first_dependency, dependency_count, ready;
    float world[12], center[3], radius; /* original composed Mat4, no rewriting */
} CohOfflineInstance;
typedef struct { float minimum[3], maximum[3]; uint32_t first, count; } CohOfflineCell;
typedef struct {
    uint32_t generation, instance_count, cell_count, asset_count, dependency_count;
    const CohOfflineInstance *instances;
    const CohOfflineCell *cells;
    const CohAssetId *assets;
    const uint32_t *dependencies;
} CohOfflineWorld;
/* Zero initialize; a live selection is single-owner and MUST NOT be copied. */
typedef struct {
    uint32_t generation,count,pin_count; size_t resident_bytes;
    uint32_t instances[COH_OFFLINE_SELECTION_CAP];
    const CohAssetBlob *pins[COH_OFFLINE_DEPENDENCY_CAP];
    CohAssetLoader *loader;
} CohOfflineSelection;
typedef struct {
    uint32_t tested_cells,visible_cells,tested_instances,visible_instances;
    uint32_t unavailable_instances,unique_assets;
    size_t required_bytes;
} CohOfflineSelectionStats;
/* Validates partition coverage and exact source identities, no heap allocation.
 * Each cell bounds must conservatively contain each of its instance spheres.
 * Source IDs must increase across the cell-partitioned packet.
 * Validation, selection, acquisition/decode and release are ASSET-LOADER-owner
 * work: NEVER call selection on simulation/audio threads. */
CohStatus coh_offline_validate(const CohOfflineWorld *);
/* Intersection uses conservative spheres and cells. Missing qualified geometry,
 * bad generation, capacity/budget/cancellation/acquisition failure preserve old
 * selection and its pins. No silent truncation or invented collision coverage.
 * All source instances are considered; no distance-based partial-success policy.
 * Before replacing an old selection, all renderer/collision borrowers MUST
 * finish. For concurrent use, select into an empty staged selection, publish
 * its generation at a consumer safe point, then retire old pins explicitly on
 * loader owner after consumer acknowledgement. The loader/world outlive all
 * their selections; generation IDs cannot be reused while a consumer lives.
 * Stats are supplied even on failure (zero initialized by this function). */
CohStatus coh_offline_select(const CohOfflineWorld *,CohAssetLoader *,uint32_t expected_generation,
                            const float center[3],float radius,size_t byte_budget,
                            CohCancel,CohOfflineSelection *,CohOfflineSelectionStats *);
void coh_offline_release(CohOfflineSelection *);
/* The exact SAME matrix must be consumed by bridge geometry and by collision
 * preparation; output is copied unchanged and has no lifetime dependency. */
CohStatus coh_offline_transform(const CohOfflineWorld *,uint32_t expected_generation,
                               uint32_t instance,float world[12]);
#ifdef __cplusplus
}
#endif
#endif
