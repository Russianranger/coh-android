/* Synthetic list comparison only; no disk freshness authority. */
#ifndef COH_FILE_LIST_COMPARE_PROVIDER_H
#define COH_FILE_LIST_COMPARE_PROVIDER_H
#include "coh_costume_import.h"
#define FLC_NODE_MAX 16u
#define FLC_PATH_MAX 260u
#define FLC_RAW_MAX 520u
#define FLC_BUDGET_MAX (1024u*1024u)
#define FLC_STACK_RESERVE 16384u
#define FLC_INPUT 1u
#define FLC_IDENTITY 2u
#define FLC_PROFILE 3u
#define FLC_PATH 4u
#define FLC_DATE 5u
#define FLC_DIGEST 6u
#define FLC_RESERVE 7u
#define FLC_COMPLETE 8u
typedef struct{uint8_t source_id[32],build_id[32],profile_id[32],run_id[32],input_sha256[32];}FileCompareIdentity;
typedef struct{uint32_t length,date_bits;char path[FLC_RAW_MAX];}FileCompareEntry;
typedef struct{uint32_t count,directory_length;char directory[FLC_PATH_MAX];FileCompareEntry entries[FLC_NODE_MAX];}FileCompareList;
/* Immutable full typed request. Nonzero signed32 fixture dates only; all paths
 * preflight the original MAX_PATH buffer after literal raw-prefix removal.
 * reserve_fault1..2+totalINSERT refuses reservations before ALL originals.
 * No source allocator NULL injection or original OOM recovery is claimed. */
typedef struct{uint32_t reserve_fault;FileCompareList lists[2];}FileCompareRequest;
typedef struct{char path[FLC_PATH_MAX];uint32_t date_bits;}FileCompareValue;
/* Diagnostics contain no path or format strings: 0 none,1 missing,2 unequal
 * date; index is the source sorted bin index or UINT32_MAX when absent. */
typedef struct{uint32_t equal,bin_count,disk_count,diagnostic,diagnostic_index;FileCompareValue entries[2][FLC_NODE_MAX];}FileCompareResult;
typedef struct{uint32_t status,stage,failed_list,failed_entry,identity_matched,create_calls,insert_calls,find_calls,search_calls,allocation_calls,earray_insert_calls,directory_calls,normalization_calls,reservation_calls,reserved_nodes,node_count,cleanup_complete,compare_calls,size_calls,diagnostic_calls,selected_reader_results_checked,lists_unchanged;}FileCompareReceipt;
/* Valid disjoint request/identity/digest/context/output/receipt spans only.
 * Comparison false is a completed transaction, not wrapper failure. Output
 * publishes atomically only after owned snapshots and storage are wiped. */
CohStatus filecompare_apply(const FileCompareRequest*,const FileCompareIdentity*,const FileCompareIdentity*,const CohCostumeImportDigest*,FileCompareResult*,FileCompareReceipt*,size_t,size_t);
int filecompare_is_idle(void);
size_t filecompare_owned_bytes(void);
#endif
