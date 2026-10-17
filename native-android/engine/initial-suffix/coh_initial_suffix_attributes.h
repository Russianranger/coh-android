#ifndef COH_INITIAL_SUFFIX_ATTRIBUTES_H
#define COH_INITIAL_SUFFIX_ATTRIBUTES_H
#include "coh_initial_suffix.h"
#include "../entity-attributes/coh_attrib_description.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct{
 CohSuffixContext base;const CohAttributeDictionary*attribute_schema;
 uint8_t expected_attribute_sha256[32];uint64_t attribute_lease;
 const CohAttribReadControl*attribute_control;
}CohSuffixAttributesContext;
/* Additive raw full-attribute profile. Original suffix API/stage sizes remain
 * unchanged. Every other source stage is identical to the frozen original raw
 * suffix implementation; this profile uses the full/monitor attribute reader.
 * Schema input, schema metadata, profile, optional control/context and its
 * pre-reserved scratch are disjoint/charged once, including enclosing loans.
 * The supplied schema must remain immutable/alive under the explicit lease.
 * Same partial-loan/preallocation/provider/packet rules as original suffix.
 * Raw complete syntax still refuses unowned dynamic/world/dictionary authority;
 * public reader/output remain unchanged. No actor, full update or ACK permit.
 * Active invention/full-initial impossible social flags still refuse.
 * External callback/zlib/crypto stack and sanitizer closure remain unqualified.
 */
CohStatus coh_initial_suffix_attributes_diagnostic(CohRepReader*,const CohSuffixAttributesContext*,
 const CohSuffixMemory*,CohSuffixDiagnostic*,CohSuffixReport*,size_t budget,size_t retained_bytes);
size_t coh_initial_suffix_attributes_stage_bytes(CohSuffixStage);
#ifdef __cplusplus
}
#endif
#endif
