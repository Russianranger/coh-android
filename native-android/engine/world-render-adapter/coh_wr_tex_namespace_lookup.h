#ifndef COH_WR_TEX_NAMESPACE_LOOKUP_H
#define COH_WR_TEX_NAMESPACE_LOOKUP_H
#include "coh_wr_tex_namespace.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {size_t aggregate_limit,external_bytes;uint32_t guarded_short_keys;} CohWrTexNamespaceLookupLimits;
enum {COH_WR_TEX_NS_LOOKUP_NULL=0,COH_WR_TEX_NS_LOOKUP_FOUND=1,COH_WR_TEX_NS_LOOKUP_ABSENT=2};
typedef struct {
 char key[128],asset_path[260];uint8_t sha256[32];
 uint32_t branch,format_flags,row,first_owner_row,source_input_generation,asset_generation;
 uint32_t guarded_short_keys,current_CLIENT_unqualified;
 size_t aggregate_reserved_bytes;
} CohWrTexNamespaceLookup;
/* Original BasicTexture texFind/texFixName over ONE real immutable namespace,
 * rather than the imported-header subset. One leading ! and positional,
 * case-sensitive source extension tests are preserved; no path/basename/PORTAL
 * rewrite or default fallback. ABSENT describes only this supplied snapshot.
 * The strict original unsafe bare4..7-byte domain refuses. guarded_short_keys=1
 * explicitly selects the separately qualified two-location texFixName repair.
 * NULL preserves the original no-lookup branch. Query needs a NUL within129
 * readable bytes, or all129 bytes must be readable for bounded refusal.
 * Copied result owns no pointers/leases. Its row may be resolved/acquired only
 * against this same still-live source; copied path/hash/generation cannot mint
 * another owner or admission. No effective alpha/TexBind/TexWord/material/GPU,
 * original current CLIENT, provider completeness or world authority is implied.
 * One source-owner thread; no callbacks/allocation/read_at/digest are executed.
 * Caller keeps query/source/provider immutable; output must be disjoint from
 * opaque source/provider storage. Public metadata/query/limits aliases refuse.
 * external_bytes covers the source's FULL recorded aggregate reservation plus
 * all other live owners/runtime peaks. Adds16KiB control and named inputs/output
 * before lookup. This reservation is policy, never RSS/global96MiB fit. Every
 * failure preserves output. Inputs/output must have their actual ABI alignment.
 */
CohStatus coh_wr_tex_namespace_lookup(const CohWrTexNamespace*,const char*,const CohWrTexNamespaceLookupLimits*,CohWrTexNamespaceLookup*);
#ifdef __cplusplus
}
#endif
#endif
