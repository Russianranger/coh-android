#ifndef COH_SOURCE_RIGID_INTERNAL_H
#define COH_SOURCE_RIGID_INTERNAL_H
#include "coh_source_rigid.h"
/* Private ownership plumbing for fixed module entry points. Never expose a
 * caller-selected policy/decoder as semantic or source admission. Version0 is
 * the existing source0/8 entry; exact7/5 require the actual retained Body version.
 * Public requests contain no geometry labels/version/generation/mask. */
typedef CohStatus (*CohSourceRigidAcquire)(CohAssetLoader*,const CohWrRigidRequest*,
 const CohWrRigidLimits*,CohCancel,CohWrRigidResource**);
CohStatus coh_source_rigid_create_using(CohSourceBody**,const CohSourceRigidRequest*,
 const CohSourceRigidLimits*,CohCancel,CohSourceRigid**,CohSourceRigidReport*,
 uint32_t,CohSourceRigidAcquire);
#endif
