#ifndef COH_SOURCE_WS_PROBE_H
#define COH_SOURCE_WS_PROBE_H
#include "coh_source_sealed.h"
#include "../working-set/coh_working_set.h"
typedef struct {
 CohSourceSealedPlan source;CohWsReport parent;CohWsPlan candidate_copy_only;
 size_t parent_booked_added_to_retained;
 uint32_t input_ticket_verified,external_lifetimes_verified,admission_permitted,parent_mutated,world_authority;
}CohSourceWsProbe;
/* Read-only measurement prerequisite, NOT a scoped reservation adapter.
 * Derives exact private copy layout from actual batch and reads actual parent.
 * Conservatively adds ALL parent.booked to full existing module retained_bytes;
 * no subtracting suspected duplicate tickets, source deps or loader charges.
 * Returned candidate_copy_only is diagnostic; it cannot authorize prepare/commit.
 * Generic API exposes no actual input-ticket/owner correlation or source/graph/
 * loader retirement witness. Thus admission_permitted is ALWAYS false. Neither
 * parent nor source is retained/mutated. All views/identities borrow batch life.
 * All opaque parent/source/control allocations caller-disjoint; known source
 * spans/controls/endpoints checked. No allocation/callback; failure leaves out
 * unchanged. Parent's own API remains read-only in this component. */
CohStatus coh_source_ws_probe(const CohWorkingSet*,const CohSourceMeshBatch*,
 const CohSourceSealedBudget*,CohSourceWsProbe*);
#endif
