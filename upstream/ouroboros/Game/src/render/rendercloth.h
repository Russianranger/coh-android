#ifndef _RENDERCLOTH_H
#define _RENDERCLOTH_H

#include "render/model.h"
#include "seq/gfxtree.h"
#include "Cloth/Cloth.h"
#include "Cloth/ClothMesh.h"

#include "render/thread/rt_cloth.h"

void modelDrawClothObject( GfxNode * node, BlendModeType blend_mode );
void modelDrawClothObjectDirect( RdrCloth *rc );
#endif
