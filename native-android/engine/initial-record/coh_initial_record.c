#include "coh_initial_record.h"
#include "../selected-record/coh_record_kernel.h"
CohStatus coh_initial_record_read(CohRepReader*r,const CohSelectedRecordContext*c,
 const CohEntSlot*p,const CohSelectedRecordMemory*m,CohSelectedRecord*out,
 CohSelectedRecordWorkspace*w,CohSelectedRecordFailure*f,size_t budget,size_t retained){
 return coh_record_kernel_read(r,c,p,m,out,w,f,budget,retained,COH_RECORD_PROFILE_INITIAL_CREATE);
}
