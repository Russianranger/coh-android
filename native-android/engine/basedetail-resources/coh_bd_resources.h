#ifndef COH_BD_RESOURCES_H
#define COH_BD_RESOURCES_H
#include "../costume-import/coh_costume_import.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_BD_RESOURCE_ROWS_MAX 4096u
#define COH_BD_RESOURCE_TEXT_MAX 524288u
#define COH_BD_RESOURCE_INPUT_MAX 524288u
#define COH_BD_RESOURCE_WORK_MAX 8388608u
#define COH_BD_RESOURCE_RAM_MAX 16777216u
#define COH_BD_RESOURCE_STACK_RESERVE 16384u
/* Source order, not renderer slots. Literal "dim" remains a sentinel string. */
typedef enum { COH_BD_GROUP, COH_BD_UNPOWERED, COH_BD_DESTROYED,
 COH_BD_MOUNT, COH_BD_UNPOWERED_MOUNT, COH_BD_BASE_EDIT, COH_BD_GROUP_COUNT } CohBdGroupKind;
typedef struct { uint32_t offset,size; } CohBdResourceText;
typedef struct {
 CohBdResourceText name,groups[COH_BD_GROUP_COUNT];
 int32_t surface; uint32_t mounted,animated;
} CohBdResourceRow;
typedef struct {
 uint8_t sha256[32]; uint64_t provenance;
 uint32_t schema_crc,dependencies,count,text_bytes,complete,runtime_generation,actor_authority;
 CohBdResourceRow rows[COH_BD_RESOURCE_ROWS_MAX];
 char text[COH_BD_RESOURCE_TEXT_MAX];
} CohBdResources;
typedef struct { CohBdResources candidate; } CohBdResourcesWorkspace;
typedef struct { uint8_t expected_sha256[32]; uint64_t provenance; } CohBdResourcePins;
typedef struct { CohCancel cancel; size_t context_bytes,scratch_reserve; } CohBdResourceControl;
/* Complete Details Parse6 cache grammar and copied six geometry-group fields.
 * Preserves persisted resource strings and surface exactly: a successful source
 * BIN load bypasses text-only DetailDictPreprocess. No suffix generation,
 * leading-* stripping, surface inference or gameplay finalizer runs here.
 * Source U8 mounted/animated fields truncate serialized words before copying.
 * Empty indirect strings are absent. Nonempty ASCII definition keys <128 and
 * resource names <1024 are admitted. Other persisted fields are fully validated
 * as opaque grammar, not evaluated. No geometry resolution, current cache
 * family, actor or world authority follows.
 * Expected digest/provenance must be independently admitted by the caller.
 * All spans, configurations, callback contexts, output and workspace are valid,
 * immutable/pairwise disjoint through the call. Callbacks may mutate only their
 * declared contexts and digest output; no reentry/concurrency. Budget charges
 * all supplied spans, callback scratch/stack, 16KiB native stack and retained
 * old owners BEFORE callbacks. No allocation. Failure preserves output; scratch
 * may be partial. Digest errors outside the CohStatus domain become COH_INVALID.
 * Success copies every dependency, allowing inputs/providers to
 * retire. Immutable output must outlive getters. Policy budget is not RSS fit.
 */
CohStatus coh_bd_resources_read(CohBytes,const CohBdResourcePins*,
 const CohCostumeImportDigest*,const CohBdResourceControl*,CohBdResources*,
 CohBdResourcesWorkspace*,size_t budget,size_t retained);
/* Row ordinal is original Details order. No inventory ID or name hash implied.
 * Empty returns NOT_FOUND with output unchanged. All successful bytes borrow the
 * immutable owner. "dim" is preserved, not passed to a geometry loader here. */
CohStatus coh_bd_resources_group(const CohBdResources*,uint32_t row,
 CohBdGroupKind,CohBytes*);
#ifdef __cplusplus
}
#endif
#endif
