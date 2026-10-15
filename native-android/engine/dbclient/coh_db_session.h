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
    uint64_t login_requests, player_lists, queue_updates, choices, handoffs,
        malformed, unsupported, server_rejections, receipt_rejections,
        suspends, disconnects, timeouts, cancellations;
    CohNetUdpDiagnostics transport;
} CohDbSessionDiagnostics;
typedef struct CohDbSession CohDbSession;
/* All methods are single-owner-thread and nonblocking. All error outputs
 * remain unchanged. Secret buffers are cleared on every terminal transition. */
CohDbSession *coh_db_session_create(const CohDbSessionConfig *);
void coh_db_session_destroy(CohDbSession *);
CohStatus coh_db_session_begin(CohDbSession *, const CohDbLogin *,
    const CohDbAuthReceipt *, uint32_t connect_id, uint64_t now_ms);
CohStatus coh_db_session_service(CohDbSession *, uint64_t now_ms, CohCancel);
CohStatus coh_db_session_players(const CohDbSession *, CohDbPlayers *);
CohStatus coh_db_session_choose(CohDbSession *, uint32_t wire_slot,
    uint32_t local_map_ip, uint32_t create_location, uint64_t now_ms);
/* Exactly one successful take. Starts graceful DB disconnect. Continue
 * service() until CLOSED. Caller owns/erases output and authorizes map peer.
 * selected_dbid is always zero: no DBID is present in the source handoff. */
CohStatus coh_db_session_take_handoff(CohDbSession *, CohDbSessionHandoff *);
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
