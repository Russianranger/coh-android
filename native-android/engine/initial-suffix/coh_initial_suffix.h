#ifndef COH_INITIAL_SUFFIX_H
#define COH_INITIAL_SUFFIX_H
#include "../entities/coh_character_outer.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_SUFFIX_STAGE_COUNT 10u
#define COH_SUFFIX_RAM_MAX (8u*1024u*1024u)
#define COH_SUFFIX_STACK_RESERVE 65536u
typedef enum {
 COH_SUFFIX_CHARACTER=1,COH_SUFFIX_POWER_INFO,COH_SUFFIX_POWER_MODES,
 COH_SUFFIX_BADGES,COH_SUFFIX_BADGE_MONITOR,COH_SUFFIX_INVENTORY,
 COH_SUFFIX_SOCIAL,COH_SUFFIX_ATTRIBUTES,COH_SUFFIX_DYNAMIC,COH_SUFFIX_VIEW
}CohSuffixStage;
typedef struct{size_t begin_bit,end_bit;uint32_t observations[6];}CohSuffixSpan;
typedef struct{
 CohBytes packet;size_t packet_bits,begin_bit,end_bit;uint64_t packet_lease_token;
 uint32_t packet_id,full_update,stage_count,raw_suffix_syntax_validated;
 uint32_t selected_entity_verified,dictionary_authority,dynamic_owner_verified;
 uint32_t transport_end_verified,complete_initial_update,actor_publication,ack_permitted;
 CohSuffixSpan stages[COH_SUFFIX_STAGE_COUNT];
}CohSuffixDiagnostic;
typedef struct{
 uint32_t full_update,packet_id,diagnostic_dynamic_count;
 uint64_t packet_lease_token;CohCharacterWireProfile character_profile;
}CohSuffixContext;
typedef struct{void*data;size_t bytes,charged_bytes;}CohSuffixLoan;
typedef struct{
 void*context;size_t context_bytes;
 CohStatus(*acquire)(void*context,size_t minimum_bytes,size_t maximum_charged_bytes,CohSuffixLoan*loan);
 void(*release)(void*context,CohSuffixLoan*loan);
}CohSuffixMemory;
typedef struct{CohStatus status;CohSuffixStage stage;size_t bit;CohSuffixDiagnostic validated;}CohSuffixReport;
/* DIAGNOSTIC ONLY: begins at receiveCharacterFromServer in a source full_update
 * body, after entity list/debug/control/deletes. Context full_update must1; it
 * is raw caller context, not selected entity/header/framing certification.
 * Packet bytes must remain immutable and alive under caller's explicit lease
 * token while any report/view/span is used. No input copy/refcount is retained.
 * No token/expected_count is treated as ownership authority.
 *
 * Each stage leases disjoint aligned caller storage, validates with qualified
 * child API, records compact observations/spans, then releases before next.
 * Failed acquire must return zero/no ownership or a populated partial loan;
 * any nonzero loan field is released once even on acquisition error. Hidden
 * allocations not represented by a loan are forbidden. release accepts partial
 * descriptors from failed acquisition and must end their ownership.
 * context_bytes declares the disjoint callback owner span and is charged once.
 * acquire receives the maximum charged allocation BEFORE it allocates; it
 * must refuse before exceeding that allowance, including padding/overhead.
 * charged_bytes>=bytes covers ALL resident scratch, including inactive union
 * capacity. Release must end ownership before next acquire; allocator internals
 * retained between loans belong in retained_bytes. This permits actual6MiB
 * character storage release before badge's stricter4MiB aggregate admission.
 * No hidden malloc/free, cap increases or uncharged permanently reserved union.
 *
 * Public output/reader always remain unchanged while dynamic ownership is
 * unqualified. Active invention/full attributes refuse immediately. Otherwise
 * diagnostic raw suffix may validate through sky/slave, then returns UNSUPPORTED
 * for unowned dynamic data. Report holds only validated packet-backed spans,
 * never a completion/actor/ACK certificate. It does not assert packet end.
 * All explicit objects and packet spans disjoint; callbacks serialized, may
 * mutate only their own declared owner and loan storage, not packet/arguments.
 * Working budget charges input+caller output/report/context/provider+active
 * charged loan+64KiB native reserve+retained<=8MiB. External callback/zlib stack
 * and zlib sanitizer closure remain unqualified as documented. */
CohStatus coh_initial_suffix_diagnostic(CohRepReader *,const CohSuffixContext *,
 const CohSuffixMemory *,CohSuffixDiagnostic *,CohSuffixReport *,
 size_t budget,size_t retained_bytes);
size_t coh_initial_suffix_stage_bytes(CohSuffixStage);
#ifdef __cplusplus
}
#endif
#endif
