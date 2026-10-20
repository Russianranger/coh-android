#ifndef COH_ORIGINAL_RARE_RECEIVE_H
#define COH_ORIGINAL_RARE_RECEIVE_H
#include "coh_entities.h"
#include "coh_very_rare_tail.h"
#include "coh_teammate_buffs.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_ORIGINAL_RARE_AGGREGATE_MAX (8u*1024u*1024u)
#define COH_ORIGINAL_RARE_STACK_RESERVE 16384u
enum {COH_ORIGINAL_RARE_PREFIX=1,COH_ORIGINAL_RARE_TAIL=2,
 COH_ORIGINAL_RARE_BUFFS=3,COH_ORIGINAL_RARE_COMPLETE=4};
typedef struct {
 CohEntRarePrefix prefix;
 CohEntVeryRareTail tail;CohEntVeryRareTailWorkspace tail_workspace;
 CohEntTeammateBuffs buffs;CohEntTeammateBuffsWorkspace buffs_workspace;
} CohOriginalRareWorkspace;
typedef struct {
 CohStatus status;size_t begin_bit,prefix_end_bit,rare_end_bit,end_bit,
  failure_bit,packet_bits;
 uint32_t stage,failure_cursor_exact,prefix_complete,rare_complete,buffs_complete,
  entity_suffix_complete,power_crc_present,power_crc,supergroup_id,
  token_count,recipe_count,detail_count,pact_count,buff_count,buff_mod_count;
} CohOriginalRareReport;
/* Consecutive normal/fresh selected-self very-rare fields, AFTER the original
 * taskforce parameters, through appendTeammatePacket end. Caller has already
 * validated the initial selected-self/very-rare profile and exact start cursor.
 * Reuses existing source-qualified parsers in original entReceive order;
 * unresolved CRC/name metadata is staged without invented lookup results.
 * Reader unchanged; no actor/whole-message completion or ACK authority.
 * Workspace is exclusive off-stack typed scratch and is wiped after parsing.
 * API/alias/budget preflight failures leave output/workspace unchanged. Parser
 * failures publish diagnostic progress. failure_cursor_exact=0 denotes an
 * atomic child parser's known component start, never a guessed failure cursor.
 * Charge retained old/candidate owners and borrowed source spans through retained;
 * helper charges complete workspace/report/reader/input and closed stack once.
 * Existing child4MiB ceilings and enclosing8MiB ceiling remain unchanged.
 */
CohStatus coh_original_rare_receive(const CohRepReader *,CohOriginalRareWorkspace *,
 CohOriginalRareReport *,size_t budget,size_t retained);
#ifdef __cplusplus
}
#endif
#endif
