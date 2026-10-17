#ifndef COH_WR_RIGID_SOURCE_H
#define COH_WR_RIGID_SOURCE_H
#include "coh_wr_rigid.h"
/* Explicit source-header policy using the separately qualified scenecatalog
 * wrapper. Whole body digest/pin, budgets and material constraints are unchanged.
 * All source rows remain validated, including bounded zero-draw metadata rows.
 * Only an ordinary selected model can become CPU geometry. A selected zero row
 * returns COH_UNSUPPORTED before material acquisition; it grants no empty draw,
 * hierarchy pruning, inherited-effect suppression or CLIENT semantic authority.
 * No caller-supplied decoder or forged metadata view is admitted. This entry
 * requires linking coh_resource_geo_source.c; default acquire remains unchanged.
 * Matching live catalog/resource/CLIENT generations remain external gates. */
CohStatus coh_wr_rigid_source_acquire(CohAssetLoader*,const CohWrRigidRequest*,
 const CohWrRigidLimits*,CohCancel,CohWrRigidResource**);
#endif
