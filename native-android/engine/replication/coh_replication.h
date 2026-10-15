#ifndef COH_REPLICATION_H
#define COH_REPLICATION_H
#include "../coh_contracts.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Source Common/comm_game.h and net_structdefs.h. These are normalized IDs.
 * Old NetLink profiles use wire ID = normalized ID + 5. */
enum { COH_REP_UPDATE=2, COH_REP_ALLENTS=3, COH_REP_SHORTCUTS=4,
    COH_REP_CONNECT_MSG=5, COH_REP_GROUPS=6 };
#define COH_REP_MESSAGE_MAX 16384u
#define COH_REP_SHORTCUT_MAX 256u
/* This list is sent separately from the 35-entry source shortcut schema.
 * The pinned server_cmds producer contains at most 915 command names. Stream
 * and discard up to 1024 names within the existing 16KiB message bound. */
#define COH_REP_ACCESSIBLE_COMMAND_MAX 1024u
#define COH_REP_NAME_MAX 256u
/* Decompressed payload, including the command. compressed=1 means the source
 * byteAlignedMode (rounded scalar widths and 32-bit packed integers), not zlib
 * input. No pointers, socket handles or secrets are retained. */
typedef struct { CohBytes bytes; size_t bits, cursor; unsigned compressed; } CohRepReader;
typedef struct { uint16_t id; uint8_t kind; } CohRepShortcut;
typedef struct { CohRepShortcut entries[COH_REP_SHORTCUT_MAX]; size_t count, accessible_commands; } CohRepSchema;
typedef struct { uint32_t accepted; float timezone_delta; } CohRepConnect;
typedef struct {
    uint32_t undo_count, redo_count, new_world, mission_map, instance_id,
        no_auto_group, base_map_id, intro_zone, team_area, page_count;
    char loadscreen[COH_REP_NAME_MAX], map_path[COH_REP_NAME_MAX];
    uint32_t beacons_loaded;
    size_t group_tail_bit; /* Group files and reference records remain unparsed. */
} CohRepScenePrefix;
typedef struct {
    uint32_t command, full_update_id, odd_send, abs_time, db_seconds,
        has_debug_info, interp_level, interp_precision, command_count;
    size_t entity_tail_bit; /* Not proof that entities/character tails are valid. */
} CohRepUpdatePrefix;
/* Per-bit position ID ordering matches entGetPosition. Defaults are the source
 * entity.c center (0,0,0), not an asserted authoritative spawn. */
typedef struct {
    uint32_t packed[3], packet_ids[24];
    CohVec3 position;
    uint32_t valid;
} CohRepPosition;
typedef struct { uint32_t position_changed, has_id, net_id; CohVec3 position, velocity; } CohRepPhysics;
typedef enum { COH_REP_DISCONNECTED, COH_REP_WAIT_MAP, COH_REP_MAP_CONNECTED,
    COH_REP_SCENE_PREFIX_SEEN, COH_REP_ENTITY_PREFIX_SEEN } CohRepPhase;
/* This inspector deliberately has no LIVE state. Complete scene/entity and
 * selected character validation is required before a render adapter can use
 * live data. Prefix acceptance never emits a spawn, ACK_FULL_UPDATE, READY or
 * RECEIVED_CHARACTER. */
typedef struct {
    CohRepPhase phase; uint32_t selected_dbid, generation, schema_generation;
    uint64_t messages, malformed, unsupported, disconnects;
    CohRepScenePrefix scene; CohRepUpdatePrefix update;
} CohRepSession;
CohStatus coh_rep_reader(CohRepReader *, CohBytes, size_t bits, int compressed);
CohStatus coh_rep_read(CohRepReader *, unsigned width, uint32_t *);
CohStatus coh_rep_pack(CohRepReader *, unsigned width, uint32_t *);
CohStatus coh_rep_string(CohRepReader *, char *, size_t capacity);
/* Standalone body parsers; cursor/output/schema unchanged on error. All full
 * command dispatch requires profile remapping below. */
CohStatus coh_rep_connect(CohRepReader *, CohRepConnect *);
CohStatus coh_rep_shortcuts(CohRepReader *, CohRepSchema *);
CohStatus coh_rep_scene_prefix(CohRepReader *, CohRepScenePrefix *);
CohStatus coh_rep_update_prefix(CohRepReader *, const CohRepSchema *, uint32_t command, CohRepUpdatePrefix *);
void coh_rep_position_init(CohRepPosition *);
/* Starts exactly at entGetPosition, NOT at a complete entity record. */
CohStatus coh_rep_position(CohRepReader *, uint32_t packet_id, CohRepPosition *);
/* Starts exactly at playerReceiveServerPhysicsPositions; optional recording
 * tail is rejected because its nested schema is not supported. */
CohStatus coh_rep_physics(CohRepReader *, CohRepPhysics *);
void coh_rep_session_init(CohRepSession *);
CohStatus coh_rep_session_begin(CohRepSession *, uint32_t selected_dbid);
void coh_rep_session_disconnect(CohRepSession *);
/* link_authenticated is the caller's real Gate26 authorization result. A false
 * value always rejects. This is an integration guard, never authentication. */
CohStatus coh_rep_session_message(CohRepSession *, CohRepSchema *, CohBytes,
    size_t bits, int compressed, int legacy_commands, int link_authenticated);
#ifdef __cplusplus
}
#endif
#endif
