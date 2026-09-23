#include "utilitieslib/stdtypes.h"
#include "../include/ailib/aiLib.h"
#include "../include/ailib/aiBehaviorInterface.h"
#include "../include/ailib/aiStruct.h"


void aiLibStartup()
{
    aiBehaviorRebuildLookupTable();
}

void aiTick(BaseEntity* e, AIVarsBase* aibase)
{
    aiBehaviorProcess((Entity*)e, aibase, &aibase->behaviors);
}