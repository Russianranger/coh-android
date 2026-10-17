#ifndef COH_POWER_RANGES_H
#define COH_POWER_RANGES_H
#include "../character-data/coh_character_data.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Reuse existing character-data admission capacity; not a source protocol max. */
#define COH_POWER_RANGES_MAX COH_CHARACTER_POWERS_MAX
#define COH_POWER_RANGES_AGGREGATE_MAX (4u*1024u*1024u)
#define COH_POWER_RANGES_STACK_RESERVE 4096u
typedef struct {uint32_t power_crc,range_word;} CohPowerRange;
typedef struct {
    uint32_t count;CohPowerRange ranges[COH_POWER_RANGES_MAX];
    size_t begin_bit,end_bit;
} CohPowerRanges;
typedef struct {CohPowerRanges candidate;} CohPowerRangesWorkspace;
/* Exact complete character_SendPowerRanges/character_ReceivePowerRanges list:
 * repeat [one bit, basepower CRC via pktSendBitsAuto, raw F32], ending zero.
 * Begins at that list's first sentinel. Present in BOTH PowerInfoUpdate paths:
 * immediately after flag=false, or after the flag=true power-definition list.
 * No scanning/offset discovery is permitted. Preserves source reverse set/power
 * send order and duplicate/zero/unresolved CRCs as wire events, not admitted
 * dictionary objects. Raw F32 includes signed-zero/nonfinite words: this is
 * wire staging, not finite range/application authority. No previous-state
 * application, complete PowerInfoUpdate, entity ownership, actor or ACK claim.
 *
 * Allocation-free; output/workspace belong in caller-owned heap/arena storage.
 * Budget charges input+out+workspace+stack reserve+retained bytes. All spans must
 * be disjoint. Failure leaves reader/output untouched; workspace unspecified. */
CohStatus coh_power_ranges(CohRepReader *,CohPowerRanges *,CohPowerRangesWorkspace *,
    size_t retained_bytes,size_t aggregate_limit);
/* Starts at entity_ReceivePowerInfoUpdate's hasPowerInfoUpdates flag. Only the
 * complete flag=false path is supported. Flag=true refuses UNSUPPORTED without
 * consumption; it never jumps over definitions or guesses range-list offsets.
 * Success includes the entire range list despite the false outer flag. */
CohStatus coh_power_info_no_changes(CohRepReader *,CohPowerRanges *,
    CohPowerRangesWorkspace *,size_t retained_bytes,size_t aggregate_limit);
#ifdef __cplusplus
}
#endif
#endif
