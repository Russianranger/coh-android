#ifndef COH_SCENEGRAPH_H
#define COH_SCENEGRAPH_H
#include "../replication/coh_groups.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Explicit admission budgets, not original engine maxima. */
#define COH_SG_DEFS_MAX 4096u
#define COH_SG_ROOTS_MAX 4096u
#define COH_SG_CHILDREN_MAX 16384u
#define COH_SG_DEPTH_MAX 128u
#define COH_SG_MEMORY_MAX (32u*1024u*1024u)
typedef float CohSgMatrix[4][3]; /* Original engine column basis, position [3]. */
typedef struct { char name[COH_REP_NAME_MAX]; CohSgMatrix matrix; uint32_t resolved; } CohSgChild;
typedef struct { char original[COH_REP_NAME_MAX], replacement[COH_REP_NAME_MAX]; uint32_t composite; } CohSgSwap;
typedef struct {
    uint32_t file, id, in_use, mod_time;
    char name[COH_REP_NAME_MAX], geometry[COH_REP_NAME_MAX], textures[2][COH_REP_NAME_MAX];
    CohSgChild *children; uint32_t child_count;
    CohSgSwap *swaps; uint32_t swap_count;
    /* Owned exact definition body (including optional render/property metadata).
     * No interpretation/completeness claim for downstream renderer semantics. */
    uint8_t *wire; size_t wire_bytes, wire_bits; unsigned wire_start_bit, aligned;
} CohSgDefinition;
typedef struct { char name[COH_REP_NAME_MAX]; uint32_t bounds_checksum, loaded; } CohSgFile;
typedef struct { uint32_t id, active, resolved; char name[COH_REP_NAME_MAX]; CohSgMatrix matrix; } CohSgRoot;
typedef struct {
    uint32_t generation, asset_generation, file_count, definition_count, root_count;
    uint32_t definitions_crc, references_crc, active_roots;
    size_t owned_bytes;
    CohSgFile *files; CohSgDefinition *definitions; CohSgRoot *roots;
    /* This is a resolved topology snapshot, NOT a live world/render permit. */
} CohSceneGraph;
typedef struct {
    const char *name; uint32_t bounds_checksum, asset_generation;
    const CohSgDefinition *definitions; uint32_t definition_count;
} CohSgImportedFile;
/* Importer returns borrowed immutable original-file catalog for the synchronous
 * call. It must contain ALL original slots, including saved wire omissions and
 * allocated tombstones, and match checksum/generation. No filesystem I/O here.
 * Null original slots are absent entries. Graph deep-copies consumed data. */
typedef CohStatus (*CohSgImportFn)(void *, const char *, uint32_t, uint32_t, CohSgImportedFile *);
typedef enum { COH_SG_GEOMETRY=1, COH_SG_TEXTURE=2, COH_SG_COMPOSITE_TEXTURE=3 } CohSgAssetKind;
typedef CohStatus (*CohSgAssetFn)(void *, CohSgAssetKind, const char *, uint32_t);
typedef struct { void *context; CohSgImportFn file; CohSgAssetFn asset; uint32_t generation; } CohSgImports;
typedef enum { COH_SG_INSPECT=1, COH_SG_IMPORT=2, COH_SG_DECODE=3, COH_SG_RESOLVE=4, COH_SG_CHECKSUM=5 } CohSgStage;
typedef struct { CohSgStage stage; CohStatus status; size_t bit; uint32_t file, definition, reference; } CohSgFailure;
/* Start immediately after GROUPS command. Pure synchronous preparation: call
 * off rendering thread. On any failure reader and *published remain unchanged.
 * On success atomically swap owned candidate and free previous snapshot. Caller
 * serializes access (not thread-safe publication). Generation must advance by
 * exactly one; incremental asset generation must match previous snapshot.
 * Existing prefix/structural inspector runs first. All topology/name/checksum,
 * explicit geometry/texture identities, cycle/depth/count bounds must pass.
 * This function sends no packets and does not admit any authoritative actor. */
CohStatus coh_scenegraph_apply(CohSceneGraph **published, CohRepReader *, const CohSgImports *, uint32_t next_generation, CohSgFailure *);
void coh_scenegraph_free(CohSceneGraph *);
/* Decode one original sendDef record, INCLUDING its id+1 prefix, without
 * publishing a graph or checking assets. This is the catalog adapter boundary.
 * Reader/output/owned_bytes are unchanged on failure. Output must not own prior
 * allocations; dispose it after use. available_bytes bounds all allocations
 * made for child/swap arrays and exact original metadata. */
CohStatus coh_scenegraph_definition_read(CohSgDefinition *, CohRepReader *,
    uint32_t file, size_t available_bytes, size_t *owned_bytes);
void coh_scenegraph_definition_dispose(CohSgDefinition *);
/* Pure original matrix composition; transactional on finite overflow. */
CohStatus coh_scenegraph_compose(const CohSgMatrix parent, const CohSgMatrix child, CohSgMatrix out);
#ifdef __cplusplus
}
#endif
#endif
