#ifndef COH_RENDERER_H
#define COH_RENDERER_H
#include "../coh_contracts.h"
#ifdef __cplusplus
extern "C" {
#endif
/* CPU spans are borrowed, immutable until flush returns, on one GL owner
 * thread. Matrices are source-layout column major, model_view already
 * source-composed. UVs are source prepared VBO values (V = 1 - disk V); no
 * second flip is made. */
typedef enum {
  COH_MAT_MULTIPLY = 0,
  COH_MAT_DUAL = 1,
  COH_MAT_ADDGLOW = 2
} CohMaterialFamily;
typedef enum {
  COH_LIGHT_VERTEX = 0,
  COH_LIGHT_DIFFUSE = 1,
  COH_LIGHT_FIXED = 2
} CohLightingMode;
typedef enum {
  COH_WRAP_REPEAT = 0,
  COH_WRAP_CLAMP = 1,
  COH_WRAP_MIRROR = 2
} CohWrap;
typedef enum {
  COH_FILTER_NEAREST = 0,
  COH_FILTER_LINEAR = 1,
  COH_FILTER_MIP_LINEAR = 2
} CohFilter;
typedef enum {
  COH_BLEND_OPAQUE = 0,
  COH_BLEND_ALPHA = 1,
  COH_BLEND_ADDITIVE = 2
} CohBlend;
typedef struct {
  float position[3], normal[3], uv0[2], uv1[2], color[4];
} CohRenderVertex;
typedef struct {
  const CohRenderVertex *vertices;
  size_t vertex_count;
  const uint32_t *indices;
  size_t index_count;
  uint64_t identity;
  uint32_t generation; /* optional backend cache identity */
} CohRenderGeometry;
typedef struct {
  uint32_t handle; /* borrowed GL/backend texture name, valid for Surface
                      generation */
  CohWrap wrap_s, wrap_t;
  CohFilter min_filter, mag_filter;
} CohRenderTexture;
typedef struct {
  CohMaterialFamily family;
  CohLightingMode lighting;
  CohRenderTexture textures[3];
  float const0[4], const1[4], fog_params[4], fog_color[4], glow_params[4];
  float light[3], diffuse[4], ambient[4], specular[3], shininess;
  float alpha_ref;
  CohBlend blend;
  uint8_t depth_test, depth_write, cull_back, front_cw;
} CohRenderMaterial;
typedef struct {
  CohRenderGeometry geometry;
  CohRenderMaterial material;
  float model_view[16], projection[16];
  uint64_t
      sequence; /* renderer fills, preserving equal-key and translucent order */
} CohRenderDraw;
typedef struct {
  /* Compile/link must consume strings synchronously. No callback may retain a
   * draw. */
  CohStatus (*compile)(void *, CohMaterialFamily, const char *, const char *,
                       uint32_t *);
  void (*destroy_program)(void *, uint32_t);
  CohStatus (*bind)(void *, uint32_t, const CohRenderMaterial *);
  CohStatus (*draw)(void *, uint32_t, const CohRenderDraw *);
  void *context;
} CohRenderBackend;
typedef struct {
  size_t max_draws, max_vertices_per_draw, max_indices_per_draw;
  size_t shader_capacity; /* 1..3, lazy LRU */
} CohRendererConfig;
typedef struct {
  size_t owned_bytes, borrowed_vertex_bytes, borrowed_index_bytes, queued,
      high_water_draws;
  uint64_t submitted, drawn, rejected, compiles, cache_hits, evictions,
      state_binds, cancelled;
  uint32_t surface_generation;
} CohRendererStats;
typedef struct CohRenderer CohRenderer;
CohRendererConfig coh_renderer_default_config(void);
CohRenderMaterial coh_renderer_default_material(CohMaterialFamily);
CohStatus coh_renderer_create(const CohRendererConfig *,
                              const CohRenderBackend *, CohRenderer **);
void coh_renderer_destroy(CohRenderer *);
/* begin is invalid with outstanding submissions. Surface generation mismatch is
 * rejected. */
CohStatus coh_renderer_begin(CohRenderer *, uint32_t surface_generation);
CohStatus coh_renderer_submit(CohRenderer *, const CohRenderDraw *);
/* Only contiguous opaque runs are batched. Translucent draws preserve caller
 * order; caller must supply correct back-to-front order. No GL
 * synchronization/readback. */
CohStatus coh_renderer_flush(CohRenderer *, CohCancel);
/* Drops pending draws and invalidates programs. When context_alive=0, no GL
 * deletion. */
void coh_renderer_surface_lost(CohRenderer *, uint32_t new_generation,
                               int context_alive);
CohRendererStats coh_renderer_stats(const CohRenderer *);
/* Public scalar source-contract evaluators. Output unchanged on malformed
 * input. Fragment samples are already sampled RGBA; glow mask is the red sample
 * at floor(uv0)/128 + glow_params.yw (caller controls the sampler). */
CohStatus coh_renderer_vertex(const CohRenderDraw *, const CohRenderVertex *,
                              float clip[4], float normal[3], float lit[4],
                              float *fog);
CohStatus coh_renderer_fragment(const CohRenderMaterial *, const float base[4],
                                const float dual[4], float glow_mask,
                                const float lit[4], float fog, float rgba[4],
                                int *discard);
/* Fixed normalized framebuffer blending, including original alpha equation. */
void coh_renderer_blend(CohBlend, const float src[4], const float dst[4],
                        float out[4]);
/* Null-terminated ESSL 3.00 source, stable for the module lifetime. */
const char *coh_renderer_vertex_shader(void);
const char *coh_renderer_fragment_shader(CohMaterialFamily);
/* ESSL3.20 core precise variants retain source transform operation order.
 * Backend selects only with an actual GLES3.2 context; 3.00 stays TF-gated. */
const char *coh_renderer_vertex_shader_precise(void);
const char *coh_renderer_fragment_shader_precise(CohMaterialFamily);
#ifdef __cplusplus
}
#endif
#endif
