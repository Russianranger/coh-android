#ifndef COH_WR_TEX_NAMESPACE_H
#define COH_WR_TEX_NAMESPACE_H
#include "../assets/coh_asset_loader.h"
#ifdef __cplusplus
extern "C" {
#endif

typedef struct CohWrTexNamespace CohWrTexNamespace;
typedef struct CohWrTexNamespaceBody CohWrTexNamespaceBody;
typedef CohStatus (*CohWrTexNamespaceDigest)(void *,CohBytes,uint8_t[32]);

/* A complete immutable directory snapshot supplied by its real provider, in
 * that provider's original enumeration order. Paths are relative to the data
 * root, ASCII, <=259 bytes. Empty directories must be explicit; a nonempty
 * directory may be implicit only if first-creation spelling/order is preserved
 * by its first descendant record. Directory bytes must be zero. File generation equals the root
 * generation. A list of selected texture headers is NOT a directory snapshot. */
typedef struct {
 const char *path;
 int32_t timestamp;
 uint32_t is_directory;
 CohAssetSource bytes;
} CohWrTexNamespaceFile;
typedef struct {
 const CohWrTexNamespaceFile *files;
 uint32_t count,generation;
 const char *root_path; /* actual data-root spelling, ASCII, <=1023 bytes */
} CohWrTexNamespaceRoot;

enum {
 COH_WR_TEX_NS_DEVELOPMENT=0,COH_WR_TEX_NS_DEVELOPMENT_DYNAMIC=1,
 COH_WR_TEX_NS_I_LIKE_PIGS=2,COH_WR_TEX_NS_PIGS_ONLY=3
};
typedef struct {
 /* Roots are in fileLoadDataDirs search-list order, highest priority first.
  * PIGGs are in the actual PigSet order, including patches. HOGG is refused. */
 const CohWrTexNamespaceRoot *roots;
 const CohAssetSource *piggs;
 uint32_t root_count,pigg_count,input_generation;
 uint32_t mode,quickload,development_data,disallow_overrides;
 uint32_t folder_exclusion; /* original ALL=0, EXCLUDE=1, ONLY=2 */
 const char *exclusion_folder; /* required only for non-ALL policy */
 const char *const *ignore_prefixes;
 uint32_t ignore_prefix_count;
 uint32_t lwc_active,lwc_last_completed_stage;
 /* NULL means an explicitly NEW, empty native Basic table. For a later LWC
  * scan use the actual predecessor produced by this module. All old roots and
  * PIGGs must remain byte-immutable and present in exactly the same prefix. */
 const CohWrTexNamespace *predecessor;
 CohWrTexNamespaceDigest digest;
 void *digest_context;
 /* One real provider lease is acquired before any source read and retired only
  * after loader destruction. It covers every source read_at/digest context and
  * their immutable bytes. These callbacks are not attestations of completeness.
  * The provider must actually enforce the snapshot and generation contract.
  * Failed hold acquires NO lease; successful hold is balanced by one drop. */
 CohStatus (*provider_hold)(void *);
 void (*provider_drop)(void *);
 void *provider_context;
} CohWrTexNamespaceRequest;
typedef struct {
 size_t owned_limit,aggregate_limit,external_bytes;
 CohAssetLimits loader;
 uint32_t record_limit,node_limit,basic_limit,body_lease_limit;
} CohWrTexNamespaceLimits;
typedef struct {
 uint32_t roots,piggs,source_records,tree_nodes,basic_rows,first_keys;
 uint32_t duplicates_retained,lwc_skipped,ignored,source_input_generation;
 size_t owned_bytes,peak_owned_bytes,aggregate_reserved_bytes;
 /* This owner closes declared immutable provider selection only. These remain
  * false: original deployment/current CLIENT table, defaults, TexOpt/Basic
  * reset, composite/permutation/material, GPU, Surface and world authority. */
 uint32_t unresolved_client_semantics;
} CohWrTexNamespaceReport;
typedef struct {
 CohAssetId asset;
 uint8_t sha256[32];
 uint32_t row,first_owner_row;
 int32_t virtual_location,timestamp,file_index;
 const char *original_name,*directory,*basic_key;
 CohBytes cached_mips;
 uint32_t width,height,cached_flags,initial_basic_flags,file_offset,file_bytes;
 float cached_fade[2];
 uint8_t cached_alpha;
} CohWrTexNamespaceBasic;

/* All calls use one owner thread. No OS scanning, implicit source search,
 * watcher update or namespace claim is hidden behind the callbacks. The native
 * caller must construct the actual complete root/PigSet snapshot; normalized
 * historical inventories cannot establish that. Filesystem-only/absolute-path
 * legacy scans and live changes are deliberately unsupported, not approximated.
 * Only nonnegative signed32 source timestamps, canonical relative paths and
 * original PIGG name_id==internal ordinal are admitted. Header dimensions and
 * declared payload sizes must fit positive/nonnegative signed32, fade must be
 * finite, and the original JPEG consistency assertion must hold. Other native
 * safety refusals abort the whole build rather than publishing a partial table.
 * Metadata getter views live until destroy. Acquired body byte views live only
 * until that lease is released. Each acquire transfers one lease; borrowed
 * aliases of its opaque handle all become invalid after the sole release.
 * Bodies are actual existing-loader pins; destroy refuses any live body lease.
 * *out must be NULL. Refusals preserve
 * outputs, release all partial pins/heap/provider leases, and preserve the
 * predecessor. NUL-terminated input paths/prefixes must have the documented
 * bound readable even when unterminated. Source callbacks and caller inputs are
 * immutable during build; output spans must also be outside opaque provider
 * storage. Reentry from any external callback refuses with COH_STATE for the
 * observing owner, including the predecessor while a successor is built.
 * external_bytes includes all provider/callback/old-owner runtime peaks and
 * must cover the known predecessor owned bytes plus its FULL configured loader
 * reservation before any callback or source read; this minimum is enforced.
 * A fixed64KiB module preparation/control reserve plus the FULL configured
 * loader reservation and input spans are charged before source reads. No RSS,
 * allocator overhead, libc stack or global-budget proof is implied. */
CohStatus coh_wr_tex_namespace_build(const CohWrTexNamespaceRequest*,const CohWrTexNamespaceLimits*,CohCancel,CohWrTexNamespace**);
CohStatus coh_wr_tex_namespace_destroy(CohWrTexNamespace**);
CohStatus coh_wr_tex_namespace_report(const CohWrTexNamespace*,CohWrTexNamespaceReport*);
CohStatus coh_wr_tex_namespace_basic(const CohWrTexNamespace*,uint32_t,CohWrTexNamespaceBasic*);
/* Exact Basic key lookup: first retained basename owner, never composite lookup
 * and never texFixName on a caller request. Missing means absent only from this
 * declared source owner, not from an original/current Game CLIENT table. */
CohStatus coh_wr_tex_namespace_find(const CohWrTexNamespace*,const char*,CohWrTexNamespaceBasic*);
CohStatus coh_wr_tex_namespace_acquire(CohWrTexNamespace*,uint32_t,CohCancel,const CohWrTexNamespaceBody**);
CohStatus coh_wr_tex_namespace_body(const CohWrTexNamespaceBody*,CohBytes*);
CohStatus coh_wr_tex_namespace_release(CohWrTexNamespace*,const CohWrTexNamespaceBody**);
#ifdef __cplusplus
}
#endif
#endif
