#ifndef COH_SCENE_H
#define COH_SCENE_H
#include "coh_mesh.h"
#define COH_SCENE_PARTS 11u
#define COH_SCENE_TEXTURES 32u
typedef struct {
    CohMeshView mesh;
    uint32_t socket,base_texture,dual_texture;
    float const0[4],const1[4],diffuse_scale,ambient_scale,alpha_ref;
    uint32_t flags; /* bit0: source DoubleSided; bit1: alpha-bearing Hair mask */
} CohScenePart;
typedef struct { uint32_t width,height; const uint8_t *rgba; size_t bytes; } CohSceneTexture;
typedef struct {
    const uint8_t *bytes; size_t byte_count;
    uint32_t part_count,texture_count,vertices,indices,blended_vertices;
    CohScenePart parts[COH_SCENE_PARTS];
    CohSceneTexture textures[COH_SCENE_TEXTURES];
} CohScene;
/* Bounded contiguous COHCHAR8 adapter, not a legacy pointer-based GEO loader.
 * Borrowed immutable bytes. Output remains untouched on every parse failure. */
int coh_scene_parse(const uint8_t *,size_t,CohScene *);
#endif
