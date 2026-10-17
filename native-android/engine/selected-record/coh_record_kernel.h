#ifndef COH_RECORD_KERNEL_H
#define COH_RECORD_KERNEL_H
/* Private shared grammar. Public callers use the constrained profile wrappers. */
#include "coh_selected_record.h"
#define COH_RECORD_PROFILE_SELECTED 1u
#define COH_RECORD_PROFILE_INITIAL_CREATE 2u
CohStatus coh_record_kernel_read(CohRepReader*,const CohSelectedRecordContext*,
 const CohEntSlot*,const CohSelectedRecordMemory*,CohSelectedRecord*,
 CohSelectedRecordWorkspace*,CohSelectedRecordFailure*,size_t,size_t,unsigned);
#endif
