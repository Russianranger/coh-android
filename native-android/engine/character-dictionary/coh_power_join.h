#ifndef COH_POWER_JOIN_H
#define COH_POWER_JOIN_H
#include "coh_power_categories.h"
#include "coh_power_sets.h"
#include "coh_power_stream.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_POWER_JOIN_REF_MAX 32768u
#define COH_POWER_JOIN_RAM_MAX (8u*1024u*1024u)
#define COH_POWER_JOIN_STACK_RESERVE 16384u
#define COH_POWER_JOIN_WORK_MAX (64u*1024u*1024u)
#define COH_POWER_JOIN_NONE UINT32_MAX
typedef struct {uint32_t first,count,parent_category;} CohPowerJoinSet;
typedef struct {uint32_t declared_power,resolved_power;} CohPowerJoinReference;
typedef struct {
 const CohPowerCategoryDictionary *categories;
 const CohPowerSetDictionary *sets;
 const CohPowerStreamDictionary *powers;
 uint32_t category_count,set_count,power_count,category_reference_count,power_reference_count;
 uint32_t reached_set_count,alternate_name_count;
 uint8_t complete_forward_join,parent_projection,runtime_generation,actor_authority;
 uint32_t category_sets[COH_CATEGORY_REFS_MAX];
 CohPowerJoinSet set_links[COH_POWER_SET_MAX];
 CohPowerJoinReference power_links[COH_POWER_JOIN_REF_MAX];
 uint32_t power_parent_sets[COH_POWER_STREAM_RECORD_MAX];
} CohPowerJoin;
typedef struct {CohPowerJoin candidate;} CohPowerJoinWorkspace;
/* Source SetForwardPointers order and exact (case-sensitive) alternate fullname
 * decision; references are never silently removed. Missing declared/alternate
 * identities refuse atomically. This does not synthesize DuplicateMissingPowers
 * clones. Raw allocated rows, including unreachable sets/powers, remain owned by
 * the input dictionaries. Reverse SetBackPointers set/power parent precedence is
 * projected; nested AttribModTemplate links/finalization are NOT executed.
 *
 * All three admitted immutable owners, sets input lease, and powers provider/file
 * lease must outlive this owner. Provider context/scratch are pre-reserved; no
 * allocation, no digest lifecycle calls, <=259-byte individual name reads.
 * Full spans/retained input/owner/context/scratch/stack charged before callbacks.
 * This standalone historical join does not establish current SERVERONLY/CLIENT
 * cache generation, semantic class/power state, actor authority or any ACK.
 */
CohStatus coh_power_join_prepare(const CohPowerCategoryDictionary*,
 const CohPowerSetDictionary*,const CohPowerStreamDictionary*,CohPowerJoin*,
 CohPowerJoinWorkspace*,size_t budget,size_t retained);
#ifdef __cplusplus
}
#endif
#endif
