#ifndef COH_INVENTORY_PHASE_H
#define COH_INVENTORY_PHASE_H
#include "coh_inventory.h"
#include "coh_invention.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_INVENTORY_PHASE_RAM_MAX (8u*1024u*1024u)
#define COH_INVENTORY_PHASE_STACK_RESERVE 8192u
typedef struct {
 CohInventoryUpdate inventory;CohInventionUpdate invention;char workshop[32];
 size_t begin_bit,inventory_end_bit,invention_end_bit,end_bit;
}CohInventoryPhase;
typedef struct {
 CohInventoryPhase candidate;CohInventoryWorkspace inventory;CohInventionWorkspace invention;
}CohInventoryPhaseWorkspace;
/* Atomic original post-badge inventory→invention→workshop subtransaction.
 * Stops BEFORE team-up-to-date flag; later team/super/league/etc remain required.
 * Requires statusChange0, the only source original-consumer-aligned invention
 * profile. Nonzero status returns UNSUPPORTED with reader/output unchanged,
 * never treating the original no-op consumer as a zero-length producer body.
 * Auction text remains opaque/unresolved; no trading/workshop/UI/state/ACK.
 * All spans pairwise disjoint. Caller heap/arena; input+allout+workspace+stack+
 * retained within8MiB. Child ownership is charged once. No allocations. */
CohStatus coh_inventory_phase_read(CohRepReader *,CohInventoryPhase *,
 CohInventoryPhaseWorkspace *,size_t budget,size_t retained_bytes);
#ifdef __cplusplus
}
#endif
#endif
