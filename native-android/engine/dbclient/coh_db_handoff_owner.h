#ifndef COH_DB_HANDOFF_OWNER_H
#define COH_DB_HANDOFF_OWNER_H
#include "coh_db_session.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Single owner thread. Only a validated DBSession take creates this owner.
 * No cookie/password accessor or caller-constructed handoff admission exists. */
typedef struct {
    uint32_t user_id, selected_dbid, selected_slot, selection_generation;
    uint32_t session_generation, receipt_generation, connect_id;
    CohNetEndpoint db_peer;
    unsigned local_development_auth, selected_dbid_owner_bound;
    unsigned claimed, retired;
} CohDbHandoffMetadata;
/* Allocate and validate before consuming the existing one-shot DB take.
 * Output must initially be NULL and remains unchanged on failure. Continue DB service until CLOSED as before. */
CohStatus coh_db_session_take_handoff_owner(CohDbSession *, CohDbHandoffOwner **);
CohStatus coh_db_handoff_owner_retain(CohDbHandoffOwner *);
void coh_db_handoff_owner_release(CohDbHandoffOwner *);
/* Immediate irreversible secret wipe shared by all retained references. */
void coh_db_handoff_owner_retire(CohDbHandoffOwner *);
CohStatus coh_db_handoff_owner_metadata(const CohDbHandoffOwner *, CohDbHandoffMetadata *);
#ifdef __cplusplus
}
#endif
#endif
