#ifndef COH_INITIAL_PARTCOUNT_PROBE_H
#define COH_INITIAL_PARTCOUNT_PROBE_H
#include "coh_initial_scales_probe.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
 COH_INITIAL_PARTCOUNT_INPUT=1,COH_INITIAL_PARTCOUNT_FLAG,COH_INITIAL_PARTCOUNT_COUNT,
 COH_INITIAL_PARTCOUNT_DEFAULT_CATALOG,COH_INITIAL_PARTCOUNT_COUNT_LIMIT,
 COH_INITIAL_PARTCOUNT_CATALOG
} CohInitialPartcountStage;
typedef struct {
 CohStatus status;CohInitialPartcountStage stage;
 size_t begin_bit,end_bit,failure_bit;
 uint32_t compressed,explicit_count,flag_read,count_read,part_count,count_width,framing_validated;
} CohInitialPartcountProbe;
#define COH_INITIAL_PARTCOUNT_EXCESS (COH_COSTUME_PART_MAX+1u)
/* FIRST body's initial self/extra1 profile, in the SAME immutable ALLENTS loan
 * after30 verified finite scales. Strict Boolean flag0 stops after the flag at
 * unresolved default catalog; no GetBodyPartCount value is supplied. Flag1 reads
 * one transactional U32 Pack4, then stops before runtime bodytype/count catalog
 * checks and every part cache/index bit, including explicit0/exact end.
 * The existing native capacity30 is a policy limit, NOT the runtime catalog's
 * size. Larger fully decoded counts fail LIMIT; discard value, retain sentinel31
 * only. Count widths4/12/28/60 packed or32 compressed; at most61/40 total bits.
 * FLAG truncation stays at begin; malformed compressed flag consumes8bits.
 * COUNT truncation/overflow stays after the flag. Only complete bounded framing
 * sets end_bit/framing_validated; it NEVER grants catalog/count membership,
 * complete costume, ownership, generation, actor, authority or application ACK.
 * No COH_OK, allocation or value/pointer retention beyond bounded diagnostics;
 *4MiB cap. Invalid API/alias leaves output unchanged.
 */
CohStatus coh_initial_partcount_probe(const CohRepReader *,CohInitialPartcountProbe *);
#define COH_INITIAL_PARTCOUNT_REPORT_MAX 80u
/* [status,stage,begin,delta,explicit_count,part_count,count_width,framing_validated].
 * part_count31 ONLY means excess classification; it is not the original value.
 */
int coh_initial_partcount_probe_json(const CohInitialPartcountProbe *,char *,size_t);
/* [status,37+stage,done0,done1,list_end,total_delta,m]. Stage39 FLAG,40 COUNT,
 *41 DEFAULT_CATALOG_REQUIRED,42 COUNT_LIMIT,43 BODY_CATALOG_REQUIRED.
 * Metadata0..20 retains accepted SG/scales complete context. Bits21..25 are
 * bounded count0..30 or31 excess. Bits26..28 are width selector0 none,1=4,2=12,
 *3=28,4=60,5=32,6 malformed compressed flag consumed. Stage implies presence.
 * Partcount begin=failure minus flag/Pack width; SG end=partcount begin-960,
 * SG begin=SG end-2304. Earlier boundaries recover via retained parent metadata.
 * No unresolved default, actual excess value, part or dictionary is supplied.
 */
int coh_initial_partcount_progress_json(const CohInitialRewardListProbe *,
 const CohInitialCostumeSlotsProbe *,const CohInitialCostumeBodyProbe *,
 const CohInitialAppearanceProbe *,const CohInitialSgcolorsProbe *,
 const CohInitialScalesProbe *,const CohInitialPartcountProbe *,char *,size_t);
#ifdef __cplusplus
}
#endif
#endif
