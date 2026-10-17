#ifndef COH_WR_RIGID_V5_H
#define COH_WR_RIGID_V5_H
#include "coh_wr_rigid.h"
/* Exact v5 rigid CPU entry, independently qualified source header/legacy LOD
 * structure. Preserves original rows and raw legacy LOD bytes; does not APPLY
 * LOD, GRID, tricks or materials, nor infer source/live/GPU/world authority.
 * Same independent digest/material/budget/ownership contract as rigid acquire.
 * Existing default/source0/8 and explicitv7 entry semantics remain unchanged. */
CohStatus coh_wr_rigid_v5_acquire(CohAssetLoader*,const CohWrRigidRequest*,
 const CohWrRigidLimits*,CohCancel,CohWrRigidResource**);
#endif
