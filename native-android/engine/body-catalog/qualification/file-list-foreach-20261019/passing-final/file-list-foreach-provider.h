/* Fixture only: no filesystem, runtime catalog or freshness authority. */
#ifndef COH_FILE_LIST_FOREACH_PROVIDER_H
#define COH_FILE_LIST_FOREACH_PROVIDER_H
#include "coh_costume_import.h"
#define FFE_OP_MAX 32u
#define FFE_NODE_MAX 16u
#define FFE_PATH_MAX 260u
#define FFE_RAW_MAX 520u
#define FFE_BUDGET_MAX (1024u*1024u)
#define FFE_STACK_RESERVE 16384u
#define FFE_INSERT 1u
#define FFE_FIND 2u
#define FFE_SEARCH 3u
#define FFE_INPUT 1u
#define FFE_IDENTITY 2u
#define FFE_PROFILE 3u
#define FFE_PATH 4u
#define FFE_DATE 5u
#define FFE_DIGEST 6u
#define FFE_CAPACITY 7u
#define FFE_RESERVE 8u
#define FFE_COMPLETE 9u
typedef struct{uint8_t source_id[32],build_id[32],profile_id[32],run_id[32],input_sha256[32];}FileForEachIdentity;
typedef struct{uint32_t kind,length,date_bits;char path[FFE_RAW_MAX];}FileForEachOperation;
/* Entire fixed typed request is immutable and hashed, including unused bytes.
 * INSERT strips the literal case-insensitive raw prefix before normalizing.
 * FIND normalizes only; SEARCH uses the supplied path literally. Zero INSERT
 * dates refuse even for duplicates, before all original functions execute.
 * reserve_fault 0 succeeds; 1..1+INSERT count refuses owned reservation before
 * source entry. It is not source allocator OOM recovery. callback_capacity is
 * 0..16 and must hold the exact independently preflighted unique stored list.
 * Capacity refusal precedes ALL original calls, including list construction.
 * There is no external callback selector or function-pointer argument. */
typedef struct{uint32_t count,directory_length,reserve_fault,callback_capacity;char directory[FFE_PATH_MAX];FileForEachOperation operations[FFE_OP_MAX];}FileForEachRequest;
/* Callback trace contains owned bytes and signed32 date bits only. */
typedef struct{char path[FFE_PATH_MAX];uint32_t date_bits;}FileForEachEntry;
typedef struct{uint32_t count;FileForEachEntry entries[FFE_NODE_MAX];}FileForEachResult;
typedef struct{uint32_t status,stage,failed_operation,identity_matched,create_calls,insert_calls,find_calls,search_calls,allocation_calls,earray_insert_calls,directory_calls,normalization_calls,reservation_calls,reserved_nodes,node_count,cleanup_complete,foreach_calls,callback_calls,node_addresses_checked,list_unchanged,context_closed,required_callbacks,callback_capacity;}FileForEachReceipt;
/* All request, labels, digest, digest context, output and receipt spans must be
 * valid and disjoint. Invalid sinks stay unchanged. Output commits atomically
 * after source completion and volatile cleanup; only safe numeric diagnostics
 * may change on refusal. No original heap/earray/platform closure is claimed. */
CohStatus fileforeach_apply(const FileForEachRequest*,const FileForEachIdentity*,const FileForEachIdentity*,const CohCostumeImportDigest*,FileForEachResult*,FileForEachReceipt*,size_t,size_t);
int fileforeach_is_idle(void);
size_t fileforeach_owned_bytes(void);
#endif
