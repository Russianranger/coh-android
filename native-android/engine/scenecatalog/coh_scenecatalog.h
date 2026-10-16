#ifndef COH_SCENECATALOG_H
#define COH_SCENECATALOG_H
#include "../scenegraph/coh_scenegraph.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_CATALOG_INPUT_MAX (32u*1024u*1024u)
#define COH_CATALOG_DEFS_MAX 65536u
#define COH_CATALOG_SLOTS_MAX 65536u
#define COH_CATALOG_CHILDREN_MAX 262144u
#define COH_CATALOG_MEMORY_MAX COH_SG_MEMORY_MAX
/* Counts are numeric source observations, never live-world readiness. */
typedef enum { COH_CATALOG_HEADER=1,COH_CATALOG_FILE=2,COH_CATALOG_RECORD=3,
    COH_CATALOG_DECODE=4,COH_CATALOG_CHECKSUM=5,COH_CATALOG_PUBLISH=6 } CohCatalogStage;
typedef struct {
    CohStatus status; CohCatalogStage stage; size_t offset;
    uint32_t file, slot, generation, files, slots, definitions, children;
    uint32_t source_defs_crc, source_refs_crc, source_active_roots;
    size_t input_bytes, wire_bytes, minimum_owned_bytes, owned_bytes;
    uint32_t exceeds_graph_definitions, exceeds_graph_children;
} CohCatalogReport;
typedef struct CohSceneCatalog CohSceneCatalog;
/* Allocation-free envelope/name-CRC/count preflight. It does not prove complete
 * record validity; load performs the bounded original-record decode. Failures
 * return numeric diagnostics. Source data/provenance must be independently
 * pinned by the caller before use; names CRC is not payload authentication. */
CohStatus coh_scenecatalog_preflight(CohBytes,uint32_t generation,CohCatalogReport *);
/* Whole-candidate transaction: prior catalog unchanged on ANY failure. Input is
 * borrowed during call; all imported definitions/metadata are owned on success.
 * Prior+candidate ownership is bounded by 64 MiB; each catalog by 32 MiB. */
CohStatus coh_scenecatalog_load(CohSceneCatalog **,CohBytes,uint32_t generation,CohCatalogReport *);
void coh_scenecatalog_free(CohSceneCatalog *);
CohStatus coh_scenecatalog_file(void *,const char *,uint32_t checksum,uint32_t generation,CohSgImportedFile *);
/* Initial complete GROUPS binding. Incremental updates require their own graph
 * CRC validation and may legitimately differ from the exported root snapshot. */
CohStatus coh_scenecatalog_match(const CohSceneCatalog *,const CohGroupsInspection *);
void coh_scenecatalog_report(const CohSceneCatalog *,CohCatalogReport *);
/* Stream validation/walk owns at most one decoded record. The 64 KiB reserve
 * includes stack descriptors and bounded preflight indexes; payload accounting
 * is not process RSS or allocator bookkeeping. Existing eager cap is unchanged. */
#define COH_CATALOG_WALK_STACK_RESERVE (64u*1024u)
typedef struct {
    size_t working_limit, aggregate_limit, retained_bytes;
} CohCatalogWalkBudget;
typedef struct {
    const char *name;
    uint32_t index, bounds_checksum, slots, records, generation;
} CohCatalogFileView;
typedef struct {
    CohBytes catalog;
    const CohCatalogFileView *file;
    uint32_t slot, allocated, aligned;
    size_t record_offset, wire_offset, wire_bytes, wire_bits;
    const CohSgDefinition *definition;
} CohCatalogSlotView;
typedef CohStatus (*CohCatalogFileFn)(void *,const CohCatalogFileView *);
typedef CohStatus (*CohCatalogSlotFn)(void *,const CohCatalogSlotView *);
typedef struct { void *context; CohCatalogFileFn file; CohCatalogSlotFn slot; } CohCatalogVisitor;
typedef struct {
    CohCatalogReport catalog;
    uint32_t files_visited, slots_visited, records_validated;
    size_t peak_record_owned_bytes, peak_working_bytes, peak_aggregate_bytes;
    /* Known peaks include successfully decoded records, even if their callback
     * fails. A failed decoder frees partial allocations without a byte receipt;
     * this flag marks that uncertainty and the admitted bounds remain valid. */
    uint32_t failed_record_peak_unknown;
    size_t working_upper_bound, aggregate_upper_bound;
} CohCatalogWalkReport;
/* Entire envelope/name-CRC/count preflight precedes callbacks. Every file is
 * visited, including empty files; every original slot is visited in order.
 * A hole has allocated=0, NULL definition and zero record/wire fields. An
 * allocated tombstone has allocated=1 and definition->in_use=0. Exact offsets
 * refer to the borrowed immutable input; record_offset includes the 16-byte
 * record header, wire_offset starts its original serialized sendDef record.
 * All views/decoded pointers expire on callback return. Callbacks must not
 * mutate input or views. Budget/visitor remain immutable for the call; report,
 * budget, visitor and caller control storage must be disjoint from input and
 * each other. Caller must stage changes and discard on ANY failure;
 * callbacks never grant publication/ACK authority. Returning non-OK cancels
 * with that status. NULL visitor performs complete record validation only.
 * Working input+reserve+one record <=32 MiB, aggregate adds caller's maximum
 * retained bytes and is bounded by COH_SG_TRANSACTION_MAX. Caller must account
 * for all external old/candidate state in retained_bytes, serialize access and
 * keep input immutable for the call (longer if it retains offset views).
 * SHA256/source generation authentication is external. Root transforms are
 * absent from COHCAT01 and must come from the corresponding original GROUPS. */
CohStatus coh_scenecatalog_walk(CohBytes,uint32_t generation,const CohCatalogWalkBudget *,
    const CohCatalogVisitor *,CohCatalogWalkReport *);
#ifdef __cplusplus
}
#endif
#endif
