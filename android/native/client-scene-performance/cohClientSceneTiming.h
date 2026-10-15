/* Opt-in, bounded scene timing. No allocation, payload read or loader policy. */
#ifndef COH_CLIENT_SCENE_TIMING_H
#define COH_CLIENT_SCENE_TIMING_H
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int cohClientSceneExactOption(const char *name)
{
    const char *value = getenv(name);
    return value && strcmp(value, "1") == 0;
}

static int cohClientSceneProfileEnabled(void)
{
    static int enabled = -1;
    if (enabled < 0)
        enabled = cohClientSceneExactOption("COH_CLIENT_SCENE_PROFILE");
    return enabled;
}

static int cohClientSceneDeferDiscardedFx(void)
{
    static int enabled = -1;
    if (enabled < 0)
        enabled = cohClientSceneExactOption("COH_CLIENT_DEFER_DISCARDED_FX_PRELOAD");
    return enabled;
}

static DWORD cohClientSceneBegin(void)
{
    return cohClientSceneProfileEnabled() ? GetTickCount() : 0;
}

static void cohClientScenePhase(const char *phase, DWORD *begin, int success)
{
    static unsigned int reports;
    DWORD now;
    if (!cohClientSceneProfileEnabled())
        return;
    now = GetTickCount();
    if (reports < 128)
    {
        ++reports;
        printf("COH_CLIENT_SCENE_PHASE_V1 {\"phase\":\"%s\",\"milliseconds\":%lu,\"success\":%d,\"ordinal\":%u,\"clock\":\"GetTickCount\",\"bound_per_translation_unit\":128}\n",
            phase, (unsigned long)(DWORD)(now - *begin), success, reports);
    }
    *begin = now;
}
#endif
