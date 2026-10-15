#ifndef COH_SESSION_STREAM_QUALIFY_H
#define COH_SESSION_STREAM_QUALIFY_H
#include "../../../../../engine/renderer/coh_renderer.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint64_t tf_components, tf_mismatches, visible_pixels;
    float max_error;
} CohStreamQualification;
/* Once per current context, on its GL owner thread, while renderer is idle.
 * Draws retain their real geometry, material handles, matrices and projection.
 * At most 200,000 total borrowed vertices and 512 draws are admitted. No asset
 * names, generated replacement geometry or per-frame readback are involved.
 * Per-attempt stats are reset, including on failure; the caller aggregates.
 * Restores draw/read framebuffer, viewport, pixel-pack state and TF objects;
 * unbinds samplers 0..2 and restores accepted LEQUAL/depth-write/CW/BACK state.
 * Caller rebinds its program and VAO before the next accepted rendering pass. */
int coh_stream_qualify(CohRenderer *renderer, const CohRenderDraw *draws,
                       size_t count, CohStreamQualification *stats,
                       char *error, size_t errorcap);
#ifdef __cplusplus
}
#endif
#endif
