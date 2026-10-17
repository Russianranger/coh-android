#ifndef COH_CHARACTER_INITIAL_H
#define COH_CHARACTER_INITIAL_H
#include "coh_character_prefix.h"
#include "coh_entities.h"
#include "../character-data/coh_character_data.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_CHARACTER_INITIAL_RAM_MAX COH_CHARACTER_RAM_MAX
#define COH_CHARACTER_INITIAL_STACK_RESERVE 8192u
#define COH_CHARACTER_ORIGINAL_SET_BYTES 128u
typedef struct {
    CohCharacterPrefix account;
    CohCharacterData character;
    char primary_set[COH_CHARACTER_ORIGINAL_SET_BYTES];
    char secondary_set[COH_CHARACTER_ORIGINAL_SET_BYTES];
    uint32_t ally_id,gang_id,pvp_switch,pvp_active,pvp_timer,is_ganker;
    CohEntCharacterStats self_stats;
    uint32_t packet_id;
    size_t begin_bit,prefix_end_bit,character_end_bit,names_end_bit,end_bit;
} CohCharacterInitialPrefix;
typedef struct {
    CohCharacterInitialPrefix candidate;
    CohCharacterWorkspace character;
} CohCharacterInitialWorkspace;
typedef enum {
    COH_CHARACTER_INITIAL_ACCOUNT=1,COH_CHARACTER_INITIAL_DATA,
    COH_CHARACTER_INITIAL_SETS,COH_CHARACTER_INITIAL_ALLY_PVP,
    COH_CHARACTER_INITIAL_SELF_STATS
} CohCharacterInitialStage;
typedef struct {
    CohStatus status;CohCharacterInitialStage stage;size_t bit;
    CohCharacterFailure character;CohEntFailure entity;
} CohCharacterInitialFailure;
/* Composes original sendCharacterToClient from its first server flag THROUGH
 * full SendCharacterToSelf stats, stopping immediately BEFORE sendTray.
 * This is a raw prefix transaction, not a complete character/full-update.
 * No dictionary authority, selected DBID/entity ownership, actor, ACK or
 * entitlement application. Account bytes are sensitive; never log by default.
 * All reader/profile/output/workspace/failure/input spans must be disjoint.
 * Output/workspace belong on heap or caller arena. Aggregate budget charges
 * input + complete output + workspace + stack reserve + retained_bytes once.
 * On failure output/reader unchanged; workspace unspecified, failure diagnostic
 * may be written only after all alias checks pass. No allocation/retained input.
 * Non-debug absolute stats only; exact source/profile generation still required.
 * Original powerset strings refuse overlong values instead of truncating.
 * Subsequent tray/UI/account/global grammar and message end remain unvalidated. */
CohStatus coh_character_initial_read(CohRepReader *,const CohCharacterWireProfile *,
    uint32_t packet_id,CohCharacterInitialWorkspace *,CohCharacterInitialPrefix *,
    size_t budget,size_t retained_bytes,CohCharacterInitialFailure *);
#ifdef __cplusplus
}
#endif
#endif
