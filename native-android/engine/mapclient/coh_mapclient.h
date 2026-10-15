#ifndef COH_ENGINE_MAPCLIENT_H
#define COH_ENGINE_MAPCLIENT_H
#include "../auth/coh_auth.h"
#include "../network/coh_net_udp.h"
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Source Common/comm_game.h, COMM_MAX_CMD=2. Old command profiles add five.
 * byte_aligned describes the DECOMPRESSED payload profile, not zlib input. */
enum { COH_MAP_INPUT=2, COH_MAP_REQSCENE=3, COH_MAP_REQSHORTCUTS=4,
    COH_MAP_REQALLENTS=5, COH_MAP_READY=6, COH_MAP_CONNECT=9 };
typedef struct { unsigned legacy_commands, byte_aligned; } CohMapProfile;
#define COH_MAP_PACKET_MAX 128u
typedef struct { uint8_t data[COH_MAP_PACKET_MAX]; uint32_t bits; } CohMapPacket;
typedef struct {
    uint32_t cookie, cod, console_open, initial_login;
    const uint8_t *password_md5; /* borrowed 16-byte secret; READY only */
} CohMapFields;
/* Existing characters only: CONNECT emits newCharacter=0. No DBID or link ID
 * is emitted in place of the map cookie. READY output is sensitive; caller
 * must wipe it after queueing. Failed calls preserve output. */
CohStatus coh_map_serialize(unsigned command, CohMapProfile,
    const CohMapFields *, CohMapPacket *);
void coh_map_packet_wipe(CohMapPacket *);

typedef enum { COH_MAP_IDLE, COH_MAP_NET_CONNECTING, COH_MAP_WAIT_CONNECT,
    COH_MAP_WAIT_SHORTCUTS, COH_MAP_WAIT_SCENE, COH_MAP_SCENE_INCOMPLETE,
    COH_MAP_DISCONNECTING, COH_MAP_CLOSED, COH_MAP_SUSPENDED,
    COH_MAP_TIMED_OUT, COH_MAP_FAILED } CohMapPhase;
/* There is deliberately no LIVE state. The pinned replication parser reads
 * scene/entity prefixes only. This controller NEVER sends REQALLENTS, READY,
 * ACK_FULL_UPDATE or RECEIVED_CHARACTER after prefix-only acceptance. */
typedef struct {
    CohNetUdpConfig udp;
    uint64_t application_timeout_ms;
    unsigned message_budget; /* 1..16 per service call */
    unsigned cod;
} CohMapConfig;
typedef struct {
    /* Caller authorization from a completed AuthServer path, or the explicit
     * loopback development path below. Neither field creates acceptance evidence. */
    int authenticated, endpoint_authorized;
    /* Explicit source UseFakeAuth mode: never evidence of AuthServer login.
     * Mutually exclusive with authenticated; loopback-only, unknown DBID. */
    int local_development_authorized;
    uint32_t selected_slot, selection_generation;
    uint32_t selected_dbid; /* optional: 0 when DB protocol did not supply one */
    CohAuthMapHandoff handoff;
    unsigned address_index; /* 0 or 1, must match config UDP peer */
} CohMapAuthorization;
/* Numeric parser checkpoints distinguish transport capacity, command parsing,
 * complete handshake parsing and deliberate incomplete replication. */
typedef enum { COH_MAP_STAGE_NONE, COH_MAP_STAGE_UDP_SERVICE,
    COH_MAP_STAGE_MESSAGE_NEXT, COH_MAP_STAGE_COMMAND,
    COH_MAP_STAGE_CONNECT, COH_MAP_STAGE_SHORTCUTS,
    COH_MAP_STAGE_SCENE_PREFIX, COH_MAP_STAGE_ENTITY_PREFIX,
    COH_MAP_STAGE_SEND_COMMAND, COH_MAP_STAGE_APPLICATION_TIMEOUT } CohMapStage;
typedef struct {
    CohMapPhase phase;
    CohMapStage stage;
    CohStatus last_status;
    uint32_t last_command, last_payload_bits;
    unsigned last_command_valid, last_byte_aligned;
    uint32_t selected_slot, selection_generation, selected_dbid;
    uint32_t map_id, map_link_id, generation;
    unsigned local_development_authorized;
    unsigned character_identity_verified; /* always0 until complete own-entity decode */
    uint64_t accepted_messages, rejected_messages, malformed, unsupported;
    uint64_t scene_prefixes, entity_prefixes, disconnects, suspends, timeouts;
    CohRepPhase inspector_phase;
    CohNetUdpDiagnostics udp;
    /* No account, password, key, cookie, body or remote error string. */
} CohMapDiagnostics;
typedef struct CohMapClient CohMapClient;
CohStatus coh_map_config_validate(const CohMapConfig *);
CohMapClient *coh_map_client_create(const CohMapConfig *);
void coh_map_client_destroy(CohMapClient *);
/* A new authorization is mandatory after suspend/disconnect/failure. A fresh
 * transport connect_id is mandatory on reuse. Single owner thread; no DNS,
 * discovery, credential access, JNI, blocking waits or implicit retries. */
CohStatus coh_map_client_begin(CohMapClient *, const CohMapAuthorization *,
    uint32_t connect_id, uint64_t now_ms);
CohStatus coh_map_client_service(CohMapClient *, uint64_t now_ms, CohCancel);
CohStatus coh_map_client_disconnect(CohMapClient *, uint64_t now_ms);
void coh_map_client_suspend(CohMapClient *);
void coh_map_client_close(CohMapClient *);
/* Exposes only the bound local endpoint, useful for an authorized socket host.
 * It never exposes the borrowed auth handoff cookie or session material. */
CohStatus coh_map_client_local_endpoint(const CohMapClient *, CohNetEndpoint *);
void coh_map_client_diagnostics(const CohMapClient *, CohMapDiagnostics *);
#ifdef __cplusplus
}
#endif
#endif
