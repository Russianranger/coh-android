#ifndef COH_HUD_AXIS_NAVIGATION_H
#define COH_HUD_AXIS_NAVIGATION_H
#include "../coh_hud.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Additive mobile-focus policy, not original game/server movement prediction.
 * Caller supplies a selected navigation stick only while UI navigation owns it.
 * All calls occur on the HUD owner thread. No pointers, clock APIs or heap. */
typedef struct {
    int direction,clock_seen,repeating;
    uint64_t last_sample_ms,last_action_ms;
    uint64_t samples,actions,repeats,blocked,rejected;
} CohHudAxisNavigation;
void coh_hud_axis_reset(CohHudAxisNavigation *navigation);
/* Normalized finite axes [-1,1], positive y down; monotonic elapsed ms.
 * Engage .55 / release .35, competing axis switches with a .15 margin.
 * Immediate direction edge; held focus repeat after 350 ms, then every 110 ms.
 * Slow frames emit at most one action; no catch-up burst. Equal timestamps do
 * not repeat. Boundary/no-neighbor is a successful bounded no-op, counted in
 * blocked. Other errors preserve the held direction/timing for a later retry.
 * Reset on navigation OFF, device/focus loss and lifecycle pause. */
CohStatus coh_hud_axis_step(CohHud *hud,CohHudAxisNavigation *navigation,float x,float y,uint64_t monotonic_ms);
#ifdef __cplusplus
}
#endif
#endif
