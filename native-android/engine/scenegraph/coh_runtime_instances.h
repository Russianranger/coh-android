#ifndef COH_RUNTIME_INSTANCES_H
#define COH_RUNTIME_INSTANCES_H
#include "coh_runtime_bounds.h"
#define COH_RUNTIME_INSTANCE_BATCH_MAX 1024u
#define COH_RUNTIME_INSTANCE_COUNT_MAX 16777216u
#define COH_RUNTIME_INSTANCE_WORK_MAX 67108864u
#define COH_RUNTIME_INSTANCE_STEP_MAX 65536u
typedef struct {
    uint32_t graph_generation,node,root_slot,depth,incoming_edge,model_present,external;
    uint64_t ordinal,parent_ordinal;
    CohSgMatrix world;
} CohRuntimeInstance;
typedef struct {
    uint32_t node,next_child,emitted,incoming_edge;
    uint64_t ordinal,parent_ordinal;
    CohSgMatrix world;
} CohRuntimeInstanceFrame;
typedef struct {uint64_t maximum_occurrences,maximum_work;} CohRuntimeInstancesConfig;
typedef struct {size_t aggregate_limit,retained_bytes;} CohRuntimeInstancesBudget;
typedef struct {
    CohRuntimeGraphBinding graph;
    uint64_t occurrences,model_occurrences,external_occurrences,work;
    uint32_t roots_started,maximum_depth,complete,batch_count,steps;
    size_t aggregate_reserved_bytes;
    uint32_t assets_admitted,world_authority;
} CohRuntimeInstancesReport;
/* API-owned state in caller storage: initialize only through begin and never
 * edit metadata or resume on another graph. A byte-for-byte continuation copy
 * under the SAME graph lease starts an independent walk; serialize each copy. Graph and its exact
 * source owners stay immutable and retained externally until the cursor and
 * all borrowers of its results retire. No implicit retain or allocation.
 * Frame stack is a PATH, never a global visited/deduplication set. */
typedef struct {
    const CohRuntimeGraph *graph;
    CohBytes catalog,snapshot;
    CohRuntimeGraphBinding binding;
    uint32_t nodes,root_slots;
    CohRuntimeInstancesConfig config;
    size_t aggregate_limit,base_reserved_bytes;
    uint32_t next_root,active_root,depth,initialized;
    CohRuntimeInstancesReport progress;
    CohRuntimeInstanceFrame frames[COH_SG_DEPTH_MAX+1u];
} CohRuntimeInstances;
/* Deterministic original root-slot / child-entry preorder, one record for EVERY
 * root-to-node occurrence, including shared DAG nodes, empty and no-model nodes.
 * Root world matrices are observed raw source roots; children compose parent
 * world * source child-local in original mulMat4Inline operation order.
 * Ordinals identify this walk only; parent_ordinal UINT64_MAX marks a root.
 * They are not entity IDs or world/session authority. No subtree pruning/LOD.
 *
 * Account all other owners/indexes/graphs/bounds/resources/allocator slack and
 * cancellation scratch in retained_bytes. Graph pool, borrowed catalog+snapshot,
 * cursor and 64 KiB stack reserve are added; next additionally charges the FULL
 * supplied batch capacity and report. Named aggregate <=96 MiB, not process RSS.
 * Controls/known inputs/output spans must be disjoint; opaque graph allocation
 * and cancellation context disjointness is a caller ownership precondition.
 * begin/next leave cursor and report unchanged on failure. Batch rows are
 * mutable scratch on ANY return: discard the entire attempted batch on error.
 * On OK only report.batch_count rows are valid immutable VALUE copies until
 * caller reuse. No pointer/name/geometry/CLIENT material or LOD is published.
 * Work/steps count main-loop state transitions, not CPU instructions. A child
 * transition performs at most 128 path-cycle comparisons (plus fixed metadata
 * lookups and fixed-size matrix arithmetic); the depth ceiling bounds this extra work.
 * Per-call steps yield with OK and committed progress, possibly zero rows.
 * Total work/occurrence/depth/finite-transform/cycle/cancel failure refuses the
 * attempted batch; previously successful batches remain historical values but
 * cannot be claimed complete. A complete walk may be polled again (empty OK).
 */
CohStatus coh_runtime_instances_begin(const CohRuntimeGraph *,const CohRuntimeInstancesConfig *,
    const CohRuntimeInstancesBudget *,CohRuntimeInstances *,CohRuntimeInstancesReport *);
CohStatus coh_runtime_instances_next(CohRuntimeInstances *,CohRuntimeInstance *,size_t capacity,
    uint32_t step_limit,CohCancel,CohRuntimeInstancesReport *);
typedef struct {CohRuntimeInstance instance;CohGroupBounds local_source_bounds;} CohRuntimeInstanceSelectionInput;
/* Prepare value-only visibility input from an UNMODIFIED successful batch and
 * completed bounds diagnostic of this exact graph. Caller retains the bounds
 * array/report (and charges them externally); no inferred/default bounds.
 * This is a local source box + composed matrix, not CLIENT effective bounds,
 * culling/LOD/material choice, geometry ownership, GPU or live-world permit.
 * Output unchanged on refusal; input/controls/output known spans disjoint. */
CohStatus coh_runtime_instance_selection_input(const CohRuntimeInstances *,const CohRuntimeInstance *,
    const CohRuntimeBoundsReport *,const CohRuntimeBoundsRow *,size_t rows,
    CohRuntimeInstanceSelectionInput *);
#endif
