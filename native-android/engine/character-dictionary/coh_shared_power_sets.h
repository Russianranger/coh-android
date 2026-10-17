#ifndef COH_SHARED_POWER_SETS_H
#define COH_SHARED_POWER_SETS_H
#include "coh_power_ids.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_SHARED_SETS_MAX COH_CATEGORY_REFS_MAX
#define COH_SHARED_SETS_RAM_MAX (8u*1024u*1024u)
#define COH_SHARED_SETS_STACK_RESERVE 16384u
#define COH_SHARED_SETS_WORK_MAX (64u*1024u*1024u)
typedef struct {
 const CohPowerIDs *ids;
 uint32_t count,appended_count,source_calls;
 uint8_t source_layout_projection,initial_from_empty,runtime_generation,actor_authority;
 uint32_t sets[COH_SHARED_SETS_MAX];
} CohSharedPowerSets;
typedef struct {CohSharedPowerSets candidate;} CohSharedPowerSetsWorkspace;
/* Original FindSharedPowersets walks finalized sorted categories/local set refs
 * and appends every Shared set, preserving repeated references. It does NOT
 * clear the global list. prior=NULL models one call on an initially empty
 * source fixture; this is not evidence that a running process has empty state.
 * A prior owner may append only using the SAME immutable ID/dictionary owner;
 * cross-dictionary retained source pointers require a different lifetime owner
 * and refuse here. Original U8 binary Shared conversion is preserved.
 *
 * IDs, join, all raw dictionaries, set input and provider/file leases must
 * outlive this layout and every later append. A prior layout may retire after
 * successful disjoint append: its sequence is copied, transitive leases remain
 * borrowed.
 *
 * All transitive input owners/set bytes/provider context/scratch and optional
 * prior/output/workspace/caller-retained/stack are disjoint and charged before
 * work under the literal8MiB cap. No allocation/callback, count guessed from
 * allocated rows, deduplication or current generation authority. Failure leaves
 * output unchanged. This source-only layout does not enable character wire
 * profile authority, semantic character creation, actor or any ACK.
 */
CohStatus coh_shared_power_sets_prepare(const CohPowerIDs*,const CohSharedPowerSets*,
 CohSharedPowerSets*,CohSharedPowerSetsWorkspace*,size_t,size_t);
#ifdef __cplusplus
}
#endif
#endif
