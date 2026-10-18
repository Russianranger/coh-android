/* NONSHIPPING: fresh Auth -> one ordinary empty-slot allocation offer.
 * New source/host qualification and integration remain separate obligations. */
#ifndef COH_FRESH_CHARACTER_OWNER_H
#define COH_FRESH_CHARACTER_OWNER_H
#include "../../login/coh_login.h"
#include "../../dbclient/coh_db_session.h"
#ifdef __cplusplus
extern "C" {
#endif

typedef struct CohFreshCharacterOwner CohFreshCharacterOwner;
typedef struct {
    CohNetEndpoint auth_endpoint; /* Exact loopback; port20000..59999. */
    const CohAuthCrypto *crypto;  /* Borrowed immutable through owner destroy. */
    uint32_t connect_id;          /* Fresh nonzero transport entropy, not a grant. */
    uint8_t executable_checksum[16]; /* Actual measured probe; no reference claim. */
    CohNetEndpoint owned_map_endpoint; /* Actual owned loopback UDP7001; not a DBID. */
    uint32_t owned_map_id;        /* First bounded scope is original Atlas Map1. */
} CohFreshCharacterConfig;
typedef enum {
    COH_FRESH_CHARACTER_IDLE,
    COH_FRESH_CHARACTER_AUTHENTICATING,
    COH_FRESH_CHARACTER_WAIT_LIST,
    COH_FRESH_CHARACTER_WAIT_OFFER,
    COH_FRESH_CHARACTER_COMPLETE,
    COH_FRESH_CHARACTER_FAILED,
    COH_FRESH_CHARACTER_CANCELLED,
    COH_FRESH_CHARACTER_CLOSED
} CohFreshCharacterPhase;
typedef enum {
    COH_FRESH_CHARACTER_FAILURE_NONE,
    COH_FRESH_CHARACTER_FAILURE_INPUT,
    COH_FRESH_CHARACTER_FAILURE_AUTH,
    COH_FRESH_CHARACTER_FAILURE_SHARD,
    COH_FRESH_CHARACTER_FAILURE_GRANT,
    COH_FRESH_CHARACTER_FAILURE_DB_BEGIN,
    COH_FRESH_CHARACTER_FAILURE_DB,
    COH_FRESH_CHARACTER_FAILURE_LIST,
    COH_FRESH_CHARACTER_FAILURE_CREATE,
    COH_FRESH_CHARACTER_FAILURE_OFFER,
    COH_FRESH_CHARACTER_FAILURE_RETIRE,
    COH_FRESH_CHARACTER_FAILURE_TIMEOUT,
    COH_FRESH_CHARACTER_FAILURE_CANCEL,
    COH_FRESH_CHARACTER_FAILURE_CLOSE
} CohFreshCharacterFailure;
typedef struct {
    CohFreshCharacterPhase phase;
    CohFreshCharacterFailure failure;
    CohStatus status;
    /* Real public controller observations, separated from terminal cleanup. */
    CohLoginState observed_auth_phase, final_auth_phase;
    CohDbSessionPhase observed_db_phase, final_db_phase;
    uint32_t session_generation, receipt_generation, selection_generation;
    unsigned begin_attempted, shard_attempted, bridge_attempted;
    unsigned creation_attempted, retirement_attempted;
    unsigned actual_grant_verified, matching_empty_list_verified;
    unsigned creation_request_queued, allocated_offer_observed;
    unsigned private_offer_retired, container_uninitialized;
    unsigned persistent_allocation_possible;
    unsigned private_name_wiped, bridge_temporaries_wiped;
    unsigned controllers_destroyed, cleanup_cancel_close_used;
    /* Explicit source policy/limits, not observations of a remote predicate. */
    unsigned provisional_development_policy, development_skip_requested;
    unsigned actual_server_development_skip_observed;
    unsigned normal_version_admitted, checksum_reference_admitted;
    unsigned initialized_character, persistent_rollback_claimed;
    unsigned map_socket_opened, map_character_body_sent, sends_ready;
    unsigned sends_received_character, sends_full_update_ack;
    unsigned current_world_verified, actor_publication, world_authority;
} CohFreshCharacterDiagnostics;

/* Single owner thread; no component/controller/list/grant/UID/DBID/cookie or
 * handoff can be supplied or returned. There is no continuation/claim method.
 * Only public CohLogin/CohDbSession/new creation+retire methods are composed.
 * The completed strict empty-list owner is neither called nor cloned.
 *
 * Fixed scope: original encrypted Auth protocol191021, registered shard1 and
 * DB127.0.0.1:7000; private expected fixture identity is compared to the ACTUAL
 * authorization, never minted. Original DB protocol20110614, development
 * no_version_check1, source-labelled dev patch string and required original DH.
 * This does not admit normal client version/checksum or observe server devskip.
 * Map policy requires original positive Atlas Map1 and exact loopback UDP peer;
 * its independent executable/generation/readiness proof belongs to the driver.
 *
 * Borrowed provider/callback objects and their contexts must remain live and
 * immutable through consuming calls/controller destruction and must not alias
 * mutable owner/controller/credential/name/output/destroy-pointer storage.
 * Context extents are undeclared by existing callback APIs: this is a caller
 * precondition, not a claim of transitive pointer/opaque UDP alias detection.
 * Known owner/provider-object spans refuse. Inputs are immutable during calls.
 */
CohFreshCharacterOwner *coh_fresh_character_create(const CohFreshCharacterConfig *);
/* One attempt is consumed BEFORE input validation, copying, allocation or any
 * component call. Account/password are borrowed for this call only. The private
 * new-name copy is1..63 printable ASCII bytes, retained only until the single
 * creation attempt or terminal cleanup, then wiped. No caller slot selector.
 * The owner requires exactly one complete matching all-empty/unlocked list
 * and derives the first available ordinary wire slot from that actual list.
 */
CohStatus coh_fresh_character_begin(CohFreshCharacterOwner *, const char *account,
    const char *password, CohBytes private_new_name, uint64_t now_ms);
/* Nonblocking; total30s/connect3s/reply10s. All methods busy-refuse reentry;
 * diagnostic/destroy outputs remain unchanged, cancel/close do not mutate the
 * busy owner. Poll cancellation immediately before bridge, creation, retirement
 * and scalar success. No retry/rebegin/resume after ANY terminal outcome.
 *
 * Creation is consumed before the public primitive call even if it refuses.
 * Success requires its parser-derived creation-specific offer and successful
 * terminal retirement. Destroy both controllers and wipe new private storage
 * BEFORE publishing COMPLETE. No Map socket is opened or character body sent.
 * container_uninitialized is a source-route inference, not a SQL content read.
 * Queue success makes persistent_allocation_possible true even if later cancel
 * or failure; this owner never claims persistent rollback or database cleanup.
 */
CohStatus coh_fresh_character_service(CohFreshCharacterOwner *, uint64_t now_ms, CohCancel);
CohStatus coh_fresh_character_timeout(CohFreshCharacterOwner *);
CohStatus coh_fresh_character_cancel(CohFreshCharacterOwner *);
CohStatus coh_fresh_character_close(CohFreshCharacterOwner *);
/* The slot holds NULL or a live owner returned by create, never an arbitrary
 * address. Busy refusal preserves it; successful destroy clears it. */
CohStatus coh_fresh_character_destroy(CohFreshCharacterOwner **);
CohStatus coh_fresh_character_diagnostics(const CohFreshCharacterOwner *,
    CohFreshCharacterDiagnostics *);
#ifdef __cplusplus
}
#endif
#endif
