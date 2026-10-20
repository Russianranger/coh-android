#ifndef COH_INITIAL_CAPTURE_PRIVATE_H
#define COH_INITIAL_CAPTURE_PRIVATE_H
#include "coh_initial_capture.h"
typedef struct CohInitialMap CohInitialMap;
typedef struct {unsigned valid;CohMapPhase phase;} CohInitialMapFailurePhase;
typedef CohStatus (*CohInitialMapObserver)(void *,const CohInitialCaptureEvent *);
CohInitialMap *coh_initial_map_create(CohMapClient *);
void coh_initial_map_destroy(CohInitialMap *);
CohStatus coh_initial_map_service(CohInitialMap *,uint64_t,CohCancel,
 CohInitialMapObserver,void *,const void *,size_t,const void *,size_t);
CohStatus coh_initial_map_lease(const CohInitialMap *,const CohInitialCaptureEvent *,
 CohInitialCaptureLease *);
int coh_initial_map_output_disjoint(const CohInitialMap *,const void *,size_t);
void coh_initial_map_diagnostics(const CohInitialMap *,CohInitialCaptureDiagnostics *);
CohInitialMapFailurePhase coh_initial_map_failure_phase(const CohInitialMap *);
#ifdef COH_FRAME_CAPTURE_DIAGNOSTIC
CohStatus coh_initial_map_local_password_digest(CohInitialMap *,const uint8_t[16]);
CohStatus coh_initial_map_finish_initial(CohInitialMap *,const CohInitialCaptureEvent *,size_t);
void coh_initial_map_forget_ready(CohInitialMap *);
#ifdef COH_BOUNDED_CONTINUATION_DIAGNOSTIC
void coh_initial_map_abort_reason(CohInitialMap *,CohInitialAbort);
#endif
size_t coh_initial_map_continuation_bytes(void);
#endif
#endif
