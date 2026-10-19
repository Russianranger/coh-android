#ifndef COH_INITIAL_SGCOLORS_PROBE_H
#define COH_INITIAL_SGCOLORS_PROBE_H
#include "coh_initial_appearance_probe.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
 COH_INITIAL_SGCOLORS_INPUT=1,COH_INITIAL_SGCOLORS_WORD,COH_INITIAL_SGCOLORS_SCALES
} CohInitialSgcolorsStage;
typedef struct {
 CohStatus status;CohInitialSgcolorsStage stage;
 size_t begin_bit,end_bit,failure_bit;
 uint32_t compressed,words_read,array_validated;
} CohInitialSgcolorsProbe;
#define COH_INITIAL_SGCOLORS_WORDS 72u
/* FIRST body's initial self profile, in the SAME immutable ALLENTS loan after
 * verified appearance scalars. Exactly6 slots*12 raw U32 bitset words, discarded
 * without color/resource interpretation. Count only completed words. On a short
 * word, failure is its first bit; slot=words_read/12, channel=words_read%12.
 * Complete array stops BEFORE the first scale F32: UNSUPPORTED, or INVALID at
 * exact end with array_validated retained. No COH_OK, costume/character, catalog,
 * generation, ownership, actor, world or application ACK admission.
 * At most72 reads/2304 bits in either profile. No allocation/value/pointer
 * retention; existing4MiB cap. Invalid API/alias input leaves output unchanged.
 */
CohStatus coh_initial_sgcolors_probe(const CohRepReader *,CohInitialSgcolorsProbe *);
#define COH_INITIAL_SGCOLORS_REPORT_MAX 80u
/* [status,stage,begin,delta,words_read,validated]. Channel order per slot:
 * Primary low/high, Secondary low/high, Primary2 low/high, Secondary2 low/high,
 * Tertiary low/high, Quaternary low/high. No word values are retained/exported.
 */
int coh_initial_sgcolors_probe_json(const CohInitialSgcolorsProbe *,char *,size_t);
/* Completed parents: [status,31+stage,done0,done1,list_end,total_delta,m].
 * Stage33 WORD,34 FIRST_SCALES_REQUIRED. Metadata: slot-pair0..5 (triangular
 * count*(count-1)/2+current,0..54),additional6..13,deferred14,body present15..16,
 * second cached17,compressed18,appearance Pack selector19..20,words21..27.
 * Packed selector0..3 -> Pack widths6/18/42/74, scalar widths43/55/79/111;
 * compressed selector0 -> scalar width88. SG begin=failure-32*words; body prefix
 * end=SG begin-scalar width. All prior boundaries/complete context recoverable.
 */
int coh_initial_sgcolors_progress_json(const CohInitialRewardListProbe *,
 const CohInitialCostumeSlotsProbe *,const CohInitialCostumeBodyProbe *,
 const CohInitialAppearanceProbe *,const CohInitialSgcolorsProbe *,char *,size_t);
#ifdef __cplusplus
}
#endif
#endif
