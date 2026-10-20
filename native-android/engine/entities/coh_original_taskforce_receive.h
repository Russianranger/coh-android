#ifndef COH_ORIGINAL_TASKFORCE_RECEIVE_H
#define COH_ORIGINAL_TASKFORCE_RECEIVE_H
#include "coh_original_costume_receive.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_ORIGINAL_TASKFORCE_STACK_RESERVE 16384u
enum{COH_ORIGINAL_TASKFORCE_ARCHITECT=1,COH_ORIGINAL_TASKFORCE_BODY=2,
 COH_ORIGINAL_TASKFORCE_CUSTOM=3,COH_ORIGINAL_TASKFORCE_REVIEW=4,
 COH_ORIGINAL_TASKFORCE_PARAMETERS=5,COH_ORIGINAL_TASKFORCE_COMPLETE=6};
typedef struct{
 CohStatus status;size_t begin_bit,end_bit,failure_bit,packet_bits;
 uint32_t field,on_architect,on_flashback,body_count,custom_parts,review_present,
  review_bytes[3],parameter_mask,parameters[32],complete;
 CohOriginalCostumeReport body;
}CohOriginalTaskforceReport;
/* Exact consecutive original architect + parameter functions for the already
 * validated selected-self very-rare profile, ending before SendOnOddSend.
 * CLIENT ordinary/extra/palette slots feed the same unchanged costume receiver;
 * custom NPC uses the whole original function. Discard-only typed owners never
 * publish actor/UI state. No capture pointer exists, preserving main-body capture.
 * No heap; reader remains unchanged. API-invalid/alias input preserves output.
 * Caller charges message, body workspace, immutable tables/index, this report,
 * complete retained/candidate owners and stack reserve under existing8MiB.
 * Relative time words remain raw; no guessed clock or generation is supplied.
 */
CohStatus coh_original_taskforce_receive(const CohRepReader *,uint32_t body_parts,
 const CohClientCostumeSlots *,CohOriginalCostumeWorkspace *,CohOriginalTaskforceReport *);
#ifdef __cplusplus
}
#endif
#endif
