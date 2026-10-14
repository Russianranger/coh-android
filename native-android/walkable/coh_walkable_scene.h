#ifndef COH_WALKABLE_SCENE_H
#define COH_WALKABLE_SCENE_H
#include "coh_world_scene.h"
#include "coh_walk.h"
#define COH_WALKABLE_PARTS 32u
#define COH_WALKABLE_TEXTURES 16u
typedef struct {
    CohWorldPart material;
    float uv_scale0[2],uv_scale1[2];
} CohWalkablePart;
typedef struct {
    const uint8_t *bytes; size_t byte_count;
    uint32_t part_count,texture_count,triangle_count,vertices,indices;
    CohWalkablePart parts[COH_WALKABLE_PARTS];
    CohWorldTexture textures[COH_WALKABLE_TEXTURES];
    const CohWalkTriangle *triangles;
    float bounds_min[3],bounds_max[3],spawn[3],spawn_yaw;
} CohWalkableScene;
/* Immutable COHWALK1 on little-endian IEEE binary32 Android ARM64/x86 hosts.
 * Baked authored world vertices and collision vertices share exact floats.
 * The bounded header, contiguous spans, materials and triangles are checked;
 * no disk pointer is relocated. Output is unchanged on failure. */
int coh_walkable_scene_parse(const uint8_t *,size_t,CohWalkableScene *);
#endif
