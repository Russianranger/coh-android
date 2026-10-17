#ifndef COH_WR_RIGID_INTERNAL_H
#define COH_WR_RIGID_INTERNAL_H
/* Private decoder plumbing for the two source-qualified module entry points.
 * Do not expose these callbacks as an asset or semantic admission interface. */
#include "coh_wr_rigid.h"
typedef CohStatus (*CohWrRigidHeaderOpen)(CohBytes,uint8_t*,size_t,uint32_t,CohAssetGeo*);
typedef CohStatus (*CohWrRigidHeaderModel)(const CohAssetGeo*,uint32_t,CohAssetGeoModel*,uint32_t*);
CohStatus coh_wr_rigid_acquire_using(CohAssetLoader*,const CohWrRigidRequest*,
 const CohWrRigidLimits*,CohCancel,CohWrRigidResource**,CohWrRigidHeaderOpen,CohWrRigidHeaderModel);
#endif
