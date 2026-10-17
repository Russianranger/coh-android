#ifndef COH_RUNTIME_GRAPH_H
#define COH_RUNTIME_GRAPH_H
#include "runtime_snapshot.h"
typedef struct CohRuntimeGraph CohRuntimeGraph;
typedef struct {
    uint32_t generation,catalog_generation;
    CohRuntimeSnapshotPins pins;
} CohRuntimeGraphBinding;
typedef struct {
    uint32_t file,slot,external,in_use,reachable,child_first,child_count;
    uint32_t source_model_present,empty_owned_future;
    const char *name;CohBytes wire;size_t wire_bits;unsigned aligned;
} CohRuntimeGraphNode;
typedef struct {uint32_t target;CohSgMatrix matrix;} CohRuntimeGraphChild;
typedef struct {uint32_t active,node;CohSgMatrix matrix;} CohRuntimeGraphRoot;
typedef struct {
    CohRuntimeSnapshotReport source;
    uint32_t generation,catalog_generation,asset_generation,nodes,edges;
    size_t owned_bytes,prior_owned_bytes,prior_input_bytes,aggregate_peak_bytes;
} CohRuntimeGraphReport;
/* Immutable COMPACT SOURCE GRAPH, never a world/resource/actor permit. Exact
 * existing snapshot audit admission is required before any pointer escapes.
 * Original saved slots, external pre_alloc owners, root slots, edge order and
 * matrices are retained. An empty_owned_future is an observed active external
 * object with no model/children; its identity remains in the graph and is never
 * fabricated into a saved slot or resource. Other future records remain explicit
 * external nodes. Neither kind is an admitted render resource.
 *
 * Inputs stay independently authenticated, immutable and caller-pinned through
 * retirement. This module borrows them; it never copies/releases their storage.
 * Source/run digests are required trusted provenance labels, not evidence that
 * a live GROUPS transaction was received. Source-only graph publication cannot
 * set world authority. Run off-thread, serialize publication and retire only
 * after all borrowers finish. Binding/candidate/report/budget/input spans must
 * be disjoint; *candidate must be NULL. Failure leaves outputs unchanged.
 *
 * Exact next graph generation is required. Catalog/asset generations cannot
 * regress; a retained catalog generation preserves catalog/source/run/snapshot
 * identity. Old+new input allocations are charged even if spans alias. Include
 * owner indexes, allocation slack, digest scratch, asset resources and all other
 * retained data in budget.retained_bytes (without the input bytes already added
 * here). 32MiB owned and 96MiB aggregate payload limits remain in force; these
 * are named reservation bounds, not allocator overhead or whole-process RSS. */
CohStatus coh_runtime_graph_build(const CohRuntimeGraph *,CohBytes catalog,CohBytes snapshot,
    const CohRuntimeGraphBinding *,const CohRuntimeSnapshotBudget *,const CohCancel *,
    CohRuntimeGraph **candidate,CohRuntimeGraphReport *);
CohStatus coh_runtime_graph_publish(CohRuntimeGraph **current,CohRuntimeGraph **candidate,
    CohRuntimeGraph **retired);
void coh_runtime_graph_free(CohRuntimeGraph *);
CohStatus coh_runtime_graph_report(const CohRuntimeGraph *,CohRuntimeGraphReport *);
CohStatus coh_runtime_graph_node(const CohRuntimeGraph *,uint32_t,CohRuntimeGraphNode *);
CohStatus coh_runtime_graph_child(const CohRuntimeGraph *,uint32_t,CohRuntimeGraphChild *);
CohStatus coh_runtime_graph_root(const CohRuntimeGraph *,uint32_t,CohRuntimeGraphRoot *);
CohStatus coh_runtime_graph_slot(const CohRuntimeGraph *,uint32_t file,uint32_t slot,uint32_t *);
/* Exact canonical names only; no newly introduced aliases/case folding. */
CohStatus coh_runtime_graph_name(const CohRuntimeGraph *,const char *,uint32_t *);
typedef struct {uint32_t parent,edge,queue;} CohRuntimeGraphWitnessWork;
typedef struct {
    uint32_t root_slot,length;
    uint32_t nodes[COH_SG_DEPTH_MAX+1u],edges[COH_SG_DEPTH_MAX];
} CohRuntimeGraphWitness;
/* Deterministic shortest source path, using root slot and child order. Edges
 * are global graph edge indexes; compose the selected root and edge matrices
 * in source order. This is topology evidence, never a draw/resource permit.
 * Supply at least report.nodes workspace rows, disjoint from graph/inputs/out;
 * charge their bytes as retained memory alongside the graph. No allocation.
 * Work is mutable scratch; out remains unchanged on failure/cancellation. */
CohStatus coh_runtime_graph_witness(const CohRuntimeGraph *,uint32_t node,
    CohRuntimeGraphWitnessWork *,size_t rows,const CohCancel *,CohRuntimeGraphWitness *);
#endif
