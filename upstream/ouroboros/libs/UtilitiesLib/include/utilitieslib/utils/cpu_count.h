#ifndef _CPU_COUNT_H
#define _CPU_COUNT_H

#include "../stdtypes.h"

C_DECLARATIONS_BEGIN

int getNumVirtualCpus(void);
int getNumRealCpus(void);
int getCacheLineSize(void);

C_DECLARATIONS_END

#endif
