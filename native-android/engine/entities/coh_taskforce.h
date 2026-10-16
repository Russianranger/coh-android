#ifndef COH_TASKFORCE_H
#define COH_TASKFORCE_H
#include "coh_costume.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_TASKFORCE_PARAMETERS 32u
#define COH_TASKFORCE_REVIEW_NAME 256u
#define COH_TASKFORCE_REVIEW_AUTHOR 128u
#define COH_TASKFORCE_REVIEW_DESCRIPTION 4096u
/* Wire event, not persistent taskforce or actor state. A missing architect
 * update clears onArchitect in source. When onArchitect is true, exists=0
 * clears a prior contact costume; exists=1/body=0 retains it; body=1 replaces
 * it. Absent review/parameter updates retain prior semantic data. */
typedef struct {
    uint32_t generation,architect_update,on_architect,architect_flags,
        architect_id,contact_override,costume_exists,costume_body,
        custom_exists,custom_body,review_present,rating,european,
        invincible,untargetable,on_flashback,parameter_update,parameter_mask;
    char contact_name[32],review_name[COH_TASKFORCE_REVIEW_NAME],
        review_author[COH_TASKFORCE_REVIEW_AUTHOR],review_description[COH_TASKFORCE_REVIEW_DESCRIPTION];
    /* Source slots 1 and 23 contain raw relative clock words, modulo 2^32;
     * conversion requires the future transaction's explicit client timebase. */
    uint32_t parameters[COH_TASKFORCE_PARAMETERS];
    CohEntCostume costume;CohEntCustomCostume custom;size_t end_bit;
} CohEntTaskforce;
typedef struct {CohEntTaskforce candidate;CohEntCostumeWorkspace body;} CohEntTaskforceWorkspace;
/* Complete two consecutive selected-self very-rare taskforce substructures,
 * beginning at entRecieveTaskforceArchitectInfo's update flag. No outer rare
 * bit, identity, dictionary authenticity, history or ACK admission. Generation
 * must be nonzero; a dictionary is required only for a new full costume body.
 * No allocations/packet retention; reader/output atomic, workspace unspecified
 * on failure. Distinct off-stack buffers; never embed this in every slot. */
CohStatus coh_ent_taskforce(CohRepReader *,const CohEntCostumeDictionary *,
    uint32_t generation,CohEntTaskforceWorkspace *,CohEntTaskforce *,CohEntFailure *);
#ifdef __cplusplus
}
#endif
#endif
