#ifndef COH_INITIAL_APPEARANCE_PROBE_H
#define COH_INITIAL_APPEARANCE_PROBE_H
#include "coh_initial_costume_body_probe.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
 COH_INITIAL_APPEARANCE_INPUT=1,COH_INITIAL_APPEARANCE_BODYTYPE,
 COH_INITIAL_APPEARANCE_SKIN,COH_INITIAL_APPEARANCE_CONVERTED,
 COH_INITIAL_APPEARANCE_SUPERSET,COH_INITIAL_APPEARANCE_EXTRA,
 COH_INITIAL_APPEARANCE_COLORS
} CohInitialAppearanceStage;
typedef struct {
 CohStatus status;CohInitialAppearanceStage stage;
 size_t begin_bit,bodytype_end_bit,end_bit,failure_bit;
 uint32_t compressed,fields_read,scalars_validated;
} CohInitialAppearanceProbe;
/* FIRST body's initial self/full-list profile, at verified optional-name prefix
 * end in the SAME immutable ALLENTS loan. Read/discard raw Pack6 bodytype and
 * skin32, then width-check converted1, supergroup selector3 and extra1.
 * Pack6 is escaped U32 syntax, not a six-bit catalog bound. Do not invent a
 * body-type count, dictionary, generation or resource-identity certificate.
 * Extra0 is source-valid for other profiles but UNSUPPORTED here: initial self
 * costume_send uses send_names1. Extra1 completes only this scalar syntax.
 * Stop BEFORE the SG color array: UNSUPPORTED, or INVALID at exact end with
 * scalars_validated retained. No COH_OK/costume/character/actor/ACK admission.
 * At most111 packed/88 compressed bits, no allocation/value/pointer retention,
 * existing4MiB cap. Invalid API/alias input leaves output unchanged.
 */
CohStatus coh_initial_appearance_probe(const CohRepReader *,CohInitialAppearanceProbe *);
#define COH_INITIAL_APPEARANCE_REPORT_MAX 96u
/* [status,stage,begin,bodytype_end,delta,fields_read,validated]. A failed Pack
 * preserves the first scalar cursor, as the existing transactional reader does.
 */
int coh_initial_appearance_probe_json(const CohInitialAppearanceProbe *,char *,size_t);
/* After complete lists/slots/body prefix: [status,25+stage,done0,done1,list_end,
 * total_delta,m]. Stages27..32 BODYTYPE/SKIN/CONVERTED/SUPERSET/EXTRA/COLORS.
 * m: current0..3,additional4..11,deferred12,count13..16,body present17..18,
 * second-field cached19,compressed20,scalar-consumed21..27 (<=111).
 * Completed body masks3/3,prefix1 and first cached0 are implied. Old prefix end
 * =list_end+total_delta-scalar_consumed; exact failure=list_end+total_delta.
 * Slot end=list_end+(compressed?40:22). Earlier failure projections unchanged.
 */
int coh_initial_appearance_progress_json(const CohInitialRewardListProbe *,
 const CohInitialCostumeSlotsProbe *,const CohInitialCostumeBodyProbe *,
 const CohInitialAppearanceProbe *,char *,size_t);
#ifdef __cplusplus
}
#endif
#endif
