#ifndef COH_SOURCE_PLACEMENT_H
#define COH_SOURCE_PLACEMENT_H
#include "coh_source_sealed.h"
#include "../scenegraph/coh_runtime_candidates.h"
enum {COH_SOURCE_PLACEMENT_NO_MODEL=1,COH_SOURCE_PLACEMENT_NOT_PREPARED=2,
 COH_SOURCE_PLACEMENT_GEOMETRY=3};
typedef struct {size_t aggregate_limit,retained_bytes;} CohSourcePlacementBudget;
typedef struct {
 CohRuntimeCandidate candidate;CohSourceSealedEntry geometry;
 uint32_t result,sealed_slot,source_geometry_available,unresolved;
 size_t aggregate_reserved_bytes,preparation_reserve;
 uint32_t renderer_ready,client_materials_available,live_generation_admitted,world_authority;
} CohSourcePlacement;
/* Synchronous no-allocation join of an UNMODIFIED successful source-candidate
 * value and a bounded retained sealed SOURCE mesh subset. Requires identical
 * ACTUAL join/catalog/snapshot/graph owners; equal hashes/generations alone do
 * not match. Input candidate must retain its original pager/context/graph
 * contract. Finite source world matrices remain walk-local historical values,
 * not live poses. Missing prepared geometry and no-model objects are explicit
 * OK diagnostics, never dropped or fabricated. Only SOURCE_BODY may be cleared.
 *
 * Sealed/context/graph and any open pager/walker/batches remain externally live
 * and immutable. Output pointer spans borrow sealed lifetime, not output's.
 * Charges exact sealed + source + context owners (common actual join tree once),
 * inputs/output, 16 KiB native call reserve, ALL other retained owners via budget
 * under unchanged 96 MiB cap. No parent ticket is accepted or issued. Add live
 * loader/provider reservations, walkers/pagers/batches/bounds, old outputs, other
 * candidates, allocator slack, callback/runtime/GPU bytes in retained_bytes.
 * Controls/source/private opaque allocations must be caller-disjoint; known
 * source, sealed and context controls are guarded. Output unchanged on refusal.
 * No callbacks, allocation, retention, I/O, material binding or publication.
 */
CohStatus coh_source_placement_prepare(const CohSourceSealed *,const CohRuntimeCandidates *,
 const CohRuntimeCandidate *,const CohSourcePlacementBudget *,CohSourcePlacement *);
#endif
