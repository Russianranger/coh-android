#ifndef COH_INITIAL_REWARD_PROBE_H
#define COH_INITIAL_REWARD_PROBE_H
#include "../entities/coh_costume.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
 COH_INITIAL_REWARD_INPUT=1,COH_INITIAL_REWARD_PRESENCE,
 COH_INITIAL_REWARD_STORAGE,COH_INITIAL_REWARD_TEXT,
 COH_INITIAL_REWARD_DICTIONARY,COH_INITIAL_REWARD_CONTINUATION
} CohInitialRewardStage;
typedef struct {
 CohStatus status;CohInitialRewardStage stage;
 size_t begin_bit,end_bit,failure_bit;
 uint32_t presence_seen,in_table,literal_bytes,literal_validated;
} CohInitialRewardProbe;
/* One non-debug pktSendIndexedString leaf, entered immediately AFTER the
 * existing costume-prefix observer's present-reward flag in the same loan.
 * That outer flag requires nested presence1; nested0 is invalid, not another
 * absent reward. Strict rounded Booleans preserve the packed bit offset.
 *
 * Literal strings stream through NUL without copying or text assumptions.
 * Existing CohEntCostumeText.value limit260 includes NUL:259 text bytes fit.
 * Indexed storage stops BEFORE Pack(defaultBitsPack(stash capacity)); no
 * dictionary/index/generation is supplied, consumed, resolved or admitted.
 * A completed literal stops BEFORE remaining rewards/framing. Both boundaries
 * return UNSUPPORTED, or INVALID if no following bits remain. No COH_OK result,
 * reward-list completion, ownership, actor, authority or ACK permit is granted.
 *
 * Input/output/payload must be disjoint. Invalid API input leaves output
 * unchanged. Input reader and payload always remain immutable. No allocation,
 * pointer/name retention or change to the existing4MiB reader cap.
 */
CohStatus coh_initial_reward_probe(const CohRepReader *,CohInitialRewardProbe *);
#define COH_INITIAL_REWARD_TEXT_MAX 260u
#define COH_INITIAL_REWARD_REPORT_MAX 192u
/* Compact child projection uses the enclosing report's authority-false fields.
 * bit is the first failure/next-boundary cursor; zero stage renders null. */
int coh_initial_reward_probe_json(const CohInitialRewardProbe *,char *,size_t);
#ifdef __cplusplus
}
#endif
#endif
