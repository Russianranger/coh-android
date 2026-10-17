#ifndef COH_NATIVE_LOCAL_OWNER_H
#define COH_NATIVE_LOCAL_OWNER_H
#include "../dbclient/coh_db_session.h"
#include "../mapclient/coh_mapclient.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Explicit development-only entry to a local UseFakeAuth DbServer. No
 * AuthServer receipt, password, discovery or background reconnection exists.
 * Both DB and returned MapServer endpoints MUST be IPv4 loopback. */
typedef struct {
    CohDbSessionConfig db;
    CohMapConfig map; /* peer ignored until a genuine DB handoff arrives */
    unsigned local_development_enabled; /* exactly 1, explicit caller policy */
} CohLocalConfig;
typedef enum {
    COH_LOCAL_IDLE, COH_LOCAL_DB_CONNECTING, COH_LOCAL_CHARACTERS_READY,
    COH_LOCAL_MAP_CONNECTING, COH_LOCAL_SCENE_INCOMPLETE, COH_LOCAL_CLOSED,
    COH_LOCAL_SUSPENDED, COH_LOCAL_CANCELLED, COH_LOCAL_FAILED,
    COH_LOCAL_TIMED_OUT, COH_LOCAL_UNSUPPORTED
} CohLocalPhase;
typedef struct { uint32_t count, selectable_count; CohDbPlayer players[COH_DB_SLOTS_MAX]; } CohLocalCharacters;
typedef struct {
    CohLocalPhase phase;
    CohDbSessionPhase db_phase;
    CohMapPhase map_phase;
    CohStatus last_status;
    /* The terminal failure phases are captured before cleanup clears active
     * authorization and closes sockets. Current phases still prove cleanup. */
    unsigned terminal_failure;
    CohDbSessionPhase terminal_db_phase;
    CohMapPhase terminal_map_phase;
    CohMapDiagnostics map_protocol;
    uint32_t generation, selection_generation;
    unsigned local_development_auth, server_identity_bound;
    /* Actual retained DBSession handoff owner only; no entity/world authority. */
    unsigned selected_dbid_owner_bound;
    uint64_t attempts, character_lists, character_choices, map_handoffs,
        policy_rejections, failures, suspends, cancellations, opened_sockets,
        closed_sockets;
    /* Numeric state only. No account, character name, UID, cookie, key,
     * server text, packet body or credential appears in this report. */
} CohLocalDiagnostics;
typedef struct CohLocal CohLocal;
/* Default limits and loopback bind; explicit DB peer/port, callback/key
 * policy and development_enabled must be provided before create. */
CohLocalConfig coh_local_default_config(void);
/* Mirrors existing explicitly local -noversioncheck1 launcher policy:
 * protocol check retained; development stamp comparison skipped; no Windows
 * executable checksum is invented for a native binary. Only begin_local may
 * use this policy, with loopback endpoints and explicit development enable. */
CohStatus coh_local_login_policy(CohDbLogin *out);
CohLocal *coh_local_create(const CohLocalConfig *);
void coh_local_destroy(CohLocal *);
/* policy account/user_id/cookie must be zero. Account is bounded ASCII and
 * copied only into the transient login; no password accepted. Fresh nonzero
 * distinct connection IDs must exceed both IDs from prior attempts. */
CohStatus coh_local_begin(CohLocal *, const CohDbLogin *policy,
    const char *account, uint32_t db_connect_id, uint32_t map_connect_id,
    uint64_t now_ms);
CohStatus coh_local_service(CohLocal *, uint64_t now_ms, CohCancel);
/* Optional synchronous diagnostic seam to the actual owned Map receive loan.
 * No observer is installed across service calls. Default service uses NULL.
 * Client/event/reader pointers expire on callback return; do not retain them.
 * Only coh_map_client_scene_lease or the bounded scene-record constructor may
 * use the supplied client during the callback. Other Map calls are forbidden.
 * Local mutations/reentrant service are refused; void mutations are no-ops.
 * Local diagnostics may be read. Copies/record/provider allocations require the
 * caller's complete aggregate budget; no memory is allocated by this seam.
 * Callback result cannot change protocol policy, SCENE_INCOMPLETE, READY or ACK.
 * Actual DB handoff ownership does not establish entity or world authority. */
typedef void (*CohLocalSceneObserver)(void *,const CohMapClient *,
    const CohMapSceneObservation *);
CohStatus coh_local_service_observed(CohLocal *,uint64_t now_ms,CohCancel,
    CohLocalSceneObserver,void *context);
CohStatus coh_local_characters(const CohLocal *, CohLocalCharacters *);
CohStatus coh_local_choose_character(CohLocal *, uint32_t wire_slot,
    uint64_t now_ms);
void coh_local_suspend(CohLocal *);
void coh_local_cancel(CohLocal *);
void coh_local_close(CohLocal *);
void coh_local_diagnostics(const CohLocal *, CohLocalDiagnostics *);
#ifdef __cplusplus
}
#endif
#endif
