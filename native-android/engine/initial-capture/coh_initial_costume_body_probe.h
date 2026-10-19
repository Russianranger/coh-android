#ifndef COH_INITIAL_COSTUME_BODY_PROBE_H
#define COH_INITIAL_COSTUME_BODY_PROBE_H
#include "coh_initial_costume_slots_probe.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
 COH_INITIAL_COSTUME_BODY_INPUT=1,COH_INITIAL_COSTUME_BODY_FLAG,
 COH_INITIAL_COSTUME_BODY_CACHE,COH_INITIAL_COSTUME_BODY_PRESENCE,
 COH_INITIAL_COSTUME_BODY_STORAGE,COH_INITIAL_COSTUME_BODY_TEXT,
 COH_INITIAL_COSTUME_BODY_INDEXED_DICTIONARY,COH_INITIAL_COSTUME_BODY_BODYTYPE
} CohInitialCostumeBodyStage;
typedef struct {
 CohStatus status;CohInitialCostumeBodyStage stage;
 size_t begin_bit,end_bit,failure_bit;
 uint32_t field,compressed,seen_mask,present_mask,complete_mask,cached_mask,
  cache_count,literals,literal_bytes,prefix_validated;
} CohInitialCostumeBodyProbe;
/* FIRST body's optional entTypeFile and costumeFilePrefix only, in the SAME
 * immutable ALLENTS loan after validated initial self/full-list slots. Reset
 * local cache state per call, as original costume_send/receive do per body.
 * Each present field reads cached flag. A hit requires one prior complete
 * literal, including empty; this two-field prefix never reads cache index bits.
 * Misses reuse the accepted260-byte NUL-inclusive literal leaf, discarding text.
 * Stop BEFORE any indexed-string Pack, or BEFORE bodytype Pack6 after both
 * optional fields complete. Neither boundary returns COH_OK. Exact-end INVALID
 * retains completed literals/fields and prefix observation. This is syntax,
 * never a resource identity, costume/character, ownership or generation proof.
 * No allocation/text/pointer retention; at most4168 packed/4224 compressed bits,
 * existing4MiB cap. Invalid API/alias input leaves output unchanged.
 */
CohStatus coh_initial_costume_body_probe(const CohRepReader *,CohInitialCostumeBodyProbe *);
#define COH_INITIAL_COSTUME_BODY_REPORT_MAX 96u
/* [status,stage,field,begin,delta,metadata]. Field1 entTypeFile,2 prefix.
 * Metadata: present0..1, complete2..3, cached4..5, prefix_validated6,
 * seen7..8, compressed9. All fields are numeric; no text is retained/exported. */
int coh_initial_costume_body_probe_json(const CohInitialCostumeBodyProbe *,char *,size_t);
/* After complete lists/slots: [status,stage14..26,done0,done1,list_end,delta,m].
 * Absolute failure=list_end+delta; slot end=list_end+(compressed?40:22).
 * m: current0..3,additional4..11,deferred12,count13..16,present17..18,
 * complete19..20,cached21..22,prefix_validated23,seen24..25,compressed26.
 * Full-list1 and slot-framing1 are implied. Stage14..19 field1 FLAG..DICTIONARY;
 * stage20..25 field2 FLAG..DICTIONARY;26 FIRST_BODYTYPE_REQUIRED.
 * Reject bad context/domains; keep prior reward/slot failure projections intact.
 */
int coh_initial_costume_body_progress_json(const CohInitialRewardListProbe *,
 const CohInitialCostumeSlotsProbe *,const CohInitialCostumeBodyProbe *,char *,size_t);
#ifdef __cplusplus
}
#endif
#endif
