#ifndef COH_SOURCE_RIGID_VERSIONS_H
#define COH_SOURCE_RIGID_VERSIONS_H
#include "coh_source_rigid.h"
/* Separate exact-version opt-ins, preserving the existing source0/8 factory.
 * The actual opaque Body derives version/path/model/SHA/owner/generations;
 * public request supplies only joinordinal and external material callbacks.
 * A mismatched actual Body refuses before allocation/material callbacks.
 * Same transfer-on-complete-success, immutable lease, budget and borrowed graph/
 * loader lifetime contract as coh_source_rigid_create. No public policy mask.
 * CLIENT materials/LOD, direct open, live/world/GPU authority remain absent. */
CohStatus coh_source_rigid_v7_create(CohSourceBody**,const CohSourceRigidRequest*,
 const CohSourceRigidLimits*,CohCancel,CohSourceRigid**,CohSourceRigidReport*);
CohStatus coh_source_rigid_v5_create(CohSourceBody**,const CohSourceRigidRequest*,
 const CohSourceRigidLimits*,CohCancel,CohSourceRigid**,CohSourceRigidReport*);
#endif
