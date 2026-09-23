/***************************************************************************
 *     Copyright (c) 2005-2006, Cryptic Studios
 *     All Rights Reserved
 *     Confidential Property of Cryptic Studios
 ***************************************************************************/
#include "storytaskinfo.h"
#include "storyarcprivate.h"
#include <utilitieslib/utils/utils.h>
#include <utilitieslib/assert/assert.h>
#include <utilitieslib/utils/error.h>
#include <utilitieslib/utils/mathutil.h>
#include <utilitieslib/components/earray.h>
#include <utilitieslib/components/MemoryPool.h>

MP_DEFINE(StoryTaskInfo);
StoryTaskInfo* storyTaskInfoAlloc()
{
    MP_CREATE(StoryTaskInfo, 10); 
    return MP_ALLOC(StoryTaskInfo);
}

void storyTaskInfoFree(StoryTaskInfo* info) 
{ 
    MP_FREE(StoryTaskInfo, info); 
}

void storyTaskInfoDestroy(StoryTaskInfo* info)
{
    storyTaskInfoFree(info);
}
