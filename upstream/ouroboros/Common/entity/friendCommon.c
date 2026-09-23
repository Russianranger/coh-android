#include "entity/friendCommon.h"
#include <utilitieslib/stdtypes.h>
#include <utilitieslib/utils/memcheck.h>

void friendDestroy(Friend *f)
{
    if (!f)
        return;
    SAFE_FREE(f->mapname);
    SAFE_FREE(f->name);
    f->origin = NULL; // Don't free, it's allocated with allocAddString
    f->arch = NULL;
}