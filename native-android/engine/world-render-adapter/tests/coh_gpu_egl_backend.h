#ifndef COH_GPU_EGL_BACKEND_H
#define COH_GPU_EGL_BACKEND_H
/* STANDALONE qualification backend. Owns private EGL pbuffers/contexts; it
 * cannot adopt or authorize the game's protected renderer context/materials. */
#include "../coh_wr_gpu_texture.h"
typedef struct CohGpuEglBackend CohGpuEglBackend;
typedef struct {
    uint32_t gles_major,contexts_created,surfaces_created,contexts_destroyed,surfaces_destroyed;
    uint32_t gpu_owners,pending_cleanup,readbacks;
    char gl_version[192],gl_renderer[192];
} CohGpuEglReport;
/* One standalone backend per process. On initialization failure a nonNULL
 * partial owner retains cleanup responsibility; close() must still be called. */
CohStatus coh_gpu_egl_create(CohGpuEglBackend **);
CohStatus coh_gpu_egl_token(CohGpuEglBackend *,CohWrGpuToken *);
CohStatus coh_gpu_egl_upload(CohGpuEglBackend *,const CohWrTextureResource *,const CohWrSamplerSource *,const CohWrGpuLimits *,CohWrGpuTexture **);
CohStatus coh_gpu_egl_view(CohGpuEglBackend *,const CohWrGpuTexture *,CohWrGpuToken,CohRenderTexture *);
CohStatus coh_gpu_egl_readback(CohGpuEglBackend *,const CohWrGpuTexture *,uint32_t,uint8_t *rgba,size_t capacity);
CohStatus coh_gpu_egl_release(CohGpuEglBackend *,CohWrGpuTexture **);
/* Qualification-only deterministic callback failures; not an application API. */
CohStatus coh_gpu_egl_test_faults(CohGpuEglBackend *,unsigned image_error,unsigned deletion_error);
CohStatus coh_gpu_egl_retry_cleanup(CohGpuEglBackend *);
CohStatus coh_gpu_egl_replace_surface(CohGpuEglBackend *);
CohStatus coh_gpu_egl_replace_context(CohGpuEglBackend *);
CohStatus coh_gpu_egl_report(CohGpuEglBackend *,CohGpuEglReport *);
/* Destroy all actual owned contexts; verifies destruction before abandoning old
 * journals. GPU CPU owners still require release() before close(). */
CohStatus coh_gpu_egl_destroy_contexts(CohGpuEglBackend *);
CohStatus coh_gpu_egl_close(CohGpuEglBackend **);
#endif
