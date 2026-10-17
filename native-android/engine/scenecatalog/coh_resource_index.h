#ifndef COH_RESOURCE_INDEX_H
#define COH_RESOURCE_INDEX_H
#include "../assets/coh_asset_geo.h"
#define COH_RESOURCE_ROWS_MAX 65536u
#define COH_RESOURCE_INPUT_MAX (32u*1024u*1024u)
#define COH_RESOURCE_RECORD_MAX (128u*1024u)
#define COH_RESOURCE_TEXTURES_MAX 256u
typedef struct CohResourceIndex CohResourceIndex;
typedef CohStatus (*CohResourceDigest)(void *,CohBytes,uint8_t[32]);
typedef struct {CohBytes record;uint8_t sha256[32];} CohResourceSource;
/* An independently admitted manifest maps the exact observed gld name to an
 * exact canonical loader ID. This explicit mapping is never inferred. */
typedef struct {const char *source_geo_name;CohAssetId id;uint8_t sha256[32];} CohResourceGeoPin;
typedef struct {
    uint32_t generation,asset_generation;
    uint8_t source_sha256[32],run_sha256[32],manifest_sha256[32];
} CohResourceBinding;
typedef struct {size_t owned_limit,aggregate_limit,retained_bytes,loader_reservation;} CohResourceBudget;
typedef struct {
    uint32_t owner_kind,file,slot,original_id,model_present,model_row,geo_disk_row,runtime_bucket_first,runtime_bucket_count,geo_version,zero_draw_model;
    const char *definition_name,*model_name,*geo_name,*trick_name,*trick_file,*library_name;
    uint32_t gld_loadstate,model_loadstate,model_flags,trick_present,trick_info_present;
    uint32_t trick_flags[2],info_model_flags,info_group_flags;
    float source_min[3],source_max[3],source_scale[3],source_radius,source_lod[6];
    uint32_t unresolved_client_semantics; /* always nonzero: no material/LOD permit */
    CohAssetGeoModel model;
} CohResourceView;
typedef struct {uint32_t rows,geos,lookup_work_units;size_t owned_bytes,aggregate_reserved_bytes;} CohResourceReport;
/* Bounded equivalents of original groupGetPublicName+groupNameIdx,
 * compareModelNamesAndLengths and trickFromObjectName's lookup key selection.
 * ASCII only, nonempty; outputs unchanged on refusal. Library key is lowercased
 * for original default case-insensitive stash. Model key keeps clone suffix. */
CohStatus coh_resource_library_key(const char *,char out[256]);
CohStatus coh_resource_model_key(const char *,char out[256]);
CohStatus coh_resource_trick_key(const char *,char out[256]);
/* Original geoSortModels rank, ignoring the first __suffix and comparing base
 * lengths case-insensitively. Selected equivalent keys are ambiguous and fail.
 * Names are borrowed for this call; no source/resource authority is conferred. */
CohStatus coh_resource_model_order(const char *query,const char *const *disk_names,
    uint32_t count,CohCancel,uint32_t *runtime_row,uint32_t *disk_row);
typedef struct {uint32_t first,count,disk_row;} CohResourceModelBucket;
/* Exact full-name uniqueness plus original sorted comparator bucket. Equal
 * base keys are allowed, but this never asserts their internal qsort order.
 * A captured runtime row is admissible only inside [first,first+count). */
CohStatus coh_resource_model_bucket(const char *query,const char *const *disk_names,
    uint32_t count,CohCancel,CohResourceModelBucket *);
/* Grammar-only borrowed observation. No digest/provenance or asset admission;
 * returned names borrow record bytes, model view remains zero. */
CohStatus coh_resource_source_view(CohBytes,uint32_t asset_generation,CohResourceView *);
/* Source-only immutable model/GEO index. Inputs are independently admitted
 * COHRES01 records and exact per-GEO pins, not proof by supplied hash label.
 * The source/run/manifest receipt chain must be admitted outside this parser.
 * Native code copies record bytes, verifies their hashes, retains exact loader
 * blobs and checks actual GEO model/material rows against observed Model owners.
 * No loader aliases or guessed path/extensions are introduced.
 * All source/pin input storage stays immutable during preparation.
 * Caller owns the loader thread; loader outlives index and all views. Its total
 * configured allocation limit MUST be <=loader_reservation (public API cannot
 * introspect limits). Reservation covers all old/new loader pins and scratch;
 * stats are checked before/after each acquire. Reserve other live work in
 * retained_bytes; input bytes, old index, candidate and workspaces are charged.
 * *out must be NULL; old and output unchanged on failure. Immutable byte views
 * remain valid until free. No cancellation/lookup/allocation on render thread.
 * NO materials, client tricks/LOD, assets draw-ready, actor or live authority. */
CohStatus coh_resource_index_build(const CohResourceIndex *old,CohAssetLoader *,
    const CohResourceSource *,size_t source_count,const CohResourceGeoPin *,size_t pin_count,
    const CohResourceBinding *,const CohResourceBudget *,CohResourceDigest,void *,CohCancel,
    CohResourceIndex **out,CohResourceReport *);
void coh_resource_index_free(CohResourceIndex *);
/* Copied immutable metadata and ordinal raw source observation. Raw bytes/names
 * borrow index lifetime; no pin callback, digest recomputation or admission. */
CohStatus coh_resource_index_metadata(const CohResourceIndex *,CohResourceBinding *,CohResourceReport *);
CohStatus coh_resource_index_record(const CohResourceIndex *,uint32_t ordinal,CohBytes *,CohResourceView *);
CohStatus coh_resource_index_view(const CohResourceIndex *,uint32_t owner_kind,
    uint32_t file,uint32_t slot,CohResourceView *);
CohStatus coh_resource_index_material(const CohResourceIndex *,uint32_t owner_kind,
    uint32_t file,uint32_t slot,uint32_t part,CohAssetGeoMaterial *);
/* Borrowed immutable decompressed original GEO header selected by this exact
 * owner, valid only until index retirement. No allocation or authority change;
 * output unchanged for absent/no-model owners. Output must be disjoint. */
CohStatus coh_resource_index_header(const CohResourceIndex *,uint32_t owner_kind,
    uint32_t file,uint32_t slot,CohBytes *);
#endif
