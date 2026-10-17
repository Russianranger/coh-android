#ifndef COH_WR_LOD_CACHE_H
#define COH_WR_LOD_CACHE_H
#include "coh_wr_texopt.h"
typedef struct CohWrLodCache CohWrLodCache;
typedef struct CohWrLodDictionary CohWrLodDictionary;
typedef struct {size_t owned_limit,aggregate_limit,loader_reservation,external_bytes;} CohWrLodCacheLimits;
typedef struct {uint32_t historical_input_generation,rows,children,source_files,force_automatic;size_t owned_bytes,loader_reservation,aggregate_reserved_bytes;uint8_t cache_sha256[32];} CohWrLodCacheReport;
typedef struct {CohBytes model_name,source_file;uint32_t ordinal,force_automatic,child_count,historical_input_generation;} CohWrLodCacheRow;
typedef struct {float max_error,lod_near,lod_nearfade,lod_far,lod_farfade;uint32_t flags;CohBytes model_name;} CohWrLodCacheChild;
/* Exact historical lods.bin admission, not an active CLIENT LOD dictionary.
 * Complete original persisted schema/order; bounded rows/children, no eager
 * runtime EArray/string graph. Loader outlives owner/views. Configure total
 * loader limit<=loader_reservation; whole reservation+owned bytes+16KiB prep
 * plus external old/provider/runtime peaks charged BEFORE acquisition. */
CohStatus coh_wr_lod_cache_open(CohAssetLoader*,CohAssetId,CohWrTexOptDigest,void*,const CohWrLodCacheLimits*,CohCancel,CohWrLodCache**);
/* Every CohBytes view is borrowed, not NUL-terminated, and needs its owner. */
void coh_wr_lod_cache_release(CohWrLodCache**);
CohStatus coh_wr_lod_cache_report(const CohWrLodCache*,CohWrLodCacheReport*);
CohStatus coh_wr_lod_cache_row(const CohWrLodCache*,uint32_t,CohWrLodCacheRow*);
CohStatus coh_wr_lod_cache_child(const CohWrLodCache*,uint32_t,uint32_t,CohWrLodCacheChild*);
/* Supplied ORIGINAL writable-path resolution boundary. No guessed data root or
 * filesystem probing. Input source name and output are NUL-terminated ASCII;
 * callback must write an actual immutable source-qualified original path or
 * refuse. Qualification uses explicit path observers, never actual-path proof.
 * Callback/storage/runtime peaks belong in caller external reservation. */
typedef CohStatus(*CohWrLodWritablePath)(void*,const char*,char out[260]);
typedef struct {size_t owned_limit,aggregate_limit,external_bytes;} CohWrLodDictionaryLimits;
typedef struct {CohWrLodCacheReport source;uint32_t rows,unique_keys,duplicate_keys;size_t owned_bytes,aggregate_reserved_bytes;} CohWrLodDictionaryReport;
typedef struct {CohBytes writable_path,normalized_model_name;uint32_t ordinal,table_owner_ordinal,force_automatic,child_count;} CohWrLodDictionaryRow;
enum {COH_WR_LOD_DICTIONARY_ABSENT=0,COH_WR_LOD_DICTIONARY_RETURN_EXISTING=1,COH_WR_LOD_DICTIONARY_CONSTRUCT_FORCE_AUTO=2};
typedef struct {uint32_t branch,ordinal,unresolved_client_semantics;} CohWrLodDictionaryLookup;
/* Atomic initial postprocess SOURCE index. On success only, consumes *source;
 * all raw bytes/children remain owned through it. Exact original first duplicate
 * wins, first __ suffix truncation and case-insensitive key semantics. Original
 * MAX_PATH registration truncation is outside this bounded domain: refuses a
 * combined key>=260 rather than indexing a truncated key. Geometry filename
 * resolution/modelname_specified, runtime reload/removed flags, CLIENT generation
 * and actual allocator/stash ABI remain unresolved. This is not live admission.
 * external includes source owned bytes+WHOLE loader reservation+16KiB source
 * controls and other old/provider/callback/runtime peaks. Adds32KiB own reserve.
 * No source/output changes on any refusal; all outputs must be disjoint. */
CohStatus coh_wr_lod_dictionary_stage(CohWrLodCache**,CohWrLodWritablePath,void*,const CohWrLodDictionaryLimits*,CohCancel,CohWrLodDictionary**);
void coh_wr_lod_dictionary_release(CohWrLodDictionary**);
CohStatus coh_wr_lod_dictionary_report(const CohWrLodDictionary*,CohWrLodDictionaryReport*);
CohStatus coh_wr_lod_dictionary_row(const CohWrLodDictionary*,uint32_t,CohWrLodDictionaryRow*);
CohStatus coh_wr_lod_dictionary_child(const CohWrLodDictionary*,uint32_t,uint32_t,CohWrLodCacheChild*);
/* Source getLODFileName path projection (no fileLocateWrite/path authority).
 * Original first case-insensitive /data/ and first .geo rules retained. */
CohStatus coh_wr_lod_source_filename(const char*,char out[260]);
/* Original initial-cache early-return precedence from lodinfoFromObjectName.
 * Resolves getLODFileName(geo) through the supplied actual path boundary, appends
 * whole model name, truncates at first __, then looks up initial dictionary.
 * Existing parsed rows return before automatic construction; force_auto with
 * no children continues construction. No runtime removed/reload state is guessed.
 * Read-only; no dictionary insertion, material/mesh/LOD selection or world permit.
 * Both queries and callback results must stay immutable through the call. */
CohStatus coh_wr_lod_dictionary_lookup(const CohWrLodDictionary*,const char*geo,const char*model,CohWrLodWritablePath,void*,CohWrLodDictionaryLookup*);
#endif
