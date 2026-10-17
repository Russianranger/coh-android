#include "coh_source_rigid_legacy_formats.h"
#include "coh_source_rigid_internal.h"
#include "../world-render-adapter/coh_wr_rigid_legacy_formats.h"
#define ENTRY(version) \
CohStatus coh_source_rigid_v##version##_create(CohSourceBody**body,const CohSourceRigidRequest*q,const CohSourceRigidLimits*b,CohCancel cancel,CohSourceRigid**out,CohSourceRigidReport*r){return coh_source_rigid_create_using(body,q,b,cancel,out,r,version,coh_wr_rigid_v##version##_acquire);}
ENTRY(2)
ENTRY(3)
ENTRY(4)
#undef ENTRY
