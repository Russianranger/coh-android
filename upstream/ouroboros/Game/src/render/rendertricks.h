#ifndef _RENDERTRICKS_H
#define _RENDERTRICKS_H

#include <utilitieslib/utils/mathutil.h>
#include "seq/gfxtree.h"
#include "seq/animtrackanimate.h"

typedef struct TrickNode TrickNode;

void gfxNodeSetEntAlpha(GfxNode *node,U8 alpha,int seqHandle );
void gfxNodeSetAlpha(GfxNode *node,U8 alpha,int root);
void gfxNodeSetAlphaFx(GfxNode *node,U8 alpha, int root);
void QuickYawMat(Mat3 mat);

#endif
