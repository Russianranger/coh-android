#include "utilitieslib/stdtypes.h"
#include "utilitieslib/UtilsNew/lock.h"

void lazyLockInit(volatile LONG *initializing, volatile S32 *initialized, CRITICAL_SECTION *cs)
{
    LONG init = InterlockedExchange(initializing, 1);
    if(!init) // first
    {
        InitializeCriticalSectionAndSpinCount(cs, 4000);
        *initialized = 1;
    }
    else
    {
        while(!*initialized)
            Sleep(1);
    }
}
