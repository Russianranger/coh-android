#ifndef COH_WORLD_CAPTURE_HOOKS_H
#define COH_WORLD_CAPTURE_HOOKS_H
#include "coh_world_capture.h"
/* Probe-only GNU/LLD --wrap boundary. Exactly one owner thread and one fresh
 * local session per process. This never patches accepted module sources. */
typedef struct {
    CohWorldCaptureBinding binding;
    CohNetEndpoint db,map;
    unsigned version;
    size_t retained_reservation;
    CohNetUdp *db_udp,*map_udp;
    CohWorldCapture *capture;
    CohStatus capture_status;
    CohGroupsFailure capture_failure;
    unsigned db_creates,map_creates,groups_seen,map_commands,blocked_commands,blocked_endpoints;
} CohWorldCaptureHooks;
CohStatus coh_world_capture_hooks_begin(CohWorldCaptureHooks *);
void coh_world_capture_hooks_end(void);
#endif
