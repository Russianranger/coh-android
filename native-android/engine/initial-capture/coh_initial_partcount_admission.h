#ifndef COH_INITIAL_PARTCOUNT_ADMISSION_H
#define COH_INITIAL_PARTCOUNT_ADMISSION_H
#include "coh_initial_partcount_probe.h"
#include "../character-dictionary/coh_costume_owner.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
 COH_INITIAL_COUNT_ADMISSION_INPUT=1, COH_INITIAL_COUNT_ADMISSION_APPEARANCE,
 COH_INITIAL_COUNT_ADMISSION_SGCOLORS, COH_INITIAL_COUNT_ADMISSION_SCALES,
 COH_INITIAL_COUNT_ADMISSION_FRAMING, COH_INITIAL_COUNT_ADMISSION_DEFAULT_CATALOG,
 COH_INITIAL_COUNT_ADMISSION_EXPLICIT_CATALOG, COH_INITIAL_COUNT_ADMISSION_BODYTYPE,
 COH_INITIAL_COUNT_ADMISSION_COUNT, COH_INITIAL_COUNT_ADMISSION_PART_BODY
} CohInitialCountAdmissionStage;
typedef struct {
 CohStatus status; CohInitialCountAdmissionStage stage;
 size_t begin_bit, count_begin_bit, end_bit, failure_bit;
 uint32_t explicit_count, part_count, catalog_validated;
} CohInitialCountAdmission;
/* Nonshipping, read-only continuation from the SAME exact immutable ALLENTS
 * loan at its previously established appearance/bodytype begin. Replays the
 * existing bounded appearance/SG/scales/count probes; bodytype is reread from
 * that same prefix rather than accepted as a caller integer. Framing flag0
 * REQUIRES a source-current owner query supplying actual GetBodyPartCount;
 * flag1 preserves separate Pack4 framing and the SAME catalog/generation gate.
 * Then original bodytype<count followed by count<=GetBodyPartCount is checked
 * before any part/cache/index bit, including explicit0. Local cap30 is a safety
 * policy, never a source default. This API always refuses to accept a costume:
 * qualified admission ends UNSUPPORTED/PART_BODY at the exact count end.
 *
 * Production owner query currently has NO authenticated runtime producer and
 * therefore cannot admit a count. Test-only substitute queries are not current
 * provenance. Source/session/generation/loan ownership and immutable lifetime
 * belong to that opaque query; the caller must hold its actual provider leases
 * across this synchronous call. No persistent owner, reservation ticket, heap
 * allocation, callback retention or raw packet/bodytype retention is introduced.
 * Existing 4MiB packet cap and 16KiB call reserve remain; external owner/source
 * dependencies and old/new candidates remain charged by the actual parent.
 * Input reader/packet unchanged. Invalid API/alias preserves output; semantic
 * refusal publishes only the bounded diagnostic. No parts, actor or ACK permit.
 */
CohStatus coh_initial_partcount_admission(const CohRepReader *,
 const CohCostumeOwner *,const CohCostumePacketBinding *,CohInitialCountAdmission *);
#ifdef __cplusplus
}
#endif
#endif
