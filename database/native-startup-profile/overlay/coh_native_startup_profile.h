/* Observational only: no loader, allocation, source or validation decisions. */
#ifndef COH_NATIVE_STARTUP_PROFILE_H
#define COH_NATIVE_STARTUP_PROFILE_H
#ifdef COH_NATIVE_STARTUP_PROFILE
#include <windows.h>
#include <stdio.h>
#include <string.h>
typedef unsigned long long CohNativeProfileClock;
typedef struct CohNativeProfile {
    CohNativeProfileClock started;
    const char *phase;
    unsigned int token, active, clock_valid;
} CohNativeProfile;
static unsigned int cohNativeProfileRows;
static int cohNativeProfileClock(CohNativeProfileClock *out)
{
    LARGE_INTEGER count, frequency;
    double value;
    if (!QueryPerformanceFrequency(&frequency) || frequency.QuadPart <= 0
        || !QueryPerformanceCounter(&count) || count.QuadPart < 0) return 0;
    value = (double)count.QuadPart * 1000000.0 / (double)frequency.QuadPart;
    if (value >= 18446744073709551616.0) return 0;
    *out = (CohNativeProfileClock)value;
    return 1;
}
static void cohNativeProfileBegin(CohNativeProfile *value, const char *phase, const char *input)
{
    unsigned int i;
    memset(value, 0, sizeof(*value));
    if (cohNativeProfileRows >= 256u) return;
    ++cohNativeProfileRows;
    value->active = 1;
    value->phase = phase;
    value->token = 2166136261u;
    if (input) for (i = 0; i < 512 && input[i]; ++i)
        value->token = (value->token ^ (unsigned char)input[i]) * 16777619u;
    value->clock_valid = cohNativeProfileClock(&value->started);
}
static void cohNativeProfileEnd(CohNativeProfile *value, int success)
{
    CohNativeProfileClock now = 0, elapsed = 0;
    if (!value->active) return;
    if (value->clock_valid && (!cohNativeProfileClock(&now) || now < value->started))
        value->clock_valid = 0;
    if (value->clock_valid) elapsed = now - value->started;
    printf("COH_NATIVE_STARTUP_PROFILE_V1 phase=%s input_token=%08x success=%u clock_valid=%u elapsed_us=%llu\n",
        value->phase, value->token, success ? 1u : 0u, value->clock_valid, elapsed);
    value->active = 0;
}
#define COH_NATIVE_PROFILE_DECLARE(name) CohNativeProfile cohNativeProfile_##name
#define COH_NATIVE_PROFILE_BEGIN(name, phase, input) cohNativeProfileBegin(&cohNativeProfile_##name, phase, input)
#define COH_NATIVE_PROFILE_END(name, success) cohNativeProfileEnd(&cohNativeProfile_##name, success)
#else
#define COH_NATIVE_PROFILE_DECLARE(name)
#define COH_NATIVE_PROFILE_BEGIN(name, phase, input) ((void)0)
#define COH_NATIVE_PROFILE_END(name, success) ((void)0)
#endif
#endif
