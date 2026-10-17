#ifndef COH_SELECTED_RECORD_H
#define COH_SELECTED_RECORD_H
#include "../entities/coh_costume.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_SELECTED_RECORD_STAGES 13u
#define COH_SELECTED_RECORD_RAM_MAX (8u*1024u*1024u)
#define COH_SELECTED_RECORD_STACK_RESERVE 65536u
typedef enum{
 COH_RECORD_CREATE=1,COH_RECORD_POSE_SEQUENCE,COH_RECORD_TRIGGERS,COH_RECORD_NETFX,
 COH_RECORD_COSTUME,COH_RECORD_POWER_CUSTOM,COH_RECORD_TITLES,COH_RECORD_RAGDOLL,
 COH_RECORD_COMMON,COH_RECORD_TASKFORCE,COH_RECORD_RARE_PREFIX,
 COH_RECORD_RARE_TAIL,COH_RECORD_TEAMMATE
}CohSelectedRecordStage;
typedef struct{size_t begin_bit,end_bit;uint32_t observations[6];}CohSelectedRecordSpan;
typedef struct{
 uint32_t selected_dbid,packet_id,entity_index,interp_level,dictionary_generation;
 const CohEntCostumeDictionary*costume_dictionary;uint64_t packet_lease_token;
 uint8_t expected_dictionary_sha256[32];
}CohSelectedRecordContext;
typedef struct{
 CohBytes packet;size_t packet_bits,begin_bit,end_bit;uint64_t packet_lease_token;
 uint32_t packet_id,dictionary_generation,stage_count,raw_record_validated;
 CohEntSlot selected;CohEntRecord core;CohEntTitles titles;CohEntRarePrefix rare_prefix;
 CohSelectedRecordSpan stages[COH_SELECTED_RECORD_STAGES];
 uint8_t dictionary_manifest_sha256[32];
 uint32_t selected_wire_dbid_matched,dictionary_manifest_matched,whole_list_uniqueness_verified,
  dictionary_authority,complete_initial_update,actor_publication,ack_permitted;
}CohSelectedRecord;
typedef struct{CohSelectedRecord candidate;}CohSelectedRecordWorkspace;
typedef struct{void*data;size_t bytes,charged_bytes;}CohSelectedRecordLoan;
typedef struct{
 void*context;size_t context_bytes;
 CohStatus(*acquire)(void*,size_t minimum_bytes,size_t maximum_charged_bytes,CohSelectedRecordLoan*);
 void(*release)(void*,CohSelectedRecordLoan*);
}CohSelectedRecordMemory;
typedef struct{CohStatus status;CohSelectedRecordStage stage;size_t bit;CohEntFailure entity;uint32_t validated_stages;}CohSelectedRecordFailure;
/* INITIAL SELECTED SELF-CREATE raw record, starting after the list delta index.
 * Strict source order through the FINAL teammate/buff body; no scanning/skips.
 * End sentinel/non-create/nonself/interpolated unsupported profiles refuse.
 * context DBID must come from the actual owned source-qualified DB handoff,
 * never a slot/cookie/fixture. Context integers do not authenticate that owner.
 * Prior slot is copied/reset with existing create/delete ordering, not mutated.
 * Packet views retain exact spans plus compact raw states/events, no huge POD
 * appearance/power/SG/buff copies. All conditional bodies are fully validated
 * through qualified child parsers before reader/output commit. The report is
 * diagnostic only. No whole-list uniqueness, source dictionary authority,
 * initial-update/actor/ACK certificate; later full transaction gates remain.
 *
 * Non-NULL dictionary requires a nonzero expected manifest SHA; every decoded
 * full appearance and taskforce costume must match it, not generation alone.
 * Packet immutable lease and exact dictionary generation/source ownership must
 * remain alive in the enclosing owner while views are used/replayed. Loan data
 * is released before the next stage; result has no loan-pointer dependency.
 * acquire receives a preallocation maximum including all overhead/padding;
 * partial populated error loans must release once, no hidden ownership. release
 * ends active ownership; reusable retained pools belong in retained_bytes.
 * Callback owner context bytes and every explicit span pairwise disjoint; only
 * that owner/loan scratch may mutate in callbacks. Loan alignment>=long double.
 * Named8MiB owned budget charges full fixed/input/prior/context/output/report/
 * workspace/dictionary bytes+active charged loan+64KiB stack+caller retained.
 * SG tail and buff stage also obey existing stricter4MiB aggregate caps. No
 * callback allocator stack/whole library resident-memory closure is inferred.
 */
CohStatus coh_selected_record_read(CohRepReader*,const CohSelectedRecordContext*,
 const CohEntSlot*prior,const CohSelectedRecordMemory*,CohSelectedRecord*,
 CohSelectedRecordWorkspace*,CohSelectedRecordFailure*,size_t budget,size_t retained_bytes);
size_t coh_selected_record_stage_bytes(CohSelectedRecordStage);
#ifdef __cplusplus
}
#endif
#endif
