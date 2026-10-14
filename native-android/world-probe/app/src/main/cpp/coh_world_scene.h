#ifndef COH_WORLD_SCENE_H
#define COH_WORLD_SCENE_H
#include "coh_mesh.h"
#include "coh_world.h"
#define COH_WORLD_PARTS 16u
#define COH_WORLD_TEXTURES 32u
typedef struct {
    CohMeshView mesh;
    uint32_t node,base_texture,dual_texture,flags,mode;
    float const0[4],const1[4],diffuse_scale,ambient_scale,alpha_ref;
} CohWorldPart;
typedef struct { uint32_t width,height;const uint8_t*rgba;size_t bytes; } CohWorldTexture;
typedef struct {
    const uint8_t*bytes;size_t byte_count;
    uint32_t part_count,texture_count,vertices,indices;
    CohWorldInputs inputs;
    CohWorldPart parts[COH_WORLD_PARTS];
    CohWorldTexture textures[COH_WORLD_TEXTURES];
} CohWorldScene;
/* Bounded contiguous immutable COHWOR09 fixture adapter. Output unchanged on failure. */
int coh_world_scene_parse(const uint8_t*,size_t,CohWorldScene*);
#endif
