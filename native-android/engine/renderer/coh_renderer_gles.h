#ifndef COH_RENDERER_GLES_H
#define COH_RENDERER_GLES_H
#include "coh_renderer.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct CohGlesRenderer CohGlesRenderer;
/* GLES3 context must be current. Owns fixed-capacity VBO/IBO, VAO, samplers and
 * up to four transient programs (three cached + one compiling before eviction).
 * Texture names remain caller-owned. Uploads caller vertices/indices with
 * glBufferSubData, no readback/fence/glFinish. Immutable GPU mesh cache is
 * future work; this initial adapter prioritizes bounded storage over draw
 * throughput. *out must be NULL. Occupied output refuses with COH_STATE before
 * allocation or GL calls, preserving both the owner and backend descriptor. */
CohStatus coh_renderer_gles_create(size_t max_vertices, size_t max_indices,
                                   CohGlesRenderer **out,
                                   CohRenderBackend *backend);
/* Call core surface_lost before recreate. Preserves the backend context
 * pointer. */
CohStatus coh_renderer_gles_recreate(CohGlesRenderer *,
                                     int previous_context_alive);
void coh_renderer_gles_destroy(CohGlesRenderer *, int context_alive);
const char *coh_renderer_gles_shader_log(const CohGlesRenderer *);
size_t coh_renderer_gles_buffer_bytes(const CohGlesRenderer *);
size_t coh_renderer_gles_owned_bytes(const CohGlesRenderer *);
size_t coh_renderer_gles_allocation_bytes(void);
#ifdef __cplusplus
}
#endif
#endif
