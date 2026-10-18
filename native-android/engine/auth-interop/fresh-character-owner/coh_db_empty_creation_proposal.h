/* PROPOSAL ONLY: no implementation, integration, linking or runtime admission.
 * C owns any eventual minimal ordinary DB-session implementation. */
#ifndef COH_DB_EMPTY_CREATION_PROPOSAL_H
#define COH_DB_EMPTY_CREATION_PROPOSAL_H
#include "../../dbclient/coh_db_session.h"
#ifdef __cplusplus
extern "C" {
#endif

/* Exact Common/comm_backend.h enum value; this first bounded scope permits
 * only original PRIMAL_HERO/Atlas routing, not arbitrary create locations. */
typedef enum { COH_DB_CREATE_PRIMAL_HERO = 1 } CohDbCreationLocation;
typedef struct {
    uint32_t wire_slot;
    CohBytes name; /* borrowed1..63 bytes, no NUL/control; never retained raw */
    CohDbCreationLocation location;
    uint32_t expected_session_generation, expected_receipt_generation;
    uint64_t expected_list_generation; /* actual player_lists sequence, exactly1 */
} CohDbEmptyCreationRequest;

/* Missing ordinary opaque-session primitive: no UID/DBID/cookie/local-map-IP
 * setter. Requires fresh ordinary real-auth session (never begin_local),
 * CHARACTERS, complete internal matching-UID list, exact generation comparisons,
 * one lifetime list, no queue/unsupported/choice/handoff and an actual unlocked
 * EMPTY/nonvisitor wire slot. Expected numbers compare actual private state;
 * they never supply identity or authenticate a caller.
 *
 * Admit the active ordinary-auth CHARACTERS context from private state alone;
 * then consume the per-session-object attempt BEFORE consulting request
 * generation comparisons, slot, name, encoder or queue. Stale generations and
 * invalid request fields cannot retry the same admitted session object.
 * Keep that latch across every error, cancel, begin/rebegin and terminal state;
 * a new outer owner also consumes before making this call. No retry permitted.
 * Encode via unchanged coh_db_choose_encode(local_map_ip=0), queue reliably,
 * then and only then set distinct creation mode/selection generation/WAIT_MAP.
 * Failure never invents a handoff or means persistent allocation was undone. */
CohStatus coh_db_session_create_empty(CohDbSession *,
    const CohDbEmptyCreationRequest *, uint64_t now_ms);

typedef struct {
    uint32_t expected_session_generation, expected_receipt_generation;
    uint32_t expected_selection_generation;
    uint32_t owned_map_id; /* existing owned static Map registration, not DBID */
    CohNetEndpoint owned_map_endpoint; /* explicit actual owned Map UDP peer */
} CohDbCreatedOfferPolicy;
typedef struct {
    unsigned server_allocated_offer_observed;
    unsigned private_offer_retired;
    unsigned container_uninitialized;
    unsigned persistent_rollback_claimed; /* always0 */
    uint32_t session_generation, receipt_generation, selection_generation;
} CohDbCreatedOfferSummary;

/* Only distinct creation mode plus actual source-parsed MAP_CONNECT may
 * complete this operation. Match private current generation, positive actual
 * server DBID, source Map id/endpoint and nonreserved actual Map cookie; no
 * caller DBID/cookie or fabricated player-list identity is accepted.
 *
 * Consume once, retire/wipe the offer and cancel the DB session BEFORE copying
 * a fixed scalar summary. No Map socket is opened. It deliberately cannot be
 * continued later; a future full creator needs a different opaque offer type.
 * All failure outputs unchanged and known input/output/session aliases refuse.
 * 'private_offer_retired' covers private retained data, not SQL row rollback or
 * independent OS-handle retirement. The platform shim/driver proves those.
 *
 * Required minimal companion guards in ordinary core: BOTH existing
 * coh_db_session_take_handoff and coh_db_session_take_handoff_owner[_alloc]
 * refuse creation-mode sessions. No existing Map serializer is widened. */
CohStatus coh_db_session_retire_created_offer(CohDbSession *,
    const CohDbCreatedOfferPolicy *, CohDbCreatedOfferSummary *);

#ifdef __cplusplus
}
#endif
#endif
