#ifndef _RENDERSHADOW_H
#define _RENDERSHADOW_H

#include "render/model.h"
#include "seq/gfxtree.h"
#include "graphics/splat.h"
#include "seq/animtrackanimate.h"
#include "render/thread/rt_shadow.h"

// stencil shadows
int shadowVolumeVisible(Vec3 mid,F32 radius,F32 shadow_dist);
void shadowStartScene(void);
void shadowFinishScene(void);
void modelDrawShadowVolume(Model *model,Mat4 mat,int alpha,int shadow_mask, GfxNode * node);


// splat shadows
void modelDrawShadowObject( Mat4 viewspace, Splat * splat );

#endif
