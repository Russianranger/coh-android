/* Nonshipping SERVER observer. No namespace certificate or loader bypass. */
#ifndef COH_MAP_BIN_OBSERVER_H
#define COH_MAP_BIN_OBSERVER_H

#ifdef SERVER
#include <windows.h>
#include <stdio.h>
#include <string.h>

#define COH_MAP_BIN_OBSERVER_LIMIT 256u
#define COH_MAP_BIN_OBSERVER_PHASES 6u
typedef unsigned long long CohMapBinClock;
typedef struct CohMapBinObservation {
    CohMapBinClock previous, elapsed[COH_MAP_BIN_OBSERVER_PHASES];
    unsigned int ordinal, phase, active, clock_valid;
    unsigned int input_token;
} CohMapBinObservation;
static unsigned int cohMapBinObservationCount;

static int cohMapBinClock(CohMapBinClock *value)
{
    LARGE_INTEGER counter, frequency;
    double microseconds;
    if (!QueryPerformanceFrequency(&frequency) || frequency.QuadPart <= 0
        || !QueryPerformanceCounter(&counter) || counter.QuadPart < 0)
        return 0;
    /* This is observation only. Double conversion avoids integer overflow. */
    microseconds = (double)counter.QuadPart * 1000000.0 / (double)frequency.QuadPart;
    if (microseconds >= 18446744073709551616.0) return 0;
    *value = (CohMapBinClock)microseconds;
    return 1;
}

static unsigned int cohMapBinInputToken(const char *bin, const char *dir, const char *mask)
{
    const char *inputs[3];
    unsigned int hash = 2166136261u, i, j;
    inputs[0] = bin; inputs[1] = dir; inputs[2] = mask;
    for (i = 0; i < 3; ++i) {
        /* Bounded diagnostic identifier, deliberately not an integrity proof. */
        hash = (hash ^ (inputs[i] ? 1u : 0u)) * 16777619u;
        if (inputs[i]) for (j = 0; j < 512 && inputs[i][j]; ++j)
            hash = (hash ^ (unsigned char)inputs[i][j]) * 16777619u;
        hash = (hash ^ 255u) * 16777619u;
    }
    return hash;
}

static void cohMapBinBegin(CohMapBinObservation *value, const char *bin,
                           const char *dir, const char *mask)
{
    memset(value, 0, sizeof(*value));
    if (cohMapBinObservationCount >= COH_MAP_BIN_OBSERVER_LIMIT) return;
    value->ordinal = ++cohMapBinObservationCount;
    value->active = 1;
    value->input_token = cohMapBinInputToken(bin, dir, mask);
    value->clock_valid = cohMapBinClock(&value->previous);
}

static void cohMapBinPhase(CohMapBinObservation *value, unsigned int next)
{
    CohMapBinClock now = 0;
    if (!value->active) return;
    if (value->clock_valid && (!cohMapBinClock(&now) || now < value->previous))
        value->clock_valid = 0;
    if (value->clock_valid && value->phase < COH_MAP_BIN_OBSERVER_PHASES)
        value->elapsed[value->phase] = now - value->previous;
    value->previous = now;
    value->phase = next;
}

static void cohMapBinFinish(CohMapBinObservation *value, const char *outcome)
{
    unsigned int i;
    if (!value->active) return;
    cohMapBinPhase(value, COH_MAP_BIN_OBSERVER_PHASES);
    /* Invalid/partial time is explicit; never present a partial sum as a total. */
    if (!value->clock_valid) for (i = 0; i < COH_MAP_BIN_OBSERVER_PHASES; ++i)
        value->elapsed[i] = 0;
    printf("COH_MAP_BIN_FRESHNESS_V1 ordinal=%u input_token=%08x outcome=%s clock_valid=%u "
           "open_us=%llu dependencies_us=%llu scan_us=%llu dates_us=%llu membership_us=%llu cleanup_us=%llu\n",
           value->ordinal, value->input_token, outcome, value->clock_valid,
           value->elapsed[0], value->elapsed[1], value->elapsed[2],
           value->elapsed[3], value->elapsed[4], value->elapsed[5]);
    value->active = 0;
}

#define COH_MAP_BIN_DECLARE() CohMapBinObservation cohMapBinObservation
#define COH_MAP_BIN_BEGIN(bin, dir, mask) cohMapBinBegin(&cohMapBinObservation, bin, dir, mask)
#define COH_MAP_BIN_PHASE(next) cohMapBinPhase(&cohMapBinObservation, next)
#define COH_MAP_BIN_FINISH(outcome) cohMapBinFinish(&cohMapBinObservation, outcome)
#else
#define COH_MAP_BIN_DECLARE()
#define COH_MAP_BIN_BEGIN(bin, dir, mask) ((void)0)
#define COH_MAP_BIN_PHASE(next) ((void)0)
#define COH_MAP_BIN_FINISH(outcome) ((void)0)
#endif
#endif
