#ifndef COH_ORIGINS_H
#define COH_ORIGINS_H
#include "../costume-import/coh_costume_import.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_ORIGIN_MAX 128u
#define COH_ORIGIN_TEXT_MAX 32768u
#define COH_ORIGIN_INPUT_MAX 65536u
#define COH_ORIGIN_RAM_MAX 262144u
#define COH_ORIGIN_STACK_RESERVE 8192u
typedef struct{uint32_t offset,size;}CohOriginText;
typedef struct{CohOriginText fields[5];}CohOriginEntry;
typedef struct{
 uint8_t input_sha256[32];uint64_t source_lease;
 uint32_t schema_crc,count,text_bytes,dependency_count;
 uint8_t raw_schema_validated,schema_crc_matched,runtime_generation,actor_authority;
 CohOriginEntry entries[COH_ORIGIN_MAX];char text[COH_ORIGIN_TEXT_MAX];
}CohOriginDictionary;
typedef struct{CohOriginDictionary candidate;}CohOriginWorkspace;
/* Complete original ParseCharacterOrigins binary schema, exact input digest and
 * original ParseTableCRC. Entries/strings are copied in original array order;
 * duplicates and empty fields preserved. Input may retire after successful read.
 * The nonzero lease names source provenance only, never live server generation.
 * Digest provider/context/scratch plus all input/out/work spans are charged and
 * disjoint before callback. Reader failure leaves output unchanged. No allocator.
 * Runtime shared-cache selection, SERVERONLY association and actor state false.
 */
CohStatus coh_origins_read(CohBytes,uint64_t,const uint8_t expected_sha256[32],
 const CohCostumeImportDigest*,CohOriginDictionary*,CohOriginWorkspace*,size_t budget,size_t retained);
/* Source reverse-array lookup for ASCII names, preserving last duplicate winner.
 * Non-ASCII query/key refuses rather than guessing the original CRT locale.
 * Caller retains the immutable admitted owner for the returned row index. */
CohStatus coh_origins_find(const CohOriginDictionary*,CohBytes name,uint32_t*index);
#ifdef __cplusplus
}
#endif
#endif
