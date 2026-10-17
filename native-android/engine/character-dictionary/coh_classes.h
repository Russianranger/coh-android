#ifndef COH_CLASSES_H
#define COH_CLASSES_H
#include "coh_origins.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_CLASS_MAX 64u
#define COH_CLASS_FIELDS 39u
#define COH_CLASS_TEXTS_MAX 8192u
#define COH_CLASS_TEXT_BYTES_MAX 131072u
#define COH_CLASS_TABLES_MAX 4096u
#define COH_CLASS_INPUT_MAX (8u*1024u*1024u)
#define COH_CLASS_RAM_MAX (8u*1024u*1024u)
#define COH_CLASS_STACK_RESERVE 16384u
typedef struct{uint32_t begin,end;}CohClassSpan;
typedef struct{uint32_t owner,table,row,field,element,offset,size;}CohClassText;
typedef struct{CohClassSpan record,fields[COH_CLASS_FIELDS];uint32_t name_text;}CohClassEntry;
typedef struct{CohClassSpan record;uint32_t owner,row,name_text;}CohClassModTable;
typedef struct{
 CohBytes input;uint64_t input_lease;uint8_t input_sha256[32];
 uint32_t header_crc,count,text_count,text_bytes,modtable_count,dependency_count;
 uint64_t scalar_words,array_words;
 uint8_t raw_schema_validated,source_crc_verified,runtime_generation,actor_authority;
 CohClassEntry entries[COH_CLASS_MAX];CohClassText texts[COH_CLASS_TEXTS_MAX];
 CohClassModTable modtables[COH_CLASS_TABLES_MAX];char text[COH_CLASS_TEXT_BYTES_MAX];
}CohClassDictionary;
typedef struct{CohClassDictionary candidate;}CohClassWorkspace;
/* Complete pinned original binary schema, including all nested attribute/table
 * scalar arrays and final pointer payloads. Copies strings and preserves ordered
 * source field/record spans; raw scalar arrays stay in immutable leased input.
 * All spans/digest scratch/retained charges precede callbacks. No allocations;
 * transactional output. Local bounds refuse, never skip a required field.
 * Expected SHA verifies exact historical bytes; observed header CRC is NOT an
 * original ParseTableCRC recomputation. g_pParsePowerDefines stash construction,
 * original repack/finalize/cache/SERVERONLY/current generation remain gates.
 * Caller retains immutable input under lease for every dictionary/span use.
 * No authoritative class/character/actor/application ACK admission.
 */
CohStatus coh_classes_read(CohBytes,uint64_t,const uint8_t expected_sha256[32],
 const CohCostumeImportDigest*,CohClassDictionary*,CohClassWorkspace*,size_t,size_t);
CohStatus coh_classes_find(const CohClassDictionary*,CohBytes,uint32_t*);
#ifdef __cplusplus
}
#endif
#endif
