#ifndef COH_POWER_CATEGORIES_H
#define COH_POWER_CATEGORIES_H
#include "coh_origins.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_CATEGORY_MAX 256u
#define COH_CATEGORY_REFS_MAX 8192u
#define COH_CATEGORY_TEXT_MAX 262144u
#define COH_CATEGORY_INPUT_MAX 524288u
#define COH_CATEGORY_RAM_MAX 1048576u
#define COH_CATEGORY_STACK_RESERVE 8192u
typedef struct{CohOriginText fields[5];uint32_t set_first,set_count,index_first,index_count;}CohPowerCategoryEntry;
typedef struct{
 uint8_t input_sha256[32];uint64_t source_lease;
 uint32_t schema_crc,count,set_count,index_count,text_bytes,dependency_count;
 uint8_t raw_schema_validated,schema_crc_matched,complete_power_dictionary,actor_authority;
 CohPowerCategoryEntry entries[COH_CATEGORY_MAX];CohOriginText sets[COH_CATEGORY_REFS_MAX];
 uint32_t indices[COH_CATEGORY_REFS_MAX];char text[COH_CATEGORY_TEXT_MAX];
}CohPowerCategoryDictionary;
typedef struct{CohPowerCategoryDictionary candidate;}CohPowerCategoryWorkspace;
/* Complete original category cache grammar. Copies every string/set-name/raw
 * packed index in original order; no set reference is discarded or resolved.
 * Unique nonempty ASCII category names are required by the qualified source
 * hash/lookup profile. Duplicates refuse the entire import as original dictionary
 * construction does. All spans/digest scratch/retained charges precede callback;
 * no allocations; output unchanged on every refusal. Source bytes may retire on
 * success. Historical SHA/schema is not current server cache/generation authority.
 * Full set/power dictionary/repack/application/actor and ACK remain unqualified. */
CohStatus coh_power_categories_read(CohBytes,uint64_t,const uint8_t[32],const CohCostumeImportDigest*,
 CohPowerCategoryDictionary*,CohPowerCategoryWorkspace*,size_t,size_t);
CohStatus coh_power_categories_find(const CohPowerCategoryDictionary*,CohBytes,uint32_t*);
#ifdef __cplusplus
}
#endif
#endif
