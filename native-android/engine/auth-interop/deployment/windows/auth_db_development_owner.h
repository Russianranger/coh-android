/* NONSHIPPING: one fresh Auth -> real-auth DB development-policy experiment. */
#ifndef COH_AUTH_DB_DEVELOPMENT_OWNER_H
#define COH_AUTH_DB_DEVELOPMENT_OWNER_H
#include "../../../login/coh_login.h"
#include "../../../dbclient/coh_db_session.h"
#ifdef __cplusplus
extern "C" {
#endif

typedef struct CohAuthDbDevelopmentOwner CohAuthDbDevelopmentOwner;
typedef struct {
    CohNetEndpoint auth_endpoint; /* Explicit loopback port20000..59999. */
    /* Provider and its context remain immutable and live through destroy.
     * The actual probe selects its independently admitted OpenSSL provider. */
    const CohAuthCrypto *crypto;
    /* Fresh nonzero transport nonce from the actual probe's entropy source;
     * not an account/grant generation or authentication proof. */
    uint32_t connect_id;
    /* Measured actual probe PE MD5; never treated as an admitted reference. */
    uint8_t executable_checksum[16];
} CohAuthDbDevelopmentConfig;
typedef enum {
    COH_AUTH_DB_DEV_IDLE, COH_AUTH_DB_DEV_AUTH, COH_AUTH_DB_DEV_DB,
    COH_AUTH_DB_DEV_COMPLETE, COH_AUTH_DB_DEV_FAILED,
    COH_AUTH_DB_DEV_CANCELLED, COH_AUTH_DB_DEV_CLOSED
} CohAuthDbDevelopmentPhase;
typedef enum {
    COH_AUTH_DB_DEV_FAILURE_NONE, COH_AUTH_DB_DEV_FAILURE_INPUT,
    COH_AUTH_DB_DEV_FAILURE_AUTH, COH_AUTH_DB_DEV_FAILURE_SHARD,
    COH_AUTH_DB_DEV_FAILURE_GRANT, COH_AUTH_DB_DEV_FAILURE_DB_BEGIN,
    COH_AUTH_DB_DEV_FAILURE_DB, COH_AUTH_DB_DEV_FAILURE_LIST,
    COH_AUTH_DB_DEV_FAILURE_TIMEOUT, COH_AUTH_DB_DEV_FAILURE_CANCEL
} CohAuthDbDevelopmentFailure;
typedef struct {
    CohAuthDbDevelopmentPhase phase;
    CohAuthDbDevelopmentFailure failure;
    CohStatus status;
    /* Last real phases before controllers are destroyed; no reconstruction. */
    CohLoginState auth_phase;
    CohDbSessionPhase db_phase;
    CohLoginState auth_final_phase;
    CohDbSessionPhase db_final_phase;
    unsigned begun, grant_consumed, selected_shard_verified;
    unsigned complete_matching_list, all_slots_empty_unlocked;
    unsigned cleanup_cancel_close_used, controllers_destroyed;
    uint32_t slots, base_slots, bonus_slots;
    uint64_t auth_frames, db_login_requests, db_player_lists;
    uint64_t db_queue_updates, db_unsupported, db_choices, db_handoffs;
    /* Explicit experiment policy. These do not prove the remote server used it. */
    unsigned development_skip_requested;
    unsigned normal_version_admitted, checksum_reference_admitted;
    unsigned character_selected, map_handoff_verified, current_world_verified;
} CohAuthDbDevelopmentDiagnostics;

/* Single owner thread. No grant, UID, cookie, DBID, receipt, player names,
 * raw packet or controller can be supplied or exported through this API.
 * One begin ATTEMPT per owner, including invalid input and failed allocation.
 * No retry/resume/reuse after failure, cancellation, timeout or close.
 * Fixed scope: Auth protocol191021, shard1/127.0.0.1:7000, private fixture UID,
 * original DB protocol20110614, original development no_version_check=1,
 * encryption_required=1 and fresh original session DH; no fake-auth DB begin.
 * AUTHORIZED is a frozen completed receipt, not a revocation/TTL monitor.
 * The DB copied-message profile stays bounded to16KiB, including decoded data.
 * Configuration and credentials are immutable during their consuming call.
 * The provider/context and callback/context must not overlap mutable owner,
 * controller, credential, output or destroy-pointer storage; their context
 * sizes are not declared by these existing callback APIs and are a caller
 * precondition. Known owner/provider-object alias spans are rejected here.
 */
CohAuthDbDevelopmentOwner *coh_auth_db_development_create(
    const CohAuthDbDevelopmentConfig *);
CohStatus coh_auth_db_development_begin(CohAuthDbDevelopmentOwner *,
    const char *account, const char *password, uint64_t now_ms);
/* Nonblocking; fixed total30s/connect3s/reply10s limits. Cancel is checked
 * before bridge creation and before public success. Callback reentry into any
 * method is refused/no-op. Caller must not destroy the owner in a callback. */
CohStatus coh_auth_db_development_service(CohAuthDbDevelopmentOwner *,
    uint64_t now_ms, CohCancel);
/* Active-only fixed timeout/cancel. Close destroys retained controllers and
 * secrets without manufacturing success; terminal cause/phase snapshots stay.
 * Complete matching empty/unlocked SEND_PLAYERS is followed by intentional
 * cancel-close only when player_lists==1 and queue_updates/unsupported/choices/
 * handoffs==0, slots>0 and every slot is EMPTY/unlocked/nonvisitor/noninvalid.
 * No second list or independent service is silently admitted by this owner.
 * The complete source list and both auth arrays are parsed by the existing DB
 * controller; the private list copy is wiped and only counts survive.
 * Success is followed by intentional
 * cancel-close and destruction of BOTH controllers before COMPLETE publication.
 * This is not a graceful peer-disconnect acknowledgement. There is no choose,
 * creation, handoff, Map, actor or whole-character/ACK API.
 */
CohStatus coh_auth_db_development_timeout(CohAuthDbDevelopmentOwner *);
CohStatus coh_auth_db_development_cancel(CohAuthDbDevelopmentOwner *);
CohStatus coh_auth_db_development_close(CohAuthDbDevelopmentOwner *);
/* Busy refusal leaves *owner unchanged. Successful destroy clears *owner. */
CohStatus coh_auth_db_development_destroy(CohAuthDbDevelopmentOwner **owner);
/* Transactional scalar output; no private grant/list/controller data. */
CohStatus coh_auth_db_development_diagnostics(const CohAuthDbDevelopmentOwner *,
    CohAuthDbDevelopmentDiagnostics *);
#ifdef __cplusplus
}
#endif
#endif
