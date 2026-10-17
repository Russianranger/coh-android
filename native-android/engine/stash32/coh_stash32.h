#ifndef COH_STASH32_H
#define COH_STASH32_H
#include "../coh_contracts.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_STASH32_SLOT_MAX 65536u
#define COH_STASH32_KEY_MAX 4096u
#define COH_STASH32_BUDGET_MAX (1024u*1024u)
#define COH_STASH32_STACK_RESERVE 16384u
#define COH_STASH32_DEFAULT_SEED 0xfacefaceu
/* Source Win32 ub4 is unsigned long32. Native LP64 unsigned long MUST NOT be
 * substituted. Byte-safe little-endian loads preserve x86 source behavior.
 * Default source string hash ORs0x20 into EVERY byte, including punctuation;
 * this is not Unicode or generic case folding. Hashing is not string equality. */
CohStatus coh_stash32_string_hash(CohBytes,uint32_t seed,uint32_t *out);
uint32_t coh_stash32_int_hash(uint32_t key,uint32_t seed);
typedef struct{
 uint32_t initial_slots,max_size,valid_count,resize_count,duplicate_count,zero_count;
 uint32_t slots[COH_STASH32_SLOT_MAX];
 uint32_t source_hash_bits,source_prefix_only,complete_global_dictionary,actor_authority;
} CohStash32IntSnapshot;
typedef struct{uint32_t slots[2][COH_STASH32_SLOT_MAX];} CohStash32IntWorkspace;
/* Source addPaletteToTables-style NO-DELETE integer insertion sequence, including
 * zero skip, duplicate refusal,75% resize and ascending old-slot reinsertion.
 * Caller supplies original key ORDER; this API cannot establish its origin or
 * completeness. This is an immutable caller-owned diagnostic prefix snapshot,
 * never a complete costume palette/world/actor dictionary admission.
 * All complete input/workspace/output spans disjoint; no allocation. Named
 * budget<=1MiB charges full fixed capacities, caller retained and16KiB stack.
 * Workspace may change on refusal; out commits only after the entire sequence.
 * Initial size must be an admitted power of two8..65536; source constructor
 * capacity rounding is the caller's separately qualified responsibility.
 */
CohStatus coh_stash32_int_prefix(const uint32_t *keys,size_t count,uint32_t initial_slots,
 CohStash32IntWorkspace *,CohStash32IntSnapshot *,size_t budget,size_t retained);
#ifdef __cplusplus
}
#endif
#endif
