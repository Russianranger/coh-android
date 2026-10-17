#ifndef COH_WR_RIGID_LEGACY_FORMATS_H
#define COH_WR_RIGID_LEGACY_FORMATS_H
#include "coh_wr_rigid.h"
/* Three separate fixed source-qualified CPU opt-ins, never a caller mask.
 * v2 uses the original fixed legacy216/packs remap; v3/v4 variable records;
 * v4 obsolete lightmap transform slots are preserved and skipped as in source.
 * All validate legacy LOD input; none APPLY CLIENT LOD/tricks/materials or grant
 * source-generation, instance, GPU, live/world authority. Existing entries and
 * their ownership/digest/material/aggregate reservation contracts are preserved. */
CohStatus coh_wr_rigid_v2_acquire(CohAssetLoader*,const CohWrRigidRequest*,const CohWrRigidLimits*,CohCancel,CohWrRigidResource**);
CohStatus coh_wr_rigid_v3_acquire(CohAssetLoader*,const CohWrRigidRequest*,const CohWrRigidLimits*,CohCancel,CohWrRigidResource**);
CohStatus coh_wr_rigid_v4_acquire(CohAssetLoader*,const CohWrRigidRequest*,const CohWrRigidLimits*,CohCancel,CohWrRigidResource**);
#endif
