/* Nonshipping, bounded Cg observations. Never authorize cached shader bytes. */
#ifndef COH_NATIVE_CG_PROFILE_H
#define COH_NATIVE_CG_PROFILE_H
#include <windows.h>
#include <stdio.h>
#include <string.h>
typedef unsigned long long CohCgClock;
typedef struct CohNativeCgProfile {
    CohCgClock begin, create_us, load_us;
    unsigned int active, valid, kind, loaded, token;
} CohNativeCgProfile;
static unsigned int cohCgRows;
static int cohCgClock(CohCgClock *out) {
    LARGE_INTEGER count, frequency;
    double value;
    if (!QueryPerformanceFrequency(&frequency) || frequency.QuadPart <= 0 ||
        !QueryPerformanceCounter(&count) || count.QuadPart < 0) return 0;
    value = (double)count.QuadPart * 1000000.0 / (double)frequency.QuadPart;
    if (value >= 18446744073709551616.0) return 0;
    *out = (CohCgClock)value;
    return 1;
}
static void cohCgBegin(CohNativeCgProfile *p, unsigned int kind, const char *name) {
    unsigned int i;
    memset(p, 0, sizeof(*p));
    if (cohCgRows >= 1024u) return;
    ++cohCgRows;
    p->active = 1; p->kind = kind; p->token = 2166136261u;
    if (name) for (i = 0; i < 512 && name[i]; ++i)
        p->token = (p->token ^ (unsigned char)name[i]) * 16777619u;
    p->valid = cohCgClock(&p->begin);
}
static void cohCgElapsed(CohNativeCgProfile *p, CohCgClock *target) {
    CohCgClock now;
    if (!p->active || !p->valid) return;
    if (!cohCgClock(&now) || now < p->begin) { p->valid = 0; return; }
    *target = now - p->begin;
}
static void cohCgLoadBegin(CohNativeCgProfile *p) {
    if (!p->active) return;
    p->loaded = 1;
    if (p->valid) p->valid = cohCgClock(&p->begin);
}
static void cohCgEnd(CohNativeCgProfile *p, int success) {
    if (!p->active) return;
    if (!p->valid) p->create_us = p->load_us = 0;
    printf("COH_NATIVE_CG_PROFILE_V1 kind=%u input_token=%08x success=%u clock_valid=%u create_us=%llu driver_load_called=%u driver_load_us=%llu\n",
        p->kind, p->token, success ? 1u : 0u, p->valid, p->create_us, p->loaded, p->load_us);
    p->active = 0;
}
#endif
