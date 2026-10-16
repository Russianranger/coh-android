#ifndef COH_ENTITIES_H
#define COH_ENTITIES_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_ENT_INDEX_MAX 10239u
#define COH_ENT_GENERATION_MAX 2147483647u
#define COH_ENT_DELETE_MAX 256u
#define COH_ENT_TRIGGER_MAX 16u
#define COH_ENT_LIST_MAX 256u
#define COH_ENT_PLACATE_MAX 32u
#define COH_ENT_STATUS_MAX 16u
#define COH_ENT_INVENTORY_TYPES 5u
#define COH_ENT_NETFX_MAX 32u
/* All state here is uncommitted inspection/staging state. A valid record is not
 * a valid ALLENTS/UPDATE packet, resolved appearance, or a renderable actor. */
typedef enum {
    COH_ENT_STAGE_CREATE=1, COH_ENT_STAGE_IDENTITY, COH_ENT_STAGE_PET_POWER,
    COH_ENT_STAGE_CREATE_STRINGS, COH_ENT_STAGE_STATE, COH_ENT_STAGE_POSITION,
    COH_ENT_STAGE_INTERPOLATION, COH_ENT_STAGE_ORIENTATION, COH_ENT_STAGE_SEQUENCE,
    COH_ENT_STAGE_NETFX, COH_ENT_STAGE_APPEARANCE, COH_ENT_STAGE_POWER_CUSTOM,
    COH_ENT_STAGE_TITLES, COH_ENT_STAGE_RAGDOLL, COH_ENT_STAGE_CHARACTER_STATS,
    COH_ENT_STAGE_VISION, COH_ENT_STAGE_RARE_TAIL, COH_ENT_STAGE_BUFFS,
    COH_ENT_STAGE_DELETES, COH_ENT_STAGE_LIST, COH_ENT_STAGE_FULL_UPDATE_TAIL,
    COH_ENT_STAGE_OWNERSHIP, COH_ENT_STAGE_TARGET, COH_ENT_STAGE_STATUS,
    COH_ENT_STAGE_INVENTORY, COH_ENT_STAGE_ATTRIBUTE_SCHEMA, COH_ENT_STAGE_COSTUME_DICTIONARY,
    COH_ENT_STAGE_COSTUME_BODY, COH_ENT_STAGE_CUSTOM_COSTUME,
    COH_ENT_STAGE_TASKFORCE_ARCHITECT, COH_ENT_STAGE_TASKFORCE_PARAMETERS
} CohEntStage;
typedef struct { CohStatus status; CohEntStage stage; size_t bit; } CohEntFailure;
typedef struct {
    uint32_t create, end, entity_id, type, is_self, access_level, dbid,
        owner_index, creator_index, commandable_pet, visible_pet, dismissable_pet,
        special_power_state, pet_power_crc, critter_form, class_index, origin_index,
        player_type, player_subtype, praetorian_progress, player_type_location,
        fade_in, in_phase, random_seed, rank, detail_id, contact_handle;
    char name[256];
    size_t end_bit;
} CohEntCreate;
typedef struct { float quaternion[4]; uint32_t packet_ids[3], valid; } CohEntOrientation;
typedef struct { uint32_t index, entity_id; } CohEntDelete;
typedef struct { uint32_t count; CohEntDelete entries[COH_ENT_DELETE_MAX]; size_t end_bit; } CohEntDeletes;
/* Values remain unresolved references. A known costume index or power CRC
 * does not validate its dictionary or any rig/material resource generation. */
typedef struct {
    uint32_t type, npc_index, costume_index, packet_id, translucency, translucency_packet;
    char sequence_name[260], world_group[260];
} CohEntAppearance;
typedef struct {
    uint32_t packet_id, target, assist, taunter, clear_target, count;
    uint32_t placates[COH_ENT_PLACATE_MAX];
} CohEntTarget;
typedef struct {
    uint32_t packet_id, effects, vision_phases, exclusive_vision_phase, count;
    char descriptions[COH_ENT_STATUS_MAX][128];
} CohEntStatusEffects;
typedef struct {
    uint32_t valid, count, total[COH_ENT_INVENTORY_TYPES], used[COH_ENT_INVENTORY_TYPES],
        auction_total, boost_total;
} CohEntInventorySizes;
/* Standalone title metadata; exact source string capacities. Integer fields
 * preserve wire bits and do not resolve badge/title dictionaries. The owning
 * entity generation must reset this state; packet_id alone is not identity. */
typedef struct {
    uint32_t valid, packet_id, title_the, colors[2], badge, glowie_unlocked,
        gender, name_gender, attach_article, respec_tokens, turnstile_event,
        turnstile_mission, helper_status;
    char name[128], the_text[10], common[32], origin[32], special[128];
} CohEntTitles;
/* Source schema order is translated to these stable named offsets.
 * Attribute IDs: HP, absorb, endurance, meter, perception, stealth, confused,
 * to-hit. Integer IDs: level, combat level, XP, debt, rested XP, influence. */
typedef struct {
    float current[8], maximum[8];
    uint32_t current_packets[8], maximum_packets[8], integer_packets[6];
    uint32_t current_valid, maximum_valid, integer_valid;
    int32_t integers[6];
} CohEntCharacterStats;
typedef struct {
    CohEntCreate identity;
    CohEntCharacterStats stats;
    CohEntAppearance appearance;
    CohEntTarget target;
    CohEntStatusEffects status_effects;
    CohEntInventorySizes inventory;
    uint32_t combat_mod_shift;
    CohRepPosition position;
    CohEntOrientation orientation;
    uint32_t index, present, create_packet, delete_packet, deleted_entity_id,
        state_mode, state_packet, sequence_index, sequence_ticks, sequence_bits,
        sequence_packet, vision_phases, exclusive_vision_phase, con_yellow;
} CohEntSlot;
typedef struct { uint32_t index, ticks, fx_id; } CohEntTrigger;
/* Unresolved network effect events, not live renderer effect instances.
 * Origin/target type 0=entity, 1=position; zero entity means source/no target.
 * Packet ownership must retain these in its transaction if effects are used. */
typedef struct {
    uint32_t command, net_id, pitch_to_target, power_type_flags, handle,
        has_color_tint, primary_color, secondary_color, client_timer, trigger_fx,
        power, debris, origin_type, origin_entity, bone_id, target_type, target_entity;
    float duration, radius, origin_position[3], target_position[3];
} CohEntNetFx;
typedef struct {uint32_t count;CohEntNetFx entries[COH_ENT_NETFX_MAX];size_t end_bit;} CohEntNetFxList;
typedef struct {
    CohEntNetFxList netfx;
    CohEntCreate identity; uint32_t rare, medium_rare, very_rare,
        pchar_things, trigger_count, appearance_type, ragdoll_bones;
    CohEntTrigger triggers[COH_ENT_TRIGGER_MAX]; size_t end_bit;
} CohEntRecord;
typedef struct {
    uint32_t count, self_index, self_entity_id, self_dbid;
    size_t end_bit;
} CohEntList;
/* Caller-owned bounded scratch (sizeof must be queried), intended for an arena/heap/static
 * owner rather than the call stack. Its contents are unspecified on failure;
 * it never contains committed game or render state. */
typedef struct {
    CohEntSlot slots[COH_ENT_LIST_MAX];
    uint32_t visited[COH_ENT_LIST_MAX];
} CohEntListWorkspace;
/* Source delta-index arithmetic, explicitly modulo 2^32; previous starts at
 * -1. Source append passes can descend. This helper admits candidates 0..MAX;
 * only coh_ent_list recognizes the sentinel after the maximum slot. */
CohStatus coh_ent_next_index(CohRepReader *, int32_t previous, uint32_t *, CohEntFailure *);
/* This is the checkEntCreate grammar including its create and sentinel bits.
 * It starts after the delta index. It does not read the entity's later body.
 * self ownership must match the selected DBID before any successful output. */
CohStatus coh_ent_create(CohRepReader *, uint32_t selected_dbid,
    CohEntCreate *, CohEntFailure *);
void coh_ent_orientation_init(CohEntOrientation *);
CohStatus coh_ent_orientation(CohRepReader *, uint32_t packet_id,
    CohEntOrientation *, CohEntFailure *);
void coh_ent_slot_init(CohEntSlot *, uint32_t index);
/* Standalone source substructures; transactional and unresolved staging only.
 * Target includes its update flag, status starts at character_ReceiveStatusEffects
 * (after its outer update flag), inventory includes the packed valid flag.
 * Stale target/status packets are fully consumed but leave prior values intact.
 * Inventory follows the original unversioned stream semantics. */
/* Complete bounded original NetFX substructure, including zero count.
 * Atomic output; no event execution, dictionary resolution or acknowledgments. */
CohStatus coh_ent_netfx(CohRepReader *, CohEntNetFxList *, CohEntFailure *);
CohStatus coh_ent_appearance(CohRepReader *, uint32_t packet_id,
    CohEntAppearance *, CohEntFailure *);
/* Decodes pinned basic (self_schema=0) or self (self_schema=1) absolute
 * non-debug ParserRecv schema. Unknown fields, duplicate fields, removed
 * embedded structs and relative substructures fail closed. Atomic per-field
 * packet ordering; this is statistics only, never a character transaction. */
CohStatus coh_ent_character_stats(CohRepReader *, uint32_t packet_id,
    uint32_t self_schema, CohEntCharacterStats *, CohEntFailure *);
CohStatus coh_ent_target(CohRepReader *, uint32_t packet_id, uint32_t is_self,
    CohEntTarget *, CohEntFailure *);
CohStatus coh_ent_status_effects(CohRepReader *, uint32_t packet_id,
    CohEntStatusEffects *, CohEntFailure *);
CohStatus coh_ent_inventory_sizes(CohRepReader *, CohEntInventorySizes *, CohEntFailure *);
/* Includes the source presence flag. Absent titles retain prior state; present
 * stale packets are fully validated then discarded. Equal packet IDs apply,
 * matching entReceive's titles-specific '<' test. Rejects oversized strings
 * instead of legacy truncation. Reader/state are atomic on every error.
 * Only caller-owned transaction staging; no record or actor publication. */
CohStatus coh_ent_titles(CohRepReader *, uint32_t packet_id, CohEntTitles *, CohEntFailure *);
/* Reads one complete supported entity record. In/out slot is STAGING ONLY.
 * Unsupported branch, malformed input, or identity failure leaves reader,
 * slot and record unchanged; failure receipt is diagnostic only.
 * Unknown update indices fail closed, rather than inventing original dummy
 * entities. A stale generation returns COH_STATE. No external game callbacks. */
CohStatus coh_ent_record(CohRepReader *, uint32_t selected_dbid,
    uint32_t packet_id, uint32_t interp_level, CohEntSlot *,
    CohEntRecord *, CohEntFailure *);
/* Complete supported entity-list substructure, starting at its first delta
 * and ending immediately after the canonical delta=0/create=1/end=1 sentinel.
 * slots is the caller's complete bounded staging table, with fixed unique
 * indices (including tombstones); unmentioned slots retain their values.
 * Missing slots fail rather than creating a dummy. Reader, slots, and result
 * commit only when every record and global selected/self ownership validate.
 * At most one live self player may exist; zero self is a valid list fragment,
 * explicitly reported as self_index=0 and never establishes player authority.
 * Workspace, reader, table, result, and failure must not alias one another.
 * This does not read subsequent control/deletes/character/global tails. */
CohStatus coh_ent_list(CohRepReader *, uint32_t selected_dbid,
    uint32_t packet_id, uint32_t interp_level, CohEntSlot *, size_t count,
    CohEntListWorkspace *, CohEntList *, CohEntFailure *);
/* Complete standalone delete substructure. Input begins at entReceiveDeletes,
 * after control state. This function cannot find that offset in ALLENTS. */
CohStatus coh_ent_deletes(CohRepReader *, CohEntDeletes *, CohEntFailure *);
/* Atomic staging operation; verifies the whole batch before applying it.
 * Source deletion ordering compares packet IDs, not the entity-id in the
 * delete record. Equal create/delete packet IDs retain the live slot. */
CohStatus coh_ent_stage_deletes(CohEntSlot *, size_t count,
    const CohEntDeletes *, uint32_t packet_id);
/* Explicit full-message barrier: no current path accepts a character/global
 * tail or produces READY/RECEIVED_CHARACTER/ACK_FULL_UPDATE. */
CohStatus coh_ent_full_update_tail(CohRepReader *, CohEntFailure *);
#ifdef __cplusplus
}
#endif
#endif
