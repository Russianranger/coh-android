#ifndef COH_MESH_H
#define COH_MESH_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define COH_MESH_HEADER_BYTES 64u
#define COH_MESH_VERTEX_BYTES 48u
#define COH_MESH_MAX_VERTICES 65536u
#define COH_MESH_MAX_INDICES 196608u
#define COH_MESH_MAX_BONES 15u
#define COH_MESH_GLOBAL_BONE_COUNT 99u
/* Canonical, little-endian COHMESH1 bytes derived offline from real geometry.
 * This standalone fixture parser is not a complete .geo loader. The view borrows
 * immutable caller-owned bytes; no legacy pointer is used as a native pointer. */
typedef struct {
    const uint8_t *bytes;
    size_t byte_count;
    uint32_t vertex_count, index_count, bone_count;
    uint32_t vertices_offset, indices_offset, bone_ids_offset;
} CohMeshView;
typedef struct {
    float position[3], normal[3], uv[2], weights[2];
    uint32_t bones[2]; /* local palette slots, legacy encoded row offset / 3 */
} CohMeshVertex;
typedef struct { float position[3], normal[3]; } CohSkinnedVertex;
/* Return0 on success; outputs remain untouched on failure. Parsing validates
 * every vertex, triangle and original global bone identity before publication. */
int coh_mesh_parse(const uint8_t *, size_t, CohMeshView *);
int coh_mesh_vertex(const CohMeshView *, uint32_t, CohMeshVertex *);
int coh_mesh_index(const CohMeshView *, uint32_t, uint32_t *);
int coh_mesh_global_bone(const CohMeshView *, uint32_t, uint32_t *);
/* Source GPU contract:3 affine vec4 rows per local bone, blend using weights.y,
 * then normalize the blended normal. This differs from the original software
 * fallback's unnormalized normal. Controlled poses are not animation playback. */
int coh_mesh_skin_vertex(const CohMeshVertex *, const float *palette_rows,
                         uint32_t palette_bones, CohSkinnedVertex *);
#ifdef __cplusplus
}
#endif
#endif
