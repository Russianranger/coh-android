/* A launch-only overlay. The saved graphics preferences remain the baseline. */
#ifndef COH_ANDROID_GRAPHICS_PROFILE_H
#define COH_ANDROID_GRAPHICS_PROFILE_H

#include <string.h>

typedef struct CohAndroidGraphicsProfile {
    int captured;
    GfxSettings saved;
} CohAndroidGraphicsProfile;

static int cohAndroidGraphicsProfileEnabled(const char *profile)
{
    return profile && !strcmp(profile, "performance");
}

static int cohAndroidGraphicsProfileApply(CohAndroidGraphicsProfile *profile,
    const char *selected, GfxSettings *settings,
    void (*minimumSettings)(GfxSettings *))
{
    if (!cohAndroidGraphicsProfileEnabled(selected))
        return 0;
    if (!profile->captured) {
        profile->saved = *settings;
        profile->captured = 1;
    }
    minimumSettings(settings);
    settings->antialiasing = 0;
    settings->useRenderScale = RENDERSCALE_SCALE;
    settings->renderScaleX = settings->renderScaleY = 0.75f;
    return 1;
}

static void cohAndroidGraphicsProfileSaved(const CohAndroidGraphicsProfile *profile,
    GfxSettings *settings)
{
    if (profile->captured)
        *settings = profile->saved;
}

#endif
