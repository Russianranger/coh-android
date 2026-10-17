#ifndef COH_RUNTIME_GRAPH_OWNER_H
#define COH_RUNTIME_GRAPH_OWNER_H
#include "runtime_graph.h"
#include "../scenecatalog/coh_catalog_snapshot.h"
typedef struct CohRuntimeGraphOwner CohRuntimeGraphOwner;
typedef struct {size_t owned_limit,aggregate_limit,retained_bytes;} CohRuntimeGraphOwnerBudget;
typedef struct {
 uint32_t generation,nodes,edges;
 size_t owner_bytes,graph_bytes,dependencies_bytes,aggregate_reserved_bytes;
} CohRuntimeGraphOwnerReport;
/* Serialized immutable ownership, not source/session/render authority. Actual
 * catalog and snapshot owners are retained until AFTER the owned graph retires.
 * Bindings derive from those owners; digest must hash actual bytes. old remains
 * caller-held throughout preparation; no historical owner chain is retained.
 * owned_limit covers this object+graph, <=32MiB; aggregate<=96MiB includes old
 * and new complete source owners even when aliased, nested192KiB core scratch
 * and64KiB local scratch. Caller charges digest stack/allocator overhead and all
 * other live dependencies in retained_bytes. Controls/outputs/source spans must
 * be disjoint, immutable, not inside opaque graph/catalog/snapshot allocations.
 * External opaque allocation non-overlap is a caller prerequisite. On failure
 * old, *out and report are unchanged. *out must initially be NULL. */
CohStatus coh_runtime_graph_owner_create(const CohRuntimeGraphOwner *old,
 CohCatalogOwner *,CohCatalogSnapshot *,uint32_t generation,
 const CohRuntimeGraphOwnerBudget *,const CohCatalogDigest *,const CohCancel *,
 CohRuntimeGraphOwner **out,CohRuntimeGraphOwnerReport *);
CohStatus coh_runtime_graph_owner_retain(CohRuntimeGraphOwner *);
void coh_runtime_graph_owner_release(CohRuntimeGraphOwner *);
/* Borrowed views remain valid through last owner release. No graph ownership
 * transfer; callers must not free the borrowed graph. Outputs disjoint. */
CohStatus coh_runtime_graph_owner_view(const CohRuntimeGraphOwner *,
 const CohRuntimeGraph **,CohCatalogOwner **,CohCatalogSnapshot **,
 CohRuntimeGraphOwnerReport *);
#endif
