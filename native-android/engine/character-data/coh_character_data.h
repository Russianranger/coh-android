#ifndef COH_CHARACTER_DATA_H
#define COH_CHARACTER_DATA_H
#include "../replication/coh_replication.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_CHARACTER_BUILDS 8u
#define COH_CHARACTER_SETS_MAX 256u
#define COH_CHARACTER_POWERS_MAX 1024u
#define COH_CHARACTER_BOOSTS_MAX 2048u
#define COH_CHARACTER_INVENTORY_MAX 2048u
#define COH_CHARACTER_BOOST_SLOTS 70u
#define COH_CHARACTER_RAM_MAX (8u*1024u*1024u)
/* Structural g_numSharedPowersets is loaded from the original dictionary and
 * is NOT transmitted. Caller must bind it to exact source/profile generation.
 * A nonzero digest is a required identity, not independently verified proof.
 * Dictionary object references remain unresolved in every output. Supported
 * players require each build's declared set count >= shared_set_count. Original
 * producer can emit smaller counts; those layouts are explicitly refused. */
typedef struct {
    uint32_t generation, shared_set_count, shared_set_count_bound, player;
    uint8_t source_profile_sha256[32];
} CohCharacterWireProfile;
typedef struct {uint32_t type,id,filled;} CohCharacterPowerup;
typedef struct {
    uint32_t present, power_crc, level, combines, powerup_count;
    float variables[4];
    CohCharacterPowerup powerups[10];
} CohCharacterBoost;
typedef struct {
    uint32_t power_crc,level,charges,creation_time,enabled,disabled_manually,unique_id;
    float range,usage_time,available_time;
    uint32_t boost_first,boost_count,global_first,global_count;
} CohCharacterPower;
typedef struct {uint32_t build,index,level,power_first,power_count,empty_root_crc;} CohCharacterSet;
typedef struct {uint32_t level,total_sets,set_first,set_count;} CohCharacterBuild;
typedef struct {uint32_t type,index,amount,id;float variables[4];} CohCharacterInventoryItem;
typedef struct {uint32_t total,first,count;} CohCharacterInventory;
/* Pointer-free wire metadata only. Numeric references/names have not been
 * admitted against class/origin/power/reward/inventory dictionaries. No actor
 * ownership, powers execution, gameplay creation, ACK or publication occurs. */
typedef struct {
    CohCharacterWireProfile profile;
    char class_name[256],origin_name[256];
    uint32_t level,combat_mod_shift,current_build,location,multiple_builds,active_build;
    uint32_t build_count,set_count,power_count,boost_count,inventory_count;
    CohCharacterBuild builds[COH_CHARACTER_BUILDS];
    CohCharacterSet sets[COH_CHARACTER_SETS_MAX];
    CohCharacterPower powers[COH_CHARACTER_POWERS_MAX];
    CohCharacterBoost boosts[COH_CHARACTER_BOOSTS_MAX];
    uint32_t inspiration_columns,inspiration_rows,inspirations[5][4];
    uint32_t boost_inventory[COH_CHARACTER_BOOST_SLOTS]; /* pool indexes, including empty slots */
    CohCharacterInventory inventories[5];
    CohCharacterInventoryItem items[COH_CHARACTER_INVENTORY_MAX];
    uint32_t auction_slots,dictionary_bindings_verified;
    size_t end_bit;
} CohCharacterData;
typedef struct {CohCharacterData candidate;} CohCharacterWorkspace;
typedef enum {COH_CHARACTER_PROFILE=1,COH_CHARACTER_IDENTITY,COH_CHARACTER_POWERS,
    COH_CHARACTER_BOOST,COH_CHARACTER_INSPIRATIONS,COH_CHARACTER_BOOST_INVENTORY,
    COH_CHARACTER_INVENTORIES} CohCharacterStage;
typedef struct {CohStatus status;CohCharacterStage stage;size_t bit;} CohCharacterFailure;
/* Caller owns output (old generation) and scratch candidate (new generation).
 * Reader, failure, output and scratch must be mutually disjoint and disjoint
 * from borrowed input. Reader/failure must also be disjoint from profile;
 * profile may reside in output/scratch because it is copied before changes.
 * Alias rejection returns INVALID without writing failure. Scratch is otherwise
 * unspecified on failure; reader/output unchanged. Includes input/retained bytes
 * in aggregate admission: 2*sizeof(Data)+input.size+retained_bytes <= budget,
 * budget <= RAM_MAX. Allocate POD/workspace in an arena/heap, not call stack.
 * Budget covers named storage, excluding bounded call stack/allocator overhead;
 * it is not a process RSS or total application working-set limit.
 * Starts at character_Receive, ends after inventories. Does not consume or
 * validate enclosing full-update fields. Requires non-debug scalar profile. */
CohStatus coh_character_data_read(CohRepReader *,const CohCharacterWireProfile *,
    CohCharacterWorkspace *,CohCharacterData *,size_t budget,size_t retained_bytes,
    CohCharacterFailure *);
#ifdef __cplusplus
}
#endif
#endif
