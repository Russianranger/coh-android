/* Original source fixture only; no runtime/catalog/generation/authority. */
#ifndef COH_BODY_READ_PROVIDER_H
#define COH_BODY_READ_PROVIDER_H
#include "coh_costume_import.h"
#define CACHE_HIT_LOADER_STAGE_INPUT 1u
#define CACHE_HIT_LOADER_STAGE_IDENTITY 2u
#define CACHE_HIT_LOADER_STAGE_PROFILE 3u
#define CACHE_HIT_LOADER_STAGE_HEADER 4u
#define CACHE_HIT_LOADER_STAGE_TYPE_LENGTH 5u
#define CACHE_HIT_LOADER_STAGE_HEADER_EXTENT 6u
#define CACHE_HIT_LOADER_STAGE_DEPENDENCY_HEADER 7u
#define CACHE_HIT_LOADER_STAGE_DEPENDENCY_SIZE 8u
#define CACHE_HIT_LOADER_STAGE_BODY_LENGTH 9u
#define CACHE_HIT_LOADER_STAGE_COUNT 10u
#define CACHE_HIT_LOADER_STAGE_ROW_LENGTH 11u
#define CACHE_HIT_LOADER_STAGE_STRING 12u
#define CACHE_HIT_LOADER_STAGE_SCALAR 13u
#define CACHE_HIT_LOADER_STAGE_DIGEST 14u
#define CACHE_HIT_LOADER_STAGE_HEADER_REJECT 15u
#define CACHE_HIT_LOADER_STAGE_SOURCE_REJECT 16u
#define CACHE_HIT_LOADER_STAGE_RESERVATION 17u
#define CACHE_HIT_LOADER_STAGE_COMPLETE 18u
#define CACHE_HIT_LOADER_PART_MAX 30u
#define CACHE_HIT_LOADER_STRING_MAX 260u
#define CACHE_HIT_LOADER_INPUT_MAX 65536u
#define CACHE_HIT_LOADER_BUDGET_MAX (1024u*1024u)
#define CACHE_HIT_LOADER_STACK_RESERVE 98304u
typedef struct{uint8_t source_id[32],build_id[32],profile_id[32],run_id[32],input_sha256[32];}CacheHitLoaderIdentity;
typedef struct{
 char name[260],source_file[260],geometry_name[260],texture_name[260],base_name[260];
 uint32_t raw[7]; /* first BoneCount,influence,last BoneCount,DontClear,bones2,index */
 uint32_t final_num_parts,final_influence_cost,final_dont_clear,final_bones[2],final_index,string_null_mask;
}CacheHitLoaderPart;
typedef struct{
 uint32_t source_crc,header_end,dependency_end,body_end,part_count,raw_array_count,body_declared_size;
 CacheHitLoaderPart parts[CACHE_HIT_LOADER_PART_MAX];
}CacheHitLoaderResult;
typedef struct{
 uint32_t entry_calls,shared_calls,acquire_calls,load_calls,locate_calls,persist_calls,binary_calls,callback_calls,struct_clear_calls,loader_return,getter_count,selected_handle,supplied_handle_matched,selector_diagnostics,loader_diagnostics,trace_count,trace[32];
 uint32_t source_crc,source_calls,crc_calls,mode_calls,update_calls,stream_bytes,visited_fields,interpret_calls,crypto_cleanup_complete;
 uint32_t status,stage,failure_byte,open_calls,read_calls,seek_calls;
 uint32_t source_close_calls,wrapper_close_calls,header_accepted,filelist_calls;
 uint32_t table_calls,capacity_calls,allocation_calls,string_calls,int_calls,u8_calls;
 uint32_t warning_calls,source_result,header_end,dependency_end,body_end;
 uint32_t source_node_count,raw_array_count,body_declared_size,fixture_identity_matched,cleanup_complete;
}CacheHitLoaderReceipt;
/* All spans/digest context disjoint. Invalid sinks unchanged. Safe numeric
 * diagnostics may change on refusal; result commits only after source success
 * and owned cleanup. Actual original CRC feeds original production ignoreCRC1 open. fault0 normal,1 owned open refusal,2 row-arena reservation refusal,3 crypto-object reservation refusal,4 fixture missing-cache path; reservation refusals precede source entry. Original NULL allocator returns are not recoverable and are not simulated.
 */
CohStatus cache_hit_loader_apply(CohBytes,const CacheHitLoaderIdentity*,const CacheHitLoaderIdentity*,
 const CohCostumeImportDigest*,uint32_t,uint32_t,
 CacheHitLoaderResult*,CacheHitLoaderReceipt*,size_t,size_t);
int cache_hit_loader_is_idle(void);
size_t cache_hit_loader_owner_bytes(void);
size_t cache_hit_loader_crypto_object_bytes(void);
#endif
