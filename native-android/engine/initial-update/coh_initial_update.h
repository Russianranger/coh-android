#ifndef COH_INITIAL_UPDATE_H
#define COH_INITIAL_UPDATE_H
#include "../initial-record/coh_initial_list.h"
#include "../initial-suffix/coh_initial_suffix.h"
#include "../entity-control/coh_entity_control.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_INITIAL_UPDATE_STACK_RESERVE (COH_INITIAL_LIST_STACK_RESERVE+32768u)
typedef struct{
 CohSelectedRecordContext record; CohCharacterWireProfile character;
 uint32_t session_generation,schema_generation,legacy_commands,diagnostic_dynamic_count;
}CohInitialUpdateContext;
typedef enum{COH_INITIAL_COMMAND=1,COH_INITIAL_HEADER,COH_INITIAL_LIST,
 COH_INITIAL_CONTROL,COH_INITIAL_DELETES,COH_INITIAL_SUFFIX,COH_INITIAL_COMMAND_TAIL,
 COH_INITIAL_AUTHORITY}CohInitialUpdateStage;
typedef struct{
 CohBytes packet;size_t packet_bits,begin_bit,header_end_bit,list_end_bit,
 control_end_bit,deletes_end_bit,suffix_end_bit,end_bit;
 uint64_t packet_lease_token;uint32_t packet_id,session_generation;
 CohRepUpdatePrefix header;CohInitialList list;CohControlUpdate control;
 CohEntDeletes deletes;CohSuffixDiagnostic suffix;
 uint32_t raw_initial_syntax_validated,transport_end_verified,command_count;
 uint32_t selected_owner_verified,dictionary_authority,dynamic_owner_verified,
 complete_initial_update,actor_publication,ack_permitted;
}CohInitialUpdateDiagnostic;
typedef struct{
 CohStatus status;CohInitialUpdateStage stage;size_t bit;uint32_t refused_command;
 CohInitialListFailure list;CohControlFailure control;CohEntFailure deletes;
 CohSuffixReport suffix;CohInitialUpdateDiagnostic validated;
}CohInitialUpdateReport;
typedef struct{const void*pointer;size_t bytes;}CohInitialUpdateSpan;
typedef struct{
 const CohSelectedRecordMemory*original;CohInitialUpdateSpan spans[9];
}CohInitialUpdateAllocator;
typedef struct{
 CohRepReader reader;CohSelectedRecordContext record_context;
 CohInitialListWorkspace list_workspace;CohInitialListEntry entries[COH_ENT_LIST_MAX];
 CohSuffixContext suffix_context;CohSuffixDiagnostic suffix_output;
 CohSelectedRecordMemory record_memory;CohSuffixMemory suffix_memory;
 CohInitialUpdateAllocator allocator;
}CohInitialUpdateWorkspace;
/* Source-ordered INITIAL ALLENTS diagnostic owner. Whole public reader is
 * unchanged on every return; only report/workspace are scratch. A fully read
 * raw syntax candidate is reported with UNSUPPORTED until authentic selected
 * handoff, exact runtime dictionaries and world/dynamic ownership are admitted.
 * No actor, complete-update or ACK permit is minted from caller context.
 *
 * Header(debug0/odd1)->full-create compact list->control->deletes->entire
 * character/global suffix->bounded trailing meta-command/zero-end profile.
 * Unknown game commands refuse before their body, never scan/skip. Nested
 * commands use original normalized enum values even in legacy top-level mode.
 * At most256 creates; existing local bounds and stricter child budgets remain.
 * Only deletes naming this same packet's creates are supported; unknown prior
 * tombstones require an admitted previous-world owner, not silent discard.
 * Source same-packet delete cannot remove a just-created slot. Control is raw
 * staging; no final simulation position is inferred from entity/forced pose.
 *
 * Packet/schema/dictionary/context/provider/report/workspace/reader spans must
 * be pairwise disjoint. Packet is immutable under the enclosing caller's lease
 * for the complete diagnostic lifetime. Reports retain only packet-backed spans
 * and compact observations; scratch loans are released sequentially. The loan
 * provider obeys selected-record preallocation/partial-release contracts and
 * may modify only its own declared context and active loan. Retained pools and
 * allocator overhead are charged in retained_bytes/charged_bytes. Named8MiB
 * charges all explicit owned storage, input, dictionary, active loan and128KiB
 * native stack. External callback/zlib stack and sanitizer closure are not
 * inferred. Workspace entries are scratch, never a persistent published list.
 */
CohStatus coh_initial_update_diagnostic(CohRepReader*,const CohInitialUpdateContext*,
 const CohRepSchema*,const CohSelectedRecordMemory*,CohInitialUpdateWorkspace*,
 CohInitialUpdateReport*,size_t budget,size_t retained_bytes);
#ifdef __cplusplus
}
#endif
#endif
