#ifndef COH_ATTRIBUTE_DICTIONARY_H
#define COH_ATTRIBUTE_DICTIONARY_H
#include "../costume-import/coh_costume_import.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_ATTRIBUTE_DICTIONARY_ROWS_MAX 256u
#define COH_ATTRIBUTE_DICTIONARY_CATEGORIES_MAX 32u
#define COH_ATTRIBUTE_DICTIONARY_INPUT_MAX 65536u
#define COH_ATTRIBUTE_DICTIONARY_RAM_MAX (512u*1024u)
#define COH_ATTRIBUTE_DICTIONARY_STACK_RESERVE 16384u
typedef struct{
 uint32_t category,row,category_rows,type,style,key,offset,show_base_word,lookup_key;
 CohBytes category_name,name,display_name,tooltip;
}CohAttributeDescription;
typedef struct{
 CohBytes input;uint64_t input_lease_token;uint8_t input_sha256[32];
 uint32_t schema_crc,category_count,row_count,dependency_count;
 CohAttributeDescription ordered[COH_ATTRIBUTE_DICTIONARY_ROWS_MAX];
 uint32_t raw_schema_validated,schema_crc_matched,runtime_cache_branch_verified,
 current_server_generation,actor_authority;
}CohAttributeDictionary;
typedef struct{CohAttributeDictionary candidate;}CohAttributeDictionaryWorkspace;
/* Exact Parse6 attribute-category schema, original ordinal ordering reversed
 * exactly as send/receiveAttribDescription. Full segment lengths/counts/strings
 * validate atomically; no dense key filtering or duplicate removal. lookup_key
 * preserves original 32-bit (sizeof(CharacterAttributes)*type)+offset arithmetic.
 * show_base_word retains original raw U32 before original U8 narrowing.
 * Input and string views are borrowed immutable under a nonzero caller lease.
 * Expected complete input SHA must be independently bound to recovery evidence;
 * digest provider runs only after complete bounded admission/reservation. Its
 * scratch_reserve/owner and external stack/crypto closure remain explicit.
 * Schema CRC matches qualified original ParseTableCRC0x315acdb1; this does not
 * observe CLIENT/SERVER shared/cache selection or a matching live generation.
 * No state dictionaries/current runtime or actor authority is inferred.
 * All explicit spans are pairwise disjoint; budget charges fullinput/out/work/
 * expectedSHA/provider/context/scratch+16KiBnative reserve+retained<=512KiB.
 * Refusal preserves output, workspace is scratch. No hidden allocations.
 */
CohStatus coh_attribute_dictionary_read(CohBytes,uint64_t lease,const uint8_t expected_sha256[32],
 const CohCostumeImportDigest*,CohAttributeDictionary*,CohAttributeDictionaryWorkspace*,
 size_t budget,size_t retained_bytes);
#ifdef __cplusplus
}
#endif
#endif
