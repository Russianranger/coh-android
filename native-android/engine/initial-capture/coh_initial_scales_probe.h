#ifndef COH_INITIAL_SCALES_PROBE_H
#define COH_INITIAL_SCALES_PROBE_H
#include "coh_initial_sgcolors_probe.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
 COH_INITIAL_SCALES_INPUT=1,COH_INITIAL_SCALES_VALUE,COH_INITIAL_SCALES_NONFINITE,
 COH_INITIAL_SCALES_PART_COUNT
} CohInitialScalesStage;
typedef struct {
 CohStatus status;CohInitialScalesStage stage;
 size_t begin_bit,end_bit,failure_bit;
 uint32_t compressed,scales_read,nonfinite_seen,scales_validated;
} CohInitialScalesProbe;
#define COH_INITIAL_SCALES_COUNT COH_COSTUME_SCALE_COUNT
/* FIRST body's initial self/extra1 profile, in the SAME immutable ALLENTS loan
 * after verified SG words. Exactly30 F32 wire words; reject exponent-all-ones
 * as nonfinite, matching existing native isfinite policy without FP evaluation.
 * Original sender can emit nonfinite bits; this refusal is native finite policy.
 * All finite magnitudes, signed zero and subnormals fit; no extra range/clamp.
 * Discard every value. Only complete finite words increment scales_read. Short
 * VALUE fails at the current word begin; NONFINITE consumes its whole32 bits
 * without incrementing the finite count. At most30 reads/960 bits, either mode.
 * Complete finite scales stop BEFORE part-count flag: UNSUPPORTED, or INVALID at
 * exact end preserving scales_validated. No COH_OK, costume/character, resource,
 * generation, ownership, actor, world or application ACK admission. No allocation
 * or value/pointer retention;4MiB cap. Invalid API/alias leaves output unchanged.
 */
CohStatus coh_initial_scales_probe(const CohRepReader *,CohInitialScalesProbe *);
#define COH_INITIAL_SCALES_REPORT_MAX 80u
/* [status,stage,begin,delta,finite_count,nonfinite,validated]. */
int coh_initial_scales_probe_json(const CohInitialScalesProbe *,char *,size_t);
/* Completed parents: [status,33+stage,done0,done1,list_end,total_delta,m].
 * Stage35 VALUE,36 NONFINITE,37 FIRST_PART_COUNT_REQUIRED. Metadata0..20 is the
 * accepted SG complete-context encoding;21..25 finite_count,26 nonfinite.
 * SG end=failure-32*(finite_count+nonfinite); SG begin=SG end-2304. Recover earlier
 * boundaries via the retained slot-pair and Pack selector. Earlier failures keep
 * their projections. No scale value or part-count default is supplied/exported.
 */
int coh_initial_scales_progress_json(const CohInitialRewardListProbe *,
 const CohInitialCostumeSlotsProbe *,const CohInitialCostumeBodyProbe *,
 const CohInitialAppearanceProbe *,const CohInitialSgcolorsProbe *,
 const CohInitialScalesProbe *,char *,size_t);
#ifdef __cplusplus
}
#endif
#endif
