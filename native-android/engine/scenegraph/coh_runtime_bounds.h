#ifndef COH_RUNTIME_BOUNDS_H
#define COH_RUNTIME_BOUNDS_H
#include "runtime_graph.h"
#include "coh_group_bounds.h"
typedef enum {COH_RB_UNVISITED=0,COH_RB_COMPUTED=1,COH_RB_FUTURE_BOUNDS_MISSING=2,
    COH_RB_DEFINITION_MISSING=3,COH_RB_CHILD_BLOCKED=4,COH_RB_CAPTURED_FUTURE=5} CohRuntimeBoundsResult;
typedef struct {CohGroupBounds bounds;uint32_t color,result;} CohRuntimeBoundsRow;
typedef struct {uint32_t node,next;} CohRuntimeBoundsFrame;
/* Provider supplies ONLY independently qualified immediate definition/model
 * inputs. child pointers/count and cancellation are overwritten by
 * the adapter; a nonzero pre_alloc refuses. Return NOT_FOUND/UNSUPPORTED to record missing input. No asset
 * callbacks or I/O are performed by the adapter itself. Callback reservations
 * (including streamed file/header owners) MUST fit budget.retained_bytes. */
typedef CohStatus (*CohRuntimeBoundsDefinition)(void *,uint32_t,
    const CohRuntimeGraphNode *,CohGroupBoundsInput *);
typedef struct {size_t aggregate_limit,retained_bytes;} CohRuntimeBoundsBudget;
typedef struct {
    CohRuntimeGraphBinding graph;
    uint32_t visited,computed,captured_future,future_missing,definition_missing,child_blocked;
    uint32_t active_roots,computed_roots,blocked_roots,maximum_first_visit_depth;
    size_t workspace_bytes,aggregate_reserved_bytes;
    uint32_t assets_admitted,world_authority; /* always zero */
} CohRuntimeBoundsReport;
/* Root-reachable source-only numerical diagnostic, not world publication.
 * Caller retains immutable graph and its actual source owners. Workspaces are
 * mutable scratch and may change on ANY return; only inspect results after OK.
 * Row capacity >=graph.nodes; child capacity >=largest reachable child count;
 * frame capacity >=COH_SG_DEPTH_MAX+1. Supplied capacities are fully charged.
 * Known workspace/control/report and exposed source spans are pairwise
 * checked before writes. Opaque graph allocations and callback contexts must
 * also be disjoint by caller ownership precondition; their extents cannot be
 * inferred here. Callback may not mutate any input/control/workspace or graph. No allocations. Deterministic root/edge-order DFS processes shared
 * nodes once, refuses cycles/depth overflow, and never visits disconnected
 * components. Future pre_alloc bounds are copied only from exact captured live values,
 * never inferred from empty geometry. Missing observed bounds conservatively
 * block every ancestor (even volume parents). Missing
 * provider input records a blocker, not dummy geometry. Report unchanged on
 * error/cancel/limit. OK may contain blockers and never grants authority. */
CohStatus coh_runtime_bounds_diagnose(const CohRuntimeGraph *,
    CohRuntimeBoundsDefinition,void *,const CohRuntimeBoundsBudget *,CohCancel,
    CohRuntimeBoundsRow *,size_t,CohGroupBoundsChild *,size_t,
    CohRuntimeBoundsFrame *,size_t,CohRuntimeBoundsReport *);
#endif
