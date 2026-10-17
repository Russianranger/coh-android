#ifndef COH_POWER_IDS_H
#define COH_POWER_IDS_H
#include "coh_power_join.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_POWER_IDS_RAM_MAX (8u*1024u*1024u)
#define COH_POWER_IDS_STACK_RESERVE 16384u
#define COH_POWER_IDS_WORK_MAX (64u*1024u*1024u)
typedef struct {uint32_t category,set,power;uint8_t assigned;} CohPowerRuntimeID;
typedef struct {
 const CohPowerJoin *join;
 uint32_t category_count,set_count,power_count,assigned_power_count;
 uint8_t source_id_projection,complete_finalization,runtime_generation,actor_authority;
 uint32_t sorted_categories[COH_CATEGORY_MAX];
 CohPowerRuntimeID ids[COH_POWER_STREAM_RECORD_MAX];
 uint32_t set_parent_categories[COH_POWER_SET_MAX];
 uint32_t power_parent_sets[COH_POWER_STREAM_RECORD_MAX];
} CohPowerIDs;
typedef struct {CohPowerIDs candidate;} CohPowerIDsWorkspace;
/* Original FinalizeDict strcmp category order and basepower_SetID overwrite
 * order, followed by source SetBackPointers reverse parent overwrite order.
 * Category indices are SORTED positions, never raw cache indices. Set/power IDs
 * are category/set-local ordinals, never allocated dictionary row ordinals.
 * Unreached allocated powers have assigned=0, not an invented valid zero ID.
 *
 * Borrows the complete join and all its immutable dictionary/provider leases.
 * Fixed source bounds and all transitive owners/set input/provider context/
 * scratch/caller retained/stack are charged before sorting. No file callbacks,
 * allocations, modifier/FX/diminishing-return finalization or runtime admission.
 * Source-only projection does not establish current IDs for a live server, actor
 * authority, complete FinalizePower/FinalizeDict, or any application ACK.
 */
CohStatus coh_power_ids_prepare(const CohPowerJoin*,CohPowerIDs*,CohPowerIDsWorkspace*,size_t,size_t);
/* Read-only category/set/power ordinal resolution against this immutable view.
 * Out preserves its prior value on refusal; no source generation is inferred. */
CohStatus coh_power_ids_find(const CohPowerIDs*,uint32_t,uint32_t,uint32_t,uint32_t*);
#ifdef __cplusplus
}
#endif
#endif
