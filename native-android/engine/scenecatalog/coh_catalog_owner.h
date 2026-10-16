#ifndef COH_CATALOG_OWNER_H
#define COH_CATALOG_OWNER_H
#include "coh_scenecatalog.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Preparation-side immutable ownership. This is not an authority certificate. */
typedef struct CohCatalogOwner CohCatalogOwner;
typedef struct {
    uint32_t owner_generation, catalog_generation, asset_generation, map_generation;
    uint8_t catalog_sha256[32], source_sha256[32], inventory_sha256[32], map_sha256[32];
} CohCatalogBinding;
/* A detached capture may set map_generation=0 and map_sha256 all zero. It can
 * be owned/indexed but compare_groups refuses until a later owner binds both.
 * source_sha256 identifies independently checked source-provenance evidence;
 * inventory_sha256 identifies the exact source asset inventory. */
/* Caller supplies an independently qualified SHA256 provider. It must hash the
 * supplied owned bytes, not return the expected pin or trust caller metadata.
 * Provider/context must not mutate or retain the borrowed span. No default or
 * success-only provider is supplied. Pins/provenance trust is external. */
typedef CohStatus (*CohCatalogSha256Fn)(void *,CohBytes,uint8_t output[32]);
typedef struct { void *context; CohCatalogSha256Fn sha256; } CohCatalogDigest;
typedef struct {
    size_t owned_limit, working_limit, aggregate_limit, retained_bytes;
} CohCatalogOwnerBudget;
typedef struct {
    CohStatus status;
    CohCatalogWalkReport walk;
    size_t owned_bytes, index_bytes, input_bytes, previous_bytes, retained_bytes;
    size_t peak_aggregate_bytes;
} CohCatalogOwnerReport;
typedef struct {
    uint32_t file, slot, allocated, in_use, child_count;
    size_t record_offset, wire_offset, wire_bytes;
    char name[COH_REP_NAME_MAX];
} CohCatalogRecordIdentity;
/* out must be NULL on entry. old is unchanged and never retained implicitly.
 * Next owner generation is exactly old+1 (or 1). Asset/map/catalog generations
 * cannot regress; the digest associated with an unchanged generation cannot
 * change. Changing source requires a new catalog generation.
 * Input+old owner are automatically charged, even if input aliases old bytes.
 * retained_bytes adds every other live owner/graph/asset/callback workspace.
 * Provider call stack/scratch is caller charged in retained_bytes. The native
 * walk charges its existing 64KiB stack reserve. Limits cover named payload,
 * not allocator metadata, RSS, server, graphics or driver memory.
 * Caller serializes preparation, retain/release and accesses. These counters
 * are not atomic. Pointer/control/input storage must be disjoint and input
 * stable during the copy. On any error out and old are unchanged. */
CohStatus coh_catalog_owner_create(const CohCatalogOwner *old,CohBytes,
    const CohCatalogBinding *,const CohCatalogOwnerBudget *,const CohCatalogDigest *,
    CohCatalogOwner **out,CohCatalogOwnerReport *);
CohStatus coh_catalog_owner_retain(CohCatalogOwner *);
void coh_catalog_owner_release(CohCatalogOwner *);
/* Borrowed immutable span/file name remain valid until the last release.
 * A compact graph retaining offsets MUST retain the owner for its lifetime.
 * No mutable pointer or decoded-record pointer escapes this API. */
CohStatus coh_catalog_owner_bytes(const CohCatalogOwner *,CohBytes *);
CohStatus coh_catalog_owner_binding(const CohCatalogOwner *,CohCatalogBinding *);
size_t coh_catalog_owner_owned_bytes(const CohCatalogOwner *);
CohStatus coh_catalog_owner_file(const CohCatalogOwner *,uint32_t file,CohCatalogFileView *);
/* O(1) original file/slot indexing; bounded prefix decode, no allocations.
 * Holes and allocated tombstones stay distinct. Output changes only on success. */
CohStatus coh_catalog_owner_record(const CohCatalogOwner *,uint32_t file,uint32_t slot,
    CohCatalogRecordIdentity *);
enum {
    COH_CATALOG_MISMATCH_BINDING=1u, COH_CATALOG_MISMATCH_NEW_WORLD=2u,
    COH_CATALOG_MISMATCH_FILES=4u, COH_CATALOG_MISMATCH_DEFS_CRC=8u,
    COH_CATALOG_MISMATCH_REFS_CRC=16u, COH_CATALOG_MISMATCH_ROOTS=32u
};
typedef struct {
    CohStatus status;uint32_t mismatches;
    CohGroupsInspection groups;CohGroupsFailure failure;
} CohCatalogGroupsMatch;
/* Read-only complete original GROUPS structural inspection plus numeric footer
 * compatibility. Binding must equal the owner, and reader begins immediately
 * after normalized GROUPS command. Reader is never advanced. A successful
 * comparison establishes neither same-session/source provenance nor resolved
 * graph, recomputed root CRC, assets, actor, READY/ACK or render authority.
 * Runtime generation/source receipts, file name/checksum parity, exact root
 * identities/transforms and complete graph validation remain owner duties. */
CohStatus coh_catalog_owner_compare_groups(const CohCatalogOwner *,const CohCatalogBinding *,
    const CohRepReader *,CohCatalogGroupsMatch *);
#ifdef __cplusplus
}
#endif
#endif
