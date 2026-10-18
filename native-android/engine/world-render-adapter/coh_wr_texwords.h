#ifndef COH_WR_TEXWORDS_H
#define COH_WR_TEXWORDS_H
#include "coh_wr_tex_namespace.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct CohWrTexWords CohWrTexWords;
typedef struct {
 const char *locale;
 uint32_t region_eu,texword_edit,production_mode,verbose;
 /* This is a cold native dictionary operation, not a deferred runtime reload.
  * The source path which waits for compositors/uses a prior override refuses. */
 uint32_t allow_loading,pending_compositors,has_override;
} CohWrTexWordsConfig;
typedef struct {
 CohAssetId asset;uint8_t sha256[32];size_t bytes;
 CohWrTexWordsConfig config;
 CohWrTexNamespaceDigest digest;void *digest_context;
} CohWrTexWordsRequest;
typedef struct {
 size_t owned_limit,aggregate_limit,loader_reservation,external_bytes;
 uint32_t record_limit,node_limit;
} CohWrTexWordsLimits;
typedef struct {
 uint32_t source_generation,records,source_files,nested_structs,fields,keys;
 size_t owned_bytes,preparation_aggregate_reserved_bytes;
 uint8_t sha256[32];char locale[32],secondary_locale[32],search_path[80];
 uint32_t layout_composition_unqualified,current_generation_unqualified;
} CohWrTexWordsReport;
typedef struct {
 CohBytes source_name,serialized_record;
 uint32_t source_ordinal,source_generation;
} CohWrTexWordRecord;
enum {
 COH_WR_TEXWORD_CURRENT_LOCALE=1,COH_WR_TEXWORD_BASE_EXPLICIT=2,
 COH_WR_TEXWORD_BASE_WITHOUT_BASIC=3,COH_WR_TEXWORD_DEBUG_DUMMY=4
};
typedef struct {
 uint32_t matched,source_ordinal,route,namespace_queries,source_generation;
 uint32_t layout_composition_unqualified,current_generation_unqualified;
 char basic_query[128];
} CohWrTexWordSelection;
typedef struct {size_t aggregate_limit,external_bytes;} CohWrTexWordQueryLimits;

/* Complete Parse6/479da30a schema traversal, cold locale dictionary and original
 * TexWord lookup semantics only. Exact selected cache bytes/path/generation/hash
 * must come from the real loader/provider. The whole cache is copied; the input
 * loader/provider can actually retire after success. No TexWord layer fixups,
 * images/fonts/composition, Basic mutation, reload, material or current CLIENT
 * generation is admitted. Production+edit requires source files, so refuses.
 * Duplicate same-locale basenames refuse instead of depending on qsort ties.
 * UK secondary-locale priority is preserved independently of equal sort order.
 * Root names are canonical relative TEXTS/<locale>/<path>/<name>.texword ASCII paths
 * with forward slashes; other/mixed/absolute path spellings refuse. Layer
 * strings may be opaque nonzero bytes. Names must have a NUL within their stated
 * bound, or the complete bound must be readable for an unterminated refusal.
 * Nested strings are <12000 bytes (original tokenizer limit), without embedded
 * NUL; nonfinite floats refuse. Each nested record/array/string is traversed; unknown/trailing schema refuses.
 * No source row is silently dropped. Positive selections remain unrenderable.
 * All calls use one owner thread. Inputs and output spans are immutable/disjoint
 * for each call and outside opaque loader/provider/namespace private storage.
 * Callbacks must not mutate/destroy/reenter the borrowed loader/provider.
 * Loader configured total must be <=loader_reservation (peak alone is no proof).
 * Before callbacks, construction reserves the full owned_limit+loader allowance,
 * inputs, external peaks and fixed32KiB own control; every refusal releases its
 * real source pin and candidate allocation, preserving *out (initially NULL).
 * External provider/callback/libc/old resources/RSS remain caller obligations. */
CohStatus coh_wr_texwords_create(CohAssetLoader*,const CohWrTexWordsRequest*,const CohWrTexWordsLimits*,CohCancel,CohWrTexWords**);
CohStatus coh_wr_texwords_destroy(CohWrTexWords**);
CohStatus coh_wr_texwords_report(const CohWrTexWords*,CohWrTexWordsReport*);
CohStatus coh_wr_texwords_record(const CohWrTexWords*,uint32_t,CohWrTexWordRecord*);
/* Query search is original0/1. A supplied real still-live namespace is required
 * exactly for the no-explicit-locale #Base Basic-presence branch; no subset miss
 * or guessed white identity substitutes for it. This borrows no lifetime after
 * return. Copied ordinal requires this same still-live TexWord owner to resolve.
 * Safe stems are3..122 printable ASCII bytes, with no path, dot or !;
 * other unsafe/truncating original texFind domains refuse. Optional #suffix is
 * retained for original Base/explicit-locale branching, never a locale override.
 * external_bytes must cover this owner's owned bytes and the namespace's full
 * recorded reservation when used; adds inputs and16KiB query control. */
CohStatus coh_wr_texwords_find(const CohWrTexWords*,const CohWrTexNamespace*,const char*,int,const CohWrTexWordQueryLimits*,CohWrTexWordSelection*);
#ifdef __cplusplus
}
#endif
#endif
