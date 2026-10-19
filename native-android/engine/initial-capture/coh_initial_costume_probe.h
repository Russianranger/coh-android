#ifndef COH_INITIAL_COSTUME_PROBE_H
#define COH_INITIAL_COSTUME_PROBE_H
#include "../entities/coh_costume.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
 COH_INITIAL_COSTUME_INPUT=1,COH_INITIAL_COSTUME_SELECTOR_FLAG,
 COH_INITIAL_COSTUME_SELECTOR,COH_INITIAL_COSTUME_SELF,
 COH_INITIAL_COSTUME_REWARD_COUNT,COH_INITIAL_COSTUME_REWARD_FLAG,
 COH_INITIAL_COSTUME_SLOTS,COH_INITIAL_COSTUME_MULTIPLE,
 COH_INITIAL_COSTUME_STORED_COUNT,COH_INITIAL_COSTUME_REWARD_STRING,
 COH_INITIAL_COSTUME_BODY_DICTIONARY,COH_INITIAL_COSTUME_NPC_BODY,
 COH_INITIAL_COSTUME_SEQUENCE_BODY
} CohInitialCostumeStage;
typedef struct {
 CohStatus status;CohInitialCostumeStage stage;
 size_t begin_bit,selector_end_bit,prefix_end_bit,failure_bit;
 uint32_t type,selector_validated,self_seen,self_wire_consistent,
  reward_list,reward_index,reward_count[2],absent_rewards[2],
  body_count,framing_validated;
} CohInitialCostumeProbe;
/* Diagnostic prefix only, at the validated NetFX end in the same immutable
 * initial-create loan. create_is_self is that record's raw create observation,
 * NOT authenticated ownership. All objects/spans must be disjoint; invalid API
 * input leaves output unchanged. No allocation or resource/dictionary access.
 * Existing 4MiB message, 256 rewards/group and 10 stored-costume caps apply.
 *
 * Initial full-create forces a nonzero appearance selector. Entire costume
 * compares its self bit, then streams bounded absent reward flags and slot/list
 * framing. Initial self creates require the source full stored-costume list.
 * A present reward stops BEFORE pktSendIndexedString (literal/index branch
 * unread); full/owned variants stop BEFORE the first costume body. NPC/sequence
 * variants are classified and stop BEFORE their own dictionary-free bodies.
 * No body is read or skipped. Successful bounded framing returns UNSUPPORTED
 * at the named dependency/variant; no following bits is INVALID there. Partial
 * framing preserves the first failure, never a complete-costume admission.
 * No text, IDs, generation, actor state, authority or application ACK survives.
 */
CohStatus coh_initial_costume_probe(const CohRepReader *,uint32_t create_is_self,
 CohInitialCostumeProbe *);
#define COH_INITIAL_COSTUME_REPORT_MAX 640u
/* Compact numeric child of the existing authority-false report; zero => null. */
int coh_initial_costume_probe_json(const CohInitialCostumeProbe *,char *,size_t);
#ifdef __cplusplus
}
#endif
#endif
