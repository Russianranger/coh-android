#ifndef COH_POWER_BOOST_SLOTS_H
#define COH_POWER_BOOST_SLOTS_H
#include "coh_schedules.h"
#include "coh_power_stream.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_POWER_SLOT_RECORD_MAX 65536u
#define COH_POWER_SLOT_RAM_MAX (4u*1024u*1024u)
#define COH_POWER_SLOT_STACK_RESERVE 16384u
typedef struct{
 const CohPowerStreamDictionary*powers;const CohSchedules*schedules;
 uint32_t power_row,power_crc,wire_boost_count,free_schedule_count;
 int32_t character_level,level_bought,max_boosts,free_allowed,boosts_bought;
 uint8_t historical_state_projection,runtime_generation,actor_authority;
}CohPowerBoostSlots;
typedef struct{uint8_t record[COH_POWER_SLOT_RECORD_MAX];}CohPowerBoostSlotsWorkspace;
/* Source character_ReceivePowers boost-slot application arithmetic, using the
 * actual selected BasePower.iMaxBoosts from the borrowed immutable full cache.
 * Validates the complete selected record through the existing source descriptor
 * (including every nested field) and exact record end, reading <=4KiB at a time.
 * No eager power graph, digest lifecycle, allocation or gameplay mutation.
 *
 * All powers/provider/file and schedules leases outlive this projection. Budget
 * charges full owners/context/scratch/out/workspace/retained/16KiB stack before
 * callbacks. Cancellation/IO/syntax/alias/budget/overflow failures preserve out.
 * Native profile wire_boost_count<=2048; unsafe original signed arithmetic
 * overflow refuses. Historical cache identity does not establish current loaded
 * generation, complete power/class/character state, actor or any ACK.
 */
CohStatus coh_power_boost_slots_prepare(const CohPowerStreamDictionary*,const CohSchedules*,
 uint32_t,int32_t,int32_t,uint32_t,CohPowerBoostSlots*,CohPowerBoostSlotsWorkspace*,size_t,size_t);
#ifdef __cplusplus
}
#endif
#endif
