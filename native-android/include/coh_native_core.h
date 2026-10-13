#ifndef COH_NATIVE_CORE_H
#define COH_NATIVE_CORE_H
#include <stdint.h>
#include <stddef.h>
typedef struct { uint32_t P[18], S[4][256]; } CohBlowfish;
/* All functions return0 on success. These modules are not wired into Game. */
int coh_bf_init(CohBlowfish *, const uint8_t *, size_t);
int coh_bf_crypt(CohBlowfish *, uint8_t *, size_t, int decrypt);
typedef struct { uint32_t header_bytes,bone_offset,bone_count,hierarchy_offset; float hip,length; } CohAnimHeader;
typedef struct {
    uint16_t rotation_keys,position_keys,rotation_frames,position_frames;
    uint8_t id,flags,rotation_stride,position_stride;
    const uint8_t *rotation,*position;
    size_t rotation_bytes,position_bytes;
} CohBoneView;
/* Views borrow caller-owned bytes; no disk pointer slot is interpreted as a native pointer. */
int coh_anim_header(const uint8_t *,size_t,CohAnimHeader *);
int coh_anim_bone(const uint8_t *,size_t,uint32_t,CohBoneView *);
typedef struct { uint32_t packed_bytes,unpacked_bytes,offset; } CohPack32;
typedef struct { const uint8_t *bytes; size_t stored_bytes,decoded_bytes; int compressed; } CohPackView;
int coh_pack_view(const uint8_t *record,size_t record_bytes,const uint8_t *payload,
                  size_t payload_bytes,size_t maximum_decoded_bytes,CohPackView *);
typedef struct {
    uint32_t version,record_bytes,texture_count,vertex_count,triangle_count,reflection_count;
    float radius;
    uint32_t bone_info_offset,texture_index_offset,name_offset,alternate_pivot_offset;
    uint32_t pack_count;
    CohPack32 packs[10];
    int16_t id;
} CohGeoModel;
/* v3-v8 decompressed model-record metadata only, not a complete .geo scene loader. */
int coh_geo_model(const uint8_t *,size_t,uint32_t version,CohGeoModel *);
typedef struct {
    uint32_t width,height,mip_count,format; /* format = 1/3/5 for DXT1/3/5 */
    const uint8_t *blocks;
    size_t block_bytes,rgba_bytes;
} CohDdsMip;
/* Legacy 2D DDS only. Validates the complete declared mip chain. Returns 2 for
 * unsupported formats, 1 for invalid input/capacity. Views borrow input bytes.
 * RGBA output must be disjoint from input. Output remains untouched on failure. */
int coh_dds_mip(const uint8_t *,size_t,uint32_t level,CohDdsMip *);
int coh_dds_rgba(const uint8_t *,size_t,uint32_t level,uint8_t *,size_t);
#endif
