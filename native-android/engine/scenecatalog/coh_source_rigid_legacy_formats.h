#ifndef COH_SOURCE_RIGID_LEGACY_FORMATS_H
#define COH_SOURCE_RIGID_LEGACY_FORMATS_H
#include "coh_source_rigid.h"
/* Fixed exactv2/v3/v4 opt-ins. Public requests contain only source ordinal and
 * external material/digest callbacks. Actual retained Body supplies version,
 * path/fullmodel/SHA/owner/generations; no caller geometry labels or mask.
 * Same transfer-on-success/rollback, budgets, borrowed graph+loader lifetime
 * contract as the default. Existing default0/8 and v7/v5 entries stay separate.
 * No portal/material/CLIENT LOD/instance/GPU/live/world permission is granted. */
CohStatus coh_source_rigid_v2_create(CohSourceBody**,const CohSourceRigidRequest*,const CohSourceRigidLimits*,CohCancel,CohSourceRigid**,CohSourceRigidReport*);
CohStatus coh_source_rigid_v3_create(CohSourceBody**,const CohSourceRigidRequest*,const CohSourceRigidLimits*,CohCancel,CohSourceRigid**,CohSourceRigidReport*);
CohStatus coh_source_rigid_v4_create(CohSourceBody**,const CohSourceRigidRequest*,const CohSourceRigidLimits*,CohCancel,CohSourceRigid**,CohSourceRigidReport*);
#endif
