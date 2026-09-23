#include "utilitieslib/utilitiesLib.h"
#include "utilitieslib/utils/memcheck.h"
#include "utilitieslib/utils/rand.h"
#include "utilitieslib/utils/mathutil.h"
#include "utilitieslib/components/referencesystem.h"
#include "utilitieslib/utils/wininclude.h"

static bool bInit = false;
int gBuildVersion = 0;

void utilitiesLibPreAutoRunStuff(void)
{
    static int once = 0;

    if (!once)
    {            
        once = 1;
        memCheckInit();
//         ScratchStackInitSystem();
    }
}

bool utilitiesLibStartup()
{
    if ( bInit )
        return false;

    initRand();
    initQuickTrig();
    RefSystem_Init();

    return true;
}

void DebuggerPrint(const char * msg) {
    OutputDebugStringA(msg);
}
