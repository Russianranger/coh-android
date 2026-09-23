#ifndef _SPRITE_LIST_H
#define _SPRITE_LIST_H

#include "render/sprite.h"

DisplaySprite *createDisplaySprite(F32 zp);
int getSpriteIndex(int orderedIndex);
void spriteListReset(void);

#endif
