#ifndef COH_CLIENT_DISTANCE_H
#define COH_CLIENT_DISTANCE_H
#include "../coh_contracts.h"
typedef struct {
 float view_mid[3],parent_node_mid[3];
 float client_vis_dist_scaled_cache,client_vis_def_radius_cache,game_lod_scale;
 uint32_t lod_fadenode,client_flags_cache;
} CohClientDistanceInput;
typedef struct {
 float squared_distance,source_return;
 uint32_t used_parent_mid,exception_flags,far_rejected,source_return_nonzero;
} CohClientDistanceProjection;
/* PURE original CLIENT closeEnough projection only. Inputs must already be the
 * complete actual CLIENT view-space mid, inherited parent draw state, flags and
 * makeAGroupEnt caches. SERVER bounds/lod6 do not supply these prerequisites.
 * Original far-test exceptions and zero-distance return are preserved exactly.
 * Finite USED inputs/results required; no sign clamp or generic distance rule.
 * Inputs/output disjoint; transactional on refusal; allocation-free.
 * No frustum/shadow/fog/portal/dynamic/near-LOD/material/live-generation or
 * draw visibility decision is established. Do NOT use this projection alone
 * to discard a candidate. Compile normal finite semantics / FP contraction off.
 */
CohStatus coh_client_distance_project(const CohClientDistanceInput *,CohClientDistanceProjection *);
#endif
