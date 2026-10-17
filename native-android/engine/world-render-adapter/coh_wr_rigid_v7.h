#ifndef COH_WR_RIGID_V7_H
#define COH_WR_RIGID_V7_H
#include "coh_wr_rigid.h"
/* Explicit source-header v7 rigid CPU entry ONLY. Existing default and source
 * entries remain v0/v8. Does not apply CLIENT autolod/reductions/GRID/tricks or
 * imply material, geometry-generation, instance, GPU or world authority.
 * Same digest, material callback, aggregate reservation and ownership/lifetime
 * contract as coh_wr_rigid_acquire. Materials require independent qualification. */
CohStatus coh_wr_rigid_v7_acquire(CohAssetLoader*,const CohWrRigidRequest*,
 const CohWrRigidLimits*,CohCancel,CohWrRigidResource**);
#endif
