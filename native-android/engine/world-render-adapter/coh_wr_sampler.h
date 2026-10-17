#ifndef COH_WR_SAMPLER_H
#define COH_WR_SAMPLER_H
#include "../renderer/coh_renderer.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Pure CLIENT source-value projection; this is NOT a material, texture lookup,
 * generation, source-authentication or world admission API. effective_flags
 * must come from the qualified final BasicTexture.texopt_flags, never cached
 * .texture TexOptFlags, GEO texture names or SERVER model trick flags.
 * mip_count is TexReadInfo's DDS count AFTER original skip reduction;
 * zero denotes the one-level no-mipmap source case.
 * Supplier must retain/upload every admitted level and prove identities,
 * effective CLIENT trick resolution/capabilities and Surface ownership.
 * This helper owns no storage, GL handles, material or resource pins. */
typedef struct {
    uint32_t effective_flags,target,width,height,mip_count,available_levels;
    uint32_t clamp_to_edge; /* original gl_clamp_val == GL_CLAMP_TO_EDGE */
    float anisotropy; /* effective sampling state: only exactly1 supported */
} CohWrSamplerSource;
/* out unchanged on refusal; zero GPU name on success. Cube, JPEG, border,
 * unknown flags, nonedge clamp, anisotropy>1 and incomplete mip filtering
 * cannot be represented faithfully by this bounded backend. */
CohStatus coh_wr_sampler_project(const CohWrSamplerSource *,CohRenderTexture *out);
#ifdef __cplusplus
}
#endif
#endif
