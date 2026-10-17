#ifndef COH_ENGINE_MAPCLIENT_H
#define COH_ENGINE_MAPCLIENT_H
#include "../auth/coh_auth.h"
#include "../network/coh_net_udp.h"
#include "../replication/coh_replication.h"
#include "../replication/coh_groups.h"
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
/* There is deliberately no LIVE state. Normal GROUPS structural traversal
 * does not resolve the imported asset graph or own-entity identity. This
 * controller NEVER sends REQALLENTS, READY, ACK_FULL_UPDATE or
 * RECEIVED_CHARACTER after structural inspection. */
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
     * Mutually exclusive with authenticated; loopback-only. An expected DBID
     * may come from a source-qualified owned DBSession handoff, independently
     * of encrypted authentication. Generic raw link_id is not that proof. */
    int local_development_authorized;
    uint32_t selected_slot, selection_generation;
    uint32_t selected_dbid; /* optional positive INT32; 0 when unestablished */
    CohAuthMapHandoff handoff;
    unsigned address_index; /* 0 or 1, must match config UDP peer */
} CohMapAuthorization;
/* Numeric parser checkpoints distinguish transport capacity, command parsing,
 * complete handshake parsing and deliberate incomplete replication. */
typedef enum { COH_MAP_STAGE_NONE, COH_MAP_STAGE_UDP_SERVICE,
    COH_MAP_STAGE_MESSAGE_NEXT, COH_MAP_STAGE_COMMAND,
    COH_MAP_STAGE_CONNECT, COH_MAP_STAGE_SHORTCUTS,
    COH_MAP_STAGE_SCENE_PREFIX, COH_MAP_STAGE_ENTITY_PREFIX,
    COH_MAP_STAGE_SEND_COMMAND, COH_MAP_STAGE_APPLICATION_TIMEOUT,
    COH_MAP_STAGE_SCENE_STRUCTURE } CohMapStage;
typedef struct {
    CohMapPhase phase;
    CohMapStage stage;
    CohStatus last_status;
    uint32_t last_command, last_payload_bits;
    /* Bounded owned Map-body diagnostics only; no bytes are retained here.
     * scene_decoded_bytes changes only after a valid GROUPS prefix. */
    uint32_t last_decoded_bytes, scene_decoded_bytes;
    unsigned last_command_valid, last_byte_aligned;
    uint32_t selected_slot, selection_generation, selected_dbid;
    uint32_t map_id, map_link_id, generation;
    unsigned local_development_authorized;
    unsigned character_identity_verified; /* always0 until complete own-entity decode */
    uint64_t accepted_messages, rejected_messages, malformed, unsupported;
    uint64_t scene_prefixes, entity_prefixes, disconnects, suspends, timeouts;
    uint64_t scene_structures;
    /* Last completely inspected normal GROUPS structure; transactional on
     * failure. The separate failure checkpoint is numeric and owns no input.
     * Footer CRCs are observed source fields, not verified asset checksums. */
    CohGroupsInspection scene_inspection;
    CohGroupsFailure scene_failure;
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
/* Optional synchronous observation after complete normal GROUPS inspection.
 * reader starts immediately after the normalized command in the exact owned
 * decoded message; cursor/bits/alignment retain their original representation.
 * All pointers, including the event, expire when the callback returns. The
 * callback must not modify input, retain pointers or reenter any client method except the lease getter below.
 * It may copy/prepare under its own explicit aggregate memory/work budget;
 * callback allocations and retained copies are NOT charged by this controller.
 * Called at most message_budget times per service, never for a failed parse.
 * This is a receive observation, not a catalog/CRC/actor/world permit. Numeric
 * selection fields retain their existing provisional scope (DBID may be zero).
 * The service result, SCENE_INCOMPLETE and outgoing command policy are unchanged.
 * No observer is installed or retained across calls; the default service passes
 * NULL. Neither this seam nor callback return can cause READY/application ACK. */
typedef struct {
    CohRepReader reader;
    CohGroupsInspection inspection;
    uint32_t map_generation, selection_generation, selected_slot, selected_dbid;
    uint32_t map_id, map_link_id;
    unsigned local_development_authorized;
} CohMapSceneObservation;
typedef void (*CohMapSceneObserver)(void *, const CohMapSceneObservation *);
CohStatus coh_map_client_service_observed(CohMapClient *, uint64_t now_ms,
    CohCancel, CohMapSceneObserver, void *context);
/* Actual-current receive loan, never a durable session or source-generation
 * certificate. Getter succeeds only inside this client's current scene callback
 * for its EXACT event address and original reader representation. It derives all
 * fields from the opaque client and actual decoded network loan; caller supplies
 * no replacement labels. Output is a value copy; reader bytes still expire on
 * callback return. Copy bytes under an explicit budget before returning.
 * Only this getter may be called from the callback; all other client reentry
 * remains forbidden. Known client/event/message/payload spans must be disjoint
 * from output. Failure leaves output unchanged. Selected DBID provenance remains
 * unbound for legacy raw begin authorization, even when positive. Connection ID
 * and message generations are local correlation observations, not secrets or
 * durable identity tokens. No ACK, authentication, actor or world permit. */
typedef struct {
 CohRepReader reader;CohGroupsInspection inspection;
 uint64_t message_generation;
 uint32_t message_id,ordered_id,connection_id,transport_version;
 uint32_t map_generation,selection_generation,selected_slot,selected_dbid,map_id,map_link_id;
 unsigned ordered,local_development_authorized;
 unsigned selected_dbid_owner_bound,source_generation_admitted,world_authority;
} CohMapSceneLease;
CohStatus coh_map_client_scene_lease(const CohMapClient *,const CohMapSceneObservation *,
 CohMapSceneLease *);
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
