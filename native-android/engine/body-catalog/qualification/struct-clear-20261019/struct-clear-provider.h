/* Original source fixture only; no runtime/catalog/generation/authority. */
#ifndef COH_BODY_READ_PROVIDER_H
#define COH_BODY_READ_PROVIDER_H
#include "coh_costume_import.h"
#define STRUCT_CLEAR_STAGE_INPUT 1u
#define STRUCT_CLEAR_STAGE_IDENTITY 2u
#define STRUCT_CLEAR_STAGE_PROFILE 3u
#define STRUCT_CLEAR_STAGE_HEADER 4u
#define STRUCT_CLEAR_STAGE_TYPE_LENGTH 5u
#define STRUCT_CLEAR_STAGE_HEADER_EXTENT 6u
#define STRUCT_CLEAR_STAGE_DEPENDENCY_HEADER 7u
#define STRUCT_CLEAR_STAGE_DEPENDENCY_SIZE 8u
#define STRUCT_CLEAR_STAGE_BODY_LENGTH 9u
#define STRUCT_CLEAR_STAGE_COUNT 10u
#define STRUCT_CLEAR_STAGE_ROW_LENGTH 11u
#define STRUCT_CLEAR_STAGE_STRING 12u
#define STRUCT_CLEAR_STAGE_SCALAR 13u
#define STRUCT_CLEAR_STAGE_DIGEST 14u
#define STRUCT_CLEAR_STAGE_HEADER_REJECT 15u
#define STRUCT_CLEAR_STAGE_SOURCE_REJECT 16u
#define STRUCT_CLEAR_STAGE_RESERVATION 17u
#define STRUCT_CLEAR_STAGE_COMPLETE 18u
#define STRUCT_CLEAR_PART_MAX 30u
#define STRUCT_CLEAR_STRING_MAX 260u
#define STRUCT_CLEAR_INPUT_MAX 65536u
#define STRUCT_CLEAR_BUDGET_MAX (1024u*1024u)
#define STRUCT_CLEAR_STACK_RESERVE 98304u
typedef struct{uint8_t source_id[32],build_id[32],profile_id[32],run_id[32],input_sha256[32];}StructClearIdentity;
typedef struct{
 char name[260],source_file[260],geometry_name[260],texture_name[260],base_name[260];
 uint32_t raw[7]; /* first BoneCount,influence,last BoneCount,DontClear,bones2,index */
 uint32_t final_num_parts,final_influence_cost,final_dont_clear,final_bones[2],final_index,string_null_mask;
}StructClearPart;
typedef struct{
 uint32_t source_crc,header_end,dependency_end,body_end,part_count,raw_array_count,body_declared_size;
 StructClearPart parts[STRUCT_CLEAR_PART_MAX];
}StructClearResult;
typedef struct{
 uint32_t clear_nodes,clear_strings,clear_arrays,clear_order_count,clear_order[30],clear_numeric_preserved,clear_root_null;
 uint32_t entry_calls,shared_calls,acquire_calls,load_calls,locate_calls,persist_calls,binary_calls,callback_calls,struct_clear_calls,loader_return,getter_count,selected_handle,supplied_handle_matched,selector_diagnostics,loader_diagnostics,trace_count,trace[32];
 uint32_t source_crc,source_calls,crc_calls,mode_calls,update_calls,stream_bytes,visited_fields,interpret_calls,crypto_cleanup_complete;
 uint32_t status,stage,failure_byte,open_calls,read_calls,seek_calls;
 uint32_t source_close_calls,wrapper_close_calls,header_accepted,filelist_calls;
 uint32_t table_calls,capacity_calls,allocation_calls,string_calls,int_calls,u8_calls;
 uint32_t warning_calls,source_result,header_end,dependency_end,body_end;
 uint32_t source_node_count,raw_array_count,body_declared_size,fixture_identity_matched,cleanup_complete;
}StructClearReceipt;
/* All spans/digest context disjoint. Invalid sinks unchanged. Safe numeric
 * diagnostics may change on refusal; result commits only after source success
 * and owned cleanup. Actual original CRC feeds original production ignoreCRC1 open. fault0 normal,1 owned open refusal,2 row-arena reservation refusal,3 crypto-object reservation refusal,4 fixture missing-cache path; reservation refusals precede source entry. Original NULL allocator returns are not recoverable and are not simulated.
 */
CohStatus struct_clear_apply(CohBytes,const StructClearIdentity*,const StructClearIdentity*,
 const CohCostumeImportDigest*,uint32_t,uint32_t,
 StructClearResult*,StructClearReceipt*,size_t,size_t);
int struct_clear_is_idle(void);
size_t struct_clear_owner_bytes(void);
size_t struct_clear_crypto_object_bytes(void);

/* No pointer-bearing request or borrowed storage is admitted. present=0 keeps
 * a partial earray slot NULL; string_mask chooses the five original strings.
 * Every selected string is owned even when its length is zero. pool/borrowed
 * and unsupported storage modes refuse before any original code executes. */
typedef struct{uint32_t present,string_mask,length[5];}StructClearRow;
typedef struct{uint32_t count,array_present,reserve_fault,borrowed;StructClearRow rows[30];}StructClearRequest;
typedef struct{uint32_t rows,strings,arrays,order_count,order[30],numeric_preserved,root_null,repeat_no_releases;}StructClearFixtureResult;
CohStatus struct_clear_fixture(const StructClearRequest*,const StructClearIdentity*,const StructClearIdentity*,const CohCostumeImportDigest*,StructClearFixtureResult*,StructClearReceipt*,size_t,size_t);
#endif
