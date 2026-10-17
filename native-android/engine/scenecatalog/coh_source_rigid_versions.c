#include "coh_source_rigid_versions.h"
#include "coh_source_rigid_internal.h"
#include "../world-render-adapter/coh_wr_rigid_v7.h"
#include "../world-render-adapter/coh_wr_rigid_v5.h"
CohStatus coh_source_rigid_v7_create(CohSourceBody**body,const CohSourceRigidRequest*q,
 const CohSourceRigidLimits*b,CohCancel cancel,CohSourceRigid**out,CohSourceRigidReport*r){
 return coh_source_rigid_create_using(body,q,b,cancel,out,r,7,coh_wr_rigid_v7_acquire);
}
CohStatus coh_source_rigid_v5_create(CohSourceBody**body,const CohSourceRigidRequest*q,
 const CohSourceRigidLimits*b,CohCancel cancel,CohSourceRigid**out,CohSourceRigidReport*r){
 return coh_source_rigid_create_using(body,q,b,cancel,out,r,5,coh_wr_rigid_v5_acquire);
}
