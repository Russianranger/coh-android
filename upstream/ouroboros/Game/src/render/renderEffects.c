#include "render/renderEffects.h"
#include "render/thread/rt_queue.h"
#include "render/thread/rt_effects.h"
#include "render/tex_gen.h"
#include "render/tex.h"
#include <utilitieslib/utils/timing.h>
#include <utilitieslib/utils/mathutil.h>
#include "seq/gfxtree.h"
#include "seq/anim.h"
#include "graphics/camera.h"

void rdrPostprocessing(PBuffer *pbFrameBuffer)
{
    rdrQueue(DRAWCMD_POSTPROCESSING,&pbFrameBuffer,sizeof(pbFrameBuffer));
}

void rdrRenderScaled(PBuffer *pbFrameBuffer)
{
    rdrQueue(DRAWCMD_RENDERSCALED,&pbFrameBuffer,sizeof(pbFrameBuffer));
}

void rdrHDRThumbnailDebug(void)
{
    rdrQueueCmd(DRAWCMD_HDRDEBUG);
}

void rdrSunFlareUpdate(GfxNode * sun, float * visibility)
{
    RdrSunFlareParams params;

    if(!sun || !sun->model || !sun->model->vbo) {
        *visibility = 0.0f;
        return;
    }

    params.vbo = sun->model->vbo;
    mulMat4(cam_info.viewmat, sun->mat, params.mat);
    params.visibility = visibility;

    PERFINFO_AUTO_START("rdrSunFlareUpdateDirect",1);
    rdrQueue(DRAWCMD_SUNFLAREUPDATE, &params, sizeof(params));
    PERFINFO_AUTO_STOP();
}