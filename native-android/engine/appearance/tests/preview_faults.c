/* Qualification only: inject one deterministic failure into the unchanged
 * production owner boundary, never into its geometry/animation kernels. */
#include "../../renderer/coh_renderer.h"
#include <GLES3/gl3.h>
static unsigned submit_countdown,upload_failure;
void coh_preview_test_submit_failure(unsigned after){submit_countdown=after;}
void coh_preview_test_upload_failure(unsigned enabled){upload_failure=enabled;}
static CohStatus test_submit(CohRenderer*r,const CohRenderDraw*d){if(submit_countdown&&!--submit_countdown)return COH_INVALID;return coh_renderer_submit(r,d);}
static void test_upload(GLenum target,GLint level,GLint format,GLsizei w,GLsizei h,GLint border,GLenum pixel_format,GLenum type,const void*data){if(upload_failure){upload_failure=0;target=0;}glTexImage2D(target,level,format,w,h,border,pixel_format,type,data);}
#define coh_renderer_submit test_submit
#define glTexImage2D test_upload
#include "../coh_appearance_preview.c"
