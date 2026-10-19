#ifndef COH_INITIAL_REWARD_LIST_PROBE_H
#define COH_INITIAL_REWARD_LIST_PROBE_H
#include "coh_initial_reward_probe.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
 COH_INITIAL_REWARD_LIST_INPUT=1,COH_INITIAL_REWARD_LIST_COUNT,
 COH_INITIAL_REWARD_LIST_FLAG,COH_INITIAL_REWARD_LIST_STRING,
 COH_INITIAL_REWARD_LIST_DICTIONARY,COH_INITIAL_REWARD_LIST_SLOTS
} CohInitialRewardListStage;
typedef struct {
 CohStatus status;CohInitialRewardListStage stage;
 size_t begin_bit,end_bit,failure_bit;
 uint32_t group,index,counts[2],entries[2],literals,literal_bytes,list_validated;
 CohInitialRewardStage leaf_stage;
} CohInitialRewardListProbe;
/* Reparse BOTH original non-debug costume-reward groups from their first U32
 * count in the SAME immutable ALLENTS loan. The caller derives that cursor
 * from validated type1/self1 framing, not saved counts or resume indexes.
 * No ownership/generation certificate follows from caller-provided position.
 *
 * Each actual count is bounded by the existing256-per-group native limit.
 * Absent flags and completed literals count as entries; indexed/partial/null
 * strings never do. Reuse the accepted literal parser and260-byte NUL limit.
 * Indexed storage stops before any packed index, even in compressed mode.
 * Complete final literals are counted even when the leaf reports exact-end
 * INVALID; this enclosing parser then diagnoses the actual next boundary.
 *
 * Stop BEFORE deferred/slot framing after both groups. Complete lists return
 * UNSUPPORTED/SLOTS, or INVALID there if no following bits remain. No COH_OK,
 * costume/character admission, resource lookup, generation, actor or ACK permit.
 * No reward text or borrowed pointer is retained. No allocation; at most512
 * entries and the existing4MiB reader cap. Input/output/payload must be disjoint;
 * invalid API input leaves output unchanged. Reader/payload always immutable.
 */
CohStatus coh_initial_reward_list_probe(const CohRepReader *,CohInitialRewardListProbe *);
#define COH_INITIAL_REWARD_LIST_REPORT_MAX 128u
/* Numeric continuation progress, appended inside existing first_reward_string:
 * [status,stage,group,index,entries0,entries1,bit,complete,leaf_stage].
 * Group is1/2, index zero-based; only complete entries increment progress.
 * Stage0 renders null; authority-false fields remain in the parent report. */
int coh_initial_reward_list_probe_json(const CohInitialRewardListProbe *,char *,size_t);
#ifdef __cplusplus
}
#endif
#endif
