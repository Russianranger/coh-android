#ifndef COH_INITIAL_POWER_SLOTS_H
#define COH_INITIAL_POWER_SLOTS_H
#include "coh_power_boost_slots.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_INITIAL_POWER_SLOTS_MAX COH_SCHEDULE_WORDS_MAX
#define COH_INITIAL_POWER_SLOT_EMPTY UINT32_MAX
#define COH_INITIAL_POWER_SLOTS_RAM_MAX COH_POWER_SLOT_RAM_MAX
#define COH_INITIAL_POWER_SLOTS_STACK_RESERVE 16384u
typedef struct {
 CohPowerBoostSlots source;
 int32_t level_finalize_target;
 uint32_t slot_count;
 uint8_t fresh_slot_constructor,historical_state_projection,runtime_generation,actor_authority;
 uint32_t slots[COH_INITIAL_POWER_SLOTS_MAX];
} CohInitialPowerSlots;
typedef struct {
 CohInitialPowerSlots candidate;
 CohPowerBoostSlotsWorkspace record;
} CohInitialPowerSlotsWorkspace;
/* NEW power only: source power_Create starts ppBoosts empty. Apply the initial
 * ReceivePowers purchased-slot arithmetic, then complete power_LevelFinalize
 * boost-slot growth using actual persisted BoostsAllowed count and MaxBoosts.
 * Every constructed slot is EMPTY; this does not instantiate any Boost object.
 * No caller prior-slot count/previous Power/assumed retained state is accepted.
 * Reused regular powers and temporary duplicate selection belong to the future
 * source-ordered character owner, and cannot use this as a retained-state update.
 *
 * Exactly one existing full-record read pass; canonical scalar is recomputed,
 * never trusted from a caller POD. Complete transitive owners/provider/context/
 * scratch/out/workspace/retained and both16KiB stack reserves are charged before
 * callbacks. No allocation, whole graph, actor or ACK. Failure preserves out;
 * scratch unspecified. Borrowed stream/schedules/provider/file leases outlive
 * output. A historical constructor does not establish current generation or
 * full power_Create/ReceivePowers/character semantic application. */
CohStatus coh_initial_power_slots_create(const CohPowerStreamDictionary*,const CohSchedules*,
 uint32_t,int32_t,int32_t,uint32_t,CohInitialPowerSlots*,CohInitialPowerSlotsWorkspace*,size_t,size_t);
#ifdef __cplusplus
}
#endif
#endif
