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
/* All state here is uncommitted inspection/staging state. A valid record is not
 * a valid ALLENTS/UPDATE packet, resolved appearance, or a renderable actor. */
typedef enum {
    COH_ENT_STAGE_CREATE=1, COH_ENT_STAGE_IDENTITY, COH_ENT_STAGE_PET_POWER,
    COH_ENT_STAGE_CREATE_STRINGS, COH_ENT_STAGE_STATE, COH_ENT_STAGE_POSITION,
    COH_ENT_STAGE_INTERPOLATION, COH_ENT_STAGE_ORIENTATION, COH_ENT_STAGE_SEQUENCE,
    COH_ENT_STAGE_NETFX, COH_ENT_STAGE_APPEARANCE, COH_ENT_STAGE_POWER_CUSTOM,
    COH_ENT_STAGE_TITLES, COH_ENT_STAGE_RAGDOLL, COH_ENT_STAGE_CHARACTER_STATS,
    COH_ENT_STAGE_VISION, COH_ENT_STAGE_RARE_TAIL, COH_ENT_STAGE_BUFFS,
    COH_ENT_STAGE_DELETES, COH_ENT_STAGE_LIST, COH_ENT_STAGE_FULL_UPDATE_TAIL
} CohEntStage;
typedef struct { CohStatus status; CohEntStage stage; size_t bit; } CohEntFailure;
typedef struct {
    uint32_t create, end, entity_id, type, is_self, access_level, dbid,
        owner_index, creator_index, commandable_pet, visible_pet, dismissable_pet,
        special_power_state, critter_form, class_index, origin_index,
        player_type, player_subtype, praetorian_progress, player_type_location,
        fade_in, in_phase, random_seed, rank, detail_id, contact_handle;
    char name[256];
    size_t end_bit;
} CohEntCreate;
typedef struct { float quaternion[4]; uint32_t packet_ids[3], valid; } CohEntOrientation;
typedef struct { uint32_t index, entity_id; } CohEntDelete;
typedef struct { uint32_t count; CohEntDelete entries[COH_ENT_DELETE_MAX]; size_t end_bit; } CohEntDeletes;
typedef struct {
    CohEntCreate identity;
    CohRepPosition position;
    CohEntOrientation orientation;
    uint32_t index, present, create_packet, delete_packet, deleted_entity_id,
        state_mode, state_packet, sequence_index, sequence_ticks, sequence_bits,
        sequence_packet, vision_phases, exclusive_vision_phase, con_yellow;
} CohEntSlot;
typedef struct { uint32_t index, ticks, fx_id; } CohEntTrigger;
typedef struct {
    CohEntCreate identity; uint32_t rare, medium_rare, very_rare,
        pchar_things, trigger_count, appearance_type, ragdoll_bones;
    CohEntTrigger triggers[COH_ENT_TRIGGER_MAX]; size_t end_bit;
} CohEntRecord;
/* Source delta-index grammar; previous starts at -1. Index 0 is admitted only
 * as an end sentinel by the record decoder, never as an entity. */
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
/* Reads one complete supported entity record. In/out slot is STAGING ONLY.
 * Unsupported branch, malformed input, or identity failure leaves reader,
 * slot and record unchanged; failure receipt is diagnostic only.
 * Unknown update indices fail closed, rather than inventing original dummy
 * entities. A stale generation returns COH_STATE. No external game callbacks. */
CohStatus coh_ent_record(CohRepReader *, uint32_t selected_dbid,
    uint32_t packet_id, uint32_t interp_level, CohEntSlot *,
    CohEntRecord *, CohEntFailure *);
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
