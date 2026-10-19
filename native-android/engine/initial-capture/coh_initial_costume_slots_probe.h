#ifndef COH_INITIAL_COSTUME_SLOTS_PROBE_H
#define COH_INITIAL_COSTUME_SLOTS_PROBE_H
#include "coh_initial_reward_list_probe.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
 COH_INITIAL_COSTUME_SLOTS_INPUT=1,COH_INITIAL_COSTUME_SLOTS_DEFERRED,
 COH_INITIAL_COSTUME_SLOTS_CURRENT,COH_INITIAL_COSTUME_SLOTS_ADDITIONAL,
 COH_INITIAL_COSTUME_SLOTS_MULTIPLE,COH_INITIAL_COSTUME_SLOTS_COUNT,
 COH_INITIAL_COSTUME_SLOTS_BODY
} CohInitialCostumeSlotsStage;
typedef struct {
 CohStatus status;CohInitialCostumeSlotsStage stage;
 size_t begin_bit,end_bit,failure_bit;
 uint32_t deferred,current,additional,multiple,body_count,framing_validated;
} CohInitialCostumeSlotsProbe;
/* Original initial self/type1 profile ONLY. The receiver supplies the cursor
 * after BOTH independently parsed reward groups, in the same immutable loan.
 * This cursor is no identity, ownership or source-generation certificate.
 * Read deferred, current8, additional8, full-list flag and stored count4.
 * Current<10; full-list must1; stored count1..10 and current<count. Additional
 * is only an unsigned wire value, not entitlement or total slot ownership.
 * Never apply deferred/current or inspect ANY costume body/dictionary index.
 * Complete framing returns UNSUPPORTED/BODY, or INVALID at exact packet end,
 * retaining framing_validated. No COH_OK or authority/application ACK permit.
 * No allocation/borrowed pointer retained. At most22 packed or40 compressed
 * bits; existing4MiB cap. Invalid API/alias input leaves output unchanged.
 */
CohStatus coh_initial_costume_slots_probe(const CohRepReader *,CohInitialCostumeSlotsProbe *);
#define COH_INITIAL_COSTUME_SLOTS_REPORT_MAX 80u
/* [status,stage,begin_bit,failure_bit-begin_bit,metadata]. Metadata: deferred
 * bit0, current1..8, additional9..16, multiple17, count18..21, validated22.
 * Completed-list JNI projection combines this with reward counts; see handoff.
 */
int coh_initial_costume_slots_probe_json(const CohInitialCostumeSlotsProbe *,char *,size_t);
/* Completed-list projection: [status,6+stage,done0,done1,list_end,delta,metadata].
 * Stage8..13 discriminates it from the unchanged9-value reward-failure tuple.
 * Keeps both boundaries: first failure = list_end+delta. Reject bad context.
 */
int coh_initial_costume_slots_progress_json(const CohInitialRewardListProbe *,
 const CohInitialCostumeSlotsProbe *,char *,size_t);
#ifdef __cplusplus
}
#endif
#endif
