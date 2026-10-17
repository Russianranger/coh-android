#ifndef COH_INITIAL_UPDATE_ATTRIBUTES_H
#define COH_INITIAL_UPDATE_ATTRIBUTES_H
#include "coh_initial_update.h"
#include "../initial-suffix/coh_initial_suffix_attributes.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct{
 CohInitialUpdateContext base;const CohAttributeDictionary*attribute_schema;
 uint8_t expected_attribute_sha256[32];uint64_t attribute_lease;
 const CohAttribReadControl*attribute_control;
}CohInitialUpdateAttributesContext;
typedef struct{
 const CohSelectedRecordMemory*original;CohInitialUpdateSpan spans[13];
}CohInitialUpdateAttributesAllocator;
typedef struct{
 CohRepReader reader;CohSelectedRecordContext record_context;
 CohInitialListWorkspace list_workspace;CohInitialListEntry entries[COH_ENT_LIST_MAX];
 CohSuffixAttributesContext suffix_context;CohSuffixDiagnostic suffix_output;
 CohSelectedRecordMemory record_memory;CohSuffixMemory suffix_memory;
 CohInitialUpdateAttributesAllocator allocator;
}CohInitialUpdateAttributesWorkspace;
/* Additive full initial raw profile with exact ordered attribute schema. Reads
 * the same original header/list/control/deletes/character/global/command order
 * as the frozen initial diagnostic, using the schema-bound optional attribute
 * suffix. Original public API and all native child implementations unchanged.
 * Attribute profile/schema/input/control/context/scratch are disjoint, charged
 * once and included in enclosing loan alias checks BEFORE any allocation.
 * Schema/current source association remains a caller-owned immutable diagnostic
 * prerequisite; caller keeps profile/schema/packet under their explicit leases
 * for any report use/replay. Counts/lease labels are not authority.
 * Same named8MiB,128KiB native reserve, sequential pre-reserved loans and strict
 * child bounds. Runtime dictionary/world/selection authority remains false;
 * output reader always unchanged and return never OK. No actor/complete update/
 * READY/RECEIVED_CHARACTER/application ACK. Unknown command/delete tails refuse.
 * External callback/zlib/crypto dependency stack/sanitizer closure unqualified.
 */
CohStatus coh_initial_update_attributes_diagnostic(CohRepReader*,const CohInitialUpdateAttributesContext*,
 const CohRepSchema*,const CohSelectedRecordMemory*,CohInitialUpdateAttributesWorkspace*,
 CohInitialUpdateReport*,size_t budget,size_t retained_bytes);
#ifdef __cplusplus
}
#endif
#endif
