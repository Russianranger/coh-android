#ifndef COH_COSTUME_IMPORT_H
#define COH_COSTUME_IMPORT_H
#include "../entities/coh_costume.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_COSTUME_IMPORT_INPUT_MAX (4u*1024u*1024u)
#define COH_COSTUME_IMPORT_BUDGET_MAX (8u*1024u*1024u)
#define COH_COSTUME_IMPORT_STACK_RESERVE 16384u
/* Source-builder/schema ID generated from source-pins.json. Not an asset ID. */
extern const uint8_t coh_costume_import_source_id[32];
typedef struct {
 uint32_t generation,body_parts,body_types;
 uint8_t payload_sha256[32],source_sha256[32],inventory_sha256[32],profile_sha256[32],run_sha256[32];
} CohCostumeImportPins;
typedef CohStatus (*CohCostumeImportDigestFn)(void *,CohBytes,uint8_t [32]);
typedef struct {
 CohCostumeImportDigestFn sha256;void *context;size_t context_bytes,scratch_reserve;
} CohCostumeImportDigest;
typedef struct {
 uint32_t generation,body_parts,body_types,slots[3],present[3];
 size_t input_bytes,temporary_bytes,dictionary_bytes,charged_peak_bytes;
 uint8_t payload_sha256[32],source_sha256[32],inventory_sha256[32],profile_sha256[32],run_sha256[32];
 /* Syntax/integrity import only: neither capture origin nor actor is certified. */
 uint32_t capture_origin_verified,actor_authority;
} CohCostumeImportReceipt;
/* Host/off-thread import. Input/pins/provider/context/output/receipt are pairwise
 * disjoint, unchanged through call, and live through digest + loader copying.
 * *out must be NULL. Output and receipt commit together only after full import.
 * Caller independently verifies expected pins against authentic capture receipts;
 * digest callback computes SHA256 of the ENTIRE input, has no hidden retained
 * storage, and must reserve all its transient memory before invocation. Its
 * implementation/stack qualification remains external. Input and all named
 * spans, 4MiB maximum immutable loader allocation, temporary slot arrays, native
 * stack reserve and retained bytes are charged BEFORE any allocation/callback.
 * Result has no input/provider lifetime dependency; free via existing loader.
 * Local format COHCDI1 is an export contract, never an original network packet.
 */
CohStatus coh_costume_import(CohBytes,const CohCostumeImportPins *,
 const CohCostumeImportDigest *,CohEntCostumeDictionary **,CohCostumeImportReceipt *,
 size_t budget,size_t retained);
#ifdef __cplusplus
}
#endif
#endif
