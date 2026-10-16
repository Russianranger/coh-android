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
#ifdef __cplusplus
}
#endif
#endif
