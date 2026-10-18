#ifndef COH_DB_SESSION_H
#define COH_DB_SESSION_H
#include "coh_dbclient.h"
#include "../network/coh_net_udp.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    CohNetUdpConfig transport; /* Explicit caller-authorized disposable peer. */
    uint64_t request_timeout_ms;
    int outbound_compressed;
} CohDbSessionConfig;
/* Returned by the independently authenticated AuthServer flow. verified=1
 * is caller attestation, NOT proof manufactured by this module. A new receipt
 * generation is mandatory after suspend/disconnect/failure; stale cookies
 * never replay automatically on foreground return. No password is accepted. */
typedef struct {
    uint32_t user_id, game_cookie, generation;
    char account[15];
    int verified;
} CohDbAuthReceipt;
typedef enum {
    COH_DB_IDLE, COH_DB_CONNECTING, COH_DB_WAIT_PLAYERS, COH_DB_QUEUED,
    COH_DB_CHARACTERS, COH_DB_WAIT_MAP, COH_DB_HANDOFF_READY,
    COH_DB_DISCONNECTING, COH_DB_SUSPENDED, COH_DB_CLOSED,
    COH_DB_FAILED, COH_DB_CANCELLED, COH_DB_TIMED_OUT
} CohDbSessionPhase;
typedef struct {
    CohAuthMapHandoff map;
    uint32_t selected_slot, selection_generation, selected_dbid;
} CohDbSessionHandoff;
typedef struct {
    CohDbSessionPhase phase;
    uint32_t generation, selection_generation, queue_position, queue_count;
    unsigned local_development_auth, server_identity_bound;
    uint64_t login_requests, player_lists, queue_updates, choices, handoffs,
        malformed, unsupported, server_rejections, receipt_rejections,
        suspends, disconnects, timeouts, cancellations;
    /* Complete independent account controls, never a character-list grant.
     * Counters are lifetime diagnostics; no request deadline is reset. */
    uint64_t account_unavailable, account_charcounts;
    uint32_t account_last_shards, account_last_error_branch;
    /* Complete envelope count only; no retained inventory/account state. */
    uint64_t account_inventories;
    uint32_t account_last_inventory_items;
    CohNetUdpDiagnostics transport;
} CohDbSessionDiagnostics;
typedef struct CohDbSession CohDbSession;
typedef struct CohDbHandoffOwner CohDbHandoffOwner;
/* All methods are single-owner-thread and nonblocking. All error outputs
 * remain unchanged. Secret buffers are cleared on every terminal transition. */
CohDbSession *coh_db_session_create(const CohDbSessionConfig *);
void coh_db_session_destroy(CohDbSession *);
CohStatus coh_db_session_begin(CohDbSession *, const CohDbLogin *,
    const CohDbAuthReceipt *, uint32_t connect_id, uint64_t now_ms);
/* Explicit source -db/UseFakeAuth path. Both local bind and DB peer must be
 * loopback, login UID/cookie zero, generation fresh/nonzero. First genuine
 * SEND_PLAYERS must supply a nonzero UID; all later lists must match it.
 * This is NOT AuthServer authentication and cannot create CohDbAuthReceipt. */
CohStatus coh_db_session_begin_local(CohDbSession *, const CohDbLogin *,
    uint32_t generation, uint32_t connect_id, uint64_t now_ms);
CohStatus coh_db_session_service(CohDbSession *, uint64_t now_ms, CohCancel);
CohStatus coh_db_session_players(const CohDbSession *, CohDbPlayers *);
CohStatus coh_db_session_choose(CohDbSession *, uint32_t wire_slot,
    uint32_t local_map_ip, uint32_t create_location, uint64_t now_ms);
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
 * After pointer/alignment/known-alias admission, consume BEFORE policy fields;
 * every admitted retirement attempt cancels/wipes even on policy mismatch.
 * Retire/wipe the offer and cancel the DB session BEFORE copying
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


/* Creation-mode sessions refuse BOTH raw and typed ordinary handoff takes. */
/* Exactly one successful take. Starts graceful DB disconnect. Continue
 * service() until CLOSED. Caller owns/erases output and authorizes map peer.
 * selected_dbid comes from the exact DBGAMESERVER_MAP_CONNECT producer's
 * first field (EntCon.id), after this opaque owner validated DB list/choice and
 * WAIT_MAP command/transport context. Direct and Queue7-field relay profiles are
 * source qualified. Generic map.link_id alone is NOT a DBID authority. This
 * binds source DB selection, not cryptographic authentication or a complete
 * Map self/character transaction; local development auth remains provisional. */
CohStatus coh_db_session_take_handoff(CohDbSession *, CohDbSessionHandoff *);
/* Additive opaque provenance owner. See coh_db_handoff_owner.h for lifecycle. */
CohStatus coh_db_session_take_handoff_owner(CohDbSession *, CohDbHandoffOwner **);
CohStatus coh_db_session_disconnect(CohDbSession *, uint64_t now_ms);
void coh_db_session_suspend(CohDbSession *);
void coh_db_session_cancel(CohDbSession *);
CohStatus coh_db_session_local_endpoint(const CohDbSession *, CohNetEndpoint *);
CohDbSessionPhase coh_db_session_phase(const CohDbSession *);
void coh_db_session_diagnostics(const CohDbSession *, CohDbSessionDiagnostics *);
#ifdef __cplusplus
}
#endif
#endif
