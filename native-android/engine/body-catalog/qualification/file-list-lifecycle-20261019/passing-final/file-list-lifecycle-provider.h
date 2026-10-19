/* Fixture only: no filesystem, runtime catalog or freshness authority. */
#ifndef COH_FILE_LIST_LIFECYCLE_PROVIDER_H
#define COH_FILE_LIST_LIFECYCLE_PROVIDER_H
#include "coh_costume_import.h"
#define FLL_OP_MAX 32u
#define FLL_NODE_MAX 16u
#define FLL_PATH_MAX 260u
#define FLL_RAW_MAX 520u
#define FLL_BUDGET_MAX (1024u*1024u)
#define FLL_STACK_RESERVE 16384u
#define FLL_INSERT 1u
#define FLL_FIND 2u
#define FLL_SEARCH 3u
#define FLL_INPUT 1u
#define FLL_IDENTITY 2u
#define FLL_PROFILE 3u
#define FLL_PATH 4u
#define FLL_DATE 5u
#define FLL_DIGEST 6u
#define FLL_CAPACITY 7u
#define FLL_RESERVE 8u
#define FLL_COMPLETE 9u
typedef struct{uint8_t source_id[32],build_id[32],profile_id[32],run_id[32],input_sha256[32];}FileLifecycleIdentity;
typedef struct{uint32_t kind,length,date_bits;char path[FLL_RAW_MAX];}FileLifecycleOperation;
/* Typed immutable owned fixture request. Modes: 0 ordinary owned array;
 * 1 NULL handle (no operations); 2 append one NULL slot. Modes3..7 describe
 * borrowed node/storage, compressed flags, invalid count/capacity and refuse
 * before original execution. No caller-supplied pointers enter the list.
 * Nonzero INSERT dates exclude filesystem calls. Reservation faults occur
 * before ALL original calls and release every already-reserved host block. */
typedef struct{uint32_t count,directory_length,reserve_fault,fixture_mode;char directory[FLL_PATH_MAX];FileLifecycleOperation operations[FLL_OP_MAX];}FileLifecycleRequest;
typedef struct{char path[FLL_PATH_MAX];uint32_t date_bits;}FileLifecycleEntry;
typedef struct{uint32_t count;FileLifecycleEntry entries[FLL_NODE_MAX];}FileLifecycleResult;
typedef struct{uint32_t status,stage,failed_operation,identity_matched,create_calls,insert_calls,find_calls,search_calls,allocation_calls,earray_insert_calls,directory_calls,normalization_calls,reservation_calls,reserved_nodes,node_count,cleanup_complete,length_calls,destroy_calls,node_free_calls,storage_free_calls,handle_null,slots_cleared,release_order_checked,reservation_releases,fixture_mode;}FileLifecycleReceipt;
/* All arguments and digest context are disjoint spans. Outputs contain owned
 * value copies only and publish after source destruction and owner wipe.
 * No original engine allocator, platform heap, scanning or freshness closure. */
CohStatus filelifecycle_apply(const FileLifecycleRequest*,const FileLifecycleIdentity*,const FileLifecycleIdentity*,const CohCostumeImportDigest*,FileLifecycleResult*,FileLifecycleReceipt*,size_t,size_t);
int filelifecycle_is_idle(void);
size_t filelifecycle_owned_bytes(void);
#endif
