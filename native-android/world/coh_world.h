#ifndef COH_WORLD_H
#define COH_WORLD_H
#include <stddef.h>
#include <stdint.h>
#define COH_WORLD_NODES 6u
#define COH_WORLD_CAMERAS 6u
#define COH_WORLD_INPUT_BYTES 520u
/* Mat4 contains four source columns of three floats; Mat44 has four of four. */
typedef struct { uint32_t parent; float position[3],pyr_degrees[3]; } CohWorldNode;
typedef struct { float position[3],pyr_degrees[3],fovy,aspect,znear,zfar; uint32_t flip_x,flip_y; } CohWorldCamera;
typedef struct { CohWorldNode nodes[COH_WORLD_NODES]; CohWorldCamera cameras[COH_WORLD_CAMERAS]; } CohWorldInputs;
int coh_world_parse_inputs(const uint8_t *bytes,size_t byte_count,CohWorldInputs *out);
int coh_world_group_matrices(const CohWorldInputs *inputs,float local[COH_WORLD_NODES][12],float world[COH_WORLD_NODES][12]);
/* Original group traversal starts at the view matrix and composes each child. */
int coh_world_group_eye_matrices(const CohWorldInputs *inputs,const float view[12],float eye[COH_WORLD_NODES][12]);
/* An aspect_override of zero selects the source fixture camera aspect. */
int coh_world_camera(const CohWorldInputs *inputs,uint32_t camera,float aspect_override,float view[12],float projection[16]);
void coh_world_gl_matrix(const float source[12],float gl_columns[16]);
/* output: world xyz, unnormalized eye normal xyz, eye xyz, homogeneous clip xyzw. */
int coh_world_vertex(const float world[12],const float modelview[12],const float projection[16],const float position[3],const float normal[3],float output[13]);
#endif
