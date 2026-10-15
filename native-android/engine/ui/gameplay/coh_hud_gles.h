#ifndef COH_HUD_GLES_H
#define COH_HUD_GLES_H
#include "../coh_hud.h"
#ifdef __cplusplus
extern "C" {
#endif
#define COH_HUD_GLES_BATCH_QUADS 128u
typedef struct { float x,y,u,v,r,g,b,a; } CohHudVertex;
/* Handle belongs to the caller and current GL context. red_coverage=1 samples
 * the red channel as glyph coverage (e.g. GL_R8); 0 samples an RGBA image. */
typedef struct { uint32_t handle; int red_coverage; } CohHudTexture;
typedef CohStatus (*CohHudTextureFn)(void *context,uint32_t resource,CohHudTexture *texture);
typedef struct {
    uint64_t frames,quads,draw_calls,bytes_uploaded,rejected_frames,gl_errors,preexisting_errors;
    size_t arena_bytes,batch_high_water;
} CohHudGlesStats;
typedef struct {
    uint32_t generation,program,buffer,vao; int viewport_uniform,mode_uniform,sampler_uniform;
    CohHudVertex vertices[COH_HUD_GLES_BATCH_QUADS*6u];
    /* Resolve before any drawing, so missing/invalid resources fail atomically. */
    CohHudTexture resolved[COH_UI_DRAWS];
    char shader_log[1024]; CohHudGlesStats stats;
} CohHudGles;
/* GL thread, current GLES3 context. Zero-initialize renderer before first create.
 * Caller uploads/owns original font atlas. This is a last-pass backend: draw
 * leaves program/VAO/array-buffer/texture zero, scissor disabled, depth-write
 * true; blending enabled and depth/cull disabled. Establish scene state before
 * the next scene pass. No glFinish, readback or dynamic heap allocation. */
CohStatus coh_hud_gles_create(CohHudGles *renderer,uint32_t generation);
CohStatus coh_hud_gles_draw(CohHudGles *renderer,int width,int height,uint32_t generation,
                           const CohUiDraw *draws,size_t count,CohHudTextureFn resolve,void *context);
void coh_hud_gles_destroy(CohHudGles *renderer); /* same current context, idempotent */
void coh_hud_gles_forget(CohHudGles *renderer); /* context already lost: never calls GL */
/* Pure geometry/validation functions shared with host tests. */
CohStatus coh_hud_quad(const CohUiDraw *draw,uint32_t generation,CohHudVertex out[6]);
CohStatus coh_hud_scissor(CohUiRect clip,int width,int height,int out[4]);
#ifdef __cplusplus
}
#endif
#endif
