#ifndef COH_DBCLIENT_H
#define COH_DBCLIENT_H
#include "../coh_contracts.h"
#include "../auth/coh_auth.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_DB_PROTOCOL_VERSION 20110614u
#define COH_DB_AUTH_BYTES 128u
#define COH_DB_SLOTS_MAX 64u
#define COH_DB_MESSAGE_MAX 65536u
#define COH_DB_LOGIN_MAX 4096u
enum { COH_DB_SEND_PLAYERS=2, COH_DB_MESSAGE=3, COH_DB_MAP_CONNECT=4,
       COH_DB_QUEUE_POSITION=20, COH_DB_LOGIN=2, COH_DB_CHOOSE_PLAYER=3 };
/* Explicit caller-owned, sensitive configuration. Protocol/checksum/version
 * must be authorized for the disposable server. No defaults bypass checks.
 * This module has no logging, sockets or credential persistence. */
typedef struct {
    char account[15], patch_version[128], patch_message[256], system_spec[1024];
    uint32_t user_id, protocol_version, cookie, no_version_check, no_timeout;
    uint8_t auth_user_data[COH_DB_AUTH_BYTES], executable_checksum[16];
    uint32_t keyed_access_level;
    char keyed_access_issued_to[256];
} CohDbLogin;
typedef struct {
    uint32_t slot, local_map_ip, create_location;
    char name[64];
} CohDbChoose;
typedef struct {
    uint32_t wire_slot, level, db_flags, type, subtype, type_by_location,
        praetorian, body_type, skin_color, map_seconds, seconds_till_offline,
        last_online, slot_lock;
    float scale, bone_scale;
    char name[64], player_class[64], origin[64], primary_power[64],
        secondary_power[64], map_name[256];
    uint32_t empty, visitor, invalid;
} CohDbPlayer;
typedef struct {
    uint32_t user_id, nag_going_rogue, beta_shard, vip_shard, base_slots,
        max_slots, bonus_slots, vip, premium_nag, selectable_count;
    /* Remote console command is consumed but NEVER executed or exposed. */
    uint32_t ignored_remote_command;
    CohDbPlayer players[COH_DB_SLOTS_MAX];
    uint8_t auth_user_data[COH_DB_AUTH_BYTES], overridden_auth[COH_DB_AUTH_BYTES];
} CohDbPlayers;
typedef struct { uint32_t position, count; } CohDbQueue;
/* Whole logical packet includes its command. legacy_commands adds the source
 * old NetLink +5 offset. byte_aligned is decompressed packet's profile, not
 * an instruction to inflate zlib. All failure outputs remain unchanged.
 * These functions do not assert server authentication or successful login. */
CohStatus coh_db_login_encode(const CohDbLogin *, int byte_aligned,
    int legacy_commands, uint8_t *, size_t capacity, size_t *bit_length);
/* Development-only source -db login. UID/cookie MUST be zero. It creates
 * no authenticated receipt and is admitted only by begin_local on loopback. */
CohStatus coh_db_local_login_encode(const CohDbLogin *, int byte_aligned,
    int legacy_commands, uint8_t *, size_t capacity, size_t *bit_length);
CohStatus coh_db_choose_encode(const CohDbChoose *, int byte_aligned,
    int legacy_commands, uint8_t *, size_t capacity, size_t *bit_length);
CohStatus coh_db_players_parse(CohBytes, size_t bit_length, int byte_aligned,
    int legacy_commands, CohDbPlayers *);
CohStatus coh_db_queue_parse(CohBytes, size_t bit_length, int byte_aligned,
    int legacy_commands, CohDbQueue *);
/* Whole MAP_CONNECT body adapter to the already-qualified auth handoff
 * parser. Values remain sensitive; caller must authorize the reported map
 * endpoint before opening another socket. */
CohStatus coh_db_map_handoff_parse(CohBytes, size_t bit_length,
    int byte_aligned, int legacy_commands, CohAuthMapHandoff *);
/* Validates and discards the entire source DBGAMESERVER_MSG string. Never
 * returns remote text. A valid error is still a session rejection. */
CohStatus coh_db_server_error_parse(CohBytes, size_t bit_length,
    int byte_aligned, int legacy_commands);
/* Creates a choice only for a nonempty, valid, nonvisitor, unlocked wire slot.
 * No dbid is invented: source SEND_PLAYERS does not carry one. */
CohStatus coh_db_player_choose(const CohDbPlayers *, uint32_t wire_slot,
    uint32_t local_map_ip, uint32_t create_location, CohDbChoose *);
void coh_db_wipe(void *, size_t);
#ifdef __cplusplus
}
#endif
#endif
