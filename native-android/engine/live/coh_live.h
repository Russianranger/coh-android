#ifndef COH_NATIVE_LIVE_OWNER_H
#define COH_NATIVE_LIVE_OWNER_H
#include "../login/coh_login.h"
#include "../dbclient/coh_db_session.h"
#include "../mapclient/coh_mapclient.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Single thread owns all methods/callbacks. Callback must not reenter owner.
 * An explicit map selection invokes policy on a public endpoint only. It
 * never receives a cookie, account, key or raw server packet. */
typedef CohStatus (*CohLiveMapPolicy)(void *, CohNetEndpoint, uint32_t auth_generation);
typedef struct {
    CohLoginConfig login;
    CohNetEndpoint authorized_auth;
    CohDbSessionConfig db; /* Peer must equal the explicitly selected auth shard. */
    CohMapConfig map; /* udp.peer ignored; populated only after map policy approval. */
    CohLiveMapPolicy approve_map;
    void *policy_context;
} CohLiveConfig;
typedef enum { COH_LIVE_IDLE, COH_LIVE_AUTHENTICATING, COH_LIVE_SHARDS_READY,
    COH_LIVE_DB_CONNECTING, COH_LIVE_CHARACTERS_READY, COH_LIVE_MAP_APPROVAL,
    COH_LIVE_MAP_CONNECTING, COH_LIVE_SCENE_INCOMPLETE, COH_LIVE_CLOSED,
    COH_LIVE_SUSPENDED, COH_LIVE_CANCELLED, COH_LIVE_FAILED,
    COH_LIVE_TIMED_OUT, COH_LIVE_UNSUPPORTED } CohLivePhase;
/* Names are UI content, excluded from diagnostics. No auth arrays escape. */
typedef struct { uint32_t count, selectable_count; CohDbPlayer players[COH_DB_SLOTS_MAX]; } CohLiveCharacters;
typedef struct {
    CohLivePhase phase;CohLoginState auth_state;CohDbSessionPhase db_phase;CohMapPhase map_phase;
    uint32_t authentication_generation, selection_generation;
    uint64_t attempts, auth_receipts, shard_choices, character_choices,
        map_approvals, policy_rejections, failures, suspends, cancellations,
        closed_sockets, opened_sockets;
    CohStatus last_status;
    /* No account/password, key, session, cookie, endpoint, body or remote text. */
} CohLiveDiagnostics;
typedef struct CohLive CohLive;
CohLive *coh_live_create(const CohLiveConfig *);
void coh_live_destroy(CohLive *);
/* No external authenticated receipt can be injected. Fresh credentials and
 * fresh nonzero distinct connection IDs, each greater than both IDs from the
 * previous attempt, are required (no wraparound within this owner lifetime).
 * db_policy.account/user_id/cookie must be zero and are populated exclusively
 * from the completed AuthServer protocol result. Other version/checksum/auth
 * userdata fields are explicit server-policy inputs and are never weakened.
 * begin never retries/replays credentials after failure or foreground return. */
CohStatus coh_live_begin(CohLive *, const CohDbLogin *db_policy,
    const char *account, const char *password, uint32_t subscription,
    uint16_t platform_flags, uint32_t db_connect_id, uint32_t map_connect_id,
    uint64_t now_ms);
CohStatus coh_live_service(CohLive *, uint64_t now_ms, CohCancel);
CohStatus coh_live_shards(const CohLive *, CohAuthShards *);
CohStatus coh_live_choose_shard(CohLive *, uint8_t shard_id, uint64_t now_ms);
CohStatus coh_live_characters(const CohLive *, CohLiveCharacters *);
CohStatus coh_live_choose_character(CohLive *, uint32_t wire_slot,
    uint32_t local_map_ip, uint32_t create_location, uint64_t now_ms);
/* Only public numeric addresses/ports; cookie stays owned and private. */
CohStatus coh_live_map_candidates(const CohLive *, CohNetEndpoint out[2]);
CohStatus coh_live_choose_map(CohLive *, unsigned address_index, uint64_t now_ms);
void coh_live_suspend(CohLive *);
void coh_live_cancel(CohLive *);
void coh_live_close(CohLive *);
void coh_live_diagnostics(const CohLive *, CohLiveDiagnostics *);
#ifdef __cplusplus
}
#endif
#endif
