#ifndef COH_RUNTIME_CANDIDATES_H
#define COH_RUNTIME_CANDIDATES_H
#include "coh_runtime_instances.h"
#include "../scenecatalog/coh_resource_join.h"
typedef struct CohRuntimeCandidates CohRuntimeCandidates;
typedef struct {size_t owned_limit,aggregate_limit,retained_bytes;} CohRuntimeCandidateBudget;
enum {
 COH_CANDIDATE_CLIENT_CACHE=1u<<0,COH_CANDIDATE_CLIENT_TRICKS=1u<<1,
 COH_CANDIDATE_PARENT_DRAW=1u<<2,COH_CANDIDATE_CAMERA=1u<<3,
 COH_CANDIDATE_SHADOW_FOG_PORTALS=1u<<4,COH_CANDIDATE_DYNAMIC=1u<<5,
 COH_CANDIDATE_CLIENT_LOD=1u<<6,COH_CANDIDATE_CLIENT_MATERIALS=1u<<7,
 COH_CANDIDATE_LIVE_GENERATION=1u<<8,COH_CANDIDATE_SOURCE_BODY=1u<<9,
 COH_CANDIDATE_SOURCE_BOUNDS=1u<<10
};
#define COH_CANDIDATE_CLIENT_UNKNOWN_MASK 511u
typedef struct {
 CohRuntimeInstance instance;uint32_t source_ordinal,source_model_present;
 uint8_t source_record_sha256[32];
 uint32_t bounds_result,has_source_bounds,unresolved;
 CohGroupBounds local_source_bounds; /* Meaningful ONLY when has_source_bounds. */
} CohRuntimeCandidate;
typedef struct {
 uint32_t nodes,source_rows,graph_generation,catalog_generation;
 size_t owned_bytes,dependency_bytes,aggregate_reserved_bytes;
 uint32_t assets_admitted,visibility_admitted,world_authority;
} CohRuntimeCandidateOwnerReport;
/* Immutable preparation-side source routing. Retains the actual join, which
 * retains catalog/snapshot/resource storage. Graph remains BORROWED: caller
 * must keep it live and immutable until this context AND all pagers retire.
 * Actual graph pointer, borrowed source spans and copied owner bindings must
 * agree. A bounded inverse map is built; ordinal is NEVER assumed to be node.
 * Source raw records (including observed SERVER trick/hide/unknown flags) stay
 * intact in the retained join and may be queried below. They are never treated
 * as complete CLIENT flags. No asset loads, path guesses or GPU ownership.
 *
 * Owned cap <=32 MiB, named aggregate <=96 MiB. Unique join/catalog/snapshot/graph
 * payloads, new context/map and 64 KiB stack reserve are added automatically.
 * retained_bytes charges every other owner, allocation slack and cancellation
 * scratch. Controls/known source spans disjoint; opaque allocations/context
 * also caller-disjoint. *outNULL; failure leaves out/report unchanged. */
CohStatus coh_runtime_candidates_create(const CohRuntimeGraph *,CohResourceJoin *,
 const CohRuntimeCandidateBudget *,CohCancel,CohRuntimeCandidates **out,CohRuntimeCandidateOwnerReport *);
CohStatus coh_runtime_candidates_retain(CohRuntimeCandidates *);
void coh_runtime_candidates_free(CohRuntimeCandidates *);
CohStatus coh_runtime_candidates_report(const CohRuntimeCandidates *,CohRuntimeCandidateOwnerReport *);
/* Borrowed immutable exact source bytes through last context/pager release.
 * Source metadata only; no file-body/material/LOD/live-generation admission.
 * Query outputs must be disjoint from controls/private/source allocations. */
CohStatus coh_runtime_candidates_node(const CohRuntimeCandidates *,uint32_t node,uint32_t *ordinal);
CohStatus coh_runtime_candidates_source(const CohRuntimeCandidates *,uint32_t ordinal,CohResourceSource *);
typedef struct {
 uint32_t processed,total,emitted,model_candidates,no_model_candidates;
 uint32_t with_source_bounds,without_source_bounds,complete,steps;
 size_t aggregate_reserved_bytes;
 uint32_t visibility_rejected,assets_admitted,visibility_admitted,world_authority;
} CohRuntimeCandidatePageReport;
/* Zero-initialize; API-owned, not copyable. begin retains context, close releases
 * it exactly once. Batch and optional bounds ARRAY remain immutable and borrowed
 * until close; the bounds REPORT is consumed synchronously by begin. A walker
 * may continue only with a DIFFERENT batch allocation while this one is open.
 * The batch must be an unmodified complete latest successful walker batch under
 * this exact graph lease. Optional bounds are an unmodified successful source
 * diagnostic of this graph; blocked/missing rows remain explicit candidates.
 */
typedef struct {
 CohRuntimeCandidates *owner;const CohRuntimeInstance *batch;
 const CohRuntimeBoundsRow *bounds;size_t bounds_rows;
 uint32_t active,count,offset;size_t base_reserved_bytes,aggregate_limit;
 CohRuntimeCandidatePageReport progress;
} CohRuntimeCandidatePager;
/* All input/output controls known disjoint. Input batch and optional bounds
 * capacity, pager/report and 64 KiB stack reserve are added to actual retained
 * context dependencies. Other state (including walker cursor) belongs in caller
 * retained_bytes; it MUST NOT double-count these added owners/inputs.
 * owned_limit applies only to create; begin/next perform no allocation.
 * Failure leaves pager/report unchanged and retains nothing.
 */
CohStatus coh_runtime_candidates_begin(CohRuntimeCandidates *,const CohRuntimeInstances *,
 const CohRuntimeInstance *,size_t count,const CohRuntimeBoundsReport *,
 const CohRuntimeBoundsRow *,size_t bounds_rows,const CohRuntimeCandidateBudget *,
 CohCancel,CohRuntimeCandidatePager *,CohRuntimeCandidatePageReport *);
/* One output for EVERY input occurrence, including no-model/future/effect cases.
 * Neither source bounds nor observed hide/trick flags permit dropping anything.
 * All CLIENT/body/material/live gaps stay explicit. max capacity<=1024; bounded
 * step limit counts rows. No subtree pruning, camera filtering, path sorting,
 * deduplication or loading. Cursor/report commit only on OK; output is scratch
 * on error (discard attempted batch). Valid rows are immutable VALUE copies
 * until caller reuse. report.emitted is this call's count; processed is cumulative.
 * Output capacity/report bytes additionally charged. No callbacks except cancel.
 */
CohStatus coh_runtime_candidates_next(CohRuntimeCandidatePager *,CohRuntimeCandidate *,
 size_t capacity,uint32_t step_limit,CohCancel,CohRuntimeCandidatePageReport *);
void coh_runtime_candidates_close(CohRuntimeCandidatePager *);
#endif
