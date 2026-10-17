#ifndef COH_PUBLIC_BOUNDS_H
#define COH_PUBLIC_BOUNDS_H
#include "../scenecatalog/coh_catalog_owner.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_PUBLIC_BOUNDS_INPUT_MAX (32u*1024u*1024u)
#define COH_PUBLIC_BOUNDS_STACK_RESERVE (64u*1024u)
typedef struct CohPublicBounds CohPublicBounds;
typedef struct {
 uint32_t generation;CohCatalogBinding catalog;
 uint8_t raw_sha256[32],run_sha256[32];
} CohPublicBoundsBinding;
typedef struct {size_t owned_limit,aggregate_limit,retained_bytes;} CohPublicBoundsBudget;
typedef struct {
 uint32_t files,slots,public_rows,raw_prefix_bytes;
 size_t owned_bytes,aggregate_reserved_bytes;
 uint32_t original_win32_layout_verified,source_generation_admitted,cache_equivalence_verified,world_authority;
} CohPublicBoundsReport;
typedef struct {
 uint32_t file,slot,allocated,in_use,is_public;const char*name;CohBytes raw;
} CohPublicBoundsRow;
/* Immutable source-only input owner, not an original ABI/cache capability.
 * Retains the ACTUAL CatalogOwner and copies SHA-verified COHRBW01 bytes.
 * Full file/slot order, names/activity/public decisions, original file checksum
 * tokens and exact embedded48B catalog header must match that retained owner.
 * Raw60B prefixes are opaque: preserve all padding/NaNs, never infer layout.
 * Matching hashes/labels alone do NOT authenticate source/runtime/cache state.
 * Caller independently qualifies actual source ABI+run capture chain. Every
 * authority/ABI/cache flag remains0, even after token-byte comparison below.
 * old unchanged; generation exactlyold+1 or1; out initiallyNULL. Named aggregate
 * charges input+new+old owner+catalog (old catalog too if different)+64KiB stack.
 * retained_bytes includes digest stack/context, all other live payload/providers
 * and allocator slack where required by caller; not RSS/driver/process proof.
 * Serial preparation/refcounts, immutable inputs, disjoint known spans; opaque
 * old/catalog/digest/context allocations also disjoint by caller contract.
 * On ANY error output pointer/report/old unchanged; partial allocations freed.
 */
CohStatus coh_public_bounds_create(const CohPublicBounds*old,CohCatalogOwner*,CohBytes,
 const CohPublicBoundsBinding*,const CohPublicBoundsBudget*,const CohCatalogDigest*,
 CohPublicBounds**out,CohPublicBoundsReport*);
CohStatus coh_public_bounds_retain(CohPublicBounds*);
void coh_public_bounds_release(CohPublicBounds*);
CohStatus coh_public_bounds_binding(const CohPublicBounds*,CohPublicBoundsBinding*);
CohStatus coh_public_bounds_report(const CohPublicBounds*,CohPublicBoundsReport*);
/* Borrowed name/raw span valid through last release; no mutable source escapes. */
CohStatus coh_public_bounds_row(const CohPublicBounds*,uint32_t file,uint32_t slot,CohPublicBoundsRow*);
/* Pure current-byte token equality, NOT cache-computation generation evidence.
 * File0 refuses as original writer skips it. Mismatch preserves out; observed
 * zero tokens are NOT normalized/replaced. Caller still needs original cache
 * computation/source-state association before any cache-equivalence claim. */
typedef struct {uint32_t checksum,public_rows;size_t bytes_hashed;} CohPublicBoundsToken;
CohStatus coh_public_bounds_compare_token(const CohPublicBounds*,uint32_t file,CohPublicBoundsToken*);
#ifdef __cplusplus
}
#endif
#endif
