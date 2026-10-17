#ifndef COH_POWER_INFO_H
#define COH_POWER_INFO_H
#include "../character-data/coh_character_data.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_POWER_INFO_DEFINITIONS 256u
#define COH_POWER_INFO_EVENTS 1024u
#define COH_POWER_INFO_BOOSTS 2048u
#define COH_POWER_INFO_LIMIT (8u*1024u*1024u)
typedef struct {uint32_t build,set,power;} CohPowerRef;
typedef struct {
    CohPowerRef ref;uint32_t present,crc,set_level,level,charges,creation_time;
    uint32_t enabled,disabled_manually,unique_id,boost_first,boost_count,global_first,global_count;
    float usage_time,available_time;
} CohPowerDefinition;
typedef struct {uint32_t crc;float range;} CohPowerRange;
typedef struct {
    CohPowerRef ref;uint32_t present,value,disabled_manually,charges;
    float usage_time,available_time,timer;
} CohPowerStatus;
typedef struct {uint32_t column,row,present,crc;} CohPowerInspiration;
typedef struct {uint32_t slot,boost;} CohPowerInventoryBoost;
/* Ordered raw events, never a power dictionary or applied gameplay state.
 * Even has_updates=0 carries the mandatory terminated range stream. Unknown
 * CRCs (including zero), PowerRef words, flags, duplicate updates and order are
 * retained. No UI/power execution, stale-state application, actor or ACK permit. */
typedef struct {
    uint32_t has_updates,current_build,redefine,default_present,default_crc;
    uint32_t definition_count,range_count,active_count,enabled_count,usage_count,recharge_count;
    uint32_t inspiration_count,inventory_boost_count,boost_count;
    CohPowerDefinition definitions[COH_POWER_INFO_DEFINITIONS];
    CohPowerRange ranges[COH_POWER_INFO_EVENTS];
    CohPowerStatus active[COH_POWER_INFO_EVENTS],enabled[COH_POWER_INFO_EVENTS];
    CohPowerStatus usage[COH_POWER_INFO_EVENTS],recharge[COH_POWER_INFO_EVENTS];
    CohPowerInspiration inspirations[COH_POWER_INFO_EVENTS];
    CohPowerInventoryBoost inventory_boosts[COH_POWER_INFO_EVENTS];
    CohCharacterBoost boosts[COH_POWER_INFO_BOOSTS];
    size_t begin_bit,end_bit;
} CohPowerInfoUpdate;
typedef struct {CohPowerInfoUpdate candidate;} CohPowerInfoWorkspace;
/* Caller heap/arena owns output and workspace (never put these on a thread
 * stack). Exact standalone entity_ReceivePowerInfoUpdate syntax; does not read
 * the following PowerModeUpdate. All reader/output/workspace/input spans must
 * be disjoint. Output and reader remain byte-identical on every refusal;
 * workspace is unspecified. Admission charges both PODs, borrowed input, 8KiB
 * bounded stack reserve and caller retained_bytes under <=8MiB. No allocation,
 * retained input, dictionary lookup or mutation occurs. Caller serializes use.
 * Finite float and pool bounds are explicit native admission policy, not a
 * claim about original earray or whole-process memory limits. */
CohStatus coh_global_power_info(CohRepReader *,CohPowerInfoUpdate *,
    CohPowerInfoWorkspace *,size_t retained_bytes,size_t aggregate_limit);
#ifdef __cplusplus
}
#endif
#endif
