#ifndef _RENDERBONEDMODEL_H
#define _RENDERBONEDMODEL_H

#include "seq/gfxtree.h" 
#include "render/thread/rt_queue.h" 
#include "render/thread/rt_bonedmodel.h" 

typedef struct BoneInfo BoneInfo;

void modelDrawBonedNode( GfxNode *node, BlendModeType blend_mode, int tex_index, Mat4 viewMatrix );
BoneInfo * assignDummyBoneInfo(char * model_name);
void initMyFakeBoneInfo(void);
GfxNode * modelInitADummyNode( Model *model, Mat4 mat );

#endif
