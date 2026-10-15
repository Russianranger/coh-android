#ifndef COH_ASSET_LOADER_H
#define COH_ASSET_LOADER_H
#include "../coh_contracts.h"
#include "../../include/coh_native_core.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_ASSET_PATH_MAX 1024u
/* All calls are single-owner-thread. Sources remain immutable and alive until
 * destroy. read_at must return exactly count bytes or an error; it never owns dst. */
typedef CohStatus (*CohAssetReadAt)(void *,uint64_t offset,void *dst,size_t count);
typedef struct { CohAssetReadAt read_at; void *context; uint64_t size; uint32_t generation; } CohAssetSource;
typedef struct CohAssetLoader CohAssetLoader;
typedef struct CohAssetBlob CohAssetBlob;
typedef struct {
    size_t total_bytes,cache_bytes,max_asset_bytes,max_stored_bytes;
    uint32_t entries,sources,cache_entries;
} CohAssetLimits;
typedef struct {
    size_t allocated_bytes,peak_allocated_bytes,resident_bytes,peak_resident_bytes;
    uint32_t indexed_entries,mounted_sources,resident_entries,pinned_blobs;
    uint64_t cache_hits,cache_misses,evictions,reads,read_bytes,rejections;
} CohAssetStats;
typedef struct {
    CohAssetId id; uint64_t offset; uint32_t decoded_bytes,stored_bytes,timestamp;
    uint8_t md5[16]; int compressed; /* recorded identity, not a verified digest */
} CohAssetInfo;
/* Limits include this module's heap and zlib allocations (allocator overhead and
 * caller buffers excluded). Output pointers are unchanged on failure. */
CohStatus coh_asset_create(const CohAssetLimits *,CohAssetLoader **);
/* Destroy refuses live acquired blobs with COH_STATE; successful destroy NULLs *p. */
CohStatus coh_asset_destroy(CohAssetLoader **p);
CohAssetStats coh_asset_stats(const CohAssetLoader *);
/* Transactional: malformed mount never publishes partial paths. PIGG v1/v2,
 * little-endian 16-byte archive/48-byte record (extended sizes admitted).
 * No HOGG. Latest mount wins unqualified generation=0 lookups. */
CohStatus coh_asset_mount_pigg(CohAssetLoader *,CohAssetSource,CohCancel);
/* Loose/extracted pack entry. Separate immutable source per file, no implicit OS
 * traversal. Path must be virtual relative; no '.', '..', colon, or empty path. */
CohStatus coh_asset_mount_file(CohAssetLoader *,const char *path,CohAssetSource);
CohStatus coh_asset_lookup(CohAssetLoader *,CohAssetId,CohAssetInfo *);
/* Acquire pins resident bytes until release. Eviction only touches unpinned LRU.
 * Generation=0 resolves latest mounted, otherwise exact generation. */
CohStatus coh_asset_acquire(CohAssetLoader *,CohAssetId,CohCancel,const CohAssetBlob **);
void coh_asset_release(CohAssetLoader *,const CohAssetBlob *);
CohBytes coh_asset_bytes(const CohAssetBlob *);
CohAssetId coh_asset_identity(const CohAssetBlob *);
void coh_asset_trim(CohAssetLoader *); /* evict every unpinned blob */
/* Bounded graph resolution: caller enumerates source-authentic dependency IDs,
 * e.g. GEO material names after table resolution. No recursive loading, hidden
 * aliases or guessed texture names. BFS visits each canonical identity once;
 * cycles terminate. visit_cap bounds both entries and enumeration per node.
 * Callback IDs are copied before the next callback. acquired blob is temporary.
 * Missing dependency fails precisely; no partial retained graph on return. */
typedef CohStatus (*CohAssetDependencies)(void *,CohAssetId,CohBytes,
                                         CohAssetId *out,size_t capacity,size_t *count);
CohStatus coh_asset_resolve(CohAssetLoader *,CohAssetId,CohAssetDependencies,void *,
                           uint32_t visit_cap,CohCancel,uint32_t *visited);
/* Typed borrowed adapters. Every output view remains valid while input is held.
 * Original .texture wrapper preserves name/flags/fade; DDS DXT1/3/5 goes through
 * qualified decoder. Raw DDS also accepted. TGA/other codecs are unsupported. */
typedef struct { CohBytes dds; const char *name; uint32_t flags,width,height;
                 float fade[2]; uint8_t alpha; } CohAssetTexture;
CohStatus coh_asset_texture(CohBytes,CohAssetTexture *);
CohStatus coh_asset_texture_rgba(const CohAssetTexture *,uint32_t mip,uint8_t *,size_t);
CohStatus coh_asset_animation(CohBytes,CohAnimHeader *);
/* Ogg/Vorbis identification view only. Actual decoding stays with existing
 * qualified off-thread decoder; this function does not decode or admit Opus. */
typedef struct { uint32_t sample_rate; uint8_t channels; CohBytes encoded; } CohAssetSound;
CohStatus coh_asset_sound(CohBytes,CohAssetSound *);
#ifdef __cplusplus
}
#endif
#endif
