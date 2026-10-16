#ifndef COH_RUNTIME_SNAPSHOT_H
#define COH_RUNTIME_SNAPSHOT_H
#include "coh_scenegraph.h"
#define COH_RUNTIME_SNAPSHOT_INPUT_MAX (16u*1024u*1024u)
#define COH_RUNTIME_SNAPSHOT_EXTERNAL_MAX 64u
#define COH_RUNTIME_SNAPSHOT_STACK_RESERVE (128u*1024u)
typedef CohStatus (*CohRuntimeDigestFn)(void *,CohBytes,uint8_t[32]);
typedef struct {
    uint32_t asset_generation;
    uint8_t catalog_sha256[32],snapshot_sha256[32],source_sha256[32],run_sha256[32];
    CohRuntimeDigestFn digest;void *context;
} CohRuntimeSnapshotPins;
typedef struct {size_t aggregate_limit,retained_bytes;} CohRuntimeSnapshotBudget;
typedef struct {
    char name[COH_REP_NAME_MAX],library_path[COH_REP_NAME_MAX];
    uint32_t original_id,referenced,reachable,model_present,bounds_lookup_found;
} CohRuntimeExternalDiagnostic;
typedef struct {
    uint32_t files,slots,definitions,children,root_slots,active_roots,external_count;
    uint32_t source_defs_crc,source_refs_crc,definitions_crc_verified,references_crc_verified;
    uint32_t reachable_definitions,reachable_external,reachable_edges,maximum_depth;
    uint32_t root_matrices_verified,complete_source_name_closure;
    uint32_t graph_published,assets_admitted,groups_received,actor_admitted,world_authority;
    size_t catalog_bytes,snapshot_bytes,owned_bytes,peak_record_bytes,stack_reserve;
    size_t retained_bytes,aggregate_peak_bytes;
    CohRuntimeExternalDiagnostic external[COH_RUNTIME_SNAPSHOT_EXTERNAL_MAX];
} CohRuntimeSnapshotReport;
/* NONSHIPPING, synchronous source-snapshot diagnostic. No graph, object view,
 * resource pin, ACK or publication interface exists. Both input allocations
 * remain immutable and caller-owned throughout. Independently trusted pins
 * bind exact copied/exported bytes; source/run pins are required provenance
 * labels, not cryptographic evidence established by this parser. The digest
 * callback must compute SHA256; all its scratch and caller retained allocations
 * must be charged in retained_bytes. Output and controls must be disjoint.
 * Every failure leaves output unchanged. Successful future records are actual
 * separately observed source pre_alloc ownership, NEVER ordinary saved slots
 * or renderable substitutes. Only root-reachable topology is cycle/depth
 * checked. Catalog and snapshot from the same owner-thread boundary are an
 * external admission prerequisite. This does not receive or authenticate a
 * GROUPS transaction, character, asset generation or live world. */
CohStatus coh_runtime_snapshot_audit(CohBytes catalog,CohBytes snapshot,
    const CohRuntimeSnapshotPins *,const CohRuntimeSnapshotBudget *,
    const CohCancel *,CohRuntimeSnapshotReport *);
#endif
