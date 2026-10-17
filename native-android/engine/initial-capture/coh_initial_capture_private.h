#ifndef COH_INITIAL_CAPTURE_PRIVATE_H
#define COH_INITIAL_CAPTURE_PRIVATE_H
#include "coh_initial_capture.h"
typedef struct CohInitialMap CohInitialMap;
typedef CohStatus (*CohInitialMapObserver)(void *,const CohInitialCaptureEvent *);
CohInitialMap *coh_initial_map_create(CohMapClient *);
void coh_initial_map_destroy(CohInitialMap *);
CohStatus coh_initial_map_service(CohInitialMap *,uint64_t,CohCancel,
 CohInitialMapObserver,void *,const void *,size_t,const void *,size_t);
CohStatus coh_initial_map_lease(const CohInitialMap *,const CohInitialCaptureEvent *,
 CohInitialCaptureLease *);
int coh_initial_map_output_disjoint(const CohInitialMap *,const void *,size_t);
void coh_initial_map_diagnostics(const CohInitialMap *,CohInitialCaptureDiagnostics *);
#endif
