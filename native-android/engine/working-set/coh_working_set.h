#ifndef COH_WORKING_SET_H
#define COH_WORKING_SET_H
#include "../coh_contracts.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_WS_MAX (96u*1024u*1024u)
#define COH_WS_SLOTS 64u
typedef struct CohWorkingSet CohWorkingSet;
/* Accounting correlation only: never a source/session identity or security
 * capability. Callers serialize each parent and all borrowed tickets. */
typedef struct { uint64_t parent_serial,serial; uint32_t slot,reserved; } CohWsTicket;
typedef struct {
 size_t persistent_bytes,temporary_bytes,call_reserve,child_limit;
} CohWsPlan;
typedef struct {
 size_t limit,base_reserved,booked,peak; uint32_t preparing,resident;
} CohWsReport;
/* Fixed parent metadata and a 16KiB call reserve are charged at creation.
 * This is an allocation RESERVATION ledger, not a malloc tracker. It derives no
 * module footprints or actual owner liveness. Qualified concrete adapters are
 * REQUIRED before using it to partition existing module aggregate contracts.
 * It does not retain/free module owners. Current standalone APIs keep their
 * all-retained semantics; this API does not authorize omitting outside bytes. */
CohStatus coh_ws_create(size_t limit,CohWorkingSet **out);
/* Full persistent+temporary+call reservation admitted before child work.
 * child_limit is a caller policy ceiling, not a replacement module cap.
 * No callback/allocation occurs after parent creation. Outputs initially zero;
 * failures preserve parent and outputs, including peak/serial counters. */
CohStatus coh_ws_prepare(CohWorkingSet *,const CohWsPlan *,CohWsTicket *out);
/* Call AFTER the child has returned and freed ALL temporary allocations.
 * Actual retained bytes may only shrink its persistent reservation. owner is
 * a billing key, not evidence of source identity/size. No duplicate live key.
 * Future adapters must derive bytes from actual module owners and keep source
 * dependencies alive. Failure keeps the complete preparation reservation. */
CohStatus coh_ws_commit(CohWorkingSet *,const CohWsTicket *,const void *owner,
 size_t actual_retained_bytes);
/* Call only AFTER actual resources are released. abort applies to preparation;
 * release applies to a committed matching key. Successful call zeros ticket;
 * copied/stale/wrong-parent tickets cannot release another reservation. */
CohStatus coh_ws_abort(CohWorkingSet *,CohWsTicket *);
CohStatus coh_ws_release(CohWorkingSet *,CohWsTicket *,const void *owner);
CohStatus coh_ws_report(const CohWorkingSet *,CohWsReport *);
/* Refuses while any reservation remains. No implicit owner destruction. */
CohStatus coh_ws_destroy(CohWorkingSet **);
#ifdef __cplusplus
}
#endif
#endif
