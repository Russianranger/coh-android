#ifndef COH_WR_RIGID_INTERNAL_H
#define COH_WR_RIGID_INTERNAL_H
/* Private decoder plumbing for the explicit source-qualified module entry points.
 * Do not expose these callbacks as an asset or semantic admission interface. */
#include "coh_wr_rigid.h"
typedef CohStatus (*CohWrRigidHeaderOpen)(CohBytes,uint8_t*,size_t,uint32_t,CohAssetGeo*);
typedef CohStatus (*CohWrRigidHeaderModel)(const CohAssetGeo*,uint32_t,CohAssetGeoModel*,uint32_t*);
CohStatus coh_wr_rigid_acquire_using(CohAssetLoader*,const CohWrRigidRequest*,
 const CohWrRigidLimits*,CohCancel,CohWrRigidResource**,CohWrRigidHeaderOpen,CohWrRigidHeaderModel);
typedef enum {COH_WR_RIGID_DEFAULT_0_8=0,COH_WR_RIGID_EXACT_SOURCE_7=7,COH_WR_RIGID_EXACT_SOURCE_5=5,COH_WR_RIGID_EXACT_SOURCE_2=2,COH_WR_RIGID_EXACT_SOURCE_3=3,COH_WR_RIGID_EXACT_SOURCE_4=4} CohWrRigidPolicy;
/* Internal, fixed module policy. No caller-forged header view or public
 * permission callback. Existing entry always selects DEFAULT_0_8. */
CohStatus coh_wr_rigid_acquire_policy(CohAssetLoader*,const CohWrRigidRequest*,
 const CohWrRigidLimits*,CohCancel,CohWrRigidResource**,CohWrRigidHeaderOpen,
 CohWrRigidHeaderModel,CohWrRigidPolicy);
#endif
